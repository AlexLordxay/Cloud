# «Є 13-й знак зодіаку» — everything that moves, as functions of the video time t (s): the camera over the sky, the Sun
# on the ecliptic, highlights, the Babylonian sectors, the supernova. Shared by frames.py (the picture) and captions.py.
import math, datetime
import numpy as np
from sky import ecl, vec, slerp, ECL_POLE

def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)

def ramp(t, a, b):
    return ease((t - a) / (b - a))

def win(t, a, b, d=0.5):
    return ease(min((t - a) / d, (b - t) / d))

OPH = slerp(vec(257.0, -6.0), ecl(256.0), 0.45)   # Ophiuchus with a bit of the ecliptic in the frame
SCO = ecl(244.0, -3.0)
SN = vec(262.675, -21.48)                         # Kepler's supernova, 1604
POLE = ECL_POLE

# camera keys: (t, centre, scale px/rad at 720 wide, roll deg); between keys it glides (slerp + log scale, eased)
KEYS = [(0.0, POLE, 150, 0), (8.9, POLE, 160, 22), (13.6, OPH, 930, 22), (21.6, OPH, 1000, 22), (23.6, SCO, 1100, 22),
        (26.6, POLE, 160, 22), (41.2, POLE, 165, 10), (44.0, SN, 1050, 10), (52.6, SN, 1150, 10),
        (55.0, OPH, 950, 22), (70.0, OPH, 1050, 22)]

def camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

# the Sun: (t, ecliptic longitude) keys, and when it shows
SUN_KEYS = [(3.0, -30.0), (8.4, 232.0), (13.6, 252.0), (14.6, 247.6), (21.6, 265.0), (22.4, 241.0), (24.0, 247.6),
            (54.6, 247.6), (58.0, 265.0)]
SUN_SHOW = [(2.6, 24.6), (53.0, 99)]

def sun(t):
    lam = SUN_KEYS[0][1] if t < SUN_KEYS[0][0] else SUN_KEYS[-1][1]
    for (t0, l0), (t1, l1) in zip(SUN_KEYS, SUN_KEYS[1:]):
        if t0 <= t <= t1:
            lam = l0 + (l1 - l0) * ease((t - t0) / (t1 - t0)) if l1 > l0 else (l0 if t < t1 - 0.4 else l1); break
    k = max(win(t, a, b, 0.5) for a, b in SUN_SHOW)
    if 21.6 < t < 22.4: k *= abs(t - 22.0) / 0.4     # a blink while it jumps back into Scorpius
    return lam % 360, k

# the Sun's ecliptic longitude -> the date (2026)
def sun_lon(d):
    n = (d - datetime.datetime(2000, 1, 1, 12)).total_seconds() / 86400
    L, g = 280.460 + 0.9856474 * n, math.radians(357.528 + 0.9856003 * n)
    return (L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360

_DATES = [(sun_lon(datetime.datetime(2026, 1, 1) + datetime.timedelta(days=i)), datetime.date(2026, 1, 1) + datetime.timedelta(days=i)) for i in range(365)]
MONTHS = ['січня', 'лютого', 'березня', 'квітня', 'травня', 'червня', 'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня']

def date_of(lam):
    best = min(_DATES, key=lambda p: abs((p[0] - lam + 180) % 360 - 180))[1]
    return f'{best.day} {MONTHS[best.month - 1]}'

# the 12 equal Babylonian signs, 30° each: drawn aligned with the constellations, then the Earth's axis turns them away
SIGNS = ['Овен', 'Телець', 'Близнята', 'Рак', 'Лев', 'Діва', 'Терези', 'Скорпіон', 'Стрілець', 'Козеріг', 'Водолій', 'Риби']

def sectors(t):
    """(opacity, offset deg): the sign borders lie at offset + 30·k of ecliptic longitude"""
    return win(t, 27.0, 41.6, 0.8), 28.0 - 28.0 * ramp(t, 35.6, 40.6)

def view(t):
    c, s, r = camera(t)
    lam, sk = sun(t)
    oph = max(ramp(t, 9.5, 11.5) * (1 - ramp(t, 24.4, 25.6)), ramp(t, 53.0, 55.0))
    sec, _ = sectors(t)
    labels = 1 - sec
    zl = {'Oph': ramp(t, 0.9, 1.6) * labels}
    sn_t = t - 44.2
    glow = []
    if 43.0 < t < 53.5:
        k = (min(1.0, (t - 43.6) / 0.6) if t < 44.2 else math.exp(-max(0.0, sn_t) / 5.0)) * win(t, 43.0, 53.3, 0.6)
        glow = [(SN, 90, (180, 210, 255), 0.6 * k), (SN, 24, (220, 236, 255), 2.2 * k), (SN, 6, (255, 255, 255), 4.0 * k)]
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 if sec < 0.5 else 0.7 + 0.3 * sec, hi={'Oph': oph},
                borders={'Oph': oph, 'Sco': win(t, 14.4, 24.4, 0.6)}, zlines=0.8, lines=0.25, labels=labels, zlabel=zl,
                sun=lam, sun_k=sk, sun_r=18, label_size=20, glow=glow, clip_rho=2.0)
