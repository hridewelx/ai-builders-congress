/* ==================================================================
   LOTLINE — small dependency-free interaction layer.
   No network calls, no storage of tokens, no client-side decisions.
   ================================================================== */
(function () {
  "use strict";

  var $ = function (selector, root) { return (root || document).querySelector(selector); };
  var $$ = function (selector, root) { return Array.prototype.slice.call((root || document).querySelectorAll(selector)); };

  /* ----------------------------------------------------------------
     Sidebar: desktop collapse, mobile drawer
  ---------------------------------------------------------------- */
  var railToggle = $("[data-rail-toggle]");
  var drawerToggle = $("[data-drawer-toggle]");
  var drawerClose = $$("[data-drawer-close]");
  var sidebar = $("#sidebar");

  function setDrawer(open) {
    document.body.classList.toggle("drawer-open", open);
    if (drawerToggle) drawerToggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open && sidebar) {
      var first = sidebar.querySelector("a, button");
      if (first) first.focus();
    } else if (drawerToggle) {
      drawerToggle.focus();
    }
  }

  if (railToggle) {
    railToggle.addEventListener("click", function () {
      var collapsed = document.body.classList.toggle("rail-collapsed");
      railToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      railToggle.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
    });
  }
  if (drawerToggle) {
    drawerToggle.addEventListener("click", function () {
      if (window.innerWidth <= 900) {
        setDrawer(!document.body.classList.contains("drawer-open"));
      } else {
        var collapsed = document.body.classList.toggle("rail-collapsed");
        if (railToggle) {
          railToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
          railToggle.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
        }
      }
    });
  }
  drawerClose.forEach(function (el) {
    if (el.hasAttribute("data-drawer-close") && el.closest(".rail")) {
      el.addEventListener("click", function () { setDrawer(false); });
    } else if (el.classList.contains("mobile-scrim")) {
      el.addEventListener("click", function () { setDrawer(false); });
    }
  });
  window.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && document.body.classList.contains("drawer-open")) setDrawer(false);
  });

  /* Close the avatar menu when clicking outside it. */
  $$("details.user-menu").forEach(function (menu) {
    document.addEventListener("click", function (event) {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
    menu.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { menu.open = false; menu.querySelector("summary").focus(); }
    });
  });

  /* ----------------------------------------------------------------
     Dialogs (HTML5 <dialog> with focus trap and trigger return)
  ---------------------------------------------------------------- */
  var lastFocusedTrigger = null;

  function openDialog(id, trigger) {
    var dialog = document.getElementById(id);
    if (!dialog) return;
    lastFocusedTrigger = trigger || document.activeElement;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    var focusable = dialog.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
    if (focusable.length) focusable[0].focus();
  }

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
    if (lastFocusedTrigger && typeof lastFocusedTrigger.focus === "function") {
      lastFocusedTrigger.focus();
      lastFocusedTrigger = null;
    }
  }

  $$("[data-dialog-open]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      openDialog(trigger.getAttribute("data-dialog-open"), trigger);
    });
  });

  $$("[data-dialog-close]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      closeDialog(trigger.closest("dialog"));
    });
  });

  $$("dialog").forEach(function (dialog) {
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) closeDialog(dialog);
    });

    dialog.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDialog(dialog);
      } else if (event.key === "Tab") {
        var focusable = dialog.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
        if (!focusable.length) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    });

    dialog.addEventListener("close", function () {
      if (lastFocusedTrigger && typeof lastFocusedTrigger.focus === "function") {
        lastFocusedTrigger.focus();
        lastFocusedTrigger = null;
      }
    });
  });
  $$("[data-dialog-confirm]").forEach(function (button) {
    button.addEventListener("click", function () {
      var dialog = button.closest("dialog");
      var formId = dialog && dialog.getAttribute("data-confirm-form");
      if (formId) {
        var form = document.getElementById(formId);
        if (form) { form.requestSubmit ? form.requestSubmit() : form.submit(); return; }
      }
      closeDialog(dialog);
      var toastId = dialog && dialog.getAttribute("data-confirm-toast");
      if (toastId) showToast(toastId);
    });
  });

  /* ----------------------------------------------------------------
     Toasts
  ---------------------------------------------------------------- */
  var toastTimers = {};
  function showToast(id) {
    var toast = document.getElementById(id);
    if (!toast) return;
    toast.classList.add("is-visible");
    if (toastTimers[id]) window.clearTimeout(toastTimers[id]);
    toastTimers[id] = window.setTimeout(function () { toast.classList.remove("is-visible"); }, 5200);
  }
  function hideToast(toast) {
    if (!toast) return;
    toast.classList.remove("is-visible");
    if (toastTimers[toast.id]) window.clearTimeout(toastTimers[toast.id]);
  }
  $$("[data-toast-show]").forEach(function (trigger) {
    trigger.addEventListener("click", function () { showToast(trigger.getAttribute("data-toast-show")); });
  });
  $$("[data-toast-close]").forEach(function (trigger) {
    trigger.addEventListener("click", function () { hideToast(trigger.closest(".toast")); });
  });

  /* ----------------------------------------------------------------
     Progressive data table: filter, sort, paginate (DOM only)
  ---------------------------------------------------------------- */
  $$("[data-table]").forEach(function (wrapper) {
    var table = wrapper.querySelector("table");
    if (!table || !table.tBodies.length) return;
    var tbody = table.tBodies[0];
    var rows = Array.prototype.slice.call(tbody.rows);
    var filter = wrapper.querySelector("[data-table-filter]");
    var count = wrapper.querySelector("[data-table-count]");
    var pager = wrapper.querySelector("[data-table-pagination]");
    var pageSize = parseInt(wrapper.getAttribute("data-page-size") || "8", 10);
    if (!pageSize || pageSize < 1) pageSize = 8;
    var page = 1;
    var sortIndex = -1;
    var sortDir = 1;

    function cellText(row, index) {
      var cell = row.cells[index];
      return cell ? (cell.getAttribute("data-sort-value") || cell.textContent || "").trim() : "";
    }
    function matches(row, term) {
      if (!term) return true;
      return (row.textContent || "").toLowerCase().indexOf(term) !== -1;
    }
    function render() {
      var term = filter ? (filter.value || "").trim().toLowerCase() : "";
      var visible = rows.filter(function (row) { return matches(row, term); });
      if (sortIndex >= 0) {
        visible.sort(function (a, b) {
          var av = cellText(a, sortIndex);
          var bv = cellText(b, sortIndex);
          var an = parseFloat(av.replace(/[^0-9.\-]/g, ""));
          var bn = parseFloat(bv.replace(/[^0-9.\-]/g, ""));
          var numeric = !isNaN(an) && !isNaN(bn) && av !== "" && bv !== "";
          var cmp = numeric ? (an - bn) : av.localeCompare(bv, undefined, { numeric: true, sensitivity: "base" });
          return cmp * sortDir;
        });
        visible.forEach(function (row) { tbody.appendChild(row); });
      }
      var total = visible.length;
      var pages = Math.max(1, Math.ceil(total / pageSize));
      if (page > pages) page = pages;
      rows.forEach(function (row) { row.hidden = true; });
      visible.slice((page - 1) * pageSize, page * pageSize).forEach(function (row) { row.hidden = false; });
      if (count) count.textContent = (total ? ((page - 1) * pageSize + 1) + "–" + Math.min(page * pageSize, total) + " of " + total : "0 of 0");
      if (pager) {
        pager.textContent = "";
        var info = document.createElement("span");
        info.textContent = "Page " + page + " of " + pages;
        var prev = document.createElement("button");
        prev.type = "button";
        prev.className = "btn sm ghost";
        prev.textContent = "Previous";
        prev.disabled = page <= 1;
        prev.addEventListener("click", function () { page -= 1; render(); });
        var next = document.createElement("button");
        next.type = "button";
        next.className = "btn sm ghost";
        next.textContent = "Next";
        next.disabled = page >= pages;
        next.addEventListener("click", function () { page += 1; render(); });
        pager.appendChild(prev);
        pager.appendChild(info);
        pager.appendChild(next);
      }
    }
    if (filter) filter.addEventListener("input", function () { page = 1; render(); });
    $$("th[data-sort]", table).forEach(function (th) {
      var index = Array.prototype.indexOf.call(th.parentNode.children, th);
      th.setAttribute("tabindex", "0");
      th.setAttribute("role", "button");
      function sort() {
        if (sortIndex === index) sortDir = -sortDir;
        else { sortIndex = index; sortDir = 1; }
        $$("th[data-sort]", table).forEach(function (other) { other.removeAttribute("aria-sort"); });
        th.setAttribute("aria-sort", sortDir === 1 ? "ascending" : "descending");
        render();
      }
      th.addEventListener("click", sort);
      th.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); sort(); }
      });
    });
    render();
  });

  /* ----------------------------------------------------------------
     Print
  ---------------------------------------------------------------- */
  $$("[data-print]").forEach(function (button) {
    button.addEventListener("click", function () { window.print(); });
  });

  /* ----------------------------------------------------------------
     Review viewer: zoom, pan, heat toggle, box<->proposal linking
  ---------------------------------------------------------------- */
  var viewer = document.getElementById("viewer");
  var viewerScroll = document.getElementById("viewerScroll");
  var mainImage = document.getElementById("mainImage");
  var heatToggle = document.getElementById("heatToggle");
  var pending = document.getElementById("pendingBox");
  var cx = document.getElementById("cx");
  var cy = document.getElementById("cy");
  var zoomLevel = document.getElementById("zoomLevel");
  var boxLayer = document.getElementById("boxLayer");

  if (heatToggle && mainImage) {
    var heatOn = false;
    heatToggle.addEventListener("click", function () {
      heatOn = !heatOn;
      if (heatOn) {
        mainImage.dataset.originalSrc = mainImage.src;
        mainImage.src = mainImage.dataset.heat;
      } else if (mainImage.dataset.originalSrc) {
        mainImage.src = mainImage.dataset.originalSrc;
      }
      heatToggle.textContent = heatOn
        ? (heatToggle.getAttribute("data-show-photo") || "Show photo")
        : (heatToggle.getAttribute("data-show-heat") || "Show attention map");
    });
  }

  if (viewerScroll && mainImage) {
    var scale = 1, minScale = 1, maxScale = 4, panX = 0, panY = 0;
    var panning = false, startX = 0, startY = 0, baseX = 0, baseY = 0;
    var moved = false;

    function apply() {
      var transform = "translate(" + panX + "px," + panY + "px) scale(" + scale + ")";
      mainImage.style.transform = transform;
      if (boxLayer) {
        boxLayer.style.transform = transform;
        boxLayer.style.transformOrigin = "0 0";
      }
      if (zoomLevel) zoomLevel.textContent = Math.round(scale * 100) + "%";
    }
    function setScale(next, cxClient, cyClient) {
      var rect = viewerScroll.getBoundingClientRect();
      var px = (cxClient === undefined) ? rect.width / 2 : cxClient - rect.left;
      var py = (cyClient === undefined) ? rect.height / 2 : cyClient - rect.top;
      var newScale = Math.min(maxScale, Math.max(minScale, next));
      // keep the point under the cursor stable
      var ratio = newScale / scale;
      panX = px - (px - panX) * ratio;
      panY = py - (py - panY) * ratio;
      scale = newScale;
      if (scale <= minScale) { panX = 0; panY = 0; }
      apply();
    }
    function reset() { scale = 1; panX = 0; panY = 0; apply(); }

    $$("[data-zoom]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var dir = btn.getAttribute("data-zoom");
        if (dir === "in") setScale(scale * 1.25);
        else if (dir === "out") setScale(scale / 1.25);
        else reset();
      });
    });

    viewerScroll.addEventListener("wheel", function (event) {
      if (!event.ctrlKey && Math.abs(event.deltaY) < 2) return;
      event.preventDefault();
      setScale(scale * (event.deltaY < 0 ? 1.12 : 0.89), event.clientX, event.clientY);
    }, { passive: false });

    viewerScroll.addEventListener("pointerdown", function (event) {
      if (event.button !== 0) return;
      panning = true; moved = false;
      startX = event.clientX; startY = event.clientY; baseX = panX; baseY = panY;
      viewerScroll.classList.add("is-panning");
      viewerScroll.setPointerCapture(event.pointerId);
    });
    viewerScroll.addEventListener("pointermove", function (event) {
      if (!panning) return;
      var dx = event.clientX - startX, dy = event.clientY - startY;
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      panX = baseX + dx; panY = baseY + dy; apply();
    });
    viewerScroll.addEventListener("pointerup", function (event) {
      panning = false;
      viewerScroll.classList.remove("is-panning");
      try { viewerScroll.releasePointerCapture(event.pointerId); } catch (e) {}
    });

    document.addEventListener("keydown", function (event) {
      var tag = (event.target && event.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (event.key === "+" || event.key === "=") { setScale(scale * 1.25); event.preventDefault(); }
      else if (event.key === "-" || event.key === "_") { setScale(scale / 1.25); event.preventDefault(); }
      else if (event.key === "0") { reset(); event.preventDefault(); }
      else if (event.key === "c" || event.key === "C") {
        var selProp = $(".prop.sel") || $(".prop");
        if (selProp) {
          var d = selProp.querySelector("details");
          if (d) { d.open = true; var inp = d.querySelector("select, input"); if (inp) inp.focus(); event.preventDefault(); }
        }
      } else if (event.key === "x" || event.key === "X" || event.key === "r" || event.key === "R") {
        var selPropR = $(".prop.sel") || $(".prop");
        if (selPropR) {
          var rejectBtn = selPropR.querySelector('form[action*="/reject"] button');
          if (rejectBtn) { rejectBtn.focus(); event.preventDefault(); }
        }
      } else if (event.key === "]" || event.key === "n" || event.key === "N") {
        var nextLink = $('a[href*="/review/"][class*="primary"]');
        if (nextLink) { nextLink.click(); event.preventDefault(); }
      } else if (event.key === "[") {
        var queueLink = $('a[href*="/review"][class*="ghost"]');
        if (queueLink) { queueLink.click(); event.preventDefault(); }
      }
    });

    // click to place a manual box (only when not panning and not zoomed far)
    viewerScroll.addEventListener("click", function (event) {
      if (moved) { moved = false; return; }
      if (event.target.closest(".box[data-pid]")) return;
      if (!pending || !cx || !cy) return;
      var rect = mainImage.getBoundingClientRect();
      var x = (event.clientX - rect.left) / rect.width;
      var y = (event.clientY - rect.top) / rect.height;
      if (x < 0 || x > 1 || y < 0 || y > 1) return;
      cx.value = Math.min(0.98, Math.max(0.02, x)).toFixed(4);
      cy.value = Math.min(0.98, Math.max(0.02, y)).toFixed(4);
      pending.style.display = "block";
      pending.style.left = (x * 100) + "%";
      pending.style.top = (y * 100) + "%";

      var manualCard = document.getElementById("manualAddCard");
      if (manualCard) {
        manualCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        var addType = document.getElementById("add-type");
        if (addType) addType.focus();
      }
    });
  }

  $$(".box[data-pid]").forEach(function (box) {
    box.addEventListener("click", function () {
      var id = box.dataset.pid;
      $$(".box").forEach(function (b) { b.classList.remove("sel"); });
      box.classList.add("sel");
      var prop = document.getElementById("prop-" + id);
      if (prop) {
        $$(".prop").forEach(function (p) { p.classList.remove("sel"); });
        prop.classList.add("sel");
        prop.scrollIntoView({ behavior: "smooth", block: "center" });
        var d = prop.querySelector("details");
        if (d) d.open = true;
      }
    });
  });

  $$(".prop[data-pid]").forEach(function (prop) {
    prop.addEventListener("mouseenter", function () {
      var box = document.querySelector('.box[data-pid="' + prop.dataset.pid + '"]');
      if (box) box.classList.add("sel");
    });
    prop.addEventListener("mouseleave", function () {
      var box = document.querySelector('.box[data-pid="' + prop.dataset.pid + '"]');
      if (box) box.classList.remove("sel");
    });
  });

  /* ----------------------------------------------------------------
     Upload validation: JPEG/PNG + 15 MB, Drag & Drop + Live Preview
  ---------------------------------------------------------------- */
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

  /* ----------------------------------------------------------------
     Capture: Unit jumper and Side filter
  ---------------------------------------------------------------- */
  var unitPicker = document.getElementById("unitPicker");
  if (unitPicker) {
    unitPicker.addEventListener("change", function () {
      var val = unitPicker.value;
      var cards = $$(".unit-garment-card");
      if (val === "all") {
        cards.forEach(function (c) { c.style.display = ""; });
      } else {
        cards.forEach(function (c) {
          if (c.id === val) {
            c.style.display = "";
            c.scrollIntoView({ behavior: "smooth", block: "start" });
          } else {
            c.style.display = "none";
          }
        });
      }
    });
  }

  $$("[data-filter-side]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var side = btn.getAttribute("data-filter-side");
      $$("[data-filter-side]").forEach(function (b) { b.classList.remove("active", "subtle"); b.classList.add("ghost"); });
      btn.classList.add("active", "subtle");
      btn.classList.remove("ghost");
      $$(".upload-view").forEach(function (view) {
        if (side === "all" || view.getAttribute("data-side") === side) {
          view.style.display = "";
        } else {
          view.style.display = "none";
        }
      });
    });
  });

  /* ----------------------------------------------------------------
     Password Visibility Toggle (Login screen)
  ---------------------------------------------------------------- */
  var passToggle = document.getElementById("passToggle");
  var passInput = document.getElementById("password");
  if (passToggle && passInput) {
    passToggle.addEventListener("click", function () {
      var isPass = passInput.type === "password";
      passInput.type = isPass ? "text" : "password";
      passToggle.setAttribute("aria-label", isPass ? "Hide password" : "Show password");
      passToggle.setAttribute("title", isPass ? "Hide password" : "Show password");
      passToggle.innerHTML = isPass
        ? '<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>'
        : '<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
      passInput.focus();
    });
  }

  /* ----------------------------------------------------------------
     Copy to Clipboard (Admin temp passwords)
  ---------------------------------------------------------------- */
  $$("[data-copy-target]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var targetId = btn.getAttribute("data-copy-target");
      var targetEl = document.getElementById(targetId);
      if (!targetEl) return;
      var text = targetEl.textContent.trim();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text);
      } else {
        var ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      var origHTML = btn.innerHTML;
      btn.innerHTML = '<span>✓ Copied</span>';
      window.setTimeout(function () { btn.innerHTML = origHTML; }, 2200);
    });
  });

  /* Copy hash button */
  $$("[data-copy-hash]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy-hash");
      if (!text) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text);
      } else {
        var ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      var origHTML = btn.innerHTML;
      btn.innerHTML = '<span style="color:var(--success);font-weight:700">✓</span>';
      window.setTimeout(function () { btn.innerHTML = origHTML; }, 2000);
    });
  });

  /* ----------------------------------------------------------------
     Lot Code auto-uppercase (Create Lot)
  ---------------------------------------------------------------- */
  var lotCodeInput = document.getElementById("lot-code");
  if (lotCodeInput) {
    lotCodeInput.addEventListener("input", function () {
      var pos = lotCodeInput.selectionStart;
      lotCodeInput.value = lotCodeInput.value.toUpperCase();
      try { lotCodeInput.setSelectionRange(pos, pos); } catch (e) {}
    });
  }

  /* ----------------------------------------------------------------
     Audit Log payload toggle
  ---------------------------------------------------------------- */
  var toggleAuditBtn = document.getElementById("toggleAuditDetails");
  if (toggleAuditBtn) {
    var allExpanded = false;
    toggleAuditBtn.addEventListener("click", function () {
      allExpanded = !allExpanded;
      $$("table details").forEach(function (d) { d.open = allExpanded; });
      var span = toggleAuditBtn.querySelector("span");
      if (span) span.textContent = allExpanded ? "Collapse All Payloads" : "Expand All Payloads";
    });
  }

  /* ----------------------------------------------------------------
     Decision Override: Reason counter, Gated submit & Dynamic risk notice
  ---------------------------------------------------------------- */
  var reasonInput = document.getElementById("override-reason");
  var charCounter = document.getElementById("charCounter");
  var submitOverrideBtn = document.getElementById("submitOverrideBtn");
  var overrideDisp = document.getElementById("override-disposition");
  var highRiskNotice = document.getElementById("highRiskNotice");
  var immediateNotice = document.getElementById("immediateNotice");

  function updateOverrideState() {
    if (reasonInput && charCounter) {
      var len = reasonInput.value.trim().length;
      charCounter.textContent = len + " / 20 minimum";
      charCounter.style.color = len >= 20 ? "var(--green)" : "var(--muted)";
      if (submitOverrideBtn) {
        submitOverrideBtn.disabled = len < 20;
      }
    }
    if (overrideDisp) {
      var val = overrideDisp.value;
      if (highRiskNotice && immediateNotice) {
        if (val === "OVERRIDE_ACCEPT") {
          highRiskNotice.style.display = "";
          immediateNotice.style.display = "none";
        } else if (val === "OVERRIDE_REJECT") {
          highRiskNotice.style.display = "none";
          immediateNotice.style.display = "";
        }
      }
    }
  }

  if (reasonInput) reasonInput.addEventListener("input", updateOverrideState);
  if (overrideDisp) overrideDisp.addEventListener("change", updateOverrideState);
  if (reasonInput || overrideDisp) updateOverrideState();

  /* ----------------------------------------------------------------
     Sampling Plan: Single-sampling Re = Ac + 1 Invariant Validator
  ---------------------------------------------------------------- */
  $$(".ac-input").forEach(function (acInput) {
    var c = acInput.getAttribute("data-class");
    var reInput = document.getElementById(c + "_re");
    function validateAcRe() {
      var acVal = parseInt(acInput.value, 10);
      var reVal = reInput ? parseInt(reInput.value, 10) : NaN;
      if (!isNaN(acVal) && reInput) {
        if (isNaN(reVal) || reVal <= acVal) {
          reInput.setCustomValidity("Re must be greater than Ac (single sampling rule: Re = Ac + 1)");
        } else {
          reInput.setCustomValidity("");
        }
      }
    }
    acInput.addEventListener("input", function () {
      var acVal = parseInt(acInput.value, 10);
      if (!isNaN(acVal) && reInput) {
        reInput.value = acVal + 1;
      }
      validateAcRe();
    });
    if (reInput) reInput.addEventListener("input", validateAcRe);
  });

  /* ----------------------------------------------------------------
     Dashboard: Instant Lot Filter & Search with Directory Deep-Link
  ---------------------------------------------------------------- */
  var lotSearchInput = document.getElementById("lotSearchInput");
  var filterTabs = $$(".filter-pills .pill-btn");
  var lotCards = $$("[data-lot-card]");
  var lotEmptyMatch = document.getElementById("lotEmptyMatch");
  var lotSearchDirLink = document.getElementById("lotSearchDirLink");

  function filterDashboardLots() {
    var q = lotSearchInput ? lotSearchInput.value.trim().toLowerCase() : "";
    var activeTab = document.querySelector(".filter-pills .pill-btn.on");
    var tabFilter = activeTab ? activeTab.getAttribute("data-filter-tab") : "all";

    if (lotSearchDirLink) {
      lotSearchDirLink.href = "/lots?q=" + encodeURIComponent(q);
    }

    var visibleCount = 0;
    lotCards.forEach(function (card) {
      var hay = (card.getAttribute("data-lot-search") || "").toLowerCase();
      var status = card.getAttribute("data-lot-status") || "";

      var matchesQ = !q || hay.indexOf(q) !== -1;
      var matchesTab = tabFilter === "all" || status === tabFilter;

      if (matchesQ && matchesTab) {
        card.style.display = "";
        visibleCount++;
      } else {
        card.style.display = "none";
      }
    });

    if (lotEmptyMatch) {
      lotEmptyMatch.style.display = (visibleCount === 0 && (q !== "" || tabFilter !== "all")) ? "block" : "none";
    }

    var announcer = document.getElementById("lotSearchResultsLive");
    if (announcer) {
      if (q !== "" || tabFilter !== "all") {
        var isBn = document.documentElement.lang === "bn";
        if (visibleCount === 0) {
          announcer.textContent = isBn ? "কোনো লট পাওয়া যায়নি" : "No matching lots found";
        } else {
          var numStr = isBn ? (visibleCount + "").replace(/[0-9]/g, function (d) { return "০১২৩৪৫৬৭৮৯"[d]; }) : visibleCount;
          announcer.textContent = isBn ? numStr + "টি লট প্রদর্শিত হচ্ছে" : visibleCount + " lots found";
        }
      } else {
        announcer.textContent = "";
      }
    }
  }

  if (lotSearchInput) {
    lotSearchInput.addEventListener("input", filterDashboardLots);
  }
  if (filterTabs.length) {
    filterTabs.forEach(function (btn) {
      btn.addEventListener("click", function () {
        filterTabs.forEach(function (b) {
          b.classList.remove("on");
          b.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("on");
        btn.setAttribute("aria-pressed", "true");
        filterDashboardLots();
      });
    });
  }

  /* ----------------------------------------------------------------
     Lot tabs: History hash & scroll sync
  ---------------------------------------------------------------- */
  function syncHistoryTab() {
    var historySection = $("#history");
    var historyTab = $('nav.tabs a[href*="#history"]');
    if (!historySection || !historyTab) return;
    var navTabs = historyTab.closest("nav.tabs");
    if (!navTabs) return;
    var allTabs = $$("a", navTabs);
    var firstTab = allTabs[0];

    if (window.location.hash === "#history") {
      allTabs.forEach(function (tab) {
        tab.classList.remove("on");
        tab.removeAttribute("aria-current");
      });
      historyTab.classList.add("on");
      historyTab.setAttribute("aria-current", "location");
    } else if (window.location.hash === "" || window.location.hash === "#") {
      if (historyTab.classList.contains("on")) {
        historyTab.classList.remove("on");
        historyTab.removeAttribute("aria-current");
        if (firstTab) {
          firstTab.classList.add("on");
          firstTab.setAttribute("aria-current", "page");
        }
      }
    }
  }

  window.addEventListener("hashchange", syncHistoryTab);
  if (window.location.hash === "#history") {
    syncHistoryTab();
  }
  var historyTabBtn = $('nav.tabs a[href*="#history"]');
  if (historyTabBtn) {
    historyTabBtn.addEventListener("click", function () {
      setTimeout(syncHistoryTab, 10);
    });
  }

  /* --- Numeral formatting helper --- */
  function formatNum(num, lang) {
    if (num === null || num === undefined || isNaN(num)) return "--";
    var s = String(num);
    if (lang === "bn") {
      var bnDigits = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];
      return s.replace(/[0-9]/g, function (d) {
        return bnDigits[parseInt(d, 10)];
      });
    }
    return s;
  }

  /* --- Sampling Plan Interactive Controller --- */
  function initPlanPage() {
    var form = $("#planForm");
    if (!form) return;
    var previewCard = $("#planPreviewCard");

    var errorSummary = $("#errorSummary");
    if (errorSummary) {
      errorSummary.focus();
    }

    var lotSize = parseInt(previewCard ? previewCard.getAttribute("data-lotsize") : 0, 10) || 0;
    var unitsPresent = parseInt(previewCard ? previewCard.getAttribute("data-units-present") : 0, 10) || 0;
    var nonvisualStatus = previewCard ? previewCard.getAttribute("data-nonvisual-status") : "pending";
    var critDefects = parseInt(previewCard ? previewCard.getAttribute("data-crit-defects") : 0, 10) || 0;
    var majDefects = parseInt(previewCard ? previewCard.getAttribute("data-maj-defects") : 0, 10) || 0;
    var minDefects = parseInt(previewCard ? previewCard.getAttribute("data-min-defects") : 0, 10) || 0;
    var lang = (previewCard ? previewCard.getAttribute("data-lang") : "bn") || "bn";

    var nInput = $("#plan-n");
    var modeSelect = $("#plan-mode");
    var sourceEditionInput = $("#source_edition");
    var sourceRefInput = $("#source_reference");
    var unreferencedNotice = $("#unreferencedNotice");
    var isDemoInput = $("#is_demo");
    var confirmedCheck = $("#confirmed");
    var btnDemoPreset = $("#btnDemoPreset");

    function updateModeDescription() {
      if (!modeSelect) return;
      var val = modeSelect.value;
      var descHighest = $("#desc-highest_class_only");
      var descEvery = $("#desc-every_class");
      if (descHighest) descHighest.style.display = val === "highest_class_only" ? "block" : "none";
      if (descEvery) descEvery.style.display = val === "every_class" ? "block" : "none";
    }
    if (modeSelect) {
      modeSelect.addEventListener("change", function () {
        updateModeDescription();
        updatePreview();
      });
    }

    function updateSourceNotice() {
      if (!unreferencedNotice) return;
      var edition = sourceEditionInput ? sourceEditionInput.value.trim() : "";
      var ref = sourceRefInput ? sourceRefInput.value.trim() : "";
      if (!edition && !ref) {
        unreferencedNotice.style.display = "flex";
      } else {
        unreferencedNotice.style.display = "none";
      }
    }
    if (sourceEditionInput) {
      sourceEditionInput.addEventListener("input", function () {
        if (isDemoInput && isDemoInput.value === "1") {
          isDemoInput.value = "0";
        }
        updateSourceNotice();
        updatePreview();
      });
    }
    if (sourceRefInput) {
      sourceRefInput.addEventListener("input", function () {
        updateSourceNotice();
        updatePreview();
      });
    }

    ["critical", "major", "minor"].forEach(function (c) {
      var acInput = $("#" + c + "_ac");
      var reInput = $("#" + c + "_re");

      if (acInput && reInput) {
        acInput.addEventListener("input", function () {
          var acVal = parseInt(acInput.value, 10);
          if (!isNaN(acVal) && acVal >= 0) {
            reInput.value = acVal + 1;
          }
          checkReInvariant(c);
          updatePreview();
        });

        reInput.addEventListener("input", function () {
          checkReInvariant(c);
          updatePreview();
        });
      }
    });

    function checkReInvariant(c) {
      var acInput = $("#" + c + "_ac");
      var reInput = $("#" + c + "_re");
      var warnBox = $("#" + c + "_warning");
      if (!acInput || !reInput || !warnBox) return true;

      var acVal = parseInt(acInput.value, 10);
      var reVal = parseInt(reInput.value, 10);

      if (!isNaN(acVal) && !isNaN(reVal)) {
        if (reVal !== acVal + 1) {
          warnBox.textContent = lang === "bn"
            ? "সতর্কতা: সিঙ্গেল স্যাম্পলিংয়ে Re = Ac + 1 হতে হবে (প্রত্যাশিত Re=" + formatNum(acVal + 1, lang) + ")"
            : "Warning: Single sampling requires Re = Ac + 1 (expected Re=" + (acVal + 1) + ")";
          warnBox.style.display = "block";
          reInput.classList.add("is-invalid");
          return false;
        } else {
          warnBox.style.display = "none";
          warnBox.textContent = "";
          reInput.classList.remove("is-invalid");
          return true;
        }
      }
      return false;
    }

    if (btnDemoPreset) {
      btnDemoPreset.addEventListener("click", function () {
        var presetN = Math.min(8, lotSize || 8);
        if (nInput) nInput.value = presetN;
        if (modeSelect) modeSelect.value = "highest_class_only";

        var critAql = $("#critical_aql");
        var critAc = $("#critical_ac");
        var critRe = $("#critical_re");
        if (critAql) critAql.value = "0.0";
        if (critAc) critAc.value = "0";
        if (critRe) critRe.value = "1";

        var majAql = $("#major_aql");
        var majAc = $("#major_ac");
        var majRe = $("#major_re");
        if (majAql) majAql.value = "2.5";
        if (majAc) majAc.value = "1";
        if (majRe) majRe.value = "2";

        var minAql = $("#minor_aql");
        var minAc = $("#minor_ac");
        var minRe = $("#minor_re");
        if (minAql) minAql.value = "4.0";
        if (minAc) minAc.value = "2";
        if (minRe) minRe.value = "3";

        if (sourceEditionInput) {
          sourceEditionInput.value = lang === "bn" ? "অননুমোদিত ডেমো অনুমান" : "Unauthorized demo assumption";
        }
        if (sourceRefInput) {
          sourceRefInput.value = lang === "bn"
            ? "ডেমো টেস্টিং প্রিসেট — কোনো স্ট্যান্ডার্ড থেকে নেওয়া নয়"
            : "Demo testing preset — not from a standard";
        }
        if (isDemoInput) isDemoInput.value = "1";
        if (confirmedCheck) confirmedCheck.checked = true;

        ["critical", "major", "minor"].forEach(checkReInvariant);
        updateModeDescription();
        updateSourceNotice();
        updatePreview();

        if (window.LotlineUI && window.LotlineUI.toast) {
          window.LotlineUI.toast(
            lang === "bn"
              ? "ডেমো প্রিসেট লোড হয়েছে (অননুমোদিত ডেমো অনুমান)"
              : "Demo preset loaded (unauthorized demo assumption)",
            "info"
          );
        }
      });
    }

    function updatePreview() {
      if (!previewCard) return;

      var nVal = nInput ? parseInt(nInput.value, 10) : 0;
      var coverageEl = $("#previewCoverage");
      var coverageBar = $("#previewCoverageBar");
      var coverageHint = $("#previewCoverageHint");
      var validationBadge = $("#previewValidationBadge");

      var critAc = $("#critical_ac") ? parseInt($("#critical_ac").value, 10) : NaN;
      var critRe = $("#critical_re") ? parseInt($("#critical_re").value, 10) : NaN;
      var majAc = $("#major_ac") ? parseInt($("#major_ac").value, 10) : NaN;
      var majRe = $("#major_re") ? parseInt($("#major_re").value, 10) : NaN;
      var minAc = $("#minor_ac") ? parseInt($("#minor_ac").value, 10) : NaN;
      var minRe = $("#minor_re") ? parseInt($("#minor_re").value, 10) : NaN;

      var previewCrit = $("#previewCrit");
      var previewMaj = $("#previewMaj");
      var previewMin = $("#previewMin");
      var previewMode = $("#previewMode");
      var previewSourceLabel = $("#previewSourceLabel");

      var forecastBox = $("#previewForecastBox");
      var forecastTitle = $("#previewForecastTitle");
      var forecastDesc = $("#previewForecastDesc");

      if (!isNaN(nVal) && nVal > 0 && lotSize > 0) {
        var pct = Math.min(100, Math.round((nVal / lotSize) * 100));
        if (coverageEl) {
          coverageEl.textContent = formatNum(nVal, lang) + " / " + formatNum(lotSize, lang) + " (" + formatNum(pct, lang) + "%)";
        }
        if (coverageBar) {
          coverageBar.style.width = pct + "%";
          if (nVal >= lotSize) {
            coverageBar.classList.add("is-100");
          } else {
            coverageBar.classList.remove("is-100");
          }
        }
        if (coverageHint) {
          if (nVal >= lotSize) {
            coverageHint.textContent = lang === "bn"
              ? "সতর্কতা: ১০০% সম্পূর্ণ পরিদর্শন নির্বাচন করা হয়েছে"
              : "Warning: 100% full inspection selected";
            coverageHint.className = "small text-warning mt-1 bold";
          } else {
            coverageHint.textContent = lang === "bn"
              ? "লটের আকার " + formatNum(lotSize, lang) + " ইউনিটের মধ্যে " + formatNum(nVal, lang) + " ইউনিটের নমুনা"
              : "Sample of " + nVal + " garments from lot size " + lotSize;
            coverageHint.className = "small dim mt-1";
          }
        }
      } else {
        if (coverageEl) coverageEl.textContent = "--";
        if (coverageBar) coverageBar.style.width = "0%";
      }

      if (previewCrit) {
        previewCrit.textContent = (!isNaN(critAc) && !isNaN(critRe))
          ? "Ac: " + formatNum(critAc, lang) + " / Re: " + formatNum(critRe, lang)
          : "--";
      }
      if (previewMaj) {
        previewMaj.textContent = (!isNaN(majAc) && !isNaN(majRe))
          ? "Ac: " + formatNum(majAc, lang) + " / Re: " + formatNum(majRe, lang)
          : "--";
      }
      if (previewMin) {
        previewMin.textContent = (!isNaN(minAc) && !isNaN(minRe))
          ? "Ac: " + formatNum(minAc, lang) + " / Re: " + formatNum(minRe, lang)
          : "--";
      }

      if (previewMode && modeSelect) {
        previewMode.textContent = modeSelect.value === "highest_class_only"
          ? (lang === "bn" ? "সর্বোচ্চ শ্রেণি গণনা" : "Highest class only")
          : (lang === "bn" ? "প্রতিটি শ্রেণি গণনা" : "Every class");
      }

      if (previewSourceLabel) {
        var isDemo = isDemoInput && isDemoInput.value === "1";
        var edition = sourceEditionInput ? sourceEditionInput.value.trim() : "";
        var ref = sourceRefInput ? sourceRefInput.value.trim() : "";
        if (isDemo) {
          previewSourceLabel.textContent = lang === "bn" ? "অননুমোদিত ডেমো অনুমান" : "Unauthorized demo assumption";
          previewSourceLabel.className = "badge badge-warning ms-1";
        } else if (edition || ref) {
          previewSourceLabel.textContent = edition || ref;
          previewSourceLabel.className = "badge badge-neutral ms-1";
        } else {
          previewSourceLabel.textContent = lang === "bn" ? "অননুমোদিত অনুমান" : "Unauthorized assumption";
          previewSourceLabel.className = "badge badge-neutral ms-1";
        }
      }

      var isValid = (
        !isNaN(nVal) && nVal >= 1 && nVal <= lotSize &&
        !isNaN(critAc) && critAc >= 0 && !isNaN(critRe) && critRe === critAc + 1 &&
        !isNaN(majAc) && majAc >= 0 && !isNaN(majRe) && majRe === majAc + 1 &&
        !isNaN(minAc) && minAc >= 0 && !isNaN(minRe) && minRe === minAc + 1
      );

      if (validationBadge) {
        if (isValid) {
          validationBadge.className = "badge badge-success";
          validationBadge.textContent = lang === "bn" ? "বৈধ সিঙ্গেল-স্যাম্পলিং" : "Valid single sampling";
        } else {
          validationBadge.className = "badge badge-danger";
          validationBadge.textContent = lang === "bn" ? "অবৈধ / অসম্পূর্ণ" : "Invalid / incomplete";
        }
      }

      if (forecastBox && forecastTitle && forecastDesc) {
        forecastBox.className = "preview-forecast-box p-3 rounded";
        if (!isValid) {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (প্ল্যান অসম্পূর্ণ)" : "HOLD Forecast (Invalid Plan)";
          forecastDesc.textContent = lang === "bn"
            ? "প্ল্যানের মান অসম্পূর্ণ বা সিঙ্গেল স্যাম্পলিং নিয়মের বাইরে থাকলে সিদ্ধান্ত গণনা HOLD_PLAN_INVALID রিটার্ন করবে।"
            : "Missing or invalid plan values will cause the decision engine to return HOLD_PLAN_INVALID.";
        } else if (unitsPresent === 0) {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (প্রমাণ নেই)" : "HOLD Forecast (No Evidence)";
          forecastDesc.textContent = lang === "bn"
            ? "০ গার্মেন্ট নিবন্ধিত — সংরক্ষণের পরও HOLD থাকবে: প্রমাণ নেই (HOLD_UNITS_MISSING)।"
            : "0 garments registered — will remain HOLD after saving: no evidence (HOLD_UNITS_MISSING).";
        } else if (unitsPresent < nVal) {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (নমুনা অপূর্ণ)" : "HOLD Forecast (Incomplete Sample)";
          forecastDesc.textContent = lang === "bn"
            ? "নমুনা সম্পূর্ণ নয় (" + formatNum(unitsPresent, lang) + "/" + formatNum(nVal, lang) + " গার্মেন্ট) — সিদ্ধান্ত HOLD_UNITS_MISSING থাকবে।"
            : "Sample incomplete (" + unitsPresent + "/" + nVal + " garments) — decision will remain HOLD_UNITS_MISSING.";
        } else if (nonvisualStatus === "failed") {
          forecastBox.classList.add("forecast-reject");
          forecastTitle.textContent = lang === "bn" ? "REJECT পূর্বাভাস (নন-ভিজুয়াল ব্যর্থ)" : "REJECT Forecast (Non-visual Failed)";
          forecastDesc.textContent = lang === "bn"
            ? "ক্রিটিক্যাল নন-ভিজুয়াল চেক ব্যর্থ হিসেবে রেকর্ড করা আছে — সিদ্ধান্ত REJECT হবে।"
            : "Critical non-visual check recorded as failed — decision will be REJECT.";
        } else if (nonvisualStatus === "pending") {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (নন-ভিজুয়াল বাকি)" : "HOLD Forecast (Non-visual Pending)";
          forecastDesc.textContent = lang === "bn"
            ? "ক্রিটিক্যাল নন-ভিজুয়াল চেক এখনো সম্পন্ন হয়নি — সিদ্ধান্ত HOLD থাকবে।"
            : "Critical non-visual check is pending — decision will remain HOLD.";
        } else if (
          (!isNaN(critRe) && critDefects >= critRe) ||
          (!isNaN(majRe) && majDefects >= majRe) ||
          (!isNaN(minRe) && minDefects >= minRe)
        ) {
          forecastBox.classList.add("forecast-reject");
          forecastTitle.textContent = lang === "bn" ? "REJECT পূর্বাভাস (ত্রুটি সীমা অতিক্রম)" : "REJECT Forecast (Limit Exceeded)";
          forecastDesc.textContent = lang === "bn"
            ? "নিশ্চিত ত্রুটির সংখ্যা প্রত্যাখ্যান সীমা (Re) ছুঁয়েছে বা অতিক্রম করেছে — সিদ্ধান্ত REJECT হবে।"
            : "Confirmed defect counts reached or exceeded rejection limit (Re) — decision will be REJECT.";
        } else {
          forecastBox.classList.add("forecast-accept");
          forecastTitle.textContent = lang === "bn" ? "ACCEPT পূর্বাভাস (শর্ত পূরণ)" : "ACCEPT Forecast (Criteria Met)";
          forecastDesc.textContent = lang === "bn"
            ? "বর্তমান প্রমাণের ভিত্তিতে সমস্ত শ্রেণি গ্রহণযোগ্য সীমার (Ac) মধ্যে রয়েছে — সিদ্ধান্ত ACCEPT হওয়ার উপযুক্ত।"
            : "Based on current evidence, all classes are within acceptance limit (Ac) — eligible for ACCEPT.";
        }
      }
    }

    if (nInput) {
      nInput.addEventListener("input", updatePreview);
    }

    updateModeDescription();
    updateSourceNotice();
    ["critical", "major", "minor"].forEach(checkReInvariant);
    updatePreview();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPlanPage);
  } else {
    initPlanPage();
  }

  window.LotlineUI = { toast: showToast, openDialog: openDialog };
})();
