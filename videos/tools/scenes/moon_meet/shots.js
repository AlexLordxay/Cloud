// Camera flights over the real relief (terrain.js). Keyframes: [km east, real km of altitude above the datum, km south]
// of the patch centre; "look" is the point aimed at. One degree of latitude on the Moon is 30.3 km.
// Copernicus: 93 km across, floor about -3.6 km, rim about +0.8 km, central peaks at the centre.
// Tranquility: Apollo 11's landing site at the centre, mare at about -1.9 km.
// Tycho: 85 km across, floor about -3.4 km, rim up to +1.8 km.
// South (85.5° S, 0°): rough highlands about -1…-3 km; a massif up to +5.7 km 60–120 km east of the centre.
module.exports = {
  // the hook: from high in the south, diving toward the crater with the morning shadows inside it; aimed past the
  // centre so the crater sits low in the frame, clear of the big title
  hook: { site: 'copernicus', dur: 4.6, keys: [
    { t: 0, pos: [-10, 150, 175], look: [0, -2, -20] },
    { t: 4.6, pos: [-6, 75, 100], look: [0, -2, -12] },
  ] },
  // Apollo 11: coming down from the north toward the landing site (marked), the Sun low in the east (on the left)
  apollo: { site: 'tranquility', dur: 7.4, ease: true, marker: [0, 0], keys: [
    { t: 0, pos: [6, 24, -55], look: [0, -1.9, 0] },
    { t: 7.4, pos: [2, 6, -14], look: [0, -1.9, 0] },
  ] },
  // Tycho: in from the south over the rim, the evening shadows across the floor and the central peak
  tycho: { site: 'tycho', dur: 8.2, keys: [
    { t: 0, pos: [-8, 32, 105], look: [0, -3, 5] },
    { t: 8.2, pos: [-2, 20, 36], look: [0, -3, -26] },
  ] },
  // the Earth over the horizon: near the south pole, gliding north over a plain, the Earth ~4.5° up straight ahead and
  // half lit (the Sun low in the east, on the right); a slow zoom in on it while coming down nearer the ground (so the
  // horizon, which dips ~6° from up high, stays in the frame), Ukraine on its lit side, 40° right of the middle, the
  // north pole leaning 28° toward us (the most the Earth's tilt and the Moon's orbit allow)
  earth: { site: 'south', dur: 8.0, fov: 26, fovTo: 20, earth: [0, 4.5], earthFace: [49, 31, 40], earthLean: 28, earthshine: 2.5, keys: [
    { t: 0, pos: [-60, 9, 95], look: [-58, 2, -150] },
    { t: 8.0, pos: [-60, 6, 67], look: [-58, 8.3, -150] },
  ] },
};
