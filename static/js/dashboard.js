/* Dashboard: instant lot filter, deep links, history tabs, numerals.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
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
  });
})();
