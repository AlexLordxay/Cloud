# Prepares the 3D Mars terrain for "Знайомся: Марс": heights from the MGS laser altimeter (MOLA MEGDR, 128 px/degree,
# ~463 m, NASA, public domain) and colour from the Viking colour mosaic (USGS, ~925 m, public domain).
#
#   python3 scenes/mars_meet/terrain_data.py      -> work/mars_meet/<site>/{height.bin, colour.jpg, normal.png, meta.json}
#
# Downloads (once, ~1 GB) into work/mars_meet/: two MOLA tiles and the Viking mosaic. For each site a square patch
# around a centre is cut out; heights go to a Float32 grid (metres), the colour is resampled onto the same grid, and
# a normal map is baked at full height resolution so the relief stays sharp under the light.
import json, os, urllib.request
import numpy as np
from PIL import Image

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'mars_meet')
MOLA = 'https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/'
VIKING = 'https://planetarymaps.usgs.gov/mosaic/Mars_Viking_ClrMosaic_global_925m.tif'
PPD = 128                     # MOLA pixels per degree
R_MARS = 3389.5e3             # metres
# name: (centre latitude, centre east longitude, half size in degrees, grid size)
SITES = {
    'olympus': (18.4, 226.2, 9.0, 2048),
    'valles': (-9.0, 293.0, 9.0, 1536),
}


def fetch(url, path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print('downloading', url, flush=True)
        urllib.request.urlretrieve(url, path)
    return path


def mola_tile(lat, lon):
    """The MOLA tile holding (lat, lon): tiles are 44° tall (top edges 88, 44, 0, -44) and 90° wide."""
    top = next(t for t in (88, 44, 0, -44) if t - 44 <= lat <= t)
    left = int(lon // 90 * 90) % 360
    name = f"megt{abs(top):02d}{'n' if top >= 0 else 's'}{left:03d}hb.img"
    a = np.memmap(fetch(MOLA + name, os.path.join(WORK, 'dem', name)), dtype='>i2', mode='r', shape=(44 * PPD, 90 * PPD))
    return a, top, left


def heights(lat0, lon0, half, n):
    """Heights on an n×n grid of latitude/longitude around the centre (bilinear)."""
    a, top, left = mola_tile(lat0, lon0)
    lats = np.linspace(lat0 + half, lat0 - half, n)
    lons = np.linspace(lon0 - half, lon0 + half, n)
    r = (top - lats) * PPD - 0.5
    c = (lons - left) * PPD - 0.5
    r0 = np.clip(np.floor(r).astype(int), 0, a.shape[0] - 2); fr = (r - r0)[:, None]
    c0 = np.clip(np.floor(c).astype(int), 0, a.shape[1] - 2); fc = (c - c0)[None, :]
    sub = np.asarray(a[r0.min():r0.max() + 2, c0.min():c0.max() + 2], dtype=np.float32)
    rr, cc = r0 - r0.min(), c0 - c0.min()
    g = lambda i, j: sub[np.ix_(rr + i, cc + j)]
    return (g(0, 0) * (1 - fc) + g(0, 1) * fc) * (1 - fr) + (g(1, 0) * (1 - fc) + g(1, 1) * fc) * fr


def colour(lat0, lon0, half, n):
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(fetch(VIKING, os.path.join(WORK, 'viking_925m.tif')))
    ppd = im.size[0] / 360.0
    w = lon0 - 360 if lon0 > 180 else lon0          # the mosaic runs from -180 to 180
    box = ((w - half + 180) * ppd, (90 - lat0 - half) * ppd, (w + half + 180) * ppd, (90 - lat0 + half) * ppd)
    return im.resize((n, n), Image.BICUBIC, box=box)


def main():
    for name, (lat0, lon0, half, n) in SITES.items():
        out = os.path.join(WORK, name); os.makedirs(out, exist_ok=True)
        h = heights(lat0, lon0, half, n)
        # metres per grid step: north–south, and east–west at the centre latitude
        dy = 2 * half / (n - 1) * np.pi / 180 * R_MARS
        dx = dy * np.cos(np.radians(lat0))
        gy, gx = np.gradient(h, dy, dx)
        nrm = np.dstack([-gx, gy, np.ones_like(h)])                       # x east, y north, z up
        nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
        Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, 'normal.png'))
        colour(lat0, lon0, half, n).save(os.path.join(out, 'colour.jpg'), quality=93)
        h.astype('<f4').tofile(os.path.join(out, 'height.bin'))
        json.dump({'lat': lat0, 'lon': lon0, 'half': half, 'n': n, 'dx': dx, 'dy': dy, 'hmin': float(h.min()),
                   'hmax': float(h.max()), 'R': R_MARS}, open(os.path.join(out, 'meta.json'), 'w'))
        print(name, n, 'grid,', f'{dx / 1000:.2f}×{dy / 1000:.2f} km steps,', f'{h.min():.0f}…{h.max():.0f} m')


if __name__ == '__main__':
    main()
