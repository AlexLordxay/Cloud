# «Як насправді рухаються планети» — every frame of the picture (1080x1920), drawn here in numpy/PIL:
#   A  0–4.9    the textbook picture (planets in a row, big, close) → true distances and sizes (they vanish to dots)
#   B  4.6–11.6 a row of Suns: 41 between the Sun and Mercury, ~3 230 to Neptune (planet ticks on the line)
#   C  11.2–19.8 Mercury's surface (work/mercury_meet/shot_rm_sun, MESSENGER relief) — the «movie» Sun, then the honest one
#   D  19.4–29.8 the Milky Way (NASA/JPL-Caltech/R. Hurt illustration): the Sun ~26 000 ly out, going round clockwise
#   E  29.2–39.9 the Sun flying, the planets' paths as long helices (orbit plane ~60° to the motion; scale compressed)
#   F  39.6–44.9 the myth (planets trailing behind like a comet's tail) → how it really is
#   G  44.5–56  the Earth and the Moon (the counter of km is compose.py's COUNTER)
#   python3 render.py [workers] [frame …]   -> work/real_motion/frames/f_%05d.jpg (skips frames that exist)
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
TEX = os.path.abspath(os.path.join(TOOLS, '../../planetarium/textures'))
OUT = os.path.join(TOOLS, 'work', 'real_motion', 'frames')
MERC = os.path.join(TOOLS, 'work', 'mercury_meet', 'shot_rm_sun')
W, H = 1080, 1920
FPS = 30
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']
FONT = os.path.join(TOOLS, 'fonts', 'Commissioner.ttf')

def sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def ramp(t, a, b): return sm((t - a) / (b - a))
def win(t, a, b, d=0.5): return min(ramp(t, a - d, a), 1 - ramp(t, b, b + d))
def lerp(a, b, k): return a + (b - a) * k
def nrm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

AU = 149.6e6
PL = [  # name, a (AU), radius km, texture, period (years), heliocentric longitude 12.11.2026 (deg, astronomy-engine)
    ('mercury', 0.387, 2440, 'mercury.jpg', 0.241, 88.1), ('venus', 0.723, 6052, 'venus_atmosphere.jpg', 0.615, 61.0),
    ('earth', 1.0, 6371, 'earth_day.jpg', 1.0, 49.6), ('mars', 1.524, 3390, 'mars.jpg', 1.881, 106.0),
    ('jupiter', 5.203, 69911, 'jupiter.jpg', 11.86, 134.8), ('saturn', 9.537, 58232, 'saturn.jpg', 29.45, 12.6),
    ('uranus', 19.19, 25362, 'uranus.jpg', 84.0, 63.5), ('neptune', 30.07, 24622, 'neptune.jpg', 164.8, 3.3)]
UA = {'mercury': 'Меркурій', 'venus': 'Венера', 'earth': 'Земля', 'mars': 'Марс', 'jupiter': 'Юпітер', 'saturn': 'Сатурн',
      'uranus': 'Уран', 'neptune': 'Нептун'}
R_SUN = 696000.0

# ---------------------------------------------------------------- assets (loaded once per worker)
_A = {}
def A(key):
    if key in _A: return _A[key]
    Image.MAX_IMAGE_PIXELS = None
    if key == 'stars':
        sky = Image.open(os.path.join(TOOLS, 'data', 'sky', 'eso0932a.jpg')).convert('RGB')
        c = sky.crop((4300, 500, 5900, 2900))   # 1600x2400: a stretch towards the anticentre, away from the bright core
        v = np.asarray(c, np.float32) / 255
        v = np.clip((v - 0.04) * 1.05, 0, 1) ** 1.15 * 0.85
        _A[key] = v
    elif key == 'mw':
        _A[key] = Image.open(os.path.join(HERE, 'assets', 'milkyway_pia10748.jpg')).convert('RGB')
    elif key.startswith('tex:'):
        _A[key] = np.asarray(Image.open(os.path.join(TEX, key[4:])).convert('RGB'), np.float32) / 255
    elif key == 'ring':
        r = np.asarray(Image.open(os.path.join(TEX, 'saturn_ring.png')).convert('RGBA'), np.float32) / 255
        _A[key] = r[r.shape[0] // 2]
    elif key.startswith('font:'):
        from PIL import ImageFont
        f = ImageFont.truetype(FONT, int(key[5:]))
        try: f.set_variation_by_axes([600])
        except Exception: pass
        _A[key] = f
    return _A[key]

def stars_bg(dx=0.0, dy=0.0, k=1.0):
    """the photographic star field, panned by (dx, dy) px; k: brightness"""
    S = A('stars'); h, w = S.shape[:2]
    x0 = int((w - W) / 2 + dx) % (w - W); y0 = int((h - H) / 2 + dy) % (h - H)
    return S[y0:y0 + H, x0:x0 + W] * k

def to_img(a): return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

# ---------------------------------------------------------------- camera + globes
class Cam:
    def __init__(self, pos, target, fov=40.0, up=(0, 0, 1)):
        self.p = np.asarray(pos, float); f = nrm(np.asarray(target, float) - self.p)
        r = nrm(np.cross(f, up)); u = np.cross(r, f)
        self.f, self.r, self.u = f, r, u
        self.k = (H / 2) / math.tan(math.radians(fov) / 2)
    def proj(self, X):
        X = np.atleast_2d(X) - self.p
        z = X @ self.f
        return W / 2 + self.k * (X @ self.r) / z, H / 2 - self.k * (X @ self.u) / z, z

def globe(name, rpx, cam_r, cam_u, cam_b, light, spin=0.0, ring=False):
    """an RGBA sprite of a lit, textured sphere of radius rpx (px) seen along -cam_b; light: unit vector to the Sun (world)"""
    pad = 2.35 if ring else 1.08
    S = max(4, int(2 * rpx * pad + 4))
    yy, xx = (np.mgrid[0:S, 0:S] - S / 2 + 0.5) / rpx
    y = -yy; x = xx
    rr = x * x + y * y
    z = np.sqrt(np.clip(1 - rr, 0, 1))
    n = x[..., None] * cam_r + y[..., None] * cam_u + z[..., None] * cam_b
    lat = np.arcsin(np.clip(n[..., 2], -1, 1)); lon = np.arctan2(n[..., 1], n[..., 0]) + spin
    tex = A('tex:' + PLF[name]); th, tw = tex.shape[:2]
    u = ((lon / (2 * np.pi)) % 1) * (tw - 1); v = (0.5 - lat / np.pi) * (th - 1)
    col = tex[v.astype(int).clip(0, th - 1), u.astype(int).clip(0, tw - 1)]
    mu = np.clip(n @ light, -1, 1)
    lam = np.clip(mu, 0, 1)
    if name in ('jupiter', 'saturn', 'uranus', 'neptune', 'venus'):
        shade = 0.015 + 1.0 * lam ** 0.75 * (0.75 + 0.25 * z)        # gas giants / clouds: softer terminator, limb darkening
    else:
        shade = 0.01 + 1.05 * lam ** 0.9
    rgb = col * shade[..., None]
    if name == 'earth':
        night = A('tex:earth_night.jpg'); nh, nw = night.shape[:2]
        nl = night[(v / (th - 1) * (nh - 1)).astype(int).clip(0, nh - 1), (u / (tw - 1) * (nw - 1)).astype(int).clip(0, nw - 1)]
        dark = np.clip(-mu * 4 + 0.15, 0, 1)
        rgb = rgb + nl * np.array([1.0, 0.8, 0.5]) * 0.9 * dark[..., None]
        rim = np.clip(1 - z, 0, 1) ** 2.2 * np.clip(mu + 0.25, 0, 1)
        rgb = rgb + rim[..., None] * np.array([0.25, 0.5, 1.0]) * 0.9
    if name == 'neptune':
        rgb = rgb * np.array([0.92, 1.0, 1.02])
    alpha = np.clip((1 - np.sqrt(rr)) * rpx / 1.2, 0, 1)
    out = np.dstack([rgb, alpha])
    if ring:
        N = nrm([math.sin(math.radians(26.7)), 0, math.cos(math.radians(26.7))])       # Saturn's ring plane
        bn = cam_b @ N
        if abs(bn) > 1e-3:
            s = -(x * (cam_r @ N) + y * (cam_u @ N)) / bn
            P = x[..., None] * cam_r + y[..., None] * cam_u + s[..., None] * cam_b
            rho = np.linalg.norm(P, axis=-1)
            rt = A('ring'); k = ((rho - 1.24) / (2.27 - 1.24))
            on = (k >= 0) & (k <= 1)
            ri = (k.clip(0, 1) * (len(rt) - 1)).astype(int)
            rc = rt[ri, :3]; ra = rt[ri, 3] * on
            lit = 0.25 + 0.85 * abs(light @ N)
            behind = (s < 0) & (rr < 1)
            ra = np.where(behind, 0, ra)
            out[..., :3] = out[..., :3] * (1 - ra[..., None]) + rc * lit * ra[..., None]
            out[..., 3] = np.maximum(out[..., 3], ra)
    return to_rgba(out)

def to_rgba(a): return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGBA')

PLF = {n: f for n, _, _, f, _, _ in PL}

def sun_sprite(rpx, glow=1.0, t=0.0):
    """the Sun: textured, limb-darkened disc and a soft glow, as additive RGB (S x S) and its size"""
    S = int(rpx * 2 * (3.2 if glow > 0 else 1.1) + 6)
    yy, xx = (np.mgrid[0:S, 0:S] - S / 2 + 0.5) / max(rpx, 0.5)
    rr = np.sqrt(xx * xx + yy * yy)
    tex = A('tex:sun.jpg'); th, tw = tex.shape[:2]
    z = np.sqrt(np.clip(1 - rr * rr, 0, 1))
    lon = np.arctan2(xx, z) + t * 0.05; lat = np.arcsin(np.clip(-yy, -1, 1))
    col = tex[((0.5 - lat / np.pi) * (th - 1)).astype(int).clip(0, th - 1), (((lon / (2 * np.pi)) % 1) * (tw - 1)).astype(int).clip(0, tw - 1)]
    lum = col.mean(-1, keepdims=True)
    base = np.array([1.0, 0.93, 0.78]) * (0.75 + 0.5 * lum)
    limb = (0.35 + 0.65 * z ** 0.6)[..., None]
    disc = np.clip((1 - rr) * max(rpx, 0.5) * 1.5 + 0.5, 0, 1)[..., None]
    g = glow * (0.55 * np.exp(-((rr - 1).clip(0) / 0.35) ** 2) + 0.25 * np.exp(-((rr - 1).clip(0) / 1.3) ** 2))[..., None] * np.array([1.0, 0.75, 0.42])
    return base * limb * disc * 1.15 + g * (1 - disc)

def add(canvas, sprite, cx, cy):
    """additive paste of an RGB float sprite centred at (cx, cy)"""
    h, w = sprite.shape[:2]; x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    canvas[ya:yb, xa:xb] += sprite[ya - y0:yb - y0, xa - x0:xb - x0]

def over(canvas, im, cx, cy):
    """alpha paste of an RGBA PIL sprite centred at (cx, cy) onto a float canvas"""
    a = np.asarray(im, np.float32) / 255; h, w = a.shape[:2]
    x0 = int(round(cx - w / 2)); y0 = int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    s = a[ya - y0:yb - y0, xa - x0:xb - x0]
    c = canvas[ya:yb, xa:xb]; c[:] = c * (1 - s[..., 3:]) + s[..., :3] * s[..., 3:]

def glowdot(canvas, cx, cy, r, col, k=1.0):
    s = int(r * 6 + 4); yy, xx = np.mgrid[0:s, 0:s] - s / 2 + 0.5
    d = np.sqrt(xx * xx + yy * yy)
    add(canvas, (np.exp(-(d / r) ** 2) * 1.0 + 0.25 * np.exp(-(d / (2.5 * r)) ** 2))[..., None] * np.array(col) * k, cx, cy)

def lines(canvas, pts_list, col, width=2, k=1.0):
    """anti-aliased polylines (drawn at 2x and added)"""
    im = Image.new('L', (W * 2, H * 2), 0); d = ImageDraw.Draw(im)
    for pts, a in pts_list:
        if len(pts) > 1: d.line([(2 * x, 2 * y) for x, y in pts], fill=int(255 * min(1, a)), width=width * 2)
    m = np.asarray(im.resize((W, H), Image.LANCZOS), np.float32) / 255
    canvas += m[..., None] * np.array(col) * k

def label(img, x, y, text, size=30, fill=(225, 232, 245), a=1.0, anchor='mm'):
    if a <= 0: return
    d = ImageDraw.Draw(img); f = A(f'font:{size}')
    d.text((x + 2, y + 2), text, font=f, anchor=anchor, fill=(0, 0, 0, int(160 * a)))
    d.text((x, y), text, font=f, anchor=anchor, fill=fill + (int(255 * a),))

# ---------------------------------------------------------------- A: textbook → true scale
TB_D = [1.55 + 0.62 * i for i in range(8)]                  # textbook distances (Sun radius 1)
TB_R = [0.13, 0.21, 0.22, 0.16, 0.5, 0.44, 0.3, 0.29]
def shot_A(t):
    m = ramp(t, 2.9, 4.6)                                       # 0 textbook … 1 true
    cv = stars_bg(dx=t * 6, dy=-t * 3, k=0.75)
    D_tb = TB_D[-1]; D_tr = 30.07
    tgt = np.array([lerp(0.5, 0.0, m), 0, 0])
    ang = math.radians(lerp(13, 40, m)); dist = lerp(2.35, 2.6, m) - 0.03 * t
    cam = Cam(tgt + np.array([0, -math.cos(ang) * dist, math.sin(ang) * dist]), tgt, fov=46)
    L = []
    for i, (n, a, r, f, T, lon0) in enumerate(PL):
        d = math.exp(lerp(math.log(TB_D[i] / D_tb), math.log(a / D_tr), m))
        R = math.exp(lerp(math.log(TB_R[i] / D_tb), math.log(r / AU / D_tr), m))
        th = math.radians(lerp(-4 + 1.2 * i, lon0 - 20, m) + 2.0 * t / max(0.3, T ** 0.5))
        L.append((n, d, R, th))
    # orbits
    orb = []
    for n, d, R, th in L:
        ph = np.linspace(0, 2 * np.pi, 220)
        x, y, z = cam.proj(np.stack([d * np.cos(ph), d * np.sin(ph), 0 * ph], 1))
        orb.append((list(zip(x.tolist(), y.tolist())), 0.55))
    lines(cv, orb, (0.75, 0.8, 0.9), width=1, k=0.6)
    # the Sun
    rs = math.exp(lerp(math.log(1.0 / D_tb), math.log(R_SUN / AU / D_tr), m))
    x, y, z = cam.proj([0, 0, 0]); rpx = cam.k * rs / z[0]
    add(cv, sun_sprite(max(rpx, 0.6), glow=1.0 if rpx > 3 else 0.0, t=t), x[0], y[0])
    if rpx < 6: glowdot(cv, x[0], y[0], 7 + 5 * (1 - ramp(rpx, 2, 6)), (1.0, 0.85, 0.6), 1.2)
    # planets, far first
    order = sorted(L, key=lambda q: -cam.proj([q[1] * math.cos(q[3]), q[1] * math.sin(q[3]), 0])[2][0])
    img_lbl = []
    for n, d, R, th in order:
        P = np.array([d * math.cos(th), d * math.sin(th), 0])
        x, y, z = cam.proj(P); rpx = cam.k * R / z[0]
        if rpx >= 1.2:
            g = globe(n, rpx, cam.r, cam.u, -cam.f, nrm(-P), spin=0.15 * t, ring=(n == 'saturn'))
            cv_img = None
            over(cv, g, x[0], y[0])
        else:
            glowdot(cv, x[0], y[0], 1.6, (0.85, 0.88, 0.95), 0.9 * ramp(t, 3.0, 4.2))
        img_lbl.append((n, x[0], y[0], rpx))
    img = to_img(cv).convert('RGBA')
    k = ramp(t, 3.9, 4.4)
    for n, x, y, rpx in img_lbl:
        if n in ('jupiter', 'neptune'): label(img, x, y - 26, UA[n], 24, a=k)
    return img.convert('RGB')

# ---------------------------------------------------------------- B: a row of Suns
TICKS = [(n, a * AU / (2 * R_SUN)) for n, a, *_ in PL]            # in Sun diameters from the Sun's centre
def shot_B(t):
    cv = stars_bg(dx=200 + t * 4, dy=300, k=0.55)
    # camera: centre c (Sun diameters), scale s (px per diameter)
    keys = [(4.6, 0.0, 300.0), (5.6, 1.2, 300.0), (8.4, 21.0, 23.0), (9.0, 21.0, 22.0), (11.2, 1640.0, 0.30), (12.0, 1650.0, 0.29)]
    for (t0, c0, s0), (t1, c1, s1) in zip(keys, keys[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0)); c = lerp(c0, c1, k); s = math.exp(lerp(math.log(s0), math.log(s1), k)); break
    else: c, s = keys[-1][1], keys[-1][2]
    X = lambda u: W / 2 + (u - c) * s
    Y = 900
    # how many Suns are laid down: 41 to Mercury by 8.3 s, then on to Neptune
    n = 41.6 * ramp(t, 5.0, 8.3) if t < 9.0 else 41.6 + (3229 - 41.6) * ramp(t, 9.1, 11.0)
    if s * 1.0 >= 2.0:
        for i in range(0, int(math.ceil(n)) + 1):
            x = X(i)
            if x < -s or x > W + s: continue
            kk = min(1.0, n - i + 1) if i > 0 else 1.0
            if kk <= 0: continue
            if i == 0: add(cv, sun_sprite(s / 2, glow=1.0, t=t), x, Y)
            else: add(cv, sun_sprite(s / 2, glow=0.0, t=t + i) * np.array([1.0, 0.82, 0.55]) * 0.8 * kk, x, Y)
    # when the Suns are too small to see: a golden line from the Sun to the last one laid
    lk = 1 - ramp(s, 2.0, 5.0)
    if lk > 0:
        x0, x1 = max(0.0, X(0)), min(float(W), X(n))
        if x1 > x0:
            yy = np.arange(H)[:, None]; band = np.exp(-((yy - Y) / 2.2) ** 2) * 0.9 + np.exp(-((yy - Y) / 9) ** 2) * 0.25
            xx = np.arange(W)[None, :]; on = ((xx >= x0) & (xx <= x1)).astype(np.float32)
            cv += (band * on)[..., None] * np.array([1.0, 0.78, 0.45]) * lk
        glowdot(cv, X(0), Y, 6, (1.0, 0.85, 0.6), 1.3 * lk)
    img = to_img(cv).convert('RGBA')
    # planet ticks: a small globe (or point) and the name, where the row has reached it
    for name, u in TICKS:
        if u > n + 0.5: continue
        x = X(u)
        if not (-40 < x < W + 40): continue
        a = min(1.0, (n - u) / 3 + 0.3) if name != 'mercury' else ramp(t, 7.9, 8.4)
        if name == 'mercury' and t > 9.6: a *= 1 - ramp(t, 9.6, 10.2)
        d = ImageDraw.Draw(img)
        d.ellipse((x - 9, Y - 9, x + 9, Y + 9), outline=(200, 225, 255, int(230 * a)), width=2)
        if name == 'mercury' or name in ('earth', 'jupiter', 'saturn', 'neptune') and t > 9.0:
            label(img, x, Y - 40 - (30 if name in ('earth',) else 0), UA[name], 26, a=a)
    return img.convert('RGB')

# ---------------------------------------------------------------- C: Mercury's surface, the movie Sun → the honest one
_sunpos = {}
def merc_frame(t):
    n = len([f for f in os.listdir(MERC) if f.endswith('.jpg')]) if os.path.isdir(MERC) else 0
    i = int(min(max(0, (t - 11.2) * FPS), max(0, n - 1)))
    im = Image.open(os.path.join(MERC, f'f_{i:05d}.jpg')).convert('RGB').resize((W, H), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    if i not in _sunpos:
        # the disc: the peak of the blurred brightness (glare streaks and lit ground don't pull it off), then the
        # saturated pixels round that peak give the radius
        lum = Image.fromarray((a.mean(-1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
        L_ = np.asarray(lum, np.float32); py, px = np.unravel_index(np.argmax(L_), L_.shape)
        cx, cy = px * 4 + 2, py * 4 + 2
        yy, xx = np.mgrid[0:H, 0:W]
        m = (a.mean(-1) > 0.97) & ((xx - cx) ** 2 + (yy - cy) ** 2 < 150 ** 2)
        ys, xs = np.nonzero(m)
        _sunpos[i] = (xs.mean(), ys.mean(), math.sqrt(len(xs) / math.pi)) if len(xs) > 20 else (cx, cy, 40)
    return a, _sunpos[i]

def shot_C(t):
    a, (sx, sy, sr) = merc_frame(t)
    cv = a.copy()
    km = win(t, 11.0, 14.3, 0.6)                                 # «у кіно»: a Sun half the sky
    if km > 0:
        R = 420 * (0.9 + 0.1 * ramp(t, 11.0, 14.3))
        spr = sun_sprite(R, glow=1.0, t=t)
        tmp = np.zeros_like(cv); add(tmp, spr, sx, sy + 120)
        cv = cv * (1 - 0.35 * km) + tmp * km
    img = to_img(cv).convert('RGBA')
    k = win(t, 15.4, 19.4, 0.5)                                  # the honest Sun and the one from the Earth beside it
    if k > 0:
        d = ImageDraw.Draw(img)
        r_e = sr * 0.533 / 1.4
        ex, ey = sx - 260, sy
        tmp = np.zeros((H, W, 3), np.float32); add(tmp, sun_sprite(r_e, glow=0.0, t=t), ex, ey)
        img = to_img(np.asarray(img.convert('RGB'), np.float32) / 255 + tmp * k).convert('RGBA'); d = ImageDraw.Draw(img)
        d.ellipse((sx - sr - 14, sy - sr - 14, sx + sr + 14, sy + sr + 14), outline=(255, 220, 160, int(200 * k)), width=2)
        label(img, sx, sy + sr + 46, 'з Меркурія', 28, a=k)
        label(img, ex, ey + sr + 46, 'з Землі', 28, a=k)
    if km > 0:
        label(img, W / 2, 1560, 'так показують у кіно', 30, fill=(255, 200, 150), a=ramp(t, 11.6, 12.2) * (1 - ramp(t, 13.9, 14.4)))
    return img.convert('RGB')

# ---------------------------------------------------------------- D: the Milky Way
SUN_GAL = (0.5, 0.735)            # the Sun in PIA10748 (fraction of the picture), ~26 000 ly below the centre
def shot_D(t):
    mw = A('mw'); S = mw.size[0]
    rot = -(t - 19.4) * 0.9                                     # degrees: slow clockwise turn (seen from the north)
    zoom = math.exp(lerp(math.log(3.2), math.log(1.0), ramp(t, 19.6, 23.6)))
    zoom = math.exp(lerp(math.log(zoom), math.log(4.0), ramp(t, 27.4, 29.8)))
    # the Sun's position after the turn
    cx, cy = S / 2, S / 2
    sx0, sy0 = SUN_GAL[0] * S - cx, SUN_GAL[1] * S - cy
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    sxr, syr = sx0 * ca + sy0 * sa, -sx0 * sa + sy0 * ca       # PIL rotate is counter-clockwise for positive angles
    # view centre: from the Sun (zoomed in) to the galaxy's centre
    f = ramp(t, 19.6, 23.6) * (1 - ramp(t, 27.4, 29.8))
    vx, vy = lerp(sxr, 0, f), lerp(syr, 0, f)
    fit = H / S * 1.02                                          # px per source px at zoom 1 (the whole galaxy in the height)
    sc = fit * zoom
    # the window straight from the picture: output pixel (X, Y) -> source = centre + R(-rot) * ((X, Y) - frame centre) / sc + view
    cr, sr_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    # source = C + Rinv * (v + d/sc) where Rinv undoes the turn (screen y down)
    def M(dx, dy): return cr * dx - sr_ * dy, sr_ * dx + cr * dy
    ax, ay = M(1 / sc, 0); bx, by = M(0, 1 / sc); ox, oy = M(vx, vy)
    cx0 = cx + ox - ax * W / 2 - bx * H / 2; cy0 = cy + oy - ay * W / 2 - by * H / 2
    im = mw.transform((W, H), Image.AFFINE, (ax, bx, cx0, ay, by, cy0), Image.BICUBIC)
    cv = np.asarray(im, np.float32) / 255
    cv = np.maximum(cv, stars_bg(k=0.25) * (1 - cv.mean(-1, keepdims=True) * 2).clip(0, 1))
    px, py = W / 2 + (sxr - vx) * sc, H / 2 + (syr - vy) * sc
    k = ramp(t, 20.6, 21.4)
    # the path ahead: a faint arc along the Sun's orbit (clockwise), brightest at the Sun
    ak = win(t, 22.2, 28.6, 0.6)
    if ak > 0:
        R = math.hypot(sxr, syr); a0 = math.atan2(syr, sxr)
        pts = []
        for j in range(60):
            aa = a0 + j * math.radians(0.6)                             # clockwise on screen (y down) = increasing angle
            pts.append(((W / 2 + (R * math.cos(aa) - vx) * sc), (H / 2 + (R * math.sin(aa) - vy) * sc)))
        segs = [(pts[j:j + 2], ak * (1 - j / 60) ** 1.5) for j in range(59)]
        lines(cv, segs, (1.0, 0.86, 0.6), width=3, k=0.9)
    glowdot(cv, px, py, 7, (1.0, 0.9, 0.7), 1.4 * k)
    img = to_img(cv).convert('RGBA'); d = ImageDraw.Draw(img)
    r = 22 + 10 * (1 - k)
    d.ellipse((px - r, py - r, px + r, py + r), outline=(255, 225, 170, int(230 * k)), width=3)
    label(img, px, py + r + 30, 'Сонце', 30, fill=(255, 225, 170), a=k * (1 - ramp(t, 27.4, 28.2)))
    label(img, W / 2, 560, 'художня ілюстрація', 24, fill=(190, 198, 215), a=win(t, 20.0, 28.6, 0.6) * 0.85)
    return img.convert('RGB')

# ---------------------------------------------------------------- E/F: the helices, the myth
V = nrm([math.cos(math.radians(59)), 0, math.sin(math.radians(59))])   # the Sun's motion: ~59° out of the planets' plane
SPEED = 3.2                                                             # AU per year (really ~49: compressed)
INNER = [p for p in PL if p[0] in ('mercury', 'venus', 'earth', 'mars')]
def tau_of(t): return 2.6 + (t - 29.2) * 0.34                            # years of simulated time
def real_pos(name, a, T, lon0, tau):
    th = math.radians(lon0) + 2 * math.pi * tau / T
    return V * SPEED * tau + a * np.array([math.cos(th), math.sin(th), 0.0])
# the myth: orbits square to the motion, each planet lagging behind the Sun in a cone
E1 = nrm(np.cross(V, [0, 1, 0])); E2 = np.cross(V, E1)
def myth_pos(name, a, T, lon0, tau):
    th = math.radians(lon0) + 2 * math.pi * tau / T
    return V * SPEED * tau - V * a * 3.2 + a * (math.cos(th) * E1 + math.sin(th) * E2)

def shot_EF(t):
    tau = tau_of(t)
    my = ramp(t, 39.6, 40.4) * (1 - ramp(t, 42.6, 44.0))         # how much of the myth is shown
    S = V * SPEED * tau
    # camera: beside the path, the motion pointing up the screen, slowly swinging round
    sw = math.radians(-60 + (t - 29.2) * 3.0)
    side = nrm(math.cos(sw) * np.cross(V, [0, 0, 1]) + math.sin(sw) * E2 * 0.8 + np.cross(V, [0, 0, 1]) * 0.2)
    tgt = S - V * 2.4
    cam = Cam(tgt + side * 7.2, tgt, fov=48, up=V)
    cv = stars_bg(dx=(t - 29) * 10, dy=(t - 29) * 40, k=0.7)
    def P(p, tt): return (1 - my) * real_pos(*p, tt) + my * myth_pos(*p, tt)
    # trails: the last 3 years of each path
    segs_e, segs_o = [], []
    for p in INNER:
        taus = np.linspace(max(0.0, tau - 3.0), tau, 260)
        pts = np.array([P((p[0], p[1], p[4], p[5]), tt) for tt in taus])
        x, y, z = cam.proj(pts)
        fade = np.linspace(0, 1, len(taus)) ** 1.4
        seg = [([(x[j], y[j]), (x[j + 1], y[j + 1])], fade[j]) for j in range(len(taus) - 1) if z[j] > 0.1]
        (segs_e if p[0] == 'earth' else segs_o).extend(seg)
    lines(cv, segs_o, tuple(np.array([0.85, 0.88, 0.95]) * (1 - my) + np.array([1.0, 0.45, 0.4]) * my), width=2, k=0.55)
    lines(cv, segs_e, tuple(np.array([0.35, 0.65, 1.0]) * (1 - my) + np.array([1.0, 0.4, 0.35]) * my), width=3, k=1.0)
    # the Sun's own path: a straight glowing line
    x, y, z = cam.proj(np.array([S - V * 12, S]))
    lines(cv, [([(x[0], y[0]), (x[1], y[1])], 1.0)], (1.0, 0.8, 0.5), width=2, k=0.35)
    xs, ys, zs = cam.proj(S)
    add(cv, sun_sprite(16, glow=1.0, t=t), xs[0], ys[0])
    img_l = []
    for p in INNER:
        pp = P((p[0], p[1], p[4], p[5]), tau)
        x, y, z = cam.proj(pp)
        r = {'mercury': 7, 'venus': 10, 'earth': 11, 'mars': 8}[p[0]]
        g = globe(p[0], r, cam.r, cam.u, -cam.f, nrm(S - pp), spin=t * 0.4)
        over(cv, g, x[0], y[0]); img_l.append((p[0], x[0], y[0]))
    img = to_img(cv).convert('RGBA')
    for n, x, y in img_l:
        if n == 'earth': label(img, x + 46, y - 22, 'Земля', 28, fill=(150, 200, 255), a=win(t, 34.8, 44.4, 0.5))
    return img.convert('RGB')

# ---------------------------------------------------------------- G: the Earth and the Moon
def shot_G(t):
    cv = stars_bg(dx=(t - 44) * 6, dy=(t - 44) * 26, k=0.8)
    cam = Cam([0, -10, 0], [0, 0, 0], fov=30)
    L = nrm([-1.0, 0.35, 0.25])
    rz = 330 * (1 + 0.025 * (t - 44.5))
    over(cv, globe('moon', 70, cam.r, cam.u, -cam.f, L, spin=0.3), 250 - (t - 44.5) * 4, 470)
    over(cv, globe('earth', rz, cam.r, cam.u, -cam.f, L, spin=1.2 + 0.06 * (t - 44.5)), W / 2 + 40, 1040)
    return to_img(cv)
PLF['moon'] = 'moon.jpg'

# ---------------------------------------------------------------- the timeline: shots and the dissolves between them
SHOTS = [(0.0, 4.9, shot_A), (4.6, 11.6, shot_B), (11.2, 19.8, shot_C), (19.4, 29.8, shot_D), (29.2, 44.9, shot_EF),
         (44.5, 99, shot_G)]
def frame(t):
    act = [(a, b, f) for a, b, f in SHOTS if a <= t <= b]
    if len(act) == 1: return act[0][2](t)
    (a1, b1, f1), (a2, b2, f2) = act[0], act[-1]
    k = sm((t - a2) / (b1 - a2))
    return Image.blend(f1(t), f2(t), k)

def job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return
    frame(i / FPS).save(p, quality=93)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * FPS)
    todo = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()) as pool:
        for c, _ in enumerate(pool.imap_unordered(job, todo, chunksize=2)):
            if c % 60 == 0: print('frame', c, '/', len(todo), flush=True)
    print('frames done', n)
