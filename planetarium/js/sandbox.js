// Небозвід — the sandbox: "what if?" with real gravity. The Sun and the eight planets start where they are on the site's
// date, then move by Newton's law (every body pulls every other), so a change — a second Sun, Jupiter in the Earth's
// place, a heavier Sun — shows what happens to all the rest. The main site keeps its exact orbits; leaving the sandbox
// puts everything back. Moons ride with their planets as usual; dwarf planets and comets step aside.
// Plain scripts sharing one scope; index.html loads it before main.js (it uses main.js's state only at run time).
"use strict";

const sandbox = (() => {
  const G = 2.959122083e-4;                       // AU³ / (solar mass · day²)
  const ID = ["sun", "mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"];
  const MASS = { sun: 1, mercury: 1.66e-7, venus: 2.448e-6, earth: 3.04e-6, mars: 3.227e-7, jupiter: 9.548e-4, saturn: 2.859e-4, uranus: 4.366e-5, neptune: 5.151e-5 };
  const NAME = { sun: "Сонце", sun2: "Друге Сонце", mercury: "Меркурій", venus: "Венера", earth: "Земля", mars: "Марс", jupiter: "Юпітер", saturn: "Сатурн", uranus: "Уран", neptune: "Нептун" };
  const WITH = { sun: "Сонцем", sun2: "другим Сонцем", mercury: "Меркурієм", venus: "Венерою", earth: "Землею", mars: "Марсом", jupiter: "Юпітером", saturn: "Сатурном", uranus: "Ураном", neptune: "Нептуном" };
  const fem = id => id === "earth" || id === "venus";
  const verb = (id, m, f) => fem(id) ? f : m;
  // Simulated days per real second.
  const SPEEDS = [[2, "2 доби/с"], [10, "10 діб/с"], [60, "2 міс/с"], [365, "1 рік/с"], [3650, "10 років/с"]];
  const SCENARIOS = {
    "two-suns": { title: "Друге Сонце", speed: 3,
      text: "Ще одна така сама зоря на відстані Сатурна — і дві зорі кружляють одна навколо одної. Близькі планети ще тримаються свого Сонця, а дальні гіганти не мають шансів." },
    "jupiter-earth": { title: "Юпітер замість Землі", speed: 3,
      text: "Юпітер і Земля помінялися місцями. Велетень у 318 разів важчий за Землю тепер тягне сусідів — дивись на Марс і Венеру." },
    "heavy-sun": { title: "Сонце вдвічі важче", speed: 2,
      text: "Сонце раптом стало вдвічі масивнішим — і в 11 разів яскравішим. Планети рухаються надто повільно для нової сили тяжіння й падають на витягнуті орбіти." },
    "no-sun": { title: "Сонце зникло", speed: 3,
      text: "Сонця більше немає. Ніщо не тримає планети — вони летять по прямих, кожна туди, куди рухалася тієї миті. Світло зникне через 8 хвилин." },
    "stop-earth": { title: "Земля зупинилася", speed: 0,
      text: "Земля раптом зупинилася на своїй орбіті. Ніщо більше не відводить її вбік — і вона падає прямо на Сонце." },
  };
  const S = { on: false, bodies: [], days: 0, speed: 3, scenario: "", jd0: 0, events: new Set(), trails: null, sun2: null };
  const V = () => new THREE.Vector3();

  function body(id, m, pos, vel) { return { id, m, p: pos, v: vel, a: V(), alive: true, trail: [] }; }
  // The real system on the site's date: positions from the orbits, velocities from a day's difference.
  function realStart(jd) {
    const out = [body("sun", MASS.sun, V(), V())];
    for (const id of ID.slice(1)) {
      const p = helioAU(id, jd, V()), p1 = helioAU(id, jd + 0.5, V()), p0 = helioAU(id, jd - 0.5, V());
      out.push(body(id, MASS[id], p, p1.sub(p0)));
    }
    return out;
  }
  const get = id => S.bodies.find(b => b.id === id);

  function accel() {
    const B = S.bodies;
    for (const b of B) b.a.set(0, 0, 0);
    for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) {
      const a = B[i], b = B[j];
      if (!a.alive || !b.alive) continue;
      const dx = b.p.x - a.p.x, dy = b.p.y - a.p.y, dz = b.p.z - a.p.z, r2 = dx * dx + dy * dy + dz * dz + 1e-10, ir3 = 1 / (r2 * Math.sqrt(r2));
      a.a.x += G * b.m * dx * ir3; a.a.y += G * b.m * dy * ir3; a.a.z += G * b.m * dz * ir3;
      b.a.x -= G * a.m * dx * ir3; b.a.y -= G * a.m * dy * ir3; b.a.z -= G * a.m * dz * ir3;
    }
  }
  // A step small enough for the closest pair (a fraction of their mutual "orbit time").
  function stepSize() {
    const B = S.bodies; let dt = 2;
    for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) {
      const a = B[i], b = B[j];
      if (!a.alive || !b.alive || a.m + b.m < 1e-9) continue;
      const r = a.p.distanceTo(b.p);
      dt = Math.min(dt, 0.015 * Math.sqrt(r * r * r / (G * (a.m + b.m))));
    }
    return Math.max(dt, 1e-4);
  }
  // Kick–drift–kick (leapfrog): energy stays honest over thousands of orbits.
  function advance(days) {
    let left = days, n = 0;
    while (left > 1e-9 && n < 4000) {
      const h = Math.min(left, stepSize());
      for (const b of S.bodies) if (b.alive) b.v.addScaledVector(b.a, h / 2);
      for (const b of S.bodies) if (b.alive) b.p.addScaledVector(b.v, h);
      accel();
      for (const b of S.bodies) if (b.alive) b.v.addScaledVector(b.a, h / 2);
      left -= h; S.days += h; n++;
      collide();
    }
  }
  // Two bodies closer than this (AU) merge: a planet into a star, or the lighter planet into the heavier one.
  const HIT = { star: 0.012, planet: 0.004 };
  const isStar = b => b.id === "sun" || b.id === "sun2";
  function collide() {
    const B = S.bodies;
    for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) {
      const a = B[i], b = B[j];
      if (!a.alive || !b.alive) continue;
      const lim = isStar(a) || isStar(b) ? HIT.star : HIT.planet;
      if (a.p.distanceTo(b.p) > lim) continue;
      const big = isStar(a) && !isStar(b) ? a : isStar(b) && !isStar(a) ? b : a.m >= b.m ? a : b, small = big === a ? b : a;
      if (small.m === 0 && isStar(small)) continue;
      big.v.multiplyScalar(big.m).addScaledVector(small.v, small.m).multiplyScalar(1 / (big.m + small.m || 1));
      big.m += small.m; small.alive = false;
      const who = NAME[small.id], when = `через ${years(S.days)}`;
      note("hit-" + small.id, isStar(big) ? `${who} ${verb(small.id, "впав", "впала")} на ${big.id === "sun" ? "Сонце" : "друге Сонце"} — ${when}.`
        : `${who} ${verb(small.id, "зіткнувся", "зіткнулася")} з ${WITH[big.id]} — ${when}.`);
    }
  }
  function years(d) {
    if (d < 60) return `${Math.max(1, Math.round(d))} ${plural(Math.max(1, Math.round(d)), ["добу", "доби", "діб"])}`;
    if (d < 730) return `${Math.round(d / 30.44)} ${plural(Math.round(d / 30.44), ["місяць", "місяці", "місяців"])}`;
    const y = Math.round(d / 365.25);
    return `${y} ${plural(y, ["рік", "роки", "років"])}`;
  }
  function plural(n, f) { const m10 = n % 10, m100 = n % 100; return m10 === 1 && m100 !== 11 ? f[0] : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? f[1] : f[2]; }
  function note(key, text) {
    if (S.events.has(key)) return;
    S.events.add(key);
    showToast(text, 5000);
  }
  // Planets that fly off: farther than 80 AU from the stars and faster than escape speed.
  function watch() {
    const stars = S.bodies.filter(b => isStar(b) && b.alive && b.m > 0);
    if (!stars.length) return;
    const M = stars.reduce((s, b) => s + b.m, 0), c = V(), cv = V();
    for (const s of stars) { c.addScaledVector(s.p, s.m / M); cv.addScaledVector(s.v, s.m / M); }
    for (const b of S.bodies) {
      if (!b.alive || isStar(b)) continue;
      const r = b.p.distanceTo(c), v = b.v.distanceTo(cv);
      if (r > 80 && v * v > 2 * G * M / r) note("out-" + b.id, `${NAME[b.id]} ${verb(b.id, "вилетів", "вилетіла")} за межі системи — через ${years(S.days)}.`);
    }
  }

  /* ---------- Scenarios ---------- */
  function setup(key) {
    S.scenario = SCENARIOS[key] ? key : "";
    S.bodies = realStart(S.jd0);
    S.days = 0; S.events.clear();
    const sun = get("sun"), earth = get("earth"), jup = get("jupiter");
    if (key === "two-suns") {
      // An equal star 9.5 AU away; both circle their midpoint, and the planets keep moving round the first one.
      const a = 9.5, v = Math.sqrt(G * 2 / a);
      const dir = V().set(-0.6, 0, 0.8).normalize(), side = V().set(dir.z, 0, -dir.x);
      const s2 = body("sun2", 1, dir.clone().multiplyScalar(a), side.clone().multiplyScalar(v / 2));
      for (const b of S.bodies) b.v.addScaledVector(side, -v / 2);
      S.bodies.push(s2);
    } else if (key === "jupiter-earth") {
      const p = earth.p.clone(), v = earth.v.clone();
      earth.p.copy(jup.p); earth.v.copy(jup.v); jup.p.copy(p); jup.v.copy(v);
    } else if (key === "heavy-sun") {
      sun.m = 2;
    } else if (key === "no-sun") {
      sun.m = 0;
    } else if (key === "stop-earth") {
      earth.v.set(0, 0, 0);
    }
    accel();
    for (const b of S.bodies) b.trail.length = 0;
    S.speed = SCENARIOS[key] ? SCENARIOS[key].speed : 3;
    if (S.sun2) S.sun2.visible = key === "two-suns";
    renderPanel();
  }

  /* ---------- Look ---------- */
  const TRAIL = 700;
  function makeTrails() {
    S.trails = {};
    for (const id of ID.concat("sun2")) {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(TRAIL * 3), 3));
      g.setDrawRange(0, 0);
      const col = id === "sun2" ? 0xffc070 : (byId[id] && byId[id].dot) || "#9fb2d8";
      const line = new THREE.Line(g, new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: 0.55 }));
      line.frustumCulled = false; line.visible = false;
      scene.add(line); S.trails[id] = line;
    }
    // the second Sun: a bright disc with the Sun's glow (no surface effects)
    const sun = byId.sun, g = new THREE.Group();
    g.add(new THREE.Mesh(new THREE.SphereGeometry(sun.radius * 0.95, 48, 32), new THREE.MeshBasicMaterial({ color: 0xffe2b0 })));
    g.add(glowSprite("255,170,90", sun.radius * 11, 0.24));
    g.visible = false; scene.add(g); S.sun2 = g;
  }
  const tS = V(), tRel = V();
  // Scene position of a body: relative to the first Sun (it stays in the middle of the screen), on the site's distance scale.
  function scenePos(b, out) { return toScene(tRel.copy(b.p).sub(get("sun").p), out); }
  function drawTrails() {
    for (const b of S.bodies) {
      const line = S.trails[b.id];
      if (!line || b.id === "sun") continue;
      line.visible = b.alive;
      if (!b.alive) continue;
      const p = scenePos(b, tS), tr = b.trail, last = tr[tr.length - 1];
      if (!last || last.distanceToSquared(p) > 0.25) { tr.push(p.clone()); if (tr.length > TRAIL) tr.shift(); }
      const arr = line.geometry.attributes.position.array;
      for (let k = 0; k < tr.length; k++) { arr[k * 3] = tr[k].x; arr[k * 3 + 1] = tr[k].y; arr[k * 3 + 2] = tr[k].z; }
      line.geometry.attributes.position.needsUpdate = true;
      line.geometry.setDrawRange(0, tr.length);
    }
  }
  // The Earth's temperature from the light it gets now (today's +15 °C at 1 AU from one Sun); a star's light ∝ mass^3.5.
  function earthTemp() {
    const e = get("earth");
    if (!e.alive) return null;
    let flux = 0;
    for (const s of S.bodies) if (isStar(s) && s.alive && s.m > 0) flux += Math.pow(s.m, 3.5) / Math.max(e.p.distanceToSquared(s.p), 1e-6);
    return flux <= 0 ? -270 : Math.max(-270, 288 * Math.pow(flux, 0.25) - 273);
  }

  /* ---------- Panel ---------- */
  const el = id => document.getElementById(id);
  function renderPanel() {
    const sc = SCENARIOS[S.scenario];
    el("sbTitle").textContent = sc ? sc.title : "Справжня Сонячна система";
    el("sbText").textContent = sc ? sc.text : "Тепер планети рухаються за законом тяжіння. Обери, що змінити, — і дивись, що станеться з усіма іншими.";
    document.querySelectorAll("#sbScenes button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.s === S.scenario)));
    el("sbSpeed").value = S.speed; el("sbSpeedOut").textContent = SPEEDS[S.speed][1];
  }
  let lastRead = "";
  function readout() {
    const t = earthTemp(), e = get("earth"), sun = get("sun");
    const temp = t === null ? "Землі більше немає" : `Земля: ${t > 0 ? "+" : t < 0 ? "−" : ""}${Math.abs(Math.round(t))} °C · ${e.p.distanceTo(sun.p).toFixed(2).replace(".", ",")} а. о. від Сонця`;
    const txt = `Минуло: ${S.days < 1 ? "0 діб" : years(S.days)} · ${temp}`;
    if (txt !== lastRead) { el("sbRead").textContent = txt; lastRead = txt; }
  }

  function open(key) {
    if (!S.trails) makeTrails();
    if (typeof endTour === "function" && document.body.classList.contains("touring")) endTour();
    S.on = true;
    S.jd0 = jdOf(state.simMs);
    document.body.classList.add("sandboxing");
    el("sandbox").hidden = false;
    el("sandboxBtn").setAttribute("aria-pressed", "true");
    for (const b of BODIES) {
      if (b.orbitLine) b.orbitLine.visible = false;
      if (!b.parent && b.id !== "sun" && !ID.includes(b.id)) b.group.visible = false;   // dwarf planets and comets
    }
    setup(key || "");
    if (state.index >= 0) showOverview();
    try { history.replaceState(null, "", "#sandbox" + (S.scenario ? "-" + S.scenario : "")); } catch (e) { /* not allowed here */ }
  }
  function close() {
    S.on = false;
    document.body.classList.remove("sandboxing");
    el("sandbox").hidden = true;
    el("sandboxBtn").setAttribute("aria-pressed", "false");
    for (const id in S.trails) S.trails[id].visible = false;
    S.sun2.visible = false;
    for (const b of BODIES) {
      if (b.orbitLine) b.orbitLine.visible = state.orbits;
      b.group.visible = true;
    }
    state.jumped = true;                              // glide back to the real places
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* not allowed here */ }
  }
  // One frame: run the physics, then put the bodies where it says. Returns the moons' clock for placeAll.
  function step(dt) {
    const days = state.paused ? 0 : dt * SPEEDS[S.speed][0];
    advance(days);
    watch();
    for (const b of S.bodies) {
      const B = byId[b.id];
      if (b.id === "sun2") { scenePos(b, S.sun2.position); S.sun2.visible = b.alive; continue; }
      if (!B) continue;
      if (b.id !== "sun") { B.group.visible = b.alive; tRel.copy(b.p).sub(get("sun").p); B.simAU = tRel.clone(); }
      else B.group.visible = b.m > 0;
    }
    drawTrails();
    readout();
    return { jd: S.jd0 + S.days, dDays: days, fine: days / Math.max(dt, 1e-3) <= 1 };
  }

  // Wire the panel.
  const wire = () => {
    el("sandboxBtn").addEventListener("click", () => { S.on ? close() : open(""); if (typeof setMenu === "function") setMenu(false); });
    el("sbClose").addEventListener("click", close);
    el("sbReset").addEventListener("click", () => setup(S.scenario));
    document.querySelectorAll("#sbScenes button").forEach(b => b.addEventListener("click", () => {
      const k = b.dataset.s === S.scenario ? "" : b.dataset.s;
      setup(k);
      try { history.replaceState(null, "", "#sandbox" + (k ? "-" + k : "")); } catch (e) { /* not allowed here */ }
    }));
    el("sbSpeed").addEventListener("input", e => { S.speed = +e.target.value; renderPanel(); });
  };
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", wire); else wire();

  return { get on() { return S.on; }, open, close, step, scenarios: Object.keys(SCENARIOS) };
})();
