"""Обкладинка Reels/TikTok 1080x1920 «СОНЦЕ НЕ ЖОВТЕ» з першого кадру (поле соняшників, жовте Сонце).
Текст — у середній зоні 4:5 (сітка Instagram обрізає 1080x1350 по центру)."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, '../../../work/sun_imagine/frames/f_00009.jpg')
fr = Image.open(src).convert('RGB')
fr = ImageEnhance.Color(fr).enhance(1.15)
W, H = fr.size
c = np.asarray(fr).astype(float)
# a soft darkening behind the text
y = np.linspace(0, 1, H)[:, None, None]
band = np.exp(-((y - 0.25) / 0.10) ** 2) * 0.45
c = c * (1 - band)
canvas = Image.fromarray(np.clip(c, 0, 255).astype('uint8'))
d = ImageDraw.Draw(canvas)
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
def text(cy, s, size, fill, stroke=10):
    f = ImageFont.truetype(F, size)
    d.text((W / 2, cy), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor='mm')
text(400, 'СОНЦЕ', 190, (255, 255, 255))
text(590, 'НЕ ЖОВТЕ', 150, (255, 212, 40))
text(1590, 'а яке тоді? ☀', 64, (255, 255, 255), stroke=6)
out = os.path.join(here, '../../../../sun_imagine_cover.jpg')
canvas.save(out, quality=92)
print(out, os.path.getsize(out))
