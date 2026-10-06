// Небозвід — the guided tour: the camera flies from stop to stop on its own, circles each body slowly and shows a
// short text. Touching the scene pauses it; ‹ › step back and forth; ✕ or Esc ends it. Opens from the menu, from the
// first-visit hint and by the link nebozvid.com.ua/#tour.
"use strict";

const TOUR = [
  ["sun", "Сонце", "Наша зірка. У ньому 99,86 % маси всієї Сонячної системи, а його світло летить до Землі 8 хвилин 20 секунд."],
  ["earth", "Земля", "Єдиний відомий світ із життям. Удень над океанами пливуть хмари, а на нічному боці світяться міста."],
  ["moon", "Місяць", "Завжди повернутий до нас одним боком. Кратери — сліди ударів за мільярди років. Тут ходили 12 людей."],
  ["mars", "Марс", "Тут найвища гора Сонячної системи — вулкан Олімп, утричі вищий за Еверест. А пилові бурі часом накривають усю планету."],
  ["jupiter", "Юпітер", "Найбільша планета. Велика червона пляма — буря, ширша за Землю, яку спостерігають уже понад 150 років."],
  ["io", "Іо", "Найвулканічніший світ: сотні діючих вулканів. Надра Іо розігрівають припливи від сусіда-велетня Юпітера."],
  ["europa", "Європа", "Під кригою — солоний океан, і води в ньому більше, ніж на всій Землі. Одне з найкращих місць для пошуку життя."],
  ["saturn", "Сатурн", "Кільця з льоду й каміння мають сотні тисяч кілометрів у ширину, а завтовшки подекуди лише десятки метрів."],
  ["titan", "Титан", "Єдиний супутник зі щільною атмосферою. Під помаранчевим смогом — річки й моря з рідкого метану."],
  ["enceladus", "Енцелад", "Крижаний супутник, з тріщин якого б’ють гейзери води. Вони живлять одне з кілець Сатурна."],
  ["uranus", "Уран", "Лежить на боці: вісь нахилена на 98°. Тому на кожному полюсі 42 роки триває день і 42 роки — ніч."],
  ["neptune", "Нептун", "Найвітряніша планета: вітри до 2000 км/год. Його спершу обчислили на папері, а вже потім побачили в телескоп."],
  ["pluto", "Плутон", "Карликова планета із «серцем» з азотного льоду. Апарат New Horizons пролетів повз нього 2015 року."],
  ["cg67p", "Комета 67P", "Перша комета, на яку посадили апарат — «Філи», 2014 рік. Формою вона нагадує гумову качечку."],
  ["halley", "Комета Галлея", "Повертається раз на 76 років, наступного разу — 2061-го. Її пил щоосені сиплеться на Землю метеорами Оріоніди."],
  [null, "Уся Сонячна система", "Планети стоять так, як зараз на небі. Тепер досліджуй сам: торкнись будь-якої планети."],
];
const tour = { on: false, i: 0, paused: false, held: 0, last: 0, dur: 0 };
const tourEl = $("tour");

// Long enough to read the text calmly once the camera has arrived.
const stopDur = text => Math.max(9, 3.5 + text.split(/\s+/).length * 0.42) * 1000;

function tourStep(i) {
  tour.i = Math.max(0, Math.min(TOUR.length - 1, i));
  const [id, title, text] = TOUR[tour.i];
  tour.held = 0; tour.dur = stopDur(text);
  $("tourCount").textContent = `${tour.i + 1} / ${TOUR.length}`;
  $("tourTitle").textContent = title;
  $("tourText").textContent = text;
  $("tourPrev").disabled = tour.i === 0;
  $("tourNext").textContent = tour.i === TOUR.length - 1 ? "Готово" : "›";
  $("tourNext").setAttribute("aria-label", tour.i === TOUR.length - 1 ? "Завершити екскурсію" : "Далі");
  // the text card fades in anew for each stop
  tourEl.classList.remove("show"); void tourEl.offsetWidth; tourEl.classList.add("show");
  if (id) focusBody(byId[id].index); else showOverview();
  setTourPaused(false);
}
function setTourPaused(p) {
  tour.paused = p;
  controls.autoRotate = !p && !reduceMotion;
  $("tourPause").textContent = p ? "▶" : "❚❚";
  $("tourPause").setAttribute("aria-label", p ? "Продовжити" : "Пауза");
  tourEl.classList.toggle("paused", p);
}
function startTour() {
  if (welcomeClose) welcomeClose();
  setMenu(false); setCatalog(false);
  if (!$("support").hidden) setSupport(false);
  tour.on = true;
  document.body.classList.add("touring");
  tourEl.hidden = false;
  controls.autoRotateSpeed = 0.45;
  tour.last = performance.now();
  tourStep(0);
  requestAnimationFrame(tourTick);
}
function endTour() {
  if (!tour.on) return;
  tour.on = false;
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
  if (tour.held >= tour.dur) {
    if (tour.i < TOUR.length - 1) tourStep(tour.i + 1);
    else { endTour(); return; }
  }
  requestAnimationFrame(tourTick);
}

$("tourBtn").addEventListener("click", startTour);
$("welcomeTour").addEventListener("click", startTour);
$("tourClose").addEventListener("click", endTour);
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
