// The music bed of «На якій я планеті?» (Венера): survive2's flute-stop organ (scenes/moonfall/music_variants.js) on a
// score of its own (MUSIC.md): soft, a little mysterious through the clues, thinning to one high held note through the
// countdown (the breath before the answer), then the lift into major over ~2 s at the answer — no hit — and an open,
// light close. No bass below C3, no drums.
//   node scenes/puzzle_venus/music.js   ->  work/puzzle_venus/music.wav
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const SC = JSON.parse(fs.readFileSync(path.join(__dirname, 'scene.json')));
const T = SC.duration, OUT = path.resolve(__dirname, '../../work/puzzle_venus/music.wav');
const S = SC.beats;

function score({ organ, FL, REG_MID, lv }, S, T) {
  // [start, notes, how full]
  const CH = [
    [0.0, [57, 60, 64, 69], 0.3],                  // the question: Am
    [S.c1, [53, 57, 60, 65], 0.26],                // clue 1: F
    [S.c2, [50, 53, 57, 62], 0.26],                // clue 2: Dm
    [S.c3, [52, 56, 59, 64], 0.3],                 // clue 3: E (the heat: leaning on)
    [S.opts, [57, 60, 64, 69], 0.3],               // the options: Am
    [S.write, [53, 57, 60, 65], 0.28],             // «write in the comments»: F
    [S.n3, [52, 57, 59, 64], 0.16],                // the countdown: Esus4, thin …
    [S.n1, [64], 0.12],                            //   … one high note left (the breath)
    [S.ans - 0.4, [53, 57, 60, 65], 0.34],         // the answer: F …
    [S.ans + 1.4, [60, 64, 67, 72], 0.5],          //   … C: the lift (eased in, no hit)
    [S.bye, [53, 57, 60, 65], 0.34],               // goodbye: F …
    [S.bye + 2.0, [55, 60, 62, 67], 0.3],          //   … Gsus4, open
  ];
  CH.forEach(([a, ns, d], i) => {
    const b = (CH[i + 1] ? CH[i + 1][0] : T) + 0.8;
    ns.forEach((m, j) => organ(a + j * 0.08, b, m + 12, d > 0.45 ? REG_MID : FL, lv(d, 0.03, 0.22), 700 + 2600 * d, 1.4, 1.4));
  });
  CH.forEach(([a, ns, d], i) => { const b = CH[i + 1] ? CH[i + 1][0] : T; if (b - a < 2.5 || d < 0.25) return; organ(a + 0.6, b - 0.2, ns[ns.length > 2 ? 2 : 0] + 24, FL, 0.045, 2600, 1.0, 1.2, 4.6 + 0.1 * (i % 4)); });
}

(async () => {
  const code = fs.readFileSync(path.resolve(__dirname, '../moonfall/music_variants.js'), 'utf8');
  const br = await chromium.launch(), p = await br.newPage();
  const out = await p.evaluate(async ({ code, sc, S, T }) => {
    eval(code + '; window.__mk = createMoonMusic;'); const score0 = eval('(' + sc + ')'), score = o => score0(o, S, T);
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
  }, { code, sc: score.toString(), S, T });
  fs.mkdirSync(path.dirname(OUT), { recursive: true }); fs.writeFileSync(OUT, Buffer.from(out, 'base64'));
  console.log('written', OUT, T, 's');
  await br.close();
})();
