(function () {
  const root = document.documentElement;
  const button = document.querySelector(".theme-toggle");
  const stored = localStorage.getItem("twg-theme");

  if (stored === "light") {
    root.dataset.theme = "light";
  }

  function updateLabel() {
    const isLight = root.dataset.theme === "light";
    button.setAttribute("aria-label", isLight ? "Switch to dark theme" : "Switch to light theme");
    button.setAttribute("title", isLight ? "Switch to dark theme" : "Switch to light theme");
  }

  if (!button) {
    return;
  }

  updateLabel();
  button.addEventListener("click", function () {
    const next = root.dataset.theme === "light" ? "dark" : "light";
    if (next === "light") {
      root.dataset.theme = "light";
      localStorage.setItem("twg-theme", "light");
    } else {
      delete root.dataset.theme;
      localStorage.setItem("twg-theme", "dark");
    }
    updateLabel();
  });
}());

