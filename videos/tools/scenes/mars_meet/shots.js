// Camera flights over the real relief (terrain.js). Keyframes: [km east, real km of altitude above the datum, km south]
// of the patch centre; "look" is the point aimed at. One degree of latitude on Mars is 59.2 km.
// Olympus: summit 21.2 km at (20, 63); the cliff round its foot is 300 km out (west side x ≈ -270).
// Valles Marineris: floor about -5 km, plateau +3 km; the canyon runs from (-220, 85) east-south-east to (500, 290).
module.exports = {
  // the hook: from high above, diving toward the whole volcano and its summit calderas (thin haze up here); aimed
  // past the summit so the calderas sit low in the frame, clear of the big title
  hook: { site: 'olympus', dur: 3.4, fog: 1 / 2400, sun: [-0.85, 0.24, -0.25], keys: [
    { t: 0, pos: [20, 250, 430], look: [20, 6, -30] },
    { t: 3.4, pos: [20, 150, 285], look: [20, 10, -10] },
  ] },
  // Olympus Mons: from far out, rising over the flank toward the summit calderas
  olympus: { site: 'olympus', dur: 7.2, ease: true, sun: [-0.85, 0.24, -0.25], keys: [
    { t: 0, pos: [40, 150, 470], look: [20, 6, 63] },
    { t: 7.2, pos: [30, 85, 260], look: [20, 12, 63] },
  ] },
  // Valles Marineris: from above the northern rim, looking east-south-east along the canyon
  valles: { site: 'valles', dur: 7.2, ex: 3, sun: [0.35, 0.33, -0.85], keys: [
    { t: 0, pos: [-330, 38, 30], look: [60, -5, 175] },
    { t: 7.2, pos: [-150, 32, 80], look: [230, -5, 215] },
  ] },
  // Sunset in Gale crater (Curiosity's home): low over the floor east of Mount Sharp, looking west as the Sun goes down
  // behind it, the blue glow round the Sun
  sunset: { site: 'gale', dur: 6.4, ex: 2, dusk: 1, fov: 46, fog: 1 / 420, shadowBias: 0.14, sunPath: [[268.5, 6.5], [269.5, 2.6]], keys: [
    { t: 0, pos: [70, -1.2, 8], look: [-60, -0.6, 0] },
    { t: 6.4, pos: [58, -1.3, 4], look: [-60, -0.9, -2] },
  ] },
};
