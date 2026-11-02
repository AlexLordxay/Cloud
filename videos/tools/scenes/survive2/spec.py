# «Скільки ти протримаєшся…» v2 — what the titles say and when (seconds into each shot of timeline.json); post.py draws
# them, sfx.py times its stopwatch ticks and stops by them. Estimates are rough (nobody has tried): a suit's oxygen
# ~8 h; Mercury's dayside ~430 °C — a suit can't shed that much heat for long (~10 min); Venus ~465 °C and 92 bar — a
# soft suit is crushed at once; Jupiter: no surface, the Galileo probe sent data for 58 min (1995); Titan −180 °C, 1.5 bar,
# no oxygen; Neptune ~−200 °C at the cloud tops, winds to ~2 000 km/h (~5 min); the Sun's surface ~5 500 °C.
RED, GREEN = (240, 80, 64), (110, 225, 130)

# world: (name, the conditions)
NAMES = {
    'venus_hook': ('ВЕНЕРА', '+465 °C · тиск ×92'),
    'moon': ('МІСЯЦЬ', '−170…+120 °C · вакуум'),
    'mercury': ('МЕРКУРІЙ', '+430 °C · Сонце втричі більше'),
    'venus': ('ВЕНЕРА', '+465 °C · тиск ×92'),
    'mars': ('МАРС', '−60 °C · повітря < 1 % земного'),
    'jupiter': ('ЮПІТЕР', 'поверхні немає · тяжіння ×2,5'),
    'titan': ('ТИТАН', '−180 °C · тиск ×1,5 · кисню немає'),
    'neptune': ('НЕПТУН', '−200 °C · вітер 2000 км/год'),
    'sun': ('СОНЦЕ', '+5500 °C'),
    'earth': ('ЗЕМЛЯ', ''),
}
# world: (start, stop, seconds it stops on, colour, the line under it)
TIMERS = {
    'venus_hook': (0.15, 3.0, 3, RED, ''),
    'moon': (0.4, 4.4, 8 * 3600, GREEN, 'доки є кисень'),
    'mercury': (0.4, 4.4, 600, RED, 'скафандр перегрівся'),
    'venus': (0.4, 3.6, 3, RED, 'тиск роздавив скафандр'),
    'mars': (0.4, 4.6, 8 * 3600, GREEN, 'тут можна жити'),
    'jupiter': (0.4, 7.3, 58 * 60, RED, 'стільки протримався зонд «Галілео»'),
    'titan': (0.4, 4.7, 8 * 3600, GREEN, 'і можна літати'),
    'neptune': (0.4, 4.74, 300, RED, 'замерз'),
    'sun': (0.2, 0.2, 0, RED, 'ні секунди'),
}
HOOK = (3.75, 'Скільки ти протримаєшся\nна кожній планеті?')
LOST = 7.6                                   # Jupiter: «зв'язок втрачено» from here to the end of the shot
EARTH_LINE = (3.6, 'усе життя')              # under ЗЕМЛЯ, green
QUESTION = (4.9, 'На якій планеті\nпротримався б ти?', 'пиши в коментарях')
CREDITS = {'moon': 'Рельєф Місяця — NASA LRO (LOLA, LROC) · Земля збільшена'}
NOTE = 'Час — приблизні оцінки'


def timer_value(world, lt):
    """The stopwatch at lt: from 0 at start, faster and faster, landing on the value at stop (then held)."""
    a, b, v, _, _ = TIMERS[world]
    if v == 0: return 0
    u = min(1.0, max(0.0, (lt - a) / max(1e-6, b - a)))
    import math
    p = 1.0 if v <= 10 else 1.0 + 0.9 * math.log10(v)
    return v * u ** p


def fmt(sec):
    sec = int(round(sec)); return '%d:%02d:%02d' % (sec // 3600, sec // 60 % 60, sec % 60)
