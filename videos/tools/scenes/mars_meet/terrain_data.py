# Prepares the 3D Mars terrain for "Знайомся: Марс", from three global USGS mosaics (all public domain), reading only
# the patch round each site straight out of the multi-gigabyte files (rangetiff.py):
#   heights — HRSC + MOLA blended DEM, 200 m/pixel (Mars Express stereo cameras on the MOLA laser altimeter base);
#   colour  — Viking MDIM 2.1 colour mosaic, 232 m/pixel;
#   detail  — THEMIS daytime infrared mosaic, 100 m/pixel: its fine light-and-dark pattern (crater rims, ridges, dunes)
#             is laid over the Viking colour as a high-pass, so the surface stays sharp close up.
#
#   python3 scenes/mars_meet/terrain_data.py [site]   -> work/mars_meet/<site>/{height.bin, colour.jpg, normal.png, meta.json}
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
from rangetiff import latlon_window

Image.MAX_IMAGE_PIXELS = None
TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'mars_meet')
USGS = 'https://planetarymaps.usgs.gov/mosaic/'
DEM = USGS + 'Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif'
VIKING = USGS + 'Mars_Viking_MDIM21_ClrMosaic_global_232m.tif'
THEMIS = USGS + 'Mars_MO_THEMIS-IR-Day_mosaic_global_100m_v12.tif'
R_MARS = 3389.5e3
NH, NT = 4096, 8192                  # height / normal grid, colour texture
# name: (centre latitude, centre east longitude, half size in degrees)
SITES = {'olympus': (18.4, 226.2, 9.0), 'valles': (-9.0, 293.0, 9.0), 'gale': (-5.2, 137.8, 2.2)}


def cached(name, site, fetch):
    """Raw mosaic windows are kept in work/ so the grid sizes can be changed without downloading again."""
    path = os.path.join(WORK, site, f'raw_{name}.npz')
    if not os.path.exists(path):
        img, box = fetch()
        np.savez(path, img=img, box=np.array(box))
    z = np.load(path)
    return z['img'], tuple(z['box'])


def resample(img, box, lat0, lon0, half, n):
    """img (covering box = top, bottom, west, east) onto an n×n grid round the centre, bilinear."""
    top, bot, west, east = box
    lats = np.linspace(lat0 + half, lat0 - half, n)
    lons = np.linspace(lon0 - half, lon0 + half, n)
    r = (top - lats) / (top - bot) * img.shape[0] - 0.5
    c = (lons - west) / (east - west) * img.shape[1] - 0.5
    r0 = np.clip(np.floor(r).astype(int), 0, img.shape[0] - 2); fr = (r - r0)[:, None]
    c0 = np.clip(np.floor(c).astype(int), 0, img.shape[1] - 2); fc = (c - c0)[None, :]
    if img.ndim == 3: fr, fc = fr[..., None], fc[..., None]
    a = img.astype(np.float32)
    g = lambda i, j: a[np.ix_(r0 + i, c0 + j)]
    return (g(0, 0) * (1 - fc) + g(0, 1) * fc) * (1 - fr) + (g(1, 0) * (1 - fc) + g(1, 1) * fc) * fr


def build(site):
    lat0, lon0, half = SITES[site]
    out = os.path.join(WORK, site); os.makedirs(out, exist_ok=True)
    w = lon0 - 360 if lon0 > 180 else lon0
    box = (lat0 - half - 0.1, lat0 + half + 0.1, w - half - 0.1, w + half + 0.1)
    print(site, 'heights…', flush=True)
    dem, dbox = cached('dem', site, lambda: latlon_window(DEM, *box))
    print(site, 'colour…', flush=True)
    vik, vbox = cached('viking', site, lambda: latlon_window(VIKING, *box))
    print(site, 'detail…', flush=True)
    # the THEMIS file's columns run from 0° east (its header says -180°, but the pictures say otherwise — checked on
    # Olympus's calderas), so it is read and resampled with longitudes shifted by 180°
    tb = (box[0], box[1], lon0 - 180 - half - 0.1, lon0 - 180 + half + 0.1)
    thm, tbox = cached('themis', site, lambda: latlon_window(THEMIS, *tb))

    h = resample(dem, dbox, lat0, w, half, NH)
    dy = 2 * half / (NH - 1) * np.pi / 180 * R_MARS
    dx = dy * np.cos(np.radians(lat0))
    gy, gx = np.gradient(h, dy, dx)
    nrm = np.dstack([-gx, gy, np.ones_like(h)])                       # x east, y north, z up
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, 'normal.png'))
    h.astype('<f4').tofile(os.path.join(out, 'height.bin'))

    col = resample(vik, vbox, lat0, w, half, NT)
    # the Viking mosaic is stitched from pictures taken in different light: its seams show as straight edges, so only
    # its broad colour is kept (blurred over ~6 km); the sharp detail comes from THEMIS below
    col = np.dstack([np.asarray(Image.fromarray(col[..., i].astype(np.uint8)).filter(ImageFilter.GaussianBlur(48)), np.float32) for i in range(3)])
    t = resample(thm, tbox, lat0, lon0 - 180, half, NT)
    valid = t > 2                                                      # holes in the infrared mosaic
    blur = np.asarray(Image.fromarray(np.clip(t, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)), np.float32)
    detail = np.where(valid & (blur > 2), np.clip(t / np.maximum(blur, 1), 0.6, 1.45), 1.0)
    # The Viking colours are washed out and bluish in places (frost, haze in the old pictures): the brightness is kept and
    # recoloured along a Martian ramp — dark basalt brown, rust, pale dust — with a little of the original hue left.
    lum = col @ np.array([0.3, 0.59, 0.11], np.float32)
    lo, hi = np.percentile(lum, 2), np.percentile(lum, 98)
    k = np.clip((lum - lo) / max(hi - lo, 1), 0, 1)[..., None]
    dark, mid, light = (np.array(c, np.float32) for c in ((62, 34, 22), (168, 88, 50), (222, 160, 112)))
    ramp = np.where(k < 0.5, dark + (mid - dark) * (k / 0.5), mid + (light - mid) * ((k - 0.5) / 0.5))
    col = ramp * 0.78 + col * 0.22
    col = np.clip(col * (1 + 0.95 * (detail - 1))[..., None], 0, 255)
    Image.fromarray(col.astype(np.uint8)).save(os.path.join(out, 'colour.jpg'), quality=92)
    json.dump({'lat': lat0, 'lon': lon0, 'half': half, 'n': NH, 'dx': dx, 'dy': dy, 'hmin': float(h.min()),
               'hmax': float(h.max()), 'R': R_MARS}, open(os.path.join(out, 'meta.json'), 'w'))
    print(site, f'{NH} grid, {dx:.0f}×{dy:.0f} m steps, {h.min():.0f}…{h.max():.0f} m; colour {NT}²', flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:] or SITES: build(s)
