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
      setDrawer(!document.body.classList.contains("drawer-open"));
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
     Dialogs
  ---------------------------------------------------------------- */
  function openDialog(id) {
    var dialog = document.getElementById(id);
    if (!dialog) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    var focusable = dialog.querySelector("input, select, textarea, button");
    if (focusable) focusable.focus();
  }
  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }
  $$("[data-dialog-open]").forEach(function (trigger) {
    trigger.addEventListener("click", function () { openDialog(trigger.getAttribute("data-dialog-open")); });
  });
  $$("[data-dialog-close]").forEach(function (trigger) {
    trigger.addEventListener("click", function () { closeDialog(trigger.closest("dialog")); });
  });
  $$("dialog").forEach(function (dialog) {
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) closeDialog(dialog);
    });
    dialog.addEventListener("close", function () {
      var opener = document.querySelector('[data-dialog-open="' + dialog.id + '"]');
      if (opener) opener.focus();
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
     Upload validation: JPEG/PNG + 15 MB, HEIC hint, busy state
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
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) { result.textContent = ""; result.className = "upload-result"; return; }
      var name = (file.name || "").toLowerCase();
      var type = (file.type || "").toLowerCase();
      var isJpeg = /\.jpe?g$/.test(name) || type === "image/jpeg";
      var isPng = /\.png$/.test(name) || type === "image/png";
      var isHeic = /\.heic$|\.heif$/.test(name) || type === "image/heic" || type === "image/heif";
      if (isHeic) { setMsg("HEIC is not accepted. Export as JPEG or PNG.", "error"); input.value = ""; return; }
      if (!isJpeg && !isPng) { setMsg("Only JPEG and PNG photos are accepted.", "error"); input.value = ""; return; }
      if (file.size > maxBytes) { setMsg("File is larger than 15 MB.", "error"); input.value = ""; return; }
      setMsg((file.size / (1024 * 1024)).toFixed(1) + " MB · ready to upload", "ok");
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
      // if the server rejects, the redirect reloads the page and the chip is lost; this is honest progress only
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
     Decision & Plan: Character counter & Re = Ac + 1 helper
  ---------------------------------------------------------------- */
  var reasonInput = document.getElementById("override-reason");
  var charCounter = document.getElementById("charCounter");
  if (reasonInput && charCounter) {
    reasonInput.addEventListener("input", function () {
      var len = reasonInput.value.length;
      charCounter.textContent = len + " / 20 minimum";
      charCounter.style.color = len >= 20 ? "var(--green)" : "var(--muted)";
    });
  }

  $$(".ac-input").forEach(function (acInput) {
    acInput.addEventListener("input", function () {
      var c = acInput.getAttribute("data-class");
      var reInput = document.getElementById(c + "_re");
      var acVal = parseInt(acInput.value, 10);
      if (!isNaN(acVal) && reInput) {
        reInput.value = acVal + 1;
      }
    });
  });

  /* ----------------------------------------------------------------
     Dashboard: Instant Lot Filter & Search
  ---------------------------------------------------------------- */
  var lotSearchInput = document.getElementById("lotSearchInput");
  var filterTabs = $$(".filter-pills .pill-btn");
  var lotCards = $$("[data-lot-card]");
  var lotEmptyMatch = document.getElementById("lotEmptyMatch");

  function filterDashboardLots() {
    var q = lotSearchInput ? lotSearchInput.value.trim().toLowerCase() : "";
    var activeTab = document.querySelector(".filter-pills .pill-btn.on");
    var tabFilter = activeTab ? activeTab.getAttribute("data-filter-tab") : "all";

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
  }

  if (lotSearchInput) {
    lotSearchInput.addEventListener("input", filterDashboardLots);
  }
  if (filterTabs.length) {
    filterTabs.forEach(function (btn) {
      btn.addEventListener("click", function () {
        filterTabs.forEach(function (b) { b.classList.remove("on"); });
        btn.classList.add("on");
        filterDashboardLots();
      });
    });
  }

  window.LotlineUI = { toast: showToast, openDialog: openDialog };
})();
