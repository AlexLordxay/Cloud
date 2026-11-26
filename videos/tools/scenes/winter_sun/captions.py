# «Чому взимку холодно, якщо Земля найближче до Сонця?» — captions and drawings over the frames (render.py writes the
# screen positions to work/winter_sun/labels.json). Voice (scene.json parts): the whole read at +0.3 s, the last question
# moved to 44.17 s (a 2 s pause before it). compose.py draws all this at 1080 × 1920.
import json, os
from PIL import Image, ImageDraw, ImageFilter

DURATION = 50.5
HOOK_SIZE = 62
HOOK_Y = 1590
CAPTIONS = [
    (-1.0, 7.9, 'hook', 'Узимку Земля ближче\nдо Сонця, ніж улітку'),
    (8.3, 10.1, 'cap', 'Чому ж тоді взимку холодно?'),
    (10.32, 11.75, 'cap', 'Справа не у відстані'),
    (11.88, 15.7, 'cap', 'Вісь Землі нахилена'),
    (15.95, 19.5, 'cap', 'Узимку наша половина\nвідвернута від Сонця'),
    (19.75, 23.85, 'cap', 'Опівдні над Києвом Сонце\nпіднімається лише на 16°'),
    (24.18, 26.0, 'cap', 'а влітку — на 63°'),
    (26.28, 28.55, 'cap', 'Низьке Сонце світить навскоси'),
    (28.74, 33.35, 'cap', 'те саме світло розтікається\nна втричі більшу площу'),
    (33.62, 35.95, 'cap', 'День узимку — лише 8 годин'),
    (36.18, 38.05, 'cap', 'улітку — 16,5'),
    (38.29, 42.3, 'cap', 'А в Австралії зараз літо —\nСонце стоїть високо'),
    (44.17, 46.85, 'cap', 'А ти знав, що взимку\nми ближче до Сонця?'),
]
NAMES = []
SUBS = []
CREDITS = [(0.2, 8.0, 'Орбіта — в масштабі; Сонце й Земля збільшені'),
           (8.0, 19.6, 'Земля: NASA Blue Marble, Black Marble · сніг і хмари — художня візуалізація'),
           (19.7, 33.4, 'Київ: Sentinel-2 cloudless 2016 (EOX, Copernicus) · сніг — художня візуалізація'),
           (33.5, 38.1, 'Шлях Сонця над Києвом 21 грудня і 21 червня — розрахунок'),
           (38.2, 46.9, 'Художня візуалізація · Земля: NASA Blue Marble')]
CUTS = []
FADE_IN = 0
SUBSCRIBE_AT = 21.0
END_CARD = 47.0
END_TITLE = 'Чому взимку\nхолодно?'
NEXT_TEASE = 'Не проґав наступне відео'

HERE = os.path.dirname(os.path.abspath(__file__))
_LP = os.path.join(HERE, '..', '..', 'work', 'winter_sun', 'labels.json')
LAB = json.load(open(_LP)) if os.path.exists(_LP) else {}
SUN_C = (243, 185, 100)
ICE_C = (170, 215, 255)

def _fade(t, a, b, d=0.4):
    x = max(0.0, min(1.0, (t - a) / d, (b - t) / d)); return x * x * (3 - 2 * x)

def _text(img, xy, s, fnt, fill, anchor='mm', alpha=1.0):
    if alpha <= 0: return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).multiline_text((xy[0], xy[1] + 3), s, font=fnt, fill=(0, 0, 0, int(230 * alpha)), anchor=anchor, align='center', spacing=8)
    sh = sh.filter(ImageFilter.GaussianBlur(8)); img.alpha_composite(sh); img.alpha_composite(sh)
    d.multiline_text(xy, s, font=fnt, fill=fill + (int(255 * alpha),), anchor=anchor, align='center', spacing=8)
    img.alpha_composite(lay)

def _lab(t):
    return LAB.get(str(min(int(round(t * 30)), int(DURATION * 30) - 1)), {})

def _clampx(x, w=170):
    return min(1080 - w, max(w, x))

def DRAW(img, t, H_):
    f_mid = H_['font']('Commissioner.ttf', 40, 600)
    f_num = H_['font']('Unbounded.ttf', 46, 600)
    f_big = H_['font']('Unbounded.ttf', 64, 600)
    f_sm = H_['font']('Commissioner.ttf', 32, 500)
    L = _lab(t)
    # the orbit: 3 January and 5 July
    for a, b in ((3.4, 7.9), (44.0, 47.0)):
        al = _fade(t, a, b)
        if al > 0 and L.get('earth'):
            x, y, r = L['earth']
            _text(img, (_clampx(x), y + r + 62), '3 січня\n147,1 млн км', f_sm, SUN_C, alpha=al)
        al2 = _fade(t, a + 0.6, b)
        if al2 > 0 and L.get('jul'):
            x, y, r = L['jul']
            _text(img, (_clampx(x), y - r - 62), '5 липня\n152,1 млн км', f_sm, (200, 215, 240), alpha=al2)
    # the axis: the angle
    al = _fade(t, 12.2, 15.8)
    if al > 0 and L.get('angle'):
        x, y = L['angle']
        _text(img, (x + 20, y - 46), '23,44°', f_num, SUN_C, alpha=al)
    # the year: which month, where the north leans
    al = _fade(t, 16.4, 19.5, 0.25)
    if al > 0 and L.get('earth') and L.get('month'):
        x, y, r = L['earth']
        sub = {'грудень': 'північ — від Сонця', 'червень': 'північ — до Сонця'}[L['month']]
        _text(img, (_clampx(x, 200), y + r + 70), L['month'] + '\n' + sub, f_sm, (235, 240, 250), alpha=al)
    # Kyiv: the noon Sun, 16° and 63°
    for key, txt, a, b in (('sun_w', '16°', 20.4, 26.0), ('sun_s', '63°', 24.4, 26.2)):
        al = _fade(t, a, b)
        if al > 0 and L.get(key):
            x, y, k = L[key]
            _text(img, (x + 62, y - 50), txt, f_num, SUN_C if key == 'sun_s' else ICE_C, alpha=al * min(1.0, k))
    al = _fade(t, 20.0, 26.0)
    if al > 0 and L.get('centre'):
        x, y = L['centre']
        _text(img, (x, y - 62), 'Київ', f_mid, (255, 255, 255), alpha=al)
    # the beam: the footprint, ×3.2
    al = _fade(t, 26.6, 33.4)
    if al > 0 and L.get('alt') is not None and L.get('foot'):
        alt = L['alt']; area = L.get('area', 1.0)
        _text(img, (540, 420), f'{alt:.0f}°', f_big, SUN_C if alt > 40 else ICE_C, alpha=al)
        if area > 1.05:
            _text(img, (540, 510), f'площа ×{area:.1f}'.replace('.', ','), f_mid, (255, 255, 255), alpha=al * min(1.0, (area - 1.0) / 1.2))
        if t > 30.0:
            _text(img, (540, 570), 'на кожен метр — утричі менше тепла', f_sm, (215, 222, 236), alpha=al * _fade(t, 30.0, 33.4))
    # the day: two counters up top, running at the same clock speed (the winter one stops at 8 h)
    al = _fade(t, 33.9, 38.1)
    if al > 0 and L.get('win') and L.get('sum'):
        for (key, name, full, y0, col) in (('win', '21 грудня', 8.0, 400, ICE_C), ('sum', '21 червня', 16.5, 480, SUN_C)):
            hrs = L[key][2]
            txt = f'{int(hrs)} год' if hrs < full - 0.12 else ('8 год' if key == 'win' else '16,5 год')
            _text(img, (540, y0), f'{name}:  {txt}', f_num, col, alpha=al)
