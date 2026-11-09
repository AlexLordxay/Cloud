// The music bed of «Парад планет» (16.11.2026): the flute-stop organ of scenes/moonfall/music_variants.js on a score of
// its own (MUSIC.md: soft chords that breathe, waves of loudness, no bass below C3, no drums; peaks come in slowly):
// a quiet, expectant dawn at the hook; a slow climb through the view from above and the parade of planets; the sky over
// Ukraine opening into a bright major (eased in over ~2.5 s); hanging suspensions on Mars–Jupiter and the gap between
// them; light high notes for the meteors; a calm close lifting to major on «надішли».
//   node scenes/parade/music.js   ->  work/parade/music.wav
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const SC = JSON.parse(fs.readFileSync(path.join(__dirname, 'scene.json')));
const T = SC.duration, OUT = path.resolve(__dirname, '../../work/parade/music.wav');
const S = SC.beats;

function score({ organ, FL, REG_MID, lv }, S, T) {
  // [start, notes, how full]
  const CH = [
    [0.0, [57, 64, 69, 72], 0.26],                 // the dawn: Am(add9 colour), quiet
    [S.site, [53, 60, 65, 69], 0.26],              // from above: F
    [S.site + 5.5, [55, 62, 67, 71], 0.3],         //   the rays: G
    [S.lineup, [57, 60, 64, 69], 0.28],            // the parade: Am …
    [S.lineup + 7.1, [53, 57, 60, 65], 0.3],       //   Venus: F
    [S.lineup + 13.8, [50, 57, 62, 65], 0.3],      //   Mars: Dm
    [S.lineup + 18.9, [55, 59, 62, 67], 0.36],     //   Jupiter: G, fuller …
    [S.sky1 - 0.6, [60, 64, 67, 72], 0.5],         // the sky over Ukraine: C — the lift, eased in
    [S.sky1 + 9.0, [53, 60, 65, 69], 0.36],        //   Mercury: F
    [S.sky1 + 11.2, [55, 60, 62, 67], 0.3],        //   Mars and Jupiter: Gsus4 (hanging) …
    [S.site2, [50, 57, 62, 65], 0.28],             // 600 million km: Dm, thin
    [S.sky2, [57, 64, 69, 72], 0.3],               // the meteors: Am(add9)
    [S.sky2 + 5.0, [53, 60, 65, 69], 0.34],        //   F
    [S.card, [60, 64, 67, 72], 0.4],               // when to look: C
    [S.card + 5.5, [53, 57, 60, 65], 0.34],        //   F
    [S.cta, [55, 60, 62, 67], 0.34],               // «збережи…»: Gsus4 …
    [S.cta + 2.4, [60, 64, 67, 72], 0.44],         //   … C, open to the end
  ];
  CH.forEach(([a, ns, d], i) => {
    const b = (CH[i + 1] ? CH[i + 1][0] : T) + 0.8;
    ns.forEach((m, j) => organ(a + j * 0.08, b, m + 12, d > 0.45 ? REG_MID : FL, lv(d, 0.03, 0.22), 700 + 2600 * d, 1.6, 1.6));
  });
  CH.forEach(([a, ns, d], i) => { const b = CH[i + 1] ? CH[i + 1][0] : T; if (b - a < 2.5 || d < 0.27) return; organ(a + 0.7, b - 0.2, ns[2] + 24, FL, 0.04, 2600, 1.0, 1.2, 4.6 + 0.1 * (i % 4)); });
  // the meteors: a light high note each, like a glint
  for (const m of S.meteors || []) organ(m, m + 1.4, 88 + (Math.round(m * 7) % 3) * 2, FL, 0.021, 4200, 0.02, 1.2);
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
