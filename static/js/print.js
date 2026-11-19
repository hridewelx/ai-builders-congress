/* Print button.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
  /* ----------------------------------------------------------------
     Print
  ---------------------------------------------------------------- */
  $$("[data-print]").forEach(function (button) {
    button.addEventListener("click", function () { window.print(); });
  });
  });
})();
