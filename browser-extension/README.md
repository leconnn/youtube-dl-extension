# youtube-dl Firefox extension

Adds a toolbar button that downloads the YouTube video on the current tab as
MP4 (with a resolution picker), or extracts its audio as MP3 (with a bitrate
picker) or WAV. Estimated file size is shown for each option before you
download. Windows and Firefox only, for now.

## Installing (Windows)

1. Close Firefox completely if it's open. The installer needs this (see
   below) and will prompt you to close it if you forget.
2. Download `youtube-dl-extension-setup.exe` from the
   [latest release](https://github.com/leconnn/youtube-dl-extension/releases/latest).
3. Run it. Windows will show a SmartScreen warning ("Windows protected your
   PC") because the installer isn't code-signed; click "More info", then
   "Run anyway". This is expected, not a sign of anything wrong; see
   "Why the SmartScreen warning" below.
4. Approve the admin prompt (UAC). Admin rights are needed because the
   installer writes to Program Files and to Firefox's own installation
   folder; see "What the installer actually does" below for exactly what it
   changes.
5. On the finish page, leave "Launch Firefox now" checked (or open it
   yourself afterward). Then open a YouTube video and click the extension's
   toolbar icon (it may be tucked under the puzzle piece icon; click it,
   then optionally pin the extension).

That's it. No Python install, no separate ffmpeg download, no manual
Firefox configuration; the installer bundles everything the extension needs.

Why Firefox has to be closed: it only reads its extension configuration at
startup, so installing (or upgrading) while it's already running would
leave the extension not actually appear until some later restart you might
not think to make.

### Why the SmartScreen warning

The installer and the bundled program it installs (`host.exe`) aren't
signed with a code-signing certificate (those cost money on an ongoing
basis; this is a personal, free project). Unsigned Windows executables
routinely trigger SmartScreen and occasionally third-party antivirus,
regardless of what they actually do; it's a reputation heuristic, not a
detection of anything specific in this code. If you want to verify the
installer yourself before running it, the full source for everything it
contains is this repository; see "Building from source" below.

### What the installer actually does

Everything happens under a single admin prompt:

- Copies the bundled program (a native Python runtime plus this repo's
  `youtube_dl` engine plus ffmpeg, packaged together so nothing separate
  needs installing) to `Program Files\youtube-dl-extension\`.
- Registers that program as a Firefox native messaging host, at
  `HKLM\SOFTWARE\Mozilla\NativeMessagingHosts\com.leconnn.youtube_dl_extension`.
  This is what lets Firefox launch it on demand instead of you having to
  start anything by hand.
- Installs the extension itself into Firefox via Firefox's enterprise
  policy mechanism (a `distribution\policies.json` file next to
  `firefox.exe`). The extension is signed by Mozilla (through their
  unlisted/self-distribution channel, not a public Add-ons store listing),
  since regular release Firefox refuses to install an unsigned extension
  even via this mechanism; see "Why isn't the extension in the Firefox
  Add-ons store" below. If Firefox already has a `distribution\policies.json`
  (uncommon, usually only on managed/enterprise machines), the installer
  leaves it alone rather than risk overwriting it, and shows you the few
  lines to add by hand instead.

Uninstalling (via Windows Settings, like any other program) reverses all
three steps.

### Why isn't the extension in the Firefox Add-ons store

It is signed by Mozilla, just not publicly listed. Getting an unlisted,
self-distributed signed copy is a quick one-time setup (a free Mozilla
add-on developer account and API credentials) repeated for every release;
a full public listing adds a review/discovery process on top of that,
which isn't needed for a tool distributed via its own GitHub releases. The
enterprise policy install above is a real Firefox feature for installing a
signed-but-unlisted extension outside the store, not a workaround; what it
cannot do is skip signing entirely; regular release Firefox enforces that
regardless of installation method.

## Using it

Open a YouTube video, click the toolbar icon, choose MP4 (with resolution),
MP3 (with bitrate), or WAV, each showing an estimated file size, and click
Download.

The filename box is pre-filled with the video's own title as gray
placeholder text; type over it to save under a different name.

Progress shows in the popup, and you get a desktop notification when it
finishes or fails even if you've closed the popup, since a background
script tracks the job independently. Click a finished-download notification
to open its folder in Explorer with the file selected.

By default the finished file lands in `Downloads\youtube-dl-extension\` in
your user folder. Click the gear icon in the popup to set a different
download location.

If a file with the resulting name already exists (re-downloading the same
video, or two videos ending up with the same name), the saved file gets
" (2)", " (3)", and so on appended, the same way a browser's own download
manager avoids overwriting.

Click the sun/moon icon to switch between light and dark mode; your choice
is remembered.

## Notes and limitations

- YouTube only, by design, for now. See the main repository README for the
  full list of sites `youtube_dl` supports; extending
  `core.fetch_formats`/`core.run_download` to other sites is
  straightforward, since both the native host and the dev HTTP server
  share that logic.
- Playlist URLs aren't supported yet: a `watch?...&list=...` link downloads
  just that one video, and a bare playlist link is rejected with a message
  rather than silently doing the wrong thing.
- No auto-update. A new release means downloading and running the new
  installer; it upgrades the existing install in place.
- Respect copyright and each site's Terms of Service when downloading; this
  tool doesn't grant any rights to content you don't already have.

## Licensing note on the bundled ffmpeg

The installer bundles an ffmpeg build sourced from
[BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds), configured for
LGPL rather than GPL licensing, so redistributing it doesn't carry GPL's
source-offer obligations. See `native-host/vendor/README.md` for the exact
version and build configuration used. The rest of this repository's own
code is Unlicense (public domain); see the top-level `LICENSE` file.

## Uninstalling

Uninstall "youtube-dl Downloader" from Windows Settings > Apps, same as any
other program. This removes the installed files, the native messaging
registry entry, and the Firefox policy entry (if the installer created it).
You may also want to remove the extension from `about:addons` in Firefox,
though the uninstaller already prevents it from being installed again on
next Firefox launch.

## Building from source

See `installer/README.md` for building the Windows installer from scratch
(PyInstaller bundling, sourcing ffmpeg, compiling with Inno Setup), or
`native-host/README.md` for a lighter local development setup that skips
packaging entirely (register the native host against a plain Python script,
reload the unpacked extension via `about:debugging`). `backend/server.py`
is a separate, plain HTTP version of the same download/convert logic
(sharing `backend/core.py` with the native host), kept around as a faster
curl-testable loop while developing; it's not part of the installed
extension's runtime path.
