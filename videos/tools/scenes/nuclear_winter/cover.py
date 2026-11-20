"""Обкладинка Reels/TikTok/Shorts 1080x1920 «ЯДЕРНА ЗИМА −8 °C» з чистого кадру (Земля під сажею, render.py кадр 1485).
Холодне тонування, сніжинки-попіл, текст у середній зоні 4:5 (сітка Instagram обрізає 1080x1350 по центру).
  python3 render.py 2 1485 && python3 cover.py   -> videos/nuclear_winter_cover.jpg"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
here = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(here, '../..'))
fr = Image.open(os.path.join(TOOLS, 'work', 'nuclear_winter', 'frames', 'f_01485.jpg')).convert('RGB')
W, H = fr.size
c = np.asarray(fr, np.float32) / 255
# cold grade: less saturation, a blue cast in the shadows and the ash
lum = c.mean(2, keepdims=True)
c = lum + (c - lum) * 0.75
c = c * np.array([0.88, 0.95, 1.08]) + np.array([0.0, 0.01, 0.03])
y = np.linspace(0, 1, H)[:, None, None]; x = np.linspace(-1, 1, W)[None, :, None]
c = np.clip(c * 1.25, 0, 1) ** 0.85                                   # lift the ash and the land
c *= 1 - 0.38 * np.exp(-((y - 0.37) / 0.16) ** 2)                  # a dark band behind the words
c *= 1 - 0.35 * np.clip(np.abs(x) - 0.55, 0, 1) / 0.45              # soft side vignette
c *= 1 - 0.5 * np.clip((y - 0.86) / 0.14, 0, 1)                     # darker bottom (UI of the apps)
im = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
# ash / snow flakes: two layers, the near one blurred
rng = np.random.default_rng(7)
for n, rmin, rmax, blur, a in ((260, 1.5, 3.5, 0.6, 170), (40, 5, 9, 2.5, 120)):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for _ in range(n):
        px, py, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(rmin, rmax)
        d.ellipse([px - r, py - r, px + r, py + r], fill=(225, 232, 240, int(a * rng.uniform(0.5, 1))))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
def text(cy, s, size, fill, stroke=10, glow=None):
    f = ImageFont.truetype(F, size)
    if glow:
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((W / 2, cy), s, font=f, fill=glow, anchor='mm')
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(size * 0.18)))
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((W / 2 + 6, cy + 9), s, font=f, fill=(0, 0, 0, 200), anchor='mm')
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(im).text((W / 2, cy), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(8, 12, 20), anchor='mm')
text(520, 'ЯДЕРНА', 170, (255, 255, 255))
text(690, 'ЗИМА', 230, (255, 255, 255))
text(960, '−8 °C', 250, (150, 205, 255), stroke=12, glow=(110, 180, 255, 200))
text(1150, 'на роки', 78, (225, 235, 245), stroke=6)
text(1560, 'що каже наука', 64, (255, 255, 255), stroke=6)
out = os.path.abspath(os.path.join(TOOLS, '..', 'nuclear_winter_cover.jpg'))
im.convert('RGB').save(out, quality=92); print(out)
