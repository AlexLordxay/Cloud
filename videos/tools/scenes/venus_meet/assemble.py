# Lays the picture of "Знайомся: Венера" onto one timeline (720 × 1280, work/venus_meet/frames/): the 3D flights over
# the real relief (terrain.js → work/venus_meet/shot_<name>/), the site's Venus (rec.js → work/venus_meet/site/), and
# a drawn piece (Venus beside the Earth, true sizes) and a NASA photo of Venus in the dusk sky — with
# 0.4 s crossfades at the cuts. Captions, logo and the end card come after (compose.py). Run by frames.sh.
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'venus_meet')
TEX = os.path.join(TOOLS, '../../planetarium/textures')
W, H, FPS, XF = 720, 1280, 30, 0.2           # XF: half the crossfade
DURATION = json.load(open(os.path.join(HERE, 'scene.json')))['duration']
sys.path.insert(0, os.path.join(HERE, '..', 'moontrip'))

# (cut where the piece starts, what it is): ('shot', name) a 3D flight; ('site', recording time at the cut) the site;
# ('draw', name) a drawn piece
PIECES = [
    (0.0, ('shot', 'dawn')),
    (3.0, ('site', 3.0)),
    (11.2, ('draw', 'sizes')),
    (16.8, ('draw', 'evening')),
    (24.9, ('shot', 'plains')),
    (34.1, ('shot', 'deck')),
    (46.0, ('shot', 'maat')),
    (56.0, ('shot', 'dusk')),
    (71.3, ('site', 11.6)),
]
cuts = [c for c, _ in PIECES] + [DURATION + 1]

_files = {}
def frames(d):
    if d not in _files: _files[d] = sorted(f for f in os.listdir(d) if f.endswith('.jpg'))
    return _files[d]

def shot(name, start, t):
    d = os.path.join(WORK, 'shot_' + name); fs = frames(d)
    return Image.open(os.path.join(d, fs[min(len(fs) - 1, max(0, round((t - start) * FPS)))])).convert('RGB')

def site(rt):
    d = os.path.join(WORK, 'site'); fs = frames(d)
    i = round(rt * FPS); f = f'f_{i:05d}.jpg'
    if f not in fs: f = fs[0] if i < int(fs[0][2:7]) else fs[-1]
    return Image.open(os.path.join(d, f)).convert('RGB')

# ---- drawn pieces
F_LAB = ImageFont.truetype(os.path.join(TOOLS, 'fonts', 'Commissioner.ttf'), 34)
F_NUM = ImageFont.truetype(os.path.join(TOOLS, 'fonts', 'Unbounded.ttf'), 30)
_cache = {}

def stars(seed, n, top=1.0):
    rng = np.random.default_rng(seed); im = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(im)
    for _ in range(n):
        x, y, b = rng.uniform(0, W), rng.uniform(0, H * top), rng.uniform(0.2, 1) ** 2
        r = 0.5 + 1.3 * b; d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(50 + 200 * b)))
    return im

def sizes(u):
    """Venus and the Earth side by side at their true sizes (12 104 and 12 742 km across), drifting slowly closer."""
    if 'sizes' not in _cache:
        from make import sphere                                   # moontrip's textured-sphere drawer
        bg = Image.new('RGBA', (W, H), (4, 6, 14, 255)); bg.alpha_composite(stars(3, 260))
        _cache['sizes'] = (bg, sphere(os.path.join(TEX, 'venus_atmosphere_2k.jpg'), 300, 0, light=(-0.5, 0.35, 0.8)),
                           sphere(os.path.join(TEX, 'earth_day_2k.jpg'), 316, 20, light=(-0.5, 0.35, 0.8),
                                  clouds=os.path.join(TEX, 'earth_clouds.png'), rim=(0.25, 0.5, 1.0)))
    bg, ven, ear = _cache['sizes']
    k = 0.55 + 0.05 * u                                           # 300/316 px radii at 1.0; both shrunk to fit side by side
    im = bg.copy()
    for img, cx, name, km in ((ven, 0.27, 'Венера', '12 104 км'), (ear, 0.73, 'Земля', '12 742 км')):
        s = img.resize((round(img.width * k * 0.92), round(img.height * k * 0.92)), Image.LANCZOS)
        x, y = int(cx * W - s.width / 2), int(0.47 * H - s.height / 2)
        im.alpha_composite(s, (x, y))
        d = ImageDraw.Draw(im)
        d.text((cx * W, y + s.height + 34), name, font=F_LAB, fill=(255, 255, 255, 235), anchor='mm')
        d.text((cx * W, y + s.height + 78), km, font=F_NUM, fill=(255, 214, 120, 235), anchor='mm')
    return im.convert('RGB')

PHOTO = 'NHQ202605180003.jpg'                  # NASA/Bill Ingalls, 18.05.2026: the Moon and Venus over Washington at dusk
VENUS_AT = (0.309, 0.223)                      # where Venus is in the photo (fractions of its width and height)

def evening(u):
    """The Evening Star in a real dusk sky (NASA photo, a slow push-in), Venus named with a pointer."""
    if 'photo' not in _cache: _cache['photo'] = Image.open(os.path.join(WORK, 'photos', PHOTO)).convert('RGB')
    im = _cache['photo']; z = 1.0 + 0.07 * u
    ih = im.height / z; iw = ih * W / H
    cx, cy = 0.5 * im.width, im.height * (0.5 - 0.06 * u)
    x0 = min(max(0, cx - iw / 2), im.width - iw); y0 = min(max(0, cy - ih / 2), im.height - ih)
    out = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + iw, y0 + ih)).convert('RGBA')
    vx = (VENUS_AT[0] * im.width - x0) / iw * W; vy = (VENUS_AT[1] * im.height - y0) / ih * H
    a = min(1.0, max(0.0, (u - 0.08) / 0.12))
    if a > 0:
        lay = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(lay)
        d.ellipse((vx - 16, vy - 16, vx + 16, vy + 16), outline=(255, 214, 120, int(230 * a)), width=2)
        d.line((vx - 12, vy + 12, vx - 60, vy + 60), fill=(255, 214, 120, int(230 * a)), width=2)
        d.text((vx - 64 + 1, vy + 64 + 2), 'Венера', font=F_LAB, fill=(0, 0, 0, int(170 * a)), anchor='rt')
        d.text((vx - 64, vy + 64), 'Венера', font=F_LAB, fill=(255, 255, 255, int(255 * a)), anchor='rt')
        out.alpha_composite(lay)
    return out.convert('RGB')

DRAW = {'sizes': sizes, 'evening': evening}

def piece(k, t):
    start, src = PIECES[k]
    s0 = 0 if k == 0 else start - XF
    if src[0] == 'shot': return shot(src[1], s0, t)
    if src[0] == 'site': return site(src[1] + (t - start))
    end = cuts[k + 1] + XF
    return DRAW[src[1]]((t - s0) / (end - s0))

def main():
    out = os.path.join(WORK, 'frames'); os.makedirs(out, exist_ok=True)
    for i in range(round(DURATION * FPS)):
        t = i / FPS
        k = max(j for j in range(len(PIECES)) if cuts[j] - XF <= t)
        img = piece(k, t)
        if k > 0 and t < cuts[k] + XF:                         # in a crossfade: the previous piece under this one
            img = Image.blend(piece(k - 1, t), img, (t - (cuts[k] - XF)) / (2 * XF))
        img.save(os.path.join(out, f'f_{i:05d}.jpg'), quality=94)
        if i % 300 == 0: print('frame', i, flush=True)

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'still':        # python3 assemble.py still <piece> <u>  (drawn pieces only)
        DRAW[sys.argv[2]](float(sys.argv[3])).save(os.path.join(WORK, f'draw_{sys.argv[2]}.jpg')); sys.exit()
    main()
