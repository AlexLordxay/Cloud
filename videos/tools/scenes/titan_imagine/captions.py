# «А ти уявляєш Титан так?» — captions and drawings over the frames (frames.py), timed to the voice (scene.json parts:
# phrases at 0.3, 4.0, 6.1, 10.37, 16.38, 25.79, 33.56 s). compose.py draws them at 1080 × 1920.
import json, math, os
from PIL import Image, ImageDraw, ImageFilter

DURATION = 41.5
HOOK_SIZE = 64
HOOK_Y = 1560
CAPTIONS = [
    (-1.0, 3.75, 'hook', 'На Титані ти міг би\nлітати, махаючи\nруками'),
    (4.0, 5.95, 'cap', 'А ти уявляєш Титан так?'),
    (6.1, 10.2, 'cap', 'Найбільший супутник Сатурна —\nбільший за планету Меркурій'),
    (10.37, 16.2, 'cap', 'Повітря вчетверо щільніше за наше,\nа тяжіння — у 7 разів слабше'),
    (16.38, 22.9, 'cap', 'Там ідуть дощі, течуть ріки\nй хлюпочуть моря —'),
    (23.0, 25.6, 'cap', 'тільки не з води,\nа з рідкого метану'),
    (25.79, 33.3, 'cap', 'У 2034 році туди прилетить\nдрон NASA «Дрегонфлай»'),
    (33.56, 36.0, 'cap', 'Ти б наважився полетіти на Титан?'),
]
NAMES = []
SUBS = []
CREDITS = [(0.2, 3.6, 'Художня візуалізація · нахил кілець перебільшено'),
           (3.9, 6.0, 'Моря й ріки — за радаром «Кассіні»'),
           (6.2, 10.9, 'Розміри справжні · карти: NASA/JPL, Solar System Scope (CC BY 4.0)'),
           (11.0, 16.2, 'Карта Титана: NASA/JPL/Univ. of Arizona (VIMS «Кассіні»)'),
           (16.4, 25.6, 'Рельєф — художня реконструкція · освітлення підсилено'),
           (25.8, 33.4, '«Дрегонфлай» (NASA/APL) — художня модель'),
           (33.6, 36.0, 'Художня візуалізація')]
CUTS = []
FADE_IN = 0
SUBSCRIBE_AT = 27.0
END_CARD = 36.4
END_TITLE = 'Титан:\nметанові моря'
NEXT_TEASE = 'Не проґав наступний супутник'

HERE = os.path.dirname(os.path.abspath(__file__))
_LP = os.path.join(HERE, '..', '..', 'work', 'titan_imagine', 'labels.json')
LAB = json.load(open(_LP)) if os.path.exists(_LP) else {}
SUN_C = (243, 185, 100)
COLD_C = (170, 215, 255)
_s = 1080 / 720

def _fade(t, a, b, d=0.4):
    x = max(0.0, min(1.0, (t - a) / d, (b - t) / d)); return x * x * (3 - 2 * x)

def _text(img, xy, s, fnt, fill, anchor='mm', alpha=1.0):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).multiline_text((xy[0], xy[1] + 3), s, font=fnt, fill=(0, 0, 0, int(230 * alpha)), anchor=anchor, align='center', spacing=8)
    sh = sh.filter(ImageFilter.GaussianBlur(8)); img.alpha_composite(sh); img.alpha_composite(sh)
    d.multiline_text(xy, s, font=fnt, fill=fill + (int(255 * alpha),), anchor=anchor, align='center', spacing=8); img.alpha_composite(lay)

def _lab(t):
    return LAB.get(str(min(int(round(t * 30)), int(DURATION * 30) - 1)), {})

def DRAW(img, t, H_):
    W, H = img.size
    f_mid = H_['font']('Commissioner.ttf', 40, 600)
    f_big = H_['font']('Unbounded.ttf', 110, 600)
    f_sm = H_['font']('Commissioner.ttf', 32, 500)
    L = _lab(t)
    # Saturn behind Titan
    a = _fade(t, 6.4, 8.5)
    if a > 0 and L.get('sat'):
        x, y, r = (v * _s for v in L['sat'])
        if 0 < x < W and 0 < y < H:
            _text(img, (x, y - r - 50), 'Сатурн', f_sm, (235, 225, 205), alpha=a)
    # Titan and Mercury side by side: names and sizes
    a = _fade(t, 8.8, 10.9)
    if a > 0 and L.get('ti') and L.get('me'):
        for key, name, col in (('ti', 'Титан · 5 150 км', SUN_C), ('me', 'Меркурій · 4 879 км', (215, 218, 228))):
            x, y, r = (v * _s for v in L[key])
            _text(img, (x, y + r * 1.25 + 50), name, f_sm, col, alpha=a)
    # the air and the gravity
    a = _fade(t, 11.0, 13.5)
    if a > 0:
        _text(img, (W / 2, 1560), '×4', f_big, SUN_C, alpha=a)
        _text(img, (W / 2, 1670), 'щільніше повітря, ніж на Землі', f_mid, (235, 225, 210), alpha=a)
    a = _fade(t, 13.6, 16.2)
    if a > 0:
        _text(img, (W / 2, 1560), '1/7', f_big, SUN_C, alpha=a)
        _text(img, (W / 2, 1670), 'земного тяжіння', f_mid, (235, 225, 210), alpha=a)
    # the cold
    a = _fade(t, 23.1, 25.6)
    if a > 0:
        _text(img, (W / 2, 330), '−180 °C', f_big, COLD_C, alpha=a)
        _text(img, (W / 2, 440), 'рідкий метан замість води', f_mid, (225, 230, 240), alpha=a)
    # Dragonfly
    a = _fade(t, 26.4, 33.0)
    if a > 0:
        _text(img, (W / 2, 1560), '«Дрегонфлай» · NASA', f_mid, SUN_C, alpha=a)
        _text(img, (W / 2, 1616), 'старт 2028 · прибуття 2034', f_sm, (235, 225, 210), alpha=a)
