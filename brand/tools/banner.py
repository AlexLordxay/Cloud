# YouTube channel banner, 2560 × 1440. Everything that matters sits in the centre 1546 × 423 — the part YouTube shows
# on every device (phones crop to it); the rest is starry sky that TVs and wide screens reveal.
#
#   python3 banner.py <saturn still> [out]      (default out: ../youtube_banner.jpg)
#
# The still is the site's Saturn shot rendered wide and sharp: in videos/tools,
#   REC_W=3200 REC_H=1260 REC_TAG=banner node rec.js ogcard stills 20   → work/ogcard_banner/still_20.jpg
import importlib.util, os, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('compose', os.path.join(HERE, '../../videos/tools/compose.py'))
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)   # logo and fonts from the videos

W, H = 2560, 1440
SAFE = (507, 508, 2053, 931)          # x0, y0, x1, y1 of the always-visible area
src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '../youtube_banner.jpg')

# Sky: the site's background colour with a fixed scatter of stars, so the edges match the rendered shot.
img = Image.new('RGB', (W, H), (4, 6, 12)); d = ImageDraw.Draw(img); rnd = random.Random(7)
for _ in range(2600):
    x, y = rnd.uniform(0, W), rnd.uniform(0, H); b = int(70 + rnd.random() ** 3 * 185)
    tint = rnd.random(); col = (int(b * (1 if tint > 0.8 else 0.88)), int(b * 0.92), int(b * (1 if tint < 0.3 else 0.88)))
    r = 1.3 if rnd.random() < 0.08 else 0.7
    d.ellipse([x - r, y - r, x + r, y + r], fill=col)

# Saturn: the rendered shot scaled down, its edges fading into the sky, the planet on the right of the safe area.
k = 0.52
shot = Image.open(src).convert('RGB'); shot = shot.resize((int(shot.width * k), int(shot.height * k)), Image.LANCZOS)
cx = int(SAFE[2] - 380)                       # where Saturn's centre goes
ox, oy = cx - shot.width // 2, (H - shot.height) // 2
mask = Image.new('L', shot.size, 0); md = ImageDraw.Draw(mask)
md.ellipse([shot.width * 0.18, shot.height * 0.02, shot.width * 0.82, shot.height * 0.98], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(shot.height * 0.12))
img.paste(shot, (ox, oy), mask)
img = img.convert('RGBA')

# Logo with its star, and the tagline, on the left of the safe area.
size = 190
lay, (sx, sy) = C.logo_layer(size)
sf = ImageFont.truetype(C.F_STAR, int(size * 0.36))
glow = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(glow).text((sx, sy), '✦', font=sf, fill=(170, 205, 255, 255), anchor='mm')
lay.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size * 0.08)))
ImageDraw.Draw(lay).text((sx, sy), '✦', font=sf, fill=(255, 255, 255, 255), anchor='mm')
pad = int(size * 0.6)
lx, ly = SAFE[0] + 40 - pad, 560 - pad
sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh.paste((0, 0, 0, 255), (lx, ly + 4), lay.getchannel('A'))
img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
img.alpha_composite(lay, (lx, ly))

def text(s, fnt, x, y, fill):
    t = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(t).text((x, y + 3), s, font=fnt, fill=(0, 0, 0, 210))
    img.alpha_composite(t.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(img).text((x, y), s, font=fnt, fill=fill)
text('Сонячна система в 3D', C.font('Commissioner.ttf', 58, 500), SAFE[0] + 52, 772, (233, 237, 246, 255))
text('на реальних даних · nebozvid.com.ua', C.font('Commissioner.ttf', 38, 400), SAFE[0] + 54, 852, (165, 176, 200, 255))

img.convert('RGB').save(out, 'JPEG', quality=90, optimize=True, progressive=True)
print(out, os.path.getsize(out) // 1024, 'KB')
