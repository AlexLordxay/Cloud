# «Знайомся: Нептун» — the fall through the clouds. A volumetric renderer on the CPU (numba), since the WebGL of the other
# scenes runs in SwiftShader and would take minutes a frame for clouds like these.
#
#   python3 scenes/neptune_meet/clouds.py build            -> work/neptune_meet/vol_*.npy (density, light; ~5 min)
#   python3 scenes/neptune_meet/clouds.py stills 0,3,6     -> work/neptune_meet/cl_<t>.png
#   python3 scenes/neptune_meet/clouds.py video t0 t1 [n k]-> work/neptune_meet/cl/f_<frame>.png (every k-th of n workers)
#
# The world: z up, metres. A deck of cumulus with a winding shaft down through it; the walls are billows (a signed distance
# to the shaft and to the top of the deck, bumped by three octaves of cellular "puffs"). Above, far away, streaks of cirrus.
# Light: the Sun (a bright star, 30 au away) from above; its optical depth is swept layer by layer down the volume; the sky
# light is a second, blurred sweep straight down. Colour: methane eats red, so the deeper the light has gone, the bluer it
# is — white tops, blue walls, navy depths (the way the real Neptune turns blue).
import sys, os, math, time
import numpy as np
from numba import njit, prange

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '..', '..', 'work', 'neptune_meet')
os.makedirs(WORK, exist_ok=True)

H = 2.5                      # voxel, m
NX, NY, NZ = 576, 576, 1280  # 1440 x 1440 x 3200 m
X0, Y0, Z0 = -720.0, -720.0, 0.0
ZTOP = 2700.0                # the mean top of the deck
SIG = 0.07                   # extinction of the cloud at density 1, 1/m
SUN = np.array([0.30, 0.12, 1.0]); SUN /= np.linalg.norm(SUN)
TAUMAX = 30.0


# ---------------------------------------------------------------------------------------------------------- noise
@njit(cache=True, inline='always')
def hash3(i, j, k, s):
    h = (i * 374761393 + j * 668265263 + k * 1274126177 + s * 1442695040) & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    h = h ^ (h >> 16)
    return h


@njit(cache=True, inline='always')
def rnd(h):
    return (h & 0xffffff) / 16777216.0


@njit(cache=True)
def worley(x, y, z, s):
    # F1 (distance to the nearest feature point, cells of size 1) — 1-F1^2 is a round puff
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    best = 9.0
    for dk in range(-1, 2):
        for dj in range(-1, 2):
            for di in range(-1, 2):
                ci, cj, ck = ix + di, iy + dj, iz + dk
                h = hash3(int(ci), int(cj), int(ck), s)
                px = ci + rnd(h); py = cj + rnd(hash3(int(ci), int(cj), int(ck), s + 17)); pz = ck + rnd(hash3(int(ci), int(cj), int(ck), s + 31))
                d = (px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2
                if d < best:
                    best = d
    return best  # squared


@njit(cache=True)
def vnoise(x, y, z, s):
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    ux, uy, uz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    r = 0.0
    for dk in range(2):
        for dj in range(2):
            for di in range(2):
                v = rnd(hash3(int(ix + di), int(iy + dj), int(iz + dk), s))
                r += v * (ux if di else 1 - ux) * (uy if dj else 1 - uy) * (uz if dk else 1 - uz)
    return r


@njit(cache=True)
def fbm(x, y, z, s, oct):
    a, f, r, n = 0.5, 1.0, 0.0, 0.0
    for o in range(oct):
        r += a * vnoise(x * f, y * f, z * f, s + o * 101)
        n += a; a *= 0.5; f *= 2.03
    return r / n


# ---------------------------------------------------------------------------------------------------------- the shape
@njit(cache=True)
def shaft(z):
    # the centre of the shaft and its radius at height z
    cx = 110 * math.sin(z / 520 + 0.7) + 45 * math.sin(z / 230 + 2.1)
    cy = 90 * math.sin(z / 610 + 2.4) + 40 * math.sin(z / 270 + 0.3)
    r = 230 + 60 * math.sin(z / 380 + 1.3) + 30 * math.sin(z / 170)
    return cx, cy, r


@njit(cache=True)
def sdist(x, y, z):
    # signed distance into the cloud before the puffs (+ inside)
    cx, cy, r = shaft(z)
    ang = math.atan2(y - cy, x - cx)
    rr = r * (1 + 0.18 * math.sin(3 * ang + z / 300) + 0.1 * math.sin(5 * ang - z / 210))
    s1 = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) - rr
    # top of the deck: rolling, with turrets
    top = ZTOP + 260 * (fbm(x / 700, y / 700, 0.5, 7, 3) - 0.5) + 520 * max(0.0, fbm(x / 380, y / 380, 3.5, 11, 2) - 0.55)
    s2 = top - z
    s = min(s1, s2)
    # bulges and caves
    s += 70 * (fbm(x / 260, y / 260, z / 260, 23, 3) - 0.5)
    return s


@njit(cache=True)
def puffs(x, y, z):
    b = 0.0
    b += 34 * (0.55 - worley(x / 70, y / 70, z / 70, 1))
    b += 13 * (0.55 - worley(x / 26, y / 26, z / 26, 2))
    b += 4.5 * (0.55 - worley(x / 9.5, y / 9.5, z / 9.5, 3))
    return b


@njit(parallel=True, cache=True)
def build_density(den):
    for k in prange(NZ):
        z = Z0 + (k + 0.5) * H
        for j in range(NY):
            y = Y0 + (j + 0.5) * H
            for i in range(NX):
                x = X0 + (i + 0.5) * H
                s = sdist(x, y, z)
                if s < -60:
                    den[k, j, i] = 0
                    continue
                if s > 90:
                    den[k, j, i] = 255
                    continue
                s += puffs(x, y, z)
                d = s / 4.0
                if d <= 0:
                    den[k, j, i] = 0
                else:
                    # inside: a little texture, so thin edges are wispy
                    tex = 0.75 + 0.5 * vnoise(x / 6, y / 6, z / 6, 41)
                    v = min(1.0, d) * min(1.0, tex if d < 3 else 1.0)
                    den[k, j, i] = int(v * 255 + 0.5)


@njit(cache=True)
def bilerp(a, x, y):
    ny, nx = a.shape
    x = min(max(x, 0.0), nx - 1.001); y = min(max(y, 0.0), ny - 1.001)
    i, j = int(x), int(y); fx, fy = x - i, y - j
    return (a[j, i] * (1 - fx) + a[j, i + 1] * fx) * (1 - fy) + (a[j + 1, i] * (1 - fx) + a[j + 1, i + 1] * fx) * fy


@njit(parallel=True, cache=True)
def sweep_sun(den, out, lx, ly, lz):
    # optical depth towards the Sun, from the top layer down; each layer looks up along the light into the one above
    prev = np.zeros((NY, NX), np.float32)
    cur = np.zeros((NY, NX), np.float32)
    sx, sy = lx / lz, ly / lz
    for k in range(NZ - 1, -1, -1):
        for j in prange(NY):
            for i in range(NX):
                t = bilerp(prev, i + sx, j + sy)
                cur[j, i] = t + den[k, j, i] / 255.0 * SIG * H / lz
        for j in prange(NY):
            for i in range(NX):
                prev[j, i] = cur[j, i]
                out[k, j, i] = int(255 * math.sqrt(min(cur[j, i], TAUMAX) / TAUMAX) + 0.5)


@njit(parallel=True, cache=True)
def sweep_sky(den, out):
    # the sky light: straight down, spreading sideways (a blur each layer) — a soft occlusion from above
    prev = np.zeros((NY, NX), np.float32)
    tmp = np.zeros((NY, NX), np.float32)
    R = 3
    for k in range(NZ - 1, -1, -1):
        for j in prange(NY):
            for i in range(NX):
                s = 0.0; n = 0
                for d in range(-R, R + 1):
                    ii = min(max(i + d, 0), NX - 1); s += prev[j, ii]; n += 1
                tmp[j, i] = s / n
        for j in prange(NY):
            for i in range(NX):
                s = 0.0; n = 0
                for d in range(-R, R + 1):
                    jj = min(max(j + d, 0), NY - 1); s += tmp[jj, i]; n += 1
                prev[j, i] = s / n + den[k, j, i] / 255.0 * SIG * H * 0.35
                out[k, j, i] = int(255 * math.sqrt(min(prev[j, i], TAUMAX) / TAUMAX) + 0.5)


B = 8  # coarse block for skipping empty space


@njit(parallel=True, cache=True)
def coarse(den, occ):
    nz, ny, nx = occ.shape
    for k in prange(nz):
        for j in range(ny):
            for i in range(nx):
                m = 0
                for kk in range(k * B - 1, k * B + B + 1):
                    for jj in range(j * B - 1, j * B + B + 1):
                        for ii in range(i * B - 1, i * B + B + 1):
                            if 0 <= kk < NZ and 0 <= jj < NY and 0 <= ii < NX:
                                if den[kk, jj, ii] > m:
                                    m = den[kk, jj, ii]
                occ[k, j, i] = 0 if m < 2 else 1


@njit(cache=True)
def chamfer(occ, dist):
    # distance (in blocks, chebyshev) to the nearest occupied block
    nz, ny, nx = occ.shape
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                dist[k, j, i] = 0 if occ[k, j, i] else 100
    for it in range(12):
        ch = False
        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    d = dist[k, j, i]
                    if d == 0:
                        continue
                    m = d
                    for dk in range(-1, 2):
                        for dj in range(-1, 2):
                            for di in range(-1, 2):
                                kk, jj, ii = k + dk, j + dj, i + di
                                if 0 <= kk < nz and 0 <= jj < ny and 0 <= ii < nx:
                                    if dist[kk, jj, ii] + 1 < m:
                                        m = dist[kk, jj, ii] + 1
                    if m < d:
                        dist[k, j, i] = m; ch = True
        if not ch:
            break


def build():
    t0 = time.time()
    den = np.zeros((NZ, NY, NX), np.uint8)
    build_density(den); print('density', round(time.time() - t0), 's', flush=True)
    sun = np.zeros_like(den); sweep_sun(den, sun, *SUN); print('sun', round(time.time() - t0), 's', flush=True)
    sky = np.zeros_like(den); sweep_sky(den, sky); print('sky', round(time.time() - t0), 's', flush=True)
    occ = np.zeros((NZ // B, NY // B, NX // B), np.uint8); coarse(den, occ)
    dist = np.zeros_like(occ); chamfer(occ, dist); print('skip', round(time.time() - t0), 's', flush=True)
    for n, a in (('den', den), ('sun', sun), ('sky', sky), ('dist', dist)):
        np.save(os.path.join(WORK, f'vol_{n}.npy'), a)


# ---------------------------------------------------------------------------------------------------------- rendering
@njit(cache=True, inline='always')
def tri(a, x, y, z):
    # trilinear in voxel coordinates (cell centres at .5)
    x -= 0.5; y -= 0.5; z -= 0.5
    if x < 0 or y < 0 or z < 0 or x >= NX - 1 or y >= NY - 1 or z >= NZ - 1:
        return -1.0
    i, j, k = int(x), int(y), int(z)
    fx, fy, fz = x - i, y - j, z - k
    c00 = a[k, j, i] * (1 - fx) + a[k, j, i + 1] * fx
    c10 = a[k, j + 1, i] * (1 - fx) + a[k, j + 1, i + 1] * fx
    c01 = a[k + 1, j, i] * (1 - fx) + a[k + 1, j, i + 1] * fx
    c11 = a[k + 1, j + 1, i] * (1 - fx) + a[k + 1, j + 1, i + 1] * fx
    return ((c00 * (1 - fy) + c10 * fy) * (1 - fz) + (c01 * (1 - fy) + c11 * fy) * fz) / 255.0


@njit(cache=True, inline='always')
def hg(c, g):
    return (1 - g * g) / (4 * math.pi * (1 + g * g - 2 * g * c) ** 1.5)


@njit(cache=True)
def gas(depth, ch):
    # transmission of the methane-rich gas over `depth` metres below the top of the deck (artistic scale), per channel
    k = (1 / 900.0, 1 / 2600.0, 1 / 9000.0)[ch]
    return math.exp(-max(depth, 0.0) * k)


@njit(cache=True)
def sky_col(dx, dy, dz, ch, sunk):
    # above the deck: a deep blue sky, cirrus streaks far up, the Sun a tiny hard star
    zen = (0.010, 0.035, 0.11)[ch]
    hor = (0.10, 0.25, 0.48)[ch]
    u = max(dz, 0.0)
    c = hor + (zen - hor) * (1 - (1 - u) ** 3)
    if dz > 0.02:
        # cirrus on a plane 6 km above the deck
        t = 6000.0 / dz
        px, py = dx * t, dy * t
        # stretched along the wind (x)
        q = fbm(px / 5200, py / 900, 0.3, 61, 5)
        q2 = fbm(px / 1700, py / 300, 1.3, 67, 4)
        w = max(0.0, q * 0.85 + q2 * 0.45 - 0.62) * 2.6
        w *= min(1.0, dz * 4)
        cc = (0.85, 0.93, 1.0)[ch]
        c = c * (1 - min(w, 1.0) * 0.6) + cc * min(w, 1.2) * 0.75
    cs = dx * SUN[0] + dy * SUN[1] + dz * SUN[2]
    if cs > 0.9999:
        c += 60.0 * sunk
    c += 0.25 * sunk * hg(cs, 0.92) * 0.1
    return c


@njit(parallel=True, cache=True)
def render(den, sun, sky, dist, img, cam, fwd, right, up, fov, expo, seed):
    hgt, wid = img.shape[0], img.shape[1]
    tanf = math.tan(fov * 0.5)
    sunC = (1.0, 0.97, 0.92)
    ambTop = (0.30, 0.42, 0.62)
    for py in prange(hgt):
        for px in range(wid):
            u = ((px + 0.5) / wid * 2 - 1) * tanf * wid / hgt
            v = (1 - (py + 0.5) / hgt * 2) * tanf
            dx = fwd[0] + right[0] * u + up[0] * v
            dy = fwd[1] + right[1] * u + up[1] * v
            dz = fwd[2] + right[2] * u + up[2] * v
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            cth = dx * SUN[0] + dy * SUN[1] + dz * SUN[2]
            ph0 = hg(cth, 0.6) * 0.7 + hg(cth, -0.25) * 0.3
            ph1 = hg(cth, 0.3) * 0.6 + hg(cth, -0.15) * 0.4
            ph2 = 1 / (4 * math.pi)
            jit = rnd(hash3(px, py, seed, 5))
            L = np.zeros(3); T = np.ones(3)
            t = 0.5 + jit * H
            tmax = 9000.0
            while t < tmax:
                x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                vx = (x - X0) / H; vy = (y - Y0) / H; vz = (z - Z0) / H
                if vz >= NZ - 1 and dz > 0:
                    break
                if vx < 0 or vy < 0 or vz < 0 or vx >= NX - 1 or vy >= NY - 1 or vz >= NZ - 1:
                    # outside the volume: treat the walls beyond as cloud-less (the sky above, navy below)
                    if vz < 0 or (dz <= 0 and (vx < 0 or vy < 0 or vx >= NX - 1 or vy >= NY - 1) and z < ZTOP):
                        break
                    t += 20.0
                    continue
                cb = dist[int(vz) // B, int(vy) // B, int(vx) // B]
                if cb > 1:
                    t += (cb - 1) * B * H * 0.95 + H * 0.5
                    continue
                d = tri(den, vx, vy, vz)
                step = max(H * 0.55, t * 0.0035)
                if d > 0.004:
                    # fine grain near the camera so walls close up aren't smooth
                    if t < 250:
                        d *= 0.82 + 0.36 * vnoise(x / 2.2, y / 2.2, z / 2.2, 77)
                    ts = tri(sun, vx, vy, vz); ts = ts * ts * TAUMAX
                    ta = tri(sky, vx, vy, vz); ta = ta * ta * TAUMAX
                    sig = d * SIG
                    # multiple scattering, Wrenninge-style octaves
                    ms = math.exp(-ts) * ph0 + 0.5 * math.exp(-ts * 0.35) * ph1 + 0.25 * math.exp(-ts * 0.12) * ph2
                    powder = 1 - 0.6 * math.exp(-ts * 3 - 0.3)
                    depth = ZTOP + 200 - z
                    a = math.exp(-sig * step)
                    for ch in range(3):
                        g = gas(depth / SUN[2], ch)
                        ga = gas(depth, ch)
                        S = (sunC[ch] * g * ms * 4.2 * powder + ambTop[ch] * ga * math.exp(-ta) * 0.55 + ambTop[ch] * ga * 0.04)
                        L[ch] += T[ch] * S * (1 - a)
                        T[ch] *= a
                    if T[0] < 0.004 and T[1] < 0.004 and T[2] < 0.004:
                        break
                t += step
            # what's behind
            if T[2] > 0.004:
                for ch in range(3):
                    if dz > 0 and cam[2] + dz * t > ZTOP - 400:
                        bg = sky_col(dx, dy, dz, ch, 1.0)
                    else:
                        zz = cam[2] + dz * min(t, 3000.0)
                        bg = (0.004, 0.014, 0.045)[ch] * gas(ZTOP - zz, ch) * 3
                    L[ch] += T[ch] * bg
            # air haze between the camera and the first cloud: thin, blue
            for ch in range(3):
                img[py, px, ch] = L[ch] * expo


def tonemap(img):
    # filmic: ACES-ish, then sRGB
    a = img
    x = (a * (2.51 * a + 0.03)) / (a * (2.43 * a + 0.59) + 0.14)
    x = np.clip(x, 0, 1)
    return (np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------------------------------------------------- the camera
def look(pos, target, roll=0.0):
    f = np.array(target, float) - np.array(pos, float); f /= np.linalg.norm(f)
    wup = np.array([0, 1.0, 0]) if abs(f[2]) > 0.98 else np.array([0, 0, 1.0])
    r = np.cross(f, wup); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    c, s = math.cos(roll), math.sin(roll)
    r2 = r * c + u * s; u2 = -r * s + u * c
    return f, r2, u2


def smooth(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * (3 - 2 * k)


def cam_at(t):
    # test: 0–3 s above the deck, looking down into the shaft; 3–10 s falling down it
    cx, cy, _ = shaft(ZTOP + 300)
    if t < 3.5:
        k = t / 3.5
        z = ZTOP + 1100 - 700 * smooth(k) - 80 * k
        pos = np.array([cx + 260 * (1 - k), cy - 200 * (1 - k), z])
        tgt = np.array([cx, cy, ZTOP - 900])
        f, r, u = look(pos, tgt, roll=0.15 * k)
        return pos, f, r, u
    k = t - 3.5
    v = 160.0  # m/s
    z0 = ZTOP + 1100 - 780
    z = z0 - v * k - 8 * k * k
    sx, sy, _ = shaft(z)
    s0x, s0y, _ = shaft(z0)
    bl = smooth(k / 1.5)
    px = (cx + (s0x - cx)) * (1 - bl) + sx * bl
    py = (cy + (s0y - cy)) * (1 - bl) + sy * bl
    pos = np.array([px, py, z])
    tx, ty, _ = shaft(z - 600)
    tgt = np.array([tx + 60 * math.sin(k * 0.4), ty, z - 600])
    f, r, u = look(pos, tgt, roll=0.15 + 0.12 * k)
    return pos, f, r, u


def load():
    return [np.load(os.path.join(WORK, f'vol_{n}.npy'), mmap_mode='r') for n in ('den', 'sun', 'sky', 'dist')]


def frame(vols, t, W=720, Hh=1280, seed=0):
    pos, f, r, u = cam_at(t)
    img = np.zeros((Hh, W, 3), np.float64)
    render(*vols, img, pos, f, r, u, math.radians(68), 1.0, seed)
    return tonemap(img)


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'build':
        build()
    else:
        from PIL import Image
        vols = [np.ascontiguousarray(a) for a in load()]
        W = int(os.environ.get('W', 720)); Hh = int(os.environ.get('HH', 1280))
        if mode == 'stills':
            for t in map(float, sys.argv[2].split(',')):
                t0 = time.time()
                Image.fromarray(frame(vols, t, W, Hh)).save(os.path.join(WORK, f'cl_{t}.png'))
                print('still', t, round(time.time() - t0, 1), 's', flush=True)
        elif mode == 'video':
            t0s, t1s = float(sys.argv[2]), float(sys.argv[3])
            nw, kw = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1, 0)
            out = os.path.join(WORK, 'cl'); os.makedirs(out, exist_ok=True)
            for fi in range(int(t0s * 30), int(t1s * 30)):
                if fi % nw != kw:
                    continue
                fn = os.path.join(out, f'f_{fi:05d}.png')
                if os.path.exists(fn):
                    continue
                Image.fromarray(frame(vols, fi / 30, W, Hh, seed=fi)).save(fn)
                print(fi, flush=True)
