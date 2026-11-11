# Сторіз «Нас 500!» — подяка читачам Instagram (11.11.2026). Запуск з videos/tools: python3 ../stories/thanks500.py
# Тло — справжнє небо (ESO/S. Brunier, CC BY 4.0), Чумацький Шлях по діагоналі, як у rozigrash.py.
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np, os
W, H = 1080, 1920
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thanks500.png')
Image.MAX_IMAGE_PIXELS = None
sky = Image.open('data/sky/eso0932a.jpg').convert('RGB')
c = sky.crop((1700, 0, 4300, 3000)).rotate(32, resample=Image.BICUBIC)
s = max(W / c.width, H / c.height) * 1.8
c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS)
x0, y0 = (c.width - W) // 2, (c.height - H) // 2
bg = ImageEnhance.Brightness(c.crop((x0, y0, x0 + W, y0 + H))).enhance(0.8)
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
ctext(290, '500', U(300, 800), gold, glow=28)
ctext(640, 'ДЯКУЄМО!', U(84), white)
lines = ['Ви — найкраща аудиторія', 'у всьому Всесвіті']
for i, t in enumerate(lines): ctext(800 + i * 72, t, C(56), white)
body = ['Кожен ваш лайк, коментар', 'і пересилання допомагає', '«Небозвіду» рости', '', 'Разом дивимося на небо —', 'і попереду ще багато космосу']
for i, t in enumerate(body):
    if t: ctext(1110 + i * 64, t, C(48), soft)
ctext(1720, 'НЕБОЗВІД', U(40), gold)
ctext(1782, 'nebozvid.com.ua', C(36), soft, shadow=False)
img.convert('RGB').save(OUT)
print(OUT)
