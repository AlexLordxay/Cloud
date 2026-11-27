# «А ти уявляєш Титан так?» — the two landscapes as height fields (metres, 2048 × 2048 over 40 × 40 km, x east, y north)
# -> work/titan_imagine/{coast,dunes}_{z,a}.npy
#   coast: hills cut by branching river valleys that run south into a methane sea; near the shore the valleys are
#          drowned into long inlets; methane rivers run along the valley floors (WL: liquid level, -1000 = none) — like Vid Flumina flowing into Ligeia Mare (Cassini radar). The sea is below z = 0.
#   dunes: long parallel linear dunes running east–west, ~2.2 km apart and ~90 m tall, dark organic sand between brighter
#          interdune flats, with the Y-junctions the Cassini radar shows in Shangri-La and Belet.
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
WK = os.path.join(HERE, '..', '..', 'work', 'titan_imagine'); os.makedirs(WK, exist_ok=True)
N, HALF = 2048, 20000.0
cell = 2 * HALF / (N - 1)
xs = np.linspace(-HALF, HALF, N); X, Y = np.meshgrid(xs, xs)   # Z[j, i]: y = xs[j], x = xs[i]

def noise(scale_m, seed, ani=(1.0, 1.0)):
    # smooth noise ~N(0,1) with features about scale_m across (ani stretches x, y)
    rng = np.random.default_rng(seed)
    nx = max(4, int(2 * HALF / (scale_m * ani[0]))); ny = max(4, int(2 * HALF / (scale_m * ani[1])))
    r = gaussian_filter(rng.standard_normal((ny + 4, nx + 4)), 1.0)
    r = (r - r.mean()) / r.std()
    im = Image.fromarray(r.astype(np.float32)).resize((N + int(4 * N / nx), N + int(4 * N / ny)), Image.BICUBIC)
    a = np.asarray(im)[int(2 * N / ny):int(2 * N / ny) + N, int(2 * N / nx):int(2 * N / nx) + N]
    return a / max(a.std(), 1e-6)

def fbm(scale_m, seed, octaves=5, gain=0.5):
    s = 0.0; a = 1.0; tot = 0.0
    for o in range(octaves):
        s = s + a * noise(scale_m / 2 ** o, seed + 17 * o); tot += a; a *= gain
    return s / tot

def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def coast():
    # the shore wanders around y ≈ 0; land rises to the north
    cw = 2600 * noise(9000, 1) + 900 * noise(2500, 2)
    yy = Y + cw
    land = ss(-3000, 9000, yy)
    base = -70 + 330 * land
    hills = 190 * fbm(3500, 3, 6) * (0.25 + 0.75 * land)
    h = base + hills
    # main valleys run north–south (stretched noise), warped so they meander; tributaries join them
    wx = 900 * noise(3000, 4) + 250 * noise(800, 8); wy = 700 * noise(3000, 5)
    vmain = np.abs(noise_at(X + wx, Y + wy, 1700, 6000, 6))
    trib = np.abs(noise_at(X + 0.7 * wx + 120 * noise(500, 9), Y + 0.6 * wy, 600, 1400, 7))
    F = -30 + 200 * ss(-2000, 17000, Y + 0.3 * cw)                 # the valley floor, falling toward the sea
    hv = F + 260 * (1 - np.exp(-(vmain / 0.30) ** 2)) + 30 * (1 - np.exp(-(vmain / 0.06) ** 2))
    ht = F + 18 + 150 * (1 - np.exp(-(trib / 0.25) ** 2)) + 12 * (1 - np.exp(-(trib / 0.06) ** 2)) + 120 * np.exp(-(vmain / 0.3) ** 2) * 0
    h = smin(h, hv, 35.0)
    h = smin(h, np.where(vmain > 0.15, ht, 1e4), 25.0)
    # the sea floor
    h = np.where(h < 0, h * 0.8 - 6, h)
    h = gaussian_filter(h, 0.7)
    # the liquid: the sea at 0, the rivers 3 m above their channel floors
    # (the level is set over the whole valley; the liquid shows only where the ground dips below it: the channel)
    wl = np.zeros_like(h)
    wl = np.where((vmain < 0.3) & (F > -5), np.maximum(wl, F + 3.0), wl)
    wl = np.where((trib < 0.3) & (vmain > 0.15) & (F > -5), np.maximum(wl, F + 20.0), wl)
    # albedo: brighter highlands (water-ice bedrock with organics), dark river floors and plains
    a = 0.40 + 0.10 * fbm(1200, 11, 4) + 0.10 * ss(40, 260, h - F) - 0.12 * np.exp(-(vmain / 0.12) ** 2)
    a = np.clip(a, 0.18, 0.62)
    return h.astype(np.float32), a.astype(np.float32), wl.astype(np.float32)

def noise_at(x, y, sx, sy, seed):
    # anisotropic noise sampled at warped coordinates (bilinear from a coarse grid)
    rng = np.random.default_rng(seed)
    gx = int(2 * HALF / sx) + 8; gy = int(2 * HALF / sy) + 8
    g = gaussian_filter(rng.standard_normal((gy, gx)), 0.8); g = (g - g.mean()) / g.std()
    fx = (x + HALF) / sx + 2; fy = (y + HALF) / sy + 2
    fx = np.clip(fx, 0, gx - 1.001); fy = np.clip(fy, 0, gy - 1.001)
    i = fx.astype(int); j = fy.astype(int); tx = fx - i; ty = fy - j
    tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty)
    v = (g[j, i] * (1 - tx) + g[j, i + 1] * tx) * (1 - ty) + (g[j + 1, i] * (1 - tx) + g[j + 1, i + 1] * tx) * ty
    return v / 1.0

def dunes():
    lam = 1800.0
    yy = Y + 420 * noise(7000, 21) + 140 * noise(1800, 22)
    r = (yy / lam) % 1.0
    p = 1 - np.abs(2 * r - 1)
    # dune crests are sharp, the flanks concave
    prof = np.clip((p - 0.30) / 0.70, 0, 1) ** 1.25            # near-triangular dunes, flat interdune corridors
    # height varies along the dune; some dunes die out (where the interdune gaps join: Y-junctions)
    amp = 140 * ss(-1.3, 0.4, noise(5000, 23, (1.0, 0.35)))
    # a second, offset set of dunes merging into the first in places
    r2 = ((yy + lam * 0.5) / lam) % 1.0
    p2 = (1 - np.abs(2 * r2 - 1)) ** 1.6
    amp2 = 110 * ss(0.8, 1.8, noise(6000, 24, (1.0, 0.35)))
    h = np.maximum(amp * prof, amp2 * p2)
    # wind ripples and a gently rolling floor
    h = h + 6 * fbm(4000, 25, 3) + 1.2 * noise(260, 26)
    h = h + 25.0                     # all above the (absent) sea
    sand = np.clip(np.maximum(amp / 140 * p, amp2 / 110 * (1 - np.abs(2 * r2 - 1))) * 2.2 - 0.45, 0, 1)   # the dark sand covers the whole dune body
    a = 0.52 + 0.05 * fbm(1500, 27, 3)          # the bright interdune (gravel, ice)
    a = a * (1 - sand) + (0.13 + 0.025 * noise(800, 28)) * sand
    return gaussian_filter(h, 0.6).astype(np.float32), np.clip(a, 0.12, 0.65).astype(np.float32), np.full((N, N), -1000.0, np.float32)

if __name__ == '__main__':
    for name, fn in (('coast', coast), ('dunes', dunes)):
        h, a, wl = fn()
        np.save(os.path.join(WK, f'{name}_z.npy'), h); np.save(os.path.join(WK, f'{name}_a.npy'), a); np.save(os.path.join(WK, f'{name}_w.npy'), wl)
        v = (np.clip((h - h.min()) / (h.max() - h.min()), 0, 1) * 255).astype(np.uint8)
        im = np.stack([v, v, v], -1); im[wl > h] = (20, 40, 90)
        Image.fromarray(im).resize((512, 512)).save(os.path.join(WK, f'{name}_map.jpg'))
        print(name, float(h.min()), float(h.max()), 'sea fraction', float((h < 0).mean()))
