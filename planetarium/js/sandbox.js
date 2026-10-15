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
    "stop-earth": { title: "Земля зупинилася", speed: 2,
      text: "Земля раптом зупинилася на своїй орбіті. Ніщо більше не відводить її вбік — і вона падає прямо на Сонце." },
  };
  const S = { on: false, bodies: [], days: 0, t: 0, speed: 5, scenario: "", jd0: 0, events: new Set(), trails: null, sun2: null, hits: [], booms: [], splashes: [], shells: {}, log: [], slow: 1, director: true, holdUntil: 0, cool: {} };
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
      collide();
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
  const HIT = { star: 0.006, planet: 0.004 };
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
  // "jupiter-earth": the same day, the Earth and Jupiter swapped.
  const STORY_START = {
    "jupiter-earth": {"jd":2461284.5,"bodies":[["sun",1,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "no-sun": {"jd":2461284.5,"bodies":[["sun",0,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "heavy-sun": {"jd":2461284.5,"bodies":[["sun",2,[0,0,0],[0,0,0]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.009067121410422596,-0.0013533878243529099,0.026736150795543694]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.01623758698677691,-0.0007747289772347885,-0.011804427963593489]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.006103149325228707,-9.606720727967957e-07,-0.015911724344803146]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.012617947830879106,0.00043480529313185204,-0.005983355099650645]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.0059818921752397,0.0001520486531615614,0.004375334065029435]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.0012562785245968655,-4.529654143409223e-05,-0.0054832253119529994]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0035113982721561854,5.15837649088316e-05,-0.0016441978961339032]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.00015515841646518425,-6.139143961414462e-05,-0.003154704488425253]]]},
    "two-suns": {"jd":2461284.5,"bodies":[["sun",1,[0,0,0],[-0.0031571457238594816,0,-0.002367859292894611]],["mercury",1.66e-07,[-0.37412871975394074,0.037835307808411316,-0.04308932160208013],[-0.012224267134282077,-0.0013533878243529099,0.024368291502649082]],["venus",2.448e-06,[0.42713524811837844,-0.03273709986437799,0.5888710816320306],[0.013080441262917427,-0.0007747289772347885,-0.0141722872564881]],["earth",3.04e-06,[0.9373057084200472,2.2663869282527352e-05,0.3744812715308984],[0.0029460036013692257,-9.606720727967957e-07,-0.018279583637697758]],["mars",3.227e-07,[0.5205122983414849,0.017159140685411713,-1.4278278325263192],[-0.01577509355473859,0.00043480529313185204,-0.008351214392545256]],["jupiter",0.0009548,[-3.3139558513459093,0.05698772074507977,-4.1289640748717416],[-0.009139037899099181,0.0001520486531615614,0.002007474772134824]],["saturn",0.0002859,[9.296131415160414,-0.39801345797913995,-1.614430627423567],[-0.004413424248456347,-4.529654143409223e-05,-0.00785108460484761]],["uranus",4.366e-05,[9.033600955578068,-0.05319776394240551,-17.214745517988877],[-0.0066685439960156665,5.15837649088316e-05,-0.0040120571890285145]],["neptune",5.151e-05,[29.841944808645934,-0.7140756416898539,-1.2808313774897009],[-0.003312304140324666,-6.139143961414462e-05,-0.005522563781319864]],["sun2",1,[-5.7,0,7.6000000000000005],[0.0031571457238594816,0,0.002367859292894611]]]},
  };
  function setup(key, fixed) {
    S.scenario = SCENARIOS[key] ? key : "";
    const start = fixed && STORY_START[key];
    if (start) S.jd0 = start.jd;
    S.bodies = start ? start.bodies.map(([id, m, p, v]) => body(id, m, V().fromArray(p), V().fromArray(v))) : realStart(S.jd0);
    S.days = 0; S.t = 0; S.t0 = 0; S.events.clear(); S.hits.length = 0; clearBooms(); hideShells();
    S.log.length = 0; S.slow = 1; S.cool = {}; endShot(false); renderLog();
    const sun = get("sun"), earth = get("earth"), jup = get("jupiter");
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
      earth.v.set(0, 0, 0);
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
    if (S.scenario === "no-sun") return cooled(288) - 273;
    if (S.scenario === "jupiter-earth") { let f = 0; for (const s of S.bodies) if (isStar(s) && s.alive && s.m > 0) f += Math.pow(s.m, 3.5) / Math.max(e.p.distanceToSquared(s.p), 1e-6); return Math.max(288 * Math.pow(f, 0.25), cooled(288)) - 273; }
    let flux = 0;
    for (const s of S.bodies) if (isStar(s) && s.alive && s.m > 0) flux += Math.pow(s.m, 3.5) / Math.max(e.p.distanceToSquared(s.p), 1e-6);
    return flux <= 0 ? -270 : Math.max(-270, 288 * Math.pow(flux, 0.25) - 273);
  }

  /* ---------- Effects: heat, frost, explosions ---------- */
  // A body's temperature (K) as a bare rock in the light it gets now: 278 K at 1 AU from one Sun; a star's light ∝ mass^3.5.
  // Without any star a planet does not freeze at once: its air, oceans and rock hold heat. Earth: below zero within a
  // week, about −70 °C after a year, −240 °C only after a million years (an interpolation in log time); others alike.
  const COOL = [[0, 0], [0.006, 0], [7, 0.125], [60, 0.24], [365, 0.345], [3650, 0.45], [1e5, 0.65], [1e6, 1]];
  function cooled(T0) {
    const d = S.days; let k = 1;
    while (k < COOL.length - 1 && d > COOL[k][0]) k++;
    const [d0, g0] = COOL[k - 1], [d1, g1] = COOL[k];
    const f = d <= d0 ? 0 : Math.min(1, Math.log((d + 1e-3) / (d0 + 1e-3)) / Math.log((d1 + 1e-3) / (d0 + 1e-3)));
    return T0 - (T0 - 33) * (g0 + (g1 - g0) * f);
  }
  function tempK(b) {
    if (S.scenario === "no-sun") return cooled(278 / Math.sqrt(b.r0 || 1));
    if (S.scenario === "jupiter-earth" && b.id === "earth") return Math.max(eqK(b), cooled(278));   // it cools for years
    return eqK(b);
  }
  function eqK(b) {
    let flux = 0;
    for (const s of S.bodies) if (isStar(s) && s.alive && s.m > 0 && s !== b) flux += Math.pow(s.m, 3.5) / Math.max(b.p.distanceToSquared(s.p), 1e-8);
    return 278 * Math.pow(flux, 0.25);
  }
  const ROCKY = ["mercury", "venus", "earth", "mars"];
  // How a planet changes with the light it gets, as in reality, in stages by its bare-rock temperature T (K):
  //  the Earth dries out first (330–520 K: the oceans boil off, it turns to desert, the clouds go);
  //  rocky planets char and crack (600–1100 K: a dark crust with magma glowing through the cracks, more and more of them);
  //  then melt (1100–1700 K: a sea of moving lava) and boil off a tail of vapour streaming away from the star (from ~900 K);
  //  gas giants have no ground: they glow hotter and hotter and blow off a tail; rocky ones frost over in the cold.
  // All of it is a shell over the planet's own material, shaded by the hottest star, plus a glow and a tail.
  const ramp = (x, a, b) => Math.min(1, Math.max(0, (x - a) / (b - a)));
  let tailTex = null;
  function makeShells() {
    tailTex = glowSprite("255,255,255", 1, 1).material.map;
    for (const id of ID.slice(1)) {
      const B = byId[id], gas = !ROCKY.includes(id);
      const u = { dry: { value: 0 }, crack: { value: 0 }, melt: { value: 0 }, frost: { value: 0 }, flash: { value: 0 }, dark: { value: 0 },
        time: { value: Math.random() * 50 }, sunDir: { value: new THREE.Vector3(1, 0, 0) } };
      const m = new THREE.Mesh(new THREE.SphereGeometry(B.radius * 1.018, 96, 64), new THREE.ShaderMaterial({
        uniforms: u, transparent: true, depthWrite: false, defines: gas ? { GAS: 1 } : {},
        vertexShader: `varying vec3 vN; varying vec3 vW; varying vec3 vP;
          void main(){ vP = normalize(position); vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
        fragmentShader: NOISE_GLSL + `uniform float dry; uniform float crack; uniform float melt; uniform float frost; uniform float flash; uniform float dark; uniform float time; uniform vec3 sunDir;
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
            // molten: flowing lava, bright where it is hottest, crusting over in dark rafts
            float lv = fbm(vP * 3.0 + vec3(time * 0.05, time * 0.03, 0.0)) * 0.5 + 0.5;
            float rafts = smoothstep(0.55, 0.7, fbm(vP * 5.0 - vec3(0.0, time * 0.04, 0.0)) * 0.5 + 0.5) * (1.0 - melt * 0.8);
            vec3 lava = mix(vec3(0.8, 0.12, 0.01), vec3(1.0, 0.65, 0.2), lv);
            lava = mix(lava, vec3(1.0, 0.92, 0.7), smoothstep(0.85, 1.0, melt) * lv);
            lava = mix(lava * 2.0, crust * lit, rafts);
            col = mix(col, lava, melt);
            a = mix(a, 1.0, melt);
          #else
            // a gas giant heating up: the cloud tops glow from dull red to orange, brightest towards the star
            float bands = 0.5 + 0.5 * sin(vP.y * 18.0 + fbm(vP * 3.0 + time * 0.04) * 3.0);
            vec3 hot = mix(vec3(0.7, 0.12, 0.02), vec3(1.0, 0.6, 0.2), bands * melt);
            float ga = melt * (0.45 + 0.35 * bands + 0.3 * max(ndl, 0.0));
            col = hot * 1.8 * ga; a = ga;
          #endif
            // the glowing limb of a hot planet, and the flash of an impact
            float hotRim = max(melt, crack * 0.6) * rim * rim;
            col += vec3(1.0, 0.4, 0.08) * (hotRim * 1.5 + flash * 2.0);
            a = max(a, max(hotRim, flash));
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
      // the tail: vapour boiled off the planet, streaming away from the star and fading
      const NT = 240, tp = new Float32Array(NT * 3), tc = new Float32Array(NT * 3);
      const tg = new THREE.BufferGeometry(); tg.setAttribute("position", new THREE.BufferAttribute(tp, 3)); tg.setAttribute("color", new THREE.BufferAttribute(tc, 3));
      const tail = new THREE.Points(tg, new THREE.PointsMaterial({ size: B.radius * 0.75, map: tailTex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
      tail.frustumCulled = false; tail.visible = false; scene.add(tail);
      const seeds = Array.from({ length: NT }, () => [Math.random(), Math.random() * 2 - 1, Math.random() * 2 - 1, 0.6 + Math.random() * 0.8]);
      // the Earth's blue air glow goes with the oceans
      // (and every rocky planet's air glow goes out when no star is left to light it)
      const air = ROCKY.includes(id) ? B.tiltGroup.children.filter(c => c !== m && c.material && c.material.blending === THREE.AdditiveBlending) : [];
      S.shells[id] = { m, u, glow, tail, seeds, flash: 0, gas, air };
    }
  }
  // No star shines any more (its last light, 8 minutes on the way, has passed too).
  const starless = () => S.days > 0.006 && !S.bodies.some(s => isStar(s) && s.alive && s.m > 0);
  const tSun = V(), tOff = V(), tSide = V(), tUp = V();
  function shells(dt) {
    // the Sun's light goes out with it (moons and other plain surfaces)
    if (typeof sunLight !== "undefined") sunLight.intensity += ((starless() ? 0.12 : 1.7) - sunLight.intensity) * Math.min(1, dt * 1.2);
    // the belts of small bodies held by the Sun scatter too: they fade away
    for (const belt of typeof asteroidBelt !== "undefined" ? [asteroidBelt, kuiperBelt] : []) {
      const m = belt.material, o = m.userData.o ?? (m.userData.o = m.opacity);
      m.opacity += ((starless() ? 0 : o) - m.opacity) * Math.min(1, dt * 0.8);
      belt.visible = m.opacity > 0.01;
    }
    for (const b of S.bodies) {
      const sh = S.shells[b.id];
      if (!sh) continue;
      const B = byId[b.id], T = tempK(b);
      sh.flash = Math.max(0, sh.flash - dt * 0.5);
      const ease = (u, v, k) => { u.value += (v - u.value) * Math.min(1, dt * k); };
      ease(sh.u.dry, b.id === "earth" ? ramp(T, 330, 520) : 0, 2);
      ease(sh.u.crack, sh.gas ? 0 : ramp(T, 600, 1100), 2);
      ease(sh.u.melt, sh.gas ? ramp(T, 700, 1800) : ramp(T, 1100, 1700), 2);
      ease(sh.u.frost, !ROCKY.includes(b.id) ? 0 : S.scenario === "no-sun" ? ramp(S.days, 5, 400) : S.scenario === "jupiter-earth" && b.id === "earth" ? ramp(S.days, 30, 700) : ramp(-T, -175, -55), 1.5);
      sh.u.flash.value = sh.flash;
      ease(sh.u.dark, starless() ? 0.7 : 0, 1.2);
      sh.u.time.value += dt;
      // the brightest star lights the shell
      let best = null, bf = 0;
      for (const s of S.bodies) if (isStar(s) && s.alive && s.m > 0) { const f = Math.pow(s.m, 3.5) / Math.max(b.p.distanceToSquared(s.p), 1e-8); if (f > bf) { bf = f; best = s; } }
      if (best) sh.u.sunDir.value.copy(scenePos(best, tSun)).sub(B.world).normalize();
      const u = sh.u, any = u.dry.value + u.crack.value + u.melt.value + u.frost.value + u.flash.value + u.dark.value;
      sh.m.visible = b.alive && any > 0.01;
      const heat = Math.max(u.crack.value * 0.6, u.melt.value, u.flash.value);
      sh.glow.visible = b.alive && heat > 0.03;
      sh.glow.material.opacity = 0.55 * heat;
      // the Earth's clouds burn away as it dries
      if (b.id === "earth" && typeof earthClouds !== "undefined" && earthClouds) earthClouds.visible = !b.alive || u.dry.value < 0.4;
      for (const c of sh.air) c.visible = u.dry.value < 0.5 && u.crack.value < 0.3 && u.dark.value < 0.3;
      // the vapour tail
      const tk = b.alive && best ? ramp(T, 850, 1600) : 0;
      sh.tail.visible = tk > 0.01;
      if (sh.tail.visible) {
        tOff.copy(sh.u.sunDir.value).negate();                  // away from the star
        tSide.crossVectors(tOff, Math.abs(tOff.y) > 0.9 ? tUp.set(1, 0, 0) : tUp.set(0, 1, 0)).normalize(); tUp.crossVectors(tSide, tOff);
        const pa = sh.tail.geometry.attributes.position, ca = sh.tail.geometry.attributes.color, L = B.radius * (4 + 14 * tk);
        for (let k = 0; k < sh.seeds.length; k++) {
          const [s0, x, y, sp] = sh.seeds[k], f = (s0 + sh.u.time.value * 0.25 * sp) % 1, d = f * L, w = B.radius * (0.5 + 1.6 * f);
          pa.setXYZ(k, B.world.x + tOff.x * (B.radius + d) + (tSide.x * x + tUp.x * y) * w, B.world.y + tOff.y * (B.radius + d) + (tSide.y * x + tUp.y * y) * w, B.world.z + tOff.z * (B.radius + d) + (tSide.z * x + tUp.z * y) * w);
          const fade = (1 - f) * (1 - f) * tk * 0.55;
          ca.setXYZ(k, fade, fade * (0.5 - 0.3 * f), fade * (0.15 + 0.2 * f));
        }
        pa.needsUpdate = true; ca.needsUpdate = true;
      }
    }
  }
  function hideShells() {
    for (const id in S.shells) { const sh = S.shells[id]; sh.m.visible = sh.glow.visible = sh.tail.visible = false; sh.flash = 0; for (const k of ["dry", "crack", "melt", "frost", "flash", "dark"]) sh.u[k].value = 0; }
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
    S.booms.length = 0; S.splashes.length = 0;
  }

  // A planet falling into a star: the surface takes the blow like a flare. Arcs of glowing plasma leap out of the spot,
  // hang and fall back as they fade (drawn like the Sun's own prominences), a bright wave runs out over the surface,
  // and the spot flashes. c: the star's centre in the scene, dir: towards the impact, R: the star's radius on screen.
  function splash(c, dir, R) {
    const g = new THREE.Group(); g.position.copy(c); scene.add(g);
    const A = dir.clone().normalize();
    const arcs = [];
    for (let i = 0; i < 14; i++) {
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
      const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 72, R * (0.03 + Math.random() * 0.04), 10, false), new THREE.ShaderMaterial({
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
      g.add(m); arcs.push({ m, u, delay: Math.random() * 0.5, speed: 0.8 + Math.random() * 0.6 });
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
    S.splashes.push({ g, arcs, wu, flash, t: 0, R });
  }
  function splashes(dt) {
    for (let k = S.splashes.length - 1; k >= 0; k--) {
      const e = S.splashes[k]; e.t += dt;
      const t = e.t;
      for (const a of e.arcs) {
        const x = Math.max(0, t - a.delay) * a.speed;
        // up fast, hang, then sink back as it cools
        a.u.grow.value = Math.min(1, x / 0.9) * (1 - 0.6 * smooth01((x - 3.0) / 3.0));
        a.u.life.value = Math.min(1, x / 0.3) * (1 - smooth01((x - 2.8) / 3.2));
        a.u.time.value += dt;
      }
      e.wu.w.value = 1.4 * (1 - Math.exp(-t * 0.9));
      e.wu.k.value = 1 - smooth01((t - 2) / 3);
      e.flash.material.opacity = Math.max(0, 1 - t / 1.2);
      e.flash.scale.setScalar(e.R * (1.5 + 2.5 * Math.min(1, t / 0.3)));
      if (t > 8) { scene.remove(e.g); e.g.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); }); S.splashes.splice(k, 1); }
    }
  }
  const smooth01 = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  // Turn this frame's collisions into explosions: on the star's surface facing the planet, or where two planets met.
  function fireHits() {
    for (const h of S.hits) {
      const small = get(h.small), big = get(h.big);
      if (h.star) {
        const c = scenePos(big, V()), dir = scenePos(small, V()).sub(c);
        if (dir.lengthSq() < 1e-6) dir.set(1, 0, 0);
        splash(c, dir, byId.sun.radius * SUN_K * (big.id === "sun2" ? 0.95 : 1));
      } else {
        boom(scenePos(small, V()), Math.max(byId[h.small].radius, 0.8), false);
        if (S.shells[h.big]) S.shells[h.big].flash = 1;   // the survivor glows from the impact
      }
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
      if (!b.alive || isStar(b)) continue;
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
      const half = gap * 0.5 + pr * 3, dist = half / Math.tan(camera.fov * DEG / 2) * 1.35 * shot.dk;
      sT.copy(sDir).multiplyScalar(-gap * 0.5 + gap * 0.18);
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
    const k = 1 - Math.exp(-dt * (shot.t < 2.5 ? 1.6 : 4));   // glide in, then hold steady on the planet
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
        text: "Меркурій тепер підходить до Сонця втричі ближче, ніж раніше, і розжарюється до лави. Через 4 роки він врізається у Венеру на швидкості 60 км/с. Венера поглинає його." },
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
        life: "Люди: поки що нічого не помічають.",
        text: "Уяви: Земля раптом зупинилася на своїй орбіті. Її швидкість — 30 км/с — щезла. Ніщо більше не несе її вбік, і Сонце починає тягнути її до себе." },
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
    if (!st.end && story.held >= st.min && done && story.after >= (st.after || 0)) storyStep(story.i + 1);
    // touching the scene hands the camera to the viewer for a while; then it glides back
    const held = performance.now() < S.holdUntil;
    if (held) { if (!story.wasHeld) controls.enabled = true; }
    else {
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
  function renderPanel() {
    const sc = SCENARIOS[S.scenario];
    el("sbTitle").textContent = sc ? sc.title : "Справжня Сонячна система";
    document.querySelector("#sandbox .sb-kicker").dataset.title = sc ? sc.title : "без змін";
    el("sbText").textContent = sc ? sc.text : "Тепер планети рухаються за законом тяжіння. Обери, що змінити, — і дивись, що станеться з усіма іншими.";
    document.querySelectorAll("#sbScenes button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.s === S.scenario)));
    el("sbSpeedOut").textContent = SPEEDS[S.speed][1];
    el("sbDirector").setAttribute("aria-pressed", String(S.director));
    el("sbSlower").disabled = S.speed <= 1; el("sbFaster").disabled = S.speed >= SPEEDS.length - 1;
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

  function open(key) {
    if (!S.trails) { makeTrails(); makeShells(); }
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
    for (const id of ID.slice(1)) { byId[id].sbScale = 1; byId[id].group.scale.setScalar(1); }
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
    const days = story.on ? storyTick(dt) : state.paused ? 0 : dt * SPEEDS[S.speed][0] * S.slow;
    advance(days);
    watch();
    for (const b of S.bodies) {
      const B = byId[b.id];
      if (b.id === "sun2") { scenePos(b, S.sun2.position); S.sun2.visible = b.alive; continue; }
      if (!B) continue;
      if (b.id !== "sun") { B.group.visible = b.alive; shown(b, tRel).sub(shown(get("sun"), tLag)); B.simAU = tRel.clone(); }
      else B.group.visible = b.m > 0 || S.days < 0.0058;   // gone, but its last light is still on the way for 8 minutes
    }
    shrinkClose(dt);
    drawTrails();
    fireHits(); booms(dt); splashes(dt); shells(dt);
    readout();
    return { jd: S.jd0 + S.days, dDays: days, fine: days / Math.max(dt, 1e-3) <= 1 };
  }

  // Planets are drawn far bigger than their distances allow, so two that pass close would swallow each other on the
  // screen. While they are close, both are drawn smaller (moons and glow with them), so the gap between them is seen.
  const tA = new THREE.Vector3(), tB = new THREE.Vector3();
  function shrinkClose(dt) {
    const P = S.bodies.filter(b => b.alive && !isStar(b) && byId[b.id]);
    for (const b of P) {
      const B = byId[b.id];
      let k = 1;
      scenePos(b, tA);
      for (const o of P) if (o !== b) k = Math.min(k, Math.max(0.12, scenePos(o, tB).distanceTo(tA) / ((B.radius + byId[o.id].radius) * 2.2)));
      B.sbScale = (B.sbScale || 1) + (k - (B.sbScale || 1)) * Math.min(1, dt * 4);
      B.group.scale.setScalar(B.sbScale);
    }
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
      if (S.speed) { S.resume = S.speed; S.speed = 0; } else S.speed = S.resume || 2;
      renderPanel();
    });
    el("sbOverview").addEventListener("click", () => { endShot(false); S.holdUntil = performance.now() + 8000; showOverview(); });
    el("sbDirector").addEventListener("click", () => { S.director = !S.director; S.holdUntil = 0; renderPanel(); });
    canvas.addEventListener("pointerdown", () => { if (S.on) S.holdUntil = performance.now() + 12000; });
    canvas.addEventListener("wheel", () => { if (S.on) S.holdUntil = performance.now() + 12000; }, { passive: true });
    el("sbsClose").addEventListener("click", () => endStory(true));
    el("sbsAgain").addEventListener("click", () => startStory(story.key));
    el("sbsNext").addEventListener("click", () => {
      const st = story.steps[story.i];
      if (st.end) { endStory(false); setup(""); showOverview(); return; }
      if (!st.until || story.held < st.min && st.until()) storyStep(story.i + 1);   // nothing to wait for: go on
      else story.ff = true;                                                       // let time run fast to the event
    });
    el("sbsPause").addEventListener("click", () => {
      story.paused = !story.paused;
      el("sbsPause").textContent = story.paused ? "▶" : "❚❚";
      el("sbStory").classList.toggle("paused", story.paused);
    });
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

  return { get on() { return S.on; }, open, close, step, toScene: sbToScene, scenarios: Object.keys(SCENARIOS), _state: S, _shot: shot, _story: story };   // _state: for tests
})();
