// "Великий вибух був не вибухом" — the video's own score (see /MUSIC.md): one pipe organ, no bass, no drums, no
// orchestra. A clock-like eighth-note arpeggio that groups in threes against the bar, held chords that breathe, dynamics
// in long waves, hushes before the radiant moments, minor brightening to major. Everything is synthesised; no quotation.
// Times are tied to timeline.json (seconds). createSceneMusic(ctx, dest) -> { start(), scheduleUntil() }.
function createSceneMusic(ctx, dest, seg) {
  // seg = {from, to}: render only the notes that start in [from, to), shifted to start at 0 (the renderer renders the piece
  // in slices and sums them, to keep the audio graph small)
  const SEG0 = seg ? seg.from : 0, SEG1 = seg ? seg.to : 1e9;
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const rnd = (a, b) => a + Math.random() * (b - a);
  const E = 0.275;                                   // one eighth note (s)
  const T_END = 378.53;
  const OUT_GAIN = 2.9;

  // ---- space: gentle glue compressor + a long, dark generated hall --------------------------------------------------
  const master = ctx.createGain();   // (no compressor: the dynamics are written in, and slices must sum linearly)
  const out = ctx.createGain(); out.gain.value = OUT_GAIN;
  master.connect(out).connect(dest);
  const len = Math.floor(ctx.sampleRate * 6.5), ir = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c); let lp = 0;
    for (let i = 0; i < len; i++) {
      const k = 0.55 - 0.45 * Math.min(1, i / (len * 0.5));          // damp the highs more and more as it decays
      lp += k * ((Math.random() * 2 - 1) - lp);
      d[i] = lp * Math.pow(1 - i / len, 2.6) * (i < 400 ? i / 400 : 1);
    }
  }
  const verb = ctx.createConvolver(); verb.buffer = ir;
  const wet = ctx.createGain(); wet.gain.value = 0.55; verb.connect(wet).connect(master);
  const organBus = ctx.createGain(); organBus.gain.value = 0.2;
  organBus.connect(master);
  const send = ctx.createGain(); send.gain.value = 0.95; organBus.connect(send).connect(verb);

  const noise = (() => {
    const b = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return b;
  })();
  // one slow tremulant shared by all pipes
  const trem = ctx.createOscillator(), tremD = ctx.createGain();
  trem.frequency.value = 5.0; tremD.gain.value = 5; trem.connect(tremD); trem.start(0); trem.stop(T_END + 20);

  // ---- the organ voice: sine partials (stops), tremulant, a breath of wind noise on the attack ----------------------
  const REG8 = [[1, 1], [2, 0.35]];
  const REG_MID = [[1, 1], [2, 0.6], [3, 0.3], [4, 0.25]];
  const REG_FULL = [[1, 1], [2, 0.8], [3, 0.5], [4, 0.5], [5, 0.3], [6, 0.3], [8, 0.2]];
  // t0..t1 = the note sounds in full (att in, hold until t1), then dies away over rel
  function organ(t0, t1, m, reg, level, cut, att = 0.05, rel = 0.4, pan = rnd(-0.35, 0.35)) {
    if (level < 0.001 || t1 <= t0 || t0 < SEG0 || t0 >= SEG1) return;
    t0 -= SEG0; t1 -= SEG0;
    const end = Math.max(t1, t0 + att) + rel;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = cut; lp.Q.value = 0.5;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(level, t0 + att);
    g.gain.setValueAtTime(level, Math.max(t1, t0 + att)); g.gain.linearRampToValueAtTime(0, end);
    const p = ctx.createStereoPanner(); p.pan.value = pan;
    lp.connect(g).connect(p).connect(organBus);
    for (const [r, a] of reg) {
      const f = midi(m) * r; if (f > 9000 || f < 18) continue;
      const ag = ctx.createGain(); ag.gain.value = a / reg.length * 1.6; ag.connect(lp);
      const o = ctx.createOscillator(); o.type = r <= 1 ? 'triangle' : 'sine'; o.frequency.value = f;
      tremD.connect(o.detune); o.connect(ag); o.start(t0); o.stop(end + 0.05);
    }
    if (att < 0.2) {
      const n = ctx.createBufferSource(); n.buffer = noise;
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = midi(m) * 4; bp.Q.value = 3;
      const ng = ctx.createGain(); ng.gain.setValueAtTime(level * 0.3, t0); ng.gain.exponentialRampToValueAtTime(0.0005, t0 + 0.09);
      n.connect(bp).connect(ng).connect(p); n.start(t0); n.stop(t0 + 0.1);
    }
  }

  // ---- the plan ----------------------------------------------------------------------------------------------------
  const CHORDS = {
    Am: [57, 60, 64], F: [57, 60, 65], C: [55, 60, 64], G: [55, 59, 62], Dm: [57, 62, 65], Em: [55, 59, 64],
    E: [56, 59, 64], A: [57, 61, 64], D: [57, 62, 66], Bm: [59, 62, 66], 'F#m': [57, 61, 66],
  };
  // sections: chords spread evenly over [t0, t1); oct = shift of the figure; step = 1 plays every eighth, 3 only the accents
  const SECT = [
    { t0: 0,      t1: 32.05,  ch: ['Am', 'F', 'C', 'G', 'Am', 'F', 'Dm', 'Em'] },                      // hook
    { t0: 32.05,  t1: 56.6,   ch: ['Am', 'Dm', 'F', 'E', 'Am', 'Dm'] },                                // inflation
    { t0: 58.3,   t1: 79.09,  ch: ['F', 'C', 'Dm', 'E', 'Am'] },
    { t0: 79.09,  t1: 104,    ch: ['Am', 'G', 'F', 'E', 'Am', 'G', 'F', 'E'], oct: 12, busy: true },  // hot soup
    { t0: 104,    t1: 128.65, ch: ['Dm', 'Am', 'F', 'C', 'G', 'Am'], busy: true },
    { t0: 128.65, t1: 178.6,  ch: ['C', 'G', 'Am', 'F', 'C', 'G', 'F', 'Dm', 'C', 'G', 'Am', 'F'] },    // first light
    { t0: 180.6,  t1: 192.58, ch: ['D', 'A', 'Bm', 'A'] },
    { t0: 221.6,  t1: 263.66, ch: ['A', 'E', 'F#m', 'D', 'A', 'E', 'Bm', 'D', 'F#m', 'E'] },           // first stars
    { t0: 263.66, t1: 293.3,  ch: ['Am', 'F', 'C', 'G', 'Dm'], step: 3, broad: true },                 // web
    { t0: 293.3,  t1: 332.83, ch: ['F', 'C', 'Am', 'G', 'Dm', 'F', 'C', 'G'], oct: 12, soft: true },   // "you"
    { t0: 332.83, t1: 346.6,  ch: ['Am', 'F', 'C', 'G'] },                                             // finale
    { t0: 346.6,  t1: 361.75, ch: ['A', 'D', 'F#m', 'E', 'A'] },
    { t0: 361.75, t1: 378.5,  ch: ['A', 'D', 'A'], quiet: true },                                      // end card
  ];
  for (const s of SECT) {
    const L = (s.t1 - s.t0) / s.ch.length;
    s.list = s.ch.map((n, i) => ({ ta: s.t0 + i * L, tb: s.t0 + (i + 1) * L, name: n, notes: CHORDS[n] }));
  }
  const sectAt = t => SECT.find(s => t >= s.t0 && t < s.t1);

  // overall intensity 0..1 (smooth, piecewise linear): the waves of the whole piece
  const KP = [
    [0, .10], [8, .12], [20, .18], [31, .24], [32.05, .16], [43, .18], [46.2, .26], [50, .92], [54.2, .92], [56.6, 0],
    [58.3, 0], [61.5, .40], [70, .5], [78.5, .55], [79.2, .50], [85, .65], [95, .82], [103.5, .82], [106, .40],
    [114, .45], [121, .45], [128.6, .40], [135, .40], [150, .5], [162, .5], [170, .42], [177, .38], [178.6, 0],
    [180.6, 0], [184, .85], [188, .8], [191, .25], [192.58, 0], [221.6, 0], [222.5, .22], [226, .40], [250, .55],
    [262, .55], [263.66, .45], [268, .7], [285, .7], [291, .5], [293.3, .3], [305, .3], [307, .4], [311, .45],
    [316, .3], [330, .28], [332.83, .3], [341, .5], [344.5, .55], [345.5, .12], [346.6, .12], [351, 1.0], [360, 1.0],
    [362, .42], [366, .3], [372, .2], [376, .05], [378.53, 0],
  ];
  const I = t => {
    if (t <= KP[0][0]) return KP[0][1];
    for (let i = 1; i < KP.length; i++) if (t < KP[i][0]) {
      const [a, x] = KP[i - 1], [b, y] = KP[i];
      return x + (y - x) * (t - a) / (b - a);
    }
    return 0;
  };

  function schedule() {
    // 1) the clock: eighth notes in threes, a cell of three chord tones, the first of every three accented
    for (let k = 0, t = 0; t < T_END - 1; k++, t = k * E) {
      const s = sectAt(t); if (!s) continue;
      const d = I(t); if (d < 0.03) continue;
      const ch = s.list.find(c => t >= c.ta && t < c.tb), b = ch.notes.map(n => n + 12 + (s.oct || 0));
      const cell = [b[0], b[2], b[1] + 12], i3 = k % 3;
      if (s.step === 3 && i3) continue;
      const acc = i3 === 0 ? 1.25 : 0.85, dd = d * (s.soft ? 0.95 : s.quiet ? 0.7 : 1);
      const reg = dd > 0.55 ? REG_MID : REG8;
      const lvl = (0.04 + 0.17 * Math.pow(dd, 1.3)) * acc * (s.step === 3 ? 0.8 : 1);
      const hold = s.step === 3 ? E * 2.5 : E * 0.9;
      organ(t, t + hold, cell[i3], reg, lvl, 1000 + 3500 * dd, 0.012, s.step === 3 ? 0.6 : 0.12);
      if (dd > 0.45) organ(t, t + hold, cell[i3] + 12, REG8, 0.05 + 0.13 * (dd - 0.45), 2800, 0.012, s.step === 3 ? 0.6 : 0.12);
      if (s.busy && dd > 0.3) {                                  // hot soup: a flicker on the off-beat, an octave up
        organ(t + E / 2, t + E * 0.85, cell[(i3 + 1) % 3] + 12, REG8, (0.02 + 0.1 * dd) * 0.8, 3200, 0.008, 0.08);
      }
    }
    // 2) held chords that breathe in and out
    for (const s of SECT) for (const c of s.list) {
      const L = c.tb - c.ta, mid = I(c.ta + L / 2); if (mid < 0.05) continue;
      const w = mid * (s.soft ? 0.9 : s.quiet ? 0.35 : 1);
      const att = Math.min(s.broad ? 2.8 : 2.2, L * 0.45), lv = 0.04 + 0.12 * w, cut = 800 + 2300 * w;
      const tb = Math.min(c.tb + 0.6, s.t1 + 0.4);
      c.notes.forEach(m => organ(c.ta, tb, m + 12, w > 0.5 ? REG_MID : REG8, lv, cut, att, 1.8));
      organ(c.ta, tb, c.notes[0] + 24, REG8, lv * 0.7, 2500, att + 0.3, 1.8);
      if (s.broad) { organ(c.ta, tb, c.notes[1], REG8, lv * 0.8, 1200, att, 2.0); organ(c.ta, tb, c.notes[2] + 24, REG8, lv, 3000, att, 2.0); }
    }

    // 3) events -------------------------------------------------------------------------------------------------
    // K6: a long swell (3.8 s in) to the first peak, then it lets go; one high note carries through the pause
    for (const m of [57, 64, 69, 72, 76, 81]) organ(46.2, 54.6, m, REG_MID, 0.17, 3000, 3.8, 2.2);
    organ(50, 55.5, 88, REG8, 0.08, 3500, 1.5, 1.5);
    organ(55.2, 58.9, 88, REG8, 0.08, 3000, 1.0, 1.0);
    // 178.6 hush: one high note, then the radiant swell (D major, 3.4 s in) at 180.6
    organ(177.6, 182.6, 88, REG8, 0.09, 3000, 1.2, 1.2);
    for (const m of [62, 66, 69, 74, 78, 81]) organ(180.6, 188.5, m, REG_MID, 0.17, 3500, 3.4, 3.0);
    organ(182.5, 190, 90, REG8, 0.08, 3500, 1.5, 2.0);
    // dark ages: almost silence, a very sparse high soft tone
    [[193.5, 88, 5.5], [199.0, 81, 5.5], [204.5, 84, 6.0], [210.0, 76, 5.5]].forEach(([t, m, d]) => organ(t, t + d * 0.4, m, REG8, 0.045, 1800, 2.0, d * 0.6));
    // first star: a quiet held note, then the slow bloom: Am opens, the third lifts to C#, A major
    organ(214.0, 217.6, 76, REG8, 0.07, 1800, 1.4, 1.6);
    for (const m of [57, 64, 69, 72, 76]) organ(216.0, 222.0, m + (m < 60 ? 12 : 0), REG8, 0.13, 2000, 2.6, 2.6);
    for (const m of [73, 76, 81, 85]) organ(219.0, 228.0, m, REG_MID, 0.12, 3500, 2.8, 3.0);
    // web: a broad open chord rising over 3 s
    for (const m of [57, 64, 69, 72, 76, 81]) organ(263.66, 270.5, m, REG_MID, 0.14, 2800, 3.0, 2.5);
    // «Ти»: a few high drops for the spark of hydrogen (31 s: 317.9 on)
    [[319.5, 88], [322.2, 91], [324.0, 86], [326.8, 93], [329.2, 88]].forEach(([t, m]) => organ(t, t + 0.25, m, REG8, 0.05, 4000, 0.01, 1.4));
    // finale: hush (345.5), then A major breathes in over 4.2 s to the brightest chord, held, then settles
    organ(344.8, 348.8, 88, REG8, 0.09, 3000, 0.8, 1.2);
    for (const m of [57, 61, 64, 69, 73, 76, 81]) organ(346.6, 360.5, m, REG_FULL, 0.2, 4500, 4.2, 3.2);
    organ(348.5, 361, 85, REG_MID, 0.1, 4500, 3.0, 3.0);
    organ(350.5, 360, 93, REG8, 0.07, 5000, 3.0, 2.5);
    // end card: soft resolution in A major, lasting and fading away to 378.5
    for (const m of [61, 64, 69, 73, 76]) organ(361.0, 372.5, m, REG8, 0.07, 2200, 2.8, 5.8);
    organ(364, 372.5, 81, REG8, 0.05, 2500, 3.0, 5.0);
  }
  return { output: master, start() { schedule(); }, scheduleUntil() {} };
}
