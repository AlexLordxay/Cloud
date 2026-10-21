# The Earth 66 million years ago, for "Що сталося з Землею, коли вимерли динозаври": its maps, made from the PALEOMAP
# PaleoDEM for the Cretaceous–Paleogene boundary (Scotese & Wright 2018, 6′ grid, CC BY 4.0; zenodo.org/records/5460860),
# with finer relief and coastlines added by noise below the grid's 11 km.
#   work/chicxulub/maps/color.jpg   8192×4096: forests, savanna and deserts by the climate belts of a warm, ice-free
#                                   world (dry near 25° and far from the sea), mountains bare, seas by depth
#   work/chicxulub/maps/relief.png  8192×4096: the land's slopes east and north (R, G; 128 = flat), for the shading
#   work/chicxulub/maps/sea.png     4096×2048: 1 over water (the glint)
#   work/chicxulub/maps/clouds.jpg  8192×4096: real weather — NASA's Blue Marble cloud map (Visible Earth, NASA
#                                   Goddard) — with the ice it also shows (Antarctica, Greenland, the Arctic pack, Tibet's
#                                   snow: none of it there in an ice-free world) faded into clouds drawn on the sphere
#                                   (domain-warped noise, cover by latitude: equatorial towers, clear subtropics, storm belts)
#
#   python3 scenes/chicxulub/maps.py          (fetches the DEM from Zenodo and the clouds from NASA the first time)
#   python3 scenes/chicxulub/maps.py clouds   (only the clouds again)
import os, sys, subprocess, numpy as np, h5py
from PIL import Image
from scipy import ndimage

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
WORK = os.path.join(TOOLS, 'work', 'chicxulub'); DL = os.path.join(WORK, 'dl'); OUT = os.path.join(WORK, 'maps')
CLOUDS = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57747/cloud_combined_8192.tif'
ZIP = 'https://zenodo.org/api/records/5460860/files/Scotese_Wright_2018_Maps_1-88_6minX6min_PaleoDEMS_nc.zip/content'
W, H = 8192, 4096


def fetch():
    nc = os.path.join(DL, 'kt65.nc')
    if not os.path.exists(nc):
        os.makedirs(DL, exist_ok=True); z = os.path.join(DL, 'dem6.zip')
        subprocess.run(['curl', '-sSL', '-C', '-', '-o', z, ZIP], check=True)
        subprocess.run(['unzip', '-o', '-j', '-d', DL, z, '*Map16_PALEOMAP_6min_KT_Boundary_65Ma.nc'], check=True)
        os.rename([os.path.join(DL, f) for f in os.listdir(DL) if f.startswith('Map16')][0], nc)
    return h5py.File(nc, 'r')['z'][...][:, :-1].astype(np.float32)       # north is the first row; the repeated 180° column off


# Chicxulub on this map (palaeo-coordinates): the crater Scotese drew in at the boundary is taken out, since our Earth
# is the one just before the impact, and the north of Yucatán is put under the shallow sea of its carbonate platform
# (the asteroid struck water some tens to a couple of hundred metres deep). Also closed: a narrow double channel the
# grid draws across southern Mexico, which reads as a scratch from space.
CHX = (24.95, -71.9)


def before_impact(z):
    la = 90 - np.arange(z.shape[0])[:, None] * 0.1; lo = -180 + np.arange(z.shape[1])[None, :] * 0.1
    dx = (lo - CHX[1]) * np.cos(np.radians(CHX[0])); dy = la - CHX[0]; r = np.hypot(dx, dy)
    ann = (r > 1.3) & (r < 1.7)
    z = np.where(r < 1.3, np.median(z[ann]), z)
    z = ndimage.gaussian_filter(z, 1.0) * (r < 2.2) + z * (r >= 2.2)
    r2 = np.hypot(dx, la - CHX[0] - 0.8)
    z = z - 150 * np.clip((3.4 - r2) / 1.8, 0, 1) ** 1.5 * (z > -400)
    box = (lo > -95) & (lo < -74) & (la > 15) & (la < 27)
    land = z > 0
    shut = ndimage.binary_closing(land, structure=ndimage.generate_binary_structure(2, 1), iterations=5) & ~land & box
    return np.where(shut, 120.0, z).astype(np.float32)


def hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = h.astype(np.uint32); h ^= h >> 13; h *= np.uint32(0x5bd1e995); h ^= h >> 15
    return h.astype(np.float32) / 4294967296.0


def vnoise(P, f, seed):
    X = P * f; i = np.floor(X); t = X - i; i = i.astype(np.int64); u = t * t * (3 - 2 * t)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[..., 0] if dx else 1 - u[..., 0]) * (u[..., 1] if dy else 1 - u[..., 1]) * (u[..., 2] if dz else 1 - u[..., 2])
                out = out + w * hash3(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out * 2 - 1


def fbm(P, f, octaves, seed, gain=0.5):
    s, a, n = 0, 1.0, 0
    for o in range(octaves): s = s + a * vnoise(P, f * 2 ** o, seed + o); n += a; a *= gain
    return s / n


def sphere(w, h, rows=None):
    lat = (0.5 - (np.arange(h) + 0.5) / h) * np.pi if rows is None else rows
    lon = ((np.arange(w) + 0.5) / w - 0.5) * 2 * np.pi
    la, lo = np.meshgrid(lat, lon, indexing='ij')
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], -1).astype(np.float32), la


def field(w, h, fn, chunk=256):
    out = np.empty((h, w), np.float32); lat = (0.5 - (np.arange(h) + 0.5) / h) * np.pi
    for r in range(0, h, chunk):
        P, la = sphere(w, h, lat[r:r + chunk]); out[r:r + chunk] = fn(P, la)
    return out


def up(a, w, h, order=3):
    hh, ww = a.shape
    y = (np.arange(h) + 0.5) * hh / h - 0.5; x = (np.arange(w) + 0.5) * ww / w - 0.5
    Y, X = np.meshgrid(y, x, indexing='ij')
    return ndimage.map_coordinates(a, [np.clip(Y, 0, hh - 1), X % ww], order=order, mode='grid-wrap').astype(np.float32)


def ramp(x, xs, cols):
    return np.stack([np.interp(x, xs, [c[k] for c in cols]) for k in range(3)], -1)


def paint(z0, W, H, ice=0.0):
    """A DEM (6′ grid, metres) as the map's colour (sRGB 0–255), the land's slopes (relief.png's R, G) and the land.
    ice: how far toward the equator, in degrees from the south pole, an Antarctic ice sheet reaches (0: none)."""
    # the grid's 40 m steps and 11 km cells smoothed, then finer relief: rough in the mountains, enough at sea level
    # to break the coasts into bays and capes
    z = up(ndimage.gaussian_filter(z0, 0.8, mode='wrap'), W, H)
    zb = z.copy()
    det = field(W, H, lambda P, la: fbm(P, 24, 7, 11, 0.55))
    rough = np.clip(np.abs(z) / 1200, 0, 1)
    z = z + det * (28 + 900 * rough * (z > 0) + 250 * (z < 0) * np.clip((-z - 300) / 600, 0, 1))
    land = z > 0
    lat = np.degrees(sphere(1, H)[1][:, :1]) * np.ones((1, W), np.float32)
    alat = np.abs(lat)

    # moisture: a dry belt about 25° either side of the equator, drier far inland, wetter up the windward slopes
    small = land[::4, ::4]
    dist = ndimage.distance_transform_edt(small) * (40075 / (W / 4))          # km (east–west stretch near the poles ignored)
    dist = up(dist.astype(np.float32), W, H, order=1)
    belt = 1 - 0.62 * np.exp(-((alat - 24) / 10) ** 2) - 0.12 * np.exp(-((alat - 90) / 25) ** 2)
    moist = belt * (0.42 + 0.58 * np.exp(-dist / 1100)) + 0.22 * field(W, H, lambda P, la: fbm(P, 6, 6, 21))
    moist += 0.1 * np.clip(z / 1500, 0, 1)
    # valleys gather water: greener where the land sits below its surroundings (draws out the drainage)
    moist += np.clip((ndimage.uniform_filter(zb, 41, mode='wrap') - zb) / 300, -0.08, 0.15) * (z > 0)
    # land colours (sRGB, as satellites see them): wet forest, savanna, steppe, sand
    cl = ramp(moist, [0.12, 0.28, 0.40, 0.52, 0.66, 0.85],
              [(206, 178, 128), (184, 150, 102), (140, 124, 78), (98, 98, 52), (44, 66, 28), (26, 46, 20)])
    cl = cl * (1 + 0.10 * field(W, H, lambda P, la: fbm(P, 40, 6, 31)))[..., None]
    # patches of a yellower and a deeper green at a few hundred km, so the forests are not one even carpet
    hue = field(W, H, lambda P, la: fbm(P, 14, 5, 35))[..., None] * (moist > 0.45)[..., None]
    cl = cl + hue * np.array([18, 10, -6])
    # high latitudes: darker conifer-like forest, a little bluer
    hi = np.clip((alat - 50) / 20, 0, 1)[..., None] * (moist > 0.5)[..., None]
    cl = cl * (1 - 0.25 * hi) + np.array([22, 40, 30]) * 0.25 * hi
    # mountains: bare rock where high and steep
    gy, gx = np.gradient(z, 4.89e3 * 8192 / W)                                  # m per m (≈4.9 km cells at 8192)
    gx = gx / np.maximum(np.cos(np.radians(lat)), 0.05)
    slope = np.hypot(gx, gy)
    rock = np.clip((z - 1300) / 1500, 0, 1) * 0.6 + np.clip(slope / 0.08, 0, 1) * 0.5
    rock = np.clip(rock, 0, 0.85)[..., None]
    cl = cl * (1 - rock) + np.array([118, 104, 88]) * rock
    # the Antarctic ice sheet (from ~34 million years ago): white, a little blue, over the land near the pole
    if ice > 0:
        sheet = np.clip((-90 + ice - lat) / 4, 0, 1)[..., None] * (z > 0)[..., None]
        cl = cl * (1 - sheet) + np.array([226, 232, 238]) * sheet
    # seas: shelves of the warm shallow seas, darker with depth
    d = -z
    cs = ramp(d, [0, 25, 70, 160, 400, 1500, 4000],
              [(52, 118, 128), (38, 98, 120), (26, 76, 108), (18, 58, 94), (12, 42, 80), (8, 28, 62), (6, 20, 50)])
    cs = cs * (1 + 0.05 * field(W, H, lambda P, la: fbm(P, 10, 5, 41)))[..., None]
    # the coast: a slightly lighter, sandier edge of shallow water
    col = np.where(land[..., None], cl, cs)

    # relief: slopes of the land only (the sea stays smooth for the glint), scaled ×5 into 0…255
    zl = np.maximum(z, 0)
    gy, gx = np.gradient(zl, 4.89e3 * 8192 / W)
    gx = gx / np.maximum(np.cos(np.radians(lat)), 0.05)
    rel = np.stack([np.clip(128 + gx * 5 * 127, 0, 255), np.clip(128 - gy * 5 * 127, 0, 255), np.full_like(gx, 128)], -1)
    return col, rel, land


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    only_clouds = sys.argv[1:] == ['clouds']
    if not only_clouds:
        col, rel, land = paint(before_impact(fetch()), W, H)
        Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'color.jpg'), quality=92)
        Image.fromarray(rel.astype(np.uint8)).save(os.path.join(OUT, 'relief.png'))
        Image.fromarray((~land[::2, ::2] * 255).astype(np.uint8)).save(os.path.join(OUT, 'sea.png'))

    def clouds(P, la):
        a = np.degrees(np.abs(la))
        # zonal shear: each latitude turned about the axis by its own angle, so the swirls are drawn out east–west
        q = np.stack([fbm(P, 2.0, 4, 51 + k) for k in range(3)], -1)
        ph = 0.35 * np.sin(3 * la) + 0.5 * q[..., 0]
        c, s_ = np.cos(ph), np.sin(ph)
        R = np.stack([P[..., 0] * c - P[..., 1] * s_, P[..., 0] * s_ + P[..., 1] * c, P[..., 2]], -1)
        n = fbm(R + 0.45 * q, 3.5, 9, 61, 0.56)
        cover = 0.30 * np.exp(-(a / 8) ** 2) + 0.05 + 0.30 * np.exp(-((a - 55) / 13) ** 2) - 0.12 * np.exp(-((a - 24) / 9) ** 2)
        x = n + cover
        c = np.clip((x - 0.04) / 0.30, 0, 1) ** 1.3                   # thin edges, thick bright cores
        billow = 1 - np.abs(fbm(R, 16, 5, 67))                          # cauliflower tops
        c = c * (0.5 + 0.5 * billow ** 2)
        # fair-weather cumulus: fine specks over the subtropics and the tropics
        sp = np.clip((fbm(P, 90, 3, 73) - 0.30) / 0.3, 0, 1) * np.exp(-((a - 18) / 14) ** 2) * 0.22
        sp = sp * np.clip(fbm(P, 9, 3, 79) * 2.5 + 0.2, 0, 1)                 # in fields, not everywhere
        return np.clip(np.maximum(c, sp), 0, 1)
    tif = os.path.join(WORK, 'nasa', 'cloud_combined_8192.tif')
    if not os.path.exists(tif):
        os.makedirs(os.path.dirname(tif), exist_ok=True)
        subprocess.run(['curl', '-sS', '-C', '-', '-o', tif, CLOUDS], check=True)
    Image.MAX_IMAGE_PIXELS = None
    nasa = np.asarray(Image.open(tif).convert('L')).astype(np.float32) / 255
    nasa = np.clip((nasa - 0.04) / 0.9, 0, 1)
    la = np.degrees(sphere(1, H)[1][:, :1]); lo = ((np.arange(W) + 0.5) / W - 0.5)[None, :] * 360
    blob = lambda a, o, ra, ro: np.clip(1.6 - 1.6 * np.hypot((la - a) / ra, (lo - o) / ro), 0, 1) ** 1.5
    # the polar ice gives way to drawn clouds; Greenland's sheet and Tibet's snow simply to clear sky
    ice = np.clip(np.clip((-58 - la) / 9, 0, 1) + np.clip((la - 71) / 7, 0, 1), 0, 1)
    snow = np.clip(blob(73, -41, 15, 26) + 0.6 * blob(33, 87, 9, 18), 0, 1)
    proc = up(field(2048, 1024, clouds), W, H, order=1)
    cld = (nasa * (1 - snow)) * (1 - ice) + proc * ice
    Image.fromarray((cld * 255).astype(np.uint8)).save(os.path.join(OUT, 'clouds.jpg'), quality=93)
    print('clouds', cld.mean())
