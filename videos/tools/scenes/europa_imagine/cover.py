# Cover 1080×1920 for «А ти уявляєш Європу так?» (Reels / TikTok / Shorts): a raw 3D frame from raw_w3d.mp4, upscaled from
# 720×1280, with the title (inside the 4:5 grid crop, y 285–1635).
#   python3 videos/tools/scenes/europa_imagine/cover_render.py && python3 videos/tools/scenes/europa_imagine/cover.py
#   -> videos/europa_imagine_cover.jpg
import os, subprocess, io
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..', '..', '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
W, H = 1080, 1920

def frame(t):
    png = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-loglevel', 'error', '-ss', str(t), '-i',
                          os.path.join(HERE, 'raw_w3d.mp4'), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                         capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert('RGB').resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))

def ctext(im, y, t, size, fill):
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(F, size)
    while d.textlength(t, font=f) > W - 70: size -= 2; f = ImageFont.truetype(F, size)
    w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 240))
    sh = sh.filter(ImageFilter.GaussianBlur(12)); im.alpha_composite(sh); im.alpha_composite(sh)
    d.text(((W - w) / 2, y), t, font=f, fill=fill)

def make(t, dx, dy, lines, out):
    im = Image.new('RGB', (W, H), (0, 0, 0)); im.paste(frame(t), (dx, dy)); im = im.convert('RGBA')
    for y, s, size, col in lines: ctext(im, y, s, size, col)
    im.convert('RGB').save(os.path.join(V, out), quality=93)

ICE = (150, 215, 255)
# Europa cut open (ice shell, the ocean glowing blue, rock, iron core), Jupiter behind: rendered for the cover at 1080 × 1920
# (cover_render.py; the video's own frame cuts the globe at the right edge)
im = Image.open(os.path.join(HERE, '..', '..', 'work', 'europa_imagine', 'cover_raw.png')).convert('RGBA')
for y, s_, size, col in [(300, 'ПІД КРИГОЮ —', 108, (255, 255, 255)), (428, 'ЦІЛИЙ ОКЕАН', 120, ICE),
                         (1575, 'води більше, ніж у всіх океанах Землі', 46, (230, 236, 245))]:
    ctext(im, y, s_, size, col)
im.convert('RGB').save(os.path.join(V, 'europa_imagine_cover.jpg'), quality=93)
print('ok')
