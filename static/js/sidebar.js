/* Sidebar: desktop collapse and the mobile drawer.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
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
  });
})();
