# Cover 1080×1920 for «А ти уявляєш Плутон так?» (Reels / TikTok / Shorts): raw 3D frame at 3.9 s (Ukraine laid on Pluto's
# heart, to scale) from scenes/pluto_imagine/raw_w3d.mp4, upscaled from 720×1280 and moved down to make room for the title
# (inside the 4:5 grid crop, y 285–1635).   python3 videos/tools/scenes/pluto_imagine/cover.py -> videos/pluto_imagine_cover.jpg
import os, subprocess, io
import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..', '..', '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
png = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-loglevel', 'error', '-ss', '3.9', '-i',
                      os.path.join(HERE, 'raw_w3d.mp4'), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                     capture_output=True, check=True).stdout
fr = Image.open(io.BytesIO(png)).convert('RGB').resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
W, H = 1080, 1920
im = Image.new('RGB', (W, H), (0, 0, 0)); im.paste(fr, (0, 170))
im = im.convert('RGBA'); d = ImageDraw.Draw(im)
def ctext(y, t, size, fill):
    f = ImageFont.truetype(F, size)
    while d.textlength(t, font=f) > W - 70: size -= 2; f = ImageFont.truetype(F, size)
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 240))
    sh = sh.filter(ImageFilter.GaussianBlur(12)); im.alpha_composite(sh); im.alpha_composite(sh)
    d.text(((W - w) / 2, y), t, font=f, fill=fill)
ctext(300, 'СЕРЦЕ ПЛУТОНА', 104, (255, 255, 255))
ctext(425, 'ШИРШЕ ЗА УКРАЇНУ', 104, (255, 214, 90))
im.convert('RGB').save(os.path.join(V, 'pluto_imagine_cover.jpg'), quality=93)
print('ok')
