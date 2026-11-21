"""Шпалери для донатерів: кадри сцени videos/tools/scenes/wallpapers → planetarium/dyakuyu/wp/.

    cd videos/tools && FAST=1 node rec.js wallpapers stills 0.5,1.5,2.5,3.5,4.5,5.5,6.5
    python3 planetarium/tools/wallpapers.py

Кожна шпалера 1290×2796 (iPhone Pro Max; на інших телефонах обрізається по краях) з тихим підписом «Небозвід» унизу,
плюс мініатюра 430×932 для сторінки.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(ROOT, 'videos/tools/work')
OUT = os.path.join(ROOT, 'planetarium/dyakuyu/wp')
FONT = os.path.join(ROOT, 'videos/tools/fonts/CormorantItalic.ttf')
LIST = [  # (файл у work, slug, назва)
    ('wallpapers/still_0.5.jpg', 'saturn', 'Сатурн'),
    ('wallpapers/still_6.5.jpg', 'saturn-pole', 'Шестикутник Сатурна'),
    ('wallpapers/still_1.5.jpg', 'jupiter', 'Юпітер'),
    ('wallpapers/still_2.5.jpg', 'earth', 'Нічна Земля'),
    ('wallpapers/still_3.5.jpg', 'mars', 'Марс'),
    ('wallpapers/still_5.5.jpg', 'moon', 'Місяць'),
    ('wallpapers/still_4.5.jpg', 'neptune', 'Нептун'),
]

def sign(im):
    W, H = im.size
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONT, 64)
    t = 'Небозвід'
    w = d.textlength(t, font=f)
    d.text(((W - w) / 2, H - 190), t, font=f, fill=(233, 237, 246, 120))
    return Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')

os.makedirs(OUT, exist_ok=True)
for i, (src, slug, name) in enumerate(LIST, 1):
    p = os.path.join(WORK, src)
    if not os.path.exists(p):
        print('немає', src); continue
    im = Image.open(p).convert('RGB')
    if im.size != (1290, 2796):
        im = im.resize((1290, 2796), Image.LANCZOS)
    im = sign(im)
    base = f'{i:02d}-{slug}'
    im.save(os.path.join(OUT, base + '.jpg'), quality=90, optimize=True, progressive=True)
    im.resize((430, 932), Image.LANCZOS).save(os.path.join(OUT, base + '_s.jpg'), quality=82, optimize=True, progressive=True)
    print(base, name)
