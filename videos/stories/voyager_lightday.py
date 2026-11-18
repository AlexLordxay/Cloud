# Сторіз 18.11.2026: Вояджер-1 — 1 світлова доба від Землі (10:16:07 UTC = 12:16 Київ; EarthSky/NASA).
# Тло — справжній знімок «Pale Blue Dot Revisited» (Voyager 1, 14.02.1990; NASA/JPL-Caltech, PIA23645, Public Domain).
# Запуск з videos/tools: python3 ../stories/voyager_lightday.py
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np, os
HERE = os.path.dirname(os.path.abspath(__file__)); W, H = 1080, 1920
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
src = Image.open(os.path.join(HERE, 'assets', 'pale_blue_dot_PIA23645.jpg')).convert('RGB')
DX, DY = 3110, 2689; cw = 2900; ch = round(cw * H / W)
x0 = DX - cw // 2; y0 = max(0, min(src.height - ch, DY - round(ch * 0.52)))
bg = src.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS)
bg = ImageEnhance.Brightness(bg).enhance(0.85)
a = np.asarray(bg).astype(np.float32) / 255
yy = np.linspace(0, 1, H)[:, None, None]
a *= 1 - 0.55 * np.exp(-((yy - 0.17) / 0.12) ** 2) - 0.6 * np.exp(-((yy - 0.80) / 0.13) ** 2)
img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
px, py = (DX - x0) * W / cw, (DY - y0) * H / ch
# Земля — підсилена цятка + кільце
d = ImageDraw.Draw(img)
g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([px - 7, py - 7, px + 7, py + 7], fill=(190, 220, 255, 255))
img.alpha_composite(g.filter(ImageFilter.GaussianBlur(4)))
d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(225, 240, 255))
d.ellipse([px - 46, py - 46, px + 46, py + 46], outline=gold, width=4)
def ctext(y, t, font, fill, x=None, anchor='ma'):
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x or W / 2, y + 3), t, font=font, fill=(0, 0, 0, 210), anchor=anchor)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5))); ImageDraw.Draw(img).text((x or W / 2, y), t, font=font, fill=fill, anchor=anchor)
ctext(py - 30, 'Земля', C(40, 700), gold, x=px + 70, anchor='la')
ctext(250, 'ВОЯДЖЕР-1', U(60), gold)
ctext(350, 'СВІТЛОВА', U(100, 800), white)
ctext(470, 'ДОБА', U(100, 800), white)
ctext(600, 'від Землі — уперше в історії', C(48, 600), white)
ctext(668, '18 листопада о 12:16 за Києвом', C(42, 500), soft)
y = 1360
for t, f, c in [('Його сигнал летить до нас 24 години', C(46, 700), white),
                ('25,9 млрд км · у дорозі з 1977 року', C(42, 500), soft), ('', None, None),
                ('Ця цятка — наша Земля.', C(42, 600), white),
                ('Так її сфотографував Вояджер-1', C(40, 500), soft),
                ('у 1990-му з 6 млрд км', C(40, 500), soft)]:
    if f: ctext(y, t, f, c)
    y += 62 if f else 30
ctext(1790, 'Знімок: NASA/JPL-Caltech («Pale Blue Dot Revisited»)', C(26, 500), (160, 165, 180))
img.convert('RGB').save(os.path.join(HERE, 'voyager_lightday.png')); print('ok', round(px), round(py))
