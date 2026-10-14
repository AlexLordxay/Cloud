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
  const S = { on: false, bodies: [], days: 0, speed: 3, scenario: "", jd0: 0, events: new Set(), trails: null, sun2: null, hits: [], booms: [], shells: {} };
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
      S.hits.push({ small: small.id, big: big.id, star: isStar(big) });
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
    S.days = 0; S.events.clear(); S.hits.length = 0; clearBooms(); hideShells();
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

  /* ---------- Effects: heat, frost, explosions ---------- */
  // A body's temperature (K) as a bare rock in the light it gets now: 278 K at 1 AU from one Sun; a star's light ∝ mass^3.5.
  function tempK(b) {
    let flux = 0;
    for (const s of S.bodies) if (isStar(s) && s.alive && s.m > 0 && s !== b) flux += Math.pow(s.m, 3.5) / Math.max(b.p.distanceToSquared(s.p), 1e-8);
    return 278 * Math.pow(flux, 0.25);
  }
  const ROCKY = ["mercury", "venus", "earth", "mars"];
  // A thin shell over each planet: it glows like hot metal (dull red → orange → yellow-white) when the planet gets
  // fierce light, and rocky planets frost over, white and patchy, when they lose it. It sits over the planet's own
  // material, whatever that is.
  function makeShells() {
    for (const id of ID.slice(1)) {
      const B = byId[id];
      const u = { heat: { value: 0 }, frost: { value: 0 } };
      const m = new THREE.Mesh(new THREE.SphereGeometry(B.radius * 1.015, 64, 40), new THREE.ShaderMaterial({
        uniforms: u, transparent: true, depthWrite: false,
        vertexShader: `varying vec3 vN; varying vec3 vW; varying vec3 vP;
          void main(){ vP = position; vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
        fragmentShader: `uniform float heat; uniform float frost; varying vec3 vN; varying vec3 vW; varying vec3 vP;
          float h(vec3 p){ return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
          float n3(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
            return mix(mix(mix(h(i), h(i + vec3(1,0,0)), f.x), mix(h(i + vec3(0,1,0)), h(i + vec3(1,1,0)), f.x), f.y),
                       mix(mix(h(i + vec3(0,0,1)), h(i + vec3(1,0,1)), f.x), mix(h(i + vec3(0,1,1)), h(i + vec3(1,1,1)), f.x), f.y), f.z); }
          void main(){
            vec3 V = normalize(cameraPosition - vW); float rim = 1.0 - max(dot(normalize(vN), V), 0.0);
            vec3 q = normalize(vP) * 3.0; float n = 0.55 * n3(q) + 0.3 * n3(q * 2.7) + 0.15 * n3(q * 7.0);
            vec3 hot = mix(vec3(0.55, 0.04, 0.0), vec3(1.0, 0.45, 0.08), smoothstep(0.2, 0.7, heat));
            hot = mix(hot, vec3(1.0, 0.92, 0.7), smoothstep(0.75, 1.0, heat));
            float ha = heat * (0.45 + 0.35 * n + 0.4 * rim);
            float fa = frost * smoothstep(0.62 - 0.5 * frost, 0.7 - 0.45 * frost, n) * 0.9;
            float a = clamp(ha + fa, 0.0, 1.0);
            vec3 c = (hot * ha * 1.6 + vec3(0.88, 0.94, 1.0) * fa) / max(a, 1e-3);
            gl_FragColor = vec4(c, a);
          }`,
      }));
      m.visible = false; B.tiltGroup.add(m);
      const glow = glowSprite("255,120,40", B.radius * 5, 0); glow.visible = false; B.group.add(glow);
      S.shells[id] = { m, u, glow, flash: 0 };
    }
  }
  function shells(dt) {
    for (const b of S.bodies) {
      const sh = S.shells[b.id];
      if (!sh) continue;
      const T = tempK(b);
      sh.flash = Math.max(0, sh.flash - dt * 0.5);
      const heat = Math.min(1, Math.max(0, (T - 600) / 1200) + sh.flash);
      const frost = ROCKY.includes(b.id) ? Math.min(1, Math.max(0, (175 - T) / 120)) : 0;
      sh.u.heat.value += (heat - sh.u.heat.value) * Math.min(1, dt * 3);
      sh.u.frost.value += (frost - sh.u.frost.value) * Math.min(1, dt * 1.5);
      sh.m.visible = b.alive && (sh.u.heat.value > 0.01 || sh.u.frost.value > 0.01);
      sh.glow.visible = b.alive && sh.u.heat.value > 0.05;
      sh.glow.material.opacity = 0.5 * sh.u.heat.value;
    }
  }
  function hideShells() { for (const id in S.shells) { S.shells[id].m.visible = false; S.shells[id].glow.visible = false; S.shells[id].flash = 0; } }

  // An explosion: a flash, a ring of shock running out, and debris that flies apart, slows and cools.
  let ringTex = null;
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
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ color: hot ? 0xffa050 : 0xffd090, size: size * 0.35, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
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
  function clearBooms() { for (const e of S.booms) scene.remove(e.g); S.booms.length = 0; }
  // Turn this frame's collisions into explosions: on the star's surface facing the planet, or where two planets met.
  function fireHits() {
    for (const h of S.hits) {
      const small = get(h.small), big = get(h.big);
      if (h.star) {
        const c = scenePos(big, V()), dir = scenePos(small, V()).sub(c);
        if (dir.lengthSq() < 1e-6) dir.set(1, 0, 0);
        boom(c.add(dir.normalize().multiplyScalar(byId.sun.radius * 1.05)), byId.sun.radius * 0.35, true);
      } else {
        boom(scenePos(small, V()), Math.max(byId[h.small].radius, 0.8), false);
        if (S.shells[h.big]) S.shells[h.big].flash = 1;   // the survivor glows from the impact
      }
    }
    S.hits.length = 0;
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
    hideShells(); clearBooms();
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
    fireHits(); booms(dt); shells(dt);
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
