(() => {
  const BACKEND_BASE = "http://172.20.10.3:8000";

  // Validation constants
  const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB
  const ALLOWED_MIME_TYPES = [
    "text/plain", "application/pdf", "image/png", "image/jpeg",
    "application/zip", "application/octet-stream",
  ];

  const $ = (sel) => document.querySelector(sel);

  const backendUrlLabel = $("#backendUrlLabel");
  const btnPing = $("#btnPing");

  const dropzone = $("#dropzone");
  const fileInput = $("#fileInput");
  const btnClear = $("#btnClear");
  const btnUpload = $("#btnUpload");
  const selectedList = $("#selectedList");

  const maxSizeLabel = $("#maxSizeLabel");
  const typesLabel = $("#typesLabel");

  const btnRefreshFiles = $("#btnRefreshFiles");
  const filesList = $("#filesList");

  const toastsEl = $("#toasts");

  backendUrlLabel.textContent = BACKEND_BASE;
  maxSizeLabel.textContent = formatBytes(MAX_FILE_SIZE_BYTES);
  typesLabel.textContent = "common types + .zip + binary";

  let selected = [];
  let lastFiles = [];

  // ---------- Toasts ----------
  function toast(type, text, ttlMs = 2600) {
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `
      <div class="msg">${escapeHtml(text)}</div>
      <button class="x" title="Dismiss">×</button>
    `;
    el.querySelector(".x").addEventListener("click", () => el.remove());
    toastsEl.prepend(el);
    if (ttlMs > 0) setTimeout(() => el.remove(), ttlMs);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  async function pingBackend() {
    try {
      const res = await fetch(`${BACKEND_BASE}/files`, { method: "GET" });
      if (!res.ok) return toast("error", `Backend reachable but returned ${res.status} on GET /files`);
      const data = await res.json();
      toast("ok", `Backend OK. ${Array.isArray(data) ? data.length : "?"} file(s) listed.`);
    } catch (err) {
      toast("error", `Cannot reach backend at ${BACKEND_BASE}. ${err}`);
    }
  }

  // ---------- Upload selection ----------
  function validateFile(file) {
    const errors = [];
    if (file.size > MAX_FILE_SIZE_BYTES) errors.push(`Too large: ${formatBytes(file.size)} (max ${formatBytes(MAX_FILE_SIZE_BYTES)})`);
    if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) errors.push(`Type not allowed: ${file.type}`);
    return errors;
  }

  function addFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    const additions = files.map((file) => {
      const errors = validateFile(file);
      return {
        id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()),
        file, ok: errors.length === 0, errors,
        state: "queued", progress: 0,
        result: null, errorText: "", xhr: null,
      };
    });

    selected = selected.concat(additions);
    renderSelected();
    updateUploadButton();

    const okCount = additions.filter(x => x.ok).length;
    const badCount = additions.length - okCount;
    if (okCount) toast("ok", `Selected ${okCount} file(s) ready.`);
    if (badCount) toast("error", `${badCount} file(s) invalid (see list).`);
  }

  function updateUploadButton() {
    btnUpload.disabled = !selected.some(x => x.ok && ["queued","failed","canceled"].includes(x.state));
  }

  function clearSelected() {
    for (const item of selected) if (item.state === "uploading" && item.xhr) try { item.xhr.abort(); } catch {}
    selected = [];
    renderSelected();
    fileInput.value = "";
    toast("ok", "Selection cleared.");
    updateUploadButton();
  }

  function removeOne(id) {
    const item = selected.find(x => x.id === id);
    if (item && item.state === "uploading" && item.xhr) try { item.xhr.abort(); } catch {}
    selected = selected.filter(x => x.id !== id);
    renderSelected();
    updateUploadButton();
  }

  function stateBadge(item) {
    if (!item.ok) return `<span class="badge error">⚠ Invalid</span>`;
    if (item.state === "queued") return `<span class="badge info">⏳ Queued</span>`;
    if (item.state === "uploading") return `<span class="badge info">⬆ Uploading</span>`;
    if (item.state === "success") return `<span class="badge ok">✓ Uploaded</span>`;
    if (item.state === "failed") return `<span class="badge error">✕ Failed</span>`;
    if (item.state === "canceled") return `<span class="badge error">⦸ Canceled</span>`;
    return `<span class="badge info">${escapeHtml(item.state)}</span>`;
  }

  function renderSelected() {
    selectedList.innerHTML = "";
    if (!selected.length) {
      selectedList.innerHTML = `<div class="placeholder">No files selected yet.</div>`;
      return;
    }

    for (const item of selected) {
      const el = document.createElement("div");
      el.className = "item";

      const errors = item.errors.map(e => `<div class="submeta">• ${escapeHtml(e)}</div>`).join("");
      const serverLine = item.result ? `<div class="submeta">Server id: <code>${escapeHtml(item.result.id)}</code></div>` : "";
      const failLine = item.errorText ? `<div class="submeta">Error: ${escapeHtml(item.errorText)}</div>` : "";

      const showProgress = item.ok && (item.state === "uploading" || item.state === "success");
      const progressHtml = showProgress ? `
        <div class="progressline">
          <div class="progress"><div style="width:${item.progress}%"></div></div>
          <div class="pct">${item.progress}%</div>
        </div>` : "";

      const canCancel = item.state === "uploading";
      const canRetry = item.ok && (item.state === "failed" || item.state === "canceled");
      const canUploadNow = item.ok && item.state === "queued";

      el.innerHTML = `
        <div class="meta">
          <div class="name" title="${escapeHtml(item.file.name)}">${escapeHtml(item.file.name)}</div>
          <div class="submeta">${formatBytes(item.file.size)} ${item.file.type ? "· " + escapeHtml(item.file.type) : ""}</div>
          ${progressHtml}
          ${serverLine}
          ${failLine}
          ${!item.ok ? `<div style="margin-top:6px">${errors}</div>` : ""}
        </div>
        <div class="actions">
          ${stateBadge(item)}
          <button class="btn btn-danger btn-small" data-remove="${item.id}">Remove</button>
          ${canUploadNow ? `<button class="btn btn-small" data-uploadone="${item.id}">Upload</button>` : ""}
          ${canCancel ? `<button class="btn btn-danger btn-small" data-cancel="${item.id}">Cancel</button>` : ""}
          ${canRetry ? `<button class="btn btn-small" data-retry="${item.id}">Retry</button>` : ""}
        </div>
      `;
      selectedList.appendChild(el);
    }

    selectedList.querySelectorAll("[data-remove]").forEach(b => b.addEventListener("click", () => removeOne(b.dataset.remove)));
    selectedList.querySelectorAll("[data-cancel]").forEach(b => b.addEventListener("click", () => cancelUpload(b.dataset.cancel)));
    selectedList.querySelectorAll("[data-retry]").forEach(b => b.addEventListener("click", () => retryUpload(b.dataset.retry)));
    selectedList.querySelectorAll("[data-uploadone]").forEach(b => b.addEventListener("click", () => startUploadOne(b.dataset.uploadone)));
  }

  function startUploadAllValid() {
    const ids = selected.filter(x => x.ok && ["queued","failed","canceled"].includes(x.state)).map(x => x.id);
    if (!ids.length) return toast("error", "No valid queued files to upload.");
    uploadSequential(ids);
  }

  async function uploadSequential(ids) {
    for (const id of ids) {
      const item = selected.find(x => x.id === id);
      if (!item) continue;
      if (!["queued","failed","canceled"].includes(item.state)) continue;
      // eslint-disable-next-line no-await-in-loop
      await uploadOne(item);
      renderSelected(); updateUploadButton();
    }
  }

  function startUploadOne(id) {
    const item = selected.find(x => x.id === id);
    if (!item || !item.ok || item.state !== "queued") return;
    uploadOne(item).then(() => { renderSelected(); updateUploadButton(); });
  }

  function retryUpload(id) {
    const item = selected.find(x => x.id === id);
    if (!item || !item.ok || !["failed","canceled"].includes(item.state)) return;
    item.state = "queued"; item.progress = 0; item.errorText = ""; item.result = null;
    renderSelected(); updateUploadButton();
    startUploadOne(id);
  }

  function cancelUpload(id) {
    const item = selected.find(x => x.id === id);
    if (!item || item.state !== "uploading" || !item.xhr) return;
    try { item.xhr.abort(); } catch {}
    item.state = "canceled"; item.errorText = "Canceled by user";
    renderSelected(); updateUploadButton();
  }

  function uploadOne(item) {
    return new Promise((resolve) => {
      item.state = "uploading"; item.progress = 0; item.errorText = ""; item.result = null;
      const xhr = new XMLHttpRequest();
      item.xhr = xhr;
      xhr.open("POST", `${BACKEND_BASE}/files`);

      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable) {
          item.progress = Math.max(0, Math.min(100, Math.round((evt.loaded / evt.total) * 100)));
          renderSelected();
        }
      };

      xhr.onload = () => {
        item.xhr = null;
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            item.result = JSON.parse(xhr.responseText);
            item.state = "success"; item.progress = 100;
            toast("ok", `Uploaded: ${item.file.name}`);
            refreshFiles();
          } catch {
            item.state = "failed"; item.errorText = "Upload ok but response JSON parse failed.";
            toast("error", `Upload parse error: ${item.file.name}`);
          }
        } else {
          item.state = "failed"; item.errorText = `HTTP ${xhr.status}: ${xhr.responseText || "Upload failed"}`;
          toast("error", `Upload failed: ${item.file.name} (HTTP ${xhr.status})`);
        }
        resolve();
      };

      xhr.onerror = () => {
        item.xhr = null; item.state = "failed"; item.errorText = "Network error.";
        toast("error", `Upload failed (network): ${item.file.name}`);
        resolve();
      };

      xhr.onabort = () => {
        item.xhr = null;
        if (item.state === "uploading") {
          item.state = "canceled"; item.errorText = "Canceled by user";
          toast("error", `Canceled: ${item.file.name}`);
        }
        resolve();
      };

      const form = new FormData();
      form.append("file", item.file, item.file.name);
      xhr.send(form);
    });
  }

  // ---------- File list ----------
  async function refreshFiles() {
    try {
      const res = await fetch(`${BACKEND_BASE}/files`);
      if (!res.ok) return toast("error", `Failed to load files: HTTP ${res.status}`);
      const data = await res.json();
      lastFiles = Array.isArray(data) ? data : [];
      renderFiles();
    } catch (err) {
      toast("error", `Failed to load files: ${err}`);
    }
  }

  function renderFiles() {
    filesList.innerHTML = "";
    if (!lastFiles.length) {
      filesList.innerHTML = `<div class="placeholder">No files uploaded yet.</div>`;
      return;
    }

    for (const f of lastFiles) {
      const row = document.createElement("div");
      row.className = "file-row";

      const name = f.filename || f.name || f.id;
      const size = typeof f.size === "number" ? formatBytes(f.size) : "—";
      const uploaded = f.uploaded_at ? new Date(f.uploaded_at).toLocaleString() : "—";

      row.innerHTML = `
        <div class="file-left">
          <div class="file-name" title="${escapeHtml(name)}">${escapeHtml(name)}</div>
          <div class="file-meta">${size} · Uploaded: ${escapeHtml(uploaded)}</div>
        </div>
        <div class="file-actions">
          <button class="btn btn-small" data-copy="${escapeHtml(f.id)}">Copy link</button>
          <button class="btn btn-small" data-download="${escapeHtml(f.id)}">Download</button>
          <button class="btn btn-danger btn-small" data-delete="${escapeHtml(f.id)}">Delete</button>
        </div>
      `;
      filesList.appendChild(row);
    }

    filesList.querySelectorAll("[data-download]").forEach(b => b.addEventListener("click", () => downloadFile(b.dataset.download)));
    filesList.querySelectorAll("[data-delete]").forEach(b => b.addEventListener("click", () => deleteFile(b.dataset.delete)));
    filesList.querySelectorAll("[data-copy]").forEach(b => b.addEventListener("click", () => copyLink(b.dataset.copy)));
  }

  function downloadFile(id) {
    window.open(`${BACKEND_BASE}/files/${encodeURIComponent(id)}/download`, "_blank");
  }

  async function copyLink(id) {
    // If you later add POST /files/{id}/share, we can use it.
    // For now, copy download link (works reliably).
    const downloadUrl = `${BACKEND_BASE}/files/${encodeURIComponent(id)}/download`;

    try {
      await navigator.clipboard.writeText(downloadUrl);
      toast("ok", "Download link copied to clipboard.");
    } catch {
      // fallback: prompt
      window.prompt("Copy this link:", downloadUrl);
      toast("ok", "Copy the link from the prompt.");
    }
  }

  async function deleteFile(id) {
    if (!confirm("Delete this file?")) return;
    try {
      const res = await fetch(`${BACKEND_BASE}/files/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (!res.ok) return toast("error", `Delete failed: HTTP ${res.status}`);
      toast("ok", "File deleted.");
      refreshFiles();
    } catch (err) {
      toast("error", `Delete failed: ${err}`);
    }
  }

  function formatBytes(bytes) {
    const units = ["B","KB","MB","GB"];
    let b = bytes, i = 0;
    while (b >= 1024 && i < units.length - 1) { b /= 1024; i++; }
    return `${b.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  }

  // Events
  btnPing.addEventListener("click", pingBackend);
  btnClear.addEventListener("click", clearSelected);
  btnUpload.addEventListener("click", startUploadAllValid);
  btnRefreshFiles.addEventListener("click", refreshFiles);
  fileInput.addEventListener("change", (e) => addFiles(e.target.files));

  ["dragenter","dragover"].forEach(evt => dropzone.addEventListener(evt, (e) => {
    e.preventDefault(); e.stopPropagation(); dropzone.classList.add("dragover");
  }));
  ["dragleave","drop"].forEach(evt => dropzone.addEventListener(evt, (e) => {
    e.preventDefault(); e.stopPropagation(); dropzone.classList.remove("dragover");
  }));
  dropzone.addEventListener("drop", (e) => { const dt = e.dataTransfer; if (dt && dt.files) addFiles(dt.files); });
  dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });

  // init
  renderSelected();
  updateUploadButton();
  pingBackend();
  refreshFiles();
})();