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

def _spaced(d, x, y, text, ft, fill, track):
    if track <= 1.5:
        d.text((x, y), text, font=ft, fill=fill); return x + d.textlength(text, font=ft)
    for ch in text:
        d.text((x, y), ch, font=ft, fill=fill); x += d.textlength(ch, font=ft) + track
    return x

def text_w(text, ft, track):
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    if track <= 1.5: return d.textlength(text, font=ft)
    return sum(d.textlength(ch, font=ft) for ch in text) + track * (len(text) - 1)

def draw_label(im, text, x, y, size=34, k=1.0, sub=None, style='glass', anchor=None):
    """calm captions. style 'glass': a soft dark frosted panel, a thin gold bar on the left, spaced capitals (+ an optional
    small second line). style 'pin': a small glowing dot at `anchor` (the place), a fine leader line to the text, text with
    a soft shadow and no panel. k: 0..1 appearance (fade + 12 px slide)"""
    if k <= 0: return
    a = min(1.0, k); slide = (1 - cm_sm(k)) * 12
    ft = font(size, 500); track = size * 0.12
    fs = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Regular.otf', int(size * 0.56)) if sub else None
    tw = text_w(text, ft, track); sw = text_w(sub, fs, size * 0.05) if sub else 0
    w = int(max(tw, sw) + size * 1.55); h = int(size * (1.55 if not sub else 2.35))
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0 = int(x + slide); y0 = int(y)
    if style == 'glass':
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        ds.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(size * 0.28), fill=(6, 10, 20, int(120 * a)))
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.18)); lay.alpha_composite(sh)
        d.rounded_rectangle([x0 + int(size * 0.32), y0 + int(size * 0.32), x0 + int(size * 0.32) + 3, y0 + h - int(size * 0.32)],
                            radius=2, fill=(255, 200, 110, int(230 * a)))
        tx = x0 + int(size * 0.62)
        _spaced(d, tx, y0 + int(size * 0.18), text, ft, (255, 255, 255, int(240 * a)), track)
        if sub: _spaced(d, tx, y0 + int(size * 1.38), sub, fs, (215, 222, 235, int(200 * a)), size * 0.05)
    else:
        ax, ay = anchor if anchor else (x - size, y + size)
        r = size * 0.16
        g = Image.new('RGBA', im.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
        dg.ellipse([ax - r * 3, ay - r * 3, ax + r * 3, ay + r * 3], fill=(255, 210, 130, int(110 * a)))
        g = g.filter(ImageFilter.GaussianBlur(r * 1.6)); lay.alpha_composite(g)
        d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=(255, 235, 200, int(255 * a)))
        ly = y0 + size * 0.75
        d.line([ax, ay, x0 - size * 0.3, ly], fill=(255, 255, 255, int(150 * a)), width=2)
        d.line([x0 - size * 0.3, ly, x0 - size * 0.05, ly], fill=(255, 255, 255, int(150 * a)), width=2)
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        _spaced(ds, x0 + 2, y0 + int(size * 0.12) + 2, text, ft, (0, 0, 0, int(200 * a)), track)
        if sub: _spaced(ds, x0 + 2, y0 + int(size * 1.32) + 2, sub, fs, (0, 0, 0, int(200 * a)), size * 0.05)
        sh = sh.filter(ImageFilter.GaussianBlur(3)); lay.alpha_composite(sh)
        _spaced(d, x0, y0 + int(size * 0.12), text, ft, (255, 255, 255, int(245 * a)), track)
        if sub: _spaced(d, x0, y0 + int(size * 1.32), sub, fs, (220, 226, 238, int(210 * a)), size * 0.05)
    im.alpha_composite(lay)

def cm_sm(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
