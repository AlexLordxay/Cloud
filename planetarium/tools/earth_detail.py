# Builds the detailed Earth: a pyramid of map chunks the site streams in as the camera nears the surface.
#
#   python3 earth_detail.py <day tiles> <day zoom-8 tiles> <night tiles> [parts]   ->  ../textures/earth/
#
#   day tiles         …/@freetiler/nasa-bluemarble/tiles (npm, zooms 0–7)
#   day zoom-8 tiles  …/tiles of github.com/freetiler/nasa-bluemarble (zoom 8 is only on GitHub)
#   night tiles       …/@freetiler/nasa-blackmarble/tiles (npm, zooms 0–7)
#   parts             any of 123 4 n (default: all), to rebuild only some levels
#
# Sources: NASA Blue Marble (shaded relief and bathymetry) and NASA Black Marble (city lights), web-mercator tiles
# z/x/y.jpeg, 256 px (NASA open data, cut by freetiler). Zoom 7 is ~1.2 km per pixel at the equator, zoom 8 ~600 m.
# Output: the site's own layout, plate carrée like earth_day.jpg, in 2048 px chunks named <level>/<x>_<y>.jpg
# (x from 180° W eastwards, y from the north pole down):
#   level 1   8192 × 4096   4 × 2 chunks    ~4.9 km per pixel
#   level 2  16384 × 8192   8 × 4 chunks    ~2.4 km
#   level 3  32768 × 16384 16 × 8 chunks    ~1.2 km
#   level 4  65536 × 32768 32 × 16 chunks   ~600 m, only chunks with land (open ocean stays on level 3)
#   n3       city lights on the level-3 grid
# Land colours are matched to earth_day.jpg (per-channel mean and spread over land), so switching maps is seamless.
# Water is flattened to the base map's ocean tone: the source shows the sea floor (shelves, trenches), which reads as
# fog from orbit; the site also finds water by that tone, for the Sun's glint. City lights are matched to
# earth_night.jpg the same way. Beyond the mercator limit (±85.05°) the polar caps come from the base maps.
import math, os, sys
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'textures')
OUT = os.path.join(TEX, 'earth')
DAY, DAY8, NIGHT = sys.argv[1:4]
PARTS = sys.argv[4] if len(sys.argv) > 4 else '1234n'
CH = 2048                               # chunk size
LEVELS = {1: (4, 2), 2: (8, 4), 3: (16, 8), 4: (32, 16)}
MERC_LIMIT = math.degrees(math.atan(math.sinh(math.pi)))   # 85.0511°

_tiles = {}
def tile(root, z, x, y):
    k = (root, z, x, y)
    if k not in _tiles:
        if len(_tiles) > 4000: _tiles.clear()
        p = os.path.join(root, str(z), str(x % (2 ** z)), f'{y}.jpeg')
        _tiles[k] = np.asarray(Image.open(p).convert('RGB'), dtype=np.float32) if os.path.exists(p) else np.zeros((256, 256, 3), np.float32)
    return _tiles[k]

def merc_sample(root, z, lon, lat):
    """Bilinear sample of a mercator pyramid at zoom z for arrays of lon/lat (deg). Returns float RGB."""
    n = 2 ** z
    lat = np.clip(lat, -MERC_LIMIT + 1e-6, MERC_LIMIT - 1e-6)
    px = (lon + 180.0) / 360.0 * n * 256 - 0.5
    py = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / math.pi) / 2 * n * 256 - 0.5
    py = np.clip(py, 0, n * 256 - 1.001)
    # mosaic of the tiles touched
    tx0, tx1 = int(np.floor(px.min() / 256)) - 1, int(np.floor(px.max() / 256)) + 1
    ty0, ty1 = max(0, int(np.floor(py.min() / 256))), min(n - 1, int(np.floor(py.max() / 256)) + 1)
    mos = np.concatenate([np.concatenate([tile(root, z, tx, ty) for tx in range(tx0, tx1 + 1)], axis=1) for ty in range(ty0, ty1 + 1)], axis=0)
    fx, fy = px - tx0 * 256, py - ty0 * 256
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    ax, ay = (fx - x0)[..., None], (fy - y0)[..., None]
    x0 = np.clip(x0, 0, mos.shape[1] - 2); y0 = np.clip(y0, 0, mos.shape[0] - 2)
    a, b = mos[y0, x0], mos[y0, x0 + 1]
    c, d = mos[y0 + 1, x0], mos[y0 + 1, x0 + 1]
    return (a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay

load = lambda f: np.asarray(Image.open(os.path.join(TEX, f)).convert('RGB'), dtype=np.float32)
base, spec, nbase = load('earth_day.jpg'), load('earth_specular.jpg'), load('earth_night.jpg')
def base_sample(lon, lat, img=None):
    img = base if img is None else img
    H, W = img.shape[:2]
    fx = (lon + 180) / 360 * W - 0.5; fy = (90 - lat) / 180 * H - 0.5
    x0 = np.clip(np.floor(fx).astype(int), 0, W - 2); y0 = np.clip(np.floor(fy).astype(int), 0, H - 2)
    ax, ay = np.clip(fx - x0, 0, 1)[..., None], np.clip(fy - y0, 0, 1)[..., None]
    a, b, c, d = img[y0, x0], img[y0, x0 + 1], img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay

def is_water(rgb):
    return (rgb[..., 2] - np.maximum(rgb[..., 0], rgb[..., 1])) > 6

def moments(src, ref):
    # Mean and spread matched per channel (a least-squares fit would flatten the contrast: the base maps are blurrier).
    return [(ref[:, ch].std() / src[:, ch].std(), ref[:, ch].mean() - ref[:, ch].std() / src[:, ch].std() * src[:, ch].mean()) for ch in range(3)]

# Colour match against the base maps, on a coarse grid (in sRGB).
H0, W0 = 960, 1920
LON, LAT = np.meshgrid(-180 + (np.arange(W0) + 0.5) / W0 * 360, 90 - (np.arange(H0) + 0.5) / H0 * 180)
s5 = merc_sample(DAY, 5, LON, LAT)
land = base_sample(LON, LAT, spec)[..., 0] < 40
m = (np.abs(LAT) < 75) & land & ~is_water(s5)
FIT = moments(s5[m], base_sample(LON, LAT)[m])
sea = (base_sample(LON, LAT, spec)[..., 0] > 220) & (np.abs(LAT) < 60)
OCEAN = np.median(base_sample(LON, LAT)[sea], axis=0)
mn = np.abs(LAT) < 75
NFIT = moments(merc_sample(NIGHT, 5, LON, LAT)[mn], base_sample(LON, LAT, nbase)[mn])
print('ocean tone:', OCEAN.round(1), ' day fit:', [(round(k, 3), round(c, 1)) for k, c in FIT],
      ' night fit:', [(round(k, 3), round(c, 1)) for k, c in NFIT], flush=True)

def grid(level, cx, cy):
    nx, ny = LEVELS[level]
    span_lon, span_lat = 360 / nx, 180 / ny
    lon = -180 + cx * span_lon + (np.arange(CH) + 0.5) / CH * span_lon
    lat = 90 - cy * span_lat - (np.arange(CH) + 0.5) / CH * span_lat
    return np.meshgrid(lon, lat)

def finish(rgb, LON, LAT, polar):
    # polar caps from the base map, blended in over a degree below the mercator limit
    w = np.clip((np.abs(LAT) - (MERC_LIMIT - 1.2)) / 1.0, 0, 1)[..., None]
    if w.max() > 0: rgb = rgb * (1 - w) + base_sample(LON, LAT, polar) * w
    return Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8))

def day_chunk(level, cx, cy, root, z):
    LON, LAT = grid(level, cx, cy)
    rgb = merc_sample(root, z, LON, LAT)
    water = is_water(rgb)[..., None].astype(np.float32)
    for ch in range(3): rgb[..., ch] = rgb[..., ch] * FIT[ch][0] + FIT[ch][1]
    return finish(rgb * (1 - water) + OCEAN * water, LON, LAT, base), float(1 - water.mean())

def night_chunk(cx, cy):
    LON, LAT = grid(3, cx, cy)
    rgb = merc_sample(NIGHT, 7, LON, LAT)
    for ch in range(3): rgb[..., ch] = rgb[..., ch] * NFIT[ch][0] + NFIT[ch][1]
    return finish(rgb, LON, LAT, nbase)

def save(im, *path):
    os.makedirs(os.path.join(OUT, *path[:-1]), exist_ok=True)
    im.save(os.path.join(OUT, *path), quality=80, optimize=True, progressive=True)

if '4' in PARTS:
    nx, ny = LEVELS[4]
    kept = 0
    for cy in range(ny):
        for cx in range(nx):
            LON, LAT = grid(4, cx, cy)
            if is_water(merc_sample(DAY, 5, LON[::64, ::64], LAT[::64, ::64])).mean() > 0.98: continue   # open ocean
            im, landfrac = day_chunk(4, cx, cy, DAY8, 8)
            if landfrac < 0.01: continue
            save(im, '4', f'{cx}_{cy}.jpg'); kept += 1
        print('level 4 row', cy, 'kept so far', kept, flush=True)

if '1' in PARTS or '2' in PARTS or '3' in PARTS:
    for level in (3, 2, 1):
        nx, ny = LEVELS[level]
        for cy in range(ny):
            for cx in range(nx):
                if level == 3:
                    im = day_chunk(3, cx, cy, DAY, 7)[0]
                else:
                    # downsample the four children of the finer level
                    f = Image.new('RGB', (CH * 2, CH * 2))
                    for dy in (0, 1):
                        for dx in (0, 1):
                            f.paste(Image.open(os.path.join(OUT, str(level + 1), f'{cx * 2 + dx}_{cy * 2 + dy}.jpg')), (dx * CH, dy * CH))
                    im = f.resize((CH, CH), Image.LANCZOS)
                save(im, str(level), f'{cx}_{cy}.jpg')
            print('level', level, 'row', cy, flush=True)

if 'n' in PARTS:
    nx, ny = LEVELS[3]
    for cy in range(ny):
        for cx in range(nx):
            save(night_chunk(cx, cy), 'n3', f'{cx}_{cy}.jpg')
        print('night row', cy, flush=True)
