// Небозвід — interface: chips, labels, catalogue, info panel.
// Plain scripts sharing one scope; index.html loads them in order.
"use strict";

/* ---------- UI ---------- */
const $ = id => document.getElementById(id);
const chipsEl = $("chips"), tagsEl = $("tags"), infoEl = $("info"), moonsEl = $("moons"), moonListEl = $("moonList");
// Seconds of simulated time per real second.
const RATES = [[1, "реальний"], [60, "1 хв/с"], [3600, "1 год/с"], [86400, "1 доба/с"], [604800, "1 тижд/с"], [2629800, "1 міс/с"], [31557600, "1 рік/с"]];

function makeChip(b) {
  const chip = document.createElement("button");
  chip.className = "chip"; chip.type = "button";
  chip.innerHTML = `<i style="background:${b.dot};color:${b.dot}"></i>${b.short || b.name}`;
  chip.addEventListener("click", () => focusBody(b.index));
  return chip;
}
BODIES.forEach((b, i) => {
  b.index = i;
  if (!b.parent) {
    if (b.id === "ceres" || b.id === "halley") {
      const sep = document.createElement("span");
      sep.className = "sep"; sep.setAttribute("aria-hidden", "true");
      chipsEl.appendChild(sep);
    }
    b.chip = makeChip(b);
    chipsEl.appendChild(b.chip);
  }
  const tag = document.createElement("button");
  tag.className = "tag" + (b.parent ? " moon" : b.dwarf ? " dwarf" : b.comet ? " comet" : "");
  tag.type = "button"; tag.textContent = b.short || b.name; tag.tabIndex = -1;
  tag.addEventListener("click", () => focusBody(i));
  tagsEl.appendChild(tag);
  b.tag = tag;
});

// Catalogue: planets (dwarfs below), moons grouped by their planet, comets.
const catalogEl = $("catalog");
function catItem(b, list) {
  const label = b.comet ? b.name.replace(/^Комета /, "") : b.name;
  const chip = document.createElement("button");
  chip.className = "chip"; chip.type = "button";
  chip.innerHTML = `<i style="background:${b.dot};color:${b.dot}"></i>${label}${b.short && b.short !== label ? ` <small>${b.short}</small>` : ""}`;
  chip.addEventListener("click", () => { setCatalog(false); focusBody(b.index); });
  list.appendChild(chip);
  b.catChip = chip;
}
for (const b of BODIES) {
  if (b.comet) catItem(b, $("catComets"));
  else if (b.dwarf) catItem(b, $("catDwarfs"));
  else if (!b.parent) catItem(b, $("catPlanets"));
}
for (const p of MAIN) {
  if (!p.moons) continue;
  const group = document.createElement("div"), h = document.createElement("h3"), list = document.createElement("div");
  h.textContent = p.name; list.className = "cat-list";
  group.append(h, list);
  $("catMoons").appendChild(group);
  for (const m of p.moons) catItem(m, list);
}
function setCatTab(tab) {
  catalogEl.dataset.tab = tab;
  for (const t of catalogEl.querySelectorAll(".cat-tabs button")) t.setAttribute("aria-selected", String(t.dataset.tab === tab));
}
function setCatalog(open) {
  if (open) {
    // Open on the group of whatever is in focus.
    const b = state.index >= 0 ? BODIES[state.index] : null;
    setCatTab(b && b.parent ? "moons" : b && b.comet ? "comets" : "planets");
    setMenu(false);
  }
  catalogEl.hidden = !open;
  $("allBtn").setAttribute("aria-expanded", String(open));
}
for (const t of catalogEl.querySelectorAll(".cat-tabs button")) t.addEventListener("click", () => setCatTab(t.dataset.tab));

function fmtRatio(d, ref, refName) {
  const r = d / ref;
  const s = r >= 10 ? Math.round(r).toString() : r.toFixed(r < 1 ? 2 : 1).replace(".", ",");
  return `${s} × ${refName}`;
}
function renderInfo(b) {
  const data = b || OVERVIEW;
  $("kind").textContent = data.kind;
  $("name").textContent = data.name;
  let rows = data.stats;
  if (b) {
    const isMoon = b.parent && b.id !== "moon";
    const note = b.comet ? "ядро" : b.id === "earth" ? "еталон для порівняння" : isMoon ? fmtRatio(b.d, MOON_D, "Місяця") : fmtRatio(b.d, EARTH_D, "Землі");
    rows = [["Діаметр", b.dText || (b.d.toLocaleString("uk-UA") + " км"), note]].concat(b.stats);
  }
  $("stats").innerHTML = rows.map(r => `<div><dt>${r[0]}</dt><dd>${r[1]}${r[2] ? `<small>${r[2]}</small>` : ""}</dd></div>`).join("");
  $("desc").textContent = data.desc;
  $("voice").textContent = (b && b.voice) || "";
  $("voice").hidden = !(b && b.voice);
  $("fact").textContent = data.fact;
  const act = $("actions");
  act.innerHTML = "";
  act.hidden = !(b && (b.actions || SURFACES[b.id]));
  if (b && SURFACES[b.id]) {
    const btn = document.createElement("button");
    btn.type = "button"; btn.id = "surface-" + b.id;
    btn.textContent = surfaceLabel(SURFACES[b.id]);
    btn.addEventListener("click", () => toggleSurface(b.id));
    act.appendChild(btn);
  }
  if (b && b.actions) {
    for (const [label, iso, rate] of b.actions) {
      const btn = document.createElement("button");
      btn.type = "button"; btn.textContent = label;
      btn.addEventListener("click", () => jumpTo(Date.parse(iso), rate != null ? rate : 3, label));
      act.appendChild(btn);
    }
  }
  updateLive(true);

  const family = b ? (b.parent || b) : null;
  moonListEl.innerHTML = "";
  moonsEl.hidden = !(family && family.moons);
  if (family && family.moons) {
    $("moonsLabel").textContent = b.parent ? `Система: ${family.name}` : "Супутники";
    const list = b.parent ? [family].concat(family.moons) : family.moons;
    for (const m of list) {
      const c = makeChip(m);
      c.setAttribute("aria-current", m === b ? "true" : "false");
      moonListEl.appendChild(c);
    }
  }
}
