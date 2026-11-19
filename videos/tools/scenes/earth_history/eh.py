# Shared engine for «Історія Землі» (16:9, 1920×1080): cameras, the photographic Earth (sun_imagine/earthk.py) with any
# equirectangular map swapped in (paleo maps, ice, magma), textured spheres in numpy (magma Earth, Theia, the Moon),
# particles, post. All images are linear HDR float32 (H, W, 3) until finish().
import math, os, sys, functools
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, os.path.join(TOOLS, 'scenes', 'sun_imagine')); sys.path.insert(0, HERE)
import common as cm
RES = os.environ.get('EH_RES', '1920x1080')
cm.W, cm.H = (int(x) for x in RES.split('x'))
SCALE = cm.W / 1920.0
import earthk
W, H, FPS = cm.W, cm.H, 30
RE = earthk.RE
WORK = os.path.join(TOOLS, 'work', 'earth_history'); PALEO = os.path.join(WORK, 'paleo')
ACTS_DIR = os.path.join(WORK, 'acts' if os.environ.get('EH_RES', '1920x1080') == '1920x1080' else 'acts_' + os.environ['EH_RES'])
GAL = cm.rot_axis([0.3, 1.0, 0.2], 2.2)
sm, ramp, lerp, lerpv, nrm, ll = cm.sm, cm.ramp, cm.lerp, cm.lerpv, cm.nrm, cm.ll

def keys(t, ks):
    """smooth piecewise interpolation through (time, value) keys"""
    if t <= ks[0][0]: return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0))
            return lerpv(v0, v1, k) if isinstance(v0, (list, tuple, np.ndarray)) else lerp(v0, v1, k)
    return ks[-1][1]

# ---------------------------------------------------------------- maps
@functools.lru_cache(maxsize=12)
def paleo(age):
    a = np.asarray(Image.open(os.path.join(PALEO, f'ep_{age}.png')).convert('RGB')).astype(np.float32)
    shelf = (a[..., 2] > 95) & (a[..., 1] > 80) & (a[..., 0] < 70)          # the bright shallow seas: calmer, deeper blue
    a[shelf] = a[shelf] * np.array([0.75, 0.72, 0.85])
    return np.ascontiguousarray(np.clip(a, 0, 255).astype(np.uint8))

@functools.lru_cache(maxsize=1)
def today():
    return np.ascontiguousarray(np.asarray(earthk.maps()['day'][::4, ::4], np.uint8))      # 4096×2048 Blue Marble

AGES = sorted(int(f[3:-4]) for f in os.listdir(PALEO) if f.startswith('ep_')) if os.path.isdir(PALEO) else []

def paleo_at(ma):
    """the map at `ma` million years ago: a cross-fade of the two nearest painted epochs"""
    if ma <= 0: return paleo(0)
    a = max([x for x in AGES if x <= ma], default=AGES[0]); b = min([x for x in AGES if x >= ma], default=AGES[-1])
    if a == b: return paleo(a)
    k = (ma - a) / (b - a)
    return np.ascontiguousarray((paleo(a) * (1 - k) + paleo(b) * k).astype(np.uint8))

_CL = {}
def clouds_roll(shift):
    """the site's cloud map rolled east–west (so ancient skies do not repeat today's weather)"""
    key = int(shift) % 1024
    if key not in _CL:
        if len(_CL) > 6: _CL.clear()
        base = _CL.setdefault('base', np.asarray(earthk.maps()['clouds']))
        _CL[key] = np.ascontiguousarray(np.roll(base, key, axis=1))
    return _CL[key]

def globe(img, c, tex, sun, expo=0.8, cloud_k=0.5, night_k=0.0, cloud_shift=0, air_k=1.0, home=(0.0, 0.0)):
    M = earthk.maps()
    keep = (M['day'], M['clouds'])
    M['day'] = tex; M['clouds'] = clouds_roll(cloud_shift) if cloud_shift else keep[1]
    earthk.earth(img, c, sun, sun_k=18.0, disc_k=0.0, cloud_k=cloud_k, night_k=night_k, fields=0.0, home=home, expo=expo,
                 air_k=air_k)
    M['day'], M['clouds'] = keep

def orbit_cam(lat, lon, dist, fov=36.0, look=(0, 0, 0), up=(0, 0, 1), dlat=0.0, dlon=0.0):
    """camera at (lat, lon) `dist` km from the centre, looking at `look` (km) — offset by dlat/dlon degrees"""
    o = ll(lat, lon) * dist
    tgt = np.asarray(look, float) + (ll(lat + dlat, lon + dlon) * RE - ll(lat, lon) * RE if (dlat or dlon) else 0)
    return cm.cam(o, tgt, up, fov)

def side_sun(c, a=-0.75, b=0.35, d=0.45):
    """a light from the camera's left/up/front, so the globe is lit the same way whatever the camera does"""
    o, f, r, u, k = c
    return nrm(r * a + u * b - f * d)

def space(c, gain=0.6, band=0.3):
    img = np.zeros((H, W, 3), np.float32)
    cm.sky(img, c, GAL, gain, stars=1.0, band=band)
    return img

# ---------------------------------------------------------------- numpy spheres
@functools.lru_cache(maxsize=1)
def pix_grid():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return xx - W / 2, -(yy - H / 2)

def rays(c):
    o, f, r, u, k = c
    gx, gy = pix_grid()
    D = f[None, None, :] * k + r[None, None, :] * gx[..., None] + u[None, None, :] * gy[..., None]
    return D / np.linalg.norm(D, axis=-1, keepdims=True)

def hit(c, D, C, R):
    o = c[0]; oc = o - np.asarray(C, float)
    b = D @ oc; cc = oc @ oc - R * R; disc = b * b - cc
    m = disc > 0
    t = np.where(m, -b - np.sqrt(np.maximum(disc, 0)), np.inf)
    m &= t > 0
    return m, np.where(m, t, np.inf)

def sample(tex, lat, lon):
    """bilinear sample of an equirect map (H, W, C) float at lat/lon radians"""
    h, w = tex.shape[:2]
    x = ((lon + math.pi) / (2 * math.pi)) % 1.0 * w - 0.5; y = np.clip((math.pi / 2 - lat) / math.pi * h - 0.5, 0, h - 1.001)
    x0 = np.floor(x).astype(np.int64); y0 = y.astype(np.int64); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    x0 %= w; x1 = (x0 + 1) % w; y1 = np.minimum(y0 + 1, h - 1)
    return ((tex[y0, x0] * (1 - fx) + tex[y0, x1] * fx) * (1 - fy) + (tex[y1, x0] * (1 - fx) + tex[y1, x1] * fx) * fy)

def rotz(a):
    ca, sa = math.cos(a), math.sin(a); return np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1.0]])

def body(img, c, D, C, R, alb, emi=None, L=(1, 0, 0), spin=0.0, ambient=0.01, depth=None, atm=None, emi_k=1.0):
    """a textured sphere: alb/emi equirect float maps (linear); spin: rotation about z (rad); returns the hit mask/depth.
    atm: (r, g, b) colour of a thin glowing rim (hot air, dust)"""
    m, t = hit(c, D, C, R)
    if depth is not None: m &= t < depth
    if not m.any(): return m, t
    P = c[0] + D[m] * t[m][:, None]; N = (P - np.asarray(C, float)) / R
    Nb = N @ rotz(spin)                                     # into the body frame
    lat = np.arcsin(np.clip(Nb[:, 2], -1, 1)); lon = np.arctan2(Nb[:, 1], Nb[:, 0])
    a = sample(alb, lat, lon)
    dif = np.clip(N @ nrm(L), 0, 1)[:, None]
    col = a * (dif * 3.0 + ambient)
    if emi is not None: col = col + sample(emi, lat, lon) * emi_k
    if atm is not None:
        mu = np.clip(-(D[m] * N).sum(-1), 0, 1)[:, None]
        col = col + np.asarray(atm, np.float32) * (1 - mu) ** 4 * (0.3 + dif)
    img[m] = col
    return m, t

# ---------------------------------------------------------------- noise on the sphere (precomputed maps)
def _hash3(ix, iy, iz):
    n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFFFF).astype(np.float32) / 0xFFFFFF

def vnoise3(p):
    q = np.floor(p).astype(np.int64); f = (p - q).astype(np.float32); f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * _hash3(q[..., 0] + dx, q[..., 1] + dy, q[..., 2] + dz)
    return out

def fbm3(p, o=5, lac=2.03):
    a, s, t = 0.5, 1.0, 0
    for _ in range(o):
        t = t + a * vnoise3(p * s); s *= lac; a *= 0.5
    return t

def sphere_grid(w, h):
    lat = (0.5 - (np.arange(h) + 0.5) / h) * math.pi; lon = ((np.arange(w) + 0.5) / w - 0.5) * 2 * math.pi
    la, lo = np.meshgrid(lat, lon, indexing='ij')
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1).astype(np.float32)

def cached_map(name, fn):
    """a precomputed float16 map in work/earth_history/maps/<name>.npy"""
    p = os.path.join(WORK, 'maps', name + '.npy')
    if os.path.exists(p): return np.load(p).astype(np.float32)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    a = fn().astype(np.float16); np.save(p, a); return a.astype(np.float32)

def magma_maps(seed=0.0, w=4096, h=2048):
    """the magma ocean: dark cooling crust plates with glowing seams; returns (albedo, emission) linear maps"""
    def mk():
        P = sphere_grid(w, h)
        n = fbm3(P * 3.2 + seed, 6)
        seam = np.clip(1 - np.abs(fbm3(P * 6.0 + 3.0 + seed, 5) - 0.5) * 9.0, 0, 1) ** 3
        fine = fbm3(P * 22.0 + 7.0 + seed, 4)
        alb = np.stack([0.06 + 0.05 * n, 0.045 + 0.035 * n, 0.04 + 0.025 * n], -1) * (0.8 + 0.4 * fine[..., None])
        emi = np.array([2.2, 0.55, 0.10], np.float32) * (seam[..., None] * 0.8 + 0.015 + 0.05 * np.clip(fine - 0.6, 0, 1)[..., None])
        return np.concatenate([alb, emi], -1)
    a = cached_map(f'magma_{seed:g}_{w}', mk)
    return a[..., :3], a[..., 3:]

def rock_maps(seed=11.0, w=2048, h=1024, tint=(1.15, 1.0, 0.86), base=0.05):
    """an airless cratered rock world (Theia, the young Moon): albedo map"""
    def mk():
        P = sphere_grid(w, h)
        n = fbm3(P * 3.2 + seed, 6); n2 = fbm3(P * 14.0 + seed + 5, 4)
        cr = np.clip(1 - np.abs(fbm3(P * 45.0 + seed + 4, 4) - 0.5) * 7, 0, 1) ** 4
        v = base + 0.10 * n + 0.05 * n2 - 0.03 * cr
        return np.stack([v * tint[0], v * tint[1], v * tint[2]], -1)
    return cached_map(f'rock_{seed:g}', mk)

# ---------------------------------------------------------------- particles & glows
def splat(img, c, X, col, size=1):
    """additive points: X (N, 3) world positions, col (N, 3) or (3,)"""
    x, y, z = cm.project(c, X)
    ok = (z > 0) & (x >= 1) & (x < W - 2) & (y >= 1) & (y < H - 2)
    xi = x[ok].astype(np.int64); yi = y[ok].astype(np.int64)
    cc = np.broadcast_to(np.asarray(col, np.float32), (len(X), 3))[ok]
    for dy in range(size):
        for dx in range(size):
            np.add.at(img, (yi + dy, xi + dx), cc)

def glow(img, px, py, sigmas_gains, col):
    gx, gy = pix_grid()
    r2 = (gx + W / 2 - px) ** 2 + (-gy + H / 2 - py) ** 2
    acc = 0
    for s, g in sigmas_gains: s = s * SCALE; acc = acc + np.exp(-r2 / (2 * s * s)) * g
    img += acc[..., None] * np.asarray(col, np.float32)

# ---------------------------------------------------------------- post
def finish(img, expo=1.0, bloom=0.45, vig=0.22):
    img = cm.bloom(img, thr=0.9, k=bloom) if H % 4 == 0 and W % 4 == 0 else img
    img = cm.vignette(cm.tonemap(img, expo), vig)
    return cm.to_u8(img)
