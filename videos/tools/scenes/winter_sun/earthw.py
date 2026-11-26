# The Earth for «Чому взимку холодно» (from sun_imagine/earthk.py) — numba: single-scattering atmosphere (Rayleigh + Mie),
# NASA Blue Marble with a sharper map over Ukraine and Sentinel-2 maps of Kyiv (±75 km and ±12 km), each in summer and
# under snow (winterize.py); seasonal snow on the land of the northern hemisphere (a snow line by longitude, patchy);
# clouds (the 1024 px map plus fractal detail); city lights; the Sun's disc through the air; and a «light beam»: a square
# bundle of sunlight (volumetric glow + its footprint on the ground — long and dim when the Sun is low).
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
K_LAT, K_LON = 50.4501, 30.5234
KX = 111.32 * math.cos(math.radians(K_LAT)); KY = 111.2

@nb.njit(inline='always')
def texl(img, x, y, c):
    """bilinear on an array, x, y in pixels"""
    h, w = img.shape[0], img.shape[1]
    x = min(max(x - 0.5, 0.0), w - 1.001); y = min(max(y - 0.5, 0.0), h - 1.001)
    x0 = int(x); y0 = int(y); fx = x - x0; fy = y - y0
    return ((img[y0, x0, c] * (1 - fx) + img[y0, x0 + 1, c] * fx) * (1 - fy) +
            (img[y0 + 1, x0, c] * (1 - fx) + img[y0 + 1, x0 + 1, c] * fx) * fy) / 255.0

@nb.njit(inline='always')
def snow_line(lon):
    """the southern edge of the snow cover in a snowy mid-winter (deg N) by longitude (deg)"""
    if lon < -125: return 56.0
    if lon < -100: return 47.0 + (lon + 125) * -0.12
    if lon < -75: return 42.0
    if lon < -55: return 43.0 + (lon + 75) * 0.1
    if lon < -12: return 60.0
    if lon < 8: return 60.0 - (lon + 12) * 0.25
    if lon < 25: return 55.0 - (lon - 8) * 0.30
    if lon < 45: return 49.9 - (lon - 25) * 0.30
    if lon < 100: return 44.0 - (lon - 45) * 0.04
    if lon < 125: return 41.8 - (lon - 100) * 0.05
    if lon < 145: return 40.5 + (lon - 125) * 0.25
    return 46.0

@nb.njit(inline='always')
def albedo(lat, lon, fp, day, ua, kyiv, kyiv_w, k75, k75_w, snow):
    """linear albedo at (lat, lon) radians; fp = pixel footprint, km; snow 0…1 = how deep into winter"""
    u = (lon + math.pi) / (2 * math.pi); v = (math.pi / 2 - lat) / math.pi
    r = tex3(day, u, v, 0); g = tex3(day, u, v, 1); b = tex3(day, u, v, 2)
    dlon = math.degrees(lon); dlat = math.degrees(lat)
    if fp < 3.0 and UA_L0 + 0.2 < dlon < UA_L1 - 0.2 and UA_B0 + 0.2 < dlat < UA_B1 - 0.2:
        uu = (dlon - UA_L0) / (UA_L1 - UA_L0); vv = (UA_B1 - dlat) / (UA_B1 - UA_B0)
        k = smooth(3.0, 0.8, fp)
        r = r * (1 - k) + tex3(ua, uu, vv, 0) * k; g = g * (1 - k) + tex3(ua, uu, vv, 1) * k; b = b * (1 - k) + tex3(ua, uu, vv, 2) * k
    water = b > r * 1.2 and b > g * 1.02
    # seasonal snow (from space): land north of the snow line, patchy at its edge; forest stays darker
    if snow > 0.0 and not water and dlat > 30.0:
        sl = snow_line(dlon) + (1.0 - snow) * 14.0
        pat = fbm2(dlon * 0.9, dlat * 0.9, 4)
        cov = smooth(sl - 3.0, sl + 3.0, dlat + (pat - 0.5) * 9.0) * snow
        lum = 0.3 * r + 0.55 * g + 0.15 * b
        dark = smooth(0.30, 0.12, lum)                 # taiga: dark crowns over the snow
        cov *= 1.0 - 0.55 * dark
        r = r * (1 - cov) + 0.86 * cov; g = g * (1 - cov) + 0.88 * cov; b = b * (1 - cov) + 0.93 * cov
    # Kyiv: Sentinel-2 maps (±75 km, then ±12 km), summer → snow
    if fp < 0.6:
        x = (dlon - K_LON) * KX; y = (dlat - K_LAT) * KY
        if abs(x) < 74.0 and abs(y) < 74.0:
            k = smooth(0.6, 0.15, fp) * smooth(74.0, 66.0, max(abs(x), abs(y)))
            px = (x + 75.0) / 150.0 * k75.shape[1]; py = (75.0 - y) / 150.0 * k75.shape[0]
            kr = texl(k75, px, py, 0) * (1 - snow) + texl(k75_w, px, py, 0) * snow
            kg = texl(k75, px, py, 1) * (1 - snow) + texl(k75_w, px, py, 1) * snow
            kb = texl(k75, px, py, 2) * (1 - snow) + texl(k75_w, px, py, 2) * snow
            if fp < 0.08 and abs(x) < 11.8 and abs(y) < 11.8:
                k2 = smooth(0.08, 0.02, fp) * smooth(11.8, 10.0, max(abs(x), abs(y)))
                px = (x + 12.0) / 24.0 * kyiv.shape[1]; py = (12.0 - y) / 24.0 * kyiv.shape[0]
                kr = kr * (1 - k2) + (texl(kyiv, px, py, 0) * (1 - snow) + texl(kyiv_w, px, py, 0) * snow) * k2
                kg = kg * (1 - k2) + (texl(kyiv, px, py, 1) * (1 - snow) + texl(kyiv_w, px, py, 1) * snow) * k2
                kb = kb * (1 - k2) + (texl(kyiv, px, py, 2) * (1 - snow) + texl(kyiv_w, px, py, 2) * snow) * k2
            # the Sentinel maps are brighter than Blue Marble: match them a little
            r = r * (1 - k) + kr * 0.92 * k; g = g * (1 - k) + kg * 0.92 * k; b = b * (1 - k) + kb * 0.92 * k
    return r ** 2.2, g ** 2.2, b ** 2.2

@nb.njit(inline='always')
def clouds_at(clouds, lat, lon, fp, cloud_k):
    if cloud_k <= 0.0: return 0.0
    cl = tex1(clouds, (lon + math.pi) / (2 * math.pi), (math.pi / 2 - lat) / math.pi)
    # fractal detail below the map's 39 km pixels (only where there are clouds already)
    dl = math.degrees(lon) * math.cos(lat); db = math.degrees(lat)
    det = fbm2(dl * 3.0, db * 3.0, 5) - 0.5
    kd = smooth(60.0, 6.0, fp)
    cl = cl + det * 0.55 * kd * smooth(0.05, 0.45, cl) * (1.2 - cl)
    return smooth(0.18, 0.85, cl) * cloud_k

@nb.njit(parallel=True, fastmath=True)
def k_earth(out, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, sx, sy, sz, T, day, ua, night, clouds,
            kyiv, kyiv_w, k75, k75_w, snow, sun_k, disc_k, disc_rad, cloud_k, night_k, expo, air_k,
            bm_on, bcx, bcy, bcz, b1x, b1y, b1z, b2x, b2y, b2z, bside, btop, bglow, bfoot, ground_k):
    """adds the Earth and its air into out (H x W x 3; what is there already is the space behind, dimmed by the air).
    The beam: centre on the ground (bc), axes b1, b2 across it (both ⊥ the Sun), side bside km, from the ground up to btop km
    along the Sun direction; bglow = its glow in the air, bfoot = the sunlight it carries (the rest of the ground gets
    ground_k of the sunlight)."""
    Hh, Ww = out.shape[0], out.shape[1]
    br0 = 5.8e-3; br1 = 13.5e-3; br2 = 33.1e-3
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            b = ox * dx + oy * dy + oz * dz
            c2 = ox * ox + oy * oy + oz * oz
            da = b * b - (c2 - RA * RA)
            r_ = 0.0; g_ = 0.0; b_ = 0.0
            Tv0 = 1.0; Tv1 = 1.0; Tv2 = 1.0
            hitg = False
            tg = -1.0
            if da > 0:
                t0 = max(0.0, -b - math.sqrt(da)); t1 = -b + math.sqrt(da)
                if t1 > 0:
                    dg = b * b - (c2 - RE * RE)
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
                    ms = 1.25
                    r_ += sun_k * air_k * (sr0 * br0 * pr * ms + sm0 * BM * pm)
                    g_ += sun_k * air_k * (sr1 * br1 * pr * ms + sm1 * BM * pm)
                    b_ += sun_k * air_k * (sr2 * br2 * pr * ms + sm2 * BM * pm)
                    if hitg:
                        px = ox + dx * tg; py = oy + dy * tg; pz = oz + dz * tg
                        nx = px / RE; ny = py / RE; nz = pz / RE
                        lat = math.asin(min(1.0, max(-1.0, nz))); lon = math.atan2(ny, nx)
                        fp = tg / k / n
                        fpc = fp / max(0.15, -(nx * dx + ny * dy + nz * dz))
                        ar, ag, ab = albedo(lat, lon, fpc, day, ua, kyiv, kyiv_w, k75, k75_w, snow)
                        mun = nx * sx + ny * sy + nz * sz
                        ts0 = lut(T, 0.0, mun, 0); ts1 = lut(T, 0.0, mun, 1); ts2 = lut(T, 0.0, mun, 2)
                        lam = max(0.0, mun)
                        gk = 1.0
                        if bm_on > 0:
                            # inside the beam's footprint? (project along the Sun onto the beam's cross-section)
                            qx = px - bcx; qy = py - bcy; qz = pz - bcz
                            a1 = qx * b1x + qy * b1y + qz * b1z; a2 = qx * b2x + qy * b2y + qz * b2z
                            ins = smooth(0.5 * bside + 0.01, 0.5 * bside - 0.01, abs(a1)) * smooth(0.5 * bside + 0.01, 0.5 * bside - 0.01, abs(a2))
                            gk = ground_k + (1.0 - ground_k) * ins
                            # the light the beam brings, shown as a warm glow per unit area (∝ sin of the Sun's height):
                            # high Sun — a small hot spot, low Sun — a long, faint one
                            heat = bfoot * lam * ins
                            r_ += heat * 1.00 * Tv0; g_ += heat * 0.62 * Tv1; b_ += heat * 0.22 * Tv2
                        amb = 0.10 * smooth(-0.12, 0.25, mun) * (0.35 + 0.65 * min(1.0, gk))
                        cl = clouds_at(clouds, lat, lon, fpc, cloud_k)
                        gr0 = (ar * (1 - cl) + 0.9 * cl) * (lam * ts0 * gk + amb * 0.6)
                        gr1 = (ag * (1 - cl) + 0.9 * cl) * (lam * ts1 * gk + amb * 0.8)
                        gr2 = (ab * (1 - cl) + 0.92 * cl) * (lam * ts2 * gk + amb * 1.0)
                        nl = 0.0
                        if night_k > 0.0:
                            nl = tex1(night, (lon + math.pi) / (2 * math.pi), (math.pi / 2 - lat) / math.pi)
                            dk = smooth(0.08, -0.12, mun) if sun_k > 0 else 1.0
                            nl = nl * nl * night_k * dk * (1 - cl * 0.7)
                        if sun_k <= 0:
                            nl += 0.004
                        r_ += gr0 * sun_k * Tv0 + nl * 1.0 * Tv0; g_ += gr1 * sun_k * Tv1 + nl * 0.72 * Tv1; b_ += gr2 * sun_k * Tv2 + nl * 0.42 * Tv2
            # the beam's glow in the air: the length of the ray inside the box (slab method in the beam frame)
            if bm_on > 0 and bglow > 0:
                qx = ox - bcx; qy = oy - bcy; qz = oz - bcz
                o1 = qx * b1x + qy * b1y + qz * b1z; d1 = dx * b1x + dy * b1y + dz * b1z
                o2 = qx * b2x + qy * b2y + qz * b2z; d2 = dx * b2x + dy * b2y + dz * b2z
                o3 = qx * sx + qy * sy + qz * sz; d3 = dx * sx + dy * sy + dz * sz
                tn = 0.0; tf = 1e9
                hs = 0.5 * bside
                ok = True
                for (oo, dd, lo, hi) in ((o1, d1, -hs, hs), (o2, d2, -hs, hs), (o3, d3, -0.05, btop)):
                    if abs(dd) < 1e-9:
                        if oo < lo or oo > hi: ok = False
                    else:
                        ta = (lo - oo) / dd; tb = (hi - oo) / dd
                        if ta > tb: ta, tb = tb, ta
                        tn = max(tn, ta); tf = min(tf, tb)
                if hitg: tf = min(tf, tg)
                if ok and tf > tn:
                    # brighter near the ground (denser air), softer towards the top
                    tm = 0.5 * (tn + tf)
                    h3 = o3 + d3 * tm
                    w = (tf - tn) * bglow * (0.35 + 0.65 * math.exp(-max(0.0, h3) / 4.0))
                    r_ += w * 1.0; g_ += w * 0.93; b_ += w * 0.80
            if not hitg:
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
                    air = 0.25 + 0.75 * sat((1.0 - Tv0) * 6.0)
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
        T = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        S = os.path.join(T, 'work', 'sun_imagine'); Wd = os.path.join(T, 'work', 'winter_sun')
        for n in ('day', 'ua', 'night', 'clouds'):
            _M[n] = np.load(os.path.join(S, n + '.npy'), mmap_mode='r')
        for n in ('kyiv', 'kyiv_w', 'kyiv75', 'kyiv75_w'):
            _M[n] = np.ascontiguousarray(np.load(os.path.join(Wd, n + '.npy')).astype(np.float32))
        _M['T'] = make_lut(5.8e-3, 13.5e-3, 33.1e-3, BM)
    return _M

def local_axes(lat, lon):
    a, b = math.radians(lat), math.radians(lon)
    up = np.array([math.cos(a) * math.cos(b), math.cos(a) * math.sin(b), math.sin(a)])
    east = np.array([-math.sin(b), math.cos(b), 0.0])
    north = np.cross(up, east)
    return up, east, north

def earth(img, c, sun_dir, sun_k=18.0, disc_k=3.0, disc_rad=math.radians(0.27), cloud_k=0.0, night_k=0.0,
          snow=0.0, expo=1.0, air_k=1.0, beam=None):
    """beam: dict(centre=world point on the ground, side=km, top=km, glow=, foot=, ground=)"""
    M = maps()
    o, f, r, u, k = c
    s = np.asarray(sun_dir, float)
    if beam:
        bc = np.asarray(beam['centre'], float)
        b1 = np.cross(s, beam.get('up', [0, 0, 1.0])); b1 = b1 / np.linalg.norm(b1); b2 = np.cross(s, b1)
        args = (1, bc[0], bc[1], bc[2], b1[0], b1[1], b1[2], b2[0], b2[1], b2[2], beam['side'], beam['top'],
                beam.get('glow', 0.0), beam.get('foot', 1.0), beam.get('ground', 1.0))
    else:
        args = (0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0)
    k_earth(img, o[0], o[1], o[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, s[0], s[1], s[2], M['T'],
            M['day'], M['ua'], M['night'], M['clouds'], M['kyiv'], M['kyiv_w'], M['kyiv75'], M['kyiv75_w'], float(snow),
            sun_k, disc_k, disc_rad, cloud_k, night_k, expo, air_k, *args)
