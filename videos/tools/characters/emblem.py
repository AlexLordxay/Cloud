# The astronaut's patch: "МІСІЯ" round the top, a big star in the middle, the site's wordmark (Cormorant Italic, the dawn-to-night gradient, a star over the "і", drawn
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
# the wordmark, as on the site
lay, (sx, sy) = compose.logo_layer(104)
sf = ImageFont.truetype(compose.F_STAR, int(104 * 0.36))
st = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(st).text((sx, sy), '✦', font=sf, fill=(255, 255, 255, 255), anchor='mm')
gl = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).text((sx, sy), '✦', font=sf, fill=(170, 205, 255, 255), anchor='mm')
lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(104 * 0.08))); lay.alpha_composite(st)
bb = lay.getbbox(); lay = lay.crop(bb)
w = int(N * 0.52); lay = lay.resize((w, int(lay.height * w / lay.width)), Image.LANCZOS)
img.alpha_composite(lay, (int(c - lay.width / 2), int(392 - lay.height / 2)))
# "МІСІЯ" round the top, letter by letter along an arc
f = ImageFont.truetype(os.path.join(compose.FONTS, 'Commissioner.ttf'), 40)
try: f.set_variation_by_axes([600 if a['name'] in (b'Weight', 'Weight') else a['default'] for a in f.get_variation_axes()])
except Exception: pass
word, R0 = 'МІСІЯ', c - 72
widths = [ImageDraw.Draw(Image.new('L', (1, 1))).textlength(ch, font=f) + 10 for ch in word]
total, span, acc = sum(widths), 0.95, 0
for ch, wd in zip(word, widths):
    a = -math.pi / 2 - span / 2 + span * (acc + wd / 2) / total; acc += wd
    t = Image.new('RGBA', (80, 80), (0, 0, 0, 0)); ImageDraw.Draw(t).text((40, 40), ch, font=f, fill=(236, 240, 250, 255), anchor='mm')
    t = t.rotate(-math.degrees(a + math.pi / 2), resample=Image.BICUBIC)
    img.alpha_composite(t, (int(c + math.cos(a) * R0 - 40), int(c + math.sin(a) * R0 - 40)))
img.putalpha(Image.composite(img.getchannel('A'), Image.new('L', (N, N), 0), mask))
buf = io.BytesIO(); img.save(buf, 'PNG', optimize=True)
os.makedirs(os.path.join(HERE, '..', 'work'), exist_ok=True); img.save(os.path.join(HERE, '..', 'work', 'emblem_preview.png'))
with open(os.path.join(HERE, 'emblem.js'), 'w') as f:
    f.write('// Made by characters/emblem.py: the Nebozvid patch for the astronaut (PNG, data URL).\n')
    f.write("window.__astronautEmblem = 'data:image/png;base64," + base64.b64encode(buf.getvalue()).decode() + "';\n")
print('emblem.js', len(buf.getvalue()) // 1024, 'KB')
