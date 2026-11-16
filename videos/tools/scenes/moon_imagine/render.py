# «А ти уявляєш Місяць так?» — every frame (1080x1920, 30 fps). Maps: NASA CGI Moon Kit (SVS 4720): LRO LROC WAC colour
# (16k) and LOLA elevation (64 px/deg) -> work/moon_imagine/{color16k,dem64,dem16}.npy. Ray-traced with numba.
#   S1  0.0–4.6   the Moon as people picture it: a small lamp in the night sky → the camera rushes at it
#   S2  4.0–10.0  "a whole world": low flight over Copernicus at the morning terminator, then pitch up to the Earth
#   S3  9.4–33.0  the Earth–Moon gap to scale; the planets stack up one by one (named in the voice) — they don't fit
#                 (3 718 km short on average); the Moon moves out to apogee — now they fit
#   S4  32.6–36.2 tidal locking: the Moon goes round the Earth always showing the same face (top view)
#   S5  35.6–45.4 the camera orbits round to the far side: no seas, all craters; fully sunlit
#   S6  45.0–51.4 the Moon drifts away 3.8 cm a year: a laser from Earth to the Apollo reflectors
#   S7  51.0–56.6 eclipses: a total eclipse now → in the far future the Moon is too small: an annular ring
#   S8  56.2–65.0 the full near side, slowly turning (libration); the end card from 61.2
#   python3 render.py [workers] [frame …]
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw
from multiprocessing import Pool
import numba as nb

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(TOOLS, 'scenes', 'real_motion')]
import render as R
from render import sm, lerp, nrm, stars_bg
WORK = os.path.join(TOOLS, 'work', 'moon_imagine'); OUT = os.path.join(WORK, 'frames')
W, H, FPS = 1080, 1920, 30
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']
RM = 1737.4                                   # km

_M = {}
def maps():
    if not _M:
        _M['col'] = np.load(os.path.join(WORK, 'color16k.npy'), mmap_mode='r')
        _M['d64'] = np.load(os.path.join(WORK, 'dem64m.npy'), mmap_mode='r')     # int16 metres
        _M['d16'] = np.load(os.path.join(WORK, 'dem16.npy'), mmap_mode='r')
    return _M

def ll(lat, lon):
    a, b = math.radians(lat), math.radians(lon)
    return np.array([math.cos(a) * math.cos(b), math.cos(a) * math.sin(b), math.sin(a)])

# ---------------------------------------------------------------- numba kernels
@nb.njit(inline='always')
def bil(img, u, v):
    """bilinear on an H x W float/uint array; u (0..1 wraps), v (0..1)"""
    h, w = img.shape[0], img.shape[1]
    x = (u % 1.0) * w - 0.5; y = min(max(v * h - 0.5, 0.0), h - 1.001)
    x0 = int(math.floor(x)); y0 = int(y); fx = x - x0; fy = y - y0
    x0 = x0 % w; x1 = (x0 + 1) % w; y1 = min(y0 + 1, h - 1)
    a = float(img[y0, x0]); b = float(img[y0, x1]); c = float(img[y1, x0]); d = float(img[y1, x1])
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

@nb.njit(inline='always')
def bil3(img, u, v, k):
    h, w = img.shape[0], img.shape[1]
    x = (u % 1.0) * w - 0.5; y = min(max(v * h - 0.5, 0.0), h - 1.001)
    x0 = int(math.floor(x)); y0 = int(y); fx = x - x0; fy = y - y0
    x0 = x0 % w; x1 = (x0 + 1) % w; y1 = min(y0 + 1, h - 1)
    a = float(img[y0, x0, k]); b = float(img[y0, x1, k]); c = float(img[y1, x0, k]); d = float(img[y1, x1, k])
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

@nb.njit(inline='always')
def hsh(x, y):
    s = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return s - math.floor(s)

@nb.njit(inline='always')
def vnoise(x, y):
    xi = math.floor(x); yi = math.floor(y); fx = x - xi; fy = y - yi
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = hsh(xi, yi); b = hsh(xi + 1, yi); c = hsh(xi, yi + 1); d = hsh(xi + 1, yi + 1)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

@nb.njit(parallel=True)
def k_globe(out, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, Rs, cx, cy, cz, rot, sun, col, dem, exag, earthlit, step):
    """a textured, relief-shaded Moon (sphere radius Rs at (cx,cy,cz), moon-fixed frame rot: world = rot @ body).
    out: H x W x 3 (added where hit); returns nothing. step: shading normal finite-difference in map texels"""
    Hh, Ww = out.shape[0], out.shape[1]
    dh, dw = dem.shape[0], dem.shape[1]
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            px = ox - cx; py = oy - cy; pz = oz - cz
            b = dx * px + dy * py + dz * pz; c = px * px + py * py + pz * pz - Rs * Rs
            disc = b * b - c
            if disc <= 0: continue
            t = -b - math.sqrt(disc)
            if t <= 0: continue
            # world normal and point
            nx = (px + t * dx) / Rs; ny = (py + t * dy) / Rs; nz = (pz + t * dz) / Rs
            # body coordinates (rot^T @ n)
            bx = rot[0, 0] * nx + rot[1, 0] * ny + rot[2, 0] * nz
            by = rot[0, 1] * nx + rot[1, 1] * ny + rot[2, 1] * nz
            bz = rot[0, 2] * nx + rot[1, 2] * ny + rot[2, 2] * nz
            lat = math.asin(min(1.0, max(-1.0, bz))); lon = math.atan2(by, bx)
            u = (lon + math.pi) / (2 * math.pi); v = (math.pi / 2 - lat) / math.pi
            # relief normal from the elevation map (central differences, km per radian)
            du = step / dw; dv = step / dh
            hE = bil(dem, u + du, v); hW = bil(dem, u - du, v); hN = bil(dem, u, v - dv); hS = bil(dem, u, v + dv)
            cl = max(math.cos(lat), 0.05)
            gx = (hE - hW) * exag / (2 * du * 2 * math.pi * 1737.4 * cl)     # slope east
            gy = (hN - hS) * exag / (2 * dv * math.pi * 1737.4)               # slope north
            # local east / north in body frame
            ex = -math.sin(lon); ey = math.cos(lon); ez = 0.0
            nnx = -math.sin(lat) * math.cos(lon); nny = -math.sin(lat) * math.sin(lon); nnz = math.cos(lat)
            qx = bx - gx * ex - gy * nnx; qy = by - gx * ey - gy * nny; qz = bz - gx * ez - gy * nnz
            qn = math.sqrt(qx * qx + qy * qy + qz * qz); qx /= qn; qy /= qn; qz /= qn
            # back to world
            wx = rot[0, 0] * qx + rot[0, 1] * qy + rot[0, 2] * qz
            wy = rot[1, 0] * qx + rot[1, 1] * qy + rot[1, 2] * qz
            wz = rot[2, 0] * qx + rot[2, 1] * qy + rot[2, 2] * qz
            mu0 = wx * sun[0] + wy * sun[1] + wz * sun[2]
            mus = nx * sun[0] + ny * sun[1] + nz * sun[2]
            mu = -(nx * dx + ny * dy + nz * dz)
            al_r = bil3(col, u, v, 0) / 255.0; al_g = bil3(col, u, v, 1) / 255.0; al_b = bil3(col, u, v, 2) / 255.0
            # Lommel–Seeliger (the flat full Moon) blended with Lambert (relief at low Sun); a soft terminator
            ls = 0.0
            if mu0 > 0 and mu > 0: ls = 2 * mu0 / (mu0 + mu)
            lam = max(mu0, 0.0)
            sh = (0.55 * ls + 0.75 * lam) * min(1.0, max(0.0, (mus + 0.02) / 0.06))
            e = earthlit * max(0.0, mu) * 0.02
            out[j, i, 0] = al_r * (sh * 1.0 + e)
            out[j, i, 1] = al_g * (sh * 0.985 + e)
            out[j, i, 2] = al_b * (sh * 0.96 + e * 1.1)

@nb.njit(parallel=True)
def k_terrain(out, depth, ox, oy, oz, fx, fy, fz, rx, ry, rz, ux, uy, uz, k, sun, col, dem, exag, tmax):
    """height-field ray march over the Moon (centre at origin, radius 1737.4 km + LOLA heights * exag);
    shadows by a second march towards the Sun; a fine noise adds small craters/roughness below the map's 0.5 km"""
    Hh, Ww = out.shape[0], out.shape[1]
    dh, dw = dem.shape[0], dem.shape[1]
    Rb = 1737.4
    for j in nb.prange(Hh):
        for i in range(Ww):
            X = (i + 0.5 - Ww / 2) / k; Y = -(j + 0.5 - Hh / 2) / k
            dx = fx + X * rx + Y * ux; dy = fy + X * ry + Y * uy; dz = fz + X * rz + Y * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            t = 0.0; hit = False
            px = ox; py = oy; pz = oz
            prev_gap = 1e9
            for s in range(700):
                px = ox + dx * t; py = oy + dy * t; pz = oz + dz * t
                r = math.sqrt(px * px + py * py + pz * pz)
                lat = math.asin(pz / r); lon = math.atan2(py, px)
                u = (lon + math.pi) / (2 * math.pi); v = (math.pi / 2 - lat) / math.pi
                hs = Rb + bil(dem, u, v) * exag
                gap = r - hs
                if gap < 0:
                    # refine between the last two steps
                    hit = True
                    break
                if t > tmax: break
                st = max(0.02 + t * 0.0009, gap * 0.45)
                t += st
                prev_gap = gap
            if not hit:
                continue
            # binary refine
            ta = t - max(0.02 + t * 0.0009, prev_gap * 0.45); tb = t
            for q in range(8):
                tm = 0.5 * (ta + tb)
                px = ox + dx * tm; py = oy + dy * tm; pz = oz + dz * tm
                r = math.sqrt(px * px + py * py + pz * pz)
                lat = math.asin(pz / r); lon = math.atan2(py, px)
                u = (lon + math.pi) / (2 * math.pi); v = (math.pi / 2 - lat) / math.pi
                if r - (Rb + bil(dem, u, v) * exag) < 0: tb = tm
                else: ta = tm
            t = tb
            px = ox + dx * t; py = oy + dy * t; pz = oz + dz * t
            r = math.sqrt(px * px + py * py + pz * pz)
            lat = math.asin(pz / r); lon = math.atan2(py, px)
            u = (lon + math.pi) / (2 * math.pi); v = (math.pi / 2 - lat) / math.pi
            # normal from the map (1 texel)
            du = 1.0 / dw; dv = 1.0 / dh; cl = max(math.cos(lat), 0.05)
            hE = bil(dem, u + du, v); hW = bil(dem, u - du, v); hN = bil(dem, u, v - dv); hS = bil(dem, u, v + dv)
            # fine detail: noise in km over a 0.25–2 km scale
            xk = lon * Rb * cl; yk = lat * Rb
            nd = 0.0; amp = 0.06; fr = 1.0
            for o in range(4):
                nd += (vnoise(xk * fr, yk * fr) - 0.5) * amp; amp *= 0.5; fr *= 2.1
            e1 = 0.004
            ndx = 0.0; ndy = 0.0; amp = 0.06; fr = 1.0
            for o in range(4):
                ndx += (vnoise((xk + e1) * fr, yk * fr) - vnoise((xk - e1) * fr, yk * fr)) * amp / (2 * e1);
                ndy += (vnoise(xk * fr, (yk + e1) * fr) - vnoise(xk * fr, (yk - e1) * fr)) * amp / (2 * e1)
                amp *= 0.5; fr *= 2.1
            gx = (hE - hW) * exag / (2 * du * 2 * math.pi * Rb * cl) + ndx * 0.35
            gy = (hN - hS) * exag / (2 * dv * math.pi * Rb) + ndy * 0.35
            bx = px / r; by = py / r; bz = pz / r
            ex = -math.sin(lon); ey = math.cos(lon)
            nnx = -math.sin(lat) * math.cos(lon); nny = -math.sin(lat) * math.sin(lon); nnz = math.cos(lat)
            qx = bx - gx * ex - gy * nnx; qy = by - gx * ey - gy * nny; qz = bz - gy * nnz
            qn = math.sqrt(qx * qx + qy * qy + qz * qz); qx /= qn; qy /= qn; qz /= qn
            mu0 = qx * sun[0] + qy * sun[1] + qz * sun[2]
            # shadow: march towards the Sun
            lit = 1.0
            if mu0 <= 0: lit = 0.0
            else:
                ts = 0.15
                for s2 in range(90):
                    sx = px + sun[0] * ts; sy = py + sun[1] * ts; sz = pz + sun[2] * ts
                    rr = math.sqrt(sx * sx + sy * sy + sz * sz)
                    if rr > Rb + 12: break
                    la2 = math.asin(sz / rr); lo2 = math.atan2(sy, sx)
                    h2 = Rb + bil(dem, (lo2 + math.pi) / (2 * math.pi), (math.pi / 2 - la2) / math.pi) * exag
                    gap2 = rr - h2
                    if gap2 < 0:
                        lit = 0.0; break
                    lit = min(lit, max(0.0, gap2 / (0.012 * ts + 0.02)))      # soft penumbra
                    ts += max(0.12, gap2 * 0.5)
            mu = -(qx * dx + qy * dy + qz * dz)
            ls = 0.0
            if mu0 > 0 and mu > 0: ls = 2 * mu0 / (mu0 + max(mu, 0.05))
            sh = (0.45 * ls + 0.85 * max(mu0, 0.0)) * lit
            alr = bil3(col, u, v, 0) / 255.0; alg = bil3(col, u, v, 1) / 255.0; alb = bil3(col, u, v, 2) / 255.0
            dark = 0.92 + 0.16 * (vnoise(xk * 3.1, yk * 3.1) - 0.5)
            # a whisper of earthshine in the shadows (the Earth is up there)
            amb = 0.010
            out[j, i, 0] = alr * dark * (sh + amb)
            out[j, i, 1] = alg * dark * (sh * 0.985 + amb)
            out[j, i, 2] = alb * dark * (sh * 0.96 + amb * 1.15)
            depth[j, i] = t

# ---------------------------------------------------------------- helpers
def axes(p, g, up):
    f = nrm(np.asarray(g, float) - p); r = nrm(np.cross(f, up)); u = np.cross(r, f)
    return f, r, u

def moon_globe(img, p, g, up, fov, center, Rs, rot, sun, exag=2.0, step=1.5, gain=1.0):
    f, r, u = axes(p, g, up)
    k = (H / 2) / math.tan(math.radians(fov) / 2)
    buf = np.zeros((H, W, 3), np.float32)
    M = maps()
    k_globe(buf, p[0], p[1], p[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, Rs, center[0], center[1], center[2],
            np.ascontiguousarray(rot), np.asarray(sun, np.float64), M['col'], M['d16'], exag, 0.0, step)
    hit = buf.sum(-1) > 0
    img[hit] = buf[hit] * gain
    return k

def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])

def bloom(img, thr=1.0, k=0.6):
    from scipy.ndimage import gaussian_filter
    b = np.clip(img - thr, 0, 10).astype(np.float32)
    if b.max() <= 0: return img
    s = b.reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3))
    acc = gaussian_filter(s, (2, 2, 0)) * 0.7 + gaussian_filter(s, (8, 8, 0)) * 0.5 + gaussian_filter(s, (24, 24, 0)) * 0.3
    return img + np.repeat(np.repeat(acc, 4, 0), 4, 1) * k

def tonemap(x, expo=1.0):
    y = 1 - np.exp(-np.maximum(x, 0) * 1.25 * expo)
    return np.clip(y, 0, 1) ** (1 / 1.9)

def stars(t, dx=0.0, dy=0.0, k=0.55):
    return stars_bg(dx=dx, dy=dy, k=0.6) ** 1.6 * k

def earth_sprite(img, cx, cy, rpx, view_dir, light, up=(0, 0, 1)):
    """the Earth (textured globe from the site) seen along view_dir (towards the Earth), lit by `light`"""
    b = -nrm(view_dir); r = nrm(np.cross(up, b)) if abs(np.dot(up, b)) < 0.99 else nrm(np.cross([1, 0, 0], b)); u = np.cross(b, r)
    spr = R.globe('earth', max(rpx, 0.8), r, u, b, nrm(light))
    R.over(img, spr, cx, cy)
    # a thin blue halo
    if rpx > 6:
        s = int(rpx * 2.6 + 6); yy, xx = np.mgrid[0:s, 0:s] - s / 2 + 0.5
        d = np.sqrt(xx * xx + yy * yy) / rpx
        halo = np.exp(-((d - 1.0) / 0.035) ** 2) * (d > 0.97) * 0.35
        R.add(img, halo[..., None] * np.array([0.35, 0.6, 1.0]), cx, cy)

# ---------------------------------------------------------------- the scene geometry (moon-centred, km)
# Sun for the morning terminator over Copernicus (9.62 N, 20.08 W): the Sun ~6° above the eastern horizon
COPER = ll(9.62, -20.08)
SUN_T = nrm(ll(1.5, -20.08 + 84.0))
EARTH_DIR = nrm(ll(0.0, 0.0))                       # the sub-Earth point (no libration)

# ---------------------------------------------------------------- S1: a lamp in the sky → rushing in
def shot_S1(t):
    # the Moon as seen from Earth (a near-full disc, slightly gibbous) — tiny at first, then the camera rushes at it
    img = stars(t, dx=t * 4, dy=-t * 2, k=0.5)
    k0 = sm((t - 1.6) / 3.0)
    # distance from 380 000 km (a small lamp) to ~3 000 km
    dist = math.exp(lerp(math.log(380000.0), math.log(2600.0), k0 ** 1.4))
    fov = lerp(9.0, 52.0, sm((t - 2.0) / 2.6))       # starts "telephoto" so the lamp is visible but small
    view = nrm(ll(5, -15))                          # looking at the near side, a bit north-west of centre
    p = view * dist
    g = np.zeros(3); up = np.array([0, 0, 1.0])
    sun = nrm(ll(0, 55))                            # waxing gibbous, the terminator on the western limb
    moon_globe(img, p, g, up, fov, np.zeros(3), RM, np.eye(3), sun, exag=2.0, step=1.0 if dist < 20000 else 2.0, gain=1.15)
    return img

# ---------------------------------------------------------------- S2: the flight over Copernicus
def terrain_cam(t):
    # from the east towards Copernicus at ~20 km, the crater ahead; at the end pitch up to the Earth high in the sky
    k = (t - 4.0) / 6.0
    lat = lerp(9.3, 9.55, k); lon = lerp(-16.4, -18.3, k)
    alt = lerp(20.0, 30.0, sm((k - 0.5) / 0.5))
    P = ll(lat, lon) * (RM + alt)
    fwd_ground = nrm(ll(9.62, -20.08) * RM - ll(lat, lon) * RM)
    upv = nrm(P)
    fwd_ground = nrm(fwd_ground - upv * float(fwd_ground @ upv))
    pitch = lerp(-0.20, -0.16, k) + 1.25 * sm((k - 0.66) / 0.34)
    look = nrm(fwd_ground * math.cos(pitch) + upv * math.sin(pitch))
    return P, P + look * 100, upv, lerp(56.0, 24.0, sm((k - 0.7) / 0.3))

def shot_S2(t):
    p, g, up, fov = terrain_cam(t)
    f, r, u = axes(p, g, up)
    k = (H / 2) / math.tan(math.radians(fov) / 2)
    img = stars(t, dx=-t * 10, dy=t * 12, k=0.45)
    buf = np.zeros((H, W, 3), np.float32); depth = np.zeros((H, W), np.float32)
    M = maps()
    k_terrain(buf, depth, p[0], p[1], p[2], f[0], f[1], f[2], r[0], r[1], r[2], u[0], u[1], u[2], k, np.asarray(SUN_T, np.float64),
              M['col'], M['d64'], 0.001, 900.0)
    hit = depth > 0
    img[hit] = (buf[hit] * 0.95) ** 1.18
    # the Earth high in the black sky (where it really is seen from Copernicus), a crescent-gibbous lit by the same Sun
    cam = R.Cam(p, g, fov=fov, up=up)
    E = EARTH_DIR * 384400.0
    x, y, z = cam.proj(E)
    if z[0] > 0:
        rpx = cam.k * 6371.0 / z[0]
        earth_sprite(img, float(x[0]), float(y[0]), rpx, E - p, SUN_T, up=up)
    return img

def draw_globe(img, name, rp, x, y, cr, cu, cb, light, spin=0.0, ring=False):
    """a globe sprite, skipped when off screen; big ones rendered at <= 700 px radius and scaled up (memory)"""
    ext = rp * (2.35 if ring else 1.1)
    if y + ext < 0 or y - ext > H or x + ext < 0 or x - ext > W or rp < 0.4: return
    cap = 700.0
    if rp <= cap:
        R.over(img, R.globe(name, rp, cr, cu, cb, light, spin=spin, ring=ring), x, y); return
    spr = R.globe(name, cap, cr, cu, cb, light, spin=spin, ring=ring)
    f = rp / cap; w0, h0 = spr.size
    # crop to what is on screen before scaling
    left = max(0, (x - w0 * f / 2) ); top = max(0, (y - h0 * f / 2))
    sx0 = max(0.0, (0 - (x - w0 * f / 2)) / f); sy0 = max(0.0, (0 - (y - h0 * f / 2)) / f)
    sx1 = min(w0, (W - (x - w0 * f / 2)) / f); sy1 = min(h0, (H - (y - h0 * f / 2)) / f)
    if sx1 <= sx0 or sy1 <= sy0: return
    ow, oh = int(round((sx1 - sx0) * f)), int(round((sy1 - sy0) * f))
    if ow < 1 or oh < 1: return
    part = spr.resize((ow, oh), Image.BICUBIC, box=(sx0, sy0, sx1, sy1))
    R.over(img, part, left + ow / 2, top + oh / 2)

# ---------------------------------------------------------------- S3: the gap to scale, the planets
PLAN = [('mercury', 4879.4), ('venus', 12103.6), ('mars', 6779.0), ('jupiter', 139820.0), ('saturn', 116460.0),
        ('uranus', 50724.0), ('neptune', 49244.0)]
RE = 6371.0
GAP_MEAN = 384400.0 - RE - RM        # 376 291.6 km
GAP_APO = 406700.0 - RE - RM         # 398 591.6 km
SUMD = sum(d for _, d in PLAN)       # 380 010.4 km
# when each planet arrives (the names in the voice; voice offset 0.25 s)
ARRIVE = [15.06, 16.35, 17.27, 18.34, 19.28, 19.85, 20.59]

def gap_now(t):
    return lerp(GAP_MEAN, GAP_APO, sm((t - 27.3) / 3.0))

def s3_view(t):
    """(centre in km above Earth's surface, km per px)"""
    # 9.4–14.9: pull out from the Moon down to the whole system; 14.9–21: follow the stack up; 21–26: look at the
    # overshoot at the Moon; 26–33: the whole system again
    tot = GAP_MEAN + RE + RM
    whole = (GAP_MEAN / 2, (tot + 60000) / (H * 0.92))
    if t < 14.9:
        k = sm((t - 9.6) / 4.6)
        c = lerp(GAP_MEAN + RM, whole[0], k); s = math.exp(lerp(math.log(60.0), math.log(whole[1]), k))
        return c, s
    if t < 21.0:
        # the stack's top, a little below the frame centre
        top = stack_top(t)
        k = sm((t - 14.9) / 1.0)
        c = lerp(whole[0], max(top - 60000, 30000), k * 0.0 + 0.0) if False else whole[0]
        return whole
    if t < 26.4:
        k = sm((t - 21.2) / 1.4) * (1 - sm((t - 25.4) / 1.0))
        c = lerp(whole[0], GAP_MEAN - 2000, k); s = math.exp(lerp(math.log(whole[1]), math.log(32.0), k))
        return c, s
    return whole

def stack_top(t):
    h = 0.0
    for (n, d), ta in zip(PLAN, ARRIVE):
        h += d * sm((t - ta) / 0.55)
    return h

def shot_S3(t):
    img = stars(t, dx=t * 2, dy=-t * 1.5, k=0.45)
    c, s = s3_view(t)
    def y_of(hkm): return H / 2 - (hkm - c) / s
    gap = gap_now(t)
    light = nrm(np.array([1.0, 0.3, 0.35]))            # from the right
    cam_r, cam_u, cam_b = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
    # the Earth (its top at height 0) and the Moon (its bottom at the gap)
    cx = W / 2
    ye = y_of(-RE); re_px = RE / s
    draw_globe(img, 'earth', re_px, cx, ye, cam_r, cam_u, cam_b, light, spin=2.2)
    # the planets, stacked from the Earth's surface up (each slides in from the side)
    h = 0.0
    for (n, d), ta in zip(PLAN, ARRIVE):
        a = sm((t - ta) / 0.55)
        if a <= 0: break
        rp = d / 2 / s
        yc = y_of(h + d / 2)
        xc = cx + (1 - a) * (W * 0.9 if (PLAN.index((n, d)) % 2 == 0) else -W * 0.9)
        if n == 'saturn':
            Nr = nrm([math.sin(math.radians(26.7)), 0, math.cos(math.radians(26.7))]); bb = np.array([0, 1.0, 0])
            uu = nrm(Nr + 0.10 * bb); bb = nrm(bb - uu * float(bb @ uu)); rr = np.cross(uu, bb)
            draw_globe(img, n, rp, xc, yc, rr, uu, bb, nrm(rr * 0.8 + bb * 0.5 + uu * 0.2), ring=True)
        else:
            draw_globe(img, n, rp, xc, yc, cam_r, cam_u, cam_b, light)
        h += d * a
    ym = y_of(gap + RM); rm_px = RM / s
    draw_globe(img, 'moon', max(rm_px, 3.0), cx, ym, cam_r, cam_u, cam_b, light, spin=-1.6)
    # the overshoot: a red mark where the stack runs into the Moon (only while the gap is the mean one)
    ov = SUMD - gap
    if t > 21.4 and ov > 0:
        al = sm((t - 21.4) / 0.4)
        y0 = y_of(gap); y1 = y_of(SUMD)
        d = ImageDraw.Draw(Image.new('L', (1, 1)))
        R.lines(img, [([(cx - 260, y0), (cx + 260, y0)], al), ([(cx - 260, y1), (cx + 260, y1)], al)], (1.0, 0.25, 0.2), width=3, k=1.2)
    return img

def labels_S3(t, im):
    c, s = s3_view(t)
    def y_of(hkm): return H / 2 - (hkm - c) / s
    names = {'mercury': 'Меркурій', 'venus': 'Венера', 'mars': 'Марс', 'jupiter': 'Юпітер', 'saturn': 'Сатурн', 'uranus': 'Уран', 'neptune': 'Нептун'}
    h = 0.0
    for idx, ((n, d), ta) in enumerate(zip(PLAN, ARRIVE)):
        a = sm((t - ta) / 0.55)
        if a <= 0: break
        al = a * (1 - sm((t - 21.0) / 0.5)) * (1 - sm((t - 9.0) / 0.1) * 0)
        yc = y_of(h + d / 2); rp = d / 2 / s
        side = 1 if idx % 2 == 0 else -1
        x = W / 2 + side * (max(rp, 8) + 30)
        R.label(im, x, yc, names[n], size=34, a=al, anchor='lm' if side > 0 else 'rm')
        h += d * a
    if 21.6 < t < 26.4:
        a = sm((t - 21.8) / 0.4) * (1 - sm((t - 26.0) / 0.4))
        R.label(im, W / 2 + 300, (y_of(gap_now(t)) + y_of(SUMD)) / 2, 'не вистачає\n3 718 км', size=34, fill=(255, 120, 110), a=a, anchor='lm')
    if t > 30.0:
        a = sm((t - 30.2) / 0.5) * (1 - sm((t - 32.6) / 0.4))
        R.label(im, W / 2 + 40, y_of(gap_now(t) + RM), 'Місяць найдалі: усі вміщаються', size=32, fill=(150, 255, 170), a=a, anchor='lm')
        R.label(im, W / 2 + 40, y_of(-RE * 0.2), 'Земля', size=34, a=a, anchor='lm')
    if t > 9.8 and t < 14.9:
        a = sm((t - 10.4) / 0.5) * (1 - sm((t - 14.4) / 0.4))
        R.label(im, W / 2 + 40, y_of(-RE * 0.2), 'Земля', size=36, a=a, anchor='lm')
        R.label(im, W / 2 + 40, y_of(gap_now(t) + RM), 'Місяць', size=36, a=a, anchor='lm')

# ---------------------------------------------------------------- S4: tidal locking (top view)
def shot_S4(t):
    img = stars(t, dx=t * 3, k=0.45)
    # the camera above the Earth's north pole; the Moon at 1/8 of the real distance (labelled), its face to the Earth
    ang = (t - 32.6) * 0.9 + 0.6
    D = 30000.0
    Mc = np.array([math.cos(ang), math.sin(ang), 0.0]) * D
    p = np.array([0.0, -9000.0, 125000.0]); g = np.array([0.0, 2000.0, 0.0]); up = np.array([0, 1.0, 0])
    sun = nrm(np.array([1.0, -0.6, 0.15]))
    # the Moon's body frame: its x axis (the near-side centre) always points at the Earth
    xb = -nrm(Mc); zb = np.array([0, 0, 1.0]); yb = np.cross(zb, xb)
    rot = np.stack([xb, yb, zb], 1)
    fov = 34.0
    moon_globe(img, p, g, up, fov, Mc, RM * 2.4, rot, sun, exag=2.0, step=2.0, gain=1.2)
    cam = R.Cam(p, g, fov=fov, up=up)
    x, y, z = cam.proj(np.zeros(3)); rpx = cam.k * RE * 1.0 / z[0]
    earth_sprite(img, float(x[0]), float(y[0]), rpx, -p, sun, up=(0, 1.0, 0))
    # the orbit, faint
    a = np.linspace(0, 2 * np.pi, 200)
    pts = np.stack([np.cos(a) * D, np.sin(a) * D, np.zeros_like(a)], 1)
    xx, yy, zz = cam.proj(pts)
    R.lines(img, [([(xx[i], yy[i]) for i in range(len(a))], 0.25)], (0.7, 0.8, 1.0), width=1)
    return img

# ---------------------------------------------------------------- S5: round to the far side
def shot_S5(t):
    img = stars(t, dx=-t * 6, dy=t * 1, k=0.5)
    k = sm((t - 35.6) / 9.8)
    # the camera swings from over the near side (lon 0) to the far side (lon 180) at ~2.6 Moon radii
    lon = lerp(-10.0, 175.0, k); lat = lerp(8.0, 14.0, k)
    dist = RM * lerp(3.0, 2.25, sm((t - 37) / 6))
    p = ll(lat, lon) * dist
    # the Sun behind the camera, a little to the side: everything we look at is lit (the far side is not dark)
    sun = nrm(ll(lat + 10, lon + 25))
    moon_globe(img, p, np.zeros(3), np.array([0, 0, 1.0]), 46.0, np.zeros(3), RM, np.eye(3), sun, exag=2.2, step=1.0, gain=1.15)
    return img

# ---------------------------------------------------------------- S6: drifting away, the laser
def shot_S6(t):
    img = stars(t, dx=t * 4, dy=0, k=0.45)
    k = sm((t - 45.0) / 6.4)
    # Earth lower left, the Moon upper right (distance compressed, labelled); the Moon creeps away
    ex, ey, er = 300, 1500, 170
    mx = lerp(760, 820, k); my = lerp(560, 470, k); mr = 46
    sun = nrm(np.array([1.0, 0.25, 0.5]))
    R.over(img, R.globe('earth', er, np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), np.array([0, -1.0, 0]), nrm(np.array([0.9, -0.3, 0.4])), spin=0.9), ex, ey)
    R.over(img, R.globe('moon', mr, np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), np.array([0, -1.0, 0]), nrm(np.array([0.9, -0.3, 0.4])), spin=-1.5), mx, my)
    # the laser pulses (green, 532 nm, as at the Apache Point observatory), out and back
    sx, sy = ex + er * 0.55, ey - er * 0.84
    for q in range(3):
        ph = ((t - 45.6) * 0.55 + q / 3) % 1.0
        if t < 45.6: continue
        a0 = ph; a1 = max(0, ph - 0.08)
        pts = [(lerp(sx, mx, a1), lerp(sy, my, a1)), (lerp(sx, mx, a0), lerp(sy, my, a0))]
        R.lines(img, [(pts, 0.9)], (0.35, 1.0, 0.45), width=3, k=1.6)
    R.lines(img, [([(sx, sy), (mx, my)], 0.12)], (0.35, 1.0, 0.45), width=1, k=1.0)
    return img

# ---------------------------------------------------------------- S7: eclipses
def disc(rpx, soft=1.2):
    s = int(rpx * 2 + 8); yy, xx = np.mgrid[0:s, 0:s] - s / 2 + 0.5
    return np.clip((rpx - np.sqrt(xx * xx + yy * yy)) / soft + 0.5, 0, 1)

def corona(rs, t, k=1.0):
    s = int(rs * 9); yy, xx = np.mgrid[0:s, 0:s] - s / 2 + 0.5
    rr = np.sqrt(xx * xx + yy * yy) / rs; ang = np.arctan2(yy, xx)
    streams = 0.55 + 0.45 * (0.5 + 0.5 * np.sin(ang * 7 + 0.4)) * (0.5 + 0.5 * np.sin(ang * 13 + 1.7)) + 0.25 * np.cos(2 * ang) ** 2
    c = np.where(rr > 1, (rr ** -3.2) * streams, 0) * 1.6 + np.exp(-((rr - 1.0) / 0.03) ** 2) * (rr > 1) * 0.6
    return c[..., None] * np.array([1.0, 0.95, 0.9]) * k

def shot_S7(t):
    img = stars(t, dx=t * 2, k=0.35) * 0.6
    k = sm((t - 53.0) / 3.0)                     # now → far future (the Moon smaller in the sky)
    cx, cy = W / 2, 900
    rs = 300.0
    rmoon = rs * lerp(1.035, 0.90, k)            # now: the Moon's disc a bit bigger (total); later: smaller (annular)
    off = lerp(-420, 0, sm((t - 51.0) / 1.6))
    # the Sun: a textured disc
    sun = R.sun_sprite(rs, glow=0.0, t=t)
    R.add(img, sun * 1.6, cx, cy)
    # the corona only while the Sun is fully covered
    cover = max(0.0, 1 - abs(off) / (rs * 0.15)) * (1 - sm((k - 0.25) / 0.25))
    if cover > 0: R.add(img, corona(rs, t, 0.8 * cover), cx, cy)
    # the Moon: a black disc
    m = disc(rmoon)
    s = m.shape[0]; x0 = int(cx + off - s / 2); y0 = int(cy - s / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + s), min(H, y0 + s)
    if xa < xb and ya < yb:
        a = m[ya - y0:yb - y0, xa - x0:xb - x0, None]
        img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - a) + np.array([0.004, 0.004, 0.006]) * a
    # glare of the ring (annular) — bloom handles it
    return img

# ---------------------------------------------------------------- S8: the full near side, libration
def shot_S8(t):
    img = stars(t, dx=t * 3, dy=t, k=0.5)
    lib_lon = 6.5 * math.sin((t - 56) * 0.35); lib_lat = 5.0 * math.sin((t - 56) * 0.27 + 1)
    p = ll(lib_lat, lib_lon) * RM * 3.05
    sun = nrm(ll(1.0, lib_lon + 8))
    moon_globe(img, p, np.zeros(3), np.array([0, 0, 1.0]), 46.0 - 4 * sm((t - 56.2) / 8), np.zeros(3), RM, np.eye(3), sun, exag=2.0, step=1.2, gain=1.1)
    return img

SHOTS = [(0.0, 4.6, shot_S1), (4.0, 10.0, shot_S2), (9.4, 33.0, shot_S3), (32.6, 36.2, shot_S4), (35.6, 45.4, shot_S5),
         (45.0, 51.4, shot_S6), (51.0, 56.6, shot_S7), (56.2, 65.0, shot_S8)]

def post(img, expo=1.0):
    img = bloom(np.nan_to_num(img, nan=0.0, posinf=10.0, neginf=0.0))
    yy, xx = np.mgrid[0:H, 0:W]; vig = 1 - 0.30 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2
    return tonemap(img * vig[..., None], expo)

def frame(t):
    act = [(a, b, f) for a, b, f in SHOTS if a <= t <= b]
    out = None
    for a, b, f in act:
        im = post(f(t))
        if out is None: out = im
        else:
            prev_end = max(bb for aa, bb, ff in act if ff is not f and aa < a)
            k = sm((t - a) / max(1e-3, prev_end - a))
            out = out * (1 - k) + im * k
    if out is None: out = np.zeros((H, W, 3), np.float32)
    pil = R.to_img(out)
    if 9.4 <= t <= 33.0: labels_S3(t, pil)
    return pil

def job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return
    frame(i / FPS).save(p + '.tmp.jpg', quality=93); os.replace(p + '.tmp.jpg', p)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * FPS)
    todo = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 3) as pool:
        for c, _ in enumerate(pool.imap_unordered(job, todo, chunksize=2)):
            if c % 60 == 0: print('frame', c, '/', len(todo), flush=True)
    print('frames done', n)
