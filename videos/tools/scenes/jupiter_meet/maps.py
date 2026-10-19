# Maps of Io, Europa and Ganymede for "Знайомся: Юпітер": the global USGS mosaics (Galileo SSI + Voyager, public
# domain, ~200 MB each), fetched once and brought down to 8192×4096 equirectangular JPEGs (longitude −180…180 left
# to right, as the renderer expects). Europa's mosaic is grey: it is tinted — pale bluish ice, the dark lineae and
# chaos a rusty brown, as in Galileo's colour views.
#
#   python3 scenes/jupiter_meet/maps.py   -> work/jupiter_meet/maps/{io,europa,ganymede}.jpg
import io, os, urllib.request
import numpy as np
import tifffile
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(TOOLS, 'work', 'jupiter_meet', 'maps')
USGS = 'https://planetarymaps.usgs.gov/mosaic/'
MAPS = {
    'io': 'Io_GalileoSSI-Voyager_Global_Mosaic_ClrMerge_1km.tif',
    'europa': 'Europa_Voyager_GalileoSSI_global_mosaic_500m.tif',
    'ganymede': 'Ganymede_Voyager_GalileoSSI_Global_ClrMosaic_1435m.tif',
}
W, H = 8192, 4096
UA = 'nebozvid-video/1.0'


def fetch(name):
    """The whole mosaic, downloaded once into work/ (resumed with Range requests if the connection drops)."""
    raw = os.path.join(OUT, name + '.tif')
    if not os.path.exists(raw):
        url, part = USGS + MAPS[name], raw + '.part'
        head = urllib.request.urlopen(urllib.request.Request(url, headers={'Range': 'bytes=0-0', 'User-Agent': UA}), timeout=60)
        size = int(head.headers['Content-Range'].split('/')[1])
        for attempt in range(20):
            have = os.path.getsize(part) if os.path.exists(part) else 0
            if have >= size: break
            print(name, f'downloading {have >> 20}/{size >> 20} MB…', flush=True)
            req = urllib.request.Request(url, headers={'Range': f'bytes={have}-', 'User-Agent': UA})
            try:
                with urllib.request.urlopen(req, timeout=600) as r, open(part, 'ab') as f:
                    while True:
                        b = r.read(1 << 22)
                        if not b: break
                        f.write(b)
            except Exception as e:
                print(name, 'interrupted:', e, flush=True)
        assert os.path.getsize(part) == size, (name, os.path.getsize(part), size)
        os.rename(part, raw)
    a = tifffile.imread(raw)
    if a.ndim == 3 and a.shape[0] == 3: a = np.moveaxis(a, 0, -1)       # planes first → RGB last
    return a


def fill_gaps(img):
    """No-data (black, near the poles) filled with the surrounding surface: a blur of the valid pixels, normalised by the
    blurred mask (repeated at growing radii so even wide gaps are covered)."""
    a = np.asarray(img, np.float32)
    if a.ndim == 2: a = a[..., None]
    valid = (a.max(axis=2) > 3).astype(np.float32)
    out = a.copy()
    small = lambda x, r: np.asarray(Image.fromarray(np.clip(x, 0, 255).astype(np.uint8)).resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r)).resize((W, H), Image.BILINEAR), np.float32)
    for r in (2, 6, 18, 60):
        num = np.dstack([small(a[..., c] * valid, r) for c in range(a.shape[2])])
        den = small(valid * 255, r)[..., None] / 255
        fill = num / np.maximum(den, 1e-4)
        hole = (valid < 0.5) & (den[..., 0] > 0.02)
        out[hole] = fill[hole]
        valid = np.maximum(valid, hole.astype(np.float32))
    out = np.clip(out, 0, 255).astype(np.uint8)
    return Image.fromarray(out[..., 0] if out.shape[2] == 1 else out)


def polar_caps(img, lim):
    """Beyond latitude ±lim the mosaics hold only smeared fill: the caps are replaced by the surface just outside them
    (the band lim-8°…lim-2°, averaged per longitude and blurred), faded in over 3°."""
    a = np.asarray(img, np.float32)
    if a.ndim == 2: a = a[..., None]
    lat = 90 - (np.arange(H) + 0.5) / H * 180
    out = a.copy()
    for sgn in (1, -1):
        band = (sgn * lat > lim - 8) & (sgn * lat < lim - 2)
        ring = a[band].mean(axis=0)                                        # W × channels
        ring = np.dstack([np.asarray(Image.fromarray(np.clip(ring[None, :, c], 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40)), np.float32)[0] for c in range(a.shape[2])])[0]
        w = np.clip((sgn * lat - lim) / 3 + 1, 0, 1)[:, None, None]        # 0 below lim-3°, 1 beyond lim
        out = out * (1 - w * (sgn * lat[:, None, None] > 0)) + ring[None] * w * (sgn * lat[:, None, None] > 0)
    out = np.clip(out, 0, 255).astype(np.uint8)
    return Image.fromarray(out[..., 0] if out.shape[2] == 1 else out)


CAPS = {'europa': 79, 'ganymede': 82}


def build(name):
    a = fetch(name)
    img = fill_gaps(Image.fromarray(a).resize((W, H), Image.LANCZOS))
    if name in CAPS: img = polar_caps(img, CAPS[name])
    if name == 'europa':
        g = np.asarray(img, np.float32) / 255
        lo, hi = np.percentile(g, 1), np.percentile(g, 99.5)
        k = np.clip((g - lo) / (hi - lo), 0, 1)[..., None]
        dark, ice = np.array([118, 74, 48], np.float32), np.array([236, 238, 242], np.float32)
        img = Image.fromarray(np.clip(dark + (ice - dark) * k ** 0.8, 0, 255).astype(np.uint8))
    img.convert('RGB').save(os.path.join(OUT, name + '.jpg'), quality=92)
    print(name, 'done', a.shape, flush=True)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for n in MAPS: build(n)
