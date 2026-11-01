// The music bed of «Скільки ти важиш…» (the moonfall organ, scenes/moonfall/music_variants.js, given a score of its
// own): soft flute-stop chords that change with every world, a slow line on top; a fuller swell for the Sun, awe for
// the neutron star, and at the question an open, unresolved chord. Quiet — it sits under the voice. No bass below C3,
// no pulse, every rise a slow swell (MUSIC.md).
//   node scenes/weight/music.js   ->  work/weight/music.wav  (72.3 s, stereo, 44.1 kHz)
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const T = 72.3, OUT = path.resolve(__dirname, '../../work/weight/music.wav');

function score({ organ, FL, REG_MID, lv }) {
  // [start (the shot's), notes, how full]: C, Am, F, G, Em, F → C, Am → G, F, G (the Sun), Em → C (the neutron star), F → Gsus4
  const CH = [
    [0.0, [60, 64, 67, 72], 0.3], [14.41, [57, 60, 64, 69], 0.3], [17.44, [53, 57, 60, 65], 0.3], [20.67, [55, 59, 62, 67], 0.32],
    [27.54, [52, 55, 59, 64], 0.4], [32.69, [53, 57, 60, 65], 0.32], [38.0, [55, 60, 64, 67], 0.34], [43.25, [57, 60, 64, 69], 0.3],
    [47.0, [55, 59, 62, 67], 0.3], [50.64, [53, 57, 60, 65], 0.28], [54.34, [55, 59, 62, 67], 0.6], [57.91, [52, 55, 59, 64], 0.45],
    [62.0, [48, 55, 60, 64], 0.5], [66.12, [53, 57, 60, 65], 0.3], [69.0, [55, 60, 62, 67], 0.28],
  ];
  CH.forEach(([a, ns, d], i) => {
    const b = (CH[i + 1] ? CH[i + 1][0] : T) + 0.8;
    ns.forEach((m, j) => organ(a + j * 0.08, b, m + 12, d > 0.45 ? REG_MID : FL, lv(d, 0.03, 0.22), 700 + 2600 * d, 1.4, 1.4));
  });
  // a slow line on top: the chord's fifth or third, an octave up, one per world
  CH.forEach(([a, ns], i) => { const b = CH[i + 1] ? CH[i + 1][0] : T; if (b - a < 2.5) return; organ(a + 0.6, b - 0.2, ns[2] + 24, FL, 0.05, 2600, 1.0, 1.2, 4.6 + 0.1 * (i % 4)); });
}

(async () => {
  const code = fs.readFileSync(path.resolve(__dirname, '../moonfall/music_variants.js'), 'utf8');
  const br = await chromium.launch(), p = await br.newPage();
  const out = await p.evaluate(async ({ code, sc, T }) => {
    eval(code + '; window.__mk = createMoonMusic;'); const score = eval('(' + sc + ')');
    const SR = 44100, ctx = new OfflineAudioContext(2, Math.ceil(SR * T), SR);
    const g = ctx.createGain(); g.connect(ctx.destination);
    g.gain.setValueAtTime(0.9, 0); g.gain.setValueAtTime(0.9, T - 2.0); g.gain.linearRampToValueAtTime(0, T - 0.05);
    window.__mk(ctx, g, score).start();
    const buf = await ctx.startRendering(), L = buf.getChannelData(0), R = buf.getChannelData(1), n = L.length;
    const ab = new ArrayBuffer(44 + n * 4), dv = new DataView(ab), w = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
    w(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); w(8, 'WAVEfmt '); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, 2, true); dv.setUint32(24, SR, true); dv.setUint32(28, SR * 4, true);
    dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, 'data'); dv.setUint32(40, n * 4, true);
    for (let i = 0; i < n; i++) { dv.setInt16(44 + i * 4, Math.max(-1, Math.min(1, L[i])) * 32767, true); dv.setInt16(46 + i * 4, Math.max(-1, Math.min(1, R[i])) * 32767, true); }
    let bin = ''; const u8 = new Uint8Array(ab);
    for (let i = 0; i < u8.length; i += 8192) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 8192));
    return btoa(bin);
  }, { code, sc: score.toString(), T });
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, Buffer.from(out, 'base64'));
  console.log('written', OUT);
  await br.close();
})();
