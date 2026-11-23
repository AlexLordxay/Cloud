# Vertical cover 1080×1920 «6 СЕКУНД ДО ПІВНОЧІ» (Facebook/Instagram Reels): the hook's night Earth over Ukraine,
# rendered natively in portrait (EH_RES=1080x1920 python3 acts.py hook stills 2), the clock at 23:59:54, the words in
# the dark sky, all inside the 4:5 crop (y 285–1635).   python3 cover_v.py -> videos/earth_history_cover_v.jpg
import os
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from overlay import draw_clock, font
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
W, H = 1080, 1920
src = Image.open(os.path.join(TOOLS, 'work', 'earth_history', 'stills', 'hook_2.jpg')).convert('RGB')
src = ImageEnhance.Color(src).enhance(1.3); src = ImageEnhance.Contrast(src).enhance(1.1)
im = src.convert('RGBA')
lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
gold, white = (255, 200, 96, 255), (255, 255, 255, 255)
f1, f2 = font(228, 700), font(140, 700)
sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
y0 = 330
w6 = d.textlength('6 ', font=f1); wl = d.textlength('6 СЕКУНД', font=f1); x0 = (W - wl) / 2
w2 = d.textlength('ДО ПІВНОЧІ', font=f2); x2 = (W - w2) / 2
for s, f, xx, yy in (('6 СЕКУНД', f1, x0, y0), ('ДО ПІВНОЧІ', f2, x2, y0 + 262)):
    ds.text((xx + 6, yy + 8), s, font=f, fill=(0, 0, 0, 230))
sh = sh.filter(ImageFilter.GaussianBlur(10)); im.alpha_composite(sh); im.alpha_composite(sh)
d.text((x0, y0), '6', font=f1, fill=gold); d.text((x0 + w6, y0), 'СЕКУНД', font=f1, fill=white)
d.text((x2, y0 + 262), 'ДО ПІВНОЧІ', font=f2, fill=white)
im.alpha_composite(lay)
draw_clock(im, 23 + 59 / 60 + 54 / 3600, 300_000, W / 2, 1210, 120, alpha=1.0, glow=0.6)
dst = os.path.abspath(os.path.join(TOOLS, '..', 'earth_history_cover_v.jpg'))
im.convert('RGB').save(dst, quality=93); print(dst)
