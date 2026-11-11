// node render_music.js [out.wav] — renders music.js offline (48 kHz stereo, 378.53 s) in headless Chromium.
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');
let pw; try { pw = require('playwright'); } catch (e) { pw = require(execSync('npm root -g').toString().trim() + '/playwright'); }
const outFile = process.argv[2] || path.join(__dirname, 'music.wav');
const T = JSON.parse(fs.readFileSync(path.join(__dirname, 'timeline.json'), 'utf8')).duration;
(async () => {
  const br = await pw.chromium.launch(), p = await br.newPage();
  const code = fs.readFileSync(path.join(__dirname, 'music.js'), 'utf8');
  const b64 = await p.evaluate(async ({ code, T }) => {
    eval(code + '; window.__mk = createSceneMusic;');
    const SR = 48000, N = Math.round(SR * T), SL = 40, TAIL = 14;
    const L = new Float32Array(N), R = new Float32Array(N);
    for (let a = 0; a < T; a += SL) {
      const len = Math.min(T - a + 0, SL + TAIL), ctx = new OfflineAudioContext(2, Math.round(SR * len), SR);
      const g = ctx.createGain(); g.connect(ctx.destination);
      const piece = window.__mk(ctx, g, { from: a, to: a + SL }); piece.start(); piece.scheduleUntil(T);
      const buf = await ctx.startRendering(), l = buf.getChannelData(0), r = buf.getChannelData(1), o = Math.round(a * SR);
      for (let i = 0; i < l.length && o + i < N; i++) { L[o + i] += l[i]; R[o + i] += r[i]; }
    }
    const n = N;
    for (let i = 0; i < 2400; i++) { L[i] *= i / 2400; R[i] *= i / 2400; }
    const fo = Math.round(3 * SR); for (let i = 0; i < fo; i++) { const k = (1 - i / fo); L[N - fo + i] *= k; R[N - fo + i] *= k; }
    const ab = new ArrayBuffer(44 + n * 4), dv = new DataView(ab);
    const w = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
    w(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); w(8, 'WAVEfmt '); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, 2, true); dv.setUint32(24, SR, true); dv.setUint32(28, SR * 4, true);
    dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, 'data'); dv.setUint32(40, n * 4, true);
    for (let i = 0; i < n; i++) { dv.setInt16(44 + i * 4, Math.max(-1, Math.min(1, L[i])) * 32767, true); dv.setInt16(46 + i * 4, Math.max(-1, Math.min(1, R[i])) * 32767, true); }
    let bin = ''; const u8 = new Uint8Array(ab);
    for (let i = 0; i < u8.length; i += 8192) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 8192));
    return btoa(bin);
  }, { code, T });
  fs.writeFileSync(outFile, Buffer.from(b64, 'base64'));
  console.log('written', outFile);
  await br.close();
})();
