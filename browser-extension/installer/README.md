# Building the Windows installer

This is the developer-facing build process. For the end-user installation
guide, see `browser-extension/README.md`.

`setup.iss` (Inno Setup) produces one `.exe` that installs everything a user
needs: the bundled native host (Python + yt-dlp + ffmpeg, via PyInstaller),
and the Firefox extension itself (signed by Mozilla through their unlisted
distribution channel, not a public Add-ons store listing), registered
through Firefox's enterprise policy mechanism since it isn't publicly
listed; see "Why isn't the extension in the Firefox Add-ons store" in the
main README.

## One-time setup

- `pip install pyinstaller yt-dlp` (neither is a dependency of anything
  else in this repo; only needed for building the installer)
- An LGPL Windows ffmpeg build in `../native-host/vendor/ffmpeg/ffmpeg.exe`
  and `ffprobe.exe`, see `../native-host/vendor/README.md`
- Inno Setup 6: `winget install -e --id JRSoftware.InnoSetup --scope user --silent`
  (installs to `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`)

## Build

```powershell
.\build.ps1
```

This packages `browser-extension/extension/` into `youtube-dl-extension.xpi`,
runs `pyinstaller host.spec` in `native-host/` to produce `dist/host/`, then
compiles `setup.iss`. The result is
`browser-extension/installer/Output/youtube-dl-extension-setup.exe`.

None of `dist/`, `build/`, `vendor/ffmpeg/`, `Output/`, or the generated
`.xpi` are committed to git (large binaries, and the `.xpi`/installer are
published as GitHub Release assets instead, not repo files).

## What the installer actually does

Requires admin rights (needed for both of the steps below), all under one
UAC prompt:

1. Copies the bundled host (`host.exe` + `_internal/`, including ffmpeg) to
   `Program Files\youtube-dl-extension\`.
2. Writes a native messaging manifest there and registers it at
   `HKLM\SOFTWARE\Mozilla\NativeMessagingHosts\com.leconnn.youtube_dl_extension`.
3. Locates the Firefox installation via the Windows App Paths registry key,
   and if it doesn't already have a `distribution\policies.json`, writes one
   that installs the bundled `.xpi` via Firefox's `ExtensionSettings` policy.
   If a `policies.json` already exists, the installer leaves it alone and
   shows the snippet to add by hand instead of risking overwriting an
   existing configuration.

The uninstaller reverses all of this: removes the install directory, the
registry key, and (only if this installer created it) the Firefox
`policies.json` it wrote.

## Testing changes to this script

Compiling doesn't run the installer. Actually running it modifies real
system state (Program Files, HKLM, and whatever Firefox install it finds),
so test on a VM or throwaway machine when possible, and always verify the
uninstaller actually undoes each step, before pointing it at a machine you
care about.
