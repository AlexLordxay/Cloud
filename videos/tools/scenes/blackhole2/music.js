// «Що буде, якщо впасти в чорну діру?» v2 — the video's own score, in the spirit of the Hoverla organ score (MUSIC.md):
// one organ, no bass, no drums. C minor; a clock-like figure (root, fifth, octave in eighths, falling in threes across the
// bar) that swells out to the galaxy and back, quickens as the astronaut sinks to the horizon, slows to a stop for the
// friend's view, circles high round the photon sphere; a long rise to the horizon, where C minor brightens to C major
// over 2.5 s (no hit), then a hush: one high note, a soft open chord for "nobody knows", a quiet close.
// Times in seconds of the video (see script.md / captions.py).
function createSceneMusic(ctx, dest) {
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const rnd = (a, b) => a + Math.random() * (b - a);
  const BEAT = 0.625, S16 = BEAT / 4, CHORD = 8 * BEAT;
  const ROOTS = [36, 32, 29, 31];
  const UPPER = [[60, 63, 67], [60, 63, 68], [60, 65, 68], [59, 62, 67]];
  const HIT = 26.25;

  // Glue and space: a compressor on the whole mix and a long generated hall.
  const master = ctx.createDynamicsCompressor();
  master.threshold.value = -16; master.ratio.value = 3; master.attack.value = 0.02; master.release.value = 0.3;
  const out = ctx.createGain(); out.gain.value = 0.55;   // headroom: the hit must not clip
  master.connect(out).connect(dest);
  const len = Math.floor(ctx.sampleRate * 5), ir = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.4);
  }
  const verb = ctx.createConvolver(); verb.buffer = ir;
  const wet = ctx.createGain(); wet.gain.value = 0.5; verb.connect(wet).connect(master);
  const bus = (gain, send) => {
    const g = ctx.createGain(); g.gain.value = gain; g.connect(master);
    const s = ctx.createGain(); s.gain.value = send; g.connect(s).connect(verb);
    return g;
  };
  const strings = bus(0.16, 0.25), brass = bus(0.06, 0.5), choir = bus(0.035, 0.9), bells = bus(0.07, 0.8),
    drums = bus(0.5, 0.35), pad = bus(0.05, 0.7), sub = bus(0.22, 0.1), fx = bus(0.05, 0.6);
  const noise = (() => {
    const b = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return b;
  })();
  const osc = (type, f, t0, t1, out, detune = 0) => {
    const o = ctx.createOscillator(); o.type = type; o.frequency.value = f; o.detune.value = detune;
    o.connect(out); o.start(t0); o.stop(t1); return o;
  };
  const env = (t0, a, hold, rel, peak = 1) => {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(peak, t0 + a);
    g.gain.setValueAtTime(peak, t0 + a + hold); g.gain.linearRampToValueAtTime(0, t0 + a + hold + rel);
    return g;
  };

  // Low strings, spiccato: two detuned saws and a sub-octave square through a plucked low-pass.
  function spic(t, m, vel, cut) {
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 1.2;
    lp.frequency.setValueAtTime(cut, t); lp.frequency.exponentialRampToValueAtTime(cut * 0.35, t + 0.12);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + 0.006); g.gain.exponentialRampToValueAtTime(0.001, t + 0.16);
    lp.connect(g).connect(strings);
    osc('sawtooth', midi(m), t, t + 0.18, lp, -7); osc('sawtooth', midi(m), t, t + 0.18, lp, 7);
    const sq = ctx.createGain(); sq.gain.value = 0.35; sq.connect(lp); osc('square', midi(m - 12), t, t + 0.18, sq);
  }
  // Brass swell: three saws, the filter opening and closing over the note.
  function horn(t0, t1, m, level) {
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 0.7;
    lp.frequency.setValueAtTime(250, t0); lp.frequency.linearRampToValueAtTime(1700, t0 + (t1 - t0) * 0.55);
    lp.frequency.linearRampToValueAtTime(500, t1 + 0.6);
    const g = env(t0, Math.min(1.6, (t1 - t0) * 0.4), Math.max(0, (t1 - t0) * 0.6 - 0.2), 1.2, level);
    lp.connect(g).connect(brass);
    for (const c of [-9, 0, 8]) osc('sawtooth', midi(m), t0, t1 + 1.3, lp, c);
  }
  // Choir "aah": detuned triangles with vibrato through two vowel formants.
  function aah(t0, t1, m, level) {
    const f1 = ctx.createBiquadFilter(); f1.type = 'bandpass'; f1.frequency.value = 760; f1.Q.value = 3;
    const f2 = ctx.createBiquadFilter(); f2.type = 'bandpass'; f2.frequency.value = 1180; f2.Q.value = 4;
    const g = env(t0, 2.2, Math.max(0, t1 - t0 - 2.2), 2.5, level);
    f1.connect(g); f2.connect(g); g.connect(choir);
    for (const c of [-12, -4, 5, 11]) {
      const o = osc('sawtooth', midi(m), t0, t1 + 2.6, f1, c); o.connect(f2);
      const lfo = ctx.createOscillator(), d = ctx.createGain();
      lfo.frequency.value = rnd(4.4, 5.6); d.gain.value = 9; lfo.connect(d).connect(o.detune);
      lfo.start(t0); lfo.stop(t1 + 2.6);
    }
  }
  // Soft pad: sine and triangle, slow in and out.
  function padNote(t0, t1, m, level) {
    const g = env(t0, 2.5, Math.max(0, t1 - t0 - 2.5), 3, level); g.connect(pad);
    osc('sine', midi(m), t0, t1 + 3.1, g, -4); osc('triangle', midi(m), t0, t1 + 3.1, g, 4);
  }
  // Bell / celesta: a sine with inharmonic partials and a long ring.
  function bell(t, m, vel) {
    const g = ctx.createGain(); g.connect(bells);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0008, t + 3.4);
    for (const [mul, a] of [[1, 1], [2.76, 0.28], [5.4, 0.1]]) {
      const ag = ctx.createGain(); ag.gain.value = a; ag.connect(g); osc('sine', midi(m) * mul, t, t + 3.5, ag);
    }
  }
  // Timpani: a falling sine plus a short felt thump.
  function timp(t, vel, m = 38) {
    const g = ctx.createGain(); g.connect(drums);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + 0.01); g.gain.exponentialRampToValueAtTime(0.001, t + 1.8);
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(midi(m) * 1.9, t); o.frequency.exponentialRampToValueAtTime(midi(m), t + 0.25);
    o.connect(g); o.start(t); o.stop(t + 1.9);
    const n = ctx.createBufferSource(); n.buffer = noise;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 380;
    const ng = ctx.createGain(); ng.gain.setValueAtTime(vel * 0.6, t); ng.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
    n.connect(lp).connect(ng).connect(drums); n.start(t); n.stop(t + 0.15);
  }
  function subNote(t0, t1, m, level) {
    const g = env(t0, 0.8, Math.max(0, t1 - t0 - 0.8), 1.5, level); g.connect(sub);
    osc('sine', midi(m), t0, t1 + 1.6, g);
  }
  // Riser into the hit: noise sweeping up and a slowly climbing saw.
  function riser(t0, t1) {
    const n = ctx.createBufferSource(); n.buffer = noise; n.loop = true;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = 2;
    bp.frequency.setValueAtTime(250, t0); bp.frequency.exponentialRampToValueAtTime(7000, t1);
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(1.2, t1); g.gain.setValueAtTime(0, t1 + 0.01);
    n.connect(bp).connect(g).connect(fx); n.start(t0); n.stop(t1 + 0.05);
    const o = ctx.createOscillator(); o.type = 'sawtooth';
    o.frequency.setValueAtTime(midi(50), t0); o.frequency.exponentialRampToValueAtTime(midi(74), t1);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2200;
    const og = ctx.createGain(); og.gain.setValueAtTime(0.0001, t0); og.gain.exponentialRampToValueAtTime(0.5, t1); og.gain.setValueAtTime(0, t1 + 0.01);
    o.connect(lp).connect(og).connect(fx); o.start(t0); o.stop(t1 + 0.05);
  }
  // The hit: a deep falling boom with a burst of noise, timpani and the whole chord at once.
  function hit(t) {
    const g = ctx.createGain(); g.connect(drums);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(1.6, t + 0.01); g.gain.exponentialRampToValueAtTime(0.001, t + 3.5);
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(70, t); o.frequency.exponentialRampToValueAtTime(28, t + 2.5);
    o.connect(g); o.start(t); o.stop(t + 3.6);
    const n = ctx.createBufferSource(); n.buffer = noise;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.setValueAtTime(5000, t); lp.frequency.exponentialRampToValueAtTime(200, t + 1.5);
    const ng = ctx.createGain(); ng.gain.setValueAtTime(0.8, t); ng.gain.exponentialRampToValueAtTime(0.001, t + 2);
    n.connect(lp).connect(ng).connect(fx); n.start(t); n.stop(t + 2);
    timp(t, 1.2);
    for (const m of [48, 55, 60, 63]) horn(t, t + 0.8, m, 0.9);
    for (const m of [72, 75, 79]) aah(t, t + 1.2, m, 0.6);
  }

  // Tremolo strings: two saws through a rising low-pass, amplitude flickering fast (the "tense bow" sound).
  function trem(t0, t1, m, level) {
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 0.8;
    lp.frequency.setValueAtTime(700, t0); lp.frequency.linearRampToValueAtTime(2600, t1);
    const tg = ctx.createGain(); tg.gain.value = 0.6;
    const lfo = ctx.createOscillator(), ld = ctx.createGain(); lfo.frequency.value = rnd(7.5, 9); ld.gain.value = 0.4;
    lfo.connect(ld).connect(tg.gain); lfo.start(t0); lfo.stop(t1 + 0.4);
    const g = env(t0, 1.5, Math.max(0, t1 - t0 - 1.8), 0.3, level);
    lp.connect(tg).connect(g).connect(strings);
    for (const c of [-8, 8]) osc('sawtooth', midi(m), t0, t1 + 0.4, lp, c);
  }
  // Piano-ish pluck: a sine with a quick-fading second harmonic, long ring.
  function piano(t, m, vel) {
    const g = ctx.createGain(); g.connect(bells);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + 0.006); g.gain.exponentialRampToValueAtTime(0.0008, t + 3.2);
    osc('sine', midi(m), t, t + 3.3, g);
    const h = ctx.createGain(); h.gain.setValueAtTime(0.35, t); h.gain.exponentialRampToValueAtTime(0.001, t + 0.5); h.connect(g);
    osc('triangle', midi(m) * 2, t, t + 0.6, h);
  }

  // Pipe organ: sine partials (the "stops") with a slow tremulant, a touch of wind noise on the attack ("chiff"),
  // a low-pass that opens as the registration grows. Stops are [harmonic ratio, level].
  const organBus = bus(0.11, 0.95);
  const REG8 = [[1, 1], [2, 0.4]];
  const REG_MID = [[1, 1], [2, 0.6], [3, 0.3], [4, 0.25]];
  const REG_FULL = [[1, 1], [2, 0.8], [3, 0.5], [4, 0.5], [5, 0.3], [6, 0.3], [8, 0.2]];
  function organ(t0, t1, m, reg, level, cut, att = 0.05, rel = 0.4) {
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = cut; lp.Q.value = 0.5;
    const g = env(t0, att, Math.max(0, t1 - t0 - att), rel, level);
    lp.connect(g).connect(organBus);
    const lfo = ctx.createOscillator(), ld = ctx.createGain(); lfo.frequency.value = 5.2; ld.gain.value = 5;
    lfo.connect(ld); lfo.start(t0); lfo.stop(t1 + 0.5);
    for (const [r, a] of reg) {
      const f = midi(m) * r; if (f > 9000 || f < 18) continue;
      const ag = ctx.createGain(); ag.gain.value = a / reg.length * 1.6; ag.connect(lp);
      const o = ctx.createOscillator(); o.type = r <= 1 ? 'triangle' : 'sine'; o.frequency.value = f;
      ld.connect(o.detune); o.connect(ag); o.start(t0); o.stop(t1 + 0.5);
    }
    const n = ctx.createBufferSource(); n.buffer = noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = midi(m) * 4; bp.Q.value = 3;
    const ng = ctx.createGain(); ng.gain.setValueAtTime(level * 0.35, t0); ng.gain.exponentialRampToValueAtTime(0.001, t0 + 0.09);
    n.connect(bp).connect(ng).connect(organBus); n.start(t0); n.stop(t0 + 0.1);
  }

  function schedule() {
    const E8 = BEAT / 2, E16 = BEAT / 4;
    const FL = [[1, 1], [2, 0.35]];
    const CH = { Cm: [48, 51, 55], Ab: [44, 48, 51], Fm: [41, 44, 48], G: [43, 47, 50], Eb: [43, 46, 51], C: [48, 52, 55], Db: [44, 49, 53] };
    // [from, chord]: the harmony along the video
    const PLAN = [[0, 'Cm'], [6.2, 'Ab'], [9.0, 'Eb'], [10.2, 'Fm'], [12.7, 'Cm'], [14.6, 'G'], [16.4, 'Ab'], [18.6, 'Eb'],
      [20.9, 'Cm'], [23.4, 'Ab'], [25.9, 'Fm'], [28.4, 'G'], [30.4, 'Cm'], [32.4, 'Ab'], [34.2, 'G'], [37.2, 'Cm'],
      [42.0, 'Fm'], [46.0, 'Cm'], [50.6, 'Fm'], [53.4, 'Ab'], [56.4, 'Fm'], [59.3, 'G'], [62.6, 'Eb'], [65.0, 'Ab'],
      [67.3, 'Fm'], [68.6, 'C'], [71.0, 'Ab'], [79.4, 'Cm'], [83.0, 'C']];
    const chordAt = t => { let c = PLAN[0][1]; for (const [t0, k] of PLAN) if (t >= t0 - 1e-6) c = k; return CH[c]; };
    // loudness of the figure (0 = silent), its note length and the octave above, by time
    const dyn = t => t < 6.2 ? 0.12 + 0.1 * t / 6.2 : t < 9.0 ? 0.22 + 0.5 * (t - 6.2) / 2.8 : t < 10.2 ? 0.72 : t < 12.7 ? 0.72 - 0.25 * (t - 10.2) / 2.5 :
      t < 16.4 ? 0.42 : t < 20.9 ? 0.2 : t < 34.2 ? 0.25 + 0.7 * (t - 20.9) / 13.3 : t < 37.0 ? 0.95 - 0.2 * (t - 34.2) / 2.8 : 0;
    // the figure: eighths, sixteenths as he nears the horizon
    let t = 0, i = 0;
    while (t < 37.0) {
      const d = dyn(t), step = t > 28.4 && t < 37 ? E16 : E8;
      if (d > 0) {
        const f = chordAt(t), m = [f[0], f[0] + 7, f[0] + 12][i % 3] + 12;
        organ(t, t + step * 0.9, m, d > 0.55 ? REG_MID : FL, 0.08 + 0.2 * d, 900 + 3200 * d, 0.01, 0.12);
        if (d > 0.45) organ(t, t + step * 0.9, m + 12, FL, 0.04 + 0.12 * (d - 0.45), 2500, 0.01, 0.12);
      }
      t += step; i++;
    }
    // held chords that breathe, one per stretch of the plan, up to the hush at the horizon
    PLAN.forEach(([t0, k], c) => {
      const t1 = c + 1 < PLAN.length ? PLAN[c + 1][0] : 86.5;
      if (t0 >= 71.0) return;
      const d = t0 < 37 ? Math.max(0.15, dyn(t0 + 0.5)) : t0 < 50.6 ? 0.2 : t0 < 67.3 ? 0.4 : 0.6;
      for (const m of CH[k]) organ(t0, t1 + 0.3, m + 12, t0 > 30 && t0 < 37 ? REG_MID : FL, 0.07 + 0.18 * d, 800 + 2400 * d, 1.4, 1.2);
    });
    // the boundary: a low held chord with a minor second against it (unease), no figure
    organ(37.2, 41.8, 61, FL, 0.12, 1500, 1.2, 1.0);
    // the friend's view: the figure slows down to a stop, one note hangs on
    for (let tt = 42.0, k = 0, dt = E8; tt < 47.5; tt += dt, k++, dt *= 1.13) {
      const f = CH.Fm, m = [f[0], f[0] + 7, f[0] + 12][k % 3] + 12;
      organ(tt, tt + Math.min(dt * 0.9, 0.6), m, FL, 0.16, 1400, 0.01, 0.25);
    }
    organ(47.6, 50.5, 72, FL, 0.12, 2000, 0.4, 0.8);
    // the fall goes on: the figure back, quick; round the photon sphere a high line circles
    for (let tt = 50.6, k = 0; tt < 59.2; tt += E16, k++) {
      const f = chordAt(tt), m = [f[0], f[0] + 7, f[0] + 12, f[0] + 7][k % 4] + 24;
      const d = tt < 53.4 ? 0.35 + 0.15 * (tt - 50.6) / 2.8 : 0.45;
      organ(tt, tt + E16 * 0.9, m, FL, 0.05 + 0.14 * d, 2200, 0.01, 0.1);
    }
    // the small hole: tension (sixteenths on G with a flattened sixth); Sgr A*: E flat, warm and calm
    for (let tt = 59.3, k = 0; tt < 62.5; tt += E16, k++) organ(tt, tt + E16 * 0.9, [55, 62, 67, 68][k % 4], FL, 0.12, 1800, 0.01, 0.1);
    for (let tt = 62.6, k = 0; tt < 67.2; tt += E8, k++) { const f = chordAt(tt); organ(tt, tt + E8 * 0.9, [f[0], f[0] + 7, f[0] + 12][k % 3] + 24, FL, 0.13, 1800, 0.01, 0.12); }
    // the long rise to the horizon: the figure grows, and C minor brightens to C major over 2.5 s
    for (let tt = 67.3, k = 0; tt < 71.0; tt += E16, k++) {
      const d = 0.5 + 0.5 * (tt - 67.3) / 3.7, f = chordAt(tt), m = [f[0], f[0] + 7, f[0] + 12][k % 3] + 12;
      organ(tt, tt + E16 * 0.9, m, d > 0.6 ? REG_MID : FL, 0.08 + 0.2 * d, 1200 + 3000 * d, 0.01, 0.1);
      organ(tt, tt + E16 * 0.9, m + 12, FL, 0.05 + 0.12 * d, 2800, 0.01, 0.1);
    }
    for (const m of [48, 52, 55, 60, 64, 67, 72]) organ(68.4, 71.2, m + 12, REG_FULL, 0.2, 4200, 2.5, 1.6);
    // the hush: one high note hangs on; then a soft open chord (A flat major over C) for "nobody knows"
    organ(71.0, 79.0, 79, FL, 0.1, 2500, 0.6, 2.0);
    for (const m of [72, 75, 80, 84]) organ(75.6, 80.5, m, FL, 0.16, 2400, 1.6, 1.6);
    // the close: C minor, then C major, quiet
    for (const m of [60, 63, 67, 72]) organ(79.4, 83.4, m, FL, 0.14, 1800, 1.5, 1.0);
    for (const m of [60, 64, 67, 72]) organ(83.0, 86.5, m, FL, 0.14, 1800, 1.5, 1.2);
  }
  return {
    output: master,
    start() { schedule(); },
    scheduleUntil() {},
  };
}
