// Renders the soundtrack offline: the site's own ambient music, plus (optionally) a planet's voice during a window.
//
//   node audio.js <scene>        -> work/<scene>/audio.wav
//
// The music and voices are taken straight from the site (planetarium/js/audio.js), so the video sounds exactly like the site.
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');

const TOOLS = __dirname, SITE = path.resolve(TOOLS, '../../planetarium');
const name = process.argv[2];
if (!name) { console.log('usage: node audio.js <scene>'); process.exit(1); }
const cfg = JSON.parse(fs.readFileSync(path.join(TOOLS, 'scenes', name, 'scene.json'), 'utf8'));
const WORK = path.join(TOOLS, 'work', name);

// Source of a top-level function in the site: from "function NAME(" to the closing brace at column 0.
function fnSource(src, fname) {
  const i = src.indexOf('\nfunction ' + fname + '(');
  if (i < 0) throw new Error('not found in the site: ' + fname);
  const j = src.indexOf('\n}\n', i);
  return src.slice(i + 1, j + 2);
}

(async () => {
  const site = fs.readFileSync(path.join(SITE, 'js/audio.js'), 'utf8');
  const code = fnSource(site, 'createAmbientMusic') + '\n' + fnSource(site, 'createPlanetVoices');
  const br = await chromium.launch();
  const p = await br.newPage();
  const out = await p.evaluate(async ({ code, T, a }) => {
    eval(code + '; window.__mk = createAmbientMusic; window.__pv = createPlanetVoices;');
    const SR = 44100;
    const ctx = new OfflineAudioContext(2, Math.ceil(SR * T), SR);
    const g = ctx.createGain(); g.connect(ctx.destination);
    g.gain.setValueAtTime(0, 0); g.gain.linearRampToValueAtTime(0.9, 2.0);
    g.gain.setValueAtTime(0.9, T - 4); g.gain.linearRampToValueAtTime(0, T - 0.3);
    const piece = window.__mk(ctx, g);
    piece.start(0.05); piece.scheduleUntil(T);
    if (a && a.voice) {
      // A planet's voice (synthesised after real recordings), faded in and out over the given window.
      const vg = ctx.createGain(); vg.connect(ctx.destination);
      const pv = window.__pv(ctx, vg), v = pv._voices[a.voice];
      v.level = 1; v.g.gain.value = 1;
      vg.gain.setValueAtTime(0, 0); vg.gain.setValueAtTime(0, a.voiceIn[0]); vg.gain.linearRampToValueAtTime(a.voiceLevel, a.voiceIn[1]);
      vg.gain.setValueAtTime(a.voiceLevel, a.voiceOut[0]); vg.gain.linearRampToValueAtTime(0, a.voiceOut[1]);
      pv.schedule(a.voiceOut[1] + 1.5);
    }
    if (a && a.song) {
      // The comet's "song": Rosetta's magnetometer heard 40–50 mHz oscillations around 67P; sped up, they sound like
      // soft clicks and whistles. Synthesised in that spirit: short gliding chirps through a band-pass, with an echo.
      const sg = ctx.createGain(); sg.connect(ctx.destination);
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 520; bp.Q.value = 0.9;
      const dl = ctx.createDelay(1); dl.delayTime.value = 0.23; const fb = ctx.createGain(); fb.gain.value = 0.35;
      bp.connect(sg); bp.connect(dl); dl.connect(fb).connect(dl); dl.connect(sg);
      const [s0, s1] = a.song, lvl = a.songLevel || 0.5;
      sg.gain.setValueAtTime(0, 0); sg.gain.setValueAtTime(0, s0); sg.gain.linearRampToValueAtTime(lvl, s0 + 1.5);
      sg.gain.setValueAtTime(lvl, s1 - 1.5); sg.gain.linearRampToValueAtTime(0, s1);
      let x = s0;
      while (x < s1) {
        const o = ctx.createOscillator(), g2 = ctx.createGain();
        const f0 = 260 + Math.random() * 520, f1 = f0 * (0.6 + Math.random() * 0.9), d = 0.07 + Math.random() * 0.22;
        o.type = Math.random() < 0.3 ? 'triangle' : 'sine';
        o.frequency.setValueAtTime(f0, x); o.frequency.exponentialRampToValueAtTime(f1, x + d);
        g2.gain.setValueAtTime(0, x); g2.gain.linearRampToValueAtTime(0.35 + Math.random() * 0.4, x + 0.012); g2.gain.exponentialRampToValueAtTime(0.001, x + d);
        o.connect(g2).connect(bp); o.start(x); o.stop(x + d + 0.02);
        x += 0.05 + Math.random() * Math.random() * 0.35;
      }
    }
    const buf = await ctx.startRendering();
    const L = buf.getChannelData(0), R = buf.getChannelData(1), n = L.length;
    const ab = new ArrayBuffer(44 + n * 4), dv = new DataView(ab);
    const w = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
    w(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); w(8, 'WAVEfmt '); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, 2, true); dv.setUint32(24, SR, true); dv.setUint32(28, SR * 4, true);
    dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, 'data'); dv.setUint32(40, n * 4, true);
    for (let i = 0; i < n; i++) { dv.setInt16(44 + i * 4, Math.max(-1, Math.min(1, L[i])) * 32767, true); dv.setInt16(46 + i * 4, Math.max(-1, Math.min(1, R[i])) * 32767, true); }
    let bin = ''; const u8 = new Uint8Array(ab);
    for (let i = 0; i < u8.length; i += 8192) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 8192));
    return btoa(bin);
  }, { code, T: cfg.duration + 1, a: cfg.audio || null });
  fs.mkdirSync(WORK, { recursive: true });
  fs.writeFileSync(path.join(WORK, 'audio.wav'), Buffer.from(out, 'base64'));
  console.log('audio.wav written');
  await br.close();
})();
