# «Ти Терези?» — captions over the sky (frames.py). The voice (scene.json): «Ти Терези? … а річ» from 0.2 s, the Sun's dates from 6.4 s,
# Gliese 581 from 12.2 s, the fact «твоє сузір'я колись було клешнями Скорпіона» from 20.15 s (the voice's own claws line is cut: the fact
# says it), the call to comment from 32.5 s (a 2 s pause before it). DRAW: the date under the Sun and the scales' sign.
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import timeline as T

DURATION = 39.0
CAPTIONS = [
    (-1.0, 1.3, 'hook', 'Ти Терези?'),
    (1.6, 6.05, 'cap', 'Це єдиний знак зодіаку,\nщо не жива істота, а річ'),
    (6.45, 11.75, 'cap', 'Сонце проходить крізь нього\nз 30 жовтня до 23 листопада'),
    (12.25, 19.75, 'cap', 'У Терезах є зоря Глізе 581 —\nодна з перших, біля якої знайшли\nпланети, схожі на Землю'),
    (20.2, 24.0, 'cap', 'Твоє сузір’я колись було\nклешнями Скорпіона'),
    (24.45, 30.5, 'cap', 'Його найяскравіші зорі досі звуться\n«південна клешня»\nі «північна клешня»'),
    (32.55, 35.95, 'cap', 'Напиши свій знак у коментарях —\nпокажу наступним'),
]
NAMES = [(1.6, 11.75, 'Терези'), (12.25, 19.75, 'Глізе 581'), (20.2, 30.5, 'Терези'), (32.55, 35.95, 'Терези')]
SUBS = [(6.45, 11.75, 'за гороскопом — з 23 вересня по 22 жовтня'), (12.25, 19.75, 'червоний карлик · ~20 світлових років'),
        (24.45, 30.5, 'арабською — Зубенельгенубі та Зубенешамалі')]
CREDITS = [(0.0, 35.95, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 12.6
SUBSCRIBE_Y = 1700
END_CARD = 36.3
END_TITLE = 'Знайди свій знак\nна справжньому небі —\nна сайті'

W, H = 1080, 1920

def DRAW(img, t, g):
    lam, k = T.sun(t)
    al = g['fade'](t, 6.4, 11.7, 0.35) * k
    if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470, al, fill=g['SUN'])
