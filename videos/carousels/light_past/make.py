"""Карусель «Ти дивишся в минуле» 1080x1350 (Instagram/Facebook). python3 make.py -> slide_1..8.jpg"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, 'assets')
FONTS = os.path.join(HERE, '..', '..', 'tools', 'fonts')
W, H = 1080, 1350
GOLD, WHITE, SOFT, DIM = (247, 198, 107), (255, 255, 255), (232, 228, 220), (150, 150, 160)
def font(file, size, wght):
    f = ImageFont.truetype(os.path.join(FONTS, file), size)
    try: f.set_variation_by_axes([wght if a['name'] in (b'Weight', 'Weight') else a['default'] for a in f.get_variation_axes()])
    except Exception: pass
    return f
fq = lambda s, w=700: font('Unbounded.ttf', s, w)
fc = lambda s, w=600: font('Commissioner.ttf', s, w)
logo_f = ImageFont.truetype(os.path.join(FONTS, 'CormorantItalic.ttf'), 46)

def fit(name, width, cy):
    im = Image.open(os.path.join(A, name)).convert('RGB'); s = width / im.width
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    c = Image.new('RGB', (W, H)); c.paste(im, ((W - im.width) // 2, round(cy - im.height / 2))); return c

def bg(name, cx=0.5, cy=0.5, zoom=1.0, top=0.0, enh=1.0, img=None):
    im = img if img is not None else Image.open(os.path.join(A, name)).convert('RGB')
    s = max(W / im.width, H / im.height) * zoom
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = min(max(round(cx * im.width - W / 2), 0), im.width - W); y = min(max(round(cy * im.height - H / 2), 0), im.height - H)
    im = im.crop((x, y, x + W, y + H))
    if enh != 1: im = ImageEnhance.Color(im).enhance(enh)
    a = np.asarray(im).astype(np.float32)
    yy = np.linspace(0, 1, H)[:, None, None]
    shade = np.clip((yy - 0.42) / 0.40, 0, 1) ** 1.3 * 0.88 + np.clip((0.12 - yy) / 0.12, 0, 1) * 0.45
    return Image.fromarray((a * (1 - shade)).clip(0, 255).astype(np.uint8))

def wrap(d, text, f, maxw):
    out, line = [], ''
    for w in text.split():
        t = (line + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw: line = t
        else: out.append(line); line = w
    out.append(line); return out

def shadow_text(im, xy, t, f, fill, anchor='la'):
    sh = Image.new('L', im.size, 0); ImageDraw.Draw(sh).text((xy[0], xy[1] + 3), t, font=f, fill=200, anchor=anchor)
    im.paste((0, 0, 0), mask=sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).text(xy, t, font=f, fill=fill, anchor=anchor)

def logo(im):
    shadow_text(im, (W / 2, 52), 'Небозвід', logo_f, GOLD, 'ma')

def slide(n, img, name, big, body, credit):
    im = img; d = ImageDraw.Draw(im); logo(im)
    L = 72; y = 860
    shadow_text(im, (L, y), name.upper(), fc(38, 700), SOFT); y += 62
    for ln in wrap(d, big, fq(78, 700), W - 2 * L):
        shadow_text(im, (L, y), ln, fq(78, 700), GOLD); y += 96
    y += 14
    for ln in wrap(d, body, fc(40, 500), W - 2 * L):
        shadow_text(im, (L, y), ln, fc(40, 500), WHITE); y += 54
    d.text((L, H - 46), credit, font=fc(22, 500), fill=DIM)
    im.save(os.path.join(HERE, f'slide_{n}.jpg'), quality=93); print(n, 'end y', y)

def sun_img():
    im = fit('sun_aia.jpg', 1080, 560)
    a = np.asarray(im).astype(np.float32) / 255
    a = np.clip((a - 0.02) * 1.35, 0, 1) ** 0.85          # яскравіше й контрастніше
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    a = np.stack([np.clip(r * 1.05, 0, 1), g * 0.80, b * 0.45], -1)   # тепліший, ближче до оранжевого
    return Image.fromarray((a * 255).astype(np.uint8))

def jup_img():
    im = fit('jupiter_juno.jpg', 1240, 470)
    a = np.asarray(im).astype(np.float32) / 255
    a = np.clip(a * 1.12, 0, 1) ** 0.95
    return Image.fromarray((a * 255).astype(np.uint8))

# 1 — обкладинка
im = bg('milkyway.jpg', 0.5, 0.5, 1.7); d = ImageDraw.Draw(im); logo(im)
y = 830
for ln in ['Ти дивишся', 'в минуле']:
    shadow_text(im, (W / 2, y), ln, fq(92, 800), WHITE, 'ma'); y += 112
y += 20
for ln in wrap(d, 'Світло летить до нас секунди, роки й мільйони років. Ось коли вирушило те, що ти бачиш на небі', fc(40, 500), W - 120):
    shadow_text(im, (W / 2, y), ln, fc(40, 500), SOFT, 'ma'); y += 54
shadow_text(im, (W / 2, y + 30), 'гортай', fc(34, 700), GOLD, 'ma')
d.text((72, H - 46), 'Фото: ESO/S. Brunier (CC BY 4.0)', font=fc(22, 500), fill=DIM)
im.save(os.path.join(HERE, 'slide_1.jpg'), quality=93); print(1, y)

slide(2, bg('moon.jpg', 0.5, 0.40, 0.92), 'Місяць', '1,3 секунди тому',
      'Найближчий сусід. Навіть його світло трохи запізнюється.', 'Фото: Gregory H. Revera (CC BY-SA 3.0, Wikimedia Commons)')
slide(3, bg(None, img=sun_img()), 'Сонце', '8 хвилин 20 секунд тому',
      'Якби Сонце зараз згасло, ми ще 8 хвилин бачили б його світло.', 'Знімок в ультрафіолеті: NASA/GSFC/SDO (AIA 171 Å)')
slide(4, bg(None, img=jup_img()), 'Юпітер', '~44 хвилини тому',
      'Стільки летить його світло цими днями. Залежно від положення на орбіті — від 35 до 52 хвилин.', '«Юнона»: NASA/JPL-Caltech/SwRI/MSSS; обробка Kevin M. Gill (CC BY)')
slide(5, bg('pleiades.jpg', 0.5, 0.42, 1.0), 'Плеяди', '~440 років тому',
      'Це світло вирушило приблизно тоді, коли в Острозі друкували Острозьку Біблію (1581).', 'Знімок: NASA, ESA, AURA/Caltech, Palomar Observatory')
slide(6, bg('orion.jpg', 0.55, 0.40, 1.0), 'Туманність Оріона', '~1 350 років тому',
      'Тоді ще не було Київської Русі. Її видно навіть без телескопа — як розмиту зірку під поясом Оріона.', 'Знімок: NASA, ESA, M. Robberto (STScI/ESA), Hubble Orion Treasury Project (CC BY 4.0)')
slide(7, bg('andromeda.jpg', 0.5, 0.45, 1.0), 'Галактика Андромеди', '~2,5 мільйона років тому',
      'Коли це світло вирушило, в Африці лише з\'являлися перші люди.', 'Фото: Lviatour (CC BY-SA 4.0, Wikimedia Commons)')

# 8 — заклик
im = bg('milkyway.jpg', 0.3, 0.5, 1.15); d = ImageDraw.Draw(im); logo(im)
y = 760
for ln in wrap(d, 'Подивись сьогодні ввечері на небо', fq(66, 700), W - 140):
    shadow_text(im, (W / 2, y), ln, fq(66, 700), WHITE, 'ma'); y += 84
y += 24
for ln in wrap(d, 'і пам\'ятай: кожна зірка — це лист із минулого', fc(42, 500), W - 160):
    shadow_text(im, (W / 2, y), ln, fc(42, 500), SOFT, 'ma'); y += 56
y += 40
shadow_text(im, (W / 2, y), 'Перешли тому, з ким дивишся на зорі', fc(38, 700), GOLD, 'ma')
shadow_text(im, (W / 2, y + 60), 'Збережи, щоб не загубити', fc(38, 700), GOLD, 'ma')
d.text((72, H - 46), 'Фото: ESO/S. Brunier (CC BY 4.0) · Відстані: NASA, Gaia, VLBA', font=fc(22, 500), fill=DIM)
im.save(os.path.join(HERE, 'slide_8.jpg'), quality=93); print(8, y)
