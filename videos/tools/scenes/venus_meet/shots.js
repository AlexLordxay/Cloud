// Camera flights over the real Venus relief (terrain.js). Keyframes: [km east, real km of altitude above the datum,
// km south] of the patch centre; "look" is the point aimed at. One degree on Venus is 105.6 km.
// Maat Mons: summit ~9.7 km above the datum near the patch centre; the plains round it ~2–3 km. A broad shield (slopes
// of a few degrees), so the heights are exaggerated ×5 (said in the credits).
module.exports = {
  // test: Maat Mons from the south-west
  maat: { site: 'maat', dur: 6, ex: 5, fog: 1 / 1100, sun: [-0.65, 0.42, 0.35], keys: [
    { t: 0, pos: [-330, 15, 400], look: [0, 10, -10] },
    { t: 6, pos: [-280, 14, 340], look: [0, 10, -10] },
  ] },
};
