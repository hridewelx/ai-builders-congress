/* Review viewer: zoom, pan, attention map, box/proposal linking.
   Runs through the shared boot queue in /static/app.js, in file order. */
(function () {
  "use strict";
  window.LotlineBoot = window.LotlineBoot || [];
  window.LotlineBoot.push(function (api) {
    var $ = api.$, $$ = api.$$, showToast = api.toast;
  /* ----------------------------------------------------------------
     Review viewer: zoom, pan, heat toggle, box<->proposal linking
  ---------------------------------------------------------------- */
  var viewer = document.getElementById("viewer");
  var viewerScroll = document.getElementById("viewerScroll");
  var mainImage = document.getElementById("mainImage");
  var heatToggle = document.getElementById("heatToggle");
  var pending = document.getElementById("pendingBox");
  var cx = document.getElementById("cx");
  var cy = document.getElementById("cy");
  var zoomLevel = document.getElementById("zoomLevel");
  var boxLayer = document.getElementById("boxLayer");

  if (heatToggle && mainImage) {
    var heatOn = false;
    heatToggle.addEventListener("click", function () {
      heatOn = !heatOn;
      if (heatOn) {
        mainImage.dataset.originalSrc = mainImage.src;
        mainImage.src = mainImage.dataset.heat;
      } else if (mainImage.dataset.originalSrc) {
        mainImage.src = mainImage.dataset.originalSrc;
      }
      heatToggle.textContent = heatOn
        ? (heatToggle.getAttribute("data-show-photo") || "Show photo")
        : (heatToggle.getAttribute("data-show-heat") || "Show attention map");
    });
  }

  if (viewerScroll && mainImage) {
    var scale = 1, minScale = 1, maxScale = 4, panX = 0, panY = 0;
    var panning = false, startX = 0, startY = 0, baseX = 0, baseY = 0;
    var moved = false;

    function apply() {
      var transform = "translate(" + panX + "px," + panY + "px) scale(" + scale + ")";
      mainImage.style.transform = transform;
      if (boxLayer) {
        boxLayer.style.transform = transform;
        boxLayer.style.transformOrigin = "0 0";
      }
      if (zoomLevel) zoomLevel.textContent = Math.round(scale * 100) + "%";
    }
    function setScale(next, cxClient, cyClient) {
      var rect = viewerScroll.getBoundingClientRect();
      var px = (cxClient === undefined) ? rect.width / 2 : cxClient - rect.left;
      var py = (cyClient === undefined) ? rect.height / 2 : cyClient - rect.top;
      var newScale = Math.min(maxScale, Math.max(minScale, next));
      // keep the point under the cursor stable
      var ratio = newScale / scale;
      panX = px - (px - panX) * ratio;
      panY = py - (py - panY) * ratio;
      scale = newScale;
      if (scale <= minScale) { panX = 0; panY = 0; }
      apply();
    }
    function reset() { scale = 1; panX = 0; panY = 0; apply(); }

    $$("[data-zoom]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var dir = btn.getAttribute("data-zoom");
        if (dir === "in") setScale(scale * 1.25);
        else if (dir === "out") setScale(scale / 1.25);
        else reset();
      });
    });

    viewerScroll.addEventListener("wheel", function (event) {
      if (!event.ctrlKey && Math.abs(event.deltaY) < 2) return;
      event.preventDefault();
      setScale(scale * (event.deltaY < 0 ? 1.12 : 0.89), event.clientX, event.clientY);
    }, { passive: false });

    viewerScroll.addEventListener("pointerdown", function (event) {
      if (event.button !== 0) return;
      panning = true; moved = false;
      startX = event.clientX; startY = event.clientY; baseX = panX; baseY = panY;
      viewerScroll.classList.add("is-panning");
      viewerScroll.setPointerCapture(event.pointerId);
    });
    viewerScroll.addEventListener("pointermove", function (event) {
      if (!panning) return;
      var dx = event.clientX - startX, dy = event.clientY - startY;
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      panX = baseX + dx; panY = baseY + dy; apply();
    });
    viewerScroll.addEventListener("pointerup", function (event) {
      panning = false;
      viewerScroll.classList.remove("is-panning");
      try { viewerScroll.releasePointerCapture(event.pointerId); } catch (e) {}
    });

    document.addEventListener("keydown", function (event) {
      var tag = (event.target && event.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (event.key === "+" || event.key === "=") { setScale(scale * 1.25); event.preventDefault(); }
      else if (event.key === "-" || event.key === "_") { setScale(scale / 1.25); event.preventDefault(); }
      else if (event.key === "0") { reset(); event.preventDefault(); }
      else if (event.key === "c" || event.key === "C") {
        var selProp = $(".prop.sel") || $(".prop");
        if (selProp) {
          var d = selProp.querySelector("details");
          if (d) { d.open = true; var inp = d.querySelector("select, input"); if (inp) inp.focus(); event.preventDefault(); }
        }
      } else if (event.key === "x" || event.key === "X" || event.key === "r" || event.key === "R") {
        var selPropR = $(".prop.sel") || $(".prop");
        if (selPropR) {
          var rejectBtn = selPropR.querySelector('form[action*="/reject"] button');
          if (rejectBtn) { rejectBtn.focus(); event.preventDefault(); }
        }
      } else if (event.key === "]" || event.key === "n" || event.key === "N") {
        var nextLink = $('a[href*="/review/"][class*="primary"]');
        if (nextLink) { nextLink.click(); event.preventDefault(); }
      } else if (event.key === "[") {
        var queueLink = $('a[href*="/review"][class*="ghost"]');
        if (queueLink) { queueLink.click(); event.preventDefault(); }
      }
    });

    // click to place a manual box (only when not panning and not zoomed far)
    viewerScroll.addEventListener("click", function (event) {
      if (moved) { moved = false; return; }
      if (event.target.closest(".box[data-pid]")) return;
      if (!pending || !cx || !cy) return;
      var rect = mainImage.getBoundingClientRect();
      var x = (event.clientX - rect.left) / rect.width;
      var y = (event.clientY - rect.top) / rect.height;
      if (x < 0 || x > 1 || y < 0 || y > 1) return;
      cx.value = Math.min(0.98, Math.max(0.02, x)).toFixed(4);
      cy.value = Math.min(0.98, Math.max(0.02, y)).toFixed(4);
      pending.style.display = "block";
      pending.style.left = (x * 100) + "%";
      pending.style.top = (y * 100) + "%";

      var manualCard = document.getElementById("manualAddCard");
      if (manualCard) {
        manualCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        var addType = document.getElementById("add-type");
        if (addType) addType.focus();
      }
    });
  }

  $$(".box[data-pid]").forEach(function (box) {
    box.addEventListener("click", function () {
      var id = box.dataset.pid;
      $$(".box").forEach(function (b) { b.classList.remove("sel"); });
      box.classList.add("sel");
      var prop = document.getElementById("prop-" + id);
      if (prop) {
        $$(".prop").forEach(function (p) { p.classList.remove("sel"); });
        prop.classList.add("sel");
        prop.scrollIntoView({ behavior: "smooth", block: "center" });
        var d = prop.querySelector("details");
        if (d) d.open = true;
      }
    });
  });

  $$(".prop[data-pid]").forEach(function (prop) {
    prop.addEventListener("mouseenter", function () {
      var box = document.querySelector('.box[data-pid="' + prop.dataset.pid + '"]');
      if (box) box.classList.add("sel");
    });
    prop.addEventListener("mouseleave", function () {
      var box = document.querySelector('.box[data-pid="' + prop.dataset.pid + '"]');
      if (box) box.classList.remove("sel");
    });
  });
  });
})();
