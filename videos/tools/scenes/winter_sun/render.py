# «Чому взимку холодно, якщо Земля найближче до Сонця?» — every frame (1080x1920, 30 fps); shots dissolve into each other.
#   ORBIT  the real orbit (to scale: almost a circle), the Sun at its focus, the Earth at perihelion (3 Jan, 147.1 mln km)
#          and where it will be on 5 Jul (152.1 mln km); the Sun and the Earth enlarged so they can be seen
#   DIVE   down to the Earth: Europe and Ukraine under snow, the low winter Sun
#   AXIS   the Earth from the side: its axis (23.4° from the perpendicular to the orbit), the north turned away from the Sun
#   YEAR   a year in four seconds: the axis keeps pointing the same way — in June the north leans to the Sun, in December away
#   KYIV   down to Kyiv in winter (Sentinel-2, under snow): the sky dome, the noon Sun at 16° → summer, 63° (the snow melts)
#   BEAM   the same bundle of sunlight: at 63° a small hot spot, at 16° a long faint one — 3.2 times the area
#   DAY    the Sun's path on 21 Dec (8 h) and 21 Jun (16.5 h) over Kyiv
#   AUS    up and round the globe to Australia: summer, the Sun high
#   END    back out to the orbit: the Earth at perihelion
# Geometry: ORBIT/YEAR in the ecliptic frame (million km, Sun at the origin, z = ecliptic north); the Earth shots in the
# Earth-fixed frame (km, z = north). Earth maps: work/sun_imagine (textures.py), Kyiv: work/winter_sun (kyivmap.py, winterize.py).
#   python3 render.py [workers] [frame …]        -> work/winter_sun/frames/f_%05d.jpg (+ labels.json)
#   python3 render.py still t1 t2 …              -> scratchpad stills
import math, os, sys, json
import numpy as np
from PIL import Image
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(TOOLS, 'scenes', 'sun_imagine')); sys.path.insert(0, HERE)
from common import sm, ramp, lerp, lerpv, nrm, ease, ll, cam, cam_dir, project, sky, rot_axis, bloom, tonemap, vignette, to_u8, W, H, FPS
import sunk
import earthw as E

WORK = os.path.join(TOOLS, 'work', 'winter_sun'); OUT = os.path.join(WORK, 'frames')
CFG = json.load(open(os.path.join(HERE, 'scene.json'))); DUR = CFG['duration']
T = CFG.get('times', {})
def tk(name, default): return float(T.get(name, default))

# ---------------------------------------------------------------- helpers
def keys(t, ks):
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0))
            return lerpv(v0, v1, k) if isinstance(v0, np.ndarray) else lerp(v0, v1, k)
    return ks[-1][1]

def logkeys(t, ks):
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            return math.exp(lerp(math.log(v0), math.log(v1), sm((t - t0) / (t1 - t0))))
    return ks[-1][1]

def Rx(a):
    c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def Rz(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

GAL = rot_axis([0.3, 1.0, 0.2], 2.2)

def glow_lines(img, pts, col, w=2.0, gain=1.0, halo=1.0, dash=0.0, closed=False):
    """antialiased glowing polyline into the HDR image; pts: (N, 2) screen px (NaN breaks the line); dash: px period"""
    pts = np.asarray(pts, float)
    segs = list(zip(pts[:-1], pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
    col = np.asarray(col, np.float32)
    run = 0.0
    sig = max(2.0, w * 2.2) * halo
    for p0, p1 in segs:
        if not (np.all(np.isfinite(p0)) and np.all(np.isfinite(p1))): continue
        L = float(np.hypot(*(p1 - p0)))
        if L < 1e-6: continue
        if dash > 0:
            ph0 = run % dash; run += L
            # cut the segment into the "on" halves of the dash period
            pieces = []; s = -ph0
            while s < L:
                a, b = max(0.0, s), min(L, s + dash * 0.55)
                if b > a: pieces.append((p0 + (p1 - p0) * a / L, p0 + (p1 - p0) * b / L))
                s += dash
        else:
            pieces = [(p0, p1)]
        for a, b in pieces:
            pad = sig * 3 + w
            x0 = int(max(0, math.floor(min(a[0], b[0]) - pad))); x1 = int(min(W, math.ceil(max(a[0], b[0]) + pad)))
            y0 = int(max(0, math.floor(min(a[1], b[1]) - pad))); y1 = int(min(H, math.ceil(max(a[1], b[1]) + pad)))
            if x1 <= x0 or y1 <= y0: continue
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
            d = b - a; LL = float(d @ d)
            tt = np.clip(((xx - a[0]) * d[0] + (yy - a[1]) * d[1]) / max(LL, 1e-9), 0, 1)
            dist = np.hypot(xx - (a[0] + tt * d[0]), yy - (a[1] + tt * d[1]))
            core = np.clip(w / 2 + 0.5 - dist, 0, 1)
            gl = np.exp(-dist ** 2 / (2 * sig * sig)) * 0.35 * halo
            v = np.maximum(core, gl) * gain
            reg = img[y0:y1, x0:x1]
            reg += (v[..., None] * col)

def glow_dot(img, x, y, r, col, gain=1.0, halo=3.0):
    pad = int(r * halo * 3 + 4)
    x0, x1 = max(0, int(x - pad)), min(W, int(x + pad)); y0, y1 = max(0, int(y - pad)), min(H, int(y + pad))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
    d = np.hypot(xx - x, yy - y)
    v = np.clip(r + 0.5 - d, 0, 1) + 0.5 * np.exp(-(d / (r * halo)) ** 2)
    img[y0:y1, x0:x1] += v[..., None] * np.asarray(col, np.float32) * gain

def proj1(c, X):
    x, y, z = project(c, np.asarray(X, float)[None])
    return float(x[0]), float(y[0]), float(z[0])

def proj_many(c, P):
    x, y, z = project(c, P)
    out = np.stack([x, y], 1)
    out[z <= 1e-9] = np.nan
    return out

# ---------------------------------------------------------------- the orbit (ecliptic frame, million km)
A_AU = 149.598; ECC = 0.01671
EPS = math.radians(23.44)
L_PERI = math.radians(102.9)                 # the Earth's heliocentric longitude at perihelion (3 Jan)
AX = np.array([0.0, math.sin(EPS), math.cos(EPS)])   # the north pole direction (ecliptic frame)
R_SUN = 0.6957; R_EARTH = 0.006371           # million km

def L_date(day_of_year):
    """heliocentric longitude (rad) — mean motion is close enough for the pictures (equation of centre added)"""
    M = 2 * math.pi * (day_of_year - 3.0) / 365.256
    return L_PERI + M + 2 * ECC * math.sin(M)
def epos(L):
    r = A_AU * (1 - ECC ** 2) / (1 + ECC * math.cos(L - L_PERI))
    return np.array([r * math.cos(L), r * math.sin(L), 0.0])
L_JAN3 = L_PERI; L_JUL5 = L_PERI + math.pi
L_DEC21 = math.radians(90.0); L_JUN21 = math.radians(270.0)

def ecl_to_ecef(theta):
    """3x3: ecliptic -> Earth-fixed, Earth rotation angle theta"""
    return Rz(-theta) @ Rx(EPS)

def theta_noon(L, lon_deg):
    """the rotation angle at which longitude lon_deg has the Sun on its meridian, Earth at longitude L"""
    s = Rx(EPS) @ nrm(-epos(L))
    ra = math.atan2(s[1], s[0])
    return ra - math.radians(lon_deg)

# ---------------------------------------------------------------- one picture of the orbit / Sun / Earth (ecliptic)
SPOTS = np.array([list(ll(a, b)) + [ru, rp, sd] for a, b, ru, rp, sd in
                  [(14.0, 20.0, 0.012, 0.03, 1.0), (-9.0, -35.0, 0.009, 0.022, 3.0), (18.0, 120.0, 0.006, 0.014, 6.0)]])
ROT_S = np.eye(3)

def orbit_picture(c, t, L, theta, emag, smag, orbit_a=1.0, ghost=0.0, axis_a=0.0, sun_gain=2.2, cloud_k=0.9,
                  snow=1.0, sky_gain=1.0, earth_expo=0.55, lab=None, axis_full=True):
    """c: camera in the ecliptic frame (million km). Returns the HDR image; lab gets screen positions."""
    img = np.zeros((H, W, 3), np.float32)
    o, f, r, u, k = c
    sky(img, (o, f, r, u, k), GAL, sky_gain, stars=1.0, band=0.10)
    P = epos(L)
    # the orbit, the Sun–Earth lines
    if orbit_a > 0:
        Ls = np.linspace(0, 2 * math.pi, 721)
        pts = proj_many(c, np.array([epos(a) for a in Ls]))
        glow_lines(img, pts, (0.55, 0.75, 1.0), w=1.6, gain=0.55 * orbit_a, halo=0.7)
    # the Sun (enlarged smag times): k_sun works in solar radii around the Sun
    rs = R_SUN * smag
    cs = (o / rs, f, r, u, k)
    sunk.k_sun(img, cs[0][0], cs[0][1], cs[0][2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, ROT_S, SPOTS,
               t * 0.5, sun_gain, 0.35, 0.0, 0.0, 1.0, 1.0, 0.97, 0.90, 1.0, 0.88, 0.70)
    # the distances: dashed lines from the Sun to the Earth (3 Jan) and to where it will be on 5 Jul
    if ghost > 0:
        for X, col in ((P, (1.0, 0.78, 0.45)), (epos(L_JUL5), (0.6, 0.8, 1.0))):
            seg = proj_many(c, np.array([X * q for q in np.linspace(0.06, 0.93, 40)]))
            glow_lines(img, seg, col, w=1.5, gain=0.7 * ghost, halo=0.5, dash=18.0)
    # the ghost Earth on 5 July
    if ghost > 0:
        Pg = epos(L_JUL5)
        x, y, z = proj1(c, Pg)
        rp = k * R_EARTH * emag / z
        glow_dot(img, x, y, max(2.0, rp * 0.9), (0.6, 0.8, 1.0), gain=0.55 * ghost, halo=1.6)
        if lab is not None: lab['jul'] = [x, y, rp]
    # the Earth (enlarged emag times): render in its own frame
    M = ecl_to_ecef(theta)
    oe = M @ ((o - P) / emag * 1e6)               # km, as if the Earth were its real size
    ce = (oe, M @ f, M @ r, M @ u, k)
    sdir = M @ nrm(-P)
    E.earth(img, ce, sdir, sun_k=18.0, disc_k=0.0, cloud_k=cloud_k, night_k=1.2, snow=snow, expo=earth_expo)
    x, y, z = proj1(c, P)
    rp = k * R_EARTH * emag / z
    if lab is not None:
        lab['earth'] = [x, y, rp]
        xs, ys, zs = proj1(c, np.zeros(3)); lab['sun'] = [xs, ys, k * rs / zs]
    if axis_a > 0:
        draw_axis(img, c, P, R_EARTH * emag, axis_a, lab, full=axis_full)
    return img

def draw_axis(img, c, P, R, a, lab=None, ext=1.55, full=True):
    """the Earth's axis through the poles (only the parts not hidden by the globe) + the perpendicular to the orbit"""
    o = c[0]
    def visible(X):
        # hidden if the segment from the camera to X passes through the sphere first
        d = X - o; L = np.linalg.norm(d); d = d / L
        b = (o - P) @ d; cc = (o - P) @ (o - P) - R * R
        disc = b * b - cc
        if disc <= 0: return True
        t0 = -b - math.sqrt(disc)
        return not (0 < t0 < L - 1e-9)
    n = 160
    ts = np.linspace(-ext, ext, n)
    pts = []
    # outside the globe: bright; through it: faint (as if seen through the planet)
    rp = c[4] * R / max(1e-9, float(np.linalg.norm(P - o)))
    wk = min(1.0, max(0.45, rp / 200.0))
    out_ = np.array([proj_many(c, (P + AX * R * s)[None])[0] if abs(s) >= 1.0 else [np.nan, np.nan] for s in ts])
    inn_ = np.array([proj_many(c, (P + AX * R * s)[None])[0] if abs(s) <= 1.0 else [np.nan, np.nan] for s in ts])
    glow_lines(img, out_, (0.70, 0.90, 1.0), w=2.6 * wk, gain=1.25 * a * wk, halo=1.0 * wk)
    glow_lines(img, inn_, (0.70, 0.90, 1.0), w=1.8 * wk, gain=0.30 * a, halo=0.4 * wk)
    if not full: return
    # the perpendicular to the orbit (dashed)
    up = np.array([0, 0, 1.0])
    pp = np.array([proj_many(c, (P + up * R * s)[None])[0] for s in np.linspace(-ext * 0.95, ext * 0.95, 120)])
    glow_lines(img, pp, (1.0, 1.0, 1.0), w=1.6, gain=0.55 * a, halo=0.5, dash=20.0)
    if lab is not None:
        top = proj_many(c, (P + AX * R * ext)[None])[0]; nup = proj_many(c, (P + up * R * ext * 0.95)[None])[0]
        lab['axis_top'] = [float(top[0]), float(top[1])]; lab['perp_top'] = [float(nup[0]), float(nup[1])]
        # the arc between them, at 1.25 R
        arc = []
        for kk in np.linspace(0, 1, 30):
            v = nrm(up * (1 - kk) + AX * kk)
            arc.append(proj_many(c, (P + v * R * 1.3)[None])[0])
        glow_lines(img, np.array(arc), (1.0, 0.82, 0.45), w=2.6, gain=1.4 * a, halo=1.0)
        mid = proj_many(c, (P + nrm(up + AX) * R * 1.45)[None])[0]
        lab['angle'] = [float(mid[0]), float(mid[1])]

# ---------------------------------------------------------------- post
def post(img, expo=1.0, thr=1.1, bk=0.5, vig=0.22):
    img = np.nan_to_num(img, nan=0.0, posinf=20.0, neginf=0.0)
    img = bloom(img, thr, bk, 1.0)
    return tonemap(vignette(img, vig), expo)

# ---------------------------------------------------------------- ORBIT: the real orbit
T_ORB0, T_ORB1 = 0.0, tk('dive', 6.9)
def orbit_cam(t, el0=28.0, el1=50.0, d0=900.0, d1=780.0, az=38.0):
    k = ease((t - T_ORB0) / (T_ORB1 - T_ORB0 + 0.6))
    el = math.radians(lerp(el0, el1, k)); d = lerp(d0, d1, k); a = math.radians(az + 10 * k)
    o = np.array([math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)]) * d
    tgt = np.array([0.0, 0.0, -25.0])
    return cam(o, tgt, [0, 0, 1.0], 44)

EMAG_FAR = 1300.0; SMAG = 20.0
def shot_orbit(t):
    c = orbit_cam(t)
    lab = {}
    img = orbit_picture(c, t, L_WIN, th_win(t), EMAG_FAR, SMAG, orbit_a=ramp(t, 0.2, 1.4), ghost=ramp(t, 3.4, 4.2), lab=lab)
    return post(img, 1.0), lab

# ---------------------------------------------------------------- DIVE: down to the Earth → AXIS: its axis
T_DIVE0, T_DIVE1 = tk('dive', 6.9) - 0.5, tk('axis', 9.6)
T_AX0, T_AX1 = T_DIVE1, tk('year', 14.4)
L_WIN = L_JAN3

def axis_cam(t):
    k = (t - T_AX0) / (T_AX1 - T_AX0)
    P = epos(L_WIN)
    sdir = nrm(-P)
    side = nrm(np.cross([0, 0, 1.0], sdir))
    # first from above Europe (the question), then down to the side to show the tilt
    el = lerp(2.4, 0.14, ease(min(1.0, max(0.0, (t - T_AX0) / 1.8))))
    v = nrm(side + np.array([0, 0, el]) + sdir * lerp(1.6, 1.35, k))
    d = lerp(0.050, 0.046, ease(min(1.0, max(0.0, k))))
    return cam(P + v * d, P, [0, 0, 1.0], 40)

def face_theta(v_ecl, lon_deg):
    """the rotation angle that puts longitude lon_deg under the direction v_ecl (from the Earth's centre)"""
    q = Rx(EPS) @ nrm(v_ecl)
    return math.atan2(q[1], q[0]) - math.radians(lon_deg)

def th_win(t):
    # Ukraine turned to the axis-shot camera (afternoon there: the Sun low in the south-west), turning slowly
    P = epos(L_WIN)
    return face_theta(axis_cam(T_AX0)[0] - P, 26.0) + (t - T_AX0) * 0.06

def shot_dive(t):
    k = (t - T_DIVE0) / (T_DIVE1 - T_DIVE0)
    P = epos(L_WIN)
    c0 = orbit_cam(T_DIVE0); c1 = axis_cam(T_AX0)
    r0 = c0[0] - P; r1 = c1[0] - P
    e = ease(min(1.0, max(0.0, k)))
    d = math.exp(lerp(math.log(np.linalg.norm(r0)), math.log(np.linalg.norm(r1)), e))
    o = P + slerp(r0, r1, e) * d
    tgt = lerpv(np.array([0.0, 0.0, -25.0]), P, ease(min(1.0, k * 2.5)))
    c = cam(o, tgt, [0, 0, 1.0], lerp(44, 40, e))
    emag = max(1.0, EMAG_FAR * (d / np.linalg.norm(r0)) ** 0.75)
    lab = {}
    img = orbit_picture(c, t, L_WIN, th_win(t), emag, SMAG, orbit_a=1 - ramp(t, T_DIVE0, T_DIVE0 + 1.2), ghost=0.0, lab=lab)
    return post(img, 1.0), lab

def shot_axis(t):
    c = axis_cam(t)
    lab = {}
    img = orbit_picture(c, t, L_WIN, th_win(t), 1.0, SMAG, orbit_a=0.0, ghost=0.0, axis_a=ramp(t, T_AX0 + 1.3, T_AX0 + 2.0), lab=lab)
    return post(img, 1.0), lab

# ---------------------------------------------------------------- YEAR: a year in four seconds
T_YR0, T_YR1 = tk('year', 14.4) - 0.5, tk('kyiv', 18.6)
YEAR_EMAG = 3200.0
def shot_year(t):
    k = (t - T_YR0) / (T_YR1 - T_YR0)
    run = ease(min(1.0, max(0.0, (t - T_YR0 - 0.6) / (T_YR1 - T_YR0 - 1.0))))
    L = L_DEC21 + 2 * math.pi * run
    th = theta_noon(L, 30.5) + t * 2.0
    el = math.radians(lerp(20.0, 26.0, k)); a = math.radians(lerp(-8.0, 4.0, k))
    d = 900.0
    o = np.array([math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)]) * d
    c = cam(o, np.array([0, 0, -30.0]), [0, 0, 1.0], 44)
    lab = {}
    img = orbit_picture(c, t, L, th, YEAR_EMAG, SMAG * 1.2, orbit_a=0.8, ghost=0.0, axis_a=1.0, lab=lab, cloud_k=0.6, axis_full=False)
    # where it is in the year
    lab['month'] = 'грудень' if math.cos(L - L_DEC21) > 0.5 else ('червень' if math.cos(L - L_JUN21) > 0.5 else '')
    return post(img, 1.0), lab

# ---------------------------------------------------------------- KYIV: the dome, the noon Sun
UPK, EASTK, NORTHK = E.local_axes(E.K_LAT, E.K_LON)
C0 = UPK * E.RE
def at(x, y, z): return C0 + EASTK * x + NORTHK * y + UPK * z
def sdir_k(alt, az):
    a, z = math.radians(alt), math.radians(az)
    return nrm(UPK * math.sin(a) + (NORTHK * math.cos(z) + EASTK * math.sin(z)) * math.cos(a))
DOME_R = 5.0

def sun_path_kyiv(date):
    """[(hours from sunrise, alt, az)] for Kyiv on a date (ephem), every 6 minutes"""
    import ephem
    ob = ephem.Observer(); ob.lat, ob.lon = '50.4501', '30.5234'; ob.pressure = 0; ob.horizon = '-0:50'
    ob.date = date + ' 00:00'
    sr = ob.next_rising(ephem.Sun()); ss = ob.next_setting(ephem.Sun())
    out = []
    n = 120
    for i in range(n + 1):
        ob.date = ephem.Date(sr + (ss - sr) * i / n)
        s = ephem.Sun(ob)
        out.append(((ss - sr) * 24 * i / n, math.degrees(s.alt), math.degrees(s.az)))
    return out, (ss - sr) * 24
_P = {}
def paths():
    if not _P:
        _P['w'], _P['wl'] = sun_path_kyiv('2026/12/21')
        _P['s'], _P['sl'] = sun_path_kyiv('2027/06/21')
    return _P

def kyiv_cam(t, t0, t1):
    # from the east-north-east, looking west-south-west: the southern sky (the noon Sun) left of the middle
    k = ease((t - t0) / (t1 - t0))
    o = at(lerp(14.5, 12.5, k), lerp(5.5, 4.5, k), lerp(4.6, 3.8, k))
    return cam(o, at(-3.2, -3.4, lerp(2.4, 2.8, k)), UPK, 54)

def dome_lines(img, c, a):
    if a <= 0: return
    # the dome: the horizon circle and a few meridians, faint
    ring = proj_many(c, np.array([at(DOME_R * math.sin(q), DOME_R * math.cos(q), 0.0) for q in np.linspace(0, 2 * math.pi, 181)]))
    glow_lines(img, ring, (0.8, 0.9, 1.0), w=1.6, gain=0.55 * a, halo=0.6)
    for az in (0, 45, 90, 135):
        q = math.radians(az)
        arc = [at(*(DOME_R * np.array([math.cos(math.radians(e)) * math.sin(q), math.cos(math.radians(e)) * math.cos(q), math.sin(math.radians(e))])))
               for e in np.linspace(0, 180, 91)]
        glow_lines(img, proj_many(c, np.array(arc)), (0.8, 0.9, 1.0), w=1.2, gain=0.22 * a, halo=0.5)

def sun_on_dome(alt, az):
    a, z = math.radians(alt), math.radians(az)
    return at(DOME_R * math.cos(a) * math.sin(z), DOME_R * math.cos(a) * math.cos(z), DOME_R * math.sin(a))

def path_pts(c, path, upto=1.0):
    n = max(2, int(len(path) * upto))
    return proj_many(c, np.array([sun_on_dome(al, az) for _, al, az in path[:n]]))

def kyiv_render(c, sun_alt, snow, beam=None, expo=0.5, ground_k=1.0):
    img = np.zeros((H, W, 3), np.float32)
    expo = expo * (1.0 - 0.32 * snow)                  # under snow: a darker, colder picture (the snow is still bright)
    s = sdir_k(sun_alt, 180.0)
    E.earth(img, c, s, sun_k=18.0, disc_k=0.0, cloud_k=0.0, snow=snow, expo=expo, beam=beam)
    return img

T_KY0, T_KY1 = tk('kyiv', 18.6) - 0.5, tk('beam', 23.4)
def shot_kyiv(t):
    c = kyiv_cam(t, T_KY0, tk('day', 28.8) + 1.0)
    lab = {}
    # winter noon first, then the Sun climbs to the summer noon and the snow melts
    tw = tk('summer', 21.2)
    k = ramp(t, tw - 0.2, tw + 1.4)
    alt = lerp(16.1, 63.0, k)
    img = kyiv_render(c, alt, snow=1.0 - k)
    a = ramp(t, T_KY0 + 0.6, T_KY0 + 1.3)
    dome_lines(img, c, a)
    # the noon Sun on the dome, the angle from the centre
    P0 = at(0, 0, 0)
    for nm, al, kk in (('w', 16.1, 1 - ramp(t, tw + 1.6, tw + 2.4)), ('s', 63.0, ramp(t, tw - 0.2, tw + 1.4))):
        if kk <= 0: continue
        X = sun_on_dome(alt if nm == 's' else al, 180.0) if nm == 's' else sun_on_dome(al, 180.0)
        x, y, z = proj1(c, X); x0, y0, _ = proj1(c, P0)
        glow_lines(img, np.array([[x0, y0], [x, y]]), (1.0, 0.85, 0.5), w=2.2, gain=1.2 * kk * a, halo=0.8)
        h = proj1(c, at(0, -DOME_R, 0))
        glow_lines(img, np.array([[x0, y0], [h[0], h[1]]]), (1.0, 1.0, 1.0), w=1.6, gain=0.6 * kk * a, halo=0.5, dash=16)
        glow_dot(img, x, y, 13.0, (1.0, 0.92, 0.75), gain=6.0 * kk * a, halo=3.0)
        lab['sun_' + nm] = [x, y, kk * a]
    lab['centre'] = list(proj1(c, P0)[:2])
    return post(img, 1.0), lab

# ---------------------------------------------------------------- BEAM: the same light, spread
T_BM0, T_BM1 = tk('beam', 23.4) - 0.5, tk('day', 28.8)
def beam_cam(t):
    k = ease((t - T_BM0) / (T_BM1 - T_BM0))
    o = at(lerp(15.0, 19.0, k), lerp(4.5, 2.5, k), lerp(4.6, 7.0, k))
    return cam(o, at(lerp(-2.0, -3.8, k), lerp(-1.0, -0.6, k), 1.2), UPK, 54)

def blend_cam(c0, c1, k):
    o = lerpv(c0[0], c1[0], k); f = slerp(c0[1], c1[1], k)
    return cam_dir(o, f, UPK, math.degrees(2 * math.atan((H / 2) / lerp(c0[4], c1[4], k))))

def shot_beam(t):
    c = blend_cam(kyiv_cam(t, T_KY0, tk('day', 28.8) + 1.0), beam_cam(t), ease((t - T_BM0) / 1.2))
    lab = {}
    tl = tk('tilt', 25.0)
    k = ramp(t, tl, tl + 1.8)                              # 63° -> 16°
    alt = lerp(63.0, 16.1, k)
    on = ramp(t, T_BM0 + 0.3, T_BM0 + 1.1)
    TOP = 9.0
    bm = dict(centre=at(0, 0, 0), side=2.4, top=TOP, glow=(0.16 + 0.22 * k) * on, foot=7.0 * on, ground=1.0 - (0.55 + 0.15 * k) * on, up=UPK)
    img = kyiv_render(c, alt, snow=k, beam=bm)
    s = sdir_k(alt, 180.0)
    hs = 1.2; L = hs / math.sin(math.radians(alt))
    # the tube's four long edges, from the top of the light down to the corners of the footprint
    b1 = nrm(np.cross(s, UPK)); b2 = nrm(np.cross(s, b1))
    for sa, sb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        base = at(0, 0, 0) + b1 * hs * sa + b2 * hs * sb
        g = base - s * ((base - at(0, 0, 0)) @ UPK) / (s @ UPK)      # where that edge meets the ground
        seg = [g + s * TOP * q for q in np.linspace(0, 1, 24)]
        pts = proj_many(c, np.array(seg))
        for m in range(len(pts) - 1):
            glow_lines(img, pts[m:m + 2], (1.0, 0.85, 0.5), w=lerp(1.6, 2.2, k), gain=lerp(0.8, 1.7, k) * on * (1 - 0.8 * m / len(pts)), halo=0.6)
    corners = [at(-hs, -L, 0), at(hs, -L, 0), at(hs, L, 0), at(-hs, L, 0)]
    glow_lines(img, proj_many(c, np.array(corners)), (1.0, 0.8, 0.45), w=2.0, gain=0.9 * on, halo=0.7, closed=True)
    lab['foot'] = list(proj1(c, at(0, -L, 0))[:2]) + [on]
    lab['area'] = 1.0 / math.sin(math.radians(alt)) / (1.0 / math.sin(math.radians(63.0)))
    lab['alt'] = alt
    return post(img, 1.0), lab

# ---------------------------------------------------------------- DAY: 8 h vs 16.5 h
T_DY0, T_DY1 = tk('day', 28.8) - 0.5, tk('aus', 33.0)
def day_cam(t):
    k = ease((t - T_DY0) / (T_DY1 - T_DY0))
    # from the north, looking south: east on the left, west on the right — the classic sun-path view
    o = at(lerp(1.5, 0.5, k), lerp(14.0, 13.0, k), lerp(5.2, 4.8, k))
    return cam(o, at(0.0, -2.5, 2.3), UPK, 58)

def shot_day(t):
    c = blend_cam(beam_cam(T_BM1), day_cam(t), ease((t - T_DY0) / 1.3))
    P = paths()
    lab = {}
    run = ramp(t, T_DY0 + 0.7, T_DY1 - 0.6)
    # the winter Sun lights the ground (it runs its short path); snow
    img = np.zeros((H, W, 3), np.float32)
    E.earth(img, c, sdir_k(14.0, 165.0), sun_k=18.0, disc_k=0.0, cloud_k=0.0, snow=1.0, expo=0.5 * 0.68)
    dome_lines(img, c, 1.0)
    a = ramp(t, T_DY0 + 0.3, T_DY0 + 0.9)
    # summer path drawn as it runs (16.5 h), winter path (8 h) — both suns move at the same clock speed
    for key, col, nm in (('s', (1.0, 0.85, 0.45), 'sum'), ('w', (0.6, 0.85, 1.0), 'win')):
        p = P[key]; hours = P[key + 'l']
        hrs = run * 16.52
        frac = min(1.0, hrs / hours)
        pts = path_pts(c, p, 1.0)
        glow_lines(img, pts, col, w=1.4, gain=0.35 * a, halo=0.5, dash=14)
        n = max(2, int(frac * (len(p) - 1)) + 1)
        glow_lines(img, pts[:n], col, w=3.0, gain=1.3 * a, halo=1.0)
        hx, hy = pts[n - 1]
        glow_dot(img, hx, hy, 11.0, (1.0, 0.92, 0.75), gain=5.0 * a, halo=2.6)
        lab[nm] = [float(hx), float(hy), min(hrs, hours), a]
    return post(img, 1.0), lab

# ---------------------------------------------------------------- AUS: round the globe to Australia
T_AU0, T_AU1 = tk('aus', 33.0) - 0.5, tk('end', 38.6)
def shot_aus(t):
    k = (t - T_AU0) / (T_AU1 - T_AU0)
    L = L_DEC21
    P = epos(L)
    th = theta_noon(L, 145.0)                          # noon over eastern Australia
    M = ecl_to_ecef(th)
    up_k = M.T @ ll(50.45, 30.52); up_a = M.T @ ll(-30.0, 140.0)
    e = ease(min(1.0, k * 1.1))
    v = slerp(up_k, nrm(up_a + nrm(-P) * 0.2), e)
    d = lerp(0.022, 0.026, k)
    o = P + v * d
    c = cam(o, P, M.T @ np.array([0, 0, 1.0]) * (1 - e) + np.array([0, 0, 1.0]) * e, 42)
    lab = {}
    img = orbit_picture(c, t, L, th, 1.0, SMAG, orbit_a=0.0, ghost=0.0, lab=lab, cloud_k=0.9, snow=1.0)
    xs = proj1(c, P + up_a * R_EARTH * 0.92)
    lab['aus'] = [xs[0], xs[1]]
    return post(img, 1.0), lab

def slerp(a, b, k):
    a = nrm(a); b = nrm(b)
    om = math.acos(max(-1.0, min(1.0, float(a @ b))))
    if om < 1e-6: return a
    return nrm((math.sin((1 - k) * om) * a + math.sin(k * om) * b) / math.sin(om))

# ---------------------------------------------------------------- END: back out to the orbit
T_EN0, T_EN1 = tk('end', 38.6) - 0.5, DUR
def shot_end(t):
    k = (t - T_EN0) / (T_EN1 - T_EN0)
    c = orbit_cam(lerp(1.5, 5.0, ease(min(1.0, k * 1.5))))
    L = L_JAN3
    lab = {}
    img = orbit_picture(c, t, L, theta_noon(L, 30.5) + t * 0.15, EMAG_FAR, SMAG, orbit_a=1.0, ghost=1.0, lab=lab)
    return post(img, 1.0), lab

# ---------------------------------------------------------------- the timeline
SHOTS = [(0.0, T_ORB1, shot_orbit), (T_DIVE0, T_DIVE1, shot_dive), (T_AX0, T_AX1, shot_axis), (T_YR0, T_YR1, shot_year),
         (T_KY0, T_KY1, shot_kyiv), (T_BM0, T_BM1, shot_beam), (T_DY0, T_DY1, shot_day), (T_AU0, T_AU1, shot_aus),
         (T_EN0, DUR + 1, shot_end)]

def frame(t):
    act = [(a, b, f) for a, b, f in SHOTS if a <= t <= b]
    out = None; lab = {}
    for a, b, f in act:
        im, lb = f(t)
        if out is None: out = im; lab = lb
        else:
            prev_end = max(bb for aa, bb, ff in act if ff is not f and aa < a)
            kk = sm((t - a) / max(1e-3, prev_end - a))
            out = out * (1 - kk) + im * kk
            if kk > 0.5: lab = lb
    if out is None: out = np.zeros((H, W, 3), np.float32)
    return Image.fromarray(to_u8(out)), lab

def job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return i, None
    im, lab = frame(i / FPS)
    im.save(p + '.tmp.jpg', quality=94); os.replace(p + '.tmp.jpg', p)
    return i, lab

def jsonable(d):
    out = {}
    for k_, v in d.items():
        if isinstance(v, (list, tuple, np.ndarray)): out[k_] = [float(x) for x in v]
        elif isinstance(v, (int, float, np.floating)): out[k_] = float(v)
        else: out[k_] = v
    return out

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == 'still':
        sp = os.environ.get('STILL_DIR', '/tmp')
        for a in sys.argv[2:]:
            im, lab = frame(float(a)); im.save(os.path.join(sp, f'st_{a}.jpg'), quality=90); print(a, jsonable(lab))
        sys.exit()
    n = int(DUR * FPS)
    todo = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    LP = os.path.join(WORK, 'labels.json')
    labs = json.load(open(LP)) if os.path.exists(LP) else {}
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as pool:
        for cnt, (i, lab) in enumerate(pool.imap_unordered(job, todo, chunksize=1)):
            if lab is not None: labs[str(i)] = jsonable(lab)
            if cnt % 30 == 0:
                print('frame', cnt, '/', len(todo), flush=True)
                json.dump(labs, open(LP, 'w'))
    json.dump(labs, open(LP, 'w'))
    print('frames done', n)
