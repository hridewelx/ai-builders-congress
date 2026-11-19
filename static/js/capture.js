/* Capture: unit jumper and side filter.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
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
  });
})();
