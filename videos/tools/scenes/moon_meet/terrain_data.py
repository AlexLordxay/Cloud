# Prepares the 3D Moon terrain for "Знайомся: Місяць", from two global USGS mosaics (public domain), reading only the
# patch round each site straight out of the multi-gigabyte files (rangetiff.py from mars_meet):
#   heights    — LRO LOLA laser altimeter DEM, 118 m/pixel (stored in half-metres);
#   brightness — LRO LROC WAC mosaic, 100 m/pixel: blurred for the broad albedo (dark maria, pale highlands), plus a
#                little of its fine detail. Its own shading (taken in morning light) is mostly blurred away, the light
#                comes from the heights.
# Each patch is a square of real kilometres round the site (azimuthal equidistant projection), so it is true to shape
# even next to the pole, where the mosaics' degrees of longitude shrink to nothing.
# The Moon has no air, so shadows are black and sharp: they are baked here for each site's Sun (shadow.png), from the
# exaggerated heights bent to the Moon's curvature — the same surface terrain.js draws.
#
#   python3 scenes/moon_meet/terrain_data.py [site]   -> work/moon_meet/<site>/{height.bin, colour.jpg, normal.png, shadow.png, meta.json}
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mars_meet'))
from rangetiff import latlon_window

Image.MAX_IMAGE_PIXELS = None
TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'moon_meet')
USGS = 'https://planetarymaps.usgs.gov/mosaic/'
DEM = USGS + 'Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif'
WAC = USGS + 'Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif'
R_MOON = 1737.4e3
NH, NT = 4096, 4096                  # height / normal / shadow grid, colour texture
EX = 1.6                             # vertical exaggeration, shared with terrain.js through meta.json
# name: (centre latitude, centre east longitude, half size in km, Sun azimuth from north through east, elevation);
# the Sun's azimuth is where it really stands at that elevation and latitude (it moves along the lunar equator's sky)
SITES = {
    'copernicus': (9.62, -20.08, 150, 92, 14),      # morning light: the terraced walls throw long shadows
    'tranquility': (0.674, 23.473, 75, 90, 11),     # the Sun as Apollo 11 saw it on landing, ~11° in the east
    'tycho': (-43.31, -11.36, 120, 286, 16),        # evening light from the west-north-west (far south: the Sun is northward)
    'south': (-85.5, 0.0, 130, 90, 6),              # near the south pole: the Earth ~4.5° over the northern horizon,
                                                    # the Sun low in the east — half the Earth lit
}


def grid_latlon(lat0, lon0, half, n):
    """Latitude and longitude (degrees) of an n×n grid of points `half` km either side of the centre, rows north →
    south, columns west → east (inverse azimuthal equidistant projection)."""
    x = np.linspace(-half, half, n)[None, :] * 1e3                        # east
    y = np.linspace(half, -half, n)[:, None] * 1e3                        # north
    rho = np.maximum(np.hypot(x, y), 1e-6); c = rho / R_MOON
    p0, l0 = np.radians(lat0), np.radians(lon0)
    lat = np.arcsin(np.cos(c) * np.sin(p0) + y * np.sin(c) * np.cos(p0) / rho)
    lon = l0 + np.arctan2(x * np.sin(c), rho * np.cos(p0) * np.cos(c) - y * np.sin(p0) * np.sin(c))
    return np.degrees(lat), (np.degrees(lon) + 180) % 360 - 180


def cached(name, site, fetch):
    """Raw mosaic windows are kept in work/ so the grid sizes can be changed without downloading again."""
    path = os.path.join(WORK, site, f'raw_{name}.npz')
    if not os.path.exists(path):
        img, box = fetch()
        np.savez(path, img=img, box=np.array(box))
    z = np.load(path)
    return z['img'], tuple(z['box'])


def sample(img, box, lat, lon):
    """img (covering box = top, bottom, west, east) at the given latitudes and longitudes, bilinear."""
    top, bot, west, east = box
    r = (top - lat) / (top - bot) * img.shape[0] - 0.5
    c = (lon - west) / (east - west) * img.shape[1] - 0.5
    r0 = np.clip(np.floor(r).astype(int), 0, img.shape[0] - 2); fr = np.clip(r - r0, 0, 1)
    c0 = np.clip(np.floor(c).astype(int), 0, img.shape[1] - 2); fc = np.clip(c - c0, 0, 1)
    a = img.astype(np.float32)
    return (a[r0, c0] * (1 - fc) + a[r0, c0 + 1] * fc) * (1 - fr) + (a[r0 + 1, c0] * (1 - fc) + a[r0 + 1, c0 + 1] * fc) * fr


def gblur(a, sigma):
    """A Gaussian blur of a float grid (PIL blurs only 8-bit images): one short kernel along each axis, edges held."""
    r = int(3 * sigma); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    for ax in (0, 1):
        p = np.pad(a, [(r, r) if i == ax else (0, 0) for i in (0, 1)], mode='edge')
        a = sum(w * np.take(p, np.arange(i, i + a.shape[ax]), axis=ax) for i, w in enumerate(k))
    return a.astype(np.float32)


def sun_vector(az, el):
    """x east, y up, z south — terrain.js's axes."""
    a, e = np.radians(az), np.radians(el)
    return [float(np.sin(a) * np.cos(e)), float(np.sin(e)), float(-np.cos(a) * np.cos(e))]


def shadows(h, step, az, el):
    """1 where the Sun is seen, 0 in shadow: the grid is turned so the Sun shines along the rows from the left, swept
    once keeping the highest sight-line so far, then turned back."""
    n = h.shape[0]
    ang = np.degrees(np.arctan2(-np.cos(np.radians(az)), np.sin(np.radians(az))))   # sunward, image axes (y down)
    low = float(h.min()) - 1e6
    im = Image.fromarray(h.astype(np.float32) - low)                       # padding (0) sits far below every height
    rot = np.asarray(im.rotate(-(180 - ang), resample=Image.BILINEAR, expand=True), np.float32) + low
    drop = step * np.tan(np.radians(el))
    lit = np.ones_like(rot)
    m = np.full(rot.shape[0], -np.inf, np.float32)
    for c in range(rot.shape[1]):
        m = m - drop
        lit[:, c] = rot[:, c] >= m
        m = np.maximum(m, rot[:, c])
    back = Image.fromarray((lit * 255).astype(np.uint8)).rotate(180 - ang, resample=Image.BILINEAR, expand=True)
    W, H = back.size
    return back.crop(((W - n) // 2, (H - n) // 2, (W - n) // 2 + n, (H - n) // 2 + n)).filter(ImageFilter.GaussianBlur(1.2))


def build(site):
    lat0, lon0, half, saz, sel = SITES[site]
    out = os.path.join(WORK, site); os.makedirs(out, exist_ok=True)
    lat, lon = grid_latlon(lat0, lon0, half, NH)
    # the window of the mosaics that holds the patch (longitudes kept on one side of the date line)
    box = (float(lat.min()) - 0.05, float(lat.max()) + 0.05, float(lon.min()) - 0.05, float(lon.max()) + 0.05)
    print(site, 'heights…', [round(b, 2) for b in box], flush=True)
    dem, dbox = cached('dem', site, lambda: latlon_window(DEM, *box))
    print(site, 'brightness…', flush=True)
    wac, wbox = cached('wac', site, lambda: latlon_window(WAC, *box))

    step = 2 * half * 1e3 / (NH - 1)
    h = sample(dem, dbox, lat, lon) * 0.5                                  # half-metres → metres
    # LOLA is gridded from laser tracks: a light blur (below its own 118 m) hides the steps between them
    h = gblur(h, max(1.0, 60 / step))
    gy, gx = np.gradient(h, step, step)
    nrm = np.dstack([-gx, gy, np.ones_like(h)])                            # x east, y north, z up
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, 'normal.png'))
    h.astype('<f4').tofile(os.path.join(out, 'height.bin'))

    # the same surface terrain.js draws: exaggerated, and bent down with distance from the centre
    x = (np.arange(NH) - (NH - 1) / 2) * step
    hc = h * EX - (x[None, :] ** 2 + x[:, None] ** 2) / (2 * R_MOON)
    print(site, 'shadows…', flush=True)
    shadows(hc.astype(np.float32), step, saz, sel).save(os.path.join(out, 'shadow.png'))

    if NT != NH: lat, lon = grid_latlon(lat0, lon0, half, NT)
    w = sample(wac, wbox, lat, lon)
    valid = w > 1
    fill = np.where(valid, w, np.median(w[valid]))
    blur = lambda a, r: np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)
    broad = blur(fill, max(4, 2500 / step))                                # ~2.5 km: maria and highlands, rays, haloes
    fine = np.clip(fill / np.maximum(blur(fill, 4), 1), 0.75, 1.3)         # small craters, rocks — kept gently
    lum = broad * (1 + 0.45 * (fine - 1))
    # one brightness scale for every site, so the dark maria stay darker than the highlands
    k = np.clip((lum - 15) / (130 - 15), 0, 1)
    v = 60 + 170 * k                                                       # grey, never black (shadows do that)
    col = np.dstack([v * 1.02, v * 1.0, v * 0.96])                         # the faintest warm tint, as in photos
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, 'colour.jpg'), quality=92)
    json.dump({'lat': lat0, 'lon': lon0, 'half': half, 'n': NH, 'dx': step, 'dy': step, 'hmin': float(h.min()),
               'hmax': float(h.max()), 'R': R_MOON, 'ex': EX, 'sun': sun_vector(saz, sel)},
              open(os.path.join(out, 'meta.json'), 'w'))
    print(site, f'{NH} grid, {step:.0f} m steps, {h.min():.0f}…{h.max():.0f} m', flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:] or SITES: build(s)
