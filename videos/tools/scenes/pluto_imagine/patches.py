# Two relief patches for the continuous flight (world3d.js), laid exactly on the sphere so the camera can come down
# from space without a cut: 'heart' — the whole of Sputnik Planitia and its western shore (700 km either side, 342 m
# steps), 'tenzing' — Tenzing Montes in close-up (110 km, 54 m). Data: the USGS New Horizons DEM and mosaic (300 m/px),
# read by window (terrain_data.fetch). The 300 m heights smooth the mountains, so on high or steep ground a ridged
# fractal adds crests and gullies at 5 km → 260 m (artistic detail; the shapes of the ranges are the real ones).
# Each patch: height.bin (m, the patch's own grid, rows north → south), normal.png (WORLD normals: x toward lon 0,
# y north, z toward lon −90°, with the heights exaggerated by EX), colour.jpg (the globe's colouring, so the seams
# vanish), shadow.png (baked for the shared Sun), meta.json. Edges: heights taper to the datum (the globe sphere) at the
# heart's border, and the close-up's border blends into the heart patch's heights and colour.
#   python3 scenes/pluto_imagine/patches.py [heart|tenzing]
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import terrain_data as T
Image.MAX_IMAGE_PIXELS = None
WORK = T.WORK
R = T.R_PLUTO
SUN = (20.0, 240.0)                  # the subsolar point (lat, lon east): low light on Tenzing, the heart lit
EX = 1.3
NH = 4096
PATCHES = {
    'heart':   dict(lat=12.0, lon=178.0, half=700, crag=260, demblur=900, taper='globe'),
    'tenzing': dict(lat=-15.0, lon=176.5, half=110, crag=380, demblur=320, taper='heart'),
}
D = np.pi / 180

def P(lat, lon):
    return np.stack([np.cos(lat * D) * np.cos(lon * D), np.sin(lat * D), -np.cos(lat * D) * np.sin(lon * D)], -1)

def local_sun(lat, lon):
    up = P(np.array(lat), np.array(lon)); s = P(np.array(SUN[0]), np.array(SUN[1]))
    north = np.array([0, 1, 0]) - up * up[1]; north /= np.linalg.norm(north)
    east = np.cross(north, up)
    el = np.degrees(np.arcsin(s @ up)); az = np.degrees(np.arctan2(s @ east, s @ north)) % 360
    return float(az), float(el)

def to_xy(lat, lon, c):
    """azimuthal equidistant round centre c: metres east, metres north"""
    p0, l0, p, l = c[0] * D, c[1] * D, lat * D, lon * D
    cc = np.arccos(np.clip(np.sin(p0) * np.sin(p) + np.cos(p0) * np.cos(p) * np.cos(l - l0), -1, 1))
    k = np.where(cc > 1e-9, cc / np.maximum(np.sin(cc), 1e-12), 1)
    return R * k * np.cos(p) * np.sin(l - l0), R * k * (np.cos(p0) * np.sin(p) - np.sin(p0) * np.cos(p) * np.cos(l - l0))

def build(name):
    S = PATCHES[name]; lat0, lon0, half = S['lat'], S['lon'], S['half']
    out = os.path.join(WORK, name); os.makedirs(out, exist_ok=True)
    lat, lon = T.grid_latlon(lat0, lon0, half, NH)
    print(name, 'data…', flush=True)
    dem, dbox = T.cached('dem', name, lambda: T.fetch(T.DEM, lat, lon))
    dem = dem.astype(np.float32); bad = dem < -30000
    if bad.any(): dem[bad] = np.median(dem[~bad])
    mos, mbox = T.cached('mos', name, lambda: T.fetch(T.MOS, lat, lon))
    step = 2 * half * 1e3 / (NH - 1)
    h = T.gblur(T.sample(dem, dbox, lat, lon), S['demblur'] / step)
    b = T.sample(mos.astype(np.float32), mbox, lat, lon)
    lb = np.log(np.maximum(b, 1)); fine = lb - T.gblur(lb, 2500 / step)
    h = h + np.clip(fine, -0.6, 0.6) * 140.0
    base = T.gblur(h, 2000 / step)
    gy0, gx0 = np.gradient(base, step, step); slope = np.hypot(gx0, gy0)
    plain = np.percentile(base, 20)
    mask = np.clip(np.clip((base - plain) / 1500, 0, 1) * 0.7 + np.clip(slope / 0.25, 0, 1) * 0.6, 0, 1)
    mask = np.clip(T.gblur(mask, 1500 / step), 0, 1)
    cr = T.crags(NH, step, 7)
    h = h + cr * (S['crag'] * mask + 30 * (1 - mask))
    # colour exactly as the globe's (globe_tex.py): the site map's colour × the mosaic's detail on its broad brightness
    site = np.asarray(Image.open(T.SITE_TEX).convert('RGB'), np.float32)
    th, tw = site.shape[:2]
    rr = np.clip(((90 - lat) / 180 * th).astype(int), 0, th - 1); cc = np.clip((((lon + 180) % 360) / 360 * tw).astype(int), 0, tw - 1)
    srgb = np.dstack([T.gblur(site[rr, cc][..., k], 2.0 * 2000 / step) for k in range(3)])
    slum = srgb.mean(axis=2); chroma = srgb / np.maximum(slum, 1)[..., None]
    detail = np.clip(b / np.maximum(T.gblur(b, 36000 / step), 1), 0.4, 1.8)
    L = T.gblur(slum, 36000 / step) * (1 + (detail - 1) * 0.9) * (1 + 0.10 * np.clip(cr, -1.5, 1.5) * mask)
    col = chroma * L[..., None]
    # edges
    e = np.minimum(np.minimum(np.arange(NH), NH - 1 - np.arange(NH))[None, :], np.minimum(np.arange(NH), NH - 1 - np.arange(NH))[:, None]) / (NH - 1)
    if S['taper'] == 'globe':
        w = np.clip(e / 0.06, 0, 1); w = w * w * (3 - 2 * w)
        h = h * w
        glob = np.asarray(Image.open(os.path.join(WORK, 'globe.jpg')).convert('RGB'), np.float32)
        gr = np.clip(((90 - lat) / 180 * glob.shape[0]).astype(int), 0, glob.shape[0] - 1); gc = np.clip((lon / 360 * glob.shape[1]).astype(int), 0, glob.shape[1] - 1)
        col = col * w[..., None] + glob[gr, gc] * (1 - w[..., None])
    else:
        P0 = PATCHES['heart']; hm = json.load(open(os.path.join(WORK, 'heart', 'meta.json')))
        hh = np.fromfile(os.path.join(WORK, 'heart', 'height.bin'), '<f4').reshape(hm['n'], hm['n'])
        hc = np.asarray(Image.open(os.path.join(WORK, 'heart', 'colour.jpg')).convert('RGB'), np.float32)
        x, y = to_xy(lat, lon, (P0['lat'], P0['lon']))
        st = 2 * P0['half'] * 1e3 / (hm['n'] - 1)
        ci = np.clip((x / st + (hm['n'] - 1) / 2), 0, hm['n'] - 1); ri = np.clip(((hm['n'] - 1) / 2 - y / st), 0, hm['n'] - 1)
        r0 = np.floor(ri).astype(int).clip(0, hm['n'] - 2); c0 = np.floor(ci).astype(int).clip(0, hm['n'] - 2); fr = ri - r0; fc = ci - c0
        H2 = (hh[r0, c0] * (1 - fc) + hh[r0, c0 + 1] * fc) * (1 - fr) + (hh[r0 + 1, c0] * (1 - fc) + hh[r0 + 1, c0 + 1] * fc) * fr
        C2 = hc[np.round(ri).astype(int), np.round(ci).astype(int)]
        w = np.clip(e / 0.12, 0, 1); w = w * w * (3 - 2 * w)
        h = h * w + H2 * (1 - w); col = col * w[..., None] + C2 * (1 - w[..., None])
    h = h.astype(np.float32)
    h.tofile(os.path.join(out, 'height.bin'))
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(out, 'colour.jpg'), quality=93)
    # world normals of the exaggerated surface
    pos = P(lat, lon) * (R + h * EX)[..., None]
    du = np.gradient(pos, axis=1); dv = np.gradient(pos, axis=0)            # east, south
    n = np.cross(du, dv); n *= -1                                            # outward
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    up = P(lat, lon)
    if (np.sum(n * up, axis=2) < 0).mean() > 0.5: n = -n
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(out, 'normal.png'))
    az, el = local_sun(lat0, lon0)
    x = (np.arange(NH) - (NH - 1) / 2) * step
    hc = (h * EX - (x[None, :] ** 2 + x[:, None] ** 2) / (2 * R)).astype(np.float32)
    print(name, f'shadows (Sun az {az:.0f}°, el {el:.1f}°)…', flush=True)
    T.shadows(hc, step, az, el, blur=1.0).save(os.path.join(out, 'shadow.png'))
    json.dump({'lat': lat0, 'lon': lon0, 'half': half, 'n': NH, 'step': step, 'R': R, 'ex': EX, 'sun': SUN, 'az': az, 'el': el},
              open(os.path.join(out, 'meta.json'), 'w'))
    print(name, f'{step:.0f} m, {h.min():.0f}…{h.max():.0f} m', flush=True)

if __name__ == '__main__':
    for s in sys.argv[1:] or ['heart', 'tenzing']: build(s)
