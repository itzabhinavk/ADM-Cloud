(function () {
  "use strict";

  const csrf = () => {
    const el = document.querySelector('meta[name="csrf-token"]');
    return el ? el.getAttribute("content") : "";
  };

  // ==================== DARK MODE ====================
  function initDarkMode() {
    const toggle = document.getElementById("darkModeToggle");
    if (!toggle) return;

    const isDarkMode = () => {
      const stored = localStorage.getItem("darkMode");
      if (stored !== null) return stored === "true";
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    };

    const setDarkMode = (dark) => {
      if (dark) {
        document.documentElement.dataset.theme = "dark";
        toggle.textContent = "☀️";
        localStorage.setItem("darkMode", "true");
      } else {
        document.documentElement.dataset.theme = "light";
        toggle.textContent = "🌙";
        localStorage.setItem("darkMode", "false");
      }
    };

    setDarkMode(isDarkMode());
    toggle.addEventListener("click", () => {
      const dark = document.documentElement.dataset.theme !== "dark";
      setDarkMode(dark);
    });
  }

  // ==================== NOTIFICATIONS ====================
  function toast(message, kind, duration = 3200) {
    const host = document.getElementById("toasts");
    if (!host) return;
    const node = document.createElement("div");
    node.className = "toast" + (kind === "error" ? " error" : kind === "success" ? " success" : "");
    node.textContent = message;
    host.appendChild(node);
    setTimeout(() => node.remove(), duration);
  }

  // ==================== FILE UTILS ====================
  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  async function compressImage(file, quality = 0.8) {
    if (file.type === "image/gif") return file;
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement("canvas");
          canvas.width = img.width;
          canvas.height = img.height;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(img, 0, 0);
          const outputType = "image/jpeg";
          canvas.toBlob((blob) => {
            if (!blob) return reject(new Error("Compression failed"));
            const baseName = file.name.replace(/\.[^.]+$/, "");
            resolve(new File([blob], `${baseName}.jpg`, { type: outputType }));
          }, outputType, quality);
        };
        img.onerror = () => reject(new Error("Image load failed"));
        img.src = e.target.result;
      };
      reader.onerror = () => reject(new Error("File read failed"));
    });
  }

  // ==================== FILE PREVIEW MODAL WITH COMPRESSION ====================
  function createPreviewModal() {
    const modal = document.createElement("div");
    modal.id = "filePreviewModal";
    modal.className = "preview-modal hidden";
    modal.innerHTML = `
      <div class="preview-header">
        <div class="preview-filename" id="previewFileName"></div>
        <button class="preview-close" id="previewClose">Close (ESC)</button>
      </div>
      <div class="preview-content" id="previewContent">
        <img id="previewImage" alt="Preview" style="display:none;">
        <span id="previewLoading" style="color:#fff;">Loading...</span>
      </div>
      <div class="preview-controls">
        <div class="compression-group">
          <label for="compressionSlider">Compression:</label>
          <input type="range" id="compressionSlider" class="compression-slider" min="30" max="100" value="80">
          <span class="compression-value" id="compressionValue">80%</span>
          <span id="compressedSize" style="color:#ccc;font-size:11px;"></span>
        </div>
        <div class="edit-filename">
          <input type="text" id="renameInput" placeholder="New filename" maxlength="255">
          <button class="rename-btn" id="renameBtn">Rename</button>
        </div>
        <label for="previewCategory">Save in</label>
        <select id="previewCategory" class="category-select"><option value="">Public folder</option></select>
        <button class="btn btn-primary" id="previewUploadBtn" type="button">Upload image</button>
      </div>
    `;
    document.body.appendChild(modal);
    return modal;
  }

  let currentFileForPreview = null;
  let previewModal = null;
  let pendingPreviewFiles = [];

  function initPreviewModal() {
    if (!previewModal) previewModal = createPreviewModal();

    const closeBtn = document.getElementById("previewClose");
    const close = () => previewModal.classList.add("hidden");
    closeBtn.addEventListener("click", close);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !previewModal.classList.contains("hidden")) close();
    });
    previewModal.addEventListener("click", (e) => {
      if (e.target === previewModal) close();
    });

    const slider = document.getElementById("compressionSlider");
    const value = document.getElementById("compressionValue");
    const compressed = document.getElementById("compressedSize");

    slider.addEventListener("input", async (e) => {
      const q = parseInt(e.target.value) / 100;
      value.textContent = e.target.value + "%";
      if (currentFileForPreview) {
        try {
          const compFile = await compressImage(currentFileForPreview, q);
          compressed.textContent = "→ " + formatBytes(compFile.size);
          currentFileForPreview._compressedSize = compFile.size;
          currentFileForPreview._compressionQuality = q;
        } catch (err) {
          compressed.textContent = "Compress error";
        }
      }
    });

    document.getElementById("renameBtn").addEventListener("click", () => {
      let newName = document.getElementById("renameInput").value.trim();
      if (newName && currentFileForPreview) {
        const originalExtension = currentFileForPreview.name.includes(".")
          ? currentFileForPreview.name.slice(currentFileForPreview.name.lastIndexOf("."))
          : "";
        if (originalExtension && !newName.includes(".")) newName += originalExtension;
        currentFileForPreview._newName = newName;
        document.getElementById("previewFileName").textContent = newName;
        toast("Filename updated to: " + newName, "success", 2000);
      }
    });
    document.getElementById("previewUploadBtn").addEventListener("click", async () => {
      if (!currentFileForPreview) return;
      const uploadBtn = document.getElementById("previewUploadBtn");
      uploadBtn.disabled = true;
      try {
        const uploaded = await uploadFile(currentFileForPreview);
        if (uploaded && pendingPreviewFiles.length) {
          showFilePreview(pendingPreviewFiles.shift());
        } else if (uploaded) {
          previewModal.classList.add("hidden");
        }
      } finally {
        uploadBtn.disabled = false;
      }
    });
  }

  function showFilePreview(file) {
    if (!previewModal) initPreviewModal();

    currentFileForPreview = file;
    const modal = previewModal;
    modal.classList.remove("hidden");

    document.getElementById("previewFileName").textContent = file.name;
    document.getElementById("renameInput").value = "";
    document.getElementById("renameInput").placeholder = "Currently: " + file.name;
    document.getElementById("compressionSlider").value = 80;
    document.getElementById("compressionValue").textContent = "80%";
    document.getElementById("compressedSize").textContent = formatBytes(file.size);
    currentFileForPreview._compressionQuality = 0.8;
    document.getElementById("previewCategory").value = document.getElementById("uploadCategory")?.value || "";
    const categorySelect = document.getElementById("uploadCategory");
    const previewCategory = document.getElementById("previewCategory");
    previewCategory.innerHTML = categorySelect ? categorySelect.innerHTML : '<option value="">Public folder</option>';
    previewCategory.value = categorySelect?.value || "";

    const reader = new FileReader();
    const img = document.getElementById("previewImage");
    const loading = document.getElementById("previewLoading");

    reader.onload = (e) => {
      img.src = e.target.result;
      img.style.display = "block";
      loading.style.display = "none";
    };
    reader.onerror = () => {
      loading.textContent = "Could not load preview";
    };
    reader.readAsDataURL(file);
  }

  async function copyText(text) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (e) { /* fall through to legacy path */ }
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    area.remove();
    return ok;
  }

  // ==================== CONFIRM DIALOG ====================
  const dialog = document.getElementById("confirm-dialog");
  function confirmAction(message) {
    if (!dialog || typeof dialog.showModal !== "function") {
      return Promise.resolve(window.confirm(message || "Are you sure?"));
    }
    return new Promise((resolve) => {
      const ok = document.getElementById("confirm-ok");
      const cancel = document.getElementById("confirm-cancel");
      const done = (value) => {
        ok.removeEventListener("click", onOk);
        cancel.removeEventListener("click", onCancel);
        dialog.close();
        resolve(value);
      };
      const onOk = () => done(true);
      const onCancel = () => done(false);
      ok.addEventListener("click", onOk);
      cancel.addEventListener("click", onCancel);
      dialog.showModal();
    });
  }

  document.querySelectorAll(".js-confirm-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirmed === "1") return;
      event.preventDefault();
      confirmAction(form.dataset.confirm).then((ok) => {
        if (ok) { form.dataset.confirmed = "1"; form.submit(); }
      });
    });
  });

  // ==================== LIVE STATS UPDATE ====================
  function updateStatsLive(imageCount, totalBytes) {
    const stats = document.querySelector(".stats");
    if (!stats) return;

    const values = stats.querySelectorAll(".stat-value");
    if (values.length >= 2) {
      const countEl = values[0];
      const sizeEl = values[1];

      if (parseInt(countEl.textContent) !== imageCount) {
        countEl.classList.add("updating");
        countEl.textContent = imageCount;
        setTimeout(() => countEl.classList.remove("updating"), 400);
      }

      const formatted = formatBytes(totalBytes);
      if (sizeEl.textContent !== formatted) {
        sizeEl.classList.add("updating");
        sizeEl.textContent = formatted;
        setTimeout(() => sizeEl.classList.remove("updating"), 400);
      }
    }
  }

  async function refreshStats() {
    try {
      const res = await fetch("/api/images/stats", { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (!res.ok) return;
      const data = await res.json();
      updateStatsLive(data.count, data.total_bytes);
    } catch (e) { /* stats are non-critical */ }
  }

  function initCategories() {
    const filter = document.getElementById("categoryFilter");
    const createButton = document.getElementById("createCategoryBtn");
    const nameInput = document.getElementById("newCategoryName");
    if (filter) {
      filter.addEventListener("change", () => {
        const url = new URL(window.location.href);
        if (filter.value) url.searchParams.set("category_id", filter.value);
        else url.searchParams.delete("category_id");
        url.searchParams.delete("page");
        window.location.assign(url.toString());
      });
    }
    if (!createButton || !nameInput) return;
    createButton.addEventListener("click", async () => {
      const name = nameInput.value.trim();
      if (!name) return toast("Enter a folder name first", "error");
      createButton.disabled = true;
      try {
        const res = await fetch("/api/images/categories", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), Accept: "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ name }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || "Could not create folder");
        document.querySelectorAll("#categoryFilter, #uploadCategory, #previewCategory").forEach((select) => {
          if (!select || select.querySelector(`option[value="${data.category.id}"]`)) return;
          select.add(new Option(data.category.name, data.category.id));
        });
        document.getElementById("uploadCategory").value = String(data.category.id);
        nameInput.value = "";
        toast("Folder created", "success");
      } catch (err) {
        toast(err.message, "error");
      } finally {
        createButton.disabled = false;
      }
    });
  }

  // ==================== COPY & DELETE (EVENT DELEGATION) ====================
  document.addEventListener("click", async (event) => {
    const previewBtn = event.target.closest(".card-thumb");
    if (previewBtn) {
      const img = previewBtn.querySelector("img");
      if (img) showImageGalleryPreview(img.src, img.alt);
      return;
    }

    const copyBtn = event.target.closest(".js-copy");
    if (copyBtn) {
      const ok = await copyText(copyBtn.dataset.url);
      toast(ok ? "Link copied to clipboard" : "Copy failed — select the link manually", ok ? "success" : "error");
      return;
    }

    const delBtn = event.target.closest(".js-delete");
    if (!delBtn) return;
    const ok = await confirmAction("Delete this image?");
    if (!ok) return;
    delBtn.disabled = true;
    try {
      const res = await fetch("/api/images/" + encodeURIComponent(delBtn.dataset.slug), {
        method: "DELETE",
        headers: { "X-CSRFToken": csrf(), Accept: "application/json" },
        credentials: "same-origin",
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || "Delete failed");
      const card = delBtn.closest(".card");
      if (card) card.remove();
      toast("Image deleted", "success");
      refreshStats();
    } catch (err) {
      delBtn.disabled = false;
      toast(err.message || "Delete failed", "error");
    }
  });

  // ==================== GALLERY IMAGE PREVIEW ====================
  function initGalleryPreview() {
    const overlay = document.createElement("div");
    overlay.className = "image-preview-overlay";
    overlay.innerHTML = '<div class="image-preview-content"><img alt=""></div>';
    overlay.id = "galleryPreviewOverlay";
    document.body.appendChild(overlay);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.classList.remove("active");
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlay.classList.contains("active")) {
        overlay.classList.remove("active");
      }
    });
  }

  function showImageGalleryPreview(src, alt) {
    let overlay = document.getElementById("galleryPreviewOverlay");
    if (!overlay) {
      initGalleryPreview();
      overlay = document.getElementById("galleryPreviewOverlay");
    }
    overlay.querySelector("img").src = src;
    overlay.querySelector("img").alt = alt || "Preview";
    overlay.classList.add("active");
  }

  // ==================== FILE UPLOAD ORCHESTRATION ====================
  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  const queue = document.getElementById("upload-queue");
  const gallery = document.getElementById("gallery");
  if (!dropzone || !input) {
    initDarkMode();
    return;
  }

  const browse = document.getElementById("browse-btn");
  if (browse) browse.addEventListener("click", (e) => { e.stopPropagation(); input.click(); });
  dropzone.addEventListener("click", (e) => {
    if (e.target === dropzone || e.target.closest(".dropzone-inner")) input.click();
  });

  dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  ["dragenter", "dragover"].forEach((type) =>
    dropzone.addEventListener(type, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((type) =>
    dropzone.addEventListener(type, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); }));
  dropzone.addEventListener("drop", (e) => handleFiles(e.dataTransfer.files));
  input.addEventListener("change", (e) => {
    const files = Array.from(e.target.files || []);
    handleFiles(files);
    input.value = "";
  });

  function handleFiles(files) {
    if (files.length === 0) return;
    const images = Array.from(files).filter((file) => file.type.startsWith("image/"));
    const rejected = files.length - images.length;
    if (rejected) toast(`${rejected} non-image file(s) skipped`, "error");
    if (!images.length) return;
    pendingPreviewFiles = images.slice(1);
    showFilePreview(images[0]);
  }

  // ==================== UPLOAD ITEM RENDERING ====================
  function createUploadItem(file) {
    const li = document.createElement("li");
    li.className = "upload-item uploading";

    const row = document.createElement("div");
    row.className = "upload-item-with-thumb";

    const thumb = document.createElement("div");
    thumb.className = "upload-item-thumb";
    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = document.createElement("img");
        img.src = e.target.result;
        thumb.innerHTML = "";
        thumb.appendChild(img);
      };
      reader.readAsDataURL(file);
    } else {
      thumb.textContent = "📄";
    }

    const info = document.createElement("div");
    info.style.display = "flex";
    info.style.flexDirection = "column";
    info.style.gap = "4px";
    info.style.minWidth = "0";

    const name = document.createElement("span");
    name.className = "upload-item-name";
    name.textContent = escapeHtml(file._newName || file.name);
    name.style.overflow = "hidden";
    name.style.textOverflow = "ellipsis";
    name.style.whiteSpace = "nowrap";
    name.style.fontSize = "13px";
    name.style.fontWeight = "600";

    const meta = document.createElement("span");
    meta.className = "upload-item-meta";
    meta.textContent = formatBytes(file.size);
    meta.style.fontSize = "12px";
    meta.style.color = "var(--muted)";

    const status = document.createElement("span");
    status.className = "upload-item-status";
    status.textContent = "0%";
    status.style.fontSize = "12px";
    status.style.fontWeight = "600";
    status.style.color = "var(--brand)";

    info.appendChild(name);
    info.appendChild(meta);
    info.appendChild(status);

    row.appendChild(thumb);
    row.appendChild(info);
    row.appendChild(status);

    li.appendChild(row);
    return { li, statusEl: status };
  }

  // ==================== GALLERY CARD RENDERING ====================
  function renderCard(image) {
    const empty = document.getElementById("empty-state");
    if (empty) empty.remove();
    if (!gallery) return;
    const article = document.createElement("article");
    article.className = "card";
    article.dataset.slug = image.slug;
    article.innerHTML =
      '<a class="card-thumb" href="' + image.public_url + '">' +
      '<img src="' + image.thumbnail_url + '" alt="" loading="lazy"></a>' +
      '<div class="card-body"><p class="card-name">' + escapeHtml(image.filename) + "</p>" +
      '<p class="card-meta">Just now' + (image.width ? " · " + image.width + "×" + image.height : "") + "</p></div>" +
      '<div class="card-actions">' +
      '<button class="btn btn-small btn-primary js-copy" type="button" data-url="' + image.public_url + '">Copy URL</button>' +
      '<a class="btn btn-small btn-ghost" href="' + image.public_url + '">Open</a>' +
      '<button class="btn btn-small btn-danger js-delete" type="button" data-slug="' + image.slug + '">Delete</button>' +
      "</div>";
    gallery.prepend(article);
  }

  // ==================== UPLOAD EXECUTION ====================
  async function uploadFile(file) {
    if (!file.type.startsWith("image/")) {
      toast("Only image files allowed", "error");
      return;
    }

    const { li: row, statusEl } = createUploadItem(file);
    if (queue) queue.appendChild(row);
    row.classList.add("uploading");

    try {
      const body = new FormData();
      const fileToUpload = file._compressionQuality
        ? await compressImage(file, file._compressionQuality)
        : file;
      let uploadName = file._newName || fileToUpload.name || file.name;
      if (fileToUpload.type === "image/jpeg" && !/\.jpe?g$/i.test(uploadName)) {
        uploadName = uploadName.replace(/\.[^.]+$/, "") + ".jpg";
      }
      body.append("file", fileToUpload, uploadName);
      const selectedCategory = document.getElementById("previewCategory")?.value
        || document.getElementById("uploadCategory")?.value
        || "";
      if (selectedCategory) body.append("category_id", selectedCategory);
      statusEl.textContent = "Uploading...";
      const res = await fetch("/api/images/upload", {
        method: "POST",
        body,
        headers: { "X-CSRFToken": csrf(), Accept: "application/json" },
        credentials: "same-origin",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Upload failed");
      row.className = "upload-item success";
      statusEl.textContent = "✓";
      setTimeout(() => row.remove(), 2000);
      renderCard(data.image);
      toast("✓ " + (file._newName || file.name) + " uploaded", "success");
      refreshStats();
      return true;
    } catch (err) {
      row.className = "upload-item error";
      statusEl.textContent = "✗";
      toast(err.message || "Upload failed", "error");
      return false;
    }
  }

  // ==================== INITIALIZATION ====================
  initDarkMode();
  initCategories();
  initPreviewModal();
  initGalleryPreview();
})();
