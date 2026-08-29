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

  /* --- The mark's menu --------------------------------------------------- */
  // A disclosure rather than a role="menu" widget: the contents are ordinary
  // links, and links inside a menu role stop announcing themselves as links.
  var markTrigger = document.querySelector(".mark-trigger");
  var markMenu = document.getElementById("mark-menu");

  if (markTrigger && markMenu) {
    var markItems = markMenu.querySelectorAll("a");
    markItems.forEach(function (a, i) {
      a.parentNode.style.setProperty("--i", i);
    });

    function closeMark(returnFocus) {
      if (markTrigger.getAttribute("aria-expanded") !== "true") return;
      markTrigger.setAttribute("aria-expanded", "false");
      markMenu.hidden = true;
      if (returnFocus) markTrigger.focus();
    }

    function openMark() {
      markTrigger.setAttribute("aria-expanded", "true");
      markMenu.hidden = false;

      // Open upwards when the panel would otherwise run off the bottom of the
      // window. Measured rather than assumed: the hero sits at different
      // heights depending on how the headline wraps.
      markMenu.classList.remove("is-up");
      var room = window.innerHeight - markMenu.getBoundingClientRect().bottom;
      if (room < 8) markMenu.classList.add("is-up");

      // Restart the stagger: without this the rows only animate the first time.
      markMenu.querySelectorAll("li").forEach(function (li) {
        li.style.animation = "none";
        void li.offsetWidth;
        li.style.animation = "";
      });
    }

    markTrigger.addEventListener("click", function () {
      if (markTrigger.getAttribute("aria-expanded") === "true") closeMark(false);
      else openMark();
    });

    markTrigger.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
      e.preventDefault();
      openMark();
      markItems[e.key === "ArrowDown" ? 0 : markItems.length - 1].focus();
    });

    markMenu.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
      var list = Array.prototype.slice.call(markItems);
      var i = list.indexOf(document.activeElement);
      if (i === -1) return;
      e.preventDefault();
      var step = e.key === "ArrowDown" ? 1 : -1;
      list[(i + step + list.length) % list.length].focus();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMark(true);
    });

    document.addEventListener("click", function (e) {
      if (!e.target.closest(".hero-mark")) closeMark(false);
    });

    // Tabbing past the last item should close it, the same as clicking away.
    document.addEventListener("focusin", function (e) {
      if (!e.target.closest(".hero-mark")) closeMark(false);
    });
  }

  /* --- Current year ----------------------------------------------------- */
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });
})();
