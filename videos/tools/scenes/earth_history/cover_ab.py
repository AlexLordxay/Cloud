# Three YouTube covers 1280×720 for an A/B test («Test & Compare»), in the style of «НІЧОГО НЕ ВИБУХАЛО» (CTR 6,1 %):
# Inter Black capitals with a black stroke, white + yellow, on clean 3D stills of our own scene
#   EH_RES=1920x1080 python3 acts.py hook stills 3,17.5 ; EH_RES=1920x1080 python3 acts.py theia stills 20
#   python3 cover_ab.py -> videos/earth_history_cover_a.jpg / _b.jpg / _c.jpg
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
ST = os.path.join(TOOLS, 'work', 'earth_history', 'stills'); OUT = os.path.join(TOOLS, '..')
W, H = 1280, 720
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
WHITE, YEL = (255, 255, 255), (255, 205, 40)

def base(name, shade):
    im = Image.open(os.path.join(ST, name)).convert('RGB').resize((W, H), Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(1.25); im = ImageEnhance.Contrast(im).enhance(1.08)
    c = np.asarray(im, np.float32)
    y = np.linspace(0, 1, H)[:, None, None]; x = np.linspace(0, 1, W)[None, :, None]
    c *= shade(x, y)
    return Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))

def lines(im, rows):
    d = ImageDraw.Draw(im)
    for (x, y, s, size, fill) in rows:
        f = ImageFont.truetype(F, size)
        assert d.textbbox((x, y), s, font=f, stroke_width=8)[2] < W - 20, s
        d.text((x, y), s, font=f, fill=fill, stroke_width=8, stroke_fill=(0, 0, 0))
    return im

# A — «4,5 МЛРД РОКІВ ЗА 10 ХВИЛИН»: the whole day-side Earth on the right, words on the dark left
a = base('hook_17.5.jpg', lambda x, y: 0.35 + 0.65 * np.clip((x - 0.05) / 0.55, 0, 1))
lines(a, [(44, 70, '4,5 МЛРД', 150, YEL), (44, 250, 'РОКІВ', 150, WHITE), (44, 430, 'ЗА 10 ХВ', 150, YEL)])
a.save(os.path.join(OUT, 'earth_history_cover_a.jpg'), quality=92)

# B — «ЛЮДИ — ЛИШЕ 6 СЕКУНД»: the night Earth with the city lights, words in the sky above
b = base('hook_3.jpg', lambda x, y: 0.45 + 0.55 * np.clip((y - 0.1) / 0.6, 0, 1))
lines(b, [(44, 30, 'ЛЮДИ — ЛИШЕ', 112, WHITE), (44, 165, '6 СЕКУНД', 170, YEL)])
b.save(os.path.join(OUT, 'earth_history_cover_b.jpg'), quality=92)

# C — «ЯК НАРОДИЛАСЯ ЗЕМЛЯ»: the molten young Earth and Theia coming in, words on the dark lower left
c = base('theia_20.jpg', lambda x, y: 1.0 - 0.35 * np.clip((y - 0.55) / 0.3, 0, 1) * np.clip((0.75 - x) / 0.4, 0, 1))
lines(c, [(44, 370, 'ЯК НАРОДИЛАСЯ', 104, WHITE), (44, 500, 'ЗЕМЛЯ', 170, YEL)])
c.save(os.path.join(OUT, 'earth_history_cover_c.jpg'), quality=92)
print('ok')
