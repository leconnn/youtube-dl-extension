# youtube-dl Firefox extension

Adds a toolbar button that downloads the YouTube video on the current tab as
MP4 (with a quality picker), or extracts its audio as MP3 (with a bitrate
picker) or WAV.

## Why a local backend?

A browser extension can't run this repo's Python `youtube_dl` engine or
`ffmpeg` by itself. So this extension talks to a small local HTTP server
(`backend/server.py`) that runs on your machine, uses `youtube_dl` from this
repo to resolve formats and download, and uses `ffmpeg` to convert/merge.
Only YouTube is supported for now; the backend can be extended to any site
`youtube_dl` already supports.

## Requirements

- Python 3 (this repo's `youtube_dl` package, already in the repo root)
- `ffmpeg` available on your `PATH`
- Firefox

## 1. Run the backend

```
python browser-extension/backend/server.py
```

This prints an auth token and starts listening on `http://127.0.0.1:4325`.
Downloads are saved to `~/Downloads/youtube-dl-extension/`. Keep this
running while you use the extension.

## 2. Load the extension in Firefox

1. Go to `about:debugging#/runtime/this-firefox`.
2. Click "Load Temporary Add-on…" and select
   `browser-extension/extension/manifest.json`.
3. Click the extension's toolbar icon, then "Backend settings" to open its
   options page, and paste in the token printed by the server (also saved to
   `browser-extension/backend/token.txt`).

(Temporary add-ons are removed when Firefox restarts — reload them from
`about:debugging` each session, or package/sign the extension for permanent
installation.)

## 3. Use it

Open a YouTube video, click the toolbar icon, choose MP4 (+ resolution), MP3
(+ bitrate), or WAV, and click Download. Progress is shown in the popup; the
finished file lands in `~/Downloads/youtube-dl-extension/`.

## Notes / limitations

- YouTube only, by design, to start (see the main repo README for the full
  list of sites `youtube_dl` supports — extending `/formats` and `/download`
  in `backend/server.py` to other sites is straightforward).
- The backend only accepts requests carrying the correct `X-Auth-Token` and
  only allows CORS from `moz-extension://` origins, so other websites open
  in your browser can't silently trigger downloads.
- The backend binds to `127.0.0.1` only (not your network).
