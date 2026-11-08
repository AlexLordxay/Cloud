# «Знайомся: Уран» — Verona Rupes on Miranda: a scarp ~20 km high (NASA's estimate; the tallest known cliff in the Solar
# System), drawn on the CPU (numba): a heightfield baked on two grids (a 1 km patch at 0.5 m round the camera, and
# 90 km at 22 m for the rest), ray-marched, with the moon's curvature (radius 236 km: the horizon is close), grooves and
# ridges on the plateau (the "coronae"), gullies down the face, craters; lit by the low Sun and by Uranus' cyan light.
# The sky is uranus.py's: Uranus 22° across, its rings almost edge-on, the stars.
#
#   from miranda import cliff_frame
#   local frame (km): x along the edge, y across it (the drop is at y > 0), z up; the edge's top at z = 0.
import math, os, sys
import numpy as np
from numba import njit, prange
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import uranus as U
from uranus import TR, RW, RH, W, H, fbm, smooth, PERM

HC = 20.0            # km, the drop
RUN = 6.5            # km, the face's horizontal run (~72°)
RM = 235.8           # km, Miranda's radius
A_MIR = 129900.0     # km, its orbit
# the coarse grid (km)
CX0, CY0, CN, CH = -40.0, -40.0, 4096, 80.0 / 4096
# the mid grid along the fall (km)
MX0, MY0, MN, MH = -4.0, -1.5, 3072, 9.0 / 3072
# the fine grid at the rim, round the start (km)
FX0, FY0, FN, FH = -0.5, -0.6, 2048, 1.0 / 2048

@njit(cache=True)
def crater(x, y, cs, seed, P):
    """a field of craters (bowls with raised rims) in cells of size cs"""
    i0 = math.floor(x / cs); j0 = math.floor(y / cs)
    h = 0.0
    for dj in range(-1, 2):
        for di in range(-1, 2):
            i = i0 + di; j = j0 + dj
            hh = math.sin(i * 127.1 + j * 311.7 + seed) * 43758.5453
            u = hh - math.floor(hh)
            if u > 0.45: continue
            hh2 = math.sin(i * 269.5 + j * 183.3 + seed * 1.7) * 43758.5453; v = hh2 - math.floor(hh2)
            hh3 = math.sin(i * 419.2 + j * 371.9 + seed * 2.3) * 43758.5453; w = hh3 - math.floor(hh3)
            cx = (i + 0.2 + 0.6 * v) * cs; cy = (j + 0.2 + 0.6 * w) * cs
            r = cs * (0.12 + 0.30 * u)
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
            if d < 1.0: h += r * 0.22 * (d * d - 1.0) + r * 0.06
            elif d < 2.0: h += r * 0.06 * (2.0 - d) ** 2
    return h

@njit(cache=True)
def edge_y(x, P):
    return 0.45 * fbm(x * 0.22, 0.3, 1.1, P, 4, 2.1, 0.5) + 0.12 * fbm(x * 1.4, 0.7, 2.3, P, 3, 2.1, 0.5)

@njit(cache=True)
def height(x, y, P, fine):
    """terrain height (km) at (x, y), without the curvature"""
    e = edge_y(x, P)
    s = (y - e) / RUN
    # the face: steep from the very edge (~72° on average), uneven: buttresses, ledges of harder layers, gullies
    g = fbm(x * 0.8, s * 1.2, 4.4, P, 4, 2.2, 0.55)
    sc = min(1.0, max(0.0, s + 0.05 * g))
    prof = 1.0 - (1.0 - sc) ** 1.12
    z = -HC * prof
    fk = smooth(0.0, 0.03, s) - smooth(0.92, 1.0, s)
    # in and out of the face, as horizontal offsets turned into height (the face is steep: dz = slope * dy)
    jut = 0.20 * fbm(x * 0.55, z * 0.40, 2.2, P, 5, 2.1, 0.55) + 0.07 * fbm(x * 3.0, z * 2.6, 6.1, P, 4, 2.1, 0.5)
    gully = 0.08 * fbm(x * 2.0, z * 0.9, 7.7, P, 3, 2.0, 0.5) * (0.5 + fbm(x * 0.2, z * 0.3, 1.3, P, 2, 2.0, 0.5))
    ledge = 0.05 * math.sin(z * 1.7 + 1.5 * fbm(x * 0.3, z * 0.1, 0.0, P, 2, 2.0, 0.5))
    z += (jut + gully + ledge) * (HC / RUN) * fk
    # the plateau: grooves and ridges parallel to the edge (Miranda's coronae), craters
    if s < 0.2:
        k = 1.0 - smooth(0.0, 0.2, s)
        rid = 0.10 * math.sin((y - e) * 2.4 + 2.0 * fbm(x * 0.12, y * 0.12, 0.5, P, 3, 2.0, 0.5)) \
            + 0.035 * math.sin((y - e) * 7.1 + x * 0.15)
        z += k * (rid * smooth(-12.0, -1.5, y - e) + 0.12 * fbm(x * 0.25, y * 0.25, 3.3, P, 4, 2.0, 0.5) * smooth(-3.0, -0.3, y - e)
                  + crater(x, y, 2.5, 1.0, P) * smooth(-2.0, -0.6, y - e) + 0.6 * crater(x, y, 0.7, 2.0, P) * smooth(-1.0, -0.25, y - e))
    # the plain below: rolling, cratered
    if s > 0.8:
        k = smooth(0.8, 1.0, s)
        z += k * (0.5 * fbm(x * 0.12, y * 0.12, 9.1, P, 4, 2.0, 0.5) + crater(x, y, 4.0, 3.0, P))
    if fine:
        # metres-scale relief near the camera: regolith, small craters, stones
        z += 0.0015 * fbm(x * 900.0, y * 900.0, 1.3, P, 3, 2.0, 0.5) + 0.004 * fbm(x * 180.0, y * 180.0, 2.7, P, 3, 2.0, 0.5)
        z += crater(x, y, 0.06, 5.0, P) * 0.6 + crater(x, y, 0.015, 6.0, P) * 0.5
    return z

@njit(cache=True, parallel=True)
def bake(G, x0, y0, h, fine, P):
    n = G.shape[0]
    for j in prange(n):
        for i in range(n):
            G[j, i] = height(x0 + (i + 0.5) * h, y0 + (j + 0.5) * h, P, fine)

@njit(cache=True, inline='always')
def grid(G, x0, y0, h, x, y):
    n = G.shape[0]
    fx = (x - x0) / h - 0.5; fy = (y - y0) / h - 0.5
    i = int(math.floor(fx)); j = int(math.floor(fy))
    if i < 0 or j < 0 or i >= n - 1 or j >= n - 1: return 1e9
    ax = fx - i; ay = fy - j
    return (G[j, i] * (1 - ax) + G[j, i + 1] * ax) * (1 - ay) + (G[j + 1, i] * (1 - ax) + G[j + 1, i + 1] * ax) * ay

@njit(cache=True, inline='always')
def hgt(GC, GM, GF, x, y):
    c = grid(GC, CX0, CY0, CH, x, y)
    m = grid(GM, MX0, MY0, MH, x, y)
    if m < 1e8:
        ex = min(x - MX0, MX0 + MN * MH - x, y - MY0, MY0 + MN * MH - y)
        k = min(1.0, ex / 0.4)
        c = m * k + c * (1 - k) if c < 1e8 else m
    f = grid(GF, FX0, FY0, FH, x, y)
    if f < 1e8:
        ex = min(x - FX0, FX0 + FN * FH - x, y - FY0, FY0 + FN * FH - y)
        k = min(1.0, ex / 0.08)
        c = f * k + c * (1 - k)
    if c < 1e8: return c
    return -HC * 0.5

@njit(cache=True, inline='always')
def curv(x, y):
    return -(x * x + y * y) / (2 * RM)

@njit(cache=True, parallel=True)
def render(img, mask, RW, RH, ox, oy, oz, rx, ry, rz, ux, uy, uz, fx, fy, fz, TX, TY, GC, GM, GF, Sx, Sy, Sz, sun,
           Ux, Uy, Uz, uni, P, rock):
    pix = 2.0 * TY / RH
    for j in prange(RH):
        for i in range(RW):
            px_ = ((i + 0.5) / RW * 2 - 1) * TX; py_ = (1 - (j + 0.5) / RH * 2) * TY
            dx = fx + px_ * rx + py_ * ux; dy = fy + px_ * ry + py_ * uy; dz = fz + px_ * rz + py_ * uz
            nn = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= nn; dy /= nn; dz /= nn
            t = 0.0002; hit = False
            for it in range(700):
                x = ox + dx * t; y = oy + dy * t; z = oz + dz * t
                hh = hgt(GC, GM, GF, x, y) + curv(x, y)
                d = z - hh
                if d < 0.00025 + t * pix * 0.3:
                    hit = True; break
                t += max(d * 0.45, t * pix * 0.6, 0.00015)
                if t > 160.0 or z < -HC - 30: break
            # the falling rock (km): x, y, z, r
            if rock[3] > 0:
                cx_, cy_, cz_ = rock[0] - ox, rock[1] - oy, rock[2] - oz
                b = cx_ * dx + cy_ * dy + cz_ * dz
                h2 = cx_ * cx_ + cy_ * cy_ + cz_ * cz_ - b * b
                if b > 0 and h2 < rock[3] * rock[3]:
                    tr = b - math.sqrt(rock[3] * rock[3] - h2)
                    if (not hit) or tr < t:
                        nx = (dx * tr - cx_) / rock[3]; ny = (dy * tr - cy_) / rock[3]; nz = (dz * tr - cz_) / rock[3]
                        nx += 0.5 * fbm(nx * 3 + rock[4], ny * 3, nz * 3, P, 4, 2.0, 0.5); ny += 0.5 * fbm(nx * 3, ny * 3 + rock[4], nz * 3, P, 4, 2.0, 0.5)
                        nz += 0.5 * fbm(nx * 3, ny * 3, nz * 3 + rock[4], P, 4, 2.0, 0.5)
                        nl = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nl; ny /= nl; nz /= nl
                        l_ = max(nx * Sx + ny * Sy + nz * Sz, 0.0); lu_ = max(nx * Ux + ny * Uy + nz * Uz, 0.0)
                        img[j, i, 0] = 0.28 * (sun * l_ * 1.6 + uni * lu_ * 0.55); img[j, i, 1] = 0.28 * (sun * l_ * 1.56 + uni * lu_ * 0.9)
                        img[j, i, 2] = 0.28 * (sun * l_ * 1.52 + uni * lu_ * 1.0); mask[j, i] = 1.0
                        continue
            if not hit:
                continue
            x = ox + dx * t; y = oy + dy * t
            # normal from the heightfield (finite differences at the pixel's scale)
            e = max(t * pix * 1.5, 0.0003)
            hx = (hgt(GC, GM, GF, x + e, y) - hgt(GC, GM, GF, x - e, y)) / (2 * e) - x / RM
            hy = (hgt(GC, GM, GF, x, y + e) - hgt(GC, GM, GF, x, y - e)) / (2 * e) - y / RM
            nx, ny, nz = -hx, -hy, 1.0
            nl = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nl; ny /= nl; nz /= nl
            # albedo: grey ice, the scarp face brighter (fresh), dark streaks, light bands of layers
            zz = hgt(GC, GM, GF, x, y)
            face = smooth(0.35, 0.75, 1.0 - nz)
            al = 0.30 * (1.0 + 0.25 * fbm(x * 0.6, y * 0.6, 4.0, P, 4, 2.0, 0.5) + 0.12 * fbm(x * 40, y * 40, 5.0, P, 3, 2.0, 0.5))
            al *= 1.0 + face * (0.35 + 0.25 * math.sin(zz * 3.1 + 2.0 * fbm(x * 0.5, zz * 0.3, 1.0, P, 2, 2.0, 0.5)))
            # shadow towards the Sun: march the heightfield
            lit = max(nx * Sx + ny * Sy + nz * Sz, 0.0)
            if lit > 0:
                ts = 0.0004
                for it in range(160):
                    qx = x + Sx * ts; qy = y + Sy * ts; qz = hgt(GC, GM, GF, x, y) + curv(x, y) + Sz * ts + 0.0002
                    dd = qz - (hgt(GC, GM, GF, qx, qy) + curv(qx, qy))
                    if dd < 0: lit = 0.0; break
                    ts += max(dd * 0.6, ts * 0.02, 0.0004)
                    if ts > 60.0: break
            # Uranus' light (a big cyan lamp in the sky) and a little bounce from the bright ground
            lu = max(nx * Ux + ny * Uy + nz * Uz, 0.0)
            amb = 0.06 * (0.6 + 0.4 * nz)
            # Lommel-Seeliger-ish (icy, porous): flatter than Lambert
            mu = max(-(nx * dx + ny * dy + nz * dz), 0.05)
            ls = lit / (lit + mu) * 2.0 if lit > 0 else 0.0
            img[j, i, 0] = al * (sun * ls * 1.00 + uni * lu * 0.55 + amb * 0.6)
            img[j, i, 1] = al * (sun * ls * 0.98 + uni * lu * 0.90 + amb * 0.9)
            img[j, i, 2] = al * (sun * ls * 0.95 + uni * lu * 1.00 + amb * 1.0)
            mask[j, i] = 1.0

_grids = {}
def grids():
    if not _grids:
        p = os.path.join(U.WORK, 'miranda_grids.npz')
        if os.path.exists(p):
            z = np.load(p); _grids.update(c=z['c'], m=z['m'], f=z['f'])
        else:
            GC = np.zeros((CN, CN), np.float32); bake(GC, CX0, CY0, CH, False, PERM)
            GM = np.zeros((MN, MN), np.float32); bake(GM, MX0, MY0, MH, False, PERM)
            GF = np.zeros((FN, FN), np.float32); bake(GF, FX0, FY0, FH, True, PERM)
            np.savez(p, c=GC, m=GM, f=GF); _grids.update(c=GC, m=GM, f=GF)
    return _grids['c'], _grids['m'], _grids['f']

# ---- the sky's geometry: Uranus 28° up straight ahead (+y, over the drop), the Sun 90° from it, low on the right
UR_LOC = np.array([0.18, -0.72, 0.67]); UR_LOC /= np.linalg.norm(UR_LOC)    # above the plateau, seen from the abyss
def _sun_loc():
    # a unit vector 90° from UR_LOC, 14° above the horizon, to the right (+x)
    el = math.radians(11)
    best = None
    for az in np.linspace(-math.pi, math.pi, 3601):
        v = np.array([math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)])
        if v[0] > 0 and (best is None or abs(v @ UR_LOC) < abs(best @ UR_LOC)): best = v
    return best
SUN_LOC = _sun_loc()
PHI_M = math.radians(90.0)                          # Miranda's place on its orbit (Uranus frame)
P_M = A_MIR * np.array([math.cos(PHI_M), math.sin(PHI_M), 0.0])
UR_U = -P_M / np.linalg.norm(P_M)
def _rot():
    """local -> Uranus' frame: UR_LOC -> UR_U, SUN_LOC -> S26 (both 90° apart)"""
    S = U.sun_dir_2026()
    a1, b1 = UR_LOC, SUN_LOC - UR_LOC * (SUN_LOC @ UR_LOC); b1 /= np.linalg.norm(b1)
    a2, b2 = UR_U, S - UR_U * (S @ UR_U); b2 /= np.linalg.norm(b2)
    A = np.stack([a1, b1, np.cross(a1, b1)], 1); B = np.stack([a2, b2, np.cross(a2, b2)], 1)
    return B @ A.T
ROT = _rot()

def cliff_frame(cam, target, up=(0, 0, 1), fovy=60.0, expo=0.52, raw=False, bloom=1.0, rock=None):
    cam = np.asarray(cam, float)
    TY = math.tan(math.radians(fovy) / 2); TX = TY * RW / RH
    r, u, f = TR.cam_basis(cam, target, up)
    GC, GM, GF = grids()
    RK = np.array(rock if rock is not None else [0, 0, 0, 0, 0], np.float64)
    img = np.zeros((RH, RW, 3), np.float32); mask = np.zeros((RH, RW), np.float32)
    ang = math.asin(U.RE / A_MIR)
    uni = 2 * math.pi * (1 - math.cos(ang)) / math.pi * 0.5 * 0.5
    render(img, mask, RW, RH, *cam, *r, *u, *f, TX, TY, GC, GM, GF, *SUN_LOC, 1.0, *UR_LOC, uni, PERM, RK)
    img *= expo
    # the sky: Uranus, its rings, the stars (in Uranus' frame)
    rp, up_, fp = ROT @ r, ROT @ u, ROT @ f
    bg = np.zeros((RH, RW, 3), np.float32); bm = np.zeros((RH, RW), np.float32)
    T = U.textures()
    U.render(bg, bm, RW, RH, *P_M, *rp, *up_, *fp, TX, TY, *U.sun_dir_2026(), 0.0, 0.3, PERM, U.RINGS, U.DUST,
             14.0, 0.0, 1.0, 1.0, 1.0, True, np.zeros((0, 7)), T, T.shape[2], T.shape[1], 1.0)
    sky = TR.background(rp, up_, fp, TX, TY, np.maximum(bm, mask), 0.8, 0.22, TR.GAL)
    out = img + (bg * 1.1 + sky * (1 - bm[..., None])) * (1 - mask[..., None])
    if raw: return out
    return TR.finish(out, bloom)

def ground(x, y):
    GC, GM, GF = grids()
    return float(hgt(GC, GM, GF, x, y) + curv(x, y))

if __name__ == '__main__' and sys.argv[1:2] == ['test']:
    import time
    t0 = time.time(); grids(); print('grids', time.time() - t0)
    print('sun', SUN_LOC.round(3), 'uranus', UR_LOC.round(3))
    cliff_frame((1.5, 15.0, -7.0), (0.0, 0.0, -8.0), fovy=64).save(os.path.join(U.WORK, 'mir_a.jpg')); print('a', time.time() - t0)
    e = edge_y(0.0, PERM); z0 = ground(0.0, e - 0.004)
    yw = e + 0.3 / (HC / RUN) + 0.03           # just off the face, 300 m down
    rk = [0.0, yw, z0 - 0.3, 0.002, 3.0]
    cliff_frame((0.06, yw + 0.06, z0 - 0.27), (0.0, yw - 0.02, z0 - 0.33), fovy=60, rock=rk).save(os.path.join(U.WORK, 'mir_b.jpg')); print('b', time.time() - t0)
