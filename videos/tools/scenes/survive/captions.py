# "How long would you last on each planet?" — the Nebozvid astronaut on Mercury, Venus, Mars, Jupiter and
# Neptune (see cam.js). Facts: Mercury's day side reaches ~430 °C and the Sun there looks up to 3 times bigger;
# Venus: ~465 °C at the ground and 92 times the Earth's air pressure (like ~900 m under the sea); Mars: about −60 °C on
# average and air under 1 % of ours — a suit copes; Jupiter has no surface, gravity 2.5 times ours, and pressure and
# heat grow as you sink; Neptune: about −200 °C at the cloud tops and winds up to ~2 000 km/h, the fastest known.
# Each planet has a stopwatch that speeds up and stops at a rough real-world estimate (nobody has tested it): Mercury
# ~10 min before the suit overheats (sunlight ~7 times ours plus the hot ground, more than a suit can shed); Venus ~3 s
# (a soft suit is crushed at once); Mars ~8 h (a spacesuit's oxygen); Jupiter ~1 h of falling (the Galileo probe
# lasted 58 min in 1995); Neptune ~5 min (−200 °C air in a 2 000 km/h wind takes the heat away fast). The stop
# moments match cam.js (Mercury's flash at +5.4 s, and so on).
DURATION = 42.0
CAP_FADE = 0.35
RED, GREEN = (235, 90, 70), (120, 220, 130)
CAPTIONS = [
    (-1.0, 3.0, 'hook', 'Скільки ти\nпротримаєшся\nна кожній планеті?'),
    (3.2, 5.5, 'cap', 'Сонце тут утричі більше'),
    (5.8, 7.7, 'cap', '≈10 хвилин —\nі скафандр перегрівся'),
    (8.6, 12.3, 'cap', 'Тиск — як на глибині\nмайже кілометр під водою'),
    (12.6, 15.2, 'cap', '3 секунди —\nі тиск роздавив скафандр'),
    (16.1, 20.0, 'cap', 'Холодно й повітря майже немає,\nале скафандр тримає'),
    (20.6, 22.8, 'cap', 'Вижив! Доки є кисень —\nблизько 8 годин'),
    (23.6, 28.8, 'cap', 'Поверхні немає. Зонд «Галілео»\nпротримався тут 58 хвилин'),
    (29.1, 30.2, 'cap', '≈1 година падіння —\nтиск і жар'),
    (31.1, 34.6, 'cap', 'Найшвидший вітер\nу Сонячній системі'),
    (34.9, 37.8, 'cap', '≈5 хвилин — замерз,\nі його знесло вітром'),
]
NAMES = [
    (3.2, 7.7, 'Меркурій'),
    (8.4, 15.2, 'Венера'),
    (15.9, 22.8, 'Марс'),
    (23.4, 30.2, 'Юпітер'),
    (30.9, 37.8, 'Нептун'),
]
SUBS = [
    (3.2, 7.7, '+430 °C'),
    (8.4, 15.2, '+465 °C · тиск ×92'),
    (15.9, 22.8, '−60 °C'),
    (23.4, 30.2, 'тяжіння ×2,5'),
    (30.9, 37.8, '−200 °C · вітер 2000 км/год'),
]
# (show from, show to, start, stop at, the time it stops on (s), colour once stopped)
TIMERS = [
    (0.1, 7.8, 0.0, 5.3, 600, RED),
    (8.2, 15.3, 8.0, 12.5, 3, RED),
    (15.7, 22.9, 15.5, 20.5, 8 * 3600, GREEN),
    (23.2, 30.3, 23.0, 29.0, 3600, RED),
    (30.7, 37.9, 30.5, 35.0, 300, RED),
]
CUTS = [8.0, 15.5, 23.0, 30.5, 38.0]
FADE_IN = 0
HOOK_SIZE = 76
END_CARD = 38.3
END_TITLE = 'Вижити можна\nлише на Марсі.\nПоки що'
CREDITS = [(0.2, 37.8, 'Час — приблизні оцінки')]
