# Segment 5 — К6, ВАУ №1 (0:43.4–1:00.6): inflation.
#   «Простір роздувся щонайменше в сто мільярдів мільярдів мільярдів разів»: the hydrogen atom (from seg04) in the
#     middle; the foam around it starts to stream outwards, faster and faster — space itself swelling;
#   «Уяви: атом за одне клацання пальцями виріс до світлового року»: the atom keeps its place on screen while the
#     world shrinks past it — real photographs at their true sizes: a sand grain (0,5 mm), the Earth, the Sun — each
#     rushes in from bigger than the frame and vanishes into a dot inside the cloud — 26 orders of magnitude in ~4,5 s;
#   «Фізики називають це інфляцією» + 2 s pause: the cloud now a light-year across, stars inside it, a scale bar.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, k3
from noise2 import fbm_grid

T0, T1 = 43.4, 60.6
STATEFUL = True
SNAP0, SNAP1 = 50.15, 54.9            # the «click»: atom 1e-10 m -> 1 light-year
LA0, LA1 = -10.0, math.log10(9.4607e15)
ATOM_PX = 52.5                        # px per Bohr radius at the start (as seg04 ends)
OBJ = [  # name, asset, log10 size (m), label, x-offset in the cloud (px at its smallest)
    ('sand', 'sand_grain.jpg', math.log10(5e-4), 'піщинка · 0,5 мм'),
    ('earth', 'earth_bluemarble.jpg', math.log10(1.2742e7), 'Земля'),
    ('sun', 'sun_visible.jpg', math.log10(1.3927e9), 'Сонце'),
]
_atom = None
_rng = np.random.default_rng(5)
_disc = {}


from scipy.interpolate import PchipInterpolator
# the atom's size (log10 m) through the «click»: fast between the objects, slower while each one passes
_KEY = [(SNAP0, LA0), (50.85, -4.6), (51.55, -2.2), (51.95, 5.6), (52.65, 8.3), (53.05, 9.0), (53.75, 10.9),
        (54.3, 13.8), (SNAP1, LA1)]
_LS = PchipInterpolator([k[0] for k in _KEY], [k[1] for k in _KEY])


def logsize(T):
    return float(_LS(min(max(T, SNAP0), SNAP1)))


def disc_of(asset):
    """the object's centre and radius in its photo (bright object on dark) — found once"""
    if asset not in _disc:
        img = fx.load(asset, 2400)
        g = img.mean(-1)
        m = (g > max(0.02, np.percentile(g, 50) * 1.5)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))          # the largest object (one sand grain of many)
        ys, xs = np.nonzero(lab == big)
        cx, cy = xs.mean(), ys.mean()
        r = np.percentile(np.hypot(xs - cx, ys - cy), 97)
        _disc[asset] = (img, cx, cy, r)
    return _disc[asset]


def frame(T):
    global _atom
    if _atom is None: _atom = k3.Atom(np.random.default_rng(7))
    t = T - T0
    W, H = fx.W, fx.H
    img = np.zeros((H, W, 3), np.float32)
    L = logsize(T)
    grow = math.log10(ATOM_PX * 4.0) + fx.smooth((T - SNAP0 + 0.3) / 1.2) * math.log10(330 / (ATOM_PX * 4.0) * 1.0)
    atom_r_px = 10 ** grow                                  # the cloud's radius on screen (≈4 Bohr radii)
    ppm = atom_r_px / (10 ** L / 2)                         # screen px per metre (the atom = 10**L m across)
    # background: the foam streaming outwards (space swelling) before the click, the stars of the Galaxy after it
    pre = 1 - fx.ramp(T, SNAP0 - 0.3, SNAP0 + 0.6)
    if pre > 0:
        z = math.exp(0.10 * t + 0.9 * max(0.0, t - 2.0) ** 1.7 * 0.12)
        a = np.zeros((270, 480), np.float32)
        fbm_grid(a, -1.6 / z, -0.9 / z, 5.0 / 480 / z, 5.0 / 480 / z, 0.5 * t + 6.0, 5, 0.58, 2.1, 1, 0.9)
        th = np.clip((a - 0.62) / 0.22, 0, 1) ** 2.2 * 0.13 * pre * (0.35 + 0.65 * fx.ramp(T, T0, T0 + 1.0))
        th = cv2.resize(th, (W, H), interpolation=cv2.INTER_LINEAR)
        img += th[..., None] * np.array([0.55, 0.62, 1.0], np.float32)
    post = fx.ramp(T, SNAP1 - 1.2, SNAP1 + 0.4)
    if post > 0:
        mw = fx.load('milkyway_panorama.jpg', 6000)
        hh, ww = mw.shape[:2]
        sc = 1.25 * H / hh * (1 + 0.012 * (T - SNAP1))
        img += fx.warp(mw, ww * 0.38, hh * 0.5, sc) * (0.9 * post)
    # the objects, each at its true size relative to the atom
    labels = []
    for nm, asset, ls, lab in OBJ:
        rpx = ppm * 10 ** ls / 2
        if 2.0 < rpx < 2600:
            im, cx, cy, r = disc_of(asset)
            sc = rpx / r
            vis = fx.smooth((math.log10(rpx) - math.log10(2.0)) / 0.5) * fx.smooth((math.log10(2600) - math.log10(rpx)) / 0.35)
            lay = fx.warp(im, cx, cy, sc)
            if nm == 'sand':                                      # just the one grain (the photo shows 36 in a grid)
                lay *= fx.disc_mask(W / 2, H / 2, rpx * 1.3, 0.25)
            img = img * (1 - 0.92 * vis * fx.disc_mask(W / 2, H / 2, rpx * 1.02, 0.04)) + lay * vis
            if 25 < rpx < 900:
                al = fx.smooth((math.log10(rpx) - math.log10(25)) / 0.25) * fx.smooth((math.log10(900) - math.log10(rpx)) / 0.25)
                labels.append((W / 2, H / 2 + max(rpx, 30) + 18, lab, 30, al * 0.85, fx.FONT_L, 'mt'))
    # the atom's cloud — always the same on screen; by the end it is a light-year across
    _atom.step()
    a_al = 1.0 - 0.55 * post
    _atom.draw(img, W / 2, H / 2, atom_r_px / 4.0, a_al, t)
    out = fx.finish(img, _rng, exposure=1.0, thr=0.45, vig=0.28, grain=0.011).astype(np.float32) / 255
    al = fx.ramp(T, SNAP1 + 0.2, SNAP1 + 1.0) * (1 - fx.ramp(T, T1 - 0.9, T1 - 0.2))
    if al > 0:
        r = atom_r_px
        labels.append((W / 2, H / 2 + r + 34, '1 світловий рік', 30, al * 0.85, fx.FONT_L, 'mt'))
    m = fx.text_mask(labels)
    if al > 0:
        yb = int(H / 2 + atom_r_px + 18); x0, x1 = int(W / 2 - atom_r_px), int(W / 2 + atom_r_px)
        m[yb:yb + 2, x0:x1] = np.maximum(m[yb:yb + 2, x0:x1], 0.6 * al)
        for xx in (x0, x1 - 2): m[yb - 7:yb + 8, xx:xx + 2] = np.maximum(m[yb - 7:yb + 8, xx:xx + 2], 0.6 * al)
    out = out * (1 - m[..., None]) + m[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
