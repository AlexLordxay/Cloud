# «Що, якби Місяць упав на Землю?»: no voice, so the words are few — the hook, four captions, the question; and what
# a helmet would show: the time left, the distance to the Moon, the tide, a ring round the Moon while it is still a speck.
# DRAW (compose.py calls it for every frame) also lays the inside of the helmet over the view: its dark rim, a faint
# reflection on the visor, the flash of the impact and the gold sun visor coming down after it.
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

FPS, W, H = 30, 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.abspath(os.path.join(HERE, '../../work/moonfall/frames'))
SUN = (243, 185, 100)
_FONTS, _HELMET = {}, {}


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


def _helmet():
    # the visor seen from inside the helmet: the opening's rim curving across the top and bottom of the view (dark,
    # soft), the seal round it catching the light (brighter toward the upper left), a faint sheen on the curved glass.
    # Drawn bigger than the frame so it can lag a little behind the head's turns (the helmet sits on the suit).
    if 'img' in _HELMET: return _HELMET['img']
    import numpy as np
    P = 80
    y, x = np.mgrid[0:H + 2 * P, 0:W + 2 * P].astype(np.float32)
    dx, dy = (x - P - W * 0.5) / (W * 0.60), (y - P - H * 0.485) / (H * 0.535)
    r = (np.abs(dx) ** 2.4 + np.abs(dy) ** 2.4) ** (1 / 2.4)
    dark = np.clip((r - 0.90) / 0.13, 0, 1) ** 1.3 * 0.96
    lightside = np.clip(0.55 - 0.45 * (dx * 0.6 + dy * 0.8), 0.15, 1.0)
    seal = np.exp(-((r - 0.955) / 0.012) ** 2) * 0.22 * lightside
    sheen = np.exp(-(((x - P) - (y - P) * 0.42 - W * 0.12) / (W * 0.20)) ** 2) * 0.03 * np.clip(1 - (y - P) / (H * 0.75), 0, 1)
    arc = np.exp(-((r - 0.80) / 0.035) ** 2) * 0.025 * np.clip(-dy, 0, 1)
    glow = seal + sheen + arc
    a = np.clip(dark + glow, 0, 1)
    c = np.where(a > 1e-4, 255 * glow / np.maximum(a, 1e-4), 0)
    rgb = np.dstack([c * 0.96, c * 0.92, c * 0.86])
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA')
    _HELMET['img'] = im
    return im


def DRAW(img, t, g):
    st = _state(t)
    d = ImageDraw.Draw(img)
    # the Moon while it is still small: a thin ring and its name
    if st and st.get('front') and 3.2 < t < 16.0:
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
    # the gold sun visor slides down over the glass after the flash: amber, a little darker, its edge passing down
    gold = _sm((t - 33.75) / 0.75)
    if gold > 0:
        edge = gold * H * 1.08
        mask = Image.new('L', (1, H))
        mask.putdata([int(255 * min(1.0, max(0.0, (edge - yy) / 60.0))) for yy in range(H)])
        mask = mask.resize(img.size)
        gl = Image.new('RGBA', img.size, (105, 62, 12, 80)); gl.putalpha(mask.point(lambda v: v * 80 // 255))
        img.alpha_composite(gl)
        if gold < 1:
            ln = Image.new('RGBA', img.size, (0, 0, 0, 0))
            ImageDraw.Draw(ln).rectangle((0, edge - 3, W, edge + 3), fill=(255, 220, 160, int(90 * (1 - gold))))
            img.alpha_composite(ln.filter(ImageFilter.GaussianBlur(3)))
    # the helmet's rim, lagging a little behind the head's turns
    ox = oy = 0
    if st:
        ox = int(max(-60, min(60, st.get('yawRate', 0) * 1.6)))
        oy = int(max(-60, min(60, st.get('pitchRate', 0) * 1.6)))
    hm = _helmet()
    img.alpha_composite(hm.crop((80 - ox, 80 - oy, 80 - ox + W, 80 - oy + H)))
    # the readouts, up top under the logo
    if st:
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
                draw(img, '◀◀', g['ImageFont'].truetype(g['F_STAR'], 40), 470, _fade(t, 1.7, 3.0, 0.15), fill=(255, 255, 255))
        za = _fade(t, 10.4, 23.4, 0.5)
        if za > 0 and st.get('zeta', 0) > 0.3:
            z = st['zeta']
            txt = f'приплив ≈ {z:.0f} м' if z < 1000 else f'приплив ≈ {z / 1000:.1f} км'.replace('.', ',')
            g['draw_block'](img, txt, _font(g, 'Commissioner.ttf', 34, 600), 470, za, fill=(150, 205, 255))
