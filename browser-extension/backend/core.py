#!/usr/bin/env python
# coding: utf-8
"""Shared youtube_dl extraction/download logic.

Used by both server.py (the local HTTP dev/test backend) and
native-host/host.py (the native messaging host used by the packaged
extension), so the actual extraction/conversion behavior only lives in one
place.
"""

from __future__ import unicode_literals

import os
import re
import sys

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(CORE_DIR))
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, REPO_ROOT)

import youtube_dl  # noqa: E402

DOWNLOAD_DIR = os.path.join(os.path.expanduser('~'), 'Downloads', 'youtube-dl-extension')

YOUTUBE_URL_RE = re.compile(
    r'^https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/)|youtu\.be/)',
    re.IGNORECASE,
)

MP3_QUALITIES = {'best', '320', '256', '192', '128'}


def ensure_download_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def video_qualities_from_info(info):
    heights = set()
    for fmt in info.get('formats', []) or []:
        if fmt.get('vcodec') and fmt.get('vcodec') != 'none' and fmt.get('height'):
            heights.add(int(fmt['height']))
    return sorted(heights, reverse=True)


def expected_final_path(ydl, info, mode):
    base = ydl.prepare_filename(info)
    root, _ext = os.path.splitext(base)
    ext = {'mp4': 'mp4', 'mp3': 'mp3', 'wav': 'wav'}[mode]
    return root + '.' + ext


def fetch_formats(url):
    """Returns the /formats-style info dict for `url`.

    Raises ValueError (user-facing message) for a bad/unsupported URL or a
    playlist link; other exceptions propagate from youtube_dl as-is (e.g.
    the video being unavailable).
    """
    if not url or not YOUTUBE_URL_RE.match(url):
        raise ValueError('URL is missing or not a supported (YouTube) URL')

    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get('_type') == 'playlist' or 'formats' not in info:
        raise ValueError('Playlists are not supported yet. Open an individual video.')

    return {
        'title': info.get('title'),
        'thumbnail': info.get('thumbnail'),
        'duration': info.get('duration'),
        'video_qualities': video_qualities_from_info(info),
        'mp3_qualities': sorted(MP3_QUALITIES, key=lambda q: (q != 'best', -int(q) if q != 'best' else 0)),
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


def run_download(url, mode, quality, on_progress, ffmpeg_location=None):
    """Downloads/converts `url` per `mode`/`quality`.

    Calls on_progress(**kwargs) with partial updates as the download
    proceeds (e.g. status='downloading', percent=...; status='converting'),
    then a final call: status='finished', percent=100, filename=..., path=...
    or status='error', error=....

    `ffmpeg_location` lets a frozen/bundled host point at its own bundled
    ffmpeg instead of relying on PATH.
    """
    ensure_download_dir()

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
        'noprogress': False,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
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
    else:
        on_progress(status='error', error='Unknown mode: %s' % mode)
        return

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
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
