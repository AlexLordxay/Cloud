# «А ти уявляєш Європу так?» — the renderers (numba, CPU, ray tracing). Units: km.
#   terrain(): the 200 km flight patch (prep.py) as a height field, mirrored beyond its edges and bent with Europa's
#     curvature, so the horizon is real; or (slab=True) cut out as a block whose sides show the layers below: the ice
#     shell and the ocean. Low Sun, hard shadows (no air), faint orange Jupiter-shine, glints on the ice; the black sky
#     with stars, Jupiter (true angular size from Europa, lit from the side) and the small Sun.
#   space(): Europa as a globe (the coloured mosaic), optionally cut open (a wedge removed: ice, ocean, rock, iron),
#     the Moon beside it at true scale, Jupiter in the background, stars.
import math
import numpy as np
from numba import njit, prange

R_E = 1560.8
J_R, J_D = 69911.0, 671100.0

@njit(fastmath=True, inline='always')
def tex2(T, u, v):
    # bilinear lookup, u wraps, v clamps; T: (h, w, 3)
    h, w = T.shape[0], T.shape[1]
    x = (u - math.floor(u)) * w - 0.5; y = min(max(v, 0.0), 1.0) * (h - 1)
    i = int(math.floor(x)); j = int(y); fx = x - i; fy = y - j
    i0 = i % w; i1 = (i + 1) % w; j1 = min(j + 1, h - 1)
    r = (T[j, i0, 0] * (1 - fx) + T[j, i1, 0] * fx) * (1 - fy) + (T[j1, i0, 0] * (1 - fx) + T[j1, i1, 0] * fx) * fy
    g = (T[j, i0, 1] * (1 - fx) + T[j, i1, 1] * fx) * (1 - fy) + (T[j1, i0, 1] * (1 - fx) + T[j1, i1, 1] * fx) * fy
    b = (T[j, i0, 2] * (1 - fx) + T[j, i1, 2] * fx) * (1 - fy) + (T[j1, i0, 2] * (1 - fx) + T[j1, i1, 2] * fx) * fy
    return r, g, b

@njit(fastmath=True, inline='always')
def mirror(p, n):
    # mirror-repeat index space [0, n-1]
    m = 2 * (n - 1)
    p = p % m
    if p < 0: p += m
    return p if p <= n - 1 else m - p

@njit(fastmath=True, inline='always')
def vn2(x, y):
    i = math.floor(x); j = math.floor(y); fx = x - i; fy = y - j
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    def hh(a, b):
        v = math.sin(a * 127.1 + b * 311.7) * 43758.5453
        return v - math.floor(v)
    return (hh(i, j) * (1 - fx) + hh(i + 1, j) * fx) * (1 - fy) + (hh(i, j + 1) * (1 - fx) + hh(i + 1, j + 1) * fx) * fy

@njit(fastmath=True)
def hgt(Z, x, y, pk, half, curv, slab, mic=1.0):
    # height (km) at x, y (km); outside the patch mirrored, minus the curvature drop
    n = Z.shape[0]
    if slab and (abs(x) > half or abs(y) > half): return -1e9
    px = mirror((x + half) / pk - 0.5, n); py = mirror((half - y) / pk - 0.5, n)
    i = int(px); j = int(py); i = min(i, n - 2); j = min(j, n - 2); fx = px - i; fy = py - j
    h = (Z[j, i] * (1 - fx) + Z[j, i + 1] * fx) * (1 - fy) + (Z[j + 1, i] * (1 - fx) + Z[j + 1, i + 1] * fx) * fy
    # sub-pixel roughness (hummocks and blocks a few metres high), for the close-ups
    if mic > 0: h += mic * (0.006 * (vn2(x * 25.0, y * 25.0) - 0.5) + 0.0025 * (vn2(x * 90.0 + 7.0, y * 90.0) - 0.5))
    if curv: h -= (x * x + y * y) / (2 * R_E)
    return h

@njit(fastmath=True, inline='always')
def albedo(A, x, y, pk, half):
    n = A.shape[0]
    px = mirror((x + half) / pk - 0.5, n); py = mirror((half - y) / pk - 0.5, n)
    i = min(int(px), n - 2); j = min(int(py), n - 2); fx = px - i; fy = py - j
    r = (A[j, i, 0] * (1 - fx) + A[j, i + 1, 0] * fx) * (1 - fy) + (A[j + 1, i, 0] * (1 - fx) + A[j + 1, i + 1, 0] * fx) * fy
    g = (A[j, i, 1] * (1 - fx) + A[j, i + 1, 1] * fx) * (1 - fy) + (A[j + 1, i, 1] * (1 - fx) + A[j + 1, i + 1, 1] * fx) * fy
    b = (A[j, i, 2] * (1 - fx) + A[j, i + 1, 2] * fx) * (1 - fy) + (A[j + 1, i, 2] * (1 - fx) + A[j + 1, i + 1, 2] * fx) * fy
    return r, g, b

@njit(fastmath=True, inline='always')
def hash3(x, y, z):
    v = math.sin(x * 12.9898 + y * 78.233 + z * 37.719) * 43758.5453
    return v - math.floor(v)

@njit(fastmath=True)
def sky(SK, JT, dx, dy, dz, sun, jd, jang, jax, jrot, sunk):
    # the sky in direction d: stars, Jupiter (a sphere of angular radius jang in direction jd, axis jax), the Sun
    r = 0.0; g = 0.0; b = 0.0
    u = math.atan2(dx, -dy) / (2 * math.pi) + 0.5; v = math.acos(max(-1.0, min(1.0, dz))) / math.pi
    sr, sg, sb = tex2(SK, u, v)
    r = sr * sr * 0.5; g = sg * sg * 0.5; b = sb * sb * 0.5
    c = dx * jd[0] + dy * jd[1] + dz * jd[2]
    sj = math.sin(jang)
    if c > math.cos(jang) * 0.999:
        # ray to a unit-distance sphere of radius sj
        bq = c; disc = bq * bq - (1 - sj * sj)
        if disc > 0:
            t = bq - math.sqrt(disc)
            nx = (dx * t - jd[0]) / sj; ny = (dy * t - jd[1]) / sj; nz = (dz * t - jd[2]) / sj
            # Jupiter's own frame: axis jax, longitude from a reference perpendicular
            ax = jax
            e1x = jd[1] * ax[2] - jd[2] * ax[1]; e1y = jd[2] * ax[0] - jd[0] * ax[2]; e1z = jd[0] * ax[1] - jd[1] * ax[0]
            el = math.sqrt(e1x * e1x + e1y * e1y + e1z * e1z); e1x /= el; e1y /= el; e1z /= el
            e2x = ax[1] * e1z - ax[2] * e1y; e2y = ax[2] * e1x - ax[0] * e1z; e2z = ax[0] * e1y - ax[1] * e1x
            sl = nx * ax[0] + ny * ax[1] + nz * ax[2]
            lat = math.asin(max(-1.0, min(1.0, sl)))
            lon = math.atan2(nx * e2x + ny * e2y + nz * e2z, nx * e1x + ny * e1y + nz * e1z) + jrot
            tr, tg, tb = tex2(JT, lon / (2 * math.pi), 0.5 - lat / math.pi)
            lam = nx * sun[0] + ny * sun[1] + nz * sun[2]
            mu = -(nx * dx + ny * dy + nz * dz)
            li = max(0.0, lam) ** 0.85 * (0.55 + 0.45 * max(mu, 0.0) ** 0.3)
            li += 0.004
            # the terminator softened by the atmosphere
            li *= 0.5 + 0.5 * math.tanh(lam * 25.0) if lam < 0.05 else 1.0
            r = tr * tr * li * 1.6; g = tg * tg * li * 1.6; b = tb * tb * li * 1.6
            # a thin bright rim on the day side
            rim = max(0.0, 1.0 - mu) ** 6 * max(lam + 0.1, 0.0)
            r += 0.15 * rim; g += 0.14 * rim; b += 0.16 * rim
    # the Sun: a tiny disc (0.1°) and a glow
    cs = dx * sun[0] + dy * sun[1] + dz * sun[2]
    if sunk > 0:
        a = math.acos(max(-1.0, min(1.0, cs)))
        if a < 0.0009: r += 60.0 * sunk; g += 58.0 * sunk; b += 54.0 * sunk
        gl = sunk * (0.6 * math.exp(-a / 0.004) + 0.08 * math.exp(-a / 0.03))
        r += gl; g += gl * 0.97; b += gl * 0.92
    return r, g, b

@njit(parallel=True, fastmath=True)
def terrain(Z, A, pk, half, SK, JT, cam, fw, rt, up, fov, sun, jd, jang, jax, jrot, slab, depth_ice, depth_ocean, expo, out, ss, hmax):
    H, W = out.shape[0], out.shape[1]
    tanf = math.tan(fov / 2)
    curv = not slab
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
                    hit = 0; t = 0.0; tmax = 3000.0
                    # slab: start where the ray enters the block (x, y within half, z within [-depth, 3])
                    t0 = 0.0
                    if slab:
                        tn = -1e9; tf = 1e9; face = -1
                        for ax in range(3):
                            o = cam[ax]; d = dx if ax == 0 else (dy if ax == 1 else dz)
                            lo = -half if ax < 2 else -(depth_ice + depth_ocean)
                            hi = half if ax < 2 else 3.0
                            if abs(d) < 1e-9:
                                if o < lo or o > hi: tn = 1e9
                            else:
                                ta = (lo - o) / d; tb = (hi - o) / d
                                if ta > tb: ta, tb = tb, ta
                                if ta > tn: tn = ta; face = ax
                                if tb < tf: tf = tb
                        if tn < tf and tf > 0:
                            t0 = max(tn, 0.0); tmax = tf
                            # entering through a side: below the surface there -> the cut face
                            if face < 2 and tn > 0:
                                qx = cam[0] + dx * tn; qy = cam[1] + dy * tn; qz = cam[2] + dz * tn
                                hs = hgt(Z, max(-half, min(half, qx)), max(-half, min(half, qy)), pk, half, False, False)
                                if qz < hs:
                                    hit = 2; t = tn
                        else:
                            tmax = -1.0
                    if hit == 0 and tmax > 0:
                        t = t0 + 0.01
                        st = 0.01
                        for s in range(900):
                            x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                            # above everything: rising -> sky; falling -> jump down to the top of the relief
                            if z > hmax + 0.02:
                                if dz >= 0: break
                                tj = (z - hmax - 0.01) / -dz
                                if tj > st: t += tj; st = tj; continue
                            mic = 1.0 if t < 3.0 else 0.0
                            hh = hgt(Z, x, y, pk, half, curv, slab, mic)
                            if hh < -1e8: break
                            dz_ = z - hh
                            if dz_ < 0:
                                ta = t - st
                                for k in range(10):
                                    tm = (ta + t) / 2
                                    if cam[2] + dz * tm < hgt(Z, cam[0] + dx * tm, cam[1] + dy * tm, pk, half, curv, slab, mic): t = tm
                                    else: ta = tm
                                hit = 1; break
                            st = max(0.006, min(dz_ * 0.7, 0.006 * t + 0.015))
                            st = max(st, 0.004 * t)
                            t += st
                            if t > tmax: break
                    if hit == 1:
                        x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                        e = max(0.004, min(pk, t * 0.0015))
                        mic = 1.0 if t < 3.0 else 0.0
                        gx = (hgt(Z, x + e, y, pk, half, curv, slab, mic) - hgt(Z, x - e, y, pk, half, curv, slab, mic)) / (2 * e)
                        gy = (hgt(Z, x, y + e, pk, half, curv, slab, mic) - hgt(Z, x, y - e, pk, half, curv, slab, mic)) / (2 * e)
                        # rock-scale roughness near the camera
                        nk = max(0.0, 1.0 - t / 6.0)
                        if nk > 0:
                            q = 9.0
                            gx += nk * 0.25 * (hash3(math.floor(x * q), math.floor(y * q), 1.0) - 0.5)
                            gy += nk * 0.25 * (hash3(math.floor(x * q), math.floor(y * q), 2.0) - 0.5)
                        nl = math.sqrt(gx * gx + gy * gy + 1.0); n0 = -gx / nl; n1 = -gy / nl; n2 = 1.0 / nl
                        if curv:
                            # the local vertical tilts with the curvature
                            n0 += x / R_E; n1 += y / R_E; nn = math.sqrt(n0 * n0 + n1 * n1 + n2 * n2); n0 /= nn; n1 /= nn; n2 /= nn
                        ar, ag, ab = albedo(A, x, y, pk, half)
                        ar *= ar; ag *= ag; ab *= ab                       # to linear
                        lam = n0 * sun[0] + n1 * sun[1] + n2 * sun[2]
                        sh = 1.0
                        if lam > 0:
                            qx = x + n0 * 0.003; qy = y + n1 * 0.003; qz = z + n2 * 0.003; sst = 0.02
                            for k in range(40):
                                qx += sun[0] * sst; qy += sun[1] * sst; qz += sun[2] * sst
                                hh = hgt(Z, qx, qy, pk, half, curv, slab, 0.0)
                                if hh < -1e8: break
                                if qz < hh: sh = 0.0; break
                                sst *= 1.18
                                if qz - hh > 3.0: break
                        lam = max(lam, 0.0)
                        # ice: a bright, slightly forward-scattering surface; glints on smooth facets
                        vx = -dx; vy = -dy; vz = -dz
                        hx = sun[0] + vx; hy = sun[1] + vy; hz = sun[2] + vz; hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                        spec = max(0.0, (n0 * hx + n1 * hy + n2 * hz) / hl) ** 60 * 0.6 * sh * (lam > 0)
                        gl = hash3(math.floor(x * 300), math.floor(y * 300), math.floor(z * 300))
                        if gl > 0.997 and t < 2.5: spec += 3.0 * sh * lam
                        jl = max(0.0, n0 * jd[0] + n1 * jd[1] + n2 * jd[2]) * 0.06
                        r = ar * (2.2 * lam * sh + jl * 1.0 + 0.004) + spec
                        g = ag * (2.2 * lam * sh + jl * 0.80 + 0.005) + spec
                        b = ab * (2.2 * lam * sh + jl * 0.62 + 0.008) + spec * 1.05
                        # light falling off with distance only for the eye (no air): a faint darkening far away
                        f = math.exp(-t / 1800.0)
                        r *= f; g *= f; b *= f
                    elif hit == 2:
                        x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                        hs = hgt(Z, max(-half, min(half, x)), max(-half, min(half, y)), pk, half, False, False)
                        dep = hs - z
                        # face normal (which side) for a little shading
                        fn = 0.75 if abs(abs(x) - half) < 1e-3 else 0.55
                        if dep < depth_ice:
                            # the ice shell: white-blue, layered, cracks running down
                            k = dep / depth_ice
                            lay = 0.85 + 0.15 * math.sin(dep * 2.3 + 1.7 * math.sin(x * 0.07 + y * 0.05))
                            crack = hash3(math.floor((x + y) * 0.35), 0.0, 3.0)
                            cr = 0.6 if (crack > 0.93 and (((x + y) * 0.35) % 1.0) < 0.06) else 1.0
                            r = (0.70 - 0.35 * k) * lay * cr * fn; g = (0.80 - 0.25 * k) * lay * cr * fn; b = (0.92 - 0.1 * k) * lay * cr * fn
                        elif dep < depth_ice + depth_ocean:
                            # the ocean: deep blue, darker with depth, a glow under the ice, drifting specks
                            k = (dep - depth_ice) / depth_ocean
                            gl = math.exp(-(dep - depth_ice) / 6.0)
                            sp = 1.0 + 0.5 * (hash3(math.floor(x * 1.5), math.floor(y * 1.5), math.floor(z * 1.5)) > 0.985)
                            r = (0.010 + 0.05 * gl) * fn * sp; g = (0.08 * (1 - k) + 0.02 + 0.18 * gl) * fn * sp; b = (0.30 * (1 - k) + 0.07 + 0.35 * gl) * fn * sp
                        else:
                            r = 0.12 * fn; g = 0.09 * fn; b = 0.07 * fn
                        r *= 1.2; g *= 1.2; b *= 1.2
                    else:
                        r, g, b = sky(SK, JT, dx, dy, dz, sun, jd, jang, jax, jrot, 1.0)
                    acr += r; acg += g; acb += b
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k

@njit(fastmath=True, inline='always')
def ray_sphere(ox, oy, oz, dx, dy, dz, cx, cy, cz, R):
    lx = ox - cx; ly = oy - cy; lz = oz - cz
    b = lx * dx + ly * dy + lz * dz; c = lx * lx + ly * ly + lz * lz - R * R
    disc = b * b - c
    if disc < 0: return -1.0, -1.0
    s = math.sqrt(disc)
    return -b - s, -b + s

@njit(parallel=True, fastmath=True)
def space(GT, MT, SK, JT, cam, fw, rt, up, fov, sun, jd, jang, jax, jrot, erot, moon_pos, cut, cut_dir, expo, out, ss, clip, BOX):
    # Europa at the origin (radius R_E, north +z), texture GT (equirect, lon 0 at +x rotated by erot);
    # the Moon (radius 1737.4) at moon_pos if moon_pos[3] > 0; a wedge of angle cut*90° removed round cut_dir
    H, W = out.shape[0], out.shape[1]
    tanf = math.tan(fov / 2)
    MR = 1737.4
    # layer radii (km): ice to ~25 km down, ocean to ~150 km, rock mantle, iron core
    r_ice = R_E - 25.0; r_oc = R_E - 160.0; r_core = 600.0
    for py_ in prange(H):
        for px_ in range(W):
            acr = 0.0; acg = 0.0; acb = 0.0
            for sy in range(ss):
                for sx in range(ss):
                    u = (2 * (px_ + (sx + 0.5) / ss) / W - 1) * tanf * W / H
                    v = (1 - 2 * (py_ + (sy + 0.5) / ss) / H) * tanf
                    dx = fw[0] + rt[0] * u + up[0] * v; dy = fw[1] + rt[1] * u + up[1] * v; dz = fw[2] + rt[2] * u + up[2] * v
                    dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
                    best = 1e18; kind = 0; nx = 0.0; ny = 0.0; nz = 0.0; px = 0.0; py = 0.0; pz = 0.0
                    # Europa, optionally with an octant-like slice removed: z > 0 and azimuth within ±cut·45° of cut_dir
                    t1, t2 = ray_sphere(cam[0], cam[1], cam[2], dx, dy, dz, 0.0, 0.0, 0.0, R_E)
                    if t2 > 0:
                        ca = math.cos(cut * math.pi / 4)
                        a0 = math.atan2(cut_dir[1], cut_dir[0])
                        for tt in (t1, t2):
                            if tt <= 0 or kind != 0: continue
                            qx = cam[0] + dx * tt; qy = cam[1] + dy * tt; qz = cam[2] + dz * tt
                            inw = cut > 0 and qz > 0 and (qx * cut_dir[0] + qy * cut_dir[1]) / max(math.sqrt(qx * qx + qy * qy), 1e-6) > ca
                            if not inw:
                                best = tt; kind = 1; px = qx; py = qy; pz = qz; nx = qx / R_E; ny = qy / R_E; nz = qz / R_E
                        if cut > 0:
                            # the three cut faces: two vertical half-planes (z > 0) and the floor (z = 0) of the slice
                            for f in range(3):
                                if f < 2:
                                    sgn = -1.0 if f == 0 else 1.0
                                    a = a0 + sgn * cut * math.pi / 4
                                    pnx = -math.sin(a); pny = math.cos(a); pnz = 0.0
                                else:
                                    pnx = 0.0; pny = 0.0; pnz = 1.0
                                den = dx * pnx + dy * pny + dz * pnz
                                if abs(den) < 1e-9: continue
                                tp = -(cam[0] * pnx + cam[1] * pny + cam[2] * pnz) / den
                                if tp <= 0 or tp >= best: continue
                                qx = cam[0] + dx * tp; qy = cam[1] + dy * tp; qz = cam[2] + dz * tp
                                rr = math.sqrt(qx * qx + qy * qy + qz * qz)
                                if rr >= R_E: continue
                                if f < 2:
                                    if qz < 0 or qx * math.cos(a) + qy * math.sin(a) < 0: continue
                                else:
                                    if (qx * cut_dir[0] + qy * cut_dir[1]) / max(math.sqrt(qx * qx + qy * qy), 1e-6) < ca: continue
                                # face normal toward the camera
                                sd = 1.0 if (cam[0] - qx) * pnx + (cam[1] - qy) * pny + (cam[2] - qz) * pnz > 0 else -1.0
                                best = tp; kind = 3; px = qx; py = qy; pz = qz; nx = pnx * sd; ny = pny * sd; nz = pnz * sd
                    if moon_pos[3] > 0:
                        m1, m2 = ray_sphere(cam[0], cam[1], cam[2], dx, dy, dz, moon_pos[0], moon_pos[1], moon_pos[2], MR)
                        if m1 > 0 and m1 < best:
                            best = m1; kind = 2; px = cam[0] + dx * m1; py = cam[1] + dy * m1; pz = cam[2] + dz * m1
                            nx = (px - moon_pos[0]) / MR; ny = (py - moon_pos[1]) / MR; nz = (pz - moon_pos[2]) / MR
                    # «Europa Clipper»: boxes in metres round clip[0:3] (km), world-aligned
                    cmat = 0; cnx = 0.0; cny = 0.0; cnz = 0.0; clx = 0.0; cly = 0.0
                    if clip[3] > 0:
                        ox = (cam[0] - clip[0]) * 1000.0; oy = (cam[1] - clip[1]) * 1000.0; oz = (cam[2] - clip[2]) * 1000.0
                        for q in range(BOX.shape[0]):
                            tn = -1e18; tf = 1e18; fa = 0; fs = 1.0
                            for ax in range(3):
                                o = ox if ax == 0 else (oy if ax == 1 else oz); d_ = dx if ax == 0 else (dy if ax == 1 else dz)
                                lo = BOX[q, ax] - BOX[q, 3 + ax]; hi = BOX[q, ax] + BOX[q, 3 + ax]
                                if abs(d_) < 1e-12:
                                    if o < lo or o > hi: tn = 1e18
                                    continue
                                ta = (lo - o) / d_; tb = (hi - o) / d_; sgn = -1.0
                                if ta > tb: ta, tb = tb, ta; sgn = 1.0
                                if ta > tn: tn = ta; fa = ax; fs = sgn
                                if tb < tf: tf = tb
                            if tn < tf and tn > 0 and tn / 1000.0 < best:
                                best = tn / 1000.0; kind = 4; cmat = int(BOX[q, 6])
                                cnx = fs if fa == 0 else 0.0; cny = fs if fa == 1 else 0.0; cnz = fs if fa == 2 else 0.0
                                clx = ox + dx * tn; cly = oy + dy * tn
                    r = 0.0; g = 0.0; b = 0.0
                    if kind == 4:
                        lam = max(0.0, cnx * sun[0] + cny * sun[1] + cnz * sun[2])
                        hx = sun[0] - dx; hy = sun[1] - dy; hz = sun[2] - dz; hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                        sp = max(0.0, (cnx * hx + cny * hy + cnz * hz) / hl)
                        # Europa below lights the underside a little (icy, bright)
                        amb = 0.06 + 0.10 * max(0.0, -cnz)
                        if cmat == 1:      # gold thermal blanket, crinkled
                            cr = 0.75 + 0.5 * vn2(clx * 6.0, cly * 6.0 + cnz * 3.0)
                            r = (0.95 * lam + amb) * 0.78 * cr + sp ** 20 * 1.2; g = (0.95 * lam + amb) * 0.55 * cr + sp ** 20 * 0.9; b = (0.95 * lam + amb) * 0.18 * cr + sp ** 20 * 0.4
                        elif cmat == 2:    # white antenna
                            r = (lam + amb) * 0.85 + sp ** 30 * 0.5; g = r; b = r * 1.02
                        elif cmat == 3:    # solar cells with silver grid lines
                            gx_ = (abs(clx) * 2.0) % 1.0; gy_ = (cly * 2.0) % 1.0
                            line = 1.0 if (gx_ < 0.04 or gy_ < 0.04) else 0.0
                            r = (lam + amb) * (0.04 + 0.5 * line) + sp ** 40 * 1.5; g = (lam + amb) * (0.06 + 0.5 * line) + sp ** 40 * 1.5; b = (lam + amb) * (0.16 + 0.5 * line) + sp ** 40 * 1.6
                        else:              # dark structure
                            r = (lam + amb) * 0.18 + sp ** 10 * 0.3; g = r; b = r * 1.05
                    elif kind == 1 or kind == 2:
                        lat = math.asin(max(-1.0, min(1.0, nz))); lon = math.atan2(ny, nx)
                        if kind == 1:
                            tr, tg, tb = tex2(GT, (lon + erot) / (2 * math.pi), 0.5 - lat / math.pi)
                        else:
                            tr, tg, tb = tex2(MT, (lon + 1.0) / (2 * math.pi), 0.5 - lat / math.pi)
                        tr *= tr; tg *= tg; tb *= tb
                        lam = nx * sun[0] + ny * sun[1] + nz * sun[2]
                        mu = -(nx * dx + ny * dy + nz * dz)
                        # Lommel–Seeliger-ish for icy/dusty bodies (no hard limb darkening), soft terminator
                        li = max(lam, 0.0) / (max(lam, 0.0) + max(mu, 0.02)) * 2.0 * (0.7 if kind == 1 else 0.9)
                        li = li * 0.9 + 0.1 * max(lam, 0.0)
                        jl = max(0.0, nx * jd[0] + ny * jd[1] + nz * jd[2]) * (0.02 if kind == 1 else 0.0)
                        r = tr * (li * 1.9 + jl); g = tg * (li * 1.9 + jl * 0.8); b = tb * (li * 1.9 + jl * 0.62)
                        if kind == 2: r *= 0.85; g *= 0.85; b *= 0.85
                    elif kind == 3:
                        rr = math.sqrt(px * px + py * py + pz * pz)
                        li = 0.35 + 0.65 * max(0.0, nx * sun[0] + ny * sun[1] + nz * sun[2])
                        n1_ = vn2(px * 0.02, py * 0.02 + pz * 0.02); n2_ = vn2(px * 0.08 + 3.0, py * 0.08 + pz * 0.08)
                        if rr > r_ice:
                            r = 0.80; g = 0.88; b = 0.97
                            li = 0.7 + 0.3 * li
                        elif rr > r_oc:
                            k = (r_ice - rr) / (r_ice - r_oc)
                            # the ocean: luminous blue under the ice, deeper below, with faint currents
                            cur = 0.85 + 0.3 * n2_
                            r = (0.03 + 0.12 * (1 - k)) * cur; g = (0.35 + 0.65 * (1 - k)) * cur; b = (1.0 + 0.8 * (1 - k)) * cur
                            li = 0.9 + 0.2 * li
                        elif rr > r_core:
                            k = (rr - r_core) / (r_oc - r_core)
                            m = 0.8 + 0.25 * n1_ + 0.1 * n2_
                            r = (0.30 + 0.12 * k) * m; g = (0.22 + 0.08 * k) * m; b = (0.17 + 0.05 * k) * m
                        else:
                            k = rr / r_core
                            m = 0.85 + 0.2 * n2_
                            r = (0.62 - 0.15 * k) * m; g = (0.46 - 0.12 * k) * m; b = (0.36 - 0.1 * k) * m
                        r *= li; g *= li; b *= li
                    else:
                        r, g, b = sky(SK, JT, dx, dy, dz, sun, jd, jang, jax, jrot, 1.0)
                    acr += r; acg += g; acb += b
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k

def tonemap(img):
    # ACES fit, gamma
    x = img * 0.9
    y = np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
    return y ** (1 / 2.2)

def bloom(img):
    from scipy.ndimage import gaussian_filter
    hi = np.clip(img - 1.0, 0, None)
    return img + 0.35 * gaussian_filter(hi, (6, 6, 0)) + 0.25 * gaussian_filter(hi, (24, 24, 0))
