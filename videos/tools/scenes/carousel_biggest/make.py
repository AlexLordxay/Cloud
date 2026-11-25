# Карусель «Найбільше в Сонячній системі» (25.11.2026): 8 слайдів 1080 × 1350 (4:5) для FB/IG.
# Фото: NASA images-api (work/carousel_biggest/dl), Сонце — з текстури сайту з крапкою-Землею в масштабі.
#   python3 scenes/carousel_biggest/make.py   -> videos/carousel_biggest/01.jpg … 08.jpg
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLS)
import compose as C
DL = os.path.join(TOOLS, 'work', 'carousel_biggest', 'dl'); OUT = os.path.join(TOOLS, '..', 'carousel_biggest')
os.makedirs(OUT, exist_ok=True)
W, H = 1080, 1350
SUN = (243, 185, 100)
f_kick = C.font('Commissioner.ttf', 34, 600)
f_title = C.font('Unbounded.ttf', 66, 600)
f_big = C.font('Unbounded.ttf', 150, 700)
f_body = C.font('Commissioner.ttf', 42, 500)
f_small = C.font('Commissioner.ttf', 24, 500)
f_hook = C.font('Unbounded.ttf', 78, 700)

def cover_crop(im, w, h, fx=0.5, fy=0.5, zoom=1.0):
    im = im.convert('RGB'); s = max(w / im.width, h / im.height) * zoom
    im = im.resize((int(im.width * s + 0.5), int(im.height * s + 0.5)), Image.LANCZOS)
    x = int((im.width - w) * fx); y = int((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))

def shade(img, y0, y1):
    # darken toward the bottom for the text
    g = np.zeros((H, 1), np.float32); yy = np.arange(H)[:, None]
    g = np.clip((yy - y0) / (y1 - y0), 0, 1) ** 1.3 * 0.93
    a = np.asarray(img).astype(np.float32) * (1 - g[..., None]) + np.array([6, 8, 14]) * g[..., None]
    return Image.fromarray(a.astype(np.uint8))

def text(img, xy, s, f, fill, anchor='la', spacing=10, shadow=True):
    d = ImageDraw.Draw(img)
    if shadow:
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).multiline_text((xy[0], xy[1] + 3), s, font=f, fill=(0, 0, 0, 200), anchor=anchor, spacing=spacing)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    d.multiline_text(xy, s, font=f, fill=fill, anchor=anchor, spacing=spacing)

def frame(photo, kicker, big, title, body, credit, n, fx=0.5, fy=0.5, zoom=1.0, top=820):
    img = shade(cover_crop(photo, W, H, fx, fy, zoom), top - 260, top + 160).convert('RGBA')
    x = 70
    text(img, (x, top - 170), kicker.upper(), f_kick, SUN)
    text(img, (x - 6, top - 135), big, f_big, (255, 255, 255))
    text(img, (x, top + 50), title, f_title, (255, 255, 255), spacing=12)
    text(img, (x, top + 50 + 82 * (title.count('\n') + 1) + 20), body, f_body, (215, 222, 236), spacing=12)
    text(img, (x, H - 46), credit, f_small, (150, 158, 175), shadow=False)
    text(img, (W - 60, 60), f'{n}/8', f_kick, (220, 226, 240), anchor='ra')
    logo(img, 60)
    return img

def logo(img, cy, size=52, cx=None):
    lay, _ = C.logo_layer(size)
    img.alpha_composite(lay, (int(70 - size * 0.6) if cx is None else int(cx - lay.size[0] / 2), int(cy - lay.size[1] / 2)))

def sun_render(n=1000):
    tex = np.asarray(Image.open(os.path.join(TOOLS, '..', '..', 'planetarium', 'textures', 'sun.jpg')).convert('RGB')).astype(np.float32) / 255
    yy, xx = np.mgrid[0:n, 0:n]; u = (xx - n / 2 + 0.5) / (n / 2); v = (yy - n / 2 + 0.5) / (n / 2)
    r2 = u * u + v * v; m = r2 <= 1; z = np.sqrt(np.clip(1 - r2, 0, 1))
    lat = np.arcsin(np.clip(-v, -1, 1)); lon = np.arctan2(u, z) + 0.6
    ty = ((0.5 - lat / np.pi) * (tex.shape[0] - 1)).astype(int); tx = (((lon / (2 * np.pi)) % 1) * (tex.shape[1] - 1)).astype(int)
    c = tex[ty, tx] * (0.35 + 0.65 * z[..., None] ** 0.6)[..., :] * 1.25
    c = np.clip(c, 0, 1) * m[..., None]
    glow = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40))
    out = Image.fromarray((c * 255).astype(np.uint8))
    return out, glow

def main():
    ld = lambda f: Image.open(os.path.join(DL, f))
    slides = []
    # 1 — the hook
    img = shade(cover_crop(Image.open(os.path.join(TOOLS, 'work', 'carousel_biggest', 'olympus.jpg')), W, H, 0.5, 0.5, 1.0), 560, 1050).convert('RGBA')
    text(img, (70, 820), 'Тут є гора\nу 2,5 раза вища\nза Еверест', f_hook, (255, 255, 255), spacing=14)
    text(img, (70, 1160), 'Найбільше в Сонячній системі', f_body, SUN)
    w_ = ImageDraw.Draw(img).textlength('Найбільше в Сонячній системі', font=f_body)
    text(img, (70 + w_ + 18, 1158), '→', C.ImageFont.truetype(C.F_STAR, 44), SUN)
    text(img, (70, H - 46), 'Гора Олімп, Марс: 3D за картою висот NASA (MOLA), висоти ×4', f_small, (150, 158, 175), shadow=False)
    logo(img, 60); slides.append(img)
    # 2 — Olympus Mons
    slides.append(frame(Image.open(os.path.join(TOOLS, 'work', 'carousel_biggest', 'olympus.jpg')), 'Найвища гора · Марс', '22 км', 'Гора Олімп', 'У 2,5 раза вища за Еверест.\nЗавширшки ~600 км — майже\nз пів України.', 'Кальдера на вершині — 80 км. 3D за картою висот NASA (MOLA), висоти ×4', 2, 0.5, 0.2, 1.35))
    # 3 — the Great Red Spot
    slides.append(frame(ld('PIA21772.jpg'), 'Найбільший шторм · Юпітер', '> Землі', 'Велика червона пляма', 'Вихор, ширший за всю Землю.\nВирує щонайменше 150 років.', 'Фото: NASA/JPL-Caltech/SwRI/MSSS (Juno)', 3, 0.5, 0.3, 1.0))
    # 4 — Valles Marineris
    slides.append(frame(ld('PIA00425.jpg'), 'Найбільший каньйон · Марс', '4 000 км', 'Долина Марінер', 'Утричі довша за Україну\nзі сходу на захід.\nГлибина — до 7 км.', 'Каньйон Офір, частина Долини Марінер. Фото: NASA/JPL (Viking)', 4, 0.45, 0.2, 1.0))
    # 5 — Verona Rupes
    slides.append(frame(ld('PIA18185.jpg'), 'Найвища скеля · Міранда, супутник Урана', '~20 км', 'Урвище Верона', 'Якби зістрибнути з краю,\nпадав би ~12 хвилин.', 'Фото: NASA/JPL (Voyager 2)', 5, 0.5, 0.2, 1.0))
    # 6 — Ganymede
    slides.append(frame(ld('PIA25012.jpg'), 'Найбільший супутник · Юпітер', '5 268 км', 'Ганімед', 'Більший за планету Меркурій\n(4 879 км).', 'Поверхня Ганімеда зблизька. Фото: NASA/JPL-Caltech/SwRI/MSSS (Juno)', 6, 0.5, 0.2, 1.0))
    # 7 — the Sun with the Earth to scale
    bg = Image.new('RGB', (W, H), (4, 5, 10)); s, glow = sun_render(1700)
    g = Image.new('RGB', s.size, (255, 170, 60)); bg.paste(g, (-1020, -620), glow); bg.paste(s, (-1020, -620), Image.fromarray((np.asarray(s).max(-1) > 0).astype(np.uint8) * 255))
    img = shade(bg, 500, 900).convert('RGBA')
    er = 1700 / 2 / 109.2                                   # the Earth's radius at the Sun's scale
    d = ImageDraw.Draw(img); ex, ey = 900, 430
    d.ellipse((ex - er, ey - er, ex + er, ey + er), fill=(110, 160, 255))
    text(img, (ex, ey + 30), 'Земля', f_body, (220, 230, 255), anchor='ma')
    x, top = 70, 820
    text(img, (x, top - 170), 'НАЙБІЛЬШЕ ТІЛО · СОНЦЕ', f_kick, SUN)
    text(img, (x - 6, top - 135), '1,3 млн', f_big, (255, 255, 255))
    text(img, (x, top + 50), 'Земель', f_title, (255, 255, 255))
    text(img, (x, top + 152), 'вмістилося б у Сонці.\nНа ньому — 99,8 % маси\nусієї Сонячної системи.', f_body, (215, 222, 236), spacing=12)
    text(img, (x, H - 46), 'Сонце й Земля — у справжньому масштабі', f_small, (150, 158, 175), shadow=False)
    text(img, (W - 60, 60), '7/8', f_kick, (220, 226, 240), anchor='ra'); logo(img, 60)
    slides.append(img)
    # 8 — the question
    img = shade(cover_crop(ld('PIA21775.jpg'), W, H, 0.5, 0.5, 1.4), 0, 700).convert('RGBA')
    text(img, (W / 2, 560), 'Що вразило\nнайбільше?', f_hook, (255, 255, 255), anchor='ma', spacing=14)
    text(img, (W / 2, 800), 'Пиши в коментарях', f_body, SUN, anchor='ma')
    text(img, (W / 2, 870), 'і перешли тому, хто любить космос', f_body, (215, 222, 236), anchor='ma')
    logo(img, 1100, 96, W / 2)
    text(img, (W - 60, 60), '8/8', f_kick, (220, 226, 240), anchor='ra')
    slides.append(img)
    for i, im in enumerate(slides, 1):
        im.convert('RGB').save(os.path.join(OUT, f'{i:02d}.jpg'), quality=92)
    print('slides', len(slides))

if __name__ == '__main__':
    main()
