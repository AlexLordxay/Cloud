# The maps of today's Earth for «Що, якби Місяць упав на Землю?», all 8192 × 4096, plate carrée like the site's maps
# (x from 180° W eastwards, y from the north pole down):
#   work/moonfall/maps/color.jpg   the site's detailed day map (level 2, NASA Blue Marble), halved
#   work/moonfall/maps/night.jpg   the site's city lights (level n3, NASA Black Marble), quartered
#   work/moonfall/maps/clouds.jpg  NASA Visible Earth cloud map (cloud_combined_8192)
#   work/moonfall/maps/hgt.png     R, G: height of the ground or the sea floor, metres, in two linear parts so the GPU's
#                                  filtering stays exact: h = 64 (R − 128) + (G − 128) / 4 (−8 km … +8 km, 0.25 m steps);
#                                  B: the sea as the day map shows it (255), for the coasts to match the picture
# Heights: Mapzen/Tilezen terrain tiles (Terrarium, zoom 5, ~4.9 km per pixel at the equator; sources SRTM, GMTED2010,
# ETOPO1 and others), AWS open data. Beyond the mercator limit (±85°) the last row is repeated.
#   python3 scenes/moonfall/maps.py
import math, os, subprocess, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
TEX = os.path.abspath(os.path.join(TOOLS, '../../planetarium/textures'))
WORK = os.path.join(TOOLS, 'work', 'moonfall'); DL = os.path.join(WORK, 'dl'); OUT = os.path.join(WORK, 'maps')
W, H = 8192, 4096
Z = 5
TERR = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
CLOUDS = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57747/cloud_combined_8192.tif'


def mosaic(level, nx, ny, step):
    """The site's chunks of one level glued together, scaled down by `step`."""
    d = os.path.join(TEX, 'earth', level)
    cw = 2048 // step
    im = Image.new('RGB', (nx * cw, ny * cw))
    for x in range(nx):
        for y in range(ny):
            im.paste(Image.open(os.path.join(d, f'{x}_{y}.jpg')).convert('RGB').resize((cw, cw), Image.LANCZOS), (x * cw, y * cw))
    return im


def terrarium():
    n = 2 ** Z
    td = os.path.join(DL, f'terr{Z}'); os.makedirs(td, exist_ok=True)
    def get(xy):
        x, y = xy; f = os.path.join(td, f'{x}_{y}.png')
        for attempt in range(6):                                          # the proxy drops a request now and then
            if os.path.exists(f) and os.path.getsize(f) > 100: return f
            subprocess.run(['curl', '-sS', '-m', '60', '-o', f, TERR.format(z=Z, x=x, y=y)])
            time.sleep(2 ** attempt * 0.5)
        raise RuntimeError('tile failed: ' + f)
    with ThreadPoolExecutor(16) as ex: list(ex.map(get, [(x, y) for x in range(n) for y in range(n)]))
    merc = np.zeros((n * 256, n * 256), np.float32)
    for x in range(n):
        for y in range(n):
            a = np.asarray(Image.open(os.path.join(td, f'{x}_{y}.png')).convert('RGB'), np.float32)
            merc[y * 256:(y + 1) * 256, x * 256:(x + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    # to plate carrée: each output row's latitude → mercator row (bilinear in y; x is the same longitude spacing)
    N = n * 256
    lat = 90 - (np.arange(H) + 0.5) * 180 / H
    lim = math.degrees(math.atan(math.sinh(math.pi)))
    la = np.radians(np.clip(lat, -lim + 1e-4, lim - 1e-4))
    py = (1 - np.log(np.tan(la) + 1 / np.cos(la)) / math.pi) / 2 * N - 0.5
    y0 = np.clip(np.floor(py).astype(int), 0, N - 2); fy = np.clip(py - y0, 0, 1)[:, None]
    rows = merc[y0] * (1 - fy) + merc[y0 + 1] * fy                         # H × N
    px = (np.arange(W) + 0.5) * N / W - 0.5
    x0 = np.clip(np.floor(px).astype(int), 0, N - 2); fx = np.clip(px - x0, 0, 1)[None, :]
    return rows[:, x0] * (1 - fx) + rows[:, x0 + 1] * fx


def main():
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(os.path.join(OUT, 'color.jpg')):
        mosaic('2', 8, 4, 1).resize((W, H), Image.LANCZOS).save(os.path.join(OUT, 'color.jpg'), quality=93)
        print('color.jpg')
    if not os.path.exists(os.path.join(OUT, 'night.jpg')):
        mosaic('n3', 16, 8, 4).resize((W, H), Image.LANCZOS).save(os.path.join(OUT, 'night.jpg'), quality=93)
        print('night.jpg')
    if not os.path.exists(os.path.join(OUT, 'clouds.jpg')):
        tif = os.path.join(DL, 'cloud_combined_8192.tif')
        if not os.path.exists(tif):
            os.makedirs(DL, exist_ok=True)
            subprocess.run(['curl', '-sS', '-C', '-', '-o', tif, CLOUDS], check=True)
        Image.open(tif).convert('L').resize((W, H), Image.LANCZOS).save(os.path.join(OUT, 'clouds.jpg'), quality=92)
        print('clouds.jpg')
    h = terrarium()
    sea = np.asarray(Image.open(os.path.join(TEX, 'earth_specular.jpg')).convert('L').resize((W, H), Image.BILINEAR), np.float32)
    hq = np.clip(h, -8000, 8000)
    r = np.clip(np.round(hq / 64) + 128, 0, 255)
    g = np.clip(np.round((hq - 64 * (r - 128)) * 4 + 128), 0, 255)
    b = np.where(sea > 100, 255, 0)
    Image.fromarray(np.stack([r, g, b], -1).astype(np.uint8)).save(os.path.join(OUT, 'hgt.png'))
    print('hgt.png', f'{h.min():.0f}…{h.max():.0f} m')
    for name, la, lo in [('Київ', 50.45, 30.52), ('Говерла', 48.16, 24.50), ('Еверест', 27.99, 86.93), ('Нідерланди', 52.2, 5.3), ('Чорне море', 43.0, 34.0), ('Маріанська западина', 11.35, 142.2)]:
        y = int((90 - la) / 180 * H); x = int((lo + 180) / 360 * W)
        print(f'  {name}: {h[y, x]:.0f} m (sea mask {b[y, x]})')


if __name__ == '__main__':
    main()
