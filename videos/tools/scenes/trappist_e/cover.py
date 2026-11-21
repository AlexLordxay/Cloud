# Cover 1080x1920 for «Знайомся: TRAPPIST-1e». Background: CLEAN=1 python3 still.py videos/stories/assets/trappist_clean.png
# Text inside the 4:5 grid crop (y 285–1635).   python3 videos/tools/scenes/trappist_e/cover.py -> videos/trappist_e_cover.jpg
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..', '..', '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'; FB = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
im = Image.open(os.path.join(V, 'stories', 'assets', 'trappist_clean.png')).convert('RGBA'); W, H = im.size
# TRAPPIST-1f sits right under the «?» and reads as a stray dot: cover it with a patch of nearby sky
im.paste(im.crop((690, 560, 750, 620)), (775, 600))
d = ImageDraw.Draw(im)
def ctext(y, t, f, fill):
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 230))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); d.text(((W - w) / 2, y), t, font=f, fill=fill)
ctext(330, 'ДВІЙНИК', ImageFont.truetype(F, 150), (255, 255, 255))
ctext(490, 'ЗЕМЛІ?', ImageFont.truetype(F, 150), (255, 196, 92))
ctext(675, 'TRAPPIST-1e · 40 світлових років', ImageFont.truetype(FB, 46), (235, 236, 242))
im.convert('RGB').save(os.path.join(V, 'trappist_e_cover.jpg'), quality=93)
print('ok')
