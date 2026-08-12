#!/bin/bash
# Rebuilds build/ytsubs-x86_64.AppImage from app.py + ui/.
#
# Requires: python3, pip (python3 -m ensurepip), and either a cached
# electron-builder AppImage runtime (~/.cache/electron-builder/appimage/*/linux-x64/mksquashfs
# and .../runtime-x64) or `appimagetool` + `mksquashfs` on PATH.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

APPDIR=build/AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/app" "$APPDIR/usr/lib/pyapp"

cp -r app.py ui "$APPDIR/usr/app/"
cp packaging/AppRun "$APPDIR/AppRun"
cp packaging/ytsubs.desktop "$APPDIR/ytsubs.desktop"
cp packaging/ytsubs.png "$APPDIR/ytsubs.png"
chmod +x "$APPDIR/AppRun"

python3 -m venv --clear /tmp/ytsubs-build-venv
source /tmp/ytsubs-build-venv/bin/activate
pip install --quiet --upgrade --target "$APPDIR/usr/lib/pyapp" --no-compile pywebview yt-dlp pip requests
deactivate
rm -rf /tmp/ytsubs-build-venv

ln -sf ytsubs.png "$APPDIR/.DirIcon"

MKSQ="$(command -v mksquashfs || true)"
RUNTIME=""
for d in "$HOME"/.cache/electron-builder/appimage/*/linux-x64; do
  [ -x "$d/mksquashfs" ] && MKSQ="$d/mksquashfs"
  [ -f "${d%linux-x64}runtime-x64" ] && RUNTIME="${d%linux-x64}runtime-x64"
done

if [ -z "$MKSQ" ] || [ -z "$RUNTIME" ]; then
  echo "Falling back to appimagetool on PATH…"
  command -v appimagetool >/dev/null || { echo "Need mksquashfs+runtime-x64 (from an electron-builder cache) or appimagetool on PATH"; exit 1; }
  ARCH=x86_64 appimagetool "$APPDIR" build/ytsubs-x86_64.AppImage
else
  rm -f build/app.squashfs build/ytsubs-x86_64.AppImage
  "$MKSQ" "$APPDIR" build/app.squashfs -root-owned -noappend -quiet
  cat "$RUNTIME" build/app.squashfs > build/ytsubs-x86_64.AppImage
  rm -f build/app.squashfs
fi

chmod +x build/ytsubs-x86_64.AppImage
echo "Built build/ytsubs-x86_64.AppImage"
