# «Знайомся: TRAPPIST-1e»: captions, names and the end card, timed to the author's voice (timeline.json). The pictures
# come from shots.py; compose.py lays these over them.
import json, os
_TL = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timeline.json')))
def P(i): return _TL['phrases'][i]['t0'], _TL['phrases'][i]['t1']
SHOT = {x['name']: (x['t0'], x['t1']) for x in _TL['shots']}
DURATION = _TL['dur']
CAPTIONS = [
    (-1.0, P(0)[1] + 0.1, 'hook', 'Двійник\nЗемлі?'),
    (P(1)[0], P(1)[1], 'cap', 'І вона зовсім\nне схожа на Землю'),
    (P(2)[0], P(3)[1], 'cap', 'Знайомся: TRAPPIST-1e'),
    (P(5)[0], P(5)[1], 'cap', 'Вона за 40 світлових років\nвід нас'),
    (P(6)[0], P(6)[1], 'cap', 'Розміром майже як Земля'),
    (P(7)[0], P(7)[1], 'cap', 'і тепла отримує\nна третину менше, ніж ми'),
    (P(8)[0], P(8)[1], 'cap', 'Але її зоря — не Сонце,'),
    (P(9)[0], P(9)[1], 'cap', 'а тьмяний червоний карлик,\nледь більший за Юпітер'),
    (P(10)[0], P(10)[1], 'cap', 'Планета так близько до зорі,\nщо рік тут триває 6 днів'),
    (P(11)[0], P(11)[1], 'cap', 'Тож якщо тобі 30 —'),
    (P(12)[0], P(12)[1], 'cap', 'тут тобі було б\nмайже 1 800'),
    (P(13)[0], P(13)[1], 'cap', 'Найімовірніше, вона завжди\nповернута до зорі одним боком'),
    (P(14)[0], P(14)[1], 'cap', 'Там вічний день:'),
    (P(15)[0], P(15)[1], 'cap', 'зоря нерухомо висить у небі'),
    (P(16)[0], P(16)[1], 'cap', 'А з другого боку —'),
    (P(17)[0], P(17)[1], 'cap', 'вічна ніч'),
    (P(18)[0], P(18)[1], 'cap', 'Поруч ще шість планет —'),
    (P(19)[0], P(19)[1], 'cap', 'і всі вони поміщаються\nвсередині орбіти Меркурія'),
    (P(20)[0], P(20)[1], 'cap', 'Тому сусідні планети на небі\nбувають завбільшки як наш Місяць —'),
    (P(21)[0], P(21)[1], 'cap', 'і помітно пропливають повз'),
    (P(22)[0], P(22)[1], 'cap', 'Яка вона насправді,'),
    (P(23)[0], P(23)[1], 'cap', 'поки ніхто не знає'),
    (P(24)[0], P(24)[1], 'cap', 'Якщо там є повітря й вода,'),
    (P(25)[0], P(25)[1], 'cap', 'вчені припускають\nпланету-око:'),
    (P(26)[0], P(26)[1], 'cap', 'усе вкрите кригою,'),
    (P(27)[0], P(27)[1], 'cap', 'а під зорею —\nвідкритий океан'),
    (P(28)[0], P(28)[1], 'cap', 'І можливо, на його берегах\nє життя'),
    (P(29)[0], P(29)[1], 'cap', 'Тільки рослини під такою зорею,\nймовірно, були б не зелені,'),
    (P(30)[0], P(30)[1], 'cap', 'а майже чорні —'),
    (P(31)[0], P(31)[1], 'cap', 'щоб ловити якомога\nбільше світла'),
    (P(32)[0], P(32)[1], 'cap', 'Але поки це лише мрія'),
    (P(33)[0], P(33)[1], 'cap', 'Відповідь шукає телескоп\n«Джеймс Вебб» —'),
    (P(34)[0], P(34)[1], 'cap', 'просто зараз'),
    (P(35)[0], P(35)[1], 'cap', 'Надішли це тому,\nхто мріє про другу Землю'),
    (P(36)[0], P(36)[1], 'cap', 'І напиши, яку планету\nпоказати наступною'),
]
EARTH = (P(5)[0] - 0.21, P(5)[1] + 0.21)     # the flight away from the Earth (shots.py)
NAMES = [(P(2)[0], EARTH[0] - 0.05, 'TRAPPIST-1e'), (EARTH[0] + 0.1, EARTH[1] - 0.1, '40 світлових років'),
         (EARTH[1] + 0.1, P(7)[1], 'TRAPPIST-1e'), (P(10)[0], P(12)[1], '1 рік = 6 діб'), (P(25)[0], P(27)[1], 'планета-око')]
SUBS = [(EARTH[0] + 0.3, EARTH[1] - 0.1, 'стільки летить світло звідти до нас'), (EARTH[1] + 0.1, P(7)[1], '40 світлових років від нас'),
        (P(11)[0], P(12)[1], '30 земних років ≈ 1 800 тутешніх')]
_s = SHOT
CREDITS = [
    (0.0, EARTH[0] - 0.1, 'Художня візуалізація за даними NASA · поверхні ніхто не бачив'),
    (EARTH[0] + 0.1, EARTH[1] - 0.1, 'Земля: текстури NASA · художня візуалізація'),
    (EARTH[1] + 0.1, _s['star'][0] - 0.2, 'Художня візуалізація за даними NASA · поверхні ніхто не бачив'),
    (_s['star'][0] + 0.1, _s['year'][0] - 0.1, 'Розміри Сонця, TRAPPIST-1 і Юпітера — у масштабі'),
    (_s['year'][0] + 0.1, _s['lock'][0] - 0.1, 'Орбіти — у масштабі · планети збільшено'),
    (_s['lock'][0] + 0.1, _s['system'][0] - 0.1, 'Художня візуалізація'),
    (_s['system'][0] + 0.1, _s['sky'][0] - 0.1, 'Орбіти — у масштабі · планети збільшено'),
    (_s['sky'][0] + 0.1, _s['eye'][0] - 0.1, 'Розміри на небі — справжні · час пришвидшено'),
    (_s['eye'][0] + 0.1, _s['life'][0] - 0.1, 'Планета-око — гіпотеза · художня візуалізація'),
    (_s['life'][0] + 0.1, _s['dream'][0] - 0.1, 'Рослини — уява; темні рослини — гіпотеза (Kiang, NASA)'),
    (_s['dream'][0] + 0.1, P(36)[1] + 0.1, 'Художня візуалізація за даними NASA'),
]
CUTS = [(EARTH[0], 0.12), (EARTH[1], 0.12)] + [(_s[k][0], 0.22) for k in ('star', 'year', 'lock', 'system', 'sky', 'eye')]
FADE_IN = 0
HOOK_SIZE = 84
HOOK_Y = 420
SUBSCRIBE_AT = _s['eye'][0] + 1.0
END_CARD = P(36)[1] + 0.45
END_TITLE = 'Куди полетимо\nнаступного разу?'
NEXT_TEASE = 'Не проґав наступну планету'

# ---- the comment that asked for this planet: a card over the picture while the camera swings round ----
# comment.png (the author's screenshot, cropped to the comment) if it is there; otherwise a card drawn from the text
CARD = (P(1)[1] + 0.05, EARTH[0] - 0.15)
_card = {}
def _card_img(g):
    if 'im' in _card: return _card['im']
    from PIL import Image, ImageDraw, ImageFilter
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, 'comment.png')
    Wc = 880
    if os.path.exists(src):
        im = Image.open(src).convert('RGBA')
        im = im.resize((Wc, int(im.size[1] * Wc / im.size[0])), Image.LANCZOS)
    else:
        f1, f2 = g['font']('Commissioner.ttf', 34, 700), g['font']('Commissioner.ttf', 38, 500)
        text = 'Проксима Центавра b, або люба з планет\nнавколо зірки TRAPPIST-1'
        im = Image.new('RGBA', (Wc, 230), (28, 30, 36, 255)); d = ImageDraw.Draw(im)
        d.ellipse((30, 34, 104, 108), fill=(120, 150, 220, 255))
        d.text((67, 71), 'A', font=g['font']('Unbounded.ttf', 38, 600), anchor='mm', fill=(255, 255, 255, 255))
        d.text((128, 40), '@Andara', font=f1, fill=(200, 205, 215, 255))
        d.multiline_text((128, 90), text, font=f2, fill=(245, 245, 250, 255), spacing=10)
    # rounded corners
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), 30, fill=255)
    im.putalpha(Image.fromarray(__import__('numpy').minimum(__import__('numpy').asarray(im.getchannel('A')), __import__('numpy').asarray(m))))
    _card['im'] = im
    return im

def DRAW(img, t, g):
    a, b = CARD
    al = g['ease'](g['fade'](t, a, b, 0.45))
    if al <= 0: return
    from PIL import Image, ImageFilter
    im = _card_img(g)
    slide = (1 - g['ease'](min(1.0, (t - a) / 0.5))) * 60
    x = int((g['W'] - im.size[0]) / 2); y = int(560 - im.size[1] / 2 + slide)
    g['draw_block'](img, 'Ви просили — показуємо', g['f_end3'], y - 46, al, fill=(255, 214, 160))
    lay = im.copy()
    if al < 1: lay.putalpha(lay.getchannel('A').point(lambda v: int(v * al)))
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); shl = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    shl.putalpha(lay.getchannel('A').point(lambda v: int(v * 0.7))); sh.paste(shl, (x, y + 8))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    img.alpha_composite(lay, (x, y))
