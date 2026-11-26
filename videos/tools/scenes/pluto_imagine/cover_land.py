# Covers 1080×1920 for «А ти уявляєш Плутон так?» on the low flight over the ice mountains (raw 3D frame at 30 s: the far,
# tiny Sun, the blue haze over the horizon) — the author's pick (26.11). Four titles to choose from, in the dark sky
# (inside the 4:5 grid crop, y 285–1635).   python3 videos/tools/scenes/pluto_imagine/cover_land.py -> videos/pluto_cover_{a,b,c,d}.jpg
import os, subprocess, io
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..', '..', '..')
F = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'; FB = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
png = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-loglevel', 'error', '-ss', '30.0', '-i',
                      os.path.join(HERE, 'raw_w3d.mp4'), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                     capture_output=True, check=True).stdout
base = Image.open(io.BytesIO(png)).convert('RGB').resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
W, H = base.size
ICE = (150, 205, 255); WARM = (255, 214, 120)
def make(lines, sub, name):
    im = base.convert('RGBA'); d = ImageDraw.Draw(im)
    def ctext(y, t, font, size, fill):
        f = ImageFont.truetype(font, size)
        while d.textlength(t, font=f) > W - 70: size -= 2; f = ImageFont.truetype(font, size)
        w = d.textlength(t, font=f); sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text(((W - w) / 2, y + 6), t, font=f, fill=(0, 0, 0, 240))
        sh = sh.filter(ImageFilter.GaussianBlur(12)); im.alpha_composite(sh); im.alpha_composite(sh)
        d.text(((W - w) / 2, y), t, font=f, fill=fill)
    y = 330
    for t, col, size in lines:
        ctext(y, t, F, size, col); y += int(size * 1.2)
    if sub: ctext(y + 30, sub, FB, 58, (226, 232, 245))
    im.convert('RGB').save(os.path.join(V, name), quality=93)
make([('А ТИ УЯВЛЯЄШ', (255, 255, 255), 104), ('ПЛУТОН ТАК?', ICE, 124)], None, 'pluto_cover_a.jpg')
make([('СЕРЦЕ ПЛУТОНА', (255, 255, 255), 104), ('ШИРШЕ ЗА УКРАЇНУ', WARM, 104)], None, 'pluto_cover_b.jpg')
make([('ТУТ ТИ ВАЖИВ БИ', (255, 255, 255), 100), ('МЕНШЕ 4 КГ', ICE, 130)], 'Плутон', 'pluto_cover_c.jpg')
make([('ЗНАЙОМСЯ:', (255, 255, 255), 100), ('ПЛУТОН', WARM, 170)], 'карликова планета на краю Сонячної системи', 'pluto_cover_d.jpg')
print('ok')
