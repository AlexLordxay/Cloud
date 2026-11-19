# The Earth for «А ти уявляєш Сонце так?» — numba: single-scattering atmosphere (Rayleigh + Mie, transmittance table),
# the ground from NASA Blue Marble (a sharper map over Ukraine), farm fields drawn procedurally when the camera is low,
# clouds from space, city lights on the night side, and the Sun's disc seen through the air (yellow low down, white above).
# Units: km, Earth-centred Earth-fixed frame (z = north). The camera and the Sun direction are given in that frame.
import math, os
import numpy as np
import numba as nb

RE = 6371.0
RA = RE + 80.0
BR = np.array([5.8e-3, 13.5e-3, 33.1e-3])     # Rayleigh scattering per km at sea level
HR = 8.0
BM = 7e-3                                       # Mie scattering per km (a clear summer morning)
HM = 1.2
GM = 0.80
NT_H, NT_MU = 128, 256

@nb.njit(inline='always')
def sat(x): return min(1.0, max(0.0, x))

@nb.njit(inline='always')
def smooth(a, b, x):
    t = sat((x - a) / (b - a)); return t * t * (3 - 2 * t)

@nb.njit(inline='always')
def hsh(x, y):
    s = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return s - math.floor(s)

@nb.njit(inline='always')
def vn2(x, y):
    xi = math.floor(x); yi = math.floor(y); fx = x - xi; fy = y - yi
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = hsh(xi, yi); b = hsh(xi + 1, yi); c = hsh(xi, yi + 1); d = hsh(xi + 1, yi + 1)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

@nb.njit(inline='always')
def fbm2(x, y, o):
    s = 0.0; a = 0.5; t = 0.0
    for i in range(o):
        s += a * vn2(x, y); t += a; x = x * 2.02 + 3.1; y = y * 2.02 - 1.7; a *= 0.5
    return s / t

@nb.njit
def make_lut(br0, br1, br2, bm):
    """transmittance from height h (0…80 km, sqrt spacing) along zenith cosine mu (-1…1) to the top of the air"""
    T = np.zeros((NT_H, NT_MU, 3))
    for a in range(NT_H):
        h = (a / (NT_H - 1)) ** 2 * (RA - RE)
        r = RE + h
        for b in range(NT_MU):
            mu = -1.0 + 2.0 * b / (NT_MU - 1)
            # distance to the top; ground hit?
            disc = r * r * (mu * mu - 1) + RA * RA
            L = -r * mu + math.sqrt(max(disc, 0.0))
            dg = r * r * (mu * mu - 1) + RE * RE
            if mu < 0 and dg >= 0:
                T[a, b, 0] = 0.0; T[a, b, 1] = 0.0; T[a, b, 2] = 0.0
                continue
            n = 64; dl = L / n; odr = 0.0; odm = 0.0
            for s in range(n):
                tt = (s + 0.5) * dl
                rr = math.sqrt(r * r + tt * tt + 2 * r * tt * mu)
                hh = rr - RE
                odr += math.exp(-hh / HR) * dl; odm += math.exp(-hh / HM) * dl
            T[a, b, 0] = math.exp(-(br0 * odr + bm * 1.1 * odm))
            T[a, b, 1] = math.exp(-(br1 * odr + bm * 1.1 * odm))
            T[a, b, 2] = math.exp(-(br2 * odr + bm * 1.1 * odm))
    return T

@nb.njit(inline='always')
def lut(T, h, mu, c):
    a = math.sqrt(sat(h / (RA - RE))) * (NT_H - 1)
    b = (min(1.0, max(-1.0, mu)) + 1.0) * 0.5 * (NT_MU - 1)
    a0 = min(int(a), NT_H - 2); b0 = min(int(b), NT_MU - 2); fa = a - a0; fb = b - b0
    return ((T[a0, b0, c] * (1 - fb) + T[a0, b0 + 1, c] * fb) * (1 - fa) +
            (T[a0 + 1, b0, c] * (1 - fb) + T[a0 + 1, b0 + 1, c] * fb) * fa)

@nb.njit(inline='always')
def tex3(img, u, v, c):
    h, w = img.shape[0], img.shape[1]
    x = (u % 1.0) * w - 0.5; y = min(max(v * h - 0.5, 0.0), h - 1.001)
    x0 = int(math.floor(x)); y0 = int(y); fx = x - x0; fy = y - y0
    x0 = x0 % w; x1 = (x0 + 1) % w; y1 = min(y0 + 1, h - 1)
    a = float(img[y0, x0, c]); b = float(img[y0, x1, c]); cc = float(img[y1, x0, c]); d = float(img[y1, x1, c])
    return ((a * (1 - fx) + b * fx) * (1 - fy) + (cc * (1 - fx) + d * fx) * fy) / 255.0

@nb.njit(inline='always')
def tex1(img, u, v):
    h, w = img.shape[0], img.shape[1]
    x = (u % 1.0) * w - 0.5; y = min(max(v * h - 0.5, 0.0), h - 1.001)
    x0 = int(math.floor(x)); y0 = int(y); fx = x - x0; fy = y - y0
    x0 = x0 % w; x1 = (x0 + 1) % w; y1 = min(y0 + 1, h - 1)
    a = float(img[y0, x0]); b = float(img[y0, x1]); cc = float(img[y1, x0]); d = float(img[y1, x1])
    return ((a * (1 - fx) + b * fx) * (1 - fy) + (cc * (1 - fx) + d * fx) * fy) / 255.0

# Ukraine map bounds (lon 0…56.25 E, lat 56.25…33.75 N)
UA_L0, UA_L1, UA_B0, UA_B1 = 0.0, 56.25, 33.75, 56.25

@nb.njit(inline='always')
def albedo(lat, lon, fp, day, ua, fields, fx0, fy0, fe0, fe1, fe2, fn0, fn1, fn2, px, py, pz):
    """linear albedo at (lat, lon) radians; fp = pixel footprint, km. fields > 0: procedural farmland near the camera
    (fx0, fy0 unused); local east/north axes fe/fn give metric coordinates of the ground point p (km)"""
    u = (lon + math.pi) / (2 * math.pi); v = (math.pi / 2 - lat) / math.pi
    r = tex3(day, u, v, 0); g = tex3(day, u, v, 1); b = tex3(day, u, v, 2)
    dlon = math.degrees(lon); dlat = math.degrees(lat)
    if fp < 3.0 and UA_L0 + 0.2 < dlon < UA_L1 - 0.2 and UA_B0 + 0.2 < dlat < UA_B1 - 0.2:
        uu = (dlon - UA_L0) / (UA_L1 - UA_L0); vv = (UA_B1 - dlat) / (UA_B1 - UA_B0)
        k = smooth(3.0, 0.8, fp)
        r = r * (1 - k) + tex3(ua, uu, vv, 0) * k; g = g * (1 - k) + tex3(ua, uu, vv, 1) * k; b = b * (1 - k) + tex3(ua, uu, vv, 2) * k
    # sRGB-ish -> linear
    r = r ** 2.2; g = g ** 2.2; b = b ** 2.2
    water = b > r * 1.2 and b > g * 1.02
    if fields > 0.0 and fp < 0.03 and not water:
        # metric coordinates on the local tangent plane (km)
        X = px * fe0 + py * fe1 + pz * fe2; Y = px * fn0 + py * fn1 + pz * fn2
        k = fields * smooth(0.03, 0.004, fp) * 0.8
        # fields: a jittered grid of parcels ~0.6 x 1.5 km, crop by hash; strips of trees along some edges
        cx = math.floor(X / 0.6 + 0.3 * math.sin(Y * 0.7)); cy = math.floor(Y / 1.5 + 0.2 * math.sin(X * 0.9))
        hcrop = hsh(cx, cy)
        fxx = X / 0.6 + 0.3 * math.sin(Y * 0.7) - cx; fyy = Y / 1.5 + 0.2 * math.sin(X * 0.9) - cy
        edge = min(min(fxx, 1 - fxx) * 0.6, min(fyy, 1 - fyy) * 1.5)
        n1 = fbm2(X * 3.0, Y * 3.0, 3)
        rows = 1.0
        if hcrop < 0.30:   # sunflowers (yellow canopy)
            cr, cg, cb = 0.36, 0.29, 0.05
        elif hcrop < 0.50: # wheat stubble / ripe wheat
            cr, cg, cb = 0.40, 0.31, 0.15
        elif hcrop < 0.72: # green (maize, beet)
            cr, cg, cb = 0.075, 0.13, 0.03
        elif hcrop < 0.85: # dark ploughed soil
            cr, cg, cb = 0.075, 0.055, 0.035
        else:              # meadow
            cr, cg, cb = 0.12, 0.17, 0.05
        # the home field is all sunflowers (around the origin of the local plane): seen from afar a speckled carpet of
        # yellow petals, dark seed discs and leaves (the plants themselves are drawn near the camera)
        home = abs(X) < 0.95 and abs(Y) < 0.75
        if home:
            # from high up: a yellow sunflower parcel like the others; close: the speckled carpet
            sp_ = fbm2(X * 900.0, Y * 900.0, 2)
            kc = smooth(0.006, 0.0015, fp)
            cr = 0.36 * (1 - kc) + (0.20 + 0.10 * sp_) * kc
            cg = 0.29 * (1 - kc) + (0.15 + 0.07 * sp_) * kc
            cb = 0.05 * (1 - kc) + 0.03 * kc
        n2 = fbm2(X * 22.0, Y * 22.0, 3)
        tone = (0.78 + 0.3 * n1 + 0.22 * (n2 - 0.5)) * rows
        if home: tone = 1.0
        cr *= tone; cg *= tone; cb *= tone
        if edge < 0.006 + 0.004 * hsh(cy, cx):   # tree belts / tracks between some fields
            if hsh(cx * 3.0, cy) < 0.6:
                cr, cg, cb = 0.035, 0.055, 0.02
        # keep the map's brightness: the parcels only re-colour it (so there is no jump when they fade out)
        ml = (r + g + b) / 3 + 1e-4; cl_ = (cr + cg + cb) / 3 + 1e-4
        sc = (ml / 0.16) ** 0.5
        cr *= sc; cg *= sc; cb *= sc
        r = r * (1 - k) + cr * k; g = g * (1 - k) + cg * k; b = b * (1 - k) + cb * k
    return r, g, b

@nb.njit(parallel=True, fastmath=True)
def k_earth(out, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, sx, sy, sz, T, day, ua, night, clouds,
            sun_k, disc_k, disc_rad, cloud_k, night_k, fields, fe, fn, expo, air_k, disc_pow):
    """adds the Earth and its air into out (H x W x 3; what is there already is the space behind, dimmed by the air)"""
    Hh, Ww = out.shape[0], out.shape[1]
    br0 = 5.8e-3; br1 = 13.5e-3; br2 = 33.1e-3
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            b = ox * dx + oy * dy + oz * dz
            c2 = ox * ox + oy * oy + oz * oz
            # the air shell
            da = b * b - (c2 - RA * RA)
            r_ = 0.0; g_ = 0.0; b_ = 0.0
            Tv0 = 1.0; Tv1 = 1.0; Tv2 = 1.0
            hitg = False
            if da > 0:
                t0 = max(0.0, -b - math.sqrt(da)); t1 = -b + math.sqrt(da)
                if t1 > 0:
                    dg = b * b - (c2 - RE * RE)
                    tg = -1.0
                    if dg > 0:
                        tg = -b - math.sqrt(dg)
                        if tg > 0:
                            t1 = tg; hitg = True
                    mus = dx * sx + dy * sy + dz * sz
                    pr = 0.0596831 * (1 + mus * mus)
                    g2 = GM * GM
                    pm = 0.119366 * (1 - g2) * (1 + mus * mus) / ((2 + g2) * (1 + g2 - 2 * GM * mus) ** 1.5)
                    N = 18
                    seg = (t1 - t0) / N
                    odr = 0.0; odm = 0.0
                    sr0 = 0.0; sr1 = 0.0; sr2 = 0.0; sm0 = 0.0; sm1 = 0.0; sm2 = 0.0
                    for s in range(N):
                        tt = t0 + (s + 0.5) * seg
                        qx = ox + dx * tt; qy = oy + dy * tt; qz = oz + dz * tt
                        rq = math.sqrt(qx * qx + qy * qy + qz * qz)
                        hq = rq - RE
                        dr = math.exp(-hq / HR) * seg; dm = math.exp(-hq / HM) * seg
                        odr += dr * 0.5; odm += dm * 0.5
                        mu_s = (qx * sx + qy * sy + qz * sz) / rq
                        e0 = math.exp(-(br0 * odr + BM * 1.1 * odm)); e1 = math.exp(-(br1 * odr + BM * 1.1 * odm)); e2 = math.exp(-(br2 * odr + BM * 1.1 * odm))
                        l0 = lut(T, hq, mu_s, 0); l1 = lut(T, hq, mu_s, 1); l2 = lut(T, hq, mu_s, 2)
                        sr0 += dr * e0 * l0; sr1 += dr * e1 * l1; sr2 += dr * e2 * l2
                        sm0 += dm * e0 * l0; sm1 += dm * e1 * l1; sm2 += dm * e2 * l2
                        odr += dr * 0.5; odm += dm * 0.5
                    Tv0 = math.exp(-(br0 * odr + BM * 1.1 * odm)); Tv1 = math.exp(-(br1 * odr + BM * 1.1 * odm)); Tv2 = math.exp(-(br2 * odr + BM * 1.1 * odm))
                    ms = 1.25                                   # a nod to multiple scattering
                    r_ += sun_k * air_k * (sr0 * br0 * pr * ms + sm0 * BM * pm)
                    g_ += sun_k * air_k * (sr1 * br1 * pr * ms + sm1 * BM * pm)
                    b_ += sun_k * air_k * (sr2 * br2 * pr * ms + sm2 * BM * pm)
                    if hitg:
                        px = ox + dx * tg; py = oy + dy * tg; pz = oz + dz * tg
                        nx = px / RE; ny = py / RE; nz = pz / RE
                        lat = math.asin(min(1.0, max(-1.0, nz))); lon = math.atan2(ny, nx)
                        fp = tg / k / n
                        ar, ag, ab = albedo(lat, lon, fp / max(0.15, -(nx * dx + ny * dy + nz * dz)), day, ua, fields, 0.0, 0.0,
                                            fe[0], fe[1], fe[2], fn[0], fn[1], fn[2], px, py, pz)
                        mun = nx * sx + ny * sy + nz * sz
                        ts0 = lut(T, 0.0, mun, 0); ts1 = lut(T, 0.0, mun, 1); ts2 = lut(T, 0.0, mun, 2)
                        lam = max(0.0, mun)
                        amb = 0.10 * smooth(-0.12, 0.25, mun)          # skylight
                        cl = 0.0
                        if cloud_k > 0.0:
                            cl = tex1(clouds, (lon + math.pi) / (2 * math.pi), (math.pi / 2 - lat) / math.pi) * cloud_k
                            cl = smooth(0.15, 0.9, cl) * cloud_k
                        gr0 = (ar * (1 - cl) + 0.9 * cl) * (lam * ts0 + amb * 0.6)
                        gr1 = (ag * (1 - cl) + 0.9 * cl) * (lam * ts1 + amb * 0.8)
                        gr2 = (ab * (1 - cl) + 0.92 * cl) * (lam * ts2 + amb * 1.0)
                        # city lights where it is dark
                        if night_k > 0.0:
                            nl = tex1(night, (lon + math.pi) / (2 * math.pi), (math.pi / 2 - lat) / math.pi)
                            dk = smooth(0.08, -0.12, mun) if sun_k > 0 else 1.0
                            nl = nl * nl * night_k * dk * (1 - cl * 0.7)
                        else:
                            nl = 0.0
                        if sun_k <= 0:
                            nl += 0.004                                  # the dark globe still shows against the stars
                        r_ += gr0 * sun_k * Tv0 + nl * 1.0 * Tv0; g_ += gr1 * sun_k * Tv1 + nl * 0.72 * Tv1; b_ += gr2 * sun_k * Tv2 + nl * 0.42 * Tv2
            if not hitg:
                # the Sun's disc, seen through whatever air is in the way: yellow low in the air, white above it
                cs = dx * sx + dy * sy + dz * sz
                cov = 0.0
                if disc_k > 0.0 and cs > math.cos(disc_rad * 12.0):
                    ang = math.acos(min(1.0, cs))
                    cov = sat((disc_rad - ang) * k + 0.5)
                    yel = sat((1.0 - Tv2 / max(Tv0, 1e-4)) * 2.6)
                    c0 = 1.0; c1 = 1.0 - 0.50 * yel; c2_ = 1.0 - 0.92 * yel
                    mu_ = math.sqrt(max(0.0, 1 - (ang / disc_rad) ** 2)) if ang < disc_rad else 0.0
                    ld = 1 - 0.35 * (1 - mu_)
                    br_ = disc_k * ld * (0.6 + 0.4 * max(Tv0, 1e-3))
                    # a warm halo around it
                    air = 0.25 + 0.75 * sat((1.0 - Tv0) * 6.0)          # the aureole is the air's (gone in space)
                    edge = (1.0 - sat(ang / (disc_rad * 12.0))) ** 2
                    hal = disc_k * 0.30 * math.exp(-max(0.0, ang - disc_rad) / (disc_rad * 1.6)) * (1 - cov) * edge * air
                    hal += disc_k * 0.10 * math.exp(-max(0.0, ang - disc_rad) / (disc_rad * 4.0)) * (1 - cov) * edge * air
                    r_ = r_ * (1 - cov) + br_ * cov * c0 + hal * c0
                    g_ = g_ * (1 - cov) + br_ * cov * c1 + hal * (c1 * 0.95)
                    b_ = b_ * (1 - cov) + br_ * cov * c2_ + hal * (c2_ * 0.85)
                if cov > 0.0:
                    Tv0 *= (1 - cov); Tv1 *= (1 - cov); Tv2 *= (1 - cov)
                out[j, i, 0] = out[j, i, 0] * Tv0 + r_ * expo
                out[j, i, 1] = out[j, i, 1] * Tv1 + g_ * expo
                out[j, i, 2] = out[j, i, 2] * Tv2 + b_ * expo
            else:
                out[j, i, 0] = r_ * expo; out[j, i, 1] = g_ * expo; out[j, i, 2] = b_ * expo

_M = {}
def maps():
    if not _M:
        W = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'work', 'sun_imagine')
        for n in ('day', 'ua', 'night', 'clouds'):
            _M[n] = np.load(os.path.join(W, n + '.npy'), mmap_mode='r')
        _M['T'] = make_lut(5.8e-3, 13.5e-3, 33.1e-3, BM)
    return _M

def local_axes(lat, lon):
    a, b = math.radians(lat), math.radians(lon)
    up = np.array([math.cos(a) * math.cos(b), math.cos(a) * math.sin(b), math.sin(a)])
    east = np.array([-math.sin(b), math.cos(b), 0.0])
    north = np.cross(up, east)
    return up, east, north

def earth(img, c, sun_dir, sun_k=18.0, disc_k=3.0, disc_rad=math.radians(0.27), cloud_k=0.0, night_k=0.0,
          fields=0.0, home=(49.0, 32.0), expo=1.0, air_k=1.0, disc_pow=2.0):
    M = maps()
    o, f, r, u, k = c
    up, east, north = local_axes(*home)
    # metric frame on the tangent plane at the home point: subtract the home point (the procedural fields are local)
    s = np.asarray(sun_dir, float)
    k_earth(img, o[0], o[1], o[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, s[0], s[1], s[2], M['T'],
            M['day'], M['ua'], M['night'], M['clouds'], sun_k, disc_k, disc_rad, cloud_k, night_k, fields, east, north,
            expo, air_k, disc_pow)
