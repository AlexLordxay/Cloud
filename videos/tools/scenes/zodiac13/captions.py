# «Є 13-й знак зодіаку» — captions over the sky (frames.py). Times: the voice runs from 0.3 s, the last phrase from 54.3 s
# (a 2 s pause before the question to the viewer).
import os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
import timeline as T

DURATION = 70.5
CAPTIONS = [
    (2.9, 8.5, 'cap', 'Протягом року Сонце проходить\nкрізь сузір’я — це і є зодіак'),
    (8.9, 13.9, 'cap', 'Але насправді воно перетинає\n13 сузір’їв'),
    (14.4, 21.8, 'cap', 'З 29 листопада до 17 грудня\nСонце — у Змієносці'),
    (22.1, 24.3, 'cap', 'А в Скорпіоні — лише тиждень'),
    (24.6, 26.4, 'cap', 'Чому його немає в гороскопах?'),
    (26.8, 35.1, 'cap', 'Понад 2500 років тому вавилоняни\nподілили небо на 12 рівних частин —\nтак було зручніше рахувати'),
    (35.3, 41.4, 'cap', 'Відтоді земна вісь повернулася —\nі знаки зсунулися\nмайже на цілий місяць'),
    (41.8, 47.0, 'cap', 'У 1604 році в Змієносці\nспалахнула наднова'),
    (47.2, 52.9, 'cap', 'останній вибух зорі в нашій Галактиці,\nякий бачили неозброєним оком'),
    (54.4, 58.2, 'cap', 'Народився з 29 листопада\nпо 17 грудня?'),
    (58.3, 61.6, 'cap', 'За справжнім небом\nти — Змієносець'),
    (61.7, 67.4, 'cap', 'Напиши свою дату в коментарях —\nскажу, де насправді було Сонце'),
]
NAMES = [(9.6, 21.8, 'Змієносець'), (22.1, 24.3, 'Скорпіон'), (27.0, 35.1, '12 знаків по 30°'),
         (35.3, 41.4, 'Прецесія земної осі'), (41.8, 52.9, '1604'), (54.4, 67.4, 'Змієносець')]
SUBS = [(9.6, 13.9, '13-те сузір’я на шляху Сонця'), (41.8, 52.9, 'наднова Кеплера'),
        (35.3, 41.4, 'повне коло — за 25 800 років')]
CREDITS = [(0.0, 67.4, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
SUBSCRIBE_AT = 30.0
SUBSCRIBE_Y = 1700
END_CARD = 67.6
END_TITLE = 'Знайди свій знак\nна справжньому небі —\nна сайті'

def DRAW(img, t, g):
    # the hook: a big «12 → 13» in the empty middle of the zodiac ring
    a = g['ease'](g['fade'](t, -1.0, 2.7, 0.35))
    if a > 0:
        f = g['font']('Unbounded.ttf', 200 if t > 1.0 else 170, 600)
        g['draw_block'](img, '13' if t > 1.0 else '12', f, 900, a, fill=(130, 220, 255) if t > 1.0 else (255, 255, 255))
        g['draw_block'](img, 'знаків зодіаку' if t > 1.0 else 'знаків зодіаку?', g['f_cap'], 1060, a)
    # the date under the Sun while it crosses Ophiuchus / Scorpius
    lam, k = T.sun(t)
    for a_, b_ in [(14.4, 24.3), (54.4, 61.6)]:
        al = g['fade'](t, a_, b_, 0.35) * k
        if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470, al, fill=g['SUN'])
