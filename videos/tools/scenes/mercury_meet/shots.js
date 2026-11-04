// Camera flights over Mercury (terrain.js). Keyframes: [km east, real km of altitude above the datum, km south] of the
// patch centre; "look" is the point aimed at. One degree on Mercury is 42.6 km.
// Hokusai: 114 km across, floor ~-3 km, centre at the patch centre. The Sun rises in the east (az 90).
module.exports = {
  // the hook: west of Hokusai, low, looking east across the crater into the dawn; the Sun comes up, stops, sinks back
  // and comes up again (near perihelion Mercury's orbit outruns its spin for a few days)
  hook: { site: 'hokusai', dur: 5.4, fov: 30, expo: 1.6, mesh: 2048, sunEl: [[0, -2.5], [1.3, 2.6], [2.1, 2.6], [3.1, 0.5], [4.6, 3.6], [5.4, 4.2]], keys: [
    { t: 0, pos: [-150, 15, 2], look: [20, 8.0, 9] },
    { t: 5.4, pos: [-136, 14, 2], look: [20, 7.6, 8] },
  ] },
};

// The whole planet (globe.js). Keys: the point under the camera (lat, lon), dist in planet radii; sun: the subsolar
// point. Portrait frames are narrow (fov 30 is only ~17° across), so a full disc needs dist ≳ 7.
module.exports.globe_shots = {
  // "Це Меркурій": the planet turning, lit from the right
  turn: { dur: 8.0, fov: 30, sun: [0, 75], linear: ['lon'], keys: [
    { t: 0, lat: 12, lon: 25, dist: 8.6 },
    { t: 8.0, lat: 8, lon: 85, dist: 7.6 },
  ] },
  // the Caloris basin, the morning terminator just past it; Ukraine's outline laid on it at true size
  calo: { dur: 6.0, fov: 30, sun: [0, 95], keys: [
    { t: 0, lat: 28, lon: 150, dist: 5.2, over: 0 },
    { t: 1.0, lat: 30, lon: 155, dist: 4.4, over: 0 },
    { t: 2.0, over: 1, lat: 30.5, lon: 158, dist: 4.1 },
    { t: 6.0, over: 1, lat: 31, lon: 161, dist: 3.8 },
  ] },
  // the shock running round the planet from Caloris to the opposite side, where the ground broke up
  shock: { dur: 6.0, fov: 30, sun: [0, 72], linear: ['shock'], keys: [
    { t: 0, lat: 31, lon: 160, dist: 6.5, shock: 0.0 },
    { t: 4.6, lat: -28, lon: -20, dist: 6.5, shock: 1.0 },
    { t: 6.0, lat: -31, lon: -17, dist: 5.6, shock: 1.0 },
  ] },
  // BepiColombo arriving (21.11.2026): a bright point swinging in round the planet, its track drawn behind it
  bepi: { dur: 5.0, fov: 34, sun: [0, 40], bepiOrbit: [1.3, 3.2, 70, 30], linear: ['bepi'], keys: [
    { t: 0, lat: 20, lon: 10, dist: 8, bepi: 0.0, bepiLine: 0 },
    { t: 1.5, bepiLine: 1 },
    { t: 5.0, lat: 16, lon: 30, dist: 7.2, bepi: 0.62, bepiLine: 1 },
  ] },
  // the question and the end card: the planet drawing away
  outro: { dur: 7.0, fov: 30, sun: [0, 95], linear: ['lon'], keys: [
    { t: 0, lat: 10, lon: 60, dist: 8.0 },
    { t: 7.0, lat: 14, lon: 75, dist: 15.0 },
  ] },
};
