/* Theme selection: light, dark, or whatever the operating system prefers.
 *
 * Loaded synchronously in <head> so the first paint already has the right
 * palette. The CSP forbids inline script, which is why this lives in a file.
 * Stored preference is a display setting only — no personal data.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "ll-theme";
  var META = "theme-color";
  var COLOURS = { light: "#f8fafc", dark: "#0a1220" };

  function stored() {
    try {
      var value = window.localStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : null;
    } catch (error) {
      return null; /* private mode, storage disabled: fall through to system */
    }
  }

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function resolve() {
    return stored() || (systemPrefersDark() ? "dark" : "light");
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
    var meta = document.querySelector('meta[name="' + META + '"]');
    if (meta) {
      meta.setAttribute("content", COLOURS[theme] || COLOURS.light);
    }
  }

  apply(resolve());

  function current() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function set(theme) {
    apply(theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch (error) {
      /* preference simply does not persist */
    }
    syncButtons();
  }

  function syncButtons() {
    var theme = current();
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      buttons[i].setAttribute("title", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
      buttons[i].setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
    }
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest ? event.target.closest("[data-theme-toggle]") : null;
    if (!button) {
      return;
    }
    event.preventDefault();
    set(current() === "dark" ? "light" : "dark");
  });

  if (window.matchMedia) {
    var query = window.matchMedia("(prefers-color-scheme: dark)");
    var onChange = function () {
      if (!stored()) {
        apply(resolve());
        syncButtons();
      }
    };
    if (query.addEventListener) {
      query.addEventListener("change", onChange);
    } else if (query.addListener) {
      query.addListener(onChange);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncButtons);
  } else {
    syncButtons();
  }

  window.LotlineTheme = { set: set, current: current };
})();
