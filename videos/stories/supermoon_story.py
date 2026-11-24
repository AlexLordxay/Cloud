# Сторіз «Суперповня 24.11.2026». Запуск з videos/tools: python3 ../stories/supermoon_story.py
# Фото Місяця: Gregory H. Revera, CC BY-SA 3.0 (Wikimedia Commons, FullMoon2010.jpg) — підпис у кадрі обов'язковий.
# Цифри: повня 14:53 UTC = 16:53 Київ, 360 770 км (Space.com, Farmers' Almanac); схід/захід для Києва — PyEphem
# (схід 15:17, захід Сонця 16:03, найвище ~опівночі на 63°). Наступна, найближча за рік — 24.12.2026.
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, os
W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'supermoon_story.png')
img = Image.new('RGBA', (W, H), (4, 6, 14, 255))
# faint stars
rng = np.random.default_rng(7); st = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
for _ in range(260):
    x, y = rng.uniform(0, W), rng.uniform(0, H); r = rng.choice([0.8, 1.0, 1.4]); a = int(rng.uniform(60, 170))
    sd.ellipse((x - r, y - r, x + r, y + r), fill=(220, 228, 255, a))
img.alpha_composite(st)
moon = Image.open('../carousels/light_past/assets/moon.jpg').convert('RGB')
# moon disc: find bounding box of bright pixels
a = np.asarray(moon.convert('L')); ys, xs = np.where(a > 40)
moon = moon.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
D = 860; moon = moon.resize((D, int(moon.height * D / moon.width)), Image.LANCZOS)
cx, cy = W // 2, 860
# warm glow
g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
gd.ellipse((cx - D // 2 - 30, cy - D // 2 - 30, cx + D // 2 + 30, cy + D // 2 + 30), fill=(255, 225, 170, 150))
img.alpha_composite(g.filter(ImageFilter.GaussianBlur(70)))
# slightly warm tint + circular mask
m = np.asarray(moon).astype(np.float32); m *= np.array([1.06, 1.01, 0.92]); m = np.clip(m * 1.05, 0, 255).astype(np.uint8)
moon = Image.fromarray(m)
mask = Image.new('L', moon.size, 0); ImageDraw.Draw(mask).ellipse((1, 1, moon.width - 2, moon.height - 2), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(1.5))
img.paste(moon, (cx - moon.width // 2, cy - moon.height // 2), mask)

def U(sz, w=700):
    f = ImageFont.truetype('fonts/Unbounded.ttf', sz)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def C(sz, w=500):
    f = ImageFont.truetype('fonts/Commissioner.ttf', sz)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
gold, white, soft = (255, 214, 140), (255, 255, 255), (205, 214, 236)
def ctext(y, t, font, fill, glow=0):
    d = ImageDraw.Draw(img); w = d.textlength(t, font=font); x = (W - w) / 2
    if glow:
        gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).text((x, y), t, font=font, fill=fill + (180,))
        img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(glow)))
    s = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(s).text((x + 3, y + 4), t, font=font, fill=(0, 0, 0, 230))
    img.alpha_composite(s.filter(ImageFilter.GaussianBlur(5))); d.text((x, y), t, font=font, fill=fill)

ctext(120, 'СЬОГОДНІ · 24 ЛИСТОПАДА', C(40, 700), gold)
f = U(100, 800); assert ImageDraw.Draw(img).textlength('СУПЕРПОВНЯ', font=f) < W - 60
ctext(180, 'СУПЕРПОВНЯ', f, white, glow=22)
rows = [('Схід над Києвом — 15:17, на сході', C(46, 700), white),
        ('Найефектніше — 16:00–17:30:', C(44, 500), soft),
        ('низько над горизонтом Місяць', C(44, 500), soft),
        ('здається велетенським', C(44, 500), soft),
        None,
        ('Повня о 16:53 · 360 770 км від Землі', C(40, 500), soft),
        ('Наступна — 24 грудня, найбільша цього року', C(40, 600), gold)]
y = 1345
for r in rows:
    if r is None: y += 26; continue
    ctext(y, *r); y += 60
print('rows end', y)
ctext(1790, 'НЕБОЗВІД', U(36), gold)
d = ImageDraw.Draw(img); cr = 'Фото Місяця: Gregory H. Revera, CC BY-SA 3.0'; fc = C(24)
d.text(((W - d.textlength(cr, font=fc)) / 2, 1850), cr, font=fc, fill=(150, 158, 180))
img.convert('RGB').save(OUT); print(OUT)
