# «Ти Скорпіон?» — the camera, the Sun, Antares and its supernova as functions of the video time t (s). The helpers
# (easing, camera glide, dates) come from the 13th-sign scene, which this one is built on.
import importlib.util, math, os, datetime
import numpy as np
from sky import ecl, vec, slerp, Sky

_s = importlib.util.spec_from_file_location('z13', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zodiac13', 'timeline.py'))
Z = importlib.util.module_from_spec(_s); _s.loader.exec_module(Z)
ease, ramp, win, date_of, sun_lon = Z.ease, Z.ramp, Z.win, Z.date_of, Z.sun_lon

ANTARES = vec(247.352, -26.432)
SCO = vec(250.0, -28.0)
LOW = vec(250.0, -17.0)                           # the summer view from Ukraine: Scorpius low over the south horizon
L23, L29 = sun_lon(datetime.datetime(2026, 11, 23, 12)), sun_lon(datetime.datetime(2026, 11, 29, 12))

KEYS = [(0.0, SCO, 620, 0), (10.2, SCO, 680, 0), (12.6, ANTARES, 1800, 0), (18.3, ANTARES, 2000, 0),
        (28.2, ANTARES, 2100, 0), (30.0, ANTARES, 1300, 0), (34.4, ANTARES, 1250, 0), (36.4, LOW, 520, 0), (39.0, LOW, 525, 0), (40.9, SCO, 600, 0), (44.4, SCO, 620, 0), (46.3, LOW, 530, 0), (56.6, LOW, 550, 0)]

def camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

SUN_KEYS = [(1.0, L23 - 4), (4.6, L23), (9.8, L29), (10.6, L29 + 0.6)]

def sun(t):
    lam = SUN_KEYS[0][1] if t < SUN_KEYS[0][0] else SUN_KEYS[-1][1]
    for (t0, l0), (t1, l1) in zip(SUN_KEYS, SUN_KEYS[1:]):
        if t0 <= t <= t1: lam = l0 + (l1 - l0) * ease((t - t0) / (t1 - t0)); break
    if t > 30: return 245.0, win(t, 39.5, 45.0, 0.8)          # the fact: on your birthday the Sun sits by Scorpius
    return lam, win(t, 1.2, 10.6, 0.5)

def sectors(t):
    return 0.0, 0.0

def view(t):
    c, s, r = camera(t)
    lam, sk = sun(t)
    hi = max(win(t, 1.0, 10.6, 0.6), ramp(t, 35.5, 37.0))
    glow = []
    red = win(t, 10.4, 34.4, 0.8)
    if red > 0: glow.append((ANTARES, 30, (255, 90, 40), 0.5 * red))
    if 30.8 < t < 35.5:                          # «колись вибухне»: a flash brighter than everything round it
        k = min(1.0, (t - 31.0) / 0.5) * win(t, 30.8, 35.4, 0.8)
        glow += [(ANTARES, 80, (255, 220, 190), 0.7 * k), (ANTARES, 20, (255, 245, 235), 2.4 * k), (ANTARES, 6, (255, 255, 255), 4.0 * k)]
    day = win(t, 39.5, 45.0, 0.8)
    if day > 0: glow.append((ecl(245.0), 330, (90, 130, 200), 0.9 * day))   # daylight round the Sun washes the stars out
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 * win(t, -1, 11.0, 0.6), hi={'Sco': hi}, borders={'Sco': hi, 'Oph': 0.5 * hi},
                zlines=0.8, lines=0.25, labels=1.0, sun=lam, sun_k=sk, sun_r=18 + 14 * day, label_size=20, glow=glow, clip_rho=2.0)
