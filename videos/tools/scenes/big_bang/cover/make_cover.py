"""Обкладинка YouTube 1280x720 «НІЧОГО НЕ ВИБУХАЛО» з кадру «Планк» (184,5 с відео)."""
import subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np
here = os.path.dirname(os.path.abspath(__file__))
video = os.path.join(here, '../../../../big_bang.mp4')
src = os.path.join(here, 'frame.png')
if not os.path.exists(src):
    subprocess.run(['ffmpeg','-v','error','-y','-ss','184.5','-i',video,'-frames:v','1',src], check=True)
fr = Image.open(src).convert('RGB')
# прибрати підпис внизу зліва (кадр — лише сфера на чорному)
a = np.array(fr); a[1000:, :700] = 0; fr = Image.fromarray(a)
fr = ImageEnhance.Color(fr).enhance(1.45)
fr = ImageEnhance.Contrast(fr).enhance(1.12)
W, H = 1280, 720
# сфера: центр ~ (960,540), r ~ 490 у 1920x1080 → у обкладинці r ≈ 400, центр праворуч
r_src, r_dst = 496, 330
k = r_dst / r_src
big = fr.resize((round(1920*k), round(1080*k)), Image.LANCZOS)
cx, cy = 960*k, 554*k
canvas = Image.new('RGB', (W, H), (0, 0, 0))
canvas.paste(big, (round(W - 350 - cx), round(H/2 - cy)))
# світіння навколо сфери
glow = Image.new('L', (W, H), 0); g = ImageDraw.Draw(glow)
gx, gy = W - 350, H/2
g.ellipse([gx-r_dst-20, gy-r_dst-20, gx+r_dst+20, gy+r_dst+20], fill=120)
glow = glow.filter(ImageFilter.GaussianBlur(40))
col = Image.new('RGB', (W, H), (255, 150, 90))
canvas = Image.composite(col, canvas, glow.point(lambda v: v//3)) if False else canvas
gl = np.array(glow)[..., None] / 255 * 0.35
c = np.array(canvas).astype(float)
c = np.maximum(c, gl * np.array([255, 160, 110]))
# затемнення ліворуч під текст
x = np.linspace(0, 1, W)[None, :, None]
shade = np.clip((x - 0.0) / 0.55, 0, 1) ** 1.2
c = c * (0.25 + 0.75 * shade)
canvas = Image.fromarray(np.clip(c, 0, 255).astype('uint8'))
d = ImageDraw.Draw(canvas)
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
def text(xy, s, size, fill, stroke=8):
    f = ImageFont.truetype(F, size)
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
    return d.textbbox(xy, s, font=f, stroke_width=stroke)
text((44, 150), 'НІЧОГО', 150, (255, 255, 255))
text((44, 315), 'НЕ', 150, (255, 205, 40))
text((44, 480), 'ВИБУХАЛО', 132, (255, 205, 40))
out = os.path.join(here, '../../../../big_bang_cover.jpg')
canvas.save(out, quality=92)
print(out, os.path.getsize(out))
