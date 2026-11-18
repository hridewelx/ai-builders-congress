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
     Existing review workspace: box <-> proposal, heat map, manual box
  ---------------------------------------------------------------- */
  var viewer = document.getElementById("viewer");
  var mainImage = document.getElementById("mainImage");
  var heatToggle = document.getElementById("heatToggle");
  var pending = document.getElementById("pendingBox");
  var cx = document.getElementById("cx");
  var cy = document.getElementById("cy");

  if (heatToggle && mainImage) {
    var heatOn = false;
    heatToggle.addEventListener("click", function () {
      heatOn = !heatOn;
      mainImage.src = heatOn ? mainImage.dataset.heat : mainImage.src.replace("/heat", "");
      heatToggle.textContent = heatOn ? "Show photo" : "Show attention map";
    });
  }

  $$(".box[data-pid]").forEach(function (box) {
    box.addEventListener("click", function () {
      var id = box.dataset.pid;
      $$(".box").forEach(function (b) { b.classList.remove("sel"); });
      box.classList.add("sel");
      var prop = document.getElementById("prop-" + id);
      if (prop) {
        prop.classList.add("sel");
        prop.scrollIntoView({ behavior: "smooth", block: "center" });
        var d = prop.querySelector("details");
        if (d) d.open = true;
      }
    });
  });

  $$(".prop[data-pid]").forEach(function (prop) {
    var box = document.querySelector('.box[data-pid="' + prop.dataset.pid + '"]');
    if (!box) return;
    prop.addEventListener("mouseenter", function () { box.classList.add("sel"); });
    prop.addEventListener("mouseleave", function () { box.classList.remove("sel"); });
  });

  if (viewer && pending && cx && cy) {
    viewer.addEventListener("click", function (event) {
      if (event.target.closest(".box[data-pid]")) return;
      var rect = viewer.getBoundingClientRect();
      var x = Math.min(0.95, Math.max(0.05, (event.clientX - rect.left) / rect.width));
      var y = Math.min(0.95, Math.max(0.05, (event.clientY - rect.top) / rect.height));
      cx.value = x.toFixed(4);
      cy.value = y.toFixed(4);
      pending.style.display = "block";
      pending.style.left = (x - 0.08) * 100 + "%";
      pending.style.top = (y - 0.08) * 100 + "%";
    });
  }

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

  window.LotlineUI = { toast: showToast, openDialog: openDialog };
})();
