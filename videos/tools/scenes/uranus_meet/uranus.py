# «Знайомся: Уран» — Uranus from space, drawn on the CPU (numba): the planet (an oblate spheroid, the pale cyan of
# Voyager 2's true-colour view, the faint zonal bands and the bright north polar cap with storms at its edge that JWST
# and Keck show), its 13 narrow, very dark rings at their real radii and widths (the epsilon ring eccentric), the dust
# between them that lights up only against the Sun (as in Voyager's PIA00142), the shadows (rings on the planet, the
# planet on the rings), textured spheres (the Earth for scale, Miranda), the Sun and the sky (the ESO Milky Way photo
# and sharp stars, from the TRAPPIST-1e renderer, whose bloom and tone mapping are used too).
#
#   from uranus import frame; img = frame(cam, target, ...)        (km, Uranus at the origin, z = its north pole)
#   python3 uranus.py test                                            -> work/uranus_meet/test_*.jpg
import math, os, sys
import numpy as np
from numba import njit, prange
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(TOOLS, 'scenes', 'trappist_e'), TOOLS]
import render as TR                     # background(), finish(), cam_basis(), RW/RH (720x1280, x2 supersampling)
from still import fbm, smooth, PERM

W, H, RW, RH = TR.W, TR.H, TR.RW, TR.RH
WORK = os.path.join(TOOLS, 'work', 'uranus_meet'); os.makedirs(WORK, exist_ok=True)
RE, RP = 25559.0, 24973.0               # equatorial and polar radius, km
SITE_TEX = os.path.join(os.path.dirname(os.path.dirname(TOOLS)), 'planetarium', 'textures')

# ---- the rings (Planetary Rings Node; French et al. 1991): radius, width (km), normal optical depth; dust: tau of
# the fine dust (seen only in forward scattering) and its width
RINGS = np.array([
    # a        w      tau    dust_tau  dust_w
    [41837.0,  1.6,   0.30,  0.0,      0.0],    # 6
    [42234.0,  2.2,   0.50,  0.0,      0.0],    # 5
    [42571.0,  2.4,   0.30,  0.0,      0.0],    # 4
    [44718.0,  9.0,   0.40,  0.0,      0.0],    # alpha
    [45661.0,  8.0,   0.30,  0.0,      0.0],    # beta
    [47176.0,  1.6,   0.30,  2.0e-3,   55.0],   # eta (and its broad dusty skirt)
    [47627.0,  3.5,   1.50,  0.0,      0.0],    # gamma
    [48300.0,  5.5,   0.50,  1.0e-3,   12.0],   # delta
    [50023.0,  2.0,   0.10,  2.5e-3,   3.0],    # lambda (dusty)
], np.float64)
EPS_A, EPS_E, EPS_W0, EPS_W1, EPS_TAU = 51149.0, 0.00794, 19.7, 96.4, 1.6   # the epsilon ring (peri/apo widths)
# the dust sheets between the rings (PIA00142: dozens of lanes from ~37 000 to ~51 000 km), the zeta ring, nu and mu
_r = np.random.default_rng(3)
_lanes = []
for k in range(46):
    a = _r.uniform(37500, 51600); _lanes.append([a, _r.uniform(30, 260), 10 ** _r.uniform(-4.0, -2.9)])
_lanes += [[39600.0, 3500.0, 4e-4], [67900.0, 3800.0, 6e-5], [97700.0, 17000.0, 9e-5]]
DUST = np.array(_lanes, np.float64)

def load_tex(name, w=2048, h=1024):
    im = Image.open(os.path.join(SITE_TEX, name)).convert('RGB').resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).astype(np.float32)   # sRGB -> linear

_tex = {}
def textures():
    if not _tex:
        _tex['all'] = np.stack([load_tex('earth_day.jpg'), load_tex('miranda.jpg')])
    return _tex['all']

@njit(cache=True, inline='always')
def tex_samp(T, k, TW, TH, nx, ny, nz, c):
    lon = math.atan2(ny, nx); lat = math.asin(min(1.0, max(-1.0, nz)))
    fx = (lon + math.pi) / (2 * math.pi) * TW - 0.5; fy = (math.pi / 2 - lat) / math.pi * TH - 0.5
    x0 = int(math.floor(fx)); y0 = int(math.floor(fy)); ax = fx - x0; ay = fy - y0
    x0m = x0 % TW; x1m = (x0 + 1) % TW; y0c = min(TH - 1, max(0, y0)); y1c = min(TH - 1, max(0, y0 + 1))
    return ((T[k, y0c, x0m, c] * (1 - ax) + T[k, y0c, x1m, c] * ax) * (1 - ay)
            + (T[k, y1c, x0m, c] * (1 - ax) + T[k, y1c, x1m, c] * ax) * ay)

# ---------------------------------------------------------------------------------------------------- the rings
@njit(cache=True, inline='always')
def box_cover(r, a, w, fp):
    """the share of a footprint [r-fp/2, r+fp/2] covered by the band [a-w/2, a+w/2]"""
    lo = max(r - fp * 0.5, a - w * 0.5); hi = min(r + fp * 0.5, a + w * 0.5)
    return max(0.0, hi - lo) / fp

@njit(cache=True)
def ring_at(px, py, fp, mu, RG, DU, eps_k):
    """at a point of the ring plane: (opacity of the dense rings along a ray with |cos| = mu, their mean optical depth
    there, the dust's optical depth); fp = the footprint of the pixel along the radius (km)"""
    r = math.sqrt(px * px + py * py)
    trans = 1.0; tau_mean = 0.0; dust = 0.0
    if r < 36000 or r > 116000: return 0.0, 0.0, 0.0
    for i in range(RG.shape[0]):
        a = RG[i, 0]
        if abs(r - a) < fp + RG[i, 1] + RG[i, 4]:
            c = box_cover(r, a, RG[i, 1], fp)
            if c > 0:
                trans *= 1.0 - c * (1.0 - math.exp(-RG[i, 2] / mu)); tau_mean += c * RG[i, 2]
            if RG[i, 3] > 0:
                dust += RG[i, 3] * box_cover(r, a, RG[i, 4], fp)
    # epsilon: an ellipse (focus at the centre), wider at apoapsis
    th = math.atan2(py, px) - 0.6
    re = EPS_A * (1 - EPS_E * EPS_E) / (1 + EPS_E * math.cos(th))
    we = EPS_W0 + (EPS_W1 - EPS_W0) * 0.5 * (1 - math.cos(th))
    if abs(r - re) < fp + we:
        c = box_cover(r, re, we, fp)
        if c > 0:
            trans *= 1.0 - c * (1.0 - math.exp(-EPS_TAU * eps_k / mu)); tau_mean += c * EPS_TAU
    for i in range(DU.shape[0]):
        if abs(r - DU[i, 0]) < fp + DU[i, 1]:
            dust += DU[i, 2] * box_cover(r, DU[i, 0], DU[i, 1], fp)
    return 1.0 - trans, tau_mean, dust

@njit(cache=True, inline='always')
def hg(c, g):
    return (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * c) ** 1.5)

@njit(cache=True, inline='always')
def hit_planet(ox, oy, oz, dx, dy, dz):
    """distance along the ray to the spheroid (or -1)"""
    k = RE / RP
    oz2 = oz * k; dz2 = dz * k
    a = dx * dx + dy * dy + dz2 * dz2
    b = ox * dx + oy * dy + oz2 * dz2
    c = ox * ox + oy * oy + oz2 * oz2 - RE * RE
    disc = b * b - a * c
    if disc < 0: return -1.0
    t = (-b - math.sqrt(disc)) / a
    if t > 0: return t
    return -1.0

# ---------------------------------------------------------------------------------------------------- the planet
@njit(cache=True)
def uranus_albedo(nx, ny, nz, rot, P, cap):
    lat = math.asin(min(1.0, max(-1.0, nz))); lon = math.atan2(ny, nx) + rot
    cl = math.cos(lat)
    # zonal structure: noise stretched along the parallels, a few soft bands
    sx, sy, sz = cl * math.cos(lon) * 2.2, cl * math.sin(lon) * 2.2, lat * 9.0
    n1 = fbm(sx, sy, sz, P, 5, 2.0, 0.55)
    n2 = fbm(sx * 3.0 + 7.0, sy * 3.0, lat * 40.0, P, 4, 2.0, 0.5)
    ld = math.degrees(lat)
    band = 0.045 * math.sin(lat * 7.0 + 0.6) + 0.030 * math.sin(lat * 17.0) + 0.070 * n1 + 0.028 * n2
    # the bright north polar cap (since ~2015, JWST 2023) and a darker collar round it
    capk = cap * smooth(50.0, 64.0, ld)
    collar = cap * (smooth(38.0, 46.0, ld) - smooth(46.0, 52.0, ld))
    # bright storms at the cap's edge
    st = 0.0
    for k in range(6):
        slat = math.radians(52.0 + 9.0 * ((k * 37) % 7) / 7.0); slon = 1.1 * k + 0.4
        cx = math.cos(slat) * math.cos(slon); cy = math.cos(slat) * math.sin(slon); cz = math.sin(slat)
        px, py, pz = cl * math.cos(lon), cl * math.sin(lon), nz
        d2 = (px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2
        st += math.exp(-d2 / (0.0009 + 0.0006 * (k % 3))) * (0.6 + 0.4 * (k % 2))
    st *= cap * (0.8 + 0.3 * n2)
    base = 1.0 + band - 0.10 * collar + 0.10 * capk + 0.30 * st
    # colour: Voyager 2 true colour (PIA18182) at mid-latitudes; deeper and greener-blue towards the equator (more
    # methane above the clouds), the cap whiter (its haze), as Keck and JWST show it
    eq = 1.0 - smooth(20.0, 60.0, abs(ld))
    r = (0.47 - 0.06 * eq + 0.17 * capk) * base
    g = (0.79 - 0.02 * eq + 0.07 * capk) * base
    b = (0.84 + 0.01 * eq + 0.03 * capk) * base
    return r, g, b

@njit(cache=True, parallel=True)
def render(img, mask, RW, RH, ox, oy, oz, rx, ry, rz, ux, uy, uz, fx, fy, fz, TX, TY,
           Sx, Sy, Sz, sun_int, rot, P, RG, DU, ring_k, dust_k, eps_k, haze, cap, planet_on,
           SPH, TEX, TW, TH, glow_k):
    pix = 2.0 * TY / RH                              # angular size of a pixel (rad)
    AR, AG, AB = 0.42, 0.72, 1.0                     # the haze's colour
    for j in prange(RH):
        for i in range(RW):
            px_ = ((i + 0.5) / RW * 2 - 1) * TX; py_ = (1 - (j + 0.5) / RH * 2) * TY
            dx = fx + px_ * rx + py_ * ux; dy = fy + px_ * ry + py_ * uy; dz = fz + px_ * rz + py_ * uz
            nn = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= nn; dy /= nn; dz /= nn
            col_r = 0.0; col_g = 0.0; col_b = 0.0; alpha = 0.0
            tp = hit_planet(ox, oy, oz, dx, dy, dz) if planet_on else -1.0
            tbest = tp if tp > 0 else 1e30
            # ---- spheres (the Earth, Miranda): in front of everything behind them
            for q in range(SPH.shape[0]):
                cx, cy, cz, rad = SPH[q, 0] - ox, SPH[q, 1] - oy, SPH[q, 2] - oz, SPH[q, 3]
                b = cx * dx + cy * dy + cz * dz
                if b <= 0: continue
                h2 = cx * cx + cy * cy + cz * cz - b * b
                if h2 >= rad * rad: continue
                t = b - math.sqrt(rad * rad - h2)
                if t > tbest: continue
                tbest = t; tp = -2.0
                nx, ny, nz = (dx * t - cx) / rad, (dy * t - cy) / rad, (dz * t - cz) / rad
                # texture frame: rotate about z by SPH[q,5], then tilt by SPH[q,6] about x
                cr, sr = math.cos(SPH[q, 5]), math.sin(SPH[q, 5]); ct, st = math.cos(SPH[q, 6]), math.sin(SPH[q, 6])
                ty_ = ny * ct + nz * st; tz_ = -ny * st + nz * ct
                tx2 = nx * cr + ty_ * sr; ty2 = -nx * sr + ty_ * cr
                k = int(SPH[q, 4])
                ar = tex_samp(TEX, k, TW, TH, tx2, ty2, tz_, 0); ag = tex_samp(TEX, k, TW, TH, tx2, ty2, tz_, 1)
                ab = tex_samp(TEX, k, TW, TH, tx2, ty2, tz_, 2)
                mu0 = nx * Sx + ny * Sy + nz * Sz
                dif = max(mu0, 0.0) * smooth(-0.02, 0.05, mu0)
                if k == 0:                                # the Earth: a thin blue atmosphere at the limb
                    nv = -(nx * dx + ny * dy + nz * dz)
                    rim = (1 - max(nv, 0.0)) ** 3 * smooth(-0.1, 0.3, mu0)
                    col_r = ar * dif * 1.6 + 0.05 * rim; col_g = ag * dif * 1.6 + 0.12 * rim; col_b = ab * dif * 1.6 + 0.35 * rim
                else:
                    col_r = ar * dif * 1.25; col_g = ag * dif * 1.22; col_b = ab * dif * 1.2
                alpha = 1.0
            # ---- the planet
            if tp > 0:
                hx, hy, hz = ox + dx * tp, oy + dy * tp, oz + dz * tp
                nx, ny, nz = hx / (RE * RE), hy / (RE * RE), hz / (RP * RP)
                nl = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nl; ny /= nl; nz /= nl
                ux_, uy_, uz_ = hx / RE, hy / RE, hz / RP                  # the "unit sphere" point, for the texture
                ul = math.sqrt(ux_ * ux_ + uy_ * uy_ + uz_ * uz_); ux_ /= ul; uy_ /= ul; uz_ /= ul
                ar, ag, ab = uranus_albedo(ux_, uy_, uz_, rot, P, cap)
                mu0 = nx * Sx + ny * Sy + nz * Sz
                mu = max(-(nx * dx + ny * dy + nz * dz), 0.0)
                # Minnaert limb darkening (k ~ 0.85 for Uranus in the visible), a soft terminator (deep haze)
                lit = (max(mu0, 0.0) ** 0.95) * (max(mu, 0.02) ** (-0.05)) * smooth(-0.06, 0.10, mu0)
                lit += 0.010 * smooth(-0.15, 0.05, mu0)                     # twilight beyond the terminator
                # the rings' shadow
                if abs(Sz) > 1e-4:
                    ts = -hz / Sz
                    if ts > 0:
                        sxp, syp = hx + Sx * ts, hy + Sy * ts
                        op, tm, du = ring_at(sxp, syp, 30.0, abs(Sz), RG, DU, eps_k)
                        lit *= 1.0 - 0.9 * op
                col_r = ar * lit * 0.80; col_g = ag * lit * 0.80; col_b = ab * lit * 0.80
                # haze over the disc, stronger towards the limb
                fr = (1 - mu) ** 4
                hl = smooth(-0.15, 0.35, mu0)
                col_r += haze * AR * 0.10 * fr * hl; col_g += haze * AG * 0.10 * fr * hl; col_b += haze * AB * 0.10 * fr * hl
                alpha = 1.0
            elif planet_on and tp == -1.0:
                # the haze just outside the limb: a thin glowing ring, lit where the Sun is, bright against the Sun
                b = -(ox * dx + oy * dy + oz * dz * (RE / RP) ** 2)
                mx, my, mz = ox + dx * b, oy + dy * b, oz + dz * b
                hd = math.sqrt(mx * mx + my * my + (mz * RE / RP) ** 2) / RE
                if b > 0 and hd < 1.06:
                    mn = math.sqrt(mx * mx + my * my + mz * mz)
                    la = smooth(-0.25, 0.35, (mx * Sx + my * Sy + mz * Sz) / mn)
                    fwd = max(0.0, dx * Sx + dy * Sy + dz * Sz)
                    k = haze * (math.exp(-(hd - 1.0) / 0.004) * 0.18 * la + math.exp(-(hd - 1.0) / 0.010) * 3.0 * fwd ** 20)
                    col_r += AR * k * 0.6; col_g += AG * k * 0.8; col_b += AB * k
                    alpha = max(alpha, min(1.0, k * 2.0))
            # ---- the rings (in front of what was hit, or over the sky)
            if (ring_k > 0 or dust_k > 0) and abs(dz) > 1e-7:
                tr = -oz / dz
                if tr > 0 and tr < tbest:
                    qx, qy = ox + dx * tr, oy + dy * tr
                    mu = abs(dz)
                    fp = max(tr * pix / max(mu, 0.02), 0.2)     # radial footprint of the pixel
                    fp = min(fp, tr * pix * 25.0)
                    op, tm, du = ring_at(qx, qy, fp, mu, RG, DU, eps_k)
                    if op > 0 or du > 0:
                        # sunlit? (the planet's shadow)
                        sh = 1.0
                        if hit_planet(qx, qy, 0.0, Sx, Sy, Sz) > 0: sh = 0.0
                        mu0 = abs(Sz)
                        same = (oz > 0) == (Sz > 0)
                        # dense rings: dark particles (single-scattering albedo ~0.03), lit face
                        ca = -(dx * Sx + dy * Sy + dz * Sz)       # cos(phase angle)
                        ph = 0.55 + 0.45 * ca                     # backscattering particles: brighter at low phase
                        lit = 0.0
                        if same: lit = 0.03 * ph * mu0 / (mu0 + mu + 1e-3) * 4.0
                        else: lit = 0.03 * 0.15 * ph
                        br = op * lit * sh * ring_k
                        # planetshine (the dark side of the rings next to the bright planet)
                        br += op * 0.0025 * ring_k
                        # dust: forward scattering, seen from either side
                        fw = hg(dx * Sx + dy * Sy + dz * Sz, 0.75)
                        dl = du / mu * fw * sh * dust_k * 6.0
                        tcol = 1.0 - op
                        col_r = col_r * tcol + br * 0.92 + dl * 0.95
                        col_g = col_g * tcol + br * 0.90 + dl * 0.97
                        col_b = col_b * tcol + br * 0.88 + dl * 1.0
                        alpha = alpha * tcol + min(1.0, op + dl * 0.3)
            # ---- the Sun: a tiny dazzling disc
            if sun_int > 0 and tbest > 1e29:
                ca_ = dx * Sx + dy * Sy + dz * Sz
                if ca_ > 0.99999:
                    ang = math.acos(min(1.0, ca_))
                    rs = 0.000245                                  # the Sun's angular radius from 19.4 au
                    e = max(0.0, 1.0 - ang / max(rs, pix * 0.7))
                    if e > 0:
                        col_r += sun_int * e; col_g += sun_int * e * 0.97; col_b += sun_int * e * 0.92
                    # its glare (wide, soft)
                    g = glow_k * sun_int * 0.002 * (pix / max(ang, pix)) ** 2.2
                    col_r += g; col_g += g * 0.97; col_b += g * 0.92
            img[j, i, 0] = col_r; img[j, i, 1] = col_g; img[j, i, 2] = col_b
            mask[j, i] = min(1.0, alpha)

# ---------------------------------------------------------------------------------------------------- python side
def sun_flare(img, cam_p, r, u, f, TX, TY, S, vis_map, k=1.0):
    """the Sun's glare in the frame: a hot core, a soft halo and thin rays; vis_map: how clear the view is at each
    pixel (the core is hidden where something is in front of it)"""
    if k <= 0: return
    S = np.asarray(S, float)
    cz = S @ f
    if cz <= 0.05: return
    x = (S @ r) / cz / TX; y = (S @ u) / cz / TY
    X = (x + 1) / 2 * RW; Y = (1 - y) / 2 * RH
    if not (-0.3 * RW < X < 1.3 * RW and -0.3 * RH < Y < 1.3 * RH): return
    xi, yi = int(np.clip(X, 0, RW - 1)), int(np.clip(Y, 0, RH - 1))
    y0, y1 = max(0, yi - 3), min(RH, yi + 4); x0, x1 = max(0, xi - 3), min(RW, xi + 4)
    vis = float(vis_map[y0:y1, x0:x1].mean()) if (0 <= X < RW and 0 <= Y < RH) else 0.0
    if vis <= 0.01: return
    yy, xx = np.mgrid[0:RH, 0:RW].astype(np.float32)
    d = np.hypot(xx - X, yy - Y) / RH + 1e-4
    ang = np.arctan2(yy - Y, xx - X)
    rays = (np.abs(np.cos(ang * 3 + 0.4)) ** 60 + 0.6 * np.abs(np.cos(ang * 2 - 0.9)) ** 90) * np.exp(-d / 0.10)
    g = (0.004 / d ** 1.6 * np.exp(-d / 0.5) + 0.25 * np.exp(-d / 0.05) + 0.8 * rays) * vis * k
    img[..., 0] += g; img[..., 1] += g * 0.97; img[..., 2] += g * 0.92


def unit(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)

def frame(cam, target, up=(0, 0, 1), fovy=34.0, sun=(0, 0, 1), sun_int=0.0, rot=0.0, ring_k=14.0, dust_k=0.0,
          eps_k=1.0, haze=1.0, cap=1.0, planet=True, spheres=None, star_gain=1.0, photo_gain=0.30, bloom=1.0,
          expo=1.0, sky_turn=0.0, glow_k=1.0, roll=0.0, raw=False, vignette=0.25):
    TY = math.tan(math.radians(fovy) / 2); TX = TY * RW / RH
    r, u, f = TR.cam_basis(cam, target, up)
    if roll:
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        r, u = r * cr + u * sr, -r * sr + u * cr
    S = unit(sun)
    img = np.zeros((RH, RW, 3), np.float32); mask = np.zeros((RH, RW), np.float32)
    SPH = np.asarray(spheres, np.float64).reshape(-1, 7) if spheres else np.zeros((0, 7))
    T = textures()
    render(img, mask, RW, RH, *map(float, cam), *r, *u, *f, TX, TY, *S, sun_int, rot, PERM, RINGS, DUST,
           ring_k, dust_k, eps_k, haze, cap, planet, SPH, T, T.shape[2], T.shape[1], glow_k)
    img *= expo
    if sun_int > 0: sun_flare(img, cam, r, u, f, TX, TY, S, 1 - mask, sun_int / 200.0)
    bg = TR.background(r, u, f, TX, TY, mask, star_gain, photo_gain, TR.GAL @ TR.rotz(sky_turn))
    img = img + bg * (1 - mask[..., None])
    if raw: return img
    return TR.finish(img, bloom, vignette)

def sun_dir_2026():
    """planet -> Sun in Uranus' frame (z = north pole) for late November 2026: the Sun 73.8° above the equator"""
    lat = math.radians(73.8)
    return np.array([math.cos(lat), 0.0, math.sin(lat)])

if __name__ == '__main__' and sys.argv[1:2] == ['test']:
    import time
    S = sun_dir_2026()
    t0 = time.time()
    # from the Sun's side, a little off: the "target"
    cam = S * 260000 + np.array([0, 40000, 0])
    frame(cam, (0, 0, 0), up=(0, 0, 1), fovy=40, sun=S).save(os.path.join(WORK, 'test_a.jpg'))
    print('a', time.time() - t0)
    # from the side, the orbital plane level: lying on its side
    cam = np.array([0, -300000, 30000.0])
    frame(cam, (0, 0, 0), up=(1, 0, 0), fovy=40, sun=S).save(os.path.join(WORK, 'test_b.jpg'))
    # against the Sun: the dust lights up
    cam = -S * 160000 + np.array([0, 20000, 0])
    frame(cam, (0, 0, 0), up=(0, 0, 1), fovy=60, sun=S, sun_int=200, dust_k=1.0).save(os.path.join(WORK, 'test_c.jpg'))
    print('done', time.time() - t0)
