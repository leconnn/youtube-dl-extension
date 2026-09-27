# youtube-dl-extension

A Firefox extension for downloading YouTube videos as MP4, MP3, or WAV,
built on top of [ytdl-org/youtube-dl](https://github.com/ytdl-org/youtube-dl)'s
download engine.

**[See `browser-extension/README.md` for the actual project](browser-extension/README.md):**
what it does, how to install it, and how it works.

## Why this repo looks like a youtube-dl fork

It is one, structurally: the `youtube_dl/` package here is that engine
(extraction, format selection, downloading, ffmpeg post-processing), which
`browser-extension/native-host/host.py` runs as a Firefox native messaging
host so the extension can trigger real downloads without a browser
extension needing filesystem or subprocess access of its own.

Everything from the original project that this one doesn't use, its CLI
entry point, man pages, shell completions, PyPI packaging, and its test
suite and CI matrix (which covers Python versions and site extractors this
project has no use for), has been removed to keep the repository focused
on what's actually here: the download engine plus the extension built on
it. See `youtube_dl/`'s own docstrings and `LICENSE` (Unlicense, unchanged)
for the engine's origins.

## Layout

- `youtube_dl/`: the download engine (mostly unmodified upstream code).
- `browser-extension/`: the actual project. Start with its README.

## License

Unlicense (public domain), see `LICENSE`. This covers both the retained
`youtube_dl/` engine and the `browser-extension/` code added on top of it.
