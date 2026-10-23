// The 3D shots of the Kadenyuk video: views as functions of time (seconds from the shot's start). Lengths include
// 0.4 s for the crossfade into the next piece (assemble.py). Places: Klishkivtsi 48.43 N 26.27 E; the shuttle shots
// are over the northern Red Sea, looking north — Columbia's orbit (28.5°) never went further north, Ukraine is on the horizon.
(() => {
  const ease = x => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x), lerp = (a, b, k) => a + (b - a) * k;
  window.SHOTS = {
    // the hook: the shuttle with its bay open, drifting closer
    hook: { dur: 4.65, at: t => { const k = t / 4.65; return {
      lat: lerp(26.8, 27.1, k), lon: 34, alt: 300, pitch: -22, sunAz: 250, sunEl: 40,
      ship: { dist: lerp(108, 86, ease(k)), down: -14, side: lerp(4, -1, k), heading: lerp(-38, -31, k), roll: lerp(26, 22, k) } }; } },
    // down onto Bukovina, Klishkivtsi in the middle
    home: { dur: 4.25, at: t => { const k = ease(t / 4.25); return {
      lat: 48.43, lon: 26.27, alt: lerp(7500, 1300, k), pitch: -90, heading: 0, sunAz: 200, sunEl: 42, mark: [48.43, 26.27],
      clouds: Math.max(0, 1 - 1.8 * k) }; } },   // the coarse cloud map would blur the close view: it clears on the way down
    // 1976: the Earth at dusk, Ukraine's lights coming on
    night: { dur: 6.3, at: t => { const k = t / 6.3; return {
      lat: 44, lon: lerp(25, 31, k), alt: 14000, pitch: -90, heading: 0, sunAt: [48, 30], sunAz: 285, sunEl: lerp(-6, -16, k) }; } },
    // the end: the shuttle draws away towards the horizon, the view lifts to it
    finale: { dur: 14.7, at: t => { const k = t / 14.7; return {
      lat: lerp(26.9, 27.5, k), lon: 34.2, alt: 300, pitch: lerp(-22, -15, ease(k)), heading: 4, sunAz: 245, sunEl: 34,
      ship: { dist: lerp(72, 210, ease(k * 0.9)), down: lerp(-11, -2, ease(k)), side: lerp(-2, 6, k), heading: lerp(-25, -15, k), roll: 20 } }; } },
  };
})();
