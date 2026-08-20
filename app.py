import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

import webview

APP_VERSION = "1.2.0"
UPDATE_REPO = "lightmorphic/ytsubs"
RELEASES_API = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"
# Every release publishes two assets: this stable name (what the updater
# always fetches) and a version-stamped copy (for anyone grabbing a specific
# release directly off the GitHub releases page).
UPDATE_ASSET_NAME = "ytsubs-x86_64.AppImage"

APP_DIR = Path.home() / ".local" / "share" / "ytsubs"
LIB_DIR = APP_DIR / "pylibs"
LIB_DIR.mkdir(parents=True, exist_ok=True)
PREFS_FILE = APP_DIR / "prefs.json"

# A user-writable copy of yt-dlp, if one has been installed by the in-app
# updater, takes priority over the version frozen into the AppImage.
sys.path.insert(0, str(LIB_DIR))

import yt_dlp  # noqa: E402
from yt_dlp.version import __version__ as YTDLP_VERSION  # noqa: E402


def base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def version_tuple(v):
    return tuple(int(part) for part in v.split(".") if part.isdigit())


# "raw" means: don't ask yt-dlp to convert, keep whatever format YouTube
# actually served (usually vtt, sometimes ttml/srv1/srv3/json3). "txt" is
# not a real yt-dlp subtitle format, so it's produced by downloading vtt
# and stripping it down ourselves.
YTDLP_SUB_FORMAT = {"srt": "srt", "vtt": "vtt", "raw": "best", "txt": "vtt"}

_TIMESTAMP_RE = re.compile(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->")
_INDEX_RE = re.compile(r"^\d+$")
_TAG_RE = re.compile(r"<[^>]+>")
_META_PREFIXES = ("WEBVTT", "NOTE", "STYLE", "KIND:", "LANGUAGE:", "REGION:")


def subtitle_file_to_text(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        raw_lines = f.read().splitlines()

    lines = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith(_META_PREFIXES):
            continue
        if _TIMESTAMP_RE.search(line):
            continue
        if _INDEX_RE.match(line):
            continue
        line = _TAG_RE.sub("", line).strip()
        if line:
            lines.append(line)

    deduped = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped) + "\n"


def _is_newer(candidate, current):
    def parts(v):
        out = []
        for piece in v.strip().lstrip("v").replace("-", ".").split(".")[:3]:
            try:
                out.append(int(piece))
            except ValueError:
                out.append(0)
        return out

    a, b = parts(candidate), parts(current)
    length = max(len(a), len(b))
    a += [0] * (length - len(a))
    b += [0] * (length - len(b))
    return a > b


_download_state = {"status": "idle", "error": None, "progress": 0.0}

# The repo is public, so this token isn't required for the update check
# to work, it just avoids the low, unauthenticated GitHub API rate limit.
# Only ever found on the maintainer's own machine; everyone else's update
# check runs unauthenticated, which works fine against a public repo.
GITHUB_TOKEN_FILE = Path.home() / "9-Claude" / "Tokens" / "ytsubs-token"


def _github_token():
    try:
        return GITHUB_TOKEN_FILE.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


class Api:
    def check_for_app_update(self):
        try:
            headers = {"Accept": "application/vnd.github+json"}
            token = _github_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(RELEASES_API, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                release = json.load(resp)
            latest = (release.get("tag_name") or "").lstrip("v")
            if not latest:
                return {"status": "error", "installed": APP_VERSION}
            asset = next(
                (a for a in release.get("assets", []) if a.get("name") == UPDATE_ASSET_NAME),
                None,
            )
            if _is_newer(latest, APP_VERSION) and asset:
                return {
                    "status": "available",
                    "installed": APP_VERSION,
                    "latest": latest,
                    # The API asset URL works with or without a token, and
                    # with a token still works if this repo ever goes
                    # private again. browser_download_url wouldn't.
                    "downloadUrl": asset["url"],
                }
            return {"status": "up-to-date", "installed": APP_VERSION, "latest": latest}
        except Exception:
            return {"status": "error", "installed": APP_VERSION}

    def download_app_update(self, url):
        appimage_path = os.environ.get("APPIMAGE")
        if not appimage_path:
            return {"ok": False, "error": "Only the packaged AppImage can update itself."}

        def worker():
            _download_state["status"] = "downloading"
            _download_state["error"] = None
            _download_state["progress"] = 0.0
            try:
                target_dir = os.path.dirname(appimage_path)
                fd, tmp_path = tempfile.mkstemp(dir=target_dir, prefix=".ytsubs-update-")
                try:
                    headers = {"Accept": "application/octet-stream"}
                    token = _github_token()
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=30) as resp, os.fdopen(fd, "wb") as out:
                        total = int(resp.headers.get("Content-Length") or 0)
                        done = 0
                        while True:
                            chunk = resp.read(1024 * 256)
                            if not chunk:
                                break
                            out.write(chunk)
                            done += len(chunk)
                            if total:
                                _download_state["progress"] = done / total
                    os.chmod(tmp_path, 0o755)
                    os.replace(tmp_path, appimage_path)
                except Exception:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise
                _download_state["progress"] = 1.0
                _download_state["status"] = "downloaded"
            except Exception as e:
                _download_state["status"] = "error"
                _download_state["error"] = str(e)

        _download_state["status"] = "downloading"
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True}

    def get_download_state(self):
        return dict(_download_state)

    def restart_app(self):
        appimage_path = os.environ.get("APPIMAGE")
        if not appimage_path:
            return {"ok": False, "error": "Only the packaged AppImage can restart itself."}
        subprocess.Popen([appimage_path], start_new_session=True, close_fds=True)
        threading.Timer(0.3, lambda: os._exit(0)).start()
        return {"ok": True}

    def get_ytdlp_status(self):
        try:
            with urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=6) as r:
                data = json.load(r)
            latest = data["info"]["version"]
        except Exception:
            latest = None
        up_to_date = latest is None or version_tuple(latest) <= version_tuple(YTDLP_VERSION)
        return {
            "installed": YTDLP_VERSION,
            "latest": latest,
            "upToDate": up_to_date,
        }

    def update_ytdlp(self):
        try:
            from pip._internal.cli.main import main as pip_main

            code = pip_main(
                [
                    "install",
                    "--upgrade",
                    "--target",
                    str(LIB_DIR),
                    "--no-warn-script-location",
                    "yt-dlp",
                ]
            )
            return {"ok": code == 0}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def fetch_info(self, url):
        try:
            ydl_opts = {"skip_download": True, "quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            return {"error": f"Couldn't read that video: {e}"}

        subs = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}

        languages = [{"code": code, "auto": False} for code in subs]
        languages += [{"code": code, "auto": True} for code in auto if code not in subs]

        def sort_key(lang):
            return (0 if lang["code"].startswith("en") else 1, lang["code"])

        languages.sort(key=sort_key)

        return {"title": info.get("title"), "languages": languages}

    def download_subtitle(self, url, lang, auto, save_dir, fmt="srt"):
        try:
            fmt = fmt if fmt in YTDLP_SUB_FORMAT else "srt"
            outtmpl = os.path.join(save_dir, "%(title)s.%(ext)s")
            ydl_opts = {
                # Never fetch the video itself, only the subtitle track.
                "skip_download": True,
                "writesubtitles": not auto,
                "writeautomaticsub": bool(auto),
                "subtitleslangs": [lang],
                "subtitlesformat": YTDLP_SUB_FORMAT[fmt],
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            requested = (info.get("requested_subtitles") or {}).get(lang)
            if not requested or not requested.get("filepath"):
                return {"ok": False, "error": "yt-dlp didn't report where the subtitle file was saved."}
            path = requested["filepath"]

            if fmt == "txt":
                text_path = os.path.splitext(path)[0] + ".txt"
                text = subtitle_file_to_text(path)
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(text)
                if os.path.exists(path):
                    os.remove(path)
                path = text_path

            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def choose_folder(self):
        window = webview.windows[0]
        result = window.create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def default_download_dir(self):
        d = Path.home() / "Downloads"
        return str(d if d.exists() else Path.home())

    def get_theme(self):
        # WebKitGTK doesn't expose localStorage for file:// pages, so the
        # theme choice is persisted here instead of in browser storage.
        try:
            with open(PREFS_FILE, encoding="utf-8") as f:
                return json.load(f).get("theme")
        except Exception:
            return None

    def set_theme(self, theme):
        try:
            with open(PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump({"theme": theme}, f)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_clipboard_text(self):
        # pywebview suppresses the browser's own right-click menu (so it can't
        # leak "Inspect Element"), which also takes native right-click paste
        # with it. The UI draws its own paste menu and calls this instead,
        # reading the OS clipboard directly from the toolkit.
        try:
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                # This runs on a js_api thread, and Qt's clipboard may only be
                # touched from the thread that owns the application object.
                # Passing `app` as the timer's context runs the read there.
                done = threading.Event()
                text = []

                def read():
                    text.append(QApplication.clipboard().text() or "")
                    done.set()

                QTimer.singleShot(0, app, read)
                done.wait(2)
                return text[0] if text else ""
        except Exception:
            pass
        try:
            from gi.repository import Gdk, Gtk

            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            return clipboard.wait_for_text() or ""
        except Exception:
            return ""


def main():
    api = Api()
    ui_dir = base_dir() / "ui"
    webview.create_window(
        "YT Subs",
        str(ui_dir / "index.html"),
        js_api=api,
        width=880,
        height=600,
        min_size=(720, 480),
    )
    # The AppImage carries its own Qt WebEngine, so nothing has to be
    # installed on the host to draw the window. Outside the AppImage, fall
    # back to whatever pywebview can find.
    try:
        import PySide6.QtWebEngineWidgets  # noqa: F401

        webview.start(gui="qt")
    except ImportError:
        webview.start()


if __name__ == "__main__":
    main()
