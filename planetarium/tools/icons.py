# Site icons from the logo's star ✦ (gold → pink → blue on deep navy), variant A chosen by the author (6.10.2026).
#
#   python3 icons.py      → ../favicon.ico (16/32/48), ../icon.svg (crisp tab icon), ../apple-touch-icon.png (180, iPhone)
import math, os
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
STOPS = [(0.0, (247, 198, 107)), (0.52, (243, 154, 139)), (1.0, (156, 194, 255))]   # the logo's gradient
S, P, R = 1024, 2.7, 0.36   # master size; star = superellipse |x|^(2/P)+|y|^(2/P)=1, radius R of the size

def star_points(cx, cy, r, n=720):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n; c, s = math.cos(t), math.sin(t)
        pts.append((cx + math.copysign(abs(c) ** P, c) * r, cy + math.copysign(abs(s) ** P, s) * r))
    return pts

def master():
    img = Image.new('RGB', (S, S)); d = ImageDraw.Draw(img)
    for r in range(S, 0, -4):   # radial background: lighter navy in the middle
        k = r / S; c = tuple(int(a + (b - a) * k) for a, b in zip((22, 32, 62), (4, 6, 12)))
        d.ellipse([S/2 - r*0.75, S/2 - r*0.75, S/2 + r*0.75, S/2 + r*0.75], fill=c)
    g = Image.new('RGB', (S, S)); px = g.load(); a = math.radians(35)
    for y in range(S):
        for x in range(S):
            u = min(1, max(0, ((x - S/2) * math.cos(a) + (y - S/2) * math.sin(a)) / (S * 0.75) + 0.5))
            for (p, c1), (q, c2) in zip(STOPS, STOPS[1:]):
                if p <= u <= q:
                    k = (u - p) / (q - p); px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))
    m = Image.new('L', (S, S)); ImageDraw.Draw(m).polygon(star_points(S/2, S/2, S*R), fill=255)
    img.paste((170, 205, 255), (0, 0), m.filter(ImageFilter.GaussianBlur(S*0.06)).point(lambda v: int(v * 0.55)))
    img.paste(g, (0, 0), m)
    return img

img = master()
img.resize((180, 180), Image.LANCZOS).save(os.path.join(OUT, 'apple-touch-icon.png'), optimize=True)
img.resize((48, 48), Image.LANCZOS).save(os.path.join(OUT, 'favicon.ico'), sizes=[(16, 16), (32, 32), (48, 48)])

# Vector version for browsers that take SVG: sharp at any size.
path = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in star_points(32, 32, 64 * R, 96)) + 'Z'
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><radialGradient id="b"><stop offset="0" stop-color="#16203e"/><stop offset="1" stop-color="#04060c"/></radialGradient>
<linearGradient id="g" x1="0.1" y1="0.15" x2="0.9" y2="0.85"><stop offset="0" stop-color="#f7c66b"/><stop offset="0.52" stop-color="#f39a8b"/><stop offset="1" stop-color="#9cc2ff"/></linearGradient></defs>
<rect width="64" height="64" rx="14" fill="url(#b)"/><path d="{path}" fill="url(#g)"/></svg>
'''
open(os.path.join(OUT, 'icon.svg'), 'w').write(svg)
print('icons written')
