# «У Землі колись могли бути кільця» — the renderers (numba, CPU, ray tracing). Units: km.
#   The ring: in the equatorial plane (z = 0 in Earth-centred coordinates), from 1.34 to 2.80 Earth radii (inside the
#   Roche limit, where the asteroid was torn apart), bands, a gap, fine ringlets; sunlit unless in the Earth's shadow
#   (a cylinder, with a reddened penumbra fringe: sunlight through the Earth's atmosphere).
#   kyiv():  Kyiv from a few hundred metres up (Sentinel-2 mosaic + SRTM heights in local km, the Earth's curvature),
#            at dusk or at night: a twilight sky (the glow toward the Sun, the Earth's shadow and the pink Belt of Venus
#            opposite), the ring across the southern sky, stars, the Dnipro as a rippled mirror, city lights, haze.
#   space(): the Earth from space with the ring: a paleogeographic map, clouds, the night side, an atmosphere limb,
#            the ring's shadow on the Earth and the Earth's on the ring; a depth buffer for particles drawn afterwards.
import math
import numpy as np
from numba import njit, prange

R = 6371.0
RIN, ROUT = 1.34 * R, 2.80 * R

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
def img2(T, x, y):
    # bilinear sample of a 2-D (h, w) or the first channel, x, y in pixels, clamped
    h, w = T.shape[0], T.shape[1]
    x = min(max(x, 0.0), w - 1.001); y = min(max(y, 0.0), h - 1.001)
    i = int(x); j = int(y); fx = x - i; fy = y - j
    return (T[j, i] * (1 - fx) + T[j, i + 1] * fx) * (1 - fy) + (T[j + 1, i] * (1 - fx) + T[j + 1, i + 1] * fx) * fy

@njit(fastmath=True, inline='always')
def img3(T, x, y):
    h, w = T.shape[0], T.shape[1]
    x = min(max(x, 0.0), w - 1.001); y = min(max(y, 0.0), h - 1.001)
    i = int(x); j = int(y); fx = x - i; fy = y - j
    r = (T[j, i, 0] * (1 - fx) + T[j, i + 1, 0] * fx) * (1 - fy) + (T[j + 1, i, 0] * (1 - fx) + T[j + 1, i + 1, 0] * fx) * fy
    g = (T[j, i, 1] * (1 - fx) + T[j, i + 1, 1] * fx) * (1 - fy) + (T[j + 1, i, 1] * (1 - fx) + T[j + 1, i + 1, 1] * fx) * fy
    b = (T[j, i, 2] * (1 - fx) + T[j, i + 1, 2] * fx) * (1 - fy) + (T[j + 1, i, 2] * (1 - fx) + T[j + 1, i + 1, 2] * fx) * fy
    return r, g, b

@njit(fastmath=True, inline='always')
def stars(SK, dx, dy, dz, pix):
    # sharp procedural stars, one candidate per 0.25° cell, a power law of brightness, ~a pixel wide
    lon = math.atan2(dy, dx); lat = math.asin(max(-1.0, min(1.0, dz)))
    cs = 0.25 * math.pi / 180
    ci = math.floor(lon / cs); cj = math.floor(lat / cs)
    r = 0.0; g = 0.0; b = 0.0
    for oj in range(-1, 2):
        for oi in range(-1, 2):
            i = ci + oi; j = cj + oj
            if hs(i, j, 41.0) < 0.12:
                sl = (i + hs(i, j, 42.0)) * cs; sb = (j + hs(i, j, 43.0)) * cs
                dl = (lon - sl) * math.cos(lat); db = lat - sb
                d2 = (dl * dl + db * db) / (pix * pix * 0.55)
                if d2 < 9.0:
                    m = 0.25 * (0.02 + hs(i, j, 44.0)) ** -0.9 * 0.22
                    k = m * math.exp(-d2); t = hs(i, j, 45.0)
                    r += k * (0.85 + 0.3 * t); g += k * 0.92; b += k * (1.15 - 0.3 * t)
    # the Milky Way's glow, faint
    u = lon / (2 * math.pi) + 0.5; v = 0.5 - lat / math.pi
    tr, tg, tb = tex2(SK, u, v)
    return r + max(0.0, tr - 0.06) * 0.08, g + max(0.0, tg - 0.06) * 0.08, b + max(0.0, tb - 0.06) * 0.09

# ---------------------------------------------------------------- the ring

# the ring's radial profile (r, g, b, opacity) from 1.30 to 2.75 R, made by prep.py (a constant for numba)
import os as _os
_RPF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', 'work', 'earth_rings', 'ring_profile.npy')
RP = np.ascontiguousarray(np.load(_RPF).astype(np.float32)) if _os.path.exists(_RPF) else np.zeros((2, 4), np.float32)

@njit(fastmath=True, inline='always')
def ring_prof(RP, r):
    # -> tau, r, g, b at radius r (km): the profile (bands, gaps) plus ringlets finer than the profile
    x = r / R
    if x < 1.30 or x > 2.75: return 0.0, 0.0, 0.0, 0.0
    n = RP.shape[0]
    k = (x - 1.30) / (2.75 - 1.30) * (n - 1)
    i = min(n - 2, int(k)); f = k - i
    a = RP[i, 3] * (1 - f) + RP[i + 1, 3] * f
    cr = RP[i, 0] * (1 - f) + RP[i + 1, 0] * f; cg = RP[i, 1] * (1 - f) + RP[i + 1, 1] * f; cb = RP[i, 2] * (1 - f) + RP[i + 1, 2] * f
    rl = 0.80 + 0.40 * vn(x * 2600.0, 0.5, 4.0) * 0.6 + 0.4 * vn(x * 900.0, 0.5, 3.0) * 0.4
    a = min(0.995, a * rl)
    tau = -math.log(max(1e-4, 1.0 - a)) * 0.55
    return tau, cr, cg, cb

@njit(fastmath=True, inline='always')
def ring_tau(r):
    t, a, b, c = ring_prof(RP, r)
    return t

@njit(fastmath=True, inline='always')
def shadow_earth(qx, qy, qz, sx, sy, sz):
    # sunlight reaching point q (Earth-centred): 1 lit, 0 in the umbra; the penumbra edge reddened (returns r, g, b)
    d = qx * sx + qy * sy + qz * sz
    if d >= 0: return 1.0, 1.0, 1.0
    rr = math.sqrt(max(0.0, qx * qx + qy * qy + qz * qz - d * d))
    e = (rr - R) / 380.0                         # across the edge: < 0 inside the Earth's shadow
    if e >= 1.0: return 1.0, 1.0, 1.0
    if e <= -0.4: return 0.0, 0.0, 0.0
    k = (e + 0.4) / 1.4
    # sunlight grazing the atmosphere: red first
    return min(1.0, k * 1.6), k ** 1.8, k ** 3.0

@njit(fastmath=True)
def ring_hit(px, py, pz, dx, dy, dz, sx, sy, sz):
    # the ring along the ray from p (Earth-centred): -> t, r, g, b (radiance, premultiplied), alpha
    if abs(dz) < 1e-9: return 1e30, 0.0, 0.0, 0.0, 0.0
    t = -pz / dz
    if t <= 0: return 1e30, 0.0, 0.0, 0.0, 0.0
    qx = px + dx * t; qy = py + dy * t
    r = math.sqrt(qx * qx + qy * qy)
    tau, pr, pg, pb = ring_prof(RP, r)
    if tau <= 0: return 1e30, 0.0, 0.0, 0.0, 0.0
    mu = abs(dz); mu0 = abs(sz)
    al = 1.0 - math.exp(-tau / max(mu, 0.02))
    lr, lg, lb = shadow_earth(qx, qy, 0.0, sx, sy, sz)
    # lit face seen (Sun and viewer on the same side) or the back, seen through (forward scattering, dimmer)
    same = (sz > 0) == (pz > 0)
    cth = -(dx * sx + dy * sy + dz * sz)
    if same:
        b_ = 0.75 * mu0 / (mu0 + mu) * (1 - math.exp(-tau * (1 / max(mu, 0.02) + 1 / max(mu0, 0.02)))) / max(al, 1e-4)
    else:
        b_ = 0.30 * math.exp(-tau / max(mu0, 0.05)) * (1.0 + 2.5 * max(0.0, -cth) ** 4)
    b_ *= 1.0 + 0.6 * max(0.0, cth) ** 6
    # dusty grey-beige rock (the profile's colours, a little greyer: chondrite, not water ice)
    cr = pr * 0.92 + 0.06; cg = pg * 0.90 + 0.05; cb = pb * 0.86 + 0.04
    k = b_ * al * 1.8
    return t, cr * k * lr, cg * k * lg, cb * k * lb, al

# ---------------------------------------------------------------- Kyiv at dusk / night

@njit(fastmath=True)
def twilight(ex, ey, ez, sx, sy, sz):
    # the sky's radiance in local east/north/up for a Sun below the horizon; (sx, sy, sz) the Sun's local direction
    e = math.degrees(math.asin(max(-1.0, min(1.0, ez))))
    hsun = math.degrees(math.asin(max(-1.0, min(1.0, sz))))
    cg = ex * sx + ey * sy + ez * sz
    gam = math.degrees(math.acos(max(-1.0, min(1.0, cg))))
    ee = max(e, 0.0)
    B = math.exp(hsun / 3.6)                                   # overall: falls ~e-fold every 3.6° the Sun sinks
    # zenith blue, deepening
    r = 0.045 * B; g = 0.095 * B; b = 0.23 * B
    # the bright, warm glow above the sunset point
    sh = math.exp(-gam / 32.0) * math.exp(-ee / 7.0) * math.exp(hsun / 3.0) * 2.2
    r += sh * 1.0; g += sh * 0.42; b += sh * 0.12
    # general horizon brightening (more air), cooler
    hb = math.exp(-ee / 9.0) * B
    r += hb * 0.16; g += hb * 0.19; b += hb * 0.28
    # opposite the Sun: the Earth's shadow (a slate-blue band rising as the Sun sinks) with the pink Belt of Venus above
    anti = max(0.0, -cg)
    es = max(0.5, -hsun * 1.0)
    belt = math.exp(-((e - es - 3.0) / 3.2) ** 2) * anti ** 1.5 * math.exp(hsun / 5.0)
    r += belt * 0.42; g += belt * 0.22; b += belt * 0.26
    if e < es:
        dim = 0.55 + 0.45 * (e / es) if e > 0 else 0.55
        k = 1 - (1 - dim) * anti
        r *= k; g *= k; b *= k * 1.05
    # night: airglow, a faint greenish band low down
    ag = 0.004 * math.exp(-ee / 12.0)
    r += ag * 0.6; g += ag * 1.0; b += ag * 0.7
    return r, g, b

@njit(fastmath=True)
def lamps(x, y, dens, fp, tm):
    # city lights: a lamp per ~14 m cell where the ground is built up (probability = density), each a point of light
    # ~1 m across, sodium-orange or white LED; where a pixel covers many cells, their average glow instead
    cs = 0.020
    lr = 0.0; lg = 0.0; lb = 0.0
    w = min(1.0, max(0.0, (fp / cs - 0.6) / 1.2))
    if w < 1.0 and dens > 0.01:
        ci = math.floor(x / cs); cj = math.floor(y / cs)
        rad = max(fp * 0.65, 0.0010)
        sc = min(1.0, (0.0016 / rad) ** 2)
        for oj in range(-1, 2):
            for oi in range(-1, 2):
                i = ci + oi; j = cj + oj
                if hs(i, j, 81.0) < dens * 0.75:
                    lx_ = (i + hs(i, j, 82.0)) * cs; ly_ = (j + hs(i, j, 83.0)) * cs
                    d2 = (x - lx_) ** 2 + (y - ly_) ** 2
                    k = (0.35 + 0.65 * hs(i, j, 84.0)) * math.exp(-d2 / (rad * rad)) * sc * 4.0
                    k *= 0.94 + 0.06 * math.sin(tm * 9.0 + i * 1.7 + j * 2.3)
                    if hs(i, j, 85.0) < 0.6: lr += k * 1.30; lg += k * 0.70; lb += k * 0.28
                    else: lr += k * 0.95; lg += k * 0.93; lb += k * 0.86
    avg = dens * 0.75 * 0.30
    lr = lr * (1 - w) + avg * 1.18 * w; lg = lg * (1 - w) + avg * 0.78 * w; lb = lb * (1 - w) + avg * 0.50 * w
    # the glow of the streets and yards under the lamps
    lr += dens * 0.05; lg += dens * 0.033; lb += dens * 0.018
    return lr, lg, lb

@njit(fastmath=True, inline='always')
def ground_h(ZI, ZO, x, y):
    # height (km) at local x, y; the inner grid within ±12.5 km, the outer beyond
    if abs(x) < 12.4 and abs(y) < 12.4:
        n = ZI.shape[0]
        return img2(ZI, (x + 12.5) / 25.0 * n - 0.5, (12.5 - y) / 25.0 * n - 0.5) * 0.001
    n = ZO.shape[0]
    return img2(ZO, (x + 68.0) / 136.0 * n - 0.5, (68.0 - y) / 136.0 * n - 0.5) * 0.001

@njit(parallel=True, fastmath=True)
def kyiv(CI, CO, ZI, ZO, WI, WO, LI, LO, SK, cam, fw, rt, up, fov, B, P, sun_l, sun_e, expo, out, ss, tm, vis, monu, MO):
    # cam: local km (x east, y north, z up); B: 3×3 local->Earth-centred (columns east, north, up); P: the camera's
    # Earth-centred position; sun_l / sun_e: the Sun's direction local / Earth-centred; monu: the Motherland Monument
    # billboard (x, y, z0, height, width) with its mask MO
    H, W = out.shape[0], out.shape[1]
    f = (H / 2) / math.tan(fov / 2)
    pix = 1.0 / f
    sx, sy, sz = sun_l[0], sun_l[1], sun_l[2]
    for py_ in prange(H):
        for px_ in range(W):
            acr = 0.0; acg = 0.0; acb = 0.0
            for sj in range(ss):
                for si in range(ss):
                    u = px_ + (si + 0.5) / ss - W / 2; v = H / 2 - (py_ + (sj + 0.5) / ss)
                    dx = fw[0] * f + rt[0] * u + up[0] * v; dy = fw[1] * f + rt[1] * u + up[1] * v; dz = fw[2] * f + rt[2] * u + up[2] * v
                    dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
                    cr, cg, cb = sky_ring(SK, dx, dy, dz, B, P, sx, sy, sz, sun_e, pix)
                    # the monument (a billboard facing the camera) in front of everything it covers
                    mt = 1e9
                    if monu[3] > 0:
                        mx = monu[0] - cam[0]; my = monu[1] - cam[1]
                        md = math.sqrt(mx * mx + my * my)
                        nx_ = mx / md; ny_ = my / md
                        den = dx * nx_ + dy * ny_
                        if den > 1e-6:
                            tt = md / den
                            hx = cam[0] + dx * tt - monu[0]; hy = cam[1] + dy * tt - monu[1]; hz = cam[2] + dz * tt
                            lat_ = hx * (-ny_) + hy * nx_
                            zb = monu[2] - (monu[0] ** 2 + monu[1] ** 2) / (2 * R)
                            uu = lat_ / monu[4] + 0.5; vv = 1.0 - (hz - zb) / monu[3]
                            if 0 <= uu < 1 and 0 <= vv < 1:
                                a = img2(MO, uu * (MO.shape[1] - 1), vv * (MO.shape[0] - 1))
                                if a > 0.02: mt = tt
                    # the ground
                    t = 0.0; hit = False; tmax = 75.0
                    zc = cam[2]
                    if dz < 0 or zc < 0.6:
                        t = 0.002
                        lastt = 0.0
                        for it in range(700):
                            x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                            h = ground_h(ZI, ZO, x, y) - (x * x + y * y) / (2 * R)
                            d = z - h
                            if d < 0:
                                a_ = lastt; b_ = t
                                for k in range(8):
                                    m_ = 0.5 * (a_ + b_)
                                    xm = cam[0] + dx * m_; ym = cam[1] + dy * m_
                                    if cam[2] + dz * m_ - (ground_h(ZI, ZO, xm, ym) - (xm * xm + ym * ym) / (2 * R)) < 0: b_ = m_
                                    else: a_ = m_
                                t = 0.5 * (a_ + b_); hit = True
                                break
                            lastt = t
                            t += max(0.003, min(0.5 * d / max(0.05, -dz + 0.03), 0.4)) + t * 0.002
                            if t > tmax: break
                    if mt < 1e8 and (not hit or mt < t):
                        # the monument: titanium-steel, lit by the sky and the ring, a floodlit plinth
                        hz_ = (cam[2] + dz * mt) - (monu[2] - (monu[0] ** 2 + monu[1] ** 2) / (2 * R))
                        fl = math.exp(-hz_ / 0.03) * 0.5
                        cr = 0.06 + fl * 1.0; cg = 0.065 + fl * 0.85; cb = 0.08 + fl * 0.6
                        fo = 1 - math.exp(-mt / vis)
                        hr, hg_, hb = twilight(dx, dy, 0.01, sx, sy, sz)
                        cr = cr * (1 - fo) + hr * fo; cg = cg * (1 - fo) + hg_ * fo; cb = cb * (1 - fo) + hb * fo
                    elif hit:
                        x = cam[0] + dx * t; y = cam[1] + dy * t
                        inner = abs(x) < 12.4 and abs(y) < 12.4
                        if inner:
                            n = CI.shape[0]; gx = (x + 12.5) / 25.0 * n - 0.5; gy = (12.5 - y) / 25.0 * n - 0.5
                            ar, ag, ab = img3(CI, gx, gy); wv = img2(WI, gx, gy); em = img2(LI, gx, gy)
                        else:
                            n = CO.shape[0]; gx = (x + 68.0) / 136.0 * n - 0.5; gy = (68.0 - y) / 136.0 * n - 0.5
                            ar, ag, ab = img3(CO, gx, gy); wv = img2(WO, gx, gy); em = img2(LO, gx, gy)
                        # the sky's light on the ground (dim, blue) plus the ring's light from the south
                        skr, skg, skb = twilight(0.0, 0.0, 1.0, sx, sy, sz)
                        amb_r = skr * 1.4 + 0.008; amb_g = skg * 1.4 + 0.008; amb_b = skb * 1.4 + 0.010
                        if wv > 0.5:
                            # the Dnipro: a mirror with ripples, Fresnel
                            nxr = (vn(x * 90.0 + tm * 0.4, y * 60.0, 5.0) - 0.5) * 0.06
                            nyr = (vn(x * 70.0, y * 110.0 - tm * 0.3, 6.0) - 0.5) * 0.06
                            nl = math.sqrt(nxr * nxr + nyr * nyr + 1)
                            nx = nxr / nl; ny = nyr / nl; nz = 1.0 / nl
                            dn = dx * nx + dy * ny + dz * nz
                            rx = dx - 2 * dn * nx; ry = dy - 2 * dn * ny; rz = abs(dz - 2 * dn * nz)
                            fr = 0.02 + 0.98 * (1 + dn) ** 5
                            kr, kg, kb = sky_ring(SK, rx, ry, rz, B, P, sx, sy, sz, sun_e, pix * 2.0)
                            cr = kr * fr + ar * 0.25 * amb_r * (1 - fr); cg = kg * fr + ag * 0.25 * amb_g * (1 - fr); cb = kb * fr + ab * 0.25 * amb_b * (1 - fr)
                            # the city's lights on the water, blurred
                            cr += em * 0.25; cg += em * 0.17; cb += em * 0.08
                        else:
                            cr = ar * amb_r; cg = ag * amb_g; cb = ab * amb_b
                            lr_, lg_, lb_ = lamps(x, y, em, t * pix, tm)
                            cr += lr_; cg += lg_; cb += lb_
                        # haze: the air between us and the ground glows with the sky's horizon colour
                        fo = 1 - math.exp(-t / vis)
                        hr, hg_, hb = twilight(dx, dy, 0.01, sx, sy, sz)
                        cr = cr * (1 - fo) + hr * fo * 0.95; cg = cg * (1 - fo) + hg_ * fo * 0.95; cb = cb * (1 - fo) + hb * fo * 0.95
                    acr += cr; acg += cg; acb += cb
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k

@njit(fastmath=True)
def sky_ring(SK, dx, dy, dz, B, P, sx, sy, sz, sun_e, pix):
    # the twilight sky, the stars and the ring in local direction d (the ring seen through the air: dimmed and reddened low)
    r, g, b = twilight(dx, dy, dz, sx, sy, sz)
    # Earth-centred direction
    ex = B[0, 0] * dx + B[0, 1] * dy + B[0, 2] * dz
    ey = B[1, 0] * dx + B[1, 1] * dy + B[1, 2] * dz
    ez = B[2, 0] * dx + B[2, 1] * dy + B[2, 2] * dz
    if dz > -0.02:
        el = max(dz, 0.0)
        am = 1.0 / (el + 0.025 * math.exp(-el * 30.0) + 0.012)          # airmass, bounded at the horizon
        tr = math.exp(-0.10 * am); tg = math.exp(-0.16 * am); tb = math.exp(-0.30 * am)
        st_r, st_g, st_b = stars(SK, ex, ey, ez, pix)
        vis_ = max(0.0, 1.0 - (r + g + b) * 8.0)                         # stars wash out in a bright sky
        r += st_r * tr * vis_; g += st_g * tg * vis_; b += st_b * tb * vis_
        t, rr, rg, rb, al = ring_hit(P[0], P[1], P[2], ex, ey, ez, sun_e[0], sun_e[1], sun_e[2])
        if t < 1e29:
            # the Earth itself in front of the ring? (a ray below the horizon is ground anyway)
            r = r * (1 - al * 0.85) + rr * tr; g = g * (1 - al * 0.85) + rg * tg; b = b * (1 - al * 0.85) + rb * tb
    return r, g, b

# ---------------------------------------------------------------- the Earth from space

@njit(fastmath=True, inline='always')
def ray_sphere(ox, oy, oz, dx, dy, dz, cx, cy, cz, Rs):
    lx = ox - cx; ly = oy - cy; lz = oz - cz
    b = lx * dx + ly * dy + lz * dz; c = lx * lx + ly * ly + lz * lz - Rs * Rs
    disc = b * b - c
    if disc < 0: return 1e30, 1e30
    s = math.sqrt(disc)
    return -b - s, -b + s

@njit(fastmath=True)
def cloud_n(x, y):
    w1 = vn(x * 1.3, y * 1.3, 51.0); w2 = vn(x * 1.3 + 5.2, y * 1.3, 52.0)
    x += 0.7 * w1; y += 0.4 * w2
    n = 0.0; a = 0.5; fq = 1.0
    for o in range(6):
        n += a * vn(x * fq * (2.0 if o > 2 else 1.0), y * fq * 1.6, 53.0 + o); a *= 0.5; fq *= 2.1
    return n

@njit(fastmath=True)
def clouds(nx, ny, nz, rot, cov):
    # procedural cloud cover on the sphere: domain-warped noise, belts by latitude (equatorial towers, storm belts);
    # near the poles the noise is taken on the polar projection instead (no streaks converging on the pole)
    lat = math.asin(max(-1.0, min(1.0, nz))); lon = math.atan2(ny, nx) + rot
    n = cloud_n(lon * 6.0, lat * 6.0)
    wp = min(1.0, max(0.0, (abs(lat) - 0.95) / 0.30))
    if wp > 0:
        ux = nx * math.cos(rot) - ny * math.sin(rot); uy = nx * math.sin(rot) + ny * math.cos(rot)
        n = n * (1 - wp) + cloud_n(ux * 6.0 + 11.0, uy * 6.0 + (7.0 if nz > 0 else -7.0)) * wp
    band = 0.55 + 0.25 * math.exp(-(lat / 0.12) ** 2) + 0.30 * math.exp(-((abs(lat) - 0.95) / 0.25) ** 2) - 0.25 * math.exp(-((abs(lat) - 0.45) / 0.15) ** 2)
    return 0.88 * min(1.0, max(0.0, (n * band - (0.60 - cov)) / 0.30)) ** 1.3

@njit(parallel=True, fastmath=True)
def space(ET, SK, cam, fw, rt, up, fov, sun, rot, ringk, expo, out, depth, ss, cov, ice, warm, arc0, arclen, band):
    # ET: the Earth's map (equirectangular, lon from -180 at u = 0), rot: its rotation; ringk: the ring's strength (0–1)
    # ice: how far from the south pole (degrees) the ice cap reaches; warm: 0..1 the light colour (glow of the fresh ring)
    H, W = out.shape[0], out.shape[1]
    f = (H / 2) / math.tan(fov / 2)
    pix = 1.0 / f
    sx, sy, sz = sun[0], sun[1], sun[2]
    for py_ in prange(H):
        for px_ in range(W):
            acr = 0.0; acg = 0.0; acb = 0.0; dmin = 1e30
            for sj in range(ss):
                for si in range(ss):
                    u = px_ + (si + 0.5) / ss - W / 2; v = H / 2 - (py_ + (sj + 0.5) / ss)
                    dx = fw[0] * f + rt[0] * u + up[0] * v; dy = fw[1] * f + rt[1] * u + up[1] * v; dz = fw[2] * f + rt[2] * u + up[2] * v
                    dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
                    ox, oy, oz = cam[0], cam[1], cam[2]
                    t0, t1 = ray_sphere(ox, oy, oz, dx, dy, dz, 0.0, 0.0, 0.0, R)
                    cr = 0.0; cg = 0.0; cb = 0.0
                    tend = 1e30
                    if t0 > 0 and t0 < 1e29:
                        tend = t0
                        px = ox + dx * t0; py = oy + dy * t0; pz = oz + dz * t0
                        nx = px / R; ny = py / R; nz = pz / R
                        lat = math.asin(max(-1.0, min(1.0, nz))); lon = math.atan2(ny, nx) + rot
                        ar, ag, ab = tex2(ET, lon / (2 * math.pi) + 0.5, 0.5 - lat / math.pi)
                        # the ice cap on the southern supercontinent (the late-Ordovician glaciation)
                        if ice > 0:
                            ip = math.degrees(lat) + 90.0
                            # (noise on the polar projection, not on lon/lat: no spikes converging on the pole)
                            ux = nx * math.cos(rot) - ny * math.sin(rot); uy = nx * math.sin(rot) + ny * math.cos(rot)
                            ice_n = 0.6 * (vn(ux * 9.0, uy * 9.0, 60.0) - 0.5) + 0.35 * (vn(ux * 27.0, uy * 27.0, 61.0) - 0.5)
                            ic = min(1.0, max(0.0, (ice - ip) / 3.0 + ice_n * 3.0))
                            if ar < ab: ic *= 0.85                        # sea ice thinner than the ice sheet on land
                            sh_ = 0.84 + 0.16 * vn(ux * 60.0, uy * 60.0, 62.0)
                            ar = ar * (1 - ic) + 0.86 * sh_ * ic; ag = ag * (1 - ic) + 0.90 * sh_ * ic; ab = ab * (1 - ic) + 0.97 * sh_ * ic
                        ndl = nx * sx + ny * sy + nz * sz
                        cl = clouds(nx, ny, nz, rot * 1.02, cov)
                        # the ring's shadow on the ground
                        rs = 1.0
                        if abs(sz) > 1e-6:
                            tq = -pz / sz
                            if tq > 0:
                                qx = px + sx * tq; qy = py + sy * tq
                                rq = math.sqrt(qx * qx + qy * qy)
                                tau = ring_tau(rq) * ringk
                                if tau > 0: rs = math.exp(-tau / max(abs(sz), 0.05))
                        lit = max(0.0, ndl)
                        term = min(1.0, max(0.0, (ndl + 0.06) / 0.12))
                        # sea glint
                        sea = 1.0 if (ab > ar and ab > 0.18 and ar < 0.25) else 0.0
                        hx = sx - dx; hy = sy - dy; hz = sz - dz
                        hl = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
                        spec = sea * (1 - cl) * max(0.0, (nx * hx + ny * hy + nz * hz) / hl) ** 900 * 0.12
                        cr_ = ar * (1 - cl) + 0.95 * cl; cg_ = ag * (1 - cl) + 0.96 * cl; cb_ = ab * (1 - cl) + 1.0 * cl
                        L = lit * rs
                        cr = cr_ * L * (1.0 + 0.10 * warm) + spec * L; cg = cg_ * L + spec * L * 0.9; cb = cb_ * L * (1.0 - 0.08 * warm) + spec * L * 0.75
                        # the night side lit faintly by the sunlit ring ("ringshine")
                        if ringk > 0 and ndl < 0.1:
                            rsn = 0.02 * ringk * max(0.0, 1.0 - abs(nz) * 1.2) * min(1.0, (0.1 - ndl) * 4)
                            cr += cr_ * rsn; cg += cg_ * rsn; cb += cb_ * rsn * 1.05
                        # the atmosphere over the disc: blue haze toward the limb
                        mu = max(0.05, -(dx * nx + dy * ny + dz * nz))
                        hz_ = 0.025 / mu
                        ah = (1 - math.exp(-hz_)) * term
                        cr = cr * (1 - ah) + 0.18 * ah; cg = cg * (1 - ah) + 0.36 * ah; cb = cb * (1 - ah) + 0.80 * ah
                        # the equatorial band (±30°) where all 21 craters of the time lie: a glow and two bright lines
                        if band > 0:
                            la = abs(math.degrees(lat))
                            ins = min(1.0, max(0.0, (30.0 - la) / 1.5))
                            ln_ = math.exp(-((la - 30.0) / 0.45) ** 2)
                            ln_ = math.exp(-((la - 30.0) / 0.22) ** 2)
                            cr += band * (ins * 0.012 + ln_ * 0.85); cg += band * (ins * 0.016 + ln_ * 0.68); cb += band * (ins * 0.008 + ln_ * 0.22)
                        # the terminator: a reddened band
                        tb_ = math.exp(-((ndl - 0.02) / 0.05) ** 2) * 0.25 * (1 - cl * 0.5)
                        cr += tb_ * cr_ * 0.6; cg += tb_ * cg_ * 0.2
                    else:
                        cr, cg, cb = stars(SK, dx, dy, dz, pix)
                        cs = dx * sx + dy * sy + dz * sz
                        if cs > 0.99997: cr += 60.0; cg += 56.0; cb += 50.0
                        elif cs > 0.999: cr += 0.3 * (cs - 0.999) / 0.001; cg += 0.28 * (cs - 0.999) / 0.001; cb += 0.24 * (cs - 0.999) / 0.001
                    # the atmosphere's limb glow (thin shell, H ~ 8 km), sunlit part only
                    b_ = ox * dx + oy * dy + oz * dz
                    cx_ = ox - dx * b_; cy_ = oy - dy * b_; cz_ = oz - dz * b_
                    hmin = math.sqrt(cx_ * cx_ + cy_ * cy_ + cz_ * cz_) - R
                    if b_ < 0 and hmin > -30 and hmin < 160:
                        tl = -b_
                        tx = ox + dx * tl; ty = oy + dy * tl; tz = oz + dz * tl
                        tn = math.sqrt(tx * tx + ty * ty + tz * tz)
                        sl = (tx * sx + ty * sy + tz * sz) / tn
                        litl = min(1.0, max(0.0, (sl + 0.15) / 0.3))
                        g_ = math.exp(-max(hmin, 0.0) / 9.0) * litl
                        if tend < 1e29: g_ *= 0.5
                        cr += g_ * 0.10; cg += g_ * 0.30; cb += g_ * 0.85
                    # the ring
                    if ringk > 0:
                        t, rr, rg, rb, al = ring_hit(ox, oy, oz, dx, dy, dz, sx, sy, sz)
                        if t < tend:
                            k_ = ringk
                            if arclen < 6.283:
                                # a ring still forming: only an arc of it, its front ragged
                                qx = ox + dx * t; qy = oy + dy * t
                                ph = (math.atan2(qy, qx) - arc0) % (2 * math.pi)
                                fr_ = arclen + 0.25 * (vn(math.sqrt(qx * qx + qy * qy) / 900.0, 0.5, 31.0) - 0.5)
                                k_ *= min(1.0, max(0.0, (fr_ - ph) / 0.35)) * min(1.0, ph / 0.2 + 0.3)
                            al *= k_
                            cr = cr * (1 - al) + rr * k_; cg = cg * (1 - al) + rg * k_; cb = cb * (1 - al) + rb * k_
                    dmin = min(dmin, tend)
                    acr += cr; acg += cg; acb += cb
            k = expo / (ss * ss)
            out[py_, px_, 0] = acr * k; out[py_, px_, 1] = acg * k; out[py_, px_, 2] = acb * k
            depth[py_, px_] = dmin

@njit(fastmath=True)
def splat(out, depth, cam, fw, rt, up, fov, P, sun, ss):
    # rocky fragments as sphere impostors: P rows (x, y, z, radius km, albedo, seed, lumpiness, glow); depth-tested
    # against the Earth (depth), lit by the Sun, a ragged silhouette and a cratered, bumpy surface by noise
    H, W = out.shape[0], out.shape[1]
    f = (H / 2) / math.tan(fov / 2)
    n = P.shape[0]
    for q in range(n):
        dx = P[q, 0] - cam[0]; dy = P[q, 1] - cam[1]; dz = P[q, 2] - cam[2]
        z = dx * fw[0] + dy * fw[1] + dz * fw[2]
        if z <= 1e-3: continue
        sx_ = W / 2 + (dx * rt[0] + dy * rt[1] + dz * rt[2]) / z * f
        sy_ = H / 2 - (dx * up[0] + dy * up[1] + dz * up[2]) / z * f
        pr = P[q, 3] / z * f
        rpx = max(pr, 0.6)
        if sx_ < -rpx - 2 or sx_ > W + rpx + 2 or sy_ < -rpx - 2 or sy_ > H + rpx + 2: continue
        seed = P[q, 5]; lum = P[q, 6]; alb = P[q, 4]; glow = P[q, 7]
        x0 = int(max(0, sx_ - rpx * 1.3 - 1)); x1 = int(min(W - 1, sx_ + rpx * 1.3 + 1))
        y0 = int(max(0, sy_ - rpx * 1.3 - 1)); y1 = int(min(H - 1, sy_ + rpx * 1.3 + 1))
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                if depth[yy, xx] < z: continue
                u = (xx + 0.5 - sx_) / rpx; v = -(yy + 0.5 - sy_) / rpx
                ang = math.atan2(v, u)
                rim = 1.0 + lum * (0.22 * (vn(math.cos(ang) * 2.0 + seed, math.sin(ang) * 2.0, 90.0) - 0.5) + 0.10 * (vn(math.cos(ang) * 6.0 + seed, math.sin(ang) * 6.0, 91.0) - 0.5))
                d2 = (u * u + v * v) / (rim * rim)
                if pr < 0.8:
                    # a point too small to resolve: just its light
                    a = math.exp(-d2 * 2.0) * min(1.0, pr / 0.8 + 0.25)
                    lt = 0.5 + 0.5 * max(0.0, -(dx * sun[0] + dy * sun[1] + dz * sun[2]) / z)
                    k = alb * lt * 3.5 + glow
                    out[yy, xx, 0] += a * k * 1.0; out[yy, xx, 1] += a * k * 0.92; out[yy, xx, 2] += a * k * (0.82 + 0.4 * glow)
                    continue
                if d2 > 1.0: continue
                w = math.sqrt(1.0 - d2)
                # the normal in world space (impostor), bumped by noise
                nxw = rt[0] * u + up[0] * v - fw[0] * w; nyw = rt[1] * u + up[1] * v - fw[1] * w; nzw = rt[2] * u + up[2] * v - fw[2] * w
                bx = vn(u * 5.0 + seed, v * 5.0, 92.0) - 0.5; by = vn(u * 5.0, v * 5.0 + seed, 93.0) - 0.5
                nxw += lum * 0.8 * (rt[0] * bx + up[0] * by); nyw += lum * 0.8 * (rt[1] * bx + up[1] * by); nzw += lum * 0.8 * (rt[2] * bx + up[2] * by)
                nl = math.sqrt(nxw * nxw + nyw * nyw + nzw * nzw); nxw /= nl; nyw /= nl; nzw /= nl
                ndl = nxw * sun[0] + nyw * sun[1] + nzw * sun[2]
                cr_ = 0.5 + 0.5 * vn(u * 14.0 + seed, v * 14.0, 94.0)
                crat = 1.0 - 0.35 * max(0.0, vn(u * 9.0 + seed * 2.0, v * 9.0, 95.0) - 0.62) * 3.0
                a_ = alb * (0.75 + 0.5 * cr_) * crat
                lt = max(0.0, ndl) * 1.3 + 0.015
                edge = min(1.0, (1.0 - d2) * rpx * 0.5)
                cr = a_ * lt * 1.02 + glow; cg = a_ * lt * 0.94 + glow * 0.85; cb = a_ * lt * 0.84 + glow * 0.75
                out[yy, xx, 0] = out[yy, xx, 0] * (1 - edge) + cr * edge
                out[yy, xx, 1] = out[yy, xx, 1] * (1 - edge) + cg * edge
                out[yy, xx, 2] = out[yy, xx, 2] * (1 - edge) + cb * edge
                if edge > 0.5: depth[yy, xx] = z

def tonemap(img):
    x = img * 0.9
    y = np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
    return y ** (1 / 2.2)

def bloom(img, s=1.0):
    from scipy.ndimage import gaussian_filter
    hi = np.clip(img - 0.9, 0, None)
    return img + 0.35 * gaussian_filter(hi, (6 * s, 6 * s, 0)) + 0.25 * gaussian_filter(hi, (24 * s, 24 * s, 0))
