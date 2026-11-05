# «Ти Козеріг?» — the camera, the Sun and the drawings over the sky as functions of the video time t (s). Built on «Ти
# Стрілець?» (the helpers come from the 13th-sign scene).
# 5.11 re-cut (lessons from «Ти Змієносець?»: the twist for everyone first, the dates later, a short ending): the fact
# («якщо ти Козеріг за гороскопом… Сонце стояло в Стрільці») now opens the video at 0.3–8.9; the main text («твоє
# сузір'я — одне з найдавніших…») follows at 9.4–42.7 and is the old timeline shifted by M = 7.75 s; the call to comment
# 43.3–46.8; the end card from 47.0. The old functions are kept as _old_* and are called with t - M.
import importlib.util, math, os, datetime
from PIL import Image, ImageDraw, ImageFilter
from sky import vec, ecl, slerp

_s = importlib.util.spec_from_file_location('z13', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zodiac13', 'timeline.py'))
Z = importlib.util.module_from_spec(_s); _s.loader.exec_module(Z)
ease, ramp, win, date_of, sun_lon = Z.ease, Z.ramp, Z.win, Z.date_of, Z.sun_lon

CAP = vec(314.0, -19.0)                            # Capricornus in the middle of the frame
TROP = ecl(286.0, -4.0)                            # between today's solstice point (Sagittarius) and that of 2000 years ago
ALG = vec(304.46, -12.53)                          # α Capricorni (Algedi): the pair on the horn
A1 = vec(304.412, -12.508)                         # α¹: ~600 light years
A2 = vec(304.514, -12.545)                         # α²: ~110 light years
SGR = vec(281.0, -26.0)
GC = vec(266.417, -29.008)
# the solstice point: the Sun's place on the shortest day — now at ecliptic longitude 270° (in Sagittarius); 2000 years
# ago precession (50.3″ a year) had it 28° further east, in Capricornus
SOL_NOW, SOL_OLD = 270.0, 270.0 + 50.3 * 2000 / 3600
L_JAN19, L_FEB16 = sun_lon(datetime.datetime(2027, 1, 19, 12)), sun_lon(datetime.datetime(2027, 2, 16, 12))
L_DEC22, L_JAN19B = sun_lon(datetime.datetime(2026, 12, 22, 12)), L_JAN19

KEYS = [(0.0, CAP, 640, 0), (8.6, CAP, 600, 0), (10.4, TROP, 520, 0), (19.0, TROP, 540, 0), (20.4, CAP, 600, 0),
        (24.5, CAP, 610, 0), (26.4, ALG, 3000, 0), (28.6, ALG, 26000, 0), (34.6, ALG, 28000, 0), (36.6, SGR, 560, 0),
        (44.4, SGR, 580, 0), (46.0, CAP, 640, 0), (52.2, CAP, 660, 0)]

def _old_camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

def _old_sun(t):
    """19 January → 16 February through Capricornus (with the dates), then for the fact 22 December → 19 January,
    which is all in Sagittarius."""
    if t < 30:
        return L_JAN19 + (L_FEB16 - L_JAN19) * ease((t - 19.9) / 4.4), win(t, 19.4, 24.6, 0.5)
    return L_DEC22 + (L_JAN19B - L_DEC22) * ease((t - 37.6) / 5.0), win(t, 36.8, 44.6, 0.5)

def sectors(t):
    return 0.0, 0.0

def _old_view(t):
    c, s, r = _old_camera(t)
    lam, sk = _old_sun(t)
    hi_cap = max(win(t, -1, 24.6, 0.6), ramp(t, 45.2, 46.4))
    hi_sgr = win(t, 36.4, 44.6, 0.6)
    deep = ramp(t, 26.8, 27.8) * (1 - ramp(t, 34.6, 35.6))                     # the deep zoom on the horn
    glow = []
    core = win(t, 41.0, 44.6, 0.6)                                              # «неподалік від центру Галактики»
    if core > 0: glow += [(GC, 90, (255, 200, 140), 0.16 * core), (GC, 14, (255, 235, 210), 0.5 * core)]
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 * max(win(t, 8.8, 24.6, 0.6), win(t, 36.4, 44.6, 0.6)),
                hi={'Cap': hi_cap, 'Sgr': hi_sgr}, borders={'Cap': hi_cap * (1 - deep), 'Sgr': hi_sgr},
                zlines=0.8 * (1 - deep), lines=0.25 * (1 - deep), labels=1.0 - deep, sun=lam, sun_k=sk, sun_r=18,
                label_size=20, glow=glow, clip_rho=2.0, photo=1.0 - deep, mw=0.0)

def _pt(P, v):
    x, y, ok = P(v)
    return float(x[0]) / 2, float(y[0]) / 2, bool(ok[0])

def _mark(d, x, y, R, k, col):
    d.ellipse((x - R, y - R, x + R, y + R), outline=col + (int(255 * k),), width=3)

def _old_overlay(img, P, t, sky):
    lay = img.convert('RGBA'); ov = Image.new('RGBA', lay.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    gold, blue = (255, 210, 120), (140, 205, 255)
    # the shortest day's Sun, 2000 years ago (in Capricornus) and now (in Sagittarius): the point slides back along the
    # ecliptic as precession carries it
    k = win(t, 12.9, 19.0, 0.5)
    if k > 0:
        x0, y0, _ = _pt(P, ecl(SOL_OLD)); x1, y1, _ = _pt(P, ecl(SOL_NOW))
        u = ease((t - 14.6) / 3.0)
        g = Image.new('RGBA', lay.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
        xs, ys = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        dg.ellipse((xs - 22, ys - 22, xs + 22, ys + 22), fill=(255, 200, 110, int(150 * k)))
        ov.alpha_composite(g.filter(ImageFilter.GaussianBlur(9)))
        d.ellipse((xs - 9, ys - 9, xs + 9, ys + 9), fill=(255, 244, 214, int(255 * k)))
        f = sky.font(11)
        d.text((x0, y0 - 30), '2000 років тому', font=f, anchor='mm', fill=gold + (int(255 * k * (1 - 0.5 * u)),))
        if u > 0.05:
            d.line((x0, y0, xs, ys), fill=gold + (int(150 * k),), width=2)
            d.text((x1, y1 + 30), 'сьогодні', font=f, anchor='mm', fill=gold + (int(255 * k * u),))
    # the horn: α¹ and α² — two stars that look like a pair but are ~600 and ~110 light years away
    k = win(t, 27.6, 34.9, 0.5)
    if k > 0:
        f = sky.font(11)
        for v_, name, col, side, a0 in ((A1, 'далека · ~600 світлових років', gold, -1, 29.6), (A2, 'ближча · ~110 світлових років', blue, 1, 30.4)):
            x, y, _ = _pt(P, v_)
            g = Image.new('RGBA', lay.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
            dg.ellipse((x - 16, y - 16, x + 16, y + 16), fill=col + (int(170 * k),))
            ov.alpha_composite(g.filter(ImageFilter.GaussianBlur(8)))
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 250, 240, int(255 * k)))
            kk = k * ramp(t, a0, a0 + 0.6)
            if kk > 0:
                _mark(d, x, y, 26, kk, col)
                d.text((x, y + side * 48), name, font=f, anchor='mm', fill=col + (int(255 * kk),))
    # the fact: the centre of the Galaxy beside the Sun in Sagittarius
    k = win(t, 41.0, 44.6, 0.5)
    if k > 0:
        x, y, _ = _pt(P, GC); R = 22 + 10 * (1 - ramp(t, 41.0, 42.0))
        _mark(d, x, y, R, k, (255, 220, 160))
        d.text((x, y - R - 12), 'центр Галактики', font=sky.font(11), anchor='mb', fill=(255, 230, 190, int(255 * k)))
    lay.alpha_composite(ov)
    return lay.convert('RGB')


# ---- the 5.11 re-cut ----
M = 7.75                                            # main block: new t = old t + M
FACT_END, CALL0, END = 8.9, 43.3, 49.5
NEW_KEYS = [(0.0, CAP, 640, 0), (2.0, CAP, 620, 0), (3.8, SGR, 560, 0), (FACT_END, SGR, 585, 0), (10.4, CAP, 600, 0)] + \
    [(t0 + M, c, s, r) for (t0, c, s, r) in KEYS if 8.6 <= t0 <= 34.6] + [(44.4, CAP, 640, 0), (END, CAP, 660, 0)]

def camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(NEW_KEYS, NEW_KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return NEW_KEYS[-1][1], NEW_KEYS[-1][2], NEW_KEYS[-1][3]

def sun(t):
    """The fact first: 22 December → 19 January, all in Sagittarius; then (old timeline) 19 January → 16 February."""
    if t < 9.2:
        return L_DEC22 + (L_JAN19B - L_DEC22) * ease((t - 2.8) / 4.6), win(t, 2.2, FACT_END, 0.5)
    if t > 42.9: return L_JAN19, 0.0
    return _old_sun(t - M)

def view(t):
    c, s, r = camera(t)
    lam, sk = sun(t)
    hi_cap = max(win(t, -1, 2.6, 0.6), win(t, 9.4, 24.6 + M, 0.6), ramp(t, 43.2, 44.4))
    hi_sgr = win(t, 2.2, FACT_END, 0.6)
    deep = ramp(t, 26.8 + M, 27.8 + M) * (1 - ramp(t, 34.6 + M, 35.6 + M))
    glow = []
    core = win(t, 6.0, FACT_END, 0.6)                                           # «неподалік від центру Галактики»
    if core > 0: glow += [(GC, 90, (255, 200, 140), 0.16 * core), (GC, 14, (255, 235, 210), 0.5 * core)]
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 * max(win(t, 8.8 + M, 24.6 + M, 0.6), win(t, 2.2, FACT_END, 0.6)),
                hi={'Cap': hi_cap, 'Sgr': hi_sgr}, borders={'Cap': hi_cap * (1 - deep), 'Sgr': hi_sgr},
                zlines=0.8 * (1 - deep), lines=0.25 * (1 - deep), labels=1.0 - deep, sun=lam, sun_k=sk, sun_r=18,
                label_size=20, glow=glow, clip_rho=2.0, photo=1.0 - deep, mw=0.0)

def overlay(img, P, t, sky):
    if 9.0 < t < 42.9:
        return _old_overlay(img, P, t - M, sky)                                  # tropic, the horn
    k = win(t, 6.0, FACT_END, 0.5)
    if k <= 0: return img
    lay = img.convert('RGBA'); ov = Image.new('RGBA', lay.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    x, y, _ = _pt(P, GC); R = 22 + 10 * (1 - ramp(t, 6.0, 7.0))
    _mark(d, x, y, R, k, (255, 220, 160))
    d.text((x, y - R - 12), 'центр Галактики', font=sky.font(11), anchor='mb', fill=(255, 230, 190, int(255 * k)))
    lay.alpha_composite(ov)
    return lay.convert('RGB')
