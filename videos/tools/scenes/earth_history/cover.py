# YouTube cover 1280×720 «6 СЕКУНД ДО ПІВНОЧІ»: the hook's night Earth (1080p act frame), the 24-hour clock at 23:59:54,
# big condensed capitals on the dark sky.
#   python3 cover.py   -> videos/earth_history_cover.jpg
import os
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from overlay import draw_clock, font
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
W, H = 1280, 720
src = Image.open(os.path.join(TOOLS, 'work', 'earth_history', 'acts', 'hook', 'f_00060.jpg')).convert('RGB')
src = ImageEnhance.Color(src).enhance(1.3); src = ImageEnhance.Contrast(src).enhance(1.1)
k = 1.12                                                   # a little closer: the limb fills the lower half
big = src.resize((int(1920 * k * W / 1920), int(1080 * k * W / 1920)), Image.LANCZOS)
cv = Image.new('RGB', (W, H)); cv.paste(big, (W - big.width, H - big.height + 20))
c = np.asarray(cv, np.float32)
y = np.linspace(0, 1, H)[:, None, None]; x = np.linspace(0, 1, W)[None, :, None]
c *= 0.55 + 0.45 * np.clip((y - 0.05) / 0.6, 0, 1) ** 0.8 + 0.0 * x   # darker sky under the words
im = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).convert('RGBA')

lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
gold, white = (255, 200, 96, 255), (255, 255, 255, 255)
f1, f2 = font(190, 700), font(112, 700)
x0, y0 = 54, 22
w6 = d.textlength('6 ', font=f1)
sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
for dd, xx, yy, s, f in ((ds, x0, y0, '6 СЕКУНД', f1), (ds, x0 + 4, y0 + 212, 'ДО ПІВНОЧІ', f2)):
    dd.text((xx + 5, yy + 7), s, font=f, fill=(0, 0, 0, 230))
sh = sh.filter(ImageFilter.GaussianBlur(9)); im.alpha_composite(sh); im.alpha_composite(sh)
d.text((x0, y0), '6', font=f1, fill=gold)
d.text((x0 + w6, y0), 'СЕКУНД', font=f1, fill=white)
d.text((x0 + 4, y0 + 212), 'ДО ПІВНОЧІ', font=f2, fill=white)
im.alpha_composite(lay)
draw_clock(im, 23 + 59 / 60 + 54 / 3600, 300_000, 1090, 150, 92, alpha=1.0, glow=0.6)
dst = os.path.abspath(os.path.join(TOOLS, '..', 'earth_history_cover.jpg'))
im.convert('RGB').save(dst, quality=92); print(dst)
