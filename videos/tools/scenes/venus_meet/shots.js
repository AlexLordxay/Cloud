// Camera flights over the real Venus relief (terrain.js). Keyframes: [km east, real km of altitude above the datum,
// km south] of the patch centre; "look" is the point aimed at. One degree on Venus is 105.6 km.
// Maat Mons: summit ~9.7 km above the datum near the patch centre; the plains round it ~2–3 km. A broad shield (slopes
// of a few degrees), so the heights are exaggerated ×5 (said in the credits). Lengths include 0.4 s for the crossfades.
// Venus turns backwards: the Sun rises in the west (azimuth 270) and sets in the east.
module.exports = {
  // the hook: dawn on the western plains — the light swelling in the haze to the west, where the Sun comes up
  dawn: { site: 'maat', dur: 3.4, ex: 5, fog: 1 / 650, dusk: 0.55, sunPath: [[268, -1], [268, 3]], keys: [
    { t: 0, pos: [-120, 6.5, 160], look: [-420, 4, 110] },
    { t: 3.4, pos: [-140, 6.2, 158], look: [-420, 4, 112] },
  ] },
  // "справжнє пекло": low and fast over the lava flows south-west of Maat, the volcano rising ahead
  plains: { site: 'maat', dur: 9.6, ex: 5, fog: 1 / 900, sun: [-0.3, 0.8, -0.4], keys: [
    { t: 0, pos: [-320, 8.5, 390], look: [-60, 4, 90] },
    { t: 9.6, pos: [-210, 7.5, 260], look: [10, 6, 20] },
  ] },
  // pressure and the acid clouds: slow, the camera tilted up to the heavy deck
  deck: { site: 'maat', dur: 12.3, ex: 5, fog: 1 / 700, sun: [0.2, 0.85, 0.3], keys: [
    { t: 0, pos: [170, 6.5, 300], look: [40, 30, 60] },
    { t: 12.3, pos: [130, 6.5, 250], look: [10, 32, 30] },
  ] },
  // Maat Mons from the south-west, drawing in
  maat: { site: 'maat', dur: 10.4, ex: 5, fog: 1 / 1100, sun: [-0.65, 0.42, 0.35], ease: true, keys: [
    { t: 0, pos: [-380, 16, 460], look: [0, 10, -10] },
    { t: 10.4, pos: [-250, 14, 310], look: [0, 10, -10] },
  ] },
  // the landers: dusk, low over the eastern plains, the last light dying in the east
  dusk: { site: 'maat', dur: 15.9, ex: 5, fog: 1 / 600, dusk: 0.75, sunPath: [[92, 4], [92, -2]], keys: [
    { t: 0, pos: [210, 6, -40], look: [520, 3, -60] },
    { t: 15.9, pos: [250, 5.8, -50], look: [520, 3, -70] },
  ] },
};
