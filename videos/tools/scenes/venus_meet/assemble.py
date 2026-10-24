# Lays the picture of "Знайомся: Венера" onto one timeline (720 × 1280, work/venus_meet/frames/): the 3D flights over
# the real relief (terrain.js → work/venus_meet/shot_<name>/), the site's Venus (rec.js → work/venus_meet/site/), and
# two drawn pieces — Venus beside the Earth (true sizes) and the Evening Star over a Ukrainian horizon at dusk — with
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

def evening(u):
    """Dusk over a Ukrainian horizon (fields, a poplar row, a church's dome): the Evening Star bright and low in the west,
    a young Moon above it; the stars come out as the sky darkens."""
    if 'evening' not in _cache:
        y = np.linspace(0, 1, H)[:, None, None]
        top, mid, low = np.array([10, 16, 44]), np.array([46, 58, 112]), np.array([236, 150, 86])
        sky = np.where(y < 0.62, top + (mid - top) * (y / 0.62), mid + (low - mid) * (np.clip(y - 0.62, 0, None) / 0.38) ** 1.4)
        sky = Image.fromarray((sky * np.ones((1, W, 1))).clip(0, 255).astype(np.uint8), 'RGB').convert('RGBA')
        land = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(land); g = H * 0.86
        pts = [(x, g + 10 * math.sin(x / 90) + 6 * math.sin(x / 31)) for x in range(0, W + 10, 10)]
        d.polygon(pts + [(W, H), (0, H)], fill=(8, 10, 16, 255))
        for i, x in enumerate(range(380, 700, 26)):              # a row of poplars
            h = 120 + 18 * math.sin(i * 1.7)
            d.ellipse((x - 11, g - h, x + 11, g + 6), fill=(8, 10, 16, 255))
        cx = 150; d.rectangle((cx - 26, g - 70, cx + 26, g + 4), fill=(8, 10, 16, 255))   # a small church
        d.ellipse((cx - 22, g - 102, cx + 22, g - 58), fill=(8, 10, 16, 255))
        d.rectangle((cx - 2, g - 132, cx + 2, g - 100), fill=(8, 10, 16, 255)); d.rectangle((cx - 10, g - 122, cx + 10, g - 118), fill=(8, 10, 16, 255))
        _cache['evening'] = (sky, land, stars(11, 300, 0.7))
    sky, land, st = _cache['evening']
    im = sky.copy()
    a = min(1.0, 0.25 + u * 0.9)
    st2 = st.copy(); st2.putalpha(st2.getchannel('A').point(lambda v: int(v * a))); im.alpha_composite(st2)
    # Venus: a brilliant point with a soft glow and short spikes
    gl = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(gl); vx, vy = 300, int(H * 0.66)
    d.ellipse((vx - 34, vy - 34, vx + 34, vy + 34), fill=(255, 250, 230, 150))
    gl = gl.filter(ImageFilter.GaussianBlur(14)); im.alpha_composite(gl)
    d = ImageDraw.Draw(im)
    d.line((vx - 22, vy, vx + 22, vy), fill=(255, 255, 245, 140), width=2); d.line((vx, vy - 22, vx, vy + 22), fill=(255, 255, 245, 140), width=2)
    d.ellipse((vx - 8, vy - 8, vx + 8, vy + 8), fill=(255, 255, 250, 255))
    # a thin young Moon higher up
    mx, my, r = 470, int(H * 0.36), 34
    moon = Image.new('RGBA', (W, H)); md = ImageDraw.Draw(moon)
    md.ellipse((mx - r, my - r, mx + r, my + r), fill=(250, 240, 210, 255)); md.ellipse((mx - r + 12, my - r - 4, mx + r + 12, my + r - 4), fill=(0, 0, 0, 0))
    mglow = moon.filter(ImageFilter.GaussianBlur(10)); im.alpha_composite(mglow); im.alpha_composite(moon)
    im.alpha_composite(land)
    return im.convert('RGB')

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
