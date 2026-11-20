# The acts of «Історія Землі»: each is frame(t) -> uint8 (H, W, 3) picture (no captions/clock: those go on in cut.py),
# t = seconds from the act's start on the cut (timeline.json; t runs a little below 0 and past the end for the dissolves).
#   python3 acts.py <act> stills 0,5,10        -> work/earth_history/stills/<act>_<t>.jpg
#   python3 acts.py <act> render [i0 i1]       -> work/earth_history/acts/<act>/f_<global frame>.jpg (resumable)
import math, os, sys, json
import numpy as np
from PIL import Image
from eh import *

TL = {a['id']: a for a in json.load(open(os.path.join(HERE, 'timeline.json')))['acts']}
XF = 1.0                                          # dissolve between acts (each act renders XF/2 beyond its ends)
ACTS = {}
def act(fn): ACTS[fn.__name__] = fn; return fn

# ================================================================ HOOK (0–28): the night Earth -> the rewind -> magma
def night_cam(t):
    lat, lon = 48.5, 31.0
    up = ll(lat, lon); east = np.array([-math.sin(math.radians(lon)), math.cos(math.radians(lon)), 0.0]); north = np.cross(up, east)
    k = sm(t / 15.0)
    alt = lerp(1700.0, 2300.0, k)
    o = up * (RE + alt) - north * lerp(2500.0, 2900.0, k) + east * lerp(-500.0, 600.0, k)
    tgt = up * RE + north * lerp(900.0, 1000.0, k) + east * lerp(-150.0, 250.0, k)
    return cm.cam(o, tgt, up, 52.0), (lat, lon)

@act
def hook(t):
    # 0–15 the night side over Ukraine (lights; dawn over the Caspian); 13–19 pull back to the whole globe, the Sun
    # comes round; 18.5–26 the rewind: the continents slide back through 540 million years, the globe spins backwards;
    # 24.5–28.5 the globe glows red and becomes the magma ocean
    if t < 19.0:
        c1, home = night_cam(min(t, 15.0))
        img = space(c1, 0.6, 0.25)
        sun = ll(12.0, home[1] + 108.0)
        k = sm((t - 13.0) / 6.0)
        if k > 0:          # pull back: blend the close camera into the far one
            far = orbit_cam(30.0, 40.0 - 25 * k, RE * lerp(1.9, 3.6, k), 36.0)
            c = tuple(lerpv(a, b, k) if i < 4 else lerp(a, b, k) for i, (a, b) in enumerate(zip(c1, far)))
            c = cm.cam_dir(c[0], c[1], np.array([0, 0, 1.0]) * k + ll(48.5, 31.0) * (1 - k), lerp(52.0, 36.0, k))
            img = space(c, 0.6, 0.25)
            sun = nrm(ll(12.0, home[1] + 108.0) * (1 - k) + side_sun(c) * k)
        else:
            c = c1
        globe(img, c, today(), sun, expo=lerp(0.9, 0.8, k), cloud_k=0.7, night_k=1.8 * (1 - k), home=home)
        return finish(img)
    # the rewind
    u = (t - 19.0) / 6.5
    ma = 540.0 * (sm(u) * 0.35 + max(0.0, u) ** 2 * 0.65) if u > 0 else 0.0
    ma = min(ma, 540.0)
    lon = 15.0 - 140.0 * (max(0.0, min(u, 1.0)) ** 1.6 * 0.75 + 0.25 * sm(u)) - 25.0 * sm((t - 25.5) / 3.5)
    dist = RE * lerp(3.6, 3.2, sm((t - 19.0) / 9.0))
    c = orbit_cam(30.0 - 22 * sm((t - 19) / 8), lon, dist, 36.0)
    img = space(c, 0.6, 0.25)
    tex = today() if ma <= 0 else paleo_at(ma)
    if ma < 4: tex = np.ascontiguousarray((today() * (1 - ma / 4) + paleo(0) * (ma / 4)).astype(np.uint8))
    globe(img, c, tex, side_sun(c), expo=0.8, cloud_k=0.7 * (1 - sm((t - 19) / 4)), cloud_shift=0)
    km = sm((t - 24.5) / 3.5)
    if km > 0:            # the glow takes over: the magma world, same size, same camera
        mag = space(c, 0.6, 0.25)
        alb, emi = magma_maps(0.0)
        D = rays(c)
        body(mag, c, D, (0, 0, 0), RE, alb, emi, L=side_sun(c), spin=math.radians(lon * 0.0 + t * 6.0), ambient=0.004,
             atm=(1.4, 0.45, 0.12))
        img = img * (1 - km) + mag * km
    return finish(img)


ANCH = {}            # act -> fn(t) -> {key: (x, y)} screen points the captions point at (moving objects)

# ================================================================ BIRTH (≈26 s): the dust disk -> the molten Earth
_DISK = {}
def disk_parts():
    if not _DISK:
        rng = np.random.default_rng(3)
        n = 340000
        r = 0.35 + 6.4 * rng.uniform(0, 1, n) ** 1.35                          # surface density falling outward
        th = rng.uniform(0, 2 * math.pi, n)
        # spiral density waves and clumps
        clump = (1 + 1.0 * np.sin(3 * th - 4.0 * np.log(r)) ** 2 * (0.6 + 0.4 * np.sin(11 * th + 7 * r) ** 2))
        for rg, wg in ((1.45, 0.10), (2.35, 0.13), (3.4, 0.16), (4.7, 0.2)):     # gaps cleared by young planets (as ALMA saw in HL Tau)
            clump = clump * (1 - 0.9 * np.exp(-((r - rg) / wg) ** 2))
        keep = rng.uniform(0, 2.3, n) < clump; r, th = r[keep], th[keep]
        z = rng.normal(0, 1, len(r)) * 0.035 * r ** 1.2
        lum = (0.30 + 0.7 * rng.uniform(0, 1, len(r)) ** 3) / r ** 0.45
        warm = np.clip(1.4 / r, 0, 1)[:, None]
        col = (np.array([1.0, 0.70, 0.46]) * warm + np.array([0.75, 0.66, 0.60]) * (1 - warm)) * lum[:, None] * 0.03
        rocks = rng.uniform(0, 1, len(r)) < 0.012
        _DISK.update(r=r, th=th, z=z, col=col.astype(np.float32), rocks=rocks)
    return _DISK

_DN = {}
def disk_noise():
    if 'n' not in _DN:
        P = np.zeros((1024, 1024, 3), np.float32)
        yy, xx = np.mgrid[0:1024, 0:1024].astype(np.float32) / 1024 * 16
        P[..., 0] = xx; P[..., 1] = yy
        _DN['n'] = fbm3(P, 5).astype(np.float32)
    return _DN['n']

def disk_density(x, y, t):
    """the dust disk seen face-on: rings and gaps (HL Tau-like), spiral waves, sheared clumps; x, y in disk units"""
    r = np.sqrt(x * x + y * y) + 1e-6; th = np.arctan2(y, x)
    om = 0.32 / r ** 1.5
    a = th - om * (t + 20)                                     # back to the rotating frame
    xr, yr = r * np.cos(a), r * np.sin(a)
    n = sample(disk_noise()[..., None], np.clip(yr / 16.0, -0.49, 0.49) * math.pi, xr / 8.0 * math.pi)[..., 0]
    d = np.exp(-r / 3.2) * (r > 0.32) * np.clip((r - 0.32) / 0.15, 0, 1) * np.clip((7.2 - r) / 1.5, 0, 1)
    d = d * (1 + 0.8 * np.sin(2 * a - 3.0 * np.log(r)) ** 2) * (0.15 + 1.9 * n ** 2.2)
    for rg, wg in ((1.45, 0.08), (2.35, 0.11), (3.4, 0.14), (4.7, 0.18)):
        d = d * (1 - 0.88 * np.exp(-((r - rg) / wg) ** 2))
    for rb, wb in ((1.9, 0.18), (2.9, 0.2), (4.05, 0.25)):     # bright rings between the gaps
        d = d * (1 + 0.6 * np.exp(-((r - rb) / wb) ** 2))
    return d, r

def disk_frame(t):
    d = disk_parts()
    k = sm((t + 0.5) / 16.0)
    ang = 0.32 * (t + 20) + 0.6
    E = np.array([math.cos(ang), math.sin(ang), 0.0])                     # where the Earth is forming
    back = nrm(np.array([math.cos(ang - 0.9), math.sin(ang - 0.9), 0.0]))
    o = E * lerp(0.4, 0.75, k) + back * lerp(3.4, 0.55, k ** 1.3) + np.array([0, 0, lerp(2.5, 0.12, k ** 1.1)])
    tgt = E * lerp(0.35, 1.0, k)
    c = cm.cam(o, tgt, [0, 0, 1], lerp(70.0, 40.0, k))
    img = space(c, 0.45, 0.2)
    D = rays(c); oz = c[0][2]
    tt = -oz / np.where(np.abs(D[..., 2]) > 1e-6, D[..., 2], 1e-6)
    m = tt > 0
    X = c[0][0] + D[..., 0] * tt; Y = c[0][1] + D[..., 1] * tt
    den, r = disk_density(np.where(m, X, 99.0), np.where(m, Y, 99.0), t)
    # seen nearly edge-on a thin sheet looks denser: 1/|cos|, capped
    slant = np.clip(1.0 / np.maximum(np.abs(D[..., 2]), 0.08), 1, 8)
    tau = den * slant * 0.32 * m
    light = 1.0 / np.maximum(r, 0.35) ** 1.15
    col = (1 - np.exp(-tau))[..., None] * light[..., None] * 1.05
    warmth = np.clip(1.6 / r, 0, 1)[..., None]
    col = col * (warmth * np.array([1.0, 0.60, 0.30], np.float32) + (1 - warmth) * np.array([0.72, 0.42, 0.27], np.float32))
    img = img * np.exp(-tau)[..., None] + col
    # rocks: sparkling points in the disk
    th = d['th'] + 0.32 * (t + 20) / d['r'] ** 1.5
    Xp = np.stack([d['r'] * np.cos(th), d['r'] * np.sin(th), d['z']], -1)
    splat(img, c, Xp[d['rocks']], d['col'][d['rocks']] * 14.0, size=2)
    sx, sy, sz = cm.project(c, np.zeros(3))
    if sz[0] > 0: glow(img, sx[0], sy[0], [(5, 40.0), (24, 4.0), (120, 0.35), (420, 0.04)], (1.0, 0.86, 0.66))
    ex, ey, ez = cm.project(c, E)
    if ez[0] > 0:
        g = lerp(0.8, 6.0, sm((t - 6) / 9))
        glow(img, ex[0], ey[0], [(3 + 10 * sm((t - 9) / 6), g), (26, g * 0.18)], (1.0, 0.55, 0.25))
        rng = np.random.default_rng(abs(int(t * 7)) + 1)
        if 8.0 < t < 15.5 and rng.uniform() < 0.35:
            glow(img, ex[0] + rng.normal(0, 30), ey[0] + rng.normal(0, 22), [(4, 8.0), (16, 0.8)], (1.0, 0.8, 0.5))
    return img, (ex[0], ey[0])

def magma_cam(t):
    k = sm((t - 13.5) / 12.5)
    return cm.cam([0, -RE * lerp(4.3, 3.3, k), RE * lerp(0.6, 0.35, k)], [RE * lerp(0.15, 0.0, k), 0, 0], [0, 0, 1], 38.0)

def meteors(img, c, t, rate=1.0, seed=5, R=RE, life=1.4):
    """small impactors: a bright streak falling in, a flash where it hits the visible face"""
    rng = np.random.default_rng(seed)
    n = int(60 * rate)
    t0s = rng.uniform(-2, 30, n); lat = rng.uniform(-60, 60, n); lon = rng.uniform(-180, 180, n)
    o = c[0]
    for i in range(n):
        u = (t - t0s[i]) / life
        if not (0 <= u <= 1.6): continue
        Pn = ll(lat[i], lon[i])
        if Pn @ nrm(o) < 0.15: continue                     # only on the face toward us
        S = Pn * R
        if u < 1.0:
            A = S + (Pn * 0.25 + nrm(np.cross(Pn, [0, 0, 1]) + 1e-6) * 0.25) * R * (1 - u) * 1.2
            pts = np.linspace(A, A + (S - A) * 0.12, 18)
            splat(img, c, pts, np.array([1.0, 0.75, 0.45]) * 1.4 * u)
        else:
            x, y, z = cm.project(c, S)
            f = math.exp(-(u - 1) * 5)
            glow(img, x[0], y[0], [(3, 12 * f), (14, 2.0 * f), (45, 0.25 * f)], (1.0, 0.6, 0.3))

def magma_frame(t, spin_rate=0.05):
    c = magma_cam(t)
    img = space(c, 0.5, 0.25)
    alb, emi = magma_maps(0.0)
    D = rays(c)
    L = nrm([-0.9, -0.35, 0.25])
    body(img, c, D, (0, 0, 0), RE, alb, emi, L=L, spin=t * spin_rate, ambient=0.004, atm=(1.4, 0.45, 0.12))
    meteors(img, c, t, 1.0)
    x, y, z = cm.project(c, np.zeros(3))
    return img, (x[0], y[0])

@act
def birth(t):
    if t < 13.5:
        img, _ = disk_frame(t); return finish(img, bloom=0.6)
    if t > 16.0:
        img, _ = magma_frame(t); return finish(img)
    k = sm((t - 13.5) / 2.5)
    a, _ = disk_frame(t); b, _ = magma_frame(t)
    return finish(a * (1 - k) + b * k, bloom=lerp(0.6, 0.45, k))
ANCH['birth'] = lambda t: {'earth': magma_frame.__defaults__ and tuple(cm.project(magma_cam(t), np.zeros(3))[i][0] for i in (0, 1))}

# ================================================================ THEIA (≈49 s)
TU = RE / 1.35                                  # the test frame's units -> km
E_R = 1.35 * TU; T_R = 0.72 * TU; M_R = 0.37 * TU
IMPACT = 4.1                                    # «…врізається…» (local seconds)
CONTACT_DIR = nrm([0.78, 0.36, -0.52])          # where Theia strikes, from the Earth's centre

def theia_pos(t):
    u = max(0.0, IMPACT - t)
    side = nrm(np.cross(CONTACT_DIR, [0, 0, 1]))
    return CONTACT_DIR * (E_R + T_R * 0.85) + (CONTACT_DIR * 0.55 + side * 0.85) * u * 0.9 * TU * 1.0

_PL = {}
def plume():
    if not _PL:
        rng = np.random.default_rng(9); n = 60000
        side = nrm(np.cross(CONTACT_DIR, [0, 0, 1])); up = nrm(np.cross(side, CONTACT_DIR))
        a0 = rng.normal(0, 0.35, n); spread = rng.normal(0, 1, n)
        rr = rng.uniform(1.25, 3.4, n) ** 1.3
        _PL.update(a0=a0, spread=spread, rr=rr, side=side, up=up, w=rng.uniform(0.6, 1.4, n),
                   hot=rng.uniform(0, 1, n), ph=rng.uniform(0, 2 * math.pi, n))
    return _PL

def plume_pts(tau, gather=0.0):
    p = plume()
    grow = 1 - math.exp(-tau / 1.6)
    r = E_R + (p['rr'] * E_R - E_R) * grow
    ang = p['a0'] + p['w'] * 0.22 * tau / (p['rr'] ** 1.5)
    # thickness collapses into the orbital plane, the ring forms
    th = p['spread'] * 0.35 * math.exp(-tau / 4.0)
    ax, ay = CONTACT_DIR, p['side']
    X = (np.cos(ang)[:, None] * ax + np.sin(ang)[:, None] * ay) * r[:, None] + p['up'] * (th * E_R)[:, None]
    if gather > 0:      # the Moon gathers out of the ring
        M = moon_pos(0.0)
        X = X * (1 - gather) + M * gather + (X - M) * 0.0
    return X

def moon_pos(recede):
    side = plume()['side']
    ang = 2.2
    d = lerp(3.8, 9.0, recede) * E_R
    return (math.cos(ang) * CONTACT_DIR + math.sin(ang) * side) * d

def theia_cam(t):
    base_o = np.array([0.95, 0.15, -7.0]) * TU; base_t = np.array([0.95, 0.15, 0.0]) * TU
    M = moon_pos(0.0); mn = nrm(M)
    perp = nrm(np.cross(mn, [0, 0, 1.0])); upv = nrm(np.cross(perp, mn))
    # 18–30: high over the glowing surface, the young Moon huge above the horizon
    hi_o = (perp * 1.75 - mn * 0.55 + upv * 0.35) * E_R
    hi_t = M * 0.9 + perp * 0.0
    # 31–37: wide: the Earth on one side, the Moon drifting away on the other
    mid = M * 0.5
    wide_o = mid + nrm(np.cross(mn, upv)) * 15.0 * E_R + upv * 2.0 * E_R
    o = keys(t, [(17.0, base_o), (22.5, hi_o), (29.5, hi_o + perp * 0.12 * E_R), (35.5, wide_o)])
    tg = keys(t, [(17.0, base_t), (22.5, hi_t), (29.5, hi_t), (35.5, mid + M * 0.25)])
    fov = keys(t, [(17.0, 33.0), (22.5, 27.0), (29.5, 25.0), (35.5, 34.0)])
    upd = keys(t, [(17.0, np.array([0, 1.0, 0])), (22.5, upv), (29.5, upv), (35.5, upv)])
    return cm.cam(o, tg, nrm(upd), fov)

def theia_world(t):
    c = theia_cam(t)
    img = space(c, 0.55, 0.3)
    D = rays(c)
    L = nrm([-0.85, 0.35, 0.25])
    alb, emi = magma_maps(0.0)
    tau = t - IMPACT
    heat = (math.exp(-max(tau, 0) / 6.0) * 1.6 + 1.0) if tau > 0 else 1.0
    spin = t * (0.05 if t < 24 else 0.05 + 0.5 * sm((t - 24) / 3) - 0.45 * sm((t - 30) / 4))   # «доба — 6 годин»
    mE, tE = body(img, c, D, (0, 0, 0), E_R, alb, emi, L=L, spin=spin, ambient=0.004, atm=(1.4, 0.45, 0.12), emi_k=heat)
    if tau < 2.2:                                    # Theia (it sinks into the Earth and is gone)
        rk = rock_maps(11.0)
        TP = theia_pos(t) - (CONTACT_DIR * T_R * 1.6 * sm(tau / 2.2) if tau > 0 else 0)
        body(img, c, D, TP, T_R * (1 - 0.35 * sm(tau / 2.2)), rk, None, L=L, spin=0.3 + t * 0.02, ambient=0.006, depth=tE)
    if tau > -0.3:
        x, y, z = cm.project(c, CONTACT_DIR * E_R)
        f = math.exp(-max(tau, 0) / 1.4) * sm((tau + 0.3) / 0.3)
        if z[0] > 0: glow(img, x[0], y[0], [(26, 10 * f), (110, 1.2 * f), (420, 0.08 * f)], (1.0, 0.62, 0.3))
    if tau > 0 and t < 21.5:                          # the plume -> the ring -> the Moon
        gather = sm((t - 15.4) / 4.0)
        X = plume_pts(tau, gather)
        hot = math.exp(-tau / 8.0)
        col = np.array([2.0, 0.75, 0.25]) * (0.35 + 0.65 * hot) * (1 - 0.9 * gather) * 0.9
        x, y, z = cm.project(c, X)
        # hide the points behind the Earth
        vis = np.ones(len(X), bool)
        oc = c[0]; Dp = X - oc; dist = np.linalg.norm(Dp, axis=1); Dn = Dp / dist[:, None]
        b = Dn @ oc; cc = oc @ oc - E_R ** 2; disc = b * b - cc
        tt = -b - np.sqrt(np.maximum(disc, 0)); vis &= ~((disc > 0) & (tt > 0) & (tt < dist))
        acc = np.zeros_like(img); splat(acc, c, X[vis], col * 1.1, size=2)
        from scipy.ndimage import gaussian_filter
        small = acc.reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3))
        img += acc + np.repeat(np.repeat(gaussian_filter(small, (3, 3, 0)) * 1.0 + gaussian_filter(small, (12, 12, 0)) * 0.5, 4, 0), 4, 1)
    if t > 15.4:                                      # the Moon
        g = sm((t - 15.4) / 4.0)
        rec = sm((t - 30.5) / 6.0)
        MP = moon_pos(rec)
        malb, memi = magma_maps(4.0)
        body(img, c, D, MP, M_R * max(g, 0.02), malb * 1.3, memi * lerp(0.9, 0.25, sm((t - 19) / 12)), L=L, spin=t * 0.02,
             ambient=0.004, depth=tE if mE.any() else None, atm=(1.0, 0.4, 0.12))
    return img, c

def cutaway(t):
    """today's Earth with a quarter cut away: crust, mantle, the cores — and two huge blobs at the base of the mantle"""
    k = sm((t - 37.0) / 12.0)
    c = orbit_cam(lerp(24.0, 18.0, k), lerp(-35.0, -15.0, k), RE * lerp(3.4, 3.0, k), 36.0)
    img = space(c, 0.55, 0.3)
    D = rays(c); o = c[0]
    b = np.array([0, 0, 1.0]); v = nrm(o - (o @ b) * b); s_ = nrm(np.cross(b, v))
    n1 = nrm(v + s_ * 1.0); n2 = b                                        # the removed quarter faces the camera at 45°
    a_ = -n1
    m, t0 = hit(c, D, (0, 0, 0), RE)
    P0 = o + D * t0[..., None]
    inW = m & ((P0 @ n1) > 0) & ((P0 @ n2) > 0)
    # surface (outside the wedge): Blue Marble
    surf = m & ~inW
    tex = today().astype(np.float32) / 255.0
    if surf.any():
        P = P0[surf] / RE
        lat = np.arcsin(np.clip(P[:, 2], -1, 1)); lon = np.arctan2(P[:, 1], P[:, 0])
        L = side_sun(c)
        col = sample(tex, lat, lon) ** 2.2 * (np.clip(P @ L, 0, 1)[:, None] * 2.6 + 0.02)
        mu = np.clip(-(D[surf] * P).sum(-1), 0, 1)[:, None]
        col += np.array([0.25, 0.45, 1.0]) * (1 - mu) ** 3 * 0.5
        img[surf] = col
    # inside: the two cut faces
    Dw = D[inW]; Pw = P0[inW]
    best = np.full(len(Dw), np.inf); face = np.zeros(len(Dw), int)
    for j, (nn, other) in enumerate(((n1, n2), (n2, n1))):
        den = Dw @ nn
        tt = np.where(np.abs(den) > 1e-9, -(o @ nn) / den, np.inf)
        Q = o + Dw * tt[:, None]
        okk = (tt > t0[inW] - 1) & ((Q @ other) >= 0) & (np.linalg.norm(Q, axis=1) <= RE)
        upd = okk & (tt < best); best = np.where(upd, tt, best); face = np.where(upd, j, face)
    got = np.isfinite(best)
    Q = o + Dw * best[:, None]; r = np.linalg.norm(Q, axis=1) / RE
    colw = np.zeros((len(Dw), 3), np.float32)
    mant = np.clip((r - 0.546) / (0.99 - 0.546), 0, 1)[:, None]
    cmant = np.array([1.6, 0.42, 0.10]) * (1 - mant) + np.array([0.55, 0.12, 0.04]) * mant
    cout = np.array([3.0, 1.5, 0.35]); cin = np.array([4.0, 3.2, 1.5])
    colw[:] = cmant
    colw[r < 0.546] = cout; colw[r < 0.19] = cin
    colw[r > 0.985] = np.array([0.18, 0.13, 0.10])
    # the blobs (LLSVPs): two dense domes on the core–mantle boundary, up to ~1000 km tall, thousands of km wide
    nz = fbm3(Q / RE * 5.0 + 2.0, 3)
    e1 = nrm(np.cross(n2, n1))                    # along the vertical face, horizontal
    hz = np.where(face == 0, Q @ n2, Q @ (-e1)) / RE     # in-face coordinate along the face (0 at the axis)
    ph = np.arctan2(np.where(face == 0, Q @ n2, Q @ e1), np.where(face == 0, Q @ (-n1 * 0 + e1), Q @ n1) + 1e-9)
    hgt = (r - 0.546) / 0.16
    ang_c = np.where(face == 0, 0.9, -0.7)
    ang = np.arctan2(Q @ np.where(face[:, None] == 0, n2, e1).T if False else 0, 1) if False else None
    blob = np.zeros(len(Q), bool)
    for f_, cen, wid in ((0, 0.50, 0.30), (1, 0.45, 0.26)):
        on = face == f_
        if f_ == 0: u = (Q @ n2) / RE / np.maximum(r, 1e-3)      # sin of the angle up from the equatorial face's edge
        else: u = (Q @ e1) / RE / np.maximum(r, 1e-3)
        dome = np.clip(1 - ((u - cen) / wid) ** 2, 0, 1) ** 0.6 * (1.0 + 0.25 * (nz - 0.5))
        blob |= on & (hgt > 0) & (hgt < dome)
    colw[blob] = np.array([0.42, 0.07, 0.20]) * (0.75 + 0.5 * nz[blob, None])
    sh = 0.75 + 0.25 * (face == 0)
    out = np.zeros((len(Dw), 3), np.float32); out[got] = colw[got] * sh[got, None]
    img[inW] = out
    # where the caption points: a blob on the left face
    A = (n2 * 0.33 + n1 * 0.0) * RE + nrm(np.cross(n1, n2)) * 0.0
    A = nrm(n1 * 0.0 + n2 * 0.33 + (-a_) * 0.0) * 0.6 * RE
    return img, c, A

@act
def theia(t):
    if t < 36.5:
        img, c = theia_world(t); return finish(img, expo=0.9)
    if t > 38.5:
        img, c, _ = cutaway(t); return finish(img, expo=0.9)
    k = sm((t - 36.5) / 2.0)
    a, _ = theia_world(t); b, _, _ = cutaway(t)
    return finish(a * (1 - k) + b * k, expo=0.9)

def theia_anchors(t):
    out = {}
    c = theia_cam(t); x, y, z = cm.project(c, theia_pos(t)); out['theia'] = (x[0], y[0])
    if t > 15: x, y, z = cm.project(c, moon_pos(sm((t - 30.5) / 6.0))); out['moon'] = (x[0], y[0])
    if t > 37:
        k = sm((t - 37.0) / 12.0)
        c2 = orbit_cam(lerp(24.0, 18.0, k), lerp(-35.0, -15.0, k), RE * lerp(3.4, 3.0, k), 36.0)
        o = c2[0]; bz = np.array([0, 0, 1.0]); v = nrm(o - (o @ bz) * bz); s_ = nrm(np.cross(bz, v)); n1 = nrm(v + s_)
        e1 = nrm(np.cross(bz, n1))
        cands = [(sg * e1 * math.cos(math.radians(30)) + bz * math.sin(math.radians(30))) * 0.62 * RE for sg in (1, -1)]
        A = min(cands, key=lambda P: np.linalg.norm(P - o))
        x, y, z = cm.project(c2, A); out['blob'] = (x[0], y[0])
    return out
ANCH['theia'] = theia_anchors


# ================================================================ the globe acts
def globe_shot(t, tex, cam, sun=None, expo=0.8, cloud_k=0.5, cloud_shift=0, night_k=0.0, air_k=1.0, home=(0.0, 0.0), bg=0.6):
    c = globe_cam(cam)
    expo *= 0.88
    img = space(c, bg, 0.3)
    globe(img, c, tex, side_sun(c) if sun is None else sun, expo=expo, cloud_k=cloud_k, cloud_shift=cloud_shift,
          night_k=night_k, air_k=air_k, home=home)
    return img, c

LASTCAM = {}
def globe_cam(cam):
    lat, lon, dist, fov = cam
    if dist > 2.3: dist *= 1.2                    # the whole globe in the frame, a little air around it
    c = orbit_cam(lat, lon, dist * RE, fov)
    LASTCAM['c'] = c
    return c
def ckeys(t, ks):            # camera keys: (t, (lat, lon, dist, fov))
    return tuple(float(x) for x in keys(t, [(a, np.array(b, float)) for a, b in ks]))

def mix_tex(a, b, k):
    if k <= 0: return a
    if k >= 1: return b
    if a.shape != b.shape:            # bring the smaller map up to the larger one's size
        big, small = (a, b) if a.shape[0] > b.shape[0] else (b, a)
        up = np.asarray(Image.fromarray(small).resize((big.shape[1], big.shape[0]), Image.BILINEAR))
        a, b = (a, up) if a is big else (up, b)
    return np.ascontiguousarray((a * (1 - k) + b * k).astype(np.uint8))

def noise_tex(name, fn):
    p = os.path.join(WORK, 'maps', name + '.png')
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True); Image.fromarray(fn()).save(p)
    return np.ascontiguousarray(np.asarray(Image.open(p).convert('RGB'), np.uint8))

def ocean_world():
    """the first oceans: dark water, a scatter of volcanic islands (no continents yet)"""
    def mk():
        P = sphere_grid(2048, 1024)
        n = fbm3(P * 4.0 + 1.0, 6); n2 = fbm3(P * 18.0 + 3.0, 4)
        land = n > 0.70
        sea = np.array([14, 30, 58]) * (0.85 + 0.3 * n2[..., None]); shelf = np.array([30, 70, 95])
        rock = np.array([88, 76, 68]) * (0.7 + 0.6 * n2[..., None])
        col = np.where(land[..., None], rock, np.where((n > 0.66)[..., None], shelf, sea))
        return np.clip(col, 0, 255).astype(np.uint8)
    return noise_tex('ocean_world', mk)

def archean(tint=0.0):
    """Archean Earth: small grey cratons, wide shallow seas with microbial mats along the shores"""
    def mk():
        P = sphere_grid(2048, 1024)
        n = fbm3(P * 3.2 + 7.0, 6); n2 = fbm3(P * 20.0 + 9.0, 4)
        land = n > 0.64; shelf = (n > 0.585) & ~land
        sea = np.array([16, 36, 62]) * (0.85 + 0.3 * n2[..., None])
        mats = np.array([44, 86, 84]) * (0.8 + 0.4 * n2[..., None])
        rock = np.array([118, 100, 86]) * (0.7 + 0.6 * n2[..., None])
        col = np.where(land[..., None], rock, np.where(shelf[..., None], mats, sea))
        return np.clip(col, 0, 255).astype(np.uint8)
    base = noise_tex('archean', mk)
    if tint <= 0: return base
    def mk2():                     # the rusting seas: iron oxide red along the shelves
        P = sphere_grid(2048, 1024)
        n = fbm3(P * 3.2 + 7.0, 6)
        shelf = ((n > 0.52) & (n <= 0.64)).astype(np.float32)[..., None]
        b = base.astype(np.float32)
        return np.clip(b * (1 - 0.75 * shelf) + np.array([150, 62, 30]) * 0.75 * shelf, 0, 255).astype(np.uint8)
    rust = noise_tex('archean_rust', mk2)
    return mix_tex(base, rust, tint)

def proterozoic():
    """a Proterozoic supercontinent (Columbia/Rodinia-like), bare rock, no plants"""
    def mk():
        P = sphere_grid(2048, 1024)
        lat = np.arcsin(P[..., 2]); lon = np.arctan2(P[..., 1], P[..., 0])
        mass = np.exp(-((lat - 0.1) / 0.75) ** 2 - ((np.angle(np.exp(1j * (lon - 0.6)))) / 1.3) ** 2)
        n = fbm3(P * 3.0 + 13.0, 6) * 0.55 + mass * 0.55; n2 = fbm3(P * 22.0 + 2.0, 4)
        land = n > 0.62; shelf = (n > 0.57) & ~land
        sea = np.array([12, 34, 66]) * (0.85 + 0.3 * n2[..., None]); sh = np.array([34, 84, 108])
        rock = np.array([142, 118, 96]) * (0.7 + 0.6 * n2[..., None])
        col = np.where(land[..., None], rock, np.where(shelf[..., None], sh, sea))
        return np.clip(col, 0, 255).astype(np.uint8)
    return noise_tex('proterozoic', mk)

def iced(tex, front, seed=0.0):
    """ice from the poles down to latitude `front` (degrees), ragged edge; ice textured, a little blue"""
    key = ('ice', id(tex))
    if key not in _ICE:
        _ICE.clear()
        h, w = tex.shape[:2]
        P = sphere_grid(w, h)
        lat = np.degrees(np.arcsin(P[..., 2]))
        n_a = fbm3(P * 30.0 + 2.0, 4); n_b = fbm3(P * 120.0 + 9.0, 3)
        ridge = np.clip(1 - np.abs(fbm3(P * 45.0 + 4.0, 4) - 0.5) * 10, 0, 1) ** 3
        v = 0.50 + 0.16 * n_a + 0.08 * n_b - 0.12 * ridge
        ICE = np.stack([v * 0.86, v * 0.94, v * 1.0], -1) * 255
        _ICE[key] = (np.abs(lat), (fbm3(P * 6.0, 5) - 0.5) * 14.0, ICE)
    alat, edge, ICE = _ICE[key]
    m = np.clip((alat + edge - front) / 6.0, 0, 1)[..., None]
    return np.ascontiguousarray(np.clip(tex * (1 - m) + ICE * m, 0, 255).astype(np.uint8))
_ICE = {}

def magma_globe(t, cam, k_emis=1.0):
    c = globe_cam(cam)
    img = space(c, 0.6, 0.3)
    alb, emi = magma_maps(0.0)
    body(img, c, rays(c), (0, 0, 0), RE, alb, emi, L=side_sun(c), spin=t * 0.05, ambient=0.004, atm=(1.4, 0.45, 0.12), emi_k=k_emis)
    return img, c

@act
def oceans(t):
    cam = ckeys(t, [(-0.5, (12, 40, 3.2, 36)), (25.6, (6, 95, 2.9, 36))])
    if t < 7.0:
        a, c = magma_globe(t, cam, k_emis=lerp(1.0, 0.15, sm(t / 6.0)))
        if t < 3.0: return finish(a)
    tex = ocean_world()
    steam = 1 - sm((t - 9.0) / 7.0)
    b, c = globe_shot(t, tex, cam, expo=0.85, cloud_k=lerp(1.0, 0.55, 1 - steam), cloud_shift=300, air_k=1.2)
    if t < 7.0:
        k = sm((t - 3.0) / 4.0); img = a * (1 - k) + b * k
    else:
        img = b
    if t > 17.5: meteors(img, c, t - 17.5, 0.6, seed=8, life=1.2)
    return finish(img)

@act
def life(t):
    cam = ckeys(t, [(-0.5, (-5, 120, 2.2, 38)), (17, (-12, 150, 1.75, 40)), (35.3, (-8, 175, 1.9, 38))])
    img, c = globe_shot(t, archean(), cam, expo=0.85, cloud_k=0.55, cloud_shift=500)
    return finish(img)

@act
def oxygen(t):
    rust = sm((t - 10.0) / 6.0) * (1 - 0.6 * sm((t - 28.0) / 10.0))
    cam = ckeys(t, [(-0.5, (-8, 180, 1.9, 38)), (24, (5, 230, 2.6, 36)), (48.4, (10, 270, 3.0, 36))])
    img, c = globe_shot(t, archean(rust), cam, expo=0.85, cloud_k=0.5, cloud_shift=650, air_k=lerp(0.7, 1.15, sm((t - 25) / 15)))
    return finish(img)

@act
def boring(t):
    cam = ckeys(t, [(-0.5, (10, 270, 3.0, 36)), (31.9, (16, 330, 3.3, 36))])
    tex = mix_tex(archean(0.4), proterozoic(), sm((t + 0.5) / 4.0))
    img, c = globe_shot(t, tex, cam, expo=0.82, cloud_k=0.5, cloud_shift=800)
    return finish(img)

@act
def snowball(t):
    cam = ckeys(t, [(-0.5, (16, 330, 3.3, 36)), (21.9, (8, 380, 3.4, 36))])
    tex = proterozoic()
    front = 75.0 - 75.0 * sm((t - 1.0) / 8.0) + 70.0 * sm((t - 15.5) / 6.0)
    img, c = globe_shot(t, iced(tex, front), cam, expo=0.55, cloud_k=0.35, cloud_shift=900)
    if 12.5 < t < 20.5:              # volcanoes through the ice, the CO2 builds up
        rng = np.random.default_rng(4)
        for i in range(14):
            la, lo = rng.uniform(-35, 35), rng.uniform(0, 360)
            x, y, z = cm.project(c, ll(la, lo) * RE)
            if ll(la, lo) @ nrm(c[0]) > 0.45:
                f = sm((t - 12.5 - i * 0.25) / 1.0) * (1 - sm((t - 19.0) / 1.5)) * (0.6 + 0.4 * math.sin(t * 3 + i))
                glow(img, x[0], y[0], [(2.5, 9 * f), (10, 1.2 * f)], (1.0, 0.45, 0.15))
    return finish(img)

def paleo_globe(t, ma, cam, cloud_k=0.5, cloud_shift=0, expo=0.82, air_k=1.0):
    return globe_shot(t, paleo_at(ma), cam, expo=expo, cloud_k=cloud_k, cloud_shift=cloud_shift, air_k=air_k)

@act
def ediacara(t):
    tex = mix_tex(iced(proterozoic(), 70.0), paleo(540), sm((t + 0.5) / 5.0))
    cam = ckeys(t, [(-0.5, (8, 20, 3.4, 36)), (12.0, (-20, 40, 3.0, 36))])
    img, c = globe_shot(t, tex, cam, expo=0.82, cloud_k=0.45, cloud_shift=950)
    return finish(img)

@act
def cambrian(t):
    cam = ckeys(t, [(-0.5, (-20, 40, 3.0, 36)), (22.8, (-30, 90, 2.4, 38))])
    img, c = paleo_globe(t, lerp(540, 500, sm(t / 22.3)), cam, cloud_shift=980)
    return finish(img)

@act
def land(t):
    cam = ckeys(t, [(-0.5, (-30, 90, 2.4, 38)), (16.6, (-15, 130, 2.0, 40))])
    img, c = paleo_globe(t, lerp(480, 380, sm(t / 16.1)), cam, cloud_shift=1000)
    return finish(img)

@act
def coal(t):
    cam = ckeys(t, [(-0.5, (-15, 130, 2.0, 40)), (24.6, (-5, 170, 2.6, 36))])
    img, c = paleo_globe(t, lerp(370, 300, sm(t / 24.1)), cam, cloud_shift=1020)
    return finish(img)

SIB = (60.0, 60.0)          # the Siberian Traps on the 250 Ma map (approximate)
@act
def permian(t):
    cam = ckeys(t, [(-0.5, (-5, 170, 2.6, 36)), (4.0, (35, 70, 3.0, 36)), (14.0, (45, 62, 2.6, 38)), (26.0, (30, 40, 3.1, 36))])
    smoke = sm((t - 6.0) / 8.0)
    img, c = paleo_globe(t, lerp(290, 250, sm(t / 10.0)), cam, cloud_shift=1040, expo=lerp(0.82, 0.62, smoke), air_k=1 + 0.8 * smoke)
    if t > 4.0:                       # the traps: fissures glowing over a huge area of Siberia
        rng = np.random.default_rng(2)
        for i in range(60):
            la = SIB[0] + rng.normal(0, 6); lo = SIB[1] + rng.normal(0, 11)
            P = ll(la, lo)
            if P @ nrm(c[0]) < 0.4: continue
            x, y, z = cm.project(c, P * RE)
            f = sm((t - 4.0 - rng.uniform(0, 6)) / 1.5) * (0.7 + 0.3 * math.sin(t * 2.3 + i)) * (1 - 0.5 * sm((t - 20) / 5))
            glow(img, x[0], y[0], [(2.0, 7 * f), (9, 0.9 * f)], (1.0, 0.4, 0.12))
    return finish(img)

@act
def dinos(t):
    cam = ckeys(t, [(-0.5, (30, 40, 3.1, 36)), (12, (20, -10, 2.8, 36)), (29.7, (15, -40, 3.0, 36))])
    img, c = paleo_globe(t, lerp(240, 65, sm((t - 1.0) / 26.0)), cam, cloud_shift=1060)
    return finish(img)

@act
def mammals(t):
    cam = ckeys(t, [(-0.5, (15, -40, 3.0, 36)), (8, (20, 60, 2.7, 36)), (17, (25, 80, 2.4, 38)), (23.5, (8, 28, 2.9, 36)), (30.5, (30, 40, 3.3, 36)), (40.0, (35, 35, 3.0, 36))])
    ma = lerp(65, 0, sm(t / 22.0))
    tex = paleo_at(ma) if t < 22.5 else today()
    if 22.5 <= t < 25.0: tex = mix_tex(paleo(0), today(), sm((t - 22.5) / 2.5))
    lat, lon, dist, fov = cam
    c = globe_cam(cam)
    img = space(c, 0.6, 0.3)
    night = sm((t - 30.5) / 4.0)
    sun = nrm(side_sun(c) * (1 - night) + ll(10.0, lon + 120.0) * night)
    globe(img, c, tex, sun, expo=lerp(0.82, 0.9, night), cloud_k=0.55, night_k=1.8 * night, home=(lat, lon))
    return finish(img)

@act
def future(t):
    cam = ckeys(t, [(-0.5, (35, 35, 3.0, 36)), (12, (20, -10, 3.1, 36)), (30, (10, -40, 3.4, 36)), (44.2, (5, -60, 6.5, 34))])
    lat, lon, dist, fov = cam
    c = globe_cam(cam)
    img = space(c, 0.6, 0.3)
    bright = sm((t - 11.5) / 6.0) * (1 - sm((t - 21.0) / 5.0))
    globe(img, c, today(), side_sun(c), expo=0.82 * (1 + 0.6 * bright), cloud_k=0.55, air_k=1 + 0.5 * bright, home=(lat, lon))
    return finish(img)

# ================================================================ helpers for the run
def act_range(name):
    a = TL[name]; return a['start'] - XF / 2, a['end'] + XF / 2

def render(name, i0=None, i1=None):
    t0, t1 = act_range(name)
    f0, f1 = max(0, int(math.floor(t0 * FPS))), int(math.ceil(t1 * FPS))
    if i0 is not None: f0, f1 = max(f0, i0), min(f1, i1)
    d = os.path.join(ACTS_DIR, name); os.makedirs(d, exist_ok=True)
    for i in range(f0, f1):
        p = os.path.join(d, f'f_{i:05d}.jpg')
        if os.path.exists(p): continue
        Image.fromarray(ACTS[name](i / FPS - TL[name]['start'])).save(p, quality=94)
        if i % 60 == 0: print(name, i, '/', f1, flush=True)

if __name__ == '__main__':
    name, mode = sys.argv[1], sys.argv[2]
    if mode == 'stills':
        d = os.path.join(WORK, 'stills'); os.makedirs(d, exist_ok=True)
        ims = []
        for t in [float(x) for x in sys.argv[3].split(',')]:
            a = ACTS[name](t); ims.append(Image.fromarray(a).resize((640, 360)))
            Image.fromarray(a).save(os.path.join(d, f'{name}_{t:g}.jpg'), quality=90)
        sheet = Image.new('RGB', (640 * 3, 360 * ((len(ims) + 2) // 3)))
        for i, im in enumerate(ims): sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
        sheet.save(os.path.join(d, f'{name}_sheet.jpg'), quality=88); print('sheet')
    else:
        a = [int(x) for x in sys.argv[3:5]] if len(sys.argv) > 4 else [None, None]
        render(name, *a)
