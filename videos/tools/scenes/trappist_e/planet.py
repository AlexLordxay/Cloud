# «Знайомся: TRAPPIST-1e» — the renderer. The planet's surface (the same procedural "eyeball" world as in still.py:
# ice, an open ocean under the star, islands, clouds) is baked once into maps in the planet's own frame — it is tidally
# locked, so the light on every point never changes — and every frame then only looks the maps up along its rays and
# adds what depends on the view: the ocean's glint, the haze at the limb, the star, the neighbours and the sky.
#
# Planet frame (lengths in radii of TRAPPIST-1e): the planet at the origin, +X towards the star (the substellar point),
# +Z the orbit's normal, Y = Z x X. The noise is evaluated in still.py's coordinates, so the world looks the same.
#   python3 planet.py bake        -> work/trappist_e/maps/*.npy (~1 min on 4 cores)
import math, os, sys
import numpy as np
from numba import njit, prange
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, TOOLS]
import still as ST
from still import perlin, fbm, ridged, smooth, warp, clouds, PERM

WORK = os.path.join(TOOLS, 'work', 'trappist_e')
MAPS = os.path.join(WORK, 'maps')
TW, TH = 6144, 3072

# ---- the system ----
AU_KM, RE_KM, RSUN_KM = 1.495978707e8, 6371.0, 695700.0
UNIT = 0.920 * RE_KM
A_E = 0.02925 * AU_KM / UNIT                                   # 746.6: the star's distance
R_STAR = 0.1192 * RSUN_KM / UNIT                               # 14.15
PLANETS = {  # name: (radius in R_e, semi-major axis in AU, period in days)   (Agol et al. 2021)
    'b': (1.116 / 0.920, 0.01154, 1.5109), 'c': (1.097 / 0.920, 0.01580, 2.4218), 'd': (0.788 / 0.920, 0.02227, 4.0496),
    'e': (1.0, 0.02925, 6.0996), 'f': (1.045 / 0.920, 0.03849, 9.2067), 'g': (1.129 / 0.920, 0.04683, 12.3529),
    'h': (0.755 / 0.920, 0.06189, 18.7729)}
STAR = ST.STAR.copy()                                          # the star's light (partly eye-adapted), max channel 1
EXP = 1.08                                                     # exposure, as in the approved still

# still.py's frame -> planet frame
Xs = ST.L / np.linalg.norm(ST.L); Zs = ST.NRM / np.linalg.norm(ST.NRM); Ys = np.cross(Zs, Xs)
B_SP = np.stack([Xs, Ys, Zs])                                  # rows: planet axes in still coords; p = B_SP @ v
def s2p(v): return B_SP @ np.asarray(v, float)

# ---- the surface, with vegetation (for the "life" part) and a few more islands in the warm ocean ----
@njit(cache=True)
def surface2(px, py, pz, Lx, Ly, Lz, P):
    """-> albedo r,g,b; ocean; height; vegetation weight (where plants could grow: low land, no ice)"""
    qx, qy, qz = warp(px, py, pz, P)
    th = math.acos(min(1.0, max(-1.0, px * Lx + py * Ly + pz * Lz)))
    nl = fbm(qx * 2.3, qy * 2.3, qz * 2.3, P, 8, 2.05, 0.52)
    land = smooth(0.30, 0.34, nl)
    # an archipelago in the warm ocean (only under the star)
    na = fbm(qx * 5.5 + 3.0, qy * 5.5, qz * 5.5, P, 7, 2.1, 0.52)
    warm = 1.0 - smooth(math.radians(24.0), math.radians(34.0), th)
    land = max(land, smooth(0.255, 0.29, na) * warm)
    mount = ridged(qx * 7.0, qy * 7.0, qz * 7.0, P, 6, 2.1, 0.5)
    th0 = math.radians(35.0) + math.radians(10.0) * fbm(qx * 3.1, qy * 3.1, qz * 3.1, P, 5, 2.2, 0.55)
    floes = fbm(px * 46.0, py * 46.0, pz * 46.0, P, 4, 2.3, 0.5)
    k = (th - th0) / math.radians(6.0)
    ice = smooth(-0.15, 1.0, k + 0.55 * floes)
    ocean = (1.0 - ice) * (1.0 - land)
    big = fbm(qx * 5.0, qy * 5.0, qz * 5.0, P, 5, 2.0, 0.5)
    rid = ridged(qx * 26.0, qy * 26.0, qz * 26.0, P, 4, 2.2, 0.5)
    crack = smooth(0.80, 0.97, rid)
    bare = smooth(0.02, 0.22, -big) * smooth(-0.2, 0.25, fbm(qx * 11.0, qy * 11.0, qz * 11.0, P, 4, 2.1, 0.5))
    a_ice = (0.84 + 0.06 * big) * (1 - 0.42 * bare) - 0.12 * crack
    ir, ig, ib = a_ice * (1 - 0.30 * bare), a_ice * (1 - 0.05 * bare), a_ice * (1 + 0.35 * bare)
    var = fbm(qx * 18.0, qy * 18.0, qz * 18.0, P, 4, 2.0, 0.5)
    rr, rg, rb = 0.105 + 0.03 * var, 0.088 + 0.025 * var, 0.072 + 0.02 * var
    snow = smooth(0.45, 0.8, mount) * smooth(-0.6, 0.6, k)
    rr = rr + (0.75 - rr) * snow; rg = rg + (0.74 - rg) * snow; rb = rb + (0.74 - rb) * snow
    shelf = smooth(-2.5, 0.0, k)
    wr, wg, wb = 0.010 + 0.012 * shelf, 0.024 + 0.030 * shelf, 0.050 + 0.040 * shelf
    sr = ir * ice + wr * (1 - ice); sg = ig * ice + wg * (1 - ice); sb = ib * ice + wb * (1 - ice)
    ar = sr * (1 - land) + rr * land; ag = sg * (1 - land) + rg * land; ab = sb * (1 - land) + rb * land
    h = land * (0.35 + 0.65 * mount) + (1 - land) * ice * (0.08 * rid + 0.05 * big)
    # plants: on land, off the ice, below the snow, thinning on steep high ground; patchy
    pv = fbm(qx * 30.0, qy * 30.0, qz * 30.0, P, 4, 2.1, 0.5)
    veg = land * (1 - ice) * (1 - snow) * (1 - smooth(0.55, 0.85, mount)) * smooth(-0.45, -0.05, pv + 0.15 - 0.4 * (1 - warm))
    return ar, ag, ab, ocean, h, veg

@njit(cache=True, parallel=True)
def bake(alb, lig, oce, veg, cla, clr, TW, TH, Lx, Ly, Lz, Xx, Xy, Xz, Yx, Yy, Yz, Zx, Zy, Zz, Sr, Sg, Sb, P):
    for j in prange(TH):
        lat = math.pi / 2 - (j + 0.5) / TH * math.pi
        cl, sl = math.cos(lat), math.sin(lat)
        for i in range(TW):
            lon = (i + 0.5) / TW * 2 * math.pi - math.pi
            a, b, c = cl * math.cos(lon), cl * math.sin(lon), sl
            # the point in still.py's coordinates
            nx, ny, nz = a * Xx + b * Yx + c * Zx, a * Xy + b * Yy + c * Zy, a * Xz + b * Yz + c * Zz
            mu = nx * Lx + ny * Ly + nz * Lz
            if mu < -0.14: continue
            ar, ag, ab, ocean, h0, vg = surface2(nx, ny, nz, Lx, Ly, Lz, P)
            ex, ey, ez = -nz, 0.0, nx
            en = math.sqrt(ex * ex + ey * ey + ez * ez) + 1e-9; ex /= en; ey /= en; ez /= en
            fx, fy, fz = ny * ez - nz * ey, nz * ex - nx * ez, nx * ey - ny * ex
            eps = 0.0016
            h1 = surface2(nx + ex * eps, ny + ey * eps, nz + ez * eps, Lx, Ly, Lz, P)[4]
            h2 = surface2(nx + fx * eps, ny + fy * eps, nz + fz * eps, Lx, Ly, Lz, P)[4]
            gx, gy = (h1 - h0) / eps * 0.012, (h2 - h0) / eps * 0.012
            bx, by, bz = nx - gx * ex - gy * fx, ny - gx * ey - gy * fy, nz - gx * ez - gy * fz
            bn = math.sqrt(bx * bx + by * by + bz * bz)
            mub = (bx * Lx + by * Ly + bz * Lz) / bn
            term = smooth(-0.035, 0.05, mu)
            dif = term * max(mub, 0.0)
            tw = smooth(0.0, 0.22, mu)
            lr, lg, lb = Sr, Sg * (0.70 + 0.30 * tw), Sb * (0.50 + 0.50 * tw)
            tlx, tly, tlz = Lx - mu * nx, Ly - mu * ny, Lz - mu * nz
            sx, sy, sz = nx + tlx * 0.014, ny + tly * 0.014, nz + tlz * 0.014
            sn = math.sqrt(sx * sx + sy * sy + sz * sz)
            ct = clouds(sx / sn, sy / sn, sz / sn, Lx, Ly, Lz, P)
            shadow = 1.0 - 0.65 * ct
            amb = smooth(-0.10, 0.25, mu)
            alb[j, i, 0] = ar; alb[j, i, 1] = ag; alb[j, i, 2] = ab
            lig[j, i, 0] = dif * lr * shadow + 0.030 * amb
            lig[j, i, 1] = dif * lg * shadow + 0.045 * amb
            lig[j, i, 2] = dif * lb * shadow + 0.095 * amb
            oce[j, i] = ocean * shadow
            veg[j, i] = vg
            cc = clouds(nx, ny, nz, Lx, Ly, Lz, P)
            bil = 0.78 + 0.22 * fbm(nx * 55.0, ny * 55.0, nz * 55.0, P, 3, 2.1, 0.5) * 2.0
            cd = smooth(-0.06, 0.06, mu) * (0.20 + 0.80 * max(mu, 0.0)) * (1.0 - 0.45 * max(0.0, ct - cc)) * bil
            ca = 0.035 * amb
            cla[j, i] = cc
            clr[j, i, 0] = (0.80 * cd * lr + ca * 0.8) * cc
            clr[j, i, 1] = (0.84 * cd * lg + ca * 1.1) * cc
            clr[j, i, 2] = (0.90 * cd * lb + ca * 2.2) * cc

def do_bake():
    os.makedirs(MAPS, exist_ok=True)
    alb = np.zeros((TH, TW, 3), np.float32); lig = np.zeros((TH, TW, 3), np.float32)
    oce = np.zeros((TH, TW), np.float32); veg = np.zeros((TH, TW), np.float32)
    cla = np.zeros((TH, TW), np.float32); clr = np.zeros((TH, TW, 3), np.float32)
    L = Xs
    bake(alb, lig, oce, veg, cla, clr, TW, TH, L[0], L[1], L[2], Xs[0], Xs[1], Xs[2], Ys[0], Ys[1], Ys[2], Zs[0], Zs[1], Zs[2],
         STAR[0] * EXP, STAR[1] * EXP, STAR[2] * EXP, PERM)
    for n, a in (('alb', alb), ('lig', lig), ('oce', oce), ('veg', veg), ('cla', cla), ('clr', clr)):
        np.save(os.path.join(MAPS, n + '.npy'), a.astype(np.float16))
    print('baked', TW, TH)

_M = {}
def maps():
    if not _M:
        for n in ('alb', 'lig', 'oce', 'veg', 'cla', 'clr'):
            _M[n] = np.load(os.path.join(MAPS, n + '.npy'), mmap_mode='r')
    return _M

if __name__ == '__main__' and sys.argv[1:] == ['bake']:
    import time; t = time.time(); do_bake(); print(round(time.time() - t, 1), 's')
