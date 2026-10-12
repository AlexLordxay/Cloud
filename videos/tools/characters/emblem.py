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
# The two words round the rim in the site's wordmark font (Cormorant Italic Bold): МІСІЯ along the top, Небозвід along
# the bottom (letters upright, the dawn-to-night gradient across it, a star in place of the dot of the і).
def grad(u):
    for (a, ca), (b, cb) in zip(compose.LOGO_STOPS, compose.LOGO_STOPS[1:]):
        if a <= u <= b:
            k = (u - a) / (b - a); return tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3))
    return compose.LOGO_STOPS[-1][1]
def arc(word, size, R0, span, bottom, colour):
    f = compose.font('CormorantItalic.ttf', size, 700)
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    widths = [d0.textlength(ch, font=f) + size * (0.12 if ch == 'ı' else 0.05) for ch in word]
    total, acc = sum(widths), 0
    for i, (ch, wd) in enumerate(zip(word, widths)):
        u = (acc + wd / 2) / total; acc += wd
        a = (math.pi / 2 + span / 2 - span * u) if bottom else (-math.pi / 2 - span / 2 + span * u)
        rot = (a - math.pi / 2) if bottom else (a + math.pi / 2)
        T = int(size * 2); t = Image.new('RGBA', (T, T), (0, 0, 0, 0)); td = ImageDraw.Draw(t)
        td.text((T / 2, T / 2), ch, font=f, fill=colour(i / max(1, len(word) - 1)) + (255,), anchor='ms')   # baseline on the arc
        if ch == 'ı':   # the star over the і, white with a blue glow, as in the logo
            sf = ImageFont.truetype(compose.F_STAR, int(size * 0.5)); sy = T / 2 - size * 0.66
            g = Image.new('RGBA', (T, T), (0, 0, 0, 0)); ImageDraw.Draw(g).text((T / 2 + size * 0.06, sy), '✦', font=sf, fill=(170, 205, 255, 255), anchor='mm')
            t.alpha_composite(g.filter(ImageFilter.GaussianBlur(size * 0.06))); td.text((T / 2 + size * 0.06, sy), '✦', font=sf, fill=(255, 255, 255, 255), anchor='mm')
        t = t.rotate(math.degrees(rot) if bottom else -math.degrees(rot), resample=Image.BICUBIC)
        img.alpha_composite(t, (int(c + math.cos(a) * R0 - T / 2), int(c + math.sin(a) * R0 - T / 2)))
arc('МІСІЯ', 56, c - 92, 0.95, False, lambda u: (236, 240, 250))
arc('Небозвıд', 76, c - 60, 1.5, True, lambda u: grad(u))
img.putalpha(Image.composite(img.getchannel('A'), Image.new('L', (N, N), 0), mask))
buf = io.BytesIO(); img.save(buf, 'PNG', optimize=True)
os.makedirs(os.path.join(HERE, '..', 'work'), exist_ok=True); img.save(os.path.join(HERE, '..', 'work', 'emblem_preview.png'))
with open(os.path.join(HERE, 'emblem.js'), 'w') as f:
    f.write('// Made by characters/emblem.py: the Nebozvid patch for the astronaut (PNG, data URL).\n')
    f.write("window.__astronautEmblem = 'data:image/png;base64," + base64.b64encode(buf.getvalue()).decode() + "';\n")
print('emblem.js', len(buf.getvalue()) // 1024, 'KB')
