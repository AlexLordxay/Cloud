// Camera flights over Pluto (terrain.js). Keyframes: [km east, real km of altitude above the datum, km south] of the
// patch centre; "look" is the point aimed at. One degree on Pluto is 20.7 km.
module.exports = {
  // test: Tenzing Montes from the south, the low Sun from the east
  test: { site: 'tenzing', dur: 6, fov: 50, haze: 1.6, expo: 2.4, mesh: 2048, keys: [
    { t: 0, pos: [-70, 7.5, 45], look: [10, 4.5, -5] },
    { t: 6, pos: [-64, 7, 41], look: [10, 4.5, -5] },
  ] },
};
module.exports.globe_shots = {};
