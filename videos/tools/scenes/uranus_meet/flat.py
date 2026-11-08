# «Знайомся: Уран» — the flat shots: Herschel's eyepiece in March 1781 (the real sky round Uranus that night: a little
# disc among the stars of Taurus), Voyager 2's real photo of Miranda (NASA PIA18185) slowly closing in on Verona Rupes,
# and the sky over Ukraine on 25 November 2026: Taurus, the Pleiades (Волосожар) and Uranus 5.6° from them, then the
# binoculars' view with both in it.
#   python3 flat.py stills <shot> t1,t2   |   python3 flat.py video <shot>
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [TOOLS, HERE]
from sky import Sky, vec
W, H, FPS = 720, 1280, 30
WORK = os.path.join(TOOLS, 'work', 'uranus_meet')
NASA = os.path.join(WORK, 'nasa')
DUR = {'herschel': 7.0, 'mirphoto': 4.5, 'skynow': 8.5}
try:
    DUR.update(json.load(open(os.path.join(HERE, 'timeline.json')))['shots'])
except Exception:
    pass

def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)

def lerp(a, b, k): return a + (b - a) * k

def font(name, size, wght=600):
    f = ImageFont.truetype(os.path.join(TOOLS, 'fonts', name), size)
    try: f.set_variation_by_axes([wght])
    except Exception: pass
    return f

def text(dr, xy, s, f, fill, anchor='mm', shadow=True):
    if shadow: dr.text((xy[0] + 2, xy[1] + 2), s, font=f, fill=(0, 0, 0), anchor=anchor)
    dr.text(xy, s, font=f, fill=fill, anchor=anchor)

_sky = {}
def sky():
    if not _sky: _sky['s'] = Sky(W, H, 2)
    return _sky['s']

# ---------------------------------------------------------------------------------------------------- 1781
U1781 = vec(83.950, 23.551)        # Uranus on 13 March 1781 (astronomy-engine), on the Taurus-Gemini border
def shot_herschel(t):
    d = DUR['herschel']
    k = t / d
    S = sky()
    # the eyepiece: ~1° of sky, drifting slowly (the sky turning; no clock drive in 1781)
    c = vec(83.950 + lerp(0.30, -0.25, k), 23.551 + lerp(0.06, -0.04, k))
    scale = H / math.radians(2.6)
    img = S.render({'centre': c, 'scale': scale, 'roll': 0.0, 'photo': 0.0, 'mw': 0, 'lines': 0, 'zlines': 0,
                    'ecliptic': 0, 'labels': 0, 'stars': 3.0})
    P = S.proj(c, scale)
    x, y, ok = P(U1781); x, y = float(x[0]) / 2, float(y[0]) / 2
    # Uranus: a small greenish disc (bigger and steadier than the points of the stars — that is how Herschel saw it)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for r_, a_ in ((20, 30), (12, 70), (7.5, 255)):
        dl.ellipse([x - r_, y - r_, x + r_, y + r_], fill=(175, 225, 220, a_))
    lay = lay.filter(ImageFilter.GaussianBlur(1.6))
    img = img.convert('RGBA'); img.alpha_composite(lay)
    # the eyepiece: a soft round field, warm old-glass tint
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot(xx - W / 2, yy - H * 0.46) / (W * 0.44)
    m = np.clip((1.0 - r) / 0.035, 0, 1) * (1 - 0.35 * r ** 2)
    a = np.asarray(img.convert('RGB'), np.float32) * m[..., None] * np.array([1.0, 0.97, 0.9])
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img, 'RGBA')
    # the date, and later the name he wanted for it
    al = int(255 * ease((t - 0.3) / 0.6))
    f1 = font('Unbounded.ttf', 54)
    text(dr, (W / 2, H * 0.46 - W * 0.44 - 60), '13 березня 1781', f1, (255, 214, 140, al))
    kg = ease((t - 3.3) / 0.7)
    if kg > 0:
        f2 = font('CormorantItalic.ttf', 76, 700)
        text(dr, (W / 2, H * 0.46 + W * 0.44 + 70), 'Georgium Sidus', f2, (235, 225, 200, int(255 * kg)))
    return img

# ---------------------------------------------------------------------------------------------------- Miranda (photo)
def shot_mirphoto(t):
    d = DUR['mirphoto']
    k = ease(t / d)
    ph = Image.open(os.path.join(NASA, 'PIA18185.jpg')).convert('RGB')
    pw, phh = ph.size
    # from the whole moon to Verona Rupes (the bright scarp at the bottom limb)
    zx, zy = 0.635, 0.905
    z = lerp(1.0, 3.4, k)
    vw = pw / z * 1.04; vh = vw * H / W
    cx = lerp(0.5, zx, k) * pw; cy = lerp(0.5, zy, k ** 0.8) * phh
    box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
    img = ph.crop(tuple(int(round(b)) for b in box)).resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(2, 60, 2))
    g = np.random.default_rng(int(t * 30)).normal(0, 3.0, (H, W, 1))
    img = Image.fromarray(np.clip(np.asarray(img, np.float32) * 0.95 + g, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img, 'RGBA')
    f = font('Commissioner.ttf', 26, 500)
    text(dr, (W / 2, H - 90), 'Справжній знімок «Вояджера-2», 1986 · NASA/JPL', f, (220, 225, 230, 200))
    kl = ease((t - d * 0.6) / 0.6)
    if kl > 0:
        # mark the scarp
        px = (zx * pw - box[0]) / vw * W; py = (zy * phh - box[1]) / vh * H
        r = 95
        dr.ellipse([px - r, py - r, px + r, py + r], outline=(255, 214, 140, int(230 * kl)), width=4)
        f2 = font('Unbounded.ttf', 40)
        text(dr, (px, py - r - 40), 'урвище Верона', f2, (255, 214, 140, int(255 * kl)))
    return img

# ---------------------------------------------------------------------------------------------------- 25.11.2026
PLEI = vec(56.75, 24.12)
URAN = vec(61.70, 20.74)        # Uranus, 25 Nov 2026 (astronomy-engine)
ALDE = vec(68.98, 16.51)
def shot_skynow(t):
    d = DUR['skynow']
    S = sky()
    k1 = ease(t / 3.8)                           # the evening sky, Taurus
    k2 = ease((t - 3.8) / 2.2)                    # into the binoculars (at «Візьми бінокль»)
    mid = 0.58 * PLEI + 0.42 * URAN; mid /= np.linalg.norm(mid)
    c0 = (PLEI + URAN + ALDE) / 3; c0 /= np.linalg.norm(c0)
    c = c0 * (1 - k2) + mid * k2; c /= np.linalg.norm(c)
    scale = lerp(H / math.radians(34.0) * lerp(0.92, 1.0, k1), H / math.radians(15.0), k2)
    roll = -35.0                                  # as it stands in the east in the evening
    img = S.render({'centre': c, 'scale': scale, 'roll': roll, 'photo': 0.55, 'lines': 0.55 * (1 - k2),
                    'zlines': 0.55 * (1 - k2), 'hi': {'Tau': 0.8 * (1 - k2)}, 'ecliptic': 0, 'labels': 0,
                    'stars': 1.15 + 0.4 * k2})
    P = S.proj(c, scale, roll)
    def xy(v):
        x, y, ok = P(v); return float(x[0]) / 2, float(y[0]) / 2
    dr = ImageDraw.Draw(img, 'RGBA')
    fl = font('Unbounded.ttf', 34); fs = font('Commissioner.ttf', 28, 600)
    a1 = int(255 * ease((t - 0.4) / 0.6))
    # Uranus: a marker round its point
    ux, uy = xy(URAN)
    pulse = 1 + 0.08 * math.sin(t * 5)
    r = 30 * pulse
    dr.ellipse([ux - r, uy - r, ux + r, uy + r], outline=(140, 235, 225, a1), width=4)
    dr.ellipse([ux - 4, uy - 4, ux + 4, uy + 4], fill=(190, 240, 235, a1))
    text(dr, (ux + 70, uy + 52), 'Уран', fl, (150, 235, 228, a1))
    px_, py_ = xy(PLEI)
    text(dr, (px_, py_ - 62), 'Волосожар', fl, (255, 214, 140, a1))
    if k2 < 0.5:
        axx, ayy = xy(ALDE)
        text(dr, (axx + 10, ayy + 48), 'Альдебаран', fs, (230, 220, 210, int(a1 * (1 - 2 * k2))))
    # binoculars: two overlapping round fields
    if k2 > 0:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        R = W * 0.49
        dd = np.hypot(xx - W * 0.5, yy - H * 0.5) / R
        m = np.clip((1.0 - dd) / 0.03, 0, 1)
        m = 1 - k2 * (1 - m)
        a = np.asarray(img, np.float32) * m[..., None]
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return img

SHOTS = {'herschel': shot_herschel, 'mirphoto': shot_mirphoto, 'skynow': shot_skynow}

if __name__ == '__main__':
    mode, name = sys.argv[1], sys.argv[2]
    fn = SHOTS[name]
    if mode == 'stills':
        for t in map(float, sys.argv[3].split(',')):
            fn(t).save(os.path.join(WORK, f'st_{name}_{t}.jpg'), quality=90); print(name, t)
    else:
        out = os.path.join(WORK, 'shots', name); os.makedirs(out, exist_ok=True)
        for fi in range(int(round(DUR[name] * FPS))):
            p = os.path.join(out, f'f_{fi:05d}.jpg')
            if os.path.exists(p): continue
            fn(fi / FPS).save(p, quality=93)
        print(name, 'done')
