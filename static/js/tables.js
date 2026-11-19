/* Progressive data table: filter, sort and paginate in the DOM.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
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
  });
})();
