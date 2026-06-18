(function () {
  "use strict";

  var root = document.documentElement;

  /* ----- Theme toggle ----- */

  var stored = localStorage.getItem("twg-theme");
  if (stored === "light") {
    root.dataset.theme = "light";
  }

  var button = document.querySelector(".theme-toggle");
  if (button) {
    function updateLabel() {
      var isLight = root.dataset.theme === "light";
      button.setAttribute("aria-label", isLight ? "Switch to dark theme" : "Switch to light theme");
      button.setAttribute("title", isLight ? "Switch to dark theme" : "Switch to light theme");
    }

    updateLabel();
    button.addEventListener("click", function () {
      var next = root.dataset.theme === "light" ? "dark" : "light";
      if (next === "light") {
        root.dataset.theme = "light";
        localStorage.setItem("twg-theme", "light");
      } else {
        delete root.dataset.theme;
        localStorage.setItem("twg-theme", "dark");
      }
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