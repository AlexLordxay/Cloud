# «Магнітні бурі» — every frame (1080x1920, 30 fps). Shots overlap and dissolve; the camera never stops.
#   S1 0.0–5.2   night Earth from orbit, the aurora oval on the northern limb; the Sun rises over the limb
#   S2 4.6–8.8   REAL: NASA SDO 304 Å, the X3.3 flare of 23.10.2024 — slow push into the flare on the limb
#   S3 8.2–12.8  REAL: SOHO/LASCO C2, the CME of 23.07.2012 (optical-flow in-betweens of the 12-min images)
#   S4 12.2–22.6 one flight: the CME bubble crosses (compressed) space to the Earth → the magnetosphere: bow shock,
#                field lines squeezed on the day side, the plasma flowing round, some of it down to the poles → the ovals light
#   S5 22.0–25.8 REAL: aurora from the ISS (NASA iss072e159172)
#   S6 25.2–30.9 storm effects: GPS and geostationary orbits round the night Earth, a strong oval
#   S7 30.3–38.9 1859: the oval pushed far south over the Americas, Cuba and Hawaii marked
#   S8 38.3–55.0 health: the dipole field round a day-lit Earth; it trembles by < 2 % (counters in captions.py)
#   S9 54.4–57.4 down over Ukraine at night: red aurora over the northern horizon
#   S10 56.8–62.4 the author's photo IMG_3810 (Chernivtsi oblast, 20.01.2026), slow push-in
#   S11 61.8–72.0 the author's photo IMG_3842 (two layers: red above, green low)
# Geometry: Earth radius 1, Earth-fixed frame (z = north). Earth maps from nuclear_winter (textures.py).
#   python3 render.py [workers] [frame …]   -> work/magnetic_storms/frames/f_%05d.jpg
import math, os, sys, json, importlib.util
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(TOOLS, 'scenes', 'real_motion')]
import render as R
from render import sm, ramp, lerp, nrm, stars_bg
_spec = importlib.util.spec_from_file_location('nw_render', os.path.join(TOOLS, 'scenes', 'nuclear_winter', 'render.py'))
NW = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(NW)
WORK = os.path.join(TOOLS, 'work', 'magnetic_storms'); OUT = os.path.join(WORK, 'frames')
ASSETS = os.path.join(HERE, 'assets')
W, H, FPS = 1080, 1920, 30
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']
KM = 1 / 6371.0
ll = NW.ll
_maps0 = NW.maps
def _maps():
    M = _maps0()
    if 'hi' not in M:
        M['clouds'] = np.load(os.path.join(WORK, 'clouds4k.npy'), mmap_mode='r')
        M['hi'] = True
    return M
NW.maps = _maps

# 20.01.2026 ~21 UT (the storm over Europe): the Sun over 20 °S, 135 °W; the dipole pole (IGRF-14, 2025) 80.8 °N 72.7 °W
SUN = ll(-20.0, -135.0)
MAG = ll(80.8, -72.7)
SUN1859 = ll(8.0, 75.0)                # 2.09.1859 ~05 UT: night over the Americas
MAG1859 = ll(77.0, -66.0)
ST0 = dict(weeks=0, soot=0, snow=0, crops=0, dim=0, lights_out=0, restore=0)

def basis(m):
    e1 = nrm(np.cross([0.0, 0.0, 1.0], m) if abs(m[2]) < 0.99 else np.cross([1.0, 0, 0], m)); e2 = np.cross(m, e1)
    return e1, e2

# ---------------------------------------------------------------- periodic 1-D noise (curtains, rays)
_N = {}
def noise1(key, n, octaves, seed):
    if key not in _N:
        g = np.random.default_rng(seed); acc = np.zeros(n, np.float32)
        for f, a in octaves:
            ph = g.uniform(0, 2 * np.pi, f); am = g.uniform(0.5, 1, f) / np.sqrt(np.arange(1, f + 1))
            x = np.arange(n) / n * 2 * np.pi
            for k in range(f):
                acc += a * am[k] * np.sin((k + 1) * x * (f // max(1, f // 2)) / 1 + ph[k]) / f * 2
        acc = (acc - acc.min()) / (acc.max() - acc.min())
        _N[key] = acc
    return _N[key]

def lookup(arr, x):
    """periodic linear lookup, x in cycles"""
    n = len(arr); f = (x % 1.0) * n; i = np.floor(f).astype(int); a = f - i
    return arr[i % n] * (1 - a) + arr[(i + 1) % n] * a

def ray_noise():
    """fine rays along the curtain (many harmonics) and slow folds"""
    if 'rays' not in _N:
        g = np.random.default_rng(5); n = 8192; x = np.arange(n) / n * 2 * np.pi
        r = np.zeros(n, np.float32)
        for k in range(40, 900, 7):
            r += g.uniform(0.3, 1) * np.sin(k * x + g.uniform(0, 6.3)) / math.sqrt(k)
        r = (r - r.min()) / (r.max() - r.min()); _N['rays'] = r
        f = np.zeros(n, np.float32)
        for k in range(2, 14):
            f += g.uniform(0.3, 1) * np.sin(k * x + g.uniform(0, 6.3)) / k
        _N['folds'] = f / np.abs(f).max()
        b = np.zeros(n, np.float32)
        for k in range(3, 60, 2):
            b += g.uniform(0.3, 1) * np.sin(k * x + g.uniform(0, 6.3)) / k ** 0.7
        _N['bright'] = (b - b.min()) / (b.max() - b.min())
    return _N['rays'], _N['folds'], _N['bright']

# ---------------------------------------------------------------- the aurora: emission integrated through a shell
def aurora(o, d, tground, A, t):
    """o: camera; d: (n,3) unit rays; tground: (n,) distance to the ground (inf if none); A: oval parameters.
    Oxygen 557.7 nm (green, peak ~110 km) and 630 nm (red, 200–400 km); a thin N2+ pink-violet fringe at the bottom."""
    rt = 1 + 520 * KM
    b = d @ o; c = o @ o - rt * rt; disc = b * b - c
    out = np.zeros((len(d), 3), np.float32)
    ok = disc > 0
    if not ok.any(): return out
    sq = np.sqrt(np.maximum(disc, 0))
    t0 = np.maximum(-b - sq, 0); t1 = np.minimum(-b + sq, tground)
    ok &= t1 > t0
    idx = np.nonzero(ok)[0]
    if len(idx) == 0: return out
    m = A['mag']; e1, e2 = basis(m); sdir = A['sun']
    sp = sdir - (sdir @ m) * m; sp = nrm(sp) if np.linalg.norm(sp) > 1e-6 else e1
    rays, folds, bright = ray_noise()
    NS = A.get('steps', 22)
    acc = np.zeros((len(idx), 3), np.float32)
    jit = (np.sin(idx * 12.9898) * 43758.5453) % 1.0
    T0 = t0[idx]; DT = (t1[idx] - t0[idx]); D = d[idx]
    gcol = np.array([0.16, 1.0, 0.36], np.float32); rcol = np.array([1.0, 0.04, 0.10], np.float32)
    pcol = np.array([0.75, 0.25, 0.85], np.float32)
    th0, wg, wr, kg, kr, shiftr = A['th0'], A['wg'], A['wr'], A['kg'], A['kr'], A.get('shift_r', 2.0)
    tt_ = A.get('tt', t)
    for s in range(NS):
        u = (s + jit) / NS
        tt = T0 + DT * u
        P = o + tt[:, None] * D
        r = np.linalg.norm(P, axis=1); h = (r - 1) / KM
        Pn = P / r[:, None]
        mz = Pn @ m
        colat = np.degrees(np.arccos(np.clip(np.abs(mz), 0, 1)))
        px = Pn @ e1; py = Pn @ e2
        ang = np.arctan2(py, px) / (2 * np.pi)
        # local time: 1 at magnetic midnight, 0 at noon
        cosn = -(px * (sp @ e1) + py * (sp @ e2)) / np.maximum(np.sqrt(px * px + py * py), 1e-6)
        night = 0.5 + 0.5 * cosn
        th = th0 + 3.0 * (night - 0.5) + 2.0 * lookup(folds, ang + tt_ * 0.004) + 0.25 * np.sin(ang * 2 * np.pi * 7 + tt_ * 0.15)
        dth = colat - th
        ray = 0.08 + 1.6 * lookup(rays, ang * 3 + tt_ * 0.003 + 0.002 * np.sin(tt_ * 0.7)) ** 4
        br = (0.04 + 0.96 * lookup(bright, ang + tt_ * 0.01) ** 3) * (0.15 + 0.5 * night ** 2 + 1.6 * np.exp(-((cosn - 1) / 0.25) ** 2))
        # two or three parallel arcs (the main one bright, others fainter, poleward)
        arcs = np.exp(-(dth / wg) ** 2) + 0.45 * np.exp(-((dth + 2.6 * wg + 0.4 * lookup(folds, ang * 2 + 0.3)) / (wg * 0.8)) ** 2) \
            + 0.25 * np.exp(-((dth + 5.5 * wg) / (wg * 1.4)) ** 2)
        g_h = 1 / (1 + np.exp(-(h - 100) / 3.0)) * np.exp(-np.maximum(h - 100, 0) / 38)
        r_h = np.exp(-((h - 280) / 90) ** 2) * (h > 140)
        p_h = np.exp(-((h - 95) / 5) ** 2)
        G = kg * arcs * ray * br * g_h
        Rd = kr * np.exp(-((dth + shiftr) / wr) ** 2) * (0.45 + 0.55 * ray) * (0.3 + 0.7 * br) * r_h
        Pp = kg * 0.35 * arcs * ray * br * p_h
        if A.get('north_only'):
            nk = np.clip(mz * 8, 0, 1); G = G * nk; Rd = Rd * nk; Pp = Pp * nk
        acc += (G[:, None] * gcol + Rd[:, None] * rcol + Pp[:, None] * pcol)
    acc *= (DT / KM / NS)[:, None] * 0.004
    out[idx] = acc
    return out

# ---------------------------------------------------------------- an Earth view (Earth from nuclear_winter + aurora)
def rays_grid(f, r, u, k, step):
    ys, xs = np.mgrid[0:H:step, 0:W:step].astype(np.float32)
    X = (xs + step / 2 - 0.5 - W / 2) / k; Y = -(ys + step / 2 - 0.5 - H / 2) / k
    d = f[None, None] + X[..., None] * r + Y[..., None] * u
    return d / np.linalg.norm(d, axis=-1, keepdims=True)

def sphere_t(o, d, R=1.0):
    b = d @ o; c = o @ o - R * R; disc = b * b - c
    t = -b - np.sqrt(np.maximum(disc, 0))
    return np.where((disc > 0) & (t > 0), t, np.inf)

def up2(a, step):
    """half-res float image -> full res, smooth"""
    if step == 1: return a
    from scipy.ndimage import zoom
    return zoom(a, (step, step, 1), order=1)[:H, :W]

def earth_view(t, p, g, up, fov, sun, A=None, bg_k=0.6, star_pan=(0, 0), lights_k=1.0, step=2):
    f = nrm(g - p); r = nrm(np.cross(f, up)); u = np.cross(r, f)
    k = (H / 2) / math.tan(math.radians(fov) / 2)
    bg = stars_bg(dx=star_pan[0], dy=star_pan[1], k=0.6) ** 1.6 * bg_k
    st = dict(ST0); st['lights_out'] = 1 - lights_k
    img, hit, P = NW.earth(p, f, r, u, k, t, sun, st, [], bg)
    cam = R.Cam(p, g, fov=fov, up=up)
    if A is not None:
        d = rays_grid(f, r, u, k, step); hh, ww = d.shape[:2]
        d2 = d.reshape(-1, 3)
        em = aurora(p, d2, sphere_t(p, d2), A, t).reshape(hh, ww, 3)
        img = img + up2(em, step) * A.get('gain', 1.0)
        # the oval's light on the clouds and snow below it
        if A.get('ground', 0) > 0 and hit.any():
            Ph = P[hit]; mz = np.abs(Ph @ A['mag']); colat = np.degrees(np.arccos(np.clip(mz, 0, 1)))
            gl = np.exp(-((colat - A['th0']) / (A['wg'] * 2.2)) ** 2) * A['ground']
            img[hit] += gl[:, None] * np.array([0.05, 0.22, 0.10])
    return img, cam, (f, r, u, k)

def occluded(p, X):
    """X: (n,3) points; True where the Earth (radius 1) hides them from p"""
    dv = X - p; dist = np.linalg.norm(dv, axis=1); dn = dv / dist[:, None]
    b = dn @ p; c = p @ p - 1; disc = b * b - c
    tt = -b - np.sqrt(np.maximum(disc, 0))
    return (disc > 0) & (tt > 0) & (tt < dist - 1e-3)

def polyline(img, cam, p, pts, col, a=1.0, width=2, layer=None):
    """pts (n,3): projected, hidden behind the Earth, faded behind the camera"""
    x, y, z = cam.proj(pts)
    vis = (z > 0.05) & ~occluded(p, pts)
    segs = []
    cur = []
    for i in range(len(pts)):
        if vis[i]: cur.append((float(x[i]), float(y[i])))
        else:
            if len(cur) > 1: segs.append((cur, a))
            cur = []
    if len(cur) > 1: segs.append((cur, a))
    if layer is not None: layer.extend(segs)
    else: R.lines(img, segs, col, width=width)

def draw_lines(img, segs, col, width=2, k=1.0, blur=0):
    """many polylines at once (one 2x canvas), optional soft glow"""
    if not segs: return
    im = Image.new('L', (W * 2, H * 2), 0); d = ImageDraw.Draw(im)
    for pts, a in segs:
        if len(pts) > 1: d.line([(2 * x, 2 * y) for x, y in pts], fill=int(255 * min(1, max(0, a))), width=width * 2)
    m = np.asarray(im.resize((W, H), Image.LANCZOS), np.float32) / 255
    img += m[..., None] * np.array(col) * k
    if blur:
        from scipy.ndimage import gaussian_filter
        s = m[::2, ::2]; gsm = gaussian_filter(s, blur)
        img += up2(gsm[..., None], 2) * np.array(col) * k * 0.9

def splat(img, xs, ys, w, col, step=2, blur=1.2):
    """points added at half res, blurred (soft plasma)"""
    from scipy.ndimage import gaussian_filter
    hh, ww = H // step, W // step
    acc = np.zeros((hh, ww, 3), np.float32)
    xi = (np.asarray(xs) / step).astype(int); yi = (np.asarray(ys) / step).astype(int)
    m = (xi >= 0) & (xi < ww) & (yi >= 0) & (yi < hh)
    if not m.any(): return
    cols = np.broadcast_to(np.asarray(col, np.float32), (len(xs), 3))[m] * np.asarray(w, np.float32).reshape(-1, 1)[m] if np.ndim(w) else np.broadcast_to(np.asarray(col, np.float32), (len(xs), 3))[m] * w
    np.add.at(acc, (yi[m], xi[m]), cols)
    acc = gaussian_filter(acc, (blur, blur, 0))
    img += up2(acc, step)

# ---------------------------------------------------------------- the magnetosphere
def field_line(L, phi, m, e1, e2, sdir, comp, tail, n=90):
    """a dipole line r = L cos²λ in the meridian at magnetic longitude phi, squeezed on the day side, stretched at night"""
    lam_max = math.acos(math.sqrt(min(1.0, 1.02 / L)))
    lam = np.linspace(-lam_max, lam_max, n)
    r = L * np.cos(lam) ** 2
    eq = math.cos(phi) * e1 + math.sin(phi) * e2
    P = (r * np.cos(lam))[:, None] * eq + (r * np.sin(lam))[:, None] * m
    rr = np.linalg.norm(P, axis=1); Pn = P / rr[:, None]
    day = np.clip(Pn @ sdir, 0, 1); nightc = np.clip(-(Pn @ sdir), 0, 1)
    sq = 1 - comp * day * np.clip((rr - 1.2) / 6, 0, 1)
    P = P * sq[:, None]
    P = P - sdir[None] * (tail * nightc * np.clip((rr - 2.0) / 5, 0, 1) ** 1.5 * rr * 0.8)[:, None]
    return P

def tail_line(lat_foot, phi, m, e1, e2, sdir, length, spread):
    """an open line: from the polar cap up and back along the tail"""
    s = np.linspace(0, 1, 90)
    eq = math.cos(phi) * e1 + math.sin(phi) * e2
    hemi = 1 if lat_foot > 0 else -1
    foot = math.cos(math.radians(abs(lat_foot))) * eq + hemi * math.sin(math.radians(abs(lat_foot))) * m
    side = hemi * m * spread + eq * 0.35 * spread * math.sin(phi)
    P = foot[None] * (1 + 3 * s[:, None]) * (1 - s[:, None]) + (side - sdir * length)[None] * s[:, None] ** 1.3
    # smooth the bend: up first, then back
    lift = np.sin(np.pi * np.clip(s, 0, 0.5)) [:, None] * hemi * m * spread * 0.35
    return P + lift

def bow_rings(r0, sdir, e1, e2, n_rings=11, flare=1.0, xmin=-30):
    """rings of the bow-shock paraboloid x = r0 - rho²/(2 r0 flare) (x along the Sun)"""
    out = []
    for i in range(n_rings):
        x = r0 - (i / (n_rings - 1)) ** 1.6 * (r0 - xmin)
        rho = math.sqrt(max(0.0, 2 * r0 * flare * (r0 - x)))
        a = np.linspace(0, 2 * np.pi, 140)
        pts = x * sdir[None] + rho * (np.cos(a)[:, None] * e1 + np.sin(a)[:, None] * e2)
        out.append((pts, 1 - i / n_rings))
    for j in range(16):                       # meridians
        a = j / 16 * 2 * np.pi
        xs = r0 - np.linspace(0, 1, 60) ** 1.6 * (r0 - xmin)
        rho = np.sqrt(np.maximum(0, 2 * r0 * flare * (r0 - xs)))
        pts = xs[:, None] * sdir[None] + rho[:, None] * (math.cos(a) * e1 + math.sin(a) * e2)[None]
        out.append((pts, 0.8))
    return out

def bow_sheet(r0, sdir, e1, e2, n=26000, flare=1.0, xmin=-34):
    key = ('bow', round(r0, 2))
    if 'bowu' not in _P:
        g = np.random.default_rng(8); _P['bowu'] = (g.random(n), g.uniform(0, 2 * np.pi, n))
    u, a = _P['bowu']
    x = r0 - u ** 1.3 * (r0 - xmin)
    rho = np.sqrt(np.maximum(0, 2 * r0 * flare * (r0 - x)))
    pts = x[:, None] * sdir[None] + rho[:, None] * (np.cos(a)[:, None] * e1 + np.sin(a)[:, None] * e2)
    w = np.clip((x - xmin) / 12, 0, 1) * (0.6 + 0.4 * np.clip((x - r0 + 8) / 8, 0, 1))
    return pts, w

# solar wind particles (fixed set)
_P = {}
def wind_set(n=1800, seed=3):
    if 'w' not in _P:
        g = np.random.default_rng(seed)
        b = np.sqrt(g.random(n)) * 28; ph = g.uniform(0, 2 * np.pi, n); x0 = g.uniform(0, 1, n)
        _P['w'] = (b, ph, x0, g.uniform(0.7, 1.3, n))
        k = 70
        _P['c'] = (g.uniform(0, 2 * np.pi, k), g.uniform(0, 1, k), g.choice([-1, 1], k), g.uniform(0.85, 1.15, k))
    return _P['w'], _P['c']

def wind_pos(x, b, ph, rbs, sdir, e1, e2, flare=1.15):
    """flow round the bow shock: rho² = b² + rho_s(x)² (flux kept between the streamlines)"""
    rs2 = np.maximum(0, 2 * rbs * flare * (rbs - x)); rs2 = np.where(x < rbs + 3, rs2, 0)
    rho = np.sqrt(b * b + rs2 * np.clip((rbs + 3 - x) / 3, 0, 1))
    return x[:, None] * sdir[None] + rho[:, None] * (np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2)

def magnetosphere(img, cam, p, t, M):
    """M: dict(sun, mag, comp, tail, r0 (magnetopause), rbs (bow shock), lines_a, wind_a, wind_speed, capture (0..1 progress),
    bow_a, field_jiggle)"""
    m = M['mag']; s = M['sun']
    e1, e2 = basis(m)
    # the plane through the dipole and the Sun: meridians around it
    sp = nrm(s - (s @ m) * m); sq_ = np.cross(m, sp)
    segs_b, segs_f, segs_t, segs_w = [], [], [], []
    la = M.get('lines_a', 1.0)
    bs1, bs2 = basis(s)                                    # perpendicular to the Sun line (bow shock, wind)
    if la > 0:
        jig = M.get('jiggle', 0.0)
        Lday = M.get('Lday', (2.2, 3.2, 4.4, 5.8, 7.4, 9.0))
        Lnight = M.get('Lnight', (2.2, 3.2, 4.4, 5.8, 7.4, 9.0, 11.5, 14.5, 18.5))
        lines = [(0.0, L, 1.0) for L in Lday] + [(math.pi, L, 1.0) for L in Lnight]
        for d_ in (-0.65, 0.65):
            lines += [(d_, L, 0.32) for L in (3.0, 5.0, 7.0)] + [(math.pi + d_, L, 0.32) for L in (3.0, 5.0, 7.0, 10.0)]
        for i, (phi, L, a0) in enumerate(lines):
            Lx = L * (1 + jig * math.sin(t * 2.1 + L * 1.7 + i))
            P = field_line(Lx, phi, m, sp, sq_, s, M['comp'], M['tail'], n=140 if L > 9 else 90)
            P = P[(P @ s) > -46]
            if len(P) < 2: continue
            # a loop whose plane holds the line of sight collapses to a bright bar: fade it
            eqd = math.cos(phi) * sp + math.sin(phi) * sq_; pn = nrm(np.cross(eqd, m))
            edge = abs(float(pn @ nrm(-p)))
            polyline(img, cam, p, P, None, a=la * a0 * (0.9 if L < 9 else 0.65) * min(1.0, max(0.0, (edge - 0.08) * 4)), layer=segs_f)
    if M.get('bow_a', 0) > 0:
        bp = bow_sheet(M['rbs'], s, bs1, bs2)
        x_, y_, z_ = cam.proj(bp[0])
        vis_ = (z_ > 0.1) & ~occluded(p, bp[0])
        splat(img, x_[vis_], y_[vis_], bp[1][vis_] * M['bow_a'] * 0.10, (0.55, 0.45, 1.0), blur=3.0)
    draw_lines(img, segs_f, (0.35, 0.65, 1.0), width=2, k=0.9, blur=2.5)
    draw_lines(img, segs_t, (0.30, 0.55, 1.0), width=2, k=0.8, blur=2.5)
    # the solar wind
    wa = M.get('wind_a', 0)
    if wa > 0:
        (b, ph, x0, spd), (cph, cph0, chemi, cspd) = wind_set()
        span = 70.0; X0 = 40.0
        x = X0 - ((x0 * span + t * M.get('wind_speed', 9.0) * spd) % span)
        P1 = wind_pos(x, b, ph, M['rbs'], s, bs1, bs2)
        P0 = wind_pos(x + 0.45 * spd, b, ph, M['rbs'], s, bs1, bs2)
        fade = np.clip((X0 - x) / 6, 0, 1) * np.clip((x + span - X0 + 0) / 8, 0, 1)
        xs_, ys_, ws_ = [], [], []
        for j, (dx, wj) in enumerate(((0.0, 1.0), (0.12, 0.6), (0.24, 0.35), (0.36, 0.18))):
            Pj = wind_pos(x + dx * spd, b, ph, M['rbs'], s, bs1, bs2)
            xj, yj, zj = cam.proj(Pj)
            ok_ = (zj > 0.1) & ~occluded(p, Pj)
            xs_.append(xj[ok_]); ys_.append(yj[ok_]); ws_.append((fade * spd * wj)[ok_])
        splat(img, np.concatenate(xs_), np.concatenate(ys_), np.concatenate(ws_) * wa * 0.55, (1.0, 0.82, 0.55), blur=0.9)
        # streamlines in the plane facing the camera, with bright pulses running along them
        phr = math.atan2(cam.r @ bs2, cam.r @ bs1)
        segs_s = []; px_, py_, pw_ = [], [], []
        xs_line = np.linspace(X0, X0 - span, 160)
        for side_ in (0, math.pi):
            for bi, bb in enumerate(np.linspace(0.6, 26, 24)):
                phv = np.full(len(xs_line), phr + side_)
                Pl = wind_pos(xs_line, np.full(len(xs_line), bb), phv, M['rbs'], s, bs1, bs2)
                polyline(img, cam, p, Pl, None, a=wa * 0.07 * np.clip(1 - bb / 30, 0.3, 1), layer=segs_s)
                for q in range(3):
                    xp = X0 - ((q / 3 + bi * 0.137 + side_ * 0.05 + t * M.get('wind_speed', 9.0) / span * 1.1) % 1.0) * span
                    xt = xp + np.linspace(0, 2.2, 10)
                    Pp = wind_pos(xt, np.full(10, bb), np.full(10, phr + side_), M['rbs'], s, bs1, bs2)
                    xx_, yy_, zz_ = cam.proj(Pp); okp = (zz_ > 0.1) & ~occluded(p, Pp)
                    fd = float(np.clip((X0 - xp) / 6, 0, 1) * np.clip((xp - (X0 - span)) / 8, 0, 1))
                    px_.append(xx_[okp]); py_.append(yy_[okp]); pw_.append((np.linspace(1, 0.1, 10) * fd)[okp])
        draw_lines(img, segs_s, (1.0, 0.85, 0.6), width=1, k=0.8, blur=1.5)
        if px_:
            splat(img, np.concatenate(px_), np.concatenate(py_), np.concatenate(pw_) * wa * 0.9, (1.0, 0.85, 0.6), blur=1.1)
        # the few that get in: along the lines to the poles (the cusps and the night side)
        cap = M.get('capture', 0)
        if cap > 0:
            xs_, ys_, ws_ = [], [], []
            for i in range(len(cph)):
                prog = ((cph0[i] + t * 0.22 * cspd[i]) % 1.0)
                if prog > cap * 1.2: continue
                L = 9.0
                phi = cph[i] * 0.25 + (0 if i % 3 else math.pi)       # mostly from the day side, some from the tail
                lam_f = math.acos(math.sqrt(1.02 / L))
                ks = np.linspace(max(0, prog - 0.12), prog, 8)
                lam = chemi[i] * ks * lam_f
                r = L * np.cos(lam) ** 2
                eq = math.cos(phi) * sp + math.sin(phi) * sq_
                P = (r * np.cos(lam))[:, None] * eq + (r * np.sin(lam))[:, None] * m
                rr = np.linalg.norm(P, axis=1); Pn = P / rr[:, None]
                day = np.clip(Pn @ s, 0, 1); nightc = np.clip(-(Pn @ s), 0, 1)
                P = P * (1 - M['comp'] * day * np.clip((rr - 1.2) / 6, 0, 1))[:, None]
                P = P - s[None] * (M['tail'] * nightc * np.clip((rr - 2.0) / 5, 0, 1) ** 1.5 * rr * 0.8)[:, None]
                # a little spiral round the line
                P = P + 0.12 * np.sin(ks * 90)[:, None] * sq_[None]
                xx, yy, zz = cam.proj(P)
                hid = occluded(p, P)
                for j in range(len(ks)):
                    if zz[j] > 0.1 and not hid[j]:
                        xs_.append(xx[j]); ys_.append(yy[j]); ws_.append((j + 1) / len(ks) * cap)
            if xs_:
                splat(img, np.array(xs_), np.array(ys_), np.array(ws_) * 3.0, (1.0, 0.9, 0.6), blur=1.4)

# ---------------------------------------------------------------- the CME bubble (artistic: a flux-rope shell)
def cme_points(n=42000, seed=21):
    if 'cme' not in _P:
        g = np.random.default_rng(seed)
        v = g.normal(size=(n, 3)); v /= np.linalg.norm(v, axis=1, keepdims=True)
        rough = g.random(n)
        _P['cme'] = (v, rough)
    return _P['cme']

def draw_cme(img, cam, p, center, radius, axis, intensity, t):
    """a glowing shell seen through: emission ~ path length inside it (bright rim, like a coronagraph CME), brightest
    at the nose, a twisted flux-rope core inside; ray-marched analytically at half resolution"""
    step = 2
    d = rays_grid(cam.f, cam.r, cam.u, cam.k, step); hh, ww = d.shape[:2]; d = d.reshape(-1, 3)
    oc = p - center
    def chord(Rr):
        b = d @ oc; c = oc @ oc - Rr * Rr; disc = b * b - c
        sq = np.sqrt(np.maximum(disc, 0))
        t0 = np.maximum(-b - sq, 0); t1 = np.maximum(-b + sq, 0)
        return t1 - t0, -b - sq
    th = radius * 0.16
    Lo, tin = chord(radius); Li, _ = chord(radius - th)
    shell = np.maximum(Lo - Li, 0)
    # where the ray meets the shell: the direction from the centre (nose / flanks / back)
    P = p + np.maximum(tin, 0)[:, None] * d - center
    Pn = P / np.maximum(np.linalg.norm(P, axis=1, keepdims=True), 1e-9)
    c = Pn @ axis
    e1, e2 = basis(axis)
    a_ = np.arctan2(Pn @ e2, Pn @ e1); pol = np.arccos(np.clip(c, -1, 1))
    fil = (0.35 + 0.65 * (0.5 + 0.5 * np.sin(a_ * 7 + pol * 11 + t * 0.3)) * (0.5 + 0.5 * np.sin(a_ * 17 - pol * 5 + 1.3)) ** 2)
    nose = np.clip((c + 0.25) / 1.25, 0, 1) ** 1.6
    em = (shell / th) ** 2.5 * 0.22 * nose * fil
    # the flux-rope core: a dimmer, twisted blob behind the front
    cc = center - axis * radius * 0.15
    oc2 = p - cc; b2 = d @ oc2; c2 = oc2 @ oc2 - (radius * 0.45) ** 2; core = 2 * np.sqrt(np.maximum(b2 * b2 - c2, 0)) / (radius * 0.9)
    em2 = core ** 2 * 0.06
    out = (em[:, None] * np.array([1.0, 0.38, 0.12]) + em2[:, None] * np.array([1.0, 0.30, 0.10])) * intensity
    img += up2(out.reshape(hh, ww, 3).astype(np.float32), step)

def sun_glow(img, cam, p, Ps, Rs, k=1.0, t=0.0):
    x, y, z = cam.proj(Ps)
    if z[0] <= 0: return
    rpx = cam.k * Rs / z[0]
    if rpx < 0.6:
        R.glowdot(img, x[0], y[0], 3, (1.0, 0.85, 0.6), k * 3); return
    spr = R.sun_sprite(min(rpx, 700), glow=0.6, t=t) * k * 1.6
    R.add(img, spr, x[0], y[0])
    NW.glow(img, x[0], y[0], max(rpx, 4) * 1.1, (1.0, 0.8, 0.55), 0.25 * k)

# ---------------------------------------------------------------- camera keys
def keyed(t, keys):
    """keys: (t, pos, target, up, fov); positions slerped on the sphere + radius in log"""
    for (t0, p0, g0, u0, f0), (t1, p1, g1, u1, f1) in zip(keys, keys[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0))
            r0, r1 = np.linalg.norm(p0), np.linalg.norm(p1)
            p = NW.slerp(p0 / r0, p1 / r1, k) * math.exp(lerp(math.log(r0), math.log(r1), k))
            return p, lerp(np.asarray(g0, float), np.asarray(g1, float), k), nrm(lerp(np.asarray(u0, float), np.asarray(u1, float), k)), lerp(f0, f1, k)
    t0, p0, g0, u0, f0 = keys[-1]
    return np.asarray(p0, float), np.asarray(g0, float), nrm(np.asarray(u0, float)), f0

def linear_keys(t, keys):
    """like keyed but the position is interpolated linearly in space (for long straight flights)"""
    for (t0, p0, g0, u0, f0), (t1, p1, g1, u1, f1) in zip(keys, keys[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0))
            return (lerp(np.asarray(p0, float), np.asarray(p1, float), k), lerp(np.asarray(g0, float), np.asarray(g1, float), k),
                    nrm(lerp(np.asarray(u0, float), np.asarray(u1, float), k)), lerp(f0, f1, k))
    t0, p0, g0, u0, f0 = keys[-1]
    return np.asarray(p0, float), np.asarray(g0, float), nrm(np.asarray(u0, float)), f0

# ---------------------------------------------------------------- S1: night Earth, the oval, sunrise over the limb
def oval(th0=21.0, kg=1.0, kr=0.35, wg=0.8, wr=3.5, sun=SUN, mag=MAG, **kw):
    A = dict(th0=th0, wg=wg, wr=wr, kg=kg, kr=kr, sun=sun, mag=mag, ground=0.6)
    A.update(kw); return A

def shot_S1(t):
    # over the North Atlantic at night, looking north-east across Scandinavia to the limb; the camera slides east (towards dawn)
    keys = [
        (0.0, ll(50, -28) * 2.25, ll(72, 0) * 0.55, [0, 0, 1], 50),
        (5.4, ll(52, -8) * 2.15, ll(72, 20) * 0.55, [0, 0, 1], 50),
    ]
    p, g, up, fov = keyed(t, keys)
    A = oval(th0=20.0 + 1.5 * sm(t / 5), kg=3.0, kr=0.35, wg=0.55, wr=2.5, shift_r=0.6)
    img, cam, _ = earth_view(t, p, g, up, fov, SUN, A, star_pan=(t * 6, t * 2))
    # the Sun coming up behind the limb (far right) at the end: a growing glow
    k = sm((t - 3.4) / 1.8)
    if k > 0:
        Ps = p + SUN * 0 + nrm(ll(10, 80) - p * 0.0) * 50
        x, y, z = cam.proj(np.array([p + nrm(ll(30, 95)) * 40]))
        NW.glow(img, float(x[0]), float(y[0]), 30 + 60 * k, (1.0, 0.85, 0.65), 2.5 * k)
    return img

# ---------------------------------------------------------------- S2: SDO, real
SDO_DIR = os.path.join(WORK, 'sdo4k')
SDO_C = (2048.0, 2060.0); SDO_R = 1660.0; FLARE = (470.0, 2230.0)
_IMC = {}
def sdo_frame(fi):
    """frame index (float) 30..75 — cross-dissolve between the 1-min images"""
    i0 = int(math.floor(fi)); a = fi - i0
    def get(i):
        i = min(75, max(30, i))
        if i not in _IMC:
            if len(_IMC) > 4: _IMC.pop(next(iter(_IMC)))
            _IMC[i] = Image.open(os.path.join(SDO_DIR, f's_{i:03d}.jpg')).convert('RGB')
        return _IMC[i]
    if a < 0.02: return get(i0)
    return Image.blend(get(i0), get(i0 + 1), a)

def view_crop(img, cx, cy, scale, out=(W, H)):
    """the window centred at (cx, cy) in img px, scale = output px per img px; sub-pixel, bicubic"""
    w_in = out[0] / scale; h_in = out[1] / scale
    box = (cx - w_in / 2, cy - h_in / 2, cx + w_in / 2, cy + h_in / 2)
    return img.transform(out, Image.EXTENT, box, Image.BICUBIC)

def shot_S2(t):
    # the source frame: 30 at 4.6 s, the eruption (41→46) at ~6.2–6.9 s, 62 at 8.8 s
    fi = 30 + (t - 4.6) / 4.2 * 32 if t < 8.8 else 62
    fi = 30 + 32 * ((t - 4.6) / 4.2) ** 1.0
    fi = min(75, max(30, fi))
    im = sdo_frame(fi)
    k = sm((t - 4.6) / 4.6)
    # from the whole disc (a bit wider than the frame) into the flare on the east limb
    cx = lerp(SDO_C[0], FLARE[0] + 320, k); cy = lerp(SDO_C[1], FLARE[1], k)
    scale = math.exp(lerp(math.log(W * 1.25 / (2 * SDO_R)), math.log(W / 1300), k))
    v = np.asarray(view_crop(im, cx, cy, scale), np.float32) / 255
    v = v ** 1.15 * 1.05
    bg = stars_bg(dx=t * 3, dy=t * 2, k=0.6) ** 1.6 * 0.5
    return np.maximum(v * 1.25, bg)

# ---------------------------------------------------------------- S3: LASCO C2, real
C2_DIR = os.path.join(WORK, 'c2')
_FL = {}
def c2_img(i):
    if i not in _FL:
        if len(_FL) > 6: _FL.pop(next(iter(_FL)))
        a = np.asarray(Image.open(os.path.join(C2_DIR, f'c2_{i:03d}.jpg')).convert('RGB'), np.float32) / 255
        _FL[i] = a
    return _FL[i]

C2_FRAMES = list(range(112, 146, 2))          # the unique 12-min images (each movie frame is doubled)
def c2_interp(x):
    """x: position in C2_FRAMES (float); optical-flow in-between of two images"""
    import cv2
    i = int(math.floor(x)); a = x - i
    i = min(len(C2_FRAMES) - 2, max(0, i))
    A_ = c2_img(C2_FRAMES[i]); B_ = c2_img(C2_FRAMES[i + 1])
    if a < 0.01: return A_
    key = ('flow', i)
    if key not in _FL:
        g0 = cv2.cvtColor((A_ * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY); g1 = cv2.cvtColor((B_ * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        f01 = dis.calc(g0, g1, None); f10 = dis.calc(g1, g0, None)
        _FL[key] = (f01, f10)
    f01, f10 = _FL[key]
    h, w = A_.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    wa = cv2.remap(A_, gx - f10[..., 0] * a * -1 * -1 + 0, gy, cv2.INTER_LINEAR) if False else \
        cv2.remap(A_, gx + f10[..., 0] * a, gy + f10[..., 1] * a, cv2.INTER_LINEAR)
    wb = cv2.remap(B_, gx + f01[..., 0] * (1 - a), gy + f01[..., 1] * (1 - a), cv2.INTER_LINEAR)
    return wa * (1 - a) + wb * a

def shot_S3(t):
    # 8.2–12.8: 02:00 → 04:30 UT (images 116..138), slowly pushing in towards the CME (lower right)
    k = (t - 8.2) / 4.6
    x = lerp(1.0, 11.5, sm(min(1, max(0, k))) * 0.3 + min(1, max(0, k)) * 0.7)
    a = c2_interp(x)
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    kk = min(1, max(0, k)) * 0.7 + sm(min(1, max(0, k))) * 0.3
    # the end: a dive into the occulter's white circle (the Sun's disc) — it becomes the Sun of the next shot
    dive = sm((t - 11.9) / 0.9)
    # where (and how big) the Sun of the next shot is right now: the occulter's white circle (r = 80 px) lands on it
    pf, gf, uf, ff = flight_cam(max(t, 12.2)); camf = R.Cam(pf, gf, fov=ff, up=uf)
    xs_, ys_, zs_ = camf.proj(SUN * D_SUN); rs_ = camf.k * R_SUN_S / zs_[0]
    scale = math.exp(lerp(math.log(lerp(1.18, 1.42, kk)), math.log(rs_ / 80.0), dive))
    sx = lerp(540 + lerp(0, -40, kk) * 0, float(xs_[0]), dive); sy = lerp(lerp(960, 930, kk), float(ys_[0]), dive)
    ccx, ccy = lerp(512, 512.5, dive), lerp(512, 518.9, dive)
    cx = ccx + (W / 2 - sx) / scale + lerp(lerp(0, 40, kk), 0, dive) / scale; cy = ccy + (H / 2 - sy) / scale
    v = np.asarray(view_crop(im, cx, cy, scale), np.float32) / 255
    # the timestamp strip and the square's corners: under a soft round vignette
    yy, xx = np.mgrid[0:H, 0:W]
    ix = (xx - W / 2) / scale + cx; iy = (yy - H / 2) / scale + cy
    rr = np.sqrt((ix - 512) ** 2 + (iy - 512) ** 2)
    mask = np.clip((480 - rr) / 40, 0, 1)
    bg = stars_bg(dx=t * 3, dy=t * 2, k=0.6) ** 1.6 * 0.5
    return v * mask[..., None] * 1.05 + bg * (1 - mask[..., None])

# ---------------------------------------------------------------- S4: the flight Sun → Earth → magnetosphere
D_SUN = 420.0; R_SUN_S = 34.0            # compressed: the Sun 420 Earth radii away, 34 across (labelled)
def _flight_a(t):
    """following the CME front down the Sun–Earth line (the Sun up in the frame)"""
    s = SUN; side = nrm(np.cross(s, MAG))
    front, k = cme_state(t)
    xf = D_SUN - front
    X = lerp(xf + 26, xf * 0.45 + 4, sm((t - 14.3) / 1.3))
    dist = math.exp(lerp(math.log(300), math.log(64), sm((t - 12.2) / 3.4)))
    rad = front * 0.28
    dist = max(dist, lerp(rad * 1.9, 0, sm((t - 14.6) / 1.0)))
    return s * X + side * dist, s * X, s, 50.0

def flight_cam(t):
    s = SUN; side = nrm(np.cross(s, MAG))
    if t <= 15.6: return _flight_a(t)
    p0, g0, u0, f0 = _flight_a(15.6)
    keys = [(15.6, p0, g0, u0, f0), (18.6, s * 2.0 + side * 48, s * 0.5, s, 47),
            (20.8, s * 1.0 + side * 30, s * 0.0, s, 46), (22.6, s * 0.6 + side * 10.5 + MAG * 1.5, s * 0.1, s, 46)]
    return linear_keys(t, keys)

def cme_state(t):
    """front distance from the Sun's centre (Earth radii), arrival at the magnetopause ~15.4 s"""
    k = sm((t - 11.6) / 4.1) if t < 15.7 else 1.0
    front = R_SUN_S + (D_SUN - 10 - R_SUN_S) * k
    return front, k

def shot_S4(t):
    p, g, up, fov = flight_cam(t)
    # the storm: the magnetopause squeezed from ~10 to ~6.6, the ovals growing
    hit = sm((t - 15.0) / 2.0)
    capture = sm((t - 19.6) / 2.2)
    A = oval(th0=20.0 + 5.0 * hit, kg=0.5 + 1.6 * capture, kr=0.15 + 0.5 * capture)
    img, cam, _ = earth_view(t, p, g, up, fov, SUN, A, star_pan=(t * 2, -t * 4), step=2)
    sun_glow(img, cam, p, SUN * D_SUN, R_SUN_S, k=1.0, t=t)
    front, k = cme_state(t)
    if t < 17.5:
        rad = front * 0.28; center = SUN * (D_SUN - (front - rad))
        inten = (1 - sm((t - 15.6) / 1.6)) * sm((t - 11.8) / 0.8)
        draw_cme(img, cam, p, center, rad, -SUN, inten * 0.5, t)
    M = dict(sun=SUN, mag=MAG, comp=0.15 + 0.22 * hit, tail=0.6 + 0.4 * hit, r0=10 - 3.4 * hit, rbs=13 - 3.6 * hit,
             lines_a=sm((t - 14.8) / 1.6), bow_a=sm((t - 15.2) / 1.2) * 0.8, wind_a=sm((t - 15.4) / 1.4),
             wind_speed=9 + 5 * hit, capture=capture)
    magnetosphere(img, cam, p, t, M)
    return img

# ---------------------------------------------------------------- S5: ISS photo (real)
def photo(name, t, t0, t1, z0, z1, c0, c1, bgk=0.0):
    key = 'ph:' + name
    if key not in _IMC: _IMC[key] = Image.open(os.path.join(ASSETS, name)).convert('RGB')
    im = _IMC[key]
    k = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    kk = k * 0.75 + sm(k) * 0.25                         # nearly linear: the push never stops
    w, h = im.size
    cover = max(W / w, H / h)
    scale = cover * math.exp(lerp(math.log(z0), math.log(z1), kk))
    cx = lerp(c0[0], c1[0], kk) * w; cy = lerp(c0[1], c1[1], kk) * h
    # keep the window inside the photo
    hw = W / scale / 2; hh = H / scale / 2
    cx = min(max(cx, hw), w - hw); cy = min(max(cy, hh), h - hh)
    return np.asarray(view_crop(im, cx, cy, scale), np.float32) / 255

def shot_S5(t):
    v = photo('aurora_iss072e159172.jpg', t, 22.0, 25.8, 1.00, 1.12, (0.47, 0.55), (0.47, 0.52))
    return np.clip(v * 1.15, 0, 1) ** 1.05

# ---------------------------------------------------------------- S6: storm effects — the satellites
def orbit_pts(rad, inc, raan, n=240):
    a = np.linspace(0, 2 * np.pi, n)
    i = math.radians(inc); O = math.radians(raan)
    x = np.cos(a); y = np.sin(a) * math.cos(i); z = np.sin(a) * math.sin(i)
    X = x * math.cos(O) - y * math.sin(O); Y = x * math.sin(O) + y * math.cos(O)
    return np.stack([X, Y, z], 1) * rad

def shot_S6(t):
    keys = [
        (25.2, ll(42, -10) * 9.5, ll(48, 10) * 0.2, [0, 0, 1], 44),
        (30.9, ll(40, 15) * 8.6, ll(48, 25) * 0.2, [0, 0, 1], 44),
    ]
    p, g, up, fov = keyed(t, keys)
    A = oval(th0=27.0, kg=2.2, kr=0.9, wg=2.0, wr=5.5, steps=18)
    img, cam, _ = earth_view(t, p, g, up, fov, SUN, A, star_pan=(t * 3, 0), step=2)
    segs = []; dots = []
    gps_r = (20200 + 6371) / 6371.0
    for j in range(6):
        O = j * 60 + 10
        pts = orbit_pts(gps_r, 55, O)
        polyline(img, cam, p, pts, None, a=0.32, layer=segs)
        for q in range(5):
            ang = (q / 5 + j * 0.07) * 2 * np.pi + t * 0.06
            X = orbit_pts(gps_r, 55, O, n=1)[0] * 0
            i = math.radians(55); Oo = math.radians(O)
            x, y, z = math.cos(ang), math.sin(ang) * math.cos(i), math.sin(ang) * math.sin(i)
            dots.append(np.array([x * math.cos(Oo) - y * math.sin(Oo), x * math.sin(Oo) + y * math.cos(Oo), z]) * gps_r)
    geo = orbit_pts(42164 / 6371.0, 0, 0, n=400)
    polyline(img, cam, p, geo, None, a=0.22, layer=segs)
    for q in range(26):
        ang = q / 26 * 2 * np.pi + 0.3
        dots.append(np.array([math.cos(ang), math.sin(ang), 0]) * 42164 / 6371.0)
    draw_lines(img, segs, (0.55, 0.75, 1.0), width=1, k=0.45, blur=1.5)
    D = np.array(dots); x, y, z = cam.proj(D); hid = occluded(p, D)
    for i in range(len(D)):
        if z[i] > 0 and not hid[i]:
            fl = 0.6 + 0.4 * math.sin(t * 7 + i * 1.7) * (t > 27.3)       # a storm: some flicker (charging, drag)
            R.glowdot(img, x[i], y[i], 2.2, (0.9, 0.95, 1.0), 0.9 * fl)
    return img

# ---------------------------------------------------------------- S7: 1859
HAVANA = ll(23.1, -82.4); HONOLULU = ll(21.3, -157.9)
def shot_S7(t):
    keys = [
        (30.3, ll(34, -108) * 5.6, ll(36, -112) * 0.0, [0, 0, 1], 44),
        (38.9, ll(30, -124) * 5.2, ll(32, -122) * 0.0, [0, 0, 1], 44),
    ]
    p, g, up, fov = keyed(t, keys)
    k = sm((t - 30.6) / 3.0)
    A = oval(th0=22 + 22 * k, kg=1.0 + 1.4 * k, kr=0.3 + 1.1 * k, wg=0.8 + 1.4 * k, wr=3 + 4 * k, sun=SUN1859, mag=MAG1859, steps=20, shift_r=1 + 2 * k, north_only=True, ground=0.0)
    img, cam, _ = earth_view(t, p, g, up, fov, SUN1859, A, star_pan=(-t * 3, 0), lights_k=0.0, step=2)
    # no city lights in 1859 (lights_k=0) — the ground lit only by the aurora
    return img

def markers_S7(t, img_pil):
    p, g, up, fov = keyed(t, [(30.3, ll(34, -108) * 5.6, ll(36, -112) * 0.0, [0, 0, 1], 44), (38.9, ll(30, -124) * 5.2, ll(32, -122) * 0.0, [0, 0, 1], 44)])
    cam = R.Cam(p, g, fov=fov, up=up)
    a = sm((t - 35.9) / 0.6) * (1 - sm((t - 38.5) / 0.4))
    if a <= 0: return
    d = ImageDraw.Draw(img_pil, 'RGBA')
    for v, name in ((HAVANA, 'Куба'), (HONOLULU, 'Гаваї')):
        x, y, z = cam.proj(v * 1.0)
        if z[0] <= 0 or occluded(p, v[None] * 1.001)[0]: continue
        x, y = float(x[0]), float(y[0])
        d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=(255, 235, 200, int(230 * a)), width=3)
        R.label(img_pil, x, y - 34, name, size=34, a=a)

# ---------------------------------------------------------------- S8: health — the dipole round a day-lit Earth
def shot_S8(t):
    s = SUN; m = MAG
    side = nrm(np.cross(s, m))
    keys = [
        (38.3, (s * 0.55 + side * 0.85) * 13 + m * 2.5, m * 0.6, m, 42),
        (47.0, (s * 0.85 + side * 0.5) * 12 + m * 3.0, m * 0.6, m, 40),
        (55.0, (s * 0.95 - side * 0.25) * 11 + m * 3.5, m * 0.6, m, 40),
    ]
    p, g, up, fov = keyed(t, keys)
    A = oval(th0=21, kg=0.5, kr=0.15)
    img, cam, _ = earth_view(t, p, g, up, fov, SUN, A, star_pan=(t * 2, t), step=2)
    # the field trembles: up to 2 % (shown to scale)
    jig = 0.02 * sm((t - 45.4) / 1.5) * (1 - 0.6 * sm((t - 51.0) / 2))
    M = dict(sun=SUN, mag=MAG, comp=0.25, tail=0.9, r0=8, rbs=11, lines_a=0.85, bow_a=0.0, wind_a=0.0, jiggle=jig)
    magnetosphere(img, cam, p, t, M)
    return img

# ---------------------------------------------------------------- S9: down over Ukraine
CHERNIVTSI = ll(48.3, 25.9)
def shot_S9(t):
    north = nrm(np.array([0, 0, 1.0]) - CHERNIVTSI * CHERNIVTSI[2])
    keys = [
        (54.4, CHERNIVTSI * (1 + 1400 * KM) - north * 1300 * KM, CHERNIVTSI * (1 + 200 * KM) + north * 2600 * KM, CHERNIVTSI, 60),
        (57.4, CHERNIVTSI * (1 + 420 * KM) - north * 700 * KM, CHERNIVTSI * (1 + 220 * KM) + north * 2400 * KM, CHERNIVTSI, 64),
    ]
    p, g, up, fov = linear_keys(t, keys)
    # the storm of 19–20.01.2026: the red oval down to ~50° magnetic latitude, seen low in the north from Ukraine
    A = oval(th0=33.0, kg=0.45, kr=0.55, wg=1.2, wr=11.0, shift_r=4.5, steps=26, ground=0.0)
    img, cam, _ = earth_view(t, p, g, up, fov, SUN, A, star_pan=(t * 3, 0), step=2)
    return img

# ---------------------------------------------------------------- S10–S11: the author's photos
def shot_S10(t):
    v = photo('aurora_cv_IMG_3810.jpg', t, 56.8, 62.4, 1.0, 1.16, (0.5, 0.52), (0.47, 0.50))
    return v

def shot_S11(t):
    v = photo('aurora_cv_IMG_3842.jpg', t, 61.8, 72.0, 1.0, 1.14, (0.5, 0.55), (0.56, 0.58))
    return v

SHOTS = [(0.0, 5.2, shot_S1), (4.6, 8.8, shot_S2), (8.2, 12.8, shot_S3), (12.2, 22.6, shot_S4), (22.0, 25.8, shot_S5),
         (25.2, 30.9, shot_S6), (30.3, 38.9, shot_S7), (38.3, 55.0, shot_S8), (54.4, 57.4, shot_S9), (56.8, 62.4, shot_S10),
         (61.8, 72.5, shot_S11)]
LINEAR = {'shot_S2', 'shot_S3', 'shot_S5', 'shot_S10', 'shot_S11'}      # already display-referred (photos, real data)

def post(img):
    img = NW.bloom(np.nan_to_num(img, nan=0.0, posinf=12.0, neginf=0.0))
    yy, xx = np.mgrid[0:H, 0:W]; vig = 1 - 0.35 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2
    return NW.tonemap(img * vig[..., None])

def render_shot(fn, t):
    a = fn(t)
    return a if fn.__name__ in LINEAR else post(a)

def frame(t):
    act = [(a, b, f) for a, b, f in SHOTS if a <= t <= b]
    out = None
    for a, b, f in act:
        img = render_shot(f, t)
        # dissolve: the later shot fades in over the overlap
        if out is None: out = img
        else:
            prev_end = max(bb for aa, bb, ff in act if ff is not f and aa < a) if len(act) > 1 else b
            k = sm((t - a) / max(1e-3, (prev_end - a)))
            out = out * (1 - k) + img * k
    if out is None: out = np.zeros((H, W, 3), np.float32)
    im = R.to_img(out)
    if 35.4 < t < 39.0: markers_S7(t, im)
    return im

def job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return
    frame(i / FPS).save(p + '.tmp.jpg', quality=93); os.replace(p + '.tmp.jpg', p)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * FPS)
    todo = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()) as pool:
        for c, _ in enumerate(pool.imap_unordered(job, todo, chunksize=2)):
            if c % 60 == 0: print('frame', c, '/', len(todo), flush=True)
    print('frames done', n)
