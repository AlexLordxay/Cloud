# The overlay for the globe (globe.js): Ukraine's outline laid on the Caloris basin at its true size, and the basin's
# rim (1550 km across) — drawn on an equirectangular map like the planet's (lon -180…180 left to right, lat 90…-90).
# Ukraine is taken off the Earth with an azimuthal equidistant projection round its middle (true kilometres from there)
# and put back the same way round the basin's centre on Mercury.   python3 scenes/mercury_meet/overlay.py
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '..', '..', 'work', 'mercury_meet')
R_E, R_M = 6371.0, 2439.4
CAL = (31.5, 162.7)                    # the basin's centre (MESSENGER)
UA0 = (48.4, 31.2)                     # the middle of Ukraine
W, H = 8192, 4096


def to_xy(lat, lon, c, R):
    """azimuthal equidistant: km east, km north of centre c"""
    p0, l0, p, l = map(math.radians, (c[0], c[1], lat, lon))
    cc = math.acos(max(-1, min(1, math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l - l0))))
    k = cc / math.sin(cc) if cc > 1e-9 else 1
    return R * k * math.cos(p) * math.sin(l - l0), R * k * (math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0))


def from_xy(x, y, c, R):
    rho = math.hypot(x, y); cc = rho / R
    p0, l0 = math.radians(c[0]), math.radians(c[1])
    if rho < 1e-9: return c
    lat = math.asin(math.cos(cc) * math.sin(p0) + y * math.sin(cc) * math.cos(p0) / rho)
    lon = l0 + math.atan2(x * math.sin(cc), rho * math.cos(p0) * math.cos(cc) - y * math.sin(p0) * math.sin(cc))
    return math.degrees(lat), (math.degrees(lon) + 180) % 360 - 180


def px(lat, lon):
    lon = lon if lon > CAL[1] - 180 else lon + 360          # unwrapped round the basin (it sits near the date line)
    return ((lon + 180) / 360 * W, (90 - lat) / 180 * H)


g = json.load(open(os.path.join(WORK, 'geo', 'ukraine.json')))
base = [[px(*from_xy(*to_xy(la, lo, UA0, R_E), CAL, R_M)) for lo, la in ring[0]] for ring in g['coordinates']]
# drawn twice, a map-width apart, so the part past the date line lands on the left edge
polys = base + [[(x - W, y) for x, y in p] for p in base]
ew = [to_xy(la, lo, UA0, R_E)[0] for lo, la in g['coordinates'][0][0]]
print(f'Ukraine east–west: {max(ew) - min(ew):.0f} km; Caloris: 1550 km')
im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
fill = Image.new('RGBA', (W, H), (0, 0, 0, 0)); df = ImageDraw.Draw(fill)
for p in polys: df.polygon(p, fill=(255, 213, 0, 90))                       # yellow, see-through
glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dg = ImageDraw.Draw(glow)
for p in polys: dg.line(p + [p[0]], fill=(255, 213, 0, 255), width=14)
im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
im.alpha_composite(fill)
d = ImageDraw.Draw(im)
for p in polys: d.line(p + [p[0]], fill=(255, 226, 80, 255), width=6)
# the rim: a dashed circle 775 km from the centre
rim = [px(*from_xy(775 * math.sin(a), 775 * math.cos(a), CAL, R_M)) for a in np.linspace(0, 2 * math.pi, 721)]
for off in (0, -W):
    for i in range(0, 720, 8):
        d.line([(x + off, y) for x, y in rim[i:i + 5]], fill=(110, 190, 255, 230), width=7)
im.save(os.path.join(WORK, 'overlay.png'))
print('overlay.png written')
