# The impact region in detail, for the close shots (the global map is ~5 km a pixel): 24° × 32° round Chicxulub on the
# map of 66 million years ago, 4096 × 4096 (~0.7 km a pixel). Same ground as maps.py — the same DEM, the same noise
# (its octaves carried on finer), the same colours — so it melts into the global map at its edges; with what only shows
# close up: coasts broken at sub-km, greener hollows, beaches and mangrove fringes, and the carbonate
# platform's shallows (sand banks bright turquoise, deepening to blue).
#   work/chicxulub/maps/patch_color.jpg   colour
#   work/chicxulub/maps/patch_rel.png     slopes east (R) and north (G) of the land, 128 = flat; water (B)
#
#   python3 scenes/chicxulub/patch.py        (after maps.py; BOX is also in world.js)
import os, sys, numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps import fetch, before_impact, fbm, vnoise, sphere, field, up, ramp, OUT, W, H

BOX = (13.0, 37.0, -88.0, -56.0)                  # lat south, north, lon west, east (degrees)
N = 4096


def grid(rows):
    lat = np.radians(BOX[1] - (rows + 0.5) / N * (BOX[1] - BOX[0]))
    lon = np.radians(BOX[2] + (np.arange(N) + 0.5) / N * (BOX[3] - BOX[2]))
    la, lo = np.meshgrid(lat, lon, indexing='ij')
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1).astype(np.float32), la, lo


def pfield(fn, chunk=256):
    out = np.empty((N, N), np.float32)
    for r in range(0, N, chunk):
        P, la, lo = grid(np.arange(r, min(r + chunk, N))); out[r:r + chunk] = fn(P, la)
    return out


def finer(P, f, o0, o1, seed, gain):
    # octaves o0…o1-1 of fbm(P, f, o0, seed, gain), on the same scale as its first o0 (so they add on)
    n = sum(gain ** o for o in range(o0))
    return sum(gain ** o * vnoise(P, f * 2 ** o, seed + o) for o in range(o0, o1)) / n


def sample(a, lat, lon, order=3):
    # a global grid a (north row first, from lon −180), at the places (lat, lon) in degrees, as maps.up() reads it
    hh, ww = a.shape
    y = (90 - lat) * hh / 180 - 0.5; x = (lon + 180) * ww / 360 - 0.5
    return ndimage.map_coordinates(a, [np.clip(y, 0, hh - 1), x % ww], order=order, mode='grid-wrap').astype(np.float32)


if __name__ == '__main__':
    lat = BOX[1] - (np.arange(N) + 0.5) / N * (BOX[1] - BOX[0]); lon = BOX[2] + (np.arange(N) + 0.5) / N * (BOX[3] - BOX[2])
    LA, LO = np.meshgrid(lat, lon, indexing='ij'); alat = np.abs(LA)
    z0s = ndimage.gaussian_filter(before_impact(fetch()), 0.8, mode='wrap')
    zb = sample(z0s, LA, LO)
    # the global relief noise, then three octaves more (down to ~0.4 km)
    det = pfield(lambda P, la: fbm(P, 24, 7, 11, 0.55) + finer(P, 24, 7, 10, 11, 0.55))
    rough = np.clip(np.abs(zb) / 1200, 0, 1)
    z = zb + det * (28 + 900 * rough * (zb > 0) + 250 * (zb < 0) * np.clip((-zb - 300) / 600, 0, 1))
    # the platform's shallows: banks and channels a few metres to tens of metres deep
    sh = np.clip(1 - (-z) / 120, 0, 1) * (z < 0)
    z = z + sh * 22 * pfield(lambda P, la: fbm(P, 380, 6, 131, 0.6))
    land = z > 0

    # distance from the sea, from the global map at a quarter of its size (as maps.py does)
    zl = up(z0s, W // 4, H // 4) ; dl = field(W // 4, H // 4, lambda P, la: fbm(P, 24, 7, 11, 0.55))
    rl = np.clip(np.abs(zl) / 1200, 0, 1)
    zl = zl + dl * (28 + 900 * rl * (zl > 0) + 250 * (zl < 0) * np.clip((-zl - 300) / 600, 0, 1))
    dist = ndimage.distance_transform_edt(zl > 0) * (40075 / (W / 4))
    dist = sample(dist.astype(np.float32), LA, LO, order=1)
    belt = 1 - 0.62 * np.exp(-((alat - 24) / 10) ** 2) - 0.12 * np.exp(-((alat - 90) / 25) ** 2)
    moist = belt * (0.42 + 0.58 * np.exp(-dist / 1100)) + 0.22 * pfield(lambda P, la: fbm(P, 6, 6, 21))
    moist += 0.1 * np.clip(z / 1500, 0, 1)
    moist += np.clip((ndimage.uniform_filter(zb, 287, mode='nearest') - zb) / 300, -0.08, 0.15) * land
    # finer valleys than the DEM has: the noise relief's own hollows, a little greener
    moist += np.clip((ndimage.uniform_filter(z, 31, mode='nearest') - z) / 120, -0.05, 0.12) * land
    cl = ramp(moist, [0.12, 0.28, 0.40, 0.52, 0.66, 0.85],
              [(206, 178, 128), (184, 150, 102), (140, 124, 78), (98, 98, 52), (44, 66, 28), (26, 46, 20)])
    cl = cl * (1 + 0.10 * pfield(lambda P, la: fbm(P, 40, 6, 31)) + 0.10 * pfield(lambda P, la: fbm(P, 320, 5, 115))
               + 0.10 * pfield(lambda P, la: fbm(P, 2600, 4, 111)))[..., None]
    hue = pfield(lambda P, la: fbm(P, 14, 5, 35))[..., None] * (moist > 0.45)[..., None]
    cl = cl + hue * np.array([18, 10, -6])
    # the dry land up close: rock and soil of different colours (reddish, grey), scrub in dark specks, and on the low
    # flats by the sea white salt crusts (sabkha — the same arid coasts that laid down Yucatán's gypsum and anhydrite)
    dry = np.clip((0.42 - moist) / 0.15, 0, 1)[..., None]
    tone = pfield(lambda P, la: fbm(P, 90, 5, 141))[..., None]
    cl = cl + dry * (np.clip(tone, 0, 1) * np.array([30, -6, -26]) + np.clip(-tone, 0, 1) * np.array([-24, -12, 8]) * 1.4)
    mott = pfield(lambda P, la: fbm(P, 700, 5, 151))[..., None]
    cl = cl * (1 + 0.16 * mott * (0.4 + 0.6 * dry))
    scrub = np.clip((pfield(lambda P, la: fbm(P, 1800, 4, 161)) - 0.12) / 0.2, 0, 1)[..., None] * dry * 0.45
    cl = cl * (1 - scrub) + np.array([92, 88, 58]) * scrub
    salt = (np.clip(1 - z / 18, 0, 1) * land)[..., None] * dry * np.clip(pfield(lambda P, la: fbm(P, 240, 5, 171)) * 3 + 0.5, 0, 1)[..., None]
    cl = cl * (1 - 0.7 * salt) + np.array([228, 224, 212]) * 0.7 * salt
    # mountains bare; the shore: mangrove and marsh where wet and low, a thin pale beach
    dy = (BOX[1] - BOX[0]) / N * 111320; dx = (BOX[3] - BOX[2]) / N * 111320 * np.cos(np.radians(LA))
    gy, gx = np.gradient(z, dy, axis=0), np.gradient(z, axis=1) / dx
    slope = np.hypot(gx, gy)
    rock = np.clip(np.clip((z - 1300) / 1500, 0, 1) * 0.6 + np.clip(slope / 0.1, 0, 1) * 0.5, 0, 0.85)[..., None]
    cl = cl * (1 - rock) + np.array([118, 104, 88]) * rock
    mang = (np.clip(1 - z / 14, 0, 1) * land * np.clip((moist - 0.35) / 0.15, 0, 1))[..., None] * 0.55
    cl = cl * (1 - mang) + np.array([30, 48, 26]) * mang
    beach = (np.clip(1 - z / 3.5, 0, 1) * land)[..., None] * 0.6
    cl = cl * (1 - beach) + np.array([214, 200, 168]) * beach
    # the sea: the global colours below ~45 m; above, the shallows of a carbonate bank
    d = -z
    cs = ramp(d, [0, 5, 16, 45, 90, 160, 400, 1500, 4000],
              [(176, 214, 196), (120, 196, 192), (66, 160, 172), (40, 114, 136), (28, 84, 114), (18, 60, 94), (12, 42, 80), (8, 28, 62), (6, 20, 50)])
    cs = cs * (1 + 0.05 * pfield(lambda P, la: fbm(P, 10, 5, 41)))[..., None]
    col = np.where(land[..., None], cl, cs)
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'patch_color.jpg'), quality=92)

    gy, gx = np.gradient(np.maximum(z, 0), dy, axis=0), np.gradient(np.maximum(z, 0), axis=1) / dx
    rel = np.stack([np.clip(128 + gx * 5 * 127, 0, 255), np.clip(128 - gy * 5 * 127, 0, 255), (~land) * 255.0], -1)
    Image.fromarray(rel.astype(np.uint8)).save(os.path.join(OUT, 'patch_rel.png'))
    print('land', land.mean())
