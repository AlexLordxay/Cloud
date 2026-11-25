# Cover 1080×1920 for «Ложка нейтронної зорі» (Reels / TikTok / Shorts): raw 3D frame 20 (the star above the glowing spoon,
# its radio beams crossing the frame), upscaled from 720×1280; the title under the spoon, inside the 4:5 grid crop (y 285–1635).
#   python3 videos/tools/scenes/neutron_spoon/cover.py [frame] -> videos/neutron_spoon_cover.jpg
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(HERE, '..', '..'); V = os.path.join(TOOLS, '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'; FB = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
fr = int(sys.argv[1]) if len(sys.argv) > 1 else 20
im = Image.open(os.path.join(TOOLS, 'work', 'neutron_spoon', 'w3d', f'f_{fr:05d}.jpg')).convert('RGB')
im = im.resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
W, H = im.size
a = np.asarray(im, np.float32)
y = np.arange(H)[:, None, None]
a = a * (1 - np.exp(-((y - 1330) / 260.0) ** 2) * 0.5)          # darken behind the title so it reads over the beam
im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
d = ImageDraw.Draw(im)
def ctext(y, t, f, fill):
    w = d.textlength(t, font=f); assert w < W - 70, t
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 240))
    sh = sh.filter(ImageFilter.GaussianBlur(12)); im.alpha_composite(sh); im.alpha_composite(sh)
    d.text(((W - w) / 2, y), t, font=f, fill=fill)
ctext(1125, 'ЛОЖКА ЦІЄЇ ЗОРІ', ImageFont.truetype(F, 104), (255, 255, 255))
ctext(1245, 'ВАЖИТЬ', ImageFont.truetype(F, 104), (255, 255, 255))
ctext(1372, 'МІЛЬЯРД ТОНН', ImageFont.truetype(F, 124), (255, 200, 92))
ctext(1548, 'Нейтронна зоря', ImageFont.truetype(FB, 60), (226, 232, 245))
im.convert('RGB').save(os.path.join(V, 'neutron_spoon_cover.jpg'), quality=93)
print('ok', fr)
