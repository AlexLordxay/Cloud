// Injected before the page loads: a virtual clock and a fixed random sequence, so a recording is exactly repeatable
// (re-rendering part of a video gives the same frames as before).
(() => {
  let seed = 20180601;
  Math.random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  let vt = 0;
  performance.now = () => vt * 1000;
  Date.now = () => 1.7e12 + vt * 1000;
  let queue = [];
  window.requestAnimationFrame = cb => { queue.push(cb); return queue.length; };
  window.__step = dt => { vt += dt; const q = queue; queue = []; for (const cb of q) cb(vt * 1000); };
  window.__vt = () => vt;
  // Helpers for scene scripts.
  window.__smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  window.__ease = x => { x = Math.min(1, Math.max(0, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  window.__lerp = (a, b, k) => a + (b - a) * k;
})();
