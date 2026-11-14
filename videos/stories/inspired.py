# Сторіз «Що надихнуло?» — відповідь автора на запитання (14.11.2026). Запуск з videos/tools: python3 ../stories/inspired.py
# Тло — справжнє небо (ESO/S. Brunier, CC BY 4.0). Текст вичитано (див. чат 14.11).
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np, os
W, H = 1080, 1920
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inspired.png')
Image.MAX_IMAGE_PIXELS = None
sky = Image.open('data/sky/eso0932a.jpg').convert('RGB')
c = sky.crop((3300, 0, 5900, 3000)).rotate(-28, resample=Image.BICUBIC)
s = max(W / c.width, H / c.height) * 1.8
c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS)
x0, y0 = (c.width - W) // 2, (c.height - H) // 2
bg = ImageEnhance.Brightness(c.crop((x0, y0, x0 + W, y0 + H))).enhance(0.85)
a = np.asarray(bg).astype(np.float32) / 255
yy = np.linspace(0, 1, H)[:, None, None]
a *= 1 - 0.62 * np.exp(-((yy - 0.55) / 0.22) ** 2)          # darker behind the text
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
gold, white, soft = (255, 214, 140), (255, 255, 255), (215, 222, 240)
d = ImageDraw.Draw(img)

# the question sticker is added by the author in Instagram (the space above the text is left for it)
d = ImageDraw.Draw(img)

def wrap(text, font, maxw):
    out, line = [], ''
    import re
    text = re.sub(r'(?<=\s)([іійвузаоІЙВУЗАО]|«О,) ', lambda m: m.group(1) + '\u00a0', ' ' + text).strip()
    for w in text.split(' '):
        t = (line + ' ' + w).strip()
        if d.textlength(t, font=font) <= maxw: line = t
        else: out.append(line); line = w
    if line: out.append(line)
    return out

paras = ['Ми з дитинства часто споглядаємо небо, і кожен бачить там щось своє: незвідане й чарівне.',
         'Хочеться, піднявши голову вгору ясної чи місячної ночі, побачити сузір’я і сказати: «О, я його знаю!»',
         'Щоб, коли маленька дитина поруч спитає: «Тату, а що це?», — мати відповідь.',
         'Щоб, лежачи з коханою, роздивлятися зорі й казати: «А це твоє сузір’я».']
fb = C(44, 500); y = 560; lh = 62
for p in paras:
    for ln in wrap(p, fb, W - 150):
        x = (W - d.textlength(ln.replace('\u00a0', ' '), font=fb)) / 2
        d.text((x + 2, y + 2), ln.replace('\u00a0', ' '), font=fb, fill=(0, 0, 0, 180)); d.text((x, y), ln.replace('\u00a0', ' '), font=fb, fill=soft); y += lh
    y += 30
y += 20
fe = U(46, 600)
for ln in ['Всесвіт чарівний, таємничий', 'і прекрасний —', 'його хочеться вивчати']:
    x = (W - d.textlength(ln, font=fe)) / 2
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).text((x, y), ln, font=fe, fill=gold + (190,))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(14))); d = ImageDraw.Draw(img)
    d.text((x, y), ln, font=fe, fill=gold); y += 66
assert y < 1650, y
for t, f, col, yy_ in (('НЕБОЗВІД', U(38), gold, 1700), ('nebozvid.com.ua', C(34), soft, 1758)):
    d.text(((W - d.textlength(t, font=f)) / 2, yy_), t, font=f, fill=col)
img.convert('RGB').save(OUT)
print(OUT, y)
