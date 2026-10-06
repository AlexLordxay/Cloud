// Небозвід — camera, controls, the animation loop and start-up.
// Plain scripts sharing one scope; index.html loads them in order.
"use strict";

/* ---------- Camera state ---------- */
const state = { mode: "overview", index: -1, paused: false, rate: 0, live: true, simMs: Date.now(), flight: null, orbits: true, moonKm: 384400, moonVec: new THREE.Vector3(), fine: true };
const MIN_MS = Date.UTC(1800, 0, 1), MAX_MS = Date.UTC(2200, 11, 31);
const fmtTime = new Intl.DateTimeFormat("uk-UA", { hour: "2-digit", minute: "2-digit" });
const pad = n => String(n).padStart(2, "0");
function isoDate(ms) { const d = new Date(ms); return `${String(d.getFullYear()).padStart(4, "0")}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function setRate(i) {
  state.rate = i;
  $("speed").value = String(i);
  $("speedOut").textContent = RATES[i][1];
}
function setLive(on) {
  state.live = on;
  $("now").setAttribute("aria-pressed", String(on));
}
function jumpTo(ms, rate, label) {
  state.simMs = Math.min(MAX_MS, Math.max(MIN_MS, ms));
  state.jumped = true;
  setLive(false);
  if (rate != null) setRate(rate);
  if (state.paused) $("pause").click();
  if (label) showToast(`${label}: ${new Date(state.simMs).toLocaleDateString("uk-UA", { day: "numeric", month: "long", year: "numeric" })} Час іде зі швидкістю ${RATES[state.rate][1]}.`, 5000);
}
const fmtNum = (x, d) => x.toFixed(d).replace(".", ",");
function fmtAU(au) {
  const far = au * 149.6 >= 1000;
  return `${fmtNum(au, au < 0.1 ? 3 : au < 10 ? 2 : 1)} а. о. (${far ? fmtNum(au * 0.1496, 2) + " млрд" : Math.round(au * 149.6).toLocaleString("uk-UA") + " млн"} км)`;
}
let liveAt = 0;
function updateLive(force) {
  const now = performance.now();
  if (!force && now - liveAt < 500) return;
  liveAt = now;
  const el = $("live"), b = state.index >= 0 ? BODIES[state.index] : null, E = byId.earth;
  let txt = "";
  if (b && E.auVec) {
    if (b.id === "sun") txt = `Зараз від Землі: ${fmtAU(E.au)}`;
    else if (b.id === "moon") txt = `Зараз від Землі: ${Math.round(state.moonKm).toLocaleString("uk-UA")} км`;
    else if (!b.parent) txt = `Зараз від Сонця: ${fmtAU(b.au)}` + (b.id === "earth" ? "" : `\nВід Землі: ${fmtAU(b.auVec.distanceTo(E.auVec))}`);
    if ((b.id === "earth" || b.id === "sun") && eclipse.solar) txt += `\nЗараз ${eclipse.solar}`;
    if ((b.id === "moon" || b.id === "earth") && eclipse.lunar) txt += `\nЗараз ${eclipse.lunar}`;
    if (b.id === "mars") {
      const ls = Math.round(marsLs(b.auVec)) % 360, q = ["весна", "літо", "осінь", "зима"][Math.floor(ls / 90)];
      txt += `\nСезон: ${q} у північній півкулі (Ls ${ls}°)`;
      if (marsU.globalDust.value > 0.5) txt += "\nЗараз глобальна пилова буря";
      else if (ls > 180 && ls < 330) txt += "\nСезон пилових бур";
    }
  }
  el.textContent = txt;
  el.style.whiteSpace = "pre-line";
  el.hidden = !txt;
}
const tmp = new THREE.Vector3(), tmp2 = new THREE.Vector3();
const ORIGIN = new THREE.Vector3();

function overviewCam() {
  const aspect = innerWidth / innerHeight;
  const k = Math.max(1, 1.5 / aspect);
  return new THREE.Vector3(0, 190 * k, 300 * k);
}
function startFlight(getTarget, offset, dur, relBody) {
  controls.enabled = false;
  controls.minDistance = 0; controls.maxDistance = Infinity;
  state.flight = {
    t0: performance.now(), dur: reduceMotion ? 1 : dur,
    fromCam: camera.position.clone(), fromTgt: controls.target.clone(),
    getTarget, offset, relBody,
  };
}
function setActive(b) {
  const main = b ? (b.parent || b) : null;
  for (const m of MAIN) m.chip.setAttribute("aria-current", m === main ? "true" : "false");
  for (const x of BODIES) if (x.catChip) x.catChip.setAttribute("aria-current", x === b ? "true" : "false");
  for (const x of BODIES) if (x.orbitLine) x.orbitLine.material.opacity = x === b ? 0.55 : x.baseOpacity;
  if (main) main.chip.scrollIntoView({ block: "nearest", inline: "center" });
  $("overview").setAttribute("aria-pressed", b ? "false" : "true");
}
/* ---------- Links to a body or an event: nebozvid.com.ua/#saturn, #titan, #67p, #eclipse ---------- */
// Any body id works (#titan, #halley…); a few friendlier names and events have their own entries.
// The address bar follows the view, so a copied link opens what was on screen.
const LINKS = {
  "67p": { body: "cg67p" },
  "hale-bopp": { body: "halebopp" },
  eclipse: { body: "earth", date: "2027-08-02T09:10:00Z", rate: 1, label: "Затемнення 2 серпня 2027" },
  orionids: { body: "halley" },
};
const SLUG = { cg67p: "67p" };
function linkTarget(hash) {
  const k = decodeURIComponent((hash || "").replace(/^#/, "")).toLowerCase();
  if (!k) return null;
  if (LINKS[k]) return LINKS[k];
  return byId[k] ? { body: k } : null;
}
function openLink(t) {
  if (t.date) jumpTo(Date.parse(t.date), t.rate, t.label);
  focusBody(byId[t.body].index);
}
function setLinkHash(slug) {
  try { history.replaceState(null, "", slug ? "#" + slug : location.pathname + location.search); } catch (e) { /* not allowed here */ }
}
addEventListener("hashchange", () => { const t = linkTarget(location.hash); if (t) openLink(t); });

function focusBody(i) {
  const b = BODIES[i];
  state.mode = "focus"; state.index = i;
  const dir = b.id !== "sun" ? b.world.clone().normalize() : new THREE.Vector3(0, 0, 1);
  const narrow = Math.max(1, 1.1 / (innerWidth / innerHeight));
  const dist = b.comet ? 22 * narrow : b.radius * (b.rings === "saturn" ? 5.6 : b.id === "sun" ? 3.4 : b.ring ? 6 : 4.4) * narrow;
  const offset = dir.multiplyScalar(-dist).applyAxisAngle(tmp2.set(0, 1, 0), b.id === "sun" ? 0 : b.comet ? 1.25 : 0.62);
  offset.y += dist * (b.comet ? 0.45 : 0.26);
  if (b.id === "sun") offset.set(0, dist * 0.3, dist);
  startFlight(() => b.world, offset, 1900, b);
  renderInfo(b);
  setActive(b);
  const cur = linkTarget(location.hash);
  if (!cur || cur.body !== b.id) setLinkHash(SLUG[b.id] || b.id);
}
function stepMain(dir) {
  const cur = state.index >= 0 ? BODIES[state.index] : null;
  const main = cur ? (cur.parent || cur) : null;
  let k = main ? MAIN.indexOf(main) + dir : dir > 0 ? 0 : MAIN.length - 1;
  k = (k + MAIN.length) % MAIN.length;
  focusBody(MAIN[k].index);
}
function showOverview() {
  state.mode = "overview"; state.index = -1;
  startFlight(() => ORIGIN, overviewCam(), 2000, null);
  renderInfo(null);
  setActive(null);
  setLinkHash("");
}

$("prev").addEventListener("click", () => stepMain(-1));
$("next").addEventListener("click", () => stepMain(1));
$("overview").addEventListener("click", showOverview);
$("pause").addEventListener("click", () => {
  state.paused = !state.paused;
  $("pause").setAttribute("aria-pressed", String(state.paused));
  $("pause").textContent = state.paused ? "Далі" : "Пауза";
});
$("orbits").addEventListener("click", () => {
  state.orbits = !state.orbits;
  $("orbits").setAttribute("aria-pressed", String(state.orbits));
  BODIES.forEach(b => { if (b.orbitLine) b.orbitLine.visible = state.orbits; });
});
$("speed").addEventListener("input", e => {
  setRate(+e.target.value);
  if (state.rate !== 0) setLive(false);
});
$("now").addEventListener("click", () => {
  state.simMs = Date.now();
  setRate(0);
  setLive(true);
  if (state.paused) $("pause").click();
});
$("date").addEventListener("change", e => {
  if (!e.target.value) return;
  const [y, m, d] = e.target.value.split("-").map(Number);
  const cur = new Date(state.simMs), next = new Date(state.simMs);
  next.setFullYear(y, m - 1, d);
  next.setHours(cur.getHours(), cur.getMinutes(), cur.getSeconds());
  jumpTo(next.getTime());
});
// Swap one texture for another everywhere it is used (material slots and shader uniforms).
function swapTexture(oldT, newT, keepOld) {
  newT.wrapS = oldT.wrapS; newT.wrapT = oldT.wrapT; newT.needsUpdate = true;
  scene.traverse(o => {
    const mats = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : [];
    for (const m of mats) {
      for (const k of ["map", "bumpMap", "alphaMap"]) if (m[k] === oldT) { m[k] = newT; m.needsUpdate = true; }
      if (m.uniforms) for (const u of Object.values(m.uniforms)) if (u && u.value === oldT) u.value = newT;
    }
  });
  if (!keepOld) oldT.dispose();
}
function applyQuality(nextEco) {
  if (nextEco === eco) return;
  eco = nextEco;
  renderer.setPixelRatio(pixelRatio());
  renderer.setSize(innerWidth, innerHeight, false);
  for (const m of ecoMaterials) {
    if (eco) m.defines.ECO = 1; else delete m.defines.ECO;
    m.needsUpdate = true;
  }
  // Maps: updateHiRes drops the 4096 px versions in economy mode and brings them back on approach otherwise.
}
const Q_LABEL = { auto: "авто", high: "висока", eco: "економна" };
function updateQualityButton() {
  $("quality").textContent = `Якість: ${Q_LABEL[qualitySetting]}`;
  $("quality").title = eco ? "Зараз: економна графіка" : "Зараз: повна графіка";
}
$("quality").addEventListener("click", () => {
  qualitySetting = { auto: "high", high: "eco", eco: "auto" }[qualitySetting];
  try { localStorage.setItem(Q_KEY, qualitySetting); } catch (e) { /* not saved */ }
  applyQuality(qualitySetting === "eco" || (qualitySetting === "auto" && (detectLowEnd() || autoDegraded)));
  updateQualityButton();
  showToast({
    auto: `Якість: авто. Сайт сам обирає за пристроєм; зараз ${eco ? "економна" : "повна"} графіка.`,
    high: "Якість: висока. Карти 4096 пікселів і всі ефекти.",
    eco: "Якість: економна. Легші карти, нижча роздільність і спрощене Сонце — для телефонів і слабких комп'ютерів.",
  }[qualitySetting], 5000);
});
let toastTimer = 0;
function showToast(text, ms) {
  const t = $("toast");
  t.textContent = text; t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, ms);
}
let musicExplained = false;
$("music").addEventListener("click", async () => {
  if (!music) {
    music = createMusicPlayer();
    if (!music) { showToast("Цей браузер не підтримує звук на вебсторінках.", 5000); return; }
  }
  const on = await music.toggle();
  $("music").setAttribute("aria-pressed", String(on));
  if (on && !musicExplained) {
    musicExplained = true;
    showToast("Фонова музика — композиція в дусі космічних саундтреків, створена автором: lord-xay.", 6000);
  }
});
let soundExplained = false;
$("sound").addEventListener("click", async () => {
  if (!sunAudio) {
    sunAudio = createSunAudio();
    if (!sunAudio) { showToast("Цей браузер не підтримує звук на вебсторінках.", 5000); return; }
  }
  const on = await sunAudio.toggle();
  $("sound").setAttribute("aria-pressed", String(on));
  if (on && !soundExplained) {
    soundExplained = true;
    showToast("У космосі тиша: звук там не поширюється. Біля Сонця чути його справжні коливання, прискорені в 42 000 разів, а біля Марса, Юпітера, Сатурна й Землі — звуки за мотивами реальних записів апаратів.", 9000);
  }
});
// Phone menu: open/close from the button, close when tapping elsewhere.
function setMenu(open) {
  $("menuWrap").classList.toggle("open", open);
  $("menuBtn").setAttribute("aria-expanded", String(open));
  $("menuBtn").textContent = open ? "✕" : "☰";
}
$("menuBtn").addEventListener("click", e => { e.stopPropagation(); setMenu(!$("menuWrap").classList.contains("open")); });
addEventListener("pointerdown", e => {
  if (!$("menuWrap").contains(e.target)) setMenu(false);
  if (!catalogEl.contains(e.target) && !$("allBtn").contains(e.target)) setCatalog(false);
});
$("allBtn").addEventListener("click", () => setCatalog(catalogEl.hidden));
$("menuBtn").addEventListener("click", () => setCatalog(false));
$("overview").addEventListener("click", () => setMenu(false));

/* ---------- Support (Monobank jar) ---------- */
// Opens only when the visitor asks for it. Until the jar exists (empty link) every way in stays hidden.
// The amount is passed to the jar page as ?a=<UAH>; "Своя сума" opens it empty.
const JAR_URL = "https://send.monobank.ua/jar/AAWqhjPjcW";
const SUPPORT_SUMS = [20, 50, 100, 200];
function setSupport(open) {
  $("support").hidden = $("supportBack").hidden = !open;
  if (open) { setMenu(false); setCatalog(false); $("supportClose").focus(); }
}
if (JAR_URL) {
  $("supportSums").innerHTML = SUPPORT_SUMS.map(n => `<a href="${JAR_URL}?a=${n}" target="_blank" rel="noopener">${n} ₴</a>`).join("")
    + `<a class="own" href="${JAR_URL}" target="_blank" rel="noopener">Своя сума</a>`;
  $("supportBtn").hidden = $("supportIcon").hidden = $("supportLine").hidden = false;
  for (const id of ["supportBtn", "supportIcon", "supportLink"]) $(id).addEventListener("click", () => setSupport(true));
  $("supportClose").addEventListener("click", () => setSupport(false));
  $("supportBack").addEventListener("click", () => setSupport(false));
  // From the About page: nebozvid.com.ua/#support opens the panel.
  if (location.hash === "#support") setSupport(true);
}

// The info panel folds down to its name row; the choice is remembered (open by default on wide screens only).
const INFO_KEY = "planetarium.infoOpen";
function setInfoOpen(open, remember) {
  infoEl.classList.toggle("open", open);
  $("more").setAttribute("aria-expanded", String(open));
  $("more").textContent = open ? "Згорнути" : "Детальніше";
  if (remember) try { localStorage.setItem(INFO_KEY, open ? "1" : "0"); } catch (e) { /* not saved */ }
}
let infoStartOpen = innerWidth > 720;
try { const v = localStorage.getItem(INFO_KEY); if (v !== null) infoStartOpen = v === "1"; } catch (e) { /* storage blocked */ }
setInfoOpen(infoStartOpen, false);
$("more").addEventListener("click", () => setInfoOpen(!infoEl.classList.contains("open"), true));
addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "BUTTON" && e.key === " ") return;
  if (e.key === "ArrowRight") stepMain(1);
  else if (e.key === "ArrowLeft") stepMain(-1);
  else if (e.key === "Escape") { if (!$("support").hidden) setSupport(false); else if (!catalogEl.hidden) setCatalog(false); else showOverview(); }
  else if (e.key === " " && e.target === document.body) { e.preventDefault(); $("pause").click(); }
});


// Trackpad pinch and two-finger scroll: smooth zoom right away, scaled by how far the fingers moved.
// Chrome, Edge and Firefox send a pinch as a wheel event with ctrlKey; Safari on a Mac sends gesture events.
function dollyBy(scale) {
  if (state.flight || !controls.enabled) return;
  tmp2.copy(camera.position).sub(controls.target);
  const d = Math.min(controls.maxDistance, Math.max(controls.minDistance, tmp2.length() * scale));
  camera.position.copy(controls.target).add(tmp2.setLength(d));
}
let gestureAt = 0, welcomeClose = null;
addEventListener("wheel", e => {
  if (e.target !== canvas) return;
  e.preventDefault(); e.stopPropagation();
  if (welcomeClose) welcomeClose();
  if (e.ctrlKey && performance.now() - gestureAt < 200) return;
  const dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? innerHeight : 1);
  const k = (e.ctrlKey ? 0.012 : 0.0018) * controls.zoomSpeed;
  dollyBy(Math.exp(Math.max(-0.5, Math.min(0.5, dy * k))));
}, { capture: true, passive: false });
if (navigator.maxTouchPoints === 0) {
  let lastScale = 1;
  addEventListener("gesturestart", e => { e.preventDefault(); lastScale = 1; gestureAt = performance.now(); });
  addEventListener("gesturechange", e => {
    e.preventDefault(); gestureAt = performance.now();
    if (welcomeClose) welcomeClose();
    if (e.scale > 0) dollyBy(Math.pow(lastScale / e.scale, 1.4));
    lastScale = e.scale;
  });
  addEventListener("gestureend", e => e.preventDefault());
}

// First visit: a short hint above the dock, until the visitor dismisses it or starts exploring.
const HINT_KEY = "planetarium.hintSeen";
function showWelcome() {
  try { if (localStorage.getItem(HINT_KEY)) return; } catch (e) { /* storage blocked: show anyway */ }
  const mouse = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const rows = mouse ? [
    ["👆", "<b>Клікни планету</b> — полетиш до неї"],
    ["🖱️", "<b>Тягни</b> — обертати, <b>коліщатко</b> або <b>два пальці</b> на тачпаді — наблизити"],
    ["📅", "<b>Дата вгорі</b> — небо будь-якого дня"],
  ] : [
    ["👆", "<b>Торкнись планети</b> — полетиш до неї"],
    ["🤏", "<b>Два пальці</b> — наблизити, <b>один</b> — обертати"],
    ["📅", "<b>Дата вгорі</b> — небо будь-якого дня"],
  ];
  $("welcomeList").innerHTML = rows.map(([i, t]) => `<li><span class="ico" aria-hidden="true">${i}</span><span>${t}</span></li>`).join("");
  const el = $("welcome");
  el.hidden = false;
  requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add("show")));
  let gone = false;
  const close = () => {
    if (gone) return;
    gone = true; welcomeClose = null;
    try { localStorage.setItem(HINT_KEY, "1"); } catch (e) { /* not saved */ }
    el.classList.remove("show");
    setTimeout(() => { el.hidden = true; }, 800);
  };
  $("welcomeOk").addEventListener("click", close);
  canvas.addEventListener("pointerdown", close);
  welcomeClose = close;
}

// Click / tap a body in space
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let downAt = null;
canvas.addEventListener("pointerdown", e => { downAt = [e.clientX, e.clientY]; });
canvas.addEventListener("pointerup", e => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) return;
  const r = canvas.getBoundingClientRect();
  ptr.set((e.clientX - r.left) / r.width * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects(pickables, false)[0];
  if (hit && hit.object.userData.index !== state.index) focusBody(hit.object.userData.index);
});

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(pixelRatio());
  renderer.setSize(innerWidth, innerHeight, false);
});

/* ---------- Loop ---------- */
const clock = new THREE.Clock();
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

const tA = new THREE.Vector3(), tB = new THREE.Vector3(), tAU = new THREE.Vector3();
let lastClock = "", lastDate = "";

// Place every body for Julian date jd. dDays: simulated days since the last frame (for capped spins at high speed).
function placeAll(jd, dDays, fine) {
  for (const b of BODIES) {
    if (b.parent || b.id === "sun") continue;
    helioAU(b.id, jd, b.auVec);
    b.au = b.auVec.length();
    toScene(b.auVec, tB);
    // Rotation that carries the old Sun-direction to the new one: the follow camera applies it to keep the lighting.
    if (b.group.position.lengthSq() > 0) b.dq.setFromUnitVectors(tA.copy(b.group.position).normalize(), tAU.copy(tB).normalize());
    else b.dq.identity();
    b.group.position.copy(tB);
  }
  const d = jd - J2000;
  for (const b of BODIES) {
    if (!b.parent) continue;
    if (b.id === "moon" && fine) {
      const m = moonPos(jd);
      state.moonKm = m.dist;
      state.moonVec.set(Math.cos(m.lat) * Math.cos(m.lon), Math.sin(m.lat), -Math.cos(m.lat) * Math.sin(m.lon)).multiplyScalar(m.dist);
      b.theta = m.lon;
      b.group.position.set(Math.cos(m.lat) * Math.cos(m.lon) * b.a, Math.sin(m.lat) * b.a, -Math.cos(m.lat) * Math.sin(m.lon) * b.a);
    } else {
      if (fine) b.theta = GALILEAN[b.id] ? (GALILEAN[b.id][0] + GALILEAN[b.id][1] * d) * DEG : b.phase + TAU * d / b.period;
      else b.theta += clampAbs(TAU * dDays / b.period, 0.08);
      orbitPoint(b, b.theta, b.group.position);
    }
    b.tiltGroup.rotation.y = b.theta + PI;   // tidally locked: longitude 0 of the map faces the planet
  }
}

// In "auto", measure the frame rate for a few seconds after start; if the device can't keep up, switch to economy once.
const perf = { t0: 0, frames: 0, done: false };
function watchFrameRate() {
  if (perf.done || qualitySetting !== "auto" || eco) return;
  const now = performance.now();
  if (!perf.t0) { perf.t0 = now + 2500; return; }
  if (now < perf.t0) return;
  perf.frames++;
  if (now - perf.t0 > 5000) {
    perf.done = true;
    const fps = perf.frames / ((now - perf.t0) / 1000);
    if (fps < 28) {
      autoDegraded = true;
      applyQuality(true);
      updateQualityButton();
      showToast("Пристрій не встигав, тому графіка перемкнулася на економну. Змінити можна кнопкою «Якість».", 6000);
    }
  }
}

function tick() {
  const dt = Math.min(clock.getDelta(), 0.05);
  if (!document.hidden) watchFrameRate();
  const cur = state.index >= 0 ? BODIES[state.index] : null;

  // Simulated clock.
  const rateS = state.paused ? 0 : RATES[state.rate][0];
  if (!state.paused) state.simMs = state.live ? Date.now() : state.simMs + dt * rateS * 1000;
  if (state.simMs > MAX_MS || state.simMs < MIN_MS) {
    state.simMs = Math.min(MAX_MS, Math.max(MIN_MS, state.simMs));
    if (!state.paused) $("pause").click();
  }
  const jd = jdOf(state.simMs), dDays = dt * rateS / 86400, fine = rateS <= 86400;
  state.fine = fine;
  placeAll(jd, dDays, fine);
  if (state.jumped) {
    // After a date jump, glide to the body's new place instead of snapping the camera across the system.
    state.jumped = false;
    for (const b of BODIES) b.dq.identity();
    scene.updateMatrixWorld();
    for (const b of BODIES) b.group.getWorldPosition(b.world);
    if (state.index >= 0) focusBody(state.index);
  }

  for (const b of BODIES) {
    if (b.parent || !b.rot) continue;
    if (b.id === "earth" && rateS <= 3600) b.mesh.rotation.y = gmst(jd);   // the real meridian faces the Sun
    else b.mesh.rotation.y += clampAbs(TAU * dDays / b.rot, 0.04);
  }
  asteroidBelt.rotation.y += clampAbs(TAU * dDays / 1700, 0.01);
  kuiperBelt.rotation.y += clampAbs(TAU * dDays / 90000, 0.01);
  scene.updateMatrixWorld();
  for (const b of BODIES) b.group.getWorldPosition(b.world);
  updateShadows(fine ? state.moonVec : null);
  updateEarthDetail();
  updateHiRes(dt);

  // The Sun boils in real time (not sped up with the orbit clock).
  if (sunFx) sunFx.update(state.paused ? 0 : dt * (reduceMotion ? 0.3 : 1), camera);
  if (ioFx) ioFx.update(state.paused ? 0 : dt);
  for (const { b: c, fx } of cometFxs) {
    helioAU(c.id, jd + 1, tAU);
    toScene(tAU, tA).sub(c.group.position).normalize();
    fx.update(state.paused ? 0 : dt, clamp01(1.6 * (c.reach || 1) / c.au - 0.4) * (c.activity || 1), tB.copy(c.world).normalize(), tA);
  }

  if (sunAudio && sunAudio.on) {
    // Loud next to the Sun, fading with distance; near other bodies it is barely audible.
    const sun = byId.sun, dR = camera.position.distanceTo(sun.world) / sun.radius;
    const k = clamp01((dR - 1.2) / 10.8), near = 1 - k * k * (3 - 2 * k);
    const focusOther = state.index >= 0 && BODIES[state.index] !== sun;
    const sunLevel = state.paused ? 0 : near * (focusOther ? 0.08 : 1);
    sunAudio.setLevel(sunLevel);
    // Let the Sun's hum come through: the music steps back when the hum is loud.
    if (music && music.on) music.setDuck(1 - 0.65 * sunLevel);
    // Planet voices: only for the focused planet (or one of its moons), louder the closer the camera.
    const levels = {};
    const home = state.index >= 0 ? (BODIES[state.index].parent || BODIES[state.index]) : null;
    if (home && home.voice && !state.paused) {
      const k2 = clamp01((camera.position.distanceTo(home.world) / home.radius - 2) / 12);
      levels[home.id] = 1 - k2 * k2 * (3 - 2 * k2);
    }
    sunAudio.setVoices(levels);
  }

  // Jupiter: flow phase for the sliding bands and the turning Great Red Spot (slow in real time, faster when time is sped up).
  shadowU.jFlow.value += (state.paused ? 0 : dt * 0.04) + clampAbs(dDays * 0.25, 0.01);

  // Saturn: slow band drift and the spinning vortex inside the polar hexagon.
  shadowU.sFlow.value += (state.paused ? 0 : dt * 0.03) + clampAbs(dDays * 0.2, 0.008);

  // Neptune: bands on the real wind profile and drifting high clouds.
  shadowU.nFlow.value += (state.paused ? 0 : dt * 0.035) + clampAbs(dDays * 0.3, 0.01);
  shadowU.nTime.value += state.paused ? 0 : dt;

  // Venus: the cloud deck super-rotates (≈4 days) far faster than the planet (243 days), in the same retrograde sense.
  venusU.time.value += state.paused ? 0 : dt;
  venusU.drift.value.x += clampAbs(dDays * (1 / 4 - 1 / 243), 0.0015);
  venusU.drift.value.y += clampAbs(dDays * (1 / 3.7 - 1 / 243), 0.0017);
  for (const k in SURFACES) { const sv = SURFACES[k]; sv.u.surface.value += (sv.target - sv.u.surface.value) * Math.min(1, dt * 2.5); }

  // Mars weather: season and planet-wide storms follow the real date; dust drifts with simulated time.
  marsU.time.value += state.paused ? 0 : dt;
  marsU.flow.value += clampAbs(dDays * 0.04, 0.002) + (state.paused ? 0 : dt * 0.003);
  marsU.ls.value = marsLs(byId.mars.auVec) * DEG;
  marsU.globalDust.value = globalDustAt(state.simMs);

  if (earthClouds) {
    // Clouds drift with simulated time (capped at high speeds); shimmer, lightning and aurora run in real time.
    earthU.time.value += state.paused ? 0 : dt;
    earthU.drift.value.x += clampAbs(dDays * 0.02, 0.0004);
    earthU.drift.value.y += clampAbs(dDays * 0.031, 0.0006);
    // The cloud map is low-res, so thin it out as the camera nears the surface.
    const e = byId.earth, alt = camera.position.distanceTo(e.world) / e.radius - 1;
    const k = clamp01((alt - 0.12) / 1.0);
    earthU.cloudOpacity.value = 0.06 + 0.79 * k * k * (3 - 2 * k);
  }

  // Clock readout.
  const ds = isoDate(state.simMs), ts = fmtTime.format(state.simMs);
  if (ds !== lastDate && document.activeElement !== $("date")) { $("date").value = ds; lastDate = ds; }
  if (ts !== lastClock) { $("clockTime").textContent = ts; lastClock = ts; }
  updateLive(false);

  // Keep the lighting angle steady while following: turn the camera offset with the body's path around the Sun.
  const root = cur ? (cur.parent || cur) : null;
  const f = state.flight;
  if (f) {
    if (root && root.dq) f.offset.applyQuaternion(root.dq);
    const t = clamp01((performance.now() - f.t0) / f.dur), e = ease(t);
    const target = f.getTarget();
    const endCam = tmp.copy(target).add(f.offset);
    controls.target.lerpVectors(f.fromTgt, target, e);
    camera.position.lerpVectors(f.fromCam, endCam, e);
    camera.position.y += Math.sin(PI * e) * Math.min(f.fromCam.distanceTo(endCam) * 0.12, 60);
    camera.lookAt(controls.target);
    if (t >= 1) {
      state.flight = null;
      controls.enabled = true;
      const rb = f.relBody;
      if (rb) {
        const minR = rb.shape ? rb.radius * Math.max(...rb.shape) : rb.radius;
        controls.minDistance = rb.comet ? 0.4 : minR * (rb.id === "sun" ? 1.1 : 1.05);
        controls.maxDistance = rb.comet ? 400 : Math.max(rb.radius * 24, 12);
      } else {
        controls.minDistance = 25; controls.maxDistance = 1400;
      }
    }
  } else if (cur) {
    tmp.copy(camera.position).sub(controls.target);
    if (root.dq) tmp.applyQuaternion(root.dq);
    controls.target.copy(cur.world);
    camera.position.copy(controls.target).add(tmp);
  }
  // Near plane and drag speed follow the altitude, so the camera can skim the surface.
  const focusR = cur ? cur.radius * (cur.shape ? Math.min(...cur.shape) : 1) : 0;
  const dist = camera.position.distanceTo(controls.target);
  const near = cur ? Math.max(0.001, Math.min(0.5, (dist - focusR) * 0.3)) : 0.5;
  if (Math.abs(camera.near - near) > near * 0.05) { camera.near = near; camera.updateProjectionMatrix(); }
  if (cur && !state.flight) {
    const alt = dist / cur.radius - 1;
    controls.rotateSpeed = Math.max(0.03, Math.min(0.6, alt * 0.35));
    controls.zoomSpeed = Math.max(0.3, Math.min(0.9, alt * 0.8));
  } else {
    controls.rotateSpeed = 0.6; controls.zoomSpeed = 0.8;
  }
  if (!state.flight) controls.update();

  // Labels: main bodies in the overview; the focused body's family when close.
  const w = innerWidth, h = innerHeight;
  for (const b of BODIES) {
    const show = !cur ? !b.parent : root.moons && (b === root || b.parent === root) && b !== cur;
    let vis = false;
    if (show) {
      tmp.copy(b.world); tmp.y += b.radius + (b.parent ? 0.3 : 1.2);
      tmp.project(camera);
      vis = tmp.z < 1 && Math.abs(tmp.x) < 1.1 && Math.abs(tmp.y) < 1.1;
      if (vis) {
        // Whole pixels, and the DOM is touched only when a label moves or shows/hides (style writes cost on phones).
        const tr = `translate(${Math.round((tmp.x * 0.5 + 0.5) * w)}px, ${Math.round((-tmp.y * 0.5 + 0.5) * h)}px) translate(-50%, -100%)`;
        if (tr !== b.tagTr) { b.tag.style.transform = tr; b.tagTr = tr; }
      }
    }
    if (b.tag.hidden !== !vis) b.tag.hidden = !vis;
  }

  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

/* ---------- Build ---------- */
const loader = new THREE.TextureLoader();
function loadTexture(file, key) {
  return new Promise((resolve, reject) => {
    loader.load("textures/" + file, t => {
      if (!DATA_MAPS.has(key)) t.encoding = THREE.sRGBEncoding;
      t.anisotropy = maxAniso;
      resolve(t);
    }, undefined, () => reject(new Error(file)));
  });
}
// Large maps start at 2048 px; the 4096 px version loads only while the camera is near that body (updateHiRes).
function texFile(key) {
  const f = TEXTURES[key];
  return LARGE_MAPS.has(key) ? f.replace(".jpg", "_2k.jpg") : f;
}
// The scene opens once these are in (~1.8 MB); the other planets show their own colour for a moment, then their maps.
const FIRST_MAPS = ["sun", "earth", "earthNight", "earthSpec", "earthClouds", "moon", "saturnRing"];
const MAP_COLOUR = { mercury: "mercury", venus: "venus", mars: "mars", jupiter: "jupiter", saturn: "saturn", uranus: "uranus", neptune: "neptune" };
function colourTexture(hex) {
  const c = new THREE.Color(hex), t = new THREE.DataTexture(new Uint8Array([c.r * 255, c.g * 255, c.b * 255, 255]), 1, 1);
  t.encoding = THREE.sRGBEncoding; t.needsUpdate = true;
  return t;
}
let loadedTex = null;
function loadTextures() {
  const tex = {};
  loadedTex = tex;
  let done = 0;
  for (const k in MAP_COLOUR) tex[k] = colourTexture(byId[MAP_COLOUR[k]].dot);
  return Promise.all(FIRST_MAPS.map(k => loadTexture(texFile(k), k).then(t => {
    tex[k] = t;
    done++;
    $("barFill").style.width = `${(done / FIRST_MAPS.length) * 100}%`;
    $("loadText").textContent = `Завантажено карт: ${done} з ${FIRST_MAPS.length}`;
  }))).then(() => tex);
}
// 4096 px maps only where they show: a body in view whose disc is over ~420 device pixels across its radius
// (a 2048 px map has ~1000 texels over the visible hemisphere), for at most two bodies; back to 2048 px when it shrinks
// below ~260 px or two others are bigger. A 4K map takes ~40 MB of video memory, and phones have little.
// One download at a time; never in economy mode, never mid-flight.
const HIRES = { mercury: "mercury", venus: "venus", earth: "earth", moon: "moon", moonNormal: "moon", mars: "mars", jupiter: "jupiter", saturn: "saturn" };
const HIRES_FILE = { moonNormal: "moon_normal.jpg" };
const loRes = {}, hiRes = {};
let hiBusy = false, hiCheck = 0;
const hiV = new THREE.Vector3();
// Radius on screen in device pixels, and whether the disc is in view.
function discOf(id) {
  const b = byId[id], d = Math.max(camera.position.distanceTo(b.world), b.radius * 1.0001);
  const px = b.radius / (d * Math.tan(camera.fov * DEG / 2)) * renderer.domElement.height / 2;
  hiV.copy(b.world).project(camera);
  const m = 1 + 2 * px / renderer.domElement.height;
  return { px, inView: hiV.z < 1 && Math.abs(hiV.x) < m * 1.5 && Math.abs(hiV.y) < m };
}
function updateHiRes(dt) {
  if (!loadedTex || (hiCheck -= dt) > 0) return;
  hiCheck = 0.3;
  const keys = Object.keys(HIRES).filter(k => loadedTex[k] && loadedTex[k].image && loadedTex[k].image.width > 1);
  const disc = {};
  for (const k of keys) disc[HIRES[k]] = disc[HIRES[k]] || discOf(HIRES[k]);
  const big = Object.keys(disc).sort((a, b) => disc[b].px - disc[a].px).slice(0, 2);
  for (const k of keys) {
    const c = disc[HIRES[k]];
    if (hiRes[k] && (eco || c.px < 260 || !big.includes(HIRES[k]))) {
      swapTexture(hiRes[k], loRes[k]);
      loadedTex[k] = loRes[k]; hiRes[k] = null;
    }
  }
  if (eco || hiBusy || state.flight) return;
  const want = keys.filter(k => !hiRes[k] && big.includes(HIRES[k]) && disc[HIRES[k]].inView && disc[HIRES[k]].px > 420)
    .sort((a, b) => disc[HIRES[b]].px - disc[HIRES[a]].px)[0];
  if (!want) return;
  hiBusy = true;
  loadTexture(HIRES_FILE[want] || TEXTURES[want], want).then(t => {
    hiBusy = false;
    if (eco || hiRes[want] || discOf(HIRES[want]).px < 260) { t.dispose(); return; }
    loRes[want] = loadedTex[want];
    swapTexture(loRes[want], t, true);
    loadedTex[want] = hiRes[want] = t;
  }).catch(() => { hiBusy = false; });
}
async function build() {
  let tex;
  try {
    tex = await loadTextures();
  } catch (err) {
    showFallback("textures", `Не вдалося завантажити карту поверхні (${err.message}). Оновіть сторінку. Якщо відкриваєте файл локально, запустіть його через вебсервер, наприклад: python3 -m http.server`);
    return;
  }
  const jd0 = jdOf(state.simMs);
  BODIES.forEach((b, i) => buildBody(b, i, tex, jd0));
  placeAll(jd0, 0, true);
  BODIES.forEach(b => b.dq && b.dq.identity());
  setRate(0);
  scene.updateMatrixWorld();
  BODIES.forEach(b => b.group.getWorldPosition(b.world));
  renderInfo(null);
  setActive(null);

  const end = overviewCam();
  camera.position.set(end.x * 3.2, end.y * 1.6, end.z * 3.2);
  controls.target.set(0, 0, 0);
  camera.lookAt(0, 0, 0);
  renderer.compile(scene, camera);
  await new Promise(r => requestAnimationFrame(r));
  loaderEl.classList.add("done");
  setTimeout(preloadSurfaces, 5000);
  const first = linkTarget(location.hash);
  if (first) openLink(first); else startFlight(() => ORIGIN, end, 3200, null);
  setTimeout(showWelcome, reduceMotion ? 800 : 3800);
  updateQualityButton();
  tick();

  // The other planets: their own colour until the map arrives.
  for (const key in MAP_COLOUR) {
    loadTexture(texFile(key), key).then(t => { swapTexture(tex[key], t); tex[key] = t; }).catch(() => {});
  }
  // Moons and dwarf planets: likewise.
  for (const key of LATE_TEXTURES) {
    loadTexture(key + ".jpg", key).then(t => applyLateTexture(key, t)).catch(() => {});
  }
  loadTexture("moon_normal_2k.jpg", "moonNormal").then(t => {
    moonRelief.nmap.value = tex.moonNormal = t; moonRelief.nOn.value = 1;
  }).catch(() => {});
}
build();
