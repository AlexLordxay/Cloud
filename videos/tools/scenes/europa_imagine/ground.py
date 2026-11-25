# «А ти уявляєш Європу так?» — the close-up renderer for the shot «standing on the ice» (numba, CPU, ray tracing; km).
# The 49 m/px relief of prep.py carries the big forms (the double ridge, the swells); below a pixel of it the ground
# is procedural, finer the nearer it is (level of detail by distance):
#   * the ice broken into plates ~10–25 m across (Voronoi cells), each a little tilted and lifted, with cracks between;
#   * crumpled, ridged hummocks at 60, 20, 7, 2.5, 0.9 and 0.35 m;
#   * albedo: the 500 m/px colour plus mottling at the same scales, cracks darker and bluish, crests frosty white,
#     evaluated in 3D so it does not stretch on the ridge flanks;
#   * smooth normals for the big relief (no bilinear facets) plus the detail's own normals;
#   * hard shadows from the Sun (no air) including those of the detail near the camera, light bounced off the
#     bright ice into the shadows, faint orange Jupiter-shine.
import math
import numpy as np
from numba import njit, prange
from render import R_E, mirror, sky

@njit(fastmath=True, inline='always')
def hs(i, j, s):
    # integer hash of a lattice point (much cheaper than sin with large arguments)
    n = np.int64(i) * np.int64(374761393) + np.int64(j) * np.int64(668265263) + np.int64(s) * np.int64(2246822519)
    n = (n ^ (n >> np.int64(13))) * np.int64(1274126177)
    n = n ^ (n >> np.int64(16))
    return float(n & np.int64(0xFFFFFF)) / 16777216.0

@njit(fastmath=True, inline='always')
def vn(x, y, s):
    i = math.floor(x); j = math.floor(y); fx = x - i; fy = y - j
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    return (hs(i, j, s) * (1 - fx) + hs(i + 1, j, s) * fx) * (1 - fy) + (hs(i, j + 1, s) * (1 - fx) + hs(i + 1, j + 1, s) * fx) * fy

@njit(fastmath=True, inline='always')
def vn3(x, y, z, s):
    a = vn(x, y + 17.3 * math.floor(z), s); b = vn(x, y + 17.3 * (math.floor(z) + 1), s)
    f = z - math.floor(z); f = f * f * (3 - 2 * f)
    return a * (1 - f) + b * f

@njit(fastmath=True, inline='always')
def fade(w, lod):
    # an octave of wavelength w is drawn fully when w > 3 lod, not at all below 1.5 lod
    return min(1.0, max(0.0, (w - 1.5 * lod) / (1.5 * lod)))

@njit(fastmath=True)
def base(Z, x, y, pk, half):
    n = Z.shape[0]
    px = mirror((x + half) / pk - 0.5, n); py = mirror((half - y) / pk - 0.5, n)
    i = min(int(px), n - 2); j = min(int(py), n - 2); fx = px - i; fy = py - j
    h = (Z[j, i] * (1 - fx) + Z[j, i + 1] * fx) * (1 - fy) + (Z[j + 1, i] * (1 - fx) + Z[j + 1, i + 1] * fx) * fy
    return h - (x * x + y * y) / (2 * R_E)

@njit(fastmath=True)
def plates(x, y, cell):
    # Voronoi plates: (height offset of the plate here, crack depth 0..1, plate id hash)
    gx = x / cell; gy = y / cell; ix = math.floor(gx); iy = math.floor(gy)
    d1 = 9.0; d2 = 9.0; bx = 0.0; by = 0.0
    for a in range(-1, 2):
        for b in range(-1, 2):
            cx = ix + a; cy = iy + b
            px = cx + 0.15 + 0.7 * hs(cx, cy, 41.0); py = cy + 0.15 + 0.7 * hs(cx, cy, 42.0)
            d = (gx - px) * (gx - px) + (gy - py) * (gy - py)
            if d < d1: d2 = d1; d1 = d; bx = cx; by = cy
            elif d < d2: d2 = d
    e = math.sqrt(d2) - math.sqrt(d1)                     # ~ distance to the nearest crack, in cells
    hid = hs(bx, by, 43.0)
    # each plate lifted and tilted a little
    tx = (hs(bx, by, 44.0) - 0.5) * 0.16; ty = (hs(bx, by, 45.0) - 0.5) * 0.16
    off = (hid - 0.5) * 0.0007 + (tx * (gx - bx - 0.5) + ty * (gy - by - 0.5)) * cell
    crack = max(0.0, 1.0 - e / 0.06)
    return off, crack * crack, hid

@njit(fastmath=True)
def detail(x, y, lod):
    # height (km) of everything finer than the relief map, faded out below the pixel size lod (km)
    d = 0.0
    f = fade(0.06, lod)
    if f > 0:
        d += f * 0.0030 * (vn(x / 0.06, y / 0.06, 1.0) - 0.5)
        f = fade(0.021, lod)
        if f > 0:
            r = 1.0 - abs(2 * vn(x / 0.021, y / 0.021, 2.0) - 1); d += f * 0.0016 * (r * r - 0.45)
            f = fade(0.016, lod)
            if f > 0:
                off, cr, _ = plates(x, y, 0.016)
                d += f * (off - 0.0009 * cr)
            f = fade(0.0075, lod)
            if f > 0:
                d += f * 0.0006 * (vn(x / 0.0075, y / 0.0075, 3.0) - 0.5)
                f = fade(0.0027, lod)
                if f > 0:
                    r = 1.0 - abs(2 * vn(x / 0.0027, y / 0.0027, 4.0) - 1); d += f * 0.00028 * (r * r - 0.45)
                    f = fade(0.0009, lod)
                    if f > 0:
                        r = 1.0 - abs(2 * vn(x / 0.0009, y / 0.0009, 5.0) - 1); d += f * 0.00012 * (r * r - 0.45)
                        f = fade(0.00035, lod)
                        if f > 0:
                            r = 1.0 - abs(2 * vn(x / 0.00035, y / 0.00035, 6.0) - 1); d += f * 0.00005 * (r * r - 0.45)
                            f = fade(0.00012, lod)
                            if f > 0:
                                r = 1.0 - abs(2 * vn(x / 0.00012, y / 0.00012, 7.0) - 1); d += f * 0.00002 * (r * r - 0.45)
    return d

DM = 0.0055        # the most the detail can rise above the relief map (km)

@njit(fastmath=True, inline='always')
def full(Z, x, y, pk, half, lod):
    return base(Z, x, y, pk, half) + detail(x, y, lod)

@njit(parallel=True, fastmath=True)
def ground(Z, A, pk, half, SK, JT, cam, fw, rt, up, fov, sun, jd, jang, jax, jrot, expo, out, ss, hmax):
    H, W = out.shape[0], out.shape[1]
    tanf = math.tan(fov / 2); pix = 2 * tanf / H
    for py_ in prange(H):
        for px_ in range(W):
            acr = 0.0; acg = 0.0; acb = 0.0
            for sy in range(ss):
                for sx in range(ss):
                    u = (2 * (px_ + (sx + 0.5) / ss) / W - 1) * tanf * W / H
                    v = (1 - 2 * (py_ + (sy + 0.5) / ss) / H) * tanf
                    dx = fw[0] + rt[0] * u + up[0] * v; dy = fw[1] + rt[1] * u + up[1] * v; dz = fw[2] + rt[2] * u + up[2] * v
                    dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
                    r = 0.0; g = 0.0; b = 0.0
                    hit = False; t = 0.001; st = 0.001
                    for s in range(1400):
                        x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                        if z > hmax + 0.02:
                            if dz >= 0: break
                            tj = (z - hmax - 0.01) / -dz
                            if tj > st: t += tj; st = tj; continue
                        hb = base(Z, x, y, pk, half)
                        c = z - hb
                        if c > DM:
                            st = max(0.0008, min((c - DM) * 0.8 + 0.0004, 0.006 * t + 0.015))
                            st = max(st, 0.005 * t)
                        else:
                            lod = t * pix
                            c2 = z - hb - detail(x, y, lod)
                            if c2 < 0:
                                ta = t - st
                                for k in range(12):
                                    tm = (ta + t) / 2
                                    if cam[2] + dz * tm < full(Z, cam[0] + dx * tm, cam[1] + dy * tm, pk, half, tm * pix): t = tm
                                    else: ta = tm
                                hit = True; break
                            st = max(0.00015, c2 * 0.6, 0.0012 * t + 0.004 * max(0.0, t - 0.3))
                        t += st
                        if t > 3000.0: break
                    if hit:
                        x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                        lod = t * pix
                        # normal: the relief map smoothed over ~1.5 of its pixels, plus the detail's own slope
                        e = max(0.7 * pk, t * 0.0015)
                        gx = (base(Z, x + e, y, pk, half) - base(Z, x - e, y, pk, half)) / (2 * e)
                        gy = (base(Z, x, y + e, pk, half) - base(Z, x, y - e, pk, half)) / (2 * e)
                        ed = max(0.00004, lod * 0.8)
                        gx += (detail(x + ed, y, lod) - detail(x - ed, y, lod)) / (2 * ed)
                        gy += (detail(x, y + ed, lod) - detail(x, y - ed, lod)) / (2 * ed)
                        nl = math.sqrt(gx * gx + gy * gy + 1.0); n0 = -gx / nl; n1 = -gy / nl; n2 = 1.0 / nl
                        n0 += x / R_E; n1 += y / R_E; nn = math.sqrt(n0 * n0 + n1 * n1 + n2 * n2); n0 /= nn; n1 /= nn; n2 /= nn
                        # albedo: the map, mottled at finer scales (in 3D), cracks bluish-dark, crests frosty
                        n = A.shape[0]
                        qx = mirror((x + half) / pk - 0.5, n); qy = mirror((half - y) / pk - 0.5, n)
                        i = min(int(qx), n - 2); j = min(int(qy), n - 2); fx = qx - i; fy = qy - j
                        ar = (A[j, i, 0] * (1 - fx) + A[j, i + 1, 0] * fx) * (1 - fy) + (A[j + 1, i, 0] * (1 - fx) + A[j + 1, i + 1, 0] * fx) * fy
                        ag = (A[j, i, 1] * (1 - fx) + A[j, i + 1, 1] * fx) * (1 - fy) + (A[j + 1, i, 1] * (1 - fx) + A[j + 1, i + 1, 1] * fx) * fy
                        ab = (A[j, i, 2] * (1 - fx) + A[j, i + 1, 2] * fx) * (1 - fy) + (A[j + 1, i, 2] * (1 - fx) + A[j + 1, i + 1, 2] * fx) * fy
                        m = 1.0
                        zz = z + (x * x + y * y) / (2 * R_E)
                        for o in range(4):
                            w = 0.12 / 3.2 ** o
                            fo = fade(w, lod)
                            if fo <= 0: break
                            m += fo * (0.26 - 0.04 * o) * (vn3(x / w, y / w, zz / w, 11.0 + o) - 0.5)
                        brown = 0.0
                        fo = fade(0.016, lod)
                        if fo > 0:
                            _, cr, hid = plates(x, y, 0.016)
                            m *= 1.0 - fo * 0.45 * cr
                            m *= 1.0 + fo * 0.10 * (hid - 0.5)
                            brown = fo * 0.5 * cr
                        dd = detail(x, y, lod)
                        m *= 1.0 + min(0.25, max(-0.2, dd / DM * 0.35))
                        ar *= m; ag *= m; ab *= m
                        ar = ar * (1 - brown * 0.25); ag = ag * (1 - brown * 0.12); ab = ab * (1 + brown * 0.05)
                        # the clean plains: cooler, whiter ice (the brown stays on the ridges and in the cracks)
                        lum = (ar + ag + ab) / 3; wf = min(1.0, max(0.0, (lum - 0.55) / 0.3)) * 0.55
                        ar = ar * (1 - wf) + lum * 0.96 * wf; ag = ag * (1 - wf) + lum * 0.99 * wf; ab = ab * (1 - wf) + lum * 1.05 * wf
                        ar *= ar; ag *= ag; ab *= ab                       # to linear
                        lam = n0 * sun[0] + n1 * sun[1] + n2 * sun[2]
                        sh = 1.0
                        if lam > 0:
                            sst = max(0.0002, lod); q = 0.0
                            ox = x + n0 * 0.0002; oy = y + n1 * 0.0002; oz = z + n2 * 0.0002
                            for k in range(56):
                                q += sst
                                qx = ox + sun[0] * q; qy = oy + sun[1] * q; qz = oz + sun[2] * q
                                hh = base(Z, qx, qy, pk, half)
                                if q < 0.12: hh += detail(qx, qy, lod + q * pix)
                                if qz < hh: sh = 0.0; break
                                if qz - hh > 2.0 or qz > hmax + 0.02: break
                                sst *= 1.22
                        lam = max(lam, 0.0)
                        vx = -dx; vy = -dy; vz = -dz
                        hx = sun[0] + vx; hy = sun[1] + vy; hz = sun[2] + vz; hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                        spec = max(0.0, (n0 * hx + n1 * hy + n2 * hz) / hl) ** 40 * 0.35 * sh * (lam > 0)
                        jl = max(0.0, n0 * jd[0] + n1 * jd[1] + n2 * jd[2]) * 0.06
                        bounce = 0.10 * (0.6 + 0.4 * n2)
                        r = ar * (2.2 * lam * sh + jl * 1.0 + bounce * 0.85) + spec
                        g = ag * (2.2 * lam * sh + jl * 0.80 + bounce * 0.95) + spec
                        b = ab * (2.2 * lam * sh + jl * 0.62 + bounce * 1.15) + spec * 1.05
                        f = math.exp(-t / 1800.0)
                        r *= f; g *= f; b *= f
                    else:
                        r, g, b = sky(SK, JT, dx, dy, dz, sun, jd, jang, jax, jrot, 1.0)
                    acr += r; acg += g; acb += b
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k
