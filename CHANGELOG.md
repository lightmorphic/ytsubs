# Changelog

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
