# «Що буде, якщо впасти в чорну діру?» v2: captions timed to the author's voice (scene.json narration), names, the
# escape-speed counter and the friend's porthole with his clock (DRAW, called by compose.py for every frame).
import math
from PIL import Image, ImageDraw

DURATION = 86.5
CAPTIONS = [
    (-1.0, 2.35, 'hook', 'Якби ти впав\nу чорну діру…'),
    (2.45, 5.85, 'cap', 'то побачив би те, чого\nне бачив жоден живий'),
    (6.3, 9.6, 'cap', 'Це Стрілець A* — серце\nнашої Галактики'),
    (9.7, 16.1, 'cap', 'Важить як 4 мільйони Сонць,\nа вмістився б в орбіту Меркурія'),
    (16.6, 20.4, 'cap', 'У 2022 році його вперше\nсфотографували'),
    (21.3, 23.6, 'cap', 'Що таке горизонт подій?'),
    (23.7, 28.0, 'cap', 'Щоб злетіти із Землі,\nтреба 11 км за секунду'),
    (28.05, 34.1, 'cap', 'Біля чорної діри ця швидкість росте,\nа на горизонті дорівнює\nшвидкості світла'),
    (34.15, 37.2, 'cap', 'Тому звідти не вибирається\nнавіть світло'),
    (37.3, 41.6, 'cap', 'Це не стіна — це межа,\nз-за якої не повертаються'),
    (42.2, 49.4, 'cap', 'Друг здалеку бачить, як ти\nсповільнюєшся, червонієш —\nі застигаєш на краю'),
    (49.45, 50.5, 'cap', 'Назавжди'),
    (50.8, 52.6, 'cap', 'А ти просто падаєш далі'),
    (53.1, 59.2, 'cap', 'Біля краю світло ходить по колу:\nозирнувшись, ти міг би побачити\nвласну потилицю'),
    (59.6, 62.6, 'cap', 'Мала діра розтягла б тебе,\nяк спагеті'),
    (62.65, 67.0, 'cap', 'А ця така велика, що край\nти перетнеш непомітно'),
    (67.6, 70.9, 'cap', 'Небо позаду стискається\nв яскраве коло'),
    (72.6, 74.9, 'cap', 'До центру — менше хвилини'),
    (75.8, 78.5, 'cap', 'А що там — не знає ніхто'),
    (79.7, 84.0, 'cap', 'Про яку загадку космосу\nрозповісти далі?\nПиши в коментарях'),
]
NAMES = [(6.3, 12.5, 'Стрілець A*'), (16.6, 20.5, '2022'), (21.3, 23.6, 'Горизонт подій'),
         (59.6, 62.5, 'Мала чорна діра'), (62.7, 66.9, 'Стрілець A*')]
SUBS = [(6.3, 9.6, 'центр Чумацького Шляху'), (9.7, 12.5, '4,3 млн мас Сонця · 26 000 св. років від нас'),
        (12.8, 16.2, 'пунктир — орбіта Меркурія'), (16.6, 20.5, 'перше фото · телескоп «Горизонт подій»'),
        (59.6, 62.5, '~10 мас Сонця'), (62.7, 66.9, '4,3 млн мас Сонця')]
CREDITS = [(0.0, 79.0, 'Чорна діра — уявлення художника за законами фізики')]
CUTS = []
FADE_IN = 0
HOOK_SIZE = 84
SUBSCRIBE_AT = 53.4
END_CARD = 84.0
END_TITLE = 'Більше космосу —\nна сайті'

C = 299792.458
def r4(t):           # the lamp's distance from the hole in r_s (the same as in cam.js)
    u = min(1.0, max(0.0, (t - 21.6) / 12.6))
    return max(1.004, 1 + 12 * (1 - u) ** 1.6)

def _num(v):
    return f'{int(round(v)):,}'.replace(',', ' ')

def _fade(t, a, b, d=0.35):
    return max(0.0, min(1.0, (t - a) / d, (b - t) / d))

def DRAW(img, t, g):
    W, H = img.size
    block, f_tick, f_lab, SUN = g['draw_block'], g['f_tick'], g['f_end3'], g['SUN']
    # escape speed: the Earth's, then right here (c·sqrt(r_s / r)), until it is the speed of light
    al = _fade(t, 23.7, 27.95, 0.3)
    if al > 0:
        block(img, '11,2 км/с', f_tick, 330, al, fill=SUN)
        block(img, 'щоб полетіти із Землі', f_lab, 420, al, fill=(200, 208, 224))
    al = _fade(t, 28.1, 41.6, 0.3)
    if al > 0:
        r = r4(t)
        light = r <= 1.0045
        v = C if light else C / math.sqrt(r)
        block(img, _num(v) + ' км/с', f_tick, 330, al, fill=(255, 120, 80) if light else SUN)
        block(img, '= швидкість світла' if light else 'щоб вирватися звідси', f_lab, 420, al, fill=(255, 170, 140) if light else (200, 208, 224))
    # the friend's porthole and the astronaut's clock as the friend sees it: slower and slower, stopped
    al = _fade(t, 42.0, 50.6, 0.12)
    if al > 0:
        cx, cy, R = W // 2, int(H * 0.47), int(W * 0.47)
        m = Image.new('L', (W, H), 255)
        ImageDraw.Draw(m).ellipse((cx - R, cy - R, cx + R, cy + R), fill=0)
        dark = Image.new('RGBA', (W, H), (10, 12, 16, 0)); dark.putalpha(m.point(lambda v: int(v * 0.93 * al)))
        img.alpha_composite(dark)
        ring = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ring)
        for k, (w, c) in enumerate([(26, (70, 76, 86)), (8, (120, 128, 140)), (3, (170, 176, 186))]):
            d.ellipse((cx - R - w // 2, cy - R - w // 2, cx + R + w // 2, cy + R + w // 2), outline=c + (int(255 * al),), width=w)
        for i in range(16):
            a = i / 16 * 2 * math.pi; x, y = cx + (R + 9) * math.cos(a), cy + (R + 9) * math.sin(a)
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(150, 156, 166, int(255 * al)))
        img.alpha_composite(ring)
        block(img, 'так бачить друг здалеку', f_lab, cy - R - 70, al, fill=(200, 208, 224))
        k = (1 - math.exp(-(t - 42.0) / 2.3)) / (1 - math.exp(-8.6 / 2.3))
        sec = 7.0 + 5.5 * k
        red = k * k
        block(img, f'0:{sec:04.1f}'.replace('.', ','), f_tick, cy + R + 95, al, fill=(255, int(255 - 140 * red), int(255 - 190 * red)))
        block(img, 'його годинник', f_lab, cy + R + 180, al, fill=(200, 208, 224))
    # then his own clock, ticking as ever
    al = _fade(t, 50.65, 52.9, 0.2)
    if al > 0:
        sec = 12.5 + (t - 50.6)
        block(img, f'0:{sec:04.1f}'.replace('.', ','), f_tick, 330, al)
        block(img, 'твій годинник', f_lab, 420, al, fill=(200, 208, 224))
