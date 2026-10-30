# A character sheet of the stick figures (characters/stick.py): python3 characters/stick_sheet.py out.png
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import ImageFont
from characters.stick import Canvas, Figure, POSES, phone, toilet, floor, tiles, SUN, PINK, INK

F = ImageFont.truetype(os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Commissioner.ttf'), 26 * 2)
GUY = Figure(size=300)
GIRL = Figure(size=290, hair='ponytail', behind=1.7, accent=PINK, dress=PINK)
cv = Canvas(1800, 1000)
base = 420
for i, name in enumerate(['stand', 'wave', 'shrug', 'facepalm', 'shock', 'sad']):
    x = 150 + i * 300
    GUY.draw(cv, POSES[name], (x, base - 0), held=None)
    cv.text((x, base + 150), name, F, fill=(150, 150, 160))
# the toilet scene and the girl
toilet(cv, (300, 840), 0.75)
GUY.draw(cv, POSES['sit_phone'], (318, 828), held=lambda c, h, a: phone(c, h, a, 1.2))
cv.text((300, 975), 'sit_phone + toilet', F, fill=(150, 150, 160))
for i, name in enumerate(['stand', 'wave', 'twerk']):
    x = 750 + i * 330
    held = (lambda c, h, a: phone(c, h, a, 1.1)) if name == 'twerk' else None
    GIRL.draw(cv, POSES[name], (x, 840 if name != 'twerk' else 860), held=held)
    cv.text((x, 975), 'girl · ' + name, F, fill=(150, 150, 160))
cv.image().save(sys.argv[1])
