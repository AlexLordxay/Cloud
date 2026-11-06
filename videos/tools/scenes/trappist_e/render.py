# «Знайомся: TRAPPIST-1e» — one frame of the 3D shots: the baked planet (planet.py), its haze and glint, the star,
# the neighbour planets and the sky, then bloom, tone mapping and the 720x1280 frame.
#   python3 render.py prep        -> work/trappist_e/maps/pack.npy (the maps combined for the renderer, float32)
import math, os, sys
import numpy as np
from numba import njit, prange
from PIL import Image, ImageFilter, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, TOOLS]
import planet as PL
import still as ST
from still import fbm, smooth, PERM

W, H, SS = 720, 1280, 2
RW, RH = W * SS, H * SS
PACK = os.path.join(PL.MAPS, 'pack.npy')
STARC = PL.STAR * PL.EXP

def prep():
    M = {n: np.load(os.path.join(PL.MAPS, n + '.npy')).astype(np.float32) for n in ('alb', 'lig', 'oce', 'veg', 'cla', 'clr')}
    v = M['veg'][..., None]
    pk = np.zeros((PL.TH, PL.TW, 14), np.float32)
    pk[..., 0:3] = M['alb'] * M['lig']
    pk[..., 3:6] = v * M['lig']
    pk[..., 6:9] = v * M['alb'] * M['lig']
    pk[..., 9:12] = M['clr']
    pk[..., 12] = M['cla']
    pk[..., 13] = M['oce']
    np.save(PACK, pk)
    print('pack', pk.shape)

_pack = None
def pack():
    global _pack
    if _pack is None: _pack = np.load(PACK, mmap_mode='r')
    return _pack

@njit(cache=True, inline='always')
def _samp(M, TW, TH, nx, ny, nz, c):
    lon = math.atan2(ny, nx); lat = math.asin(min(1.0, max(-1.0, nz)))
    fx = (lon + math.pi) / (2 * math.pi) * TW - 0.5; fy = (math.pi / 2 - lat) / math.pi * TH - 0.5
    x0 = int(math.floor(fx)); y0 = int(math.floor(fy)); ax = fx - x0; ay = fy - y0
    x0m = x0 % TW; x1m = (x0 + 1) % TW; y0c = min(TH - 1, max(0, y0)); y1c = min(TH - 1, max(0, y0 + 1))
    return ((M[y0c, x0m, c] * (1 - ax) + M[y0c, x1m, c] * ax) * (1 - ay) + (M[y1c, x0m, c] * (1 - ax) + M[y1c, x1m, c] * ax) * ay)

@njit(cache=True, parallel=True)
def render_scene(img, mask, RW, RH, ox, oy, oz, rx, ry, rz, ux, uy, uz, fx, fy, fz, TX, TY, M, TW, TH,
                 vk, vr, vg, vb, Sr, Sg, Sb, scx, scy, scz, srad, sint, NB, P, haze, planet_on, gvis):
    HS = 0.035
    AR, AG, AB = 1.0, 0.80, 0.70
    for j in prange(RH):
        for i in range(RW):
            px = ((i + 0.5) / RW * 2 - 1) * TX; py = (1 - (j + 0.5) / RH * 2) * TY
            dx = fx + px * rx + py * ux; dy = fy + px * ry + py * uy; dz = fz + px * rz + py * uz
            nn = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= nn; dy /= nn; dz /= nn
            r = 0.0; g = 0.0; bl = 0.0; m = 0.0
            tbest = 1e30
            # ---- the planet ----
            if planet_on:
                b = ox * dx + oy * dy + oz * dz
                c2 = ox * ox + oy * oy + oz * oz
                h2 = c2 - b * b
                if b < 0 and h2 < (1 + HS * 4) ** 2:
                    hd = math.sqrt(max(h2, 0.0))
                    # closest point of the ray to the centre: its direction lights the haze
                    mx, my, mz = ox - dx * b, oy - dy * b, oz - dz * b
                    mn = math.sqrt(mx * mx + my * my + mz * mz) + 1e-9
                    la = smooth(-0.12, 0.30, mx / mn)
                    fwd = max(0.0, dx)                                          # looking towards the star: bright rim
                    phase = 1.0 + 4.0 * fwd ** 12
                    la = max(la, 0.55 * fwd ** 40)                              # the star behind the planet: a ring all round
                    if h2 < 1.0:
                        t = -b - math.sqrt(1.0 - h2); tbest = t
                        nx, ny, nz = ox + dx * t, oy + dy * t, oz + dz * t
                        mu = nx
                        R0 = _samp(M, TW, TH, nx, ny, nz, 0); G0 = _samp(M, TW, TH, nx, ny, nz, 1); B0 = _samp(M, TW, TH, nx, ny, nz, 2)
                        if vk > 0:
                            R0 += vk * (vr * _samp(M, TW, TH, nx, ny, nz, 3) - _samp(M, TW, TH, nx, ny, nz, 6))
                            G0 += vk * (vg * _samp(M, TW, TH, nx, ny, nz, 4) - _samp(M, TW, TH, nx, ny, nz, 7))
                            B0 += vk * (vb * _samp(M, TW, TH, nx, ny, nz, 5) - _samp(M, TW, TH, nx, ny, nz, 8))
                        ca = _samp(M, TW, TH, nx, ny, nz, 12); oc = _samp(M, TW, TH, nx, ny, nz, 13)
                        r = R0 * (1 - ca) + _samp(M, TW, TH, nx, ny, nz, 9)
                        g = G0 * (1 - ca) + _samp(M, TW, TH, nx, ny, nz, 10)
                        bl = B0 * (1 - ca) + _samp(M, TW, TH, nx, ny, nz, 11)
                        # glint and the mirrored sky on the open water
                        vx, vy, vz = -dx, -dy, -dz
                        hx, hy, hz = 1.0 + vx, vy, vz
                        hn = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9; hx /= hn; hy /= hn; hz /= hn
                        nh = min(1.0, max(0.0, nx * hx + ny * hy + nz * hz))
                        vh = max(0.0, vx * hx + vy * hy + vz * hz)
                        fres = 0.02 + 0.98 * (1 - vh) ** 5
                        term = smooth(-0.035, 0.05, mu)
                        tw = smooth(0.0, 0.22, mu)
                        spec = (nh ** 500 * 7.0 + nh ** 45 * 0.30) * fres * oc * term * (1 - ca)
                        r += spec * Sr; g += spec * Sg * (0.70 + 0.30 * tw); bl += spec * Sb * (0.50 + 0.50 * tw)
                        nv = max(0.0, nx * vx + ny * vy + nz * vz)
                        fr2 = 0.02 + 0.98 * (1 - nv) ** 5
                        amb = smooth(-0.10, 0.25, mu)
                        sky = oc * amb * (0.25 + 0.75 * fr2 * 8.0) * (1 - ca)
                        r += 0.006 * sky; g += 0.020 * sky; bl += 0.055 * sky
                        path = math.sqrt(max((1 + HS) ** 2 - h2, 0.0)) - math.sqrt(max(1.0 - h2, 0.0))
                        # over the disc the air is lit where the ground under it is (the limb keeps the sky-plane light)
                        edge = min(1.0, (path / HS - 1.0) / 6.0)
                        lad = smooth(-0.12, 0.30, nx) * (1 - edge) + la * edge
                        k = haze * 0.022 * (path / HS) ** 1.7 * lad * (1.0 + (phase - 1.0) * edge)
                        r = r * (1 - 0.3 * min(k, 1.0)) + AR * Sr * k; g = g * (1 - 0.3 * min(k, 1.0)) + AG * Sg * k; bl = bl * (1 - 0.3 * min(k, 1.0)) + AB * Sb * k
                        m = 1.0
                    else:
                        path = 2 * math.sqrt(max((1 + HS) ** 2 - h2, 0.0))
                        k = haze * (0.05 * (path / HS) ** 1.2 * la + 0.02 * math.exp(-(hd - 1) / (HS * 0.8)) * la) * phase
                        r += AR * Sr * k; g += AG * Sg * k; bl += AB * Sb * k
            # ---- neighbours: small icy spheres, lit by the star from their own side ----
            for q in range(NB.shape[0]):
                cx, cy, cz, rad = NB[q, 0] - ox, NB[q, 1] - oy, NB[q, 2] - oz, NB[q, 3]
                b = cx * dx + cy * dy + cz * dz
                if b <= 0: continue
                h2 = cx * cx + cy * cy + cz * cz - b * b
                if h2 >= rad * rad: continue
                t = b - math.sqrt(rad * rad - h2)
                if t > tbest: continue
                tbest = t
                nx, ny, nz = (dx * t - cx) / rad, (dy * t - cy) / rad, (dz * t - cz) / rad
                mu = nx * NB[q, 4] + ny * NB[q, 5] + nz * NB[q, 6]
                n1 = fbm(nx * 2.6 + NB[q, 7], ny * 2.6, nz * 2.6, P, 6, 2.1, 0.5)
                n2 = fbm(nx * 9.0 + NB[q, 7], ny * 9.0, nz * 9.0, P, 4, 2.1, 0.5)
                al = 0.60 + 0.16 * n1 + 0.06 * n2
                dif = smooth(-0.04, 0.06, mu) * max(mu, 0.0)
                rim = smooth(0.0, 0.3, mu) * 0.0
                r = al * dif * Sr; g = al * dif * Sg * 0.96; bl = al * dif * Sb * 0.94
                r += 0.006 * smooth(-0.1, 0.2, mu); g += 0.008 * smooth(-0.1, 0.2, mu); bl += 0.014 * smooth(-0.1, 0.2, mu)
                m = 1.0
            # ---- the star: a limb-darkened disc (if nothing is in front) and its glow ----
            if sint > 0:
                vx, vy, vz = scx - ox, scy - oy, scz - oz
                dist = math.sqrt(vx * vx + vy * vy + vz * vz)
                ca_ = (vx * dx + vy * dy + vz * dz) / dist
                ang = math.acos(min(1.0, max(-1.0, ca_)))
                ar_ = math.asin(min(1.0, srad / dist))
                if ang < ar_ and tbest > dist * 0.5:
                    u = ang / ar_
                    mus = math.sqrt(max(0.0, 1 - u * u))
                    I = sint * (0.30 + 0.70 * mus ** 0.8)
                    # star spots and granulation, faint
                    sx_, sy_ = u * math.cos(math.atan2(vz * dy - vy * dz, dx)), u
                    spot = fbm(dx * 900.0, dy * 900.0, dz * 900.0, P, 4, 2.0, 0.5)
                    I *= 1.0 - 0.18 * smooth(0.15, 0.4, spot)
                    r = Sr * I; g = Sg * I * (0.75 + 0.25 * mus); bl = Sb * I * (0.6 + 0.4 * mus)
                    m = 1.0
                elif ang >= ar_:
                    x = ar_ / ang
                    gl = sint * gvis * (0.020 * x ** 2.4 + 0.0025 * x ** 1.1)
                    r += Sr * gl; g += Sg * gl * 0.85; bl += Sb * gl * 0.7
            img[j, i, 0] += r; img[j, i, 1] += g; img[j, i, 2] += bl
            mask[j, i] = m

@njit(cache=True, parallel=True)
def sky_sample(out, photo, PW, PH, RWq, RHq, rx, ry, rz, ux, uy, uz, fx, fy, fz, TX, TY, M00, M01, M02, M10, M11, M12, M20, M21, M22):
    for j in prange(RHq):
        for i in range(RWq):
            px = ((i + 0.5) / RWq * 2 - 1) * TX; py = (1 - (j + 0.5) / RHq * 2) * TY
            dx = fx + px * rx + py * ux; dy = fy + px * ry + py * uy; dz = fz + px * rz + py * uz
            nn = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= nn; dy /= nn; dz /= nn
            gx = M00 * dx + M01 * dy + M02 * dz; gy = M10 * dx + M11 * dy + M12 * dz; gz = M20 * dx + M21 * dy + M22 * dz
            b = math.degrees(math.asin(min(1.0, max(-1.0, gz)))); l = math.degrees(math.atan2(gy, gx))
            ffx = (0.5 - l / 360) * PW - 0.5; ffy = (90 - b) / 180 * PH - 0.5
            x0 = int(math.floor(ffx)); y0 = int(math.floor(ffy)); ax = ffx - x0; ay = ffy - y0
            x0m = x0 % PW; x1m = (x0 + 1) % PW; y0c = min(PH - 1, max(0, y0)); y1c = min(PH - 1, max(0, y0 + 1))
            for c in range(3):
                out[j, i, c] = (photo[y0c, x0m, c] * (1 - ax) + photo[y0c, x1m, c] * ax) * (1 - ay) + (photo[y1c, x0m, c] * (1 - ax) + photo[y1c, x1m, c] * ax) * ay

@njit(cache=True)
def splat(img, mask, xs, ys, br, cr, cg, cb, sig):
    H_, W_ = mask.shape
    for k in range(xs.shape[0]):
        x, y = xs[k], ys[k]
        s = sig * (0.7 + 0.5 * min(br[k], 1.5))
        R = int(3 * s) + 1
        x0, y0 = int(x), int(y)
        for yy in range(y0 - R, y0 + R + 1):
            for xx in range(x0 - R, x0 + R + 1):
                if 0 <= xx < W_ and 0 <= yy < H_ and mask[yy, xx] < 0.5:
                    w = math.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s)) * br[k]
                    img[yy, xx, 0] += cr[k] * w; img[yy, xx, 1] += cg[k] * w; img[yy, xx, 2] += cb[k] * w

# ---- the sky: the ESO photo as a soft glow + a fixed catalogue of sharp stars (random, denser along the Milky Way) ----
def gal_matrix():
    """planet frame -> galactic, so the sky behind the planet is the same as in the approved still"""
    def gal(l, b):
        l, b = math.radians(l), math.radians(b); return np.array([math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b)])
    Fw = gal(318, 14); up = np.array([0.0, 0.0, 1.0]); roll = math.radians(-38)
    Rt = np.cross(up, Fw); Rt /= np.linalg.norm(Rt); Up = np.cross(Fw, Rt)
    Rt, Up = Rt * math.cos(roll) + Up * math.sin(roll), -Rt * math.sin(roll) + Up * math.cos(roll)
    A = np.stack([Rt, Up, Fw], 1)                       # still coords -> galactic
    return A @ PL.B_SP.T                                 # planet -> still -> galactic
GAL = gal_matrix()

_sky = {}
def sky_assets():
    if not _sky:
        Image.MAX_IMAGE_PIXELS = None
        ph = np.asarray(Image.open(os.path.join(TOOLS, 'data', 'sky', 'eso0932a.jpg')).convert('RGB'), np.float32) / 255
        _sky['photo'] = ph
        r = np.random.default_rng(5)
        n = 160000
        u = r.normal(size=(n, 3)); u /= np.linalg.norm(u, axis=1)[:, None]
        g = u @ GAL.T
        b = np.degrees(np.arcsin(np.clip(g[:, 2], -1, 1))); l = np.degrees(np.arctan2(g[:, 1], g[:, 0]))
        PHh, PWw = ph.shape[:2]
        lum = ph[np.clip(((90 - b) / 180 * PHh).astype(int), 0, PHh - 1), ((0.5 - l / 360) * PWw).astype(int) % PWw].mean(-1)
        keep = r.random(n) < 0.30 + 2.0 * lum
        u = u[keep]
        _sky['g'] = u @ GAL.T                               # the catalogue in galactic coordinates
        br = np.clip(r.pareto(1.6, len(u)) * 0.05 + 0.02, 0, 3.0).astype(np.float64)
        t = r.normal(0, 0.18, len(u))
        _sky['v'] = u; _sky['br'] = br; _sky['col'] = np.stack([1 + t, np.ones(len(u)), 1 - t], 1)
        # a deep layer of faint stars for the telephoto view (galactic coordinates)
        nd = 1500000
        g2 = r.normal(size=(nd, 3)).astype(np.float32); g2 /= np.linalg.norm(g2, axis=1)[:, None]
        _sky['dg'] = g2; _sky['dbr'] = (r.pareto(2.2, nd) * 0.03 + 0.012).clip(0, 0.6).astype(np.float64)
        td = r.normal(0, 0.2, nd); _sky['dcol'] = np.stack([1 + td, np.ones(nd), 1 - td], 1)
    return _sky

def cam_basis(pos, target, up=(0, 0, 1)):
    f = np.asarray(target, float) - np.asarray(pos, float); f /= np.linalg.norm(f)
    r = np.cross(np.asarray(up, float), f); r /= np.linalg.norm(r)
    u = np.cross(f, r)
    return r, u, f

def rotz(a):
    c, s_ = math.cos(a), math.sin(a)
    return np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])

def background(r, u, f, TX, TY, mask, star_gain=1.0, photo_gain=0.38, G=None):
    S = sky_assets()
    G = GAL if G is None else G
    q = 4; RWq, RHq = RW // q, RH // q
    out = np.zeros((RHq, RWq, 3), np.float32)
    sky_sample(out, S['photo'], S['photo'].shape[1], S['photo'].shape[0], RWq, RHq, r[0], r[1], r[2], u[0], u[1], u[2],
               f[0], f[1], f[2], TX, TY, *G.ravel())
    sm = np.asarray(Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).resize((RW, RH), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    bg = (sm ** 1.6) * photo_gain
    # stars in view
    v = S['g'] @ G                                        # galactic -> this planet frame (G orthonormal)
    cz = v @ f
    sel = cz > 0.2
    vv = v[sel]; xs = (vv @ r) / (vv @ f) / TX; ys = (vv @ u) / (vv @ f) / TY
    ins = (np.abs(xs) < 1.02) & (np.abs(ys) < 1.02)
    X = (xs[ins] + 1) / 2 * RW; Y = (1 - ys[ins]) / 2 * RH
    br = S['br'][sel][ins] * star_gain; col = S['col'][sel][ins]
    # wide views show more stars per pixel than the 34° shots: keep the density similar by dimming the faint ones
    bg = bg.astype(np.float32)
    splat(bg, mask, X, Y, br, col[:, 0], col[:, 1], col[:, 2], 0.6)
    if TY < 0.1:
        v = S['dg'] @ G.astype(np.float32); cz = v @ f.astype(np.float32)
        sel = cz > 0.9
        vv = v[sel]; xs = (vv @ r) / (vv @ f) / TX; ys = (vv @ u) / (vv @ f) / TY
        ins = (np.abs(xs) < 1.02) & (np.abs(ys) < 1.02)
        X = (xs[ins] + 1) / 2 * RW; Y = (1 - ys[ins]) / 2 * RH
        dcol = S['dcol'][sel][ins]
        splat(bg, mask, X, Y, S['dbr'][sel][ins] * star_gain * 3.0, dcol[:, 0], dcol[:, 1], dcol[:, 2], 1.1)
    return bg

def finish(img, bloom=1.0, vignette=0.25, warm=None):
    # bloom in floating point (no banding): the bright parts blurred at a quarter of the size, three radii
    from scipy.ndimage import gaussian_filter
    hi = np.clip(img - 0.85, 0, 40.0)
    q = 4
    sm = hi.reshape(RH // q, q, RW // q, q, 3).mean((1, 3))
    big = np.zeros((RH // q, RW // q, 3), np.float32)
    for rr, w in ((1.5, 0.45), (6, 0.30), (18, 0.20)):
        big += np.stack([gaussian_filter(sm[..., c], rr) for c in range(3)], -1).astype(np.float32) * w
    up_ = np.stack([np.asarray(Image.fromarray(big[..., c]).resize((RW, RH), Image.BILINEAR), np.float32) for c in range(3)], -1)
    img = img + up_ * bloom
    yy, xx = np.mgrid[0:RH, 0:RW].astype(np.float32)
    v = 1 - vignette * (((xx / RW - 0.5) * 1.6) ** 2 + ((yy / RH - 0.55) * 1.2) ** 2)
    img = img * v[..., None]
    out = (ST.tonemap(img) * 255).astype(np.uint8)
    pic = Image.fromarray(out).resize((W, H), Image.LANCZOS)
    g = np.random.default_rng().normal(0, 2.0, (H, W, 1))
    return Image.fromarray(np.clip(np.asarray(pic, np.float32) + g, 0, 255).astype(np.uint8))

def neighbours(t_days, rel0, names=('f', 'g')):
    """positions of the neighbour planets in the planet frame at time t (days), from their angles rel0 (deg) ahead
    of e on the shared orbital plane; returns rows cx,cy,cz,rad, light dir, seed"""
    S = np.array([PL.A_E, 0.0, 0.0])
    rows = []
    for k, nm in enumerate(names):
        rad, a, Pd = PL.PLANETS[nm]
        a *= PL.AU_KM / PL.UNIT
        rel = math.radians(rel0[nm]) + 2 * math.pi * t_days * (1 / Pd - 1 / PL.PLANETS['e'][2])
        pos = S + a * np.array([-math.cos(rel), math.sin(rel), 0.0])
        Ld = S - pos; Ld /= np.linalg.norm(Ld)
        rows.append([*pos, rad, *Ld, 40.0 + 50 * k])
    return np.array(rows, np.float64).reshape(-1, 8)

def star_visible(cam_pos):
    """the part of the star's disc not hidden behind the planet (for its glare)"""
    o = np.asarray(cam_pos, float); S = np.array([PL.A_E, 0.0, 0.0])
    dp, ds = np.linalg.norm(o), np.linalg.norm(S - o)
    if dp < ds and True:
        rp, rs = math.asin(min(1.0, 1.0 / dp)), math.asin(min(1.0, PL.R_STAR / ds))
        sep = math.acos(min(1.0, max(-1.0, float((-o / dp) @ ((S - o) / ds)))))
        if sep >= rp + rs: return 1.0
        if sep <= rp - rs: return 0.0
        d, r1, r2 = sep, rp, rs                                   # overlap of two discs (small angles)
        a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
        a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
        a3 = 0.5 * math.sqrt(max(0.0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)))
        return max(0.0, 1.0 - (a1 + a2 - a3) / (math.pi * r2 * r2))
    return 1.0

def frame3d(cam_pos, target, fovy=34.0, up=(0, 0, 1), vk=0.0, vegcol=(0.05, 0.20, 0.04), nb=None, star=True,
            star_int=60.0, haze=1.0, planet_on=True, bloom=1.0, star_gain=1.0, photo_gain=0.38, roll=0.0, sky_turn=0.0,
            raw=False):
    TY = math.tan(math.radians(fovy) / 2); TX = TY * RW / RH
    r, u, f = cam_basis(cam_pos, target, up)
    if roll:
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        r, u = r * cr + u * sr, -r * sr + u * cr
    img = np.zeros((RH, RW, 3), np.float32); mask = np.zeros((RH, RW), np.float32)
    NB = nb if nb is not None else np.zeros((0, 8))
    render_scene(img, mask, RW, RH, *cam_pos, *r, *u, *f, TX, TY, pack(), PL.TW, PL.TH, vk, *vegcol, *STARC,
                 PL.A_E, 0.0, 0.0, PL.R_STAR, star_int if star else 0.0, NB, PERM, haze, planet_on,
                 star_visible(cam_pos) if planet_on else 1.0)
    bg = background(r, u, f, TX, TY, mask, star_gain, photo_gain, GAL @ rotz(sky_turn))
    img = img + bg * (1 - mask[..., None])
    if raw: return img
    return finish(img, bloom)

def project(cam_pos, target, fovy, p, up=(0, 0, 1)):
    TY = math.tan(math.radians(fovy) / 2); TX = TY * RW / RH
    r, u, f = cam_basis(cam_pos, target, up)
    v = np.asarray(p, float) - np.asarray(cam_pos, float)
    return ((v @ r) / (v @ f) / TX + 1) / 2 * W, (1 - (v @ u) / (v @ f) / TY) / 2 * H

if __name__ == '__main__' and sys.argv[1:] == ['prep']:
    prep()
