# «Ти Терези?» — the camera, the Sun, Gliese 581 and the two «claws» as functions of the video time t (s). The helpers (easing,
# camera glide, dates) come from the 13th-sign scene. The voice (scene.json): «Ти Терези? … а річ» 0.2–6.1, the Sun's dates 6.8–12.4,
# Gliese 581 12.8–20.3, the fact about the claws 20.75–31.1, the call to comment 33.1–36.7 (a 2 s pause before it).
import importlib.util, math, os, datetime
import numpy as np
from PIL import ImageDraw
from sky import ecl, vec, slerp

_s = importlib.util.spec_from_file_location('z13', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zodiac13', 'timeline.py'))
Z = importlib.util.module_from_spec(_s); _s.loader.exec_module(Z)
ease, ramp, win, date_of, sun_lon = Z.ease, Z.ramp, Z.win, Z.date_of, Z.sun_lon

LIB = vec(228.0, -14.0)
ZUBEN_S = vec(222.72, -16.04)         # α2 Librae, Zubenelgenubi: «the southern claw»
ZUBEN_N = vec(229.25, -9.38)          # β Librae, Zubeneschamali: «the northern claw»
GL581 = vec(229.86, -7.72)            # Gliese 581, a red dwarf ~20 light years away; four planets found 2005–2009
CLAWS = slerp(slerp(ZUBEN_S, ZUBEN_N, 0.5), vec(240.0, -22.0), 0.35)   # the two claws with Scorpius's head in the corner
L30, L23 = sun_lon(datetime.datetime(2026, 10, 30, 12)), sun_lon(datetime.datetime(2026, 11, 23, 12))
L23S, L22O = sun_lon(datetime.datetime(2026, 9, 23, 12)), sun_lon(datetime.datetime(2026, 10, 22, 12))

KEYS = [(0.0, LIB, 760, 0), (6.4, LIB, 790, 0), (12.4, LIB, 790, 0), (14.2, GL581, 2300, 0), (19.6, GL581, 2500, 0),
        (21.8, CLAWS, 900, 0), (31.2, CLAWS, 950, 0), (33.6, LIB, 700, 0), (39.6, LIB, 720, 0)]

def camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

SUN_KEYS = [(6.6, L30 - 3), (7.9, L30), (11.9, L23), (12.4, L23 + 0.5)]

def sun(t):
    lam = SUN_KEYS[0][1] if t < SUN_KEYS[0][0] else SUN_KEYS[-1][1]
    for (t0, l0), (t1, l1) in zip(SUN_KEYS, SUN_KEYS[1:]):
        if t0 <= t <= t1: lam = l0 + (l1 - l0) * ease((t - t0) / (t1 - t0)); break
    return lam, win(t, 6.6, 12.5, 0.5)

def sectors(t):
    return 0.0, 0.0

def view(t):
    c, s, r = camera(t)
    lam, sk = sun(t)
    hi = max(win(t, 0.2, 12.6, 0.6), win(t, 21.6, 39.6, 0.6))
    sco = win(t, 21.2, 31.6, 0.8)
    glow = []
    eyes = win(t, -1, 6.4, 0.6) * (0.8 + 0.2 * math.sin(t * 4.0))            # the hook: the two bright stars of the scales
    for v_ in (ZUBEN_S, ZUBEN_N): glow.append((v_, 14, (255, 236, 200), 0.9 * eyes))
    claws = win(t, 21.5, 31.4, 0.7) * (0.75 + 0.25 * math.sin(t * 3.0))
    for v_ in (ZUBEN_S, ZUBEN_N): glow.append((v_, 22, (255, 220, 170), 0.9 * claws))
    star = win(t, 14.0, 20.3, 0.6)
    if star > 0: glow.append((GL581, 16, (255, 130, 70), 0.8 * star))        # the red dwarf
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 * win(t, 6.0, 12.8, 0.6), hi={'Lib': hi, 'Sco': 0.45 * sco}, borders={'Lib': hi, 'Sco': 0.5 * sco},
                zlines=0.8, lines=0.25, labels=1.0, sun=lam, sun_k=sk, sun_r=18, label_size=20, glow=glow, clip_rho=2.0)

def _pt(P, v):
    x, y, ok = P(v)
    return float(x[0]) / 2, float(y[0]) / 2, bool(ok[0])

def overlay(img, P, t, sky):
    lay = img.convert('RGBA'); ov = lay.copy(); ov.putalpha(0); d = ImageDraw.Draw(ov)
    f = sky.font(10)
    # the claws: a ring and the old name beside each star
    k = win(t, 22.9, 31.2, 0.6)
    if k > 0:
        for v_, name, side in ((ZUBEN_S, 'Зубенельгенубі', 1), (ZUBEN_N, 'Зубенешамалі', -1)):
            x, y, ok = _pt(P, v_)
            R = 16 + 3 * math.sin(t * 3)
            d.ellipse((x - R, y - R, x + R, y + R), outline=(255, 230, 180, int(255 * k)), width=3)
            d.text((x + side * (R + 8), y), name, font=f, anchor='lm' if side > 0 else 'rm', fill=(255, 236, 200, int(255 * k)))
    # Gliese 581 and its four planets: a ring on the star, small orbits with a dot each (a sketch, not to scale)
    k = win(t, 14.1, 20.3, 0.6)
    if k > 0:
        x, y, ok = _pt(P, GL581)
        for r_, ang, nm, show in ((26, 20, 'b', 16.6), (42, 130, 'c', 17.1), (60, 235, 'd', 17.6), (82, 320, 'e', 18.1)):
            a = ramp(t, show, show + 0.5) * k
            if a <= 0: continue
            d.ellipse((x - r_, y - r_, x + r_, y + r_), outline=(255, 255, 255, int(120 * a)), width=2)
            ang_ = math.radians(ang + 40 * (t - show))
            px, py = x + r_ * math.cos(ang_), y - r_ * math.sin(ang_)
            d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(170, 220, 255, int(255 * a)))
            d.text((px + 9, py - 9), nm, font=sky.font(8), anchor='lm', fill=(200, 230, 255, int(230 * a)))
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 150, 90, int(255 * k)))
    lay.alpha_composite(ov)
    return lay.convert('RGB')
