// The site's own music (planetarium/js/audio.js: createAmbientMusic, or createCinematicMusic as on the tours), rendered
// offline for T seconds, faded in and out:   node scenes/chicxulub/site_music.js cinematic|ambient <seconds> <out.wav>
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const [kind, T, out] = [process.argv[2], +process.argv[3], process.argv[4]];
const site = fs.readFileSync(path.resolve(__dirname, '../../../../planetarium/js/audio.js'), 'utf8');
const fn = kind === 'cinematic' ? 'createCinematicMusic' : 'createAmbientMusic';
const i = site.indexOf('\nfunction ' + fn + '('), code = site.slice(i + 1, site.indexOf('\n}\n', i) + 2);
(async () => {
  const br = await chromium.launch(), p = await br.newPage();
  const b64 = await p.evaluate(async ({ code, fn, T }) => {
    eval(code + '; window.__mk = ' + fn + ';');
    const SR = 44100, ctx = new OfflineAudioContext(2, Math.ceil(SR * T), SR);
    const g = ctx.createGain(); g.connect(ctx.destination);
    g.gain.setValueAtTime(0, 0); g.gain.linearRampToValueAtTime(0.9, 1.5); g.gain.setValueAtTime(0.9, T - 2); g.gain.linearRampToValueAtTime(0, T - 0.05);
    const m = window.__mk(ctx, g); m.start(0.05, 0); m.scheduleUntil(T);
    const buf = await ctx.startRendering(), L = buf.getChannelData(0), R = buf.getChannelData(1), n = L.length;
    const ab = new ArrayBuffer(44 + n * 4), dv = new DataView(ab), w = (o, s) => [...s].forEach((c, k) => dv.setUint8(o + k, c.charCodeAt(0)));
    w(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); w(8, 'WAVEfmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
    dv.setUint32(24, SR, true); dv.setUint32(28, SR * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, 'data'); dv.setUint32(40, n * 4, true);
    for (let k = 0; k < n; k++) { dv.setInt16(44 + k * 4, Math.max(-1, Math.min(1, L[k])) * 32767, true); dv.setInt16(46 + k * 4, Math.max(-1, Math.min(1, R[k])) * 32767, true); }
    let bin = ''; const u8 = new Uint8Array(ab); for (let k = 0; k < u8.length; k += 8192) bin += String.fromCharCode.apply(null, u8.subarray(k, k + 8192));
    return btoa(bin);
  }, { code, fn, T });
  fs.writeFileSync(out, Buffer.from(b64, 'base64')); await br.close();
})();
