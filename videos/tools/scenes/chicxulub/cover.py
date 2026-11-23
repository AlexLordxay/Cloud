# Cover 1080×1920 for «Що сталося з Землею, коли вимерли динозаври» (TikTok / Instagram): the asteroid entering the
# air over the sea (frame 34.2 s of videos/dinosaurs.mp4, saved as videos/stories/assets/dino_342.png), the caption of
# that moment hidden under a dark band with our own line. Text inside the 4:5 grid crop (y 285–1635).
#   python3 videos/tools/scenes/chicxulub/cover.py -> videos/dinosaurs_cover.jpg
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..', '..', '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'; FB = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
im = Image.open(os.path.join(V, 'stories', 'assets', 'dino_342.png')).convert('RGB')
W, H = im.size
a = np.asarray(im, np.float32)
# the frame's own caption (white text with a dark shadow, ~1300–1500): replaced by the sea just below it, mirrored,
# feathered into the rows above and below
patch = a[1520:1760][::-1].copy()
w = np.ones(240, np.float32); f = np.linspace(0, 1, 30); w[:30] = f; w[-30:] = f[::-1]
a[1280:1520] = a[1280:1520] * (1 - w[:, None, None]) + patch * w[:, None, None]
y = np.arange(H)[:, None, None]
band = np.exp(-((y - 1400) / 130.0) ** 2) * 0.55
top = np.exp(-((y - 560) / 260.0) ** 2) * 0.35                   # a little shade under the title
a = a * (1 - np.maximum(band, top))
im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
d = ImageDraw.Draw(im)
def ctext(y, t, f, fill):
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 230))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); d.text(((W - w) / 2, y), t, font=f, fill=fill)
big = ImageFont.truetype(F, 128)
ctext(350, 'ДЕНЬ, КОЛИ', big, (255, 255, 255))
ctext(500, 'ЗНИКЛИ', big, (255, 196, 92))
ctext(650, 'ДИНОЗАВРИ', big, (255, 196, 92))
ctext(1365, '66 мільйонів років тому', ImageFont.truetype(FB, 56), (235, 236, 242))
im.convert('RGB').save(os.path.join(V, 'dinosaurs_cover.jpg'), quality=93)
print('ok')
