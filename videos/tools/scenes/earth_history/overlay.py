# Overlays for «Історія Землі»: the 24-hour clock of Earth's history and the stamp captions (Oswald Bold, OFL).
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
FONTS = os.path.join(TOOLS, 'fonts')
T_EARTH = 4.54e9

def font(size, wght=700, name='Oswald.ttf'):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    try: f.set_variation_by_axes([wght])
    except Exception: pass
    return f

def hours_of(years_ago):            # years ago -> clock hours (0..24)
    return 24.0 * (1.0 - years_ago / T_EARTH)

def clock_text(h):
    s = int(round(h * 3600)); s = min(s, 24 * 3600)
    return '%02d:%02d:%02d' % (s // 3600, (s // 60) % 60, s % 60) if h > 23.99 else '%02d:%02d' % (s // 3600, (s // 60) % 60)

def ago_text(years_ago):
    if years_ago >= 1e9: return ('%.2f' % (years_ago / 1e9)).rstrip('0').rstrip('.').replace('.', ',') + ' млрд років тому'
    if years_ago >= 1e6: return '%d млн років тому' % round(years_ago / 1e6)
    if years_ago >= 1e3: return '%d тис. років тому' % round(years_ago / 1e3)
    return 'сьогодні'

def draw_clock(im, h, years_ago, cx, cy, R, alpha=1.0, glow=0.0):
    """ring clock: 24 ticks, a progress arc, the time and 'years ago' under it. im: RGBA PIL image (overlay layer)"""
    S = 3; big = Image.new('RGBA', (int(R * 2.9 * S), int(R * 3.9 * S)), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    ox, oy = big.width / 2, R * 1.3 * S; r = R * S
    a = int(255 * alpha)
    d.ellipse([ox - r * 1.18, oy - r * 1.18, ox + r * 1.18, oy + r * 1.18], fill=(5, 8, 16, int(150 * alpha)))
    d.ellipse([ox - r, oy - r, ox + r, oy + r], outline=(255, 255, 255, int(70 * alpha)), width=int(2 * S))
    ang = -90 + 360 * (h / 24.0)
    d.arc([ox - r, oy - r, ox + r, oy + r], -90, ang, fill=(255, 196, 92, a), width=int(5 * S))
    for i in range(24):
        t = math.radians(-90 + i * 15); l = 0.16 if i % 6 == 0 else 0.08
        d.line([ox + math.cos(t) * r * (1 - l), oy + math.sin(t) * r * (1 - l), ox + math.cos(t) * r * 0.97, oy + math.sin(t) * r * 0.97],
               fill=(255, 255, 255, int((200 if i % 6 == 0 else 110) * alpha)), width=int(2 * S))
    t = math.radians(ang)
    d.line([ox, oy, ox + math.cos(t) * r * 0.82, oy + math.sin(t) * r * 0.82], fill=(255, 220, 150, a), width=int(4 * S))
    d.ellipse([ox - 5 * S, oy - 5 * S, ox + 5 * S, oy + 5 * S], fill=(255, 220, 150, a))
    ft = font(int(R * 0.62 * S), 600); txt = clock_text(h)
    w = d.textlength(txt, font=ft); d.text((ox - w / 2, oy + r * 1.28), txt, font=ft, fill=(255, 255, 255, a))
    fs = font(int(R * 0.27 * S), 400); sub = ago_text(years_ago)
    w = d.textlength(sub, font=fs); d.text((ox - w / 2, oy + r * 2.02), sub, font=fs, fill=(220, 225, 235, int(220 * alpha)))
    small = big.resize((big.width // S, big.height // S), Image.LANCZOS)
    if glow > 0:
        g = small.filter(ImageFilter.GaussianBlur(R * 0.25)); g.putalpha(g.getchannel('A').point(lambda v: int(v * glow)))
        im.alpha_composite(g, (int(cx - small.width / 2), int(cy - R * 1.3)))
    im.alpha_composite(small, (int(cx - small.width / 2), int(cy - R * 1.3)))

def draw_stamp(im, text, x, y, size=64, k=1.0, angle=-4.0):
    """black plate, white condensed bold text, tilted; k: 0..1 appearance (scale 1.15 -> 1, alpha)"""
    if k <= 0: return
    ft = font(size, 700); pad = int(size * 0.32)
    tw = int(ImageDraw.Draw(im).textlength(text, font=ft)); th = int(size * 1.18)
    pl = Image.new('RGBA', (tw + pad * 2, th + pad), (0, 0, 0, 0)); d = ImageDraw.Draw(pl)
    d.rectangle([0, 0, pl.width, pl.height], fill=(8, 8, 8, 235))
    d.text((pad, pad * 0.35 - size * 0.12), text, font=ft, fill=(255, 255, 255, 255))
    s = 1.0 + 0.15 * (1 - min(1.0, k * 1.4))
    pl = pl.resize((int(pl.width * s), int(pl.height * s)), Image.LANCZOS).rotate(-angle, expand=True, resample=Image.BICUBIC)
    a = pl.getchannel('A').point(lambda v: int(v * min(1.0, k * 1.6))); pl.putalpha(a)
    im.alpha_composite(pl, (int(x - pl.width / 2), int(y - pl.height / 2)))
