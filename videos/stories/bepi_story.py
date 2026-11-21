# Story 21.11.2026: BepiColombo enters Mercury orbit (ESA/JAXA). Background — clean frame of «Знайомся: Меркурій» at 77.6 s
# (ffmpeg -ss 77.6 -i videos/mercury_meet.mp4 -frames:v 1 videos/stories/assets/mercury_776.png). Bottom ~1530–1760 left free
# for the link sticker to the Mercury video.   python3 videos/stories/bepi_story.py -> videos/stories/bepi_story.png
import os
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); FONTS = os.path.join(HERE, '..', 'tools', 'fonts')
GOLD = (243, 185, 100)
im = Image.open(os.path.join(HERE, 'assets', 'mercury_776.png')).convert('RGBA')
W, H = im.size
d = ImageDraw.Draw(im)
U = lambda s: ImageFont.truetype(os.path.join(FONTS, 'Unbounded.ttf'), s)
C = lambda s, w=600: _var(os.path.join(FONTS, 'Commissioner.ttf'), s, w)
from PIL import ImageFont
def _var(p, s, w):
    f = ImageFont.truetype(p, s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def ctext(y, t, f, fill, sh=200):
    w = d.textlength(t, font=f); layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(((W - w) / 2, y + 4), t, font=f, fill=(0, 0, 0, sh))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(6))); d.text(((W - w) / 2, y), t, font=f, fill=fill)
ctext(262, 'СЬОГОДНІ · 21 ЛИСТОПАДА', C(40, 700), GOLD)
ctext(318, 'BepiColombo', U(92), (255, 255, 255))
ctext(440, 'виходить на орбіту Меркурія', C(48, 600), (235, 238, 245))
ctext(1428, '8 років у дорозі · Європа + Японія', C(38, 500), (200, 206, 220))
ctext(1490, 'Знайомся з Меркурієм', C(44, 700), GOLD)
d.polygon([(W/2 - 22, 1566), (W/2 + 22, 1566), (W/2, 1592)], fill=GOLD)   # small arrow down to the sticker
im.convert('RGB').save(os.path.join(HERE, 'bepi_story.png'))
print('ok')
