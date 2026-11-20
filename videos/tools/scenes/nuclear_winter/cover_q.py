"""Обкладинка-питання 1080x1920 «ЩО БУДЕ, ЯКЩО ПОЧНЕТЬСЯ ЯДЕРНА ВІЙНА?» з чистого кадру з «грибом» (render.py кадр 465).
Кадр збільшено й опущено, щоб гриб стояв під текстом; текст — у середній зоні 4:5 (сітка Instagram).
  python3 render.py 2 465 && python3 cover_q.py   -> videos/nuclear_winter_cover_q.jpg"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
here = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(here, '../..'))
fr = Image.open(os.path.join(TOOLS, 'work', 'nuclear_winter', 'frames', 'f_00465.jpg')).convert('RGB')
W, H = fr.size
fr = ImageEnhance.Contrast(ImageEnhance.Color(fr).enhance(1.25)).enhance(1.1)
k = 1.3                                                          # closer, the cloud at ~(540, 1330)
big = fr.resize((int(W * k), int(H * k)), Image.LANCZOS)
cx, cy = 540 * k, 840 * k
cv = Image.new('RGB', (W, H), (0, 0, 0)); cv.paste(big, (int(W / 2 - cx), int(1230 - cy)))
# stars in the black gap above the shifted frame
c = np.asarray(cv, np.float32)
rng = np.random.default_rng(3)
for _ in range(500):
    x, y = rng.integers(0, W), rng.integers(0, 620)
    if c[y, x].sum() < 40: c[y, x] = rng.uniform(90, 230)
y = np.linspace(0, 1, H)[:, None, None]
c *= 1 - 0.5 * np.exp(-((y - 0.30) / 0.17) ** 2)                 # darker behind the words
c *= 1 - 0.5 * np.clip((y - 0.87) / 0.13, 0, 1)
im = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).convert('RGBA')
# the blast's warm glow under the cloud
g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
ImageDraw.Draw(g).ellipse([540 - 330, 1230 - 260, 540 + 330, 1230 + 300], fill=(255, 140, 50, 70))
im.alpha_composite(g.filter(ImageFilter.GaussianBlur(90)))
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
def text(cy, s, size, fill, stroke=9, glow=None):
    f = ImageFont.truetype(F, size)
    if glow:
        gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl).text((W / 2, cy), s, font=f, fill=glow, anchor='mm')
        im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(size * 0.2)))
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((W / 2 + 5, cy + 8), s, font=f, fill=(0, 0, 0, 210), anchor='mm')
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    ImageDraw.Draw(im).text((W / 2, cy), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(10, 8, 6), anchor='mm')
text(400, 'ЩО БУДЕ,', 120, (255, 255, 255))
text(530, 'ЯКЩО ПОЧНЕТЬСЯ', 100, (255, 255, 255))
text(690, 'ЯДЕРНА', 175, (255, 150, 60), stroke=11, glow=(255, 110, 30, 170))
text(860, 'ВІЙНА?', 175, (255, 150, 60), stroke=11, glow=(255, 110, 30, 170))
out = os.path.abspath(os.path.join(TOOLS, '..', 'nuclear_winter_cover_q.jpg'))
im.convert('RGB').save(out, quality=92); print(out)
