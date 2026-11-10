# Instagram story 1080×1920 for «Парад планет» (10.11): the real sky of 16.11 6:20 (scenes/parade) + «Підеш дивитися?».
# The safe zone (top/bottom ~250 px) is kept clear; the middle is left empty for the «Запитання»/poll sticker.
#   python3 videos/stories/parade_story.py -> videos/stories/parade_story.png
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(HERE, '..', 'tools')
sys.path.insert(0, os.path.join(TOOLS, 'scenes', 'parade')); sys.path.insert(0, TOOLS)
import make as M
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
im = M.sky_frame(5.5).convert('RGB')
a = np.asarray(im).astype(np.float32) / 255
yy = np.linspace(0, 1, M.H)[:, None, None]
a *= 1 - 0.45 * np.exp(-((yy - 0.16) / 0.10) ** 2)          # a little shade under the title
im = Image.fromarray((a.clip(0, 1) * 255).astype(np.uint8)).convert('RGBA')
d = ImageDraw.Draw(im)
def ctext(y, t, f, fill):
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text(((M.W - w) / 2, y + 4), t, font=f, fill=(0, 0, 0, 200))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5))); d.text(((M.W - w) / 2, y), t, font=f, fill=fill)
ctext(270, '16 ЛИСТОПАДА · 6:20', M.fq(50), M.GOLD)
ctext(345, 'ПАРАД', M.fq(100), (255, 255, 255)); ctext(455, 'ПЛАНЕТ', M.fq(100), (255, 255, 255))
ctext(800, 'Підеш дивитися?', M.fq(62), (255, 255, 255))
ctext(895, '4 планети на світанку', M.fc(44, 700), (235, 232, 225))
im.convert('RGB').save(os.path.join(HERE, 'parade_story.png'))
print('ok')
