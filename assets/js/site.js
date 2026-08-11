(function () {
  "use strict";

  var toggle = document.querySelector("[data-menu-toggle]");
  var nav = document.querySelector("[data-site-nav]");

  function closeMenu() {
    if (!toggle || !nav) return;
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Open navigation");
    nav.setAttribute("data-open", "false");
    document.body.classList.remove("nav-open");
  }

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      toggle.setAttribute("aria-label", open ? "Open navigation" : "Close navigation");
      nav.setAttribute("data-open", String(!open));
      document.body.classList.toggle("nav-open", !open);
    });

    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) closeMenu();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeMenu();
        toggle.focus();
      }
    });

    window.matchMedia("(min-width: 1161px)").addEventListener("change", closeMenu);
  }

  /*
   * SEASONAL THEME SETTINGS
   *
   * Automatic schedule: fall is September-November; winter is December-February;
   * the original Sugarwood design is used March-August. To test any theme, add
   * ?theme=fall, ?theme=winter, or ?theme=default to any page URL.
   */
  var themes = {
    default: {
      label: "Welcome to Sugarwood",
      notice: "Enjoy the community spaces, resident resources, and neighborhood information collected here.",
      heroTitle: "Home is found here.",
      heroCopy: "An established neighborhood in the heart of Farragut—close to schools, parks, shopping, and the places East Tennesseans love to explore.",
      image: "images/Sugarwood-Pool-e1723392724342.jpg",
      favicon: "images/favicon-summer.jpg",
      faviconType: "image/jpeg",
      color: "#071d2e"
    },
    fall: {
      label: "Autumn in Sugarwood",
      notice: "A season for crisp walks, colorful trees, and connecting with neighbors throughout Sugarwood.",
      heroTitle: "A warm welcome, all season long.",
      heroCopy: "Sugarwood is a peaceful Farragut neighborhood where community feels close to home—especially in the colors of autumn.",
      image: "images/sugarwood-fall-hero.png",
      favicon: "images/favicon-autumn.ico",
      faviconType: "image/x-icon",
      color: "#4a2a1b"
    },
    winter: {
      label: "Winter in Sugarwood",
      notice: "Winter is a good time to stay connected, review resident resources, and look ahead to the season to come.",
      heroTitle: "A neighborhood that feels like home.",
      heroCopy: "From calm winter mornings to the promise of spring, Sugarwood is a welcoming community in the heart of Farragut.",
      image: "images/sugarwood-winter-hero.png",
      favicon: "images/favicon-winter.ico",
      faviconType: "image/x-icon",
      color: "#102b43"
    }
  };

  function automaticTheme() {
    var month = new Date().getMonth() + 1;
    if (month >= 9 && month <= 11) return "fall";
    if (month === 12 || month <= 2) return "winter";
    return "default";
  }

  function selectedTheme() {
    var preview = new URLSearchParams(window.location.search).get("theme");
    return themes[preview] ? preview : automaticTheme();
  }

  function assetBase() {
    var script = document.querySelector('script[src*="assets/js/site.js"]');
    return script ? script.src.replace(/js\/site\.js(?:\?.*)?$/, "") : "assets/";
  }

  var themeName = selectedTheme();
  var theme = themes[themeName];
  var base = assetBase();
  document.documentElement.setAttribute("data-theme", themeName);
  document.body.setAttribute("data-theme", themeName);

  var themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.setAttribute("content", theme.color);

  var favicon = document.querySelector('link[rel~="icon"]');
  if (favicon) {
    var seasonalFavicon = favicon.cloneNode(false);
    seasonalFavicon.setAttribute("href", base + theme.favicon + "?v=20260810");
    seasonalFavicon.setAttribute("type", theme.faviconType);
    favicon.parentNode.replaceChild(seasonalFavicon, favicon);
  }

  var homeHero = document.querySelector(".hero");
  if (homeHero) {
    homeHero.style.setProperty("--hero-image", 'url("' + base + theme.image + '")');
    var eyebrow = homeHero.querySelector(".eyebrow");
    var heading = homeHero.querySelector("h1");
    var copy = homeHero.querySelector(".hero-copy");
    if (eyebrow) eyebrow.textContent = theme.label;
    if (heading) heading.textContent = theme.heroTitle;
    if (copy) copy.textContent = theme.heroCopy;
  }

  var main = document.getElementById("main-content");
  if (main) {
    var notice = document.createElement("aside");
    notice.className = "season-notice";
    notice.setAttribute("aria-label", "Seasonal message");
    notice.innerHTML = '<div class="container"><strong>' + theme.label + '</strong><span>' + theme.notice + '</span></div>';
    main.insertBefore(notice, main.firstChild);
  }

  /* TEST-ONLY SEASON PREVIEW BAR — remove this block before publishing. */
  var preview = document.createElement("nav");
  var previewChoice = new URLSearchParams(window.location.search).get("theme");
  var previewLinks = [
    { label: "Original", value: "default", href: "?theme=default" },
    { label: "Fall", value: "fall", href: "?theme=fall" },
    { label: "Winter", value: "winter", href: "?theme=winter" },
    { label: "Automatic", value: null, href: window.location.pathname }
  ];

  preview.className = "theme-preview theme-preview--test-only";
  preview.setAttribute("aria-label", "Season preview (test only)");
  preview.innerHTML = '<strong>Season preview</strong><span class="theme-preview__test-label">Test only</span><span class="theme-preview__links"></span>';

  var previewLinkContainer = preview.querySelector(".theme-preview__links");
  previewLinks.forEach(function (item) {
    var link = document.createElement("a");
    var isCurrent = item.value === previewChoice || (item.value === null && !themes[previewChoice]);
    link.href = item.href;
    link.textContent = item.label;
    if (isCurrent) link.setAttribute("aria-current", "page");
    previewLinkContainer.appendChild(link);
  });

  document.body.insertBefore(preview, document.body.firstChild);
  /* END TEST-ONLY SEASON PREVIEW BAR. */

  // Every subject currently goes to the board address. Add a route-specific
  // address to `cc` later to copy another volunteer or committee automatically.
  var defaultEmail = "sugarwoodboard@sugarwood.org";
  var contactRoutes = {
    maintenance: { label: "Maintenance Issues", to: defaultEmail, cc: "" },
    keycard: { label: "Keycard Issues", to: defaultEmail, cc: "" },
    grill: { label: "Grill Area Reservation", to: defaultEmail, cc: "" },
    stingrays: { label: "Stingrays", to: defaultEmail, cc: "" },
    permit: { label: "Building Permit", to: defaultEmail, cc: "" },
    pool: { label: "Pool / Recreation Area", to: defaultEmail, cc: "" },
    website: { label: "Website Issue", to: defaultEmail, cc: "" },
    general: { label: "General Inquiry", to: defaultEmail, cc: "" }
  };

  var contactForm = document.querySelector("[data-contact-form]");
  var contactStatus = document.querySelector("[data-contact-status]");

  if (contactForm) {
    contactForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!contactForm.checkValidity()) {
        contactForm.reportValidity();
        return;
      }

      var data = new FormData(contactForm);
      var route = contactRoutes[data.get("subject")] || contactRoutes.general;
      var body = [
        "Name: " + data.get("name"),
        "Email: " + data.get("email"),
        "Subject: " + route.label,
        "",
        data.get("message")
      ].join("\n");
      var params = new URLSearchParams({
        subject: "Sugarwood HOA: " + route.label,
        body: body
      });

      if (route.cc) params.set("cc", route.cc);
      if (contactStatus) contactStatus.textContent = "Your email application should open with this message ready to review and send.";
      window.location.href = "mailto:" + route.to + "?" + params.toString();
    });
  }

  window.__SUGARWOOD_READY__ = true;
})();
