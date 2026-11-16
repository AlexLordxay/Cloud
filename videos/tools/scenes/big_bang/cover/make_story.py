"""Сторіз 1080x1920: анонс «Великого вибуху» на YouTube (місце для стікера-посилання внизу)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
fr = Image.open(os.path.join(here, 'frame.png')).convert('RGB')
a = np.array(fr); a[1000:, :700] = 0; fr = Image.fromarray(a)
fr = ImageEnhance.Color(fr).enhance(1.45); fr = ImageEnhance.Contrast(fr).enhance(1.12)
W, H = 1080, 1920
r_src, r_dst = 496, 470
k = r_dst / r_src
big = fr.resize((round(1920*k), round(1080*k)), Image.LANCZOS)
cx, cy = 960*k, 554*k
gx, gy = W/2, 900
canvas = Image.new('RGB', (W, H), (0, 0, 0))
canvas.paste(big, (round(gx - cx), round(gy - cy)))
# прибрати все поза кулею (краї кадру)
mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).ellipse([gx-r_dst, gy-r_dst, gx+r_dst, gy+r_dst], fill=255)
canvas = Image.composite(canvas, Image.new('RGB', (W, H)), mask.filter(ImageFilter.GaussianBlur(1.5)))
glow = Image.new('L', (W, H), 0); ImageDraw.Draw(glow).ellipse([gx-r_dst-25, gy-r_dst-25, gx+r_dst+25, gy+r_dst+25], fill=255)
glow = np.array(glow.filter(ImageFilter.GaussianBlur(45)))[..., None] / 255 * 0.3
c = np.maximum(np.array(canvas).astype(float), glow * np.array([255, 160, 110]))
canvas = Image.fromarray(np.clip(c, 0, 255).astype('uint8'))
d = ImageDraw.Draw(canvas)
B = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
M = '/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf'
def ctext(y, s, font, size, fill, stroke=0):
    f = ImageFont.truetype(font, size)
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
# верх (нижче зони імені профілю ~250 px)
ctext(290, 'НОВЕ ВІДЕО НА YOUTUBE', M, 44, (255, 255, 255))
d.rounded_rectangle([W/2-60, 356, W/2+60, 362], 3, fill=(255, 205, 40))
# заголовок під кулею
ctext(1330, 'НІЧОГО', B, 150, (255, 255, 255), 8)
ctext(1480, 'НЕ ВИБУХАЛО', B, 118, (255, 205, 40), 8)
ctext(1630, 'Як народився Всесвіт — 13,8 млрд років за 6 хвилин', M, 36, (225, 225, 230))
out = '/home/user/cloud/videos/stories/big_bang_story.png'
canvas.save(out); print(out)
