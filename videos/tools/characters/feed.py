# A short-video feed overlay in the familiar style (no real logos): the icon column on the right with counts under
# each icon, the author and caption at the bottom left, live-style comments rising above them, a views pill at the top
# and the progress line along the bottom edge. Drawn on a characters/stick.py Canvas (light theme: dark icons).
#
#   draw_feed(cv, t, dict(views=…, likes=…, comments=…, saves=…, shares=…), user='@…', caption='…',
#             comments=[(t0, name, text), …], liked=True, progress=t / dur)
import math, os
from PIL import Image, ImageDraw, ImageFont
from characters.stick import INK, SS

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(TOOLS, 'fonts', 'Commissioner.ttf')
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
RED = (254, 44, 85)
ICON = (34, 34, 40)
MUTED = (120, 124, 134)
AVATARS = [(255, 179, 71), (120, 200, 160), (130, 160, 250), (240, 130, 190), (170, 140, 230), (100, 190, 230)]
_F, _EMO = {}, {}


def font(size, wght=700):
    k = (size, wght)
    if k not in _F:
        f = ImageFont.truetype(FONT, size * SS)
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
        _F[k] = f
    return _F[k]


def emoji(ch, px):
    k = (ch, px)
    if k not in _EMO:
        f = ImageFont.truetype(EMOJI, 109)
        im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor='mm')
        im = im.crop(im.getbbox())
        _EMO[k] = im.resize((max(1, int(im.width * px * SS / im.height)), px * SS), Image.LANCZOS)
    return _EMO[k]


def fmt(n):
    if n >= 1e6: return f'{n / 1e6:.1f}M'.replace('.0M', 'M')
    if n >= 1e4: return f'{n / 1e3:.0f}K'
    if n >= 1e3: return f'{n / 1e3:.1f}K'.replace('.0K', 'K')
    return str(int(n))


def rich_text(cv, xy, s, f, fill=INK, epx=30, alpha=1.0):
    """Text left-aligned at xy (middle height) with emoji drawn as images; returns the width (px, final scale)."""
    x0 = x = xy[0] * SS
    y = xy[1] * SS
    for part in s.split(' '):
        if part and ord(part[0]) > 0x2500:
            for ch in part:
                if ord(ch) < 0x2000: continue
                im = emoji(ch, epx)
                cv.img.paste(im, (int(x), int(y - im.height / 2)), im)
                x += im.width + 3 * SS
        else:
            cv.d.text((x, y), part, font=f, fill=fill, anchor='lm')
            x += cv.d.textlength(part, font=f)
        x += cv.d.textlength(' ', font=f)
    return (x - x0) / SS


def _heart(cv, c, s, fill, outline=None):
    x, y = c
    r = s * 0.27
    pts = []
    for k in range(0, 361, 6):                                  # a heart curve
        a = math.radians(k)
        hx = 16 * math.sin(a) ** 3
        hy = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((x + hx * s / 34, y + hy * s / 34))
    cv.poly(pts, fill=fill)
    if outline:
        cv.line(pts + [pts[0]], s * 0.08, outline)


def _bubble(cv, c, s):
    x, y = c
    cv.ellipse((x - s * 0.5, y - s * 0.42, x + s * 0.5, y + s * 0.38), fill=ICON)
    cv.poly([(x - s * 0.32, y + s * 0.2), (x - s * 0.05, y + s * 0.3), (x - s * 0.42, y + s * 0.52)], fill=ICON)
    for dx in (-0.22, 0, 0.22):
        cv.circle((x + dx * s, y - s * 0.02), s * 0.055, col=(255, 255, 255))


def _bookmark(cv, c, s):
    x, y = c
    cv.poly([(x - s * 0.34, y - s * 0.45), (x + s * 0.34, y - s * 0.45), (x + s * 0.34, y + s * 0.48), (x, y + s * 0.2),
             (x - s * 0.34, y + s * 0.48)], fill=ICON)


def _share(cv, c, s):
    x, y = c
    cv.poly([(x + s * 0.48, y - s * 0.05), (x + s * 0.05, y - s * 0.45), (x + s * 0.05, y - s * 0.22),
             (x - s * 0.25, y - s * 0.18), (x - s * 0.48, y + s * 0.15), (x - s * 0.45, y + s * 0.42),
             (x - s * 0.25, y + s * 0.15), (x + s * 0.05, y + s * 0.1), (x + s * 0.05, y + s * 0.35)], fill=ICON)


def _eye(cv, c, s, col=ICON):
    x, y = c
    cv.ellipse((x - s * 0.6, y - s * 0.36, x + s * 0.6, y + s * 0.36), col=col, w=s * 0.12)
    cv.circle((x, y), s * 0.18, col=col)


def draw_feed(cv, t, stats, user='@user', caption='', comments=(), liked=True, progress=0.0, avatar=0):
    W, H = cv.w, cv.h
    # the views pill, top left
    cv.rrect((36, 70, 36 + 300, 70 + 76), 38, fill=(255, 255, 255), col=(226, 229, 236), w=3)
    _eye(cv, (88, 108), 50)
    cv.d.text((130 * SS, 108 * SS), fmt(stats.get('views', 0)), font=font(44, 800), fill=INK, anchor='lm')
    # the right column: avatar with "+", heart, comments, bookmark, share — counts under each
    x = W - 92
    y = H * 0.40
    cv.circle((x, y), 52, fill=AVATARS[avatar % len(AVATARS)], col=(255, 255, 255))
    cv.circle((x, y), 52, w=5, col=(255, 255, 255))
    cv.circle((x, y + 52), 20, fill=RED, col=RED)
    cv.line([(x - 9, y + 52), (x + 9, y + 52)], 5, (255, 255, 255))
    cv.line([(x, y + 43), (x, y + 61)], 5, (255, 255, 255))
    y += 150
    beat = 1 + 0.10 * max(0.0, math.sin(t * 12))
    for key, draw in (('likes', None), ('comments', _bubble), ('saves', _bookmark), ('shares', _share)):
        if key == 'likes':
            _heart(cv, (x, y), 84 * (beat if liked else 1), RED if liked else ICON)
        else:
            draw(cv, (x, y), 78)
        cv.d.text((x * SS, (y + 66) * SS), fmt(stats.get(key, 0)), font=font(30, 700), fill=INK, anchor='mm')
        y += 165
    # the author and caption, bottom left
    by = H - 150
    cv.d.text((40 * SS, by * SS), user, font=font(40, 800), fill=INK, anchor='lm')
    rich_text(cv, (40, by + 54), caption, font(32, 500), fill=(60, 62, 70), epx=30)
    # live-style comments rising above the author: avatar, name, text; the newest at the bottom
    shown = [c for c in comments if t >= c[0]]
    for j, (t0, name, text) in enumerate(reversed(shown[-3:])):
        age = t - t0
        pop = min(1.0, age / 0.2)
        cy = by - 110 - j * 96 + (1 - pop) * 36
        col = AVATARS[sum(map(ord, name)) % len(AVATARS)]
        cv.rrect((30, cy - 40, 30 + 600, cy + 40), 40, fill=(255, 255, 255) if j else (255, 243, 246), col=(230, 232, 238), w=2)
        cv.circle((76, cy), 26, fill=col, col=col)
        cv.d.text((76 * SS, cy * SS), name[1].upper(), font=font(26, 800), fill=(255, 255, 255), anchor='mm')
        cv.d.text((116 * SS, (cy - 16) * SS), name, font=font(22, 700), fill=MUTED, anchor='lm')
        rich_text(cv, (116, cy + 13), text, font(28, 600), epx=26)
    # the progress line along the bottom
    cv.rrect((0, H - 8, W, H), 0, fill=(225, 228, 236))
    cv.rrect((0, H - 8, W * min(1.0, progress), H), 0, fill=INK)
