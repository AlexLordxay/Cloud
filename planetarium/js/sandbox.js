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
  // The moons: drawn round their planets by the site, but set free when their planet is lost (or, in "stop-earth",
  // when only the planet stops) and then moved by gravity like the rest. Masses (Suns) and real orbit sizes (km).
  Object.assign(NAME, { moon: "Місяць", phobos: "Фобос", deimos: "Деймос", io: "Іо", europa: "Європа", ganymede: "Ганімед", callisto: "Каллісто",
    enceladus: "Енцелад", rhea: "Рея", titan: "Титан", miranda: "Міранда", titania: "Титанія", oberon: "Оберон", triton: "Тритон" });
  Object.assign(WITH, { moon: "Місяцем", phobos: "Фобосом", deimos: "Деймосом", io: "Іо", europa: "Європою", ganymede: "Ганімедом", callisto: "Каллісто",
    enceladus: "Енцеладом", rhea: "Реєю", titan: "Титаном", miranda: "Мірандою", titania: "Титанією", oberon: "Обероном", triton: "Тритоном" });
  const MOON_M = { moon: 3.694e-8, phobos: 5.4e-15, deimos: 7.4e-16, io: 4.49e-8, europa: 2.41e-8, ganymede: 7.45e-8, callisto: 5.42e-8,
    enceladus: 5.4e-11, rhea: 1.16e-9, titan: 6.76e-8, miranda: 3.3e-11, titania: 1.71e-9, oberon: 1.54e-9, triton: 1.08e-8 };
  const MOON_A = { moon: 384400, phobos: 9376, deimos: 23463, io: 421700, europa: 671034, ganymede: 1070412, callisto: 1882709,
    enceladus: 237948, rhea: 527108, titan: 1221870, miranda: 129390, titania: 435910, oberon: 583520, triton: 354759 };
  const MOON_IDS = Object.keys(MOON_M), MOONSET = new Set(MOON_IDS);
  const FEM = new Set(["earth", "venus", "io", "europa", "callisto", "rhea", "miranda", "titania"]);
  const fem = id => FEM.has(id);
  const verb = (id, m, f) => fem(id) ? f : m;
  // Simulated days per real second.
  const SPEEDS = [[0, "стоп"], [0.25, "6 год/с"], [2, "2 доби/с"], [10, "10 діб/с"], [60, "2 міс/с"], [365, "1 рік/с"], [3650, "10 років/с"]];
  const SCENARIOS = {
    "two-suns": { title: "Друге Сонце", speed: 5,
      text: "Ще одна така сама зоря на відстані Сатурна — і дві зорі кружляють одна навколо одної. Близькі планети ще тримаються свого Сонця, а дальні гіганти не мають шансів." },
    "jupiter-earth": { title: "Юпітер замість Землі", speed: 5,
      text: "Юпітер і Земля помінялися місцями. Велетень у 318 разів важчий за Землю тепер тягне сусідів — дивись на Марс і Венеру." },
    "heavy-sun": { title: "Сонце вдвічі важче", speed: 4,
      text: "Сонце раптом стало вдвічі масивнішим — і в 11 разів яскравішим. Планети рухаються надто повільно для нової сили тяжіння й падають на витягнуті орбіти." },
    "no-sun": { title: "Сонце зникло", speed: 5,
      text: "Сонця більше немає. Ніщо не тримає планети — вони летять по прямих, кожна туди, куди рухалася тієї миті. Світло зникне через 8 хвилин." },
    "bh-sun": { title: "Сонце — чорна діра", speed: 5,
      text: "Сонце стиснулося в чорну діру тієї самої маси — кульку завширшки 6 кілометрів. Чи впадуть у неї планети?" },
    "sgr-a": { title: "Стрілець A* замість Сонця", speed: 1,
      text: "На місці Сонця — Стрілець A*, чорна діра з центру нашої галактики, у 4,3 мільйона разів масивніша. Планети не втримаються на орбітах." },
    "stop-earth": { title: "Земля зупинилася", speed: 2,
      text: "Земля раптом зупинилася на своїй орбіті. Ніщо більше не відводить її вбік — і вона падає прямо на Сонце." },
  };
  const S = { on: false, bodies: [], days: 0, t: 0, rips: [], streams: [], speed: 5, scenario: "", jd0: 0, events: new Set(), trails: null, sun2: null, hits: [], booms: [], splashes: [], impacts: [], orphans: [], free: {}, shells: {}, log: [], slow: 1, director: true, holdUntil: 0, cool: {} };
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
  // The physics clock S.t runs in whole steps whose size depends only on where the bodies are — never on the frame
  // rate — so the same start always gives the same future (a story can be written for it). It runs a step ahead of
  // the shown clock S.days, and the bodies are drawn moved back by that small lag along their velocity.
  function advance(days) {
    S.days += days;
    let n = 0;
    while (S.t < S.days && n < 4000) {
      const h = stepSize();
      S.t0 = S.t;
      for (const b of S.bodies) { (b.p0 || (b.p0 = V())).copy(b.p); (b.v0 || (b.v0 = V())).copy(b.v); }
      for (const b of S.bodies) if (b.alive) b.v.addScaledVector(b.a, h / 2);
      for (const b of S.bodies) if (b.alive) b.p.addScaledVector(b.v, h);
      accel();
      for (const b of S.bodies) if (b.alive) b.v.addScaledVector(b.a, h / 2);
      S.t += h; n++;
      collide(); tides();
      if (S.trails) trailStep();
    }
    if (S.t < S.days) S.days = S.t;                 // too much for one frame: time waits for the physics
  }
  // Where a body is shown now (AU): on the smooth curve (cubic Hermite, from place and speed at both ends) through the
  // last physics step, at the shown clock — so a planet swinging round another moves smoothly, not in jumps.
  const shown = (b, out) => {
    const H = S.t - S.t0;
    if (!b.p0 || !(H > 0) || S.days >= S.t) return out.copy(b.p);
    const u = Math.min(1, Math.max(0, (S.days - S.t0) / H)), u2 = u * u, u3 = u2 * u;
    return out.copy(b.p0).multiplyScalar(2 * u3 - 3 * u2 + 1).addScaledVector(b.v0, (u3 - 2 * u2 + u) * H)
      .addScaledVector(b.p, -2 * u3 + 3 * u2).addScaledVector(b.v, (u3 - u2) * H);
  };
  const tLag = new THREE.Vector3();
  // Two bodies closer than this (AU) merge: a planet into a star, or the lighter planet into the heavier one.
  const HIT = { star: 0.006, planet: 0.004, moon: 0.0004 };
  const isStar = b => b.id === "sun" || b.id === "sun2";
  const shines = s => isStar(s) && s.alive && s.m > 0 && !s.bh;   // a black hole has the mass but gives no light
  // A black hole's horizon (AU): the Schwarzschild radius, 2.95 km per solar mass.
  const rsAU = b => 2.953 * b.m / 1.495978707e8;
  // Tidal disruption: a planet of radius R and mass m is torn apart closer than R·(M/m)^⅓ to a mass M — the pull on its
  // near side then beats its own gravity. The news of the black hole reaches it at the speed of light (r · 8.3 min/AU).
  const R_KM = { mercury: 2440, venus: 6052, earth: 6371, mars: 3390, jupiter: 71492, saturn: 58232, uranus: 25559, neptune: 24764,
    moon: 1737, io: 1822, europa: 1561, ganymede: 2634, callisto: 2410, titan: 2575, triton: 1353, rhea: 764, titania: 789, oberon: 761 };
  const tidalAU = (b, h) => R_KM[b.id] / 1.495978707e8 * Math.cbrt(h.m / b.m);
  function tides() {
    const h = get("sun");
    if (!h || !h.bh || !h.alive) return;
    for (const b of S.bodies) {
      if (!b.alive || !R_KM[b.id]) continue;
      const r = b.p.distanceTo(h.p);
      if (r < tidalAU(b, h) && S.t > r * 499.005 / 86400) {
        b.alive = false; S.rips.push({ id: b.id, p: b.p.clone().sub(h.p), v: b.v.clone().sub(h.v) }); S.orphans.push(b);
        note("rip-" + b.id, `${ACC[b.id]} розірвало на шматки — через ${years(S.t)}.`);
      }
    }
  }
  const ACC = { mercury: "Меркурій", venus: "Венеру", earth: "Землю", mars: "Марс", jupiter: "Юпітер", saturn: "Сатурн", uranus: "Уран", neptune: "Нептун",
    moon: "Місяць", io: "Іо", europa: "Європу", ganymede: "Ганімед", callisto: "Каллісто", titan: "Титан", triton: "Тритон", rhea: "Рею", titania: "Титанію", oberon: "Оберон" };
  function collide() {
    const B = S.bodies;
    for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) {
      const a = B[i], b = B[j];
      if (!a.alive || !b.alive) continue;
      const bh = a.bh ? a : b.bh ? b : null;
      const lim = bh ? Math.max(HIT.star, rsAU(bh)) : isStar(a) || isStar(b) ? HIT.star : MOONSET.has(a.id) || MOONSET.has(b.id) ? HIT.moon : HIT.planet;
      if (a.p.distanceTo(b.p) > lim) continue;
      const big = isStar(a) && !isStar(b) ? a : isStar(b) && !isStar(a) ? b : a.m >= b.m ? a : b, small = big === a ? b : a;
      if (small.m === 0 && isStar(small)) continue;
      big.v.multiplyScalar(big.m).addScaledVector(small.v, small.m).multiplyScalar(1 / (big.m + small.m || 1));
      big.m += small.m; small.alive = false; S.orphans.push(small);

      S.hits.push({ small: small.id, big: big.id, star: isStar(big) });
      const who = NAME[small.id], when = `через ${years(S.days)}`;
      note("hit-" + small.id, isStar(big) ? `${who} ${verb(small.id, "впав", "впала")} на ${big.id === "sun" ? "Сонце" : "друге Сонце"} — ${when}.`
        : `${who} ${verb(small.id, "зіткнувся", "зіткнулася")} з ${WITH[big.id]} — ${when}.`);
    }
  }
  function years(d) {
    if (d < 1 / 24) { const m = Math.max(1, Math.round(d * 1440)); return `${m} ${plural(m, ["хвилину", "хвилини", "хвилин"])}`; }
    if (d < 1) { const h = Math.round(d * 24); return `${h} ${plural(h, ["годину", "години", "годин"])}`; }
    if (d < 60) return `${Math.max(1, Math.round(d))} ${plural(Math.max(1, Math.round(d)), ["добу", "доби", "діб"])}`;
    if (d < 730) return `${Math.round(d / 30.44)} ${plural(Math.round(d / 30.44), ["місяць", "місяці", "місяців"])}`;
    const y = Math.round(d / 365.25);
    return `${y} ${plural(y, ["рік", "роки", "років"])}`;
  }
  function plural(n, f) { const m10 = n % 10, m100 = n % 100; return m10 === 1 && m100 !== 11 ? f[0] : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? f[1] : f[2]; }
  function note(key, text) {
    if (S.events.has(key)) return;
    S.events.add(key);
    S.log.unshift(text);
    if (S.log.length > 5) S.log.pop();
    renderLog();
    if (!story.on) showToast(text, 3500);
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
  // A story starts from one fixed moment (the bodies' exact places and speeds), so its future is always the same and
  // the words can be written for it. "two-suns": the system of 1 September 2026 with the second Sun already added;
  // "heavy-sun": the same day, the Sun twice as heavy; "no-sun": the same day, the Sun gone;
  // "jupiter-earth": the same day, the Earth and Jupiter swapped;
  // "bh-sun" / "sgr-a": the same day, the Sun a black hole of its own mass / of Sagittarius A*'s (4.3 million Suns).
  const STORY_START = {
    "sgr-a": {"jd":2461284.5,"bodies":[["sun",4300000,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "bh-sun": {"jd":2461284.5,"bodies":[["sun",1,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "jupiter-earth": {"jd":2461284.5,"bodies":[["sun",1,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "no-sun": {"jd":2461284.5,"bodies":[["sun",0,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "heavy-sun": {"jd":2461284.5,"bodies":[["sun",2,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "two-suns": {"jd":2461284.5,"bodies":[["sun",1,[0,0,0],[-0.0031571457238594816,0,-0.002367859292894611]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.012224267134282077,-0.0013533878243529099,0.024368291502649082]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.013080441262917427,-0.0007747289772347885,-0.0141722872564881]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.0029460036013692257,-9.606720727967957e-07,-0.018279583637697758]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.01577509355473859,0.00043480529313185204,-0.008351214392545256]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.009139037899099181,0.0001520486531615614,0.002007474772134824]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.004413424248456347,-4.529654143409223e-05,-0.00785108460484761]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0066685439960156665,5.15837649088316e-05,-0.0040120571890285145]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.003312304140324666,-6.139143961414462e-05,-0.005522563781319864]],["sun2",1,[-5.7,0,7.6000000000000005],[0.0031571457238594816,0,0.002367859292894611]]]},
  };
  // Set a moon free: from now on a body of its own, at its real place round the planet (in the direction it is drawn)
  // with the planet's velocity v plus its own orbital speed. It is still drawn at the site's (much larger) distance
  // from where it really is; that offset fades out over a few seconds unless keep (then it stays: the moon is drawn
  // where it was and simply moves on).
  function freeMoon(id, parent, v, keep) {
    const B = byId[id];
    if (!B || S.free[id] || !MOON_M[id]) return;
    // where it is drawn, relative to its planet (world axes are the simulation's axes)
    B.group.updateWorldMatrix(true, false); B.group.getWorldPosition(tA);
    const P = B.parent; P.group.updateWorldMatrix(true, false); P.group.getWorldPosition(tB);
    const off = tA.clone().sub(tB), dir = off.lengthSq() > 0 ? off.clone().normalize() : V().set(1, 0, 0);
    const local = B.group.position.clone();
    const aAU = MOON_A[id] / 1.495978707e8, vo = Math.sqrt(G * parent.m / aAU);
    const along = V().crossVectors(UP, dir).normalize();
    const mb = body(id, MOON_M[id], parent.p.clone().addScaledVector(dir, aAU), v.clone().addScaledVector(along, vo));
    mb.a.set(0, 0, 0); mb.r0 = mb.p.length();
    S.bodies.push(mb);
    scene.add(B.group); B.group.position.copy(tA);
    B.sbFree = true;
    S.free[id] = { b: mb, B, off, local, t: 0, keep };
  }
  function freeMoons(dt) {
    while (S.orphans.length) {
      const pb = S.orphans.shift(), P = byId[pb.id];
      if (P && P.moons) for (const m of P.moons) freeMoon(m.id, pb, pb.v, false);
    }
    for (const id in S.free) {
      const f = S.free[id], B = f.B;
      f.t += dt;
      B.group.visible = f.b.alive;
      if (!f.b.alive) continue;
      const k = f.keep ? 1 : Math.exp(-f.t / 2.5);
      scenePos(f.b, B.group.position).addScaledVector(f.off, k);
    }
  }
  function unfreeMoons() {
    for (const id in S.free) {
      const f = S.free[id], B = f.B;
      B.plane.add(B.group); B.group.position.copy(f.local);   // back on its orbit round the planet
      B.sbFree = false; B.group.visible = true; B.group.scale.setScalar(1); B.group.quaternion.identity(); B.stretched = false;
    }
    S.free = {}; S.orphans.length = 0;
  }
  function setup(key, fixed) {
    unfreeMoons();
    S.scenario = SCENARIOS[key] ? key : "";
    const start = fixed && STORY_START[key];
    if (start) S.jd0 = start.jd;
    S.bodies = start ? start.bodies.map(([id, m, p, v]) => body(id, m, V().fromArray(p), V().fromArray(v))) : realStart(S.jd0);
    S.days = 0; S.t = 0; S.t0 = 0; S.events.clear(); S.rips.length = 0; clearStreams();
    if (S.on) byId.sun.group.scale.setScalar(SUN_K);   // (a black-hole story may have shrunk it) S.hits.length = 0; clearBooms(); hideShells();
    S.log.length = 0; S.slow = 1; S.cool = {}; endShot(false); renderLog();
    const sun = get("sun"), earth = get("earth"), jup = get("jupiter");
    sun.bh = key === "bh-sun" || key === "sgr-a";
    if (!start && key === "sgr-a") sun.m = 4.3e6;
    if (start) { /* already set */ } else if (key === "two-suns") {
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
      // only the Earth stops: the Moon keeps its 30 km/s and flies on along the old orbit — far too fast for the
      // Earth to hold it (it would need to move under ~1.4 km/s relative to the Earth to stay)
      const v0 = earth.v.clone();
      earth.v.set(0, 0, 0);
      freeMoon("moon", earth, v0, true);
    }
    accel();
    for (const b of S.bodies) { b.trail.length = 0; b.r0 = b.p.length(); }
    S.speed = SCENARIOS[key] ? SCENARIOS[key].speed : 5;
    if (S.sun2) S.sun2.visible = key === "two-suns";
    renderPanel();
  }

  /* ---------- Look ---------- */
  const TRAIL = 1200;
  function makeTrails() {
    S.trails = {};
    for (const id of ID.concat("sun2")) {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(new Float32Array((TRAIL + 1) * 3), 3));
      g.setAttribute("color", new THREE.BufferAttribute(new Float32Array((TRAIL + 1) * 4), 4));   // rgb + fading alpha
      g.setDrawRange(0, 0);
      const col = new THREE.Color(id === "sun2" ? 0xffc070 : (byId[id] && byId[id].dot) || "#9fb2d8");
      const line = new THREE.Line(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false }));
      line.userData.col = col;
      line.frustumCulled = false; line.visible = false;
      scene.add(line); S.trails[id] = line;
    }
    // the second Sun: a bright disc with the Sun's glow (no surface effects)
    const sun = byId.sun, g = new THREE.Group();
    // the same living surface as the Sun's own (its shader, shared), a touch smaller
    const surf = typeof sunFx !== "undefined" && sunFx && sunFx.material ? sunFx.material : new THREE.MeshBasicMaterial({ color: 0xffe2b0 });
    g.add(new THREE.Mesh(new THREE.SphereGeometry(sun.radius * 0.95 * SUN_K, 64, 48), surf));
    g.add(glowSprite("255,170,90", sun.radius * 11 * SUN_K, 0.24));
    g.visible = false; scene.add(g); S.sun2 = g;
  }
  const tS = V(), tRel = V();
  // Scene position of a body: relative to the first Sun (it stays in the middle of the screen), on the site's distance scale.
  function scenePos(b, out) { return sbToScene(shown(b, tRel).sub(shown(get("sun"), tLag)), out); }
  // The sandbox's own distance scale: the site's beyond 0.05 AU, and inside it — where the site puts everything on the
  // Sun's surface — a log scale down to the Sun's real radius. With the Sun drawn at half size there, a close pass or a
  // fall into it can be seen instead of happening "inside" the Sun.
  const SUN_K = 0.5, R_SUN_AU = 0.00465;
  function sbDist(au) {
    if (au >= 0.05) return sceneDist(au);
    const r0 = byId.sun.radius * SUN_K;
    if (au <= R_SUN_AU) return r0 * au / R_SUN_AU;
    return r0 + (sceneDist(0.05) - r0) * Math.log(au / R_SUN_AU) / Math.log(0.05 / R_SUN_AU);
  }
  function sbToScene(vAU, out) { const r = vAU.length(); return out.copy(vAU).multiplyScalar(r > 0 ? sbDist(r) / r : 0); }
  // Trail points come from the physics steps (several per frame when time runs fast), so a fast orbit draws as a
  // smooth curve rather than a polygon of one point per frame.
  const tT = new THREE.Vector3(), tSunP = new THREE.Vector3();
  function trailStep() {
    const sun = get("sun");
    for (const b of S.bodies) {
      if (!b.alive || b.id === "sun") continue;
      sbToScene(tT.copy(b.p).sub(sun.p), tSunP);
      const tr = b.trail, last = tr[tr.length - 1];
      if (!last || last.distanceToSquared(tSunP) > 0.04) { const q = tSunP.clone(); q.t = S.t; tr.push(q); if (tr.length > TRAIL) tr.shift(); }
    }
  }
  function drawTrails() {
    for (const b of S.bodies) {
      const line = S.trails[b.id];
      if (!line || b.id === "sun") continue;
      line.visible = b.alive;
      if (!b.alive) continue;
      // the physics runs a step ahead: draw the points already reached, then end exactly at the planet
      let m = b.trail.length;
      while (m > 0 && b.trail[m - 1].t > S.days) m--;
      const tr = b.trail.slice(0, m);
      tr.push(scenePos(b, tS).clone());
      const arr = line.geometry.attributes.position.array, ca = line.geometry.attributes.color.array, c = line.userData.col;
      // the trail fades toward its tail; in a story the planet in the shot keeps a bright one, the rest step back
      const lead = story.on && (shot.on && shot.b && shot.b.id === b.id || (story.steps[story.i].hl || []).includes(b.id) || story.steps[story.i].shot.b === b.id || story.steps[story.i].shot.o === b.id), top = !story.on ? 0.7 : lead ? 1 : 0.32, n = tr.length;
      // fades along its length (the last ~70 scene units), however fast time runs
      let along = 0;
      for (let k = n - 1; k >= 0; k--) {
        arr[k * 3] = tr[k].x; arr[k * 3 + 1] = tr[k].y; arr[k * 3 + 2] = tr[k].z;
        if (k < n - 1) along += tr[k].distanceTo(tr[k + 1]);
        const f = Math.max(0, 1 - along / 70);
        ca[k * 4] = c.r; ca[k * 4 + 1] = c.g; ca[k * 4 + 2] = c.b; ca[k * 4 + 3] = top * f * f;
      }
      line.geometry.attributes.position.needsUpdate = true; line.geometry.attributes.color.needsUpdate = true;
      line.geometry.setDrawRange(0, tr.length);
    }
  }
  // The Earth's temperature from the light it gets now (today's +15 °C at 1 AU from one Sun); a star's light ∝ mass^3.5.
  function earthTemp() {
    const e = get("earth");
    if (!e.alive) return null;
    if (COLD[S.scenario]) return cooled(288) - 273;
    if (S.scenario === "jupiter-earth") { let f = 0; for (const s of S.bodies) if (shines(s)) f += Math.pow(s.m, 3.5) / Math.max(e.p.distanceToSquared(s.p), 1e-6); return Math.max(288 * Math.pow(f, 0.25), cooled(288)) - 273; }
    let flux = 0;
    for (const s of S.bodies) if (shines(s)) flux += Math.pow(s.m, 3.5) / Math.max(e.p.distanceToSquared(s.p), 1e-6);
    return flux <= 0 ? -270 : Math.max(-270, 288 * Math.pow(flux, 0.25) - 273);
  }

  /* ---------- Effects: heat, frost, explosions ---------- */
  // A body's temperature (K) as a bare rock in the light it gets now: 278 K at 1 AU from one Sun; a star's light ∝ mass^3.5.
  // Without any star a planet does not freeze at once: its air, oceans and rock hold heat. Earth: below zero within a
  // week, about −70 °C after a year, −240 °C only after a million years (an interpolation in log time); others alike.
  const COLD = { "no-sun": 1, "bh-sun": 1, "sgr-a": 1 };   // scenarios where the light is gone
  const COOL = [[0, 0], [0.006, 0], [7, 0.125], [60, 0.24], [365, 0.345], [3650, 0.45], [1e5, 0.65], [1e6, 1]];
  function cooled(T0) {
    const d = S.days; let k = 1;
    while (k < COOL.length - 1 && d > COOL[k][0]) k++;
    const [d0, g0] = COOL[k - 1], [d1, g1] = COOL[k];
    const f = d <= d0 ? 0 : Math.min(1, Math.log((d + 1e-3) / (d0 + 1e-3)) / Math.log((d1 + 1e-3) / (d0 + 1e-3)));
    return T0 - (T0 - 33) * (g0 + (g1 - g0) * f);
  }
  function tempK(b) {
    if (COLD[S.scenario]) return cooled(278 / Math.sqrt(b.r0 || 1));
    if (S.scenario === "jupiter-earth" && b.id === "earth") return Math.max(eqK(b), cooled(278));   // it cools for years
    return eqK(b);
  }
  function eqK(b) {
    let flux = 0;
    for (const s of S.bodies) if (shines(s) && s !== b) flux += Math.pow(s.m, 3.5) / Math.max(b.p.distanceToSquared(s.p), 1e-8);
    return 278 * Math.pow(flux, 0.25);
  }
  const ROCKY = ["mercury", "venus", "earth", "mars"], GIANTS = ["jupiter", "saturn", "uranus", "neptune"];
  // How a planet changes with the light it gets, as in reality, in stages by its bare-rock temperature T (K):
  //  the Earth dries out first (330–520 K: the oceans boil off, it turns to desert, the clouds go);
  //  rocky planets char and crack (600–1100 K: a dark crust with magma glowing through the cracks, more and more of them);
  //  then melt (1100–1700 K: a sea of moving lava) and boil off a tail of vapour streaming away from the star (from ~900 K);
  //  gas giants have no ground: they glow hotter and hotter and blow off a tail; rocky ones frost over in the cold.
  // All of it is a shell over the planet's own material, shaded by the hottest star, plus a glow and a tail.
  const ramp = (x, a, b) => Math.min(1, Math.max(0, (x - a) / (b - a)));
  let tailTex = null;

  /* ---------- Fire: a plume of burning rock and smoke, sparks, a jet ---------- */
  // A tapered tube along +y from 0 (the base) to 1 (the end), shaped in the vertex shader: R the radius at the base,
  // len its length, wid how many times wider it gets. The fire is bright where the tube is seen face-on (its middle)
  // and fades to the sides, so it reads as a glowing volume; turbulence (noise) streams along it. A second, wider tube
  // of dark smoke takes over further out (normal blending: it darkens the bright Sun behind it).
  const PLUME_VS = NOISE_GLSL + `uniform float R; uniform float len; uniform float wid; uniform float time; varying vec3 vN; varying vec3 vV; varying vec3 vM; varying float vY; varying vec2 vCS;
    void main(){ float y = position.y; float rad = R * mix(0.75, wid, pow(y, 1.1));   // slim at first: it comes out from behind the planet
      // not a cone: the edge bulges and pinches (more so further out), and the whole plume sways and curls
      float ang = atan(position.z, position.x);
      rad *= 1.0 + (0.18 + 0.5 * y) * snoise(vec3(cos(ang) * 1.3, sin(ang) * 1.3, y * 3.0 - time * 0.8));
      float slope = R * (wid - 0.75) * 1.1 * pow(max(y, 0.001), 0.1) / len;          // the cone's own normal (its edges then fade out)
      vec3 p = vec3(position.x * rad, y * len, position.z * rad);
      p.x += R * 1.4 * y * y * snoise(vec3(y * 1.6 - time * 0.35, 1.7, 0.0));
      p.z += R * 1.4 * y * y * snoise(vec3(y * 1.6 - time * 0.35, 5.3, 2.0));
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      vN = normalize(normalMatrix * normalize(vec3(position.x, -slope, position.z))); vV = normalize(-mv.xyz); vM = mv.xyz; vY = y; vCS = position.xz;
      gl_Position = projectionMatrix * mv; }`;
  // (pc, pr: the planet's centre in view space and its radius — fire passing in front of the planet is thinned, so
  // its molten face still shows through)
  const PLUME_FRONT = `uniform vec3 pc; uniform float pr;
    float overPlanet(vec3 m){ if (pr <= 0.0) return 0.0; vec3 d = normalize(m); float t = dot(pc, d);
      float perp = length(pc - d * t); return (1.0 - smoothstep(pr * 0.8, pr * 1.05, perp)) * step(length(m), length(pc)); }`;
  const FIRE_FS = PLUME_FRONT + `uniform float time; uniform float k; uniform float stretch; varying vec3 vN; varying vec3 vV; varying vec3 vM; varying float vY; varying vec2 vCS;
    void main(){
      float core = abs(dot(normalize(vN), normalize(vV)));
      vec3 q = vec3(vCS * 1.8, vY * stretch - time * 1.6);
      float n = fbm2(q) * 0.6 + 0.5, n2 = snoise(q * 2.2 + vec3(0.0, 4.0, -time * 1.2)) * 0.5 + 0.5;
      // soft tongues of flame, stretched along the flow, breaking up into wisps further out
      float flick = smoothstep(0.3 + 0.3 * vY, 0.85, n * 0.8 + n2 * 0.32);
      // ragged sides and a ragged end: no straight edges
      float edge = smoothstep(0.12, 0.65, core + (n2 - 0.5) * 0.7);
      float along = pow(1.0 - vY, 1.3) * smoothstep(0.0, 0.05, vY) * smoothstep(1.0, 0.55, vY + (n - 0.5) * 0.5);
      float I = edge * core * along * (0.1 + 1.25 * flick) * k * (1.0 - 0.55 * overPlanet(vM));
      float t = clamp(vY * 1.3 + (1.0 - flick) * 0.45, 0.0, 1.0);
      vec3 col = mix(vec3(1.0, 0.92, 0.72), vec3(1.0, 0.58, 0.16), smoothstep(0.0, 0.28, t));
      col = mix(col, vec3(0.9, 0.22, 0.03), smoothstep(0.28, 0.6, t));
      col = mix(col, vec3(0.35, 0.05, 0.01), smoothstep(0.6, 1.0, t));
      gl_FragColor = vec4(col, clamp(I, 0.0, 1.0)); }`;
  const SMOKE_FS = PLUME_FRONT + `uniform float time; uniform float k; uniform float stretch; varying vec3 vN; varying vec3 vV; varying vec3 vM; varying float vY; varying vec2 vCS;
    void main(){
      float core = pow(abs(dot(normalize(vN), normalize(vV))), 0.9) * (1.0 - 0.7 * overPlanet(vM));
      vec3 q = vec3(vCS * 1.1, vY * stretch * 0.7 - time * 0.9);
      float n = fbm2(q) * 0.6 + 0.5, n2 = snoise(q * 2.3 + vec3(0.0, 5.0, -time * 0.6)) * 0.5 + 0.5;
      core *= smoothstep(0.1, 0.6, core + (n - 0.5) * 0.8);
      float d = smoothstep(0.2, 0.75, n * 0.75 + n2 * 0.4);
      float a = core * d * smoothstep(0.12, 0.42, vY) * pow(1.0 - vY, 1.2) * k * 0.95;
      gl_FragColor = vec4(mix(vec3(0.03, 0.022, 0.02), vec3(0.16, 0.09, 0.05), n2), clamp(a, 0.0, 0.9)); }`;
  let plumeGeo = null;
  function firePlume(R, parent = scene) {
    if (!plumeGeo) { plumeGeo = new THREE.CylinderGeometry(1, 1, 1, 28, 40, true); plumeGeo.translate(0, 0.5, 0); }
    const mk = (fs, add, wid) => {
      const u = { time: { value: Math.random() * 40 }, k: { value: 0 }, R: { value: R }, len: { value: R }, wid: { value: wid }, stretch: { value: 5 }, pc: { value: V() }, pr: { value: 0 } };
      const m = new THREE.Mesh(plumeGeo, new THREE.ShaderMaterial({ uniforms: u, vertexShader: PLUME_VS, fragmentShader: NOISE_GLSL + fs,
        transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: add ? THREE.AdditiveBlending : THREE.NormalBlending }));
      m.frustumCulled = false; return { m, u };
    };
    const smoke = mk(SMOKE_FS, false, 3.6), fire = mk(FIRE_FS, true, 2.2);
    smoke.m.renderOrder = 3; fire.m.renderOrder = 4;
    const g = new THREE.Group(); g.add(smoke.m, fire.m); g.visible = false; parent.add(g);
    return { g, fire, smoke };
  }
  const Y_AXIS = new THREE.Vector3(0, 1, 0), qPl = new THREE.Quaternion();
  // k 0..1 how fiercely the planet boils; dir the way the plume streams; R the planet's radius on the screen
  function firePlumeSet(pl, k, pos, dir, R, dt) {
    pl.g.visible = k > 0.01;
    if (!pl.g.visible) return;
    pl.g.position.copy(pos).addScaledVector(dir, R * 0.25); pl.g.quaternion.copy(qPl.setFromUnitVectors(Y_AXIS, dir));
    const L = R * (2.5 + 10 * k);
    for (const [part, len, wid] of [[pl.fire, L, 1.7 + 1.2 * k], [pl.smoke, L * 1.7, 2.6 + 2.2 * k]]) {
      part.u.k.value = Math.min(1, k * 1.4); part.u.R.value = R; part.u.len.value = len; part.u.wid.value = wid;
      part.u.stretch.value = 2.5 + len / R * 0.35; part.u.time.value += dt;
      part.u.pc.value.copy(pos).applyMatrix4(camera.matrixWorldInverse); part.u.pr.value = R;
    }
  }
  // Sparks: drops of molten rock thrown off the hot side, swept back with the plume and left behind as the planet
  // races on, cooling from yellow to red as they go.
  function sparks(sh, k, pos, dir, sunDir, R, dt) {
    sh.tail.visible = k > 0.01 || sh.seeds.some(q => q.age < q.life);
    if (!sh.tail.visible) return;
    sh.tail.material.size = R * 0.16;
    const pa = sh.tail.geometry.attributes.position, ca = sh.tail.geometry.attributes.color;
    for (let i = 0; i < sh.seeds.length; i++) {
      const q = sh.seeds[i];
      q.age += dt;
      if (q.age >= q.life && k > 0.01 && Math.random() < k * dt * 6) {
        // from the sunward half, near the limb
        tUp.set(Math.random() * 2 - 1, Math.random() * 2 - 1, Math.random() * 2 - 1).normalize().addScaledVector(sunDir, 0.5).normalize();
        q.p.copy(pos).addScaledVector(tUp, R * 1.02);
        q.v.copy(dir).multiplyScalar(R * (1.2 + Math.random() * 3.2)).addScaledVector(tUp, R * (0.3 + Math.random() * 0.9));
        q.age = 0; q.life = 0.7 + Math.random() * 1.1;
      }
      if (q.age >= q.life) { ca.setXYZ(i, 0, 0, 0); continue; }
      q.p.addScaledVector(q.v, dt); q.v.multiplyScalar(Math.exp(-dt * 0.6));
      pa.setXYZ(i, q.p.x, q.p.y, q.p.z);
      const f = q.age / q.life, b = (1 - f) * (1 - f) * 1.3;
      ca.setXYZ(i, b, b * (0.75 - 0.5 * f), b * (0.35 - 0.3 * f));
    }
    pa.needsUpdate = true; ca.needsUpdate = true;
  }
  function makeShells() {
    tailTex = glowSprite("255,255,255", 1, 1).material.map;
    for (const id of ID.slice(1).concat(MOON_IDS.filter(m => byId[m]))) {
      const B = byId[id], gas = GIANTS.includes(id), moon = MOONSET.has(id);
      const u = { dry: { value: 0 }, crack: { value: 0 }, melt: { value: 0 }, frost: { value: 0 }, flash: { value: 0 }, dark: { value: 0 },
        time: { value: Math.random() * 50 }, sunDir: { value: new THREE.Vector3(1, 0, 0) }, hitDir: { value: new THREE.Vector3(1, 0, 0) } };
      const m = new THREE.Mesh(new THREE.SphereGeometry(B.radius * 1.018, moon ? 48 : 96, moon ? 32 : 64), new THREE.ShaderMaterial({
        uniforms: u, transparent: true, depthWrite: false, defines: gas ? { GAS: 1 } : {},
        vertexShader: `varying vec3 vN; varying vec3 vW; varying vec3 vP;
          void main(){ vP = normalize(position); vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
        fragmentShader: NOISE_GLSL + `uniform float dry; uniform float crack; uniform float melt; uniform float frost; uniform float flash; uniform float dark; uniform float time; uniform vec3 sunDir; uniform vec3 hitDir;
          varying vec3 vN; varying vec3 vW; varying vec3 vP;
          void main(){
            vec3 N = normalize(vN), V = normalize(cameraPosition - vW);
            float ndl = dot(N, sunDir), lit = 0.05 + 0.95 * max(ndl, 0.0), rim = 1.0 - max(dot(N, V), 0.0);
            float n = fbm(vP * 2.5) * 0.5 + 0.5;
            vec3 col = vec3(0.0); float a = 0.0;
          #ifndef GAS
            // dry: sand and rock, patchy at first, then everywhere (the oceans gone)
            vec3 desert = mix(vec3(0.42, 0.27, 0.15), vec3(0.78, 0.6, 0.38), smoothstep(0.3, 0.75, n));
            float da = dry * smoothstep(0.75 - dry * 0.9, 0.85 - dry * 0.9, n + 0.15);
            // charred crust with cracks of glowing magma that widen and multiply as it heats
            vec3 crust = mix(vec3(0.07, 0.05, 0.045), vec3(0.2, 0.13, 0.09), n);
            float r = 1.0 - abs(snoise(vP * 3.5) * 0.65 + snoise(vP * 8.0) * 0.35);
            float cr = smoothstep(0.985 - 0.2 * crack, 1.0, r) * crack;
            vec3 surf = mix(desert, crust, smoothstep(0.0, 0.6, crack));
            float sa = max(da, smoothstep(0.0, 0.35, crack));
            col = surf * lit * sa;
            a = sa;
            vec3 magma = mix(vec3(1.0, 0.25, 0.03), vec3(1.0, 0.7, 0.25), cr);
            col += magma * cr * 2.2;
            a = max(a, cr);
            // molten: an ocean of lava. Convection cells — bright seams where hot rock wells up, cooling crust between —
            // drifting slowly; yellow to white-hot on the side facing the star, dull red on the night side (never a
            // featureless white ball: the brightest seams stay under ~1.2)
            float lv = fbm(vP * 3.0 + vec3(time * 0.05, time * 0.03, 0.0)) * 0.5 + 0.5;
            float cell = 1.0 - abs(snoise(vP * 7.0 + vec3(0.0, time * 0.06, time * 0.04)));
            float seam = cell * cell * cell * cell * cell * cell;
            float day = smoothstep(-0.35, 0.85, ndl);
            float rafts = smoothstep(0.5, 0.68, fbm(vP * 5.0 - vec3(0.0, time * 0.04, 0.0)) * 0.5 + 0.5) * (1.0 - 0.7 * melt * day);
            float glow = (0.35 + 0.65 * lv) * (0.45 + 0.55 * day) + seam * (0.6 + 0.6 * day);
            vec3 lava = mix(vec3(0.5, 0.05, 0.01), vec3(1.0, 0.42, 0.07), clamp(glow, 0.0, 1.0));
            lava = mix(lava, vec3(1.0, 0.84, 0.5), smoothstep(0.8, 1.3, glow) * day * melt);
            lava *= 0.72 + 0.38 * min(glow, 1.25);
            lava = mix(lava, crust * (0.25 + 0.75 * lit) + vec3(0.3, 0.05, 0.0) * seam, rafts);
            col = mix(col, lava, melt);
            a = mix(a, 1.0, melt);
          #else
            // a gas giant heating up: its cloud bands glow, deep red to orange, yellow-white where they face the star
            // (it covers the planet's own colours as it heats: a mix of the two looked sickly green)
            float bands = 0.5 + 0.5 * sin(vP.y * 18.0 + fbm(vP * 3.0 + time * 0.04) * 3.0);
            float day = smoothstep(-0.4, 0.9, ndl);
            vec3 hot = mix(vec3(0.42, 0.06, 0.02), vec3(1.0, 0.48, 0.12), bands);
            hot = mix(hot, vec3(1.0, 0.8, 0.5), smoothstep(0.55, 1.0, bands * day) * melt);
            hot *= 0.45 + 0.8 * day;
            float ga = clamp(melt * 1.4, 0.0, 1.0) * (0.8 + 0.2 * bands);
            col = hot * ga; a = ga;
          #endif
            // the glowing limb of a hot planet, and the flash of an impact
            float hotRim = max(melt, crack * 0.6) * rim * rim;
            float fl = flash * (0.2 + 0.8 * pow(max(dot(N, hitDir), 0.0), 1.5));    // brightest on the side that was struck
            col += vec3(1.0, 0.4, 0.08) * (hotRim * 1.0 + fl * 1.6);
            a = max(a, max(hotRim, fl));
            // frost in the cold (rocky planets)
            float fa = frost * smoothstep(0.62 - 0.75 * frost, 0.7 - 0.55 * frost, n);   // deep cold: ice everywhere
            col = mix(col, vec3(0.88, 0.94, 1.0) * (0.25 + 0.75 * lit), fa);
            a = max(a, fa);
            // no star at all: only starlight — the planet all but goes out
            col *= 1.0 - dark; a += dark * (1.0 - a);
            col += vec3(0.16, 0.2, 0.28) * fa * dark * (0.4 + 0.6 * rim);   // ice under starlight: a faint cold sheen
            a = clamp(a, 0.0, 1.0);
            gl_FragColor = vec4(col / max(a, 1e-3), a);
          }`,
      }));
      m.visible = false; m.renderOrder = 2; B.tiltGroup.add(m);
      const glow = glowSprite("255,120,40", B.radius * 6, 0); glow.visible = false; B.group.add(glow);
      // the plume: rock boiled off the hot side streams away — fire near the planet, then dark smoke — and sparks
      // (molten drops) fly off and are left behind along the way (js: firePlume, sparks)
      const plume = firePlume(B.radius);
      const NT = 150, tp = new Float32Array(NT * 3), tc = new Float32Array(NT * 3);
      const tg = new THREE.BufferGeometry(); tg.setAttribute("position", new THREE.BufferAttribute(tp, 3)); tg.setAttribute("color", new THREE.BufferAttribute(tc, 3));
      const tail = new THREE.Points(tg, new THREE.PointsMaterial({ size: B.radius * 0.16, map: tailTex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
      tail.frustumCulled = false; tail.visible = false; scene.add(tail);
      const seeds = Array.from({ length: NT }, () => ({ p: V(), v: V(), age: 1, life: 1 }));
      // the Earth's blue air glow goes with the oceans
      // (and every rocky planet's air glow goes out when no star is left to light it)
      const air = ROCKY.includes(id) ? B.tiltGroup.children.filter(c => c !== m && c.material && c.material.blending === THREE.AdditiveBlending) : [];
      S.shells[id] = { m, u, glow, tail, seeds, plume, prev: V(), vel: V(), flash: 0, gas, air };
    }
  }
  // No star shines any more (its last light, 8 minutes on the way, has passed too).
  const starless = () => S.days > 0.006 && !S.bodies.some(s => shines(s));
  const tSun = V(), tOff = V(), tSide = V(), tUp = V();
  function shells(dt) {
    // the Sun's light goes out with it (moons and other plain surfaces)
    if (typeof sunLight !== "undefined") sunLight.intensity += ((starless() ? 0.12 : 1.7) - sunLight.intensity) * Math.min(1, dt * 1.2);
    // the belts of small bodies held by the Sun scatter too: they fade away
    for (const belt of typeof asteroidBelt !== "undefined" ? [asteroidBelt, kuiperBelt] : []) {
      const m = belt.material, o = m.userData.o ?? (m.userData.o = m.opacity);
      // also out of close shots and around a black hole: their dots would sit on top of the bright glows
      const h = get("sun"), close = story.on && shot.on && shot.mode !== "sun" && !story.wide;
      m.opacity += ((starless() || (h && h.bh) || close ? 0 : o) - m.opacity) * Math.min(1, dt * 0.8);
      belt.visible = m.opacity > 0.01;
    }
    // the planets, and the moons still round them (they get the same light, so they heat up and melt alike)
    const targets = S.bodies.filter(b => S.shells[b.id]);
    for (const id of MOON_IDS) {
      if (!S.shells[id] || S.free[id]) continue;
      const P = byId[id].parent, pb = P && get(P.id);
      if (pb) targets.push({ id, p: pb.p, r0: pb.r0, m: MOON_M[id], alive: pb.alive });
    }
    for (const b of targets) {
      const sh = S.shells[b.id];
      const B = byId[b.id], T = tempK(b);
      sh.flash = Math.max(0, sh.flash - dt * 0.5);
      const ease = (u, v, k) => { u.value += (v - u.value) * Math.min(1, dt * k); };
      ease(sh.u.dry, b.id === "earth" ? ramp(T, 330, 520) : 0, 2);
      // near a black hole, tides knead the planet: it heats up, cracks and glows before it is torn apart
      const tf = tidal(b);
      sh.impact = Math.max(0, (sh.impact || 0) - dt / 40);  // after a giant impact: an ocean of magma, slowly crusting over
      const ih = b.alive ? sh.impact : 0;
      ease(sh.u.crack, Math.max(sh.gas ? 0 : ramp(T, 600, 1100), sh.gas ? 0 : ramp(tf, 0.3, 0.75), sh.gas ? 0 : Math.min(1, ih * 2)), 3);
      ease(sh.u.melt, Math.max(sh.gas ? ramp(T, 700, 1800) : ramp(T, 1100, 1700), ramp(tf, sh.gas ? 0.35 : 0.6, 1), sh.gas ? ih * 0.6 : ramp(ih, 0.15, 0.6)), 3);
      ease(sh.u.frost, !ROCKY.includes(b.id) ? 0 : COLD[S.scenario] ? ramp(S.days, 5, 400) : S.scenario === "jupiter-earth" && b.id === "earth" ? ramp(S.days, 30, 700) : ramp(-T, -175, -55), 1.5);
      sh.u.flash.value = sh.flash;
      ease(sh.u.dark, starless() ? 0.7 * (1 - Math.max(sh.u.melt.value, sh.u.crack.value * 0.8, sh.flash)) : 0, 1.2);
      sh.u.time.value += dt;
      // the brightest star lights the shell
      let best = null, bf = 0;
      for (const s of S.bodies) if (shines(s)) { const f = Math.pow(s.m, 3.5) / Math.max(b.p.distanceToSquared(s.p), 1e-8); if (f > bf) { bf = f; best = s; } }
      if (best) sh.u.sunDir.value.copy(scenePos(best, tSun)).sub(B.world).normalize();
      const u = sh.u, any = u.dry.value + u.crack.value + u.melt.value + u.frost.value + u.flash.value + u.dark.value;
      sh.m.visible = b.alive && any > 0.01;
      const heat = Math.max(u.crack.value * 0.6, u.melt.value, u.flash.value);
      sh.glow.visible = b.alive && heat > 0.03;
      sh.glow.material.opacity = 0.32 * heat;
      // the Earth's clouds burn away as it dries
      if (b.id === "earth" && typeof earthClouds !== "undefined" && earthClouds) earthClouds.visible = !b.alive || u.dry.value < 0.4;
      for (const c of sh.air) c.visible = u.dry.value < 0.5 && u.crack.value < 0.3 && u.dark.value < 0.3;
      // the plume: away from the star and back along the planet's path (its motion on the screen)
      const tk = b.alive && best ? ramp(T, 850, 1600) : 0;
      if (dt > 0) { tA.copy(B.world).sub(sh.prev).divideScalar(dt); if (sh.prev.lengthSq() > 0 && tA.length() < B.radius * 60) sh.vel.lerp(tA, Math.min(1, dt * 3)); }
      sh.prev.copy(B.world);
      tOff.copy(sh.u.sunDir.value).negate();
      const sp = sh.vel.length();
      if (sp > B.radius * 0.05) tOff.addScaledVector(sh.vel, -0.7 / sp).normalize();
      const R = B.radius * (B.sbScale || 1);
      firePlumeSet(sh.plume, b.alive ? tk : 0, B.world, tOff, R, dt);
      sparks(sh, b.alive ? tk : 0, B.world, tOff, sh.u.sunDir.value, R, dt);
    }
  }
  function hideShells() {
    for (const id in S.shells) { const sh = S.shells[id]; sh.m.visible = sh.glow.visible = sh.tail.visible = false; sh.flash = 0; for (const k of ["dry", "crack", "melt", "frost", "flash", "dark"]) sh.u[k].value = 0;
      sh.plume.g.visible = false; sh.prev.set(0, 0, 0); sh.vel.set(0, 0, 0); for (const q of sh.seeds) q.age = q.life; }
    if (typeof earthClouds !== "undefined" && earthClouds) earthClouds.visible = true;
    for (const id in S.shells) for (const c of S.shells[id].air) c.visible = true;
  }

  // An explosion: a flash, a ring of shock running out, and debris that flies apart, slows and cools.
  let ringTex = null, softTex = null;
  function boom(pos, size, hot) {
    if (!ringTex) {
      const cv = document.createElement("canvas"); cv.width = cv.height = 256;
      const g = cv.getContext("2d"), grd = g.createRadialGradient(128, 128, 90, 128, 128, 126);
      grd.addColorStop(0, "rgba(255,220,170,0)"); grd.addColorStop(0.7, "rgba(255,220,170,0.9)"); grd.addColorStop(1, "rgba(255,220,170,0)");
      g.fillStyle = grd; g.fillRect(0, 0, 256, 256); ringTex = toTexture(cv);
    }
    const flash = glowSprite(hot ? "255,200,120" : "255,235,200", size * 6, 1);
    const ring = new THREE.Sprite(new THREE.SpriteMaterial({ map: ringTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    const N = 160, pos3 = new Float32Array(N * 3), vel = [];
    for (let i = 0; i < N; i++) {
      const u = Math.random() * 2 - 1, th = Math.random() * TAU, r = Math.sqrt(1 - u * u), sp = size * (1.5 + Math.random() * 4.5);
      vel.push(new THREE.Vector3(r * Math.cos(th), u * 0.6, r * Math.sin(th)).multiplyScalar(sp));
    }
    const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.BufferAttribute(pos3, 3));
    if (!softTex) softTex = glowSprite("255,255,255", 1, 1).material.map;
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ color: hot ? 0xffa050 : 0xffd090, size: size * 0.5, map: softTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    const g = new THREE.Group(); g.position.copy(pos); g.add(flash, ring, pts); scene.add(g);
    S.booms.push({ g, flash, ring, pts, vel, t: 0, size });
  }
  function booms(dt) {
    for (let k = S.booms.length - 1; k >= 0; k--) {
      const e = S.booms[k]; e.t += dt;
      const t = e.t, a = e.pts.geometry.attributes.position;
      e.flash.material.opacity = Math.max(0, 1 - t / 0.9);
      e.flash.scale.setScalar(e.size * (3 + 6 * Math.min(1, t / 0.25)));
      e.ring.scale.setScalar(e.size * (1 + 14 * (1 - Math.exp(-t * 1.8))));
      e.ring.material.opacity = Math.max(0, 0.8 * (1 - t / 2.2));
      const k1 = (1 - Math.exp(-t * 0.9)) / 0.9;           // the debris slows down
      for (let i = 0; i < e.vel.length; i++) { const v = e.vel[i]; a.setXYZ(i, v.x * k1, v.y * k1, v.z * k1); }
      a.needsUpdate = true;
      e.pts.material.opacity = Math.max(0, 1 - t / 3.5);
      e.pts.material.color.setRGB(1, Math.max(0.25, 0.75 - t * 0.12), Math.max(0.05, 0.4 - t * 0.12));
      if (t > 3.6) { scene.remove(e.g); e.pts.geometry.dispose(); e.pts.material.dispose(); e.flash.material.dispose(); e.ring.material.dispose(); S.booms.splice(k, 1); }
    }
  }
  function clearBooms() {
    for (const e of S.booms) scene.remove(e.g);
    for (const e of S.splashes) scene.remove(e.g);
    for (const e of S.impacts) scene.remove(e.g);
    S.booms.length = 0; S.splashes.length = 0; S.impacts.length = 0;
  }

  // A planet falling into a star: the surface takes the blow like a flare. Arcs of glowing plasma leap out of the spot,
  // hang and fall back as they fade (drawn like the Sun's own prominences), a bright wave runs out over the surface,
  // and the spot flashes. c: the star's centre in the scene, dir: towards the impact, R: the star's radius on screen.
  function splash(c, dir, R, pw = 1) {
    const g = new THREE.Group(); g.position.copy(c); scene.add(g);
    const A = dir.clone().normalize();
    const arcs = [];
    for (let i = 0; i < Math.round(7 * pw); i++) {
      const side = new THREE.Vector3().crossVectors(A, Math.abs(A.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0)).normalize();
      side.applyAxisAngle(A, Math.random() * TAU);
      const start = A.clone().applyAxisAngle(side, (Math.random() - 0.5) * 0.12);
      const sep = 0.15 + Math.random() * 0.45, height = 0.3 + Math.random() * 0.7, twist = (Math.random() - 0.5) * 0.3;
      const end = start.clone().applyAxisAngle(side, sep), normal = new THREE.Vector3().crossVectors(start, end).normalize();
      const pts = [];
      for (let k = 0; k <= 28; k++) {
        const t = k / 28, d = new THREE.Vector3().lerpVectors(start, end, t).normalize().addScaledVector(normal, Math.sin(PI * t) * twist).normalize();
        pts.push(d.multiplyScalar(R * (0.99 + height * Math.sin(PI * t))));
      }
      const u = { time: { value: Math.random() * 10 }, life: { value: 0 }, grow: { value: 0 }, seed: { value: Math.random() * 100 }, R: { value: R } };
      const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 72, R * (0.018 + Math.random() * 0.03), 10, false), new THREE.ShaderMaterial({
        uniforms: u, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
        vertexShader: `uniform float grow; uniform float R; varying vec2 vUv; varying vec3 vN; varying vec3 vV;
          void main(){ vUv = uv; vec3 d = normalize(position); vec3 p = d * (R + (length(position) - R) * grow);
            vec4 mv = modelViewMatrix * vec4(p, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
        fragmentShader: NOISE_GLSL + `uniform float time; uniform float life; uniform float seed; varying vec2 vUv; varying vec3 vN; varying vec3 vV;
          void main(){
            float core = pow(abs(dot(normalize(vN), vV)), 2.0);
            float fil = snoise(vec3(vUv.x * 7.0 - time * 0.6 + seed, sin(vUv.y * 6.2831) * 0.8, time * 0.3 + seed)) * 0.5 + 0.5;
            float I = core * (0.5 + 1.5 * fil * fil) * life;
            vec3 col = mix(vec3(1.0, 0.28, 0.04), vec3(1.0, 0.75, 0.35), fil * life);
            gl_FragColor = vec4(col, clamp(I, 0.0, 1.0));
          }`,
      }));
      g.add(m); arcs.push({ m, u, delay: 0.5 + Math.random() * 0.9, speed: 0.7 + Math.random() * 0.5 });   // after the jet
    }
    // the wave over the surface and the hot spot where it struck
    const wu = { A: { value: A }, w: { value: 0 }, k: { value: 1 } };
    const wave = new THREE.Mesh(new THREE.SphereGeometry(R * 1.012, 96, 64), new THREE.ShaderMaterial({
      uniforms: wu, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: `uniform vec3 A; uniform float w; uniform float k; varying vec3 vP;
        void main(){ float a = acos(clamp(dot(normalize(vP), A), -1.0, 1.0));
          float ring = exp(-pow((a - w) / (0.05 + 0.08 * w), 2.0)) * (1.0 - smoothstep(0.6, 1.4, w));
          float spot = exp(-a * a / 0.012) * 1.6;
          gl_FragColor = vec4(mix(vec3(1.0, 0.45, 0.1), vec3(1.0, 0.85, 0.55), spot * 0.5), clamp((ring * 0.8 + spot) * k, 0.0, 1.0)); }`,
    }));
    const flash = glowSprite("255,210,150", R * 2.5, 1); flash.position.copy(A).multiplyScalar(R * 1.05);
    g.add(wave, flash);
    // the blow itself: a white-hot core, a jet of fire thrown back out of the hole it punched, a bubble of plasma
    // swelling away into space (like a coronal mass ejection), molten drops arcing up and falling back, and a dark
    // scar left on the surface for a while, like a sunspot
    const core = glowSprite("255,250,235", R, 1); core.position.copy(A).multiplyScalar(R * 1.02); g.add(core);
    const jet = firePlume(R * 0.22 * pw, g); jet.g.visible = true; jet.g.position.copy(A).multiplyScalar(R * 0.96); jet.g.quaternion.setFromUnitVectors(Y_AXIS, A);
    const cu = { k: { value: 0 }, time: { value: Math.random() * 10 }, A: { value: A } };
    const cme = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 32), new THREE.ShaderMaterial({ uniforms: cu, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: "varying vec3 vN; varying vec3 vV; varying vec3 vP; void main(){ vP = position; vec4 mv = modelViewMatrix * vec4(position, 1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }",
      fragmentShader: NOISE_GLSL + `uniform float k; uniform float time; uniform vec3 A; varying vec3 vN; varying vec3 vV; varying vec3 vP;
        void main(){ float rim = 1.0 - abs(dot(normalize(vN), normalize(vV)));
          float fil = fbm2(vP * 3.6 + vec3(0.0, 0.0, time * 0.25)) * 0.6 + 0.5;
          float strand = 1.0 - abs(snoise(vP * vec3(5.0, 5.0, 5.0) + vec3(time * 0.2)));
          float front = smoothstep(0.15, 0.85, dot(normalize(vP), A));      // only the leading front, not a ball
          float I = rim * rim * front * (0.05 + 1.8 * fil * fil * strand * strand * strand) * k * 0.45;
          gl_FragColor = vec4(mix(vec3(1.0, 0.5, 0.18), vec3(1.0, 0.88, 0.72), clamp(fil, 0.0, 1.0)), clamp(I, 0.0, 1.0)); }` }));
    g.add(cme);
    const su = { A: { value: A }, k: { value: 0 } };
    const scar = new THREE.Mesh(new THREE.SphereGeometry(R * 1.006, 96, 64), new THREE.ShaderMaterial({ uniforms: su, transparent: true, depthWrite: false,
      vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: NOISE_GLSL + `uniform vec3 A; uniform float k; varying vec3 vP;
        void main(){ float a = acos(clamp(dot(normalize(vP), A), -1.0, 1.0));
          float n = snoise(vP * 16.0) * 0.5 + 0.5, umbra = exp(-a * a / 0.0035), pen = exp(-a * a / 0.016) * (0.5 + 0.5 * n);
          gl_FragColor = vec4(mix(vec3(0.4, 0.12, 0.02), vec3(0.06, 0.015, 0.0), umbra), clamp(umbra * 0.9 + pen * 0.55, 0.0, 0.92) * k); }` }));
    g.add(scar);
    const ND = 220, dp = new Float32Array(ND * 3), dc = new Float32Array(ND * 3), drops = [];
    const dside = new THREE.Vector3().crossVectors(A, Math.abs(A.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0)).normalize(), dup = new THREE.Vector3().crossVectors(dside, A);
    for (let i = 0; i < ND; i++) {
      const ang = Math.random() * TAU, spr = Math.pow(Math.random(), 0.7) * 0.9;
      const d = A.clone().addScaledVector(dside, Math.cos(ang) * spr).addScaledVector(dup, Math.sin(ang) * spr).normalize();
      drops.push({ d, v: R * (0.5 + Math.random() * 1.4), t0: Math.random() * 0.6 });
    }
    const dg = new THREE.BufferGeometry(); dg.setAttribute("position", new THREE.BufferAttribute(dp, 3)); dg.setAttribute("color", new THREE.BufferAttribute(dc, 3));
    if (!softTex) softTex = glowSprite("255,255,255", 1, 1).material.map;
    const dpts = new THREE.Points(dg, new THREE.PointsMaterial({ size: R * 0.05, map: softTex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    dpts.frustumCulled = false; g.add(dpts);
    S.splashes.push({ g, arcs, wu, flash, core, jet, cme, cu, su, drops, dpts, A, t: 0, R, pw });
  }
  function splashes(dt) {
    for (let k = S.splashes.length - 1; k >= 0; k--) {
      const e = S.splashes[k]; e.t += dt;
      const t = e.t;
      for (const a of e.arcs) {
        const x = Math.max(0, t - a.delay) * a.speed;
        // up fast, hang, then sink back as it cools
        a.u.grow.value = Math.min(1, x / 0.9) * (1 - 0.6 * smooth01((x - 3.0) / 3.0));
        a.u.life.value = 0.75 * Math.min(1, x / 0.3) * (1 - smooth01((x - 2.8) / 3.2));
        a.u.time.value += dt;
      }
      e.wu.w.value = 1.4 * (1 - Math.exp(-t * 0.9));
      e.wu.k.value = 1 - smooth01((t - 2) / 3);
      e.flash.material.opacity = Math.max(0, 1 - t / 1.2);
      e.flash.scale.setScalar(e.R * (1.5 + 2.5 * Math.min(1, t / 0.3)));
      const R = e.R;
      e.core.material.opacity = Math.max(0, 1 - t / 0.9);
      e.core.scale.setScalar(R * (0.5 + 1.6 * Math.min(1, t / 0.18)));
      // the jet shoots up fast, then hangs and dies down
      const jk = Math.min(1, t / 0.2) * (1 - smooth01((t - 1.0) / 3.2));
      e.jet.g.visible = jk > 0.01;
      for (const [part, f, w] of [[e.jet.fire, 1, 2.4], [e.jet.smoke, 1.25, 3.2]]) {
        part.u.k.value = jk * (part === e.jet.smoke ? 0.6 : 1); part.u.R.value = R * 0.22 * e.pw * (1 + t * 0.3);
        part.u.len.value = R * f * e.pw * (0.2 + 1.9 * (1 - Math.exp(-t * 1.4))); part.u.wid.value = w; part.u.stretch.value = 4; part.u.time.value += dt;
      }
      // the bubble swells away from the star and fades
      const bs = 0.2 + 1.7 * (1 - Math.exp(-t * 0.35));
      e.cme.position.copy(e.A).multiplyScalar(R * (1 + 0.8 * bs)); e.cme.scale.setScalar(R * 0.7 * bs);
      e.cu.k.value = smooth01(t / 1.0) * (1 - smooth01((t - 3) / 6)) * e.pw; e.cu.time.value += dt;
      e.su.k.value = smooth01((t - 0.8) / 1.5) * (1 - smooth01((t - 8) / 6)) * e.pw;
      // molten drops: thrown up, pulled back down by the star's gravity, hidden once they fall back in
      const pa = e.dpts.geometry.attributes.position, ca = e.dpts.geometry.attributes.color, gR = R * 1.1;
      for (let i = 0; i < e.drops.length; i++) {
        const q = e.drops[i], tt = t - q.t0;
        if (tt <= 0) { ca.setXYZ(i, 0, 0, 0); continue; }
        tA.copy(e.A).multiplyScalar(R * 1.01).addScaledVector(q.d, q.v * tt).addScaledVector(e.A, -0.5 * gR * tt * tt);
        if (tA.length() < R * 1.0) { ca.setXYZ(i, 0, 0, 0); continue; }
        pa.setXYZ(i, tA.x, tA.y, tA.z);
        const f = Math.min(1, tt / 3), b = 1.2 * (1 - 0.6 * f);
        ca.setXYZ(i, b, b * (0.85 - 0.6 * f), b * (0.5 - 0.45 * f));
      }
      pa.needsUpdate = true; ca.needsUpdate = true;
      if (t > 15) { scene.remove(e.g); e.g.traverse(o => { if (o.geometry && o.geometry !== plumeGeo) o.geometry.dispose(); if (o.material) o.material.dispose(); }); S.splashes.splice(k, 1); }
    }
  }
  const smooth01 = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };

  // A planet striking another: drawn on the survivor (id), at the point facing the impactor (dir), Rb its radius on
  // the screen, rs the impactor's. A white-hot flash; a fountain of fire out of the crater; a glowing wave running
  // round the planet; rocks — real chunks, glowing and cooling — thrown out: the slow ones fall back, some settle
  // into a ring round the planet (as the Moon's material once did round the Earth), the fastest fly off; a spray of
  // molten drops. A gas giant takes it differently: a fireball and a dark scar in its clouds, no rocks.
  let rockGeo = null;
  function impact(id, dir, Rb, rs) {
    const gas = GIANTS.includes(id), A = dir.clone();
    const g = new THREE.Group(); g.position.copy(byId[id].world); scene.add(g);
    const tip = A.clone().multiplyScalar(Rb);
    const core = glowSprite("255,250,235", Rb, 1); core.position.copy(tip);
    const glow = glowSprite("255,150,60", Rb * 4, 1); glow.position.copy(tip);
    g.add(core, glow);
    const jet = firePlume(Rb * (gas ? 0.3 : 0.22), g); jet.g.visible = true; jet.g.position.copy(A).multiplyScalar(Rb * 0.92); jet.g.quaternion.setFromUnitVectors(Y_AXIS, A);
    // the wave and the crater (or the scar in the clouds), on a shell round the planet
    const wu = { A: { value: A }, w: { value: 0 }, k: { value: 1 }, c: { value: 0 }, gas: { value: gas ? 1 : 0 } };
    const wave = new THREE.Mesh(new THREE.SphereGeometry(Rb * 1.02, 72, 48), new THREE.ShaderMaterial({ uniforms: wu, transparent: true, depthWrite: false,
      vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: NOISE_GLSL + `uniform vec3 A; uniform float w; uniform float k; uniform float c; uniform float gas; varying vec3 vP;
        void main(){ vec3 p = normalize(vP); float a = acos(clamp(dot(p, A), -1.0, 1.0)); float n = snoise(p * 9.0) * 0.5 + 0.5;
          float ring = exp(-pow((a - w) / (0.06 + 0.1 * w), 2.0)) * (1.0 - smoothstep(1.2, 2.6, w)) * (0.6 + 0.6 * n) * k;
          float spot = exp(-a * a / (0.03 + 0.02 * n)) * c;
          vec3 hot = mix(vec3(1.0, 0.35, 0.05), vec3(1.0, 0.8, 0.45), spot);
          if (gas > 0.5) { float scar = exp(-a * a / 0.05) * (0.55 + 0.45 * n) * c;     // a bruise in the clouds, like Shoemaker–Levy 9 on Jupiter
            gl_FragColor = vec4(mix(hot, vec3(0.05, 0.03, 0.02), step(0.001, scar) * 0.9), clamp(ring * 0.8 + scar * 0.85, 0.0, 0.95)); }
          else gl_FragColor = vec4(hot * (1.2 + spot), clamp(ring * 0.9 + spot, 0.0, 1.0)); }` }));
    wave.renderOrder = 3; g.add(wave);
    // the axis a ring of debris would circle: across the line of the blow
    const ax = V().crossVectors(A, Math.abs(A.y) > 0.9 ? V().set(1, 0, 0) : UP).normalize();
    const rocks = [];
    let inst = null;
    if (!gas) {
      if (!rockGeo) {
        // a lumpy, faceted rock: an icosphere with its corners pushed in and out
        const ico = new THREE.IcosahedronGeometry(1, 1), pa = ico.attributes.position, seen = new Map();
        for (let i = 0; i < pa.count; i++) {
          const key = `${pa.getX(i).toFixed(3)},${pa.getY(i).toFixed(3)},${pa.getZ(i).toFixed(3)}`;
          if (!seen.has(key)) seen.set(key, 0.7 + Math.random() * 0.5);
          const f = seen.get(key); pa.setXYZ(i, pa.getX(i) * f, pa.getY(i) * f * 0.85, pa.getZ(i) * f);
        }
        ico.computeVertexNormals(); rockGeo = ico;
      }
      const NR = Math.round(170 + 230 * Math.min(1, rs / Rb));   // a bigger impactor throws out more
      inst = new THREE.InstancedMesh(rockGeo, new THREE.ShaderMaterial({ uniforms: { sunDir: { value: V() } },
        vertexShader: `varying vec3 vN; varying vec3 vC;
          void main(){ vN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * normal); vC = instanceColor;
            gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0); }`,
        fragmentShader: `uniform vec3 sunDir; varying vec3 vN; varying vec3 vC;
          void main(){ float heat = vC.x, lit = 0.06 + 0.94 * max(dot(normalize(vN), sunDir), 0.0);
            vec3 rock = vec3(0.34, 0.29, 0.25) * vC.y * lit;
            vec3 hot = mix(vec3(0.9, 0.22, 0.03), vec3(1.0, 0.82, 0.5), heat * heat) * heat * (1.0 + 0.6 * heat);
            gl_FragColor = vec4(rock * (1.0 - 0.7 * heat) + hot, 1.0); }` }), NR);
      inst.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(NR * 3), 3);
      inst.frustumCulled = false; g.add(inst);
      const side = V().crossVectors(A, ax);
      for (let i = 0; i < NR; i++) {
        const ang = Math.random() * TAU, spr = Math.pow(Math.random(), 0.6) * 1.3;
        const d = A.clone().addScaledVector(ax, Math.cos(ang) * spr).addScaledVector(side, Math.sin(ang) * spr).normalize();
        const kind = Math.random(), sp = Rb * (kind < 0.45 ? 0.5 + Math.random() * 0.6 : kind < 0.8 ? 1.0 + Math.random() * 0.5 : 1.8 + Math.random() * 1.6);
        rocks.push({ p: tip.clone().addScaledVector(d, Rb * 0.03), v: d.multiplyScalar(sp), ring: kind >= 0.45 && kind < 0.8, rt: Rb * (1.45 + Math.random() * 1.1),
          s: Rb * (0.006 + Math.pow(Math.random(), 4) * 0.032) * Math.min(1.5, 0.6 + rs / Rb * 2), live: true, q: new THREE.Quaternion().random(),
          w: new THREE.Quaternion().setFromAxisAngle(V().randomDirection(), (Math.random() - 0.5) * 0.25), heat: 1, alb: 0.7 + Math.random() * 0.6 });
      }
    }
    // molten spray
    const ND = 260, dp = new Float32Array(ND * 3), dc = new Float32Array(ND * 3), drops = [];
    for (let i = 0; i < ND; i++) {
      const d = A.clone().addScaledVector(V().randomDirection(), 0.9).normalize();
      drops.push({ p: tip.clone(), v: d.multiplyScalar(Rb * (0.8 + Math.random() * 2.4)), life: 0.8 + Math.random() * 1.8 });
    }
    const dg = new THREE.BufferGeometry(); dg.setAttribute("position", new THREE.BufferAttribute(dp, 3)); dg.setAttribute("color", new THREE.BufferAttribute(dc, 3));
    if (!softTex) softTex = glowSprite("255,255,255", 1, 1).material.map;
    const dpts = new THREE.Points(dg, new THREE.PointsMaterial({ size: Rb * 0.06, map: softTex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    dpts.frustumCulled = false; g.add(dpts);
    S.impacts.push({ id, g, A, ax, Rb, gas, core, glow, jet, wu, rocks, inst, drops, dpts, t: 0 });
  }
  const mI = new THREE.Matrix4(), vS = new THREE.Vector3(), cI = new THREE.Color();
  function impacts(dt) {
    for (let k = S.impacts.length - 1; k >= 0; k--) {
      const e = S.impacts[k], B = byId[e.id], b = get(e.id);
      e.t += dt; const t = e.t, Rb = e.Rb;
      if (!b || !b.alive || t > 28) { scene.remove(e.g); e.g.traverse(o => { if (o.geometry && o.geometry !== plumeGeo && o.geometry !== rockGeo) o.geometry.dispose(); if (o.material) o.material.dispose(); }); S.impacts.splice(k, 1); continue; }
      e.g.position.copy(B.world);                          // the planet moves on: everything goes with it,
      e.g.scale.setScalar(B.sbScale || 1);                  // and is drawn smaller with it while another planet is close
      e.core.material.opacity = Math.max(0, 1 - t / 0.8); e.core.scale.setScalar(Rb * (0.6 + 2.2 * Math.min(1, t / 0.15)));
      e.glow.material.opacity = Math.max(0, 0.9 - t / 2.2); e.glow.scale.setScalar(Rb * (2 + 5 * Math.min(1, t / 0.4)));
      const jk = Math.min(1, t / 0.15) * (1 - smooth01((t - 0.8) / 3));
      e.jet.g.visible = jk > 0.01;
      for (const [part, f, w] of [[e.jet.fire, 1, e.gas ? 3.4 : 2.6], [e.jet.smoke, 1.3, e.gas ? 4.2 : 3.4]]) {
        part.u.k.value = jk * (part === e.jet.smoke ? 0.7 : 1); part.u.R.value = Rb * (e.gas ? 0.3 : 0.22) * (1 + t * 0.4);
        part.u.len.value = Rb * f * (0.15 + 1.7 * (1 - Math.exp(-t * 1.6))); part.u.wid.value = w; part.u.stretch.value = 4; part.u.time.value += dt;
      }
      e.wu.w.value = 2.4 * (1 - Math.exp(-t * 0.8)); e.wu.k.value = 1 - smooth01((t - 1.5) / 3);
      e.wu.c.value = Math.min(1, t / 0.3) * (1 - smooth01((t - (e.gas ? 10 : 6)) / 16));
      // the rocks: gravity of the planet, a little drag; ring-bound ones are steered onto circular orbits
      if (e.inst) {
        const g0 = Rb * 0.9;                                // surface gravity on this scale (scene units / s²)
        for (let i = 0; i < e.rocks.length; i++) {
          const r = e.rocks[i];
          if (!r.live) { mI.makeScale(0, 0, 0); e.inst.setMatrixAt(i, mI); continue; }
          for (let sub = 0; sub < 2; sub++) {
            const h = dt / 2, d = r.p.length();
            r.v.addScaledVector(r.p, -g0 * Rb * Rb / (d * d * d) * h);
            if (r.ring && d > Rb * 1.15) {
              const vc = Math.sqrt(g0 * Rb * Rb / d);
              tA.crossVectors(e.ax, r.p).normalize().multiplyScalar(vc).addScaledVector(r.p, (r.rt - d) / d * 0.6);
              r.v.lerp(tA, Math.min(1, h * 1.4));
            }
            r.p.addScaledVector(r.v, h);
          }
          if (r.p.length() < Rb * 0.98 && t > 0.3) r.live = false;
          r.q.multiply(r.w); r.heat = Math.max(0, 1 - t / (2.5 + (r.s / Rb) * 150));   // big rocks stay hot longer
          const fade = r.ring ? 1 - smooth01((t - 18) / 9) : 1 - smooth01((t - 6) / 6);
          vS.setScalar(r.s * Math.max(0, fade)); mI.compose(r.p, r.q, vS); e.inst.setMatrixAt(i, mI);
          // (r: how hot, g: how bright the rock) white-hot, orange, then dark rock lit by the star
          cI.setRGB(r.heat, r.alb, 0); e.inst.setColorAt(i, cI);
        }
        e.inst.instanceMatrix.needsUpdate = true; e.inst.instanceColor.needsUpdate = true;
        if (S.shells[e.id]) e.inst.material.uniforms.sunDir.value.copy(S.shells[e.id].u.sunDir.value);
      }
      const pa = e.dpts.geometry.attributes.position, ca = e.dpts.geometry.attributes.color;
      for (let i = 0; i < e.drops.length; i++) {
        const q = e.drops[i];
        if (t > q.life) { ca.setXYZ(i, 0, 0, 0); continue; }
        q.p.addScaledVector(q.v, dt); q.v.multiplyScalar(Math.exp(-dt * 1.2));
        pa.setXYZ(i, q.p.x, q.p.y, q.p.z);
        const f = t / q.life, c = (1 - f) * 1.3;
        ca.setXYZ(i, c, c * (0.8 - 0.55 * f), c * (0.4 - 0.35 * f));
      }
      pa.needsUpdate = true; ca.needsUpdate = true;
    }
  }
  // Turn this frame's collisions into explosions: on the star's surface facing the planet, or where two planets met.
  function fireHits() {
    for (const h of S.hits) {
      const small = get(h.small), big = get(h.big);
      if (h.star && big.bh) { if (BHG) BHG.glow = Math.min(1.2, BHG.glow + 0.3); }
      else if (h.star) {
        const c = scenePos(big, V()), dir = (byId[h.small] ? tA.copy(byId[h.small].world) : scenePos(small, tA)).clone().sub(c);
        if (dir.lengthSq() < 1e-6) dir.set(1, 0, 0);
        splash(c, dir, byId.sun.radius * SUN_K * (big.id === "sun2" ? 0.95 : 1), MOONSET.has(h.small) ? 0.5 : 1);
      } else if (byId[h.big]) {
        const Bb = byId[h.big], dir = scenePos(small, V()).sub(Bb.world);
        if (dir.lengthSq() < 1e-9) dir.set(1, 0, 0);
        impact(h.big, dir.normalize(), Bb.radius, byId[h.small] ? byId[h.small].radius : 0.5);   // (drawn at the planet's own size; scaled with it)
        const sh = S.shells[h.big];
        if (sh) { sh.flash = 1; sh.impact = 1; sh.u.hitDir.value.copy(dir); }   // the survivor glows, then stays molten for a long while
      } else boom(scenePos(small, V()), Math.max(byId[h.small].radius, 0.8), false);
    }
    S.hits.length = 0;
  }

  /* ---------- The director: slow motion and the camera on what matters ---------- */
  // Each frame it looks for what is about to happen: a planet on course into a star (its closest approach, from its
  // orbit, would hit it), a star-grazer, two planets closing in. Time slows so the event lasts a few real seconds, the
  // camera flies to the planet, and when it is over time speeds up again and the camera goes back to the whole system.
  // Touching the scene hands the camera back to the viewer for a while; the 🎬 button turns the director off.
  // What is coming: { b, o, kind, rate, prio } — o is the other body (a star or a planet), rate the slowest simulated
  // days per real second the event needs to last ~4 s. Kinds: "impact"/"graze" (a star), "meet" (two planets), "escape".
  function upcoming() {
    let best = null, rate = Infinity;
    const now = performance.now();
    const consider = (b, o, kind, tdyn, prio, slow = true) => {
      if (slow) rate = Math.min(rate, Math.max(0.04, tdyn / 4));
      if ((S.cool[b.id] || 0) > now && kind !== "impact") return;   // this planet had its moment a moment ago
      if (!best || prio > best.prio) best = { b, o, kind, prio };
    };
    for (const b of S.bodies) {
      if (!b.alive || isStar(b) || MOONSET.has(b.id)) continue;   // (the camera follows planets, not their moons)
      for (const st of S.bodies) {
        if (!isStar(st) || !st.alive || st.m <= 0) continue;
        const rv = tRel.copy(b.p).sub(st.p), vv = tS.copy(b.v).sub(st.v), r = rv.length();
        if (r > 0.8) continue;
        const mu = G * (st.m + b.m), v2 = vv.lengthSq(), rdv = rv.dot(vv);
        const h2 = tOff.crossVectors(rv, vv).lengthSq();
        const ex = (v2 - mu / r) * rv.x - rdv * vv.x, ey = (v2 - mu / r) * rv.y - rdv * vv.y, ez = (v2 - mu / r) * rv.z - rdv * vv.z;
        const e = Math.sqrt(ex * ex + ey * ey + ez * ez) / mu, rp = h2 / (mu * (1 + e));
        if (rp > 0.12 || rdv > 0 && r > 1.6 * rp + 0.02) continue;   // no close pass coming (or long past it)
        consider(b, st, rp < HIT.star * 1.5 ? "impact" : "graze", Math.max(r / Math.max(Math.sqrt(v2), 1e-6), 0.02), 3 / r);
      }
      for (const o of S.bodies) {
        if (o === b || !o.alive || isStar(o) || o.m < b.m) continue;
        const d = b.p.distanceTo(o.p), lim = o.m > 1e-4 ? 0.2 : 0.06;   // giants pull from farther away
        if (d > lim) continue;
        const vr = tS.copy(b.v).sub(o.v).dot(tRel.copy(b.p).sub(o.p)) / d;
        if (vr > 0 && d > lim * 0.5) continue;
        consider(b, o, "meet", Math.max(d / Math.max(Math.abs(vr), 1e-6), 0.01), 1.5 / d);
      }
      // torn loose: unbound from every star and heading out — follow it for a moment (no slow motion)
      // (free = bound neither to any one star nor to all of them together, and already away from them)
      const stars = S.bodies.filter(x => isStar(x) && x.alive && x.m > 0);
      if (stars.length && !S.events.has("free-" + b.id)) {
        const bound = x => { const r = b.p.distanceTo(x.p), v = b.v.distanceTo(x.v); return r < 3 || v * v < 2 * G * x.m / r; };
        const M = stars.reduce((a, x) => a + x.m, 0), c = V(), cv = V();
        for (const x of stars) { c.addScaledVector(x.p, x.m / M); cv.addScaledVector(x.v, x.m / M); }
        const r = b.p.distanceTo(c), v = b.v.distanceTo(cv);
        if (!stars.some(bound) && r > 3 && v * v > 2 * G * M / r) {
          note("free-" + b.id, `${NAME[b.id]} ${verb(b.id, "зірвався", "зірвалася")} з орбіти й летить геть — через ${years(S.days)}.`);
          consider(b, null, "escape", 1, 0.5, false);
          S.cool[b.id] = 0;
        }
      }
    }
    return { best, rate };
  }

  // The shot: a chase camera on the planet itself — close behind it, a little to the side, looking past it at what it is
  // falling into (or passing), so the planet stays big in the frame (its heating is seen) and the star grows behind it.
  // The camera's offset from the planet is what is smoothed, so the planet stays locked in the frame while it moves.
  // A story sets its own shots: mode "chase" (as above), "pair" (the planet and the star together, from the side and
  // above) or "sun" (the star alone, from a fixed side); dk scales the chase distance.
  const shot = { on: false, t: 0, b: null, o: null, kind: "", off: V(), aim: V(), keep: 0, mode: "chase", dk: 1, view: V(), down: V() };
  const sT = V(), sC = V(), sP = V(), sO = V(), sDir = V(), sSide = V(), UP = new THREE.Vector3(0, 1, 0);
  function frame(dt) {
    const B = byId[shot.b.id];
    if (shot.b.alive) { if (B && shot.b.id !== "sun") sP.copy(B.world); else scenePos(shot.b, sP); } // else: keep looking where it ended
    const o = shot.o || get("sun");                // torn loose: look back past it at the Sun it is leaving
    if (o && o.alive && o !== shot.b) scenePos(o, sO); else sO.set(0, 0, 0);
    const pr = B && shot.b.id !== "sun" ? B.radius * (B.sbScale || 1) : isStar(shot.b) ? byId.sun.radius * SUN_K : 1;
    if (shot.mode === "sun") {
      scenePos(get("sun"), sP);
      // far enough that a circle of dk AU fits the screen's narrower side (a phone held upright)
      const r = sbDist(shot.dk), half = camera.fov * DEG / 2, narrow = Math.min(half, Math.atan(Math.tan(half) * camera.aspect));
      const dist = r / Math.tan(narrow) * 0.9;
      sC.set(0.75, 0.9, 0.52).normalize().multiplyScalar(dist); sT.set(0, -r * 0.25, 0);
      return glide(dt);
    }
    sDir.copy(sP).sub(sO); const gap = Math.max(sDir.length(), 1e-3); sDir.divideScalar(gap);
    sSide.crossVectors(sDir, UP); if (sSide.lengthSq() < 1e-6) sSide.set(1, 0, 0); sSide.normalize();
    if (shot.mode === "stream") {
      // the debris of the planet just torn: aim at the middle of its pieces, from the side, as close as their spread allows
      const st = S.streams.find(x => x.id === shot.b.id);
      if (st) {
        let n = 0; tPa.set(0, 0, 0);
        for (let i = 0; i < st.live.length; i += 7) if (st.live[i]) { sbToScene(tPb.set(st.P[i * 3], st.P[i * 3 + 1], st.P[i * 3 + 2]), tPb); tPa.add(tPb); n++; }
        if (n) sP.copy(tPa.divideScalar(n));
      }
      sDir.copy(sP).sub(sO); const g2 = Math.max(sDir.length(), 1e-3); sDir.divideScalar(g2);
      sSide.crossVectors(sDir, UP); if (sSide.lengthSq() < 1e-6) sSide.set(1, 0, 0); sSide.normalize();
      const d = pr * 16;
      sC.copy(sDir).multiplyScalar(d * 0.35).addScaledVector(sSide, d * 0.85).addScaledVector(UP, d * 0.3);
      sT.set(0, -pr * 1.5, 0);                              // the cloud in the middle, a little high, clear of the card
      return glide(dt);
    }
    if (shot.mode === "meet") {
      // two planets passing close: from above, from a direction fixed when the shot began (so the camera never swings
      // round with the line between them), framing both once the other is near; until then it stays on this one
      const oB = shot.o && byId[shot.o.id], rs = pr + (oB ? oB.radius * (oB.sbScale || 1) : 0);
      const half = camera.fov * DEG / 2, narrow = Math.min(half, Math.atan(Math.tan(half) * camera.aspect));
      const fit = Math.min(gap, rs * 30), w = fit / gap;
      sT.copy(sDir).multiplyScalar(-gap * 0.5 * w);
      const dist = Math.max(pr * 14, (fit * 0.5 + rs * 1.5) / Math.tan(narrow) * 1.15) * shot.dk;
      sC.copy(shot.view).multiplyScalar(dist).add(sT);
      sT.addScaledVector(shot.down, dist * 0.12);           // the pair sits a little high, clear of the card
      return glide(dt);
    }
    if (shot.mode === "pair") {
      // both from high above, looking along the line between them, so on a tall phone screen they stand one above the
      // other (the screen is taller than wide); the middle sits a little high, clear of the card below
      // (a black hole's shadow and disc take room too: about three of its drawn horizons)
      const hr = shot.o && shot.o.bh && BHG ? BHG.mat.uniforms.R.value * 4 : 0;
      const half = gap * 0.5 + Math.max(pr * 3, hr), dist = half / Math.tan(camera.fov * DEG / 2) * 1.35 * shot.dk;
      sT.copy(sDir).multiplyScalar(-gap * 0.5 + gap * 0.18 + hr * 0.45);   // (with a hole, the debris higher, off the card)
      sC.copy(sDir).multiplyScalar(0.38).addScaledVector(UP, 1).normalize().multiplyScalar(dist).add(sT);
      return glide(dt);
    }
    const d = pr * 11 * shot.dk;
    // camera: mostly to the side of the planet (so its day side and its glow are seen), a little behind it and above
    sC.copy(sDir).multiplyScalar(d * 0.45).addScaledVector(sSide, d * 0.8).addScaledVector(UP, d * 0.3);
    // aim: a little past the planet toward the star, and below it, so the planet sits in the upper part of the
    // screen, clear of the panel, with the star beside it
    sT.copy(sDir).multiplyScalar(-Math.min(gap * 0.3, pr * 0.6)).addScaledVector(UP, -pr * 2.2);
    glide(dt);
  }
  function glide(dt) {
    const k = shot.snap ? 1 : 1 - Math.exp(-dt * (shot.t < 2.5 ? 1.6 : 4));   // glide in, then hold steady on the planet
    shot.snap = false;
    shot.off.lerp(sC, k); shot.aim.lerp(sT, k);
    controls.target.copy(sP).add(shot.aim); camera.position.copy(sP).add(shot.off); camera.lookAt(controls.target);
  }
  function startShot(ev) {
    shot.on = true; shot.t = 0; shot.b = ev.b; shot.o = ev.o; shot.kind = ev.kind; shot.keep = 0;
    shot.mode = ev.mode || "chase"; shot.dk = ev.dk || 1;
    const B = byId[ev.b.id];
    if (shot.mode === "sun") scenePos(get("sun"), sP); else if (B && ev.b.id !== "sun" && ev.b.alive) sP.copy(B.world); else if (ev.b.alive) scenePos(ev.b, sP);
    if (shot.mode === "meet") {
      // looking down from above and a little outward (away from the Sun), so the Sun is toward the top of the screen
      tA.copy(sP).sub(scenePos(get("sun"), tB)).setY(0).normalize();
      shot.view.copy(tA).multiplyScalar(0.5).add(UP).normalize();
      shot.down.copy(tA);                                   // on screen, outward is down
    }
    shot.off.copy(camera.position).sub(sP); shot.aim.copy(controls.target).sub(sP);
    state.flight = null; state.mode = "overview"; state.index = -1;   // the sandbox drives the camera now
    controls.enabled = false;
    // and no leftover limits: after a planet was picked the site keeps the camera within a few of its sizes, and its
    // controls would pull the story's camera in to there (a close, odd view)
    controls.minDistance = 0.001; controls.maxDistance = 1e5;
  }
  function endShot(toOverview) {
    if (!shot.on) return;
    shot.on = false; controls.enabled = true;
    if (shot.b) S.cool[shot.b.id] = performance.now() + 30000;
    if (toOverview) showOverview();
  }
  function direct(dt) {
    if (story.on) return;
    const want = SPEEDS[S.speed][0];
    const { best, rate } = want > 0 ? upcoming() : { best: null, rate: Infinity };
    // a shot lasts ~20 s at most: after that the slow motion lets go, so the end comes soon
    const cap = shot.on && shot.t > 18 ? Math.exp((shot.t - 18) * 0.5) : 1;
    const target = Math.min(1, rate * cap / Math.max(want, 1e-9));
    S.slow += (target - S.slow) * Math.min(1, dt * (target < S.slow ? 6 : 0.8));   // slow down quickly, speed up gently
    if (!S.director || performance.now() < S.holdUntil) { if (shot.on) endShot(false); return; }
    if (best && (!shot.on || (best.b !== shot.b && best.prio > 2 * (shot.prio || 0)))) { startShot(best); shot.prio = best.prio; }
    if (!shot.on) return;
    shot.t += dt;
    const live = best && best.b === shot.b;
    if (live) shot.keep = 0; else shot.keep += dt;
    // after the event: hold on the scene a little (the splash, the flash), then back to the whole system
    const linger = shot.kind === "escape" ? 4 : 3.5;
    if (!live && shot.keep > linger) { endShot(true); return; }
    frame(dt);
  }
  function renderLog() {
    const ul = el("sbLog");
    if (!ul) return;
    ul.innerHTML = S.log.map(t => `<li>${t}</li>`).join("");
    ul.hidden = !S.log.length;
  }


  /* ---------- Stories: a scenario told step by step, like the tour ---------- */
  // Each step has its text, its shot and its pace, and ends on an event (the Earth is this close, it is gone), not on a
  // timer — so the words always match what is on the screen. Pace: "rate" simulated days per real second, or "k": the
  // time left to the event shrinks e times every k real seconds (fast while far, slow at the end). "min": seconds to read.
  const Y = 365.25;
  const rSun = id => { const b = get(id); return b && b.alive ? b.p.distanceTo(get("sun").p) : 0; };
  const STORIES = {
    "sgr-a": [
      // the moments of each planet's tearing come from this start's own future (scratchpad rip.js, the same physics)
      { title: "Стрілець A* замість Сонця", shot: { mode: "sun", dk: 1.25 }, rate: 0.00012, min: 11, until: () => S.days > 0.0011,
        life: "Люди: ще кілька хвилин нічого не знають — і тяжіння, і темрява летять до Землі зі швидкістю світла.",
        text: "Уяви: замість Сонця — Стрілець A*, чорна діра з центру нашої галактики. Вона в 4,3 мільйона разів масивніша за Сонце, а її межа, звідки не вирветься навіть світло, — 25 мільйонів кілометрів завширшки." },
      { title: "Меркурій", shot: { b: "mercury", o: "sun", dk: 1.5 }, ripView: 1, at: 0.002083, k: 2.2, low: 4e-06, post: 0.0015, max: 0.0002, min: 12, until: () => !get("mercury").alive, after: 5,
        life: "Люди: на Землі ще світить Сонце — його останні промені в дорозі.",
        text: "Першим новину отримує Меркурій — за 3 хвилини. Він уже ближче до діри, ніж межа, де її тяжіння рве планети: ближчий бік тягне сильніше за дальній. Меркурій розжарюється, витягується — і розлітається потоком уламків." },
      { title: "Венера", shot: { b: "venus", o: "sun", dk: 1.5 }, ripView: 1, at: 0.013403, k: 2.2, low: 4e-06, post: 0.0015, max: 0.002, min: 11, until: () => !get("venus").alive, after: 4,
        life: "Люди: над Землею вже темно, а вона мчить до діри щораз швидше.",
        text: "За 19 хвилин — Венера. Її розпечена атмосфера й кам'яне тіло розтягуються в довгу сяючу стрічку, що закручується до діри." },
      { title: "Земля", shot: { b: "earth", o: "sun", dk: 1.6 }, ripView: 1, at: 0.026389, k: 2.4, low: 4e-06, post: 0.0015, max: 0.002, min: 14, until: () => !get("earth").alive, after: 6,
        life: "Люди: живуть лише 38 хвилин. Останні з них — темрява, землетруси й спека: припливи місять кору планети.",
        text: "Земля падає вже з третиною швидкості світла. За 72 мільйони кілометрів від діри різниця тяжіння між її боками стає сильнішою за тяжіння самої Землі — і планету розриває на шматки. Від появи діри минуло 38 хвилин." },
      { title: "Юпітер", shot: { b: "jupiter", o: "sun", dk: 1.4 }, ripView: 1, at: 0.369792, k: 1.6, low: 5e-05, post: 0.002, max: 0.03, min: 13, until: () => !get("jupiter").alive, after: 5,
        life: "Людей уже немає. Від Землі лишився потік уламків, що зник за межею діри.",
        text: "Марс зник за годину з чвертю. Велетень Юпітер тримається майже 9 годин — і його розриває ще далі від діри, ніж Землю: за 118 мільйонів кілометрів. Газ розтягується в сяючу стрічку." },
      { title: "Сатурн", shot: { b: "saturn", o: "sun", dk: 1.4 }, ripView: 1, at: 0.890833, k: 1.6, low: 5e-05, post: 0.0025, max: 0.05, min: 12, until: () => !get("saturn").alive, after: 5,
        text: "Через 21 годину — Сатурн, разом із кільцями й супутниками." },
      { title: "Тиждень — і все", shot: { mode: "sun", dk: 32 }, hl: ["uranus", "neptune"], rate: 0.6, min: 13, end: true,
        text: "Уран протримається 2,7 доби, Нептун — 5. За тиждень від Сонячної системи лишаться тільки уламки, що зникають у темряві. А сама діра навіть не стане помітно важчою." },
    ],
    "bh-sun": [
      { title: "Сонце — чорна діра", shot: { mode: "sun", dk: 1.6 }, rate: 0.0003, min: 11, until: () => S.days > 0.0058, after: 2,
        life: "Люди: ще 8 хвилин бачать Сонце — його останнє світло в дорозі.",
        text: "Уяви: Сонце миттєво стискається в чорну діру тієї самої маси. Вона крихітна — кулька завширшки 6 кілометрів, менша за Київ. Тут вона намальована більшою, інакше її не було б видно." },
      { title: "Земля впаде?", shot: { b: "earth", o: "sun", dk: 1.6 }, rate: 1.5, min: 13,
        life: "Люди: живі, але настала ніч, якій не буде кінця.",
        text: "Здається, Земля зараз упаде в діру? Ні! На її відстані тяжіння таке саме, як було: маса не змінилася. Земля летить своєю старою орбітою, і рік триває як і раніше." },
      { title: "Холод", shot: { b: "earth", o: "sun", dk: 1.4 }, rate: 30, min: 12, until: () => S.days > 365,
        life: "Люди: на поверхні не вижити. Лише в укриттях з геотермальним чи ядерним теплом — роками.",
        text: "Без сонячного світла за тиждень на Землі мороз, за рік — близько −70 °C. Океани вкриваються кригою. Але орбіта — та сама." },
      { title: "Не пилосос", shot: { mode: "sun", dk: 2.2 }, hl: ["mercury", "venus", "earth", "mars"], rate: 25, min: 13, end: true,
        life: "Люди: виживуть лише глибоко під землею — як і в історії «Без Сонця».",
        text: "Планети й далі кружляють довкола темряви, наче нічого не сталося. Чорна діра — не пилосос: вона тягне так само, як зоря тієї ж маси. Вона просто не світить." },
    ],
    "jupiter-earth": [
      { title: "Юпітер замість Землі", shot: { mode: "sun", dk: 6 }, hl: ["earth", "jupiter"], rate: 2, min: 11,
        life: "Люди: на Землі, що тепер на місці Юпітера, Сонце світить у 27 разів слабше. Перші тижні — як найсуворіша зима.",
        text: "Уяви: Юпітер і Земля помінялися місцями. Велетень, у 318 разів важчий за Землю, тепер кружляє там, де були ми, а Земля — далеко, за поясом астероїдів." },
      { title: "Венера і Юпітер", shot: { mode: "meet", b: "venus", o: "jupiter", dk: 1, wide: 1.7 }, at: 54.56, k: 3, low: 0.3, max: 6, min: 12, until: () => S.days > 54.56, after: 3,
        life: "Люди: на далекій Землі мороз міцнішає щотижня.",
        text: "Кожні півтора року Юпітер обганяє Венеру й проходить за 40 мільйонів кілометрів від неї. У небі Венери він сяє майже як повний Місяць, а його тяжіння щоразу трохи розгойдує її орбіту." },
      { title: "Юпітер у теплі", shot: { b: "jupiter", o: "sun", dk: 1.3 }, rate: 8, min: 12,
        life: "Люди: на Юпітері жити ніде — у нього немає твердої поверхні.",
        text: "Тепер Юпітер отримує в 27 разів більше світла. Він теплішає, а його великі крижані супутники — Європа, Ганімед, Каллісто — опиняються там, де колись була Земля." },
      { title: "Земля мерзне", shot: { b: "earth", o: "sun", dk: 1.4 }, rate: 40, min: 12, until: () => S.days > 400,
        life: "Люди: на поверхні не вижити. Лише під землею, з власним теплом і світлом.",
        text: "За рік на Землі близько −70 °C, океани вкриваються кригою. Рік тепер триває майже 12 земних років, а Сонце в небі вп'ятеро менше. Світла ще вистачає, щоб читати, але не щоб гріти." },
      { title: "Марс", shot: { b: "mars", o: "jupiter", dk: 1.4 }, rate: 300, min: 11, until: () => S.days > 12 * Y,
        life: "Люди: на Землі вже близько −100 °C, і холоднішає далі.",
        text: "Марс тепер найближчий сусід велетня. Юпітер щоразу смикає його, і з роками орбіта Марса то витягується, то знову округлюється." },
      { title: "Крижана Земля", shot: { b: "earth", o: "sun", dk: 1.5 }, rate: 2500, min: 12,
        life: "Люди: виживуть лише ті, хто встиг сховатися глибоко під кригу й має тепло.",
        text: "За сто років Земля охолоне до −130 °C і стане крижаною кулею. Місяць і далі кружляє поруч — тепер над білою пустелею." },
      { title: "Система вистояла", shot: { mode: "sun", dk: 7 }, hl: ["earth", "jupiter", "mars", "venus"], rate: 365, min: 12, end: true,
        life: "Людям на Землі не пощастило. Але Сонячна система — ціла.",
        text: "Дивно, але система витримує: планети помінялися місцями, проте не розлітаються й не стикаються — принаймні кілька століть. Тяжіння Сонця досі тримає всіх." },
    ],
    "no-sun": [
      { title: "Сонце зникло", shot: { mode: "sun", dk: 1.6 }, rate: 0.0006, min: 11, until: () => S.days > 0.0058, after: 2,
        life: "Люди: ще 8 хвилин навіть не знають, що сталося.",
        text: "Уяви: Сонце зникло. Не вибухнуло — просто зникло. Перші 8 хвилин на Землі нічого не змінюється: світло, яке вже в дорозі, ще летить до нас. А потім — темрява." },
      { title: "Темрява", shot: { b: "earth", o: "sun", dk: 1.4 }, rate: 0.6, min: 12, until: () => S.days > 7,
        life: "Люди: живі, але мороз як узимку, а рослини без світла почнуть гинути за кілька тижнів. Їжа закінчиться.",
        text: "Ніщо більше не тримає Землю — вона летить по прямій, туди, куди мчала тієї миті, 30 км/с. Місяць не відстає: він і далі кружляє навколо неї. За тиждень на всій планеті мороз." },
      { title: "Холод", shot: { b: "earth", o: "sun", dk: 1.4 }, rate: 30, min: 12, until: () => S.days > 365,
        life: "Люди: на поверхні не вижити. Лише в укриттях з геотермальним чи ядерним теплом — роками.",
        text: "За рік температура падає до −70 °C. Океани вкриваються кригою, повітря завмирає. Але під кригою вода лишиться рідкою ще тисячі років: Земля гріє себе зсередини." },
      { title: "Розліт", shot: { mode: "sun", dk: 90 }, hl: ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"], rate: 365, min: 12, until: () => S.days > 12 * Y,
        life: "Життя: тільки мікроби біля гарячих джерел на дні океану, під кригою. Вони можуть жити мільйони років.",
        text: "Планети розлітаються, кожна своєю прямою. Меркурій найшвидший — 47 км/с, Нептун ледь повзе — 5 км/с. Вони вже ніколи не зустрінуться." },
      { title: "Далеко від усіх", shot: { b: "earth", o: "sun", dk: 1.6 }, rate: 700, min: 12,
        life: "Через мільйон років поверхня охолоне до −240 °C.",
        text: "До відстані найближчої зорі, Проксими Центавра, Земля долетіла б лише за 40 тисяч років. І весь цей час — без жодного променя тепла." },
      { title: "Планета-сирота", shot: { mode: "sun", dk: 120 }, rate: 1500, min: 12, end: true,
        text: "У нашій Галактиці мільярди таких планет-сиріт — без зорі, у вічній темряві. Тепер Земля — одна з них." },
    ],
    "heavy-sun": [
      { title: "Сонце вдвічі важче", shot: { mode: "sun", dk: 1.8 }, rate: 3, min: 9,
        life: "Люди: за 8 хвилин світло стає в 11 разів яскравішим. Під відкритим небом — смертельна спека вже за кілька годин.",
        text: "Уяви: Сонце раптом стало вдвічі масивнішим. Така зоря світить в 11 разів яскравіше, а тягне вдвічі сильніше. Планети летять надто повільно для нової сили тяжіння." },
      { title: "Земля падає ближче", shot: { b: "earth", o: "sun", dk: 1.3 }, at: 69.7, k: 4, low: 0.6, max: 8, min: 11, until: () => S.days > 69.7, after: 2,
        life: "Життя: неможливе — океани википають, поверхня розжарюється понад +600 °C.",
        text: "За 70 днів Земля падає втричі ближче до Сонця — і злітає назад. Уже зараз на ній +250 °C, а в найближчій точці понад +600 °C: океани википають, камінь світиться. Рік тепер триває 141 день." },
      { title: "Орбіти перетинаються", shot: { mode: "sun", dk: 1.8 }, hl: ["mercury", "venus", "earth", "mars"], rate: 40, min: 10, until: () => S.days > 640,
        text: "Усі кам'яні планети тепер на витягнутих орбітах, і ці орбіти перетинаються. Рано чи пізно хтось із кимось зустрінеться." },
      { title: "Венера і Марс", shot: { mode: "meet", b: "mars", o: "venus", dk: 1, wide: 1.7 }, at: 668.36, k: 3, low: 0.15, max: 30, min: 11, until: () => S.days > 668.36, after: 3,
        text: "Перша зустріч: Венера проноситься за 2,8 мільйона кілометрів від Марса — лише в 7 разів далі, ніж Місяць від Землі." },
      { title: "Меркурій", shot: { mode: "meet", b: "mercury", o: "venus", dk: 1, wide: 1.7 }, at: 1531.3, k: 2.2, low: 0.1, max: 120, min: 12, until: () => !get("mercury").alive, after: 4,
        text: "Меркурій тепер підходить до Сонця втричі ближче, ніж раніше, і розжарюється до лави. Через 4 роки він врізається у Венеру на швидкості 60 км/с. Енергії удару вистачить, щоб розплавити Венеру всю, до самого ядра, і викинути в космос величезну масу каміння." },
      { title: "Земля і Венера", shot: { mode: "meet", b: "earth", o: "venus", dk: 1, wide: 1.7 }, at: 2497.16, k: 2.5, low: 0.2, max: 150, min: 11, until: () => S.days > 2497.16, after: 3,
        text: "Ще за три роки вже Венера проноситься за 6 мільйонів кілометрів від Землі. Орбіти й далі перетинаються, і кожна така зустріч може стати останньою." },
      { title: "Нова система", shot: { mode: "sun", dk: 6 }, hl: ["jupiter", "earth"], rate: 30, min: 12, end: true,
        life: "Життя: на кам'яних планетах неможливе — кожна раз на кілька місяців підходить до Сонця втричі ближче, ніж раніше.",
        text: "Гіганти вціліли, але їхні орбіти теж витягнулися: Юпітер тепер підходить до Сонця майже так близько, як колись Марс. А Земля — розпечена кам'яна куля з роком у 141 день." },
    ],
    "two-suns": [
      // the moments below come from this start's own future (the physics is the same every time)
      { title: "Друге Сонце", shot: { mode: "pair", b: "sun2", o: "sun", dk: 1.1 }, rate: 20, min: 10,
        life: "Люди: живуть як раніше. Лише ночі, коли друге сонце над обрієм, світлі, як похмурий день.",
        text: "Уяви: там, де кружляє Сатурн, спалахує ще одна зоря — точно така, як Сонце. Тепер дві зорі обертаються одна навколо одної, а планети опиняються між двох вогнів." },
      { title: "Гіганти тікають", shot: { mode: "sun", dk: 45 }, hl: ["saturn", "uranus", "neptune"], rate: 300, min: 12, until: () => S.days > 10 * Y,
        life: "Люди: у безпеці — Земля тримається своєї орбіти, на ній близько +15 °C.",
        text: "Сатурн, Уран і Нептун тепер тягнуть дві зорі одразу. Їхні орбіти розхитуються, і за кілька років усі троє йдуть у темряву між зорями. Більше вони не повернуться." },
      { title: "Юпітер", shot: { b: "jupiter", o: "sun2", dk: 1.4 }, rate: 220, min: 10, until: () => S.days > 14.6 * Y,
        text: "Юпітер, найважча з планет, переходить до другої зорі й тепер кружляє навколо неї. Але й там він не залишиться надовго." },
      { title: "Юпітер повертається", shot: { b: "jupiter", o: "sun", dk: 1.4 }, at: 7871.8, k: 5, low: 30, max: 300, min: 9, until: () => S.days > 7840,
        life: "Люди: поки що в безпеці.",
        text: "Друга зоря відкидає Юпітер назад — просто у внутрішню частину системи, туди, де Марс, Земля й Венера." },
      { title: "Земля", shot: { mode: "meet", b: "earth", o: "jupiter", dk: 1, wide: 3 }, at: 7871.8, k: 4, low: 0.25, max: 30, min: 12, until: () => S.days > 7871.8, after: 3,
        life: "Люди: виживуть, але на день-два припливи стають уп'ятеро сильнішими, ніж від Місяця, — узбережжя затоплює.",
        text: "Юпітер пролітає повз Землю на відстані 7 мільйонів кілометрів — лише у 17 разів далі за Місяць. У нашому небі він удвічі більший за повний Місяць." },
      { title: "Нова орбіта Землі", shot: { b: "earth", o: "sun", dk: 1.6 }, rate: 40, min: 11, until: () => S.days > 23 * Y,
        life: "Люди: виживуть, але в найспекотнішу пору тропіки стають непридатними для життя.",
        text: "Земля вціліла, але її орбіта тепер витягнута: то 0,8, то 1 а. о. від Сонця. Коли вона найближче до Сонця, спека сягає +50 °C. А в небі — два сонця." },
      { title: "Юпітер падає", shot: { b: "jupiter", o: "sun", dk: 1.3 }, at: 17411.6, k: 2.2, low: 0.3, max: 800, min: 12, until: () => S.days > 17411.6, after: 3,
        text: "Двадцять п'ять років Юпітер кидається між двома зорями. І нарешті пірнає просто до Сонця — у п'ять разів ближче, ніж літає Меркурій. Його хмари розжарюються." },
      { title: "Удар", shot: { b: "jupiter", o: "sun", dk: 1.2 }, at: 18679.7, k: 2.5, low: 0.3, max: 500, min: 12, until: () => !get("jupiter").alive, after: 4,
        text: "Ще три з половиною роки витягнутої орбіти — і Юпітер падає на Сонце. Планета, у 318 разів важча за Землю, зникає в ньому. А Сонце стає важчим лише на тисячну частку." },
      { title: "Що лишилося", shot: { mode: "pair", b: "sun2", o: "sun", dk: 1.1 }, rate: 60, min: 12, end: true,
        life: "Люди: вижили — під двома сонцями, на новій, витягнутій орбіті.",
        text: "За 51 рік із восьми планет лишилися чотири кам'яні: Меркурій, Венера, Земля й Марс. Тепер у їхньому небі два сонця, а гіганти блукають у темряві між зорями." },
    ],
    "stop-earth": [
      { title: "Земля зупинилася", shot: { b: "earth", o: "sun", dk: 1.7 }, rate: 0.6, min: 8,
        life: "Люди: живі. Але Місяць тане в небі — за добу він у 7 разів менший, — і припливи слабнуть приблизно втричі.",
        text: "Уяви: Земля раптом зупинилася на своїй орбіті. Її швидкість — 30 км/с — щезла. Ніщо більше не несе її вбік, і Сонце починає тягнути її до себе. А Місяць не зупинився: він летить далі старою орбітою і вже за добу буде за 2,6 млн км від Землі." },
      { title: "Падіння", shot: { b: "earth", o: "sun", dk: 1.3 }, rate: 4, min: 9, until: () => rSun("earth") < 0.62,
        life: "Люди: живі, але спека росте щодня. За сім тижнів на Землі вже +90 °C — без укриттів не вижити.",
        text: "Перші тижні майже нічого не помітно: Земля лише повільно набирає швидкість. Але кожного дня вона падає швидше, ніж учора, а Сонце в небі стає більшим." },
      { title: "Океани закипають", shot: { b: "earth", o: "sun" }, k: 7, min: 9, until: () => rSun("earth") < 0.2,
        life: "Люди: не вижити ніде — навіть у найглибших сховищах лише кілька днів.",
        text: "Сонце світить уже майже втричі яскравіше. Спека понад +100 °C — океани закипають, небо затягує пара, а потім вода втікає в космос. Земля стає пустелею." },
      { title: "Камінь плавиться", shot: { b: "earth", o: "sun", dk: 0.9 }, k: 6, min: 9, until: () => rSun("earth") < 0.04,
        life: "Життя: неможливе ні на поверхні, ні в глибинах.",
        text: "Ще ближче — і плавиться сам камінь. Кора тріскається, з тріщин світиться магма, і Земля перетворюється на розжарену лавову кулю. Позаду тягнеться хвіст пари." },
      { title: "Удар", shot: { b: "earth", o: "sun", dk: 1.1 }, k: 3, min: 7, until: () => !get("earth").alive, after: 4,
        text: "Останні години. Земля мчить уже сотні кілометрів за секунду — і зникає в Сонці. Для Сонця це навіть не крапля: воно в 333 000 разів важче." },
      { title: "65 днів", shot: { mode: "sun", dk: 1.7 }, rate: 6, min: 12, end: true,
        text: "Від зупинки до удару минуло б близько 65 днів. На щастя, Земля не може просто зупинитися: немає сили, здатної загальмувати планету. Тож вона летить далі — як і 4,5 млрд років до нас." },
    ],
  };
  const story = { on: false, key: "", i: 0, held: 0, after: 0, rate: 0, paused: false, ff: false, steps: null, wasHeld: false };
  let storyMusic = null;
  function storyMusicWanted() { return typeof tourMusicWanted === "undefined" ? true : tourMusicWanted; }
  async function setStoryMusic(on) {
    el("sbsSound").setAttribute("aria-pressed", String(on));
    if (typeof createMusicPlayer !== "function") return;
    if (on && !storyMusic) storyMusic = createMusicPlayer(createCinematicMusic);
    if (storyMusic && storyMusic.on !== on) await storyMusic.toggle();
  }
  function startStory(key) {
    if (!STORIES[key]) return;
    if (!story.jdReal) story.jdReal = S.jd0;
    setup(key, true);
    story.on = true; story.key = key; story.steps = STORIES[key]; story.paused = false;
    document.body.classList.add("storying");
    el("sbStory").hidden = false;
    requestAnimationFrame(() => el("sbStory").classList.add("show"));
    el("sbStory").classList.remove("paused"); el("sbsPause").textContent = "❚❚";
    setStoryMusic(storyMusicWanted());
    storyStep(0);
  }
  function endStory(keepPlaying) {
    if (!story.on) return;
    story.on = false;
    if (story.jdReal) { S.jd0 = story.jdReal; story.jdReal = 0; }
    setStoryMusic(false);
    document.body.classList.remove("storying");
    el("sbStory").classList.remove("show"); el("sbStory").hidden = true;
    endShot(false);
    if (keepPlaying) { S.speed = 3; renderPanel(); }
  }
  function storyStep(i) {
    const st = story.steps[i];
    story.i = i; story.held = 0; story.after = 0; story.ff = false;
    el("sbsCount").textContent = `${i + 1} / ${story.steps.length}`;
    el("sbsTitle").textContent = st.title;
    el("sbsText").textContent = st.text;
    el("sbsLife").textContent = st.life || ""; el("sbsLife").hidden = !st.life;
    el("sbsNext").textContent = st.end ? "Інші сценарії" : "›";
    el("sbsNext").setAttribute("aria-label", st.end ? "Інші сценарії" : "Далі");
    el("sbsBar").style.transform = `scaleX(${i / (story.steps.length - 1)})`;
    story.wide = st.shot.mode === "meet";                 // a meeting: the whole system while time runs fast
    story.ripped = false;
    storyShot();
  }
  // The step's shot. Before a meeting, while time still runs fast, the planets would whirl round the Sun on screen:
  // so the camera holds the whole system from above, and comes in to the two only once time has slowed for it.
  function storyShot() {
    const sh = story.steps[story.i].shot;
    if (story.wide) return startShot({ b: get("sun"), o: null, kind: "story", mode: "sun", dk: sh.wide || 2 });
    startShot({ b: get(sh.b || "sun"), o: sh.o ? get(sh.o) : null, kind: "story", mode: sh.mode, dk: sh.dk });
  }
  // The pace of this frame (simulated days per real second).
  function storyRate(st) {
    if (st.rate !== undefined) return st.rate;
    if (st.at !== undefined && st.post && S.days >= st.at) return st.post;   // after the event: watch what follows
    if (st.at !== undefined) return Math.min(st.max || 365, Math.max(st.low || 0.2, (st.at - S.days) / st.k));
    const e = get(st.shot.b), sun = get("sun");
    if (!e || !e.alive) return 0.3;
    const r = e.p.distanceTo(sun.p), v = Math.max(e.v.distanceTo(sun.v), 1e-6);
    return Math.max(0.03, r / v / st.k);
  }
  // One frame of the story: the pace, the step's end, the camera. Returns simulated days to run.
  function storyTick(dt) {
    const st = story.steps[story.i];
    if (!story.paused && !document.hidden) story.held += dt;
    let want = story.paused ? 0 : storyRate(st) * (story.ff ? 6 : 1);
    story.rate += (want - story.rate) * Math.min(1, dt * (want < story.rate ? 5 : 1.2));
    const done = !st.until || st.until();
    if (done && st.until) story.after += story.paused ? 0 : dt;
    // a planet just torn: stay until the camera has drawn back and the hole and the stream have been seen for a while
    const ripping = story.ripped === 1 || story.ripped === 2 && story.held - story.rippedAt < 9;
    if (!st.end && story.held >= st.min && done && story.after >= (st.after || 0) && !ripping) storyStep(story.i + 1);
    // touching the scene hands the camera to the viewer for a while; then it glides back
    // (so does picking a planet: while the viewer looks at it, the story does not take the camera back)
    const held = performance.now() < S.holdUntil || state.index >= 0;
    if (held) { if (!story.wasHeld) controls.enabled = true; }
    else {
      // a planet torn apart: draw back to show the hole and the stream of what was the planet
      const cur = story.steps[story.i];                    // (the step may have just moved on in this frame)
      // first ride along with the debris for a few seconds, close, then draw back to the hole and the whole stream
      if (cur.ripView && !story.ripped && cur.shot.b && !get(cur.shot.b).alive) {
        story.ripped = 1; story.rippedAt = story.held;
        startShot({ b: get(cur.shot.b), o: get("sun"), kind: "story", mode: "stream", dk: 1 });
      }
      if (cur.ripView && story.ripped === 1 && story.held - story.rippedAt > 3.2) {
        story.ripped = 2;
        startShot({ b: get(cur.shot.b), o: get("sun"), kind: "story", mode: "pair", dk: 1.15 });
      }
      // come in once the step's own pace (not the eased one, still slow from the step before) has dropped for the event
      if (story.wide && story.held > 2 && storyRate(st) < 6) { story.wide = false; storyShot(); }
      if (story.wasHeld) storyShot();
      shot.t += dt; frame(dt);
    }
    story.wasHeld = held;
    const t = earthTemp();
    el("sbsRead").textContent = `Минуло: ${S.days < 1 ? "0 діб" : years(S.days)}` + (t === null ? "" : ` · Земля: ${t > 0 ? "+" : t < 0 ? "−" : ""}${Math.abs(Math.round(t))} °C`);
    return dt * story.rate;
  }

  /* ---------- Panel ---------- */
  const el = id => document.getElementById(id);
  // Play again after a look round: the camera goes back to the story's own shot (whatever planet was picked meanwhile).
  function backToStory() {
    if (!story.on) return;
    S.holdUntil = 0; story.wasHeld = false;
    if (typeof setActive === "function") setActive(null);
    storyShot();                                     // (it also lets go of the picked planet: the sandbox drives the camera)
    shot.snap = true;                                // a clean cut to the story's shot, not a swing round from where the viewer was
    try { history.replaceState(null, "", "#sandbox" + (S.scenario ? "-" + S.scenario : "")); } catch (e) { /* not allowed here */ }
  }
  // the sandbox's ❚❚/▶ buttons follow the site's pause as well as their own
  let shownPause = null;
  function syncPause() {
    const p = state.paused || (story.on ? story.paused : S.speed === 0);
    if (p === shownPause) return;
    shownPause = p;
    el("sbsPause").textContent = p ? "▶" : "❚❚"; el("sbStory").classList.toggle("paused", p);
    el("sbPlay").textContent = p ? "▶" : "❚❚"; el("sbPlay").setAttribute("aria-label", p ? "Пуск" : "Пауза");
  }
  function renderPanel() {
    const sc = SCENARIOS[S.scenario];
    el("sbTitle").textContent = sc ? sc.title : "Справжня Сонячна система";
    document.querySelector("#sandbox .sb-kicker").dataset.title = sc ? sc.title : "без змін";
    el("sbText").textContent = sc ? sc.text : "Тепер планети рухаються за законом тяжіння. Обери, що змінити, — і дивись, що станеться з усіма іншими.";
    document.querySelectorAll("#sbScenes button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.s === S.scenario)));
    el("sbSpeedOut").textContent = SPEEDS[S.speed][1];
    el("sbDirector").setAttribute("aria-pressed", String(S.director));
    el("sbSlower").disabled = S.speed <= 1; el("sbFaster").disabled = S.speed >= SPEEDS.length - 1;
    shownPause = null;                               // (syncPause redraws ❚❚/▶ with the site's pause in mind)
    el("sbPlay").textContent = S.speed === 0 ? "▶" : "❚❚";
    el("sbPlay").setAttribute("aria-label", S.speed === 0 ? "Пуск" : "Пауза");
  }
  let lastRead = "";
  function readout() {
    const t = earthTemp(), e = get("earth"), sun = get("sun");
    const temp = t === null ? "Землі більше немає" : `Земля: ${t > 0 ? "+" : t < 0 ? "−" : ""}${Math.abs(Math.round(t))} °C · ${e.p.distanceTo(sun.p).toFixed(2).replace(".", ",")} а. о. від Сонця`;
    const txt = `Минуло: ${S.days < 1 ? "0 діб" : years(S.days)} · ${temp}`;
    if (txt !== lastRead) { el("sbRead").textContent = txt; lastRead = txt; }
    const sl = S.speed > 0 && S.slow < 0.85;
    const out = sl ? "уповільнено" : SPEEDS[S.speed][1];
    if (el("sbSpeedOut").textContent !== out) { el("sbSpeedOut").textContent = out; el("sbSpeedOut").classList.toggle("slow", sl); }
  }

  // The effects' shaders are compiled once, when the sandbox first opens, not at the moment of a blow (a stutter
  // there would spoil it, on a phone most of all): one of each is built out of sight, compiled and thrown away.
  function warmUp() {
    try {
      const far = V().set(0, -1e5, 0);
      splash(far, V().set(0, 1, 0), 1);
      impact("venus", V().set(1, 0, 0), 1, 0.4);
      for (const id in S.shells) { const sh = S.shells[id]; sh.plume.g.visible = true; sh.plume.g.position.copy(far); }
      renderer.compile(scene, camera);
    } catch (e) { /* a missing piece only means compiling later */ }
    clearBooms();
    for (const id in S.shells) S.shells[id].plume.g.visible = false;
  }
  function open(key) {
    if (!S.trails) { makeTrails(); makeShells(); warmUp(); }
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
    byId.sun.group.scale.setScalar(SUN_K);
    setup(key || "");
    if (state.index >= 0) showOverview();
    if (STORIES[key]) startStory(key);
    try { history.replaceState(null, "", "#sandbox" + (S.scenario ? "-" + S.scenario : "")); } catch (e) { /* not allowed here */ }
  }
  function close() {
    endStory(false);
    endShot(false);
    S.on = false;
    document.body.classList.remove("sandboxing");
    el("sandbox").hidden = true;
    el("sandboxBtn").setAttribute("aria-pressed", "false");
    for (const id in S.trails) S.trails[id].visible = false;
    S.sun2.visible = false;
    hideShells(); clearBooms();
    byId.sun.group.scale.setScalar(1);
    if (typeof sunLight !== "undefined") sunLight.intensity = 1.7;
    for (const belt of typeof asteroidBelt !== "undefined" ? [asteroidBelt, kuiperBelt] : []) { if (belt.material.userData.o !== undefined) belt.material.opacity = belt.material.userData.o; belt.visible = true; }
    for (const id of ID.slice(1)) { byId[id].sbScale = 1; byId[id].group.scale.setScalar(1); byId[id].group.quaternion.identity(); byId[id].stretched = false; }
    clearStreams(); if (BHG) BHG.g.visible = false;
    unfreeMoons();
    for (const b of BODIES) {
      if (b.orbitLine) b.orbitLine.visible = state.orbits;
      b.group.visible = true;
    }
    state.jumped = true;                              // glide back to the real places
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* not allowed here */ }
  }
  // One frame: run the physics, then put the bodies where it says. Returns the moons' clock for placeAll.
  function step(dt) {
    direct(dt);
    // one pause for everything: the site's own "Пауза" stops a story too (and its effects), and the sandbox's ❚❚
    // buttons show it; the sandbox's buttons let the site go on again (js: wire)
    const hold = state.paused || (story.on && story.paused) || (!story.on && S.speed === 0);
    const fxdt = hold ? 0 : dt;
    const days = story.on ? (state.paused ? 0 : storyTick(dt)) : state.paused ? 0 : dt * SPEEDS[S.speed][0] * S.slow;
    syncPause();
    advance(days);
    watch();
    for (const b of S.bodies) {
      const B = byId[b.id];
      if (b.id === "sun2") { scenePos(b, S.sun2.position); S.sun2.visible = b.alive; continue; }
      if (!B) continue;
      if (S.free[b.id]) continue;
      if (b.id !== "sun") { B.group.visible = b.alive; shown(b, tRel).sub(shown(get("sun"), tLag)); B.simAU = tRel.clone(); }
      else if (b.bh && sbDist(rsAU(b)) < 1) {
        // the Sun collapsing into a hole of its own mass: it shrinks to nothing over a few seconds of the story
        const k = 1 - ramp(S.days, 0.0004, 0.0022);
        B.group.visible = k > 0.02; B.group.scale.setScalar(SUN_K * Math.max(k, 0.02));
      } else B.group.visible = !b.bh && (b.m > 0 || S.days < 0.0058);   // gone, but its last light is still on the way for 8 minutes
    }
    freeMoons(fxdt);
    shrinkClose(dt);
    stretch(); blackHole(fxdt); streams(days, fxdt);
    drawTrails();
    fireHits(); booms(fxdt); splashes(fxdt); impacts(fxdt); shells(fxdt);
    readout();
    // (stopped: the moons stay put instead of jumping to their exact places)
    if (hold || days === 0) return { jd: S.jd0 + S.days, dDays: 0, fine: S.lastFine !== false && S.lastFine };
    S.lastFine = days / Math.max(dt, 1e-3) <= 1;
    return { jd: S.jd0 + S.days, dDays: days, fine: S.lastFine };
  }

  /* ---------- Black holes: the hole, tides and streams of debris ---------- */
  // tf: how near a planet is to being torn apart, (r_t / r)³ (tides grow as 1/r³) — 1 at the tidal radius.
  function tidal(b) {
    const h = get("sun");
    if (!h || !h.bh || !b.alive || !R_KM[b.id]) return 0;
    return Math.pow(tidalAU(b, h) / Math.max(b.p.distanceTo(h.p), 1e-9), 3);
  }
  // The hole, as it would look: light bent round it by its gravity. A quad facing the camera traces, for each pixel,
  // the ray from the eye past the hole (Schwarzschild bending, in units of the horizon radius): rays that fall in
  // leave a black shadow about 2.6 times the horizon, rays that cross the thin glowing disc of gas round it pick up its
  // light — hotter inwards, brighter on the side turning towards us — and the disc's far side shows above and below
  // the shadow. Debris falling in makes the disc flare up. A hole of the Sun's own mass (6 km) is drawn far bigger
  // than it is, or it could not be seen.
  let BHG = null;
  const HOLE_S = 10;                                           // the quad's half-size, in horizon radii
  function makeBlackHole() {
    const g = new THREE.Group();
    const mat = new THREE.ShaderMaterial({
      uniforms: { R: { value: 1 }, rot: { value: new THREE.Matrix3() }, time: { value: 0 }, lum: { value: 1 }, fade: { value: 1 }, dim: { value: 1 } },
      vertexShader: `
        uniform float R; varying vec3 vW; varying vec3 vC;
        void main() {
          vec3 c = modelMatrix[3].xyz; vC = c;
          vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]), up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
          vW = c + (right * position.x + up * position.y) * R * ${HOLE_S.toFixed(1)};
          gl_Position = projectionMatrix * viewMatrix * vec4(vW, 1.0);
        }`,
      fragmentShader: `
        uniform float R; uniform mat3 rot; uniform float time; uniform float lum; uniform float fade; uniform float dim; varying vec3 vW; varying vec3 vC;
        float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
        vec3 bb(float t) { return clamp(vec3(1.0, 0.42 + 0.42 * t, 0.12 + 0.5 * t * t) * t, 0.0, 4.0); }
        void main() {
          vec3 c = vC;
          vec3 p = rot * ((cameraPosition - c) / R), v = normalize(rot * (vW - cameraPosition));
          float S = ${HOLE_S.toFixed(1)};
          float b = dot(p, v), cc = dot(p, p) - S * S, disc = b * b - cc;
          if (disc < 0.0) discard;
          if (cc > 0.0) { if (-b - sqrt(disc) < 0.0) discard; p += v * (-b - sqrt(disc)); }
          vec3 hc = cross(p, v); float h2 = dot(hc, hc);
          vec3 col = vec3(0.0); float alpha = 0.0;
          for (int i = 0; i < 140; i++) {
            float rr = length(p);
            if (rr < 1.0) { alpha = 1.0; break; }
            if (rr > S + 0.5 && dot(p, v) > 0.0) break;
            float dt = clamp(0.07 * rr, 0.02, 1.2);
            vec3 q0 = p;
            v += -1.5 * h2 * p / pow(rr, 5.0) * dt; p += v * dt;
            if (q0.y * p.y < 0.0) {
              vec3 q = mix(q0, p, q0.y / (q0.y - p.y));
              float qr = length(q.xz);
              if (qr > 2.6 && qr < 8.0) {
                float sw = time * 1.4 / pow(qr, 1.5), cs = cos(sw), sn = sin(sw);
                vec2 w = vec2(q.x * cs - q.z * sn, q.x * sn + q.z * cs);   // the gas turning, faster inwards
                float rings = 0.5 + 0.5 * (0.6 * vn(w * 1.1 + qr * 1.3) + 0.4 * vn(w * 3.2 - qr * 2.0));
                float temp = pow(3.0 / qr, 1.2) * smoothstep(2.6, 3.4, qr) * (1.0 - smoothstep(4.5, 8.0, qr));
                vec3 vel = normalize(vec3(-q.z, 0.0, q.x)) * sqrt(0.5 / max(qr - 1.0, 0.5));
                float gd = 1.0 / (1.0 - dot(vel, -normalize(v)) * 0.9);
                float I = temp * rings * gd * gd * gd * lum;
                float a = clamp(temp * 1.1, 0.0, 0.7) * dim * (1.0 - alpha);   // see-through, so planets behind still show
                col += bb(I * 0.85) * a; alpha += a;
                if (alpha > 0.98) break;
              }
            }
          }
          gl_FragColor = vec4(col * fade, alpha * fade);
        }`,
      transparent: true, depthWrite: false,
      blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
    });
    const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat);
    quad.frustumCulled = false;
    g.add(quad); g.visible = false; scene.add(g);
    // the disc is tilted well away from the planets' plane, so seen from above it shows edge-on-ish, bent over the shadow
    mat.uniforms.rot.value.setFromMatrix4(new THREE.Matrix4().makeRotationX(-1.25));
    BHG = { g, quad, mat, glow: 0 };
  }
  function blackHole(dt) {
    const h = get("sun");
    if (!BHG) { if (!h || !h.bh) return; makeBlackHole(); }
    BHG.g.visible = !!(h && h.bh);
    if (!BHG.g.visible) return;
    scenePos(h, BHG.g.position);
    // a hole of the Sun's own mass appears as the Sun shrinks away; it has little gas round it, so its disc is dimmer
    const small = sbDist(rsAU(h)) < 1, grow = small ? ramp(S.days, 0.0008, 0.0024) : 1;
    // Sgr A*'s true horizon (0.085 AU) would be drawn 12 units wide — on the sandbox's squeezed distances its shadow
    // and disc would cover Mercury's and Venus's orbits — so it is drawn at a third of that, with the planets around it.
    const R = small ? 1.1 * Math.max(grow, 0.05) : Math.min(4, sbDist(rsAU(h)));
    BHG.glow = Math.max(0, BHG.glow - dt * 0.6);
    const u = BHG.mat.uniforms;
    u.R.value = R; u.time.value += dt; u.fade.value = grow;
    // seen from close by (a camera beside a planet near the hole) the disc fills the sky: it is dimmed, so the planet stands out
    u.dim.value = 0.25 + 0.75 * ramp(camera.position.distanceTo(BHG.g.position) / R, 10, 18);
    u.lum.value = (small ? 0.75 : 1) + BHG.glow * 0.8;
  }
  // A torn planet becomes a stream of debris: pieces spread along the line to the hole (the near side moves faster
  // inwards), each then falls on its own, heating up — brighter the nearer it gets — until it crosses the horizon.
  const tPa = new THREE.Vector3(), tPb = new THREE.Vector3();
  const gauss = () => (Math.random() + Math.random() + Math.random() - 1.5) * 1.15;
  function spawnStream(rip) {
    const B = byId[rip.id], h = get("sun"), r = rip.p.length(), u = rip.p.clone().divideScalar(r);
    const lat = sbDist(r) / r, rad = (sbDist(r * 1.01) - sbDist(r)) / (0.01 * r);   // scene units per AU across / along
    const Rs = B.radius * (B.sbScale || 1), vl = rip.v.length();
    const side = V().crossVectors(u, Math.abs(u.y) > 0.9 ? V().set(1, 0, 0) : UP).normalize(), up2 = V().crossVectors(side, u);
    const N = 1000, P = new Float32Array(N * 3), W = new Float32Array(N * 3), pos = new Float32Array(N * 3), col = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const sl = Math.random() * 2 - 1, a = sl * 1.4 * Rs / rad, b1 = gauss() * 0.45 * Rs / lat, b2 = gauss() * 0.45 * Rs / lat;
      P[i * 3] = rip.p.x + u.x * a + side.x * b1 + up2.x * b2; P[i * 3 + 1] = rip.p.y + u.y * a + side.y * b1 + up2.y * b2; P[i * 3 + 2] = rip.p.z + u.z * a + side.z * b1 + up2.z * b2;
      const dv = sl * 0.07 * vl, w1 = gauss() * 0.006 * vl, w2 = gauss() * 0.006 * vl;
      W[i * 3] = rip.v.x + u.x * dv + side.x * w1 + up2.x * w2; W[i * 3 + 1] = rip.v.y + u.y * dv + side.y * w1 + up2.y * w2; W[i * 3 + 2] = rip.v.z + u.z * dv + side.z * w1 + up2.z * w2;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    if (!softTex) softTex = glowSprite("255,255,255", 1, 1).material.map;
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: Rs * 0.38, map: softTex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    pts.frustumCulled = false; scene.add(pts);
    const base = new THREE.Color(B.dot || "#ffffff");
    S.streams.push({ id: rip.id, P, W, pts, base, rt: tidalAU(get(rip.id) || { id: rip.id, m: MASS[rip.id] }, h), live: new Uint8Array(N).fill(1), age: 0 });
    boom(scenePos({ p: rip.p.clone().add(h.p) }, V()), Math.max(Rs, 0.8), true);
  }
  function clearStreams() {
    for (const st of S.streams) { scene.remove(st.pts); st.pts.geometry.dispose(); st.pts.material.dispose(); }
    S.streams.length = 0;
    if (BHG) BHG.glow = 0;
  }
  function streams(days, dt) {
    while (S.rips.length) spawnStream(S.rips.shift());
    if (!S.streams.length) return;
    const h = get("sun"), GM = G * h.m, rs = rsAU(h);
    for (const st of S.streams) {
      st.age += dt;
      const P = st.P, W = st.W, N = st.live.length;
      // time steps: a small fraction of the fall time of the piece nearest the hole
      let rmin = Infinity;
      for (let i = 0; i < N; i++) if (st.live[i]) rmin = Math.min(rmin, Math.hypot(P[i * 3], P[i * 3 + 1], P[i * 3 + 2]));
      if (rmin === Infinity) continue;
      const hstep = 0.03 * Math.sqrt(rmin * rmin * rmin / GM), n = Math.min(60, Math.ceil(days / Math.max(hstep, 1e-9))), dd = days / Math.max(n, 1);
      for (let k = 0; k < n && days > 0; k++) for (let i = 0; i < N; i++) {
        if (!st.live[i]) continue;
        const j = i * 3; let x = P[j], y = P[j + 1], z = P[j + 2];
        let r2 = x * x + y * y + z * z, f = -GM / (r2 * Math.sqrt(r2)) * dd;
        W[j] += x * f; W[j + 1] += y * f; W[j + 2] += z * f;
        P[j] = x += W[j] * dd; P[j + 1] = y += W[j + 1] * dd; P[j + 2] = z += W[j + 2] * dd;
        if (x * x + y * y + z * z < rs * rs) { st.live[i] = 0; BHG.glow = Math.min(1.2, BHG.glow + 0.004); }
      }
      const pa = st.pts.geometry.attributes.position, ca = st.pts.geometry.attributes.color, fade = Math.min(1, st.age / 0.3);
      for (let i = 0; i < N; i++) {
        const j = i * 3;
        if (!st.live[i]) { ca.setXYZ(i, 0, 0, 0); continue; }
        sbToScene(tPa.set(P[j], P[j + 1], P[j + 2]), tPb);
        pa.setXYZ(i, tPb.x, tPb.y, tPb.z);
        // the planet's own colour while still cool, then red, orange and white-hot as it nears the hole
        const heat = Math.min(1, Math.pow(st.rt / Math.hypot(P[j], P[j + 1], P[j + 2]), 1.2) - 0.6);
        const hk = Math.max(0, heat);
        ca.setXYZ(i, fade * Math.min(1, st.base.r * (1 - hk) + hk * 1.3), fade * Math.min(1, st.base.g * (1 - hk) + hk * (0.45 + 0.5 * hk)), fade * Math.min(1, st.base.b * (1 - hk) + hk * 0.25 * hk));
      }
      pa.needsUpdate = true; ca.needsUpdate = true;
    }
  }
  // Just before it is torn, a planet is drawn stretched along the line to the hole.
  const qStretch = new THREE.Quaternion(), X_AXIS = new THREE.Vector3(1, 0, 0);
  // Near a star its tides stretch a planet too, the last moments before it falls in: the Roche limit, where a fluid
  // body is torn apart, is 2.44 star radii × (star density / planet density)^⅓ — about 1.5 solar radii for the Earth.
  const RHO = { mercury: 5.43, venus: 5.24, earth: 5.51, mars: 3.93, jupiter: 1.33, saturn: 0.69, uranus: 1.27, neptune: 1.64 };
  function stretch() {
    const h = get("sun");
    for (const b of S.bodies) {
      const B = byId[b.id];
      if (!B || isStar(b) || !R_KM[b.id]) continue;
      let k = 0, star = h;
      if (h && h.bh) k = ramp(tidal(b), 0.45, 1);
      else if (b.alive) for (const o of S.bodies) if (shines(o)) {
        const roche = 2.44 * R_SUN_AU * Math.cbrt(1.41 * o.m / (RHO[b.id] || 3));
        const ks = ramp(Math.pow(roche / Math.max(b.p.distanceTo(o.p), 1e-9), 3), 0.3, 1.6);
        if (ks > k) { k = ks; star = o; }
      }
      if (k <= 0) { if (B.stretched) { B.group.quaternion.identity(); B.stretched = false; } continue; }
      scenePos(star, tPa); tPb.copy(tPa).sub(B.world).normalize();
      qStretch.setFromUnitVectors(X_AXIS, tPb); B.group.quaternion.copy(qStretch); B.stretched = true;
      const sc = B.sbScale || 1, sx = 1 + (h && h.bh ? 0.9 : 0.7) * k;
      B.group.scale.set(sc * sx, sc / Math.sqrt(sx), sc / Math.sqrt(sx));
    }
  }

  // Planets are drawn far bigger than their distances allow, so two that pass close would swallow each other on the
  // screen. While they are close, both are drawn smaller (moons and glow with them), so the gap between them is seen.
  const tA = new THREE.Vector3(), tB = new THREE.Vector3();
  // The second Sun too: it has no squeezed scale round it like the first, so a planet circling it 1–2 AU away was
  // drawn passing through it ("touching" it with nothing happening). Near it, both are drawn smaller.
  function shrinkClose(dt) {
    const P = S.bodies.filter(b => b.alive && !isStar(b) && byId[b.id] && !MOONSET.has(b.id));
    const stars = S.bodies.filter(s => s.alive && s.id === "sun2"), Rs = byId.sun.radius * SUN_K * 0.95;
    let ks = 1;
    for (const b of P) {
      const B = byId[b.id];
      let k = 1;
      scenePos(b, tA);
      for (const o of P) if (o !== b) k = Math.min(k, Math.max(0.12, scenePos(o, tB).distanceTo(tA) / ((B.radius + byId[o.id].radius) * 2.2)));
      for (const st of stars) {
        const kk = scenePos(st, tB).distanceTo(tA) / ((B.radius + Rs) * 2.0);
        if (kk < 1) { k = Math.min(k, Math.max(0.06, kk)); ks = Math.min(ks, Math.max(0.15, kk)); }
      }
      B.sbScale = (B.sbScale || 1) + (k - (B.sbScale || 1)) * Math.min(1, dt * (k < (B.sbScale || 1) ? 8 : 0.9));
      B.group.scale.setScalar(B.sbScale);
    }
    if (S.sun2) { S.sun2K = (S.sun2K || 1) + (ks - (S.sun2K || 1)) * Math.min(1, dt * (ks < (S.sun2K || 1) ? 8 : 0.9)); S.sun2.scale.setScalar(S.sun2K); }
  }

  // Wire the panel.
  const wire = () => {
    el("sandboxBtn").addEventListener("click", () => { S.on ? close() : open(""); if (typeof setMenu === "function") setMenu(false); });
    el("sbClose").addEventListener("click", close);
    el("sbReset").addEventListener("click", () => setup(S.scenario));
    document.querySelectorAll("#sbScenes button").forEach(b => b.addEventListener("click", () => {
      const k = b.dataset.s === S.scenario && !STORIES[b.dataset.s] ? "" : b.dataset.s;
      if (STORIES[k]) startStory(k); else setup(k);
      try { history.replaceState(null, "", "#sandbox" + (k ? "-" + k : "")); } catch (e) { /* not allowed here */ }
    }));
    // Time: one step per tap (no slider to overshoot); ❚❚ stops it and ▶ goes on at the speed it had.
    el("sbSlower").addEventListener("click", () => { S.speed = Math.max(1, (S.speed || S.resume || 2) - 1); renderPanel(); });
    el("sbFaster").addEventListener("click", () => { S.speed = Math.min(SPEEDS.length - 1, (S.speed || S.resume || 1) + 1); renderPanel(); });
    el("sbPlay").addEventListener("click", () => {
      if (state.paused) { el("pause").click(); if (!S.speed) S.speed = S.resume || 2; }   // the site was paused: go on
      else if (S.speed) { S.resume = S.speed; S.speed = 0; } else S.speed = S.resume || 2;
      shownPause = null; renderPanel();
    });
    el("sbOverview").addEventListener("click", () => { endShot(false); S.holdUntil = performance.now() + 8000; showOverview(); });
    el("sbDirector").addEventListener("click", () => { S.director = !S.director; S.holdUntil = 0; renderPanel(); });
    canvas.addEventListener("pointerdown", () => { if (S.on) S.holdUntil = performance.now() + 12000; });
    canvas.addEventListener("wheel", () => { if (S.on) S.holdUntil = performance.now() + 12000; }, { passive: true });
    el("sbsClose").addEventListener("click", () => endStory(true));
    // the card folds down to its title and buttons (remembered for the next visit)
    const fold = on => {
      el("sbStory").classList.toggle("min", on);
      el("sbsMin").setAttribute("aria-expanded", String(!on));
      el("sbsMin").setAttribute("aria-label", on ? "Розгорнути" : "Згорнути"); el("sbsMin").title = on ? "Розгорнути" : "Згорнути";
      try { localStorage.setItem("sbStoryMin", on ? "1" : ""); } catch (e) {}
    };
    try { if (localStorage.getItem("sbStoryMin")) fold(true); } catch (e) {}
    el("sbsMin").addEventListener("click", () => fold(!el("sbStory").classList.contains("min")));
    el("sbsTitle").addEventListener("click", () => { if (el("sbStory").classList.contains("min")) fold(false); });
    el("sbsAgain").addEventListener("click", () => startStory(story.key));
    el("sbsNext").addEventListener("click", () => {
      const st = story.steps[story.i];
      if (st.end) { endStory(false); setup(""); showOverview(); return; }
      if (!st.until || story.held < st.min && st.until()) storyStep(story.i + 1);   // nothing to wait for: go on
      else story.ff = true;                                                       // let time run fast to the event
    });
    el("sbsPause").addEventListener("click", () => {
      if (state.paused) { el("pause").click(); story.paused = false; }    // the site was paused: go on
      else story.paused = !story.paused;
      if (!story.paused) backToStory();
      shownPause = null; syncPause();
    });
    // the site's own "Пауза / Далі" (on a computer it is over the story): going on brings the story's shot back too
    el("pause").addEventListener("click", () => { if (S.on && story.on && !state.paused && !story.paused) backToStory(); });
    el("sbsSound").addEventListener("click", () => {
      const on = el("sbsSound").getAttribute("aria-pressed") !== "true";
      if (typeof tourMusicWanted !== "undefined") { tourMusicWanted = on; try { localStorage.setItem(TOUR_MUSIC_KEY, on ? "1" : "0"); } catch (e) { /* not saved */ } }
      setStoryMusic(on);
    });
    el("sbFold").addEventListener("click", () => {
      const min = el("sandbox").classList.toggle("min");
      el("sbFold").setAttribute("aria-expanded", String(!min));
      el("sbFold").textContent = min ? "▴" : "▾";
    });
  };
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", wire); else wire();

  return { get on() { return S.on; }, open, close, step, toScene: sbToScene, scenarios: Object.keys(SCENARIOS), _state: S, _shot: shot, _story: story, _storyStep: i => storyStep(i) };   // _state: for tests
})();
