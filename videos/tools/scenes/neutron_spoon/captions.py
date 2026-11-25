# «Ложка нейтронної зорі» — captions, names and drawings over the frames (world.js), timed to the voice (scene.json
# parts: phrases at 0.3, 4.41, 8.35, 14.82, 22.10, 28.53 s). compose.py draws them at 1080 × 1920.
import json, math, os
from PIL import Image, ImageDraw, ImageFilter

DURATION = 34.0
HOOK_SIZE = 66
HOOK_Y = 1560                        # the hook under the spoon (the star above, the spoon in the middle)
CAPTIONS = [
    (-1.0, 4.05, 'hook', 'Чайна ложка цієї зорі\nважить мільярд тонн'),
    (4.41, 7.95, 'cap', 'Це нейтронна зоря —\nядро зорі, що вибухнула'),
    (8.35, 11.85, 'cap', 'Вона важча за Сонце,\nале менша за Київ'),
    (12.07, 14.45, 'cap', 'лише 20 км завширшки'),
    (14.82, 17.42, 'cap', 'Речовина в ній стиснута\nтак щільно,'),
    (17.55, 21.7, 'cap', 'що одна ложка важить більше,\nніж усі люди на Землі разом'),
    (22.10, 26.6, 'cap', 'А обертатися така зоря може\nпонад 700 разів за секунду'),
    (28.53, 30.75, 'cap', 'Яку зорю показати наступною?'),
]
NAMES = [(4.7, 6.9, 'Нейтронна зоря'), (7.2, 8.25, 'Крабоподібна туманність'), (8.6, 14.5, 'Київ')]
SUBS = [(4.7, 6.9, 'лінії — магнітне поле, промені — радіопучки'), (7.2, 8.25, 'залишок вибуху 1054 року, у центрі — пульсар'),
        (8.6, 11.9, 'маса зорі ≈ 1,4 Сонця')]
CREDITS = [(0.2, 7.0, 'Художня візуалізація за даними NASA'),
           (7.0, 8.25, 'Крабоподібна туманність: NASA, ESA, J. Hester, A. Loll (Hubble)'),
           (8.4, 14.6, 'Київ: Sentinel-2 cloudless 2016 (EOX, Copernicus) · розмір зорі справжній'),
           (14.8, 22.0, 'Художня візуалізація'),
           (27.9, 30.8, 'Крабоподібна туманність: NASA, ESA, J. Hester, A. Loll (Hubble)')]
CUTS = []
FADE_IN = 0
SUBSCRIBE_AT = 15.0
END_CARD = 30.9
END_TITLE = 'Нейтронна зоря:\n20 км і 1,4 Сонця'
NEXT_TEASE = 'Не проґав наступну зорю'

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = json.load(open(os.path.join(HERE, '..', '..', 'work', 'neutron_spoon', 'labels.json')))
SUN_C = (243, 185, 100)
_s = 1080 / 720

def _fade(t, a, b, d=0.4):
    x = max(0.0, min(1.0, (t - a) / d, (b - t) / d)); return x * x * (3 - 2 * x)

def _text(img, xy, s, fnt, fill, anchor='mm', alpha=1.0):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).multiline_text((xy[0], xy[1] + 3), s, font=fnt, fill=(0, 0, 0, int(230 * alpha)), anchor=anchor, align='center', spacing=8)
    sh = sh.filter(ImageFilter.GaussianBlur(8)); img.alpha_composite(sh); img.alpha_composite(sh)
    d.multiline_text(xy, s, font=fnt, fill=fill + (int(255 * alpha),), anchor=anchor, align='center', spacing=8); img.alpha_composite(lay)

def _rate(t):
    # the same spin-up as path.js
    if t < 22.5: return 0.45
    if t < 26.0:
        x = min(1.0, max(0.0, (t - 22.5) / 3.5)); e = 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
        return min(716.0, 0.45 * math.exp(math.log(716 / 0.45) * e))
    return 716.0

def DRAW(img, t, H_):
    W, H = img.size
    f_mid = H_['font']('Commissioner.ttf', 40, 600)
    f_num = H_['font']('Unbounded.ttf', 44, 600)
    f_big = H_['font']('Unbounded.ttf', 120, 600)
    i = min(len(LAB) - 1, int(t * 30)); L = LAB[i]
    # Kyiv: a scale bar under the star, 20 km
    a = _fade(t, 12.0, 14.55)
    if a > 0 and L.get('star'):
        cx, cy, r = (v * _s for v in L['star'])
        y = cy + r + 46
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.line([(cx - r, y), (cx + r, y)], fill=(255, 255, 255, int(235 * a)), width=5)
        d.line([(cx - r, y - 16), (cx - r, y + 16)], fill=(255, 255, 255, int(235 * a)), width=5)
        d.line([(cx + r, y - 16), (cx + r, y + 16)], fill=(255, 255, 255, int(235 * a)), width=5)
        img.alpha_composite(lay)
        _text(img, (cx, y + 50), '20 км', f_num, SUN_C, alpha=a)
    # the balance: what lies on each pan
    a = _fade(t, 19.1, 21.95)
    if a > 0 and L.get('panL'):
        lx, ly = L['panL'][0] * _s, L['panL'][1] * _s
        rx, ry = L['panR'][0] * _s, L['panR'][1] * _s
        _text(img, (max(190, min(W - 190, lx)), ly + 110), '1 ложка\n≈ 1 млрд т', f_mid, SUN_C, alpha=a)
        _text(img, (max(230, min(W - 230, rx)), ry - 200), 'усі люди Землі\n≈ 0,4 млрд т', f_mid, (255, 255, 255), alpha=a)
    # the spin-up counter
    a = _fade(t, 22.3, 27.2)
    if a > 0:
        v = _rate(t)
        _text(img, (W / 2, 330), f'{v:.0f}' if v >= 10 else f'{v:.1f}'.replace('.', ','), f_big, SUN_C if v >= 715 else (255, 255, 255), alpha=a)
        _text(img, (W / 2, 450), 'обертів за секунду', f_mid, (200, 210, 230), alpha=a)
