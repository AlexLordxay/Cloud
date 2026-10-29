// «Що, якби Місяць упав на Землю?» — three short organ sketches (~15 s each) to choose a style from (MUSIC.md):
// one organ, nothing below C3, no drums, no hits; every peak is a slow swell, the brightening is minor -> major over ~2.5 s.
//   1  «Годинник»  — the clock figure (root, fifth, octave in eighths, falling in threes across the bar), D minor, quickening
//   2  «Хорал»     — slow breathing chords with a lone flute line above; awe more than dread
//   3  «Відлік»    — a high tick that speeds up over a chord stack that climbs by steps (a countdown), ends in a hush
// Rendered offline by sound_preview.js (OfflineAudioContext); the final score will be one of these grown to the video's 45 s.
function createMoonMusic(ctx, dest, variant) {
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const master = ctx.createDynamicsCompressor();
  master.threshold.value = -18; master.ratio.value = 3; master.attack.value = 0.03; master.release.value = 0.4;
  const out = ctx.createGain(); out.gain.value = 0.6;
  master.connect(out).connect(dest);
  const len = Math.floor(ctx.sampleRate * 5), ir = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);
  }
  const verb = ctx.createConvolver(); verb.buffer = ir;
  const wet = ctx.createGain(); wet.gain.value = 0.55; verb.connect(wet).connect(master);
  const organBus = ctx.createGain(); organBus.gain.value = 0.12; organBus.connect(master);
  const send = ctx.createGain(); send.gain.value = 0.95; organBus.connect(send).connect(verb);
  const noise = (() => {
    const b = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return b;
  })();
  const env = (t0, a, hold, rel, peak = 1) => {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(peak, t0 + a);
    g.gain.setValueAtTime(peak, t0 + a + hold); g.gain.linearRampToValueAtTime(0, t0 + a + hold + rel);
    return g;
  };
  // Pipe organ: sine partials (the "stops") with a slow tremulant and a touch of wind on the attack; stops are [ratio, level].
  const FL = [[1, 1], [2, 0.35]];
  const REG_MID = [[1, 1], [2, 0.6], [3, 0.3], [4, 0.25]];
  const REG_FULL = [[1, 1], [2, 0.8], [3, 0.5], [4, 0.5], [5, 0.3], [6, 0.3], [8, 0.2]];
  function organ(t0, t1, m, reg, level, cut, att = 0.05, rel = 0.4, trem = 5.2) {
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = cut; lp.Q.value = 0.5;
    const g = env(t0, att, Math.max(0, t1 - t0 - att), rel, level);
    lp.connect(g).connect(organBus);
    const lfo = ctx.createOscillator(), ld = ctx.createGain(); lfo.frequency.value = trem; ld.gain.value = 5;
    lfo.connect(ld); lfo.start(t0); lfo.stop(t1 + rel + 0.1);
    for (const [r, a] of reg) {
      const f = midi(m) * r; if (f > 9000 || f < 18) continue;
      const ag = ctx.createGain(); ag.gain.value = a / reg.length * 1.6; ag.connect(lp);
      const o = ctx.createOscillator(); o.type = r <= 1 ? 'triangle' : 'sine'; o.frequency.value = f;
      ld.connect(o.detune); o.connect(ag); o.start(t0); o.stop(t1 + rel + 0.1);
    }
    const n = ctx.createBufferSource(); n.buffer = noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = midi(m) * 4; bp.Q.value = 3;
    const ng = ctx.createGain(); ng.gain.setValueAtTime(level * 0.3, t0); ng.gain.exponentialRampToValueAtTime(0.001, t0 + 0.09);
    n.connect(bp).connect(ng).connect(organBus); n.start(t0); n.stop(t0 + 0.1);
  }
  const lv = (d, lo, hi) => lo + (hi - lo) * d * d;   // swells with a long foot: quiet stays quiet, the peak is clearly louder
  // A soft organ "bell" (high flute with a quick ring) for the ticks of variant 3.
  function tick(t, m, level) {
    organ(t, t + 0.16, m, [[1, 1], [3, 0.25]], level, 3500, 0.004, 0.2, 0);
  }

  // ---------- 1. «Годинник» — D minor, 100 bpm ----------
  function clock() {
    const BEAT = 0.6, E8 = BEAT / 2, E16 = BEAT / 4;
    const CH = { Dm: [50, 53, 57], Bb: [46, 50, 53], F: [45, 48, 53], Gm: [43, 46, 50], A: [45, 49, 52], D: [50, 54, 57] };
    const PLAN = [[0, 'Dm'], [3.6, 'Bb'], [6.0, 'F'], [8.4, 'Gm'], [10.8, 'A'], [12.6, 'Dm'], [13.2, 'D']];
    const chordAt = t => { let c = PLAN[0][1]; for (const [t0, k] of PLAN) if (t >= t0 - 1e-6) c = k; return CH[c]; };
    // loudness of the figure: a small breath in, a long rise, a hush before the brightening
    const dyn = t => t < 3.0 ? 0 : t < 5.0 ? 0.14 + 0.12 * (t - 3) / 2 : t < 6.6 ? 0.26 - 0.06 * (t - 5) / 1.6 : t < 11.4 ? 0.2 + 0.78 * Math.pow((t - 6.6) / 4.8, 1.3) : t < 12.4 ? 0.98 - 0.98 * (t - 11.4) : 0;
    let t = 3.0, i = 0;
    while (t < 12.4) {
      const d = dyn(t), step = t > 9.0 ? E16 * 1.5 : E8;   // the figure quickens near the end
      const f = chordAt(t), m = [f[0], f[0] + 7, f[0] + 12][i % 3] + 12;
      organ(t, t + step * 0.9, m, d > 0.55 ? REG_MID : FL, lv(d, 0.03, 0.3), 900 + 3200 * d, 0.01, 0.12);
      if (d > 0.45) organ(t, t + step * 0.9, m + 12, FL, lv(d, 0.0, 0.2), 2500, 0.01, 0.12);
      t += step; i++;
    }
    // held chords that breathe
    PLAN.forEach(([t0, k], c) => {
      const t1 = c + 1 < PLAN.length ? PLAN[c + 1][0] : 16.0;
      if (t0 >= 12.6) return;
      const d = Math.max(0.1, dyn(t0 + 0.5));
      for (const m of CH[k]) organ(t0, t1 + 0.3, m + 12, t0 > 6 && t0 < 12 ? REG_MID : FL, lv(d, 0.03, 0.2), 800 + 2400 * d, 1.4, 1.2);
    });
    // the hush: one high note; then D minor brightens to D major over ~2.5 s (the minor third fades out as the major one fades in)
    organ(12.4, 15.6, 81, FL, 0.1, 2500, 0.5, 1.2);
    for (const m of [50, 57, 62, 69, 74, 81]) organ(12.6, 16.2, m, REG_FULL, 0.15, 3200, 1.0, 1.4);
    for (const m of [65, 77]) organ(12.6, 14.2, m, REG_FULL, 0.13, 3200, 1.0, 1.9);
    for (const m of [66, 78]) organ(13.2, 16.2, m, REG_FULL, 0.13, 3200, 2.2, 1.4);
  }

  // ---------- 2. «Хорал» — F minor, no pulse ----------
  function choral() {
    const CH = { Fm: [53, 56, 60, 63], Db: [49, 53, 56, 60], Ab: [48, 51, 56, 60], Eb: [51, 55, 58, 62], F: [53, 57, 60, 64] };
    const PLAN = [[0, 'Fm', 0.3], [3.4, 'Db', 0.6], [6.8, 'Ab', 0.85], [10.0, 'Eb', 0.5], [12.4, 'Fm', 0.35], [13.4, 'F', 0.6]];
    PLAN.forEach(([t0, k, d], c) => {
      const t1 = c + 1 < PLAN.length ? PLAN[c + 1][0] : 16.0;
      CH[k].forEach((m, j) => organ(t0 + j * 0.12, t1 + 1.2, m + 12, d > 0.5 ? REG_MID : FL, lv(d, 0.03, 0.26), 800 + 2800 * d, 1.8, 1.8));
    });
    // a lone flute line on top, long notes, an octave above the chords
    const LINE = [[0.6, 3.6, 77], [3.8, 6.8, 75], [7.0, 10.0, 72], [10.2, 12.6, 73], [12.8, 16.0, 76]];
    LINE.forEach(([a, b, m], j) => organ(a, b, m, FL, 0.1, 2800, 1.0, 1.4, 4.6 + j * 0.2));
    // an inner voice drifting down by a step, slow, under the line
    organ(2.0, 9.0, 65, FL, 0.06, 1500, 3.0, 3.0);
  }

  // ---------- 3. «Відлік» — a ticking pulse and a climbing chord ----------
  function countdown() {
    // ticks: 1/s at first, quickening to ~6/s, then they thin out to nothing; pitch hops between two high notes
    let t = 1.0, k = 0, gap = 1.0;
    while (t < 12.6) {
      const d = Math.min(1, (t - 1.0) / 9);
      tick(t, k % 2 ? 91 : 86, lv(d, 0.04, 0.16));
      gap = Math.max(0.17, gap * 0.935); t += gap; k++;
    }
    // chord stack climbing by steps: a new chord every ~2.4 s, each a whole tone higher, slowly louder
    const BASE = [[0, [45, 52, 57, 60]], [2.4, [47, 54, 59, 62]], [4.8, [49, 56, 61, 64]], [7.2, [51, 58, 63, 66]], [9.6, [53, 60, 65, 68]]];
    BASE.forEach(([t0, ch], c) => {
      const t1 = c + 1 < BASE.length ? BASE[c + 1][0] : 13.0, d = (c + 1) / BASE.length;
      ch.forEach((m, j) => organ(t0 + j * 0.08, t1 + 1.0, m + 12, d > 0.5 ? REG_MID : FL, lv(d, 0.03, 0.22), 800 + 2800 * d, 1.5, 1.4));
    });
    // the hush: ticks stop, the chord thins to two notes, then opens into a soft major sus chord
    for (const m of [65, 72]) organ(12.6, 16.2, m + 12, FL, 0.12, 2400, 1.2, 1.4);
    for (const m of [60, 67, 69, 72]) organ(13.4, 16.2, m + 12, REG_FULL, 0.13, 3000, 1.8, 1.4);
  }

  return {
    output: master,
    start() { ({ 1: clock, 2: choral, 3: countdown })[variant](); },
    scheduleUntil() {},
  };
}
