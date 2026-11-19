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
   * Dates use America/New_York so the neighborhood changes seasons at the same
   * time even when a visitor is browsing from another time zone.
   */
  var themes = {
    spring: {
      label: "Spring in Sugarwood",
      notice: "Spring brings fresh growth, neighborhood activity, and a new season for enjoying Sugarwood.",
      heroTitle: "A fresh season at home.",
      heroCopy: "Sugarwood is an established Farragut neighborhood where spring brings neighbors outdoors and community spaces back to life.",
      image: "images/swentrancecropped.jpg",
      secondaryImage: "images/Sugarwood-Pool-e1723392724342.jpg",
      secondaryAlt: "Sugarwood community swimming pool at dusk",
      secondaryPosition: "center",
      aboutImage: "images/swentrancecropped.jpg",
      aboutAlt: "Landscaped Sugarwood neighborhood entrance",
      favicon: "images/favicon-summer.jpg",
      faviconType: "image/jpeg",
      color: "#071d2e"
    },
    summer: {
      label: "Summer in Sugarwood",
      notice: "Summer is a season for the pool, recreation areas, neighborhood activities, and time together outdoors.",
      heroTitle: "Summer starts close to home.",
      heroCopy: "From pool days to evenings with neighbors, Sugarwood is a welcoming community in the heart of Farragut.",
      image: "images/Sugarwood-Pool-e1723392724342.jpg",
      secondaryImage: "images/Sugarwood-Pool-e1723392724342.jpg",
      secondaryAlt: "Sugarwood community swimming pool at dusk",
      secondaryPosition: "center",
      aboutImage: "images/swentrancecropped.jpg",
      aboutAlt: "Landscaped Sugarwood neighborhood entrance",
      favicon: "images/favicon-summer.jpg",
      faviconType: "image/jpeg",
      color: "#071d2e"
    },
    autumn: {
      label: "Autumn in Sugarwood",
      notice: "A season for crisp walks, colorful trees, and connecting with neighbors throughout Sugarwood.",
      heroTitle: "A warm welcome, all season long.",
      heroCopy: "Sugarwood is a peaceful Farragut neighborhood where community feels close to home—especially in the colors of autumn.",
      image: "images/sugarwood-front-fall-hero.jpg",
      secondaryImage: "images/sugarwood-fall-path.jpg?v=20261118-3",
      secondaryAlt: "Autumn path through a colorful Sugarwood landscape",
      secondaryPosition: "right top",
      aboutImage: "images/sugarwood-about-fall.jpg?v=20261118-1",
      aboutAlt: "Sugarwood homes framed by colorful autumn trees",
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
      secondaryImage: "images/Sugarwood-Pool-e1723392724342.jpg",
      secondaryAlt: "Sugarwood community swimming pool at dusk",
      secondaryPosition: "center",
      aboutImage: "images/swentrancecropped.jpg",
      aboutAlt: "Landscaped Sugarwood neighborhood entrance",
      favicon: "images/favicon-winter.ico",
      faviconType: "image/x-icon",
      color: "#102b43"
    }
  };

  function themeForMonthDay(month, day) {
    var monthDay = month * 100 + day;
    if (monthDay >= 1215 || monthDay < 301) return "winter";
    if (monthDay >= 922) return "autumn";
    if (monthDay >= 526) return "summer";
    return "spring";
  }

  function automaticTheme() {
    var now = new Date();
    try {
      var parts = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York",
        month: "numeric",
        day: "numeric"
      }).formatToParts(now);
      var month = Number(parts.find(function (part) { return part.type === "month"; }).value);
      var day = Number(parts.find(function (part) { return part.type === "day"; }).value);
      return themeForMonthDay(month, day);
    } catch (error) {
      return themeForMonthDay(now.getMonth() + 1, now.getDate());
    }
  }

  function assetBase() {
    var script = document.querySelector('script[src*="assets/js/site.js"]');
    return script ? script.src.replace(/js\/site\.js(?:\?.*)?$/, "") : "assets/";
  }

  var themeName = automaticTheme();
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

  var homeSecondaryImage = document.querySelector("[data-seasonal-home-image]");
  if (homeSecondaryImage && theme.secondaryImage) {
    homeSecondaryImage.setAttribute("src", base + theme.secondaryImage);
    if (theme.secondaryAlt) homeSecondaryImage.setAttribute("alt", theme.secondaryAlt);
    if (theme.secondaryPosition) homeSecondaryImage.style.objectPosition = theme.secondaryPosition;
  }

  var aboutImage = document.querySelector("[data-seasonal-about-image]");
  if (aboutImage && theme.aboutImage) {
    aboutImage.setAttribute("src", base + theme.aboutImage);
    if (theme.aboutAlt) aboutImage.setAttribute("alt", theme.aboutAlt);
  }

  var main = document.getElementById("main-content");
  if (main) {
    var notice = document.createElement("aside");
    notice.className = "season-notice";
    notice.setAttribute("aria-label", "Seasonal message");
    notice.innerHTML = '<div class="container"><strong>' + theme.label + '</strong><span>' + theme.notice + '</span></div>';
    main.insertBefore(notice, main.firstChild);
  }

  window.__SUGARWOOD_READY__ = true;
})();
