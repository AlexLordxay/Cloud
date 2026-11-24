# Сторіз «Нас 5 000 у Facebook!» (24.11.2026; на основі thanks2000.py). Запуск з videos/tools: python3 ../stories/thanks5000_fb.py
# Тло — власний рендер Сатурна (шпалера planetarium/dyakuyu/wp/01-saturn.jpg, з підписом «Небозвід» унизу).
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
W, H = 1080, 1920
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thanks5000_fb.png')
Image.MAX_IMAGE_PIXELS = None
wp = Image.open('../../planetarium/dyakuyu/wp/01-saturn.jpg').convert('RGB')   # власний рендер «Небозводу»
wp = wp.resize((W, int(wp.height * W / wp.width)), Image.LANCZOS)
bg = wp.crop((0, wp.height - H, W, wp.height))
img = bg.convert('RGBA')

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
gold, white, soft = (255, 214, 140), (255, 255, 255), (215, 222, 240)

def ctext(y, t, font, fill, glow=0, shadow=True):
    d = ImageDraw.Draw(img)
    w = d.textlength(t, font=font); x = (W - w) / 2
    if glow:
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((x, y), t, font=font, fill=fill + (200,))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(glow)))
    if shadow:
        s = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(s).text((x + 3, y + 4), t, font=font, fill=(0, 0, 0, 220))
        img.alpha_composite(s.filter(ImageFilter.GaussianBlur(5)))
    d.text((x, y), t, font=font, fill=fill)

ctext(80, 'НАС УЖЕ', U(64), white)
f = U(250, 800); n = '5 000'
assert ImageDraw.Draw(img).textlength(n, font=f) < W - 80, 'the number is wider than the frame'
ctext(165, n, f, gold, glow=28)
ctext(490, 'У FACEBOOK', U(58), white)
ctext(565, 'ДЯКУЄМО!', U(84), white)
body = [('П\u2019ять тисяч людей, які разом', 600, white), ('дивляться на небо', 600, white), None,
        ('Дякуємо, що дивитеся, коментуєте', 500, soft), ('й ділитеся нашими відео.', 500, soft)]
y = 715
for b in body:
    if b: ctext(y, b[0], C(44, b[1]), b[2]); y += 56
    else: y += 26
print('body ends at', y)
ctext(1850, 'nebozvid.com.ua', C(34), soft, shadow=False)
img.convert('RGB').save(OUT)
print(OUT)
