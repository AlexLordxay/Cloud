# Builds the detailed Earth: a pyramid of map chunks the site streams in as the camera nears the surface.
#
#   python3 earth_detail.py <tiles dir>      e.g. …/@freetiler/nasa-bluemarble/tiles   ->  ../textures/earth/
#
# Source: NASA Blue Marble (shaded relief and bathymetry), web-mercator tiles z/x/y.jpeg, 256 px, from the npm package
# @freetiler/nasa-bluemarble (NASA open data). Zoom 7 is 32768 px around the equator, ~1.2 km per pixel.
# Output: the site's own layout, plate carrée like earth_day.jpg, in 2048 px chunks named <level>/<x>_<y>.jpg
# (x from 180° W eastwards, y from the north pole down):
#   level 1   8192 × 4096   4 × 2 chunks   ~4.9 km per pixel
#   level 2  16384 × 8192   8 × 4 chunks   ~2.4 km
#   level 3  32768 × 16384 16 × 8 chunks   ~1.2 km
# Land colours are matched to earth_day.jpg (per-channel fit over land), so switching maps is seamless. Water is flattened
# to the base map's ocean tone: the source shows the sea floor (shelves, trenches), which reads as fog from orbit.
# Beyond the mercator limit (±85.05°) the polar caps come from earth_day.jpg itself.
import math, os, sys
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'textures')
OUT = os.path.join(TEX, 'earth')
SRC = sys.argv[1]
Z = 7                                   # source zoom
N = 2 ** Z                              # tiles per side at that zoom
CH = 2048                               # chunk size
LEVELS = {1: (4, 2), 2: (8, 4), 3: (16, 8)}
MERC_LIMIT = math.degrees(math.atan(math.sinh(math.pi)))   # 85.0511°

_tiles = {}
def tile(z, x, y):
    k = (z, x, y)
    if k not in _tiles:
        if len(_tiles) > 4000: _tiles.clear()
        p = os.path.join(SRC, str(z), str(x % (2 ** z)), f'{y}.jpeg')
        _tiles[k] = np.asarray(Image.open(p).convert('RGB'), dtype=np.float32) if os.path.exists(p) else np.zeros((256, 256, 3), np.float32)
    return _tiles[k]

def merc_sample(z, lon, lat):
    """Bilinear sample of the mercator pyramid at zoom z for arrays of lon/lat (deg). Returns float RGB."""
    n = 2 ** z
    lat = np.clip(lat, -MERC_LIMIT + 1e-6, MERC_LIMIT - 1e-6)
    px = (lon + 180.0) / 360.0 * n * 256 - 0.5
    py = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / math.pi) / 2 * n * 256 - 0.5
    py = np.clip(py, 0, n * 256 - 1.001)
    # mosaic of the tiles touched
    tx0, tx1 = int(np.floor(px.min() / 256)) - 1, int(np.floor(px.max() / 256)) + 1
    ty0, ty1 = max(0, int(np.floor(py.min() / 256))), min(n - 1, int(np.floor(py.max() / 256)) + 1)
    mos = np.concatenate([np.concatenate([tile(z, tx, ty) for tx in range(tx0, tx1 + 1)], axis=1) for ty in range(ty0, ty1 + 1)], axis=0)
    fx, fy = px - tx0 * 256, py - ty0 * 256
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    ax, ay = (fx - x0)[..., None], (fy - y0)[..., None]
    x0 = np.clip(x0, 0, mos.shape[1] - 2); y0 = np.clip(y0, 0, mos.shape[0] - 2)
    a, b = mos[y0, x0], mos[y0, x0 + 1]
    c, d = mos[y0 + 1, x0], mos[y0 + 1, x0 + 1]
    return (a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay

base = np.asarray(Image.open(os.path.join(TEX, 'earth_day.jpg')).convert('RGB'), dtype=np.float32)
spec = np.asarray(Image.open(os.path.join(TEX, 'earth_specular.jpg')).convert('RGB'), dtype=np.float32)
def base_sample(lon, lat, img=None):
    img = base if img is None else img
    H, W = img.shape[:2]
    fx = (lon + 180) / 360 * W - 0.5; fy = (90 - lat) / 180 * H - 0.5
    x0 = np.clip(np.floor(fx).astype(int), 0, W - 2); y0 = np.clip(np.floor(fy).astype(int), 0, H - 2)
    ax, ay = np.clip(fx - x0, 0, 1)[..., None], np.clip(fy - y0, 0, 1)[..., None]
    a, b, c, d = img[y0, x0], img[y0, x0 + 1], img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a * (1 - ax) + b * ax) * (1 - ay) + (c * (1 - ax) + d * ax) * ay

# Colour match of the Blue Marble against earth_day.jpg over land, on a coarse grid (in sRGB).
H0, W0 = 960, 1920
lat_g = 90 - (np.arange(H0) + 0.5) / H0 * 180
lon_g = -180 + (np.arange(W0) + 0.5) / W0 * 360
LON, LAT = np.meshgrid(lon_g, lat_g)
def is_water(rgb):
    return (rgb[..., 2] - np.maximum(rgb[..., 0], rgb[..., 1])) > 6
s5 = merc_sample(5, LON, LAT)
land = base_sample(LON, LAT, spec)[..., 0] < 40
m = (np.abs(LAT) < 75) & land & ~is_water(s5)
src = s5[m]; ref = base_sample(LON, LAT)[m]
sea = (base_sample(LON, LAT, spec)[..., 0] > 220) & (np.abs(LAT) < 60)
OCEAN = np.median(base_sample(LON, LAT)[sea], axis=0)
print('ocean tone:', OCEAN.round(1))
# Mean and spread matched per channel (a least-squares fit would flatten the contrast: the base map is blurrier).
FIT = []
for ch in range(3):
    k = ref[:, ch].std() / src[:, ch].std()
    FIT.append((k, ref[:, ch].mean() - k * src[:, ch].mean()))
print('colour fit (gain, offset):', [(round(k, 3), round(c, 1)) for k, c in FIT])

def chunk(level, cx, cy):
    nx, ny = LEVELS[level]
    span_lon, span_lat = 360 / nx, 180 / ny
    lon = -180 + cx * span_lon + (np.arange(CH) + 0.5) / CH * span_lon
    lat = 90 - cy * span_lat - (np.arange(CH) + 0.5) / CH * span_lat
    LON, LAT = np.meshgrid(lon, lat)
    rgb = merc_sample(Z, LON, LAT)
    water = is_water(rgb)[..., None].astype(np.float32)
    for ch in range(3): rgb[..., ch] = rgb[..., ch] * FIT[ch][0] + FIT[ch][1]
    rgb = rgb * (1 - water) + OCEAN * water
    # polar caps from the base map, blended in over a degree below the mercator limit
    w = np.clip((np.abs(LAT) - (MERC_LIMIT - 1.2)) / 1.0, 0, 1)[..., None]
    if w.max() > 0: rgb = rgb * (1 - w) + base_sample(LON, LAT) * w
    return Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8))

for level in (3, 2, 1):
    nx, ny = LEVELS[level]
    os.makedirs(os.path.join(OUT, str(level)), exist_ok=True)
    for cy in range(ny):
        for cx in range(nx):
            if level == 3:
                im = chunk(3, cx, cy)
            else:
                # downsample the four children of the finer level
                f = Image.new('RGB', (CH * 2, CH * 2))
                for dy in (0, 1):
                    for dx in (0, 1):
                        f.paste(Image.open(os.path.join(OUT, str(level + 1), f'{cx * 2 + dx}_{cy * 2 + dy}.jpg')), (dx * CH, dy * CH))
                im = f.resize((CH, CH), Image.LANCZOS)
            im.save(os.path.join(OUT, str(level), f'{cx}_{cy}.jpg'), quality=80, optimize=True, progressive=True)
        print('level', level, 'row', cy, 'done', flush=True)
