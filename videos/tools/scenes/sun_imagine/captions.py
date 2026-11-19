# «А ти уявляєш Сонце так?» — captions over render.py's frames. Voice (voice.mp3, 50,8 s) laid in 5 parts (scene.json):
# pauses for the reveal (after «так?»), before «А якби Сонце раптом зникло» and before the call to share.
# DRAW: the counters (1 300 000 Earths, ×745, 5 500 → 2 000 000 °C, 1 hour = 1 year, the 8:20 countdown) and the names
# next to things (from render.labels).
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)

DURATION = 58.4
CAPTIONS = [
    (-1.0, 2.55, 'hook', 'Ти щодня бачиш\nСонце жовтим'),
    (2.86, 4.6, 'cap', 'А насправді воно біле'),
    (4.85, 7.15, 'cap', 'Жовтим його робить\nнаше повітря'),
    (7.85, 9.7, 'hook', 'А ти уявляєш\nСонце так?'),
    (10.3, 14.65, 'cap', 'У нього вмістилося б\n1,3 мільйона таких Земель'),
    (14.9, 19.6, 'cap', 'І важить воно понад 700 разів\nбільше, ніж усі планети разом'),
    (20.0, 22.3, 'cap', 'Плями темні лише на вигляд'),
    (22.6, 24.8, 'cap', 'Найбільші — більші за Землю'),
    (25.1, 28.55, 'cap', 'Поверхня — близько 5 500 °C'),
    (28.7, 31.35, 'cap', 'А корона над нею —\nдо 2 мільйонів °C'),
    (31.7, 38.15, 'cap', 'За одну годину на Землю падає\nстільки сонячної енергії, скільки\nлюдство використовує за рік'),
    (38.5, 42.35, 'cap', 'Саме вона вирощує кожну рослину\nі всю твою їжу'),
    (43.4, 45.15, 'cap', 'А якби Сонце раптом зникло…'),
    (45.45, 48.95, 'cap', '…ти ще 8 хвилин 20 секунд\nнічого б не помітив'),
    (50.1, 53.25, 'cap', 'Перешли тому, хто досі\nмалює Сонце жовтим'),
]
NAMES = []
SUBS = []
CREDITS = [
    (0.0, 7.4, 'Візуалізація: Небозвід · Земля: NASA Blue Marble'),
    (7.6, 10.2, 'Сонце: візуалізація за даними NASA · колір — справжній, білий'),
    (10.3, 14.6, 'Об’єм Сонця — 1,3 млн об’ємів Землі (NASA)'),
    (14.9, 19.6, 'Маси: Сонце 1,989·10³⁰ кг, усі планети ≈ 2,67·10²⁷ кг · планети: Solar System Scope'),
    (20.0, 24.8, 'Пляма — до 4 000 °C, тому темніша за 5 500-градусну поверхню'),
    (25.1, 31.4, 'Художня візуалізація · масштаби стиснуто'),
    (31.7, 38.2, 'Сонце дає Землі ~1,7·10¹⁷ Вт; людство — ~620 ЕДж на рік'),
    (38.5, 42.3, 'Земля: NASA Blue Marble · зорі: ESO/S. Brunier (CC BY 4.0)'),
    (43.4, 53.2, 'Відстань Сонце–Земля стиснуто · художня візуалізація'),
]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 72
HOOK_Y = 470
CAP_FADE = 0.3
SUBSCRIBE_AT = 33.5
SUBSCRIBE_Y = 1700
END_CARD = 53.7
END_TITLE = 'Наука про Землю\nі космос — на сайті'

def _sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def _sp(n): return f'{int(round(n)):,}'.replace(',', ' ')

_R = {}
def _render():
    if 'r' not in _R:
        import render as R
        _R['r'] = R
    return _R['r']

def _scrims(img, t):
    """darken the caption bands where the picture is bright (the white Sun), so the white text always reads"""
    import numpy as np
    from PIL import Image
    a = np.asarray(img.convert('L'), np.float32) / 255
    out = None
    yy = np.arange(img.size[1], dtype=np.float32)
    for y0, y1, yc, sg in ((40, 560, 330, 210.0), (1250, 1560, 1405, 125.0), (1800, 1870, 1835, 50.0)):
        m = float(a[y0:y1].mean())
        k = min(0.5, max(0.0, (m - 0.45) * 1.4))
        if k <= 0: continue
        if out is None: out = np.zeros(img.size[1], np.float32)
        out = np.maximum(out, np.exp(-((yy - yc) / sg) ** 2) * k)
    if out is not None:
        out = np.repeat(out[:, None], img.size[0], 1)
    if out is not None:
        sh = Image.fromarray((out * 255).astype(np.uint8), 'L')
        black = Image.new('RGBA', img.size, (8, 10, 18, 255)); black.putalpha(sh)
        img.alpha_composite(black)

def DRAW(img, t, g):
    _scrims(img, t)
    big = g['f_tick']; small = g['f_end3']; SUN = g['SUN']
    def show(a, b, val, label, col=SUN, y=330):
        al = g['fade'](t, a, b, 0.35)
        if al > 0:
            g['draw_block'](img, val, big, y, al, fill=col)
            if label: g['draw_block'](img, label, small, y + 100, al, fill=(200, 208, 224))
    # 1.3 million Earths (the count follows the fill: render.py fills 12.1 → 14.3 s, power 1.15)
    n = 1300000 * _sm((t - 12.1) / 2.2) ** 1.15 if t > 12.1 else 0
    show(12.0, 14.7, _sp(n), 'Земель')
    # x745 by mass
    m = 1 + 744 * _sm((t - 16.6) / 1.6)
    show(15.6, 19.6, '×' + _sp(m), 'маса Сонця проти всіх планет')
    # temperatures
    show(25.3, 28.55, '5 500 °C', 'поверхня')
    tc = 5500 * (2000000 / 5500) ** _sm((t - 29.0) / 1.6)
    show(28.7, 31.4, _sp(tc) + ' °C', 'корона', col=(255, 196, 120))
    # an hour of sunlight = a year of humanity's energy
    show(32.4, 38.1, '1 год = 1 рік', 'сонячної енергії на Землі  ·  енергії людства')
    # the countdown of the last light
    if 45.3 < t < 49.6:
        x = min(1.0, max(0.0, (t - 45.5) / (48.95 - 45.5)))
        v = int(math.ceil(500 * (1 - x)))
        col = (255, 255, 255) if v > 0 else (255, 120, 110)
        show(45.3, 49.6, f'{v // 60}:{v % 60:02d}', 'світло ще летить до Землі' if v > 0 else 'темрява', col=col)
    # names next to things
    for x, y, text, al, anchor in _render().labels(t):
        if al <= 0: continue
        _label(img, x, y, text, g, al, anchor)

def _label(img, x, y, text, g, al, anchor):
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np
    f = g['f_end2']
    # on a bright background: dark text with a light halo
    xi, yi = int(min(max(x, 40), img.size[0] - 40)), int(min(max(y, 40), img.size[1] - 40))
    bg = float(np.asarray(img.crop((xi - 40, yi - 30, xi + 120, yi + 30)).convert('L')).mean()) / 255
    if bg > 0.6:
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        halo = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(halo).text((x, y), text, font=f, fill=(255, 255, 255, int(255 * al)), anchor=anchor, stroke_width=6, stroke_fill=(255, 255, 255, int(200 * al)))
        img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(3)))
        d.text((x, y), text, font=f, fill=(20, 28, 48, int(255 * al)), anchor=anchor)
        img.alpha_composite(lay)
        return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x, y + 2), text, font=f, fill=(0, 0, 0, int(220 * al)), anchor=anchor)
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(sh)
    d.text((x, y), text, font=f, fill=(255, 255, 255, int(255 * al)), anchor=anchor)
    img.alpha_composite(lay)
