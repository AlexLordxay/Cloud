// «Знайомся: Нептун» — the video's own score (MUSIC.md: the Hoverla organ, the author's favourite): one organ, no bass,
// no drums. A clock-like eighth-note figure (root, fifth, octave) grouping in threes against the bar, held chords that
// breathe, waves of loudness: a quiet glitter for the hook, the figure through space and the history, a swell for the
// jump and the Sun, more motion in the wind, thin and cold in the frost, a long slow rise down into the dark — then the
// hush (one high note hangs on) and the diamonds: A minor opens into A major over ~2.5 s (a lift, not a hit), and the
// end settles on the quiet figure alone. Times follow timeline.json (the author's voice).
function createSceneMusic(ctx, dest) {
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const BEAT = 0.625, E8 = BEAT / 2;
  // the timeline (timeline.json)
  const GLOBE = 5.85, COLOR = 16.25, ORBIT = 34.08, JUMP = 41.22, SUN = 49.03, WIND = 56.06, COLD = 65.68,
    DEEP = 73.65, HUSH = 81.0, LIFT = 82.1, FINAL = 91.0, END = 102.4;

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
    // the harmony: two bars (5 s) a chord, a plan per stretch of the film
    const plan = [
      [GLOBE, ['Am', 'F', 'C', 'G']], [COLOR, ['Am', 'F', 'C', 'G']], [ORBIT, ['F', 'G']], [JUMP, ['Am', 'F']],
      [SUN, ['C', 'G']], [WIND, ['Am', 'F']], [COLD, ['Em', 'Am']], [DEEP, ['Dm', 'Am', 'F']], [HUSH, ['Am']], [LIFT, ['A', 'D', 'A']],
      [FINAL, ['Am', 'F', 'Am']]];
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
    // the loudness of the figure over the film (the voice ducks it anyway)
    const wave = t =>
      t < GLOBE ? 0 :
      t < COLOR ? 0.15 + 0.2 * ramp(t, GLOBE, GLOBE + 4) :
      t < ORBIT ? 0.3 - 0.1 * ramp(t, COLOR, COLOR + 3) :
      t < JUMP ? 0.2 + 0.2 * ramp(t, ORBIT, JUMP) :
      t < SUN ? 0.4 + 0.25 * ramp(t, JUMP, SUN) :
      t < WIND ? 0.65 - 0.2 * ramp(t, SUN, SUN + 3) :
      t < COLD ? 0.55 + 0.15 * Math.sin((t - WIND) * 0.7) * 0.5 :
      t < DEEP ? 0.2 :
      t < HUSH - 0.2 ? 0.2 + 0.75 * ramp(t, DEEP, HUSH - 0.2) : 0;
    play(GLOBE, HUSH - 0.2, wave);
    // held chords that breathe in and out over each 5 s
    for (let t0 = GLOBE; t0 < HUSH - 1; t0 += 5) {
      const w = wave(t0 + 2.5), ch = chordAt(t0 + 0.1), t1 = Math.min(t0 + 5.4, HUSH - 0.2);
      for (const m of ch) organ(t0, t1, m + 12, w > 0.5 ? REG_MID : FL, 0.07 + 0.2 * w, 900 + 2500 * w, 2.2, 1.6);
    }
    // the hook: glitter — high soft notes falling like the stones (A minor), over a held high fifth
    const glit = [88, 84, 81, 88, 86, 81, 79, 84, 88, 81];
    glit.forEach((m, i) => organ(0.2 + i * 0.52, 0.2 + i * 0.52 + 0.35, m, FL, 0.06, 4000, 0.01, 1.2));
    organ(0.0, GLOBE + 0.4, 69, FL, 0.08, 2000, 1.5, 1.2); organ(0.0, GLOBE + 0.4, 76, FL, 0.06, 2500, 1.5, 1.2);
    // the Sun: a long high line opening over it
    organ(SUN + 0.5, WIND, 84, FL, 0.13, 3000, 1.8, 1.0); organ(SUN + 2.5, WIND, 88, FL, 0.08, 3000, 1.8, 1.0);
    // the cold: a thin high cluster that shivers
    organ(COLD + 0.3, DEEP, 83, FL, 0.06, 3000, 1.5, 1.0); organ(COLD + 0.5, DEEP, 84, FL, 0.05, 3000, 1.5, 1.0);
    // the long rise into the dark: a slow high line climbing
    [[DEEP + 1, 3, 76], [DEEP + 4, 2.5, 77], [DEEP + 6.5, 1.3, 79]].forEach(([t0, l, m]) => organ(t0, t0 + l, m + 12, FL, 0.14, 3000, 1.2, 0.6));
    // the hush: everything stops, one high note hangs on
    organ(HUSH - 0.25, LIFT + 1.5, 81, FL, 0.12, 2500, 0.3, 1.2);
    // the diamonds: A major breathes in over 2.5 s, the figure comes back full and bright
    for (const m of [57, 61, 64, 69, 73, 76]) organ(LIFT - 0.6, FINAL + 0.8, m, REG_MID, 0.28, 3500, 2.5, 2.0);
    play(LIFT + 0.8, FINAL, t => 0.55 + 0.35 * ramp(t, LIFT + 0.8, LIFT + 4) - 0.3 * ramp(t, FINAL - 2.5, FINAL));
    organ(LIFT + 1.5, FINAL, 85, FL, 0.15, 3200, 1.5, 1.0); organ(LIFT + 4.0, FINAL, 88, FL, 0.1, 3200, 1.5, 1.0);
    // the end: the quiet figure alone, fading; the last chord open
    play(FINAL, END - 2.0, t => 0.3 * (1 - ramp(t, FINAL, END - 2)));
    for (const m of [57, 60, 64]) organ(FINAL, END - 0.5, m + 12, FL, 0.11, 1600, 1.5, 1.5);
    organ(FINAL + 5, END - 0.5, 71, FL, 0.06, 2200, 2.0, 1.5);
  }
  return {
    output: master,
    start() { schedule(); },
    scheduleUntil() {},
  };
}
