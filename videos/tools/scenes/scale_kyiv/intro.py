# The opening of "scale_kyiv": a pull-back straight up from Maidan Nezalezhnosti in Kyiv, from ~5 km of ground on the
# screen to ~3000 km, on real satellite pictures (EOxCloudless 2017, Sentinel-2, CC BY 4.0). The 3D flight takes over
# from there (cam.js, "intro"), crossfaded in post.py.
#
#   python3 scenes/scale_kyiv/intro.py      -> work/scale_kyiv/intro/f_00000.jpg … (720×1280, 30 fps)
#
# Tiles are cached in work/scale_kyiv/tiles/. For each frame the ground span on the screen is chosen (log scale), the two
# nearest zoom levels are cut out around Maidan and blended by the fractional level, so the picture never jumps.
import math, os, sys, urllib.request
from io import BytesIO
from PIL import Image

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'scale_kyiv')
LAT, LON = 50.4501, 30.5234                     # Maidan Nezalezhnosti
W, H, FPS = 720, 1280, 30
SPAN0, SPAN1 = 5_000.0, 3_000_000.0             # metres of ground across the screen's height, first and last frame
DUR = 5.8                                       # seconds of the zoom (the crossfade to 3D is in its last 0.8 s)
ZMAX, ZMIN = 14, 5                              # 10 m pictures: zoom 14 is the finest worth fetching
URL = 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2017_3857/default/g/{z}/{y}/{x}.jpg'
EARTH = 40075016.686                            # metres round the equator (web mercator)


def world_px(lat, lon, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def tile(z, x, y):
    path = os.path.join(WORK, 'tiles', f'{z}_{x}_{y}.jpg')
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(URL.format(z=z, x=x, y=y), headers={'User-Agent': 'nebozvid-video/1.0'})
        data = urllib.request.urlopen(req, timeout=30).read()
        open(path, 'wb').write(data)
    return Image.open(path).convert('RGB')


_mosaics = {}
def mosaic(z):
    """The picture around Maidan at zoom z, wide enough for the coarsest use of this level (2 picture px per screen px)."""
    if z in _mosaics: return _mosaics[z]
    cx, cy = world_px(LAT, LON, z)
    hw, hh = W * 1.1, H * 1.1                     # half size in picture px (2× the screen, plus a margin)
    x0, x1 = int((cx - hw) // 256), int((cx + hw) // 256)
    y0, y1 = int((cy - hh) // 256), int((cy + hh) // 256)
    img = Image.new('RGB', ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256))
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            img.paste(tile(z, tx, ty), ((tx - x0) * 256, (ty - y0) * 256))
    _mosaics[z] = (img, cx - x0 * 256, cy - y0 * 256)
    return _mosaics[z]


def view(z, mpp):
    """Screen-sized cut of level z at mpp metres per screen pixel, centred on Maidan."""
    img, cx, cy = mosaic(z)
    native = EARTH * math.cos(math.radians(LAT)) / (256 * 2 ** z)   # ground metres per picture pixel here
    k = mpp / native                                                 # picture px per screen px
    box = (cx - W / 2 * k, cy - H / 2 * k, cx + W / 2 * k, cy + H / 2 * k)
    return img.resize((W, H), Image.LANCZOS, box=box)


def main():
    out = os.path.join(WORK, 'intro'); os.makedirs(out, exist_ok=True)
    n = int(round(DUR * FPS))
    for i in range(n):
        u = i / (n - 1)
        e = u ** 1.6                                                 # lift off gently, then faster and faster
        span = math.exp(math.log(SPAN0) + (math.log(SPAN1) - math.log(SPAN0)) * e)
        mpp = span / H
        zf = math.log2(EARTH * math.cos(math.radians(LAT)) / (256 * mpp))   # level whose pixel matches the screen
        zf = max(ZMIN, min(ZMAX, zf))
        z0 = int(math.floor(zf)); f = zf - z0
        a = view(z0, mpp)
        if f > 0.01 and z0 + 1 <= ZMAX: a = Image.blend(a, view(z0 + 1, mpp), f)
        a.save(os.path.join(out, f'f_{i:05d}.jpg'), quality=92)
        if i % 30 == 0: print('intro frame', i, '/', n, f'span {span / 1000:.0f} km, zoom {zf:.2f}', flush=True)
    print('intro written:', n, 'frames')


if __name__ == '__main__':
    main()
