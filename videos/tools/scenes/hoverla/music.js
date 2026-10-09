// "What if over Hoverla instead of the Moon…" — the video's own score: soft organ flutes only, no bass, no drums.
// A slow, calm tune in D major over D – Bm – G – A, one chord per world, voices added as the worlds grow; light broken
// chords from Neptune on; no sudden climax: the Sun's chord swells in over three seconds (G -> D, a soft "amen"),
// the tune rises to its highest note and the Moon's return fades back down. Everything is synthesised.
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
    const SUN = 35.5, MOON = 43.0, END = 49.5;
    const FL = [[1, 1], [2, 0.35]];                         // a soft flute stop
    const CH = [[62, 66, 69, 73], [59, 62, 66, 69], [55, 59, 62, 66], [57, 61, 64, 69]];   // Dmaj7, Bm7, Gmaj7, A
    const ORDER = [0, 1, 2, 3, 0, 1, 2];                    // one chord per 5 s up to the Sun
    ORDER.forEach((k, c) => {
      const t0 = c * 5, t1 = c === 6 ? SUN + 1.0 : t0 + 5.6;            // chords overlap: no gaps, no clicks
      const lvl = 0.16 + 0.035 * c, cut = 900 + c * 260;
      for (const m of CH[k]) organ(t0, t1, m, c < 4 ? FL : REG_MID, lvl, cut, c === 0 ? 2.0 : 1.0, 1.2);
    });
    // the tune: [start, length, note], half notes and longer, in a soft flute an octave up
    const TUNE = [[1.25, 1.25, 78], [2.5, 1.25, 76], [3.75, 1.25, 74],
      [5, 2.5, 74], [7.5, 2.5, 73], [10, 2.5, 71], [12.5, 2.5, 74], [15, 3.75, 76], [18.75, 1.25, 73],
      [20, 2.5, 78], [22.5, 2.5, 81], [25, 2.5, 83], [27.5, 2.5, 81], [30, 2.5, 79], [32.5, 3.0, 81],
      [SUN, 6.5, 86],                                      // the Sun: the highest note, held
      [MOON, 2.5, 81], [MOON + 2.5, 4.0, 78]];
    for (const [t0, len, m] of TUNE) organ(t0, t0 + len - 0.08, m, FL, t0 >= SUN ? 0.30 : 0.24, 2600, 0.12, 0.6);
    // light broken chords from Neptune on, eighths, getting a little louder towards the Sun
    for (let t = 20, i = 0; t < SUN - 0.2; t += BEAT / 2, i++) {
      const k = ORDER[Math.min(6, Math.floor(t / 5))], ch = CH[k];
      organ(t, t + 0.3, ch[[0, 2, 1, 3][i % 4]] + 12, FL, 0.07 + 0.08 * (t - 20) / 15, 2200, 0.02, 0.25);
    }
    // the Sun: D major swelling in over three seconds before it appears, warm and wide, then fading
    for (const m of [50, 57, 62, 66, 69, 74]) organ(SUN - 2.0, MOON + 0.8, m, REG_MID, 0.36, 3200, 3.0, 2.0);
    // the Moon again: soft Gmaj7 -> D, fading out
    for (const m of [67, 71, 74, 78]) organ(MOON, MOON + 3.2, m, FL, 0.2, 2000, 1.5, 1.2);
    for (const m of [62, 66, 69, 74]) organ(MOON + 3.0, END, m, FL, 0.2, 2000, 1.5, 0.8);
  }
  return {
    output: master,
    start() { schedule(); },
    scheduleUntil() {},
  };
}
