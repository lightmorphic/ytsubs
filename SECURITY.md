# Security

YT Subs is a local desktop app. It has no server component and holds no user accounts or stored credentials of its own.

## What the app talks to

- `pypi.org`: checks the installed yt-dlp version, and installs updates via pip if you click Update.
- `api.github.com`: checks this repo's releases for app updates, and downloads the new AppImage if you click Update. This repo is private, so this call uses a bearer token read from `~/.ssh/ytsubs-token` if present; without it, the check just fails closed (shows a red "can't reach GitHub" status).
- YouTube, via yt-dlp: fetching subtitle tracks is the app's entire purpose. `skip_download` is always on; the video itself is never requested.

All three are plain HTTPS requests. Nothing else calls out, and the app doesn't run a network-facing server (pywebview's local HTTP server for the UI binds to `127.0.0.1` only).

## Self-update

Clicking Update overwrites the running AppImage file in place: it downloads to a temp file in the same directory, then atomically renames it over the original. If that fails partway through, the temp file is removed and the original AppImage is left untouched.

## Reporting an issue

This is a personal-use tool with a private repo. If you find a problem, open an issue on this repo or contact the maintainer directly.
