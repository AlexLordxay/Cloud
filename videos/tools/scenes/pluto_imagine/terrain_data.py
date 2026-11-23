# Pluto's terrain round a site for «А ти уявляєш Плутон так?», from the USGS global New Horizons products (public domain;
# Schenk et al. 2018), reading only the patch round the site over HTTP (mars_meet/rangetiff.py):
#   heights    — Pluto_NewHorizons_Global_DEM_300m_Jul2017_16bit (metres, int16, nodata −32768);
#   brightness — Pluto_NewHorizons_Global_Mosaic_300m_Jul2017_8bit (LORRI/MVIC panchromatic).
# Both are simple-cylindrical, 300 m/pixel, longitude 0…360° east with 180° in the middle (Sputnik Planitia sits there).
# Colour: the mosaic's detail tinted with the site's colour map (planetarium/textures/pluto.jpg, from MVIC colour).
# Shadows baked for the site's Sun from the exaggerated heights bent to the curvature (as mercury_meet/terrain_data.py).
#   python3 scenes/pluto_imagine/terrain_data.py [site] -> work/pluto_imagine/<site>/{height.bin, colour.jpg, normal.png, shadow.png, meta.json}
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mars_meet')); sys.path.insert(0, os.path.join(HERE, '..', 'mercury_meet'))
from rangetiff import window
Image.MAX_IMAGE_PIXELS = None
TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'pluto_imagine')
SITE_TEX = os.path.join(TOOLS, '..', '..', 'planetarium', 'textures', 'pluto.jpg')
USGS = 'https://planetarymaps.usgs.gov/mosaic/'
DEM = USGS + 'Pluto_NewHorizons_Global_DEM_300m_Jul2017_16bit.tif'
MOS = USGS + 'Pluto_NewHorizons_Global_Mosaic_300m_Jul2017_8bit.tif'
R_PLUTO = 1188.3e3
PPD = 24888 / 360.0                  # pixels per degree of both mosaics
NH = 4096
SITES = {
    # Tenzing Montes (peaks to ~6 km) on the south-west shore of Sputnik Planitia, the low Sun from the east
    'tenzing': dict(lat=-15.0, lon=176.5, half=110, az=70, el=14.0, ex=1.2, demblur=320, crag=380),
    # Hillary Montes and the shore of the nitrogen-ice plain (the "heart"), seen from higher
    'hillary': dict(lat=2.0, lon=170.0, half=260, az=100, el=9.0, ex=1.4, demblur=700),
    # Sputnik Planitia itself: the convection cells of nitrogen ice, the mountains along its western shore
    'sputnik': dict(lat=15.0, lon=178.0, half=650, az=95, el=12.0, ex=2.0, demblur=1500),
}

import importlib.util
spec = importlib.util.spec_from_file_location('mtd', os.path.join(HERE, '..', 'mercury_meet', 'terrain_data.py'))
_m = importlib.util.module_from_spec(spec); spec.loader.exec_module(_m)
gblur, shadows, sun_vector, sample = _m.gblur, _m.shadows, _m.sun_vector, _m.sample


def grid_latlon(lat0, lon0, half, n):
    """Inverse azimuthal equidistant: rows north → south, columns west → east; longitudes 0…360 east."""
    x = np.linspace(-half, half, n)[None, :] * 1e3
    y = np.linspace(half, -half, n)[:, None] * 1e3
    rho = np.maximum(np.hypot(x, y), 1e-6); c = rho / R_PLUTO
    p0, l0 = np.radians(lat0), np.radians(lon0)
    lat = np.arcsin(np.cos(c) * np.sin(p0) + y * np.sin(c) * np.cos(p0) / rho)
    lon = l0 + np.arctan2(x * np.sin(c), rho * np.cos(p0) * np.cos(c) - y * np.sin(p0) * np.sin(c))
    return np.degrees(lat), np.degrees(lon) % 360


def fetch(url, lat, lon):
    la0, la1 = float(lat.min()) - 0.05, float(lat.max()) + 0.05
    lo0, lo1 = float(lon.min()) - 0.05, float(lon.max()) + 0.05
    r0, r1 = int((90 - la1) * PPD), int(np.ceil((90 - la0) * PPD))
    c0, c1 = int(lo0 * PPD), int(np.ceil(lo1 * PPD))
    img, _ = window(url, r0, r1, c0, c1)
    return img, (90 - r0 / PPD, 90 - r1 / PPD, c0 / PPD, c1 / PPD)


def cached(name, site, f):
    p = os.path.join(WORK, site, f'raw_{name}.npz')
    if not os.path.exists(p):
        img, box = f(); np.savez(p, img=img, box=np.array(box))
    z = np.load(p); return z['img'], tuple(z['box'])


def band_noise(n, step, lam_lo, lam_hi, seed):
    """Gaussian noise with wavelengths between lam_hi and lam_lo (m), unit variance (FFT band-pass)."""
    r = np.random.default_rng(seed)
    f = np.hypot(np.fft.fftfreq(n, step)[:, None], np.fft.fftfreq(n, step)[None, :])
    spec = np.fft.fft2(r.normal(size=(n, n)).astype(np.float32))
    m = np.exp(-(f * lam_hi) ** 2) * (1 - np.exp(-(f * lam_lo) ** 2))
    a = np.real(np.fft.ifft2(spec * m)).astype(np.float32)
    return a / (a.std() + 1e-9)


def crags(n, step, seed):
    """Ridged multifractal detail (m, ~0 mean): sharp crests and gullies at 3 km → 100 m, the steep blocky look of the
    water-ice mountains that the 300 m heights smooth away. Artistic, not measured."""
    out = np.zeros((n, n), np.float32); amp = 1.0
    for i, (lo, hi) in enumerate([(5000, 1600), (1800, 600), (700, 260)]):
        b = band_noise(n, step, lo, hi, seed + i)
        r = 1 - np.abs(np.tanh(b))                        # ridges where the noise crosses zero
        out += (r ** 2 - 0.35) * amp; amp *= 0.45
    return gblur(out, 1.2)


def build(site):
    S = SITES[site]; lat0, lon0, half, EX = S['lat'], S['lon'], S['half'], S['ex']
    out = os.path.join(WORK, site); os.makedirs(out, exist_ok=True)
    lat, lon = grid_latlon(lat0, lon0, half, NH)
    print(site, 'heights…', flush=True)
    dem, dbox = cached('dem', site, lambda: fetch(DEM, lat, lon))
    dem = dem.astype(np.float32); bad = dem < -30000
    if bad.any(): dem[bad] = np.median(dem[~bad])
    print(site, 'brightness…', flush=True)
    mos, mbox = cached('mos', site, lambda: fetch(MOS, lat, lon))
    step = 2 * half * 1e3 / (NH - 1)
    h = gblur(sample(dem, dbox, lat, lon), S['demblur'] / step)
    b = sample(mos.astype(np.float32), mbox, lat, lon)
    # a touch of fine relief from the mosaic's own detail (only the small scales; the DEM holds the shapes)
    lb = np.log(np.maximum(b, 1)); fine = lb - gblur(lb, 2500 / step)
    h = h + np.clip(fine, -0.6, 0.6) * 140.0
    # mountains get crags: where the ground stands above the plain or is steep
    base = gblur(h, 2000 / step)
    gy0, gx0 = np.gradient(base, step, step); slope = np.hypot(gx0, gy0)
    plain = np.percentile(base, 20)
    mask = np.clip((base - plain) / 1500, 0, 1) * 0.7 + np.clip(slope / 0.25, 0, 1) * 0.6
    mask = np.clip(gblur(mask, 1500 / step), 0, 1)
    cr = crags(NH, step, 7)
    h = h + cr * (S.get('crag', 700) * mask + 40 * (1 - mask))
    gy, gx = np.gradient(h, step, step)
    nrm = np.dstack([-gx, gy, np.ones_like(h)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    Image.fromarray(((nrm * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, 'normal.png'))
    h.astype('<f4').tofile(os.path.join(out, 'height.bin'))
    x = (np.arange(NH) - (NH - 1) / 2) * step
    hc = (h * EX - (x[None, :] ** 2 + x[:, None] ** 2) / (2 * R_PLUTO)).astype(np.float32)
    print(site, 'shadows…', flush=True)
    shadows(hc, step, S['az'], S['el']).save(os.path.join(out, 'shadow.png'))
    # colour: the site's colour map (hue, broad) × the mosaic's albedo detail. The mosaic already carries the
    # flyby's own shading in places; it is flattened a little so the baked Sun does the lighting.
    tex = np.asarray(Image.open(SITE_TEX).convert('RGB'), np.float32)
    th, tw = tex.shape[:2]
    rr = np.clip(((90 - lat) / 180 * th).astype(int), 0, th - 1)
    # the site's map: x from −180 (left) east? it follows planetarium convention — longitude 0 in the middle
    cc = np.clip((((lon + 180) % 360) / 360 * tw).astype(int), 0, tw - 1)
    hue = gblur(tex[rr, cc], 6.0) if False else np.dstack([gblur(tex[rr, cc][..., k], 8.0) for k in range(3)])
    alb = b / np.maximum(gblur(b, 6000 / step), 1)
    alb = np.clip(alb, 0.55, 1.6) ** 0.8
    base = hue / np.maximum(hue.mean(axis=2, keepdims=True), 1)          # tint only
    lum = np.clip(gblur(b, 1500 / step), 1, 255)
    lum = 125 + 85 * (lum - np.percentile(lum, 2)) / max(np.percentile(lum, 99.5) - np.percentile(lum, 2), 1)
    col = base * (lum * alb * (1 + 0.10 * np.clip(cr, -1.5, 1.5) * mask))[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, 'colour.jpg'), quality=92)
    json.dump({'lat': lat0, 'lon': lon0, 'half': half, 'n': NH, 'dx': step, 'dy': step, 'hmin': float(h.min()),
               'hmax': float(h.max()), 'R': R_PLUTO, 'ex': EX, 'sun': sun_vector(S['az'], S['el']), 'az': S['az'], 'el': S['el'],
               'els': [], 'ice': False}, open(os.path.join(out, 'meta.json'), 'w'))
    i = np.unravel_index(np.argmax(h), h.shape)
    print(site, f'{step:.0f} m steps, {h.min():.0f}…{h.max():.0f} m; highest {(i[1] - NH / 2) * step / 1e3:.0f} km E '
          f'{(i[0] - NH / 2) * step / 1e3:.0f} km S', flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:] or SITES: build(s)
