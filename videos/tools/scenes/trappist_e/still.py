# TRAPPIST-1e — a test still (5.11): the planet from space as an "eyeball" world (one of the scenarios scientists model
# for a tidally locked planet with an atmosphere and water: ice everywhere, an open ocean round the point under the star),
# lit by its dim orange-red star (behind the camera), with its neighbours TRAPPIST-1f and g in the sky at their real
# size for this configuration. Everything is drawn here on the CPU (numba): Perlin fbm on the sphere, bump relief, an
# ocean glint, clouds with shadows, a thin atmosphere; the background is the ESO/S. Brunier Milky Way photo plus sharp
# procedural stars.        python3 still.py [out.jpg]
import math, os, sys
import numpy as np
from numba import njit, prange
from PIL import Image, ImageFilter, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(TOOLS), 'trappist_test.jpg')
W, H, SS = 720, 1280, 2
RW, RH = W * SS, H * SS
FOVY = math.radians(34.0)
TY = math.tan(FOVY / 2); TX = TY * RW / RH

# ---- the system (Agol et al. 2021): radii in Earth radii, semi-major axes in AU; the star 0.1192 Sun radii, 2566 K ----
AU_KM, RE_KM = 1.495978707e8, 6371.0
RAD = {'e': 0.920, 'f': 1.045, 'g': 1.129}
SMA = {'e': 0.02925, 'f': 0.03849, 'g': 0.04683}
UNIT = RAD['e'] * RE_KM                      # lengths below are in radii of TRAPPIST-1e
TSTAR = 2566.0

def bb_rgb(T):
    """Linear sRGB of a black body (CIE 1931 via the Wyman 2013 fits), relative to the Sun (5772 K = white)."""
    lam = np.linspace(360, 830, 941)
    g = lambda m, s1, s2: np.exp(-0.5 * ((lam - m) / np.where(lam < m, s1, s2)) ** 2)
    xb = 1.056 * g(599.8, 37.9, 31.0) + 0.362 * g(442.0, 16.0, 26.7) - 0.065 * g(501.1, 20.4, 26.2)
    yb = 0.821 * g(568.8, 46.9, 40.5) + 0.286 * g(530.9, 16.3, 31.1)
    zb = 1.217 * g(437.0, 11.8, 36.0) + 0.681 * g(459.0, 26.0, 13.8)
    def rgb(T):
        l = lam * 1e-9; B = 1 / l ** 5 / (np.exp(1.4388e-2 / (l * T)) - 1)
        X, Y, Z = (B * xb).sum(), (B * yb).sum(), (B * zb).sum()
        M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
        return M @ np.array([X, Y, Z])
    c = rgb(T) / rgb(5772.0)
    return c / c.max()

# the eye adapts partly to the red light: a camera on "daylight" would show it deeper orange
STAR = bb_rgb(TSTAR) ** 0.80
STAR = (STAR / STAR.max()).astype(np.float64)

# ---- camera frame: x right, y up, z forward; the planet (radius 1) in the lower part of the frame ----
D = 6.75
dn = math.radians(4.3)
C = np.array([0.0, -math.sin(dn), math.cos(dn)]) * D
V0 = -C / np.linalg.norm(C)                                       # planet -> camera
side = np.array([-1.0, 0.78, 0.0]); side -= V0 * (side @ V0); side /= np.linalg.norm(side)
PHASE = math.radians(42.0)
L = math.cos(PHASE) * V0 + math.sin(PHASE) * side                 # planet -> star (the star is behind the camera, up left)
L /= np.linalg.norm(L)
NRM = np.cross(L, np.array([0.18, 0.0, 1.0])); NRM /= np.linalg.norm(NRM)   # the orbital plane's normal (contains L)

# ---- Perlin noise ----
rng = np.random.default_rng(11)
PERM = np.concatenate([rng.permutation(256)] * 2).astype(np.int64)

@njit(cache=True, inline='always')
def _fade(t): return t * t * t * (t * (t * 6 - 15) + 10)

@njit(cache=True, inline='always')
def _grad(h, x, y, z):
    h &= 15
    u = x if h < 8 else y
    v = y if h < 4 else (x if (h == 12 or h == 14) else z)
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

@njit(cache=True)
def perlin(x, y, z, P):
    fx, fy, fz = math.floor(x), math.floor(y), math.floor(z)
    X, Y, Z = int(fx) & 255, int(fy) & 255, int(fz) & 255
    x -= fx; y -= fy; z -= fz
    u, v, w = _fade(x), _fade(y), _fade(z)
    A = P[X] + Y; AA = P[A] + Z; AB = P[A + 1] + Z; B = P[X + 1] + Y; BA = P[B] + Z; BB = P[B + 1] + Z
    l1 = _grad(P[AA], x, y, z) + u * (_grad(P[BA], x - 1, y, z) - _grad(P[AA], x, y, z))
    l2 = _grad(P[AB], x, y - 1, z) + u * (_grad(P[BB], x - 1, y - 1, z) - _grad(P[AB], x, y - 1, z))
    l3 = _grad(P[AA + 1], x, y, z - 1) + u * (_grad(P[BA + 1], x - 1, y, z - 1) - _grad(P[AA + 1], x, y, z - 1))
    l4 = _grad(P[AB + 1], x, y - 1, z - 1) + u * (_grad(P[BB + 1], x - 1, y - 1, z - 1) - _grad(P[AB + 1], x, y - 1, z - 1))
    m1 = l1 + v * (l2 - l1); m2 = l3 + v * (l4 - l3)
    return m1 + w * (m2 - m1)

@njit(cache=True)
def fbm(x, y, z, P, octaves, lac, gain):
    s = 0.0; a = 1.0; f = 1.0; n = 0.0
    for i in range(octaves):
        s += a * perlin(x * f + i * 17.31, y * f - i * 9.17, z * f + i * 5.73, P)
        n += a; a *= gain; f *= lac
    return s / n

@njit(cache=True)
def ridged(x, y, z, P, octaves, lac, gain):
    s = 0.0; a = 1.0; f = 1.0; n = 0.0
    for i in range(octaves):
        r = 1.0 - abs(perlin(x * f - i * 3.1, y * f + i * 7.7, z * f + i * 1.9, P))
        s += a * r * r; n += a; a *= gain; f *= lac
    return s / n

@njit(cache=True, inline='always')
def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

# ---- the planet's surface at a unit point p (planet-fixed = world: it is tidally locked, the eye stays under the star) ----
@njit(cache=True)
def warp(px, py, pz, P):
    return (px + 0.32 * fbm(px * 1.7 + 11.0, py * 1.7, pz * 1.7, P, 4, 2.1, 0.5),
            py + 0.32 * fbm(px * 1.7, py * 1.7 + 23.0, pz * 1.7, P, 4, 2.1, 0.5),
            pz + 0.32 * fbm(px * 1.7, py * 1.7, pz * 1.7 + 37.0, P, 4, 2.1, 0.5))

@njit(cache=True)
def surface(px, py, pz, Lx, Ly, Lz, P):
    """-> albedo r,g,b; ocean fraction; height (for the relief)"""
    qx, qy, qz = warp(px, py, pz, P)
    th = math.acos(min(1.0, max(-1.0, px * Lx + py * Ly + pz * Lz)))
    # land: a few dark rocky highlands and island chains
    nl = fbm(qx * 2.3, qy * 2.3, qz * 2.3, P, 8, 2.05, 0.52)
    land = smooth(0.30, 0.34, nl)
    mount = ridged(qx * 7.0, qy * 7.0, qz * 7.0, P, 6, 2.1, 0.5)
    # the ice edge round the point under the star: ~36° with a ragged, warped coastline of ice
    th0 = math.radians(35.0) + math.radians(10.0) * fbm(qx * 3.1, qy * 3.1, qz * 3.1, P, 5, 2.2, 0.55)
    floes = fbm(px * 46.0, py * 46.0, pz * 46.0, P, 4, 2.3, 0.5)
    k = (th - th0) / math.radians(6.0)                            # <0 open water, 0..1 broken pack ice, >1 solid ice
    ice = smooth(-0.15, 1.0, k + 0.55 * floes)
    ocean = (1.0 - ice) * (1.0 - land)
    # ice: snow and bare blue glacial ice, pressure ridges and cracks
    big = fbm(qx * 5.0, qy * 5.0, qz * 5.0, P, 5, 2.0, 0.5)
    rid = ridged(qx * 26.0, qy * 26.0, qz * 26.0, P, 4, 2.2, 0.5)
    crack = smooth(0.80, 0.97, rid)
    bare = smooth(0.02, 0.22, -big) * smooth(-0.2, 0.25, fbm(qx * 11.0, qy * 11.0, qz * 11.0, P, 4, 2.1, 0.5))
    a_ice = (0.84 + 0.06 * big) * (1 - 0.42 * bare) - 0.12 * crack
    ir, ig, ib = a_ice * (1 - 0.30 * bare), a_ice * (1 - 0.05 * bare), a_ice * (1 + 0.35 * bare)
    # rock, snow on the high ground away from the ocean
    var = fbm(qx * 18.0, qy * 18.0, qz * 18.0, P, 4, 2.0, 0.5)
    rr, rg, rb = 0.105 + 0.03 * var, 0.088 + 0.025 * var, 0.072 + 0.02 * var
    snow = smooth(0.45, 0.8, mount) * smooth(-0.6, 0.6, k)
    rr = rr + (0.75 - rr) * snow; rg = rg + (0.74 - rg) * snow; rb = rb + (0.74 - rb) * snow
    # water: deep and dark, a touch lighter near the ice (melt, sediment)
    shelf = smooth(-2.5, 0.0, k)
    wr, wg, wb = 0.010 + 0.012 * shelf, 0.024 + 0.030 * shelf, 0.050 + 0.040 * shelf
    # mix: land over (ice/water)
    sr = ir * ice + wr * (1 - ice); sg = ig * ice + wg * (1 - ice); sb = ib * ice + wb * (1 - ice)
    ar = sr * (1 - land) + rr * land; ag = sg * (1 - land) + rg * land; ab = sb * (1 - land) + rb * land
    h = land * (0.35 + 0.65 * mount) + (1 - land) * ice * (0.08 * rid + 0.05 * big)
    return ar, ag, ab, ocean, h

@njit(cache=True)
def clouds(px, py, pz, Lx, Ly, Lz, P):
    """cloud cover 0..1: convective clusters over the warm ocean under the star, thin streaks further out"""
    d = px * Lx + py * Ly + pz * Lz
    th = math.acos(min(1.0, max(-1.0, d)))
    # a gentle swirl round the substellar point
    a = 1.1 * math.exp(-(th / 0.75) ** 2)
    ca, sa = math.cos(a), math.sin(a)
    cx = Ly * pz - Lz * py; cy = Lz * px - Lx * pz; cz = Lx * py - Ly * px
    rx = px * ca + cx * sa + Lx * d * (1 - ca); ry = py * ca + cy * sa + Ly * d * (1 - ca); rz = pz * ca + cz * sa + Lz * d * (1 - ca)
    qx, qy, qz = warp(rx * 1.3 + 5.0, ry * 1.3, rz * 1.3, P)
    n = fbm(qx * 4.2, qy * 4.2, qz * 4.2, P, 7, 2.15, 0.55)
    det = fbm(rx * 30.0, ry * 30.0, rz * 30.0, P, 3, 2.2, 0.5)
    cov = 0.04 + 0.26 * math.exp(-(th / 0.42) ** 2) + 0.12 * math.exp(-((th - 0.64) / 0.12) ** 2)
    c = n + 0.16 * det
    t0 = 0.30 - cov
    return smooth(t0, t0 + 0.24, c) * 0.82

ATM = np.array([1.0, 0.80, 0.70])

@njit(cache=True, parallel=True)
def render_planet(img, alpha, RW, RH, TX, TY, Cx, Cy, Cz, Lx, Ly, Lz, Sr, Sg, Sb, Ar, Ag, Ab, P):
    HS = 0.035                                          # atmosphere shell (exaggerated a little, for the eye)
    for j in prange(RH):
        for i in range(RW):
            dx = ((i + 0.5) / RW * 2 - 1) * TX; dy = (1 - (j + 0.5) / RH * 2) * TY; dz = 1.0
            nn = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= nn; dy /= nn; dz /= nn
            b = dx * Cx + dy * Cy + dz * Cz
            c2 = Cx * Cx + Cy * Cy + Cz * Cz
            h2 = c2 - b * b                                   # squared distance of the ray from the centre
            hd = math.sqrt(max(h2, 0.0))
            if hd > 1 + HS * 4: continue
            r = 0.0; g = 0.0; bl = 0.0; a = 0.0
            # closest point of the ray to the centre -> its "normal", for lighting the haze
            mx, my, mz = dx * b - Cx, dy * b - Cy, dz * b - Cz
            mn = math.sqrt(mx * mx + my * my + mz * mz) + 1e-9
            if hd < 1.0:
                t = b - math.sqrt(1.0 - h2)
                nx, ny, nz = dx * t - Cx, dy * t - Cy, dz * t - Cz
                vx, vy, vz = -dx, -dy, -dz
                mu = nx * Lx + ny * Ly + nz * Lz
                ar, ag, ab, ocean, h0 = surface(nx, ny, nz, Lx, Ly, Lz, P)
                # relief: the height's slope along two tangents bends the normal
                ex, ey, ez = ny * 0.0 - nz * 1.0, nz * 0.0 - nx * 0.0, nx * 1.0 - ny * 0.0
                en = math.sqrt(ex * ex + ey * ey + ez * ez) + 1e-9; ex /= en; ey /= en; ez /= en
                fx, fy, fz = ny * ez - nz * ey, nz * ex - nx * ez, nx * ey - ny * ex
                eps = 0.0016
                p1x, p1y, p1z = nx + ex * eps, ny + ey * eps, nz + ez * eps
                p2x, p2y, p2z = nx + fx * eps, ny + fy * eps, nz + fz * eps
                h1 = surface(p1x, p1y, p1z, Lx, Ly, Lz, P)[4]
                h2b = surface(p2x, p2y, p2z, Lx, Ly, Lz, P)[4]
                bump = 0.012
                gx, gy = (h1 - h0) / eps * bump, (h2b - h0) / eps * bump
                bx, by, bz = nx - gx * ex - gy * fx, ny - gx * ey - gy * fy, nz - gx * ez - gy * fz
                bn = math.sqrt(bx * bx + by * by + bz * bz); bx /= bn; by /= bn; bz /= bn
                mub = bx * Lx + by * Ly + bz * Lz
                term = smooth(-0.035, 0.05, mu)
                dif = term * max(mub, 0.0)
                # twilight: redder, dimmer light near the terminator (a long path through the air)
                tw = smooth(0.0, 0.22, mu)
                lr, lg, lb = Sr, Sg * (0.70 + 0.30 * tw), Sb * (0.50 + 0.50 * tw)
                # cloud shadow: the cloud a little toward the star
                tlx, tly, tlz = Lx - mu * nx, Ly - mu * ny, Lz - mu * nz
                sx, sy, sz = nx + tlx * 0.014, ny + tly * 0.014, nz + tlz * 0.014
                sn = math.sqrt(sx * sx + sy * sy + sz * sz)
                shadow = 1.0 - 0.65 * clouds(sx / sn, sy / sn, sz / sn, Lx, Ly, Lz, P)
                amb = smooth(-0.10, 0.25, mu)
                r = ar * (dif * lr * shadow + 0.030 * amb); g = ag * (dif * lg * shadow + 0.045 * amb); bl = ab * (dif * lb * shadow + 0.095 * amb)
                # the ocean's glint: the star mirrored in the water, with waves
                hx, hy, hz = Lx + vx, Ly + vy, Lz + vz
                hn = math.sqrt(hx * hx + hy * hy + hz * hz); hx /= hn; hy /= hn; hz /= hn
                wv = 0.0015 * fbm(nx * 9.0, ny * 9.0, nz * 9.0, P, 3, 2.0, 0.5)
                nh = min(1.0, max(0.0, nx * hx + ny * hy + nz * hz + wv))
                vh = max(0.0, vx * hx + vy * hy + vz * hz)
                fres = 0.02 + 0.98 * (1 - vh) ** 5
                spec = (nh ** 500 * 7.0 + nh ** 45 * 0.30) * fres * ocean * term * shadow
                r += spec * lr; g += spec * lg; bl += spec * lb
                # the water also mirrors the dim sky: a deep navy rather than brown-black
                sky = ocean * amb * (0.25 + 0.75 * fres * 8.0)
                r += 0.006 * sky; g += 0.020 * sky; bl += 0.055 * sky
                # clouds over everything
                cc = clouds(nx, ny, nz, Lx, Ly, Lz, P)
                # self-shadowing: thicker cloud toward the star -> darker; plus billowy brightness
                ct = clouds(sx / sn, sy / sn, sz / sn, Lx, Ly, Lz, P)
                bil = 0.78 + 0.22 * fbm(nx * 55.0, ny * 55.0, nz * 55.0, P, 3, 2.1, 0.5) * 2.0
                cd = smooth(-0.06, 0.06, mu) * (0.20 + 0.80 * max(mu, 0.0)) * (1.0 - 0.45 * max(0.0, ct - cc)) * bil
                ca = 0.035 * amb
                r = r * (1 - cc) + (0.80 * cd * lr + ca * 0.8) * cc; g = g * (1 - cc) + (0.84 * cd * lg + ca * 1.1) * cc; bl = bl * (1 - cc) + (0.90 * cd * lb + ca * 2.2) * cc
                # haze along the view through the air, strongest at the limb
                path = math.sqrt(max((1 + HS) ** 2 - h2, 0.0)) - math.sqrt(max(1.0 - h2, 0.0))
                la = smooth(-0.25, 0.35, (mx * Lx + my * Ly + mz * Lz) / mn)
                k = 0.022 * (path / HS) ** 1.7 * la
                r = r * (1 - 0.3 * k) + Ar * Sr * k; g = g * (1 - 0.3 * k) + Ag * Sg * k; bl = bl * (1 - 0.3 * k) + Ab * Sb * k
                a = 1.0
            else:
                # the halo just outside the limb
                path = 2 * math.sqrt(max((1 + HS) ** 2 - h2, 0.0)) + 0.0
                la = smooth(-0.25, 0.35, (mx * Lx + my * Ly + mz * Lz) / mn)
                k = 0.05 * (path / HS) ** 1.2 * la + 0.02 * math.exp(-(hd - 1) / (HS * 0.8)) * la
                r = Ar * Sr * k; g = Ag * Sg * k; bl = Ab * Sb * k
                a = 0.0
            img[j, i, 0] += r; img[j, i, 1] += g; img[j, i, 2] += bl
            alpha[j, i] = a

@njit(cache=True)
def render_small(img, alpha, RW, RH, TX, TY, Cx, Cy, Cz, rad, Lx, Ly, Lz, Sr, Sg, Sb, seed, P):
    """a neighbour planet: a small sphere, icy (snowball), lit by the star from its own direction"""
    cn = math.sqrt(Cx * Cx + Cy * Cy + Cz * Cz)
    # its pixel box
    px = (Cx / Cz / TX + 1) / 2 * RW; py = (1 - Cy / Cz / TY) / 2 * RH
    rp = math.asin(min(1.0, rad / cn)) / (2 * TY / RH) / 1.0 + 4
    for j in range(max(0, int(py - rp)), min(RH, int(py + rp) + 1)):
        for i in range(max(0, int(px - rp)), min(RW, int(px + rp) + 1)):
            if alpha[j, i] > 0.5: continue                  # behind TRAPPIST-1e
            acc_r = 0.0; acc_g = 0.0; acc_b = 0.0; cov = 0.0
            for sj in range(3):
                for si in range(3):
                    dx = ((i + (si + 0.5) / 3) / RW * 2 - 1) * TX; dy = (1 - (j + (sj + 0.5) / 3) / RH * 2) * TY; dz = 1.0
                    nn = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= nn; dy /= nn; dz /= nn
                    b = dx * Cx + dy * Cy + dz * Cz
                    h2 = cn * cn - b * b
                    if h2 >= rad * rad: continue
                    t = b - math.sqrt(rad * rad - h2)
                    nx, ny, nz = (dx * t - Cx) / rad, (dy * t - Cy) / rad, (dz * t - Cz) / rad
                    mu = nx * Lx + ny * Ly + nz * Lz
                    n = fbm(nx * 3.0 + seed, ny * 3.0, nz * 3.0, P, 5, 2.1, 0.5)
                    al = 0.62 + 0.18 * n
                    dif = smooth(-0.04, 0.06, mu) * max(mu, 0.0)
                    acc_r += al * dif * Sr; acc_g += al * dif * Sg * 0.97; acc_b += al * dif * Sb * 0.95
                    cov += 1.0
            if cov > 0:
                f = 1.0 / 9.0
                img[j, i, 0] = img[j, i, 0] * (1 - cov * f) + acc_r * f
                img[j, i, 1] = img[j, i, 1] * (1 - cov * f) + acc_g * f
                img[j, i, 2] = img[j, i, 2] * (1 - cov * f) + acc_b * f

def project(v):
    return ((v[0] / v[2] / TX + 1) / 2 * RW, (1 - v[1] / v[2] / TY) / 2 * RH)

def neighbours():
    """TRAPPIST-1f and g on their orbits (the plane through e and the star), placed where they show in the top of the
    frame; their size and phase follow from the geometry."""
    ae = SMA['e'] * AU_KM / UNIT
    S = C + L * ae                                                # the star
    w = np.cross(NRM, -L); w /= np.linalg.norm(w)
    out = []
    for name, ty in (('f', 0.33), ('g', 0.235)):
        a = SMA[name] * AU_KM / UNIT; rad = RAD[name] / RAD['e']
        best = None
        for psi in np.radians(np.arange(-179.5, 180, 0.25)):
            pos = S + a * (-L * math.cos(psi) + w * math.sin(psi))
            if pos[2] <= 0: continue
            x, y = project(pos)
            if not (0.08 * RW < x < 0.92 * RW): continue
            err = abs(y - ty * RH)
            score = err + 0.02 * np.linalg.norm(pos)
            if best is None or score < best[0]: best = (score, pos, x, y)
        _, pos, x, y = best
        Ls = S - pos; Ls /= np.linalg.norm(Ls)
        dist_km = np.linalg.norm(pos - C) * UNIT
        out.append((name, pos, rad, Ls, x, y, dist_km))
    return out

def background():
    """the Milky Way photo (dimmed, as a soft glow) and sharp stars"""
    from sky import vec
    Image.MAX_IMAGE_PIXELS = None
    photo = np.asarray(Image.open(os.path.join(TOOLS, 'data', 'sky', 'eso0932a.jpg')).convert('RGB'), np.float32) / 255
    q = 4; w_, h_ = RW // q, RH // q
    X, Y = np.meshgrid(((np.arange(w_) + 0.5) / w_ * 2 - 1) * TX, (1 - (np.arange(h_) + 0.5) / h_ * 2) * TY)
    d = np.stack([X, Y, np.ones_like(X)], -1); d /= np.linalg.norm(d, axis=-1, keepdims=True)
    # camera axes in galactic coordinates: looking at l=330°, b=-8°, the band slanting behind the planet
    def gal(l, b):
        l, b = math.radians(l), math.radians(b); return np.array([math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b)])
    Fw = gal(318, 14); up = np.array([0.0, 0.0, 1.0])
    roll = math.radians(-38)
    Rt = np.cross(up, Fw); Rt /= np.linalg.norm(Rt); Up = np.cross(Fw, Rt)
    Rt, Up = Rt * math.cos(roll) + Up * math.sin(roll), -Rt * math.sin(roll) + Up * math.cos(roll)
    G = d[..., :1] * Rt + d[..., 1:2] * Up + d[..., 2:3] * Fw
    b = np.degrees(np.arcsin(np.clip(G[..., 2], -1, 1))); l = np.degrees(np.arctan2(G[..., 1], G[..., 0]))
    ph, pw = photo.shape[:2]
    fx = ((0.5 - l / 360) * pw).astype(int) % pw; fy = np.clip(((90 - b) / 180 * ph).astype(int), 0, ph - 1)
    sm = photo[fy, fx]
    sm = np.asarray(Image.fromarray((np.clip(sm, 0, 1) * 255).astype(np.uint8)).resize((RW, RH), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    bg = (sm ** 1.6) * 0.38                                          # keep it a quiet glow: the stars are drawn sharp below
    lum = sm.mean(-1)
    # sharp stars: power-law brightness, denser where the Milky Way is
    r = np.random.default_rng(5)
    n = 9000
    xs = r.uniform(0, RW, n); ys = r.uniform(0, RH, n)
    keep = r.random(n) < 0.35 + 2.2 * lum[ys.astype(int), xs.astype(int)]
    xs, ys = xs[keep], ys[keep]
    br = np.clip(r.pareto(1.6, len(xs)) * 0.05 + 0.02, 0, 3.0)
    col = np.stack([np.ones(len(xs)), np.ones(len(xs)), np.ones(len(xs))], -1)
    t = r.normal(0, 0.18, len(xs)); col[:, 0] += t; col[:, 2] -= t
    stars = np.zeros((RH, RW, 3), np.float32)
    for x, y, b_, c in zip(xs, ys, br, col):
        s = 0.7 + 0.9 * min(b_, 1.5)
        x0, y0 = int(x), int(y)
        for yy in range(y0 - 3, y0 + 4):
            for xx in range(x0 - 3, x0 + 4):
                if 0 <= xx < RW and 0 <= yy < RH:
                    stars[yy, xx] += c * b_ * math.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * (s * 0.6) ** 2))
    return bg + stars

def tonemap(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14                  # ACES (Narkowicz)
    y = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    return np.where(y <= 0.0031308, 12.92 * y, 1.055 * np.power(y, 1 / 2.4) - 0.055)

def font(size, wght=600, file='Unbounded.ttf'):
    f = ImageFont.truetype(os.path.join(TOOLS, 'fonts', file), size)
    try: f.set_variation_by_axes([wght if a['name'] in (b'Weight', 'Weight') else a['default'] for a in f.get_variation_axes()])
    except Exception: pass
    return f

def main():
    sys.path.insert(0, TOOLS)
    img = background()
    alpha = np.zeros((RH, RW), np.float32)
    planet = np.zeros((RH, RW, 3), np.float64)
    EXP = 1.08
    render_planet(planet, alpha, RW, RH, TX, TY, C[0], C[1], C[2], L[0], L[1], L[2], STAR[0] * EXP, STAR[1] * EXP, STAR[2] * EXP,
                  ATM[0], ATM[1], ATM[2], PERM)
    a3 = alpha[..., None]
    img = img * (1 - a3) + planet.astype(np.float32)
    nb = neighbours()
    for name, pos, rad, Ls, x, y, dist in nb:
        render_small(img, alpha, RW, RH, TX, TY, pos[0], pos[1], pos[2], rad, Ls[0], Ls[1], Ls[2],
                     STAR[0] * EXP, STAR[1] * EXP, STAR[2] * EXP, 40.0 if name == 'f' else 90.0, PERM)
        ang = 2 * math.degrees(math.asin(rad / np.linalg.norm(pos)))
        print(f'{name}: {dist / 1e6:.2f} mln km, {ang:.2f}° across, at ({x / SS:.0f}, {y / SS:.0f})')
    # bloom: the glint and the bright ice glow softly
    hi = np.clip(img - 0.85, 0, None)
    bl = np.zeros_like(img)
    for rr, w in ((6, 0.5), (24, 0.35), (70, 0.25)):
        bl += np.asarray(Image.fromarray(np.clip(hi * 64, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rr)), np.float32) / 64 * w
    img = img + bl
    # a faint warm wash from the star just out of frame, up left (light scattered in the lens)
    yy, xx = np.mgrid[0:RH, 0:RW]
    wash = np.exp(-(((xx + 0.25 * RW) / (0.9 * RW)) ** 2 + ((yy + 0.15 * RH) / (0.55 * RH)) ** 2))[..., None]
    img = img + wash * STAR[None, None, :] * 0.05
    # vignette
    v = 1 - 0.25 * (((xx / RW - 0.5) * 1.6) ** 2 + ((yy / RH - 0.55) * 1.2) ** 2)
    img = img * v[..., None]
    out = (tonemap(img) * 255).astype(np.uint8)
    pic = Image.fromarray(out).resize((W, H), Image.LANCZOS)
    # grain
    g = np.random.default_rng(1).normal(0, 2.0, (H, W, 1))
    pic = Image.fromarray(np.clip(np.asarray(pic, np.float32) + g, 0, 255).astype(np.uint8))
    # titles, as in the videos
    d = ImageDraw.Draw(pic)
    d.text((W / 2, 64), 'Небозвід', font=font(30, 400, 'CormorantItalic.ttf'), anchor='mm', fill=(236, 200, 150))
    d.text((W / 2, 150), 'TRAPPIST-1e', font=font(52, 600), anchor='mm', fill=(255, 255, 255))
    d.text((W / 2, 200), 'найсхожіша на Землю — 40 світлових років від нас', font=font(17, 400, 'Commissioner.ttf'), anchor='mm', fill=(225, 228, 240))
    for name, pos, rad, Ls, x, y, dist in nb:
        x, y = x / SS, y / SS
        d.line((x + 14, y - 6, x + 40, y - 20), fill=(220, 220, 230, 160), width=1)
        d.text((x + 44, y - 21), 'TRAPPIST-1' + name, font=font(14, 500), anchor='lm', fill=(230, 232, 240))
    d.text((W / 2, H - 46), 'так може виглядати · художня реконструкція за даними NASA', font=font(15, 400, 'Commissioner.ttf'), anchor='mm', fill=(170, 176, 196))
    pic.save(OUT, quality=94)
    print('saved', OUT)

if __name__ == '__main__':
    main()
