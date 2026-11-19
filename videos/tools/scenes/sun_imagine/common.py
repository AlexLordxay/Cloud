# Shared bits for «А ти уявляєш Сонце так?»: camera, the photographic sky sphere (ESO/S. Brunier Milky Way panorama),
# bloom and tone mapping.
import math, os
import numpy as np
import numba as nb
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'sun_imagine')
TEX = os.path.abspath(os.path.join(TOOLS, '../../planetarium/textures'))
W, H, FPS = 1080, 1920, 30

def sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def ramp(t, a, b): return sm((t - a) / (b - a))
def win(t, a, b, d=0.5): return min(ramp(t, a - d, a), 1 - ramp(t, b, b + d))
def lerp(a, b, k): return a + (b - a) * k
def lerpv(a, b, k): return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * k
def nrm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def ease(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def ll(lat, lon):
    a, b = math.radians(lat), math.radians(lon)
    return np.array([math.cos(a) * math.cos(b), math.cos(a) * math.sin(b), math.sin(a)])

def cam(o, target, up, fov):
    o = np.asarray(o, float); f = nrm(np.asarray(target, float) - o)
    r = nrm(np.cross(f, up)); u = np.cross(r, f)
    k = (H / 2) / math.tan(math.radians(fov) / 2)
    return (o, f, r, u, k)

def cam_dir(o, f, up, fov, roll=0.0):
    f = nrm(f); r = nrm(np.cross(f, up)); u = np.cross(r, f)
    if roll:
        c, s = math.cos(roll), math.sin(roll); r, u = r * c + u * s, -r * s + u * c
    k = (H / 2) / math.tan(math.radians(fov) / 2)
    return (np.asarray(o, float), f, r, u, k)

def project(c, X):
    o, f, r, u, k = c
    X = np.atleast_2d(np.asarray(X, float)) - o
    z = X @ f
    return W / 2 + k * (X @ r) / z, H / 2 - k * (X @ u) / z, z

# ---------------------------------------------------------------- the sky sphere
_S = {}
def sky_map():
    if 'm' not in _S:
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(os.path.join(TOOLS, 'data', 'sky', 'eso0932a.jpg')).convert('RGB')
        v = np.asarray(im, np.float32) / 255.0
        v = np.clip(v - 0.035, 0, 1) ** 1.25 * 1.05            # a deep black point; keep the band and the stars
        _S['m'] = np.ascontiguousarray(v)
    return _S['m']

@nb.njit(inline='always')
def _h2(a, b, c):
    # integer hash (no diagonal patterns), -> [0, 1)
    n = (int(a) * 73856093) ^ (int(b) * 19349663) ^ (int(c * 7.0 + 3.0) * 83492791)
    n = n & 0xFFFFFFFF
    n = ((n >> 16) ^ n) * 0x45d9f3b & 0xFFFFFFFF
    n = ((n >> 16) ^ n) * 0x45d9f3b & 0xFFFFFFFF
    n = (n >> 16) ^ n
    return (n & 0xFFFFFF) / 16777216.0

@nb.njit(parallel=True, fastmath=True)
def k_stars(out, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, M, gain, N):
    """crisp procedural stars, fixed on the sky: the sphere is cut into a cube map of N x N cells per face; each cell may
    hold a star (power-law brightness, a colour from the B-V spread); drawn as a gaussian ~0.8 px wide"""
    Hh, Ww = out.shape[0], out.shape[1]
    pix = 1.0 / k                                       # radians per pixel at the centre
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            gx = M[0, 0] * dx + M[0, 1] * dy + M[0, 2] * dz
            gy = M[1, 0] * dx + M[1, 1] * dy + M[1, 2] * dz
            gz = M[2, 0] * dx + M[2, 1] * dy + M[2, 2] * dz
            ax = abs(gx); ay = abs(gy); az = abs(gz)
            if ax >= ay and ax >= az: face = 0 if gx > 0 else 1; a = gy / ax; b = gz / ax
            elif ay >= az: face = 2 if gy > 0 else 3; a = gx / ay; b = gz / ay
            else: face = 4 if gz > 0 else 5; a = gx / az; b = gy / az
            ca = (a + 1) * 0.5 * N; cb = (b + 1) * 0.5 * N
            ia = int(ca); ib = int(cb)
            r_ = 0.0; g_ = 0.0; b_ = 0.0
            for di in range(-1, 2):
                for dj in range(-1, 2):
                    qa = ia + di; qb = ib + dj
                    h = _h2(qa, qb, face)
                    if h > 0.22: continue
                    sa = qa + _h2(qa, qb, face + 7.0); sb = qb + _h2(qa, qb, face + 13.0)
                    # distance in the face plane -> radians (approx: the face is ~2/N rad per cell near its centre)
                    da = (sa - ca) * 2.0 / N; db = (sb - cb) * 2.0 / N
                    d2 = (da * da + db * db) / (pix * pix)
                    if d2 > 9.0: continue
                    m = _h2(qa, qb, face + 3.0)
                    lum = 0.03 * (m ** -1.25 - 0.9) if m > 0.001 else 20.0
                    lum = min(lum, 5.0)
                    if lum < 0.02: continue
                    w = math.exp(-d2 / 0.75) * lum
                    bv = _h2(qa, qb, face + 21.0)
                    r_ += w * (0.85 + 0.30 * bv); g_ += w * (0.92 + 0.05 * bv); b_ += w * (1.15 - 0.40 * bv)
            out[j, i, 0] += r_ * gain; out[j, i, 1] += g_ * gain; out[j, i, 2] += b_ * gain

@nb.njit(parallel=True, fastmath=True)
def k_sky(out, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, M, sky, gain):
    """adds the panorama (equirectangular, galactic) for the camera's view directions; M: world -> galactic 3x3"""
    Hh, Ww = out.shape[0], out.shape[1]
    sh, sw = sky.shape[0], sky.shape[1]
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            gx = M[0, 0] * dx + M[0, 1] * dy + M[0, 2] * dz
            gy = M[1, 0] * dx + M[1, 1] * dy + M[1, 2] * dz
            gz = M[2, 0] * dx + M[2, 1] * dy + M[2, 2] * dz
            lon = math.atan2(gy, gx); lat = math.asin(min(1.0, max(-1.0, gz)))
            # galactic longitude grows to the left; the centre in the middle
            u = 0.5 - lon / (2 * math.pi); v = 0.5 - lat / math.pi
            x = (u % 1.0) * sw - 0.5; y = min(max(v * sh - 0.5, 0.0), sh - 1.001)
            x0 = int(math.floor(x)); y0 = int(y); ax = x - x0; ay = y - y0
            x0 = x0 % sw; x1 = (x0 + 1) % sw; y1 = min(y0 + 1, sh - 1)
            for c in range(3):
                a = sky[y0, x0, c]; b = sky[y0, x1, c]; cc = sky[y1, x0, c]; d = sky[y1, x1, c]
                out[j, i, c] += ((a * (1 - ax) + b * ax) * (1 - ay) + (cc * (1 - ax) + d * ax) * ay) * gain

def rot_axis(axis, ang):
    a = nrm(axis); c, s = math.cos(ang), math.sin(ang)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K

def sky_soft():
    """the panorama blurred: only the glow of the Milky Way band and its dust lanes (the stars are drawn crisp separately)"""
    if 's' not in _S:
        from scipy.ndimage import gaussian_filter
        m = sky_map()
        small = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((3000, 1500), Image.LANCZOS), np.float32) / 255
        _S['s'] = np.ascontiguousarray(gaussian_filter(small, (3.0, 3.0, 0)) * 0.8)
    return _S['s']

def sky(img, c, M, gain=1.0, stars=1.0, band=1.0):
    o, f, r, u, k = c
    M = np.ascontiguousarray(M, np.float64)
    if band > 0:
        k_sky(img, f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, M, sky_soft(), gain * band)
    if stars > 0:
        k_stars(img, f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, M, gain * stars, 300)

# ---------------------------------------------------------------- post
def bloom(img, thr=1.0, k=0.6, wide=1.0):
    from scipy.ndimage import gaussian_filter
    b = np.clip(img - thr, 0, 40).astype(np.float32)
    if b.max() <= 0: return img
    s = b.reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3))
    acc = (gaussian_filter(s, (2, 2, 0)) * 0.6 + gaussian_filter(s, (7, 7, 0)) * 0.45 +
           gaussian_filter(s, (22, 22, 0)) * 0.35 * wide + gaussian_filter(s, (60, 60, 0)) * 0.25 * wide)
    up = np.repeat(np.repeat(acc, 4, 0), 4, 1)
    return img + up * k

def tonemap(x, expo=1.0):
    y = 1 - np.exp(-np.maximum(x, 0) * 1.25 * expo)
    return np.clip(y, 0, 1) ** (1 / 1.9)

def vignette(img, k=0.28):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - k * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2
    return img * v[..., None]

def to_u8(a): return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
