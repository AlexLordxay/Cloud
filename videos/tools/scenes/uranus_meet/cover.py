# Cover 1080×1920 for «Знайомся: Уран» (Reels / TikTok / Shorts): frame 3.8 s of videos/uranus_meet.mp4 — Uranus with
# its rings standing upright («лежить на боці»), saved as videos/stories/assets/uranus_38.png. Text inside the 4:5
# grid crop (y 285–1635).   python3 videos/tools/scenes/uranus_meet/cover.py -> videos/uranus_cover.jpg
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..', '..', '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'; FB = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
im = Image.open(os.path.join(V, 'stories', 'assets', 'uranus_38.png')).convert('RGB')
W, H = im.size
a = np.asarray(im, np.float32)
y = np.arange(H)[:, None, None]
shade = np.maximum(np.exp(-((y - 440) / 200.0) ** 2) * 0.45, np.exp(-((y - 1470) / 120.0) ** 2) * 0.45)
a = a * (1 - shade)
im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
d = ImageDraw.Draw(im)
def ctext(y, t, f, fill):
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 235))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); d.text(((W - w) / 2, y), t, font=f, fill=fill)
big = ImageFont.truetype(F, 104)
for t in ('ЛЕЖИТЬ НА БОЦІ',): assert d.textlength(t, font=big) < W - 60
ctext(310, 'ЦЯ ПЛАНЕТА', big, (255, 255, 255))
ctext(435, 'ЛЕЖИТЬ НА БОЦІ', big, (150, 228, 236))
ctext(1430, 'Знайомся: Уран', ImageFont.truetype(FB, 64), (235, 236, 242))
im.convert('RGB').save(os.path.join(V, 'uranus_cover.jpg'), quality=93)
print('ok')
