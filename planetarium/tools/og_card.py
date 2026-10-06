# The card shown when a link to the site is shared (Telegram, Facebook, X…): 1200×630, a shot of the site with the logo.
#
#   python3 og_card.py <background.jpg> [out.jpg] [title] [subtitle] [crop-x]   (default out: ../og.jpg)
#
# Title and subtitle default to the site's own; crop-x is where the 1200 px window starts in a wider still.
# The background is a still from the site: in videos/tools, `node rec.js ogcard stills 10` → work/ogcard/still_10.jpg
# (a 1600×630 frame with Saturn in the middle; the left 1200 px are kept, so Saturn sits on the right, text on the left).
import importlib.util, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('compose', os.path.join(HERE, '../../videos/tools/compose.py'))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)   # the logo and fonts used in the videos

W, H = 1200, 630
args = sys.argv[1:] + [None] * 5
src, out = args[0], args[1] or os.path.join(HERE, '../og.jpg')
TITLE, SUB = args[2] or 'Сонячна система в 3D', args[3] or 'на реальних даних · будь-яка дата'
CROP_X = int(args[4] or 0)
bg = Image.open(src).convert('RGB')
bg = bg.crop((CROP_X, 0, CROP_X + W, H)) if bg.size[0] >= W else bg.resize((W, H), Image.LANCZOS)
img = bg.convert('RGBA')

# Soft darkening on the left so the text reads over the stars.
shade = Image.new('L', (W, H))
for x in range(W):
    ImageDraw.Draw(shade).line([(x, 0), (x, H)], fill=int(170 * max(0.0, 1 - x / 640) ** 1.6))
img.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), 4)] * 3 + [shade]))

def text(s, fnt, x, y, fill):
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x, y + 2), s, font=fnt, fill=(0, 0, 0, 200))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text((x, y), s, font=fnt, fill=fill)

# Logo with its star over the "ı" (static: no twinkle in a still).
size = 112
lay, (sx, sy) = C.logo_layer(size)
sf = ImageFont.truetype(C.F_STAR, int(size * 0.36))
glow = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(glow).text((sx, sy), '✦', font=sf, fill=(170, 205, 255, 255), anchor='mm')
lay.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size * 0.08)))
ImageDraw.Draw(lay).text((sx, sy), '✦', font=sf, fill=(255, 255, 255, 255), anchor='mm')
pad = int(size * 0.6)
lx, ly = 64 - pad, 190 - pad
shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); shadow.paste((0, 0, 0, 255), (lx, ly + 3), lay.getchannel('A'))
img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
img.alpha_composite(lay, (lx, ly))

text(TITLE, C.font("Commissioner.ttf", 36, 500), 70, 330, (233, 237, 246, 255))
text(SUB, C.font("Commissioner.ttf", 25, 400), 71, 384, (165, 176, 200, 255))

img.convert('RGB').save(out, 'JPEG', quality=88, optimize=True, progressive=True)
print(out, os.path.getsize(out) // 1024, 'KB')
