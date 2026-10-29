// Renders the organ sketches of music_variants.js offline  ->  work/moonfall/music_<variant>.wav  (16 s, stereo, 44.1 kHz)
//   node scenes/moonfall/sound_preview.js [1 2 3]
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');

const HERE = __dirname, WORK = path.resolve(HERE, '../../work/moonfall');
const T = 16;
(async () => {
  const code = fs.readFileSync(path.join(HERE, 'music_variants.js'), 'utf8');
  const which = process.argv.slice(2).map(Number).filter(Boolean);
  const br = await chromium.launch();
  const p = await br.newPage();
  fs.mkdirSync(WORK, { recursive: true });
  for (const v of which.length ? which : [1, 2, 3]) {
    const out = await p.evaluate(async ({ code, v, T }) => {
      eval(code + '; window.__mk = createMoonMusic;');
      const SR = 44100;
      const ctx = new OfflineAudioContext(2, Math.ceil(SR * T), SR);
      const g = ctx.createGain(); g.connect(ctx.destination);
      g.gain.setValueAtTime(0, 0); g.gain.linearRampToValueAtTime(0.9, 1.0);
      g.gain.setValueAtTime(0.9, T - 2.2); g.gain.linearRampToValueAtTime(0, T - 0.2);
      window.__mk(ctx, g, v).start();
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
    }, { code, v, T });
    fs.writeFileSync(path.join(WORK, `music_${v}.wav`), Buffer.from(out, 'base64'));
    console.log(`music_${v}.wav written`);
  }
  await br.close();
})();
