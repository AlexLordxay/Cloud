# Prepares the 3D Venus terrain for "Знайомся: Венера", from two global USGS mosaics of NASA's Magellan mission (public
# domain), reading only the patch round each site (rangetiff.py from mars_meet):
#   heights — Magellan altimetry, 4641 m/pixel (coarse: smoothed up to the grid, the shapes are real);
#   surface — Magellan left-look radar mosaic, 75 m/pixel. Radar brightness is roughness, not colour, so it is laid on a
#             warm ramp (dark basalt brown → orange → pale ochre), the colour of the surface in the Venera landers'
#             pictures, and its fine pattern (lava flows, fractures) also roughens the lighting a little.
#
#   python3 scenes/venus_meet/terrain_data.py [site]   -> work/venus_meet/<site>/{height.bin, colour.jpg, normal.png, meta.json}
import io, json, os, sys
import numpy as np
import tifffile
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mars_meet'))
from rangetiff import RangeFile, window

Image.MAX_IMAGE_PIXELS = None
TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'venus_meet')
USGS = 'https://planetarymaps.usgs.gov/mosaic/'
DEM = USGS + 'Venus_Magellan_Topography_Global_4641m_v02.tif'
SAR = USGS + 'Venus_Magellan_LeftLook_mosaic_global_75m.tif'
R_VENUS = 6051.8e3
NH, NT = 4096, 8192                  # height / normal grid, colour texture
# name: (centre latitude, centre east longitude, half size in degrees)
SITES = {'maat': (0.6, 194.5, 4.0)}


def geo_window(url, lat0, lat1, lon0, lon1):
    """A latitude/longitude box from a simple-cylindrical mosaic, placed by its GeoTIFF tie point (the radar mosaic
    stops at ±84°, so its rows can't be counted from the pole)."""
    with tifffile.TiffFile(io.BufferedReader(RangeFile(url), 1 << 20)) as t:
        tags = t.pages[0].tags
        _, _, _, x0, y0, _ = tags['ModelTiepointTag'].value
        sx = tags['ModelPixelScaleTag'].value[0]
    mpd = np.pi / 180 * R_VENUS                                   # metres per degree
    r0, r1 = int((y0 - lat1 * mpd) / sx), int(np.ceil((y0 - lat0 * mpd) / sx))
    c0, c1 = int((lon0 * mpd - x0) / sx), int(np.ceil((lon1 * mpd - x0) / sx))
    img, _ = window(url, r0, r1, c0, c1)
    return img, ((y0 - r0 * sx) / mpd, (y0 - r1 * sx) / mpd, (x0 + c0 * sx) / mpd, (x0 + c1 * sx) / mpd)


def cached(name, site, fetch):
    path = os.path.join(WORK, site, f'raw_{name}.npz')
    if not os.path.exists(path):
        img, box = fetch()
        np.savez(path, img=img, box=np.array(box))
    z = np.load(path)
    return z['img'], tuple(z['box'])


def resample(img, box, lat0, lon0, half, n, cubic=False):
    """img (covering box = top, bottom, west, east) onto an n×n grid round the centre."""
    top, bot, west, east = box
    if cubic:                                                      # the coarse heights: a smooth bicubic upsampling
        im = Image.fromarray(img.astype(np.float32), 'F')
        x0 = (lon0 - half - west) / (east - west) * img.shape[1]; x1 = (lon0 + half - west) / (east - west) * img.shape[1]
        y0 = (top - lat0 - half) / (top - bot) * img.shape[0]; y1 = (top - lat0 + half) / (top - bot) * img.shape[0]
        return np.asarray(im.resize((n, n), Image.BICUBIC, box=(x0, y0, x1, y1)), np.float32)
    lats = np.linspace(lat0 + half, lat0 - half, n)
    lons = np.linspace(lon0 - half, lon0 + half, n)
    r = (top - lats) / (top - bot) * img.shape[0] - 0.5
    c = (lons - west) / (east - west) * img.shape[1] - 0.5
    r0 = np.clip(np.floor(r).astype(int), 0, img.shape[0] - 2); fr = (r - r0)[:, None]
    c0 = np.clip(np.floor(c).astype(int), 0, img.shape[1] - 2); fc = (c - c0)[None, :]
    a = img.astype(np.float32)
    g = lambda i, j: a[np.ix_(r0 + i, c0 + j)]
    return (g(0, 0) * (1 - fc) + g(0, 1) * fc) * (1 - fr) + (g(1, 0) * (1 - fc) + g(1, 1) * fc) * fr


def build(site):
    lat0, lon0, half = SITES[site]
    out = os.path.join(WORK, site); os.makedirs(out, exist_ok=True)
    w = lon0 - 360 if lon0 > 180 else lon0
    box = (lat0 - half - 0.3, lat0 + half + 0.3, w - half - 0.3, w + half + 0.3)
    print(site, 'heights…', flush=True)
    dem, dbox = cached('dem', site, lambda: geo_window(DEM, *box))
    print(site, 'radar…', flush=True)
    sar, sbox = cached('sar', site, lambda: geo_window(SAR, *box))

    dem = np.where(dem == -32768, np.median(dem), dem).astype(np.float32)
    h = resample(dem, dbox, lat0, w, half, NH, cubic=True)
    s = resample(sar, sbox, lat0, w, half, NT)
    valid = s > 0
    s = np.where(valid, s, np.median(s[valid]))
    blur = np.asarray(Image.fromarray(np.clip(s, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(24)), np.float32)
    detail = np.clip(s / np.maximum(blur, 1), 0.55, 1.6)

    # the lighting: slopes from the heights, roughened by the radar's fine pattern (a small bump, ~300 m)
    dy = 2 * half / (NH - 1) * np.pi / 180 * R_VENUS
    dx = dy * np.cos(np.radians(lat0))
    bump = np.asarray(Image.fromarray(((detail - 1) * 100 + 128).clip(0, 255).astype(np.uint8)).resize((NH, NH), Image.BILINEAR), np.float32)
    hb = h + (bump - 128) * 2.5
    gy, gx = np.gradient(hb, dy, dx)
    nrm = np.dstack([-gx, gy, np.ones_like(h)])                       # x east, y north, z up
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, 'normal.png'))
    h.astype('<f4').tofile(os.path.join(out, 'height.bin'))

    lo, hi = np.percentile(s, 2), np.percentile(s, 98)
    k = np.clip((s - lo) / max(hi - lo, 1), 0, 1)[..., None]
    dark, mid, light = (np.array(c, np.float32) for c in ((46, 26, 14), (150, 82, 36), (224, 170, 100)))
    col = np.where(k < 0.5, dark + (mid - dark) * (k / 0.5), mid + (light - mid) * ((k - 0.5) / 0.5))
    Image.fromarray(col.clip(0, 255).astype(np.uint8)).save(os.path.join(out, 'colour.jpg'), quality=92)
    json.dump({'lat': lat0, 'lon': lon0, 'half': half, 'n': NH, 'dx': dx, 'dy': dy, 'hmin': float(h.min()),
               'hmax': float(h.max()), 'R': R_VENUS}, open(os.path.join(out, 'meta.json'), 'w'))
    i = np.unravel_index(np.argmax(h), h.shape)
    print(site, f'{NH} grid, {dx:.0f}×{dy:.0f} m steps, {h.min():.0f}…{h.max():.0f} m, highest at '
          f'{(i[1] - (NH - 1) / 2) * dx / 1000:.0f} km east, {(i[0] - (NH - 1) / 2) * dy / 1000:.0f} km south', flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:] or SITES: build(s)
