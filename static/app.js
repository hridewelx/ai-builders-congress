/* Lotline demo interactions: box <-> proposal linking, heat map, manual box placement. */
(function () {
  const viewer = document.getElementById("viewer");
  const mainImage = document.getElementById("mainImage");
  const heatToggle = document.getElementById("heatToggle");
  const pending = document.getElementById("pendingBox");
  const cx = document.getElementById("cx");
  const cy = document.getElementById("cy");

  if (heatToggle && mainImage) {
    let on = false;
    heatToggle.addEventListener("click", function () {
      on = !on;
      mainImage.src = on ? mainImage.dataset.heat : mainImage.src.replace("/heat", "");
      heatToggle.textContent = on ? "Show photo" : "Show attention map";
    });
  }

  document.querySelectorAll(".box[data-pid]").forEach(function (box) {
    box.addEventListener("click", function () {
      const id = box.dataset.pid;
      document.querySelectorAll(".box").forEach((b) => b.classList.remove("sel"));
      box.classList.add("sel");
      const prop = document.getElementById("prop-" + id);
      if (prop) {
        prop.classList.add("sel");
        prop.scrollIntoView({ behavior: "smooth", block: "center" });
        const d = prop.querySelector("details");
        if (d) d.open = true;
      }
    });
  });

  document.querySelectorAll(".prop[data-pid]").forEach(function (prop) {
    const box = document.querySelector('.box[data-pid="' + prop.dataset.pid + '"]');
    if (!box) return;
    prop.addEventListener("mouseenter", () => box.classList.add("sel"));
    prop.addEventListener("mouseleave", () => box.classList.remove("sel"));
  });

  if (viewer && pending && cx && cy) {
    viewer.addEventListener("click", function (ev) {
      if (ev.target.closest(".box[data-pid]")) return;
      const r = viewer.getBoundingClientRect();
      const x = Math.min(0.95, Math.max(0.05, (ev.clientX - r.left) / r.width));
      const y = Math.min(0.95, Math.max(0.05, (ev.clientY - r.top) / r.height));
      cx.value = x.toFixed(4);
      cy.value = y.toFixed(4);
      pending.style.display = "block";
      pending.style.left = (x - 0.08) * 100 + "%";
      pending.style.top = (y - 0.08) * 100 + "%";
    });
  }

  document.querySelectorAll("form").forEach(function (f) {
    f.addEventListener("submit", function () {
      const b = f.querySelector("button[type=submit], button:not([type])");
      if (b && !b.disabled) {
        b.dataset.label = b.textContent;
        b.textContent = "…";
        setTimeout(() => { if (b.dataset.label) b.textContent = b.dataset.label; }, 2500);
      }
    });
  });
})();
