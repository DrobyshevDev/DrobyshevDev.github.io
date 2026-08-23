/* DrobyshevDev — site behaviour. Progressive enhancement only:
   every section is readable and every link works with this file removed. */
(function () {
  "use strict";

  /* --- Theme ------------------------------------------------------------ */
  // The stored value is applied by an inline script in <head> so the page never
  // paints in the wrong theme; this only handles the toggle itself. With
  // nothing stored the system preference decides, which is why the toggle
  // reads the media query rather than assuming light.
  var root = document.documentElement;

  function currentTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit === "dark" || explicit === "light") return explicit;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  var toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    toggle.setAttribute("aria-label", toggle.getAttribute("data-label-" + currentTheme()));
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* private mode */ }
      toggle.setAttribute("aria-label", toggle.getAttribute("data-label-" + next));
    });
  }

  /* --- Mobile navigation ------------------------------------------------ */
  var navToggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("primary-nav");

  function closeNav() {
    if (!nav || !navToggle) return;
    nav.setAttribute("data-open", "false");
    navToggle.setAttribute("aria-expanded", "false");
  }

  if (navToggle && nav) {
    navToggle.addEventListener("click", function () {
      var open = nav.getAttribute("data-open") === "true";
      nav.setAttribute("data-open", open ? "false" : "true");
      navToggle.setAttribute("aria-expanded", open ? "false" : "true");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) closeNav();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });
    // Must match the breakpoint in site.css where the panel stops being a
    // panel. A resize past it would otherwise leave the menu stuck open.
    window.addEventListener("resize", function () {
      if (window.innerWidth > 760) closeNav();
    });
  }

  /* --- Current year ----------------------------------------------------- */
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });
})();
