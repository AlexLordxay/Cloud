// «А ти уявляєш Сонце так?» — the video's own score (the synthesised instruments of «Магнітні бурі» / «Місяць»; no
// quotation): a warm morning piano figure over the sunflowers, strings swelling as we lift off through the air, a hit on
// "А ти уявляєш Сонце так?", bells climbing with the count of Earths, heavy brass as the scales tip, a shimmer for the
// glowing spot, a boiling drone over the surface and brass for the corona, a driving pulse riding the sunlight, the
// morning figure again in the field; when the Sun goes out the music stops (a ticking piano for the 8 min 20 s), and it
// comes back with the full chord when the Sun lights up. Everything is synthesised.
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
  const organBus = bus(0.2, 0.95);
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
    // the video's beats (s): voice parts at 0.3 / 0.7 / 1.2 / 1.9 / 2.6 (scene.json)
    const LIFT = 2.86, SPACE = 6.6, HIT = 7.95, EARTHS = 10.3, FILL = 12.1, SCALE = 14.9, TILT = 16.7, SPOT = 20.0,
      GLOW = 20.7, BIG = 22.6, SURF = 25.1, COR = 28.7, RIDE = 31.7, FIELD = 38.5, LAND = 41.4, OFF = 44.75,
      DARK = 48.95, ON = 50.25, END = 58.4;
    const E8 = BEAT / 2;
    const FL = [[1, 1], [2, 0.35]];
    const CH = { D: [50, 54, 57], G: [43, 47, 50], A: [45, 49, 52], Bm: [47, 50, 54], Em: [52, 55, 59], Fsm: [54, 57, 61],
      C: [48, 52, 55], E: [52, 56, 59] };
    const held = (t0, t1, k, reg, w, sh = 0) => { for (const m of CH[k]) organ(t0, t1, m + sh, reg, 0.06 + 0.2 * w, 700 + 2500 * w, 1.4, 1.6); };
    // morning over the field: a warm piano figure in D, a soft pad, a high bell
    for (let t = 0.15, i = 0; t < LIFT + 0.2; t += E8 * 1.5, i++) piano(t, [62, 66, 69, 74, 69, 66][i % 6], 0.11 + 0.02 * Math.sin(i));
    for (const m of [50, 57, 62]) padNote(0.0, LIFT + 1.5, m, 0.5);
    bell(0.4, 86, 0.05);
    // the lift: tremolo strings swelling, the pad opening; the air thins into space (a high choir)
    trem(LIFT, HIT, 62, 0.26); trem(LIFT + 0.6, HIT, 69, 0.2); trem(LIFT + 1.2, HIT, 74, 0.16);
    held(LIFT, SPACE + 0.5, 'G', REG_MID, 0.35, -12);
    for (const m of [74, 78, 81]) aah(SPACE - 1.2, HIT + 0.2, m, 0.35);
    riser(SPACE - 0.6, HIT);
    // "А ти уявляєш Сонце так?": the hit, a wide D major
    hit(HIT);
    subNote(HIT, HIT + 4, 38, 0.8);
    held(HIT, EARTHS + 0.3, 'D', REG_FULL, 0.45, -12);
    for (const m of [74, 78, 81, 86]) aah(HIT + 0.2, EARTHS + 1.0, m, 0.32);
    // our little Earth, then the Earths pour in: a rising run of bells as the count climbs
    bell(EARTHS + 0.3, 90, 0.05);
    held(EARTHS, FILL, 'Bm', REG_MID, 0.45, -12);
    for (let t = FILL, i = 0; t < SCALE - 0.4; t += S16 * 1.5, i++) bell(t, 62 + [0, 2, 4, 7, 9, 12, 14, 16][i % 8] + 12 * Math.floor(i / 16) % 24, 0.07 + 0.002 * i);
    held(FILL, SCALE, 'G', REG_MID, 0.55, -12); for (const m of [55, 62, 67]) horn(FILL, SCALE, m, 0.18);
    // the scales: heavy brass as the Sun's pan sinks; a timpani as it hits the stop
    held(SCALE, TILT, 'Em', REG_MID, 0.45, -12); for (let t = SCALE, i = 0; t < TILT; t += BEAT, i++) spic(t, [40, 47][i % 2], 0.2, 800);
    for (const m of [38, 45, 50]) horn(TILT, TILT + 1.8, m, 0.45);
    timp(TILT + 1.55, 1.0, 33); subNote(TILT + 1.5, TILT + 4, 33, 0.9);
    held(TILT, SPOT, 'A', REG_MID, 0.4, -12);
    // the spot: hushed; a shimmer when it glows on its own
    held(SPOT, BIG, 'Fsm', REG_MID, 0.38, -12);
    for (let i = 0; i < 9; i++) bell(GLOW + i * 0.07, 86 + [0, 2, 4, 7, 9, 12, 14, 16, 19][i], 0.03);
    held(BIG, SURF, 'Bm', REG_MID, 0.4, -12); bell(BIG + 0.6, 81, 0.07);
    // the surface: a deep, boiling drone; the corona: brass rising to two million degrees
    subNote(SURF, COR + 0.5, 31, 0.6); held(SURF, COR, 'Em', REG_MID, 0.32, -12);
    for (let t = SURF, i = 0; t < COR - 0.2; t += S16 * 2, i++) spic(t, [40, 47, 43, 47][i % 4], 0.16, 800);
    for (const m of [50, 57, 62, 66]) horn(COR, COR + 2.4, m, 0.32);
    trem(COR, RIDE, 74, 0.16); trem(COR + 0.5, RIDE, 78, 0.12);
    held(COR, RIDE + 0.3, 'D', REG_FULL, 0.42, -12);
    // riding the sunlight: a driving pulse, the harmony climbing
    const RIDE_CH = ['G', 'A', 'Bm', 'A'];
    for (let t = RIDE, i = 0; t < FIELD - 0.3; t += S16 * 2, i++) spic(t, [50, 57, 54, 57, 62, 57, 54, 57][i % 8], 0.26 + 0.1 * (t - RIDE) / (FIELD - RIDE), 1500);
    for (let t = RIDE; t < FIELD - 0.5; t += 1.6) timp(t, 0.45, 38);
    RIDE_CH.forEach((k, i) => { held(RIDE + i * 1.6, RIDE + (i + 1) * 1.6 + 0.2, k, REG_MID, 0.5 + 0.06 * i, -12); for (const m of CH[k]) horn(RIDE + i * 1.6, RIDE + (i + 1) * 1.6, m + 12, 0.16); });
    for (const m of [69, 74, 78]) aah(RIDE + 2.5, FIELD, m, 0.28);
    timp(RIDE, 0.6, 38);
    // home: the field again — the morning figure returns, warm and full
    held(FIELD, OFF - 0.6, 'D', REG_MID, 0.6, -12);
    for (let t = FIELD, i = 0; t < OFF - 0.6; t += E8 * 1.5, i++) piano(t, [62, 66, 69, 74, 69, 66][i % 6], 0.12);
    for (const m of [62, 66, 69]) horn(FIELD, OFF - 0.6, m, 0.26);
    // the Sun goes out: everything stops; a low pulse, a ticking piano for the eight minutes, a deep thud at the dark
    subNote(OFF - 0.05, DARK, 29, 0.12);
    for (let t = OFF + 0.7, i = 0; t < DARK - 0.1; t += E8 * 1.0, i++) piano(t, i % 2 ? 81 : 74, 0.035);
    timp(DARK, 0.9, 29);
    // it lights up again: the full chord, choir, a bright bell; a warm end in D
    hit(ON);
    held(ON, END, 'D', REG_FULL, 0.5, -12);
    for (const m of [74, 78, 81, 86]) aah(ON + 0.2, END - 1.0, m, 0.32);
    for (let t = ON + 2.0, i = 0; t < END - 1.5; t += E8 * 1.5, i++) piano(t, [74, 78, 81, 86, 81, 78][i % 6], 0.09);
    for (const m of [50, 57, 62, 66]) horn(ON + 1.5, END - 1.0, m, 0.2);
    bell(ON + 0.4, 90, 0.07);
  }
  return {
    output: master,
    start() { schedule(); },
    scheduleUntil() {},
  };
}
