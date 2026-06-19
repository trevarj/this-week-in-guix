(function () {
  "use strict";

  var root = document.documentElement;

  /* ----- Theme toggle -----
     Token strategy (see style.css):
       - :root holds dark tokens (default).
       - @media (prefers-color-scheme: light) :root:not([data-theme]) applies
         light tokens when the user has NO stored preference.
       - :root[data-theme="light"] forces light.
       - :root[data-theme="dark"] forces dark (beats the OS light media query
         via selector specificity).
     So we always set an explicit data-theme on a user choice — never delete
     it — so a "dark" choice wins over an OS "light" preference. */

  var stored = localStorage.getItem("twg-theme");
  if (stored === "light") {
    root.dataset.theme = "light";
  } else if (stored === "dark") {
    root.dataset.theme = "dark";
  }
  /* stored === null: leave data-theme unset so @media (prefers-color-scheme)
     decides, applying light tokens when the OS prefers light. */

  var button = document.querySelector(".theme-toggle");
  if (button) {
    // The effective theme is light when data-theme is explicitly light, OR
    // when no explicit override is set and the OS prefers light.
    function osPrefersLight() {
      return (
        "matchMedia" in window &&
        window.matchMedia("(prefers-color-scheme: light)").matches
      );
    }
    function isLightTheme() {
      if (root.dataset.theme) {
        return root.dataset.theme === "light";
      }
      return osPrefersLight();
    }

    function updateLabel() {
      var light = isLightTheme();
      button.setAttribute(
        "aria-label",
        light ? "Switch to dark theme" : "Switch to light theme"
      );
      button.setAttribute(
        "title",
        light ? "Switch to dark theme" : "Switch to light theme"
      );
    }

    updateLabel();
    button.addEventListener("click", function () {
      var next = isLightTheme() ? "dark" : "light";
      // Always set an explicit override so it beats the OS media query.
      root.dataset.theme = next;
      localStorage.setItem("twg-theme", next);
      updateLabel();
    });
  }

  /* ----- Reading progress bar (post pages only) ----- */

  var bar = document.querySelector(".reading-progress");
  if (bar) {
    var ticking = false;
    function updateProgress() {
      var height = root.scrollHeight - root.clientHeight;
      var pct = height > 0 ? (root.scrollTop / height) * 100 : 0;
      bar.style.width = Math.min(100, Math.max(0, pct)) + "%";
      ticking = false;
    }
    function onScroll() {
      if (!ticking) {
        window.requestAnimationFrame(updateProgress);
        ticking = true;
      }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    updateProgress();
  }

  /* ----- TOC scrollspy (post pages with a TOC) ----- */

  var tocLinks = document.querySelectorAll(".toc a[href^='#']");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var linkByTarget = {};
    var targets = [];
    tocLinks.forEach(function (link) {
      var id = link.getAttribute("href").slice(1);
      var el = document.getElementById(id);
      if (el) {
        linkByTarget[id] = link;
        targets.push(el);
      }
    });

    function setActive(id) {
      Object.keys(linkByTarget).forEach(function (key) {
        if (key === id) {
          linkByTarget[key].classList.add("is-active");
        } else {
          linkByTarget[key].classList.remove("is-active");
        }
      });
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            setActive(entry.target.id);
          }
        });
      },
      {
        // Trigger when a section heading is near the top of the viewport.
        rootMargin: "-80px 0px -70% 0px",
        threshold: 0,
      }
    );

    targets.forEach(function (el) {
      observer.observe(el);
    });
  }
}());