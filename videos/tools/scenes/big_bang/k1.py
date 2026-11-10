# «Великий вибух» — К1 (0:00–0:05.6, the hook): the first frame is already flying through endless space filled with a
# glowing grey-gold haze of dense matter, thousands of luminous clumps in it. Space STRETCHES while we fly: the haze's
# pattern widens and the gaps between the clumps grow — all at once, in every direction; the clumps themselves keep
# their size (bound things do not expand, only the space between them — as in physics). Volumetric light, depth,
# a barely felt tremor. Science film, not a cartoon: no lines, no arrows.
#
# How: comoving coordinates. The scale factor a(t) = exp(H t); a point at comoving x sits at physical a(t)(x - c(t))
# from the camera, c(t) the camera's comoving position (it flies at a constant physical speed V, so dc/dt = V / a).
#   haze   — ray-marched emission + absorption through an fBm density field in comoving coordinates (half resolution,
#            numba, parallel), so the pattern itself stretches;
#   clumps — ~10 000 glowing cores scattered where the haze is dense, splatted as Gaussians of FIXED physical size;
#   post   — bloom (3 widths), filmic tone map, light grain and vignette.
#   python3 k1.py                -> test/k1/f_####.jpg (5.6 s at 30 fps) + test/k1_still_*.jpg + test/k1.mp4
#   python3 k1.py --still 1.5    -> one frame at t = 1.5 s (test/k1_still_1.50.jpg)
import math, os, sys, subprocess
import numpy as np
from numba import njit, prange
from scipy import ndimage
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'test')
W, H = 1920, 1080
HW, HH = W // 2, H // 2                 # the haze is marched at half resolution
FPS = 30
DUR = 5.6
FOV = math.radians(62)
HUB = 0.16                              # a(t) = exp(HUB t): ×2.45 over the shot
V = 2.6                                 # the camera's physical speed (units/s)
FOG = 11.0                              # the haze's mean free path (units) — how far one sees into it
SMAX = 34.0                             # the march length
NSTEP = 110
SEED = 7
ROT = (0.939209, -0.342924, -0.017026, 0.150755, 0.367325, 0.917794, -0.308480, -0.864567, 0.396692)   # a fixed random rotation: no grid-aligned features


# ------------------------------------------------------------------------------------------------------- the noise
@njit(cache=True, inline='always')
def _h(i, j, k):
    n = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791) ^ 0x5bd1e995
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0xffffff) / 16777215.0


@njit(cache=True, inline='always')
def vnoise(x, y, z):
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    ux = fx * fx * (3 - 2 * fx); uy = fy * fy * (3 - 2 * fy); uz = fz * fz * (3 - 2 * fz)
    i, j, k = int(ix), int(iy), int(iz)
    a = _h(i, j, k) + (_h(i + 1, j, k) - _h(i, j, k)) * ux
    b = _h(i, j + 1, k) + (_h(i + 1, j + 1, k) - _h(i, j + 1, k)) * ux
    c = _h(i, j, k + 1) + (_h(i + 1, j, k + 1) - _h(i, j, k + 1)) * ux
    d = _h(i, j + 1, k + 1) + (_h(i + 1, j + 1, k + 1) - _h(i, j + 1, k + 1)) * ux
    return (a + (b - a) * uy) + ((c + (d - c) * uy) - (a + (b - a) * uy)) * uz


@njit(cache=True)
def density(x, y, z):
    # a soft, filamentary fBm: a domain-warped base + ridged detail; ~0..1.5
    s = 0.33
    r0, r1, r2, r3, r4, r5, r6, r7, r8 = ROT
    x, y, z = r0 * x + r1 * y + r2 * z, r3 * x + r4 * y + r5 * z, r6 * x + r7 * y + r8 * z
    wx = vnoise(x * 0.21 + 3.1, y * 0.21, z * 0.21) - 0.5
    wy = vnoise(x * 0.21, y * 0.21 + 7.7, z * 0.21) - 0.5
    x2, y2, z2 = x + 2.2 * wx, y + 2.2 * wy, z + 1.4 * (wx - wy)
    f = 0.0; amp = 0.55; fr = s
    r0, r1, r2, r3, r4, r5, r6, r7, r8 = ROT
    for o in range(4):
        # each octave turned by the rotation again (the value noise's lattice would otherwise line up with the view
        # and show as streaks running to the vanishing point)
        x2, y2, z2 = r0 * x2 + r1 * y2 + r2 * z2, r3 * x2 + r4 * y2 + r5 * z2, r6 * x2 + r7 * y2 + r8 * z2
        n = vnoise(x2 * fr + 17.3 * o, y2 * fr, z2 * fr)
        if o >= 2:
            n = 1.0 - abs(2.0 * n - 1.0)          # ridges: thin bright sheets and threads
        f += amp * n; amp *= 0.5; fr *= 2.03
    d = f - 0.47
    return d * 3.2 if d > 0 else 0.0


# ------------------------------------------------------------------------------------------------------- the haze
@njit(parallel=True, cache=True)
def march(img, cc0, cc1, cc2, fw, rt, up, a, tanh, aspect, nstep, smax, fog, jit):
    h, w = img.shape[0], img.shape[1]
    ds = smax / nstep
    for py in prange(h):
        for px in range(w):
            sx = (2.0 * (px + 0.5) / w - 1.0) * tanh * aspect
            sy = (1.0 - 2.0 * (py + 0.5) / h) * tanh
            dx = fw[0] + rt[0] * sx + up[0] * sy
            dy = fw[1] + rt[1] * sx + up[1] * sy
            dz = fw[2] + rt[2] * sx + up[2] * sy
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            T = 1.0; r = 0.0; g = 0.0; b = 0.0
            u0 = _h(px, py, jit)                            # jittered start (no banding)
            for k in range(nstep):
                # steps grow with distance: fine near the camera (no aliasing of the detail), coarse in the deep
                q0 = (k + u0) / nstep; q1 = (k + 1 + u0) / nstep
                s = smax * q0 * q0; ds = smax * (q1 * q1 - q0 * q0)
                # physical distance s -> comoving position
                x = cc0 + dx * s / a; y = cc1 + dy * s / a; z = cc2 + dz * s / a
                d = density(x, y, z)
                if d > 0.0:
                    sig = d * 0.045                       # extinction: optically thin -> brightness follows the column
                    em = d * d * 0.030                        # emission (the haze glows by itself: it is hot)
                    # colour: thin -> grey-gold, dense -> warm white-gold
                    hot = min(d, 1.0)
                    cr = 1.00; cg = 0.56 + 0.28 * hot; cb = 0.22 + 0.40 * hot
                    att = math.exp(-sig * ds)
                    w_ = T * em * ds
                    r += w_ * cr; g += w_ * cg; b += w_ * cb
                    T *= att
                    if T < 0.01:
                        break
            # the deep glow beyond the march (the haze never ends)
            r += T * 0.006; g += T * 0.0045; b += T * 0.003
            img[py, px, 0] = r; img[py, px, 1] = g; img[py, px, 2] = b
            img[py, px, 3] = T


# ------------------------------------------------------------------------------------------------------- the clumps
def make_clumps():
    rng = np.random.default_rng(SEED)
    n = 220000
    p = np.empty((n, 3))
    p[:, 0] = rng.uniform(-22, 22, n); p[:, 1] = rng.uniform(-14, 14, n); p[:, 2] = rng.uniform(-4, 58, n)
    d = np.array([density(*q) for q in p])
    keep = rng.uniform(0, 1, n) < np.clip(d, 0, 1.4) ** 2 * 0.07
    p = p[keep]
    m = len(p)
    size = 0.035 * np.exp(rng.normal(0, 0.45, m))                       # physical radius — fixed
    lum = np.exp(rng.normal(0, 0.55, m)) * (0.7 + 0.6 * np.clip(d[keep], 0, 1.2))
    warm = rng.uniform(0, 1, m)
    return p, size, lum, warm


@njit(cache=True)
def splat(img, Tmap, px, py, rad, inten, cr, cg, cb, depth_px_scale):
    h, w = img.shape[0], img.shape[1]
    for i in range(px.shape[0]):
        r = rad[i]
        R = int(r * 3.2 + 1.5)
        x0 = int(px[i]); y0 = int(py[i])
        if x0 + R < 0 or x0 - R >= w or y0 + R < 0 or y0 - R >= h:
            continue
        inv = 1.0 / (2.0 * r * r)
        for yy in range(max(0, y0 - R), min(h, y0 + R + 1)):
            for xx in range(max(0, x0 - R), min(w, x0 + R + 1)):
                ddx = xx + 0.5 - px[i]; ddy = yy + 0.5 - py[i]
                q = (ddx * ddx + ddy * ddy) * inv
                if q > 10.0:
                    continue
                e = math.exp(-q) * inten[i]
                img[yy, xx, 0] += e * cr[i]; img[yy, xx, 1] += e * cg[i]; img[yy, xx, 2] += e * cb[i]


# ------------------------------------------------------------------------------------------------------- the camera
def basis(t):
    # forward along +z, a slow drift of the gaze, and a faint tremor (a few thousandths of a radian)
    yaw = 0.06 * math.sin(0.35 * t + 0.4) + 0.0016 * math.sin(23.0 * t) + 0.0011 * math.sin(37.0 * t + 1.0)
    pitch = 0.035 * math.sin(0.27 * t + 1.1) + 0.0013 * math.sin(29.0 * t + 2.0)
    roll = 0.05 * math.sin(0.22 * t) + 0.0008 * math.sin(31.0 * t)
    fw = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    wup = np.array([0.0, 1.0, 0.0])
    rt = np.cross(wup, fw); rt /= np.linalg.norm(rt)
    up = np.cross(fw, rt)
    c, s = math.cos(roll), math.sin(roll)
    return fw, rt * c + up * s, -rt * s + up * c


def scale(t): return math.exp(HUB * t)


def cam_c(t):
    # comoving camera position: dc/dt = V / a(t) along +z (plus a slow sideways drift)
    z = V * (1 - math.exp(-HUB * t)) / HUB
    return np.array([0.6 * math.sin(0.3 * t), 0.3 * math.sin(0.23 * t + 0.5), z])


# ------------------------------------------------------------------------------------------------------- post
def tonemap(a):
    x = (a * (2.51 * a + 0.03)) / (a * (2.43 * a + 0.59) + 0.14)
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def post(lin, t, rng):
    b = np.clip(lin - 0.35, 0, None)
    glow = sum(wt * ndimage.gaussian_filter(b, (r, r, 0)) for r, wt in ((3, 0.35), (14, 0.30), (55, 0.30)))
    x = lin + glow
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
    x = x * v[..., None] * 1.05
    out = tonemap(x)
    g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)
    out = out + g[..., None] * 0.012 * (0.4 + 0.6 * np.sqrt(np.clip(out, 0, 1)))
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def frame(t, CL, rng):
    a = scale(t); cc = cam_c(t); fw, rt, up = basis(t)
    tanh = math.tan(FOV / 2); aspect = W / H
    haze = np.zeros((HH, HW, 4), np.float32)
    march(haze, cc[0], cc[1], cc[2], fw, rt, up, a, tanh, aspect, NSTEP, SMAX, FOG, int(t * FPS) & 1023)
    big = np.stack([ndimage.zoom(haze[..., c], 2, order=1) for c in range(4)], -1)
    big = ndimage.gaussian_filter(big, (0.8, 0.8, 0))
    lin = big[..., :3].astype(np.float64).copy()

    p, size, lum, warm = CL
    rel = (p - cc) * a                                    # physical, from the camera
    z = rel @ fw; x = rel @ rt; y = rel @ up
    ok = z > 0.15
    z, x, y, size, lum, warm = z[ok], x[ok], y[ok], size[ok], lum[ok], warm[ok]
    f = (H / 2) / tanh
    px = W / 2 + x / z * f; py = H / 2 - y / z * f
    rad = np.clip(size / z * f, 0.6, 7.0)
    # the haze in front dims a clump (Beer–Lambert with the mean free path) and they fade in from the deep
    att = np.exp(-z / (FOG * 0.9)) * np.clip((SMAX - z) / 6, 0, 1) * np.clip((z - 0.6) / 2.0, 0, 1)
    # a Gaussian's total flux ~ (size/z)^2 -> its peak stays ~constant for resolved ones; unresolved ones dim as 1/z^2
    inten = lum * att * 2.4 * np.minimum(1.0, (size / z * f / 0.6) ** 2)
    cr = np.ones_like(warm); cg = 0.84 + 0.10 * warm; cb = 0.62 + 0.26 * warm
    order = np.argsort(-z)
    splat(lin, None, px[order], py[order], rad[order], inten[order], cr[order], cg[order], cb[order], 0.0)
    return post(lin, t, rng)


def main():
    os.makedirs(os.path.join(OUT, 'k1'), exist_ok=True)
    CL = make_clumps()
    print('clumps', len(CL[0]), flush=True)
    rng = np.random.default_rng(1)
    if '--still' in sys.argv:
        t = float(sys.argv[sys.argv.index('--still') + 1])
        Image.fromarray(frame(t, CL, rng)).save(os.path.join(OUT, f'k1_still_{t:.2f}.jpg'), quality=93)
        return
    n = int(round(DUR * FPS))
    for i in range(n):
        dst = os.path.join(OUT, 'k1', f'f_{i:04d}.jpg')
        if os.path.exists(dst):
            continue                                       # resumable
        Image.fromarray(frame(i / FPS, CL, rng)).save(dst, quality=93)
        if i % 10 == 0: print(i, '/', n, flush=True)
    for t in (0.0, 2.8, 5.5):
        src = os.path.join(OUT, 'k1', f'f_{int(t * FPS):04d}.jpg')
        Image.open(src).save(os.path.join(OUT, f'k1_still_{t:.2f}.jpg'), quality=93)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(OUT, 'k1', 'f_%04d.jpg'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                    os.path.join(OUT, 'k1.mp4')], check=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
