# «Ти Близнята?» — captions over the sky (frames.py). The voice runs from 0.2 s; the fact «а Сонце — у Тельці» from 15.45 s, «найкращий зорепад року» from
# 42.15 s (in place of the voice's own Geminids line); the call to comment from 55.7 s (a 2 s pause before it). DRAW: the date under the Sun, the two insets
# (Castor's six stars, Pollux's planet).
import math, os, sys
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), os.path.dirname(os.path.abspath(__file__))]
from PIL import Image, ImageDraw, ImageFilter
import timeline as T

DURATION = 62.3
CAPTIONS = [
    (-1.0, 1.15, 'hook', 'Ти Близнята?'),
    (1.6, 4.25, 'cap', 'У твоєму сузір’ї відкрили\nдві планети'),
    (4.55, 7.45, 'cap', 'Уран — у 1781 році'),
    (7.7, 10.25, 'cap', 'Плутон — у 1930-му'),
    (10.7, 15.05, 'cap', 'Сонце проходить крізь Близнят\nз 21 червня до 20 липня'),
    (15.5, 22.9, 'cap', 'Якщо ти Близнята за гороскопом —\nу твій день народження Сонце\nстояло не в Близнятах, а в Тельці'),
    (23.1, 27.6, 'cap', 'З 21 травня до 20 червня\nвоно щороку там'),
    (28.05, 32.15, 'cap', 'Їхні голови — дві яскраві зорі:\nКастор і Поллукс'),
    (32.4, 37.5, 'cap', 'Але Кастор — не одна зоря,\nа шість, що кружляють\nодна навколо одної'),
    (37.8, 41.6, 'cap', 'А навколо Поллукса обертається\nпланета, більша за Юпітер'),
    (42.1, 49.4, 'cap', 'Щороку в середині грудня з твого\nсузір\u2019я — найкращий зорепад року'),
    (49.5, 51.8, 'cap', 'понад 100 метеорів за годину'),
    (52.0, 54.2, 'cap', 'Встигни загадати бажання'),
    (55.8, 59.0, 'cap', 'Напиши свій знак у коментарях —\nпокажу наступним'),
]
NAMES = [(1.6, 15.05, 'Близнята'), (15.5, 27.6, 'Телець'), (28.05, 32.15, 'Кастор і Поллукс'), (32.4, 37.5, 'Кастор'), (37.8, 41.6, 'Поллукс'),
         (42.1, 54.2, 'Гемініди'), (55.8, 59.0, 'Близнята')]
SUBS = [(15.5, 27.6, 'а за гороскопом — Близнята'), (32.4, 37.5, '6 зір · 3 пари'), (37.8, 41.6, 'планета Поллукс b'), (42.1, 54.2, 'пік — 13–14 грудня')]
CREDITS = [(0.0, 59.0, 'Фото неба: ESO/S. Brunier (CC BY 4.0) · межі сузір’їв — МАС')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 30.0
SUBSCRIBE_Y = 1700
END_CARD = 59.2
END_TITLE = 'Знайди свій знак\nна справжньому небі —\nна сайті'

W, H = 1080, 1920
CX, CY, R = W // 2, 900, 300

def _window(img, a):
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).ellipse((CX - R, CY - R, CX + R, CY + R), fill=int(225 * a))
    img.paste(Image.new('RGBA', (W, H), (3, 5, 12, 255)), (0, 0), m.filter(ImageFilter.GaussianBlur(3)))
    ImageDraw.Draw(img).ellipse((CX - R, CY - R, CX + R, CY + R), outline=(150, 200, 255, int(140 * a)), width=2)

def _star(img, x, y, r, col, a):
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.ellipse((x - r * 3, y - r * 3, x + r * 3, y + r * 3), fill=col + (int(70 * a),))
    g = g.filter(ImageFilter.GaussianBlur(r)); img.alpha_composite(g)
    ImageDraw.Draw(img).ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(255 * a)))

def _castor(img, t, g):
    a = g['ease'](g['fade'](t, 32.4, 37.5, 0.5))
    if a <= 0: return
    _window(img, a)
    f = g['font']('Commissioner.ttf', 30, 600); d = ImageDraw.Draw(img)
    # A and B circle each other slowly, C (two red dwarfs) far out; every pair spins fast
    ab = t * 0.5
    mx, my = CX - 10, CY - 40
    pairs = [(mx + 110 * math.cos(ab), my + 60 * math.sin(ab), 40, (190, 215, 255), 'A', 16),
             (mx - 110 * math.cos(ab), my - 60 * math.sin(ab), 34, (200, 220, 255), 'B', 14),
             (CX + 60, CY + 190, 26, (255, 140, 90), 'C', 10)]
    for x, y, sep, col, name, r in pairs:
        s = t * 3.2 + len(name)
        for sgn in (1, -1):
            _star(img, x + sgn * sep * math.cos(s), y + sgn * sep * 0.45 * math.sin(s), r if sgn > 0 else r * 0.8, col, a)
        d.text((x, y - 58), name, font=f, anchor='mm', fill=(200, 220, 255, int(220 * a)))

def _pollux(img, t, g):
    a = g['ease'](g['fade'](t, 37.8, 41.6, 0.5))
    if a <= 0: return
    _window(img, a)
    ang = (t - 37.8) * 1.3
    px, py = CX + 220 * math.cos(ang), CY + 70 * math.sin(ang)
    front = math.sin(ang) > 0
    d = ImageDraw.Draw(img)
    d.ellipse((CX - 220, CY - 70, CX + 220, CY + 70), outline=(255, 255, 255, int(70 * a)), width=2)
    def planet():
        dd = ImageDraw.Draw(img)
        dd.ellipse((px - 16, py - 16, px + 16, py + 16), fill=(200, 160, 120, int(255 * a)))
        dd.text((px, py - 34), 'планета', font=g['font']('Commissioner.ttf', 26, 600), anchor='mm', fill=(230, 220, 200, int(220 * a)))
    if not front: planet()
    _star(img, CX, CY, 46, (255, 170, 80), a)
    ImageDraw.Draw(img).ellipse((CX - 46, CY - 46, CX + 46, CY + 46), fill=(255, 196, 120, int(255 * a)))
    if front: planet()

def DRAW(img, t, g):
    lam, k = T.sun(t)
    al = max(g['fade'](t, 10.7, 15.05, 0.35), g['fade'](t, 16.0, 27.4, 0.35)) * k
    if al > 0: g['draw_block'](img, T.date_of(lam), g['font']('Unbounded.ttf', 64, 600), 470 if t < 15.3 else 510, al, fill=g['SUN'])
    _castor(img, t, g)
    _pollux(img, t, g)
