# Covers 1080×1920 for «У Землі колись могли бути кільця» (Reels / TikTok / Shorts), rendered anew (2×2 samples):
#   A (videos/earth_rings_cover.jpg):   Kyiv at midnight, the ring across the southern sky with the Earth's red-edged shadow
#   B (videos/earth_rings_cover_b.jpg): Kyiv at dusk, the sunlit ring reflected in the Dnipro
# the camera tilted up so the ring sits mid-frame, the title above it inside the 4:5 grid crop (y 285–1635).
#   python3 videos/tools/scenes/earth_rings/cover.py
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import frames as FR
import render as RD
V = os.path.join(HERE, '..', '..', '..')
FONT = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
W, H = 1080, 1920

def ctext(im, y, t, size, fill):
    d = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, size)
    while d.textlength(t, font=f) > W - 70: size -= 2; f = ImageFont.truetype(FONT, size)
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 240))
    sh = sh.filter(ImageFilter.GaussianBlur(12)); im.alpha_composite(sh); im.alpha_composite(sh)
    d.text(((W - w) / 2, y), t, font=f, fill=fill)

def make(view, out, sub):
    kind, P = view
    img = FR.render_shot(kind, P, 0.0, 2)
    im = Image.fromarray((RD.tonemap(RD.bloom(img, 1.5)) * 255).astype(np.uint8)).convert('RGBA')
    ctext(im, 300, 'У ЗЕМЛІ БУЛИ', 104, (255, 255, 255))
    ctext(im, 420, 'КІЛЬЦЯ?', 140, (255, 206, 110))
    ctext(im, 1570, sub, 46, (235, 236, 245))
    im.convert('RGB').save(os.path.join(V, out), quality=93)
    print(out, flush=True)

make(FR.kyiv_view([2.0, 6.1, 1.40], 186, 7.0, 66, 0, -16.0, 34.0), 'earth_rings_cover.jpg', 'так вони виглядали б над Києвом')
make(FR.kyiv_view([3.1, 6.8, 1.40], 206, 6.0, 66, 305, -4.0, 30.0), 'earth_rings_cover_b.jpg', 'так вони виглядали б над Києвом')
