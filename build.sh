#!/bin/bash
# Rebuilds build/ytsubs-x86_64.AppImage from app.py + ui/.
#
# Requires: python3, pip (python3 -m ensurepip), and either a cached
# electron-builder AppImage runtime (any runtime-x64 + mksquashfs under
# ~/.cache/electron-builder) or `appimagetool` + `mksquashfs` on PATH.
#
# The runtime must be a FUSE-free static build. Older cached runtimes dlopen
# libfuse.so.2, which no longer exists on Ubuntu 23.04+, current Fedora,
# openSUSE or the immutable spins -- the AppImage builds fine and then refuses
# to start. We reject any runtime that mentions libfuse.so.2 rather than
# shipping one of those again.
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

# A build venv is preferred, but some hosts ship a python3 without ensurepip
# (openSUSE among them), so fall back to any pip we can actually reach --
# including build/venv, kept from an earlier build for exactly this reason.
PIP=""
if python3 -m venv --clear /tmp/ytsubs-build-venv >/dev/null 2>&1; then
  PIP="/tmp/ytsubs-build-venv/bin/python -m pip"
elif [ -x build/venv/bin/python ]; then
  # Invoked as `python -m pip`: the venv's pip script has a stale shebang from
  # when this repo lived at a different path.
  PIP="build/venv/bin/python -m pip"
elif command -v pip3 >/dev/null; then
  PIP="pip3"
fi
if [ -z "$PIP" ]; then
  echo "No usable pip. Install your distro's python3-pip (zypper in python3-pip / apt install python3-venv) and retry."
  exit 1
fi
echo "Using pip: $PIP"
$PIP install --quiet --upgrade --target "$APPDIR/usr/lib/pyapp" --no-compile pywebview yt-dlp pip requests
rm -rf /tmp/ytsubs-build-venv

ln -sf ytsubs.png "$APPDIR/.DirIcon"

MKSQ="$(command -v mksquashfs || true)"
if [ -z "$MKSQ" ]; then
  MKSQ="$(find "$HOME/.cache/electron-builder" \
    \( -path '*/linux-x64/mksquashfs' -o -path '*/linux/x64/mksquashfs' \) \
    -type f 2>/dev/null | head -n 1)"
fi

# Pick the first cached runtime-x64 with no libfuse.so.2 reference.
RUNTIME=""
while IFS= read -r r; do
  [ -n "$r" ] || continue
  # grep the binary directly: piping strings into `grep -q` returns SIGPIPE
  # under `set -o pipefail`, which reads as "clean" and let a FUSE2 runtime through.
  if LC_ALL=C grep -qa 'libfuse\.so\.2' "$r"; then
    echo "Skipping FUSE2 runtime: $r"
    continue
  fi
  RUNTIME="$r"
  break
done <<EOF
$(find "$HOME/.cache/electron-builder" -name 'runtime-x64' -type f 2>/dev/null | sort -r)
EOF
[ -n "$RUNTIME" ] && echo "Using FUSE-free runtime: $RUNTIME"

if [ -z "$MKSQ" ] || [ -z "$RUNTIME" ]; then
  echo "Falling back to appimagetool on PATH…"
  echo "WARNING: verify the result actually launches — appimagetool may embed a FUSE2 runtime."
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
