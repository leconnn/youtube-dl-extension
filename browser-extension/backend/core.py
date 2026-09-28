#!/usr/bin/env python
# coding: utf-8
"""Shared yt-dlp extraction/download logic.

Used by both server.py (the local HTTP dev/test backend) and
native-host/host.py (the native messaging host used by the packaged
extension), so the actual extraction/conversion behavior only lives in one
place.
"""

from __future__ import unicode_literals

import json
import os
import re

import yt_dlp
from yt_dlp.utils import sanitize_filename

DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser('~'), 'Downloads', 'youtube-dl-extension')

APP_DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'), 'youtube-dl-extension')
CONFIG_PATH = os.path.join(APP_DATA_DIR, 'config.json')

YOUTUBE_URL_RE = re.compile(
    r'^https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/)|youtu\.be/)',
    re.IGNORECASE,
)

MP3_QUALITIES = {'best', '320', '256', '192', '128'}

MODE_EXTENSIONS = {'mp4': 'mp4', 'mp3': 'mp3', 'wav': 'wav'}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (ValueError, OSError):
            pass
    return {}


def save_config(config):
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f)


def get_download_dir():
    return load_config().get('download_dir') or DEFAULT_DOWNLOAD_DIR


def set_download_dir(path):
    """Validates `path` (or clears the override if falsy) and persists it."""
    if path:
        path = os.path.expanduser(path)
        os.makedirs(path, exist_ok=True)
    config = load_config()
    config['download_dir'] = path or None
    save_config(config)
    return get_download_dir()


def ensure_download_dir(download_dir=None):
    d = download_dir or get_download_dir()
    os.makedirs(d, exist_ok=True)
    return d


def _format_size(fmt):
    return fmt.get('filesize') or fmt.get('filesize_approx')


def _best_by_size(candidates, preferred_ext):
    """Picks the candidate matching `preferred_ext` if any do (mirroring the
    ext preference in run_download's format-selector strings), then the one
    with the largest known size among those, as a stand-in for "best"."""
    pool = [f for f in candidates if f.get('ext') == preferred_ext] or candidates
    sized = [f for f in pool if _format_size(f)]
    if sized:
        return max(sized, key=_format_size)
    return pool[0] if pool else None


def video_qualities_from_info(info):
    """Returns [{height, estimated_bytes}, ...] sorted by height descending.
    estimated_bytes is None when yt-dlp didn't report a size for the
    formats at that height (common for some DASH streams); it's always an
    approximation since it doesn't reproduce yt-dlp's exact format selector.
    """
    formats = info.get('formats') or []
    audio_only = [f for f in formats if f.get('acodec') not in (None, 'none') and f.get('vcodec') in (None, 'none')]
    best_audio = _best_by_size(audio_only, 'm4a')
    audio_size = _format_size(best_audio) if best_audio else None

    heights = set()
    for fmt in formats:
        if fmt.get('vcodec') and fmt.get('vcodec') != 'none' and fmt.get('height'):
            heights.add(int(fmt['height']))

    qualities = []
    for h in sorted(heights, reverse=True):
        video_candidates = [f for f in formats if f.get('vcodec') not in (None, 'none') and f.get('height') == h]
        best_video = _best_by_size(video_candidates, 'mp4')
        video_size = _format_size(best_video) if best_video else None
        if video_size is not None and audio_size is not None:
            estimated_bytes = video_size + audio_size
        elif video_size is not None:
            estimated_bytes = video_size
        else:
            estimated_bytes = None
        qualities.append({'height': h, 'estimated_bytes': estimated_bytes})
    return qualities


def best_audio_kbps(info):
    """Highest audio-only bitrate available, used to estimate MP3 'best'
    (VBR) output size; None if yt-dlp didn't report one."""
    audio_only = [f for f in (info.get('formats') or []) if f.get('acodec') not in (None, 'none') and f.get('vcodec') in (None, 'none')]
    abrs = [f['abr'] for f in audio_only if f.get('abr')]
    return max(abrs) if abrs else None


def expected_final_path(ydl, info, mode):
    base = ydl.prepare_filename(info)
    root, _ext = os.path.splitext(base)
    return root + '.' + MODE_EXTENSIONS[mode]


def dedupe_path(path):
    """If `path` already exists, appends " (2)", " (3)", ... (like a
    browser's own download manager) until a free name is found."""
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    n = 2
    while True:
        candidate = '%s (%d)%s' % (root, n, ext)
        if not os.path.exists(candidate):
            return candidate
        n += 1


def fetch_formats(url):
    """Returns the /formats-style info dict for `url`.

    Raises ValueError (user-facing message) for a bad/unsupported URL or a
    playlist link; other exceptions propagate from yt-dlp as-is (e.g.
    the video being unavailable).
    """
    if not url or not YOUTUBE_URL_RE.match(url):
        raise ValueError('URL is missing or not a supported (YouTube) URL')

    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get('_type') == 'playlist' or 'formats' not in info:
        raise ValueError('Playlists are not supported yet. Open an individual video.')

    return {
        'title': info.get('title'),
        'thumbnail': info.get('thumbnail'),
        'duration': info.get('duration'),
        'video_qualities': video_qualities_from_info(info),
        'mp3_qualities': sorted(MP3_QUALITIES, key=lambda q: (q != 'best', -int(q) if q != 'best' else 0)),
        'best_audio_kbps': best_audio_kbps(info),
    }


def validate_download_request(url, mode, quality):
    """Raises ValueError (user-facing message) if the request is invalid."""
    if not url or not YOUTUBE_URL_RE.match(url):
        raise ValueError('URL is missing or not a supported (YouTube) URL')
    if mode not in ('mp4', 'mp3', 'wav'):
        raise ValueError('mode must be one of mp4, mp3, wav')
    if mode == 'mp4' and not quality:
        raise ValueError('quality (target height) is required for mp4')
    if mode == 'mp3' and quality and str(quality) not in MP3_QUALITIES:
        raise ValueError('invalid mp3 quality')


def run_download(url, mode, quality, on_progress, ffmpeg_location=None, download_dir=None, title=None):
    """Downloads/converts `url` per `mode`/`quality`.

    Calls on_progress(**kwargs) with partial updates as the download
    proceeds (e.g. status='downloading', percent=...; status='converting'),
    then a final call: status='finished', percent=100, filename=..., path=...
    or status='error', error=....

    `ffmpeg_location` lets a frozen/bundled host point at its own bundled
    ffmpeg instead of relying on PATH. `download_dir` overrides the
    configured/default save location for this one call. `title`, if given,
    is used as the saved filename (sanitized) instead of the video's own
    title.

    The target filename is always resolved and deduped (appending " (2)",
    " (3)", ... if something's already there, like a browser's own download
    manager) before the real download starts, so re-downloading the same
    video (or two videos landing on the same name) never silently overwrites
    an existing file or leaves ffmpeg stuck waiting on an overwrite prompt
    with no console attached to show it.
    """
    if mode not in MODE_EXTENSIONS:
        on_progress(status='error', error='Unknown mode: %s' % mode)
        return

    target_dir = ensure_download_dir(download_dir)

    if not title:
        try:
            probe_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True}
            with yt_dlp.YoutubeDL(probe_opts) as probe:
                title = probe.extract_info(url, download=False).get('title') or 'video'
        except Exception as e:
            on_progress(status='error', error=str(e))
            return

    final_path = dedupe_path(os.path.join(target_dir, sanitize_filename(title, restricted=False) + '.' + MODE_EXTENSIONS[mode]))
    outtmpl = os.path.splitext(final_path)[0] + '.%(ext)s'

    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes') or 0
            update = {'status': 'downloading'}
            if total:
                update['percent'] = round(downloaded * 100 / total, 1)
            on_progress(**update)
        elif d['status'] == 'finished':
            on_progress(status='converting', percent=100)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        # We report progress ourselves via progress_hooks; yt-dlp's own
        # progress bar writes raw text straight to stdout regardless of
        # `quiet`, which corrupts the native host's framed stdout protocol
        # (host.py can only ever write well-formed frames there).
        'noprogress': True,
        'outtmpl': outtmpl,
        'progress_hooks': [hook],
        'restrictfilenames': False,
        'noplaylist': True,
    }
    if ffmpeg_location:
        ydl_opts['ffmpeg_location'] = ffmpeg_location

    if mode == 'mp4':
        height = quality
        ydl_opts['format'] = (
            'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/'
            'bestvideo[height<={h}]+bestaudio/best[height<={h}]'
        ).format(h=height)
        ydl_opts['merge_output_format'] = 'mp4'
    elif mode == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}
        pp['preferredquality'] = quality if (quality and quality != 'best') else '0'
        ydl_opts['postprocessors'] = [pp]
    elif mode == 'wav':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_path = expected_final_path(ydl, info, mode)
        on_progress(
            status='finished',
            percent=100,
            filename=os.path.basename(final_path),
            path=final_path,
        )
    except Exception as e:
        on_progress(status='error', error=str(e))
