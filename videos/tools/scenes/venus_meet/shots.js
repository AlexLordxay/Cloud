// Camera flights over the real Venus relief (terrain.js). Keyframes: [km east, real km of altitude above the datum,
// km south] of the patch centre; "look" is the point aimed at. One degree on Venus is 105.6 km.
// Maat Mons: the summit near the patch centre (terrain_data.py prints where the highest point is).
module.exports = {
  // test: Maat Mons from the south-west, low under the overcast
  maat: { site: 'maat', dur: 6, ex: 2.5, fog: 1 / 380, sun: [-0.3, 0.8, -0.4], keys: [
    { t: 0, pos: [-150, 14, 210], look: [0, 6, 0] },
    { t: 6, pos: [-110, 13, 160], look: [0, 6, 0] },
  ] },
};
