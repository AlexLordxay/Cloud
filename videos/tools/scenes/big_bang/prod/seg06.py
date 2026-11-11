# Segment 6 — К7 + К8 (0:59.8–1:19.6).
#   К7 «І ось головне: це не галактики розлітаються в порожнечі — це росте сам простір. З будь-якої галактики здається,
#      що всі інші тікають саме від неї»: real galaxies cut from the Hubble Ultra Deep Field (NASA/ESA), set in 3D.
#      Space grows (comoving coordinates, a = exp(H t)): seen from our galaxy every other one recedes, shrinks and
#      reddens (redshift) — the camera then flies to another galaxy, and from there it is the same picture.
#   К8 «Тому у Великого вибуху немає центру. Він стався всюди — і там, де зараз ти, теж»: the camera dives into a
#      spiral galaxy (a real photograph) — into an arm, towards one ordinary yellow star — and its light whites out
#      the frame (seg07 comes out of this white).
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx

T0, T1 = 59.8, 79.6
K7, K8 = 59.8, fx.shot('К8')[0]                     # 71.58
HOP0, HOP1 = 65.6, 69.6                           # the flight to another galaxy
HUB = 0.075
FOV = math.radians(58)
CACHE = os.path.join(fx.BB, 'render', 'cache_hudf_sprites.npz')
_rng = np.random.default_rng(6)
_S = None


def sprites():
    """galaxies cut from the HUDF: patches around connected bright regions, soft-edged (cached)"""
    global _S
    if _S is not None: return _S
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True); _S = list(z['s']); return _S
    img = fx.load('hudf.jpg', 6200)
    g = cv2.GaussianBlur(img.mean(-1), (0, 0), 2.0)
    bg = np.median(g)
    m = (g > bg + 0.012).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    out = []
    order = np.argsort(-st[1:, cv2.CC_STAT_AREA]) + 1
    for i in order[:260]:
        x, y, w, h, area = st[i]
        if area < 260 or w > 900 or h > 900: continue
        s = int(max(w, h) * 1.5) + 8
        cx, cy = x + w / 2, y + h / 2
        x0, y0 = int(cx - s / 2), int(cy - s / 2)
        if x0 < 0 or y0 < 0 or x0 + s > img.shape[1] or y0 + s > img.shape[0]: continue
        p = img[y0:y0 + s, x0:x0 + s].copy()
        p = np.clip(p - bg * 1.05, 0, None)                      # sky to black (additive sprites)
        yy, xx = np.mgrid[0:s, 0:s]
        r = np.hypot(xx - s / 2, yy - s / 2) / (s / 2)
        p *= np.clip((1 - r) / 0.35, 0, 1)[..., None]
        out.append(p.astype(np.float32))
    np.savez_compressed(CACHE, s=np.array(out, dtype=object))
    _S = out
    return _S


def scale(T): return math.exp(HUB * (T - K7))


_SP = {}


def spiral_sprite(n):
    # the spiral photograph as a sprite: sky subtracted, a soft round edge
    if n not in _SP:
        im = fx.load('spiral_galaxy.jpg', n).copy()
        bg = np.percentile(im.reshape(-1, 3), 30, axis=0)
        im = np.clip(im - bg * 1.1, 0, None)
        s = im.shape[0]; yy, xx = np.mgrid[0:s, 0:im.shape[1]]
        r = np.hypot(xx - im.shape[1] / 2, yy - s / 2) / (s / 2)
        im *= np.clip((0.98 - r) / 0.25, 0, 1)[..., None]
        _SP[n] = im.astype(np.float32)
    return _SP[n]


ARM = np.array([0.24, 0.12, 0.0])                 # where in galaxy 1 we dive (a point in an arm), in its size units


# the galaxies: comoving positions; 0 = our galaxy (the camera starts just behind it), 1 = the one we fly to
_rngp = np.random.default_rng(11)
N = 420
POS = np.c_[_rngp.uniform(-26, 26, N), _rngp.uniform(-15, 15, N), _rngp.uniform(-6, 60, N)]
POS[0] = (0.0, -0.35, 1.6); POS[1] = (3.2, 0.9, 9.0)
SIZE = np.exp(_rngp.normal(0, 0.35, N)) * 0.55; SIZE[0] = 1.1; SIZE[1] = 1.0
PICK = _rngp.integers(0, 10 ** 6, N)
ROT = _rngp.uniform(0, 2 * math.pi, N)


def cam(T):
    """comoving camera position and its gaze"""
    A = np.array([0.0, 0.0, 0.0]); B = POS[1] + np.array([-0.2, -0.65, -1.7])
    k = fx.smoother((T - HOP0) / (HOP1 - HOP0))
    c = A + (B - A) * k + np.array([0.15 * math.sin(0.3 * T), 0.08 * math.sin(0.23 * T), 0])
    look = np.array([0.0, 0.0, 1.0]) * (1 - k) + (POS[1] - B) / np.linalg.norm(POS[1] - B) * k
    if T > K8:                                        # the dive into galaxy 1, towards a point in an arm
        d = fx.smoother((T - K8) / 5.2)
        tgt = POS[1] + ARM * SIZE[1] - np.array([0, 0, 0.004])
        c = c + (tgt - c) * d
    look = look / np.linalg.norm(look)
    return c, look


def frame(T):
    S = sprites()
    W, H = fx.W, fx.H
    img = np.zeros((H, W, 3), np.float32)
    a = scale(T)
    c, fw = cam(T)
    up0 = np.array([0, 1.0, 0])
    rt = np.cross(up0, fw); rt /= np.linalg.norm(rt); up = np.cross(fw, rt)
    rel = (POS - c) * a
    z = rel @ fw; x = rel @ rt; y = rel @ up
    f = (H / 2) / math.tan(FOV / 2)
    order = np.argsort(-z)
    spiral = spiral_sprite(2400)
    for i in order:
        if z[i] < 0.05: continue
        px = W / 2 + x[i] / z[i] * f; py = H / 2 - y[i] / z[i] * f
        size = SIZE[i] * a ** 0 / z[i] * f                       # physical size stays: bound galaxies don't expand
        if size < 1.2: continue
        if px + size < 0 or px - size > W or py + size < 0 or py - size > H: continue
        spr = spiral if i == 1 else S[PICK[i] % len(S)]
        # redshift: the farther (the faster it recedes), the redder and dimmer
        q = min(z[i] / 40.0, 1.0) * fx.ramp(T, K7, K7 + 3.0) * (0.4 + 0.6 * min(a - 1, 1))
        tint = np.array([1.0, 1 - 0.45 * q, 1 - 0.75 * q], np.float32)
        dim = math.exp(-z[i] / 55.0) * (0.55 if i == 0 else 1.1 if i == 1 else 1.0)
        s = int(size)
        if s < 2: continue
        sc = s / spr.shape[0]
        if s > 2600:                                              # too big for a sprite: warp straight into the frame
            spr = spiral_sprite(5000) if i == 1 else spr
            sc = s / spr.shape[0]
            lay = fx.warp(spr, spr.shape[1] / 2, spr.shape[0] / 2, sc, 0.0, sx=px, sy=py)
            img += lay * tint * dim
            continue
        small = cv2.resize(spr, (s, s), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
        if i not in (1,):
            M = cv2.getRotationMatrix2D((s / 2, s / 2), math.degrees(ROT[i]), 1.0)
            small = cv2.warpAffine(small, M, (s, s))
        x0, y0 = int(px - s / 2), int(py - s / 2)
        xa, ya = max(x0, 0), max(y0, 0); xb, yb = min(x0 + s, W), min(y0 + s, H)
        if xb <= xa or yb <= ya: continue
        img[ya:yb, xa:xb] += small[ya - y0:yb - y0, xa - x0:xb - x0] * (tint * dim * 2.2)
    # К8: into the arm — a yellow star swells and whites out the frame
    if T > K8 + 3.0:
        k = fx.ramp(T, K8 + 3.0, T1 - 0.4)
        ra = (POS[1] + ARM * SIZE[1] - c) * a
        zz = max(ra @ fw, 1e-3)
        p = (W / 2 + (ra @ rt) / zz * f, H / 2 - (ra @ up) / zz * f)
        r = 3 + 2600 * k ** 3
        yy, xx = np.ogrid[0:H, 0:W]
        d2 = ((xx - p[0]) ** 2 + (yy - p[1]) ** 2) / (r * r)
        img += (np.exp(-d2) * (2.0 + 10 * k ** 2)).astype(np.float32)[..., None] * np.array([1.0, 0.9, 0.7], np.float32)
        img += (0.02 * (1 + 30 * k ** 2) / (1 + d2 * 0.05)).astype(np.float32)[..., None] * np.array([1.0, 0.85, 0.6], np.float32)
    fin = fx.ramp(T, T0, T0 + 0.8)
    return fx.finish(img * (0.25 + 0.75 * fin), _rng, exposure=1.1, thr=0.5, vig=0.26, grain=0.011)
