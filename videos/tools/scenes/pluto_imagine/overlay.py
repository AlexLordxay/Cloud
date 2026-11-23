# Ukraine's outline WITH Crimea laid on Pluto's heart at true size (azimuthal equidistant off the Earth round Ukraine's
# middle, back onto Pluto round the heart's middle), on an equirectangular map in the globe's convention (longitude
# 0…360° east left → right): yellow see-through fill, bright edge. Data as in mercury_meet/overlay.py (Natural Earth via
# datasets/geo-countries, Crimea taken from Russia's shape and joined back).   python3 scenes/pluto_imagine/overlay.py
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '..', '..', 'work', 'pluto_imagine')
R_E, R_P = 6371.0, 1188.3
HEART = (18.0, 192.0)                  # the middle of Tombaugh Regio (~1 590 km across)
UA0 = (48.4, 31.2)
W, H = 8192, 4096
sys.path.insert(0, os.path.join(HERE, '..', 'mercury_meet'))

def to_xy(lat, lon, c, R):
    p0, l0, p, l = map(math.radians, (c[0], c[1], lat, lon))
    cc = math.acos(max(-1, min(1, math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l - l0))))
    k = cc / math.sin(cc) if cc > 1e-9 else 1
    return R * k * math.cos(p) * math.sin(l - l0), R * k * (math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0))

def from_xy(x, y, c, R):
    rho = math.hypot(x, y); cc = rho / R; p0, l0 = math.radians(c[0]), math.radians(c[1])
    if rho < 1e-9: return c
    lat = math.asin(math.cos(cc) * math.sin(p0) + y * math.sin(cc) * math.cos(p0) / rho)
    lon = l0 + math.atan2(x * math.sin(cc), rho * math.cos(p0) * math.cos(cc) - y * math.sin(p0) * math.sin(cc))
    return math.degrees(lat), math.degrees(lon) % 360

def ukraine():
    from shapely.geometry import shape, Polygon
    from shapely.ops import unary_union
    d = json.load(open(os.path.join(WORK, 'geo', 'countries.geojson')))
    nm = lambda f: f['properties'].get('name') or f['properties'].get('ADMIN') or f['properties'].get('NAME')
    feat = {nm(f): f for f in d['features']}
    rus = feat['Russia']['geometry']['coordinates']
    crimea = [Polygon(r[0]) for r in rus if 44 < min(p[1] for p in r[0]) and max(p[1] for p in r[0]) < 46.3 and 32 < min(p[0] for p in r[0]) and max(p[0] for p in r[0]) < 37]
    assert len(crimea) == 1, 'Crimea not found'
    u = unary_union([shape(feat['Ukraine']['geometry']).buffer(0), crimea[0].buffer(0)]).buffer(0.002).buffer(-0.002)
    parts = sorted(u.geoms if u.geom_type == 'MultiPolygon' else [u], key=lambda p: -p.area)
    return [list(p.exterior.coords) for p in parts]

rings = ukraine()
px = lambda la, lo: (lo / 360 * W, (90 - la) / 180 * H)
polys = [[px(*from_xy(*to_xy(la, lo, UA0, R_E), HEART, R_P)) for lo, la in r] for r in rings]
ew = [to_xy(la, lo, UA0, R_E)[0] for lo, la in rings[0]]
print(f'Ukraine east–west {max(ew) - min(ew):.0f} km (with Crimea, {len(rings)} parts)')
im = Image.new('RGBA', (W, H)); fill = Image.new('RGBA', (W, H)); df = ImageDraw.Draw(fill)
for p in polys: df.polygon(p, fill=(255, 213, 0, 95))
glow = Image.new('RGBA', (W, H)); dg = ImageDraw.Draw(glow)
for p in polys: dg.line(p + [p[0]], fill=(255, 213, 0, 255), width=12)
im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(8))); im.alpha_composite(fill)
d = ImageDraw.Draw(im)
for p in polys: d.line(p + [p[0]], fill=(255, 228, 90, 255), width=5)
im.save(os.path.join(WORK, 'overlay.png'))
print('overlay.png written')
