# «Знайомся: Нептун» — the fall through the clouds. A volumetric renderer on the CPU (numba), since the WebGL of the other
# scenes runs in SwiftShader and would take minutes a frame for clouds like these.
#
#   python3 scenes/neptune_meet/clouds.py build             -> work/neptune_meet/{near,far}_*.npy (density, light; ~3 min)
#   python3 scenes/neptune_meet/clouds.py stills 0,3,6      -> work/neptune_meet/cl_<t>.png   (W=, HH= for a smaller size)
#   python3 scenes/neptune_meet/clouds.py video t0 t1 [n k] -> work/neptune_meet/cl/f_<frame>.png (every n-th from k)
#
# The world: z up, metres. A deck of cumulus with towers on top and a winding shaft down through it; the walls are billows
# (a signed distance to the shaft and to the top of the deck, bumped by octaves of round cellular "puffs"). Two volumes:
# "near" (2.5 m voxels, the shaft and the deck round it) and "far" (16 m, the sea of clouds out to the horizon, its fine
# grain added while rendering). Far up, streaks of cirrus on a plane.
# Light: the Sun (a hard bright star, 30 au away); its optical depth is swept layer by layer down each volume; the sky
# light is a second, blurred sweep straight down; the air between gets the same light, so the shaft has beams in it.
# Colour: methane eats red, so the deeper the light has gone, the bluer it is — white tops, blue walls, navy depths.
import sys, os, math, time
import numpy as np
from numba import njit, prange

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '..', '..', 'work', 'neptune_meet')
os.makedirs(WORK, exist_ok=True)

ZTOP = 2700.0                # the mean top of the deck
SIG = 0.07                   # extinction of the cloud at density 1, 1/m
SUN = np.array([0.62, 0.30, 0.72]); SUN /= np.linalg.norm(SUN)
TAUMAX = 30.0
B = 8                        # coarse block for skipping empty space
# volumes: x0, y0, z0, h, nx, ny, nz
NEAR = np.array([-1000.0, -1000.0, 0.0, 2.5, 800, 800, 1440])        # 2 x 2 x 3.6 km
FAR = np.array([-14000.0, -14000.0, 1700.0, 16.0, 1750, 1750, 128])  # 28 x 28 x 2 km


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
def sworley(x, y, z, s):
    # smooth F1^2 (a soft minimum over the nearby feature points): round puffs with soft creases between them
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    acc = 0.0
    K = 9.0
    for dk in range(-1, 2):
        for dj in range(-1, 2):
            for di in range(-1, 2):
                ci, cj, ck = int(ix + di), int(iy + dj), int(iz + dk)
                px = ci + rnd(hash3(ci, cj, ck, s)); py = cj + rnd(hash3(ci, cj, ck, s + 17)); pz = ck + rnd(hash3(ci, cj, ck, s + 31))
                d = (px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2
                acc += math.exp(-K * d)
    return -math.log(acc + 1e-9) / K


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
    cx = 140 * math.sin(z / 560 + 0.7) + 55 * math.sin(z / 240 + 2.1)
    cy = 110 * math.sin(z / 640 + 2.4) + 45 * math.sin(z / 280 + 0.3)
    r = 270 + 70 * math.sin(z / 400 + 1.3) + 35 * math.sin(z / 170)
    return cx, cy, r


@njit(cache=True)
def top_h(x, y):
    # the top of the deck: rolling, with cumulus towers; flatter round the mouth of the shaft
    base = ZTOP + 420 * (fbm(x / 2200, y / 2200, 0.5, 7, 3) - 0.5)
    tw = max(0.0, fbm(x / 700, y / 700, 3.5, 11, 3) - 0.53)
    r = math.sqrt(x * x + y * y)
    tw *= min(1.0, max(0.0, (r - 450) / 500))
    return base + 2400 * tw ** 1.15


@njit(cache=True)
def sdist(x, y, z, far):
    # signed distance into the cloud before the puffs (+ inside)
    s = top_h(x, y) - z
    if not far:
        cx, cy, r = shaft(z)
        ang = math.atan2(y - cy, x - cx)
        rr = r * (1 + 0.22 * math.sin(3 * ang + z / 300) + 0.12 * math.sin(5 * ang - z / 210))
        s1 = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) - rr
        # the mouth flares out
        s1 -= 160 * max(0.0, (z - (ZTOP - 350)) / 350) ** 2
        s = min(s, s1)
    # bulges and caves
    s += 90 * (fbm(x / 300, y / 300, z / 300, 23, 3) - 0.5)
    return s


@njit(cache=True)
def puffs(x, y, z, far):
    b = 0.0
    b += 60 * (0.42 - sworley(x / 130, y / 130, z / 130, 1))
    b += 24 * (0.42 - sworley(x / 48, y / 48, z / 48, 2))
    if not far:
        b += 9 * (0.42 - sworley(x / 18, y / 18, z / 18, 3))
        b += 3.2 * (0.42 - sworley(x / 6.5, y / 6.5, z / 6.5, 4))
    return b


@njit(parallel=True, cache=True)
def build_density(den, M, far):
    x0, y0, z0, h = M[0], M[1], M[2], M[3]
    nz, ny, nx = den.shape
    edge = 4.0 if not far else 14.0
    for k in prange(nz):
        z = z0 + (k + 0.5) * h
        for j in range(ny):
            y = y0 + (j + 0.5) * h
            for i in range(nx):
                x = x0 + (i + 0.5) * h
                s = sdist(x, y, z, far)
                if s < -110:
                    den[k, j, i] = 0
                    continue
                if s > 130:
                    den[k, j, i] = 255
                    continue
                s += puffs(x, y, z, far)
                d = s / edge
                if d <= 0:
                    den[k, j, i] = 0
                else:
                    tex = 1.0
                    if not far and d < 3:
                        tex = 0.7 + 0.6 * vnoise(x / 5, y / 5, z / 5, 41)
                    den[k, j, i] = int(min(1.0, d * tex) * 255 + 0.5)


@njit(cache=True)
def bilerp(a, x, y):
    ny, nx = a.shape
    x = min(max(x, 0.0), nx - 1.001); y = min(max(y, 0.0), ny - 1.001)
    i, j = int(x), int(y); fx, fy = x - i, y - j
    return (a[j, i] * (1 - fx) + a[j, i + 1] * fx) * (1 - fy) + (a[j + 1, i] * (1 - fx) + a[j + 1, i + 1] * fx) * fy


@njit(parallel=True, cache=True)
def sweep_sun(den, out, h, lx, ly, lz):
    # optical depth towards the Sun, from the top layer down; each layer looks up along the light into the one above
    nz, ny, nx = den.shape
    prev = np.zeros((ny, nx), np.float32)
    cur = np.zeros((ny, nx), np.float32)
    sx, sy = lx / lz, ly / lz
    for k in range(nz - 1, -1, -1):
        for j in prange(ny):
            for i in range(nx):
                t = bilerp(prev, i + sx, j + sy)
                cur[j, i] = t + den[k, j, i] / 255.0 * SIG * h / lz
        for j in prange(ny):
            for i in range(nx):
                prev[j, i] = cur[j, i]
                out[k, j, i] = int(255 * math.sqrt(min(cur[j, i], TAUMAX) / TAUMAX) + 0.5)


@njit(parallel=True, cache=True)
def sweep_sky(den, out, h, R):
    # the sky light: straight down, spreading sideways (a blur each layer) — a soft occlusion from above
    nz, ny, nx = den.shape
    prev = np.zeros((ny, nx), np.float32)
    tmp = np.zeros((ny, nx), np.float32)
    for k in range(nz - 1, -1, -1):
        for j in prange(ny):
            for i in range(nx):
                s = 0.0; n = 0
                for d in range(-R, R + 1):
                    ii = min(max(i + d, 0), nx - 1); s += prev[j, ii]; n += 1
                tmp[j, i] = s / n
        for j in prange(ny):
            for i in range(nx):
                s = 0.0; n = 0
                for d in range(-R, R + 1):
                    jj = min(max(j + d, 0), ny - 1); s += tmp[jj, i]; n += 1
                prev[j, i] = s / n + den[k, j, i] / 255.0 * SIG * h * 0.3
                out[k, j, i] = int(255 * math.sqrt(min(prev[j, i], TAUMAX) / TAUMAX) + 0.5)


@njit(parallel=True, cache=True)
def coarse(den, occ):
    nz, ny, nx = den.shape
    cz, cy, cx = occ.shape
    for k in prange(cz):
        for j in range(cy):
            for i in range(cx):
                m = 0
                for kk in range(k * B - 1, k * B + B + 1):
                    for jj in range(j * B - 1, j * B + B + 1):
                        for ii in range(i * B - 1, i * B + B + 1):
                            if 0 <= kk < nz and 0 <= jj < ny and 0 <= ii < nx:
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
    for it in range(14):
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


def build_one(name, M, far):
    t0 = time.time()
    nx, ny, nz = int(M[4]), int(M[5]), int(M[6])
    den = np.zeros((nz, ny, nx), np.uint8)
    build_density(den, M, far); print(name, 'density', round(time.time() - t0), 's', flush=True)
    sun = np.zeros_like(den); sweep_sun(den, sun, M[3], *SUN)
    sky = np.zeros_like(den); sweep_sky(den, sky, M[3], 3 if not far else 1)
    occ = np.zeros(((nz + B - 1) // B, (ny + B - 1) // B, (nx + B - 1) // B), np.uint8); coarse(den, occ)
    dist = np.zeros_like(occ); chamfer(occ, dist); print(name, 'light', round(time.time() - t0), 's', flush=True)
    for n, a in (('den', den), ('sun', sun), ('sky', sky), ('dist', dist)):
        np.save(os.path.join(WORK, f'{name}_{n}.npy'), a)


def build(which='near,far'):
    if 'near' in which:
        build_one('near', NEAR, False)
    if 'far' in which:
        build_one('far', FAR, True)


# ---------------------------------------------------------------------------------------------------------- rendering
@njit(cache=True, inline='always')
def tri(a, x, y, z):
    # trilinear in voxel coordinates (cell centres at .5)
    nz, ny, nx = a.shape
    x -= 0.5; y -= 0.5; z -= 0.5
    x = min(max(x, 0.0), nx - 1.001); y = min(max(y, 0.0), ny - 1.001); z = min(max(z, 0.0), nz - 1.001)
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


@njit(cache=True, inline='always')
def gas(depth, ch):
    # transmission of the methane-rich gas over `depth` metres below the top of the deck (artistic scale), per channel
    if ch == 0:
        k = 1 / 1000.0
    elif ch == 1:
        k = 1 / 2600.0
    else:
        k = 1 / 8000.0
    return math.exp(-max(depth, 0.0) * k)


@njit(cache=True)
def sky_col(dx, dy, dz, ch, cirrus):
    # above the deck: deep blue overhead, pale cyan haze at the horizon, cirrus streaks far up, the Sun a hard star
    zen = (0.004, 0.018, 0.075)[ch]
    hor = (0.16, 0.34, 0.56)[ch]
    u = max(dz, 0.0)
    c = hor + (zen - hor) * (1 - (1 - u) ** 4)
    if dz > 0.01 and cirrus > 0:
        t = 7000.0 / dz
        px, py = dx * t, dy * t
        # stretched along the wind (x)
        q = fbm(px / 9000, py / 1500, 0.3, 61, 5)
        q2 = fbm(px / 2600, py / 380, 1.3, 67, 4)
        w = max(0.0, q * 0.8 + q2 * 0.5 - 0.6) * 2.8
        w *= min(1.0, dz * 5) * cirrus
        cs = dx * SUN[0] + dy * SUN[1] + dz * SUN[2]
        cc = (0.8, 0.9, 1.0)[ch] * (0.6 + 0.9 * hg(cs, 0.5) * 4)
        c = c * (1 - min(w, 1.0) * 0.5) + cc * min(w, 1.3) * 0.55
    cs = dx * SUN[0] + dy * SUN[1] + dz * SUN[2]
    if cs > 0.99997:
        c += 400.0
    elif cs > 0.9999:
        c += 6.0
    c += 0.6 * (1 - u) * (1.0, 0.9, 0.75)[ch] * hg(cs, 0.85) * 0.15
    return c


@njit(cache=True, inline='always')
def air_sig(z):
    # the haze: thin above the deck, thickening down the shaft
    return 1 / 16000.0 + (1 / 1400.0) * min(1.0, max(0.0, (ZTOP + 100 - z) / 1600))


@njit(parallel=True, cache=True)
def render(nd, ns, nk, nb, fd, fs, fk, fb, img, cam, fwd, right, up, fov, expo, seed, fine):
    hgt, wid = img.shape[0], img.shape[1]
    tanf = math.tan(fov * 0.5)
    sunC = (1.0, 0.97, 0.92)
    amb = (0.10, 0.22, 0.48)
    nx0, ny0, nz0, nh = NEAR[0], NEAR[1], NEAR[2], NEAR[3]
    nnx, nny, nnz = NEAR[4], NEAR[5], NEAR[6]
    fx0, fy0, fz0, fh = FAR[0], FAR[1], FAR[2], FAR[3]
    fnx, fny, fnz = FAR[4], FAR[5], FAR[6]
    ftop = fz0 + fnz * fh
    for py in prange(hgt):
        for px in range(wid):
            u = ((px + 0.5) / wid * 2 - 1) * tanf * wid / hgt
            v = (1 - (py + 0.5) / hgt * 2) * tanf
            dx = fwd[0] + right[0] * u + up[0] * v
            dy = fwd[1] + right[1] * u + up[1] * v
            dz = fwd[2] + right[2] * u + up[2] * v
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            cth = dx * SUN[0] + dy * SUN[1] + dz * SUN[2]
            ph0 = hg(cth, 0.65) * 0.65 + hg(cth, -0.25) * 0.35
            ph1 = hg(cth, 0.35) * 0.6 + hg(cth, -0.15) * 0.4
            ph2 = 1 / (4 * math.pi)
            pha = hg(cth, 0.55) * 0.5 + 0.5 / (4 * math.pi)
            jit = rnd(hash3(px, py, seed, 5))
            L0 = 0.0; L1 = 0.0; L2 = 0.0; T0 = 1.0; T1 = 1.0; T2 = 1.0
            t = 0.3 + jit * 2.0
            ended = 0   # 0 still going, 1 sky, 2 the deep
            it = 0
            while it < 4000:
                it += 1
                x = cam[0] + dx * t; y = cam[1] + dy * t; z = cam[2] + dz * t
                # which volume?
                vol = 0
                vx = (x - nx0) / nh; vy = (y - ny0) / nh; vz = (z - nz0) / nh
                if 0 <= vx < nnx - 1 and 0 <= vy < nny - 1 and 0 <= vz < nnz - 1:
                    vol = 1
                else:
                    vx = (x - fx0) / fh; vy = (y - fy0) / fh; vz = (z - fz0) / fh
                    if 0 <= vx < fnx - 1 and 0 <= vy < fny - 1 and 0 <= vz < fnz - 1:
                        vol = 2
                if vol == 0:
                    if z >= ftop - 1 and dz >= 0:
                        ended = 1; break
                    if z < fz0 + 1:
                        ended = 2; break
                    if abs(x) > -fx0 or abs(y) > -fy0:
                        ended = 1 if z > ZTOP - 300 else 2
                        break
                    st = 30.0
                    sa = air_sig(z) * st
                    a = math.exp(-sa)
                    for ch in range(3):
                        g = gas((ZTOP + 200 - z) / SUN[2], ch)
                        c = sunC[ch] * g * pha * 2.2 + amb[ch] * gas(ZTOP + 200 - z, ch) * 0.25
                        if ch == 0:
                            L0 += T0 * c * (1 - a); T0 *= a
                        elif ch == 1:
                            L1 += T1 * c * (1 - a); T1 *= a
                        else:
                            L2 += T2 * c * (1 - a); T2 *= a
                    t += st
                    continue
                if vol == 1:
                    cb = nb[int(vz) // B, int(vy) // B, int(vx) // B]
                    h = nh
                else:
                    cb = fb[int(vz) // B, int(vy) // B, int(vx) // B]
                    h = fh
                skip = 0.0
                if cb > 1:
                    skip = (cb - 1) * B * h * 0.95 + h * 0.5
                    d = 0.0
                else:
                    d = tri(nd, vx, vy, vz) if vol == 1 else tri(fd, vx, vy, vz)
                if vol == 2 and d > 0.0 and d < 0.999:
                    # the far deck's fine grain, added here
                    q = vnoise(x / 22, y / 22, z / 22, 91) * 0.6 + vnoise(x / 8, y / 8, z / 8, 93) * 0.4
                    d = min(1.0, max(0.0, d + (q - 0.5) * 0.9))
                elif vol == 1 and fine > 0 and d > 0.0 and d < 0.999 and t < 260:
                    d *= 0.8 + 0.4 * vnoise(x / 2.0, y / 2.0, z / 2.0, 77)
                step = skip if skip > 0 else max(h * 0.5, t * 0.003)
                if vol == 2 and skip == 0:
                    step = max(4.0, t * 0.003)
                if d > 0.003:
                    if vol == 1:
                        ts = tri(ns, vx, vy, vz); ta = tri(nk, vx, vy, vz)
                    else:
                        ts = tri(fs, vx, vy, vz); ta = tri(fk, vx, vy, vz)
                    ts = ts * ts * TAUMAX; ta = ta * ta * TAUMAX
                    sig = d * SIG
                    # multiple scattering, Wrenninge-style octaves
                    ms = math.exp(-ts) * ph0 + 0.55 * math.exp(-ts * 0.3) * ph1 + 0.3 * math.exp(-ts * 0.1) * ph2
                    powder = 1 - 0.7 * math.exp(-sig * 30)
                    depth = ZTOP + 200 - z
                    a = math.exp(-sig * step)
                    for ch in range(3):
                        g = gas(depth / SUN[2], ch)
                        ga = gas(depth, ch)
                        S = sunC[ch] * g * ms * 5.0 * powder + amb[ch] * ga * (math.exp(-ta) * 0.9 + 0.05)
                        if ch == 0:
                            L0 += T0 * S * (1 - a); T0 *= a
                        elif ch == 1:
                            L1 += T1 * S * (1 - a); T1 *= a
                        else:
                            L2 += T2 * S * (1 - a); T2 *= a
                    if T0 < 0.003 and T1 < 0.003 and T2 < 0.003:
                        break
                else:
                    # air: lit by the Sun where the cloud doesn't shade it (beams down the shaft)
                    if vol == 1:
                        ts = tri(ns, vx, vy, vz)
                    else:
                        ts = tri(fs, vx, vy, vz)
                    ts = ts * ts * TAUMAX
                    sa = air_sig(z) * step
                    a = math.exp(-sa)
                    for ch in range(3):
                        g = gas((ZTOP + 200 - z) / SUN[2], ch)
                        c = sunC[ch] * g * pha * 2.2 * math.exp(-ts) + amb[ch] * gas(ZTOP + 200 - z, ch) * 0.25
                        if ch == 0:
                            L0 += T0 * c * (1 - a); T0 *= a
                        elif ch == 1:
                            L1 += T1 * c * (1 - a); T1 *= a
                        else:
                            L2 += T2 * c * (1 - a); T2 *= a
                t += step
            # what's behind
            zz = cam[2] + dz * t
            for ch in range(3):
                if ended == 1:
                    bg = sky_col(dx, dy, dz, ch, 1.0)
                else:
                    bg = (0.003, 0.012, 0.05)[ch] * gas(ZTOP - zz, ch) * 2.5
                if ch == 0:
                    L0 += T0 * bg
                elif ch == 1:
                    L1 += T1 * bg
                else:
                    L2 += T2 * bg
            img[py, px, 0] = L0 * expo; img[py, px, 1] = L1 * expo; img[py, px, 2] = L2 * expo


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


def lerp(a, b, k):
    return a + (b - a) * k


def cam_at(t):
    # test: 0–4 s high above the deck, looking out at the sea of clouds and the cirrus, then tipping down into the shaft
    # and diving in; 4–10 s falling down the shaft
    mx, my, _ = shaft(ZTOP - 300)
    T1 = 4.5
    if t < T1:
        k = t / T1
        e = smooth(k)
        pos = np.array([lerp(-900, mx - 60, e), lerp(-1100, my - 40, e), lerp(ZTOP + 1300, ZTOP + 250, k ** 1.6)])
        far = np.array([pos[0] + 3000, pos[1] + 3600, ZTOP + 600])
        dn = np.array([mx, my, ZTOP - 900])
        w = smooth((k - 0.15) / 0.85)
        tgt = far * (1 - w) + dn * w
        f, r, u = look(pos, tgt, roll=0.1 * e)
        return pos, f, r, u
    k = t - T1
    z0 = ZTOP + 250
    z = z0 - 110 * k - 6 * k * k
    sx, sy, _ = shaft(z)
    bl = smooth(k / 1.2)
    pos = np.array([lerp(mx - 60, sx, bl), lerp(my - 40, sy, bl), z])
    tx, ty, _ = shaft(z - 700)
    tgt = np.array([tx + 80 * math.sin(k * 0.5), ty, z - 700])
    f, r, u = look(pos, tgt, roll=0.1 + 0.1 * k)
    return pos, f, r, u


def load():
    out = []
    for nm in ('near', 'far'):
        for n in ('den', 'sun', 'sky', 'dist'):
            out.append(np.load(os.path.join(WORK, f'{nm}_{n}.npy')))
    return out


def frame(vols, t, W=720, Hh=1280, seed=0):
    pos, f, r, u = cam_at(t)
    img = np.zeros((Hh, W, 3), np.float64)
    render(*vols, img, pos, f, r, u, math.radians(66), 1.0, seed, 1)
    return tonemap(img)


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'build':
        build(sys.argv[2] if len(sys.argv) > 2 else 'near,far')
    else:
        from PIL import Image
        vols = load()
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
