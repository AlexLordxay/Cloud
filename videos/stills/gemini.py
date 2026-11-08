import sys, os, math, numpy as np
sys.path.insert(0, '/home/user/Cloud/videos/tools')
from sky import Sky, vec
from PIL import ImageDraw, ImageFont
W, H = 1080, 1920
S = Sky(W, H, 2)
c = vec(103.5, 22.5)                     # the middle of Gemini
scale = H / math.radians(41)
v = {'centre': c, 'scale': scale, 'roll': -20.0, 'photo': 0.9, 'lines': 0.25, 'zlines': 0.9, 'hi': {'Gem': 1.0},
     'borders': {'Gem': 0.5}, 'ecliptic': 0, 'labels': 0, 'stars': 1.3}
img = S.render(v)
img.save('/home/user/Cloud/videos/stills/gemini_clean.jpg', quality=93)
P = S.proj(c, scale, -20.0)
def xy(ra, dec):
    x, y, ok = P(vec(ra, dec)); return float(x[0]) / 2, float(y[0]) / 2
def font(n, s, w=600):
    f = ImageFont.truetype(os.path.join('/home/user/Cloud/videos/tools/fonts', n), s)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
d = ImageDraw.Draw(img)
def txt(p, s, f, col):
    d.text((p[0] + 3, p[1] + 3), s, font=f, fill=(0, 0, 0), anchor='mm'); d.text(p, s, font=f, fill=col, anchor='mm')
txt((W / 2, 260), 'Близнята', font('Unbounded.ttf', 96), (255, 214, 140))
fs = font('Commissioner.ttf', 40)
x, y = xy(113.65, 31.89); txt((x, y - 52), 'Кастор', fs, (235, 238, 245))
x, y = xy(116.33, 28.03); txt((x + 10, y + 56), 'Поллукс', fs, (235, 238, 245))
txt((W / 2, H - 70), 'Справжнє небо · фото: ESO/S. Brunier · небозвід', font('Commissioner.ttf', 28, 500), (180, 188, 205))
img.save('/home/user/Cloud/videos/stills/gemini.jpg', quality=93)
print('ok')
