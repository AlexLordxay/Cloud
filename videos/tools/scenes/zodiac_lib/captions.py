# «Ти Терези?» — captions over the sky (frames.py). The voice (scene.json; «Терези́» re-recorded 30.10 with the right stress): «Ти Терези́? … а річ»
# from 0.2 s, the Sun's dates from 6.8 s, Gliese 581 from 12.8 s, the fact «твоє сузір'я колись було клешнями Скорпіона» from 20.75 s (the voice's
# own claws line is cut: the fact says it), the call to comment from 33.1 s (a 2 s pause before it). DRAW: the date under the Sun and the scales' sign.
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import timeline as T

DURATION = 39.6
CAPTIONS = [
    (-1.0, 1.3, 'hook', 'Ти Терези?'),
    (1.65, 6.35, 'cap', 'Це єдиний знак зодіаку,\nщо не жива істота, а річ'),
    (6.85, 12.4, 'cap', 'Сонце проходить крізь нього\nз 30 жовтня до 23 листопада'),
    (12.85, 20.35, 'cap', 'У Терезах є зоря Глізе 581 —\nодна з перших, біля якої знайшли\nпланети, схожі на Землю'),
    (20.8, 24.6, 'cap', 'Твоє сузір’я колись було\nклешнями Скорпіона'),
    (25.05, 31.1, 'cap', 'Його найяскравіші зорі досі звуться\n«південна клешня»\nі «північна клешня»'),
    (33.15, 36.65, 'cap', 'Напиши свій знак у коментарях —\nпокажу наступним'),
]
NAMES = [(1.65, 12.4, 'Терези'), (12.85, 20.35, 'Глізе 581'), (20.8, 31.1, 'Терези'), (33.15, 36.65, 'Терези')]
SUBS = [(6.85, 12.4, 'за гороскопом — з 23 вересня по 22 жовтня'), (12.85, 20.35, 'червоний карлик · ~20 світлових років'),
        (25.05, 31.1, 'арабською — Зубенельгенубі та Зубенешамалі')]
CREDITS = [(0.0, 36.65, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 13.2
SUBSCRIBE_Y = 1700
END_CARD = 36.9
END_TITLE = 'Знайди свій знак\nна справжньому небі —\nна сайті'

W, H = 1080, 1920

def DRAW(img, t, g):
    lam, k = T.sun(t)
    al = g['fade'](t, 6.8, 12.3, 0.35) * k
    if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470, al, fill=g['SUN'])
