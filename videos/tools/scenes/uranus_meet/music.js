// «Знайомся: Уран» — the score of «Знайомся: TRAPPIST-1e», its cues moved onto Uranus' timeline (the hook's swing,
// Herschel, the 84-year orbit, the dive to the ring, under the ring, the clouds, the cold, the hush of the night side, the
// moons, Voyager, the sky, the end). The original notes:
// «Знайомся: TRAPPIST-1e» — the video's own score, after the Neptune one (MUSIC.md: the Hoverla organ): one organ, no
// bass, no drums. The clock-like eighth-note figure (root, fifth, octave) in threes against the bar, held chords that
// breathe, waves of loudness: a high glitter over the crescent and the star, the figure rising as the camera swings
// round to the "eye", lighter for the sizes and the six-day year, cold for the eternal night, a slow rise through the
// ocean — the hush — and «можливо, там є життя»: A minor opens into A major over ~2.5 s (a lift, not a hit); back to
// the quiet minor for «але поки це лише мрія», and the end settles on the figure alone. Times: timeline.json.
function createSceneMusic(ctx, dest) {
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const BEAT = 0.625, E8 = BEAT / 2;
  // the timeline (timeline.json)
  const REVEAL = 2.66, STAR = 12.23, YEAR = 21.23, LOCK = 28.24, SYSTEM = 37.16, SKY = 40.02, EYE = 46.81, HUSH = 55.27, LIFT = 62.31, DREAM = 75.55, FINAL = 81.06, END = 99.02;

  const master = ctx.createDynamicsCompressor();
  master.threshold.value = -16; master.ratio.value = 3; master.attack.value = 0.02; master.release.value = 0.3;
  const out = ctx.createGain(); out.gain.value = 0.6;
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
  // Pipe organ: sine partials (the stops) with a slow tremulant, a breath of wind on the attack, a low-pass that opens
  // as the registration grows. Stops are [harmonic ratio, level].
  const organBus = bus(0.11, 0.95);
  const FL = [[1, 1], [2, 0.35]];
  const REG_MID = [[1, 1], [2, 0.6], [3, 0.3], [4, 0.25]];
  function organ(t0, t1, m, reg, level, cut, att = 0.05, rel = 0.4) {
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = cut; lp.Q.value = 0.5;
    const g = env(t0, att, Math.max(0, t1 - t0 - att), rel, level);
    lp.connect(g).connect(organBus);
    const lfo = ctx.createOscillator(), ld = ctx.createGain(); lfo.frequency.value = 5.2; ld.gain.value = 5;
    lfo.connect(ld); lfo.start(t0); lfo.stop(t1 + rel + 0.1);
    for (const [r, a] of reg) {
      const f = midi(m) * r; if (f > 9000 || f < 18) continue;
      const ag = ctx.createGain(); ag.gain.value = a / reg.length * 1.6; ag.connect(lp);
      const o = ctx.createOscillator(); o.type = r <= 1 ? 'triangle' : 'sine'; o.frequency.value = f;
      ld.connect(o.detune); o.connect(ag); o.start(t0); o.stop(t1 + rel + 0.1);
    }
    const n = ctx.createBufferSource(); n.buffer = noise;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = midi(m) * 4; bp.Q.value = 3;
    const ng = ctx.createGain(); ng.gain.setValueAtTime(level * 0.35, t0); ng.gain.exponentialRampToValueAtTime(0.001, t0 + 0.09);
    n.connect(bp).connect(ng).connect(organBus); n.start(t0); n.stop(t0 + 0.1);
  }

  function schedule() {
    const CH = { Am: [57, 60, 64], F: [53, 57, 60], C: [55, 60, 64], G: [55, 59, 62], Em: [52, 55, 59], Dm: [50, 53, 57], A: [57, 61, 64], D: [50, 54, 57] };
    const plan = [
      [REVEAL, ['Am', 'F', 'C']], [STAR, ['F', 'G']], [YEAR, ['C', 'G']], [LOCK, ['Am', 'Em']], [SYSTEM, ['F', 'G']],
      [SKY, ['C']], [EYE, ['Dm', 'Am', 'F']], [HUSH, ['Am']], [LIFT, ['A', 'D', 'A']], [DREAM, ['Am', 'F']], [FINAL, ['Am', 'F', 'Am']]];
    const chordAt = t => {
      let cur = plan[0];
      for (const p of plan) if (t >= p[0] - 0.01) cur = p;
      const k = Math.floor((t - cur[0]) / 5) % cur[1].length;
      return CH[cur[1][Math.max(0, k)]];
    };
    const fig = ch => [ch[0], ch[0] + 7, ch[0] + 12];
    const play = (t0, t1, dyn) => {
      for (let t = t0, i = 0; t < t1 - 0.05; t += E8, i++) {
        const d = dyn(t), f = fig(chordAt(t)), m = f[i % 3];
        if (d <= 0.01) continue;
        organ(t, t + E8 * 0.9, m, d > 0.55 ? REG_MID : FL, 0.08 + 0.22 * d, 900 + 3000 * d, 0.01, 0.12);
        if (d > 0.45) organ(t, t + E8 * 0.9, m + 12, FL, 0.05 + 0.12 * (d - 0.45), 2500, 0.01, 0.12);
      }
    };
    const ramp = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
    const wave = t =>
      t < REVEAL ? 0 :
      t < STAR ? 0.15 + 0.4 * ramp(t, REVEAL + 1, STAR - 1) :
      t < YEAR ? 0.4 - 0.15 * ramp(t, STAR, STAR + 2) :
      t < LOCK ? 0.3 + 0.1 * ramp(t, YEAR, LOCK) :
      t < SYSTEM ? 0.25 :
      t < SKY ? 0.3 + 0.2 * ramp(t, SYSTEM, SKY) :
      t < EYE ? 0.3 :
      t < HUSH - 0.2 ? 0.25 + 0.65 * ramp(t, EYE, HUSH - 0.2) : 0;
    play(REVEAL, HUSH - 0.2, wave);
    for (let t0 = REVEAL; t0 < HUSH - 1; t0 += 5) {
      const w = wave(t0 + 2.5), ch = chordAt(t0 + 0.1), t1 = Math.min(t0 + 5.4, HUSH - 0.2);
      for (const m of ch) organ(t0, t1, m + 12, w > 0.5 ? REG_MID : FL, 0.07 + 0.2 * w, 900 + 2500 * w, 2.2, 1.6);
    }
    // the hook: glitter over the crescent and the red star, over a held high fifth
    const glit = [81, 84, 88, 86, 84, 81, 79, 81, 84, 88, 86];
    glit.forEach((m, i) => organ(0.2 + i * 0.55, 0.2 + i * 0.55 + 0.35, m, FL, 0.11 * (i < 7 ? 1 : 0.6), 4000, 0.01, 1.2));
    organ(0.0, REVEAL + 0.6, 69, FL, 0.14, 2000, 0.6, 1.4); organ(0.0, REVEAL + 0.6, 76, FL, 0.1, 2500, 0.6, 1.4);
    // the eternal night: a thin high cluster that shivers
    organ(LOCK + 9.0, SYSTEM + 0.5, 83, FL, 0.06, 3000, 1.5, 1.0); organ(LOCK + 9.2, SYSTEM + 0.5, 84, FL, 0.05, 3000, 1.5, 1.0);
    // the neighbour drifting over: a soft high line
    organ(SKY + 0.6, EYE + 0.5, 79, FL, 0.10, 3000, 1.8, 1.2);
    // the slow rise over the ocean
    [[EYE + 4, 3, 76], [EYE + 7, 2.5, 77], [EYE + 9.5, 1.6, 79]].forEach(([t0, l, m]) => organ(t0, t0 + l, m + 12, FL, 0.13, 3000, 1.2, 0.6));
    // the hush: one high note hangs on
    organ(HUSH - 0.25, LIFT + 1.5, 81, FL, 0.12, 2500, 0.3, 1.2);
    // «можливо, там є життя»: A major breathes in, the figure bright; it stays through the dark plants
    for (const m of [57, 61, 64, 69, 73, 76]) organ(LIFT - 0.6, DREAM + 0.6, m, REG_MID, 0.26, 3500, 2.5, 2.0);
    play(LIFT + 0.8, DREAM, t => 0.5 + 0.3 * ramp(t, LIFT + 0.8, LIFT + 4) - 0.35 * ramp(t, DREAM - 3, DREAM));
    organ(LIFT + 1.5, DREAM, 85, FL, 0.14, 3200, 1.5, 1.0);
    // «але поки це лише мрія»: back to A minor, quieter
    play(DREAM, FINAL, t => 0.35 - 0.1 * ramp(t, DREAM, FINAL));
    for (const m of [57, 60, 64]) organ(DREAM, FINAL + 0.5, m + 12, FL, 0.10, 1600, 2.0, 1.5);
    // the end: the quiet figure alone, fading; the last chord open
    play(FINAL, END - 2.0, t => 0.28 * (1 - ramp(t, FINAL, END - 2)));
    for (const m of [57, 60, 64]) organ(FINAL, END - 0.5, m + 12, FL, 0.11, 1600, 1.5, 1.5);
    organ(FINAL + 4, END - 0.5, 71, FL, 0.06, 2200, 2.0, 1.5);
  }
  return {
    output: master,
    start() { schedule(); },
    scheduleUntil() {},
  };
}
