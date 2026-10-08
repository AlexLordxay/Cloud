// "Where are you in the Universe" — the video's own score (not on the site). Epic trailer style in D minor at 120 bpm:
// soft high bells over a pad, then a low string ostinato ("ta-da-ta-da"), timpani, brass swells and a choir build up
// with the flight out to the galaxy; a riser and one big hit at the black hole, then a deep drone with lone high notes.
// Everything is synthesised here; no samples, no quotations. Times are in seconds of the video.
function createSceneMusic(ctx, dest) {
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const rnd = (a, b) => a + Math.random() * (b - a);
  const BEAT = 0.5, S16 = BEAT / 4, CHORD = 8 * BEAT;          // a chord lasts two bars (4 s)
  const ROOTS = [38, 34, 41, 36];                               // D, B♭, F, C (bass)
  const UPPER = [[62, 65, 69], [62, 65, 70], [60, 65, 69], [60, 64, 67]];
  const HIT = 59.0;

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
    for (const m of [50, 57, 62, 65]) horn(t, t + 0.8, m, 0.9);
    for (const m of [74, 77, 81]) aah(t, t + 1.2, m, 0.6);
  }

  function schedule() {
    // Section levels (0..1) by time: how much ostinato, how bright, where drums and brass come in.
    const ostLevel = t => t < 6 ? 0 : t < 13 ? 0.3 + 0.1 * (t - 6) / 7 : t < 21 ? 0.5 : t < 38 ? 0.6 : 0.78;
    const ostCut = t => t < 13 ? 650 : t < 21 ? 1000 : t < 38 ? 1500 : t < 48 ? 2200 : 2200 + 2200 * (t - 48) / 11;
    for (let c = 0; c * CHORD < HIT; c++) {
      const t0 = c * CHORD, t1 = Math.min(HIT, t0 + CHORD), k = c % 4, root = ROOTS[k], up = UPPER[k];
      // pad and sub under everything until the hit
      for (const m of up) padNote(t0, t1, m, t0 < 21 ? 0.9 : 0.6);
      if (t0 >= 6) subNote(t0, t1, root - 12, t0 < 13 ? 0.5 : 0.9);
      // the ostinato: straight sixteenths, accented on the beat; doubled an octave up once it is full
      for (let t = Math.max(t0, 6); t < t1 - 1e-6; t += S16) {
        const i = Math.round(t / S16) % 16, acc = [1, 0.5, 0.7, 0.5][i % 4];
        const step = [0, 0, 12, 0, 7, 0, 12, 0, 0, 0, 12, 0, 10, 0, 7, 0][i];
        spic(t, root + step, ostLevel(t) * acc, ostCut(t));
        if (t >= 38) spic(t, root + 12 + step, ostLevel(t) * acc * 0.45, ostCut(t));
      }
      // timpani: bar downbeats from 13 s, more after 21 s, a gallop in the full part, eighths in the build
      if (t0 >= 13) for (let b = 0; b < 8; b++) {
        const t = t0 + b * BEAT; if (t >= HIT) break;
        if (t < 21) { if (b % 4 === 0) timp(t, 0.6); }
        else if (t < 38) { if (b % 4 === 0) timp(t, 0.8); else if (b % 4 === 2) timp(t, 0.4); }
        else if (t < 48) { timp(t, b % 2 ? 0.45 : 0.85); if (b === 7) { timp(t + S16 * 2, 0.5); timp(t + S16 * 3, 0.6); } }
        else { const v = 0.5 + 0.6 * (t - 48) / 11; timp(t, v); timp(t + BEAT / 2, v * 0.7); }
      }
      // brass from 21 s; choir from 29 s, an octave higher in the full part
      if (t0 >= 21) for (const m of up.map(x => x - 12)) horn(t0, t1, m, t0 < 38 ? 0.55 : 0.8);
      if (t0 >= 29) for (const m of up) aah(t0, t1, m + (t0 >= 38 ? 12 : 0), t0 < 38 ? 0.5 : 0.7);
      // high soft notes on top all the way: bells, sparse at first
      const step = t0 < 6 ? 0.75 : t0 < 38 ? 1.0 : 0.5;
      for (let t = t0; t < t1 - 1e-6; t += step) {
        if (t > 0.3 && Math.random() < (t0 < 6 ? 0.85 : 0.55)) bell(t, up[Math.floor(Math.random() * 3)] + 12 + (Math.random() < 0.3 ? 12 : 0), t0 < 6 ? 0.55 : 0.45);
      }
    }
    riser(48.5, HIT);
    hit(HIT);
    // after the hit: a deep drone with lone high notes, then a soft last chord under the end card
    subNote(HIT + 0.3, 66, 26, 0.9);
    padNote(HIT + 1.5, 66, 50, 0.5);
    [[60.6, 86], [62.0, 81], [63.4, 77], [64.8, 76], [66.6, 74]].forEach(([t, m]) => bell(t, m, 0.5));
    aah(HIT + 1, 65, 81, 0.25);
    for (const m of [50, 57, 62, 64, 69]) padNote(66, 70, m, 0.7);
    bell(67.2, 86, 0.35);
  }
  return {
    output: master,
    start() { schedule(); },
    scheduleUntil() {},
  };
}
