#!/usr/bin/env python
# coding: utf-8
"""Native messaging host for the youtube-dl Downloader Firefox extension.

Speaks Firefox's native messaging stdio protocol: each message is a 4-byte
little-endian length prefix followed by that many bytes of UTF-8 JSON, in
both directions. Firefox launches this process on
`browser.runtime.connectNative()` and kills it when the port disconnects, so
there's no server to start by hand and no auth token to pair.

Must never write anything but well-formed frames to stdout -- all logging
goes to a file instead.
"""

from __future__ import unicode_literals

import json
import logging
import os
import struct
import sys
import threading

HOST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(os.path.dirname(HOST_DIR), 'backend')
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, BACKEND_DIR)

import core  # noqa: E402

LOG_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'youtube-dl-extension')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'host.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
log = logging.getLogger('host')

# When bundled with PyInstaller, ffmpeg ships alongside the executable
# instead of relying on PATH.
FFMPEG_LOCATION = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None

STDOUT_LOCK = threading.Lock()


def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        return None  # stdin closed: Firefox disconnected the port
    length = struct.unpack('<I', raw_length)[0]
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode('utf-8'))


def send_message(message):
    try:
        data = json.dumps(message).encode('utf-8')
        with STDOUT_LOCK:
            sys.stdout.buffer.write(struct.pack('<I', len(data)))
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
    except Exception:
        log.exception('failed to send message: %r', message)


def handle_ping(msg):
    send_message({'type': 'pong', 'requestId': msg.get('requestId')})


def handle_formats(msg):
    request_id = msg.get('requestId')
    try:
        info = core.fetch_formats(msg.get('url', ''))
        send_message(dict(info, type='formatsResult', requestId=request_id, ok=True))
    except Exception as e:
        send_message({'type': 'formatsResult', 'requestId': request_id, 'ok': False, 'error': str(e)})


def handle_download(msg):
    request_id = msg.get('requestId')
    url = msg.get('url', '')
    mode = msg.get('mode', '')
    quality = msg.get('quality')

    def on_progress(**kwargs):
        send_message(dict(kwargs, type='jobUpdate', requestId=request_id))

    try:
        core.validate_download_request(url, mode, quality)
    except ValueError as e:
        on_progress(status='error', error=str(e))
        return

    on_progress(status='starting', percent=0)
    core.run_download(url, mode, quality, on_progress, ffmpeg_location=FFMPEG_LOCATION)


def main():
    log.info('host started, pid=%s, frozen=%s', os.getpid(), getattr(sys, 'frozen', False))
    try:
        while True:
            try:
                msg = read_message()
            except Exception:
                log.exception('failed to read/parse a message; exiting')
                break
            if msg is None:
                log.info('stdin closed, exiting')
                break

            msg_type = msg.get('type')
            if msg_type == 'ping':
                handle_ping(msg)
            elif msg_type == 'formats':
                threading.Thread(target=handle_formats, args=(msg,), daemon=True).start()
            elif msg_type == 'download':
                threading.Thread(target=handle_download, args=(msg,), daemon=True).start()
            else:
                log.warning('unknown message type: %r', msg_type)
    except Exception:
        log.exception('fatal error in main loop')


if __name__ == '__main__':
    main()
