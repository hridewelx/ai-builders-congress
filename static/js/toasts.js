/* Toasts: show, auto-hide and close.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
  var $ = api.$;
  var $$ = api.$$;
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
  api.toast = showToast;
  });
})();
