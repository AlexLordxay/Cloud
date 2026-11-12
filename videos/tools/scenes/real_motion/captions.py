# «Як насправді рухаються планети» — captions over render.py's frames. Voice (voice.mp3) in three parts: 0.3 s (to «ніж у
# нас»), 19.8 s (to «всі планети»), 30.3 s (to the end); a pause before «І головне» and before «За рік». DRAW: the count of
# Suns in the row (shot B). COUNTER: the km flown since the video began (230 km/s round the Galaxy).
import os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]

DURATION = 56.0
CAPTIONS = [
    (-1.0, 2.45, 'hook', 'Ти уявляєш\nСонячну систему\nтак?'),
    (2.85, 4.5, 'cap', 'Насправді все інакше'),
    (4.8, 8.5, 'cap', 'Між Сонцем і Меркурієм\nвмістилося б 40 Сонць'),
    (8.85, 11.15, 'cap', 'А до Нептуна — понад 3 000'),
    (11.7, 14.3, 'cap', 'У кіно Сонце над Меркурієм —\nна пів неба'),
    (14.75, 18.95, 'cap', 'Насправді воно лише до 3 разів\nбільше, ніж у нас'),
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
CUTS = []
FADE_IN = 0
HOOK_SIZE = 76
HOOK_Y = 470
SUBSCRIBE_AT = 17.0
SUBSCRIBE_Y = 1700
END_CARD = 52.4
END_TITLE = 'Справжнє небо\nі Сонячна система —\nна сайті'

def _suns(t):
    """how many Suns are laid in the row (the same as render.py's shot B)"""
    def sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
    if t < 9.0: return 41.6 * sm((t - 5.0) / 3.3)
    return 41.6 + (3229 - 41.6) * sm((t - 9.1) / 1.9)

def DRAW(img, t, g):
    al = g['fade'](t, 5.0, 11.15, 0.35)
    if al > 0:
        n = int(_suns(t))
        g['draw_block'](img, f'{n:,}'.replace(',', ' '), g['f_tick'], 330, al, fill=g['SUN'])
        g['draw_block'](img, 'Сонць у ряд', g['f_end3'], 420, al, fill=(200, 208, 224))
