let selectedLang = null;
let selectedFormat = "srt";
let saveDir = null;

const el = (id) => document.getElementById(id);

const FORMAT_HINTS = {
  srt: "Standard subtitle file with timestamps.",
  vtt: "WebVTT subtitle file with timestamps.",
  txt: "Plain text transcript, no timestamps or formatting.",
  raw: "Whatever format YouTube served, unconverted (usually VTT).",
};

function showStatus(kind, msg) {
  const s = el("status");
  s.className = `status show ${kind}`;
  s.textContent = msg;
}
function clearStatus() {
  const s = el("status");
  s.className = "status";
  s.textContent = "";
}

function langLabel(code) {
  try {
    const dn = new Intl.DisplayNames(["en"], { type: "language" });
    return dn.of(code.split("-")[0]) || code;
  } catch {
    return code;
  }
}

async function refreshYtdlpBadge() {
  const badge = el("ytdlpBadge");
  badge.className = "ytdlp-badge";
  badge.textContent = "checking yt-dlp…";
  try {
    const status = await window.pywebview.api.get_ytdlp_status();
    if (!status.latest) {
      badge.className = "ytdlp-badge";
      badge.textContent = `yt-dlp ${status.installed} (couldn't check for updates)`;
    } else if (status.upToDate) {
      badge.className = "ytdlp-badge ok";
      badge.textContent = `yt-dlp ${status.installed}, up to date`;
    } else {
      badge.className = "ytdlp-badge stale";
      badge.innerHTML = `yt-dlp ${status.installed} → ${status.latest} available <button id="ytdlpUpdateBtn" type="button">Update</button>`;
      el("ytdlpUpdateBtn").addEventListener("click", updateYtdlp);
    }
  } catch (e) {
    badge.className = "ytdlp-badge err";
    badge.textContent = "yt-dlp status unknown";
  }
}

async function updateYtdlp() {
  const badge = el("ytdlpBadge");
  badge.className = "ytdlp-badge";
  badge.textContent = "updating yt-dlp…";
  try {
    const result = await window.pywebview.api.update_ytdlp();
    if (result.ok) {
      badge.className = "ytdlp-badge ok";
      badge.textContent = "Updated, restart YT Subs to use the new version";
    } else {
      badge.className = "ytdlp-badge err";
      badge.textContent = `Update failed: ${result.error || "unknown error"}`;
    }
  } catch (e) {
    badge.className = "ytdlp-badge err";
    badge.textContent = "Update failed";
  }
}

async function fetchSubtitles() {
  const url = el("urlInput").value.trim();
  if (!url) {
    showStatus("error", "Enter a YouTube URL first.");
    return;
  }
  clearStatus();
  el("fetchBtn").disabled = true;
  el("fetchBtn").textContent = "Looking…";
  el("resultsPanel").style.display = "none";
  el("savePanel").style.display = "none";
  selectedLang = null;

  try {
    const info = await window.pywebview.api.fetch_info(url);
    if (info.error) {
      showStatus("error", info.error);
      return;
    }
    if (!info.languages.length) {
      showStatus("error", "No subtitles are available for this video yet.");
      return;
    }
    el("videoTitle").textContent = info.title || "Video";
    const list = el("langList");
    list.innerHTML = "";
    info.languages.forEach((lang) => {
      const item = document.createElement("div");
      item.className = "lang-item";
      item.tabIndex = 0;
      item.setAttribute("role", "button");
      item.innerHTML = `<span class="code">${lang.code}</span><span>${langLabel(lang.code)}</span>${lang.auto ? '<span class="tag">auto-generated</span>' : ""}`;
      item.addEventListener("click", () => selectLang(item, lang));
      item.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectLang(item, lang); }
      });
      list.appendChild(item);
    });
    el("resultsPanel").style.display = "flex";
    el("savePanel").style.display = "block";
    if (!saveDir) {
      saveDir = await window.pywebview.api.default_download_dir();
      el("folderPath").textContent = saveDir;
    }
  } catch (e) {
    showStatus("error", "Couldn't read that video. Check the URL and try again.");
  } finally {
    el("fetchBtn").disabled = false;
    el("fetchBtn").textContent = "Find subtitles";
  }
}

function selectLang(item, lang) {
  document.querySelectorAll(".lang-item.selected").forEach((n) => n.classList.remove("selected"));
  item.classList.add("selected");
  selectedLang = lang;
  el("downloadBtn").disabled = false;
}

async function chooseFolder() {
  const dir = await window.pywebview.api.choose_folder();
  if (dir) {
    saveDir = dir;
    el("folderPath").textContent = dir;
  }
}

function selectFormat(button) {
  document.querySelectorAll(".format-item.selected").forEach((n) => n.classList.remove("selected"));
  button.classList.add("selected");
  selectedFormat = button.dataset.format;
  el("formatHint").textContent = FORMAT_HINTS[selectedFormat] || "";
}

async function downloadSubtitles() {
  const url = el("urlInput").value.trim();
  if (!url || !selectedLang || !saveDir) return;
  clearStatus();
  el("downloadBtn").disabled = true;
  el("downloadBtn").textContent = "Downloading…";
  try {
    const result = await window.pywebview.api.download_subtitle(url, selectedLang.code, selectedLang.auto, saveDir, selectedFormat);
    if (result.ok) {
      showStatus("success", `Saved: ${result.path}`);
    } else {
      showStatus("error", result.error || "Download failed.");
    }
  } catch (e) {
    showStatus("error", "Download failed.");
  } finally {
    el("downloadBtn").disabled = false;
    el("downloadBtn").textContent = "Download subtitles";
  }
}

function systemPrefersDark() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(theme) {
  if (theme) {
    document.documentElement.setAttribute("data-theme", theme);
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
}

async function initTheme() {
  try {
    const saved = await window.pywebview.api.get_theme();
    applyTheme(saved);
  } catch (e) {
    // fall back to the OS preference (already handled by CSS media queries)
  }
  el("themeToggle").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || (systemPrefersDark() ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    window.pywebview.api.set_theme(next).catch(() => {});
  });
}

function initPasteMenu() {
  const menu = el("pasteMenu");
  const input = el("urlInput");

  function hideMenu() {
    menu.hidden = true;
  }

  input.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    menu.style.left = `${e.clientX}px`;
    menu.style.top = `${e.clientY}px`;
    menu.hidden = false;
  });

  el("pasteMenuBtn").addEventListener("click", async () => {
    hideMenu();
    try {
      const text = await window.pywebview.api.get_clipboard_text();
      if (text) {
        input.value = text;
        input.focus();
        input.setSelectionRange(text.length, text.length);
      }
    } catch (e) {
      // clipboard read failed silently; Ctrl+V still works as a fallback
    }
  });

  document.addEventListener("click", (e) => {
    if (!menu.hidden && e.target !== el("pasteMenuBtn")) hideMenu();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideMenu(); });
  window.addEventListener("blur", hideMenu);
}

const UPDATE_CHECK_INTERVAL_MS = 30 * 60 * 1000;
let latestUpdateInfo = null;

function setVersionDot(cls, tooltip) {
  const dot = el("versionDot");
  dot.className = `version-dot ${cls}`;
  el("appVersion").title = tooltip;
}

function setUpdateButton(label, action, disabled) {
  const btn = el("updateBtn");
  btn.classList.remove("hidden");
  btn.disabled = !!disabled;
  btn.dataset.action = action || "";
  btn.textContent = label;
}

function hideUpdateButton() {
  el("updateBtn").classList.add("hidden");
}

async function checkForAppUpdate() {
  setVersionDot("checking", "Checking for updates…");
  try {
    const result = await window.pywebview.api.check_for_app_update();
    el("versionText").textContent = `v${result.installed}`;
    if (result.status === "available") {
      latestUpdateInfo = result;
      setVersionDot("available", `Update available: v${result.latest} (click to re-check)`);
      setUpdateButton(`Update to v${result.latest}`, "download");
    } else if (result.status === "up-to-date") {
      setVersionDot("up-to-date", `You're on the latest version, v${result.installed} (click to re-check)`);
      hideUpdateButton();
    } else {
      setVersionDot("error", "Couldn't reach GitHub to check for updates (click to retry)");
      hideUpdateButton();
    }
  } catch (e) {
    setVersionDot("error", "Couldn't reach GitHub to check for updates (click to retry)");
    hideUpdateButton();
  }
}

async function pollDownloadState() {
  while (true) {
    await new Promise((r) => setTimeout(r, 500));
    let state;
    try {
      state = await window.pywebview.api.get_download_state();
    } catch (e) {
      break;
    }
    if (state.status === "downloaded") {
      setUpdateButton("Restart to finish updating", "install");
      setVersionDot("available", "Update downloaded, restart to finish installing.");
      break;
    }
    if (state.status === "error") {
      setUpdateButton(`Update to v${latestUpdateInfo.latest}`, "download");
      showStatus("error", `Update download failed: ${state.error || "unknown error"}`);
      break;
    }
  }
}

async function handleUpdateButtonClick() {
  const btn = el("updateBtn");
  const action = btn.dataset.action;
  if (action === "download" && latestUpdateInfo) {
    setUpdateButton("Downloading…", "downloading", true);
    try {
      const result = await window.pywebview.api.download_app_update(latestUpdateInfo.downloadUrl);
      if (result.ok) {
        pollDownloadState();
      } else {
        setUpdateButton(`Update to v${latestUpdateInfo.latest}`, "download");
        showStatus("error", result.error || "Couldn't start the download.");
      }
    } catch (e) {
      setUpdateButton(`Update to v${latestUpdateInfo.latest}`, "download");
    }
  } else if (action === "install") {
    btn.disabled = true;
    await window.pywebview.api.restart_app().catch(() => {});
  }
}

function initAppUpdate() {
  checkForAppUpdate();
  el("appVersion").addEventListener("click", checkForAppUpdate);
  el("updateBtn").addEventListener("click", handleUpdateButtonClick);
  setInterval(checkForAppUpdate, UPDATE_CHECK_INTERVAL_MS);
}

window.addEventListener("pywebviewready", () => {
  // Each step runs independently, one throwing must never stop the rest
  // of the UI from wiring up (a WebKit quirk like a missing browser API
  // has broken every listener registered after it here before).
  const steps = [
    initTheme,
    initPasteMenu,
    initAppUpdate,
    refreshYtdlpBadge,
    () => el("fetchBtn").addEventListener("click", fetchSubtitles),
    () => el("urlInput").addEventListener("keydown", (e) => { if (e.key === "Enter") fetchSubtitles(); }),
    () => el("chooseFolderBtn").addEventListener("click", chooseFolder),
    () => el("downloadBtn").addEventListener("click", downloadSubtitles),
    () => document.querySelectorAll(".format-item").forEach((btn) => {
      btn.addEventListener("click", () => selectFormat(btn));
    }),
  ];
  for (const step of steps) {
    try {
      step();
    } catch (e) {
      console.error("init step failed:", e);
    }
  }
});
