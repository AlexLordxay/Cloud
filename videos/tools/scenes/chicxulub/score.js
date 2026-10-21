// Renders the score (music.js) offline, in a headless page's OfflineAudioContext, to a WAV.
//   node scenes/chicxulub/score.js <variant> <seconds> [T0] [organ|drums]   -> work/chicxulub/score_<variant>[_only].wav
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const [v = 'taiko', T = '22.5', T0 = '0', only = ''] = process.argv.slice(2);
const WORK = path.resolve(__dirname, '../../work/chicxulub');

(async () => {
  const code = fs.readFileSync(path.join(__dirname, 'music.js'), 'utf8');
  const br = await chromium.launch(), p = await br.newPage();
  p.on('pageerror', e => console.log('pageerror:', e.message));
  const b64 = await p.evaluate(async ({ code, v, T, T0, only }) => {
    eval(code + '; window.__mk = createSceneMusic;');
    const SR = 44100, ctx = new OfflineAudioContext(2, Math.ceil(SR * T), SR);
    const g = ctx.createGain(); g.connect(ctx.destination);
    g.gain.setValueAtTime(0, 0); g.gain.linearRampToValueAtTime(0.9, 0.8);
    g.gain.setValueAtTime(0.9, T - 1.5); g.gain.linearRampToValueAtTime(0, T - 0.05);
    window.__mk(ctx, g, { v, T0, only, T }).start();
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
  }, { code, v, T: +T, T0: +T0, only });
  fs.mkdirSync(WORK, { recursive: true });
  fs.writeFileSync(path.join(WORK, `score_${v}${only ? '_' + only : ''}.wav`), Buffer.from(b64, 'base64'));
  console.log(`score_${v}${only ? '_' + only : ''}.wav`);
  await br.close();
})();
