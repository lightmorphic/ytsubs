# Changelog

## v1.2.0

- The AppImage now draws its own window. It bundles Qt's WebEngine
  instead of borrowing the host's GTK WebKit2 stack, so it no longer
  asks to install anything on first run -- which is the whole point of
  an AppImage. The download goes from ~6MB to ~145MB; the app itself is
  unchanged.
- The only remaining host requirement is `python3` 3.10 or newer, which
  every current Linux desktop ships. If it's missing or too old, that's
  now said in a dialog rather than failing quietly.
- Right-click paste reads the Qt clipboard, falling back to GTK when
  running outside the AppImage.

## v1.1.1

- Fix the AppImage refusing to start on modern Linux. The build was
  embedding an old AppImage runtime that needs FUSE 2, which Ubuntu
  23.04+, current Fedora, openSUSE and the immutable spins no longer
  ship -- so double-clicking the app did nothing at all. It now uses a
  FUSE-free static runtime, and the build refuses to pick a FUSE 2 one
  even if an old copy is lying around in the cache.
- The build also copes with hosts whose python3 has no `ensurepip`.

## v1.1.0

- Replace the separate version badge and Update button with Charlie's
  unified update-status widget: the app name and version are now one
  link out to ytsubs.lightmorphic.co.uk, immediately followed by a
  single dot that is the entire update UI. Green means up to date,
  yellow with a download icon means an update is available (click to
  fetch it), a hollow ring traces download progress, green with a
  restart icon means it's ready (click to restart), red means the
  update check couldn't reach GitHub.

## v1.0.3

- Move the maintainer's optional GitHub token path from `~/.ssh/ytsubs-token`
  to `9-Claude/Tokens/ytsubs-token`. No effect for anyone else; the repo
  is public and the update check already works with no token at all.

## v1.0.2

- AppRun now checks for GTK's WebKit2 bindings before opening the window.
  If missing, it offers a one-click install via a native dialog
  (zenity, kdialog, or xmessage) instead of just failing with a
  message telling you to run a command yourself.

## v1.0.1

- Fix a duplicate-id bug where the yt-dlp update button and the app
  update button could interfere with each other.
- Bump the bundled pip (used by the yt-dlp self-updater) to close 6
  known CVEs that were in the version the build had been silently
  pinning to.
- Copy and documentation cleanup, no other behaviour changes.

## v1.0.0

- YouTube subtitle download in SRT, VTT, TXT (plain transcript), or Raw format. The video itself is never fetched.
- Language list sorted with English first, manual and auto-generated tracks both shown.
- Light and dark theme, follows the desktop setting by default with a manual toggle.
- Right-click paste on the URL field, since pywebview hides the browser's own context menu.
- Two-column layout: URL and language list on the left, format and save options on the right, nothing needs scrolling to reach.
- yt-dlp version check against PyPI with a one-click update, since YouTube changes often enough that an old yt-dlp stops working.
- App self-update: checks this repo's GitHub releases on launch, every 30 minutes, and on click. Downloads and installs in place, then prompts a restart.
