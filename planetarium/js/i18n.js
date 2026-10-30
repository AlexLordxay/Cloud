// Небозвід — languages: Ukrainian (the original, written in the code and the page) and English (js/lang_en.js).
// The English text is a dictionary keyed by the Ukrainian one: T("Огляд") → "Overview" on the English site and the
// Ukrainian string itself otherwise (or when a line has no translation yet). {0}, {1}… in a key are filled from the
// arguments: T("Зараз від Землі: {0}", d). The language: ?lang=en|uk in the address (remembered), else the last
// choice, else Ukrainian. The button in the menu switches it and reloads the page.
"use strict";

const LANGS = ["uk", "en"];
const LANG_KEY = "planetarium.lang";
const LANG = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (LANGS.includes(q)) { try { localStorage.setItem(LANG_KEY, q); } catch (e) { /* not saved */ } return q; }
  try { const s = localStorage.getItem(LANG_KEY); if (LANGS.includes(s)) return s; } catch (e) { /* storage blocked */ }
  return "uk";
})();
const EN_ON = LANG === "en";
const LOC = EN_ON ? "en-GB" : "uk-UA";       // dates and big numbers
const EN = {};                                // filled by js/lang_en.js

function T(s, ...args) {
  const r = EN_ON && EN[s] != null ? EN[s] : s;
  return args.length ? r.replace(/\{(\d)\}/g, (m, i) => args[i]) : r;
}

// The page's own text: every text node and label whose (trimmed) Ukrainian text has a translation.
function applyI18n(root) {
  if (!EN_ON) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const s = n.nodeValue.trim();
    if (s && EN[s] != null) n.nodeValue = n.nodeValue.replace(s, EN[s]);
  }
  for (const el of root.querySelectorAll("[aria-label],[title],[alt]")) {
    for (const a of ["aria-label", "title", "alt"]) {
      const v = el.getAttribute(a);
      if (v && EN[v] != null) el.setAttribute(a, EN[v]);
    }
  }
}

// The language button (in the menu) shows the other language; the address keeps its #hash.
function setupLangButton() {
  const btn = document.getElementById("langBtn");
  if (!btn) return;
  // the short code on a computer (the row is full), the language's name too in the phone menu (css)
  btn.innerHTML = EN_ON ? 'UA<span class="lang-long"> · Українська</span>' : 'EN<span class="lang-long"> · English</span>';
  btn.title = EN_ON ? "Українська" : "English";
  btn.lang = EN_ON ? "uk" : "en";
  // the choice is saved and the page reloads; the address gets ?lang only when it already has one or storage is blocked
  btn.addEventListener("click", () => {
    const next = EN_ON ? "uk" : "en", u = new URL(location.href);
    let saved = false;
    try { localStorage.setItem(LANG_KEY, next); saved = localStorage.getItem(LANG_KEY) === next; } catch (e) { /* storage blocked */ }
    if (saved && !u.searchParams.has("lang")) { location.reload(); return; }
    u.searchParams.set("lang", next);
    location.href = u.href;
  });
}

function startI18n() {
  setupLangButton();
  if (!EN_ON) return;
  document.documentElement.lang = "en";
  // the phone writes the date field in its own language (iOS: «17 лист. 2026 р.»), so the English date lies over it
  const dt = document.getElementById("dateText");
  if (dt) { dt.hidden = false; dt.parentNode.classList.add("own"); }
  document.title = T(document.title);
  const desc = document.querySelector('meta[name="description"]');
  if (desc) desc.content = T(desc.content);
  applyI18n(document.body);
}
