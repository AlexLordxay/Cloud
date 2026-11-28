# «У Землі колись могли бути кільця» — Kyiv as textures in local km (x east, y north, centred on LAT0, LON0):
#   inner_col.png   4096² over ±12.5 km (6.1 m/px) — Sentinel-2 cloudless 2016 z14, colour-corrected (the 2016 mosaic is
#                   hazy and blue-grey: contrast up, a touch warmer)
#   outer_col.png   4096² over ±68 km (33 m/px) — the same mosaic at z12
#   inner_z.npy / outer_z.npy  2048² heights (m) from the AWS Terrain Tiles (Terrarium), the same extents
#   inner_w.png / outer_w.png  water mask (the Dnipro, its lakes and channels): dark, blue-leaning, smooth pixels
#   inner_l.png / outer_l.png  city lights (emission): built-up ground (bright, grey, not green, not water) -> a scatter of lamps,
#                   denser and brighter along the roads (the mosaic's bright thin lines)
#   python3 scenes/earth_rings/prep.py   (after fetch.py)
import math, os
import numpy as np
from PIL import Image
from scipy import ndimage as nd
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WK = os.path.join(TOOLS, 'work', 'earth_rings')
LAT0, LON0 = 50.43, 30.56
KY = 111.2; KX = 111.32 * math.cos(math.radians(LAT0))

def tile_xy(lat, lon, z):
    n = 2 ** z; x = (lon + 180) / 360 * n
    y = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / math.pi) / 2 * n
    return x, y

def mosaic(d, ext):
    fs = [f for f in os.listdir(d) if f.endswith(ext)]
    xs = sorted({int(f.split('_')[0]) for f in fs}); ys = sorted({int(f.split('_')[1].split('.')[0]) for f in fs})
    x0, y0 = xs[0], ys[0]
    M = np.zeros(((ys[-1] - y0 + 1) * 256, (xs[-1] - x0 + 1) * 256, 3), np.float32)
    for f in fs:
        x = int(f.split('_')[0]); y = int(f.split('_')[1].split('.')[0])
        try:
            M[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = np.asarray(Image.open(os.path.join(d, f)).convert('RGB'), np.float32)
        except Exception:
            pass
    return M, x0, y0

def sample(M, x0, y0, z, half, n, order=1):
    km = (np.arange(n) + 0.5) / n * 2 * half - half
    gx, gy = np.meshgrid(km, -km)                       # row 0 = north
    lat = LAT0 + gy / KY; lon = LON0 + gx / KX
    tx, ty = tile_xy(lat, lon, z)
    px = (tx - x0) * 256 - 0.5; py = (ty - y0) * 256 - 0.5
    return np.stack([nd.map_coordinates(M[..., c], [py, px], order=order, mode='nearest') for c in range(M.shape[2])], -1)

def grade(c):
    # the 2016 mosaic: lift the contrast, take out the blue haze, a little warmer and greener
    c = c / 255.0
    c = np.clip((c - 0.06) * 1.35, 0, 1)
    c = c * np.array([1.04, 1.02, 0.90])
    L = c.mean(-1, keepdims=True); c = L + (c - L) * 1.25
    return np.clip(c, 0, 1)

def water(c, zz):
    # water in this mosaic: dark, with blue about as strong as green (forests are as dark but clearly greener), and
    # smooth (little texture at ~50 m); only large connected bodies (the Dnipro, its bays and lakes)
    L = c.mean(-1)
    bg = c[..., 2] / np.maximum(c[..., 1], 1e-3)
    sm = nd.uniform_filter(bg, 7)
    var = nd.uniform_filter(L ** 2, 9) - nd.uniform_filter(L, 9) ** 2
    w = (nd.uniform_filter(L, 5) < 0.14) & (sm > 0.91) & (var < 0.0012)
    w = nd.binary_opening(w, iterations=2); w = nd.binary_closing(w, iterations=3)
    lab, n = nd.label(w); sizes = nd.sum(w, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = sizes > 1500
    w = keep[lab]
    # the river and its lakes sit at the Dnipro's level (~90 m above sea): dark forest higher up is not water
    lab, n = nd.label(w); mh = nd.mean(zz, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool); keep[1:] = np.asarray(mh) < 100.0
    w = keep[lab]
    return nd.binary_fill_holes(w) & (nd.uniform_filter(L, 3) < 0.2) | w

def lights(c, w):
    # the density of built-up ground (bright, grey, not green, not water), streets (thin bright lines) denser: 0..1
    L = c.mean(-1); sat = c.max(-1) - c.min(-1)
    green = c[..., 1] > c[..., 0] * 1.06
    built = ((L > 0.22) & (sat < 0.16) & ~green & ~w).astype(np.float32)
    dens = nd.uniform_filter(built, 9)
    road = np.clip((L - nd.uniform_filter(L, 15)) * 6, 0, 1) * (dens > 0.2)
    return np.clip(nd.gaussian_filter(dens * 0.9 + road * 0.6, 1.5) * 1.2, 0, 1)

def ring_profile():
    # Saturn's ring texture (planetarium/textures/saturn_ring.png: radial colour + opacity from the C ring to the A ring's
    # edge) as the structure of the Earth's ring — the same physics shapes debris rings (bands, gaps, ringlets)
    T = np.asarray(Image.open(os.path.join(TOOLS, '..', '..', 'planetarium', 'textures', 'saturn_ring.png')).convert('RGBA')).astype(np.float32)[0] / 255
    n = 1024; x = np.linspace(0, 1, n)
    P = np.stack([np.interp(x, np.linspace(0, 1, len(T)), T[:, c]) for c in range(4)], -1)
    np.save(os.path.join(WK, 'ring_profile.npy'), P.astype(np.float32))

if __name__ == '__main__':
    ring_profile()
    D, dx0, dy0 = mosaic(os.path.join(WK, 'dem_12'), '.png')
    D = D[..., 0] * 256 + D[..., 1] + D[..., 2] / 256 - 32768
    for name, z, half, n in (('inner', 14, 12.5, 4096), ('outer', 12, 68.0, 4096)):
        h = sample(D[..., None], dx0, dy0, 12, half, 2048)[..., 0]
        # SRTM sees tree tops and roofs as bumps: smooth them out (the slopes of the Dnipro valley stay)
        h = nd.gaussian_filter(h, 2.0 if name == 'inner' else 1.0)
        zz = np.asarray(Image.fromarray(h.astype(np.float32)).resize((n, n), Image.BILINEAR))
        M, x0, y0 = mosaic(os.path.join(WK, f's2_{z}'), '.jpg')
        c = grade(sample(M, x0, y0, z, half, n))
        w = water(c, zz)
        # the water lies flat, a metre under its banks
        wl = np.asarray(Image.fromarray((w * 255).astype(np.uint8)).resize((2048, 2048), Image.BILINEAR)) / 255.0
        lvl = 90.0 if name == 'inner' else np.minimum(h, 90.0)
        h = h * (1 - wl) + lvl * wl
        np.save(os.path.join(WK, f'{name}_z.npy'), h.astype(np.float32))
        Image.fromarray((c * 255).astype(np.uint8)).save(os.path.join(WK, f'{name}_col.png'))
        Image.fromarray((w * 255).astype(np.uint8)).save(os.path.join(WK, f'{name}_w.png'))
        Image.fromarray((lights(c, w) * 255).astype(np.uint8)).save(os.path.join(WK, f'{name}_l.png'))
        print(name, 'heights', float(h.min()), float(h.max()), 'water', round(float(w.mean()), 3), flush=True)
