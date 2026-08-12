# YT Subs

A tiny Linux desktop app: paste a YouTube URL, pick a subtitle language
(English listed first), download just the subtitle file. It never
downloads the video itself — `skip_download` is hardcoded on in `app.py`.

Ships as a single AppImage, no install, no Docker, no VPS.

## Run it

```
chmod +x ytsubs-x86_64.AppImage
./ytsubs-x86_64.AppImage
```

### System requirements

The AppImage bundles its Python dependencies (pywebview, yt-dlp, pip,
requests) but uses the **host's** `python3` and GTK WebKit stack to draw
the window, since those can't be sanely bundled. Needs:

- `python3` (3.9+)
- `python3-gi`, `gir1.2-webkit2-4.1`, `libwebkit2gtk-4.1-0`

These are already present on most GNOME-based desktops. On Debian/Ubuntu:

```
sudo apt install python3-gi gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0
```

## Keeping yt-dlp current

YouTube changes often enough that yt-dlp needs frequent updates or
subtitle fetching starts failing. The app checks its installed version
against PyPI on every launch and shows a badge:

- **green** — up to date
- **amber**, with an **Update** button — a newer yt-dlp is out; click it
  to install the update (via pip, into `~/.local/share/ytsubs/pylibs`,
  which take priority over the version frozen into the AppImage), then
  restart the app
- **grey** — couldn't reach PyPI to check

## Rebuilding the AppImage

```
./build.sh
```

Regenerates `build/ytsubs-x86_64.AppImage` from `app.py` and `ui/`.
Source for the AppImage wrapper (AppRun script, .desktop file, icon)
lives in `packaging/`.

The build needs `mksquashfs` + an AppImage `runtime-x64` stub. If you
have `appimagetool` on PATH it'll use that instead; otherwise it looks
for a cached copy under `~/.cache/electron-builder/appimage/*/linux-x64/`
(left behind by any electron-builder AppImage build on this machine).

## Layout

- `app.py` — pywebview window + the yt-dlp calls (list languages,
  download one subtitle track)
- `ui/` — the interface (Lightmorphic style)
- `packaging/` — AppRun, .desktop file, icon
- `build.sh` — reproducible AppImage build
