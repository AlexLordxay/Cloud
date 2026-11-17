# Сторіз «Нас 2 000!» (17.11.2026; копія thanks1000.py). Запуск з videos/tools: python3 ../stories/thanks2000.py
# Тло — галактика Андромеди по діагоналі (Lviatour, CC BY-SA 4.0).
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np, os
W, H = 1080, 1920
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thanks2000.png')
Image.MAX_IMAGE_PIXELS = None
sky = Image.open('../carousels/light_past/assets/andromeda.jpg').convert('RGB')
c = sky
s_ = max(W / c.width, H / c.height) * 1.0
c = c.resize((int(c.width * s_), int(c.height * s_)), Image.LANCZOS)
x0, y0 = int(c.width * 0.47 - W / 2), (c.height - H) // 2
bg = ImageEnhance.Brightness(c.crop((x0, y0, x0 + W, y0 + H))).enhance(0.72)
a = np.asarray(bg).astype(np.float32) / 255
yy = np.linspace(0, 1, H)[:, None, None]
a *= 1 - 0.45 * np.exp(-((yy - 0.36) / 0.13) ** 2) - 0.5 * np.exp(-((yy - 0.70) / 0.13) ** 2)
img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')

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

def ctext(y, t, font, fill, glow=0, shadow=True):
    d = ImageDraw.Draw(img)
    w = d.textlength(t, font=font); x = (W - w) / 2
    if glow:
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((x, y), t, font=font, fill=fill + (200,))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(glow)))
    if shadow: d.text((x + 3, y + 3), t, font=font, fill=(0, 0, 0, 170))
    d.text((x, y), t, font=font, fill=fill)

ctext(190, 'НАС УЖЕ', U(64), white)
f = U(250, 800); n = '2 000'
assert ImageDraw.Draw(img).textlength(n, font=f) < W - 80, 'the number is wider than the frame'
ctext(300, n, f, gold, glow=28)
ctext(640, 'ДЯКУЄМО!', U(84), white)
lines = ['Дві тисячі людей, які разом', 'дивляться на небо']
for i, t in enumerate(lines): ctext(800 + i * 72, t, C(56), white)
body = ['Ще в суботу нас була тисяча.', 'За три дні — удвічі більше!', '', 'Дякуємо, що ділитеся', 'нашими відео з друзями.', 'Попереду — ще більше', 'справжнього космосу!']
for i, t in enumerate(body):
    if t: ctext(1110 + i * 64, t, C(48), soft)
ctext(1720, 'НЕБОЗВІД', U(40), gold)
ctext(1782, 'nebozvid.com.ua', C(36), soft, shadow=False)
img.convert('RGB').save(OUT)
print(OUT)
