// Небозвід — the guided tour: the camera flies from stop to stop on its own, circles each body slowly and shows a
// short text. Touching the scene pauses it; ‹ › step back and forth; ✕ or Esc ends it. Opens from the menu, from the
// first-visit hint and by the link nebozvid.com.ua/#tour.
"use strict";

// Each stop: body id (null: the whole system), title, text; optional `under` — a second text shown halfway, when the
// clouds or haze are taken off (Venus, Titan); optional `date` — comets are shown in a year when they were near the Sun,
// with the coma and tails out, rather than as a cold speck far away; `zoom` brings the camera that much closer.
const TOUR = [
  { id: "sun", title: "Сонце", text: "Наша зірка. У ньому 99,86 % маси всієї Сонячної системи, а його світло летить до Землі 8 хвилин 20 секунд." },
  { id: "venus", title: "Венера", text: "Найгарячіша планета: +464 °C, гарячіше, ніж на Меркурії. Суцільні хмари із сірчаної кислоти ховають поверхню.",
    under: "А так виглядає поверхня під хмарами — радарна карта апарата Magellan: вулкани, лавові рівнини, гори." },
  { id: "earth", title: "Земля", text: "Єдиний відомий світ із життям. Удень над океанами пливуть хмари, а на нічному боці світяться міста." },
  { id: "moon", title: "Місяць", text: "Завжди повернутий до нас одним боком. Кратери — сліди ударів за мільярди років. Тут ходили 12 людей." },
  { id: "mars", title: "Марс", text: "Тут найвища гора Сонячної системи — вулкан Олімп, утричі вищий за Еверест. А пилові бурі часом накривають усю планету." },
  { id: "jupiter", title: "Юпітер", text: "Найбільша планета. Велика червона пляма — буря, ширша за Землю, яку спостерігають уже понад 150 років." },
  { id: "io", title: "Іо", text: "Найвулканічніший світ: сотні діючих вулканів. Надра Іо розігрівають припливи від сусіда-велетня Юпітера." },
  { id: "europa", title: "Європа", text: "Під кригою — солоний океан, і води в ньому більше, ніж на всій Землі. Одне з найкращих місць для пошуку життя." },
  { id: "saturn", title: "Сатурн", text: "Кільця з льоду й каміння мають сотні тисяч кілометрів у ширину, а завтовшки подекуди лише десятки метрів." },
  { id: "titan", title: "Титан", text: "Єдиний супутник зі щільною атмосферою. Ззовні — гладка помаранчева куля: поверхню ховає густий смог.",
    under: "А під серпанком — дюни, гори й моря з рідкого метану біля полюса. Це інфрачервона карта апарата Cassini." },
  { id: "enceladus", title: "Енцелад", text: "Крижаний супутник, з тріщин якого б’ють гейзери води. Вони живлять одне з кілець Сатурна." },
  { id: "uranus", title: "Уран", text: "Лежить на боці: вісь нахилена на 98°. Тому на кожному полюсі 42 роки триває день і 42 роки — ніч." },
  { id: "neptune", title: "Нептун", text: "Найвітряніша планета: вітри до 2000 км/год. Його спершу обчислили на папері, а вже потім побачили в телескоп." },
  { id: "pluto", title: "Плутон", text: "Карликова планета із «серцем» з азотного льоду. Апарат New Horizons пролетів повз нього 2015 року." },
  { id: "cg67p", title: "Комета 67P", date: "2015-07-20T00:00:00Z", rate: 3, zoom: 0.3,
    text: "Липень 2015-го, комета біля Сонця. Її відкрили в Києві, а 2014 року на неї вперше в історії сів апарат — «Філи»." },
  { id: "halley", title: "Комета Галлея", date: "1986-01-20T12:00:00Z", rate: 3, zoom: 0.5,
    text: "Січень 1986-го, останній прихід. Повертається раз на 76 років, наступного разу — 2061-го. Її пил дає метеори Оріоніди." },
  { id: "halebopp", title: "Комета Гейла–Боппа", date: "1997-03-22T00:00:00Z", rate: 3, zoom: 0.6,
    text: "Березень 1997-го. Ядро завбільшки 60 км, тож півтора року її було видно без телескопа — рекорд." },
  { id: null, title: "Уся Сонячна система", text: "Планети стоять так, як зараз на небі. Тепер досліджуй сам: торкнись будь-якої планети." },
];
const tour = { on: false, i: 0, paused: false, held: 0, last: 0, dur: 0, half: 0, under: false, past: false };
const tourEl = $("tour");

// Long enough to read the text calmly once the camera has arrived.
const stopDur = text => Math.max(9, 3.5 + text.split(/\s+/).length * 0.42) * 1000;

function tourStep(i) {
  leaveStop();
  tour.i = Math.max(0, Math.min(TOUR.length - 1, i));
  const st = TOUR[tour.i];
  tour.held = 0; tour.under = false;
  tour.half = st.under ? stopDur(st.text) : 0;
  tour.dur = stopDur(st.text) + (st.under ? stopDur(st.under) : 0);
  $("tourCount").textContent = `${tour.i + 1} / ${TOUR.length}`;
  $("tourTitle").textContent = st.title;
  $("tourText").textContent = st.text;
  $("tourPrev").disabled = tour.i === 0;
  $("tourNext").textContent = tour.i === TOUR.length - 1 ? "Готово" : "›";
  $("tourNext").setAttribute("aria-label", tour.i === TOUR.length - 1 ? "Завершити екскурсію" : "Далі");
  // the text card fades in anew for each stop
  tourEl.classList.remove("show"); void tourEl.offsetWidth; tourEl.classList.add("show");
  // comets: off to a year when they were active; back to today when the tour moves on
  if (st.date) { jumpTo(Date.parse(st.date), st.rate); tour.past = true; }
  else if (tour.past) { backToNow(); }
  if (st.id) focusBody(byId[st.id].index); else showOverview();
  setTourPaused(false);
}
function backToNow() {
  tour.past = false;
  state.simMs = Date.now(); state.jumped = true;
  setRate(0); setLive(true);
}
// Leaving a stop puts back what the tour changed there (clouds, haze).
function leaveStop() {
  const st = TOUR[tour.i];
  if (tour.under && st && SURFACES[st.id] && SURFACES[st.id].on) toggleSurface(st.id);
  tour.under = false;
}
function showUnder() {
  const st = TOUR[tour.i];
  tour.under = true;
  if (!SURFACES[st.id].on) toggleSurface(st.id);
  const p = $("tourText");
  p.classList.add("swap");
  setTimeout(() => { p.textContent = st.under; p.classList.remove("swap"); }, 450);
}
function setTourPaused(p) {
  tour.paused = p;
  controls.autoRotate = !p && !reduceMotion;
  $("tourPause").textContent = p ? "▶" : "❚❚";
  $("tourPause").setAttribute("aria-label", p ? "Продовжити" : "Пауза");
  tourEl.classList.toggle("paused", p);
}
// Tour music (js/audio.js): on by default, the choice is remembered. The site's own music steps aside meanwhile.
const TOUR_MUSIC_KEY = "planetarium.tourMusic";
let tourMusic = null, tourMusicWanted = true, siteMusicWas = false;
try { tourMusicWanted = localStorage.getItem(TOUR_MUSIC_KEY) !== "0"; } catch (e) { /* storage blocked */ }
async function setTourMusic(on) {
  $("tourSound").setAttribute("aria-pressed", String(on));
  if (on && !tourMusic) tourMusic = createMusicPlayer(createCinematicMusic);
  if (tourMusic && tourMusic.on !== on) await tourMusic.toggle();
}
function startTour() {
  if (welcomeClose) welcomeClose();
  setMenu(false); setCatalog(false);
  if (!$("support").hidden) setSupport(false);
  tour.on = true;
  siteMusicWas = !!(music && music.on);
  if (siteMusicWas) $("music").click();
  setTourMusic(tourMusicWanted);
  document.body.classList.add("touring");
  tourEl.hidden = false;
  controls.autoRotateSpeed = 0.45;
  tour.last = performance.now();
  tourStep(0);
  requestAnimationFrame(tourTick);
}
function endTour() {
  if (!tour.on) return;
  leaveStop();
  if (tour.past) backToNow();
  tour.on = false;
  setTourMusic(false).then(() => { if (siteMusicWas && !(music && music.on)) $("music").click(); });
  controls.autoRotate = false;
  document.body.classList.remove("touring");
  tourEl.classList.remove("show");
  tourEl.hidden = true;
}
function tourTick() {
  if (!tour.on) return;
  const now = performance.now(), dt = now - tour.last;
  tour.last = now;
  // the clock of a stop runs only after the flight has arrived, and not while paused or in a hidden tab
  if (!tour.paused && !state.flight && !document.hidden) tour.held += dt;
  $("tourBar").style.transform = `scaleX(${Math.min(1, tour.held / tour.dur)})`;
  if (tour.half && !tour.under && tour.held >= tour.half) showUnder();
  // comets: come in closer than the usual view (each new flight — the date jump starts one more)
  const st = TOUR[tour.i];
  if (st.zoom && state.flight && !state.flight.tourZoom) { state.flight.offset.multiplyScalar(st.zoom); state.flight.tourZoom = true; }
  if (tour.held >= tour.dur) {
    if (tour.i < TOUR.length - 1) tourStep(tour.i + 1);
    else { endTour(); return; }
  }
  requestAnimationFrame(tourTick);
}

$("tourBtn").addEventListener("click", startTour);
$("welcomeTour").addEventListener("click", startTour);
$("tourClose").addEventListener("click", endTour);
$("tourSound").addEventListener("click", () => {
  tourMusicWanted = !tourMusicWanted;
  try { localStorage.setItem(TOUR_MUSIC_KEY, tourMusicWanted ? "1" : "0"); } catch (e) { /* not saved */ }
  setTourMusic(tourMusicWanted);
});
$("tourPrev").addEventListener("click", () => tourStep(tour.i - 1));
$("tourNext").addEventListener("click", () => { if (tour.i < TOUR.length - 1) tourStep(tour.i + 1); else endTour(); });
$("tourPause").addEventListener("click", () => {
  if (!tour.paused) { setTourPaused(true); return; }
  // if the visitor wandered to another body meanwhile, go back to this stop
  const id = TOUR[tour.i][0], here = id ? byId[id].index : -1;
  if (state.index !== here) tourStep(tour.i); else setTourPaused(false);
});
// Touching the scene (to look around or zoom) pauses the tour; ▶ carries on.
canvas.addEventListener("pointerdown", () => { if (tour.on && !tour.paused) setTourPaused(true); });
addEventListener("wheel", e => { if (tour.on && e.target === canvas && !tour.paused) setTourPaused(true); }, { passive: true });
// Keys during the tour: ← → move between stops, space pauses, Esc ends it.
addEventListener("keydown", e => {
  if (!tour.on || e.target.tagName === "INPUT") return;
  const k = e.key;
  if (k === "ArrowRight") $("tourNext").click();
  else if (k === "ArrowLeft") { if (tour.i > 0) tourStep(tour.i - 1); }
  else if (k === "Escape") endTour();
  else if (k === " " && e.target === document.body) { e.preventDefault(); $("tourPause").click(); }
  else return;
  e.stopImmediatePropagation();
}, true);
