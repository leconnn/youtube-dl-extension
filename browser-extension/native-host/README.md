# Native messaging host

This is what the Firefox extension actually talks to. Firefox launches this
process itself via `browser.runtime.connectNative()` and manages its
lifecycle, so there's no server to start by hand and no auth token to pair
(compare to `backend/server.py`, which is the old/dev-only HTTP path kept
around for fast curl-based iteration).

`host.py` speaks Firefox's native messaging stdio protocol (4-byte
little-endian length prefix + UTF-8 JSON, both directions) and shares its
actual extraction/download logic with `backend/server.py` via
`backend/core.py`.

## Local dev setup (no packaging)

Prerequisite: `pip install yt-dlp` (not vendored in this repo; both
`host.py` and `backend/server.py` import it as a normal dependency).

Firefox finds native messaging hosts via a registry key whose value is the
absolute path to a manifest JSON file, whose own `path` field is the
absolute path to an executable (no arguments allowed). For local testing
before any PyInstaller build exists, that executable is a small `.bat`
wrapper around `pythonw.exe` (a GUI-subsystem Python avoids a console
window flashing on every launch).

1. Create `host_dev.bat` next to this README (gitignored, since it has your
   local Python path baked in):
   ```bat
   @echo off
   "<path to pythonw.exe>" "<repo>\browser-extension\native-host\host.py"
   ```

2. Copy `com.leconnn.youtube_dl_extension.json.template` to
   `com.leconnn.youtube_dl_extension.json` (gitignored) next to it, and
   replace `__HOST_EXE_PATH__` with the absolute path to `host_dev.bat`
   (JSON-escape backslashes, e.g. `C:\\Users\\you\\...\\host_dev.bat`).

3. Register it for your user (no admin rights needed):
   ```powershell
   $key = 'HKCU:\Software\Mozilla\NativeMessagingHosts\com.leconnn.youtube_dl_extension'
   New-Item -Path $key -Force | Out-Null
   Set-ItemProperty -Path $key -Name '(Default)' -Value '<repo>\browser-extension\native-host\com.leconnn.youtube_dl_extension.json'
   ```

4. Load the extension via `about:debugging#/runtime/this-firefox` as usual.
   No options page / token step anymore; it just works once the registry
   key points at a valid manifest.

Check `%LOCALAPPDATA%\youtube-dl-extension\host.log` if something isn't
connecting. `host.py` never prints to stdout/stderr (that would corrupt
the message stream Firefox reads), so all diagnostics go there instead.

## Packaging

Once bundled with PyInstaller (`pyinstaller host.spec`), `path` in the
manifest points directly at the built `host.exe` instead of `host_dev.bat`,
and the Windows installer (`../installer/`) writes the manifest + registry
key automatically instead of doing it by hand. See `../installer/README.md`
for the full build, and `vendor/README.md` for the ffmpeg licensing note
before bundling one in.
