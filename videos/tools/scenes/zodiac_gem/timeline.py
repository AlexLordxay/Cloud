# «Ти Близнята?» — the camera, the Sun, Castor and Pollux, where Uranus and Pluto were found, and the Geminids (for the
# fact «найкращий зорепад року… загадай бажання», with one big fireball), as functions of the
# video time t (s). Helpers from the 13th-sign scene.
import importlib.util, math, os, datetime
import numpy as np
from PIL import Image, ImageDraw
from sky import ecl, vec, slerp

_s = importlib.util.spec_from_file_location('z13', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zodiac13', 'timeline.py'))
Z = importlib.util.module_from_spec(_s); _s.loader.exec_module(Z)
ease, ramp, win, date_of, sun_lon = Z.ease, Z.ramp, Z.win, Z.date_of, Z.sun_lon

CASTOR, POLLUX = vec(113.650, 31.888), vec(116.329, 28.026)
HEADS = slerp(CASTOR, POLLUX, 0.5)
GEM = vec(103.0, 24.0)
GEMC = vec(109.0, 25.0)     # the meteors: the figure in the middle, the radiant just above
URANUS = vec(90.6, 23.4)          # 13 March 1781, Herschel: by H Geminorum, at the feet of the Twins
PLUTO = vec(108.9, 22.1)          # January 1930, Tombaugh's plates: by δ Geminorum
RADIANT = vec(112.0, 33.0)        # the Geminids
lam = lambda m, d: sun_lon(datetime.datetime(2026, m, d, 12))
L_JUN21, L_JUL20, L_MAY21, L_JUN20 = lam(6, 21), lam(7, 20), lam(5, 21), lam(6, 20)

KEYS = [(0.0, GEM, 1050, 0), (10.4, GEM, 1100, 0), (15.0, GEM, 1100, 0), (17.0, HEADS, 1700, 0), (19.6, HEADS, 1750, 0),
        (21.0, CASTOR, 2600, 0), (24.9, CASTOR, 2700, 0), (26.0, POLLUX, 2600, 0), (29.0, POLLUX, 2700, 0),
        (30.6, GEMC, 1000, 0), (49.7, GEMC, 940, 0)]

def _camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

def _sun(t):          # 21 June -> 20 July through the Twins
    return L_JUN21 + (L_JUL20 - L_JUN21) * ramp(t, 11.0, 14.8), win(t, 10.4, 15.4, 0.5)

def sectors(t):
    return 0.0, 0.0

def _view(t):
    c, s, r = _camera(t)
    lm, sk = _sun(t)
    gem = max(win(t, 10.4, 30.0, 0.6), 0.5 * win(t, 29.4, 99, 0.6))
    glow = []
    eyes = win(t, -1, 19.8, 0.6) * (0.75 + 0.25 * math.sin(t * 4.0))   # the hook: the Twins' two bright eyes
    for v_ in (CASTOR, POLLUX):
        glow.append((v_, 14, (255, 236, 200), 0.9 * eyes))
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7, hi={'Gem': gem}, borders={'Gem': gem},
                zlines=0.8, lines=0.25, labels=1.0, sun=lm, sun_k=sk, sun_r=18, label_size=20, glow=glow, clip_rho=2.0)

def _pt(P, v):
    x, y, ok = P(v)
    return float(x[0]) / 2, float(y[0]) / 2, bool(ok[0])

def _overlay(img, P, t, sky):
    lay = img.convert('RGBA'); ov = Image.new('RGBA', lay.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f = sky.font(10)
    # where the two planets were found: a ring and the year
    for v_, name, a_, b_, side in ((URANUS, 'Уран · 1781', 4.4, 10.4, -1), (PLUTO, 'Плутон · 1930', 7.6, 10.4, 1)):
        k = win(t, a_, b_, 0.5)
        if k > 0:
            x, y, ok = _pt(P, v_)
            R = 14 + 4 * (1 - ramp(t, a_, a_ + 0.6))
            d.ellipse((x - R, y - R, x + R, y + R), outline=(130, 220, 255, int(255 * k)), width=3)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(200, 240, 255, int(255 * k)))
            d.text((x + side * (R + 6), y - (0 if side > 0 else 30)), name, font=f, anchor='lm' if side > 0 else 'rm', fill=(200, 236, 255, int(255 * k)))
    # the names of the two heads
    k = win(t, 15.4, 19.6, 0.5)
    if k > 0:
        for v_, name, dx in ((CASTOR, 'Кастор', -1), (POLLUX, 'Поллукс', 1)):
            x, y, ok = _pt(P, v_)
            d.text((x + dx * 22, y + 26), name, font=f, anchor='rm' if dx < 0 else 'lm', fill=(255, 236, 200, int(255 * k)))
    # the Geminids: streaks shooting out from the radiant, each a short bright line that fades
    k = win(t, 29.6, 42.6, 0.6)
    if k > 0:
        rx, ry, _ = _pt(P, RADIANT)
        rng = np.random.default_rng(3)
        for i in range(280):
            t0 = 29.6 + rng.uniform(0, 12.4); ang = rng.uniform(0, 2 * math.pi); r0 = rng.uniform(40, 260); L = rng.uniform(90, 230)
            u = (t - t0) / 0.45
            if 0 <= u <= 1:
                a = math.sin(math.pi * u)
                p0 = r0 + L * max(0, u - 0.35); p1 = r0 + L * u
                ca, sa = math.cos(ang), math.sin(ang)
                d.line((rx + ca * p0, ry + sa * p0, rx + ca * p1, ry + sa * p1), fill=(255, 250, 235, int(250 * a * k)), width=3)
    # «встигни загадати бажання»: one long, bright fireball
    u = (t - 39.4) / 1.4
    if 0 <= u <= 1:
        rx, ry, _ = _pt(P, RADIANT)
        ang = math.radians(118); ca, sa = math.cos(ang), math.sin(ang)
        p1 = 80 + 620 * ease(u); p0 = max(80.0, p1 - 260)
        a = min(1.0, 4 * (1 - u))
        for j in range(20):                      # the tail: thin and faint behind, thick and bright at the head
            q0, q1 = p0 + (p1 - p0) * j / 20, p0 + (p1 - p0) * (j + 1) / 20; s = (j + 1) / 20
            d.line((rx + ca * q0, ry + sa * q0, rx + ca * q1, ry + sa * q1), fill=(255, 244, 220, int(255 * a * s)), width=max(1, int(7 * s)))
        d.ellipse((rx + ca * p1 - 6, ry + sa * p1 - 6, rx + ca * p1 + 6, ry + sa * p1 + 6), fill=(255, 255, 255, int(255 * a)))
    lay.alpha_composite(ov)
    return lay.convert('RGB')


# ---- the fact «за гороскопом ти Близнята, а Сонце — у Тельці», spliced in after the dates (15.2 s .. 27.8 s): the camera
# goes over to Taurus, the Sun crosses it from 21 May to 20 June, and comes back; everything after it runs 12.6 s later
TAU = vec(72.0, 20.0)
CUT, D = 15.2, 12.6
TKEYS = [(CUT, GEM, 1100, 0), (17.4, TAU, 800, 0), (25.8, TAU, 830, 0), (CUT + D, GEM, 1100, 0)]

def _old(t):
    return t if t < CUT else t - D

def _in_tau(t):
    return CUT <= t < CUT + D

def camera(t):
    if not _in_tau(t): return _camera(_old(t))
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(TKEYS, TKEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0
    return TKEYS[-1][1:]

def sun(t):
    if not _in_tau(t): return _sun(_old(t))
    return L_MAY21 + (L_JUN20 - L_MAY21) * ramp(t, 17.2, 26.4), win(t, 15.7, 27.5, 0.6)

def view(t):
    if not _in_tau(t): return _view(_old(t))
    c, s, r = camera(t)
    lm, sk = sun(t)
    tau = win(t, 15.6, 27.6, 0.8)
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7, hi={'Tau': tau}, borders={'Tau': tau}, zlines=0.8, lines=0.25,
                labels=1.0, sun=lm, sun_k=sk, sun_r=18, label_size=20, glow=[], clip_rho=2.0)

def overlay(img, P, t, sky):
    return img if _in_tau(t) else _overlay(img, P, _old(t), sky)
