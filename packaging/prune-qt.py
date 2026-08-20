#!/usr/bin/env python3
"""Strip the PySide6 install down to what a pywebview Qt window actually loads.

The wheels are 650MB unpacked; almost all of it is Qt modules this app never
touches. We keep a whitelist of Python extension modules, then follow each
one's DT_NEEDED entries to work out which Qt shared libraries are genuinely
reachable, and delete the rest.
"""
import os
import re
import subprocess
import sys

ROOT = sys.argv[1]
PS = os.path.join(ROOT, "PySide6")
QT = os.path.join(PS, "Qt")

# Python-visible modules pywebview's qt backend imports, plus what
# QtWebEngineWidgets pulls in behind the scenes (it renders through Qt Quick).
KEEP_MODULES = {
    "QtCore", "QtGui", "QtWidgets", "QtNetwork", "QtDBus", "QtPrintSupport",
    "QtWebEngineCore", "QtWebEngineWidgets", "QtWebChannel",
    "QtQml", "QtQuick", "QtQuickWidgets", "QtOpenGL", "QtOpenGLWidgets",
    "QtPositioning", "QtSvg",
}
KEEP_PLUGIN_DIRS = {
    "platforms", "platformthemes", "platforminputcontexts", "xcbglintegrations",
    "egldeviceintegrations", "imageformats", "iconengines", "tls", "generic",
    "wayland-decoration-client", "wayland-graphics-integration-client",
    "wayland-shell-integration",
}
KEEP_QML_DIRS = {"QtCore", "QtQml", "QtQuick", "QtWebChannel", "QtWebEngine"}


def needed(path):
    try:
        out = subprocess.run(["readelf", "-d", path], capture_output=True,
                             text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError):
        return []
    return re.findall(r"\(NEEDED\).*?\[(.+?)\]", out)


def elf_files(*dirs):
    for d in dirs:
        for base, _, files in os.walk(d):
            for f in files:
                p = os.path.join(base, f)
                if f.endswith(".so") or ".so." in f or os.access(p, os.X_OK):
                    yield p


libdir = os.path.join(QT, "lib")
roots = [os.path.join(PS, m + ".abi3.so") for m in KEEP_MODULES]
roots = [r for r in roots if os.path.exists(r)]
roots += [os.path.join(PS, f) for f in os.listdir(PS)
          if f.startswith("libpyside") or f.startswith("libshiboken")]
roots += [os.path.join(QT, "libexec", "QtWebEngineProcess")]
for d in KEEP_PLUGIN_DIRS:
    p = os.path.join(QT, "plugins", d)
    if os.path.isdir(p):
        roots += list(elf_files(p))
for d in KEEP_QML_DIRS:
    p = os.path.join(QT, "qml", d)
    if os.path.isdir(p):
        roots += list(elf_files(p))
roots += [os.path.join(ROOT, "shiboken6", f) for f in
          (os.listdir(os.path.join(ROOT, "shiboken6")) if
           os.path.isdir(os.path.join(ROOT, "shiboken6")) else [])]

# Walk the DT_NEEDED graph from those roots through Qt's own lib directory.
reachable, queue = set(), [r for r in roots if os.path.exists(r)]
while queue:
    cur = queue.pop()
    for name in needed(cur):
        target = os.path.join(libdir, name)
        if os.path.exists(target) and target not in reachable:
            reachable.add(target)
            queue.append(target)

freed = 0


def drop(path):
    global freed
    if os.path.islink(path):
        os.unlink(path)
        return
    if os.path.isdir(path):
        for base, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(base, f)
                if not os.path.islink(fp):
                    freed += os.path.getsize(fp)
        subprocess.run(["rm", "-rf", path], check=True)
        return
    freed += os.path.getsize(path)
    os.unlink(path)


# Unused Python extension modules.
for f in os.listdir(PS):
    if f.endswith(".abi3.so") and f[:-8] not in KEEP_MODULES:
        drop(os.path.join(PS, f))
    elif f.endswith(".pyi") or f == "support":
        drop(os.path.join(PS, f))

# Unreachable Qt libraries. Symlinks are resolved so an unused .so chain goes
# entirely, while a kept library keeps its soname links.
for f in sorted(os.listdir(libdir)):
    p = os.path.join(libdir, f)
    real = os.path.realpath(p)
    if real not in reachable and p not in reachable:
        drop(p)

for d in (os.listdir(os.path.join(QT, "plugins")) if os.path.isdir(os.path.join(QT, "plugins")) else []):
    if d not in KEEP_PLUGIN_DIRS:
        drop(os.path.join(QT, "plugins", d))

for d in (os.listdir(os.path.join(QT, "qml")) if os.path.isdir(os.path.join(QT, "qml")) else []):
    if d not in KEEP_QML_DIRS:
        drop(os.path.join(QT, "qml", d))

# Build-time and developer-only payload.
for p in ("metatypes", "typesystems", "include", "glue", "lib/cmake"):
    fp = os.path.join(QT if p != "lib/cmake" else QT, p)
    if os.path.exists(fp):
        drop(fp)

# Translations: keep English only. Chromium's devtools front-end is ~11MB of
# browser developer tools nobody opens in a subtitle downloader.
tr = os.path.join(QT, "translations")
if os.path.isdir(tr):
    for f in os.listdir(tr):
        p = os.path.join(tr, f)
        if f == "qtwebengine_locales":
            for loc in os.listdir(p):
                if loc != "en-US.pak":
                    drop(os.path.join(p, loc))
        elif not f.endswith("_en.qm"):
            drop(p)
devtools = os.path.join(QT, "resources", "qtwebengine_devtools_resources.pak")
if os.path.exists(devtools):
    drop(devtools)

print(f"Pruned {freed / 1048576:.0f}MB from the Qt bundle")
