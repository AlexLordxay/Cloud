# «А ти уявляєш Титан так?» — the renderers (numba, CPU, ray tracing).
#   space():   km. Titan (R 2575 km) with its haze: an exponential orange haze (scale height 55 km) and the thin detached
#              blue haze layer at ~500 km, single scattering of sunlight (Henyey–Greenstein) with the sun's path through the
#              haze by the Chapman function (so the terminator glows and the night side shows a lit ring of haze);
#              the surface faintly through it (Cassini VIMS map as albedo, the northern seas dark). Saturn behind
#              (oblate, its rings in Titan's orbital plane: seen almost edge-on from here, as from Titan), the rings' shadow
#              on Saturn, Mercury beside Titan at true scale, stars.
#   surface(): metres. A height field (prep.py) under Titan's thick air: orange skylight from everywhere, the Sun only a
#              brighter glow, strong aerial perspective. Liquid methane at z = 0: a dark mirror with tiny ripples and
#              Fresnel reflections of the sky. Optionally the «Dragonfly» rotorcraft (boxes, cylinders, blurred rotors),
#              with its soft shadow on the ground.
import math
import numpy as np
from numba import njit, prange

R_T = 2575.0
R_A = R_T + 700.0
H_HAZE = 75.0
K_HAZE = 0.046          # extinction at the surface, 1/km (vertical optical depth ~3.4 in the visible)
DET_H, DET_W, DET_K = 500.0, 16.0, 0.00035
R_M = 2439.7
S_REQ, S_RPO = 60268.0, 54364.0
RING_IN, RING_OUT = 74500.0, 140220.0

@njit(fastmath=True, inline='always')
def tex2(T, u, v):
    h, w = T.shape[0], T.shape[1]
    x = (u - math.floor(u)) * w - 0.5; y = min(max(v, 0.0), 1.0) * (h - 1)
    i = int(math.floor(x)); j = int(y); fx = x - i; fy = y - j
    i0 = i % w; i1 = (i + 1) % w; j1 = min(j + 1, h - 1)
    r = (T[j, i0, 0] * (1 - fx) + T[j, i1, 0] * fx) * (1 - fy) + (T[j1, i0, 0] * (1 - fx) + T[j1, i1, 0] * fx) * fy
    g = (T[j, i0, 1] * (1 - fx) + T[j, i1, 1] * fx) * (1 - fy) + (T[j1, i0, 1] * (1 - fx) + T[j1, i1, 1] * fx) * fy
    b = (T[j, i0, 2] * (1 - fx) + T[j, i1, 2] * fx) * (1 - fy) + (T[j1, i0, 2] * (1 - fx) + T[j1, i1, 2] * fx) * fy
    return r, g, b

@njit(fastmath=True, inline='always')
def hs(i, j, s):
    v = math.sin(i * 127.1 + j * 311.7 + s * 74.7) * 43758.5453
    return v - math.floor(v)

@njit(fastmath=True, inline='always')
def vn(x, y, s):
    i = math.floor(x); j = math.floor(y); fx = x - i; fy = y - j
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    return (hs(i, j, s) * (1 - fx) + hs(i + 1, j, s) * fx) * (1 - fy) + (hs(i, j + 1, s) * (1 - fx) + hs(i + 1, j + 1, s) * fx) * fy

@njit(fastmath=True, inline='always')
def stars(SK, dx, dy, dz, pix):
    # sharp procedural stars (a texture would blur on the long-lens shots): one candidate star per 0.25° cell, a power-law
    # of brightnesses, drawn as a point about a pixel wide; plus a trace of the Milky Way from the texture
    lon = math.atan2(dx, -dy); lat = math.asin(max(-1.0, min(1.0, dz)))
    cs = 0.25 * math.pi / 180
    ci = math.floor(lon / cs); cj = math.floor(lat / cs)
    r = 0.0; g = 0.0; b = 0.0
    for oj in range(-1, 2):
        for oi in range(-1, 2):
            i = ci + oi; j = cj + oj
            h = hs(i, j, 41.0)
            if h < 0.10:
                sl = (i + hs(i, j, 42.0)) * cs; sb = (j + hs(i, j, 43.0)) * cs
                dl = (lon - sl) * math.cos(lat); db = lat - sb
                d2 = (dl * dl + db * db) / (pix * pix * 0.55)
                if d2 < 9.0:
                    m = 0.25 * (0.02 + hs(i, j, 44.0)) ** -0.9 * 0.22
                    k = m * math.exp(-d2)
                    tint = hs(i, j, 45.0)
                    r += k * (0.85 + 0.3 * tint); g += k * 0.92; b += k * (1.15 - 0.3 * tint)
    u = lon / (2 * math.pi) + 0.5; v = 0.5 - lat / math.pi
    tr, tg, tb = tex2(SK, u, v)
    return r + max(0.0, tr - 0.30) * 0.03, g + max(0.0, tg - 0.30) * 0.03, b + max(0.0, tb - 0.30) * 0.035

@njit(fastmath=True, inline='always')
def ray_sphere(ox, oy, oz, dx, dy, dz, cx, cy, cz, R):
    lx = ox - cx; ly = oy - cy; lz = oz - cz
    b = lx * dx + ly * dy + lz * dz; c = lx * lx + ly * ly + lz * lz - R * R
    disc = b * b - c
    if disc < 0: return 1e30, 1e30
    s = math.sqrt(disc)
    return -b - s, -b + s

@njit(fastmath=True, inline='always')
def chapman(X, mu):
    # Schüler's approximation of the Chapman function (mu >= 0)
    c = math.sqrt(X * math.pi / 2)
    return c / ((c - 1) * mu + 1)

@njit(fastmath=True, inline='always')
def sun_tau(px, py, pz, sx, sy, sz):
    # optical depth of the main haze from point p (km, Titan-centred) toward the Sun; -1 if Titan itself blocks the Sun
    r = math.sqrt(px * px + py * py + pz * pz)
    mu = (px * sx + py * sy + pz * sz) / r
    h = r - R_T
    X = r / H_HAZE
    if mu >= 0:
        return K_HAZE * H_HAZE * math.exp(-h / H_HAZE) * chapman(X, mu)
    sn = math.sqrt(max(0.0, 1 - mu * mu)); rt = r * sn            # the ray's closest approach to the centre
    if rt < R_T: return -1.0
    x0 = rt / H_HAZE
    return K_HAZE * H_HAZE * (2 * math.sqrt(x0 * math.pi / 2) * math.exp(-(rt - R_T) / H_HAZE)
                              - math.exp(-h / H_HAZE) * chapman(X, -mu))

@njit(fastmath=True, inline='always')
def hg(c, g):
    return (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * c) ** 1.5)

@njit(fastmath=True)
def titan_albedo(TT, LK, nx, ny, nz, rot):
    lon = math.atan2(ny, nx) + rot; lat = math.asin(max(-1.0, min(1.0, nz)))
    u = lon / (2 * math.pi) + 0.5; v = 0.5 - lat / math.pi
    r, g, b = tex2(TT, u, v); lk, _, _ = tex2(LK, u, v)
    L = 0.30 * r + 0.55 * g + 0.15 * b
    a = 0.035 + 0.24 * L
    a *= 1 - 0.75 * lk
    return a * 1.15, a * 0.82, a * 0.55

@njit(fastmath=True)
def saturn_hit(ox, oy, oz, dx, dy, dz, S, ex, ey, ez):
    # Saturn as an ellipsoid; (ex, ey, ez) its frame (ez = spin axis); returns t and the local hit point
    lx = ox - S[0]; ly = oy - S[1]; lz = oz - S[2]
    qx = lx * ex[0] + ly * ex[1] + lz * ex[2]; qy = lx * ey[0] + ly * ey[1] + lz * ey[2]; qz = lx * ez[0] + ly * ez[1] + lz * ez[2]
    vx = dx * ex[0] + dy * ex[1] + dz * ex[2]; vy = dx * ey[0] + dy * ey[1] + dz * ey[2]; vz = dx * ez[0] + dy * ez[1] + dz * ez[2]
    k = S_REQ / S_RPO
    qz *= k; vz *= k
    a = vx * vx + vy * vy + vz * vz; b = qx * vx + qy * vy + qz * vz; c = qx * qx + qy * qy + qz * qz - S_REQ * S_REQ
    disc = b * b - a * c
    if disc < 0: return 1e30, 0.0, 0.0, 0.0
    t = (-b - math.sqrt(disc)) / a
    if t < 0: return 1e30, 0.0, 0.0, 0.0
    return t, qx + vx * t, qy + vy * t, (qz + vz * t) / k

@njit(fastmath=True)
def space(TT, LK, ST, RG, MT, SK, cam, fw, rt, up, fov, sun, S, ex, ey, ez, mpos, mvis, trot, expo, out, ss):
    H, W = out.shape[0], out.shape[1]
    f = (H / 2) / math.tan(fov / 2)
    sx, sy, sz = sun[0], sun[1], sun[2]
    for py_ in prange(H):
        for px_ in range(W):
            acr = 0.0; acg = 0.0; acb = 0.0
            for sj in range(ss):
                for si in range(ss):
                    u = px_ + (si + 0.5) / ss - W / 2; v = H / 2 - (py_ + (sj + 0.5) / ss)
                    dx = fw[0] * f + rt[0] * u + up[0] * v; dy = fw[1] * f + rt[1] * u + up[1] * v; dz = fw[2] * f + rt[2] * u + up[2] * v
                    dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
                    ox, oy, oz = cam[0], cam[1], cam[2]
                    # what the ray ends on: Titan, Mercury, Saturn, its rings, or the sky
                    cr = 0.0; cg = 0.0; cb = 0.0
                    tend = 1e30
                    t0, t1 = ray_sphere(ox, oy, oz, dx, dy, dz, 0.0, 0.0, 0.0, R_T)
                    if t0 > 0 and t0 < tend:
                        tend = t0
                        px = ox + dx * t0; py = oy + dy * t0; pz = oz + dz * t0
                        nx = px / R_T; ny = py / R_T; nz = pz / R_T
                        ar, ag, ab = titan_albedo(TT, LK, nx, ny, nz, trot)
                        tau = sun_tau(px * 1.0005, py * 1.0005, pz * 1.0005, sx, sy, sz)
                        ndl = nx * sx + ny * sy + nz * sz
                        if tau >= 0 and ndl > 0:
                            # the sunlight reaching the ground is mostly diffused by the haze: direct + a soft wrap
                            tr = math.exp(-tau)
                            dif = ndl * tr + 0.25 * max(0.0, ndl + 0.2) * (1 - tr) * 0.6
                            cr = ar * dif * 1.0; cg = ag * dif * 0.80; cb = ab * dif * 0.55
                    hitm = False
                    if mvis > 0:
                        m0, m1 = ray_sphere(ox, oy, oz, dx, dy, dz, mpos[0], mpos[1], mpos[2], R_M)
                        if m0 > 0 and m0 < tend:
                            tend = m0; hitm = True
                            px = ox + dx * m0 - mpos[0]; py = oy + dy * m0 - mpos[1]; pz = oz + dz * m0 - mpos[2]
                            nx = px / R_M; ny = py / R_M; nz = pz / R_M
                            lon = math.atan2(ny, nx); lat = math.asin(max(-1.0, min(1.0, nz)))
                            r, g, b = tex2(MT, lon / (2 * math.pi) + 0.5, 0.5 - lat / math.pi)
                            ndl = max(0.0, nx * sx + ny * sy + nz * sz)
                            # Mercury fades in (mvis < 1): blend toward the background below
                            cr = r * ndl * 0.85 * mvis; cg = g * ndl * 0.85 * mvis; cb = b * ndl * 0.85 * mvis
                    if tend > 1e29:
                        # Saturn and the rings, far behind
                        ts, qx, qy, qz = saturn_hit(ox, oy, oz, dx, dy, dz, S, ex, ey, ez)
                        # the ring plane (through Saturn's centre, normal ez)
                        dn = dx * ez[0] + dy * ez[1] + dz * ez[2]
                        tr_ = 1e30
                        if abs(dn) > 1e-9:
                            tr_ = ((S[0] - ox) * ez[0] + (S[1] - oy) * ez[1] + (S[2] - oz) * ez[2]) / dn
                        br = 0.0; bg = 0.0; bb = 0.0; ba = 0.0     # the ring layer (in front of or behind Saturn)
                        if tr_ > 0:
                            rx = ox + dx * tr_ - S[0]; ry = oy + dy * tr_ - S[1]; rz = oz + dz * tr_ - S[2]
                            rr = math.sqrt(rx * rx + ry * ry + rz * rz)
                            if rr > RING_IN and rr < RING_OUT:
                                k = (rr - RING_IN) / (RING_OUT - RING_IN)
                                hh = RG.shape[1]; fx_ = min(hh - 1.001, max(0.0, k * hh - 0.5)); xi = int(fx_); xf = fx_ - xi
                                al = RG[0, xi, 3] * (1 - xf) + RG[0, xi + 1, 3] * xf
                                # ringlets: fine radial structure finer than the profile (tens of km)
                                rn = 0.5 * vn(rr / 160.0, 0.5, 50.0) + 0.3 * vn(rr / 55.0, 0.5, 51.0) + 0.2 * vn(rr / 21.0, 0.5, 52.0)
                                rgl = 0.72 + 0.56 * rn
                                al = min(1.0, al * (0.85 + 0.3 * rn))
                                # Saturn's shadow on the rings
                                a0, a1 = ray_sphere(rx, ry, rz, sx, sy, sz, 0.0, 0.0, 0.0, S_RPO)
                                lit = 0.04 if a0 > 0 and a0 < 1e29 else 1.0
                                # nearly edge-on: thin but optically thick — boost the opacity with the slant
                                al = 1 - (1 - al) ** (1.0 / max(0.03, abs(dn)) * 0.05 + 1.0)
                                sl = abs(sx * ez[0] + sy * ez[1] + sz * ez[2])
                                lv = lit * (0.35 + 1.6 * sl)
                                lv *= rgl
                                br = (RG[0, xi, 0] * (1 - xf) + RG[0, xi + 1, 0] * xf) * lv * 1.02
                                bg = (RG[0, xi, 1] * (1 - xf) + RG[0, xi + 1, 1] * xf) * lv * 0.96
                                bb = (RG[0, xi, 2] * (1 - xf) + RG[0, xi + 1, 2] * xf) * lv * 0.88; ba = al
                        if ts < 1e29:
                            nx = qx / S_REQ; ny = qy / S_REQ; nz = qz * S_REQ / (S_RPO * S_RPO)
                            nl = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nl; ny /= nl; nz /= nl
                            lsx = sx * ex[0] + sy * ex[1] + sz * ex[2]; lsy = sx * ey[0] + sy * ey[1] + sz * ey[2]; lsz = sx * ez[0] + sy * ez[1] + sz * ez[2]
                            ndl = max(0.0, nx * lsx + ny * lsy + nz * lsz)
                            lat = math.asin(max(-1.0, min(1.0, qz / S_RPO)))
                            lon = math.atan2(qy, qx)
                            r, g, b = tex2(ST, lon / (2 * math.pi) + 0.5, 0.5 - lat / math.pi)
                            # more contrast in the belts, and finer bands with a little turbulence than the map holds
                            r = 0.72 + (r - 0.72) * 1.55; g = 0.68 + (g - 0.68) * 1.6; b = 0.58 + (b - 0.58) * 1.6
                            wob = vn(lon * 18.0, lat * 60.0, 61.0) - 0.5
                            fb = 1.0 + 0.045 * math.sin(lat * 150.0 + 2.5 * wob) + 0.03 * math.sin(lat * 61.0 + 1.3) + 0.04 * (vn(lon * 50.0, lat * 400.0, 62.0) - 0.5)
                            r *= fb; g *= fb; b *= fb
                            # the hexagon around the north pole (~78° N), its blue-grey centre and the dark polar vortex
                            if lat > 1.2:
                                ph_ = math.atan2(qy, qx) + 0.3
                                seg = (ph_ % (math.pi / 3)) - math.pi / 6
                                rhex = 0.205 * math.cos(math.pi / 6) / math.cos(seg)
                                rho_ = math.cos(lat)
                                if rho_ < rhex:
                                    w_ = min(1.0, (rhex - rho_) / 0.02)
                                    r = r * (1 - 0.30 * w_); g = g * (1 - 0.22 * w_); b = b * (1 - 0.06 * w_)
                                    if rho_ > rhex - 0.025:
                                        r *= 0.85; g *= 0.85; b *= 0.88
                                    pv = math.exp(-(rho_ / 0.035) ** 2)
                                    r *= 1 - 0.45 * pv; g *= 1 - 0.40 * pv; b *= 1 - 0.30 * pv
                            # the rings' shadow on the globe
                            sh = 1.0
                            if abs(lsz) > 1e-6:
                                tq = -qz / lsz
                                if tq > 0:
                                    ax_ = qx + lsx * tq; ay_ = qy + lsy * tq
                                    rr = math.sqrt(ax_ * ax_ + ay_ * ay_)
                                    if rr > RING_IN and rr < RING_OUT:
                                        k = (rr - RING_IN) / (RING_OUT - RING_IN)
                                        hh = RG.shape[1]; xi = min(hh - 1, max(0, int(k * hh)))
                                        sh = 1 - 0.85 * RG[0, xi, 3]
                            vdx = dx * ex[0] + dy * ex[1] + dz * ex[2]; vdy = dx * ey[0] + dy * ey[1] + dz * ey[2]; vdz = dx * ez[0] + dy * ez[1] + dz * ez[2]
                            muv = max(0.0, -(nx * vdx + ny * vdy + nz * vdz))
                            lim = (0.55 + 0.45 * ndl ** 0.5) * (0.45 + 0.55 * muv ** 0.45)
                            cr = r * ndl * sh * lim * 0.78; cg = g * ndl * sh * lim * 0.72; cb = b * ndl * sh * lim * 0.64
                            if ba > 0 and tr_ < ts:
                                cr = cr * (1 - ba) + br * ba; cg = cg * (1 - ba) + bg * ba; cb = cb * (1 - ba) + bb * ba
                        else:
                            cr, cg, cb = stars(SK, dx, dy, dz, fov / H)
                            # the Sun: a tiny bright disc with a glow (bloom adds the rest)
                            cs = dx * sx + dy * sy + dz * sz
                            if cs > 0.99995: cr += 40.0; cg += 38.0; cb += 34.0
                            if ba > 0:
                                cr = cr * (1 - ba) + br * ba; cg = cg * (1 - ba) + bg * ba; cb = cb * (1 - ba) + bb * ba
                    # the haze along the ray up to tend
                    a0, a1 = ray_sphere(ox, oy, oz, dx, dy, dz, 0.0, 0.0, 0.0, R_A)
                    if a1 > 0 and a0 < 1e29:
                        ts_ = max(0.0, a0); te_ = min(a1, tend)
                        trr = 1.0; trg = 1.0; trb = 1.0
                        sr = 0.0; sg = 0.0; sb = 0.0
                        cth = dx * sx + dy * sy + dz * sz
                        ph = 0.7 * hg(cth, 0.62) + 0.3 * hg(cth, -0.2)
                        phd = 0.5 * hg(cth, 0.3) + 0.5 / (4 * math.pi)
                        t = ts_
                        it = 0
                        while t < te_ and it < 260:
                            it += 1
                            px = ox + dx * t; py = oy + dy * t; pz = oz + dz * t
                            r_ = math.sqrt(px * px + py * py + pz * pz); h = r_ - R_T
                            dt = min(60.0, max(1.2, 0.30 * (h + 6.0)))
                            ddet = abs(h - DET_H)
                            if ddet < 120: dt = min(dt, max(3.0, ddet * 0.4))
                            dt = min(dt, te_ - t)
                            tm = t + dt * 0.5
                            px = ox + dx * tm; py = oy + dy * tm; pz = oz + dz * tm
                            r_ = math.sqrt(px * px + py * py + pz * pz); h = max(0.0, r_ - R_T)
                            la_ = pz / r_
                            rho = K_HAZE * math.exp(-h / H_HAZE) * (1.0 + 0.10 * math.sin(la_ * 9.0 + 0.6) + 0.18 * max(0.0, la_ - 0.55))
                            nh = 1.0 - 0.16 * min(1.0, max(0.0, (la_ - 0.05) / 0.6))
                            rdet = DET_K * math.exp(-((h - DET_H) / DET_W) ** 2)
                            if rho + rdet > 1e-7:
                                tau = sun_tau(px, py, pz, sx, sy, sz)
                                if tau >= 0:
                                    lr = math.exp(-tau * 0.80); lg = math.exp(-tau * 1.0); lb = math.exp(-tau * 1.30)
                                else:
                                    lr = 0.0; lg = 0.0; lb = 0.0
                                # multiple scattering, crudely: a little light where the sun is up at that height
                                mu = (px * sx + py * sy + pz * sz) / r_
                                ms = 0.10 * max(0.0, min(1.0, (mu + 0.12) / 0.4)) * math.exp(-h / 200.0)
                                er = rho * 0.80 + rdet * 0.6; eg = rho * 1.0 + rdet * 0.9; eb = rho * 1.30 + rdet * 1.5
                                # scattering colours: the haze orange, the detached layer blue
                                s1r = rho * 0.95 * (lr * ph * 11.0 + ms); s1g = rho * 0.62 * nh * (lg * ph * 11.0 + ms); s1b = rho * 0.26 * nh * nh * (lb * ph * 11.0 + ms)
                                s2r = rdet * 0.40 * lr * phd * 9.0; s2g = rdet * 0.62 * lg * phd * 9.0; s2b = rdet * 1.10 * lb * phd * 9.0
                                sr += trr * (s1r + s2r) * dt; sg += trg * (s1g + s2g) * dt; sb += trb * (s1b + s2b) * dt
                                trr *= math.exp(-er * dt); trg *= math.exp(-eg * dt); trb *= math.exp(-eb * dt)
                            t += dt
                        cr = cr * trr + sr; cg = cg * trg + sg; cb = cb * trb + sb
                    acr += cr; acg += cg; acb += cb
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k


# ---------------------------------------------------------------- the surface (metres)

@njit(fastmath=True, inline='always')
def hf(Z, x, y, cell, half):
    # bilinear height (m) from the grid Z covering [-half, half]^2; clamped at the edges
    n = Z.shape[0]
    gx = (x + half) / cell; gy = (y + half) / cell
    gx = min(max(gx, 0.0), n - 1.001); gy = min(max(gy, 0.0), n - 1.001)
    i = int(gx); j = int(gy); fx = gx - i; fy = gy - j
    return (Z[j, i] * (1 - fx) + Z[j, i + 1] * fx) * (1 - fy) + (Z[j + 1, i] * (1 - fx) + Z[j + 1, i + 1] * fx) * fy

@njit(fastmath=True, inline='always')
def hdet(Z, x, y, cell, half, near):
    # the grid plus a little fine detail close to the camera
    h = hf(Z, x, y, cell, half)
    if near > 0:
        h += near * (vn(x / 31.0, y / 29.0, 3.0) - 0.5) * 1.2 + near * (vn(x / 9.0, y / 11.0, 5.0) - 0.5) * 0.25
    return h

@njit(fastmath=True, inline='always')
def skycol(dx, dy, dz, sx, sy, sz):
    # Titan's sky from the ground: orange all over, brighter low down and toward the Sun's side
    e = max(dz, -0.05)
    hz = math.exp(-max(e, 0.0) * 3.0)
    cs = dx * sx + dy * sy + dz * sz
    glow = 0.35 * math.exp((cs - 1) * 4.0) + 0.6 * math.exp((cs - 1) * 30.0)
    r = 0.30 + 0.42 * hz + glow * 0.9
    g = 0.14 + 0.27 * hz + glow * 0.60
    b = 0.045 + 0.11 * hz + glow * 0.28
    return r, g, b

# Dragonfly: boxes (cx cy cz hx hy hz mat) and z-cylinders (cx cy cz r z0 z1 mat), metres, x forward, z up.
# materials: 1 white body, 2 grey, 3 dark, 4 MMRTG (dark, ribbed), 5 dish (white), 9 rotor blur (translucent)
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
    # a paraboloid dish z - cz = depth (r / R)^2, r <= R (opening upward); normal toward the ray's side
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
                nx = -2 * k * x; ny = -2 * k * y; nz = 1.0; nl = math.sqrt(nx * nx + ny * ny + 1.0)
                nx /= nl; ny /= nl; nz /= nl
                if nx * dx + ny * dy + nz * dz > 0: nx = -nx; ny = -ny; nz = -nz
                return tt, nx, ny, nz
    return 1e18, 0.0, 0.0, 0.0

@njit(fastmath=True)
def trace_df(B, C, CX, D, ox, oy, oz, dx, dy, dz, rotor):
    # -> t, material, normal (local), and for rotors the index of the disc hit
    best = 1e18; mat = 0; nx = 0.0; ny = 0.0; nz = 0.0; qi = -1
    for q in range(B.shape[0]):
        t, a, b, c = hit_box(B, q, ox, oy, oz, dx, dy, dz)
        if t < best: best = t; mat = int(B[q, 6]); nx = a; ny = b; nz = c
    for q in range(C.shape[0]):
        if not rotor and int(C[q, 6]) == 9: continue
        t, a, b, c = hit_cyl(C, q, ox, oy, oz, dx, dy, dz)
        if t < best: best = t; mat = int(C[q, 6]); nx = a; ny = b; nz = c; qi = q
    # x-axis cylinders: the same test with the axes rotated (x, y, z) -> (y, z, x)
    for q in range(CX.shape[0]):
        t, a, b, c = hit_cyl(CX, q, oy, oz, ox, dy, dz, dx)
        if t < best: best = t; mat = int(CX[q, 6]); nx = c; ny = a; nz = b
    if D.shape[0] > 0:
        t, a, b, c = hit_dish(D[0], ox, oy, oz, dx, dy, dz)
        if t < best: best = t; mat = 5; nx = a; ny = b; nz = c
    return best, mat, nx, ny, nz, qi

@njit(fastmath=True)
def df_shade(mat, nx, ny, nz, sx, sy, sz, lx, ly, lz, dx, dy, dz):
    # a Dragonfly surface under Titan's diffuse orange light: (nx, ny, nz) world normal, (lx, ly, lz) the local hit point
    # (for seams and ribs), (dx, dy, dz) the view ray. Matte paint, white and silver thermal blankets with seams, gold
    # foil, dark carbon arms, the ribbed MMRTG; blankets and metal also reflect the sky.
    sky = 0.50 + 0.50 * nz
    gnd = 0.22 * max(0.0, -nz)
    sun = 0.55 * max(0.0, nx * sx + ny * sy + nz * sz)
    lt = sky + gnd + sun
    # under the body it is darker (ambient occlusion, crudely)
    if lz < -0.4 and nz < 0.5: lt *= 0.75
    met = 0.0
    if mat == 1:
        r, g, b = 0.82, 0.81, 0.78; met = 0.12
        # blanket seams and quilting
        sx_ = abs((lx / 0.52) - math.floor(lx / 0.52 + 0.5)); sz_ = abs((lz / 0.30) - math.floor(lz / 0.30 + 0.5))
        sy_ = abs((ly / 0.50) - math.floor(ly / 0.50 + 0.5))
        sm_ = min(sx_, min(sz_ if abs(nz) < 0.5 else 1.0, sy_ if abs(nz) > 0.5 else 1.0))
        if sm_ < 0.025: r *= 0.62; g *= 0.62; b *= 0.62
        q_ = vn(lx * 9.0, (ly + lz) * 9.0, 71.0)
        r *= 0.93 + 0.12 * q_; g *= 0.93 + 0.12 * q_; b *= 0.93 + 0.12 * q_
    elif mat == 2: r, g, b = 0.42, 0.43, 0.45; met = 0.35
    elif mat == 3: r, g, b = 0.07, 0.07, 0.08; met = 0.10
    elif mat == 4:
        rib = 0.5 + 0.5 * math.cos(math.atan2(lz - 0.05, ly) * 16.0)
        r, g, b = 0.10 + 0.10 * rib, 0.10 + 0.09 * rib, 0.10 + 0.08 * rib; met = 0.15
    elif mat == 5: r, g, b = 0.90, 0.89, 0.86
    elif mat == 6:
        w_ = vn(lx * 14.0, ly * 14.0, 72.0)
        r, g, b = 0.80 * (0.8 + 0.4 * w_), 0.58 * (0.8 + 0.4 * w_), 0.20 * (0.8 + 0.4 * w_); met = 0.45
    elif mat == 7: r, g, b = 0.62, 0.63, 0.66; met = 0.40       # silver blanket / deck
    elif mat == 8: r, g, b = 0.02, 0.02, 0.03; met = 0.6         # camera glass
    else: r, g, b = 0.12, 0.12, 0.13
    cr = r * lt * 1.0; cg = g * lt * 0.66; cb = b * lt * 0.36
    if met > 0:
        dn = dx * nx + dy * ny + dz * nz
        rx = dx - 2 * dn * nx; ry = dy - 2 * dn * ny; rz = dz - 2 * dn * nz
        er, eg, eb = skycol(rx, ry, max(rz, -0.2), sx, sy, sz)
        if rz < 0: er *= 0.55; eg *= 0.5; eb *= 0.45          # the ground below reflects darker
        fr = met + (1 - met) * 0.04 * (1 + dn) ** 5
        cr = cr * (1 - fr) + er * fr; cg = cg * (1 - fr) + eg * fr; cb = cb * (1 - fr) + eb * fr
    return cr, cg, cb

@njit(parallel=True, fastmath=True)
def surface(Z, AL, WL, cell, half, cam, fw, rt, up, fov, sun, expo, out, ss, fogk, tm, B, C, CX, D, dpos, dR, dvis, spin):
    H, W = out.shape[0], out.shape[1]
    f = (H / 2) / math.tan(fov / 2)
    sx, sy, sz = sun[0], sun[1], sun[2]
    # the soft light direction for the drone's shadow: mostly from above
    lx_ = sx * 0.5; ly_ = sy * 0.5; lz_ = sz * 0.5 + 1.0
    ll = math.sqrt(lx_ * lx_ + ly_ * ly_ + lz_ * lz_); lx_ /= ll; ly_ /= ll; lz_ /= ll
    for py_ in prange(H):
        for px_ in range(W):
            acr = 0.0; acg = 0.0; acb = 0.0
            for sj in range(ss):
                for si in range(ss):
                    u = px_ + (si + 0.5) / ss - W / 2; v = H / 2 - (py_ + (sj + 0.5) / ss)
                    dx = fw[0] * f + rt[0] * u + up[0] * v; dy = fw[1] * f + rt[1] * u + up[1] * v; dz = fw[2] * f + rt[2] * u + up[2] * v
                    dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
                    ox, oy, oz = cam[0], cam[1], cam[2]
                    cr = 0.0; cg = 0.0; cb = 0.0
                    # the drone first (in its own frame)
                    tdf = 1e18; mat = 0; dnx = 0.0; dny = 0.0; dnz = 0.0; rot_a = 0.0
                    rr_ = 0.0; rg_ = 0.0; rb_ = 0.0
                    if dvis > 0:
                        qx = ox - dpos[0]; qy = oy - dpos[1]; qz = oz - dpos[2]
                        lox = qx * dR[0, 0] + qy * dR[1, 0] + qz * dR[2, 0]
                        loy = qx * dR[0, 1] + qy * dR[1, 1] + qz * dR[2, 1]
                        loz = qx * dR[0, 2] + qy * dR[1, 2] + qz * dR[2, 2]
                        ldx = dx * dR[0, 0] + dy * dR[1, 0] + dz * dR[2, 0]
                        ldy = dx * dR[0, 1] + dy * dR[1, 1] + dz * dR[2, 1]
                        ldz = dx * dR[0, 2] + dy * dR[1, 2] + dz * dR[2, 2]
                        b0, b1 = ray_sphere(lox, loy, loz, ldx, ldy, ldz, -0.2, 0.0, 0.0, 3.4)
                        if b0 < 1e29 and b1 > 0:
                            t, mat, a, b, c, qi = trace_df(B, C, CX, D, lox, loy, loz, ldx, ldy, ldz, True)
                            if t < 1e17:
                                if mat == 9:
                                    # a spinning two-bladed rotor: a faint disc, two blurred blade ghosts, a darker tip ring
                                    hx = lox + ldx * t - C[qi, 0]; hy = loy + ldy * t - C[qi, 1]
                                    rr0 = math.sqrt(hx * hx + hy * hy) / C[qi, 3]
                                    ang = math.atan2(hy, hx) - spin * (1.0 if (qi % 2) == 0 else -1.0)
                                    da = abs(((ang % math.pi) + math.pi) % math.pi - math.pi / 2) - math.pi / 2
                                    bl = math.exp(-(da / (0.22 + 0.25 * (1 - rr0))) ** 2)
                                    rot_a = (0.14 + 0.55 * bl) * min(1.0, rr0 / 0.15) + 0.25 * math.exp(-((rr0 - 0.97) / 0.03) ** 2)
                                    rr_ = 0.05; rg_ = 0.05; rb_ = 0.05
                                    t2, mat2, a2, b2, c2, q2 = trace_df(B, C, CX, D, lox, loy, loz, ldx, ldy, ldz, False)
                                    if t2 < 1e17:
                                        tdf = t2; mat = mat2; a = a2; b = b2; c = c2
                                    else:
                                        tdf = 1e18
                                else:
                                    tdf = t
                                if tdf < 1e17:
                                    dnx = a * dR[0, 0] + b * dR[0, 1] + c * dR[0, 2]
                                    dny = a * dR[1, 0] + b * dR[1, 1] + c * dR[1, 2]
                                    dnz = a * dR[2, 0] + b * dR[2, 1] + c * dR[2, 2]
                                    hx = lox + ldx * tdf; hy = loy + ldy * tdf; hz = loz + ldz * tdf
                                    cr, cg, cb = df_shade(mat, dnx, dny, dnz, sx, sy, sz, hx, hy, hz, dx, dy, dz)
                    if tdf > 1e17:
                        # the ground / the sea
                        t = 0.5; hit = 0; tmax = 90000.0
                        lastd = 0.0; lastt = 0.0
                        # start where the ray enters the slab below the highest ground
                        zmax = 600.0
                        if oz > zmax:
                            if dz >= 0: t = tmax + 1
                            else: t = (oz - zmax) / (-dz)
                        it = 0
                        while t < tmax and it < 420:
                            it += 1
                            x = ox + dx * t; y = oy + dy * t; z = oz + dz * t
                            if z > zmax and dz > 0: break
                            near = 1.0 if t < 600 else 0.0
                            h = hdet(Z, x, y, cell, half, near)
                            hw = max(h, hf(WL, x, y, cell, half))
                            d = z - hw
                            if d < 0:
                                # refine between lastt and t
                                a_ = lastt; b_ = t
                                for _ in range(7):
                                    m_ = 0.5 * (a_ + b_)
                                    xm = ox + dx * m_; ym = oy + dy * m_; zm = oz + dz * m_
                                    hm = max(hdet(Z, xm, ym, cell, half, near), hf(WL, xm, ym, cell, half))
                                    if zm - hm < 0: b_ = m_
                                    else: a_ = m_
                                t = 0.5 * (a_ + b_)
                                hit = 1
                                break
                            lastt = t
                            t += max(0.35 * d / max(0.12, -dz + 0.12), 0.6 + t * 0.0016)
                        if hit:
                            x = ox + dx * t; y = oy + dy * t; z = oz + dz * t
                            near = 1.0 if t < 600 else 0.0
                            h = hdet(Z, x, y, cell, half, near)
                            wl = hf(WL, x, y, cell, half)
                            if h < wl - 0.05:
                                # liquid methane: a dark mirror with tiny ripples
                                e = 0.6 + t * 0.002
                                nx = (vn(x / 9.0 + tm * 0.35, y / 11.0, 7.0) - vn(x / 9.0 + tm * 0.35 + 0.5, y / 11.0, 7.0)) * 0.02 \
                                     + (vn(x / 2.3 - tm * 0.8, y / 2.9, 8.0) - 0.5) * 0.015 / (1 + t * 0.002)
                                ny = (vn(x / 13.0, y / 8.0 + tm * 0.25, 9.0) - 0.5) * 0.025 \
                                     + (vn(x / 2.7, y / 2.1 + tm * 0.7, 10.0) - 0.5) * 0.015 / (1 + t * 0.002)
                                nz = 1.0
                                nl = math.sqrt(nx * nx + ny * ny + 1.0); nx /= nl; ny /= nl; nz /= nl
                                dn = dx * nx + dy * ny + dz * nz
                                rx = dx - 2 * dn * nx; ry = dy - 2 * dn * ny; rz = max(0.005, dz - 2 * dn * nz)
                                ci = min(1.0, max(0.0, -dn))
                                fr = 0.016 + 0.984 * (1 - ci) ** 5
                                kr, kg, kb = skycol(rx, ry, rz, sx, sy, sz)
                                # depth: the shallow edge shows the bottom a little
                                depth = max(0.0, wl - h)
                                sh = math.exp(-depth / 6.0)
                                br = 0.025 + 0.08 * sh; bg = 0.015 + 0.05 * sh; bb = 0.008 + 0.02 * sh
                                cr = kr * fr * 1.1 + br * (1 - fr); cg = kg * fr * 1.1 + bg * (1 - fr); cb = kb * fr * 1.1 + bb * (1 - fr)
                            else:
                                e = max(0.6, cell * 0.5) if t > 600 else 0.8
                                hx1 = hdet(Z, x + e, y, cell, half, near); hx0 = hdet(Z, x - e, y, cell, half, near)
                                hy1 = hdet(Z, x, y + e, cell, half, near); hy0 = hdet(Z, x, y - e, cell, half, near)
                                # (slopes exaggerated ×2.6 for the shading only: under Titan's flat light the relief would vanish)
                                nx = -(hx1 - hx0) / (2 * e) * 2.6; ny = -(hy1 - hy0) / (2 * e) * 2.6; nz = 1.0
                                nl = math.sqrt(nx * nx + ny * ny + 1.0); nx /= nl; ny /= nl; nz /= nl
                                ar = hf(AL, x, y, cell, half)
                                ar *= 0.90 + 0.20 * vn(x / 53.0, y / 47.0, 11.0)
                                # wet ground right at the shore is darker
                                wet = max(0.0, 1 - (h - wl) / 2.5)
                                ar *= 1 - 0.45 * wet
                                sky = 0.42 + 0.38 * nz
                                sun_ = 0.95 * max(0.0, nx * sx + ny * sy + nz * sz)
                                lt = sky + sun_
                                # the drone's soft shadow
                                if dvis > 0:
                                    qx = dpos[0] - x; qy = dpos[1] - y; qz = dpos[2] - z
                                    tq = qx * lx_ + qy * ly_ + qz * lz_
                                    if tq > 0:
                                        cx = qx - lx_ * tq; cy = qy - ly_ * tq; cz = qz - lz_ * tq
                                        dd = math.sqrt(cx * cx + cy * cy + cz * cz)
                                        rad = 1.9 + tq * 0.12
                                        s_ = min(1.0, max(0.0, (dd - rad * 0.55) / (rad * 0.9)))
                                        lt *= 1 - 0.42 * dvis * (1 - s_) * (2.2 / (2.2 + tq * 0.08))
                                cr = ar * lt * 0.85; cg = ar * lt * 0.46; cb = ar * lt * 0.19
                            # aerial perspective: the thick orange air
                            hr, hg_, hb = skycol(dx, dy, 0.02, sx, sy, sz)
                            fo = 1 - math.exp(-t * fogk)
                            cr = cr * (1 - fo) + hr * fo * 0.92; cg = cg * (1 - fo) + hg_ * fo * 0.92; cb = cb * (1 - fo) + hb * fo * 0.92
                        else:
                            cr, cg, cb = skycol(dx, dy, dz, sx, sy, sz)
                    else:
                        # the drone sits in the air too: a touch of haze for its distance
                        fo = 1 - math.exp(-tdf * fogk)
                        hr, hg_, hb = skycol(dx, dy, 0.02, sx, sy, sz)
                        cr = cr * (1 - fo) + hr * fo; cg = cg * (1 - fo) + hg_ * fo; cb = cb * (1 - fo) + hb * fo
                    if rot_a > 0:
                        cr = cr * (1 - rot_a) + rr_ * rot_a; cg = cg * (1 - rot_a) + rg_ * rot_a; cb = cb * (1 - rot_a) + rb_ * rot_a
                    acr += cr; acg += cg; acb += cb
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k


def tonemap(img):
    x = img * 0.9
    y = np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
    return y ** (1 / 2.2)

def bloom(img):
    from scipy.ndimage import gaussian_filter
    hi = np.clip(img - 1.0, 0, None)
    return img + 0.35 * gaussian_filter(hi, (6, 6, 0)) + 0.25 * gaussian_filter(hi, (24, 24, 0))
