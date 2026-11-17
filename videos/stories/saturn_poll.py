# Сторіз 17.11.2026: опитування «Ти бачив Сатурн?» + підказка, де шукати. Запуск з videos/tools: python3 ../stories/saturn_poll.py
# Сатурн: Cassini PIA06193 «The Greatest Saturn Portrait ...Yet» — NASA/JPL/Space Science Institute (Public Domain).
# Положення (astronomy-engine, Київ): 17.11 20:00 — висота 40°, азимут 165° (пд.-пд.-сх.), +0,5m.
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, os
W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
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
sat = Image.open(os.path.join(HERE, 'assets', 'saturn_PIA06193.jpg')).convert('RGB')

def base(width, cy):
    s = width / sat.width
    im = sat.resize((round(sat.width * s), round(sat.height * s)), Image.LANCZOS)
    c = Image.new('RGB', (W, H)); c.paste(im, ((W - im.width) // 2, round(cy - im.height / 2)))
    # кілька зірок на тлі
    rng = np.random.default_rng(7); a = np.asarray(c).astype(np.float32)
    for _ in range(260):
        x, y = rng.integers(0, W), rng.integers(0, H)
        if a[y, x].sum() < 30: a[y, x] = rng.uniform(90, 220)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert('RGBA')

def ctext(img, y, t, font, fill, glow=0):
    d = ImageDraw.Draw(img); w = d.textlength(t, font=font); x = (W - w) / 2
    if glow:
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).text((x, y), t, font=font, fill=fill + (200,))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(glow)))
    d.text((x + 3, y + 3), t, font=font, fill=(0, 0, 0, 170)); d.text((x, y), t, font=font, fill=fill)

# 1 — опитування (місце під стікер: ~y 1250–1550)
img = base(1300, 820)
ctext(img, 270, 'ТИ БАЧИВ', U(84), white)
ctext(img, 380, 'САТУРН', U(150, 800), gold, glow=24)
ctext(img, 560, 'на власні очі?', C(60, 600), white)
ctext(img, 1700, 'Знімок «Кассіні»: NASA/JPL/Space Science Institute', C(26), (150, 150, 165))
img.convert('RGB').save(os.path.join(HERE, 'saturn_poll.png'))

# 2 — де шукати сьогодні
img = base(1150, 700)
ctext(img, 250, 'СЬОГОДНІ ВВЕЧЕРІ', C(46, 700), gold)
ctext(img, 320, 'ЗНАЙДИ САТУРН', U(76), white)
y = 1080
for t, f, col in [('близько 20:00', U(64), gold), ('на південному сході, ближче до півдня', C(46, 600), white),
                  ('на висоті 4 кулаків над обрієм', C(46, 500), soft), ('(кулак на витягнутій руці ≈ 10°)', C(38, 500), soft),
                  ('', None, None), ('Яскрава жовтувата «зірка»,', C(46, 500), white), ('яка майже не мерехтить', C(46, 500), white),
                  ('', None, None), ('А о 19:00 — нове відео', C(48, 700), gold), ('«Кільця Сатурна»', C(48, 700), gold)]:
    if f: ctext(img, y, t, f, col)
    y += 72 if f else 34
ctext(img, 1790, 'Небозвід · розрахунок для Києва', C(30, 600), (170, 170, 185))
img.convert('RGB').save(os.path.join(HERE, 'saturn_where.png'))
print('ok')
