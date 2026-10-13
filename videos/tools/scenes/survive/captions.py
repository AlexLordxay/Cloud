# "10 seconds on each planet: where would you survive?" — the Nebozvid astronaut on Mercury, Venus, Mars, Jupiter and
# Neptune (see cam.js). Facts: Mercury's day side reaches ~430 °C and the Sun there looks up to 3 times bigger;
# Venus: ~465 °C at the ground and 92 times the Earth's air pressure (like ~900 m under the sea); Mars: about −60 °C on
# average and air under 1 % of ours — a suit copes; Jupiter has no surface, gravity 2.5 times ours, and pressure and
# heat grow as you sink; Neptune: about −200 °C at the cloud tops and winds up to ~2 000 km/h, the fastest known.
# Each planet has a stopwatch (10 timer seconds over the ~7.5 s stretch) that stops when the astronaut is done for,
# with the verdict under it. The stop times match the moments in cam.js (Mercury's flash at +5.4 s, and so on).
DURATION = 42.0
CAP_FADE = 0.35
R = 10 / 7.5            # timer seconds per video second
RED, GREEN = (235, 90, 70), (120, 220, 130)
CAPTIONS = [
    (-1.0, 3.0, 'hook', '10 секунд\nна кожній планеті.\nДе ти виживеш?'),
    (3.2, 5.6, 'cap', 'Сонце тут утричі більше'),
    (5.9, 7.7, 'cap', 'Загинув на 7-й секунді:\nскафандр перегрівся'),
    (8.6, 12.3, 'cap', 'Тиск — як на глибині\nмайже кілометр під водою'),
    (12.6, 15.2, 'cap', 'Загинув на 6-й секунді:\nроздавив тиск'),
    (16.1, 20.0, 'cap', 'Холодно й повітря майже немає,\nале скафандр тримає'),
    (20.6, 22.8, 'cap', '10 секунд — ти вижив!'),
    (23.6, 28.8, 'cap', 'Поверхні немає. Ти падаєш\nу хмари, а знизу — тиск і жар'),
    (29.1, 30.2, 'cap', 'Загинув на 8-й секунді:\nтиск і жар'),
    (31.1, 34.6, 'cap', 'Найшвидший вітер\nу Сонячній системі'),
    (34.9, 37.8, 'cap', 'Загинув на 6-й секунді:\nзамерз, і його знесло'),
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
# (show from, show to, start, rate, stop at (timer s), colour once stopped)
TIMERS = [
    (0.1, 7.8, 0.0, R, 7, RED),
    (8.2, 15.3, 8.0, R, 6, RED),
    (15.7, 22.9, 15.5, 2.0, 10, GREEN),
    (23.2, 30.3, 23.0, R, 8, RED),
    (30.7, 37.9, 30.5, R, 6, RED),
]
CUTS = [8.0, 15.5, 23.0, 30.5, 38.0]
FADE_IN = 0
HOOK_SIZE = 76
END_CARD = 38.3
END_TITLE = 'Вижити можна\nлише на Марсі.\nПоки що'
CREDITS = []
