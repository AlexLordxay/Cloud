# «Ядерна зима: що каже наука» — captions over render.py's frames. Voice (voice.mp3) in 15 phrases with pauses for the
# pictures (scene.json). DRAW: the counters — warheads, weeks of spreading soot, the temperature, the harvest.
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]

DURATION = 68.5
CAPTIONS = [
    (-1.0, 4.05, 'hook', 'Що буде, якщо почнеться\nповномасштабна\nядерна війна?'),
    (4.25, 6.1, 'cap', 'Науковці це змоделювали'),
    (6.35, 10.9, 'cap', 'Сьогодні у світі —\nблизько 12 000 ядерних боєголовок'),
    (15.95, 18.25, 'cap', 'Найстрашніше — навіть не вибухи'),
    (18.45, 22.8, 'cap', 'Пожежі міст піднімуть у небо\n150 мільйонів тонн сажі'),
    (24.15, 28.6, 'cap', 'Сонце нагріє цей дим\nі підніме ще вище — у стратосферу'),
    (28.85, 31.75, 'cap', 'За кілька тижнів він огорне\nвсю Землю'),
    (34.15, 35.75, 'cap', 'Сонце потьмяніє'),
    (36.05, 39.95, 'cap', 'Середня температура планети\nвпаде більш ніж на 8 °C'),
    (40.25, 43.05, 'cap', 'Настане ядерна зима — на роки'),
    (44.95, 47.9, 'cap', 'Врожаї впадуть майже на 90 %'),
    (48.15, 51.55, 'cap', 'Від голоду можуть загинути\n5 мільярдів людей'),
    (53.95, 57.6, 'cap', 'Земля вціліє.\nА от цивілізація — навряд'),
    (58.95, 61.95, 'cap', 'Тому в ядерній війні\nне буде переможців'),
    (62.25, 64.85, 'cap', 'Перешли тому,\nкому це важливо знати'),
]
NAMES = []
SUBS = [(4.25, 6.1, 'Robock 2007 · Xia та ін., Nature Food 2022'), (18.45, 22.8, 'сценарій «150 Тг» — найбільша змодельована війна')]
CREDITS = [(0.0, 64.85, 'Візуалізація: Небозвід · Земля: NASA Blue Marble / Black Marble · модель: Robock 2007, Xia 2022')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 66
HOOK_Y = 470
SUBSCRIBE_AT = 32.0
SUBSCRIBE_Y = 1700
END_CARD = 65.0
END_TITLE = 'Наука про Землю\nі космос — на сайті'

def _sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)

def DRAW(img, t, g):
    big = g['f_tick']; small = g['f_end3']; SUN = g['SUN']
    def show(a, b, val, label, col=SUN):
        al = g['fade'](t, a, b, 0.35)
        if al > 0:
            g['draw_block'](img, val, big, 330, al, fill=col)
            g['draw_block'](img, label, small, 420, al, fill=(200, 208, 224))
    n = int(12200 * _sm((t - 6.5) / 3.6) / 100) * 100
    show(6.35, 10.9, f'{n:,}'.replace(',', ' '), 'ядерних боєголовок у світі')
    w = 4.0 * _sm((t - 28.6) / 5.4)
    if 28.85 < t < 34.0:
        k = max(1, min(4, int(w + 0.999)))
        show(28.85, 33.9, f'{k} {"тиждень" if k == 1 else "тижні"}', 'дим розходиться довкола Землі')
    temp = -8.0 * _sm((t - 36.2) / 3.4)
    show(36.05, 43.05, f'−{abs(temp):.1f} °C'.replace('.', ','), 'середня температура планети', col=(150, 200, 255))
    crop = 90 * _sm((t - 45.0) / 2.6)
    show(44.95, 47.9, f'−{int(crop)} %', 'урожаїв за 3–4 роки')
    show(48.15, 51.55, '5 млрд', 'людей під загрозою голоду', col=(255, 170, 140))
