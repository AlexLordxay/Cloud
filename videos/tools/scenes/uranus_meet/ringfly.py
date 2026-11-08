# «Знайомся: Уран» — the flight along the epsilon ring: a sheet of dark boulders (centimetres to a house), dirty ice
# darkened by radiation (albedo ~3 %), packed in clumps ("self-gravity wakes") a few metres thick, the band ~60 km wide
# with sharp edges and empty space beyond; Uranus fills a third of the sky beside it (30° in radius from 51 000 km).
# Lit by the tiny Sun high above (74° over the ring plane in 2026) and by the cyan light of the planet from the side.
# Near the camera every boulder is a sphere with a lumpy surface, ray-traced through a hashed grid, with shadows;
# farther the sheet is drawn as a whole (its optical depth and mean brightness). The planet, the other rings, the stars
# and the Sun come from uranus.py, with the epsilon ring left out.
#
#   from ringfly import ring_frame; ring_frame(cam_local, look_local, up_local, ...)
#   local frame (metres): X along the ring (prograde), Y outward (away from Uranus), Z north; origin on the ring's middle.
import math, os, sys
import numpy as np
from numba import njit, prange

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import uranus as U
from uranus import TR, RW, RH, fbm, smooth, PERM

A_RING = 51149.0                 # km, the ring's radius at the chosen longitude (taken circular here)
PHI = math.radians(105.0)        # the longitude of the camera's spot on the ring (in Uranus' frame)
HALF_W = 31.0                    # km, half the width of the epsilon ring there
SLAB = 5.0                       # m, half the thickness of the boulder layer
CELL = 2.1                       # m, the grid of the small boulders
BIG = 13.0                       # m, the grid of the big ones
NEAR = 520.0                     # m, boulders drawn one by one up to here
ALB = 0.035

def local_axes():
    er = np.array([math.cos(PHI), math.sin(PHI), 0.0])          # outward
    et = np.array([-math.sin(PHI), math.cos(PHI), 0.0])         # prograde
    ez = np.array([0.0, 0.0, 1.0])
    return et, er, ez

def to_planet(p_local_m):
    """a local point (m) -> Uranus' frame (km)"""
    et, er, ez = local_axes()
    p = np.asarray(p_local_m, float) / 1000.0
    return A_RING * np.array([math.cos(PHI), math.sin(PHI), 0.0]) + p[0] * et + p[1] * er + p[2] * ez

def dir_to_planet(v):
    et, er, ez = local_axes(); v = np.asarray(v, float)
    return v[0] * et + v[1] * er + v[2] * ez

def dir_to_local(v):
    et, er, ez = local_axes(); v = np.asarray(v, float)
    return np.array([v @ et, v @ er, v @ ez])

@njit(cache=True, inline='always')
def h3(i, j, k, s):
    h = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791) ^ (s * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xffffff) / 16777216.0

@njit(cache=True)
def wake(x, y, P):
    """the clumping of the sheet: streaks ~25° from the orbital direction, tens of metres apart"""
    c, s = 0.906, 0.423
    u = x * c + y * s; v = -x * s + y * c
    w = 0.5 + 0.5 * math.sin(v * 0.11 + 2.2 * fbm(u * 0.004, v * 0.02, 0.0, P, 3, 2.0, 0.5))
    w = w ** 1.6
    n = fbm(x * 0.013, y * 0.013, 3.0, P, 4, 2.0, 0.55)
    return min(1.0, max(0.0, 0.25 + 0.85 * w + 0.35 * n))

@njit(cache=True, inline='always')
def edge_k(y):
    """the band: sharp edges at ±HALF_W km (a little ragged)"""
    a = abs(y) / 1000.0
    return 1.0 - smooth(HALF_W - 0.15, HALF_W, a)

@njit(cache=True)
def cell_ball(i, j, k, cs, big, P):
    """the boulder of a cell (or none): centre and radius"""
    if big == 0 and abs((k + 0.5) * cs) > SLAB: return 0.0, 0.0, 0.0, -1.0
    occ = h3(i, j, k, 7 + big)
    cx = (i + 0.5) * cs; cy = (j + 0.5) * cs
    dens = wake(cx, cy, P) * edge_k(cy)
    if big == 1: dens *= 0.55
    if occ > dens * (0.80 if big == 0 else 0.55): return 0.0, 0.0, 0.0, -1.0
    u = h3(i, j, k, 11 + big)
    if big == 0: r = 0.16 + 0.80 * u ** 2.0
    else: r = 1.2 + 3.6 * u ** 2.2
    m = cs * 0.5 - r
    bx = cx + (h3(i, j, k, 3) - 0.5) * 2 * max(m, 0.0)
    by = cy + (h3(i, j, k, 5) - 0.5) * 2 * max(m, 0.0)
    zr = SLAB - r if big == 0 else max(0.0, SLAB - r * 0.6)
    bz = (k + 0.5) * cs + (h3(i, j, k, 9) - 0.5) * 2 * max(min(m, zr), 0.0) if big == 0 else (h3(i, j, k, 9) - 0.5) * 2 * zr
    return bx, by, bz, r

@njit(cache=True)
def trace(ox, oy, oz, dx, dy, dz, tmax, P, want_n):
    """the nearest boulder along the ray: t, normal, the boulder's seed (or t = -1)"""
    best = 1e30; bnx = 0.0; bny = 0.0; bnz = 0.0; seed = 0.0
    # the slab's span along the ray
    if abs(dz) < 1e-9:
        if abs(oz) > SLAB: return -1.0, 0.0, 0.0, 0.0, 0.0
        t0 = 0.0; t1 = tmax
    else:
        ta = (SLAB - oz) / dz; tb = (-SLAB - oz) / dz
        t0 = max(0.0, min(ta, tb)); t1 = min(tmax, max(ta, tb))
    if t1 <= t0: return -1.0, 0.0, 0.0, 0.0, 0.0
    for big in range(2):
        cs = CELL if big == 0 else BIG
        # 3D DDA through the cells (the big grid is one layer thick in z)
        t = t0 + 1e-4
        px = ox + dx * t; py = oy + dy * t; pz = oz + dz * t
        i = int(math.floor(px / cs)); j = int(math.floor(py / cs))
        k = int(math.floor(pz / cs)) if big == 0 else 0
        sx = 1 if dx > 0 else -1; sy = 1 if dy > 0 else -1; sz = 1 if dz > 0 else -1
        tdx = abs(cs / dx) if abs(dx) > 1e-12 else 1e30
        tdy = abs(cs / dy) if abs(dy) > 1e-12 else 1e30
        tdz = abs(cs / dz) if abs(dz) > 1e-12 else 1e30
        nxb = ((i + (1 if sx > 0 else 0)) * cs - px) / dx if abs(dx) > 1e-12 else 1e30
        nyb = ((j + (1 if sy > 0 else 0)) * cs - py) / dy if abs(dy) > 1e-12 else 1e30
        nzb = ((k + (1 if sz > 0 else 0)) * cs - pz) / dz if (abs(dz) > 1e-12 and big == 0) else 1e30
        tn = t
        for step in range(900):
            if tn > t1 or tn > best: break
            # test this cell and its neighbours across (boulders may poke out of their cell a little: they don't, r<cs/2)
            bx0, by0, bz0, r0 = cell_ball(i, j, k, cs, big, P)
            if r0 > 0:
                for part in range(3):
                    if part == 0:
                        bx, by, bz, r = bx0, by0, bz0, r0
                    else:
                        # lumps stuck to it: smaller spheres on its surface
                        ax_ = h3(i, j, k, 31 + part) * 2 - 1; ay_ = h3(i, j, k, 37 + part) * 2 - 1; az_ = h3(i, j, k, 41 + part) * 2 - 1
                        al_ = math.sqrt(ax_ * ax_ + ay_ * ay_ + az_ * az_) + 1e-6
                        r = r0 * (0.45 + 0.3 * h3(i, j, k, 43 + part))
                        bx = bx0 + ax_ / al_ * (r0 - r * 0.35); by = by0 + ay_ / al_ * (r0 - r * 0.35); bz = bz0 + az_ / al_ * (r0 - r * 0.35) * 0.6
                    cx = bx - ox; cy = by - oy; cz = bz - oz
                    b = cx * dx + cy * dy + cz * dz
                    h2 = cx * cx + cy * cy + cz * cz - b * b
                    if h2 < r * r:
                        th = b - math.sqrt(r * r - h2)
                        if th > 1e-3 and th < best:
                            best = th
                            if want_n:
                                bnx = (dx * th - cx) / r; bny = (dy * th - cy) / r; bnz = (dz * th - cz) / r
                            seed = h3(i, j, k, 21 + big)
            # step
            m = min(nxb, nyb, nzb)
            if m == nxb: i += sx; nxb += tdx
            elif m == nyb: j += sy; nyb += tdy
            else:
                k += sz; nzb += tdz
            tn = t + m
        # the loop measured m from the entry point t; keep going
    if best < 1e29: return best, bnx, bny, bnz, seed
    return -1.0, 0.0, 0.0, 0.0, 0.0

@njit(cache=True, parallel=True)
def render_ring(img, alp, RW, RH, ox, oy, oz, rx, ry, rz, ux, uy, uz, fx, fy, fz, TX, TY, Sx, Sy, Sz, sun,
                Ux, Uy, Uz, uni, P, near_k, far_k, dust_k):
    """the ring layer: premultiplied colour + opacity. (Sx..): to the Sun; (Ux..): to Uranus' centre; uni: its light"""
    for j in prange(RH):
        for i in range(RW):
            px_ = ((i + 0.5) / RW * 2 - 1) * TX; py_ = (1 - (j + 0.5) / RH * 2) * TY
            dx = fx + px_ * rx + py_ * ux; dy = fy + px_ * ry + py_ * uy; dz = fz + px_ * rz + py_ * uz
            nn = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= nn; dy /= nn; dz /= nn
            cr = 0.0; cg = 0.0; cb = 0.0; a = 0.0
            t, nx, ny, nz, sd = trace(ox, oy, oz, dx, dy, dz, NEAR * near_k, P, True)
            if t > 0:
                hx, hy, hz = ox + dx * t, oy + dy * t, oz + dz * t
                # a lumpy, cratered surface: bend the normal with noise
                q = 1.6 + sd * 2.5
                b1 = fbm(nx * q * 2 + sd * 91.0, ny * q * 2, nz * q * 2, P, 4, 2.1, 0.5)
                b2 = fbm(nx * q * 9.0, ny * q * 9.0 + sd * 7.0, nz * q * 9.0, P, 3, 2.1, 0.5)
                nx2 = nx + 0.75 * fbm(nx * q + 3.0 + sd * 13, ny * q, nz * q, P, 4, 2.2, 0.55)
                ny2 = ny + 0.75 * fbm(nx * q, ny * q + 5.0 + sd * 17, nz * q, P, 4, 2.2, 0.55)
                nz2 = nz + 0.75 * fbm(nx * q, ny * q, nz * q + 9.0 + sd * 19, P, 4, 2.2, 0.55)
                nl = math.sqrt(nx2 * nx2 + ny2 * ny2 + nz2 * nz2); nx2 /= nl; ny2 /= nl; nz2 /= nl
                al = ALB * (0.75 + 0.5 * sd) * (1.0 + 0.35 * b1 + 0.2 * b2)
                if sd > 0.93: al *= 2.2                                  # a fresher, icier fragment now and then
                mu0 = nx2 * Sx + ny2 * Sy + nz2 * Sz
                lit = 0.0
                if mu0 > 0:
                    st, _a, _b, _c, _d = trace(hx + nx * 0.02, hy + ny * 0.02, hz + nz * 0.02, Sx, Sy, Sz, 60.0, P, False)
                    if st < 0: lit = mu0
                # the planet's light from the side, and a little from the sheet below (multiple scattering)
                mu_u = max(nx2 * Ux + ny2 * Uy + nz2 * Uz, 0.0)
                v = -(nx2 * dx + ny2 * dy + nz2 * dz)
                rough = 0.75 + 0.25 * max(v, 0.0)
                # frost glints: tiny crystals catching the Sun
                hx_ = Sx - dx; hy_ = Sy - dy; hz_ = Sz - dz
                hl_ = math.sqrt(hx_ * hx_ + hy_ * hy_ + hz_ * hz_) + 1e-9
                nh = max(0.0, (nx2 * hx_ + ny2 * hy_ + nz2 * hz_) / hl_)
                gl = lit * (nh ** 300) * 0.6 * (1.0 if b2 > 0.25 else 0.0)
                cr = al * (lit * sun * 1.00 + mu_u * uni * 0.62) * rough + gl
                cg = al * (lit * sun * 0.97 + mu_u * uni * 0.92) * rough + gl
                cb = al * (lit * sun * 0.92 + mu_u * uni * 1.00) * rough + gl
                # a little air-like depth: nothing, it is vacuum — but far boulders get finer than a pixel: fade
                # into the sheet's mean
                fk = smooth(NEAR * near_k * 0.55, NEAR * near_k, t)
                a = 1.0
                if fk > 0:
                    cr = cr * (1 - fk); cg = cg * (1 - fk); cb = cb * (1 - fk); a = 1 - fk
                    # the far sheet takes the rest (below)
                if fk <= 0:
                    img[j, i, 0] = cr; img[j, i, 1] = cg; img[j, i, 2] = cb; alp[j, i] = a
                    continue
            # ---- the far sheet: crossing the mid-plane
            if abs(dz) > 1e-7 and far_k > 0:
                tp = -oz / dz
                nk = smooth(NEAR * near_k * 0.55, NEAR * near_k, tp)
                if tp > 0 and nk > 0:
                    qx = ox + dx * tp; qy = oy + dy * tp
                    mu = abs(dz)
                    ek = edge_k(qy)
                    if ek > 0:
                        w = wake(qx, qy, P)
                        tau = 1.6 * (0.35 + 0.95 * w) * ek
                        # far away a pixel covers many streaks: blur them out
                        dist = tp
                        fade = smooth(20000.0, 200000.0, dist)
                        tau = tau * (1 - fade) + 1.6 * 0.80 * ek * fade
                        op = (1.0 - math.exp(-tau / max(mu, 0.004))) * nk
                        mu0 = abs(Sz)
                        same = (oz > 0) == (Sz > 0)
                        lit = ALB * 0.9 * (mu0 if same else 0.12 * mu0) * 0.45
                        n = fbm(qx * 0.03, qy * 0.03, 7.0, P, 3, 2.0, 0.5)
                        lit *= (1.0 + 0.25 * n * (1 - fade)) * (0.12 + 0.88 * smooth(0.0, 0.3, mu))
                        hz_k = 0.2 + 0.8 * smooth(0.0, 0.3, mu)
                        fr = lit * sun * 1.00 + ALB * 0.4 * uni * 0.62 * hz_k
                        fg = lit * sun * 0.97 + ALB * 0.4 * uni * 0.92 * hz_k
                        fb = lit * sun * 0.92 + ALB * 0.4 * uni * 1.00 * hz_k
                        # behind the near boulders' faded part
                        rest = 1.0 - a
                        cr += fr * op * rest * far_k; cg += fg * op * rest * far_k; cb += fb * op * rest * far_k
                        a += op * rest * far_k
                        # the dust glowing against the Sun (seen from below)
                        if dust_k > 0:
                            c = dx * Sx + dy * Sy + dz * Sz
                            g = 0.8
                            ph = (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * c) ** 1.5)
                            dl = dust_k * 0.004 / max(mu, 0.01) * ph * ek * (0.6 + 0.8 * w) * sun
                            cr += dl * 0.95; cg += dl * 0.97; cb += dl
            if dust_k > 0:
                c = dx * Sx + dy * Sy + dz * Sz
                g = 0.82
                ph = (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * c) ** 1.5)
                dl = dust_k * 0.0035 * ph * (1.0 - min(1.0, a)) * sun
                cr += dl * 0.95; cg += dl * 0.97; cb += dl
            img[j, i, 0] = cr; img[j, i, 1] = cg; img[j, i, 2] = cb; alp[j, i] = min(1.0, a)

def ring_frame(cam, look, up=(0, 0, 1), fovy=70.0, expo=4.5, planet_gain=1.6, sun_int=300.0, near_k=1.0, far_k=1.0,
               dust_k=0.0, star_gain=0.7, photo_gain=0.25, bloom=1.0, raw=False, roll=0.0, look_is_dir=True, flare=1.0):
    """cam, look (a direction, or a point if look_is_dir=False), up: local frame, metres"""
    cam = np.asarray(cam, float)
    look = np.asarray(look, float)
    target = cam + look if look_is_dir else look
    TY = math.tan(math.radians(fovy) / 2); TX = TY * RW / RH
    r, u, f = TR.cam_basis(cam, target, up)
    if roll:
        c_, s_ = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        r, u = r * c_ + u * s_, -r * s_ + u * c_
    S = dir_to_local(U.sun_dir_2026())
    # Uranus from here (local): its centre, and how much light it throws (its disc's solid angle x albedo x phase)
    cp = to_planet(cam)
    Uc = dir_to_local(-cp / np.linalg.norm(cp))
    sinr = U.RE / np.linalg.norm(cp)
    omega = 2 * math.pi * (1 - math.sqrt(1 - sinr ** 2))
    lit_frac = 0.5 * (1 + float(np.dot(-Uc, S)))           # how much of the disc we... the planet sees lit, roughly
    uni = omega / math.pi * 0.5 * (0.3 + 0.7 * lit_frac)
    img = np.zeros((RH, RW, 3), np.float32); alp = np.zeros((RH, RW), np.float32)
    render_ring(img, alp, RW, RH, *cam, *r, *u, *f, TX, TY, *S, 1.0, *Uc, uni, PERM, near_k, far_k, dust_k)
    # the background: everything else, the same camera in Uranus' frame
    rp, up_, fp = dir_to_planet(r), dir_to_planet(u), dir_to_planet(f)
    bgimg = np.zeros((RH, RW, 3), np.float32); bmask = np.zeros((RH, RW), np.float32)
    T = U.textures()
    Sp = U.sun_dir_2026()
    U.render(bgimg, bmask, RW, RH, *cp, *rp, *up_, *fp, TX, TY, *Sp, sun_int, 0.0, PERM, U.RINGS, U.DUST,
             14.0, dust_k, 0.0, 1.0, 1.0, True, np.zeros((0, 7)), T, T.shape[2], T.shape[1], 1.0)
    bgimg *= planet_gain
    sky = TR.background(rp, up_, fp, TX, TY, np.maximum(bmask, alp), star_gain, photo_gain, TR.GAL)
    out = (bgimg + sky * (1 - bmask[..., None])) * (1 - alp[..., None]) + img * expo
    U.sun_flare(out, cp, rp, up_, fp, TX, TY, Sp, (1 - alp) * (1 - bmask), flare)
    if raw: return out
    return TR.finish(out, bloom)

if __name__ == '__main__' and sys.argv[1:2] == ['test']:
    import time
    os.makedirs(U.WORK, exist_ok=True)
    t0 = time.time()
    S = dir_to_local(U.sun_dir_2026()); print('sun local', S.round(3))
    Uc = dir_to_local(-to_planet((0, 0, 0)) / np.linalg.norm(to_planet((0, 0, 0)))); print('uranus local', Uc.round(3))
    # skimming 30 m over the sheet, looking ahead and a little towards Uranus
    ring_frame((0, 0, 22.0), np.array([0.25, -1.0, 0.06]), fovy=88).save(os.path.join(U.WORK, 'ring_a.jpg')); print('a', time.time() - t0)
    ring_frame((0, 0, 6.0), np.array([1.0, -0.9, 0.02]), fovy=80).save(os.path.join(U.WORK, 'ring_b.jpg')); print('b', time.time() - t0)
    # from below, looking up towards the Sun through the sheet
    ring_frame((0, 0, -25.0), np.array(S) * 1.0 + np.array([0.25, 0, 0]), up=(1, 0, 0), dust_k=1.0, fovy=80).save(os.path.join(U.WORK, 'ring_c.jpg'))
    print('done', time.time() - t0)
