/* Native <dialog>: focus trap, trigger return and confirm forms.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
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

  api.openDialog = openDialog;
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
  });
})();
