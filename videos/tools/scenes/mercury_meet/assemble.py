# Lays the picture of "Знайомся: Меркурій" onto one timeline (720 × 1280, work/mercury_meet/frames/): the 3D flights
# over the relief (terrain.js → work/mercury_meet/shot_<name>/), the whole planet (globe.js → globe_<name>/), and two
# drawn pieces — Mercury beside the Moon and the Earth (true sizes), and its orbit with a day that lasts two years —
# with 0.4 s crossfades at the cuts. Captions, logo and the end card come after (compose.py). Run by frames.sh.
#   python3 scenes/mercury_meet/assemble.py               all frames
#   python3 scenes/mercury_meet/assemble.py still <piece> <u>   one drawn frame (u: 0…1 through the piece)
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'mercury_meet')
TEX = os.path.join(TOOLS, '../../planetarium/textures')
W, H, FPS, XF = 720, 1280, 30, 0.2
SCENE = json.load(open(os.path.join(HERE, 'scene.json')))
DURATION = SCENE['duration']
sys.path.insert(0, os.path.join(HERE, '..', 'moontrip'))

# (cut where the piece starts, what it is): ('shot', name) a 3D flight, ('globe', name) the planet, ('draw', name)
PIECES = [tuple(p[:1]) + (tuple(p[1]),) for p in SCENE['pieces']]
cuts = [c for c, _ in PIECES] + [DURATION + 1]

_files = {}
def frames(d):
    if d not in _files: _files[d] = sorted(f for f in os.listdir(d) if f.endswith('.jpg'))
    return _files[d]

def clip(kind, name, start, t):
    d = os.path.join(WORK, f'{kind}_{name}'); fs = frames(d)
    return Image.open(os.path.join(d, fs[min(len(fs) - 1, max(0, round((t - start) * FPS)))])).convert('RGB')

# ---- drawn pieces
F_LAB = ImageFont.truetype(os.path.join(TOOLS, 'fonts', 'Commissioner.ttf'), 34)
F_NUM = ImageFont.truetype(os.path.join(TOOLS, 'fonts', 'Unbounded.ttf'), 30)
F_BIG = ImageFont.truetype(os.path.join(TOOLS, 'fonts', 'Unbounded.ttf'), 44)
SUN_C = (255, 214, 120)
_cache = {}

def stars(seed, n):
    rng = np.random.default_rng(seed); im = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(im)
    for _ in range(n):
        x, y, b = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.2, 1) ** 2
        r = 0.5 + 1.3 * b; d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(50 + 200 * b)))
    return im

def label(d, x, y, name, km, a=1.0):
    d.text((x, y), name, font=F_LAB, fill=(255, 255, 255, int(235 * a)), anchor='mm')
    d.text((x, y + 44), km, font=F_NUM, fill=SUN_C + (int(235 * a),), anchor='mm')

def sizes(u):
    """Mercury beside the Moon at their true sizes (4 879 and 3 474 km across)."""
    if 'sizes' not in _cache:
        from make import sphere                                   # moontrip's textured-sphere drawer
        bg = Image.new('RGBA', (W, H), (4, 6, 14, 255)); bg.alpha_composite(stars(9, 260))
        k = 150 / 4879
        _cache['sizes'] = (bg, sphere(os.path.join(TEX, 'mercury_2k.jpg'), 150, 160, light=(-0.6, 0.35, 0.75)),
                           sphere(os.path.join(TEX, 'moon_2k.jpg'), round(3474 * k), 0, light=(-0.6, 0.35, 0.75)))
    bg, mer, moon = _cache['sizes']
    im = bg.copy(); d = ImageDraw.Draw(im)
    e = lambda a, b: min(1.0, max(0.0, (u - a) / (b - a)))
    ease = lambda x: x * x * (3 - 2 * x)
    for img, cx, name, km, a in ((mer, 0.29, 'Меркурій', '4 879 км', ease(e(0.0, 0.15))), (moon, 0.75, 'Місяць', '3 474 км', ease(e(0.12, 0.3)))):
        if a <= 0: continue
        s = img.copy(); s.putalpha(s.getchannel('A').point(lambda v: int(v * a)))
        cy = 0.42 * H + (1 - a) * 30
        im.alpha_composite(s, (int(cx * W - s.width / 2), int(cy - s.height / 2)))
        label(d, cx * W, 0.42 * H + 150 + 44, name, km, a)
    return im.convert('RGB')

def orbit(u):
    """Mercury round the Sun twice (two of its years, 88 days each) while it turns three times on its axis — so a
    hand fixed to its ground points at the Sun again only after both: one day from noon to noon is 176 days. Near the
    Sun (perihelion) the orbit outruns the spin and the hand swings back."""
    im = Image.new('RGBA', (W, H), (4, 6, 14, 255)); im.alpha_composite(stars(4, 200)); d = ImageDraw.Draw(im)
    cx, cy, a, e = W / 2, H * 0.43, 215, 0.2056
    b = a * math.sqrt(1 - e * e); fx = cx - a * e                       # the Sun at a focus
    # the orbit
    pts = [(cx + a * math.cos(t), cy + b * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 361)]
    d.line(pts, fill=(140, 150, 175, 150), width=2)
    # the Sun
    g = Image.new('RGBA', (W, H)); ImageDraw.Draw(g).ellipse((fx - 70, cy - 70, fx + 70, cy + 70), fill=(255, 190, 90, 120))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(26))); d = ImageDraw.Draw(im)
    d.ellipse((fx - 34, cy - 34, fx + 34, cy + 34), fill=(255, 236, 190, 255))
    # time: two orbits over the piece (0.06 … 0.94), Kepler's equation for where it is
    k = min(1.0, max(0.0, (u - 0.06) / 0.88)); M = 2 * 2 * math.pi * k
    E = M
    for _ in range(8): E = M + e * math.sin(E)
    px_, py_ = cx + a * math.cos(E), cy + b * math.sin(E)
    rot = 1.5 * M                                                      # three turns on its axis per two orbits
    # Mercury: lit toward the Sun, with a hand fixed to its ground
    r = 30; sd = math.atan2(cy - py_, fx - px_)
    body = Image.new('RGBA', (W, H)); db = ImageDraw.Draw(body)
    db.ellipse((px_ - r, py_ - r, px_ + r, py_ + r), fill=(70, 70, 76, 255))
    db.pieslice((px_ - r, py_ - r, px_ + r, py_ + r), math.degrees(sd) - 90, math.degrees(sd) + 90, fill=(205, 200, 194, 255))
    im.alpha_composite(body); d = ImageDraw.Draw(im)
    hx, hy = px_ + math.cos(rot + math.pi) * (r + 16), py_ + math.sin(rot + math.pi) * (r + 16)
    d.line((px_, py_, hx, hy), fill=SUN_C + (255,), width=5); d.ellipse((hx - 7, hy - 7, hx + 7, hy + 7), fill=SUN_C + (255,))
    # the counters
    days = int(round(176 * k))
    word = 'день' if days % 10 == 1 and days % 100 != 11 else 'дні' if days % 10 in (2, 3, 4) and days % 100 not in (12, 13, 14) else 'днів'
    d.text((W / 2, H * 0.21), f'{days} {word}', font=F_BIG, fill=(255, 255, 255, 240), anchor='mm')
    yr = min(2, int(2 * k + 1e-6)); a1 = min(1.0, max(0.0, (k - 0.5) / 0.05)); a2 = min(1.0, max(0.0, (k - 0.995) / 0.005))
    if a1 > 0: d.text((W / 2, H * 0.625), '1 рік = 88 днів', font=F_NUM, fill=SUN_C + (int(240 * a1),), anchor='mm')
    if a2 > 0: d.text((W / 2, H * 0.665), '1 день = 176 днів', font=F_NUM, fill=(140, 200, 255, int(240 * a2)), anchor='mm')
    return im.convert('RGB')

DRAW = {'sizes': sizes, 'orbit': orbit}

def piece(k, t):
    start, src = PIECES[k]
    s0 = 0 if k == 0 else start - XF
    if src[0] in ('shot', 'globe'): return clip(src[0], src[1], s0, t)
    end = cuts[k + 1] + XF
    return DRAW[src[1]]((t - s0) / (end - s0))

def main():
    out = os.path.join(WORK, 'frames'); os.makedirs(out, exist_ok=True)
    for i in range(round(DURATION * FPS)):
        t = i / FPS
        k = max(j for j in range(len(PIECES)) if cuts[j] - XF <= t)
        img = piece(k, t)
        if k > 0 and t < cuts[k] + XF:
            img = Image.blend(piece(k - 1, t), img, (t - (cuts[k] - XF)) / (2 * XF))
        img.save(os.path.join(out, f'f_{i:05d}.jpg'), quality=94)
        if i % 300 == 0: print('frame', i, flush=True)

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'still':
        DRAW[sys.argv[2]](float(sys.argv[3])).save(os.path.join(WORK, f'draw_{sys.argv[2]}_{sys.argv[3]}.jpg')); sys.exit()
    main()
