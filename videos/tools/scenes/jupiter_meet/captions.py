# "Знайомся: Юпітер": captions and the end card, on the author's voice (fit_voice.py sets the shots to the phrases).
# The end card ("Знайди Юпітер сам", Небозвід) is captions only — not voiced.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import starts, duration, FPS

_S = {name: (at / FPS, (at + n) / FPS) for name, at, n in starts()}
_TEXT = [
    ('hook', 'hook', 'Цей шторм\nбільший за Землю —\nі вирує вже майже\n200 років'),
    ('zoom', 'cap', 'Знайомся: Юпітер. Усередину влізе\nпонад тисяча Земель, а важить він\nу 2,5 раза більше, ніж усі інші\nпланети разом'),
    ('spin', 'cap', 'Доба тут коротша за 10 годин —\nвін крутиться так швидко,\nщо аж сплющився'),
    ('dive', 'cap', 'Твердої поверхні немає. У 1995-му\nзонд «Галілео» пірнув у ці хмари —\nі замовк за 58 хвилин:\nйого розчавив тиск'),
    ('moons', 'cap', 'Але найцікавіше — навколо.\nУ Юпітера майже сто супутників,\nі чотири з них — цілі світи'),
    ('ioapp', 'cap', 'Іо — найвулканічніше місце\nСонячної системи'),
    ('iobreath', 'cap', 'Юпітер так стискає її своїм тяжінням,\nщо земля тут щодня піднімається\nй опускається на 100 метрів.\nВід цього надра плавляться'),
    ('pele', 'cap', 'Зазирнімо під жовту димку. Це вулкан\nПеле: його фонтан сірки злітає\nна 300 кілометрів'),
    ('loki', 'cap', 'А лавове озеро Локі —\n200 км завширшки.\nЯк від Києва до Вінниці'),
    ('europa', 'cap', 'Сусідка Європа — крижана.\nПід кригою — океан, де води вдвічі\nбільше, ніж на всій Землі'),
    ('clipper', 'cap', 'Туди вже летить зонд Europa Clipper —\nшукати життя. Прибуде у 2030-му'),
    ('ganymede', 'cap', 'А Ганімед — найбільший супутник\nСонячної системи: більший\nза Меркурій, з полярними сяйвами'),
    ('dawn', 'cap', 'А сам Юпітер можна побачити вже\nзараз: перед світанком це найяскравіша\n«зоря» на південному сході'),
]
DURATION = round(duration(), 2)
# each caption on its phrase of the voice (scene.json: [from, to, at] in seconds, sped up by "tempo")
import json
_N = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scene.json')))['narration']
_P = [(at, at + (b - a) / _N.get('tempo', 1.0)) for a, b, at in _N['parts']]
CAPTIONS = []
for (shot, kind, text), (a, b) in zip(_TEXT, _P):
    CAPTIONS.append((-1.0 if shot == 'hook' else a - 0.12, b + 0.3, kind, text))
_o = _S['outro'][0]
CAPTIONS.append((_P[-1][0] - 0.12, _P[-1][1] + 0.3, 'cap', 'Який супутник Юпітера\nтобі найцікавіший?\nПиши в коментарях'))
END_CARD = _P[-1][1] + 0.5
CREDITS = [(0.2, _S['spin'][1], 'Юпітер: Cassini (NASA/JPL)'),
           (_o + 0.5, END_CARD - 0.2, 'Супутники на справжніх відстанях: так вони стоять 30.10.2026 о 5:00'),
           (_S['moons'][0] + 0.3, _S['ganymede'][1] - 0.3, 'Карти супутників: Galileo, Voyager (NASA/JPL, USGS)')]
CUTS = []
FADE_IN = 0                 # the storm is there from the first frame
HOOK_SIZE = 76
END_TITLE = 'Знайди Юпітер\nсам'
