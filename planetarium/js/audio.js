// Небозвід — sound of the Sun, planet voices and the background music.
// Plain scripts sharing one scope; index.html loads them in order.
"use strict";

/* ---------- Sound of the Sun ---------- */
// Space is silent. What plays here is a sonification of real data:
// the hum is built from the Sun's acoustic p-modes (large separation ≈135 µHz, peak ≈3.1 mHz,
//   periods around 5 minutes), sped up 42 000× into the audible range, as in Stanford/SOHO sonifications;
const SPEEDUP = 42000;
// Voices of the planets that have real recordings behind them, synthesised after their character:
//  Mars    — wind on Perseverance's microphones: muffled, because the thin CO2 air swallows high pitches;
//  Jupiter — the hiss of plasma waves around Jupiter recorded by Juno (without the chorus chirps);
//  Saturn  — Cassini's kilometric radio emission: slow, wavering whoops sliding downwards;
//  Earth   — the soft background noise of Earth's magnetosphere (without chorus chirps or whistlers).
function createPlanetVoices(ctx, dest) {
  const white = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate), brown = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate);
  const wd = white.getChannelData(0), bd = brown.getChannelData(0);
  let last = 0;
  for (let i = 0; i < wd.length; i++) {
    wd[i] = Math.random() * 2 - 1;
    last = (last + 0.02 * wd[i]) / 1.02; bd[i] = last * 3.5;
  }
  const loop = (buf, node) => { const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true; s.connect(node); s.start(); return s; };
  const rnd = (a, b) => a + Math.random() * (b - a);

  // A short tone gliding from f0 to f1 (exponential), with a soft envelope.
  function glide(bus, t, f0, f1, dur, amp, vibrato) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(f0, t);
    o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    if (vibrato) {
      const lfo = ctx.createOscillator(), depth = ctx.createGain();
      lfo.frequency.value = vibrato[0]; depth.gain.value = vibrato[1];
      lfo.connect(depth).connect(o.frequency);
      lfo.start(t); lfo.stop(t + dur + 0.1);
    }
    const att = Math.min(0.25, dur * 0.3);
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(amp, t + att);
    g.gain.exponentialRampToValueAtTime(0.0005, t + dur);
    o.connect(g).connect(bus);
    o.start(t); o.stop(t + dur + 0.05);
  }

  const voices = {};
  function voice(id, setup, events) {
    const g = ctx.createGain();
    g.gain.value = 0;
    g.connect(dest);
    const bus = ctx.createGain();
    bus.connect(g);
    setup(bus);
    voices[id] = { g, bus, events, next: 0, level: 0 };
  }

  voice("mars", bus => {
    const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 260; lp.Q.value = 0.7;
    const gust = ctx.createGain(); gust.gain.value = 0.15;
    loop(brown, lp); lp.connect(gust).connect(bus);
    bus.gust = gust; bus.lp = lp;
  }, (v, t) => {
    v.bus.gust.gain.setTargetAtTime(rnd(0.06, 0.32), t, rnd(0.6, 1.8));
    v.bus.lp.frequency.setTargetAtTime(rnd(170, 340), t, 1.5);
    return rnd(1.5, 4.5);
  });

  voice("jupiter", bus => {
    const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 420; bp.Q.value = 0.6;
    const swell = ctx.createGain(); swell.gain.value = 0.14;
    loop(white, bp); bp.connect(swell).connect(bus);
    bus.swell = swell; bus.bp = bp;
  }, (v, t) => {
    // Only the plasma-wave hiss, breathing slowly (the chirps are left out).
    v.bus.swell.gain.setTargetAtTime(rnd(0.08, 0.18), t, rnd(1, 2.5));
    v.bus.bp.frequency.setTargetAtTime(rnd(340, 520), t, 2);
    return rnd(2, 4.5);
  });

  voice("saturn", bus => {
    const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 450; bp.Q.value = 1.2;
    const bed = ctx.createGain(); bed.gain.value = 0.06;
    loop(white, bp); bp.connect(bed).connect(bus);
  }, (v, t) => {
    const f0 = rnd(650, 1100);
    glide(v.bus, t, f0, f0 * rnd(0.3, 0.55), rnd(1.6, 3.2), 0.08, [rnd(3, 7), rnd(10, 30)]);
    return rnd(0.7, 1.6);
  });

  voice("earth", bus => {
    const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 600; bp.Q.value = 0.5;
    const swell = ctx.createGain(); swell.gain.value = 0.15;
    loop(white, bp); bp.connect(swell).connect(bus);
    bus.swell = swell; bus.bp = bp;
  }, (v, t) => {
    // Soft magnetospheric background only (no chirps or whistlers).
    v.bus.swell.gain.setTargetAtTime(rnd(0.09, 0.2), t, rnd(1.2, 2.5));
    v.bus.bp.frequency.setTargetAtTime(rnd(480, 720), t, 2);
    return rnd(2, 5);
  });

  return {
    // level per voice (0..1); events are only scheduled for voices that can be heard.
    set(levels) {
      for (const id in voices) {
        const v = voices[id], l = levels[id] || 0;
        if (Math.abs(l - v.level) > 0.01) { v.level = l; v.g.gain.setTargetAtTime(l, ctx.currentTime, 0.4); }
      }
    },
    schedule(until) {
      for (const id in voices) {
        const v = voices[id];
        if (v.level < 0.02) { v.next = Math.max(v.next, until); continue; }
        if (v.next < ctx.currentTime) v.next = ctx.currentTime;
        while (v.next < until) v.next += v.events(v, v.next);
      }
    },
    _voices: voices,
  };
}

function createSunAudio() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  const ctx = new Ctx();
  const master = ctx.createGain();
  master.gain.value = 0;
  const comp = ctx.createDynamicsCompressor();
  master.connect(comp).connect(ctx.destination);

  // Acoustic modes of degree l = 0, 1, 2: ν ≈ Δν (n + l/2 + ε) − l(l+1)·D0, weighted by a Gaussian around ν_max.
  const dNu = 135e-6, eps = 1.45, D0 = 1.5e-6, nuMax = 3.09e-3, width = 0.62e-3;
  // The Sun's hum has its own level (distance to the Sun); master is only on/off, so planet voices are independent.
  const sunBus = ctx.createGain();
  sunBus.gain.value = 0;
  sunBus.connect(master);
  const hum = ctx.createGain();
  hum.gain.value = 0.9;
  hum.connect(sunBus);
  const modes = [];
  for (let n = 13; n <= 30; n++) {
    for (let l = 0; l <= 2; l++) {
      const nu = dNu * (n + l / 2 + eps) - l * (l + 1) * D0;
      const w = Math.exp(-Math.pow((nu - nuMax) / width, 2)) * (l === 1 ? 1 : l === 0 ? 0.85 : 0.6);
      if (w < 0.04) continue;
      const osc = ctx.createOscillator();
      osc.frequency.value = nu * SPEEDUP;
      const g = ctx.createGain();
      g.gain.value = 0;
      osc.connect(g).connect(hum);
      osc.start();
      modes.push({ g, w });
    }
  }
  const norm = 0.28 / Math.sqrt(modes.reduce((s, m) => s + m.w * m.w, 0));

  // Granulation background: the Sun's low-frequency "noise floor", as soft filtered rumble.
  const noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 4, ctx.sampleRate);
  const data = noiseBuf.getChannelData(0);
  let last = 0;
  for (let i = 0; i < data.length; i++) { last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02; data[i] = last * 3.5; }
  const rumble = ctx.createBufferSource();
  rumble.buffer = noiseBuf; rumble.loop = true;
  const rumbleLp = ctx.createBiquadFilter();
  rumbleLp.type = "lowpass"; rumbleLp.frequency.value = 220;
  const rumbleGain = ctx.createGain();
  rumbleGain.gain.value = 0.25;
  rumble.connect(rumbleLp).connect(rumbleGain).connect(sunBus);
  rumble.start();

  // Modes are excited at random by convection and die away: let each amplitude wander.
  function excite() {
    const now = ctx.currentTime;
    for (const m of modes) m.g.gain.setTargetAtTime(m.w * norm * (0.25 + Math.random() * 1.1), now, 1.2);
  }
  const voices = createPlanetVoices(ctx, master);
  excite();
  const timer = setInterval(() => { excite(); voices.schedule(ctx.currentTime + 1.5); }, 900);

  let on = false, level = 0;
  return {
    get on() { return on; },
    async toggle() {
      on = !on;
      if (on) await ctx.resume();
      master.gain.setTargetAtTime(on ? 1 : 0, ctx.currentTime, 0.3);
      if (!on) setTimeout(() => { if (!on) ctx.suspend(); }, 1500);
      return on;
    },
    setLevel(v) {
      if (Math.abs(v - level) < 0.01) return;
      level = v;
      sunBus.gain.setTargetAtTime(level, ctx.currentTime, 0.25);
    },
    setVoices(levels) { voices.set(levels); },
    dispose() { clearInterval(timer); ctx.close(); },
  };
}
let sunAudio = null;

/* ---------- Background music ---------- */
// An original ambient piece generated in the browser: a soft organ pad over a low pedal note, a slow bell arpeggio
// with echoes, and a large reverb. Chords: A minor → F → C → G, each held for two bars. No samples, no quotations.
function createAmbientMusic(ctx, dest) {
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const CHORDS = [[45, 48, 52, 57], [41, 45, 48, 52], [48, 52, 55, 60], [43, 47, 50, 55]];
  const BEAT = 60 / 64 / 2;                     // an eighth note at 64 bpm
  const BAR = BEAT * 8, CHORD_LEN = BAR * 2;

  const out = ctx.createGain();
  out.gain.value = 1;
  out.connect(dest);

  // Reverb from a generated impulse: 3.5 s of decaying stereo noise.
  const len = Math.floor(ctx.sampleRate * 3.5), ir = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 3);
  }
  const verb = ctx.createConvolver();
  verb.buffer = ir;
  const wet = ctx.createGain(); wet.gain.value = 0.55;
  verb.connect(wet).connect(out);

  // Pad: organ-like tone (a few soft harmonics), low-passed with a slowly breathing cutoff.
  const organ = ctx.createPeriodicWave(new Float32Array([0, 1, 0.5, 0.3, 0.22, 0.1, 0.07, 0.04]), new Float32Array(8));
  const padBus = ctx.createGain(); padBus.gain.value = 0.05;
  const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 1400; lp.Q.value = 0.4;
  const lfo = ctx.createOscillator(), lfoAmt = ctx.createGain();
  lfo.frequency.value = 0.05; lfoAmt.gain.value = 500;
  lfo.connect(lfoAmt).connect(lp.frequency);
  lfo.start();
  padBus.connect(lp);
  lp.connect(out);
  lp.connect(verb);

  // Bells: sine with a soft overtone, echoed by a dotted-eighth delay into the reverb.
  const bellBus = ctx.createGain(); bellBus.gain.value = 0.045;
  const delay = ctx.createDelay(2); delay.delayTime.value = BEAT * 1.5;
  const fb = ctx.createGain(); fb.gain.value = 0.33;
  bellBus.connect(out);
  bellBus.connect(delay); delay.connect(fb).connect(delay);
  delay.connect(verb);
  bellBus.connect(verb);

  function padNote(m, t0, t1) {
    for (const cents of [-4, 4]) {
      const o = ctx.createOscillator();
      o.setPeriodicWave(organ);
      o.frequency.value = midi(m);
      o.detune.value = cents;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t0);
      g.gain.linearRampToValueAtTime(1, t0 + 3);
      g.gain.setValueAtTime(1, t1);
      g.gain.linearRampToValueAtTime(0, t1 + 3.5);
      o.connect(g).connect(padBus);
      o.start(t0); o.stop(t1 + 3.6);
    }
  }
  function bell(m, t) {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(1, t + 0.015);
    g.gain.exponentialRampToValueAtTime(0.001, t + 2.8);
    g.connect(bellBus);
    for (const [mul, amp] of [[1, 1], [2.0, 0.18]]) {
      const o = ctx.createOscillator(), a = ctx.createGain();
      o.frequency.value = midi(m) * mul;
      a.gain.value = amp;
      o.connect(a).connect(g);
      o.start(t); o.stop(t + 2.9);
    }
  }

  const ARP = [0, 1, 2, 3, 2, 1, 3, 1];
  let nextChordAt = 0, chordIndex = 0;
  // Schedule everything that starts before `until` (seconds on the audio clock).
  function scheduleUntil(until) {
    while (nextChordAt < until) {
      const chord = CHORDS[chordIndex % CHORDS.length], t0 = nextChordAt, t1 = t0 + CHORD_LEN;
      for (const m of chord) padNote(m, t0, t1);
      padNote(chord[0] - 12, t0, t1);                               // pedal
      if (chordIndex > 0) {                                         // bells join after the first chord
        for (let i = 0; i < 16; i++) {
          if (Math.random() < 0.3) continue;                        // leave gaps so it breathes
          bell(chord[ARP[i % 8]] + 24, t0 + i * BEAT);
        }
      }
      chordIndex++;
      nextChordAt += CHORD_LEN;
    }
  }
  return {
    output: out,
    start(t) { nextChordAt = t; chordIndex = 0; scheduleUntil(t + 1); },
    scheduleUntil,
  };
}

/* ---------- Tour music ---------- */
// Original cinematic piece for the guided tour: low strings that swell with each chord, a deep bass, a soft
// eighth-note ostinato that joins after the opening, distant low drums and, later, a high choir-like line.
// D minor: Dm → B♭ → F → C, two bars each, at 72 bpm. It grows over the first minute and breathes back every
// twelve chords. No samples, no quotations.
function createCinematicMusic(ctx, dest) {
  const midi = m => 440 * Math.pow(2, (m - 69) / 12);
  const CHORDS = [[50, 53, 57, 62], [46, 50, 53, 58], [45, 48, 53, 57], [43, 48, 52, 55]];
  const BASS = [38, 34, 41, 36];
  const BEAT = 60 / 72 / 2, CHORD_LEN = BEAT * 16;

  const out = ctx.createGain(); out.gain.value = 1; out.connect(dest);
  const len = Math.floor(ctx.sampleRate * 4.5), ir = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);
  }
  const verb = ctx.createConvolver(); verb.buffer = ir;
  const wet = ctx.createGain(); wet.gain.value = 0.6;
  verb.connect(wet).connect(out);
  const bus = (gain, dry = 1) => {
    const g = ctx.createGain(); g.gain.value = gain;
    if (dry) g.connect(out);
    g.connect(verb);
    return g;
  };
  const strings = bus(0.03), bass = bus(0.085), pluck = bus(0.028), drum = bus(0.11, 1), choir = bus(0.016, 0);
  const delay = ctx.createDelay(2); delay.delayTime.value = BEAT * 3;
  const fb = ctx.createGain(); fb.gain.value = 0.3;
  pluck.connect(delay); delay.connect(fb).connect(delay); delay.connect(verb);

  // strings: three detuned saws through a low-pass that opens and closes over the chord
  function string(m, t0, t1, bright) {
    const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.Q.value = 0.6;
    lp.frequency.setValueAtTime(350, t0);
    lp.frequency.linearRampToValueAtTime(700 + 900 * bright, (t0 + t1) / 2);
    lp.frequency.linearRampToValueAtTime(400, t1 + 2);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(1, t0 + 2.5);
    g.gain.setValueAtTime(1, t1);
    g.gain.linearRampToValueAtTime(0, t1 + 3);
    lp.connect(g).connect(strings);
    for (const cents of [-8, 0, 7]) {
      const o = ctx.createOscillator(); o.type = "sawtooth";
      o.frequency.value = midi(m); o.detune.value = cents;
      o.connect(lp); o.start(t0); o.stop(t1 + 3.1);
    }
  }
  function low(m, t0, t1) {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(1, t0 + 1.5);
    g.gain.setValueAtTime(1, t1);
    g.gain.linearRampToValueAtTime(0, t1 + 2.5);
    g.connect(bass);
    for (const [mul, type, amp] of [[1, "sine", 1], [2, "triangle", 0.25]]) {
      const o = ctx.createOscillator(), a = ctx.createGain();
      o.type = type; o.frequency.value = midi(m) * mul; a.gain.value = amp;
      o.connect(a).connect(g); o.start(t0); o.stop(t1 + 2.6);
    }
  }
  function note(m, t, vel) {
    const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 2200;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vel, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.001, t + 0.9);
    const o = ctx.createOscillator(); o.type = "triangle"; o.frequency.value = midi(m);
    o.connect(lp).connect(g).connect(pluck); o.start(t); o.stop(t + 1);
  }
  // a soft, far-away low drum: a falling sine
  function boom(t) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(78, t);
    o.frequency.exponentialRampToValueAtTime(38, t + 0.9);
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(1, t + 0.04);
    g.gain.exponentialRampToValueAtTime(0.001, t + 2.4);
    o.connect(g).connect(drum); o.start(t); o.stop(t + 2.5);
  }
  function voice(m, t0, t1) {
    const o = ctx.createOscillator(), vib = ctx.createOscillator(), va = ctx.createGain(), g = ctx.createGain();
    o.frequency.value = midi(m);
    vib.frequency.value = 4.6; va.gain.value = 3.5;
    vib.connect(va).connect(o.frequency);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(1, t0 + 4);
    g.gain.setValueAtTime(1, t1 - 1);
    g.gain.linearRampToValueAtTime(0, t1 + 2);
    o.connect(g).connect(choir);
    o.start(t0); vib.start(t0); o.stop(t1 + 2.1); vib.stop(t1 + 2.1);
  }

  const PAT = [0, 2, 1, 2, 3, 2, 1, 2];
  let nextChordAt = 0, chordIndex = 0;
  function scheduleUntil(until) {
    while (nextChordAt < until) {
      const k = chordIndex % 4, part = chordIndex % 12;   // 0–1 opening, 2–3 pulse, 4–11 full, then again
      const chord = CHORDS[k], t0 = nextChordAt, t1 = t0 + CHORD_LEN;
      const bright = part < 2 ? 0.2 : part < 4 ? 0.5 : 1;
      for (const m of chord) string(m, t0, t1, bright);
      low(BASS[k], t0, t1);
      if (part >= 2) {
        const vel = part < 4 ? 0.6 : 1;
        for (let i = 0; i < 16; i++) note(chord[PAT[i % 8]] + 12, t0 + i * BEAT, vel * (i % 4 === 0 ? 1 : 0.7));
      }
      if (part >= 4) { boom(t0); if (part >= 6) boom(t0 + BEAT * 8); }
      if (part >= 6) voice(chord[3] + 12, t0, t1);
      chordIndex++;
      nextChordAt += CHORD_LEN;
    }
  }
  return {
    output: out,
    start(t) { nextChordAt = t; chordIndex = 0; scheduleUntil(t + 1); },
    scheduleUntil,
  };
}

// Page wiring: own audio context, gentle fade in/out, quieter while the Sun's hum is loud.
let music = null;
function createMusicPlayer(makePiece = createAmbientMusic) {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  const ctx = new Ctx();
  const master = ctx.createGain();
  master.gain.value = 0;
  master.connect(ctx.destination);
  const piece = makePiece(ctx, master);
  let on = false, timer = 0, duck = 1;
  const level = () => 0.9 * duck;
  return {
    get on() { return on; },
    async toggle() {
      on = !on;
      if (on) {
        await ctx.resume();
        piece.start(ctx.currentTime + 0.1);
        timer = setInterval(() => piece.scheduleUntil(ctx.currentTime + 2), 400);
        master.gain.cancelScheduledValues(ctx.currentTime);
        master.gain.setTargetAtTime(level(), ctx.currentTime, 1.5);
      } else {
        clearInterval(timer);
        master.gain.cancelScheduledValues(ctx.currentTime);
        master.gain.setTargetAtTime(0, ctx.currentTime, 0.8);
        setTimeout(() => { if (!on) ctx.suspend(); }, 4000);
      }
      return on;
    },
    setDuck(d) {
      if (Math.abs(d - duck) < 0.02) return;
      duck = d;
      if (on) master.gain.setTargetAtTime(level(), ctx.currentTime, 0.5);
    },
  };
}
