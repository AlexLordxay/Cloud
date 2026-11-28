# «У Землі колись могли бути кільця» — captions and drawings over the frames (frames.py, rendered at 1080 × 1920),
# timed to the voice (scene.json parts: 0.15, 3.95, 6.7, 14.05, 17.45, 20.75, 27.3, 30.15, 37.0 s).
import json, math, os
from PIL import Image, ImageDraw, ImageFilter

DURATION = 44.5
HOOK_SIZE = 70
HOOK_Y = 1500
CAPTIONS = [
    (-1.0, 3.8, 'hook', 'У Землі колись\nмогли бути кільця —\nяк у Сатурна'),
    (3.95, 6.45, 'cap', 'Ось так вони виглядали б над Києвом'),
    (6.7, 13.85, 'cap', 'Повз Землю пролетів астероїд\nзавширшки 12 кілометрів —'),
    (14.05, 17.2, 'cap', 'і гравітація Землі\nрозірвала його на шматки'),
    (17.45, 20.5, 'cap', 'Уламки вишикувалися\nв кільце над екватором'),
    (20.75, 27.1, 'cap', 'Учені знайшли 21 кратер того часу —\nусі біля тодішнього екватора'),
    (27.3, 29.9, 'cap', 'саме туди падали уламки з кільця'),
    (30.15, 36.7, 'cap', 'Кільце могло сяяти десятки мільйонів років —\nі, можливо, охолодило клімат Землі'),
    (37.0, 40.1, 'cap', 'Хотів би бачити таке небо щовечора?'),
]
NAMES = []
SUBS = []
CREDITS = [(0.2, 6.4, 'Київ: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · художня візуалізація'),
           (6.6, 20.5, 'Земля 465 млн р. тому: PALEOMAP (Scotese & Wright 2018, CC BY 4.0)'),
           (20.7, 30.0, 'Гіпотеза: Tomkins, Martin, Cawood, EPSL, 2024 · позначки кратерів умовні'),
           (30.2, 36.6, 'Похолодання кінця ордовику (~445 млн р. тому) · художня візуалізація'),
           (36.8, 40.2, 'Київ: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · художня візуалізація')]
CUTS = []
FADE_IN = 0
SUBSCRIBE_AT = 24.5
END_CARD = 40.3
END_TITLE = 'Кільця Землі'
NEXT_TEASE = 'Не проґав наступне відео'

HERE = os.path.dirname(os.path.abspath(__file__))
_LP = os.path.join(HERE, '..', '..', 'work', 'earth_rings', 'labels.json')
LAB = json.load(open(_LP)) if os.path.exists(_LP) else {}
GOLD = (255, 210, 120)

def _fade(t, a, b, d=0.4):
    x = max(0.0, min(1.0, (t - a) / d, (b - t) / d)); return x * x * (3 - 2 * x)

def _text(img, xy, s, fnt, fill, anchor='mm', alpha=1.0):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).multiline_text((xy[0], xy[1] + 3), s, font=fnt, fill=(0, 0, 0, int(230 * alpha)), anchor=anchor, align='center', spacing=8)
    sh = sh.filter(ImageFilter.GaussianBlur(8)); img.alpha_composite(sh); img.alpha_composite(sh)
    d.multiline_text(xy, s, font=fnt, fill=fill + (int(255 * alpha),), anchor=anchor, align='center', spacing=8); img.alpha_composite(lay)

def DRAW(img, t, H_):
    W, H = img.size
    f_mid = H_['font']('Commissioner.ttf', 40, 600)
    f_big = H_['font']('Unbounded.ttf', 96, 600)
    f_sm = H_['font']('Commissioner.ttf', 32, 500)
    # when
    a = _fade(t, 6.8, 13.6)
    if a > 0:
        _text(img, (W / 2, 330), '466 млн років тому', f_big, GOLD, alpha=a)
        _text(img, (W / 2, 430), 'за гіпотезою вчених (2024)', f_sm, (225, 230, 240), alpha=a)
    # the Roche limit: why it came apart
    a = _fade(t, 14.3, 17.2)
    if a > 0:
        _text(img, (W / 2, 330), 'межа Роша', f_big, (255, 170, 120), alpha=a)
        _text(img, (W / 2, 430), 'ближче до Землі — і припливні сили рвуть тіло', f_sm, (225, 230, 240), alpha=a)
    # the craters
    a = _fade(t, 21.0, 27.0)
    if a > 0:
        n = min(21, max(0, int((t - 21.0) / 0.13) + 1))
        _text(img, (W / 2, 330), f'{n} кратер' + ('' if n % 10 == 1 and n != 11 else ('и' if 2 <= n % 10 <= 4 and not 12 <= n <= 14 else 'ів')), f_big, GOLD, alpha=a)
        _text(img, (W / 2, 430), 'усі — в смузі ±30° від тодішнього екватора', f_sm, (225, 230, 240), alpha=a)
    # the cooling
    a = _fade(t, 31.6, 36.6)
    if a > 0:
        _text(img, (W / 2, 330), 'льодовиковий період', f_mid, (190, 225, 255), alpha=a)
        _text(img, (W / 2, 390), 'наприкінці ордовику, ~445 млн років тому', f_sm, (225, 230, 240), alpha=a)
