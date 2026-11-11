# «Ти Водолій?» — the camera, the Sun and the drawings over the sky as functions of the video time t (s). Helpers from
# the 13th-sign scene; built like «Ти Близнята?» / «Ти Козеріг?».
# Order (voice_all.mp3 = voice.mp3 + fact.mp3): 0.2 hook + Neptune (found here in 1846, first on paper) → 11.8 the dates
# (16.02–11.03) → 17.3 the fact «ера Водолія» (the vernal equinox point slides from Pisces to Aquarius, ~2600) → 28.7 the
# Helix Nebula (a deep zoom into the real VISTA picture, captions.py) → 36.6 TRAPPIST-1 (zoom, then the ESO artist's
# impression) → 45.1 the call to comment → 47.4 the end card.
import importlib.util, math, os, datetime
from PIL import Image, ImageDraw, ImageFilter
from sky import vec, ecl, slerp

_s = importlib.util.spec_from_file_location('z13', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zodiac13', 'timeline.py'))
Z = importlib.util.module_from_spec(_s); _s.loader.exec_module(Z)
ease, ramp, win, date_of, sun_lon = Z.ease, Z.ramp, Z.win, Z.date_of, Z.sun_lon

AQR = vec(334.0, -9.0)                     # Aquarius in the middle of the frame
NEP = vec(330.388, -12.666)                # Neptune on 23 September 1846 (Galle, Berlin), J2000 — astronomy-engine
HELIX = vec(337.411, -20.837)              # NGC 7293 (ESO eso1205a: 22h29m38.6s, −20°50′14″)
TRAP = vec(346.622, -5.041)                # TRAPPIST-1 (23h06m29.4s, −5°02′29″), ~40 light years, mag 18.8
EQ_NOW = vec(359.662, -0.147)              # the vernal equinox point of 2026, in J2000 (astronomy-engine)
EQ_2600 = vec(352.290, -3.326)             # … of 2600 — just inside Aquarius (crosses the border ~2598)
FACTC = vec(355.5, -3.5)                   # between the two, Pisces and Aquarius both in the frame
L_FEB16, L_MAR11 = sun_lon(datetime.datetime(2027, 2, 16, 12)), sun_lon(datetime.datetime(2027, 3, 11, 12))

HELIX_FOV = 37.51 / 60 * math.pi / 180     # the photo's side, in radians
DEEP = 150000                              # the Helix photo (2455 px at 1.5x) covers the 1080x1920 frame with its feathered edges

KEYS = [(0.0, AQR, 620, 0), (3.4, AQR, 580, 0), (5.2, NEP, 1150, 0), (11.0, NEP, 1300, 0), (12.6, AQR, 560, 0),
        (16.8, AQR, 580, 0), (18.6, FACTC, 620, 0), (27.6, FACTC, 660, 0),
        (28.9, HELIX, 1500, 0), (31.4, HELIX, 46000, 0), (36.0, HELIX, DEEP, 0), (37.6, AQR, 900, 0),
        (39.0, TRAP, 2600, 0), (41.0, TRAP, 30000, 0), (44.6, TRAP, 36000, 0), (46.2, AQR, 600, 0), (51.0, AQR, 640, 0)]

def camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

def sun(t):
    """16 February → 11 March through Aquarius, with the dates."""
    return L_FEB16 + (L_MAR11 - L_FEB16) * ease((t - 12.4) / 4.0), win(t, 11.8, 16.9, 0.5)

def sectors(t):
    return 0.0, 0.0

def deep(t):
    """0 → 1 as the camera dives past what the sky photo can show (Helix, TRAPPIST-1)."""
    return max(ramp(t, 29.6, 30.6) * (1 - ramp(t, 36.4, 37.2)), ramp(t, 39.4, 40.2) * (1 - ramp(t, 44.8, 45.6)))

def view(t):
    c, s, r = camera(t)
    lam, sk = sun(t)
    dp = deep(t)
    hi_aqr = max(win(t, -1, 17.4, 0.6), win(t, 22.0, 29.2, 0.6), ramp(t, 45.4, 46.4))
    hi_psc = win(t, 17.8, 23.6, 0.6)
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 * max(win(t, 11.6, 17.0, 0.6), win(t, 17.6, 28.0, 0.6)),
                hi={'Aqr': hi_aqr, 'Psc': hi_psc}, borders={'Aqr': hi_aqr * (1 - dp), 'Psc': hi_psc},
                zlines=0.8 * (1 - dp), lines=0.25 * (1 - dp), labels=1.0 - dp, sun=lam, sun_k=sk, sun_r=18,
                label_size=20, glow=[], clip_rho=2.0, photo=1.0 - dp, mw=0.0)

def _pt(P, v):
    x, y, ok = P(v)
    return float(x[0]) / 2, float(y[0]) / 2, bool(ok[0])

def _ring(d, x, y, R, k, col, w=3):
    d.ellipse((x - R, y - R, x + R, y + R), outline=col + (int(255 * k),), width=w)

def _glow_dot(lay, d, x, y, k, col, r=16):
    g = Image.new('RGBA', lay.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
    dg.ellipse((x - r, y - r, x + r, y + r), fill=col + (int(170 * k),))
    lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(r / 2)))
    d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(240, 248, 255, int(255 * k)))

def overlay(img, P, t, sky):
    lay = img.convert('RGBA'); ov = Image.new('RGBA', lay.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f = sky.font(11)
    blue, gold = (140, 205, 255), (255, 210, 120)
    # Neptune: where Galle saw it on 23 September 1846 — a blue point and a ring that tightens onto it
    k = win(t, 4.0, 11.4, 0.5)
    if k > 0:
        x, y, _ = _pt(P, NEP)
        _glow_dot(lay, d, x, y, k, (110, 160, 255))
        R = 24 + 18 * (1 - ease(ramp(t, 4.0, 5.2)))
        _ring(d, x, y, R, k, blue)
        d.text((x, y - R - 14), 'Нептун · 1846', font=f, anchor='mb', fill=(200, 230, 255, int(255 * k)))
    # «ера Водолія»: the vernal equinox point now (in Pisces) slides west along the ecliptic into Aquarius by ~2600
    k = win(t, 20.6, 28.2, 0.5)
    if k > 0:
        x0, y0, _ = _pt(P, EQ_NOW); x1, y1, _ = _pt(P, EQ_2600)
        u = ease((t - 23.8) / 3.6)
        xs, ys = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        g = Image.new('RGBA', lay.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
        dg.ellipse((xs - 22, ys - 22, xs + 22, ys + 22), fill=(255, 200, 110, int(150 * k)))
        lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(9)))
        d.ellipse((xs - 9, ys - 9, xs + 9, ys + 9), fill=(255, 244, 214, int(255 * k)))
        d.text((x0, y0 - 30), 'сьогодні', font=f, anchor='mm', fill=gold + (int(255 * k * (1 - 0.5 * u)),))
        if u > 0.05:
            d.line((x0, y0, xs, ys), fill=gold + (int(150 * k),), width=2)
            d.text((x1, y1 - 30), '≈ 2600 рік', font=f, anchor='mm', fill=gold + (int(255 * k * u),))
    # TRAPPIST-1: too faint to see (19th magnitude) — a ring on its place in the sky before the picture comes
    k = win(t, 38.6, 40.6, 0.5)
    if k > 0:
        x, y, _ = _pt(P, TRAP)
        R = 26 + 16 * (1 - ease(ramp(t, 38.6, 39.6)))
        _ring(d, x, y, R, k, (255, 170, 120))
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 190, 150, int(200 * k)))
    lay.alpha_composite(ov)
    return lay.convert('RGB')
