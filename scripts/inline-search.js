(function () {
  "use strict";

  function getBase() {
    try {
      var el = document.getElementById("__config");
      if (el) {
        var cfg = JSON.parse(el.textContent);
        if (cfg && cfg.base) return cfg.base;
      }
    } catch (e) {}
    return ".";
  }

  var base = getBase();
  var index = null;

  function ensureIndex(cb) {
    if (index) return cb();
    fetch(base + "/search/search_index.json")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        index = data.docs || [];
        cb();
      })
      .catch(function () { index = []; cb(); });
  }

  function normalize(s) {
    return s.toLowerCase().replace(/\s+/g, " ").trim();
  }

  function stripHtml(s) {
    return s.replace(/<[^>]*>/g, "").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"');
  }

  function highlight(text, q) {
    var esc = stripHtml(text).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
    var idx = normalize(esc).indexOf(normalize(q));
    if (idx < 0) return esc;
    var start = Math.max(0, idx - 60);
    var snippet = (start > 0 ? "…" : "") + esc.slice(start, idx + q.length + 120) + "…";
    var re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
    return snippet.replace(re, "<mark>$1</mark>");
  }

  function renderResults(box, q) {
    var results = box.parentNode.querySelector("[data-isearch-results]");
    var qn = normalize(q);
    if (!qn) { results.innerHTML = ""; return; }
    ensureIndex(function () {
      var hits = [];
      index.forEach(function (doc) {
        var hay = normalize(doc.title + " " + stripHtml(doc.text || ""));
        if (hay.indexOf(qn) !== -1) {
          hits.push(doc);
        }
      });
      hits.sort(function (a, b) {
        var at = normalize(a.title).indexOf(qn);
        var bt = normalize(b.title).indexOf(qn);
        if (at === -1) return 1;
        if (bt === -1) return -1;
        return at - bt;
      });
      var seen = {};
      hits = hits.filter(function (doc) {
        var page = doc.location.split("#")[0];
        if (seen[page]) return false;
        seen[page] = true;
        return true;
      });
      hits = hits.slice(0, 10);
      if (!hits.length) {
        results.innerHTML = '<div class="isearch-empty">Ничего не найдено</div>';
        return;
      }
      results.innerHTML = hits.map(function (doc) {
        var href = base + "/" + doc.location;
        return (
          '<a class="isearch-item" href="' + href + '">' +
            '<div class="isearch-item__title">' + highlight(doc.title, q) + "</div>" +
            '<div class="isearch-item__snippet">' + highlight((doc.text || "").slice(0, 300), q) + "</div>" +
          "</a>"
        );
      }).join("");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var boxes = document.querySelectorAll("[data-isearch]");
    boxes.forEach(function (box) {
      var timer = null;
      box.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(function () { renderResults(box, box.value); }, 150);
      });
      box.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
          box.value = "";
          var results = box.parentNode.querySelector("[data-isearch-results]");
          results.innerHTML = "";
        }
      });
    });

    document.addEventListener(
      "keydown",
      function (e) {
        if (e.key === "/" && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
          e.preventDefault();
          e.stopPropagation();
          var box = document.querySelector(".isearch__input");
          if (box) box.focus();
        }
      },
      true
    );

    initThemeSwitch();
    initTagsPanel();
  });

  /* ---- Obsidian-style theme switch (sun/moon icon) in the left sidebar ---- */
  var SUN_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  var MOON_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  function initThemeSwitch() {
    var title = document.querySelector(".md-sidebar--primary .md-nav__title");
    if (!title) return;
    var scheme = (document.body.getAttribute("data-md-color-scheme") || "default");
    var btn = document.createElement("button");
    btn.className = "theme-switch";
    btn.type = "button";
    btn.setAttribute("aria-label", "Переключить тему");
    btn.title = "Переключить тему";
    var icon = document.createElement("span");
    icon.className = "theme-switch__icon";
    btn.appendChild(icon);
    function apply() {
      var dark = document.body.getAttribute("data-md-color-scheme") === "slate";
      icon.innerHTML = dark ? SUN_SVG : MOON_SVG;
      try {
        localStorage.setItem("__palette", JSON.stringify({ index: dark ? 1 : 0 }));
      } catch (e) {}
    }
    btn.addEventListener("click", function () {
      var dark = document.body.getAttribute("data-md-color-scheme") === "slate";
      document.body.setAttribute("data-md-color-scheme", dark ? "default" : "slate");
      apply();
    });
    apply();
    title.after(btn);
  }

  /* ---- Tags panel in the right sidebar ---- */
  function initTagsPanel() {
    if (typeof window.WIKI_TAGS === "undefined") return;
    var searchBox = document.querySelector(".isearch[data-wiki]");
    var wiki = searchBox ? (searchBox.getAttribute("data-wiki") || null) : null;
    var tags = wiki ? (window.WIKI_TAGS[wiki] || []) : (window.WIKI_TAGS.all || []);
    var secondary = document.querySelector(".md-sidebar--secondary");
    if (!secondary) return;
    var panel = document.createElement("div");
    panel.className = "tags-panel";
    tags.forEach(function (t) {
      var chip = document.createElement("button");
      chip.className = "tag-chip any";
      chip.type = "button";
      chip.textContent = "#" + t;
      chip.addEventListener("click", function () {
        var input = document.querySelector(".isearch__input");
        if (!input) return;
        if (input.value.trim() === t) {
          input.value = "";
        } else {
          input.value = t;
        }
        input.dispatchEvent(new Event("input"));
        input.focus();
      });
      panel.appendChild(chip);
    });
    var inner = secondary.querySelector(".md-sidebar__inner");
    if (inner) {
      inner.appendChild(panel);
    } else {
      secondary.appendChild(panel);
    }
  }
})();
