# «А ти уявляєш Європу так?» — captions and drawings over the frames (frames.py), timed to the voice (scene.json parts:
# phrases at 0.3, 4.67, 7.19, 14.07, 21.74, 27.27, 33.63, 42.18 s). compose.py draws them at 1080 × 1920.
import json, math, os
from PIL import Image, ImageDraw, ImageFilter

DURATION = 48.5
HOOK_SIZE = 64
HOOK_Y = 1560
CAPTIONS = [
    (-1.0, 4.35, 'hook', 'Під цим льодом води більше,\nніж у всіх океанах Землі'),
    (4.67, 6.85, 'cap', 'А ти уявляєш Європу так?'),
    (7.19, 13.7, 'cap', 'Супутник Юпітера, трохи менший\nза наш Місяць — 3 120 км'),
    (14.07, 17.8, 'cap', 'Уся поверхня — суцільний лід,\nпорізаний тріщинами'),
    (18.0, 21.4, 'cap', 'а на екваторі — мінус 160 °C'),
    (21.74, 26.9, 'cap', 'Але під кригою — солоний океан\nглибиною до 150 км'),
    (27.27, 29.75, 'cap', 'А ось такий Юпітер у небі Європи —'),
    (29.85, 33.3, 'cap', 'у 20 разів більший,\nніж Місяць у нашому небі'),
    (33.63, 40.3, 'cap', 'У 2030 році прилетить зонд NASA\n«Європа Кліпер»,\nщоб вивчити цей океан'),
    (42.18, 45.35, 'cap', 'Як думаєш, є під цим льодом життя?'),
]
NAMES = []
SUBS = []
CREDITS = [(0.2, 13.6, 'Карта: NASA/JPL, USGS (Galileo, Voyager) · будова — за даними NASA'),
           (13.8, 21.5, 'Рельєф — художня реконструкція за знімками Galileo, висоти ×3'),
           (21.8, 27.3, 'Товщину криги ще не виміряно: її вивчатиме «Європа Кліпер»'),
           (27.4, 33.5, 'Юпітер: Solar System Scope (CC BY 4.0) · розмір у небі справжній'),
           (33.8, 40.4, '«Європа Кліпер» — художня модель'),
           (40.6, 45.4, 'Художня візуалізація')]
CUTS = []
FADE_IN = 0
SUBSCRIBE_AT = 35.0
END_CARD = 45.5
END_TITLE = 'Європа:\nокеан під кригою'
NEXT_TEASE = 'Не проґав наступний супутник'

HERE = os.path.dirname(os.path.abspath(__file__))
_LP = os.path.join(HERE, '..', '..', 'work', 'europa_imagine', 'labels.json')
LAB = json.load(open(_LP)) if os.path.exists(_LP) else {}
SUN_C = (243, 185, 100)
ICE_C = (170, 215, 255)
_s = 1080 / 720
_moon = None

def _fade(t, a, b, d=0.4):
    x = max(0.0, min(1.0, (t - a) / d, (b - t) / d)); return x * x * (3 - 2 * x)

def _text(img, xy, s, fnt, fill, anchor='mm', alpha=1.0):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).multiline_text((xy[0], xy[1] + 3), s, font=fnt, fill=(0, 0, 0, int(230 * alpha)), anchor=anchor, align='center', spacing=8)
    sh = sh.filter(ImageFilter.GaussianBlur(8)); img.alpha_composite(sh); img.alpha_composite(sh)
    d.multiline_text(xy, s, font=fnt, fill=fill + (int(255 * alpha),), anchor=anchor, align='center', spacing=8); img.alpha_composite(lay)

def _line(img, pts, alpha, width=3, col=(255, 255, 255)):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).line(pts, fill=col + (int(220 * alpha),), width=width)
    img.alpha_composite(lay)

def _lab(t):
    return LAB.get(str(min(int(round(t * 30)), int(DURATION * 30) - 1)), {})

def DRAW(img, t, H_):
    global _moon
    W, H = img.size
    f_mid = H_['font']('Commissioner.ttf', 40, 600)
    f_num = H_['font']('Unbounded.ttf', 44, 600)
    f_big = H_['font']('Unbounded.ttf', 110, 600)
    f_sm = H_['font']('Commissioner.ttf', 32, 500)
    L = _lab(t)
    # Europa and the Moon side by side: their names and sizes
    a = _fade(t, 7.7, 13.7)
    if a > 0 and L.get('eu') and L.get('mo'):
        for key, name, col in (('eu', 'Європа · 3 122 км', (255, 255, 255)), ('mo', 'Місяць · 3 475 км', (200, 210, 230))):
            x, y, r = (v * _s for v in L[key])
            _text(img, (x, y + r + 56), name, f_sm, col, alpha=a)
    # the cold
    a = _fade(t, 18.0, 21.5)
    if a > 0:
        _text(img, (W / 2, 330), '−160 °C', f_big, ICE_C, alpha=a)
        _text(img, (W / 2, 440), 'на екваторі Європи', f_mid, (200, 210, 230), alpha=a)
    # the block: the ice shell and the ocean under it
    a = _fade(t, 22.2, 27.3)
    if a > 0 and L.get('ice') and L.get('ocean'):
        ix, iy, _ = (v * _s for v in L['ice']); ox, oy, _ = (v * _s for v in L['ocean'])
        side = -1 if ix > W / 2 else 1
        tx = ix + side * 150
        _line(img, [(ix, iy), (tx - side * 10, iy)], a); _text(img, (tx, iy), 'лід', f_mid, (255, 255, 255), anchor='lm' if side > 0 else 'rm', alpha=a)
        tx = ox + side * 150
        _line(img, [(ox, oy), (tx - side * 10, oy)], a); _text(img, (tx, oy), 'солоний океан\nдо 150 км', f_mid, ICE_C, anchor='lm' if side > 0 else 'rm', alpha=a)
    # the Moon as we see it, next to Jupiter as Europa sees it (true relative size)
    a = _fade(t, 29.9, 33.5)
    if a > 0 and L.get('jup'):
        jx, jy, jr = (v * _s for v in L['jup'])
        mr = max(2.5, jr * math.tan(math.radians(0.259)) / math.tan(math.atan(69911 / 671100)))
        mx, my = W * 0.78, jy + jr + 140
        if _moon is None:
            _moon = Image.open(os.path.join(HERE, '..', '..', '..', '..', 'planetarium', 'textures', 'moon.jpg')).convert('RGB').resize((64, 32))
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.ellipse((mx - mr - 10, my - mr - 10, mx + mr + 10, my + mr + 10), outline=(255, 255, 255, int(200 * a)), width=3)
        d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=(235, 235, 228, int(255 * a)))
        img.alpha_composite(lay)
        _text(img, (mx, my + mr + 52), 'Місяць у нашому\nнебі — ось такий', f_sm, (230, 235, 245), alpha=a)
    # the spacecraft
    a = _fade(t, 34.2, 40.2)
    if a > 0 and L.get('sc'):
        x, y, r = (v * _s for v in L['sc'])
        _text(img, (W / 2, min(H - 560, y + 330)), '«Європа Кліпер» · NASA', f_mid, SUN_C, alpha=a)
        _text(img, (W / 2, min(H - 500, y + 390)), 'запущено 2024 · прибуття 2030', f_sm, (210, 218, 232), alpha=a)
