/* Form guards: password reveal, clipboard, lot code, override, plan invariant.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
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
  });
})();
