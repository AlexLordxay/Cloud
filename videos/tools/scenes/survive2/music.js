// The music bed of «Скільки ти протримаєшся…» v2 (the moonfall organ, scenes/moonfall/music_variants.js, given a score
// of its own, as scenes/weight/music.js): soft flute-stop chords, one per world, minor and uneasy where he does not make
// it, opening up where he lives (the Moon, Mars, Titan); thinning out at each death so its sounds come through; at the
// Earth a slow swell from minor into major (the lift MUSIC.md asks for, coming in over 2–3 s), ending open on the
// question. No bass below C3, no pulse.
//   node scenes/survive2/music.js   ->  work/survive2/music.wav
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TL = JSON.parse(fs.readFileSync(path.join(__dirname, 'timeline.json')));
const T = TL.dur, OUT = path.resolve(__dirname, '../../work/survive2/music.wav');
const S = Object.fromEntries(TL.shots.map(s => [s.world, s.t0]));

function score({ organ, FL, REG_MID, lv }, S, T) {
  // [start, notes, how full]
  const CH = [
    [0.0, [57, 60, 64, 69], 0.32],                 // Venus (the hook): Am
    [3.6, [53, 57, 60, 65], 0.22],                 // the question: F
    [S.moon, [60, 64, 67, 72], 0.3],               // the Moon: C, calm
    [S.mercury, [52, 55, 59, 64], 0.32],           // Mercury: Em
    [S.mercury + 4.4, [53, 56, 60, 65], 0.18],     //   the heat takes him: Fm, thin
    [S.venus, [57, 60, 64, 69], 0.3],              // Venus: Am
    [S.venus + 3.5, [56, 59, 62, 68], 0.16],       //   crushed: a diminished colour, thin
    [S.mars, [55, 59, 62, 67], 0.3],               // Mars: G, he lives
    [S.mars + 3.2, [60, 64, 67, 72], 0.34],        //   «тут можна жити»: C
    [S.jupiter, [50, 53, 57, 62], 0.3],            // Jupiter: Dm, falling
    [S.jupiter + 4.5, [49, 53, 56, 61], 0.22],     //   deeper: C#dim colour
    [S.titan, [53, 57, 60, 65], 0.3],              // Titan: F
    [S.titan + 4.9, [55, 59, 62, 67], 0.36],       //   flying: G
    [S.neptune, [52, 55, 59, 64], 0.28],           // Neptune: Em, cold
    [S.neptune + 3.6, [52, 55, 58, 64], 0.16],     //   frozen: thin
    [S.sun, [57, 60, 64, 69], 0.2],                // the Sun: Am, low under the roar
    [S.earth, [57, 60, 64, 69], 0.3],              // the Earth: Am …
    [S.earth + 2.2, [53, 57, 60, 65], 0.4],        //   F …
    [S.earth + 4.2, [60, 64, 67, 72], 0.55],       //   … C: the lift on «на нашій»
    [S.earth + 6.2, [53, 57, 60, 65], 0.34],       //   the question: F …
    [S.earth + 8.0, [55, 60, 62, 67], 0.28],       //   … Gsus4, open
  ];
  CH.forEach(([a, ns, d], i) => {
    const b = (CH[i + 1] ? CH[i + 1][0] : T) + 0.8;
    ns.forEach((m, j) => organ(a + j * 0.08, b, m + 12, d > 0.45 ? REG_MID : FL, lv(d, 0.03, 0.22), 700 + 2600 * d, 1.4, 1.4));
  });
  CH.forEach(([a, ns, d], i) => { const b = CH[i + 1] ? CH[i + 1][0] : T; if (b - a < 2.5 || d < 0.25) return; organ(a + 0.6, b - 0.2, ns[2] + 24, FL, 0.045, 2600, 1.0, 1.2, 4.6 + 0.1 * (i % 4)); });
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
