/* Sampling plan controller: preview, coverage and Re = Ac + 1 checks.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
  /* --- Numeral formatting helper --- */
  function formatNum(num, lang) {
    if (num === null || num === undefined || isNaN(num)) return "--";
    var s = String(num);
    if (lang === "bn") {
      var bnDigits = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];
      return s.replace(/[0-9]/g, function (d) {
        return bnDigits[parseInt(d, 10)];
      });
    }
    return s;
  }

  /* --- Sampling Plan Interactive Controller --- */
  function initPlanPage() {
    var form = $("#planForm");
    if (!form) return;
    var previewCard = $("#planPreviewCard");

    var errorSummary = $("#errorSummary");
    if (errorSummary) {
      errorSummary.focus();
    }

    var lotSize = parseInt(previewCard ? previewCard.getAttribute("data-lotsize") : 0, 10) || 0;
    var unitsPresent = parseInt(previewCard ? previewCard.getAttribute("data-units-present") : 0, 10) || 0;
    var nonvisualStatus = previewCard ? previewCard.getAttribute("data-nonvisual-status") : "pending";
    var critDefects = parseInt(previewCard ? previewCard.getAttribute("data-crit-defects") : 0, 10) || 0;
    var majDefects = parseInt(previewCard ? previewCard.getAttribute("data-maj-defects") : 0, 10) || 0;
    var minDefects = parseInt(previewCard ? previewCard.getAttribute("data-min-defects") : 0, 10) || 0;
    var lang = (previewCard ? previewCard.getAttribute("data-lang") : "bn") || "bn";

    var nInput = $("#plan-n");
    var modeSelect = $("#plan-mode");
    var sourceEditionInput = $("#source_edition");
    var sourceRefInput = $("#source_reference");
    var unreferencedNotice = $("#unreferencedNotice");
    var isDemoInput = $("#is_demo");
    var confirmedCheck = $("#confirmed");
    var btnDemoPreset = $("#btnDemoPreset");

    function updateModeDescription() {
      if (!modeSelect) return;
      var val = modeSelect.value;
      var descHighest = $("#desc-highest_class_only");
      var descEvery = $("#desc-every_class");
      if (descHighest) descHighest.style.display = val === "highest_class_only" ? "block" : "none";
      if (descEvery) descEvery.style.display = val === "every_class" ? "block" : "none";
    }
    if (modeSelect) {
      modeSelect.addEventListener("change", function () {
        updateModeDescription();
        updatePreview();
      });
    }

    function updateSourceNotice() {
      if (!unreferencedNotice) return;
      var edition = sourceEditionInput ? sourceEditionInput.value.trim() : "";
      var ref = sourceRefInput ? sourceRefInput.value.trim() : "";
      if (!edition && !ref) {
        unreferencedNotice.style.display = "flex";
      } else {
        unreferencedNotice.style.display = "none";
      }
    }
    if (sourceEditionInput) {
      sourceEditionInput.addEventListener("input", function () {
        if (isDemoInput && isDemoInput.value === "1") {
          isDemoInput.value = "0";
        }
        updateSourceNotice();
        updatePreview();
      });
    }
    if (sourceRefInput) {
      sourceRefInput.addEventListener("input", function () {
        updateSourceNotice();
        updatePreview();
      });
    }

    ["critical", "major", "minor"].forEach(function (c) {
      var acInput = $("#" + c + "_ac");
      var reInput = $("#" + c + "_re");

      if (acInput && reInput) {
        acInput.addEventListener("input", function () {
          var acVal = parseInt(acInput.value, 10);
          if (!isNaN(acVal) && acVal >= 0) {
            reInput.value = acVal + 1;
          }
          checkReInvariant(c);
          updatePreview();
        });

        reInput.addEventListener("input", function () {
          checkReInvariant(c);
          updatePreview();
        });
      }
    });

    function checkReInvariant(c) {
      var acInput = $("#" + c + "_ac");
      var reInput = $("#" + c + "_re");
      var warnBox = $("#" + c + "_warning");
      if (!acInput || !reInput || !warnBox) return true;

      var acVal = parseInt(acInput.value, 10);
      var reVal = parseInt(reInput.value, 10);

      if (!isNaN(acVal) && !isNaN(reVal)) {
        if (reVal !== acVal + 1) {
          warnBox.textContent = lang === "bn"
            ? "সতর্কতা: সিঙ্গেল স্যাম্পলিংয়ে Re = Ac + 1 হতে হবে (প্রত্যাশিত Re=" + formatNum(acVal + 1, lang) + ")"
            : "Warning: Single sampling requires Re = Ac + 1 (expected Re=" + (acVal + 1) + ")";
          warnBox.style.display = "block";
          reInput.classList.add("is-invalid");
          return false;
        } else {
          warnBox.style.display = "none";
          warnBox.textContent = "";
          reInput.classList.remove("is-invalid");
          return true;
        }
      }
      return false;
    }

    if (btnDemoPreset) {
      btnDemoPreset.addEventListener("click", function () {
        var presetN = Math.min(8, lotSize || 8);
        if (nInput) nInput.value = presetN;
        if (modeSelect) modeSelect.value = "highest_class_only";

        var critAql = $("#critical_aql");
        var critAc = $("#critical_ac");
        var critRe = $("#critical_re");
        if (critAql) critAql.value = "0.0";
        if (critAc) critAc.value = "0";
        if (critRe) critRe.value = "1";

        var majAql = $("#major_aql");
        var majAc = $("#major_ac");
        var majRe = $("#major_re");
        if (majAql) majAql.value = "2.5";
        if (majAc) majAc.value = "1";
        if (majRe) majRe.value = "2";

        var minAql = $("#minor_aql");
        var minAc = $("#minor_ac");
        var minRe = $("#minor_re");
        if (minAql) minAql.value = "4.0";
        if (minAc) minAc.value = "2";
        if (minRe) minRe.value = "3";

        if (sourceEditionInput) {
          sourceEditionInput.value = lang === "bn" ? "অননুমোদিত ডেমো অনুমান" : "Unauthorized demo assumption";
        }
        if (sourceRefInput) {
          sourceRefInput.value = lang === "bn"
            ? "ডেমো টেস্টিং প্রিসেট — কোনো স্ট্যান্ডার্ড থেকে নেওয়া নয়"
            : "Demo testing preset — not from a standard";
        }
        if (isDemoInput) isDemoInput.value = "1";
        if (confirmedCheck) confirmedCheck.checked = true;

        ["critical", "major", "minor"].forEach(checkReInvariant);
        updateModeDescription();
        updateSourceNotice();
        updatePreview();

        if (window.LotlineUI && window.LotlineUI.toast) {
          window.LotlineUI.toast(
            lang === "bn"
              ? "ডেমো প্রিসেট লোড হয়েছে (অননুমোদিত ডেমো অনুমান)"
              : "Demo preset loaded (unauthorized demo assumption)",
            "info"
          );
        }
      });
    }

    function updatePreview() {
      if (!previewCard) return;

      var nVal = nInput ? parseInt(nInput.value, 10) : 0;
      var coverageEl = $("#previewCoverage");
      var coverageBar = $("#previewCoverageBar");
      var coverageHint = $("#previewCoverageHint");
      var validationBadge = $("#previewValidationBadge");

      var critAc = $("#critical_ac") ? parseInt($("#critical_ac").value, 10) : NaN;
      var critRe = $("#critical_re") ? parseInt($("#critical_re").value, 10) : NaN;
      var majAc = $("#major_ac") ? parseInt($("#major_ac").value, 10) : NaN;
      var majRe = $("#major_re") ? parseInt($("#major_re").value, 10) : NaN;
      var minAc = $("#minor_ac") ? parseInt($("#minor_ac").value, 10) : NaN;
      var minRe = $("#minor_re") ? parseInt($("#minor_re").value, 10) : NaN;

      var previewCrit = $("#previewCrit");
      var previewMaj = $("#previewMaj");
      var previewMin = $("#previewMin");
      var previewMode = $("#previewMode");
      var previewSourceLabel = $("#previewSourceLabel");

      var forecastBox = $("#previewForecastBox");
      var forecastTitle = $("#previewForecastTitle");
      var forecastDesc = $("#previewForecastDesc");

      if (!isNaN(nVal) && nVal > 0 && lotSize > 0) {
        var pct = Math.min(100, Math.round((nVal / lotSize) * 100));
        if (coverageEl) {
          coverageEl.textContent = formatNum(nVal, lang) + " / " + formatNum(lotSize, lang) + " (" + formatNum(pct, lang) + "%)";
        }
        if (coverageBar) {
          coverageBar.style.width = pct + "%";
          if (nVal >= lotSize) {
            coverageBar.classList.add("is-100");
          } else {
            coverageBar.classList.remove("is-100");
          }
        }
        if (coverageHint) {
          if (nVal >= lotSize) {
            coverageHint.textContent = lang === "bn"
              ? "সতর্কতা: ১০০% সম্পূর্ণ পরিদর্শন নির্বাচন করা হয়েছে"
              : "Warning: 100% full inspection selected";
            coverageHint.className = "small text-warning mt-1 bold";
          } else {
            coverageHint.textContent = lang === "bn"
              ? "লটের আকার " + formatNum(lotSize, lang) + " ইউনিটের মধ্যে " + formatNum(nVal, lang) + " ইউনিটের নমুনা"
              : "Sample of " + nVal + " garments from lot size " + lotSize;
            coverageHint.className = "small dim mt-1";
          }
        }
      } else {
        if (coverageEl) coverageEl.textContent = "--";
        if (coverageBar) coverageBar.style.width = "0%";
      }

      if (previewCrit) {
        previewCrit.textContent = (!isNaN(critAc) && !isNaN(critRe))
          ? "Ac: " + formatNum(critAc, lang) + " / Re: " + formatNum(critRe, lang)
          : "--";
      }
      if (previewMaj) {
        previewMaj.textContent = (!isNaN(majAc) && !isNaN(majRe))
          ? "Ac: " + formatNum(majAc, lang) + " / Re: " + formatNum(majRe, lang)
          : "--";
      }
      if (previewMin) {
        previewMin.textContent = (!isNaN(minAc) && !isNaN(minRe))
          ? "Ac: " + formatNum(minAc, lang) + " / Re: " + formatNum(minRe, lang)
          : "--";
      }

      if (previewMode && modeSelect) {
        previewMode.textContent = modeSelect.value === "highest_class_only"
          ? (lang === "bn" ? "সর্বোচ্চ শ্রেণি গণনা" : "Highest class only")
          : (lang === "bn" ? "প্রতিটি শ্রেণি গণনা" : "Every class");
      }

      if (previewSourceLabel) {
        var isDemo = isDemoInput && isDemoInput.value === "1";
        var edition = sourceEditionInput ? sourceEditionInput.value.trim() : "";
        var ref = sourceRefInput ? sourceRefInput.value.trim() : "";
        if (isDemo) {
          previewSourceLabel.textContent = lang === "bn" ? "অননুমোদিত ডেমো অনুমান" : "Unauthorized demo assumption";
          previewSourceLabel.className = "badge badge-warning ms-1";
        } else if (edition || ref) {
          previewSourceLabel.textContent = edition || ref;
          previewSourceLabel.className = "badge badge-neutral ms-1";
        } else {
          previewSourceLabel.textContent = lang === "bn" ? "অননুমোদিত অনুমান" : "Unauthorized assumption";
          previewSourceLabel.className = "badge badge-neutral ms-1";
        }
      }

      var isValid = (
        !isNaN(nVal) && nVal >= 1 && nVal <= lotSize &&
        !isNaN(critAc) && critAc >= 0 && !isNaN(critRe) && critRe === critAc + 1 &&
        !isNaN(majAc) && majAc >= 0 && !isNaN(majRe) && majRe === majAc + 1 &&
        !isNaN(minAc) && minAc >= 0 && !isNaN(minRe) && minRe === minAc + 1
      );

      if (validationBadge) {
        if (isValid) {
          validationBadge.className = "badge badge-success";
          validationBadge.textContent = lang === "bn" ? "বৈধ সিঙ্গেল-স্যাম্পলিং" : "Valid single sampling";
        } else {
          validationBadge.className = "badge badge-danger";
          validationBadge.textContent = lang === "bn" ? "অবৈধ / অসম্পূর্ণ" : "Invalid / incomplete";
        }
      }

      if (forecastBox && forecastTitle && forecastDesc) {
        forecastBox.className = "preview-forecast-box p-3 rounded";
        if (!isValid) {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (প্ল্যান অসম্পূর্ণ)" : "HOLD Forecast (Invalid Plan)";
          forecastDesc.textContent = lang === "bn"
            ? "প্ল্যানের মান অসম্পূর্ণ বা সিঙ্গেল স্যাম্পলিং নিয়মের বাইরে থাকলে সিদ্ধান্ত গণনা HOLD_PLAN_INVALID রিটার্ন করবে।"
            : "Missing or invalid plan values will cause the decision engine to return HOLD_PLAN_INVALID.";
        } else if (unitsPresent === 0) {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (প্রমাণ নেই)" : "HOLD Forecast (No Evidence)";
          forecastDesc.textContent = lang === "bn"
            ? "০ গার্মেন্ট নিবন্ধিত — সংরক্ষণের পরও HOLD থাকবে: প্রমাণ নেই (HOLD_UNITS_MISSING)।"
            : "0 garments registered — will remain HOLD after saving: no evidence (HOLD_UNITS_MISSING).";
        } else if (unitsPresent < nVal) {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (নমুনা অপূর্ণ)" : "HOLD Forecast (Incomplete Sample)";
          forecastDesc.textContent = lang === "bn"
            ? "নমুনা সম্পূর্ণ নয় (" + formatNum(unitsPresent, lang) + "/" + formatNum(nVal, lang) + " গার্মেন্ট) — সিদ্ধান্ত HOLD_UNITS_MISSING থাকবে।"
            : "Sample incomplete (" + unitsPresent + "/" + nVal + " garments) — decision will remain HOLD_UNITS_MISSING.";
        } else if (nonvisualStatus === "failed") {
          forecastBox.classList.add("forecast-reject");
          forecastTitle.textContent = lang === "bn" ? "REJECT পূর্বাভাস (নন-ভিজুয়াল ব্যর্থ)" : "REJECT Forecast (Non-visual Failed)";
          forecastDesc.textContent = lang === "bn"
            ? "ক্রিটিক্যাল নন-ভিজুয়াল চেক ব্যর্থ হিসেবে রেকর্ড করা আছে — সিদ্ধান্ত REJECT হবে।"
            : "Critical non-visual check recorded as failed — decision will be REJECT.";
        } else if (nonvisualStatus === "pending") {
          forecastBox.classList.add("forecast-hold");
          forecastTitle.textContent = lang === "bn" ? "HOLD পূর্বাভাস (নন-ভিজুয়াল বাকি)" : "HOLD Forecast (Non-visual Pending)";
          forecastDesc.textContent = lang === "bn"
            ? "ক্রিটিক্যাল নন-ভিজুয়াল চেক এখনো সম্পন্ন হয়নি — সিদ্ধান্ত HOLD থাকবে।"
            : "Critical non-visual check is pending — decision will remain HOLD.";
        } else if (
          (!isNaN(critRe) && critDefects >= critRe) ||
          (!isNaN(majRe) && majDefects >= majRe) ||
          (!isNaN(minRe) && minDefects >= minRe)
        ) {
          forecastBox.classList.add("forecast-reject");
          forecastTitle.textContent = lang === "bn" ? "REJECT পূর্বাভাস (ত্রুটি সীমা অতিক্রম)" : "REJECT Forecast (Limit Exceeded)";
          forecastDesc.textContent = lang === "bn"
            ? "নিশ্চিত ত্রুটির সংখ্যা প্রত্যাখ্যান সীমা (Re) ছুঁয়েছে বা অতিক্রম করেছে — সিদ্ধান্ত REJECT হবে।"
            : "Confirmed defect counts reached or exceeded rejection limit (Re) — decision will be REJECT.";
        } else {
          forecastBox.classList.add("forecast-accept");
          forecastTitle.textContent = lang === "bn" ? "ACCEPT পূর্বাভাস (শর্ত পূরণ)" : "ACCEPT Forecast (Criteria Met)";
          forecastDesc.textContent = lang === "bn"
            ? "বর্তমান প্রমাণের ভিত্তিতে সমস্ত শ্রেণি গ্রহণযোগ্য সীমার (Ac) মধ্যে রয়েছে — সিদ্ধান্ত ACCEPT হওয়ার উপযুক্ত।"
            : "Based on current evidence, all classes are within acceptance limit (Ac) — eligible for ACCEPT.";
        }
      }
    }

    if (nInput) {
      nInput.addEventListener("input", updatePreview);
    }

    updateModeDescription();
    updateSourceNotice();
    ["critical", "major", "minor"].forEach(checkReInvariant);
    updatePreview();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPlanPage);
  } else {
    initPlanPage();
  }
  });
})();
