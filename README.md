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
  context menu, so this is a small custom one backed by the Qt
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

The AppImage carries everything it needs to draw its own window: Qt's
WebEngine, the Qt platform plugins, and the Python packages (pywebview,
yt-dlp, requests). Nothing is installed on the host and nothing is
asked for.

The one thing taken from the host is `python3` itself, which has to be
3.10 or newer, because the bundled Qt wheels are built against that
ABI. Every current Linux desktop ships one. If it's missing or too old,
`AppRun` says so in a dialog rather than failing silently.

That self-containment is what makes the download ~145MB instead of
~6MB. Up to v1.1.1 the app borrowed the host's GTK WebKit2 stack to
stay small, and offered a one-click install when it wasn't there --
but an AppImage that asks you to install something is the exact thing
an AppImage is supposed to avoid.

## Keeping yt-dlp current

The yt-dlp badge in the header shows:

- **green**: up to date
- **amber**, with an **Update** button: a newer yt-dlp is out, click it
  to install the update (via pip, into `~/.local/share/ytsubs/pylibs`,
  which takes priority over the version frozen into the AppImage), then
  restart the app
- **grey**: couldn't reach PyPI to check

## Keeping the app itself current

`ytsubs` is a public repo, so the update check works with no credential
at all. If a repo-scoped GitHub token happens to be sitting at
`9-Claude/Tokens/ytsubs-token` in the maintainer's home directory, it's
used as a bearer token to avoid the low unauthenticated GitHub API rate
limit; on anyone else's machine that path just won't exist, and the
check runs unauthenticated instead.

## Rebuilding the AppImage

```
./build.sh
```

Regenerates `build/ytsubs-x86_64.AppImage` from `app.py` and `ui/`.
Source for the AppImage wrapper (AppRun script, .desktop file, icon)
lives in `packaging/`.

The build needs `mksquashfs` and an AppImage `runtime-x64` stub. It
searches anywhere under `~/.cache/electron-builder/` for both (left
behind by any electron-builder AppImage build on this machine), and
falls back to `appimagetool` on PATH if it can't find them.

`build.sh` also runs `packaging/prune-qt.py`, which walks the bundled
Qt libraries' `DT_NEEDED` entries from the modules pywebview actually
imports and deletes everything unreachable -- about 240MB of Qt the app
never loads. The image is compressed with zstd, not xz: the FUSE-free
runtime's squashfuse only understands zlib and zstd, so an xz image
builds fine and then mounts nowhere.

The runtime stub has to be a FUSE-free static build. Older cached
runtimes `dlopen` `libfuse.so.2`, which Ubuntu 23.04+, current Fedora,
openSUSE and the immutable spins no longer ship -- the AppImage builds
without complaint and then refuses to start, which to a user reads as
"I double-clicked it and nothing happened". `build.sh` rejects any
runtime that mentions `libfuse.so.2` and prints the one it picked.

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

Between steps 2 and 3, **launch the built AppImage and check the window
actually opens.** A successful build proves nothing about whether it
runs -- that's how the broken v1.1.0 release went out.

## Layout

- `app.py`: pywebview window, the yt-dlp calls (list languages, download
  one subtitle track), and the self-update logic
- `ui/`: the interface (Lightmorphic style)
- `packaging/`: AppRun, .desktop file, icon
- `build.sh`: reproducible AppImage build
