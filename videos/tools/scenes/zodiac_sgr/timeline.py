# «Ти Стрілець?» — the camera, the Sun, the Teapot and the centre of the Galaxy as functions of the video time t (s).
# The helpers (easing, camera glide, dates) come from the 13th-sign scene, which this one is built on.
import importlib.util, math, os, datetime
from PIL import Image, ImageDraw
from sky import ecl, vec, slerp

_s = importlib.util.spec_from_file_location('z13', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'zodiac13', 'timeline.py'))
Z = importlib.util.module_from_spec(_s); _s.loader.exec_module(Z)
ease, ramp, win, date_of, sun_lon = Z.ease, Z.ramp, Z.win, Z.date_of, Z.sun_lon

SGR = vec(279.0, -27.5)                            # the Teapot in the middle of the frame
GC = vec(266.417, -29.008)                         # Sagittarius A*, the centre of the Galaxy
STEAM = vec(272.0, -22.0)                          # the Milky Way's bright star clouds rising over the spout
LOW = vec(278.0, -16.0)                            # the August evening from Ukraine: low over the south horizon
# the Teapot: γ² (Alnasl, the spout's tip), δ (Kaus Media), ε (Kaus Australis), λ (Kaus Borealis, the lid),
# φ, ζ (Ascella), σ (Nunki), τ — the spout, the body, the lid and the handle
TEA = {'g': vec(271.452, -30.424), 'd': vec(275.249, -29.828), 'e': vec(276.043, -34.384), 'l': vec(276.993, -25.421),
       'p': vec(281.414, -26.991), 'z': vec(285.653, -29.880), 's': vec(283.816, -26.297), 't': vec(286.735, -27.670)}
TEA_LINES = ['gd', 'de', 'eg', 'dl', 'lp', 'pd', 'pz', 'ze', 'ps', 'st', 'tz']
L_DEC18, L_JAN19 = sun_lon(datetime.datetime(2026, 12, 18, 12)), sun_lon(datetime.datetime(2027, 1, 19, 12))

KEYS = [(0.0, SGR, 640, 0), (5.4, SGR, 600, 0), (11.0, SGR, 600, 0), (12.4, SGR, 900, 0), (15.0, SGR, 920, 0),
        (17.0, STEAM, 620, 0), (18.8, STEAM, 610, 0), (20.4, LOW, 520, 0), (23.9, LOW, 530, 0),
        (26.6, GC, 900, 0), (31.0, GC, 1500, 0), (36.4, GC, 1650, 0), (38.0, SGR, 640, 0), (45.2, SGR, 660, 0)]

def camera(t):
    for (t0, c0, s0, r0), (t1, c1, s1, r1) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            k = ease((t - t0) / (t1 - t0))
            return slerp(c0, c1, k), math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * k), r0 + (r1 - r0) * k
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3]

def sun(t):           # 18 December -> 19 January through the Archer
    return L_DEC18 + (L_JAN19 - L_DEC18) * ease((t - 6.0) / 4.8), win(t, 5.6, 11.2, 0.5)

def sectors(t):
    return 0.0, 0.0

def view(t):
    c, s, r = camera(t)
    lam, sk = sun(t)
    hi = max(win(t, -1, 11.2, 0.6), win(t, 19.0, 24.2, 0.6), ramp(t, 37.6, 39.0))
    glow = []
    steam = win(t, 15.0, 19.0, 0.8)                 # «як пара — Чумацький Шлях»
    if steam > 0: glow.append((STEAM, 150, (230, 220, 255), 0.35 * steam))
    core = win(t, 24.3, 37.0, 0.8)                  # the fact: the centre of the Galaxy, a black hole of 4 million Suns
    if core > 0: glow += [(GC, 90, (255, 200, 140), 0.16 * core), (GC, 14, (255, 235, 210), 0.5 * core)]
    return dict(centre=c, scale=s, roll=r, ecliptic=0.7 * win(t, -1, 11.4, 0.6), hi={'Sgr': hi}, borders={'Sgr': hi, 'Oph': 0.3 * hi},
                zlines=0.8, lines=0.25, labels=1.0, sun=lam, sun_k=sk, sun_r=18, label_size=20, glow=glow, clip_rho=2.0)

def _pt(P, v):
    x, y, ok = P(v)
    return float(x[0]) / 2, float(y[0]) / 2, bool(ok[0])

def overlay(img, P, t, sky):
    lay = img.convert('RGBA'); ov = Image.new('RGBA', lay.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    # the Teapot drawn over its stars, gold, while the voice names it
    k = win(t, 11.3, 18.9, 0.5)
    if k > 0:
        pts = {n: _pt(P, v_) for n, v_ in TEA.items()}
        for a_, b_ in TEA_LINES:
            (x0, y0, _), (x1, y1, _) = pts[a_], pts[b_]
            d.line((x0, y0, x1, y1), fill=(255, 210, 120, int(230 * k)), width=4)
        for x, y, _ in pts.values():
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 236, 190, int(255 * k)))
    # the centre of the Galaxy: a ring round Sagittarius A*
    k = win(t, 25.0, 37.0, 0.6)
    if k > 0:
        x, y, _ = _pt(P, GC); R = 22 + 10 * (1 - ramp(t, 25.0, 26.0))
        d.ellipse((x - R, y - R, x + R, y + R), outline=(255, 220, 160, int(255 * k)), width=3)
        d.text((x + R + 10, y), 'Стрілець A*', font=sky.font(11), anchor='lm', fill=(255, 230, 190, int(255 * k)))
    lay.alpha_composite(ov)
    return lay.convert('RGB')
