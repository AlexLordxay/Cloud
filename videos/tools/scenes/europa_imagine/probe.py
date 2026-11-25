# «А ти уявляєш Європу так?» — the shot of «Europa Clipper» over Europa (numba, CPU, ray tracing).
# The spacecraft (metres, z up = the high-gain antenna's axis, x along the solar arrays), after NASA's published
# layout: 30.5 m across the two five-panel solar arrays, a ~5 m tall body (the propulsion module, a cylinder wrapped in
# blankets), the 3 m high-gain dish on top, the REASON radar antennas along the arrays, the 8.5 m magnetometer boom.
# Primitives: boxes (BOX: cx cy cz hx hy hz mat), z-axis cylinders (CYL: cx cy cz r z0 z1 mat), one dish (DISH: cx cy cz
# R depth mat). Materials: 1 gold blanket, 2 white, 3 solar panel, 4 dark structure, 5 silver rod, 7 metal, 8 silver
# blanket. Hard sunlight with the spacecraft's own shadows, light from the bright ice below, Jupiter-shine.
import math
import numpy as np
from numba import njit, prange
from render import R_E, ray_sphere, tex2, sky, vn2

BOX = np.array([
    # the yokes from the body to the arrays, and the five panels of each wing (gaps between them)
    *[(sx * 1.6, 0, 0.3, 0.75, 0.09, 0.09, 4) for sx in (-1, 1)],
    *[(sx * (2.35 + k * 2.84 + 1.38), 0, 0.3, 1.38, 2.05, 0.035, 3) for sx in (-1, 1) for k in range(5)],
    # REASON: the long HF dipoles along the array edges and the VHF bars
    *[(sx * 8.9, sy * 2.25, 0.36, 7.7, 0.025, 0.025, 5) for sx in (-1, 1) for sy in (-1, 1)],
    # the magnetometer boom and its sensor
    (0, -5.1, -0.4, 0.035, 4.25, 0.035, 5), (0, -9.35, -0.4, 0.12, 0.12, 0.12, 4),
    # radiator panels and an instrument deck on the body
    (0, 1.0, 0.4, 0.55, 0.06, 0.75, 2), (0, -1.0, 1.0, 0.45, 0.10, 0.35, 4), (0.95, 0, -0.6, 0.08, 0.45, 0.5, 8),
], np.float64)
CYL = np.array([
    (0, 0, 0, 0.86, -1.45, 1.35, 1),      # the propulsion module, gold
    (0, 0, 0, 0.92, 1.35, 1.95, 8),       # the avionics vault band, silver
    (0, 0, 0, 0.90, -1.95, -1.45, 4),     # lower band, dark
    (0, 0, 0, 0.30, -2.45, -1.95, 7),     # the main engine bell region
    (0, 0, 0, 0.05, 2.05, 3.10, 4),       # the feed strut
    (0, 0, 0, 0.22, 3.10, 3.16, 2),       # the sub-reflector
], np.float64)
DISH = np.array([0.0, 0.0, 1.98, 1.5, 0.42, 2.0])

@njit(fastmath=True)
def hit_box(B, q, ox, oy, oz, dx, dy, dz):
    tn = -1e18; tf = 1e18; fa = 0; fs = 1.0
    for ax in range(3):
        o = ox if ax == 0 else (oy if ax == 1 else oz); d_ = dx if ax == 0 else (dy if ax == 1 else dz)
        lo = B[q, ax] - B[q, 3 + ax]; hi = B[q, ax] + B[q, 3 + ax]
        if abs(d_) < 1e-12:
            if o < lo or o > hi: return 1e18, 0.0, 0.0, 0.0
            continue
        ta = (lo - o) / d_; tb = (hi - o) / d_; sgn = -1.0
        if ta > tb: ta, tb = tb, ta; sgn = 1.0
        if ta > tn: tn = ta; fa = ax; fs = sgn
        if tb < tf: tf = tb
    if tn < tf and tn > 1e-4:
        return tn, (fs if fa == 0 else 0.0), (fs if fa == 1 else 0.0), (fs if fa == 2 else 0.0)
    return 1e18, 0.0, 0.0, 0.0

@njit(fastmath=True)
def hit_cyl(C, q, ox, oy, oz, dx, dy, dz):
    lx = ox - C[q, 0]; ly = oy - C[q, 1]; r = C[q, 3]; z0 = C[q, 4] + C[q, 2]; z1 = C[q, 5] + C[q, 2]
    best = 1e18; nx = 0.0; ny = 0.0; nz = 0.0
    a = dx * dx + dy * dy; b = lx * dx + ly * dy; c = lx * lx + ly * ly - r * r
    if a > 1e-12:
        disc = b * b - a * c
        if disc >= 0:
            s = math.sqrt(disc)
            for tt in ((-b - s) / a, (-b + s) / a):
                if tt > 1e-4:
                    z = oz + dz * tt
                    if z0 <= z <= z1:
                        best = tt; nx = (lx + dx * tt) / r; ny = (ly + dy * tt) / r; nz = 0.0
                        break
    if abs(dz) > 1e-12:
        for k in range(2):
            zc = z0 if k == 0 else z1
            tt = (zc - oz) / dz
            if tt > 1e-4 and tt < best:
                x = lx + dx * tt; y = ly + dy * tt
                if x * x + y * y <= r * r:
                    best = tt; nx = 0.0; ny = 0.0; nz = -1.0 if k == 0 else 1.0
    return best, nx, ny, nz

@njit(fastmath=True)
def hit_dish(D, ox, oy, oz, dx, dy, dz):
    # paraboloid z - cz = depth (r / R)^2, r <= R; normal toward the ray's side
    k = D[4] / (D[3] * D[3])
    lx = ox - D[0]; ly = oy - D[1]; lz = oz - D[2]
    A = k * (dx * dx + dy * dy); Bq = 2 * k * (lx * dx + ly * dy) - dz; Cq = k * (lx * lx + ly * ly) - lz
    ts0 = 1e18; ts1 = 1e18
    if abs(A) < 1e-12:
        if abs(Bq) > 1e-12: ts0 = -Cq / Bq
    else:
        disc = Bq * Bq - 4 * A * Cq
        if disc >= 0:
            s = math.sqrt(disc); ts0 = (-Bq - s) / (2 * A); ts1 = (-Bq + s) / (2 * A)
            if ts0 > ts1: ts0, ts1 = ts1, ts0
    for tt in (ts0, ts1):
        if tt > 1e-4 and tt < 1e17:
            x = lx + dx * tt; y = ly + dy * tt
            if x * x + y * y <= D[3] * D[3]:
                nx = 2 * k * x; ny = 2 * k * y; nz = -1.0; nl = math.sqrt(nx * nx + ny * ny + 1.0)
                nx /= nl; ny /= nl; nz /= nl
                if nx * dx + ny * dy + nz * dz > 0: nx = -nx; ny = -ny; nz = -nz
                return tt, nx, ny, nz, x, y
    return 1e18, 0.0, 0.0, 0.0, 0.0, 0.0

@njit(fastmath=True)
def trace_sc(B, C, D, ox, oy, oz, dx, dy, dz):
    best = 1e18; mat = 0; nx = 0.0; ny = 0.0; nz = 0.0
    for q in range(B.shape[0]):
        t, a, b, c = hit_box(B, q, ox, oy, oz, dx, dy, dz)
        if t < best: best = t; mat = int(B[q, 6]); nx = a; ny = b; nz = c
    for q in range(C.shape[0]):
        t, a, b, c = hit_cyl(C, q, ox, oy, oz, dx, dy, dz)
        if t < best: best = t; mat = int(C[q, 6]); nx = a; ny = b; nz = c
    t, a, b, c, _, _ = hit_dish(D, ox, oy, oz, dx, dy, dz)
    if t < best: best = t; mat = int(D[5]); nx = a; ny = b; nz = c
    return best, mat, nx, ny, nz

@njit(parallel=True, fastmath=True)
def clipper(GT, SK, JT, cam, fw, rt, up, fov, sun, jd, jang, jax, jrot, expo, out, ss, sc, B, C, D):
    H, W = out.shape[0], out.shape[1]
    tanf = math.tan(fov / 2)
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
                    # the spacecraft (metres round sc)
                    ox = (cam[0] - sc[0]) * 1000.0; oy = (cam[1] - sc[1]) * 1000.0; oz = (cam[2] - sc[2]) * 1000.0
                    ts, mat, nx, ny, nz = trace_sc(B, C, D, ox, oy, oz, dx, dy, dz)
                    t1, t2 = ray_sphere(cam[0], cam[1], cam[2], dx, dy, dz, 0.0, 0.0, 0.0, R_E)
                    if ts < 1e17 and (t1 <= 0 or ts / 1000.0 < t1):
                        hx_ = ox + dx * ts; hy_ = oy + dy * ts; hz_ = oz + dz * ts
                        # blankets: crinkled (bumped normals)
                        if mat == 1 or mat == 8:
                            e1 = vn2(hx_ * 7.0 + hz_ * 3.1, hy_ * 7.0 - hz_ * 2.3) - 0.5
                            e2 = vn2(hx_ * 7.0 - hz_ * 2.7 + 9.1, hy_ * 7.0 + hz_ * 3.3) - 0.5
                            e3 = vn2(hx_ * 23.0 + hz_ * 11.0, hy_ * 23.0 - hz_ * 7.0) - 0.5
                            nx += 0.55 * e1 + 0.2 * e3; ny += 0.55 * e2 - 0.2 * e3; nz += 0.4 * (e1 - e2)
                            nl = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nl; ny /= nl; nz /= nl
                        lam = nx * sun[0] + ny * sun[1] + nz * sun[2]
                        sh = 1.0
                        if lam > 0:
                            st, _, _, _, _ = trace_sc(B, C, D, hx_ + nx * 0.005, hy_ + ny * 0.005, hz_ + nz * 0.005, sun[0], sun[1], sun[2])
                            if st < 1e17: sh = 0.0
                        lam = max(lam, 0.0) * sh
                        hx = sun[0] - dx; hy = sun[1] - dy; hz = sun[2] - dz; hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                        sp = max(0.0, (nx * hx + ny * hy + nz * hz) / hl) * sh
                        # the bright ice below fills the undersides; Jupiter-shine
                        amb = 0.05 + 0.16 * max(0.0, -nz) ** 1.2
                        jl = max(0.0, nx * jd[0] + ny * jd[1] + nz * jd[2]) * 0.03
                        li = lam * 1.0 + amb + jl
                        if mat == 1:
                            r = li * 0.80 + sp ** 18 * 1.6; g = li * 0.56 + sp ** 18 * 1.2; b = li * 0.20 + sp ** 18 * 0.5
                        elif mat == 8:
                            r = li * 0.62 + sp ** 18 * 1.4; g = li * 0.63 + sp ** 18 * 1.4; b = li * 0.66 + sp ** 18 * 1.45
                        elif mat == 2:
                            r = li * 0.88 + sp ** 25 * 0.4; g = li * 0.88 + sp ** 25 * 0.4; b = li * 0.90 + sp ** 25 * 0.42
                        elif mat == 3:
                            if nz > 0.5:
                                # cells: dark blue, a silver grid, a gentle sheen
                                gx_ = (abs(hx_) * 5.2) % 1.0; gy_ = (hy_ * 3.4 + 0.5) % 1.0
                                ln = 1.0 if (gx_ < 0.05 or gy_ < 0.035) else 0.0
                                bus = 1.0 if abs(abs(hy_) - 2.0) < 0.04 else 0.0
                                cell = 0.9 + 0.2 * vn2(hx_ * 3.0, hy_ * 3.0)
                                r = li * (0.025 * cell + 0.30 * ln + 0.4 * bus) + sp ** 60 * 2.0 + sp ** 8 * 0.05
                                g = li * (0.035 * cell + 0.30 * ln + 0.4 * bus) + sp ** 60 * 2.0 + sp ** 8 * 0.06
                                b = li * (0.11 * cell + 0.32 * ln + 0.4 * bus) + sp ** 60 * 2.1 + sp ** 8 * 0.10
                            elif nz < -0.5:
                                r = li * 0.55; g = li * 0.55; b = li * 0.57
                            else:
                                r = li * 0.25; g = li * 0.25; b = li * 0.27
                        elif mat == 5:
                            r = li * 0.6 + sp ** 30 * 1.5; g = r; b = r * 1.03
                        elif mat == 7:
                            r = li * 0.35 + sp ** 12 * 0.8; g = li * 0.33 + sp ** 12 * 0.75; b = li * 0.32 + sp ** 12 * 0.7
                        else:
                            r = li * 0.09 + sp ** 10 * 0.25; g = r; b = r * 1.08
                    elif t1 > 0:
                        px = cam[0] + dx * t1; py = cam[1] + dy * t1; pz = cam[2] + dz * t1
                        nx = px / R_E; ny = py / R_E; nz = pz / R_E
                        lat = math.asin(max(-1.0, min(1.0, nz))); lon = math.atan2(ny, nx)
                        tr, tg, tb = tex2(GT, lon / (2 * math.pi), 0.5 - lat / math.pi)
                        tr *= tr; tg *= tg; tb *= tb
                        lam = nx * sun[0] + ny * sun[1] + nz * sun[2]
                        mu = -(nx * dx + ny * dy + nz * dz)
                        li = max(lam, 0.0) / (max(lam, 0.0) + max(mu, 0.02)) * 2.0 * 0.7
                        li = li * 0.9 + 0.1 * max(lam, 0.0)
                        # the spacecraft's shadow on the ice is far too small to see from here; Jupiter-shine
                        jl = max(0.0, nx * jd[0] + ny * jd[1] + nz * jd[2]) * 0.02
                        r = tr * (li * 1.9 + jl); g = tg * (li * 1.9 + jl * 0.8); b = tb * (li * 1.9 + jl * 0.62)
                    else:
                        r, g, b = sky(SK, JT, dx, dy, dz, sun, jd, jang, jax, jrot, 1.0)
                    acr += r; acg += g; acb += b
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k
