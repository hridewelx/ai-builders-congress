/* Upload validation: JPEG/PNG, size limit, drag and drop, preview.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
  /* ----------------------------------------------------------------
     Upload validation: JPEG/PNG + 15 MB, Drag & Drop + Live Preview
  ---------------------------------------------------------------- */
  /* Show the chosen filename in our own chrome, not the native control's. */
  $$(".file-pick input[type=file]").forEach(function (input) {
    var label = input.closest(".file-pick");
    var name = label && label.querySelector("[data-file-name]");
    if (!name) return;
    var idle = name.textContent;
    input.addEventListener("change", function () {
      var picked = input.files && input.files[0];
      name.textContent = picked ? picked.name : idle;
      name.title = name.textContent;
      name.classList.toggle("is-chosen", !!picked);
    });
  });

  $$(".upload-form").forEach(function (form) {
    var input = form.querySelector(".upload-input");
    var result = form.querySelector(".upload-result");
    var maxBytes = parseInt(form.getAttribute("data-max-bytes") || "15728640", 10);
    if (!input || !result) return;
    function setMsg(text, cls) {
      result.textContent = text;
      result.className = "upload-result" + (cls ? " is-" + cls : "");
    }
    function handleFile(file) {
      if (!file) { result.textContent = ""; result.className = "upload-result"; return; }
      var name = (file.name || "").toLowerCase();
      var type = (file.type || "").toLowerCase();
      var isJpeg = /\.jpe?g$/.test(name) || type === "image/jpeg";
      var isPng = /\.png$/.test(name) || type === "image/png";
      var isHeic = /\.heic$|\.heif$/.test(name) || type === "image/heic" || type === "image/heif";
      if (isHeic) { setMsg("HEIC is not accepted. Export as JPEG or PNG.", "error"); input.value = ""; return; }
      if (!isJpeg && !isPng) { setMsg("Only JPEG and PNG photos are accepted.", "error"); input.value = ""; return; }
      if (file.size > maxBytes) { setMsg("File is larger than 15 MB.", "error"); input.value = ""; return; }

      result.innerHTML = "";
      result.className = "upload-result is-ok";
      var wrap = document.createElement("div");
      wrap.style.cssText = "display:flex;align-items:center;gap:8px;margin-top:6px";
      var img = document.createElement("img");
      try { img.src = URL.createObjectURL(file); } catch (e) {}
      img.style.cssText = "width:36px;height:36px;object-fit:cover;border-radius:4px;border:1px solid var(--line)";
      var txt = document.createElement("span");
      txt.textContent = (file.size / (1024 * 1024)).toFixed(1) + " MB · ready to upload";
      wrap.appendChild(img);
      wrap.appendChild(txt);
      result.appendChild(wrap);
    }

    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      handleFile(file);
    });

    form.addEventListener("dragover", function (e) {
      e.preventDefault();
      form.classList.add("is-dragover");
    });
    form.addEventListener("dragleave", function () {
      form.classList.remove("is-dragover");
    });
    form.addEventListener("drop", function (e) {
      e.preventDefault();
      form.classList.remove("is-dragover");
      var dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length) {
        input.files = dt.files;
        handleFile(dt.files[0]);
      }
    });

    form.addEventListener("submit", function () {
      var file = input.files && input.files[0];
      if (!file) return;
      var name = (file.name || "").toLowerCase();
      if (/\.heic$|\.heif$/.test(name)) { setMsg("HEIC is not accepted. Export as JPEG or PNG.", "error"); return false; }
      if (file.size > maxBytes) { setMsg("File is larger than 15 MB.", "error"); return false; }
      setMsg("Uploading…", "busy");
      var btn = form.querySelector("button[type=submit]");
      if (btn) { btn.disabled = true; btn.textContent = "…"; }
    });
  });

  /* Busy state on form submit, without pretending the action succeeded. */
  $$("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      if (form.getAttribute("data-no-busy") !== null) return;
      var button = form.querySelector("button[type=submit], button:not([type])");
      if (button && !button.disabled) {
        button.setAttribute("aria-busy", "true");
        button.dataset.label = button.textContent;
        button.textContent = "…";
        window.setTimeout(function () {
          button.removeAttribute("aria-busy");
          if (button.dataset.label) button.textContent = button.dataset.label;
        }, 2500);
      }
    });
  });
  });
})();
