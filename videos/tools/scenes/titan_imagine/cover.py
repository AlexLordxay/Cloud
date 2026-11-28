# Cover 1080×1920 for «А ти уявляєш Титан так?» (Reels / TikTok / Shorts): cover_render.py's picture + the title inside
# the 4:5 grid crop (y 285–1635).   python3 cover_render.py && python3 cover.py -> videos/titan_imagine_cover.jpg
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..', '..', '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
W, H = 1080, 1920
def ctext(im, y, t, size, fill):
    d = ImageDraw.Draw(im); f = ImageFont.truetype(F, size)
    while d.textlength(t, font=f) > W - 70: size -= 2; f = ImageFont.truetype(F, size)
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 240))
    sh = sh.filter(ImageFilter.GaussianBlur(12)); im.alpha_composite(sh); im.alpha_composite(sh)
    d.text(((W - w) / 2, y), t, font=f, fill=fill)
im = Image.open(os.path.join(HERE, '..', '..', 'work', 'titan_imagine', 'cover_raw.png')).convert('RGBA')
ctext(im, 300, 'НА ТИТАНІ МОЖНА', 96, (255, 255, 255))
ctext(im, 420, 'ЛІТАТИ', 132, (255, 196, 92))
ctext(im, 1585, 'махаючи руками — і ось чому', 46, (240, 228, 210))
im.convert('RGB').save(os.path.join(V, 'titan_imagine_cover.jpg'), quality=93)
print('ok')
