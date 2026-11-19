# Small 2D helpers for «А ти уявляєш Сонце так?»: glowing anti-aliased lines (the scales, the light streaks) and lit
# planet globes (textures of the site: Solar System Scope, CC BY 4.0; the Earth — NASA).
import math, os
import numpy as np
from PIL import Image
from common import W, H, TEX

def glow_lines(img, segs, col, core=1.0, glow=1.0):
    """segs: [(points [(x, y), …], width px)]; additive: a sharp core plus a soft glow"""
    from scipy.ndimage import gaussian_filter
    from PIL import ImageDraw
    m = Image.new('L', (W * 2, H * 2), 0)
    d = ImageDraw.Draw(m)
    for pts, w in segs:
        p2 = [(x * 2, y * 2) for x, y in pts]
        d.line(p2, fill=255, width=max(1, int(w * 2)), joint='curve')
        for x, y in p2:
            d.ellipse([x - w, y - w, x + w, y + w], fill=255)
    a = np.asarray(m.resize((W, H), Image.LANCZOS), np.float32) / 255
    g = gaussian_filter(a, 6) * 1.6 + gaussian_filter(a, 18) * 1.2
    img += (a * core + g * glow)[..., None] * np.asarray(col, np.float32)

_T = {}
FILES = {'earth': 'earth_day.jpg', 'jupiter': 'jupiter.jpg', 'saturn': 'saturn.jpg', 'uranus': 'uranus.jpg',
         'neptune': 'neptune.jpg', 'venus': 'venus_atmosphere.jpg', 'mars': 'mars.jpg', 'mercury': 'mercury.jpg'}
def tex(name):
    if name not in _T:
        _T[name] = np.asarray(Image.open(os.path.join(TEX, FILES[name])).convert('RGB'), np.float32) / 255
        if name == 'saturn':
            r = np.asarray(Image.open(os.path.join(TEX, 'saturn_ring.png')).convert('RGBA'), np.float32) / 255
            _T['ring'] = r[r.shape[0] // 2]
    return _T[name]

def planet(img, name, rp, cx, cy, a=1.0, light=(-0.7, 0.3, 0.65), spin=0.0, gain=1.25):
    """a lit globe of radius rp px at (cx, cy), alpha a; Saturn gets its rings"""
    t = tex(name); th, tw = t.shape[:2]
    ring = name == 'saturn'
    pad = 2.4 if ring else 1.1
    S = max(5, int(rp * 2 * pad + 6))
    yy, xx = (np.mgrid[0:S, 0:S] - S / 2 + 0.5) / max(rp, 0.6)
    x = xx; y = -yy
    rr = x * x + y * y
    z = np.sqrt(np.clip(1 - rr, 0, 1))
    tilt = math.radians(26.7) if ring else 0.0
    # a tilted axis: rotate (x, y) by the tilt for the texture lookup
    xt = x * math.cos(tilt) + y * math.sin(tilt); yt = -x * math.sin(tilt) + y * math.cos(tilt)
    lat = np.arcsin(np.clip(yt, -1, 1)); lon = np.arctan2(xt, z) + spin
    col = t[((0.5 - lat / np.pi) * (th - 1)).astype(int).clip(0, th - 1), (((lon / (2 * np.pi)) % 1) * (tw - 1)).astype(int).clip(0, tw - 1)]
    L = np.asarray(light, float); L = L / np.linalg.norm(L)
    lam = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1)
    rgb = col * (0.04 + gain * lam[..., None] ** 0.9)
    if name == 'earth':
        rgb += np.array([0.25, 0.5, 1.0]) * ((1 - z) ** 2.5 * np.clip(lam + 0.2, 0, 1))[..., None] * 0.6
    al = np.clip((1 - np.sqrt(rr)) * max(rp, 0.6) + 0.5, 0, 1)
    if rp < 1.0: al = al * rp
    if ring:
        # the ring plane seen slightly from above: an ellipse, ratio 0.28
        rx_ = xt; ry_ = yt / 0.28
        rho = np.sqrt(rx_ * rx_ + ry_ * ry_)
        rt = _T['ring']; kq = (rho - 1.24) / (2.27 - 1.24)
        on = (kq >= 0) & (kq <= 1)
        ri = (kq.clip(0, 1) * (len(rt) - 1)).astype(int)
        ra = rt[ri, 3] * on
        behind = (yt > 0) & (rr < 1)                                  # the far half of the ring hides behind the globe
        ra = np.where(behind, 0, ra)
        rgb = rgb * (1 - ra[..., None]) + rt[ri, :3] * 0.9 * ra[..., None]
        al = np.maximum(al, ra)
    al = al * a
    x0 = int(round(cx - S / 2)); y0 = int(round(cy - S / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + S), min(H, y0 + S)
    if xa < xb and ya < yb:
        sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
        A = al[sl][..., None]
        img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - A) + rgb[sl] * A
