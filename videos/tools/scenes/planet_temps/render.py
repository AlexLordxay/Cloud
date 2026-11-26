# «Термометр Сонячної системи» — a tall thermometer (NASA mean temperatures, Planetary Fact Sheet), the planets turning
# at their places on the scale; the camera slides down it from the hot Venus to the icy Pluto.
#   python3 scenes/planet_temps/render.py sprites    -> work/planet_temps/spin/<planet>_NN.png (96 turns each)
#   python3 scenes/planet_temps/render.py            -> work/planet_temps/frames/f_%05d.jpg (1080×1920)
#   python3 scenes/planet_temps/render.py tall       -> work/planet_temps/tall.jpg (the whole thermometer, for the post)
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import sprites as SP
WORK = os.path.join(TOOLS, 'work', 'planet_temps'); SPIN = os.path.join(WORK, 'spin'); OUT = os.path.join(WORK, 'frames')
FONTS = os.path.join(TOOLS, 'fonts')
W, H, FPS = 1080, 1920, 30
CFG = json.load(open(os.path.join(HERE, 'scene.json'))); DUR = CFG['duration']
NSPIN = 96

def font(f, size, wght=600):
    ft = ImageFont.truetype(os.path.join(FONTS, f), size)
    try: ft.set_variation_by_axes([wght if a['name'] in (b'Weight', 'Weight') else a['default'] for a in ft.get_variation_axes()])
    except Exception: pass
    return ft

# ---------------------------------------------------------------- the scale
Y0, K = 1320, 9.0
SUN_Y, SUN_R = 840, 190
def ty(T): return Y0 + (480 - T) * K
HT = int(ty(-240) + 330)
BAR_X = 112
# name, T, x, R, label place, spin direction, Ukrainian name
PL = [('venus', 464, 600, 150, 'r', -1, 'Венера'), ('mercury', 167, 650, 105, 'r', 1, 'Меркурій'),
      ('earth', 15, 650, 135, 'r', 1, 'Земля'), ('mars', -65, 860, 100, 'l', 1, 'Марс'),
      ('jupiter', -110, 560, 165, 'tr', 1, 'Юпітер'), ('saturn', -140, 790, 115, 'b', 1, 'Сатурн'),
      ('uranus', -195, 600, 110, 'l', 1, 'Уран'), ('neptune', -200, 880, 110, 'b', 1, 'Нептун'),
      ('pluto', -225, 700, 80, 'b', 1, 'Плутон')]

def tcol(T):
    keys = [(480, (255, 70, 30)), (300, (255, 120, 40)), (150, (255, 190, 70)), (40, (255, 235, 170)), (0, (235, 245, 255)),
            (-80, (150, 210, 255)), (-160, (90, 150, 255)), (-240, (70, 90, 240))]
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if t1 <= T <= t0:
            k = (t0 - T) / (t0 - t1); return tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
    return keys[-1][1] if T < -240 else keys[0][1]

def fmt(T): return ('+' if T > 0 else ('−' if T < 0 else '')) + f'{abs(T)}°'

def sprite_args(name, R):
    a = dict(SP.P[name]); a['R'] = R
    if 'ring' in a: pass
    return a

def make_sprites():
    os.makedirs(SPIN, exist_ok=True)
    jobs = [(n, R, d, i) for n, T, x, R, lp, d, uk in PL + [('sun', 0, 0, SUN_R, '', 1, '')] for i in range(NSPIN)]
    with Pool(4) as p:
        for k, _ in enumerate(p.imap_unordered(_spr, jobs, chunksize=8)):
            if k % 96 == 0: print('sprites', k, '/', len(jobs), flush=True)

def _spr(job):
    n, R, d, i = job
    a = sprite_args(n, R); a['lon0'] = a.get('lon0', 0.0) + d * 2 * math.pi * i / NSPIN
    SP.globe(**a).save(os.path.join(SPIN, f'{n}_{i:02d}.png'))

# ---------------------------------------------------------------- the static board (stars, thermometer, labels)
def stars(img, seed=5):
    rng = np.random.default_rng(seed); d = ImageDraw.Draw(img)
    for _ in range(int(W * HT / 2500)):
        x, y = rng.uniform(0, W), rng.uniform(0, HT); m = rng.random() ** 3
        c = int(70 + 185 * m); r = 0.6 + 1.4 * m
        d.ellipse((x - r, y - r, x + r, y + r), fill=(c, c, min(255, c + 20)))

def text(img, xy, s, f, fill, anchor='mm', shadow=True, spacing=6):
    if shadow:
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).multiline_text((xy[0], xy[1] + 3), s, font=f, fill=(0, 0, 0, 230), anchor=anchor, align='center', spacing=spacing)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(img).multiline_text(xy, s, font=f, fill=fill, anchor=anchor, align='center', spacing=spacing)

def board():
    img = Image.new('RGBA', (W, HT), (5, 6, 12, 255))
    # a faint warm-to-cold wash down the board
    a = np.zeros((HT, W, 4), np.uint8)
    for y in range(0, HT, 4):
        T = 480 - (y - Y0) / K
        c = tcol(max(-240, min(480, T)))
        a[y:y + 4, :, :3] = c; a[y:y + 4, :, 3] = 16
    img.alpha_composite(Image.fromarray(a, 'RGBA'))
    stars(img)
    d = ImageDraw.Draw(img)
    # the title
    text(img, (W / 2, 300), 'ТЕРМОМЕТР', font('Unbounded.ttf', 104), (255, 255, 255))
    text(img, (W / 2, 420), 'СОНЯЧНОЇ СИСТЕМИ', font('Unbounded.ttf', 62), (255, 200, 110))
    text(img, (W / 2, 515), 'середня температура планет', font('Commissioner.ttf', 40, 500), (215, 222, 236))
    # the Sun: far off the scale (at 9 px per degree its +5 500° would be ~45 000 px up — 24 screens)
    text(img, (W / 2 + 150, SUN_Y - 40), 'Сонце', font('Unbounded.ttf', 40), (255, 255, 255), anchor='lm')
    text(img, (W / 2 + 150, SUN_Y + 30), '+5 500°', font('Unbounded.ttf', 58), (255, 220, 120), anchor='lm')
    text(img, (W / 2 + 150, SUN_Y + 105), 'поверхня; на цій шкалі\nбула б на 24 екрани вище', font('Commissioner.ttf', 28, 500), (255, 210, 160), anchor='lm')
    for yy in range(int(SUN_Y + SUN_R + 30), int(ty(480) - 40), 16):
        ImageDraw.Draw(img).line((BAR_X, yy, BAR_X, yy + 8), fill=(255, 150, 60, 200), width=4)
    # the tube
    tube = Image.new('RGBA', (W, HT), (0, 0, 0, 0)); td = ImageDraw.Draw(tube)
    y_top, y_bot = ty(480), ty(-240)
    td.rounded_rectangle((BAR_X - 26, y_top - 26, BAR_X + 26, y_bot + 10), 26, fill=(255, 255, 255, 34), outline=(255, 255, 255, 90), width=3)
    for y in range(int(y_top), int(y_bot)):
        T = 480 - (y - Y0) / K; c = tcol(T)
        td.line((BAR_X - 13, y, BAR_X + 13, y), fill=c + (255,))
    td.ellipse((BAR_X - 52, y_bot - 30, BAR_X + 52, y_bot + 74), fill=tcol(-240) + (255,), outline=(255, 255, 255, 120), width=3)
    glow = tube.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(glow); img.alpha_composite(tube)
    # ticks
    f_t = font('Commissioner.ttf', 30, 600)
    for T in range(450, -241, -50):
        y = ty(T)
        d.line((BAR_X + 30, y, BAR_X + 52, y), fill=(255, 255, 255, 200), width=3)
        text(img, (BAR_X + 62, y), fmt(T), f_t, (225, 230, 242), anchor='lm')
    for T in range(475, -241, -25):
        if T % 50: d.line((BAR_X + 30, ty(T), BAR_X + 42, ty(T)), fill=(255, 255, 255, 120), width=2)
    # Mercury: from +430° by day to −180° at night (a second, thin band)
    xm = 300; ya, yb = ty(430), ty(-180)
    band = Image.new('RGBA', (W, HT), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
    for y in range(int(ya), int(yb)):
        T = 480 - (y - Y0) / K; bd.line((xm - 4, y, xm + 4, y), fill=tcol(T) + (230,))
    bd.ellipse((xm - 10, ya - 10, xm + 10, ya + 10), fill=tcol(430) + (255,)); bd.ellipse((xm - 10, yb - 10, xm + 10, yb + 10), fill=tcol(-180) + (255,))
    img.alpha_composite(band.filter(ImageFilter.GaussianBlur(6))); img.alpha_composite(band)
    f_s = font('Commissioner.ttf', 32, 600)
    text(img, (xm + 24, ya), 'Меркурій вдень: +430°', f_s, tcol(430), anchor='lm')
    text(img, (xm + 24, yb), 'Меркурій вночі: −180°', f_s, tcol(-180), anchor='lm')
    # everyday marks on the scale
    f_r = font('Commissioner.ttf', 30, 600)
    for T, txt in ((327, 'плавиться свинець'), (100, 'кипить вода'), (0, 'замерзає вода')):
        y = ty(T)
        for xx in range(BAR_X + 30, 330, 12): d.line((xx, y, xx + 6, y), fill=(255, 255, 255, 140), width=2)
        text(img, (340, y), (f'{fmt(T)} — ' if T % 50 else '— ') + txt, f_r, (225, 230, 242), anchor='lm')
    # the labels and the pointers from the tube
    f_n = font('Unbounded.ttf', 40); f_v = font('Unbounded.ttf', 58); f_note = font('Commissioner.ttf', 30, 500)
    for n, T, x, R, lp, dr, uk in PL:
        y = ty(T); c = tcol(T)
        # a dotted pointer from the tube to the planet
        x0 = BAR_X + 30; x1 = x - R - 14
        if lp == 'l': x1 = x - R - 28 - max(d.textlength(uk, font=f_n), d.textlength(fmt(T), font=f_v)) - 18
        for xx in range(int(x0), int(x1), 14):
            d.line((xx, y, min(xx + 7, x1), y), fill=c + (170,), width=3)
        if lp == 'r': pos, anc = (x + R + 28, y), 'lm'
        elif lp == 'l': pos, anc = (x - R - 28, y), 'rm'
        elif lp == 'tr': pos, anc = (x + R + 20, y - R * 0.75), 'lm'
        else: pos, anc = (x, y + R + 62), 'mm'
        if n == 'saturn': pos = (x, y + 172)
        # name and degrees
        dy = 34
        text(img, (pos[0], pos[1] - dy), uk, f_n, (255, 255, 255), anchor=anc[0] + 'm')
        text(img, (pos[0], pos[1] + dy), fmt(T), f_v, c, anchor=anc[0] + 'm')
        if n == 'earth':
            text(img, (pos[0], pos[1] + 104), 'рекорди Землі:\nвід −89° до +57°', f_note, (205, 214, 232), anchor=anc[0] + 'm')
        if n == 'venus':
            text(img, (pos[0], pos[1] + 104), 'гарячіша\nза Меркурій', f_note, (255, 210, 170), anchor=anc[0] + 'm')
    text(img, (W / 2 + 40, HT - 110), 'Дані: NASA Planetary Fact Sheet · у газових гігантів —\nна висоті, де тиск як на Землі біля моря',
         font('Commissioner.ttf', 26, 500), (170, 180, 200))
    return img

_SP = {}
def spr(n, i):
    k = (n, i)
    if k not in _SP: _SP[k] = Image.open(os.path.join(SPIN, f'{n}_{i:02d}.png')).convert('RGBA')
    return _SP[k]

# ---------------------------------------------------------------- the camera
def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
T_HOLD, T_END = 2.2, 16.6
def scroll(t):
    k = (t - T_HOLD) / (T_END - T_HOLD)
    # a gentle start and stop, steady in between
    if k <= 0: return 0.0
    if k >= 1: return float(HT - H)
    a = 0.08
    if k < a: u = 0.5 * k * k / a
    elif k > 1 - a: u = 1 - 0.5 * a - 0.5 * (1 - k) ** 2 / a - (0.5 * a - 0.5 * a)
    else: u = k - 0.5 * a
    u = u / (1 - a)
    return float((HT - H) * min(1.0, max(0.0, u)))

_B = {}
def frame(i):
    if 'b' not in _B: _B['b'] = board()
    t = i / FPS
    sy = scroll(t)
    img = _B['b'].crop((0, int(sy), W, int(sy) + H)).copy()
    s = spr('sun', (i // 3) % NSPIN); y = SUN_Y - sy
    if y + s.height / 2 > 0: img.alpha_composite(s, (int(W / 2 - 60 - s.width / 2), int(y - s.height / 2)))
    for n, T, x, R, lp, d, uk in PL:
        y = ty(T) - sy
        s = spr(n, (i // 2) % NSPIN)
        if y + s.height / 2 < 0 or y - s.height / 2 > H: continue
        img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))
    # dim the board under the closing question, then under the end card
    k = 1.0 - 0.45 * ease((t - 15.6) / 0.6) - 0.35 * ease((t - 17.8) / 0.6)
    if k < 1.0:
        img = Image.fromarray((np.asarray(img, np.float32) * k).astype(np.uint8), 'RGBA')
    return img.convert('RGB')

def job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if not os.path.exists(p): frame(i).save(p, quality=93)
    return i

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sprites':
        make_sprites(); sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == 'tall':
        b = board()
        for n, T, x, R, lp, d, uk in PL:
            s = spr(n, 0); b.alpha_composite(s, (int(x - s.width / 2), int(ty(T) - s.height / 2)))
        s = spr('sun', 0); b.alpha_composite(s, (int(W / 2 - 60 - s.width / 2), int(SUN_Y - s.height / 2)))
        b.convert('RGB').save(os.path.join(WORK, 'tall.jpg'), quality=92); print('tall', b.size); sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == 'still':
        for a in sys.argv[2:]:
            frame(int(float(a) * FPS)).save(os.path.join(os.environ.get('STILL_DIR', '/tmp'), f'pt_{a}.jpg'), quality=90)
        sys.exit()
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * FPS)
    with Pool(4) as p:
        for k, _ in enumerate(p.imap_unordered(job, range(n), chunksize=10)):
            if k % 100 == 0: print('frame', k, '/', n, flush=True)
    print('frames done', n)
