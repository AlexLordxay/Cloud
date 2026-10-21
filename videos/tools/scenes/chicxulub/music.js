// The score of "Що сталося з Землею, коли вимерли динозаври" (score.js renders it offline). The author's taste
// (MUSIC.md): an organ in the spirit of a space-film organ score (no quotation) — a clock-like figure in eighths
// grouping in threes against the bar, chords that breathe, waves of loudness, a hush with one high note left before
// the climax, and the climax a brightening (minor to major) that comes in over 2–3 s, never a crash; drums allowed if
// they sound like real drums, not electronic ones.
//
// The drums are modal: each hit is the membrane's own partials (the inharmonic modes of a circular membrane for a
// taiko, the near-harmonic ones of a kettle drum, whose air loading tunes them), each decaying at its own rate, the
// pitch sinking a little as the skin relaxes after the blow; on top the stick or felt on the skin (a short filtered
// noise burst) and the shell; every hit slightly different in strength, pitch and timing, as players are; all in a hall
// whose high end dies sooner than its low.
//
// The bass guitar (a variant ending in '_bass') is a plucked string: Karplus–Strong — a burst of soft noise, plucked a
// fifth of the way along (the finger's warmth), running round a delay line one period long and losing its highs each
// time round, as a real string does; through a pickup (low-pass and a little drive, so its growl carries on a phone).
//
// Variants (opts.v): 'taiko' — organ and a taiko ensemble; 'timp' — organ and orchestral kettle drums (rolls);
// 'organ' — organ alone; 'taiko_bass', 'timp_bass' — with the bass guitar. opts.T0: the film time at which the music starts (cues below are in film seconds of the
// test clip: the end of the long night 0–6 s, the finale 6–22 s: the veil going 6–9.5, the snow melting 9.5–11.5, the
// drift 11.5–21, today's Earth from ~21).
function createSceneMusic(ctx, dest, opts = {}) {
  const V = (opts.v || 'taiko').split('_')[0], BASS = /_bass$/.test(opts.v || '');
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  let seed = opts.seed || 11;
  const rnd = (a, b) => a + ((seed = (seed * 16807) % 2147483647) / 2147483647) * (b - a);

  const master = ctx.createDynamicsCompressor();
  master.threshold.value = -18; master.ratio.value = 2.5; master.attack.value = 0.03; master.release.value = 0.4;
  const out = ctx.createGain(); out.gain.value = 0.5;
  master.connect(out).connect(dest);
  // the hall: 4.5 s of decaying noise, its highs fading faster than its lows (a one-pole low-pass closing over time),
  // with a few early reflections, a little different left and right
  const len = Math.floor(ctx.sampleRate * 4.5), ir = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c); let y = 0;
    for (let i = 0; i < len; i++) {
      const x = i / len, k = 0.9 * Math.exp(-x * 5) + 0.03;               // the filter closes as the tail goes on
      y += k * ((rnd(-1, 1)) - y);
      d[i] = y * Math.pow(1 - x, 2.2) * (i < ctx.sampleRate * 0.012 ? 0 : 1);
    }
    for (const [ms, a] of [[13, 0.6], [21, 0.45], [34, 0.35], [47, 0.3], [61, 0.22]]) d[Math.floor(ctx.sampleRate * (ms + c * 3) / 1000)] += a;
  }
  const verb = ctx.createConvolver(); verb.buffer = ir;
  const wet = ctx.createGain(); wet.gain.value = 0.45; verb.connect(wet).connect(master);
  const bus = (gain, send) => {
    const g = ctx.createGain(); g.gain.value = gain; g.connect(master);
    const s = ctx.createGain(); s.gain.value = send; g.connect(s).connect(verb);
    return g;
  };
  // the organ leads, the drums and the bass carry it (opts.only: 'organ', 'drums' or 'bass' — the rest muted, for
  // checking the balance)
  const on = part => !opts.only || opts.only === part;
  const organBus = bus(on('organ') ? 0.6 : 0, 0.95), drumBus = bus(on('drums') ? 0.45 : 0, 0.4);
  // no rumble: the drums lose what is below ~45 Hz (a phone can't play it, and it would only boom), shelved below 90
  const dHP = ctx.createBiquadFilter(); dHP.type = 'highpass'; dHP.frequency.value = 45; dHP.Q.value = 0.7;
  const dLS = ctx.createBiquadFilter(); dLS.type = 'lowshelf'; dLS.frequency.value = 90; dLS.gain.value = -4;
  const drumIn = ctx.createGain(); drumIn.connect(dHP).connect(dLS).connect(drumBus);
  const noise = (() => {
    const b = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = rnd(-1, 1);
    return b;
  })();
  const env = (t0, a, hold, rel, peak = 1) => {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(peak, t0 + a);
    g.gain.setValueAtTime(peak, t0 + a + hold); g.gain.linearRampToValueAtTime(0, t0 + a + hold + rel);
    return g;
  };
  const T0 = opts.T0 || 0, at = t => Math.max(0, t - T0);                  // film time → context time

  // ---- the organ: sine partials (the stops) with a slow tremulant, a breath of wind on the attack ----
  const FL = [[1, 1], [2, 0.35]];
  const MID = [[1, 1], [2, 0.6], [3, 0.3], [4, 0.25]];
  const FULL = [[1, 1], [2, 0.8], [3, 0.5], [4, 0.5], [5, 0.3], [6, 0.3], [8, 0.2]];
  function organ(t0, t1, m, reg, level, cut, att = 0.05, rel = 0.4) {
    t0 = at(t0); t1 = at(t1); if (t1 <= t0) return;
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
    n.connect(bp).connect(ng).connect(organBus); n.start(t0, rnd(0, 1.5)); n.stop(t0 + 0.1);
  }

  // ---- a drum hit: modes (ratio, level, decay in s), the pitch sinking by `bend` over the first ~80 ms, an attack
  // noise (centre frequency, length) and a shell knock (centre, decay) ----
  function drum(t, f0, vel, kind, pan) {
    t = at(t) + rnd(-0.008, 0.008); if (t < 0) return;
    vel *= rnd(0.85, 1.1); f0 *= rnd(0.985, 1.015);
    const K = kind, o = ctx.createGain(); o.gain.value = vel;
    const p = ctx.createStereoPanner(); p.pan.value = pan; o.connect(p).connect(drumIn);
    for (const [r, a, dec] of K.modes) {
      const f = f0 * r; if (f > 8000) continue;
      const s = ctx.createOscillator(); s.frequency.setValueAtTime(f * (1 + K.bend), t); s.frequency.exponentialRampToValueAtTime(f, t + 0.08);
      const g = ctx.createGain(), d = dec * rnd(0.85, 1.15);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(a, t + K.rise); g.gain.exponentialRampToValueAtTime(0.0005, t + d * 6.9);
      s.connect(g).connect(o); s.start(t); s.stop(t + d * 7);
    }
    const n = ctx.createBufferSource(); n.buffer = noise; n.playbackRate.value = rnd(0.9, 1.1);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = K.hit[0] * rnd(0.9, 1.1); bp.Q.value = 0.8;
    const ng = ctx.createGain(); ng.gain.setValueAtTime(K.hit[2], t); ng.gain.exponentialRampToValueAtTime(0.001, t + K.hit[1]);
    n.connect(bp).connect(ng).connect(o); n.start(t, rnd(0, 1.5)); n.stop(t + K.hit[1] + 0.02);
    if (K.shell) {
      const n2 = ctx.createBufferSource(); n2.buffer = noise;
      const b2 = ctx.createBiquadFilter(); b2.type = 'bandpass'; b2.frequency.value = K.shell[0]; b2.Q.value = 6;
      const g2 = ctx.createGain(); g2.gain.setValueAtTime(K.shell[2], t); g2.gain.exponentialRampToValueAtTime(0.001, t + K.shell[1]);
      n2.connect(b2).connect(g2).connect(o); n2.start(t, rnd(0, 1.5)); n2.stop(t + K.shell[1] + 0.02);
    }
  }
  // a circular membrane's modes (0,1) (1,1) (2,1) (0,2) (3,1) (1,2) (4,1) (2,2), the low ones lasting longest
  const MEMB = [[1, 1], [1.594, 0.55], [2.136, 0.38], [2.296, 0.3], [2.653, 0.22], [2.918, 0.16], [3.156, 0.12], [3.501, 0.09]];
  const ODAIKO = { modes: MEMB.map(([r, a], i) => [r, i ? a : 0.8, [0.34, 0.24, 0.18, 0.16, 0.13, 0.11, 0.09, 0.07][i]]), bend: 0.12, rise: 0.004,
    hit: [1800, 0.035, 0.5], shell: [180, 0.18, 0.25] };
  const NAGADO = { modes: MEMB.map(([r, a], i) => [r, a, [0.24, 0.17, 0.12, 0.11, 0.09, 0.08, 0.07, 0.06][i]]), bend: 0.08, rise: 0.003,
    hit: [2600, 0.025, 0.6], shell: [320, 0.1, 0.25] };
  // kettle drum: the air in the bowl pulls the modes near 1 : 1.5 : 2 : 2.5 : 3 (the "principal" sings), felt mallet
  const TIMP = { modes: [[1, 1, 0.6], [1.504, 0.6, 0.5], [1.742, 0.25, 0.3], [2.0, 0.35, 0.4], [2.44, 0.2, 0.25], [2.9, 0.12, 0.2], [0.55, 0.25, 0.12]],
    bend: 0.03, rise: 0.006, hit: [700, 0.03, 0.35], shell: null };
  // ---- the bass guitar: a plucked string (see above), muted at the note's end ----
  const bassBus = bus(on('bass') ? 0.2 : 0, 0.12);
  const bHP = ctx.createBiquadFilter(); bHP.type = 'highpass'; bHP.frequency.value = 35;
  const bLP = ctx.createBiquadFilter(); bLP.type = 'lowpass'; bLP.frequency.value = 2600; bLP.Q.value = 0.8;
  const drive = ctx.createWaveShaper(), curve = new Float32Array(1024);
  for (let i = 0; i < 1024; i++) { const x = i / 511.5 - 1; curve[i] = Math.tanh(1.8 * x) / Math.tanh(1.8); }
  drive.curve = curve; bHP.connect(drive).connect(bLP).connect(bassBus);
  function bass(t0, dur, m, vel) {
    t0 = at(t0) + rnd(-0.006, 0.006); if (t0 < 0) return;
    const SR = ctx.sampleRate, f = midi(m), N = Math.max(2, Math.round(SR / f)), L = Math.ceil(SR * (dur + 0.05));
    const line = new Float32Array(N); let y = 0;
    for (let i = 0; i < N; i++) { y += 0.3 * (rnd(-1, 1) - y); line[i] = y; }
    const P = Math.round(N * 0.2), ex = line.slice();
    for (let i = P; i < N; i++) line[i] = ex[i] - ex[i - P];                // plucked a fifth along: that harmonic gone
    const b = ctx.createBuffer(1, L, SR), d = b.getChannelData(0), damp = 0.9985 - 0.002 * (f / 200);
    let k = 0, peak = 1e-6;
    for (let i = 0; i < L; i++) {
      const k1 = (k + 1) % N; d[i] = line[k]; line[k] = damp * 0.5 * (line[k] + line[k1]); k = k1;
      if (i < N * 4) peak = Math.max(peak, Math.abs(d[i]));
    }
    const mute = Math.floor(SR * dur);                                     // the finger stops the string
    for (let i = 0; i < L; i++) d[i] = d[i] / peak * (i < mute ? 1 : Math.max(0, 1 - (i - mute) / (SR * 0.04)));
    const src = ctx.createBufferSource(); src.buffer = b;
    const g = ctx.createGain(); g.gain.value = vel * rnd(0.9, 1.05);
    src.connect(g).connect(bHP); src.start(t0);
  }
  const roll = (t0, t1, f0, v0, v1, pan, kind = TIMP, step = 0.072) => {  // single strokes, hand to hand, swelling
    for (let t = t0, i = 0; t < t1; t += step * rnd(0.92, 1.08), i++)
      drum(t, f0, v0 + (v1 - v0) * (t - t0) / (t1 - t0), kind, pan + (i % 2 ? 0.08 : -0.08));
  };

  function schedule() {
    const BEAT = 0.5, E8 = BEAT / 2, BAR = 4 * BEAT;
    // D minor through the long night; the veil going: B♭, F (lighter); the drift: Dm B♭ F C | Dm B♭ Gm A; today: D major
    const CH = { Dm: [50, 53, 57], Bb: [46, 50, 53], F: [53, 57, 60], C: [48, 52, 55], Gm: [55, 58, 62], A: [57, 61, 64], D: [50, 54, 57] };
    const PLAN = [[0, 'Dm'], [4, 'Dm'], [6, 'Bb'], [8, 'F'], [10, 'F'], [11.5, 'Dm'], [13, 'Bb'], [14.5, 'F'], [16, 'C'],
      [17, 'Gm'], [17.8, 'A'], [20, 'D']];
    const chordAt = t => { let k = 'Dm'; for (const [s, c] of PLAN) if (t >= s - 0.01) k = c; return k; };
    const HUSH = 18.6, LIGHT = 20.0, END = opts.T || 24.5;
    // loudness through the clip: low in the night, a swell as the veil goes, back down, one long rise through the drift
    const wave = t => t < 5 ? 0.15 : t < 9 ? 0.15 + 0.3 * (t - 5) / 4 : t < 11.5 ? 0.45 - 0.2 * (t - 9) / 2.5 : 0.25 + 0.75 * Math.min(1, (t - 11.5) / (HUSH - 11.5));
    // the figure (root, fifth, octave over and over, so it falls in threes across the bar), from the veil going on
    for (let t = 8, i = 0; t < HUSH - 0.05; t += E8, i++) {
      const d = wave(t), ch = CH[chordAt(t)], m = [ch[0], ch[0] + 7, ch[0] + 12][i % 3];
      organ(t, t + E8 * 0.9, m, d > 0.55 ? MID : FL, 0.08 + 0.22 * d, 1000 + 3000 * d, 0.01, 0.12);
      if (d > 0.5) organ(t, t + E8 * 0.9, m + 12, FL, 0.04 + 0.12 * (d - 0.5), 2500, 0.01, 0.12);
    }
    // held chords that breathe
    PLAN.forEach(([s, k], i) => {
      if (s >= LIGHT) return;
      const e = i + 1 < PLAN.length ? Math.min(PLAN[i + 1][0], HUSH) : HUSH, w = wave((s + e) / 2);
      for (const m of CH[k]) organ(s, e + 0.4, m + 12, w > 0.5 ? MID : FL, 0.07 + 0.2 * w, 800 + 2500 * w, Math.min(1.8, (e - s) * 0.5), 1.2);
    });
    // the night: one slow line in the middle register
    organ(0, 5.6, 62, FL, 0.1, 1200, 2.5, 1.5); organ(2.8, 5.6, 65, FL, 0.08, 1200, 1.5, 1.2);
    // a high line over the rise
    organ(15.0, 16.9, 77, FL, 0.13, 3000, 1.2, 0.6); organ(17.0, HUSH, 79, FL, 0.13, 3000, 0.6, 0.4);
    // the hush: the figure stops, one high note hangs on into the light
    organ(HUSH - 0.1, LIGHT + 1.6, 81, FL, 0.12, 2500, 0.3, 1.0);
    // today: D major breathes in over ~2.5 s, full, and stays
    for (const m of [50, 54, 57, 62, 66, 69]) organ(LIGHT - 0.6, END, m, FULL, 0.26, 3600, 2.6, 1.5);
    organ(LIGHT + 1.0, END, 78, FL, 0.14, 3200, 1.6, 1.2);

    if (V === 'taiko') {
      // a heartbeat in the night, far off; then the ensemble wakes through the drift and grows; silent for the hush;
      // into the light only a soft swell of the big drum's roll
      for (let t = 0.6; t < 6; t += 2) { drum(t, 50, 0.35, ODAIKO, -0.1); drum(t + 0.32, 50, 0.22, ODAIKO, -0.1); }
      for (let t = 6.6; t < 11.5; t += BAR) drum(t, 50, 0.45, ODAIKO, -0.1);
      for (let b = 11.5; b < HUSH - 0.1; b += BAR) {
        const k = Math.min(1, (b - 11.5) / (HUSH - 11.5));
        drum(b, 50, 0.6 + 0.4 * k, ODAIKO, -0.1); drum(b + 0.012, 52, 0.4 + 0.3 * k, ODAIKO, 0.2);
        // 3 + 3 + 2 in eighths on the middle drums, more of it as it grows
        const pat = k < 0.35 ? [3, 6] : [1, 3, 4, 6, 7];
        for (const e of pat) drum(b + e * E8, 96, (e === 3 || e === 6 ? 0.35 : 0.2) + 0.35 * k, NAGADO, e % 2 ? 0.35 : -0.3);
        if (k > 0.6) for (let s = 0; s < 8; s++) drum(b + s * E8, 205, 0.06 + 0.06 * (s % 3 === 0), NAGADO, 0.5);
      }
      roll(LIGHT - 1.0, LIGHT + 2.4, 50, 0.04, 0.3, 0, ODAIKO, 0.11);
      drum(LIGHT + 2.5, 50, 0.45, ODAIKO, 0);
    } else if (V === 'timp') {
      // kettle drums tuned to D and A: single strokes in the night, a figure in the drift, a long roll swelling into the light
      for (let t = 0.6; t < 6; t += 2) drum(t, midi(38), 0.35, TIMP, -0.2);
      roll(4.4, 6.2, midi(33), 0.03, 0.18, 0.2);
      for (let t = 6.6; t < 11.5; t += BAR) drum(t, midi(38), 0.4, TIMP, -0.2);
      for (let b = 11.5; b < HUSH - 0.1; b += BAR) {
        const k = Math.min(1, (b - 11.5) / (HUSH - 11.5));
        for (const [e, m] of [[0, 38], [3, 33], [6, 38]]) drum(b + e * E8, midi(m), 0.35 + 0.45 * k, TIMP, m === 38 ? -0.2 : 0.2);
        if (k > 0.5) for (const e of [1.5, 4.5]) drum(b + e * E8, midi(33), 0.2 + 0.25 * k, TIMP, 0.2);
      }
      roll(LIGHT - 1.4, LIGHT + 2.4, midi(38), 0.03, 0.3, -0.2);
      drum(LIGHT + 2.5, midi(38), 0.4, TIMP, -0.2);
    }
    if (BASS) {
      // the bass: none in the night; long notes on the roots as the veil goes; through the drift it drives with the
      // drums (3 + 3 + 2, the accents with them), growing; silent for the hush; long D's in the light
      const ROOT = { Dm: 38, Bb: 34, F: 41, C: 36, Gm: 43, A: 45, D: 38 };
      for (let t = 6.6; t < 11.5; t += BAR) bass(t, BAR * 0.95, ROOT[chordAt(t + 0.05)], 0.35);
      for (let b = 11.5; b < HUSH - 0.1; b += BAR) {
        const kk = Math.min(1, (b - 11.5) / (HUSH - 11.5));
        for (let e = 0; e < 8; e++) {
          const t = b + e * E8; if (t >= HUSH - 0.1) break;
          const acc = e === 0 || e === 3 || e === 6, r = ROOT[chordAt(t + 0.02)];
          if (kk < 0.3 && !acc) continue;
          bass(t, acc && kk < 0.3 ? E8 * 2.8 : E8 * 0.8, e === 6 && kk > 0.5 ? r + 12 : e === 7 ? r + 7 : r, (acc ? 0.5 : 0.3) + 0.35 * kk);
        }
      }
      for (let t = LIGHT + 2.5; t < END - 0.5; t += BAR) bass(t, BAR * 0.95, 38, 0.4);
    }
  }
  return { output: master, start() { schedule(); }, scheduleUntil() {} };
}
