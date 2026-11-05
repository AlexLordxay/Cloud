# «Знайомся: Нептун» — the flat shots (720×1280, captions come later from compose.py):
#   color  — the real Voyager 2 photo (NASA PIA01492), then a wipe to the real pale colour (after Irwin et al. 2024),
#            then both halves side by side
#   paper  — the discovery: Le Verrier's sums in ink on old paper, then the sky of 23.09.1846 (real stars, J2000; Neptune
#            from astronomy-engine) with the circle where he said to look and the dot Galle saw
#   orbit  — one Neptune year: the planet goes once round the Sun 1846 → 2011 while the Earth spins round 165 times
#   python3 scenes/neptune_meet/flat.py <shot> t0 t1 outdir   (shot-local seconds; frames f_<global frame>.jpg)
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
WORK = os.path.join(TOOLS, 'work', 'neptune_meet')
W, H = 720, 1280
FONT_U = os.path.join(TOOLS, 'fonts', 'Unbounded.ttf')
FONT_C = os.path.join(TOOLS, 'fonts', 'Commissioner.ttf')
FONT_I = os.path.join(TOOLS, 'fonts', 'CormorantItalic.ttf')
_F = {}


def font(f, s, wght=None):
    k = (f, s, wght)
    if k not in _F:
        fo = ImageFont.truetype(f, s)
        if wght:
            try: fo.set_variation_by_axes([wght if a['name'] in (b'Weight', 'Weight') else a['default'] for a in fo.get_variation_axes()])
            except Exception: pass
        _F[k] = fo
    return _F[k]


def sm(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def ease(x):
    x = min(1.0, max(0.0, x)); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def stars_bg(seed=3, n=900):
    rng = np.random.default_rng(seed)
    im = Image.new('RGB', (W, H), (2, 3, 8)); d = ImageDraw.Draw(im)
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, H); b = rng.uniform(0, 1) ** 5
        c = int(40 + 215 * b); r = 0.6 + 1.3 * b
        d.ellipse([x - r, y - r, x + r, y + r], fill=(c, c, min(255, c + 12)))
    return im.filter(ImageFilter.GaussianBlur(0.5))


def label(im, text, cx, cy, size, fill=(255, 255, 255), f=FONT_C, wght=600, alpha=1.0, halo=True):
    if alpha <= 0: return
    fo = font(f, size, wght)
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    w = d.textlength(text, font=fo); x, y = cx - w / 2, cy - size / 2
    if halo:
        sh = Image.new('L', im.size, 0); ImageDraw.Draw(sh).text((x, y), text, font=fo, fill=200, stroke_width=max(2, size // 10))
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.25)).point(lambda v: int(v * 0.8 * alpha))
        black = Image.new('RGBA', im.size, (0, 0, 0, 255)); black.putalpha(sh); lay = Image.alpha_composite(lay, black)
        d = ImageDraw.Draw(lay)
    d.text((x, y), text, font=fo, fill=fill + (int(255 * alpha),))
    im.alpha_composite(lay) if im.mode == 'RGBA' else im.paste(Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB'))


# ------------------------------------------------------------------------------------------------ colour
_photo = {}


def photos():
    if _photo: return _photo
    src = Image.open(os.path.join(WORK, 'nasa', 'pia01492.jpg')).convert('RGB')
    a = np.asarray(src).astype(np.float32) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    # the real colour (Irwin et al. 2024, from Hubble STIS and VLT MUSE): a pale greenish blue only a little bluer than
    # Uranus; the Voyager picture's contrast was stretched and its blue pushed. Same pattern of light and dark, the
    # light measured in the blue channel (the brightest there), laid on the pale tint.
    I = lin[..., 2] / max(1e-4, np.percentile(lin[..., 2], 99.5))
    I = np.clip(I, 0, 1.2) ** 0.9
    tint = np.array([0.24, 0.47, 0.72])
    pale = I[..., None] * tint[None, None, :] * 0.95 + 0.02 * I[..., None]
    pale = np.clip(pale, 0, 1)
    pale_s = np.where(pale <= 0.0031308, 12.92 * pale, 1.055 * pale ** (1 / 2.4) - 0.055)
    _photo['blue'] = src
    _photo['pale'] = Image.fromarray((pale_s * 255).astype(np.uint8))
    return _photo


def shot_color(t, T):
    # t: shot-local seconds; T: the phrases (shot-local): T['pale'] = «а блідо-блакитний», T['why'] = «Синім його…»
    P = photos(); bg = stars_bg(5)
    S = 640 + 50 * t / 8.0   # a slow push in
    blue = P['blue'].resize((int(S), int(S)), Image.LANCZOS); pale = P['pale'].resize((int(S), int(S)), Image.LANCZOS)
    x0, y0 = int(W / 2 - S / 2), int(H / 2 - S / 2 - 30)
    # the wipe: left → right on «а блідо-блакитний»
    k = ease((t - T['pale'] + 0.15) / 1.1)
    split = int(S * k)
    # on «Синім його…»: back to half and half, the line in the middle
    kh = ease((t - T['why']) / 0.8)
    if kh > 0: split = int(S * (k + (0.5 - k) * kh))
    im = bg.copy()
    mask = Image.new('L', (int(S), int(S)), 0)
    if split > 0: ImageDraw.Draw(mask).rectangle([0, 0, split, S], fill=255)
    comb = Image.composite(pale, blue, mask)
    # the photo's black is space: lay it with a soft disc mask so the stars show round the planet
    disc = Image.new('L', (int(S), int(S)), 0); ImageDraw.Draw(disc).ellipse([S * 0.035, S * 0.035, S * 0.965, S * 0.965], fill=255)
    disc = disc.filter(ImageFilter.GaussianBlur(S * 0.01))
    lum = comb.convert('L').point(lambda v: min(255, v * 6))
    im.paste(comb, (x0, y0), ImageChops.lighter(ImageChops.multiply(disc, lum), Image.new('L', disc.size, 0)))
    d = ImageDraw.Draw(im)
    if 0 < split < S * 0.985:
        d.line([x0 + split, y0 + 10, x0 + split, y0 + S - 10], fill=(255, 255, 255), width=3)
    im = im.convert('RGBA')
    a_old = sm(t / 0.5) * (1 - sm((t - T['pale']) / 0.5)) + sm((t - T['why'] - 0.3) / 0.5)
    a_new = sm((t - T['pale'] - 0.6) / 0.5)
    if kh > 0.5:
        label(im, 'справжній колір', W * 0.27, y0 - 34, 30, alpha=a_new, fill=(200, 235, 255))
        label(im, 'Вояджер-2 · 1989', W * 0.73, y0 - 34, 30, alpha=a_old)
    else:
        label(im, 'Фото «Вояджера-2» · 1989', W / 2, y0 - 34, 32, alpha=a_old)
        label(im, 'Справжній колір', W / 2, y0 - 34, 32, alpha=a_new * (1 - sm((t - T['why']) / 0.4)), fill=(200, 235, 255))
    return im.convert('RGB')


# ------------------------------------------------------------------------------------------------ paper
def paper_tex(seed=1):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    def noise(scale, s):
        g = rng.random((H // scale + 2, W // scale + 2)).astype(np.float32)
        return np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((W + scale * 2, H + scale * 2), Image.BICUBIC))[scale:scale + H, scale:scale + W] / 255.0
    n = 0.55 * noise(160, 1) + 0.3 * noise(40, 2) + 0.15 * noise(8, 3)
    fib = noise(3, 4)
    base = np.array([226, 205, 160], np.float32)
    col = base[None, None, :] * (0.86 + 0.18 * n[..., None]) - 18 * (fib[..., None] - 0.5)
    # age: darker edges and stains
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    col *= (1 - 0.45 * np.clip(r - 0.45, 0, 1) ** 1.4)[..., None]
    st = noise(220, 9); col -= np.array([30, 40, 55])[None, None, :] * np.clip(st - 0.62, 0, 1)[..., None] * 2.2
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))


INK = (42, 30, 22)
# Le Verrier's working, much simplified (the elements of his 1846 orbit for the unseen planet, and where to look)
SUMS = [
    ('Planète troublante', 44, 0),
    ('a = 36,154', 40, 1), ('e = 0,10761', 40, 1), ('m = 1/9300', 40, 1),
    ('longitude (1.I.1847) = 326° 32′', 36, 1),
    ('diamètre apparent = 3,3″', 36, 1),
    ('U. J. Le Verrier, 31 août 1846', 30, 2),
]


def shot_paper(t, T, cache={}):
    # 0 … T['sky']: the page fills with ink, line by line (as if being written), a slow push in;
    # T['sky'] …: the page dissolves into the sky chart; at T['seen'] the dot appears in the circle
    if 'paper' not in cache: cache['paper'] = paper_tex()
    if t < T['sky'] + 1.2:
        im = cache['paper'].copy().convert('RGBA')
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        y = 380; total = len(SUMS); per = (T['sky'] - 0.5) / total
        for i, (txt, sz, kind) in enumerate(SUMS):
            fo = font(FONT_I, sz + 14)
            k = (t - 0.2 - i * per) / (per * 0.9)
            if k <= 0: break
            wfull = d.textlength(txt, font=fo)
            x = 80 if kind != 2 else W - 80 - wfull
            if kind == 0: x = (W - wfull) / 2
            d.text((x, y), txt, font=fo, fill=INK + (235,))
            # reveal from the left
            if k < 1:
                d.rectangle([x + wfull * ease(k), y - 10, W, y + sz + 30], fill=(0, 0, 0, 0))
            if kind == 0:
                d.line([x, y + sz + 22, x + wfull * min(1, ease(k)), y + sz + 22], fill=INK + (200,), width=2)
            y += sz + (40 if kind == 0 else 22)
        # a quill line: a small orbit sketch and a cross where to look
        k = (t - 0.2 - total * per * 0.7) / 1.5
        if k > 0:
            cx, cy, R = W / 2, 1110, 120
            d.arc([cx - R, cy - R * 0.62, cx + R, cy + R * 0.62], 200, 200 + 300 * min(1, ease(k)), fill=INK + (210,), width=3)
            d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=INK + (220,))
            if k > 0.8:
                px, py = cx + R * math.cos(math.radians(500)), cy + R * 0.62 * math.sin(math.radians(500))
                kk = ease((k - 0.8) / 0.5); s = 16 * kk
                d.line([px - s, py - s, px + s, py + s], fill=(140, 20, 10, 230), width=4); d.line([px - s, py + s, px + s, py - s], fill=(140, 20, 10, 230), width=4)
        im.alpha_composite(lay)
        z = 1 + 0.06 * min(t, T['sky']) / T['sky']
        im = im.resize((int(W * z), int(H * z)), Image.LANCZOS).crop((int(W * (z - 1) / 2), int(H * (z - 1) / 2), int(W * (z - 1) / 2) + W, int(H * (z - 1) / 2) + H))
        page = im.convert('RGB')
        if t < T['sky']: return page
    sky = sky_chart(t - T['sky'], T['seen'] - T['sky'])
    if t < T['sky'] + 1.2:
        return Image.blend(page, sky, ease((t - T['sky']) / 1.2))
    return sky


_SK = {}


def sky_chart(t, t_seen):
    import astronomy as A
    if not _SK:
        st = json.load(open(os.path.join(TOOLS, 'data', 'sky', 'stars.6.json')))['features']
        tm = A.Time.Make(1846, 9, 23, 23, 0, 0)
        eq = A.EquatorFromVector(A.GeoVector(A.Body.Neptune, tm, True))
        ra0, de0 = eq.ra * 15.0, eq.dec
        _SK.update(stars=[(f['geometry']['coordinates'][0], f['geometry']['coordinates'][1], f['properties']['mag']) for f in st], nep=(ra0, de0))
    ra0, de0 = _SK['nep']
    scale = 52.0   # px per degree
    def proj(ra, de):
        # gnomonic round the field centre, east to the left
        r0, d0, r, d = map(math.radians, (ra0 - 1.0, de0 - 0.4, ra, de))
        c = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(r - r0)
        if c <= 0.2: return None
        x = math.cos(d) * math.sin(r - r0) / c; y = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(r - r0)) / c
        return W / 2 - math.degrees(x) * scale, H / 2 - 40 - math.degrees(y) * scale
    z = 1.0 + 0.08 * min(1.0, t / 8.0)
    im = Image.new('RGB', (W, H), (6, 10, 24)); d = ImageDraw.Draw(im)
    # a faint grid every degree (a star chart of the day)
    for k in range(-20, 21):
        pts = [proj(ra0 - 1 + k, de0 - 0.4 + j * 0.25) for j in range(-60, 61)]
        pts = [p for p in pts if p]; d.line(pts, fill=(20, 30, 55), width=1)
        pts = [proj(ra0 - 1 + j * 0.25, de0 - 0.4 + k) for j in range(-80, 81)]
        pts = [p for p in pts if p]; d.line(pts, fill=(20, 30, 55), width=1)
    for ra, de, m in _SK['stars']:
        if abs(de - de0) > 16: continue
        p = proj(ra, de)
        if not p or not (-20 < p[0] < W + 20 and -20 < p[1] < H + 20): continue
        r = max(1.2, 6.5 - 1.0 * m)
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(235, 238, 255))
    im = im.filter(ImageFilter.GaussianBlur(0.6)).convert('RGBA')
    np_ = proj(ra0, de0)
    # Le Verrier's place: 52′ off the real one (Galle, 23.09.1846: "within a degree")
    pp = proj(ra0 + 0.75, de0 + 0.45)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    kc = ease(t / 1.0)
    if kc > 0:
        R = 1.0 * scale
        for a in range(0, 360, 12):   # dashed
            a0, a1 = math.radians(a), math.radians(a + 7 * kc)
            d.arc([pp[0] - R, pp[1] - R, pp[0] + R, pp[1] + R], a, a + 7 * kc, fill=(243, 185, 100, 230), width=3)
        label(lay, 'тут має бути', pp[0], pp[1] - R - 32, 30, fill=(243, 185, 100), alpha=kc)
    ks = ease((t - t_seen) / 0.6)
    if ks > 0:
        pulse = 1 + 0.25 * math.sin(max(0, t - t_seen) * 4) * math.exp(-max(0, t - t_seen) * 0.8)
        for rr, al in ((26 * pulse, 40), (14 * pulse, 90), (6, 255)):
            d.ellipse([np_[0] - rr, np_[1] - rr, np_[0] + rr, np_[1] + rr], fill=(150, 210, 255, int(al * ks)))
        label(lay, 'Нептун', np_[0] - 10, np_[1] + 52, 36, fill=(170, 220, 255), f=FONT_U, wght=600, alpha=ks)
        label(lay, '23.09.1846', np_[0] - 10, np_[1] + 96, 28, fill=(200, 208, 224), alpha=ks)
    im.alpha_composite(lay)
    if z != 1:
        im = im.resize((int(W * z), int(H * z)), Image.LANCZOS).crop((int(W * (z - 1) / 2), int(H * (z - 1) / 2), int(W * (z - 1) / 2) + W, int(H * (z - 1) / 2) + H))
    return im.convert('RGB')


# ------------------------------------------------------------------------------------------------ orbit
def shot_orbit(t, T, cache={}):
    # top view of the solar system to Neptune: orbits to scale (Earth, Jupiter, Saturn, Uranus, Neptune), Neptune goes
    # once round from its place in 1846 (astronomy-engine) back to it in 2011 over T['go'] … T['end'] (eased); the
    # Earth whirls round 165 times; a trail behind Neptune
    import astronomy as A
    if 'base' not in cache:
        cache['base'] = stars_bg(9, 500)
    im = cache['base'].copy().convert('RGBA'); d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2 + 10; sc = 300 / 30.1   # px per au
    for au, col in ((1.0, (90, 140, 255)), (5.2, (200, 160, 110)), (9.58, (220, 200, 140)), (19.2, (140, 220, 230)), (30.07, (120, 170, 255))):
        R = au * sc
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col + (70 if au < 30 else 110,), width=1 if au < 30 else 2)
    # the Sun
    for rr, al in ((16, 40), (9, 120), (5, 255)):
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 220, 150, al))
    k = ease((t - T['go']) / (T['end'] - T['go']))
    year = 1846.73 + (2011.53 - 1846.73) * k
    def lon(body, y):
        tm = A.Time.Make(int(y), 1, 1, 0, 0, 0).AddDays((y - int(y)) * 365.25)
        return math.radians(A.EclipticLongitude(body, tm))
    L0 = lon(A.Body.Neptune, 1846.73)
    Ln = L0 + 2 * math.pi * k   # (its real motion is near enough uniform at this scale)
    R = 30.07 * sc
    # the trail
    if k > 0:
        n = max(2, int(200 * k))
        pts = [(cx + R * math.cos(L0 + (Ln - L0) * j / n), cy - R * math.sin(L0 + (Ln - L0) * j / n)) for j in range(n + 1)]
        d.line(pts, fill=(140, 200, 255, 200), width=5)
    nx, ny = cx + R * math.cos(Ln), cy - R * math.sin(Ln)
    for rr, al in ((18, 50), (9, 255)):
        d.ellipse([nx - rr, ny - rr, nx + rr, ny + rr], fill=(140, 200, 255, al))
    # the start mark
    sx, sy = cx + R * math.cos(L0), cy - R * math.sin(L0)
    d.line([sx - 14 * math.cos(L0), sy + 14 * math.sin(L0), sx + 14 * math.cos(L0), sy - 14 * math.sin(L0)], fill=(243, 185, 100, 255), width=4)
    # the Earth: round and round (a blur when it is fast)
    Le = lon(A.Body.Earth, 1846.73) + 2 * math.pi * (year - 1846.73)
    ex, ey = cx + 1.0 * sc * math.cos(Le), cy - 1.0 * sc * math.sin(Le)
    d.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=(110, 170, 255, 255))
    label(im, 'Земля', ex + 46, ey - 16, 20, fill=(150, 190, 255), alpha=1 - sm((t - T['go'] - 0.5) / 0.6))
    label(im, 'Нептун', nx, ny - 42, 30, fill=(170, 220, 255), f=FONT_U, wght=600)
    label(im, '1846', sx + 54 * math.cos(L0), sy - 54 * math.sin(L0) + 4, 26, fill=(243, 185, 100), alpha=sm(t / 0.5))
    if k >= 1:
        label(im, '2011: перший повний оберт', W / 2, cy + R + 70, 30, fill=(243, 185, 100), alpha=sm((t - T['end']) / 0.5))
    return im.convert('RGB')


if __name__ == '__main__':
    shot, a, b, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    T = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
    f0 = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    os.makedirs(out, exist_ok=True)
    fn = {'color': shot_color, 'paper': shot_paper, 'orbit': shot_orbit}[shot]
    for i in range(int(round(a * 30)), int(round(b * 30))):
        fn(i / 30.0, T).save(os.path.join(out, f'f_{f0 + i:05d}.jpg'), quality=94)
