# «Ти Скорпіон?» — captions over the sky (frames.py). The voice runs from 0.2 s; the fact «on your birthday» from 39.3 s,
# the call to comment from 49.75 s (a 2 s pause before it). DRAW: the date under the Sun, Antares in place of the Sun among the planets' orbits, the horizon.
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
from PIL import Image, ImageDraw, ImageFilter
import timeline as T

DURATION = 56.6
CAPTIONS = [
    (-1.0, 1.3, 'hook', 'Ти Скорпіон?'),
    (1.55, 4.45, 'cap', 'Твоє сузір’я — найкоротше\nв зодіаку'),
    (4.6, 10.3, 'cap', 'Сонце проходить крізь нього\nлише за тиждень'),
    (10.7, 13.1, 'cap', 'А в його серці — Антарес'),
    (13.2, 18.3, 'cap', 'Назва означає «суперник Марса» —\nвін такий самий червоний'),
    (18.6, 20.8, 'cap', 'Це червоний надгігант'),
    (20.9, 28.0, 'cap', 'На місці Сонця він поглинув би\nМеркурій, Венеру, Землю\nі навіть Марс'),
    (28.5, 34.5, 'cap', 'Антарес старіє і колись вибухне\nяк наднова — її буде видно\nнавіть удень'),
    (34.8, 38.9, 'cap', 'З України Скорпіона видно\nнизько на півдні літніми вечорами'),
    (39.4, 43.0, 'cap', 'У твій день народження\nСкорпіона не видно —\nвін ховається за Сонцем'),
    (44.6, 47.9, 'cap', 'Свій знак ти найкраще побачиш\nчерез пів року — у червні'),
    (49.8, 53.3, 'cap', 'Напиши свій знак у коментарях —\nпокажу наступним'),
]
NAMES = [(1.55, 10.3, 'Скорпіон'), (10.7, 18.3, 'Антарес'),
         (28.5, 34.5, 'Антарес'), (34.8, 38.9, 'Скорпіон'), (39.4, 43.0, 'Твій день народження'), (44.6, 53.3, 'Скорпіон')]
SUBS = [(10.7, 18.3, 'α Скорпіона · ~550 світлових років від нас'),         (28.5, 34.5, 'колись — наднова'), (34.8, 38.9, 'липень · 22:00 · південь'), (39.4, 43.0, 'Сонце поруч зі Скорпіоном'),
        (44.6, 53.3, 'червень · 23:00 · південь')]
CREDITS = [(0.0, 53.3, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 14.5
SUBSCRIBE_Y = 1700
END_CARD = 53.5
END_TITLE = 'Знайди свій знак\nна справжньому небі —\nна сайті'

W, H = 1080, 1920
AU = 135                                  # px per astronomical unit in the size comparison
ORBITS = [('Меркурій', 0.39, -40), ('Венера', 0.72, 5), ('Земля', 1.0, 45), ('Марс', 1.52, 80)]   # name, AU, label angle

def _orbits(img, t, g):
    a = g['ease'](g['fade'](t, 18.5, 28.2, 0.6))
    if a <= 0: return
    cx, cy = W // 2, 900
    dim = Image.new('RGBA', (W, H), (2, 3, 8, int(200 * a))); img.alpha_composite(dim)
    # the dimming covers the logo and the name: draw them again on top
    g['draw_logo'](img, 64, 170, 0.92 * a, t)
    g['draw_block'](img, 'Антарес на місці Сонця', g['font']('Unbounded.ttf', 52, 600), 330, a, fill=g['SUN'])
    g['draw_block'](img, 'радіус ~700 Сонць', g['f_end3'], 404, a, fill=(200, 208, 224))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    f = g['font']('Commissioner.ttf', 30, 600)
    # the red giant grows over the orbits as the voice names them (Mercury ~23.6 s … Mars ~27 s)
    R = 3.3 * AU * T.ease((t - 20.9) / 6.4)
    if R > 2:
        glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dg = ImageDraw.Draw(glow)
        dg.ellipse((cx - R * 1.08, cy - R * 1.08, cx + R * 1.08, cy + R * 1.08), fill=(255, 80, 30, int(110 * a)))
        glow = glow.filter(ImageFilter.GaussianBlur(18)); img.alpha_composite(glow)
        d2 = ImageDraw.Draw(img)
        for j in range(12):                       # limb darkening: rings from orange-red at the edge to light in the middle
            r = R * (1 - j / 12)
            c = (int(200 + 55 * j / 11), int(50 + 120 * j / 11), int(25 + 60 * j / 11), int(235 * a))
            d2.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    for name, au, ang in ORBITS:
        r = au * AU; inside = R > r
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, int((90 if inside else 170) * a)), width=2)
        x, y = cx + r * math.cos(math.radians(ang)), cy - r * math.sin(math.radians(ang))
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 255, 255, int(230 * a)))
        d.text((x + 12, y), name, font=f, anchor='lm', fill=(255, 255, 255, int((150 if inside else 240) * a)))
    d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(255, 230, 150, int(255 * a)))
    d.text((cx, cy + 34), 'Сонце', font=f, anchor='mm', fill=(255, 230, 150, int(200 * a)))
    img.alpha_composite(lay)

def _horizon(img, t, g):
    a = g['ease'](max(g['fade'](t, 35.4, 39.6, 1.0), g['fade'](t, 45.4, 99, 1.0)))
    if a <= 0: return
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    pts = [(0, 1440)] + [(x, 1440 - 26 * math.sin(x / 170) - 14 * math.sin(x / 61 + 1)) for x in range(0, W + 1, 20)] + [(W, H), (0, H)]
    d.polygon(pts, fill=(4, 6, 10, int(255 * a)))
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).rectangle((0, 1380, W, 1470), fill=(70, 60, 90, int(90 * a)))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30))); img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 1500), 'ПІВДЕНЬ', font=g['font']('Commissioner.ttf', 28, 700), anchor='mm', fill=(200, 208, 224, int(170 * a)))

def DRAW(img, t, g):
    lam, k = T.sun(t)
    al = g['fade'](t, 4.6, 10.3, 0.35) * k
    if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470, al, fill=g['SUN'])
    _orbits(img, t, g)
    _horizon(img, t, g)
