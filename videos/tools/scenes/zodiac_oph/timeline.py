# «Ти Змієносець?» — the camera, the Sun, the Star of Life, Ophiuchus with his Serpent (both halves) and Barnard's star
# as functions of the video time t (s). Built on «Ти Стрілець?»; the helpers come from the 13th-sign scene.
# The voice (scene.json parts): 0.2–41.4 the main text up to Barnard's star, 42.0–51.3 the fact, 52.0–55.6 «з України»,
# 56.2–59.5 the call to comment.
import importlib.util, math, os, datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from sky import vec, slerp

_s = importlib.util.spec_from_file_location('z13', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zodiac13', 'timeline.py'))
Z = importlib.util.module_from_spec(_s); _s.loader.exec_module(Z)
ease, ramp, win, date_of, sun_lon = Z.ease, Z.ramp, Z.win, Z.date_of, Z.sun_lon

OPHC = vec(256.0, -7.0)                            # Ophiuchus in the middle of the frame (the Sun's path at the bottom)
MID = vec(268.0, -14.0)                            # Ophiuchus and Sagittarius together («ти не Стрілець»)
SERP = vec(258.0, 3.0)                             # the Serpent's head (west) and tail (east) with Ophiuchus between
BARN = vec(269.452, 4.693)                         # Barnard's star (mag 9.5, not in the catalogue: drawn here)
LOW = vec(257.0, -4.5)                             # July 22:00 from Kyiv: the horizon (Dec -39.5 on the meridian) at y 1440
L_NOV29, L_DEC17 = sun_lon(datetime.datetime(2026, 11, 29, 12)), sun_lon(datetime.datetime(2026, 12, 17, 12))

def _ra(c): return c if c >= 0 else c + 360
# figures from d3-celestial (constellations.lines.json); sky.py keeps only one of the two Serpens features, so both are here
OPH_LINES = [[(-90.2434, -9.7736), (-93.0268, 2.7073), (-94.1319, 4.5673), (-96.2664, 12.56), (-105.5829, 9.375), (-112.2716, 1.9839),
              (-116.4136, -3.6943), (-115.4196, -4.6925), (-110.7103, -10.5671), (-102.4055, -15.7249)],
             [(-105.5829, 9.375), (-110.7103, -10.5671), (-112.2151, -16.6127), (-113.244, -18.4563), (-113.9742, -20.0373), (-113.6037, -23.4472)],
             [(-94.1319, 4.5673), (-102.4055, -15.7249), (-99.4976, -24.9995), (-98.1614, -29.867)]]
SER_HEAD = [(-123.4531, 15.4218), (-124.6123, 19.6704), (-122.8151, 18.1416), (-120.8867, 15.6616), (-123.4531, 15.4218), (-126.2994, 10.5389),
            (-123.933, 6.4256), (-122.296, 4.4777), (-116.4136, -3.6943)]
SER_TAIL = [(-102.4055, -15.7249), (-95.6033, -15.3986), (-90.2434, -9.7736), (-89.2295, -8.1803), (-84.6725, -2.8988), (-75.9451, 4.2036)]
OPH_LINES = [[vec(_ra(a), b) for a, b in s] for s in OPH_LINES]
SER_HEAD = [vec(_ra(a), b) for a, b in SER_HEAD]
SER_TAIL = [vec(_ra(a), b) for a, b in SER_TAIL]
HEAD_AT, TAIL_AT = vec(234.0, 13.0), vec(280.5, 6.5)

KEYS = [(0.0, OPHC, 640, 0), (3.9, OPHC, 620, 0), (4.6, MID, 540, 0), (6.1, MID, 540, 0), (7.2, OPHC, 700, 0), (13.2, OPHC, 690, 0),
        (22.2, OPHC, 740, 0), (24.0, SERP, 560, 0), (31.3, SERP, 580, 0), (33.4, BARN, 1800, 0), (36.0, BARN, 2100, 0),
        (38.1, BARN, 20000, 0), (41.3, BARN, 21500, 0), (43.4, BARN, 2600, 0), (51.4, BARN, 2900, 0), (52.8, LOW, 520, 0),
        (55.8, LOW, 530, 0), (57.0, OPHC, 660, 0), (63.2, OPHC, 690, 0)]

def camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

def sun(t):           # 29 November -> 17 December through Ophiuchus, while the voice says the dates
    return L_NOV29 + (L_DEC17 - L_NOV29) * ease((t - 1.9) / 5.6), win(t, -1, 8.1, 0.5)

def sectors(t):
    return 0.0, 0.0

def view(t):
    c, s, r = camera(t)
    lam, sk = sun(t)
    oph = max(win(t, -1, 22.3, 0.6), win(t, 51.6, 99, 0.6))
    ser = win(t, 22.4, 31.4, 0.6)
    deep = ramp(t, 36.3, 37.8) * (1 - ramp(t, 41.3, 42.6))          # very deep zoom: the photo gets soft, so fade it
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 * win(t, -1, 8.2, 0.6), hi={'Oph': oph, 'Sgr': 0.0},
                borders={'Oph': oph, 'Ser': ser}, zlines=0.8, lines=0.25 * (1 - deep), labels=1.0 - deep,
                zlabel={'Oph': (1.0 - deep) * (1 - 0.7 * ser)}, sun=lam, sun_k=sk, sun_r=18, label_size=20,
                photo=1.0 - deep, mw=0.0, clip_rho=2.0)

def _pt(P, v):
    x, y, ok = P(v)
    return float(x[0]) / 2, float(y[0]) / 2, bool(ok[0])

def _poly(d, P, pts, col, a, width, part=1.0):
    """a polyline through sky points, drawn up to the fraction `part` of its length (for drawing the figure in)"""
    xy = [_pt(P, v)[:2] for v in pts]
    seg = [math.dist(p, q) for p, q in zip(xy, xy[1:])]; total = sum(seg) * part
    out = [xy[0]]
    for (p, q), L in zip(zip(xy, xy[1:]), seg):
        if total <= 0: break
        k = min(1.0, total / L) if L else 1.0
        out.append((p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k)); total -= L
    if len(out) > 1: d.line(out, fill=col + (int(255 * a),), width=width, joint='curve')
    return xy

def _rod(d, cx, cy, h, a, col=(255, 255, 255), w=None):
    """the Rod of Asclepius: a staff with one snake winding round it (h: staff height, px)"""
    w = w or max(4, int(h * 0.055))
    d.line((cx, cy - h / 2, cx, cy + h / 2), fill=col + (int(255 * a),), width=w)
    pts = []
    for i in range(61):
        u = i / 60; y = cy + h * 0.38 - u * h * 0.72
        pts.append((cx + h * 0.13 * math.sin(u * 2.6 * math.pi) * (0.6 + 0.4 * u), y))
    d.line(pts, fill=col + (int(255 * a),), width=int(w * 0.85), joint='curve')
    hx, hy = pts[-1]
    d.ellipse((hx - w * 1.1, hy - w * 0.9, hx + w * 1.6, hy + w * 0.7), fill=col + (int(255 * a),))

def star_of_life(size, a):
    """the blue six-armed Star of Life (the ambulance emblem) with the rod in the middle, an RGBA image size×size"""
    S = size * 2; im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    arm_w, arm_l = S * 0.30, S * 0.48
    def bar(col, grow):
        lay = Image.new('RGBA', (S, S), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        dl.rounded_rectangle((S / 2 - arm_w / 2 - grow, S / 2 - arm_l - grow, S / 2 + arm_w / 2 + grow, S / 2 + arm_l + grow),
                             radius=S * 0.02, fill=col)
        return lay
    for col, grow in (((255, 255, 255, 255), S * 0.025), ((22, 86, 196, 255), 0)):
        for ang in (0, 60, 120):
            im.alpha_composite(bar(col, grow).rotate(ang, resample=Image.BICUBIC))
    _rod(ImageDraw.Draw(im), S / 2, S / 2, S * 0.62, 1.0, w=int(S * 0.034))
    im = im.resize((size, size), Image.LANCZOS)
    if a < 1: im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    return im

GOLD, GREEN = (255, 210, 120), (150, 235, 170)

def overlay(img, P, t, sky):
    lay = img.convert('RGBA'); ov = Image.new('RGBA', lay.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    W, H = lay.size
    # «Тоді ти не Стрілець»: Sagittarius' name struck through in red
    k = win(t, 4.6, 6.3, 0.3)
    if k > 0:
        x, y, ok = _pt(P, sky.label['Sgr'])
        if ok:
            L = 62 * ramp(t, 4.6, 5.0)
            d.line((x - 62, y + 2, x - 62 + 2 * L, y - 2), fill=(255, 90, 80, int(255 * k)), width=4)
    # Ophiuchus drawn in gold over his stars (13.4–15.8), the Serpent in green in his hands (16.4–18.3)
    ko = win(t, 13.3, 31.4, 0.5) * (1 - 0.45 * win(t, 22.6, 31.4, 0.6))
    if ko > 0:
        part = ramp(t, 13.3, 15.9)
        for s in OPH_LINES: _poly(d, P, s, GOLD, 0.9 * ko, 4, part)
        if part > 0.3:
            for s in OPH_LINES:
                for v_ in s:
                    x, y, _ = _pt(P, v_); d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 236, 190, int(255 * ko * ramp(t, 14.0, 15.0))))
    ks = win(t, 16.3, 31.4, 0.5)
    if ks > 0:
        part = ramp(t, 16.3, 18.3)
        pulse = 1 + 0.25 * math.sin((t - 22.5) * 4) * win(t, 22.5, 27.0, 0.6)
        for s, a0 in ((SER_HEAD, 27.2), (SER_TAIL, 29.7)):
            flash = 1 + 0.6 * win(t, a0, a0 + 1.6, 0.4)
            _poly(d, P, s, GREEN, min(1.0, 0.95 * ks * pulse), int(5 * min(flash, 1.4)), part)
        f = sky.font(13)
        for at, a0, txt in ((HEAD_AT, 27.2, 'ГОЛОВА'), (TAIL_AT, 29.7, 'ХВІСТ')):
            kk = win(t, a0, 31.4, 0.4)
            if kk > 0:
                x, y, _ = _pt(P, at)
                d.text((x + 2, y + 2), txt, font=f, anchor='mm', fill=(0, 0, 0, int(170 * kk)))
                d.text((x, y), txt, font=f, anchor='mm', fill=GREEN + (int(255 * kk),))
    # Barnard's star: an orange dot with a ring; the deep zoom shows it crawl north for 200 years next to the Moon's width
    kb = max(win(t, 31.8, 41.6, 0.5), win(t, 41.8, 51.6, 0.5))
    if kb > 0:
        yrs = 200 * ramp(t, 38.4, 41.0)
        ra0, de0 = 269.452, 4.693
        now = vec(ra0 - yrs * 0.80 / 3600 / math.cos(math.radians(de0)), de0 + yrs * 10.36 / 3600)
        x, y, _ = _pt(P, now); x0, y0, _ = _pt(P, BARN)
        deep = win(t, 37.4, 41.6, 0.5)
        if deep > 0 and yrs > 0:
            d.line((x0, y0, x, y), fill=(255, 170, 110, int(150 * deep)), width=3)
        # the Moon's width (0.52°) beside the path, the same size on the sky
        if deep > 0:
            mc = vec(ra0 + 0.62, de0 + 0.29); mx, my, _ = _pt(P, mc)
            mr = abs(_pt(P, vec(ra0 + 0.62, de0 + 0.29 + 0.26))[1] - my)
            d.ellipse((mx - mr, my - mr, mx + mr, my + mr), outline=(220, 225, 240, int(200 * deep)), width=3)
            d.text((mx, my + mr + 18), 'ширина Місяця', font=sky.font(12), anchor='mm', fill=(220, 225, 240, int(230 * deep)))
        g = Image.new('RGBA', lay.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
        dg.ellipse((x - 12, y - 12, x + 12, y + 12), fill=(255, 150, 90, int(140 * kb)))
        ov.alpha_composite(g.filter(ImageFilter.GaussianBlur(6)))
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 205, 160, int(255 * kb)))
        ring = kb * (1 - deep)
        if ring > 0:
            R = 22 + 10 * (1 - ramp(t, 31.8, 32.8))
            d.ellipse((x - R, y - R, x + R, y + R), outline=(255, 210, 160, int(255 * ring)), width=3)
            d.text((x + R + 10, y), 'зоря Барнарда', font=sky.font(11), anchor='lm', fill=(255, 225, 190, int(255 * ring)))
    lay.alpha_composite(ov)
    # «на кожній машині швидкої допомоги»: the Star of Life over a darkened sky; the small rod again for «символ медицини»
    k = win(t, 8.0, 13.3, 0.45)
    if k > 0:
        dark = Image.new('RGBA', lay.size, (0, 0, 0, 0))
        ImageDraw.Draw(dark).ellipse((W / 2 - 260, 600 - 260, W / 2 + 260, 600 + 260), fill=(4, 6, 12, int(170 * k)))
        lay.alpha_composite(dark.filter(ImageFilter.GaussianBlur(50)))
        sz = int(300 * (0.85 + 0.15 * ease((t - 8.0) / 0.6)))
        em = star_of_life(sz, k)
        lay.alpha_composite(em, (int(W / 2 - sz / 2), int(600 - sz / 2)))
    k = win(t, 18.6, 22.3, 0.4)
    if k > 0:
        r = Image.new('RGBA', lay.size, (0, 0, 0, 0)); _rod(ImageDraw.Draw(r), 78, 385, 150, k, col=(255, 236, 190))
        lay.alpha_composite(r)
    return lay.convert('RGB')
