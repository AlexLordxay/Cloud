# «Ти Водолій?» — captions over the sky (frames.py). Voice: hook + Neptune 0.2, the dates 11.8, the fact «ера Водолія»
# 17.3, the Helix 28.7, TRAPPIST-1 36.6, the call to comment 45.1 (without «покажу наступним» — no promises), end card 47.4.
# DRAW: the date under the Sun; the real Helix photo (ESO/VISTA) zooming in step with the sky camera; the ESO artist's
# impression of TRAPPIST-1 with a slow push-in. Both photos go under the logo, the names and the captions.
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
from PIL import Image, ImageDraw, ImageFilter
import timeline as T

HERE = os.path.dirname(os.path.abspath(__file__))
DURATION = 50.3
CAPTIONS = [
    (-1.0, 1.15, 'hook', 'Ти Водолій?'),
    (1.5, 7.05, 'cap', 'У твоєму сузір’ї відкрили\nНептун — у 1846 році'),
    (7.25, 9.75, 'cap', 'Спершу на папері — розрахунками'),
    (9.95, 11.5, 'cap', 'а потім у телескоп'),
    (11.8, 16.8, 'cap', 'Сонце проходить крізь Водолія\nз 16 лютого до 11 березня'),
    (17.3, 20.6, 'cap', 'Чув про «еру Водолія»?'),
    (20.8, 28.2, 'cap', 'Точка весняного рівнодення\nприйде у твоє сузір’я\nлише близько 2600 року'),
    (28.7, 32.65, 'cap', 'Туманність Равлик —\n«око Бога»'),
    (32.85, 36.1, 'cap', 'Так виглядає зоря,\nщо скинула свою оболонку'),
    (36.6, 39.8, 'cap', 'А ще у Водолії —\nсистема TRAPPIST-1'),
    (40.05, 44.55, 'cap', 'Сім планет розміром із Землю\nнавколо однієї маленької зорі'),
    (45.1, 47.2, 'cap', 'Напиши свій знак у коментарях'),
]
NAMES = [(1.5, 16.8, 'Водолій'), (17.3, 28.2, 'Ера Водолія'), (28.7, 36.1, 'Туманність Равлик'), (36.6, 44.55, 'TRAPPIST-1'),
         (45.1, 47.2, 'Водолій')]
SUBS = [(1.5, 11.5, 'Ле Вер’є розрахував · Галле знайшов'), (20.8, 28.2, 'зараз вона в Рибах'),
        (28.7, 36.1, 'NGC 7293 · ~650 світлових років'), (36.6, 44.55, '~40 світлових років від нас')]
CREDITS = [(0.0, 30.4, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС'),
           (30.6, 36.6, 'Фото: ESO/VISTA/J. Emerson · Cambridge Astronomical Survey Unit (CC BY 4.0)'),
           (37.0, 39.9, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС'),
           (40.1, 45.4, 'Художня ілюстрація: ESO/N. Bartmann/spaceengine.org (CC BY 4.0)'),
           (45.6, 47.2, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 18.0
SUBSCRIBE_Y = 1700
END_CARD = 47.4
END_TITLE = 'Усі 13 знаків\nна справжньому небі —\nу профілі'

W, H = 1080, 1920
_cache = {}

def _rgba(name, feather):
    """The picture with its edges feathered to transparent (fraction `feather` of each side)."""
    if name not in _cache:
        im = Image.open(os.path.join(HERE, 'assets', name)).convert('RGB')
        w, h = im.size
        if feather:
            m = Image.new('L', (w, h), 0); f = int(min(w, h) * feather)
            ImageDraw.Draw(m).rounded_rectangle((f, f, w - f, h - f), radius=f, fill=255)
            m = m.filter(ImageFilter.GaussianBlur(f / 2.2))
        else:
            m = Image.new('L', (w, h), 255)
        im = im.convert('RGBA'); im.putalpha(m)
        _cache[name] = im
    return _cache[name]

def _helix(img, t, g):
    a = g['ease'](min(1.0, max(0.0, (t - 30.0) / 1.4))) * (1 - g['ease'](min(1.0, max(0.0, (t - 36.1) / 1.0))))
    if a <= 0: return False
    _, s, _ = T.camera(t)
    side = T.HELIX_FOV * s * 1.5                           # the photo's side in px — the same angular size as the sky
    if side < 40: return False
    ph = _rgba('helix_eso1205a.jpg', 0.10)
    # crop what's on screen before scaling (the photo can be far bigger than the frame)
    k = ph.size[0] / side
    x0, y0 = W / 2 - side / 2, H / 2 - side / 2
    cx0, cy0 = max(0.0, -x0) * k, max(0.0, -y0) * k
    cx1, cy1 = min(side, W - x0) * k, min(side, H - y0) * k
    if cx1 <= cx0 or cy1 <= cy0: return False
    part = ph.crop((int(cx0), int(cy0), int(math.ceil(cx1)), int(math.ceil(cy1))))
    dw, dh = int(round((cx1 - cx0) / k)), int(round((cy1 - cy0) / k))
    part = part.resize((max(1, dw), max(1, dh)), Image.LANCZOS)
    al = part.getchannel('A').point(lambda v: int(v * a)); part.putalpha(al)
    img.alpha_composite(part, (int(round(max(0.0, x0))), int(round(max(0.0, y0)))))
    return True

def _trappist(img, t, g):
    a = g['ease'](min(1.0, max(0.0, (t - 40.0) / 1.0))) * (1 - g['ease'](min(1.0, max(0.0, (t - 44.7) / 0.9))))
    if a <= 0: return False
    ph = _rgba('trappist_eso1706a.jpg', 0)
    pw, phh = ph.size
    z = 1.0 + 0.10 * g['ease'](min(1.0, max(0.0, (t - 40.0) / 5.6)))     # a slow push-in towards the star
    ch = phh / z; cw = ch * W / H
    sx, sy = 0.39 * pw, 0.42 * phh                                          # the star in the picture
    left = min(max(sx - cw / 2, 0), pw - cw); top = min(max(sy - ch * 0.42, 0), phh - ch)
    part = ph.crop((int(left), int(top), int(left + cw), int(top + ch))).resize((W, H), Image.LANCZOS)
    part.putalpha(int(255 * a))
    img.alpha_composite(part)
    return True

def DRAW(img, t, g):
    lam, k = T.sun(t)
    al = g['fade'](t, 11.8, 16.8, 0.35) * k
    if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470, al, fill=g['SUN'])
    if _helix(img, t, g) | _trappist(img, t, g):
        # the photos cover what compose.py drew before DRAW: the logo and the name lines go back on top
        g['draw_logo'](img, 64, 170, 0.92, t)
        for a, b, text in NAMES:
            v = g['ease'](g['fade'](t, a, b, 0.35))
            if v > 0: g['draw_block'](img, text, g['f_name'], 330, v, fill=g['SUN'])
        for a, b, text in SUBS:
            v = g['ease'](g['fade'](t, a, b, 0.35))
            if v > 0: g['draw_block'](img, text, g['f_end3'], 412, v, fill=(200, 208, 224))
