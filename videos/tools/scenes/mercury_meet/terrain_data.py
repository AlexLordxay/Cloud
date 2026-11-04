# Prepares the 3D Mercury terrain for "Знайомся: Меркурій", from two global USGS mosaics of NASA's MESSENGER mission
# (public domain), reading only the patch round each site (rangetiff.py from mars_meet):
#   heights    — MESSENGER USGS DEM v2, 665 m/pixel (metres above the 2440 km sphere; smoothed up to the grid);
#   brightness — two MDIS basemaps, 166 m/pixel: LOI (low Sun angle seen from overhead: almost pure albedo) for the
#                colour, and BDR (moderate Sun: light and shadow on every slope).
# The global heights are far blurrier than their grid (a 114 km crater is a faint 25 km ring), so the relief is rebuilt:
#   * the fine relief (features under ~30 km: small craters, terraces, central peaks, ridges) by photoclinometry —
#     the shading BDR/LOI turned into slopes toward the images' Sun (found from the shading's own spectrum) and
#     integrated in the Fourier domain (regularised across the light, where one Sun says nothing);
#   * the broad shape from the global heights;
#   * the bowls of the big craters a shot is about, from their real size (diameter, depth), which neither source holds.
# Built like moon_meet/terrain_data.py: each patch is a square of real kilometres round the site (azimuthal equidistant,
# so it holds its shape next to the pole), and as Mercury has no air the shadows are black and sharp, baked here from
# the exaggerated heights bent to the planet's curvature — the same surface terrain.js draws.
#   * a site with "els" gets shadows for several Sun elevations (shadow_0.png …), so the hook's Sun can rise, stop, sink
#     back and rise again with the shadows following;
#   * a site with "ice" also gets the permanently shadowed ground (ice.png): shadowed for the Sun at the highest it can
#     stand there, from every azimuth — where MESSENGER found water ice.
#
#   python3 scenes/mercury_meet/terrain_data.py [site]   -> work/mercury_meet/<site>/{height.bin, colour.jpg, normal.png, shadow*.png, meta.json}
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mars_meet'))
from rangetiff import latlon_window

Image.MAX_IMAGE_PIXELS = None
TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'mercury_meet')
USGS = 'https://planetarymaps.usgs.gov/mosaic/'
DEM = USGS + 'Mercury_Messenger_USGS_DEM_Global_665m_v2.tif'
BDR = USGS + 'Mercury_MESSENGER_MDIS_Basemap_BDR_Mosaic_Global_166m.tif'
LOI = USGS + 'Mercury_MESSENGER_MDIS_Basemap_LOI_Mosaic_Global_166m.tif'
R_MERC = 2439.4e3
NH = 4096                            # height / normal / shadow grid and colour texture
# name: dict(lat, lon (east), half (km), az, el (the Sun: azimuth from north through east, elevation), ex, and
#            optionally els (several elevations for a moving Sun), ice (bake the permanently shadowed ground), nt)
SITES = {
    # the hook: Hokusai, a young 114 km crater with terraced walls and central peaks; dawn, the Sun rising in the east
    'hokusai': dict(lat=57.8, lon=16.8, half=170, az=90, el=3.0, ex=1.8, els=[0.3, 0.9, 1.6, 2.4, 3.3, 4.4],
                    bowls=[(57.8, 16.8, 114, 3.2)]),
    # the Caloris basin, 1550 km across: its rim mountains in the morning light from the east
    'caloris': dict(lat=31.5, lon=162.7, half=1000, az=90, el=5.0, ex=4.0),
    # Discovery Rupes (the scarp, up to ~2 km) and Shevchenko crater (143 km), low Sun from the west
    'discovery': dict(lat=-54.5, lon=-41.0, half=300, az=270, el=7.0, ex=2.2, bowls=[(-53.6, -46.0, 143, 2.2)]),
    # near the north pole: Prokofiev and its neighbours, the Sun skimming the horizon, ice in the shadows
    'pole': dict(lat=85.5, lon=-60.0, half=170, az=180, el=1.6, ex=1.8, ice=True),
}


def grid_latlon(lat0, lon0, half, n):
    """Latitude and longitude (degrees) of an n×n grid of points `half` km either side of the centre, rows north →
    south, columns west → east (inverse azimuthal equidistant projection)."""
    x = np.linspace(-half, half, n)[None, :] * 1e3
    y = np.linspace(half, -half, n)[:, None] * 1e3
    rho = np.maximum(np.hypot(x, y), 1e-6); c = rho / R_MERC
    p0, l0 = np.radians(lat0), np.radians(lon0)
    lat = np.arcsin(np.cos(c) * np.sin(p0) + y * np.sin(c) * np.cos(p0) / rho)
    lon = l0 + np.arctan2(x * np.sin(c), rho * np.cos(p0) * np.cos(c) - y * np.sin(p0) * np.sin(c))
    return np.degrees(lat), (np.degrees(lon) + 180) % 360 - 180


def cached(name, site, fetch):
    path = os.path.join(WORK, site, f'raw_{name}.npz')
    if not os.path.exists(path):
        img, box = fetch()
        np.savez(path, img=img, box=np.array(box))
    z = np.load(path)
    return z['img'], tuple(z['box'])


def fetch_box(url, lat, lon):
    """The mosaic window holding the patch. Near the pole the patch wraps all the way round in longitude."""
    la0, la1 = float(lat.min()) - 0.05, min(90.0, float(lat.max()) + 0.05)
    lo0, lo1 = float(lon.min()) - 0.05, float(lon.max()) + 0.05
    if lo1 - lo0 > 300: lo0, lo1 = -180.0, 179.99
    return latlon_window(url, la0, la1, max(-180.0, lo0), min(179.99, lo1))


def sample(img, box, lat, lon):
    top, bot, west, east = box
    r = (top - lat) / (top - bot) * img.shape[0] - 0.5
    c = (lon - west) / (east - west) * img.shape[1] - 0.5
    r0 = np.clip(np.floor(r).astype(int), 0, img.shape[0] - 2); fr = np.clip(r - r0, 0, 1)
    c0 = np.clip(np.floor(c).astype(int), 0, img.shape[1] - 2); fc = np.clip(c - c0, 0, 1)
    a = img.astype(np.float32)
    return (a[r0, c0] * (1 - fc) + a[r0, c0 + 1] * fc) * (1 - fr) + (a[r0 + 1, c0] * (1 - fc) + a[r0 + 1, c0 + 1] * fc) * fr


def gblur(a, sigma):
    """A Gaussian blur of a float grid, edges held (scipy, fast for the wide ones)."""
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(np.asarray(a, np.float32), sigma, mode='nearest', truncate=3.0).astype(np.float32)


def sun_vector(az, el):
    a, e = np.radians(az), np.radians(el)
    return [float(np.sin(a) * np.cos(e)), float(np.sin(e)), float(-np.cos(a) * np.cos(e))]


def shadows(h, step, az, el, blur=1.2):
    """1 where the Sun is seen, 0 in shadow (as moon_meet): the grid turned so the Sun shines along the rows."""
    n = h.shape[0]
    ang = np.degrees(np.arctan2(-np.cos(np.radians(az)), np.sin(np.radians(az))))
    low = float(h.min()) - 1e6
    im = Image.fromarray(h.astype(np.float32) - low)
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
    out = back.crop(((W - n) // 2, (H - n) // 2, (W - n) // 2 + n, (H - n) // 2 + n))
    return out.filter(ImageFilter.GaussianBlur(blur)) if blur else out


def relief(b, o, ok, step, cut=7e3, eps=0.1, tan_i=2.5):
    """Fine relief (m) from the shading: log(BDR / LOI), high-passed; the light axis from the shading's spectrum (slopes
    across the light leave no trace, so its power lies along the light); the sign so that shadows (on the sunward inner
    walls) sit in hollows; slopes = −shading / tan(incidence), integrated in Fourier space, then high-passed at `cut`."""
    n = b.shape[0]
    sh = np.where(ok, np.log(np.maximum(b, 1)) - np.log(np.maximum(o, 1)), 0).astype(np.float32)
    sh = np.where(ok, sh - gblur(sh, cut / step), 0)
    F = np.abs(np.fft.fftshift(np.fft.fft2(sh))) ** 2
    ky, kx = np.mgrid[-n // 2:n // 2, -n // 2:n // 2]
    m = (np.hypot(kx, ky) > n / 100) & (np.hypot(kx, ky) < n / 5)
    th = np.arctan2(ky[m], kx[m]); w = F[m]
    ang = 0.5 * np.arctan2(np.sum(w * np.sin(2 * th)), np.sum(w * np.cos(2 * th)))
    lx, ly = np.cos(ang), np.sin(ang)                                      # image axes: x east, y south
    k = np.fft.fftfreq(n, step) * 2 * np.pi; KX, KY = np.meshgrid(k, k); kl = KX * lx + KY * ly
    slope = -np.clip(sh, -0.5, 0.7) / tan_i
    Hf = np.fft.fft2(slope) * np.conj(1j * kl) / (kl ** 2 + eps ** 2 * (KX ** 2 + KY ** 2) + 1e-12); Hf[0, 0] = 0
    h = np.real(np.fft.ifft2(Hf)).astype(np.float32)
    h = h - gblur(h, cut / step)
    dark = sh < np.percentile(sh[ok], 2)
    if h[dark].mean() > 0: h = -h                                          # the light came from the other side
    print(f'  light axis {np.degrees(ang):.0f}° (x east, y south), fine relief ±{np.percentile(np.abs(h), 99):.0f} m', flush=True)
    return h


def bowl(lat0, lon0, half, n, clat, clon, D, depth):
    """A complex crater's broad shape (m): a flat-bottomed bowl `depth` below the surroundings, its rim raised ~1/5 of
    that and falling off outside; centred where the crater is on the patch's grid."""
    p0, l0, p, l = map(np.radians, (lat0, lon0, clat, clon))
    c = np.arccos(np.clip(np.sin(p0) * np.sin(p) + np.cos(p0) * np.cos(p) * np.cos(l - l0), -1, 1)); k = c / max(np.sin(c), 1e-9)
    cx = R_MERC * k * np.cos(p) * np.sin(l - l0) / 1e3
    cy = R_MERC * k * (np.cos(p0) * np.sin(p) - np.sin(p0) * np.cos(p) * np.cos(l - l0)) / 1e3
    x = np.linspace(-half, half, n)[None, :] - cx; y = np.linspace(half, -half, n)[:, None] - cy
    r = np.hypot(x, y) / (D / 2)
    rim = 0.2 * depth
    inside = -depth + (depth + rim) * np.clip((r - 0.55) / 0.45, 0, 1) ** 2
    outside = rim * np.exp(-(r - 1) / 0.35)
    return (np.where(r < 1, inside, outside) * 1e3).astype(np.float32)


def build(site):
    S = SITES[site]; lat0, lon0, half, EX = S['lat'], S['lon'], S['half'], S['ex']
    out = os.path.join(WORK, site); os.makedirs(out, exist_ok=True)
    lat, lon = grid_latlon(lat0, lon0, half, NH)
    print(site, 'heights…', flush=True)
    dem, dbox = cached('dem', site, lambda: fetch_box(DEM, lat, lon))
    print(site, 'brightness…', flush=True)
    bdr, bbox = cached('bdr', site, lambda: fetch_box(BDR, lat, lon))

    step = 2 * half * 1e3 / (NH - 1)
    dem = np.where(dem < -20000, np.median(dem), dem)
    h = sample(dem, dbox, lat, lon)
    h = gblur(h, 10e3 / step)                                             # the global heights: only their broad shape is real

    print(site, 'albedo…', flush=True)
    loi, lbox = cached('loi', site, lambda: fetch_box(LOI, lat, lon))
    b = sample(bdr, bbox, lat, lon); o = sample(loi, lbox, lat, lon)
    ok = (b > 1) & (o > 1)
    h = h + relief(b, o, ok, step) + sum(bowl(lat0, lon0, half, NH, *c) for c in S.get('bowls', []))
    hb = h
    gy, gx = np.gradient(hb, step, step)
    nrm = np.dstack([-gx, gy, np.ones_like(h)])                            # x east, y north, z up
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, 'normal.png'))
    h.astype('<f4').tofile(os.path.join(out, 'height.bin'))
    x = (np.arange(NH) - (NH - 1) / 2) * step
    hc = (h * EX - (x[None, :] ** 2 + x[:, None] ** 2) / (2 * R_MERC)).astype(np.float32)
    print(site, 'shadows…', flush=True)
    shadows(hc, step, S['az'], S['el']).save(os.path.join(out, 'shadow.png'))
    for i, e in enumerate(S.get('els', [])):
        shadows(hc, step, S['az'], e).save(os.path.join(out, f'shadow_{i}.png'))
    if S.get('ice'):
        # permanent shadow: dark wherever the Sun can stand here. Near the pole (no axial tilt) it circles the sky low:
        # highest at local noon (90° − latitude, plus its 0.7° half-width), dipping below the horizon toward midnight
        lit_ever = np.zeros((NH, NH), np.float32)
        for az in range(100, 261, 10):
            el = (90 - abs(lat0)) * np.cos(np.radians(az - 180)) + 0.7
            if el <= 0.05: continue
            lit_ever = np.maximum(lit_ever, np.asarray(shadows(hc, step, az, el, blur=0), np.float32) / 255)
        ice = 1 - lit_ever
        ice = gblur(ice, 2.0)
        Image.fromarray((np.clip(ice, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, 'ice.png'))
        print(site, f'permanent shadow: {ice.mean() * 100:.1f}% of the patch', flush=True)

    # Mercury's ground: dark grey with the faintest warm-brown tint (albedo ~0.1, darker than the Moon's highlands): the
    # LOI albedo (its fine detail kept gently), the exposure is set in the renderer
    fill = np.where(o > 1, o, np.median(o[o > 1]))
    blur = lambda a, r: np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)
    broad = blur(fill, max(3, 1500 / step))
    fine = np.clip(fill / np.maximum(blur(fill, max(2, 900 / step)), 1), 0.75, 1.3)
    lum = broad * (1 + 0.5 * (fine - 1))
    lo, hi = np.percentile(lum, 1), np.percentile(lum, 99.5)
    k = np.clip((lum - lo) / max(hi - lo, 1), 0, 1)
    v = 70 + 150 * k
    col = np.dstack([v * 1.03, v * 1.0, v * 0.95])
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, 'colour.jpg'), quality=92)
    json.dump({'lat': lat0, 'lon': lon0, 'half': half, 'n': NH, 'dx': step, 'dy': step, 'hmin': float(h.min()),
               'hmax': float(h.max()), 'R': R_MERC, 'ex': EX, 'sun': sun_vector(S['az'], S['el']), 'az': S['az'], 'el': S['el'],
               'els': S.get('els', []), 'ice': bool(S.get('ice'))}, open(os.path.join(out, 'meta.json'), 'w'))
    i = np.unravel_index(np.argmax(h), h.shape); j = np.unravel_index(np.argmin(h), h.shape)
    print(site, f'{NH} grid, {step:.0f} m steps, {h.min():.0f}…{h.max():.0f} m; highest {(i[1] - NH / 2) * step / 1e3:.0f} km E '
          f'{(i[0] - NH / 2) * step / 1e3:.0f} km S, lowest {(j[1] - NH / 2) * step / 1e3:.0f} km E {(j[0] - NH / 2) * step / 1e3:.0f} km S', flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:] or SITES: build(s)
