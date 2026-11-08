/* TinkerVision – gemeinsames Verhalten für alle Seiten:
   Dark Mode (folgt dem System, bis man selbst umschaltet), Sprachumschaltung
   und abgesicherter Zugriff auf localStorage.
   Jede Seite bindet diese Datei vor ihrem eigenen <script> ein und ruft
   TV.setLang(T, lang) mit ihrem Übersetzungsobjekt T auf. */
(function () {
  "use strict";

  var store = {
    get: function (key) {
      try { return window.localStorage.getItem(key); } catch (e) { return null; }
    },
    set: function (key, value) {
      try { window.localStorage.setItem(key, value); } catch (e) { /* privater Modus o. Ä. */ }
    }
  };

  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function savedTheme() {
    var t = store.get("tv-theme");
    return t === "dark" || t === "light" ? t : null;
  }
  function systemTheme() {
    return mq && mq.matches ? "dark" : "light";
  }
  function applyTheme(theme, remember) {
    theme = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    if (remember) store.set("tv-theme", theme);
    document.querySelectorAll("[data-theme-toggle]").forEach(function (el) {
      el.checked = theme === "dark";
    });
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#0e0f12" : "#ececf1");
  }

  // Die Sprache einer Seite steht in ihrer URL: /seite.html ist Deutsch, /en/seite.html Englisch.
  // Gibt es keine Gegenstück-Seite, wird wie früher direkt auf der Seite umgeschaltet.
  function startLang() {
    return document.documentElement.lang === "en" ? "en" : "de";
  }
  function alternateUrl(lang) {
    var link = document.querySelector('link[rel="alternate"][hreflang="' + lang + '"]');
    if (!link) return null;
    var onSite = /^https?:$/.test(location.protocol) && new URL(link.href).host === location.host;
    return onSite ? link.href : link.getAttribute("data-path");
  }
  function setLang(T, lang, opts) {
    lang = lang === "en" ? "en" : "de";
    opts = opts || {};
    var pack = T[lang] || T.de;
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var value = pack[el.getAttribute("data-i18n")];
      if (typeof value !== "string") return;
      if (opts.html || el.hasAttribute("data-i18n-html")) el.innerHTML = value;
      else el.textContent = value;
    });
    document.querySelectorAll("[data-set-lang]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", btn.getAttribute("data-set-lang") === lang ? "true" : "false");
    });
    var note = document.getElementById("en-note");
    if (note) note.hidden = lang !== "en";
    return lang;
  }

  // Klick auf DE/EN: Wahl merken und zur Seite in der anderen Sprache wechseln.
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-set-lang]");
    if (!btn) return;
    var lang = btn.getAttribute("data-set-lang");
    store.set("tv-lang", lang);
    if (lang === startLang()) { e.stopImmediatePropagation(); return; }
    var url = alternateUrl(lang);
    if (url) {
      e.stopImmediatePropagation();
      e.preventDefault();
      location.href = url + location.search + location.hash;
    }
  }, true);

  // Wer selbst eine Sprache gewählt hat, landet auch über alte Links in dieser Sprache.
  (function () {
    var chosen = store.get("tv-lang");
    if ((chosen === "de" || chosen === "en") && chosen !== startLang()) {
      var url = alternateUrl(chosen);
      if (url) location.replace(url + location.search + location.hash);
    }
  })();

  window.TV = { store: store, applyTheme: applyTheme, startLang: startLang, setLang: setLang };

  applyTheme(savedTheme() || systemTheme(), false);
  document.querySelectorAll("[data-theme-toggle]").forEach(function (el) {
    el.addEventListener("change", function () { applyTheme(el.checked ? "dark" : "light", true); });
  });
  if (mq) {
    var follow = function () { if (!savedTheme()) applyTheme(systemTheme(), false); };
    if (mq.addEventListener) mq.addEventListener("change", follow);
    else if (mq.addListener) mq.addListener(follow);
  }
})();
