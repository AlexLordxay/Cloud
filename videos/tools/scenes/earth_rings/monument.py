# The Motherland Monument (Батьківщина-Мати, Kyiv) as a silhouette mask for a billboard: 102 m to the sword's tip — the
# figure (62 m) on its pedestal building; the sword (16 m) raised in the right hand, the shield (13 × 8 m, the trident
# since 2023) in the left. Drawn in metres (x −22…22, y 0…104) -> work/earth_rings/monument.png (alpha, 440 × 1040)
import os
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); WK = os.path.join(HERE, '..', '..', 'work', 'earth_rings')
S = 40                                   # px per metre while drawing (then ÷4)
W, H = 44 * S, 104 * S
im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
P = lambda pts: [((x + 22) * S, (104 - y) * S) for x, y in pts]
# the pedestal: a stepped round building, a plinth and a drum
d.polygon(P([(-19, 0), (19, 0), (19, 6), (15, 8), (15, 22), (12, 24), (12, 34), (8.5, 36), (8.5, 40), (-8.5, 40), (-8.5, 36), (-12, 34), (-12, 24), (-15, 22), (-15, 8), (-19, 6)]), 255)
# the figure: a long gown widening to the feet, the waist, the shoulders
d.polygon(P([(-7.5, 40), (7.5, 40), (5.5, 52), (4.0, 62), (3.6, 68), (4.6, 73), (3.4, 76), (1.6, 77), (1.4, 79.5), (-1.4, 79.5), (-1.6, 77), (-3.4, 76), (-4.6, 73), (-3.6, 68), (-4.0, 62), (-5.5, 52)]), 255)
# the head
d.ellipse([((-1.7 + 22) * S, (104 - 83.6) * S), ((1.7 + 22) * S, (104 - 78.8) * S)], 255)
# the right arm raised (to her right = our left? she faces the Dnipro, east; seen from the north-east she holds the sword
# on the right of the picture): the arm up and the sword straight up
d.polygon(P([(3.2, 75.5), (4.6, 74.5), (6.4, 82.5), (6.8, 88.0), (5.6, 88.4), (4.6, 83.0)]), 255)
d.polygon(P([(5.9, 87.6), (6.7, 87.6), (6.6, 102.0), (6.25, 104.0), (5.95, 102.0)]), 255)         # the sword
d.polygon(P([(4.9, 87.4), (7.7, 87.4), (7.7, 88.2), (4.9, 88.2)]), 255)                           # its cross-guard
# the left arm out and up, the shield
d.polygon(P([(-3.2, 75.5), (-4.6, 74.5), (-9.0, 78.5), (-10.0, 80.5), (-9.0, 81.5), (-7.6, 80.0)]), 255)
d.ellipse([((-14.5 + 22) * S, (104 - 86.0) * S), ((-7.0 + 22) * S, (104 - 73.5) * S)], 255)
im = im.filter(ImageFilter.GaussianBlur(S * 0.15)).resize((W // 4, H // 4), Image.LANCZOS)
im.save(os.path.join(WK, 'monument.png')); print('ok', im.size)
