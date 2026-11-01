# «Ти Стрілець?» — captions over the sky (frames.py). The voice runs from 0.2 s (its line about the black hole is left
# out: the fact says it, and facts aren't repeated); the fact «коли ти дивишся на своє сузір'я…» from 24.3 s, the call
# to comment from 38.4 s (a 2 s pause before it). DRAW: the date under the Sun, the horizon.
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
from PIL import Image, ImageDraw, ImageFilter
import timeline as T

DURATION = 45.2
CAPTIONS = [
    (-1.0, 1.3, 'hook', 'Ти Стрілець?'),
    (1.55, 5.45, 'cap', 'Твоє сузір’я дивиться\nпрямо в серце Галактики'),
    (5.8, 11.1, 'cap', 'Сонце проходить крізь нього\nз 18 грудня до 19 січня'),
    (11.47, 15.0, 'cap', 'Його найяскравіші зорі\nскладаються в «чайник»'),
    (15.0, 18.9, 'cap', 'А над носиком, як пара, —\nЧумацький Шлях'),
    (19.25, 23.9, 'cap', 'З України Стрільця видно\nнизько на півдні\nсерпневими вечорами'),
    (24.3, 27.3, 'cap', 'Коли ти дивишся\nна своє сузір’я…'),
    (27.45, 36.5, 'cap', '…ти дивишся в центр Галактики.\nТам, за 26 000 світлових років, —\nчорна діра в 4 мільйони Сонць'),
    (38.4, 41.9, 'cap', 'Напиши свій знак у коментарях —\nпокажу наступним'),
]
NAMES = [(1.55, 18.9, 'Стрілець'), (19.25, 23.9, 'Стрілець'), (24.3, 36.5, 'Центр Галактики'), (38.4, 41.9, 'Стрілець')]
SUBS = [(11.47, 18.9, 'астеризм «Чайник»'), (19.25, 23.9, 'серпень · 22:00 · південь'), (27.45, 36.5, 'Стрілець A* · 26 000 світлових років')]
CREDITS = [(0.0, 41.9, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 13.0
SUBSCRIBE_Y = 1700
END_CARD = 42.2
END_TITLE = 'Знайди свій знак\nна справжньому небі —\nна сайті'

W, H = 1080, 1920

def _horizon(img, t, g):
    a = g['ease'](g['fade'](t, 19.6, 24.0, 1.0))
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
    al = g['fade'](t, 5.8, 11.1, 0.35) * k
    if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470, al, fill=g['SUN'])
    _horizon(img, t, g)
