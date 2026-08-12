# YT Subs

A tiny Linux desktop app: paste a YouTube URL, pick a subtitle language
(English listed first), pick a format, download just the subtitle file.
It never downloads the video itself. `skip_download` is hardcoded on in
`app.py`.

Ships as a single AppImage, no install, no Docker, no VPS.

## Features

- Formats: SRT, VTT, TXT (plain transcript, timestamps stripped), or Raw
  (whatever YouTube served, unconverted)
- Light and dark theme, follows the desktop setting by default with a
  manual toggle in the header
- Right-click paste on the URL field (pywebview hides the browser's own
  context menu, so this is a small custom one backed by the GTK
  clipboard)
- Checks for its own updates against this repo's GitHub releases: a
  green/yellow/red dot next to the version number, checked on launch,
  every 30 minutes, and on click. When a newer release is out, an Update
  button downloads it in place and swaps to a Restart button
- Checks yt-dlp's own version against PyPI the same way, since YouTube
  changes often enough that an old yt-dlp starts failing to fetch
  subtitles

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

The yt-dlp badge in the header shows:

- **green**: up to date
- **amber**, with an **Update** button: a newer yt-dlp is out, click it
  to install the update (via pip, into `~/.local/share/ytsubs/pylibs`,
  which takes priority over the version frozen into the AppImage), then
  restart the app
- **grey**: couldn't reach PyPI to check

## Keeping the app itself current

`ytsubs` is a private repo, so the update check needs a credential to
read its releases. It looks for a repo-scoped GitHub token at
`~/.ssh/ytsubs-token` and uses it as a bearer token. Without that file
present, the version dot shows red ("can't reach GitHub") rather than
failing loudly, since most people running this build won't have that
token and shouldn't need one for the app to otherwise work.

## Rebuilding the AppImage

```
./build.sh
```

Regenerates `build/ytsubs-x86_64.AppImage` from `app.py` and `ui/`.
Source for the AppImage wrapper (AppRun script, .desktop file, icon)
lives in `packaging/`.

The build needs `mksquashfs` and an AppImage `runtime-x64` stub. If you
have `appimagetool` on PATH it'll use that instead, otherwise it looks
for a cached copy under `~/.cache/electron-builder/appimage/*/linux-x64/`
(left behind by any electron-builder AppImage build on this machine).

## Releasing a new version

Every release publishes **two** copies of the same build: a version-stamped
file for anyone grabbing a specific release off the GitHub releases page, and
a stable, unversioned filename that the in-app updater always fetches (so it
never has to guess which asset is the "real" one on a release with more than
one `.AppImage` attached).

1. Bump `APP_VERSION` in `app.py`.
2. `./build.sh`
3. Commit, tag `vX.Y.Z`, push.
4. Copy the build to a version-stamped name, then upload both:
   ```
   cp build/ytsubs-x86_64.AppImage build/ytsubs-X.Y.Z-x86_64.AppImage
   gh release create vX.Y.Z \
     build/ytsubs-x86_64.AppImage \
     build/ytsubs-X.Y.Z-x86_64.AppImage \
     --title vX.Y.Z --notes "..."
   ```
   (with `GH_TOKEN` set to a token that has write access to this repo).

## Layout

- `app.py`: pywebview window, the yt-dlp calls (list languages, download
  one subtitle track), and the self-update logic
- `ui/`: the interface (Lightmorphic style)
- `packaging/`: AppRun, .desktop file, icon
- `build.sh`: reproducible AppImage build
