# «Як насправді рухаються планети» — captions over render.py's frames. Voice (voice_all.mp3 = voice.mp3 + hook_v2.mp3, the
# re-recorded «А ти уявляєш…?» at 0.15 s) in parts: «Насправді…» 3.0 s, to «ніж у нас» from 5.0 s, 19.8 s (to «всі планети»), 30.3 s (to the end); a pause before «І головне» and before «За рік». DRAW: the count of
# Suns in the row (shot B). COUNTER: the km flown since the video began (230 km/s round the Galaxy).
import os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
import warp

DURATION = 58.4
CAPTIONS = [
    (-1.0, 2.75, 'hook', 'А ти уявляєш\nСонячну систему\nтак?'),
    (3.0, 4.75, 'cap', 'Насправді все інакше'),
    (5.05, 8.75, 'cap', 'Між Сонцем і Меркурієм\nвмістилося б 40 Сонць'),
    (9.1, 11.4, 'cap', 'А до Нептуна — понад 3 000'),
    (11.95, 14.55, 'cap', 'У кіно Сонце над Меркурієм —\nна пів неба'),
    (15.0, 19.2, 'cap', 'Насправді воно лише до 3 разів\nбільше, ніж у нас'),
    (19.85, 21.8, 'cap', 'І головне: Сонце не стоїть\nна місці'),
    (22.05, 26.95, 'cap', 'Воно мчить навколо центру\nГалактики — понад 200 км/с'),
    (27.2, 29.15, 'cap', '…і несе з собою всі планети'),
    (30.4, 35.2, 'cap', 'За рік ми пролітаємо 7 млрд км —\nдалі, ніж до Плутона'),
    (35.55, 39.5, 'cap', 'Тож шлях Землі — не коло,\nа дуже розтягнута спіраль'),
    (39.9, 42.55, 'cap', 'Планети не тягнуться за Сонцем,\nяк хвіст комети'),
    (42.9, 44.45, 'cap', '…вони летять разом із ним'),
    (44.85, 48.85, 'cap', 'Поки ти дивився це відео,\nми пролетіли понад 10 000 км'),
    (49.35, 52.2, 'cap', 'Перешли тому, хто думає,\nщо сидить на місці'),
]
NAMES = [(22.05, 29.15, 'Чумацький Шлях'), (39.9, 42.55, 'Міф'), (42.9, 44.45, 'Насправді')]
SUBS = [(22.05, 29.15, 'один оберт — ~230 млн років'), (30.4, 39.5, 'масштаб стиснуто · розміри збільшено'),
        (39.9, 42.55, 'так часто показують у відео')]
COUNTER = {'per_s': 230, 'show': (44.85, 52.2), 'label': 'км пролетіли ми, поки ти дивився'}
CREDITS = [(0.0, 11.1, 'Тло: ESO/S. Brunier (CC BY 4.0) · текстури: Solar System Scope (CC BY 4.0)'),
           (11.3, 19.3, 'Рельєф Меркурія: NASA/JHUAPL/USGS, MESSENGER'),
           (19.6, 29.3, 'Ілюстрація: NASA/JPL-Caltech/R. Hurt'),
           (29.6, 52.2, 'Тло: ESO/S. Brunier (CC BY 4.0) · текстури: Solar System Scope (CC BY 4.0)')]
# all the times above are on the first recording's clock: onto the new one (warp.py)
_N = warp.new
CAPTIONS = [(_N(a), _N(b), k, x) for a, b, k, x in CAPTIONS]
# the spoken captions follow the new recording's phrases exactly (scene.json parts; «За рік…» + «далі…» share one caption)
import json as _json
_P = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scene.json')))['narration']['parts']
_SPAN = [(at, at + (b - a)) for a, b, at in _P]
_SPAN = _SPAN[:9] + [(_SPAN[9][0], _SPAN[10][1])] + _SPAN[11:]
CAPTIONS = [CAPTIONS[0]] + [(s0 - 0.05, s1 + 0.12, k, x) for (s0, s1), (_, _, k, x) in zip(_SPAN[1:], CAPTIONS[1:])]
NAMES = [(_N(a), _N(b), x) for a, b, x in NAMES]
SUBS = [(_N(a), _N(b), x) for a, b, x in SUBS]
CREDITS = [(_N(a), _N(b), x) for a, b, x in CREDITS]
COUNTER['show'] = tuple(_N(x) for x in COUNTER['show'])
CUTS = []
FADE_IN = 0
HOOK_SIZE = 76
HOOK_Y = 470
SUBSCRIBE_AT = 17.3
SUBSCRIBE_Y = 1700
END_CARD = 54.8
END_TITLE = 'Справжнє небо\nі Сонячна система —\nна сайті'

def _suns(t):
    """how many Suns are laid in the row (the same as render.py's shot B)"""
    def sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
    if t < 9.0: return 41.6 * sm((t - 5.0) / 3.3)
    return 41.6 + (3229 - 41.6) * sm((t - 9.1) / 1.9)

def DRAW(img, t, g):
    al = g['fade'](t, 4.95, warp.new(11.4), 0.35)
    if al > 0:
        n = int(_suns(warp.old(t)))
        g['draw_block'](img, f'{n:,}'.replace(',', ' '), g['f_tick'], 330, al, fill=g['SUN'])
        g['draw_block'](img, 'Сонць у ряд', g['f_end3'], 420, al, fill=(200, 208, 224))
