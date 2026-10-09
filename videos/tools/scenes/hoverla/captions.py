# "What if over Hoverla instead of the Moon…": worlds over the peak at their true sizes on the sky, then the Sun, then
# the Moon again. The timing (START, STEP) must match cam.js.
START, STEP = 5.5, 5.0
WORLDS = [   # name, fact — in the order of cam.js
    ('Марс', 'Удвічі\nбільший за Місяць'),
    ('Венера', 'У 3,5 раза.\nЯскрава, як ліхтар'),
    ('Земля', 'У 3,7 раза.\nТакою її бачать з Місяця'),
    ('Нептун', 'У 14 разів.\nВітри — до 2000 км/год'),
    ('Сатурн', 'Його кільця —\nяк 80 Місяців у ряд'),
    ('Юпітер', 'У 40 разів більший за Місяць —\nяк долоня на витягнутій руці'),
]
SUN_A, SUN_B = START + STEP * len(WORLDS), START + STEP * len(WORLDS) + 7.5   # 35.5 – 43.0
CAP_FADE = 0.6

CAPTIONS = [
    (-1.0, 5.0, 'hook', 'Що, якби\nнад Говерлою\nзамість Місяця\nбуло щось інше?'),
]
NAMES = []
for i, (name, fact) in enumerate(WORLDS):
    a = START + STEP * i
    NAMES.append((a + 0.4, a + STEP - 0.3, name))
    CAPTIONS.append((a + 0.8, a + STEP - 0.4, 'cap', fact))
NAMES.append((SUN_A + 1.2, SUN_B - 0.8, 'Сонце'))
CAPTIONS.append((SUN_A + 1.8, SUN_B - 0.8, 'cap', 'У 400 разів більше за Місяць.\nЗакрило б усе небо'))
CAPTIONS.append((SUN_B + 0.8, SUN_B + 3.8, 'cap', 'І знову наш Місяць.\nМаленький, зате свій'))
CUTS = []
FADE_IN = 0
HOOK_SIZE = 80
END_CARD = SUN_B + 4.0
DURATION = 50.0
END_TITLE = 'Добре, що в нас\nсаме Місяць'
CREDITS = [
    (0.0, END_CARD, 'Фото: Говерла з гори Туркул, автор lord-xay'),
]
