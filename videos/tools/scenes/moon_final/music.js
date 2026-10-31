// The finale's organ (the moonfall organ, scenes/moonfall/music_variants.js, given a score of its own): nothing while
// he walks; as he lifts his eyes to the Earth a soft A minor swells in on flute stops, a lone line above; when his
// head sinks it falls through F to D minor; under the question a high note alone, and an E chord left suspended,
// unresolved, the way the question is. No bass below C3, no pulse, every rise a slow swell (MUSIC.md).
//   node scenes/moon_final/music.js   ->  work/moon_final/organ.wav  (13 s, stereo, 44.1 kHz)
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const T = 13.0, OUT = path.resolve(__dirname, '../../work/moon_final/organ.wav');

function score({ organ, FL, REG_MID, lv }) {
  // [start, end, notes, how full (0…1)] — chords overlap a little, each breathing in slowly
  const CH = [
    [5.3, 7.6, [57, 60, 64, 69], 0.35],          // A minor: he looks up at the Earth
    [7.3, 8.9, [57, 60, 65, 69], 0.45],          // F over A
    [8.6, 10.6, [57, 62, 65, 69], 0.4],          // D minor: the head sinks
    [10.3, 13.0, [59, 64, 69, 71], 0.3],         // E sus4, left open under the question
  ];
  CH.forEach(([a, b, ns, d]) => ns.forEach((m, j) => organ(a + j * 0.1, b, m + 12, d > 0.42 ? REG_MID : FL, lv(d, 0.03, 0.24), 700 + 2600 * d, 1.8, 1.6)));
  // the line on top: long, falling notes; at the question one high note hangs
  [[5.8, 7.8, 76], [7.8, 9.0, 77], [9.0, 10.4, 74], [10.6, 13.0, 83]].forEach(([a, b, m], j) => organ(a, b, m, FL, j === 3 ? 0.06 : 0.09, 2600, 1.2, 1.5, 4.6 + 0.2 * j));
}

(async () => {
  const code = fs.readFileSync(path.resolve(__dirname, '../moonfall/music_variants.js'), 'utf8');
  const br = await chromium.launch(), p = await br.newPage();
  const out = await p.evaluate(async ({ code, sc, T }) => {
    eval(code + '; window.__mk = createMoonMusic;'); const score = eval('(' + sc + ')');
    const SR = 44100, ctx = new OfflineAudioContext(2, Math.ceil(SR * T), SR);
    const g = ctx.createGain(); g.connect(ctx.destination);
    g.gain.setValueAtTime(0.9, 0); g.gain.setValueAtTime(0.9, T - 1.6); g.gain.linearRampToValueAtTime(0, T - 0.05);
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
