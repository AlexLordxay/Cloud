# «А ти уявляєш Плутон так?» — captions, names and drawings over the one continuous flight (world3d.js → frames),
# timed to the voice (starts at 0.3 s). compose.py draws them at 1080 × 1920.
import json, math, os
from PIL import Image, ImageDraw, ImageFilter

DURATION = 50.6
HOOK_SIZE = 70
HOOK_Y = 1600                        # the hook under the planet (Pluto fills the middle)
CAPTIONS = [
    (-1.0, 3.3, 'hook', 'Серце Плутона ширше\nза всю Україну'),
    (3.72, 5.38, 'cap', 'А ти уявляєш Плутон так?'),
    (5.79, 11.41, 'cap', 'Він менший за наш Місяць —\nлише 2 377 км у діаметрі'),
    (11.79, 18.37, 'cap', 'А на ньому — величезне серце\nз азотного льоду, ~1 600 км'),
    (18.81, 23.1, 'cap', 'Поруч — гори з водяного льоду\nзаввишки до 6 км'),
    (23.61, 28.95, 'cap', 'Над поверхнею — блакитна мла,\nа полудень — як у нас сутінки'),
    (29.43, 34.2, 'cap', 'Якщо ти важиш 60 кг,\nна Плутоні — менше 4'),
    (34.57, 37.62, 'cap', 'Рік там триває\n248 наших років'),
    (38.09, 43.48, 'cap', 'Від відкриття у 1930-му Плутон\nще жодного разу не облетів Сонце'),
    (43.93, 47.57, 'cap', 'Перешли тому, хто досі вважає\nПлутон дев’ятою планетою'),
]
NAMES = [(12.4, 18.2, 'Рівнина Спутника'), (19.2, 23.0, 'Гори Тенцинга')]
SUBS = [(0.8, 3.3, 'Україна — 1 317 км · серце — ~1 600 км'), (12.4, 18.2, 'ліва частина «серця», азотний лід'),
        (19.2, 23.0, 'водяний лід, до ~6 км')]
RELIEF = 'Рельєф і знімки: NASA New Horizons (USGS) · висоти збільшено, дрібні деталі — художня візуалізація'
CREDITS = [(12.0, 36.0, RELIEF), (0.2, 11.4, 'Карти: NASA New Horizons, LRO · масштаб справжній')]
CUTS = []
FADE_IN = 0
SUBSCRIBE_AT = 24.0                  # the subscribe button mid-video (over the blue haze, no names up top then)
END_CARD = 47.9
NEXT_TEASE = 'Не проґав наступну планету'
END_TITLE = 'Карликова планета\nз 2006 року'

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = json.load(open(os.path.join(HERE, '..', '..', 'work', 'pluto_imagine', 'labels.json')))
SUN_C = (243, 185, 100)
_s = 1080 / 720

def _fade(t, a, b, d=0.4):
    x = max(0.0, min(1.0, (t - a) / d, (b - t) / d)); return x * x * (3 - 2 * x)

def _text(img, xy, s, fnt, fill, anchor='mm', alpha=1.0):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0], xy[1] + 3), s, font=fnt, fill=(0, 0, 0, int(230 * alpha)), anchor=anchor)
    sh = sh.filter(ImageFilter.GaussianBlur(8)); img.alpha_composite(sh); img.alpha_composite(sh)
    d.text(xy, s, font=fnt, fill=fill + (int(255 * alpha),), anchor=anchor); img.alpha_composite(lay)

_stars = None
def _orbit_bg(W, H):
    global _stars
    if _stars is None:
        import numpy as np
        r = np.random.default_rng(3); im = Image.new('RGBA', (W, H), (3, 5, 12, 255)); d = ImageDraw.Draw(im)
        for _ in range(420):
            x, y, b = r.uniform(0, W), r.uniform(0, H), r.uniform(0.2, 1) ** 2
            rr = 0.6 + 1.6 * b; d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(255, 255, 255, int(40 + 170 * b)))
        _stars = im
    return _stars.copy()

def _pluto_pos(T):
    a, e, varpi, Tp, P = 39.482, 0.2488, 224.07, 1989.68, 247.94
    M = math.radians(360 / P * (T - Tp)); E = M
    for _ in range(30): E = M + e * math.sin(E)
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2))
    r = a * (1 - e * math.cos(E)); lam = math.radians(varpi) + nu
    return r * math.cos(lam), r * math.sin(lam)

def DRAW(img, t, H_):
    W, H = img.size
    f_lab, f_num, f_big = H_['f_cap'], H_['font']('Unbounded.ttf', 40, 600), H_['font']('Unbounded.ttf', 120, 600)
    f_mid = H_['font']('Commissioner.ttf', 40, 600)
    # sizes: Pluto and the Moon side by side
    a = _fade(t, 6.4, 11.3)
    if a > 0:
        i = min(len(LAB) - 1, int(t * 30)); px, py, pr, mx, my, mr = LAB[i]
        gap = (py + pr + my - mr) / 2 * _s
        _text(img, (W / 2, gap - 46), 'Плутон · 2 377 км', f_mid, (255, 255, 255), alpha=a)
        _text(img, (W / 2, gap + 20), 'Місяць · 3 475 км', f_mid, (200, 210, 230), alpha=a)
    # weight: 60 kg on the Earth → 3.8 kg on Pluto (g = 0.063 of the Earth's)
    a = _fade(t, 29.6, 34.1)
    if a > 0:
        k = min(1.0, max(0.0, (t - 30.6) / 2.2)); k = k * k * (3 - 2 * k)
        v = 60 + (3.8 - 60) * k
        _text(img, (W / 2, 520), 'на Землі' if k < 0.5 else 'на Плутоні', f_mid, (200, 210, 230), alpha=a)
        _text(img, (W / 2, 660), (f'{v:.0f} кг' if v >= 10 else f'{v:.1f} кг'.replace('.', ',')), f_big, (255, 255, 255) if k < 1 else SUN_C, alpha=a)
        bw = 640; x0 = (W - bw) / 2
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle((x0, 770, x0 + bw, 800), 15, fill=(255, 255, 255, int(50 * a)))
        d.rounded_rectangle((x0, 770, x0 + bw * v / 60, 800), 15, fill=SUN_C + (int(230 * a),))
        img.alpha_composite(lay)
    # the orbit: from 1930 to now, a little over half the way round (fast near the Sun), the full turn in 2178
    a = _fade(t, 38.1, 44.0, 0.7)
    if a > 0:
        bg = _orbit_bg(W, H); d = ImageDraw.Draw(bg)
        cx, cy, k = W / 2 + 40, H * 0.43, 11.0                    # px per AU
        pt = lambda x, y: (cx + x * k, cy - y * k)
        # Neptune's orbit (dashed), for scale: Pluto dips inside it
        for j in range(0, 360, 4):
            p1 = pt(30.07 * math.cos(math.radians(j)), 30.07 * math.sin(math.radians(j)))
            p2 = pt(30.07 * math.cos(math.radians(j + 2)), 30.07 * math.sin(math.radians(j + 2)))
            d.line([p1, p2], fill=(110, 150, 220, 150), width=3)
        T = [1930.13 + (2178.0 - 1930.13) * j / 600 for j in range(601)]
        d.line([pt(*_pluto_pos(x)) for x in T], fill=(200, 205, 220, 150), width=3)
        # the Sun
        g = Image.new('RGBA', bg.size); ImageDraw.Draw(g).ellipse((cx - 60, cy - 60, cx + 60, cy + 60), fill=(255, 200, 110, 150))
        bg.alpha_composite(g.filter(ImageFilter.GaussianBlur(24))); d = ImageDraw.Draw(bg)
        d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=(255, 240, 200, 255))
        # 1930 → now, the travelled arc in gold
        u = min(1.0, max(0.0, (t - 38.8) / 3.6)); u = u * u * (3 - 2 * u)
        yr = 1930.13 + (2026.9 - 1930.13) * u
        arc = [pt(*_pluto_pos(1930.13 + (yr - 1930.13) * j / 200)) for j in range(201)]
        d.line(arc, fill=SUN_C + (255,), width=7)
        s0 = pt(*_pluto_pos(1930.13)); s1 = arc[-1]
        d.ellipse((s0[0] - 9, s0[1] - 9, s0[0] + 9, s0[1] + 9), outline=(255, 255, 255, 230), width=3)
        d.ellipse((s1[0] - 14, s1[1] - 14, s1[0] + 14, s1[1] + 14), fill=(222, 190, 160, 255))
        bg.putalpha(bg.getchannel('A').point(lambda v: int(v * a)))
        img.alpha_composite(bg)
        _text(img, (s0[0] + (20 if s0[0] < W / 2 else -20), s0[1] - 40), '1930', f_num, (255, 255, 255), anchor='lm' if s0[0] < W / 2 else 'rm', alpha=a)
        _text(img, (s1[0], s1[1] + 54), f'{int(yr)}', f_num, SUN_C, alpha=a)
        nx, ny = pt(30.07 * math.cos(math.radians(-62)), 30.07 * math.sin(math.radians(-62)))
        _text(img, (nx - 14, ny + 10), 'орбіта Нептуна', H_['font']('Commissioner.ttf', 30, 500), (130, 165, 230), anchor='rm', alpha=a * 0.9)
        _text(img, (W / 2, 300), 'повне коло — лише у 2178 році', f_mid, (220, 226, 240), alpha=a * min(1.0, max(0.0, (t - 41.0) / 0.6)))
