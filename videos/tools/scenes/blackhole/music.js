// "What happens if you fall into a black hole" — the video's own score: pipe organ only, no bass, no drums (the author's
// wish). Held chords swell while an arpeggio speeds up with the fall; at the horizon everything stops; then one soft high
// chord for "nobody knows what is inside". Everything is synthesised; no samples, no quotations. Times in seconds of the video.
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
  function organ(t0, t1, m, reg, level, cut, att = 0.05) {
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = cut; lp.Q.value = 0.5;
    const g = env(t0, att, Math.max(0, t1 - t0 - att), 0.4, level);
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
    const STOP = 29.4;                                   // the horizon: everything stops
    // held chords, two bars each (5 s), louder and with more stops as the fall goes on
    for (let c = 0; c * CHORD < STOP; c++) {
      const t0 = c * CHORD, t1 = Math.min(STOP, t0 + CHORD), up = UPPER[c % 4];
      const reg = c < 2 ? REG8 : c < 4 ? REG_MID : REG_FULL;
      for (const m of up) organ(t0, t1, m, reg, 0.28 + 0.06 * c, 800 + c * 800, c === 0 ? 1.5 : 0.5);
      if (c >= 4) organ(t0, t1, up[0] + 1, REG8, 0.16, 1500, 0.5);               // a minor second: unease
    }
    // the arpeggio enters with the fall (5 s) and speeds up: eighths -> sixteenths -> thirty-seconds
    let t = 5, i = 0;
    const pat = [0, 7, 12, 15, 12, 7, 0, 7];
    while (t < STOP - 0.1) {
      const base = UPPER[Math.floor(t / CHORD) % 4][0];
      const dt = t < 13 ? BEAT / 2 : t < 22 ? S16 : S16 / 2;
      const prog = (t - 5) / (STOP - 5);
      organ(t, t + Math.max(0.12, dt * 1.6), base + pat[i % 8] + (prog > 0.55 ? 12 : 0), prog < 0.35 ? REG8 : REG_MID, 0.26 + 0.3 * prog, 1200 + 4000 * prog, 0.01);
      i++; t += dt;
    }
    // after the horizon: silence, then a lone soft high chord (A flat major over C: open, unanswered)
    for (const m of [72, 75, 80, 84]) organ(30.8, 37.5, m, REG8, 0.3, 2500, 1.2);
  }
  return {
    output: master,
    start() { schedule(); },
    scheduleUntil() {},
  };
}
