// Camera flights over Mercury (terrain.js). Keyframes: [km east, real km of altitude above the datum, km south] of the
// patch centre; "look" is the point aimed at. One degree on Mercury is 42.6 km.
// Hokusai: 114 km across, floor ~-3 km, centre at the patch centre. The Sun rises in the east (az 90).
module.exports = {
  // «Як насправді рухаються планети» (real_motion): the honest Sun over Hokusai at dawn, 1.4° wide, still, a slow push
  rm_sun: { site: 'hokusai', dur: 8.4, fov: 24, expo: 1.6, mesh: 2048,
    sunEl: [[0, 3.3], [8.4, 3.6]], keys: [
    { t: 0, pos: [-152, 14, 2], look: [20, 9.5, 6] },
    { t: 8.4, pos: [-139, 13.4, 2], look: [20, 9.5, 6] },
  ] },
  // the hook: west of Hokusai, low, looking east across the crater into the dawn; the Sun comes up, stops, sinks back
  // and comes up again (near perihelion Mercury's orbit outruns its spin for a few days)
  hook: { site: 'hokusai', dur: 6.9, fov: 30, expo: 1.6, mesh: 2048,
    // timed to the words: «зійти» (up), «зупинитися» (still), «повернути назад» (down), «і зійти вдруге» (up again)
    sunEl: [[0, -2.5], [2.0, 2.6], [3.7, 2.6], [5.1, 0.5], [6.6, 3.8], [6.9, 4.0]], keys: [
    { t: 0, pos: [-150, 15, 2], look: [20, 8.0, 9] },
    { t: 6.9, pos: [-133, 14, 2], look: [20, 7.6, 8] },
  ] },
  // «Повітря немає… удень понад 400 градусів, вночі мінус 180»: high over the night side west of Caloris, looking east
  // across the terminator to the morning (the Sun 5° up over the basin, setting toward the west with the curvature)
  terminator: { site: 'caloris', dur: 10.9, fov: 46, expo: 1.4, mesh: 2048, keys: [
    { t: 0, pos: [-760, 150, 220], look: [-150, 40, 20] },
    { t: 10.9, pos: [-690, 135, 200], look: [-120, 36, 10] },
  ] },
  // «урвища заввишки в кілометри — зморшки»: Discovery Rupes near Rameau crater, from the south, the Sun low in the west
  rupes: { site: 'discovery', dur: 9.1, fov: 44, expo: 1.4, mesh: 2048, keys: [
    { t: 0, pos: [140, 30, 230], look: [80, -1, 20] },
    { t: 9.1, pos: [118, 24, 150], look: [80, -1, -20] },
  ] },
  // «Поруч — кратер Шевченка»: Shevchenko (143 km) marked, drawing in from the east
  shev: { site: 'discovery', dur: 8.3, fov: 44, expo: 1.4, mesh: 2048, marker: [-125, -38], markerH: 18, keys: [
    { t: 0, pos: [20, 60, 60], look: [-125, -2, -38] },
    { t: 8.3, pos: [-30, 48, 40], look: [-125, -2, -38] },
  ] },
  // ice: near the north pole, the Sun skimming the southern horizon, crater floors in permanent shadow glowing faintly
  pole: { site: 'pole', dur: 9.5, fov: 44, expo: 1.5, mesh: 2048, ice: 1.6, keys: [
    { t: 0, pos: [-60, 55, 170], look: [-110, -3, -30] },
    { t: 9.5, pos: [-80, 45, 120], look: [-110, -3, -40] },
  ] },
};

// The whole planet (globe.js). Keys: the point under the camera (lat, lon), dist in planet radii; sun: the subsolar
// point. Portrait frames are narrow (fov 30 is only ~17° across), so a full disc needs dist ≳ 7.
module.exports.globe_shots = {
  // "Це Меркурій": the planet turning, lit from the right
  turn: { dur: 4.8, fov: 30, sun: [0, 75], linear: ['lon'], keys: [
    { t: 0, lat: 12, lon: 35, dist: 8.4 },
    { t: 4.8, lat: 9, lon: 70, dist: 7.6 },
  ] },
  // the Caloris basin, the morning terminator just past it; Ukraine's outline laid on it at true size
  calo: { dur: 5.5, fov: 30, sun: [0, 95], keys: [
    { t: 0, lat: 28, lon: 150, dist: 5.2, over: 0 },
    { t: 1.6, lat: 30, lon: 155, dist: 4.4, over: 0 },
    { t: 2.6, over: 1, lat: 30.5, lon: 158, dist: 4.1 },
    { t: 5.5, over: 1, lat: 31, lon: 161, dist: 3.8 },
  ] },
  // the shock running round the planet from Caloris to the opposite side, where the ground broke up
  shock: { dur: 6.0, fov: 30, sun: [0, 72], linear: ['shock'], keys: [
    { t: 0, lat: 31, lon: 160, dist: 6.5, shock: 0.0 },
    { t: 4.4, lat: -28, lon: -20, dist: 6.5, shock: 1.0 },
    { t: 6.0, lat: -31, lon: -17, dist: 5.4, shock: 1.0 },
  ] },
  // BepiColombo arriving (21.11.2026): a bright point swinging in round the planet, its track drawn behind it
  bepi: { dur: 6.3, fov: 34, sun: [0, 40], bepiOrbit: [1.3, 3.2, 70, 30], linear: ['bepi'], keys: [
    { t: 0, lat: 20, lon: 10, dist: 8, bepi: 0.0, bepiLine: 0 },
    { t: 1.5, bepiLine: 1 },
    { t: 6.3, lat: 16, lon: 30, dist: 7.2, bepi: 0.62, bepiLine: 1 },
  ] },
  // the question and the end card: the planet drawing away
  outro: { dur: 8.2, fov: 30, sun: [0, 95], linear: ['lon'], keys: [
    { t: 0, lat: 10, lon: 60, dist: 8.0 },
    { t: 8.2, lat: 14, lon: 78, dist: 16.0 },
  ] },
};
