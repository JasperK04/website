/* theme.js - Light / dark theme switcher
 *
 * Reads the stored preference from localStorage (key: 'theme').
 * Falls back to the OS preference (prefers-color-scheme) when no
 * stored value exists.  Sets data-theme on <html> immediately to
 * prevent a flash of the wrong theme on page load.
 */

(function () {
  "use strict";

  var STORAGE_KEY = "theme";
  var DARK = "dark";
  var LIGHT = "light";

  // ------------------------------------------------------------------
  // Determine initial theme
  // ------------------------------------------------------------------
  function getStoredTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      return null;
    }
  }

  function getOsTheme() {
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return LIGHT;
    }
    return DARK;
  }

  function resolveTheme() {
    return getStoredTheme() || getOsTheme();
  }

  // ------------------------------------------------------------------
  // Apply theme to <html>
  // ------------------------------------------------------------------
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);

    var btn = document.getElementById("theme-toggle");
    if (!btn) return;

    if (theme === LIGHT) {
      btn.textContent = "🌙";
      btn.setAttribute("aria-label", "Switch to dark mode");
      btn.setAttribute("title", "Switch to dark mode");
    } else {
      btn.textContent = "☀️";
      btn.setAttribute("aria-label", "Switch to light mode");
      btn.setAttribute("title", "Switch to light mode");
    }
  }

  // ------------------------------------------------------------------
  // Toggle
  // ------------------------------------------------------------------
  function toggleTheme() {
    var current = document.documentElement.getAttribute("data-theme") || resolveTheme();
    var next = current === LIGHT ? DARK : LIGHT;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (_) {}
    applyTheme(next);
  }

  // ------------------------------------------------------------------
  // Init — runs as early as possible to avoid flash
  // ------------------------------------------------------------------
  applyTheme(resolveTheme());

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (btn) {
      // Re-apply to also update button label now that DOM is ready
      applyTheme(resolveTheme());
      btn.addEventListener("click", toggleTheme);
    }
  });
})();
