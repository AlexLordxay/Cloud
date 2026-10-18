// Camera flights over the real relief (terrain.js). Keyframes: [km east, real km of altitude above the datum, km south]
// of the patch centre; "look" is the point aimed at. One degree of latitude on Mars is 59.2 km.
// Olympus: summit 21.2 km at (20, 63); the cliff round its foot is 300 km out (west side x ≈ -270).
// Valles Marineris: floor about -5 km, plateau +3 km; the canyon runs from (-220, 85) east-south-east to (500, 290).
module.exports = {
  // the hook: low over the plain, the volcano's cliff ahead and its flank rising behind
  hook: { site: 'olympus', dur: 3.4, keys: [
    { t: 0, pos: [-345, 2.0, 150], look: [-240, 5, 10] },
    { t: 3.4, pos: [-315, 3.0, 95], look: [-220, 7, -10] },
  ] },
  // Olympus Mons: from far out, rising over the flank toward the summit calderas
  olympus: { site: 'olympus', dur: 7.2, ease: true, sun: [-0.85, 0.24, -0.25], keys: [
    { t: 0, pos: [40, 150, 470], look: [20, 6, 63] },
    { t: 7.2, pos: [30, 85, 260], look: [20, 12, 63] },
  ] },
  // Valles Marineris: inside the canyon, eastwards along it
  valles: { site: 'valles', dur: 7.2, keys: [
    { t: 0, pos: [-210, -0.5, 95], look: [-60, -2.5, 150] },
    { t: 7.2, pos: [-40, -0.5, 150], look: [120, -2.5, 195] },
  ] },
};
