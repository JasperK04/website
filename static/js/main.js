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
  // Search form - debounced AJAX submit
  // -----------------------------------------------------------------------
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");
  if (searchInput && searchResults && searchInput.form) {
    let debounceTimer;

    function buildSearchUrl() {
      const form = searchInput.form;
      const url = new URL(form.action, window.location.origin);
      const params = new URLSearchParams(new FormData(form));
      if ([...params.values()].every(function (value) { return !value; })) {
        url.search = "";
      } else {
        url.search = params.toString();
      }
      return url.toString();
    }

    function updateResults(html, url) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const nextResults = doc.getElementById("search-results");
      if (!nextResults) return;
      searchResults.innerHTML = nextResults.innerHTML;
      window.history.replaceState({}, "", url);
      searchInput.focus();
      searchInput.setSelectionRange(searchInput.value.length, searchInput.value.length);
    }

    function fetchResults() {
      const url = buildSearchUrl();
      fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function (res) {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.text();
        })
        .then(function (html) {
          updateResults(html, url);
        })
        .catch(function () {
          // Fallback to full navigation if something goes wrong
          window.location.assign(url);
        });
    }

    searchInput.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(fetchResults, 500);
    });

    searchInput.form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetchResults();
    });

    searchInput.form
      .querySelectorAll('input[name="tech"]')
      .forEach(function (toggle) {
        toggle.addEventListener("change", function () {
          fetchResults();
        });
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
