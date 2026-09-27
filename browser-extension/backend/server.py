#!/usr/bin/env python
# coding: utf-8
"""Local backend for the youtube-dl browser extension.

Runs a small HTTP server on 127.0.0.1 that the Firefox extension talks to.
It uses this repo's `youtube_dl` package to inspect a page's available
qualities and to download+convert to MP4 / MP3 / WAV via ffmpeg.

Usage:
    python server.py [port]

The first run generates browser-extension/backend/token.txt containing an
auth token. Paste that token into the extension's options page so the
extension is allowed to talk to this server.
"""

from __future__ import unicode_literals

import json
import os
import re
import secrets
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(BACKEND_DIR))
sys.path.insert(0, REPO_ROOT)

import youtube_dl  # noqa: E402

TOKEN_PATH = os.path.join(BACKEND_DIR, 'token.txt')
DOWNLOAD_DIR = os.path.join(os.path.expanduser('~'), 'Downloads', 'youtube-dl-extension')
DEFAULT_PORT = 4325

YOUTUBE_URL_RE = re.compile(
    r'^https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/)|youtu\.be/)',
    re.IGNORECASE,
)

MP3_QUALITIES = {'best', '320', '256', '192', '128'}

jobs = {}
jobs_lock = threading.Lock()


def get_or_create_token():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as f:
            token = f.read().strip()
            if token:
                return token
    token = secrets.token_urlsafe(24)
    with open(TOKEN_PATH, 'w') as f:
        f.write(token)
    return token


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


def run_download(job_id, url, mode, quality):
    ensure_download_dir()

    def hook(d):
        with jobs_lock:
            job = jobs[job_id]
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes') or 0
                if total:
                    job['percent'] = round(downloaded * 100 / total, 1)
                job['status'] = 'downloading'
            elif d['status'] == 'finished':
                job['status'] = 'converting'
                job['percent'] = 100

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noprogress': False,
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'progress_hooks': [hook],
        'restrictfilenames': False,
        'noplaylist': True,
    }

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
        if quality and quality != 'best':
            pp['preferredquality'] = quality
        else:
            pp['preferredquality'] = '0'
        ydl_opts['postprocessors'] = [pp]
    elif mode == 'wav':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}]
    else:
        with jobs_lock:
            jobs[job_id] = {'status': 'error', 'error': 'Unknown mode: %s' % mode}
        return

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_path = expected_final_path(ydl, info, mode)
        with jobs_lock:
            jobs[job_id] = {
                'status': 'finished',
                'percent': 100,
                'filename': os.path.basename(final_path),
                'path': final_path,
            }
    except Exception as e:
        with jobs_lock:
            jobs[job_id] = {'status': 'error', 'error': str(e)}


class Handler(BaseHTTPRequestHandler):
    server_version = 'ytdl-ext-backend/0.1'

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))

    def _cors_origin(self):
        origin = self.headers.get('Origin', '')
        if origin.startswith('moz-extension://'):
            return origin
        return None

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        origin = self._cors_origin()
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self):
        expected = get_or_create_token()
        got = self.headers.get('X-Auth-Token', '')
        return secrets.compare_digest(got, expected)

    def do_OPTIONS(self):
        self.send_response(204)
        origin = self._cors_origin()
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Auth-Token')
        self.send_header('Access-Control-Max-Age', '600')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/ping':
            self._send_json(200, {'ok': True, 'version': youtube_dl.version.__version__})
            return

        if not self._check_auth():
            self._send_json(403, {'error': 'Invalid or missing X-Auth-Token'})
            return

        if parsed.path == '/formats':
            qs = parse_qs(parsed.query)
            url = (qs.get('url') or [''])[0]
            if not url or not YOUTUBE_URL_RE.match(url):
                self._send_json(400, {'error': 'URL is missing or not a supported (YouTube) URL'})
                return
            try:
                ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True}
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                self._send_json(502, {'error': 'Failed to read video info: %s' % e})
                return
            if info.get('_type') == 'playlist' or 'formats' not in info:
                self._send_json(400, {'error': 'Playlists are not supported yet. Open an individual video.'})
                return
            self._send_json(200, {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'video_qualities': video_qualities_from_info(info),
                'mp3_qualities': sorted(MP3_QUALITIES, key=lambda q: (q != 'best', -int(q) if q != 'best' else 0)),
            })
            return

        if parsed.path == '/status':
            qs = parse_qs(parsed.query)
            job_id = (qs.get('id') or [''])[0]
            with jobs_lock:
                job = jobs.get(job_id)
            if job is None:
                self._send_json(404, {'error': 'Unknown job id'})
                return
            self._send_json(200, job)
            return

        self._send_json(404, {'error': 'Not found'})

    def do_POST(self):
        if not self._check_auth():
            self._send_json(403, {'error': 'Invalid or missing X-Auth-Token'})
            return

        parsed = urlparse(self.path)
        if parsed.path != '/download':
            self._send_json(404, {'error': 'Not found'})
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except ValueError:
            self._send_json(400, {'error': 'Invalid JSON body'})
            return

        url = body.get('url', '')
        mode = body.get('mode', '')
        quality = body.get('quality')

        if not url or not YOUTUBE_URL_RE.match(url):
            self._send_json(400, {'error': 'URL is missing or not a supported (YouTube) URL'})
            return
        if mode not in ('mp4', 'mp3', 'wav'):
            self._send_json(400, {'error': 'mode must be one of mp4, mp3, wav'})
            return
        if mode == 'mp4' and not quality:
            self._send_json(400, {'error': 'quality (target height) is required for mp4'})
            return
        if mode == 'mp3' and quality and str(quality) not in MP3_QUALITIES:
            self._send_json(400, {'error': 'invalid mp3 quality'})
            return

        job_id = uuid.uuid4().hex
        with jobs_lock:
            jobs[job_id] = {'status': 'starting', 'percent': 0}

        thread = threading.Thread(target=run_download, args=(job_id, url, mode, quality), daemon=True)
        thread.start()

        self._send_json(200, {'job_id': job_id})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    ensure_download_dir()
    token = get_or_create_token()
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('youtube-dl extension backend')
    print('  listening on http://127.0.0.1:%d' % port)
    print('  downloads saved to %s' % DOWNLOAD_DIR)
    print('  auth token (paste into the extension options page): %s' % token)
    print('  (token also saved to %s)' % TOKEN_PATH)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
