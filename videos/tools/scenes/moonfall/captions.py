# «Що, якби Місяць упав на Землю?»: no voice, so the words are few — the hook, four captions, the question; and what
# a helmet would show: the time left, the distance to the Moon, the tide, a ring round the Moon while it is still a speck.
# DRAW (compose.py calls it for every frame) also adds the flash of the impact. Nothing else is in front of the eyes:
# the camera is the astronaut's head (the author: no hands, no helmet rim — just the view, turning as the head turns).
# The per-frame numbers come from the render (work/moonfall/frames/f_NNNNN.json, written by render.js from shots.js).
import json, math, os
from PIL import Image, ImageDraw, ImageFilter

DURATION = 46.0
CAPTIONS = [
    (-1.0, 2.9, 'hook', 'Що, якби Місяць\nупав на Землю?'),
    (3.3, 8.6, 1330, 'Місяць зупинився.\nДо удару — майже 5 діб'),
    (13.2, 17.8, 1330, 'Припливи — у 1000 разів\nсильніші за звичайні'),
    (23.0, 27.6, 1330, 'Межа Роша:\nМісяць розривається'),
    (34.6, 38.8, 1330, 'Енергія удару — у мільйони разів\nбільша, ніж в астероїда,\nщо вбив динозаврів'),
    (40.0, 43.4, 1330, 'Про що ще розповісти?\nПиши в коментарях'),
]
CREDITS = [(0.0, 43.3, 'Художня візуалізація · карти Землі: NASA, Mapzen')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 74
HOOK_Y = 480
SUBSCRIBE_AT = 19.6
SUBSCRIBE_Y = 560
END_CARD = 43.5
END_TITLE = 'Більше космосу —\nна сайті'

# CLEAN=1 (the author, 30.10): a clean cut — only the Небозвід logo; no captions, readouts, credits, button or end card
CLEAN = os.environ.get('CLEAN') == '1'
if CLEAN:
    CAPTIONS, CREDITS, SUBSCRIBE_AT, END_CARD = [], [], None, 999.0

FPS, W, H = 30, 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.abspath(os.path.join(HERE, '../../work/moonfall/frames'))
SUN = (243, 185, 100)
_FONTS = {}


def _state(t):
    try:
        with open(os.path.join(FRAMES, f'f_{int(round(t * FPS)):05d}.json')) as f: return json.load(f)
    except Exception:
        return {}


def _fade(t, a, b, d=0.35):
    return max(0.0, min(1.0, (t - a) / d, (b - t) / d))


def _sm(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def _num(v):
    return f'{int(round(v)):,}'.replace(',', ' ')


def _clock(s):
    s = max(0, int(s))
    if s >= 86400: return f'{s // 86400} д {s % 86400 // 3600:02d} год {s % 3600 // 60:02d} хв'
    if s >= 3600: return f'{s // 3600} год {s % 3600 // 60:02d} хв {s % 60:02d} с'
    return f'{s // 60:02d}:{s % 60:02d}'


def _font(g, file, size, w):
    k = (file, size, w)
    if k not in _FONTS: _FONTS[k] = g['font'](file, size, w)
    return _FONTS[k]


def DRAW(img, t, g):
    st = _state(t)
    d = ImageDraw.Draw(img)
    # the Moon while it is still small: a thin ring and its name
    if st and st.get('front') and 3.2 < t < 16.0 and not CLEAN:
        mx, my, mr = st['mx'] * W, st['my'] * H, st['mr'] * H
        al = _fade(t, 3.4, 15.6, 0.6) * (1 - _sm((mr - 18) / 20))
        if al > 0:
            R = max(26.0, mr * 1.5)
            lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
            ld.ellipse((mx - R, my - R, mx + R, my + R), outline=(255, 255, 255, int(170 * al)), width=2)
            for k in range(4):                                     # four little ticks round the ring
                a = k * math.pi / 2 + math.pi / 4
                ld.line((mx + math.cos(a) * (R + 6), my + math.sin(a) * (R + 6), mx + math.cos(a) * (R + 16), my + math.sin(a) * (R + 16)), fill=(255, 255, 255, int(170 * al)), width=2)
            ld.text((mx + R + 22, my), 'Місяць', font=_font(g, 'Commissioner.ttf', 34, 600), fill=(255, 255, 255, int(220 * al)), anchor='lm')
            img.alpha_composite(lay)
    # the flash of the impact
    if t > 33.4:
        fl = min(1.0, (t - 33.4) / 0.12) * (0.92 * math.exp(-max(0.0, t - 33.55) / 0.45))
        if fl > 0.01: img.alpha_composite(Image.new('RGBA', img.size, (255, 246, 230, int(255 * fl))))
    if 1.62 < t < 1.95:                                            # the rewind starts with a blink
        img.alpha_composite(Image.new('RGBA', img.size, (255, 255, 255, int(150 * _fade(t, 1.62, 1.95, 0.12)))))
    # the readouts, up top under the logo
    if st and not CLEAN:
        tp = st.get('tp', 0)
        al = _fade(t, -1, 35.4, 0.4)
        if al > 0:
            draw = g['draw_block']
            red = tp > -60
            draw(img, 'ДО УДАРУ', _font(g, 'Commissioner.ttf', 30, 600), 285, al, fill=(200, 208, 224))
            draw(img, _clock(-tp) if tp < 0 else '00:00', _font(g, 'Unbounded.ttf', 58, 600), 345, al, fill=(255, 110, 80) if red else SUN)
            if tp < 0 and t > 2.9:
                draw(img, f"до Місяця {_num(st['z'] * 1000)} км", _font(g, 'Commissioner.ttf', 32, 500), 410, al, fill=(220, 226, 238))
            if 1.7 < t < 3.0:
                draw(img, '◀◀', g['ImageFont'].truetype(g['F_STAR'], 40), 410, _fade(t, 1.7, 3.0, 0.15), fill=(255, 255, 255))
        za = _fade(t, 10.4, 23.4, 0.5)
        if za > 0 and st.get('zeta', 0) > 0.3:
            z = st['zeta']
            txt = f'приплив ≈ {z:.0f} м' if z < 1000 else f'приплив ≈ {z / 1000:.1f} км'.replace('.', ',')
            g['draw_block'](img, txt, _font(g, 'Commissioner.ttf', 34, 600), 470, za, fill=(150, 205, 255))
