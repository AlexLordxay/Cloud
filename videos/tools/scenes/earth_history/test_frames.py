# Test stills for «Історія Землі» (16:9): python3 test_frames.py [name …]
import math, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SUN = os.path.join(os.path.dirname(HERE), 'sun_imagine')
sys.path.insert(0, SUN); sys.path.insert(0, HERE)
import common as cm
cm.W, cm.H = 1920, 1080
import earthk
from overlay import draw_clock, draw_stamp
W, H = cm.W, cm.H
OUT = os.path.join(HERE, 'test'); os.makedirs(OUT, exist_ok=True)
GAL = cm.rot_axis([0.3, 1.0, 0.2], 2.2)

def finish(img, name, layers=None, expo=1.0):
    img = cm.bloom(img, thr=0.9, k=0.5)
    img = cm.vignette(cm.tonemap(img, expo), 0.25)
    im = Image.fromarray(cm.to_u8(img)).convert('RGBA')
    if layers: layers(im)
    im.convert('RGB').save(os.path.join(OUT, name + '.jpg'), quality=92); print(name)

def night_earth(lat=48.5, lon=31.0, alt=1900.0, back=0.0):
    up = cm.ll(lat, lon); east = np.array([-math.sin(math.radians(lon)), math.cos(math.radians(lon)), 0.0]); north = np.cross(up, east)
    o = up * (earthk.RE + alt) - north * 2600.0 - east * 600.0 * back
    tgt = up * earthk.RE + north * 900.0
    c = cm.cam(o, tgt, up, 52.0)
    img = np.zeros((H, W, 3), np.float32)
    cm.sky(img, c, GAL, 0.6, stars=1.0, band=0.25)
    sun = cm.ll(12.0, lon + 108.0)                              # dawn line near the Caspian: lights on the left, sunrise on the right
    earthk.earth(img, c, sun, sun_k=18.0, disc_k=0.0, cloud_k=0.7, night_k=1.8, fields=0.0, home=(lat, lon), expo=0.9)
    return img

def hook():
    img = night_earth()
    def lay(im):
        draw_clock(im, 23.0 + 59 / 60 + 54 / 3600, 3.0e5, W - 170, 120, 70)
        draw_stamp(im, 'УКРАЇНА', 760, 610, 58, 1.0)
    finish(img, 'p1_hook', lay)


# ---------------------------------------------------------------- Theia: the impact moment
def _hash3(ix, iy, iz):
    n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFFFF).astype(np.float32) / 0xFFFFFF

def vnoise3(p):
    q = np.floor(p).astype(np.int64); f = p - q; f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * _hash3(q[..., 0] + dx, q[..., 1] + dy, q[..., 2] + dz)
    return out

def fbm3(p, o=5):
    a, s, t = 0.5, 1.0, 0
    for _ in range(o):
        t = t + a * vnoise3(p * s); s *= 2.03; a *= 0.5
    return t

def sphere_hit(D, C, R):
    b = D @ C; c = C @ C - R * R; disc = b * b - c
    m = disc > 0; t = np.where(m, b - np.sqrt(np.maximum(disc, 0)), np.inf)
    m &= t > 0
    return m, t

def theia(name='p2_theia', k_imp=1.0):
    c = cm.cam([0, 0, 0], [0, 0, 1], [0, 1, 0], 33.0)
    img = np.zeros((H, W, 3), np.float32)
    cm.sky(img, c, GAL, 0.6, stars=1.0, band=0.35)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = c[4]
    D = np.stack([(xx - W / 2) / k, -(yy - H / 2) / k, np.ones_like(xx)], -1); D /= np.linalg.norm(D, axis=-1, keepdims=True)
    L = cm.nrm([-0.85, 0.35, 0.25])                                  # the young Sun, upper left
    E_C, E_R = np.array([-0.95, -0.15, 7.0]), 1.35
    T_C, T_R = np.array([0.55, 0.32, 6.75]), 0.72
    hitE, tE = sphere_hit(D, E_C, E_R); hitT, tT = sphere_hit(D, T_C, T_R)
    useE = hitE & (tE <= tT); useT = hitT & (tT < tE)
    contact = E_C + cm.nrm(T_C - E_C) * E_R
    for use, t, C, R, kind in ((useE, tE, E_C, E_R, 'E'), (useT, tT, T_C, T_R, 'T')):
        P = D[use] * t[use][:, None]; N = (P - C) / R
        dif = np.clip(N @ L, 0, 1)[:, None]
        n = fbm3(N * 3.2 + (0 if kind == 'E' else 11.0), 6)
        if kind == 'E':     # a magma ocean: dark crust plates, glowing seams
            crust = np.stack([0.06 + 0.05 * n, 0.045 + 0.035 * n, 0.04 + 0.025 * n], -1)
            seam = np.clip(1 - np.abs(fbm3(N * 6.0 + 3.0, 5) - 0.5) * 9.0, 0, 1) ** 3
            glow = np.array([2.2, 0.55, 0.10]) * (seam[:, None] * 0.75 + 0.015)
        else:               # Theia: an older, cratered grey-brown crust
            n2 = fbm3(N * 14.0 + 5.0, 4); cr = np.clip(1 - np.abs(n2 - 0.5) * 7, 0, 1) ** 4
            v = 0.05 + 0.10 * n + 0.05 * n2 - 0.03 * cr
            crust = np.stack([v * 1.15, v * 1.0, v * 0.86], -1)
            glow = np.zeros_like(crust)
        # heat near the contact point: both bodies glow there
        dc = np.linalg.norm(P - contact, axis=-1)
        heat = np.exp(-(dc / 0.32) ** 2)[:, None] * k_imp
        col = crust * (dif * 3.0 + 0.012) + glow * (1 - 0.5 * dif) + np.array([4.0, 1.3, 0.3]) * heat * (0.5 + 0.9 * n[:, None])
        img[use] = col
    # the impact flash and the plume of molten rock, splashed out along the tangent
    px, py, _ = cm.project(c, contact)
    px, py = float(px[0]), float(py[0])
    r2 = (xx - px) ** 2 + (yy - py) ** 2
    img += (np.exp(-r2 / (2 * 26.0 ** 2)) * 9 + np.exp(-r2 / (2 * 110.0 ** 2)) * 0.9 + np.exp(-r2 / (2 * 420.0 ** 2)) * 0.06)[..., None] * np.array([1.0, 0.62, 0.3]) * k_imp
    rng = np.random.default_rng(7)
    tang = cm.nrm(np.cross(T_C - E_C, [0, 0, 1]))
    for i in range(9000):
        s = rng.normal(0, 1); u = rng.uniform(0.05, 1.0) ** 1.6
        q = contact + tang * s * u * 1.6 + cm.nrm(T_C - E_C) * rng.normal(0, 0.18) * u + np.array([0, 0, -1]) * rng.uniform(0, 0.4) * u
        X, Y, Z = cm.project(c, q); X, Y = int(X[0]), int(Y[0])
        if 1 <= X < W - 1 and 1 <= Y < H - 1:
            b = (1.4 - u) * rng.uniform(0.6, 1.4) * k_imp
            img[Y - 1:Y + 1, X - 1:X + 1] += np.array([2.2, 0.8, 0.22]) * b
    finish(img, name, lambda im: (draw_clock(im, 0.21, 4.5e9, W - 170, 120, 70), draw_stamp(im, "ТЕЙЯ", 1480, 330, 58, 1.0)), expo=0.9)

if __name__ == '__main__':
    for n in (sys.argv[1:] or ['hook']): globals()[n]()
