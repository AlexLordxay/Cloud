# "How long would it take": the Moon, Mars, the Sun and Proxima Centauri, by car (100 km/h), by plane (900 km/h) and by the
# fastest probe heading out of the Solar System, Voyager 1 (~61 000 km/h). Segments as in cam.js (SEG).
# Moon 384 400 km; Mars at its closest ~56 million km; Sun 149.6 million km; Proxima 4.24 light years ≈ 40 trillion km.
DURATION = 47.5
GOALS = [   # start, end, name, distance, (car, plane, probe)
    (4.0, 13.0, 'Місяць', '384 тисячі км', ('5 місяців', '18 днів', '6 годин')),
    (13.0, 22.0, 'Марс', '56 мільйонів км — у найближчий момент', ('64 роки', '7 років', '38 днів')),
    (22.0, 31.0, 'Сонце', '150 мільйонів км', ('171 рік', '19 років', '3,5 місяця')),
    (31.0, 41.0, 'Проксима Центавра', 'найближча зоря · 40 трильйонів км', ('46 мільйонів років', '5 мільйонів років', '75 000 років')),
]
ROWS = ('Машиною', 'Літаком', 'Зондом «Вояджер»')
CAP_FADE = 0.35
CAPTIONS = [(-1.0, 3.7, 'hook', 'Скільки їхати\nмашиною до\nнайближчої зорі?')]
NAMES, SUBS = [], []
for a, b, name, dist, times in GOALS:
    NAMES.append((a + 0.4, b - 0.4, name))
    SUBS.append((a + 0.6, b - 0.4, dist))
    for i, (row, val) in enumerate(zip(ROWS, times)):
        CAPTIONS.append((a + 1.4 + 1.3 * i, b - 0.4, 1330 + 95 * i, f'{row} — {val}'))
CAPTIONS.append((41.4, 44.6, 'cap', 'А світло долітає\nза 4 роки 3 місяці.\nНа чому полетів би ти?'))
CUTS = [4.0, 13.0, 22.0, 31.0]
FADE_IN = 0
HOOK_SIZE = 80
END_CARD = 44.8
END_TITLE = 'Більше космосу —\nна сайті'
CREDITS = [(31.0, 44.6, 'Проксима — уявлення художника за даними науки')]
