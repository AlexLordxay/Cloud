# The Sun for «А ти уявляєш Сонце так?» — numba kernels. Units: solar radii (R = 696 000 km), Sun-centred frame, z = the
# Sun's rotation axis. One kernel draws the photosphere (limb darkening per colour, granulation that "boils", faculae,
# sunspots with umbra / filamentary penumbra) and the smooth corona (streamers, polar plumes) seen past the limb;
# the coronal loops and prominences are drawn separately as soft splats of points along magnetic arches (sun_arches).
import math
import numpy as np
import numba as nb

# ---------------------------------------------------------------- noise
@nb.njit(inline='always')
def h3(x, y, z):
    s = math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453
    return s - math.floor(s)

@nb.njit(inline='always')
def vn3(x, y, z):
    xi = math.floor(x); yi = math.floor(y); zi = math.floor(z)
    fx = x - xi; fy = y - yi; fz = z - zi
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); fz = fz * fz * (3 - 2 * fz)
    a = h3(xi, yi, zi); b = h3(xi + 1, yi, zi); c = h3(xi, yi + 1, zi); d = h3(xi + 1, yi + 1, zi)
    e = h3(xi, yi, zi + 1); f = h3(xi + 1, yi, zi + 1); g = h3(xi, yi + 1, zi + 1); hh = h3(xi + 1, yi + 1, zi + 1)
    l0 = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    l1 = (e * (1 - fx) + f * fx) * (1 - fy) + (g * (1 - fx) + hh * fx) * fy
    return l0 * (1 - fz) + l1 * fz

@nb.njit(inline='always')
def fbm3(x, y, z, oct_):
    s = 0.0; a = 0.5; tot = 0.0
    for o in range(oct_):
        s += a * vn3(x, y, z); tot += a
        x = x * 2.03 + 1.7; y = y * 2.03 + 9.2; z = z * 2.03 + 3.1; a *= 0.5
    return s / tot

@nb.njit(inline='always')
def worley(x, y, z, tm):
    """cellular noise: (F1, F2) distances; feature points drift with time tm (the granules evolve)"""
    xi = math.floor(x); yi = math.floor(y); zi = math.floor(z)
    f1 = 9.0; f2 = 9.0
    for dz in range(-1, 2):
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                cx = xi + dx; cy = yi + dy; cz = zi + dz
                r1 = h3(cx, cy, cz); r2 = h3(cx + 17.3, cy - 4.1, cz + 9.9); r3 = h3(cx - 6.6, cy + 13.2, cz - 2.8)
                ph = r1 * 6.283
                px = cx + 0.5 + 0.38 * math.sin(tm * (0.6 + r2) + ph)
                py = cy + 0.5 + 0.38 * math.sin(tm * (0.5 + r3) + ph * 1.7)
                pz = cz + 0.5 + 0.38 * math.sin(tm * (0.7 + r1) + ph * 2.3)
                ddx = px - x; ddy = py - y; ddz = pz - z
                d = ddx * ddx + ddy * ddy + ddz * ddz
                if d < f1:
                    f2 = f1; f1 = d
                elif d < f2:
                    f2 = d
    return math.sqrt(f1), math.sqrt(f2)

# ---------------------------------------------------------------- the photosphere
GRAN = 560.0          # granules per solar radius (~1 250 km cells)

@nb.njit(inline='always')
def photo(px, py, pz, mu, fp, tm, spots, ns, iso, sp_gain):
    """emitted intensity (r, g, b) of the photosphere at surface point p (unit), mu = cos of the viewing angle,
    fp = the pixel footprint in solar radii (for filtering the granulation). spots: ns x 6 (x, y, z, r_umbra, r_pen, seed)"""
    # limb darkening (quadratic; stronger in blue -> the limb is warmer)
    q = 1.0 - mu
    lr = 1.0 - 0.47 * q - 0.23 * q * q
    lg = 1.0 - 0.58 * q - 0.20 * q * q
    lb = 1.0 - 0.72 * q - 0.16 * q * q
    # granulation, filtered by the footprint: full contrast when a granule spans > ~6 px
    gsz = 1.0 / GRAN
    gk = min(1.0, max(0.0, (gsz / max(fp, 1e-9) - 1.5) / 4.5))
    gval = 0.0
    if gk > 0.0:
        wx = px * GRAN; wy = py * GRAN; wz = pz * GRAN
        wq = vn3(wx * 0.9, wy * 0.9, wz * 0.9 + tm * 0.1) - 0.5
        wr = vn3(wx * 0.9 + 5.2, wy * 0.9 - 3.1, wz * 0.9) - 0.5
        f1, f2 = worley(wx + wq * 0.55, wy + wr * 0.55, wz + (wq - wr) * 0.4, tm)
        e = f2 - f1
        sub = vn3(px * GRAN * 2.7, py * GRAN * 2.7, pz * GRAN * 2.7 + tm * 0.2)
        lane = min(1.0, e / (0.45 + 0.35 * sub)); lane = lane * lane * (3 - 2 * lane)   # soft dark lanes between the granules
        cen = 1.0 - min(1.0, f1 / 0.85); cen = cen * cen * (3 - 2 * cen)
        meso = vn3(px * GRAN * 0.23, py * GRAN * 0.23, pz * GRAN * 0.23 + tm * 0.05)
        gval = (0.50 + 0.42 * lane + 0.20 * cen * lane) * (0.93 + 0.10 * sub) * (0.92 + 0.16 * meso) - 0.95
        gval *= gk * (0.55 + 0.45 * mu)                        # less contrast towards the limb (foreshortened)
    # the mottle that remains when the granules are too small to see (and the supergranulation network)
    sg = fbm3(px * 38.0, py * 38.0, pz * 38.0, 3)
    mott = (sg - 0.5) * 0.05 * (1.0 - 0.6 * gk)
    # faculae: bright network near the active regions, visible mostly towards the limb
    fac = 0.0
    spot = 1.0; sr = 1.0; sgc = 1.0; sbc = 1.0; spotness = 0.0
    for s in range(ns):
        sx = spots[s, 0]; sy = spots[s, 1]; sz = spots[s, 2]; ru = spots[s, 3]; rp = spots[s, 4]; seed = spots[s, 5]
        cd = px * sx + py * sy + pz * sz
        if cd < 0.9: continue
        d = math.acos(min(1.0, cd))                             # angular distance (radians = solar radii on the surface)
        # facular halo around each spot
        if d < rp * 4.0:
            fn = fbm3(px * 160.0 + seed, py * 160.0, pz * 160.0, 3)
            fac += max(0.0, fn - 0.48) * 1.6 * (1.0 - d / (rp * 4.0)) * (q ** 1.5) * 1.6
        if d > rp * 1.35: continue
        # local polar coordinates around the spot centre
        ex = -sy; ey = sx; ez = 0.0
        en = math.sqrt(ex * ex + ey * ey) + 1e-9; ex /= en; ey /= en
        nx = sy * ez - sz * ey; ny = sz * ex - sx * ez; nz = sx * ey - sy * ex
        a = px * ex + py * ey + pz * ez; b = px * nx + py * ny + pz * nz
        ph = math.atan2(b, a)
        # ragged edges
        edge_p = rp * (1.0 + 0.16 * (vn3(math.cos(ph) * 3.0 + seed, math.sin(ph) * 3.0, seed) - 0.5) * 2.0
                       + 0.06 * (vn3(math.cos(ph) * 11.0 + seed, math.sin(ph) * 11.0, 1.3) - 0.5) * 2.0
                       + 0.045 * (vn3(math.cos(ph) * 60.0 + seed, math.sin(ph) * 60.0, 2.7) - 0.5) * 2.0)
        edge_u = ru * (1.0 + 0.22 * (vn3(math.cos(ph) * 4.0 - seed, math.sin(ph) * 4.0, 7.1) - 0.5) * 2.0)
        aa = max(fp * 1.2, rp * 0.01)
        kp = min(1.0, max(0.0, (edge_p - d) / aa + 0.5))       # inside the penumbra
        ku = min(1.0, max(0.0, (edge_u - d) / aa + 0.5))       # inside the umbra
        if kp <= 0.0: continue
        # penumbral filaments: bright/dark radial streaks, with dark cores; they stream outwards slowly (Evershed flow)
        rr = (d - edge_u) / max(edge_p - edge_u, 1e-6)
        phw = ph + 0.10 * (vn3(rr * 1.5 + seed, ph * 2.0, 4.0) - 0.5) + 0.05 * rr * math.sin(ph * 3.0 + seed)
        fil = vn3(phw * 80.0 + seed, rr * 1.6 - tm * 0.15, 0.5) * 0.55 + vn3(phw * 190.0, rr * 3.0 - tm * 0.25, 2.5) * 0.45
        fil *= 0.75 + 0.5 * vn3(phw * 25.0, rr * 5.0, 8.0)
        fil = min(1.0, max(0.0, 0.5 + (fil - 0.5) * 2.6))
        pen = 0.38 + 0.50 * fil * fil + 0.08 * rr
        # umbra: dark, red, with umbral dots
        ud = vn3(px * 2600.0, py * 2600.0, pz * 2600.0 + tm * 0.3)
        umb = 0.035 + 0.08 * max(0.0, ud - 0.62) * 4.0
        val = pen * (1.0 - ku) + umb * ku
        f = 1.0 - kp + kp * val
        if f < spot:
            spot = f
            sr = 1.0; sgc = 1.0 - 0.12 * kp - 0.20 * ku; sbc = 1.0 - 0.25 * kp - 0.42 * ku
        spotness = max(spotness, kp)
    I = (1.0 + (gval + mott) * (1.0 - spotness) + fac * 0.35) * spot
    # isolation: the photosphere fades out and the spot is shown on its own, exposed up
    if iso > 0.0:
        keep = spotness ** 0.7
        Ic = max(I, 0.0) ** 0.42 * sp_gain * keep
        I = I * (1.0 - iso * 0.9) + Ic * iso
    return I * lr * sr, I * lg * sgc, I * lb * sbc

# ---------------------------------------------------------------- the frame kernel
@nb.njit(parallel=True, fastmath=True)
def k_sun(out, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, rot, spots, tm, gain, cor_k, rim_k, iso, sp_gain,
          tint_r, tint_g, tint_b):
    """the Sun (radius 1 at the origin) seen from camera o (axes f, r, u; k px per unit at distance 1).
    rot: body -> world rotation (3x3). Adds into out (H x W x 3)."""
    Hh, Ww = out.shape[0], out.shape[1]
    # the body frame direction of the camera, for the corona pattern
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            bq = dx * ox + dy * oy + dz * oz
            tc = -bq                                                     # closest approach along the ray
            cxp = ox + tc * dx; cyp = oy + tc * dy; czp = oz + tc * dz
            b2 = cxp * cxp + cyp * cyp + czp * czp; b = math.sqrt(b2)
            dist_c = max(tc, 1e-6)
            fp = dist_c / k / n                                          # pixel footprint near the Sun
            r_ = 0.0; g_ = 0.0; bl = 0.0
            cover = 0.0
            if tc > 0 and b < 1.0 + fp * 2:
                cover = min(1.0, max(0.0, (1.0 - b) / max(fp, 1e-9) + 0.5))
            if cover > 0.0:
                bb = min(b, 0.999999)
                th = tc - math.sqrt(1.0 - bb * bb)
                hx = ox + th * dx; hy = oy + th * dy; hz = oz + th * dz
                hn = math.sqrt(hx * hx + hy * hy + hz * hz); hx /= hn; hy /= hn; hz /= hn
                mu = max(0.0, -(hx * dx + hy * dy + hz * dz))
                fp = max(th, 1e-6) / k / n
                # body coordinates
                qx = rot[0, 0] * hx + rot[1, 0] * hy + rot[2, 0] * hz
                qy = rot[0, 1] * hx + rot[1, 1] * hy + rot[2, 1] * hz
                qz = rot[0, 2] * hx + rot[1, 2] * hy + rot[2, 2] * hz
                fps = fp / max(mu, 0.08)
                pr, pg, pb = photo(qx, qy, qz, max(mu, 0.02), fps, tm, spots, spots.shape[0], iso, sp_gain)
                r_ += pr * cover * gain * tint_r; g_ += pg * cover * gain * tint_g; bl += pb * cover * gain * tint_b
            # the corona: line-of-sight integral of a power-law density past the limb, shaped by streamers and plumes
            if b > 0.98 and cor_k > 0.0:
                half = 1.0
                if tc < 0:
                    # the nearest point on the ray is the camera itself: use its distance (continuous at tc = 0)
                    cxp = ox; cyp = oy; czp = oz; b = math.sqrt(ox * ox + oy * oy + oz * oz)
                    half = math.exp(tc * 2.5)
                bx = cxp / b; by = cyp / b; bz = czp / b
                qx = rot[0, 0] * bx + rot[1, 0] * by + rot[2, 0] * bz
                qy = rot[0, 1] * bx + rot[1, 1] * by + rot[2, 1] * bz
                qz = rot[0, 2] * bx + rot[1, 2] * by + rot[2, 2] * bz
                lat = math.asin(min(1.0, max(-1.0, qz))); lon = math.atan2(qy, qx)
                bb = max(b, 1.0)
                base = 0.45 * bb ** -9.0 + 0.30 * bb ** -3.2 + 0.05 * bb ** -1.6
                # streamers: broad helmets at low latitudes, thinner rays everywhere; plumes over the poles
                hel = 0.0
                for m in range(5):
                    lc = math.sin(m * 1.7 + 0.4) * 0.45
                    lo = m * 1.2566 + 0.3
                    dlo = math.atan2(math.sin(lon - lo), math.cos(lon - lo))
                    w = 0.22 + 0.10 * bb
                    hel += math.exp(-((lat - lc) / w) ** 2 - (dlo / 0.9) ** 2) * (0.8 + 0.6 * (bb - 1.0))
                rays = vn3(math.cos(lat) * math.cos(lon) * 14.0, math.cos(lat) * math.sin(lon) * 14.0, math.sin(lat) * 14.0)
                rays2 = vn3(math.cos(lat) * math.cos(lon) * 45.0 + 3.0, math.cos(lat) * math.sin(lon) * 45.0, math.sin(lat) * 45.0)
                pol = math.exp(-((abs(lat) - 1.5708) / 0.45) ** 2) * (0.5 + 0.8 * rays2)
                ckv = base * (0.35 + 1.4 * hel + 0.5 * pol) * (0.65 + 0.55 * rays + 0.35 * rays2)
                # fade the corona in front of the disc (it lies in front of a much brighter surface)
                fr = 1.0 - cover
                ckv *= cor_k * fr * half
                r_ += ckv * 1.00; g_ += ckv * 0.88; bl += ckv * 0.70
                # the chromosphere: a thin pink-red rim just past the limb, with spicules
                if b < 1.05 and rim_k > 0.0:
                    sp = vn3(lon * 160.0 + tm * 0.2, lat * 160.0, tm * 0.1)
                    hgt = 0.0018 + 0.0035 * sp
                    rim = math.exp(-max(0.0, b - 1.0) / hgt) * fr
                    r_ += rim * rim_k * 1.0; g_ += rim * rim_k * 0.32; bl += rim * rim_k * 0.36
            keep = 1.0 - cover
            out[j, i, 0] = out[j, i, 0] * keep + r_; out[j, i, 1] = out[j, i, 1] * keep + g_; out[j, i, 2] = out[j, i, 2] * keep + bl

# ---------------------------------------------------------------- arches: coronal loops and prominences, as splats
@nb.njit(fastmath=True)
def _proj(pts, rad, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, Ww, Hh, scr, front_k):
    """screen x, y, radius px of each point (radius -1 when hidden by the Sun or behind the camera)"""
    for p in range(pts.shape[0]):
        scr[p, 2] = -1.0
        X = pts[p, 0] - ox; Y = pts[p, 1] - oy; Z = pts[p, 2] - oz
        z = X * fx + Y * fy + Z * fz
        if z <= 1e-4: continue
        L = math.sqrt(X * X + Y * Y + Z * Z)
        dx = X / L; dy = Y / L; dz = Z / L
        bq = dx * ox + dy * oy + dz * oz
        cc = ox * ox + oy * oy + oz * oz - 1.0
        disc = bq * bq - cc
        front = 1.0
        if disc > 0:
            t0 = -bq - math.sqrt(disc)
            if 0 < t0 < L - 1e-4: continue
            if t0 >= L - 1e-4: front = front_k
        sx = Ww / 2 + k * (X * rx + Y * ry + Z * rz) / z
        sy = Hh / 2 - k * (X * ux + Y * uy + Z * uz) / z
        rp = k * rad[p] / z
        scr[p, 3] = front
        if sx < -4 * rp - 4 or sx > Ww + 4 * rp + 4 or sy < -4 * rp - 4 or sy > Hh + 4 * rp + 4: continue
        scr[p, 0] = sx; scr[p, 1] = sy; scr[p, 2] = rp

@nb.njit(parallel=True, fastmath=True)
def _splat_bands(out, scr, col, nb_):
    Hh, Ww = out.shape[0], out.shape[1]
    bh = (Hh + nb_ - 1) // nb_
    for band in nb.prange(nb_):
        ya = band * bh; yb = min(Hh, ya + bh)
        for p in range(scr.shape[0]):
            rp0 = scr[p, 2]
            if rp0 < 0: continue
            sx = scr[p, 0]; sy = scr[p, 1]
            rp = max(0.7, rp0)
            amp = (1.0 if rp0 > 0.7 else (rp0 / 0.7) ** 2) * scr[p, 3]
            R2 = int(rp * 2.5) + 1
            j0 = max(ya, int(sy) - R2); j1 = min(yb - 1, int(sy) + R2)
            if j0 > j1: continue
            i0 = max(0, int(sx) - R2); i1 = min(Ww - 1, int(sx) + R2)
            inv = 1.0 / (rp * rp)
            for jj in range(j0, j1 + 1):
                for ii in range(i0, i1 + 1):
                    ddx = ii + 0.5 - sx; ddy = jj + 0.5 - sy
                    w = math.exp(-(ddx * ddx + ddy * ddy) * inv) * amp
                    if w < 2e-3: continue
                    out[jj, ii, 0] += col[p, 0] * w; out[jj, ii, 1] += col[p, 1] * w; out[jj, ii, 2] += col[p, 2] * w

def splat(out, pts, col, rad, cam, front_k=0.15):
    """cam: (o, f, r, u, k) — soft additive points, hidden behind the Sun"""
    o, f, r, u, k = cam
    scr = np.empty((pts.shape[0], 4))
    _proj(np.ascontiguousarray(pts, np.float64), np.ascontiguousarray(rad, np.float64), o[0], o[1], o[2], f[0], f[1], f[2],
          r[0], r[1], r[2], u[0], u[1], u[2], k, out.shape[1], out.shape[0], scr, front_k)
    _splat_bands(out, scr, np.ascontiguousarray(col, np.float64), 32)
