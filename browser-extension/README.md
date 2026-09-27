# youtube-dl Firefox extension

Adds a toolbar button that downloads the YouTube video on the current tab as
MP4 (with a quality picker), or extracts its audio as MP3 (with a bitrate
picker) or WAV.

## Why a native messaging host?

A browser extension can't run this repo's Python `youtube_dl` engine or
`ffmpeg` by itself. So the extension talks to a small local process
(`native-host/host.py`) that Firefox itself launches and manages via
`browser.runtime.connectNative()`, using `youtube_dl` from this repo to
resolve formats and download, and `ffmpeg` to convert/merge. There's no
server to start by hand and no token to pair, since Firefox restricts which
extension is allowed to talk to the host. Only YouTube is supported for
now; the host can be extended to any site `youtube_dl` already supports.

`backend/server.py` is a separate, plain HTTP version of the same logic
(sharing `backend/core.py` with the native host), kept around as a faster
curl-testable loop for local development; it's not part of the extension's
actual runtime path.

## Requirements

- Python 3 (this repo's `youtube_dl` package, already in the repo root)
- `ffmpeg` available on your `PATH`
- Firefox

## 1. Register the native messaging host

See `native-host/README.md` for the step-by-step setup: create
`host_dev.bat`, a manifest JSON from the checked-in template, and a
per-user registry key pointing Firefox at it. This is a one-time step per
machine; once it's done, Firefox launches the host itself whenever the
extension needs it.

## 2. Load the extension in Firefox

1. Go to `about:debugging#/runtime/this-firefox`.
2. Click "Load Temporary Add-on..." and select
   `browser-extension/extension/manifest.json`.

(Temporary add-ons are removed when Firefox restarts, so reload them from
`about:debugging` each session, or package/sign the extension for permanent
installation.)

## 3. Use it

Open a YouTube video, click the toolbar icon, choose MP4 (+ resolution), MP3
(+ bitrate), or WAV, and click Download. The filename box is pre-filled with
the video's own title as a placeholder; type over it to save under a
different name. Progress is shown in the popup, and you'll get a desktop
notification when it finishes or fails even if you've closed the popup,
since the background script tracks the job independently.

By default the finished file lands in `~/Downloads/youtube-dl-extension/`.
Click the gear icon in the popup to set a different download location; it's
saved on the native host side (in a small config file under
`%LOCALAPPDATA%\youtube-dl-extension\`), not per-browser-profile, so it
applies regardless of which Firefox profile opens the popup.

If a file with the resulting name already exists (re-downloading the same
video, or two videos ending up with the same name), the saved file gets
" (2)", " (3)", etc. appended, the same way a browser's own download
manager avoids overwriting.

## Notes / limitations

- YouTube only, by design, to start (see the main repo README for the full
  list of sites `youtube_dl` supports; extending `core.fetch_formats`/
  `core.run_download` to other sites is straightforward, since both the
  native host and the dev HTTP server share that logic).
- Playlist URLs aren't supported yet: a `watch?...&list=...` link downloads
  just that one video, and a bare playlist link is rejected with a message
  rather than silently doing the wrong thing.
- Respect copyright and each site's Terms of Service when downloading; this
  tool doesn't grant any rights to content you don't already have.
