/* main.js - Navigation and UI interactions */

(function () {
  "use strict";

  var MOBILE_BREAKPOINT = 768;

  // -----------------------------------------------------------------------
  // Hamburger / sidebar toggle
  // -----------------------------------------------------------------------
  const hamburger = document.getElementById("hamburger");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebar-overlay");

  function openSidebar() {
    sidebar.classList.add("open");
    overlay.classList.add("visible");
    hamburger.classList.add("open");
    hamburger.setAttribute("aria-expanded", "true");
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("visible");
    hamburger.classList.remove("open");
    hamburger.setAttribute("aria-expanded", "false");
  }

  if (hamburger && sidebar && overlay) {
    hamburger.addEventListener("click", function () {
      if (sidebar.classList.contains("open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    overlay.addEventListener("click", closeSidebar);

    // Close on Escape key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("open")) {
        closeSidebar();
      }
    });

    // Close sidebar when a nav link is clicked on mobile
    sidebar.querySelectorAll(".nav-link").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth <= MOBILE_BREAKPOINT) {
          closeSidebar();
        }
      });
    });
  }

  // -----------------------------------------------------------------------
  // Active nav link highlighting
  // -----------------------------------------------------------------------
  const currentPath = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach(function (link) {
    const href = link.getAttribute("href");
    if (!href) return;
    // Exact match or prefix (for nested routes like /projects/...)
    if (
      href === currentPath ||
      (href !== "/" && currentPath.startsWith(href))
    ) {
      link.classList.add("active");
    }
  });

  // -----------------------------------------------------------------------
  // Search form - debounced auto-submit
  // -----------------------------------------------------------------------
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    let debounceTimer;

    searchInput.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        searchInput.form.submit();
      }, 400);
    });

    // Focus shortcut: press "/" to focus search
    document.addEventListener("keydown", function (e) {
      if (
        e.key === "/" &&
        document.activeElement !== searchInput &&
        document.activeElement.tagName !== "INPUT" &&
        document.activeElement.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        searchInput.focus();
      }
    });
  }
})();
