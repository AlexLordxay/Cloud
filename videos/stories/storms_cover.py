# Обкладинка допису «Магнітні бурі» для Instagram (4:5, 1080×1350; 14.11.2026). Запуск з videos/tools: python3 ../stories/storms_cover.py
# Фото: полярне сяйво з МКС, NASA iss072e159172 (суспільне надбання), assets/aurora_iss072e159172.jpg
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import compose as C
W, H = 1080, 1350
OUT = os.path.join(HERE, 'storms_cover.png')
ph = Image.open(os.path.join(HERE, 'assets', 'aurora_iss072e159172.jpg')).convert('RGB')
cw = int(ph.height * W / H); x0 = int((ph.width - cw) * 0.62)             # the red curtain and the brightest green, a little right of centre
bg = ph.crop((x0, 0, x0 + cw, ph.height)).resize((W, H), Image.LANCZOS)
bg = ImageEnhance.Color(ImageEnhance.Brightness(bg).enhance(1.25)).enhance(1.15)
a = np.asarray(bg).astype(np.float32) / 255
yy = np.linspace(0, 1, H)[:, None, None]
a *= 1 - 0.55 * np.clip(1 - yy / 0.42, 0, 1) ** 1.5                           # a darker top for the title
img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGBA')

def U(sz, w=700):
    f = ImageFont.truetype(os.path.join(HERE, '..', 'tools', 'fonts', 'Unbounded.ttf'), sz)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def Cm(sz, w=500):
    f = ImageFont.truetype(os.path.join(HERE, '..', 'tools', 'fonts', 'Commissioner.ttf'), sz)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def ctext(y, t, font, fill, glow=0):
    d = ImageDraw.Draw(img); w = d.textlength(t, font=font); x = (W - w) / 2
    assert w < W - 60, t
    if glow:
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).text((x, y), t, font=font, fill=fill + (190,))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(glow)))
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x, y + 4), t, font=font, fill=(0, 0, 0, 200))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(img).text((x, y), t, font=font, fill=fill)

C.draw_logo(img, 46, 86, 0.95, 0.0)
ctext(170, 'МАГНІТНІ', U(118, 800), (255, 255, 255))
ctext(310, 'БУРІ', U(118, 800), (140, 255, 190), glow=26)
ctext(480, 'Що це насправді?', Cm(54, 600), (235, 240, 250))
ctext(H - 62, 'Фото: NASA, полярне сяйво з МКС', Cm(28, 500), (200, 210, 225))
img.convert('RGB').save(OUT, quality=95)
print(OUT)
