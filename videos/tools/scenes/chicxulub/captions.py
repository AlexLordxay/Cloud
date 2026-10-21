# "Що сталося з Землею, коли вимерли динозаври": captions (the author's words, sentence by sentence, timed to where
# assemble.py puts each phrase), the epochs counted down in the finale, the small print, the end card.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble import placed, START, END_CARD, DURATION

# each phrase's caption(s): (seconds into the phrase where a sentence ends and the next caption takes over, ...), texts
TEXTS = [
    ((), ['66 мільйонів років тому\nодин удар змінив\nусе життя на Землі']),
    ((5.89,), ['Тоді Земля була іншою: тепла,\nмайже без льоду, Атлантика —\nвузька, Індія ще пливе до Азії',
               'А на суходолі панують\nдинозаври']),
    ((), ['А до неї летить темна брила\nзавширшки 10 кілометрів,\nнароджена десь за Юпітером, —\nу двадцять разів швидше за кулю']),
    ((), ['Вона така велика, що коли нижній\nкрай торкається моря, верхній ще\nтам, де літають літаки']),
    ((3.89,), ['Вибух — як мільярди атомних\nбомб, скинутих на Хіросіму',
               'Землю трясе сильніше, ніж\nза будь-якого землетрусу\nв історії людства']),
    ((), ['За лічені хвилини тут з’являється\nкратер завширшки 180 км —\nбільше, ніж від Києва до Житомира']),
    ((3.77,), ['Море повертається хвилею\nзаввишки півтора кілометра',
               'Цунамі обійде весь світовий океан,\nі воно в 30 000 разів потужніше\nза цунамі 2004 року']),
    ((5.05,), ['А вже в першу годину викинуті\nв космос уламки падають назад\nпо всій планеті',
               'Небо розжарюється,\nі на суходолі спалахують пожежі']),
    ((9.55,), ['Сажа, сірка й пил затягують небо.\nРік чи два до землі майже\nне доходить світло, рослини\nгинуть, настає довга зима',
               'Зникають три чверті всіх видів —\nі всі динозаври, крім птахів']),
    ((5.11, 12.6), ['Та життя повертається.\nУціліли дрібні звірі —\nнаші далекі предки',
                    'Материки повільно роз’їхалися,\nа нащадки тих звірів\nза 66 мільйонів років стали нами',
                    'Без цього астероїда нас,\nмабуть, не було б']),
    ((), ['А хто, на твою думку,\nправив би Землею, якби\nастероїд пролетів повз?']),
]
CAPTIONS = []
_ph = placed()
for i, ((f, a, b, at, end), (splits, texts)) in enumerate(zip(_ph, TEXTS)):
    nxt = _ph[i + 1][3] if i + 1 < len(_ph) else DURATION
    edges = [at] + [at + s for s in splits] + [end]
    for k, text in enumerate(texts):
        t0 = edges[k] - 0.15 if k == 0 else edges[k] + 0.25
        t1 = min(edges[k + 1] + 0.3, nxt - 0.2) if k == len(texts) - 1 else edges[k + 1] + 0.15
        CAPTIONS.append((-1.0 if i == 0 else t0, t1, 'hook' if i == 0 else 'cap', text))
HOOK_SIZE = 56

# the finale: the epochs counting down as the continents drift (finale.frame: 14 steps of 5 million years from 5.5 to
# 15 s into the shot, smoothstep-eased; the 13th lands on today's map, the 14th on the Blue Marble)
F = START['finale']
TICKER = [(F + 5.5, F + 15.0, 65, -5, F + 5.3, F + 13.1)]
TICKER_EASE = lambda x: (lambda x: x * x * (3 - 2 * x))(min(1.0, max(0.0, x)))
SUBS = [(F + 5.3, F + 13.1, 'мільйонів років тому')]
NAMES = [(F + 13.3, F + 18.5, 'Сьогодні')]

CREDITS = [(START['kpg_earth'] + 0.4, START['approach'] - 0.2, 'Земля 66 млн років тому: PALEOMAP, Scotese & Wright 2018 (CC BY 4.0)'),
           (START['approach'] + 0.6, START['entry'] - 0.2, 'Ілюстрація: відстані не в масштабі'),
           (F + 5.3, F + 13.1, 'Карти: PALEOMAP, Scotese & Wright 2018 (CC BY 4.0)'),
           (F + 13.3, F + 18.5, 'Земля сьогодні: NASA Blue Marble')]
CUTS = []                  # the shots dissolve into each other (assemble.py)
FADE_IN = 0                # the Earth is there from the first frame (the one the feed shows)
END_TITLE = 'Більше космосу —\nна сайті'
