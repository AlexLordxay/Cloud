# A Ukrainian sunflower field for «А ти уявляєш Сонце так?» — every plant is drawn in 3D (numba ray–plane rasterizer):
# a stem, two big leaves, and the head: a seed disc (Fibonacci spiral), ~30 petals that glow when the Sun is behind them,
# green sepals on the back. Heads face the east (mature sunflowers do), tilted down, swaying a little in the wind.
# Local frame: metres, x = east, y = north, z = up, origin on the ground at the home point.
import math
import numpy as np
import numba as nb

GOLD = 2.399963229728653     # the golden angle

def plants(seed=7, radius=520.0, row=0.75, step=0.38):
    """plant table: x, y, h(eight), r(head radius), az(facing), tilt, phase, leaf az 1, leaf az 2, leaf h 1, leaf h 2, size"""
    rng = np.random.default_rng(seed)
    xs = np.arange(-radius, radius, row)
    rows = []
    for x in xs:
        ny = int(2 * radius / step)
        y = -radius + np.arange(ny) * step + rng.normal(0, 0.05, ny)
        keep = (x * x + y * y) < radius * radius
        y = y[keep]; n = len(y)
        xx = x + rng.normal(0, 0.06, n)
        h = rng.normal(1.75, 0.15, n)
        r = rng.normal(0.135, 0.02, n).clip(0.08, 0.2)
        az = np.radians(rng.normal(0.0, 14.0, n))
        tilt = np.radians(rng.normal(22.0, 8.0, n))
        ph = rng.random(n) * 6.283
        la1 = rng.random(n) * 6.283; la2 = la1 + np.pi + rng.normal(0, 0.5, n)
        lh1 = h * rng.uniform(0.45, 0.6, n); lh2 = h * rng.uniform(0.65, 0.8, n)
        sz = rng.uniform(0.85, 1.15, n)
        rows.append(np.stack([xx, y, h, r, az, tilt, ph, la1, la2, lh1, lh2, sz], 1))
    return np.ascontiguousarray(np.concatenate(rows))

# ---------------------------------------------------------------- primitives: (type, centre xyz, axis u xyz, axis v xyz, size a, b, plant idx)
# type 0 = head front/back disc (u, v in the disc plane; normal = u x v), 1 = leaf, 2 = stem (a ribbon facing the camera)
@nb.njit(fastmath=True)
def build_prims(P, t, cx, cy, cz, maxd, wind, face_az, lmax):
    n = P.shape[0]
    prim = np.zeros((n * 4, 14))
    m = 0
    for i in range(n):
        x = P[i, 0]; y = P[i, 1]
        dx = x - cx; dy = y - cy
        d2 = dx * dx + dy * dy
        if d2 > maxd * maxd: continue
        h = P[i, 2]; r = P[i, 3] * P[i, 11]; az = P[i, 4] + face_az; tilt = P[i, 5]; ph = P[i, 6]
        sway = wind * (0.035 * math.sin(t * 1.3 + ph) + 0.015 * math.sin(t * 2.9 + ph * 1.7))
        # the head centre (slightly in front of the stem top, as it bends)
        fx = math.sin(az); fy = math.cos(az)                 # the facing direction on the ground (azimuth from north)
        hx = x + fx * 0.12 + sway; hy = y + fy * 0.12; hz = h - 0.08
        # the disc's normal: horizontal facing, tipped down by tilt
        nx = fx * math.cos(tilt); ny = fy * math.cos(tilt); nz = -math.sin(tilt)
        # in-disc axes: u horizontal (perpendicular to the facing), v = n x u
        ux = fy; uy = -fx; uz = 0.0
        vx = ny * uz - nz * uy; vy = nz * ux - nx * uz; vz = nx * uy - ny * ux
        prim[m, 0] = 0; prim[m, 1] = hx; prim[m, 2] = hy; prim[m, 3] = hz
        prim[m, 4] = ux; prim[m, 5] = uy; prim[m, 6] = uz; prim[m, 7] = vx; prim[m, 8] = vy; prim[m, 9] = vz
        prim[m, 10] = r * 1.75; prim[m, 11] = r; prim[m, 12] = i; prim[m, 13] = d2; m += 1
        if d2 > lmax * lmax: continue
        # stem: from the ground to just behind the head
        prim[m, 0] = 2; prim[m, 1] = x; prim[m, 2] = y; prim[m, 3] = 0.0
        prim[m, 4] = hx - fx * 0.06; prim[m, 5] = hy - fy * 0.06; prim[m, 6] = hz + 0.02
        prim[m, 10] = 0.016; prim[m, 11] = 0.0; prim[m, 12] = i; prim[m, 13] = d2 + 0.01; m += 1
        # two leaves
        for q in range(2):
            la = P[i, 7 + q]; lh = P[i, 9 + q]
            lx = math.sin(la); ly = math.cos(la)
            L = 0.26 * P[i, 11]
            ccx = x + lx * (L * 0.55) + sway * lh / h; ccy = y + ly * (L * 0.55); ccz = lh - 0.06
            # the leaf axis (outwards and drooping) and the cross axis
            ax = lx * 0.85; ay = ly * 0.85; az_ = -0.52
            bx = ly; by = -lx; bz = 0.0
            prim[m, 0] = 1; prim[m, 1] = ccx; prim[m, 2] = ccy; prim[m, 3] = ccz
            prim[m, 4] = ax; prim[m, 5] = ay; prim[m, 6] = az_; prim[m, 7] = bx; prim[m, 8] = by; prim[m, 9] = bz
            prim[m, 10] = L; prim[m, 11] = L * 0.85; prim[m, 12] = i; prim[m, 13] = d2 + 0.02 * (q + 1); m += 1
    return prim[:m]

@nb.njit(inline='always')
def hsh(a, b):
    s = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return s - math.floor(s)

@nb.njit(fastmath=True)
def head_shade(lu, lv, r, front, idx, t):
    """colour (linear) and alpha of a head at disc coords (lu, lv) metres; r = seed-disc radius"""
    rr = math.sqrt(lu * lu + lv * lv) / r
    ang = math.atan2(lv, lu)
    if front:
        if rr < 1.0:
            # seeds: Fibonacci spiral cells, darker centre ring
            k = rr * rr * 260.0
            nn = math.floor(k)
            best = 9.0
            for dn in range(-14, 15):
                q = nn + dn
                if q < 0: continue
                ra = math.sqrt(q / 260.0); aa = q * GOLD
                ex = ra * math.cos(aa) - rr * math.cos(ang); ey = ra * math.sin(aa) - rr * math.sin(ang)
                d = ex * ex + ey * ey
                if d < best: best = d
            cell = math.sqrt(best) * 16.0
            seed = 1.0 - min(1.0, cell)
            base = 0.11 + 0.10 * seed
            ring = math.exp(-((rr - 0.82) / 0.12) ** 2)
            cr = base * (1.0 + 0.6 * ring) * 0.55 + 0.02; cg = base * 0.32 + 0.012 * ring; cb = base * 0.10
            if rr < 0.35:
                cr *= 0.8; cg *= 1.25                            # a greenish-brown middle (the unopened florets)
            return cr, cg, cb, 1.0, 0.0
        # petals: ~32 in two whorls
        if rr > 1.75: return 0.0, 0.0, 0.0, 0.0, 0.0
        npet = 32.0
        a2 = ang + idx * 0.37
        f1 = (a2 * npet / 6.283185) % 1.0; f2 = (a2 * npet / 6.283185 + 0.5) % 1.0
        L1 = 1.62 - 0.12 * hsh(math.floor(a2 * npet / 6.283185), idx); L2 = 1.48 - 0.10 * hsh(math.floor(a2 * npet / 6.283185 + 0.5), idx + 3.0)
        s = (rr - 1.0) / (L1 - 1.0)
        sc_ = min(1.0, max(0.0, s))
        w1 = 0.40 * math.sin(min(1.0, sc_ * 1.6) * 1.5708) ** 0.6 * (1.0 - sc_ ** 2.2) + 0.015
        p1 = 1.0 if (abs(f1 - 0.5) < w1 and s < 1.0) else 0.0
        s2 = (rr - 1.0) / (L2 - 1.0)
        sc2 = min(1.0, max(0.0, s2))
        w2 = 0.40 * math.sin(min(1.0, sc2 * 1.6) * 1.5708) ** 0.6 * (1.0 - sc2 ** 2.2) + 0.015
        p2 = 1.0 if (abs(f2 - 0.5) < w2 and s2 < 1.0) else 0.0
        if p1 + p2 <= 0.0: return 0.0, 0.0, 0.0, 0.0, 0.0
        vein = 0.88 + 0.12 * math.cos((f1 - 0.5) * 18.0)
        pv = 0.82 + 0.3 * hsh(math.floor(a2 * npet / 6.283185) + 0.5, idx + 1.0)
        base_ = 0.75 + 0.25 * min(1.0, max(0.0, s * 2.0))
        cr = 0.78 * vein * pv * base_; cg = 0.42 * vein * pv * base_ * (0.92 + 0.1 * s); cb = 0.012
        if p1 == 0.0:
            cr *= 0.85; cg *= 0.82                             # the back whorl a touch deeper
        return cr, cg, cb, 1.0, 1.0
    else:
        # back: green receptacle and pointed sepals
        if rr < 1.15:
            return 0.06, 0.11, 0.025, 1.0, 0.0
        if rr > 1.7: return 0.0, 0.0, 0.0, 0.0, 0.0
        f1 = (ang * 22.0 / 6.283185) % 1.0
        s = (rr - 1.15) / 0.5
        if abs(f1 - 0.5) < 0.5 * (1.0 - s) ** 0.8:
            return 0.05, 0.10, 0.02, 1.0, 0.0
        # petals seen from behind (paler, translucent)
        npet = 32.0
        f2 = (ang * npet / 6.283185) % 1.0
        s3 = (rr - 1.0) / 0.6
        if abs(f2 - 0.5) < 0.5 * math.sin(min(1.0, max(0.0, s3)) * 3.14159) ** 0.55 and s3 < 1.0:
            return 0.70, 0.40, 0.02, 1.0, 1.0
        return 0.0, 0.0, 0.0, 0.0, 0.0

@nb.njit(parallel=True, fastmath=True)
def k_flowers(out, acc, A, prim, order, scr, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, sx, sy, sz, light, amb,
              haze_r, haze_g, haze_b, haze_d, t, nbands, fade_near, fade_far):
    """paints the primitives NEAR-to-far (order) into acc / A (front-to-back 'under' compositing: a pixel already
    covered is skipped before any work); scr[p] = (x0, x1, y0, y1) screen boxes"""
    Hh, Ww = out.shape[0], out.shape[1]
    bh = (Hh + nbands - 1) // nbands
    for band in nb.prange(nbands):
        ya = band * bh; yb = min(Hh, ya + bh)
        for oi in range(order.shape[0]):
            p = order[oi]
            if scr[p, 0] > scr[p, 1]: continue
            j0 = max(ya, int(scr[p, 2])); j1 = min(yb - 1, int(scr[p, 3]))
            if j0 > j1: continue
            i0 = max(0, int(scr[p, 0])); i1 = min(Ww - 1, int(scr[p, 1]))
            typ = int(prim[p, 0])
            cxp = prim[p, 1]; cyp = prim[p, 2]; czp = prim[p, 3]
            dist = math.sqrt((cxp - ox) ** 2 + (cyp - oy) ** 2 + (czp - oz) ** 2)
            hz = 1.0 - math.exp(-dist / haze_d)
            dxy = math.sqrt((cxp - ox) ** 2 + (cyp - oy) ** 2)
            dfade = min(1.0, max(0.0, (fade_far - dxy) / (fade_far - fade_near)))
            dfade = dfade * dfade * (3 - 2 * dfade)
            if dfade <= 0.0: continue
            # supersampling: 2x2 for the near, big ones; 1 for the rest
            ss = 2 if ((scr[p, 1] - scr[p, 0]) > 24 and typ == 0) else 1
            for jj in range(j0, j1 + 1):
                for ii in range(i0, i1 + 1):
                    if A[jj, ii] > 0.996: continue
                    ar = 0.0; ag = 0.0; ab = 0.0; aa = 0.0
                    for sj in range(ss):
                        for si in range(ss):
                            X = (ii + (si + 0.5) / ss - Ww / 2) / k; Y = -(jj + (sj + 0.5) / ss - Hh / 2) / k
                            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
                            if typ == 2:
                                # stem: distance from the ray to the segment
                                ax_ = prim[p, 4] - cxp; ay_ = prim[p, 5] - cyp; az_ = prim[p, 6] - czp
                                wx = ox - cxp; wy = oy - cyp; wz = oz - czp
                                a = dx * dx + dy * dy + dz * dz; b = dx * ax_ + dy * ay_ + dz * az_
                                c = ax_ * ax_ + ay_ * ay_ + az_ * az_; d = dx * wx + dy * wy + dz * wz; e = ax_ * wx + ay_ * wy + az_ * wz
                                den = a * c - b * b
                                if den < 1e-12: continue
                                sc = (b * e - c * d) / den; tc = (a * e - b * d) / den
                                tc = min(1.0, max(0.0, tc))
                                px_ = ox + dx * sc - (cxp + ax_ * tc); py_ = oy + dy * sc - (cyp + ay_ * tc); pz_ = oz + dz * sc - (czp + az_ * tc)
                                dd = math.sqrt(px_ * px_ + py_ * py_ + pz_ * pz_)
                                wdt = prim[p, 10] * (1.0 - 0.4 * tc)
                                if dd < wdt and sc > 0:
                                    shade = 0.55 + 0.45 * tc
                                    ar += 0.035 * shade; ag += 0.075 * shade; ab += 0.018 * shade; aa += 1.0
                                continue
                            # plane primitives
                            uxp = prim[p, 4]; uyp = prim[p, 5]; uzp = prim[p, 6]; vxp = prim[p, 7]; vyp = prim[p, 8]; vzp = prim[p, 9]
                            nx = uyp * vzp - uzp * vyp; ny = uzp * vxp - uxp * vzp; nz = uxp * vyp - uyp * vxp
                            nn = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nn; ny /= nn; nz /= nn
                            dn = dx * nx + dy * ny + dz * nz
                            if abs(dn) < 1e-6: continue
                            tt = ((cxp - ox) * nx + (cyp - oy) * ny + (czp - oz) * nz) / dn
                            if tt <= 0: continue
                            qx = ox + dx * tt - cxp; qy = oy + dy * tt - cyp; qz = oz + dz * tt - czp
                            uu = qx * uxp + qy * uyp + qz * uzp; vv = qx * vxp + qy * vyp + qz * vzp
                            ln_ = nx * sx + ny * sy + nz * sz
                            if typ == 0:
                                front = dn < 0
                                cr, cg, cb, al, pet = head_shade(uu, vv, prim[p, 11], front, prim[p, 12], t)
                                if al <= 0: continue
                                fl = ln_ if front else -ln_
                                lit = max(0.0, fl) * light + amb
                                if pet > 0.0 and fl < 0.0:
                                    lit += -fl * light * 0.55            # sunlight through the petals
                                ar += cr * lit; ag += cg * lit; ab += cb * lit; aa += 1.0
                            else:
                                # leaf: heart-ish outline along u (0 at the stem end … 1 at the tip), with veins
                                su = (uu / prim[p, 10] + 1.0) * 0.5
                                if su < 0 or su > 1: continue
                                wv = 0.55 * math.sin(min(1.0, su * 1.15) * 3.14159) ** 0.7 * (1.0 - 0.25 * su)
                                if abs(vv / prim[p, 11]) > wv: continue
                                vein = 0.85 + 0.15 * abs(math.sin(vv / prim[p, 11] * 14.0 - su * 5.0))
                                fl = abs(ln_)
                                back = (dn > 0) != (ln_ > 0)
                                lit = fl * light * (0.55 if back else 1.0) + amb
                                ar += 0.055 * vein * lit; ag += 0.11 * vein * lit; ab += 0.022 * vein * lit; aa += 1.0
                    if aa <= 0: continue
                    cov = aa / (ss * ss) * dfade
                    cr = ar / aa; cg = ag / aa; cb = ab / aa
                    cr = cr * (1 - hz) + haze_r * hz; cg = cg * (1 - hz) + haze_g * hz; cb = cb * (1 - hz) + haze_b * hz
                    w_ = (1.0 - A[jj, ii]) * cov
                    acc[jj, ii, 0] += cr * w_; acc[jj, ii, 1] += cg * w_; acc[jj, ii, 2] += cb * w_
                    A[jj, ii] += w_

@nb.njit(parallel=True, fastmath=True)
def screen_boxes(prim, scr, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, Ww, Hh):
    for p in nb.prange(prim.shape[0]):
        scr[p, 0] = 1.0; scr[p, 1] = 0.0
        typ = int(prim[p, 0])
        if typ == 2:
            pts = ((prim[p, 1], prim[p, 2], prim[p, 3]), (prim[p, 4], prim[p, 5], prim[p, 6]))
            rad = prim[p, 10] * 1.5
        else:
            pts = ((prim[p, 1], prim[p, 2], prim[p, 3]), (prim[p, 1], prim[p, 2], prim[p, 3]))
            rad = max(prim[p, 10], prim[p, 11]) * 1.05
        x0 = 1e9; x1 = -1e9; y0 = 1e9; y1 = -1e9; ok = False
        for q in range(2):
            X = pts[q][0] - ox; Y = pts[q][1] - oy; Z = pts[q][2] - oz
            z = X * fx + Y * fy + Z * fz
            if z < 0.05: continue
            sx = Ww / 2 + k * (X * rx + Y * ry + Z * rz) / z; sy = Hh / 2 - k * (X * ux + Y * uy + Z * uz) / z
            rp = k * rad / z + 1.5
            x0 = min(x0, sx - rp); x1 = max(x1, sx + rp); y0 = min(y0, sy - rp); y1 = max(y1, sy + rp); ok = True
        if not ok or x1 < 0 or x0 > Ww or y1 < 0 or y0 > Hh: continue
        if x1 - x0 < 0.6 and y1 - y0 < 0.6: continue
        scr[p, 0] = x0; scr[p, 1] = x1; scr[p, 2] = y0; scr[p, 3] = y1

_P = {}
def field(img, c_local, sun_local, t, light=2.2, amb=0.35, haze=(0.6, 0.62, 0.66), haze_d=900.0, maxd=440.0, wind=1.0, face_az=95.0, lmax=70.0, near=0.3):
    """c_local: (o, f, r, u, k) in the field's metres; sun_local: unit vector to the Sun"""
    if 'P' not in _P: _P['P'] = plants()
    o, f, r, u, k = c_local
    prim = build_prims(_P['P'], t, o[0], o[1], o[2], maxd, wind, math.radians(face_az), lmax)
    scr = np.empty((prim.shape[0], 4))
    screen_boxes(prim, scr, o[0], o[1], o[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, img.shape[1], img.shape[0])
    dc = np.sqrt((prim[:, 1] - o[0]) ** 2 + (prim[:, 2] - o[1]) ** 2 + (prim[:, 3] - o[2]) ** 2)
    vis = np.nonzero((scr[:, 1] >= scr[:, 0]) & (dc > near))[0]
    # near to far by the true distance from the camera (each plant's parts keep their order: head, stem, leaves)
    d = (prim[vis, 1] - o[0]) ** 2 + (prim[vis, 2] - o[1]) ** 2 + (prim[vis, 3] - o[2]) ** 2
    order = vis[np.argsort(d, kind='stable')].astype(np.int64)
    s = np.asarray(sun_local, float)
    acc = np.zeros_like(img); A = np.zeros(img.shape[:2], np.float32)
    k_flowers(img, acc, A, prim, order, scr, o[0], o[1], o[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k,
              s[0], s[1], s[2], light, amb, haze[0], haze[1], haze[2], haze_d, t, 48, maxd * 0.62, maxd)
    img[:] = acc + img * (1.0 - A)[..., None]
    return len(order)
