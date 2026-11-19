# «А ти уявляєш Сонце так?» — every frame (1080x1920, 30 fps), one continuous camera with soft hand-overs (no cuts):
#   S1  0.0–8.0   a Ukrainian sunflower field at sunrise, the Sun yellow above it → the camera lifts off through the air:
#                 the sky darkens and the Sun turns white (the air's colour leaves it; physics: Rayleigh + Mie)
#   S2  7.4–10.6  the rush to the Sun: it grows from a disc to a world — limb darkening, granulation, spots
#   S3  10.2–15.0 1.3 million Earths: our Earth beside it (to scale), then the Sun turns to glass and fills with Earths
#   S4  14.6–20.0 the scales: the Sun against all the planets (to scale) — ×745 by mass
#   S5  19.6–25.2 a sunspot: dark only by contrast (on its own it glows); the biggest are bigger than the Earth
#   S6  24.8–31.6 a low flight over the boiling granules (5 500 °C) → up over the limb: a prominence, loops, the corona
#   S7  31.2–38.6 the camera rides the sunlight to the Earth (1 hour of it = a year of humanity's energy)
#   S8  37.6–43.2 down to Ukraine, to the same sunflower field: the Sun grows every plant and all your food
#   S9  42.6–50.2 the Sun vanishes — its last light still on its way: 8 min 20 s later the Earth goes dark
#   S10 50.0–58.4 the Sun lights up again; the camera flies to it; the end card
#   python3 render.py [workers] [frame …]    (numba kernels are parallel inside; 2 workers x 2 threads is a good mix)
import math, os, sys, json
import numpy as np
from PIL import Image
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import *
import sunk, arches, earthk, flowers

OUT = os.path.join(WORK, 'frames')
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']

# ---------------------------------------------------------------- the world
HOME = (49.0, 32.0)                                  # central Ukraine (Kirovohrad region — sunflower country)
UP, EAST, NORTH = earthk.local_axes(*HOME)
def dirn(el, az):
    e, a = math.radians(el), math.radians(az)
    return UP * math.sin(e) + (NORTH * math.cos(a) + EAST * math.sin(a)) * math.cos(e)
def loc(v): return np.array([v @ EAST, v @ NORTH, v @ UP])
SUN_EL, SUN_AZ = 10.0, 100.0
S = dirn(SUN_EL, SUN_AZ)                             # the direction to the Sun (Earth frame)
GAL = rot_axis([0.3, 1.0, 0.2], 2.2)                 # world -> galactic, chosen so the Milky Way crosses the sky behind
DISC = math.radians(0.9)                             # the Sun's disc as drawn from the Earth (enlarged from 0.27° to read)
FACE = 279.0                                         # the heads face the camera (the Sun behind them; petals glow)

# the Sun's body frame: spin axis ~ world z, the active region (lat 14, lon 20) turned towards the Earth
_a = -S
_phi = math.atan2(_a[1], _a[0]) - math.radians(20.0)
ROT = np.array([[math.cos(_phi), -math.sin(_phi), 0], [math.sin(_phi), math.cos(_phi), 0], [0, 0, 1.0]])
def sbody(lat, lon): return ROT @ ll(lat, lon)        # a body point in the world frame
SPOTS_B = [(14.0, 20.0, 0.020, 0.048, 1.0), (12.5, 26.5, 0.008, 0.019, 2.0), (15.8, 23.2, 0.004, 0.010, 4.0),
           (-9.0, -35.0, 0.011, 0.028, 3.0), (-11.0, -28.0, 0.005, 0.012, 5.0), (20.0, 70.0, 0.007, 0.017, 6.0)]
SPOTS = np.array([list(ll(a, b)) + [ru, rp, sd] for a, b, ru, rp, sd in SPOTS_B])   # in the body frame (k_sun takes rot)
SPOT_W = sbody(14.0, 20.0)

def logi(a, b, k): return math.exp(lerp(math.log(a), math.log(b), k))

def keys(t, ks):
    """piecewise smooth interpolation through (time, value) keys (value may be an array)"""
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0))
            return lerpv(v0, v1, k) if isinstance(v0, np.ndarray) else lerp(v0, v1, k)
    return ks[-1][1]

def logkeys(t, ks):
    """like keys, but log-linear in the value, with a monotone smooth step (for altitudes and distances)"""
    lk = [(a, math.log(b)) for a, b in ks]
    if t <= lk[0][0]: return ks[0][1]
    for i in range(len(lk) - 1):
        (t0, v0), (t1, v1) = lk[i], lk[i + 1]
        if t <= t1:
            u = (t - t0) / (t1 - t0)
            # Catmull-Rom-ish slopes in log space keep the speed continuous through the keys
            m0 = (v1 - lk[i - 1][1]) / (t1 - lk[i - 1][0]) if i > 0 else (v1 - v0) / (t1 - t0)
            m1 = (lk[i + 2][1] - v0) / (lk[i + 2][0] - t0) if i + 2 < len(lk) else (v1 - v0) / (t1 - t0)
            dt = t1 - t0
            h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
            return math.exp(h00 * v0 + h10 * dt * m0 + h01 * v1 + h11 * dt * m1)
    return ks[-1][1]

def slerp_dir(a, b, k):
    a = nrm(a); b = nrm(b)
    om = math.acos(max(-1.0, min(1.0, float(a @ b))))
    if om < 1e-6: return a
    return nrm((math.sin((1 - k) * om) * a + math.sin(k * om) * b) / math.sin(om))

# ---------------------------------------------------------------- the layers
def layer_sky(img, c, gain=1.0, stars=1.0, band=0.12):
    sky(img, c, GAL, gain, stars=stars, band=band)

def layer_earth(img, c, t, flowers_on=True, expo=0.5, sun_k=18.0, night_k=0.0, cloud_k=0.0, fields=1.0, disc_k=5.5,
                light_k=1.0, air_k=1.0, light_dir=None, near=0.3):
    earthk.earth(img, c, S if light_dir is None else light_dir, sun_k=sun_k * light_k, disc_k=disc_k * light_k, disc_rad=DISC, cloud_k=cloud_k, night_k=night_k,
                 fields=fields, home=HOME, expo=expo, air_k=air_k)
    o, f, r, u, k = c
    alt_m = (np.linalg.norm(o) - earthk.RE) * 1000.0
    if flowers_on and alt_m < 900.0:
        home = UP * earthk.RE
        ol = loc(o - home) * 1000.0
        cl = (ol, loc(f), loc(r), loc(u), k)
        e = expo * light_k
        flowers.field(img, cl, loc(S), t, light=3.4 * e / 0.5, amb=0.55 * e / 0.5 + 0.02, face_az=FACE,
                      haze=(0.62 * e / 0.5, 0.64 * e / 0.5, 0.66 * e / 0.5), haze_d=1400.0, near=near)

def layer_sun(img, c, t, gain=2.4, cor=0.3, rim=1.2, iso=0.0, tint=(1.0, 0.97, 0.92), loops=0.0, prom=0.0, front=0.12,
              ccol=(1.0, 0.88, 0.70)):
    o, f, r, u, k = c
    sunk.k_sun(img, o[0], o[1], o[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, ROT, SPOTS, t * 0.6,
               gain, cor, rim, iso, 1.6, tint[0], tint[1], tint[2], ccol[0], ccol[1], ccol[2])
    if loops > 0:
        P, C, Rr = arches.loop_points(arches.arcade(6, 96, length=0.22, bearing=1.2), t, k=loops)
        sunk.splat(img, arches.to_world(P, ROT), C, Rr, c, front)
        P, C, Rr = arches.loop_points(arches.arcade(15, 22, length=0.16, bearing=0.3, seed=9, n=26), t, k=loops * 0.8)
        sunk.splat(img, arches.to_world(P, ROT), C, Rr, c, front)
    if prom > 0:
        P, C, Rr = arches.prominence(-2, 88, t, k=prom, bearing=1.5708, h=0.2)
        sunk.splat(img, arches.to_world(P, ROT), C, Rr, c, front)

def post(img, expo=1.0, thr=1.1, bk=0.55, wide=1.0, vig=0.26, sat=1.0):
    img = np.nan_to_num(img, nan=0.0, posinf=20.0, neginf=0.0)
    img = bloom(img, thr, bk, wide)
    y = tonemap(vignette(img, vig), expo)
    if sat != 1.0:
        l = y.mean(axis=2, keepdims=True)
        y = np.clip(l + (y - l) * sat, 0, 1)
    return y

# ---------------------------------------------------------------- S1: the field → the lift-off (Earth frame, km)
ALT_KEYS = [(0.0, 0.0019), (2.7, 0.0024), (3.3, 0.012), (3.9, 0.15), (4.5, 2.5), (5.1, 14.0), (5.9, 55.0), (6.8, 190.0),
            (7.6, 420.0)]

def s1_cam(t):
    alt = logkeys(t, ALT_KEYS)
    # a slow push forward over the flowers (towards the Sun), then straight up
    fwd = dirn(0, SUN_AZ - 8)
    ahead = 0.0006 * t + 0.002 * sm((t - 2.0) / 2.0)
    o = UP * (earthk.RE + alt) + fwd * ahead
    # look: just under the Sun, pitching down as we climb so the curve of the Earth comes into view below the Sun
    el = keys(t, [(0.0, 5.5), (2.8, 6.2), (4.6, 2.0), (6.2, -8.0), (7.6, -12.0)])
    az = keys(t, [(0.0, SUN_AZ - 3.0), (3.0, SUN_AZ - 1.5), (7.6, SUN_AZ)])
    fov = keys(t, [(0.0, 34.0), (3.0, 35.0), (5.5, 46.0), (7.6, 52.0)])
    fwd = slerp_dir(dirn(el, az), S, sm((t - 6.5) / 0.95))
    return cam_dir(o, fwd, UP, fov)

def shot_S1(t):
    c = s1_cam(t)
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    expo = keys(t, [(0.0, 0.5), (4.0, 0.5), (6.5, 0.62)])
    layer_earth(img, c, t, expo=expo, cloud_k=0.6 * ramp(t, 4.6, 6.0))
    return post(img, thr=1.4, bk=0.45, sat=1.18)

# ---------------------------------------------------------------- S2…S6: one flight in the Sun's frame (solar radii)
D0 = 1.0 / math.tan(DISC)                              # where the Sun looks as big as the disc drawn from the Earth
A_ = -S                                                # from the Sun towards the Earth
UPW = nrm(UP - A_ * float(UP @ A_))                    # the sky's 'up' of S1, perpendicular to A
SIDE = nrm(np.cross(A_, UPW)) * -1.0                   # screen right when looking from A towards the Sun

def sph(p):
    """(log r, theta, phi) of p in the basis (A, SIDE, UPW)"""
    r = np.linalg.norm(p); x, y, z = p @ A_, p @ SIDE, p @ UPW
    return np.array([math.log(r), math.atan2(y, x), math.asin(max(-1, min(1, z / r)))])
def unsph(q):
    r = math.exp(q[0]); th, ph = q[1], q[2]
    return r * (math.cos(ph) * math.cos(th) * A_ + math.cos(ph) * math.sin(th) * SIDE + math.sin(ph) * UPW)

def hermite(t, ks):
    """C1 interpolation through (time, array) keys; slopes from neighbours (zero at the ends and at repeated values)"""
    ts = [a for a, _ in ks]; vs = [np.asarray(b, float) for _, b in ks]
    if t <= ts[0]: return vs[0]
    if t >= ts[-1]: return vs[-1]
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    t0, t1 = ts[i], ts[i + 1]; v0, v1 = vs[i], vs[i + 1]; dt = t1 - t0
    def slope(j):
        # monotone (Fritsch–Carlson): no overshoot between keys
        if j == 0 or j == len(ts) - 1: return np.zeros_like(vs[j])
        d0 = (vs[j] - vs[j - 1]) / (ts[j] - ts[j - 1]); d1 = (vs[j + 1] - vs[j]) / (ts[j + 1] - ts[j])
        m = (vs[j + 1] - vs[j - 1]) / (ts[j + 1] - ts[j - 1])
        m = np.where(d0 * d1 <= 0, 0.0, m)
        lim = 3.0 * np.minimum(np.abs(d0), np.abs(d1))
        return np.clip(m, -lim, lim)
    m0, m1 = slope(i), slope(i + 1)
    u = (t - t0) / dt
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return h00 * v0 + h10 * dt * m0 + h01 * v1 + h11 * dt * m1

Q_PROM = sbody(-2.0, 88.0)                             # the prominence's foot
def _skim(k, h):
    return slerp_dir(SPOT_W, Q_PROM, k) * (1.0 + h)

def s1_end_forward():
    o, f, r, u, k = s1_cam(7.6)
    return f

# keys: time, position (world), target (world), up, fov
def _keys():
    fS1 = s1_end_forward()
    p0 = A_ * D0 * 1.02
    side_view = SIDE * 1.75 - UPW * 0.25               # where the camera looks in the scales shot (the Sun sits left-up)
    ks = [
        (7.4, p0, p0 + fS1 * 10.0, UP, 52.0),
        (7.75, p0 * 0.97, p0 + fS1 * 10.0, UP, 52.0),
        (8.5, A_ * 26.0, A_ * 30.0 * 0.0 + fS1 * 0.0, UPW, 50.0),
        (9.3, A_ * 5.0, np.zeros(3), UPW, 47.0),
        (10.3, A_ * 3.2, np.zeros(3), UPW, 46.0),
        (12.4, unsph(np.array([math.log(3.1), 0.03, 0.01])), np.zeros(3), UPW, 46.0),
        (14.5, unsph(np.array([math.log(3.05), 0.06, 0.02])), np.zeros(3), UPW, 46.0),
        (16.0, unsph(np.array([math.log(11.8), 0.0, 0.0])) + side_view, side_view, UPW, 46.0),
        (19.2, unsph(np.array([math.log(11.3), 0.01, 0.0])) + side_view, side_view, UPW, 46.0),
        (20.3, SPOT_W * 1.36 + UPW * 0.03, SPOT_W, UPW, 40.0),
        (22.4, SPOT_W * 1.21, SPOT_W, UPW, 40.0),
        (24.6, SPOT_W * 1.33 + SIDE * 0.03, SPOT_W + SIDE * 0.03, UPW, 40.0),
    ]
    return ks
_K = {}
def sun_path(t):
    if 'k' not in _K: _K['k'] = _keys()
    ks = _K['k']
    if t <= 24.6:
        # position in spherical coordinates (never through the Sun); the rest directly
        q = hermite(t, [(a, sph(p)) for a, p, _, _, _ in ks])
        o = unsph(q)
        tgt = hermite(t, [(a, g) for a, _, g, _, _ in ks])
        up = nrm(hermite(t, [(a, u) for a, _, _, u, _ in ks]))
        fov = float(hermite(t, [(a, np.array([f])) for a, _, _, _, f in ks])[0])
        if t < 8.5:
            tgt = np.zeros(3)
            up = nrm(lerpv(UP, UPW, sm((t - 7.75) / 0.75)))
        return o, tgt, up, fov
    # S6: a low flight over the surface towards the prominence, then up over the limb
    k = (t - 24.6) / 7.2
    o0, t0_, u0, f0 = sun_path(24.6)
    kp = keys(k, [(0.0, 0.0), (0.1, 0.02), (0.55, 0.42), (0.8, 0.58), (1.0, 0.66)])
    h = keys(k, [(0.0, 0.165), (0.16, 0.05), (0.5, 0.032), (0.72, 0.07), (1.0, 0.24)])
    o = _skim(kp, h)
    o = lerpv(o0, o, sm(k / 0.14))
    radial = nrm(o)
    fwd_pt = _skim(min(1.0, kp + 0.25), 0.0)                    # a point on the surface ahead
    look_ahead = lerpv(fwd_pt, Q_PROM * 1.13, sm((k - 0.45) / 0.4))
    tgt = lerpv(t0_, look_ahead, sm(k / 0.18))
    up = nrm(lerpv(u0, radial, sm(k / 0.2)))
    fov = keys(k, [(0.0, 40.0), (0.25, 60.0), (1.0, 56.0)])
    if t > 30.9:
        # leave: back up and turn towards the Earth (the forward direction becomes A_, up becomes UPW)
        kk = sm((t - 30.9) / 1.5)
        f0 = nrm(tgt - o)
        fwd = slerp_dir(f0, A_, kk)
        o = o + A_ * 2.5 * kk ** 2
        up = nrm(lerpv(up, UPW, kk))
        tgt = o + fwd
        fov = lerp(fov, 50.0, kk)
    return o, tgt, up, fov

def sun_cam(t):
    o, tgt, up, fov = sun_path(t)
    return cam(o, tgt, up, fov)

def shot_S2(t):
    c = sun_cam(t)
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    layer_sun(img, c, t, gain=keys(t, [(7.4, 3.4), (9.0, 2.8), (10.6, 2.5)]), cor=0.22)
    return post(img, thr=1.15, bk=0.7, wide=1.4)

# S3: the Earths ---------------------------------------------------------
RE_S = 6371.0 / 696000.0                               # the Earth's radius in solar radii

def shot_S3(t):
    c = sun_cam(t)
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    glass = ramp(t, 11.7, 12.4) * (1 - ramp(t, 14.4, 15.2))
    layer_sun(img, c, t, gain=lerp(2.5, 0.42, glass), cor=0.22 * (1 - 0.5 * glass))
    o, f, r, u, k = c
    if glass > 0:
        sun_rim(img, c, glass)
        fill = lerp(-1.02, 1.02, ramp(t, 12.1, 14.3) ** 1.15)
        earths(img, c, fill, glass, t)
    # our Earth in front of the Sun, to scale: a dot crossing the disc (the label comes from captions.py)
    a = ramp(t, 10.3, 10.8) * (1 - ramp(t, 11.7, 12.1))
    if a > 0:
        draw_transit_earth(img, c, t, a)
    return post(img, thr=1.15, bk=0.55)

def transit_pos(c, t):
    o, f, r, u, k = c
    d = np.linalg.norm(o)
    return o + f * (d - 1.0) * 0.55 + (r * lerp(-0.42, -0.30, (t - 10.3) / 1.8) + u * -0.38) * (d - 1.0) * 0.55 / (d - 1.0) * (d * 0.55) / (d * 0.55)

def earth_screen(c, t):
    """where the transiting Earth is on the screen and its radius (px), to scale with the Sun"""
    o, f, r, u, k = c
    d = np.linalg.norm(o)
    rs_px = k * math.tan(math.asin(1.0 / d))             # the Sun's radius on the screen
    re_px = rs_px * RE_S * 1.0                           # the Earth as seen against it (same angular scale at the Sun)
    x = W / 2 + rs_px * lerp(-0.46, -0.30, (t - 10.3) / 1.8); y = H / 2 + rs_px * 0.42
    return x, y, max(re_px, 2.2)

def draw_transit_earth(img, c, t, a):
    x, y, rp = earth_screen(c, t)
    import render_lines as RL
    # the night side faces us (the Sun is behind it): a dark disc with a thin bright rim of air
    yy, xx = np.mgrid[-40:41, -40:41].astype(np.float32)
    d = np.sqrt(xx * xx + yy * yy)
    disc_ = np.clip(rp - d + 0.5, 0, 1)[..., None] * a
    rim = np.exp(-((d - rp) / 0.9) ** 2)[..., None] * np.array([0.5, 0.75, 1.6]) * a
    ring = np.exp(-((d - 26.0) / 1.5) ** 2)[..., None] * np.array([0.9, 1.1, 1.5]) * 1.1 * a
    xa, ya = int(round(x)) - 40, int(round(y)) - 40
    sl = img[ya:ya + 81, xa:xa + 81]
    sl[:] = sl * (1 - disc_) + np.array([0.01, 0.015, 0.03]) * disc_ + rim + ring

def sun_rim(img, c, a):
    o, f, r, u, k = c
    d = np.linalg.norm(o)
    x, y, z = project(c, np.zeros(3))
    rs = k * math.tan(math.asin(1.0 / d))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.sqrt((xx - x[0]) ** 2 + (yy - y[0]) ** 2) / rs
    fres = np.where(dd < 1.0, np.clip(dd, 0, 1) ** 6, 0) * 1.2 + np.exp(-((dd - 1.0) / 0.012) ** 2) * 1.5
    img += (fres * a)[..., None] * np.array([1.0, 0.86, 0.66], np.float32)

_T = {}
def _earth_tex():
    if 'e' not in _T:
        _T['e'] = np.asarray(Image.open(os.path.join(TEX, 'earth_day_2k.jpg')).convert('RGB'), np.float32) / 255
    return _T['e']

import numba as nb
@nb.njit(parallel=True, fastmath=True)
def k_earths(out, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, ax, ay, az, fill, re, alpha, tex, lx, ly, lz):
    """a cubic lattice of Earths (radius re, spacing 2.1 re) inside the unit sphere, filled up to height `fill` along a"""
    Hh, Ww = out.shape[0], out.shape[1]
    sp = re * 2.1
    th, tw = tex.shape[0], tex.shape[1]
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            b = dx * ox + dy * oy + dz * oz
            disc = b * b - (ox * ox + oy * oy + oz * oz - 1.0)
            if disc <= 0: continue
            t0 = -b - math.sqrt(disc); t1 = -b + math.sqrt(disc)
            if t1 <= 0: continue
            t0 = max(t0, 0.0)
            # DDA through the lattice
            px = ox + dx * t0; py = oy + dy * t0; pz = oz + dz * t0
            cx = math.floor(px / sp); cy = math.floor(py / sp); cz = math.floor(pz / sp)
            stx = 1 if dx > 0 else -1; sty = 1 if dy > 0 else -1; stz = 1 if dz > 0 else -1
            tdx = abs(sp / dx) if abs(dx) > 1e-12 else 1e30; tdy = abs(sp / dy) if abs(dy) > 1e-12 else 1e30; tdz = abs(sp / dz) if abs(dz) > 1e-12 else 1e30
            nx_ = (cx + (1 if dx > 0 else 0)) * sp; ny_ = (cy + (1 if dy > 0 else 0)) * sp; nz_ = (cz + (1 if dz > 0 else 0)) * sp
            tmx = t0 + ((nx_ - px) / dx if abs(dx) > 1e-12 else 1e30)
            tmy = t0 + ((ny_ - py) / dy if abs(dy) > 1e-12 else 1e30)
            tmz = t0 + ((nz_ - pz) / dz if abs(dz) > 1e-12 else 1e30)
            hit = False; tt = 0.0; hx = 0.0; hy = 0.0; hz = 0.0; hc0 = 0.0; hc1 = 0.0; hc2 = 0.0
            for step in range(400):
                # the sphere in this cell (if the cell's centre is inside the Sun and under the fill level), jittered
                jx = (math.sin(cx * 12.9898 + cy * 78.233 + cz * 37.719) * 43758.5453) % 1.0 - 0.5
                jy = (math.sin(cx * 39.346 + cy * 11.135 + cz * 83.155) * 24634.6345) % 1.0 - 0.5
                jz = (math.sin(cx * 73.156 + cy * 52.235 + cz * 9.151) * 31871.1123) % 1.0 - 0.5
                ccx = (cx + 0.5 + jx * 0.42) * sp; ccy = (cy + 0.5 + jy * 0.42) * sp; ccz = (cz + 0.5 + jz * 0.42) * sp
                lev = fill + 0.025 * math.sin(ccx * 9.0 + ccz * 7.0) + 0.02 * math.sin(ccy * 13.0 - ccx * 5.0)
                if ccx * ccx + ccy * ccy + ccz * ccz < (1.0 - re) ** 2 and (ccx * ax + ccy * ay + ccz * az) < lev:
                    qx = ox - ccx; qy = oy - ccy; qz = oz - ccz
                    bb = dx * qx + dy * qy + dz * qz
                    dd = bb * bb - (qx * qx + qy * qy + qz * qz - re * re)
                    if dd > 0:
                        th_ = -bb - math.sqrt(dd)
                        if th_ > 0:
                            hit = True; tt = th_; hc0 = ccx; hc1 = ccy; hc2 = ccz
                            break
                if tmx < tmy and tmx < tmz:
                    if tmx > t1: break
                    cx += stx; tmx += tdx
                elif tmy < tmz:
                    if tmy > t1: break
                    cy += sty; tmy += tdy
                else:
                    if tmz > t1: break
                    cz += stz; tmz += tdz
            if not hit: continue
            hx = (ox + dx * tt - hc0) / re; hy = (oy + dy * tt - hc1) / re; hz = (oz + dz * tt - hc2) / re
            # each Earth turned its own way
            rot_ = (hc0 * 131.7 + hc1 * 77.3 + hc2 * 191.1) / sp
            lon = math.atan2(hy, hx) + rot_; lat = math.asin(min(1.0, max(-1.0, hz)))
            uu = ((lon / (2 * math.pi)) % 1.0) * (tw - 1); vv = (0.5 - lat / math.pi) * (th - 1)
            cr = tex[int(vv), int(uu), 0]; cg = tex[int(vv), int(uu), 1]; cb = tex[int(vv), int(uu), 2]
            lam = max(0.0, hx * lx + hy * ly + hz * lz)
            mu = -(hx * dx + hy * dy + hz * dz)
            rim = (1 - max(0.0, mu)) ** 3
            sh = 0.12 + 1.5 * lam
            r_ = cr * sh + 0.15 * rim; g_ = cg * sh + 0.3 * rim; b_ = cb * sh + 0.75 * rim
            # deeper ones are a bit dimmer (seen through the glass)
            dep = math.exp(-(tt - t0) * 1.6)
            a_ = alpha * (0.35 + 0.65 * dep)
            out[j, i, 0] = out[j, i, 0] * (1 - a_) + r_ * a_ * 1.2
            out[j, i, 1] = out[j, i, 1] * (1 - a_) + g_ * a_ * 1.2
            out[j, i, 2] = out[j, i, 2] * (1 - a_) + b_ * a_ * 1.2

def earths(img, c, fill, alpha, t):
    o, f, r, u, k = c
    a = u                                                    # 'up' on the screen: the level rises from the bottom
    light = nrm(-f + r * 0.4 + u * 0.5)
    k_earths(img, o[0], o[1], o[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, a[0], a[1], a[2], fill,
             RE_S, alpha, _earth_tex(), light[0], light[1], light[2])

# S4: the scales ---------------------------------------------------------
PLAN = [('jupiter', 69911), ('saturn', 58232), ('uranus', 25362), ('neptune', 24622), ('earth', 6371), ('venus', 6052),
        ('mars', 3390), ('mercury', 2440)]

SC_PIV = (1.75, 1.55); SC_ARM = 1.75; SC_DROP = 2.6        # pivot (x, y), arm length, pan hang below the beam

def sc_tilt(t):
    return math.radians(lerp(0.0, 11.0, ease((t - 16.7) / 1.5)) * (1 - ease((t - 19.2) / 0.8)))

def shot_S4(t):
    c = sun_cam(t)
    o, f, r, u, k = c
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    al = sc_tilt(t)
    # the Sun rides in the left pan: it moves with the left end of the beam (done by moving the camera the other way)
    dx = SC_ARM * (1 - math.cos(al)); dy = -SC_ARM * math.sin(al)
    cs = (o - r * dx - u * dy, f, r, u, k)
    layer_sun(img, cs, t, gain=2.5, cor=0.22)
    scales(img, c, t, al)
    return post(img, thr=1.15, bk=0.55)

def scales(img, c, t, al):
    o, f, r, u, k = c
    a = ramp(t, 15.5, 16.3) * (1 - ramp(t, 19.1, 19.45))
    if a <= 0: return
    gold = np.array([1.0, 0.78, 0.42])
    def W3(x, y): return r * x + u * y
    def P(X):
        x, y, z = project(c, X)
        if z[0] < 0.5: raise ValueError('behind')
        return float(x[0]), float(y[0])
    import render_lines as RL
    px_, py_ = SC_PIV
    ca, sa = math.cos(al), math.sin(al)
    L = (px_ - SC_ARM * ca, py_ - SC_ARM * sa); Rr = (px_ + SC_ARM * ca, py_ + SC_ARM * sa)
    try:
        _scale_lines(img, c, t, a, L, Rr, W3, P, RL, gold, px_, py_)
    except ValueError:
        return
    _scale_planets(img, c, t, a, Rr, W3, RL)

def _scale_lines(img, c, t, a, L, Rr, W3, P, RL, gold, px_, py_):
    segs = [([P(W3(*L)), P(W3(*Rr))], 3.4),
            ([P(W3(px_, py_ + 0.12)), P(W3(px_, -2.55))], 3.0),
            ([P(W3(px_ - 0.55, -2.55)), P(W3(px_ + 0.55, -2.55))], 3.4),
            ([P(W3(px_ - 0.12, py_ + 0.18)), P(W3(px_ + 0.12, py_ + 0.18)), P(W3(px_, py_ - 0.02)), P(W3(px_ - 0.12, py_ + 0.18))], 2.2)]
    for (ex, ey), w_ in ((L, 1.05), (Rr, 0.5)):
        dy_ = ey - SC_DROP
        for s_ in (-1, 1):
            segs.append(([P(W3(ex, ey)), P(W3(ex + w_ * s_, dy_ + 0.02))], 1.4))
        segs.append(([P(W3(ex - w_ - 0.05, dy_ + 0.06)), P(W3(ex - w_ * 0.6, dy_ - 0.06)), P(W3(ex + w_ * 0.6, dy_ - 0.06)), P(W3(ex + w_ + 0.05, dy_ + 0.06))], 2.6))
    RL.glow_lines(img, segs, gold * 1.3 * a)

def _scale_planets(img, c, t, a, Rr, W3, RL):
    o, f, r, u, k = c
    # all the planets in the right pan, to scale, heaped
    ex, ey = Rr; dy_ = ey - SC_DROP - 0.05
    heap = [('jupiter', -0.16, 0.0), ('saturn', 0.16, 0.0), ('uranus', 0.34, 0.0), ('neptune', -0.37, 0.0),
            ('earth', 0.03, 0.17), ('venus', 0.06, 0.17), ('mars', -0.05, 0.155), ('mercury', 0.1, 0.15)]
    drop_in = ease((t - 15.6) / 0.9)
    for name, hx, hy in heap:
        rkm = dict(PLAN)[name]; rs = rkm / 696000.0
        X = W3(ex + hx, dy_ + rs + hy + (1 - drop_in) * 2.5)
        x, y, z = project(c, X)
        rp = k * rs / z[0]
        RL.planet(img, name, max(rp, 1.0), float(x[0]), float(y[0]), a, light=(-0.75, 0.3, 0.6))

# S5: the spot -----------------------------------------------------------
def shot_S5(t):
    c = sun_cam(t)
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    iso = ramp(t, 20.7, 21.4) * (1 - ramp(t, 22.3, 22.9))
    g = keys(t, [(20.0, 2.3), (21.5, 1.9), (25.2, 1.9)])
    layer_sun(img, c, t, gain=g, cor=0.3, iso=iso, tint=(1.0, 0.95, 0.88))
    # the Earth next to the spot, to scale
    a = ramp(t, 22.6, 23.3)
    if a > 0:
        o, f, r, u, k = c
        pe = SPOT_W * (1.0 + RE_S * 1.2) + nrm(r - SPOT_W * (r @ SPOT_W)) * 0.068
        x, y, z = project(c, pe)
        rp = k * RE_S / z[0]
        import render_lines as RL
        slide = (1 - ease((t - 22.6) / 0.9)) * 600
        RL.planet(img, 'earth', rp, float(x[0]) + slide, float(y[0]), a, light=(-0.6, 0.35, 0.7))
    return post(img, thr=1.15, bk=0.55)

# S6: the surface, the limb, the corona ---------------------------------
def shot_S6(t):
    c = sun_cam(t)
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    k = (t - 25.2) / 6.4
    up = ramp(t, 28.4, 30.0)
    if t > 31.0:
        gl = ramp(t, 31.0, 32.3)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d_ = np.sqrt((xx - W / 2) ** 2 + (yy - H * 0.95) ** 2)
        img += ((np.exp(-d_ / 520.0) * 3.0 + 0.6) * gl)[..., None] * np.array([1.0, 0.86, 0.62], np.float32)
    near = ramp(t, 24.9, 25.8) * (1 - ramp(t, 31.0, 32.0))
    layer_sun(img, c, t, gain=keys(t, [(25.2, 1.9), (27.0, 2.2), (29.0, 2.6)]), cor=lerp(0.10, 0.22, up) * (1 + 0.7 * near), rim=1.6,
              tint=(1.0, lerp(0.94, 0.86, near), lerp(0.84, 0.64, near)), loops=0.14 * ramp(t, 27.6, 29.0), prom=0.085 * ramp(t, 27.6, 29.0),
              ccol=(1.0, lerp(0.88, 0.74, near), lerp(0.70, 0.42, near)))
    return post(img, thr=1.2, bk=0.6)

# ---------------------------------------------------------------- S7: riding the sunlight to the Earth (Earth frame, km)
S_SIDE = nrm(np.cross(S, UP))                         # a direction perpendicular to the Sun's

def s7_pos(t):
    k = (t - 32.0) / 6.9
    dist = logkeys(t, [(32.0, 2.2e6), (34.5, 1.6e5), (37.0, 4.2e4), (38.9, 2.6e4)])
    d = slerp_dir(S, nrm(S + S_SIDE * 0.35 + UP * 0.18), sm(k))
    return d * dist

def s7_cam(t):
    o = s7_pos(t)
    return cam_dir(o, -nrm(o), UPW, keys(t, [(32.0, 50.0), (38.9, 44.0)]))

_ST = {}
def streaks(img, c, t):
    """light flowing past towards the Earth: golden streaks, each moving faster than the camera"""
    if 'p' not in _ST:
        rng = np.random.default_rng(3)
        n = 260
        _ST['p'] = (rng.random(n), rng.normal(0, 1, (n, 2)), rng.random(n))
    ph, xy, br = _ST['p']
    o, f, r, u, k = c
    dist = np.linalg.norm(o)
    segs_hi, segs_lo = [], []
    for i in range(len(ph)):
        # a light particle on a line parallel to the view axis, at lateral offset (in units of the view's width there)
        z = ((ph[i] - (t - 32.0) * 0.55) % 1.0)            # 1 = near the camera, 0 = at the Earth
        lat = xy[i] * 0.55
        if np.hypot(*lat) < 0.16: continue                 # keep the Earth clear
        zz = 0.05 + z * 1.6                                 # depth ahead (in units of 'lat' scale)
        x0 = W / 2 + k * lat[0] / zz * 0.25; y0 = H / 2 - k * lat[1] / zz * 0.25
        z2 = zz + 0.18
        x1 = W / 2 + k * lat[0] / z2 * 0.25; y1 = H / 2 - k * lat[1] / z2 * 0.25
        a = (1 - z) ** 0.5 * sm(z / 0.15) * (0.4 + 0.6 * br[i])
        (segs_hi if br[i] > 0.6 else segs_lo).append(([(x0, y0), (x1, y1)], 1.2 + 1.6 * br[i] * (1 - z), a))
    import render_lines as RL
    for group, col in ((segs_hi, np.array([1.0, 0.85, 0.55])), (segs_lo, np.array([1.0, 0.75, 0.4]))):
        if group:
            # alpha folded into separate passes would be slow: approximate with the mean
            am = float(np.mean([g[2] for g in group]))
            RL.glow_lines(img, [(g[0], g[1]) for g in group], col * am * streak_k(t), core=0.9, glow=0.6)

def streak_k(t):
    return ramp(t, 31.9, 32.6) * (1 - ramp(t, 36.8, 38.0))

def shot_S7(t):
    c = s7_cam(t)
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    if t < 33.2:
        gl = 1 - ramp(t, 32.0, 33.2)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d_ = np.sqrt((xx - W / 2) ** 2 + (yy - H * 0.95) ** 2)
        img += ((np.exp(-d_ / 520.0) * 3.0 + 0.6) * gl)[..., None] * np.array([1.0, 0.86, 0.62], np.float32)
    layer_earth(img, c, t, flowers_on=False, expo=0.45, cloud_k=0.85, night_k=0.0, disc_k=0.0)
    if streak_k(t) > 0: streaks(img, c, t)
    return post(img, thr=1.2, bk=0.5)

# ---------------------------------------------------------------- S8: down to the field (Earth frame)
def s8_cam(t):
    # from S7's end down towards home; low down, pitch up to S1's opening view (the Sun ahead, yellow)
    o7 = s7_pos(38.3)
    alt = logkeys(t, [(38.3, np.linalg.norm(o7) - earthk.RE), (39.3, 2500.0), (40.0, 160.0), (40.6, 12.0), (41.1, 0.6),
                      (41.6, 0.012), (42.1, 0.0026), (43.0, 0.0022)])
    dir_ = slerp_dir(nrm(o7), UP, sm((t - 38.3) / 2.0))
    back = dirn(0, SUN_AZ + 180)
    o = dir_ * (earthk.RE + alt) + back * 0.006 * sm((t - 40.4) / 1.4) - back * 0.0004 * max(0.0, t - 41.8)
    look_down = -nrm(o)
    look_end = dirn(5.5, SUN_AZ - 3.0)
    fwd = slerp_dir(lerpv(look_down, -nrm(o7), 1 - sm((t - 38.3) / 1.4)), look_end, sm((t - 40.3) / 1.5))
    upv = nrm(lerpv(UPW, UP, sm((t - 38.3) / 2.2)))
    fov = keys(t, [(38.3, keys(38.3, [(32.0, 50.0), (38.9, 44.0)])), (40.4, 50.0), (41.8, 34.0)])
    return cam_dir(o, fwd, upv, fov)

def shot_S8(t):
    c = s8_cam(t)
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    layer_earth(img, c, t, expo=keys(t, [(38.3, 0.45), (40.0, 0.5)]), cloud_k=0.85 * (1 - ramp(t, 39.0, 40.0)), near=0.9)
    return post(img, thr=lerp(1.2, 1.4, ramp(t, 38.3, 40.0)), bk=lerp(0.5, 0.45, ramp(t, 38.3, 40.0)), sat=lerp(1.0, 1.18, ramp(t, 38.4, 40.0)))

# ---------------------------------------------------------------- S9 / S10: the Sun goes out (and comes back)
SUN_PX = (300.0, 540.0, 92.0)                          # where the (compressed) Sun sits on the screen, radius px
EARTH_PX = (700.0, 1420.0)
L_SIDE = None

def s9_basis():
    """a camera orientation in which the Sun's direction S falls on SUN_PX and the Earth's centre on EARTH_PX"""
    fov = 46.0; k = (H / 2) / math.tan(math.radians(fov) / 2)
    def cdir(px, py): return nrm(np.array([(px - W / 2) / k, -(py - H / 2) / k, 1.0]))
    v1 = cdir(SUN_PX[0], SUN_PX[1]); v2 = cdir(*EARTH_PX)
    # camera space (x right, y up, z forward) -> world: v1 -> S; the roll keeps 'up' near UPW
    e1 = v1; e2 = nrm(np.cross(v1, v2)); e3 = np.cross(e1, e2)
    w1 = S
    best = None
    for ang in np.linspace(0, 2 * np.pi, 720, endpoint=False):
        q = nrm(np.cross(S, UPW)); q2 = np.cross(S, q)
        w2 = q * math.cos(ang) + q2 * math.sin(ang); w3 = np.cross(w1, w2)
        Rm = np.stack([w1, w2, w3], 1) @ np.stack([e1, e2, e3], 1).T
        upw_ = Rm @ np.array([0, 1.0, 0])
        sc = float(upw_ @ UPW)
        if best is None or sc > best[0]: best = (sc, Rm)
    Rm = best[1]
    f = Rm @ np.array([0, 0, 1.0]); r = Rm @ np.array([1.0, 0, 0]); u = Rm @ np.array([0, 1.0, 0])
    dE = Rm @ v2                                        # direction from the camera to the Earth's centre
    return f, r, u, k, dE, fov

_B = {}
def s9_cam(t, dist=5.0):
    if 'b' not in _B: _B['b'] = s9_basis()
    f, r, u, k, dE, fov = _B['b']
    o = -dE * earthk.RE * dist
    return (o, f, r, u, k)

# when the Sun goes out / comes back, and the light fronts
T_OFF = 44.75; T_DARK = 48.95; T_ON = 50.25; T_LIT = 51.45

def front_radius(t, t0, t1):
    """the edge of the last (or first) light, px from the Sun's centre on the screen: reaches the Earth's far side at t1"""
    dmax = math.hypot(EARTH_PX[0] - SUN_PX[0], EARTH_PX[1] - SUN_PX[1]) + 420.0
    return SUN_PX[2] + (dmax - SUN_PX[2]) * max(0.0, (t - t0) / (t1 - t0))

def s9_light(c):
    """the light on the Earth in the compressed side-on view: from the (near) Sun's side, mostly across the view"""
    o, f, r, u, k = c
    return nrm(r * -0.62 + u * 0.70 + f * 0.25)

def shot_S9(t):
    c_end = s9_cam(t)
    if t < 43.5:
        # the climb from the field into the side-on view (as in S8: the field, the flowers, the Sun's disc)
        kk = sm((t - 42.6) / 0.9)
        c8 = s8_cam(42.6)
        a0 = np.linalg.norm(c8[0]) - earthk.RE; a1 = np.linalg.norm(c_end[0]) - earthk.RE
        ka = (t - 42.6) / 0.9
        alt = math.exp(lerp(math.log(a0), math.log(a1), min(1.0, ka) ** 1.6 * (3 - 2 * min(1.0, ka)) / (1 + 0.0 * ka)))
        xl = (math.log(alt) - math.log(a0)) / (math.log(a1) - math.log(a0))
        wdir = max(0.0, (xl - 0.55) / 0.45) ** 2                 # move across the globe only once high (above ~16 km)
        o = slerp_dir(nrm(c8[0]), nrm(c_end[0]), wdir) * (earthk.RE + alt)
        f = slerp_dir(c8[1], c_end[1], kk)
        upv = nrm(lerpv(c8[3], c_end[3], kk))
        c = cam_dir(o, f, upv, lerp(34.0, 46.0, kk))
        img = np.zeros((H, W, 3), np.float32)
        layer_sky(img, c, gain=0.8)
        hand = ramp(t, 42.95, 43.05)                         # above the air (~20 km): the Sun is drawn by its own renderer
        layer_earth(img, c, t, expo=lerp(0.5, 0.55, kk), cloud_k=0.85 * kk, disc_k=5.5 * (1 - hand),
                    light_dir=nrm(lerpv(S, s9_light(c_end), ramp(t, 43.1, 43.5))), near=0.9)
        if hand > 0:
            # it slides from its true direction to its place in the compressed side-on view, growing
            x, y, z = project(c, c[0] + S * 1e6)
            w = ease((t - 43.0) / 0.5)
            k0 = c[4]; r0 = k0 * math.tan(DISC)
            cs = sun_cam_at(c, lerp(float(x[0]), SUN_PX[0], w), lerp(float(y[0]), SUN_PX[1], w), lerp(r0, SUN_PX[2], w))
            sun = np.zeros((H, W, 3), np.float32); layer_sun(sun, cs, t, gain=2.6, cor=0.22 * w)
            m = (np.max(sun, axis=2, keepdims=True) > 0.05) * hand
            img = img * (1 - m) + sun * hand
        return post(img, thr=1.15, bk=0.55, sat=lerp(1.18, 1.0, kk))
    o, f, r, u, k_ = c_end
    c = (o * (1 - 0.03 * sm((t - 43.5) / 6.5)), f, r, u, k_)
    return s9_render(c, t, sun_on=t < T_OFF, dark_front=(T_OFF, T_DARK))

def s9_render(c, t, sun_on=True, dark_front=None, light_front=None, sun_scale=1.0, approach=0.0, earth_cam=None, earth_a=1.0):
    if earth_cam is None: earth_cam = c
    img = np.zeros((H, W, 3), np.float32)
    layer_sky(img, c, gain=0.8)
    ce = earth_cam
    lit = np.zeros((H, W, 3), np.float32); layer_earth(lit, ce, t, flowers_on=False, expo=0.55, cloud_k=0.85, night_k=0.0, disc_k=0.0, light_dir=s9_light(c))
    mask = np.ones((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.sqrt((xx - SUN_PX[0]) ** 2 + (yy - SUN_PX[1]) ** 2)
    if dark_front is not None and t > dark_front[0]:
        R_ = front_radius(t, *dark_front)
        mask = np.clip((dd - R_) / 40.0 + 0.5, 0, 1)               # 1 = still lit (outside the dark sphere)
    if light_front is not None:
        R_ = front_radius(t, *light_front) if t > light_front[0] else 0.0
        mask = np.clip((R_ - dd) / 40.0 + 0.5, 0, 1)              # 1 = lit again (inside the new light)
    need_dark = mask.min() < 0.999
    if need_dark:
        dark = np.zeros((H, W, 3), np.float32); layer_earth(dark, ce, t, flowers_on=False, expo=0.55, cloud_k=0.85, night_k=3.0, disc_k=0.0, light_k=0.0, light_dir=s9_light(c))
        earth_img = lit * mask[..., None] + dark * (1 - mask[..., None])
    else:
        earth_img = lit
    # the Earth over the stars (the earth layers drew on black: add where they are not black)
    o, f, r, u, k = c
    cover = (np.linalg.norm(earth_img, axis=2) > 1e-4).astype(np.float32) * earth_a
    img = img * (1 - cover[..., None]) + earth_img * earth_a
    # the Sun
    cs = s9_sun_cam(c, sun_scale, approach)
    if sun_on:
        layer_sun(img, cs, t, gain=2.6, cor=0.22)
    # the Sun lighting up again: a flash around it
    if light_front is not None and t >= light_front[0]:
        fl = math.exp(-(t - light_front[0]) / 0.35) * 6.0
        img += (fl * np.exp(-dd / 260.0) + fl * 0.25 * np.exp(-dd / 900.0))[..., None] * np.array([1.0, 0.95, 0.85], np.float32)
    # the front of the last light: a thin glowing shell
    for fr, sign in ((dark_front, 1), (light_front, -1)):
        if fr is None or t < fr[0]: continue
        R_ = front_radius(t, *fr)
        a = (1 - ramp(t, fr[1] - 0.2, fr[1] + 0.5)) * 0.55
        if a > 0:
            ring = np.exp(-((dd - R_) / 7.0) ** 2) * a + np.exp(-((dd - R_) / 40.0) ** 2) * a * 0.3
            img += ring[..., None] * np.array([1.0, 0.86, 0.6], np.float32)
    return post(img, thr=1.15, bk=0.55)

def sun_cam_at(c, px, py, rad):
    """a camera for the Sun's renderer with c's orientation, so the Sun's centre lands on (px, py) with radius rad px"""
    o, f, r, u, k = c
    d = nrm(f + r * (px - W / 2) / k - u * (py - H / 2) / k)
    D = 1.0 / math.sin(math.atan(rad / k))
    return (-d * D, f, r, u, k)

def s9_sun_cam(c, scale=1.0, approach=0.0):
    """the Sun's own camera: same orientation, placed so the Sun's centre falls on its screen spot with its radius;
    approach 0…1 moves that spot to the centre and grows the Sun (the flight to it)"""
    o, f, r, u, k = c
    px = lerp(SUN_PX[0], W / 2, sm(approach * 1.3)); py = lerp(SUN_PX[1], H * 0.47, sm(approach * 1.3))
    rad = math.exp(lerp(math.log(SUN_PX[2]), math.log(470.0), approach)) * scale
    d = nrm(f + r * (px - W / 2) / k - u * (py - H / 2) / k)
    D = 1.0 / math.sin(math.atan(rad / k))
    return (-d * D, f, r, u, k)

def shot_S10(t):
    c = s9_cam(t)
    o, f, r, u, k_ = c
    c = (o * (1 - 0.03), f, r, u, k_)
    if t < T_ON:
        return s9_render(c, t, sun_on=False, dark_front=(T_OFF, T_DARK))
    app = ease((t - 51.6) / 4.4)
    push = 1 + 0.10 * ease((t - 55.0) / 3.4)
    # the Earth sinks out of the frame as we leave it behind
    ce = (o * (1 - 0.03) + u * earthk.RE * 4.0 * ease((t - 51.8) / 3.0) - f * earthk.RE * 6.0 * ease((t - 51.8) / 3.0), f, r, u, k_)
    im = s9_render(c, t, sun_on=True, light_front=(T_ON, T_LIT),
                   sun_scale=(1.0 + 0.5 * ramp(t, T_ON, T_ON + 0.3) * (1 - ramp(t, T_ON + 0.3, T_ON + 1.1))) * push,
                   approach=app, earth_cam=ce, earth_a=1 - ramp(t, 53.0, 54.5))
    return im

# ---------------------------------------------------------------- label positions for captions.py
def labels(t):
    """[(x, y, text, alpha)] of the names that sit next to things on the screen"""
    out = []
    if 10.3 < t < 12.2:
        c = sun_cam(t); x, y, rp = earth_screen(c, t)
        out.append((x + 34, y, 'Земля', ramp(t, 10.5, 10.9) * (1 - ramp(t, 11.6, 12.0)), 'lm'))
    if 15.5 < t < 20.0:
        c = sun_cam(t); o, f, r, u, k = c
        al = sc_tilt(t); a = ramp(t, 15.9, 16.6) * (1 - ramp(t, 19.0, 19.35))
        px_, py_ = SC_PIV; ca, sa = math.cos(al), math.sin(al)
        Rr = (px_ + SC_ARM * ca, py_ + SC_ARM * sa)
        x, y, z = project(c, r * Rr[0] + u * (Rr[1] - SC_DROP - 0.42))
        out.append((float(x[0]), float(y[0]), 'усі планети', a, 'mm'))
        dx = SC_ARM * (1 - ca); dy = -SC_ARM * sa
        x, y, z = project(c, r * dx + u * (dy - 1.35))
        out.append((float(x[0]), float(y[0]), 'Сонце', a, 'mm'))
    if 22.7 < t < 25.0:
        c = sun_cam(t); o, f, r, u, k = c
        pe = SPOT_W * (1.0 + RE_S * 1.2) + nrm(r - SPOT_W * (r @ SPOT_W)) * 0.068
        x, y, z = project(c, pe); rp = k * RE_S / z[0]
        slide = (1 - ease((t - 22.6) / 0.9)) * 600
        out.append((float(x[0]) + slide, float(y[0]) + rp + 40, 'Земля', ramp(t, 23.2, 23.6) * (1 - ramp(t, 24.6, 25.0)), 'mm'))
    if 43.5 < t < 45.2:
        a = ramp(t, 43.6, 43.9) * (1 - ramp(t, 44.6, 45.0))
        out.append((SUN_PX[0], SUN_PX[1] + SUN_PX[2] + 46, 'Сонце', a, 'mm'))
        out.append((EARTH_PX[0] - 60, EARTH_PX[1] - 500, 'Земля', a, 'mm'))
    return out

# ---------------------------------------------------------------- the timeline
SHOTS = [(0.0, 7.75, shot_S1), (7.45, 10.8, shot_S2), (10.2, 15.0, shot_S3), (14.6, 20.2, shot_S4), (19.6, 25.4, shot_S5),
         (24.8, 32.6, shot_S6), (32.0, 38.35, shot_S7), (38.3, 42.6, shot_S8), (42.6, 50.2, shot_S9),
         (49.6, 58.5, shot_S10)]

def frame(t):
    act = [(a, b, f) for a, b, f in SHOTS if a <= t <= b]
    out = None
    for a, b, f in act:
        im = f(t)
        if out is None: out = im
        else:
            prev_end = max(bb for aa, bb, ff in act if ff is not f and aa < a)
            kk = sm((t - a) / max(1e-3, prev_end - a))
            out = out * (1 - kk) + im * kk
    if out is None: out = np.zeros((H, W, 3), np.float32)
    return Image.fromarray(to_u8(out))

def job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return
    frame(i / FPS).save(p + '.tmp.jpg', quality=94); os.replace(p + '.tmp.jpg', p)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * FPS)
    todo = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as pool:
        for cnt, _ in enumerate(pool.imap_unordered(job, todo, chunksize=1)):
            if cnt % 30 == 0: print('frame', cnt, '/', len(todo), flush=True)
    print('frames done', n)
