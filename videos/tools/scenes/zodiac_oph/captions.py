# «Ти Змієносець?» — captions over the sky (frames.py). The main voice from 0.2 s up to Barnard's star, the fact
# («світло від зорі Барнарда…») from 42.0 s, «з України» from 52.0 s, the call to comment from 56.2 s.
# DRAW: the date under the Sun, the horizon. TICKER: the years while Barnard's star crawls.
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
from PIL import Image, ImageDraw, ImageFilter
import timeline as T

DURATION = 63.2
CAPTIONS = [
    (-1.0, 1.6, 'hook', 'Ти Змієносець?'),
    (1.8, 4.1, 'cap', 'Народився\nз 29 листопада по 17 грудня?'),
    (4.4, 6.1, 'cap', 'Тоді ти не Стрілець…'),
    (6.2, 7.9, 'cap', '…ти — Змієносець'),
    (8.0, 13.1, 'cap', 'Своє сузір’я ти бачиш щодня —\nна кожній машині швидкої'),
    (13.4, 18.5, 'cap', 'Давні греки бачили в ньому\nАсклепія — лікаря зі змією'),
    (18.7, 22.2, 'cap', 'Палиця зі змією\nй досі — символ медицини'),
    (22.5, 26.9, 'cap', 'А Змія — єдине сузір’я,\nрозрізане навпіл'),
    (27.2, 31.3, 'cap', 'Голова — з одного боку,\nхвіст — з іншого'),
    (31.7, 35.7, 'cap', 'Тут же — зоря Барнарда,\nодна з найближчих до нас'),
    (35.9, 41.3, 'cap', 'Вона мчить так швидко,\nщо за 200 років зсувається\nна ширину Місяця'),
    (42.0, 46.6, 'cap', 'Світло від неї летить\nдо нас лише 6 років'),
    (46.9, 51.4, 'cap', 'Якщо тобі більше шести —\nти старший за світло,\nяке бачиш'),
    (52.0, 55.8, 'cap', 'З України Змієносця видно\nна півдні літніми вечорами'),
    (56.2, 59.6, 'cap', 'Напиши свій знак у коментарях —\nпокажу наступним'),
]
NAMES = [(1.8, 7.9, 'Змієносець'), (8.0, 13.1, 'Зірка життя'), (13.4, 22.2, 'Змієносець'), (22.5, 31.3, 'Змія'),
         (31.7, 35.7, 'Зоря Барнарда'), (42.0, 51.4, 'Зоря Барнарда'), (52.0, 55.8, 'Змієносець'), (56.2, 59.6, 'Змієносець')]
SUBS = [(8.0, 13.1, 'знак швидкої допомоги'), (13.4, 22.2, 'Асклепій тримає змію'), (22.5, 31.3, 'два шматки одного сузір’я'),
        (31.7, 35.7, '6 світлових років від нас'), (42.0, 51.4, '6 світлових років'), (52.0, 55.8, 'липень · 22:00 · південь')]
TICKER = [(38.4, 41.0, 2026, 2226, 37.6, 41.5)]
CREDITS = [(0.0, 59.6, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 24.0
SUBSCRIBE_Y = 1700
END_CARD = 60.2
END_TITLE = 'Знайди свій знак\nна справжньому небі —\nна сайті'

W, H = 1080, 1920

def _horizon(img, t, g):
    a = g['ease'](g['fade'](t, 52.2, 56.0, 1.0))
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
    al = g['fade'](t, 1.8, 7.9, 0.35) * k
    if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470, al, fill=g['SUN'])
    _horizon(img, t, g)
