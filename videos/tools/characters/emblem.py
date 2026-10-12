# The astronaut's patch: МІСІЯ and Небозвід round the rim in the site's wordmark, a big star in the middle; the wordmark (Cormorant Italic, the dawn-to-night gradient, a star over the "і", drawn
# by compose.py's logo_layer, the same code as the logo in the videos) on a round night-sky patch with a big star.
#
#   python3 characters/emblem.py   ->  characters/emblem.js  (window.__astronautEmblem = a PNG data URL)
import base64, io, math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import compose

N = 512
c = N / 2
img = Image.new('RGBA', (N, N), (0, 0, 0, 0))
# gradient rim: the logo's colours left to right
rim = Image.new('RGB', (N, N))
d = ImageDraw.Draw(rim)
for x in range(N):
    u = x / (N - 1)
    for (a, ca), (b, cb) in zip(compose.LOGO_STOPS, compose.LOGO_STOPS[1:]):
        if a <= u <= b:
            k = (u - a) / (b - a); col = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3))
    d.line([(x, 0), (x, N)], fill=col)
mask = Image.new('L', (N, N), 0); ImageDraw.Draw(mask).ellipse((4, 4, N - 4, N - 4), fill=255)
img.paste(rim, (0, 0), mask)
# the night field, lighter towards the top
field = Image.new('RGB', (N, N))
fd = ImageDraw.Draw(field)
for y in range(N):
    k = y / N
    fd.line([(0, y), (N, y)], fill=(int(30 - 20 * k), int(44 - 30 * k), int(88 - 60 * k)))
m2 = Image.new('L', (N, N), 0); ImageDraw.Draw(m2).ellipse((26, 26, N - 26, N - 26), fill=255)
img.paste(field, (0, 0), m2)
dr = ImageDraw.Draw(img)
random.seed(5)
for _ in range(45):
    a, r = random.random() * 6.283, math.sqrt(random.random()) * (c - 60)
    x, y, s = c + math.cos(a) * r, c + math.sin(a) * r, 1 + random.random() * 2.2
    dr.ellipse((x - s, y - s, x + s, y + s), fill=(255, 255, 255, int(90 + 140 * random.random())))
# the big four-point star with a soft blue glow
def star(draw, x, y, R, k, fill):
    pts = []
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2; rr = R * k if i % 2 else R
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    draw.polygon(pts, fill=fill)
glow = Image.new('RGBA', (N, N), (0, 0, 0, 0)); star(ImageDraw.Draw(glow), c, c - 6, 86, 0.24, (170, 205, 255, 255))
img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16)))
star(dr, c, c - 6, 78, 0.2, (255, 255, 255, 255))
# The two words round the rim, each drawn whole and straight first (so the letters keep their shapes and spacing),
# then bent along an arc: МІСІЯ along the top, the site's wordmark Небозвід (gradient, star over the і) along the bottom.
import numpy as np
def bend(src, Rc, ac, bottom, scale):
    """src: a straight RGBA text image drawn `scale` times larger; its middle line is laid on a circle of radius Rc
    (centre angle ac), letters upright: tops outward on the top arc, towards the centre on the bottom one."""
    a = np.asarray(src).astype(np.float32); h, w = a.shape[:2]
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    dx, dy = xs - c + 0.5, ys - c + 0.5
    r = np.hypot(dx, dy); da = np.arctan2(dy, dx) - ac; da = (da + np.pi) % (2 * np.pi) - np.pi
    if bottom: sx, sy = w / 2 - da * Rc * scale, h / 2 + (r - Rc) * scale
    else: sx, sy = w / 2 + da * Rc * scale, h / 2 - (r - Rc) * scale
    x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int); fx, fy = (sx - x0)[..., None], (sy - y0)[..., None]
    def at(yy, xx):
        ok = (xx >= 0) & (xx < w) & (yy >= 0) & (yy < h)
        v = a[np.clip(yy, 0, h - 1), np.clip(xx, 0, w - 1)]; v[~ok] = 0; return v
    out = (at(y0, x0) * (1 - fx) * (1 - fy) + at(y0, x0 + 1) * fx * (1 - fy) + at(y0 + 1, x0) * (1 - fx) * fy + at(y0 + 1, x0 + 1) * fx * fy)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')

S = 3   # draw the words three times larger, then bend (and so shrink) them
# МІСІЯ: plain, light, in the wordmark's font
f = compose.font('CormorantItalic.ttf', 52 * S, 700)
bb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), 'МІСІЯ', font=f)
t = Image.new('RGBA', (bb[2] - bb[0] + 20 * S, bb[3] - bb[1] + 20 * S), (0, 0, 0, 0))
ImageDraw.Draw(t).text((10 * S - bb[0], 10 * S - bb[1]), 'МІСІЯ', font=f, fill=(236, 240, 250, 255))
img.alpha_composite(bend(t, c - 86, -math.pi / 2, False, S))
# Небозвід: the site's wordmark itself, with its star (as compose.draw_logo makes it)
lay, (sx, sy) = compose.logo_layer(70 * S)
sf = ImageFont.truetype(compose.F_STAR, int(70 * S * 0.36))
st = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(st).text((sx, sy), '✦', font=sf, fill=(255, 255, 255, 255), anchor='mm')
gl = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).text((sx, sy), '✦', font=sf, fill=(170, 205, 255, 255), anchor='mm')
lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(70 * S * 0.08))); lay.alpha_composite(st)
lay = lay.crop(lay.getbbox())
img.alpha_composite(bend(lay, c - 74, math.pi / 2, True, S))
img.putalpha(Image.composite(img.getchannel('A'), Image.new('L', (N, N), 0), mask))
buf = io.BytesIO(); img.save(buf, 'PNG', optimize=True)
os.makedirs(os.path.join(HERE, '..', 'work'), exist_ok=True); img.save(os.path.join(HERE, '..', 'work', 'emblem_preview.png'))
with open(os.path.join(HERE, 'emblem.js'), 'w') as f:
    f.write('// Made by characters/emblem.py: the Nebozvid patch for the astronaut (PNG, data URL).\n')
    f.write("window.__astronautEmblem = 'data:image/png;base64," + base64.b64encode(buf.getvalue()).decode() + "';\n")
print('emblem.js', len(buf.getvalue()) // 1024, 'KB')
