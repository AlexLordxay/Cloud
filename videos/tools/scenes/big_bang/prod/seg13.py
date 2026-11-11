# Segment 13 — К22 + К23 (3:59.4–4:24.2), real telescopes.
#   К22 «І саме в цих вибухах уперше з'явилися вуглець, кисень і залізо. Кожна зоря — це кухня, де вариться таблиця
#       Менделєєва»: out of the supernova's white — Cassiopeia A, a real supernova remnant: JWST (NASA/ESA/CSA/STScI),
#       then Chandra's map of its elements (NASA/CXC/SAO) — not a drawing: this is how the elements are seen.
#   К23 «Найдавніша галактика, яку бачив телескоп „Вебб“… А ця червона цятка — попередня рекордсменка»: the JWST JADES
#       deep field; a slow approach through thousands of galaxies to the tiny red dot JADES-GS-z14-0, a thin frame and
#       «290 млн років після початку».
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx

T0, T1 = 239.4, 264.2
ELEM = fx.phrase('кисень і залізо')[0] - 0.3
JADES0 = fx.phrase('Кожна зоря')[1] + 0.2
DOT = fx.phrase('А ця червона')[0]
TGT = (4808.0, 3629.0)                 # JADES-GS-z14-0 in jades_field.jpg (from the release's annotated image)
_rng = np.random.default_rng(13)


def casA(T, name, maxd, gain):
    im = fx.load(name, maxd)
    h, w = im.shape[:2]
    sc = 1.08 * max(fx.W / w, fx.H / h) * (1 + 0.012 * (T - T0))
    return fx.warp(im, w / 2 + 0.006 * w * (T - T0), h / 2, sc) * gain


def frame(T):
    W, H = fx.W, fx.H
    img = np.zeros((H, W, 3), np.float32)
    a_webb = 1 - fx.ramp(T, ELEM, ELEM + 1.6)
    a_el = fx.ramp(T, ELEM, ELEM + 1.6) * (1 - fx.ramp(T, JADES0, JADES0 + 1.6))
    if a_webb > 0: img += casA(T, 'casA_webb.jpg', 3000, 1.1) * a_webb
    if a_el > 0: img += casA(T, 'casA_chandra.jpg', 3000, 1.15) * a_el
    a_j = fx.ramp(T, JADES0, JADES0 + 1.6)
    zf = 0.0
    if a_j > 0:
        im = fx.load('jades_field.jpg', 8000)
        h, w = im.shape[:2]
        # from the whole field to the dot: log-zoom, the centre glides onto the target
        k = fx.smoother((T - (JADES0 + 0.5)) / (DOT + 1.2 - (JADES0 + 0.5)))
        s0 = max(W / w, H / h) * 1.25; s1 = 9.0
        sc = math.exp(math.log(s0) * (1 - k) + math.log(s1) * k)
        cx = w / 2 + (TGT[0] - w / 2) * min(1.0, k * 1.6); cy = h / 2 + (TGT[1] - h / 2) * min(1.0, k * 1.6)
        img = img * (1 - a_j) + fx.warp(im, cx, cy, sc) * (1.25 * a_j)
        zf = k
        tx, ty = W / 2 + (TGT[0] - cx) * sc, H / 2 + (TGT[1] - cy) * sc
    wht = 1 - fx.ramp(T, T0, T0 + 1.4)
    img = img + wht * 7.0
    out = fx.finish(img, _rng, exposure=1.0, thr=0.8, bk=0.6, vig=0.24, grain=0.010).astype(np.float32) / 255
    items = []
    ca = fx.ramp(T, T0 + 1.5, T0 + 2.5) * (1 - fx.ramp(T, JADES0, JADES0 + 1.0))
    items.append((70, H - 64, 'Кассіопея A — залишок наднової («Вебб», «Чандра»)', 24, ca * 0.65, fx.FONT_L, 'lm'))
    ja = fx.ramp(T, JADES0 + 1.0, JADES0 + 2.0) * (1 - fx.ramp(T, T1 - 1.0, T1))
    items.append((70, H - 64, 'Глибоке поле JADES — «Вебб»', 24, ja * 0.65, fx.FONT_L, 'lm'))
    da = fx.ramp(T, DOT, DOT + 0.7) * (1 - fx.ramp(T, T1 - 0.8, T1))
    m = fx.text_mask(items + ([(tx, ty + 70, '290 млн років після початку', 30, da * 0.9, fx.FONT_L, 'mt')] if a_j > 0 else []))
    if da > 0 and a_j > 0:                              # a thin frame round the dot
        r = 46
        x0, x1, y0, y1 = int(tx - r), int(tx + r), int(ty - r), int(ty + r)
        for (xa, ya, xb, yb) in ((x0, y0, x1, y0 + 2), (x0, y1 - 2, x1, y1), (x0, y0, x0 + 2, y1), (x1 - 2, y0, x1, y1)):
            m[max(ya, 0):max(yb, 0), max(xa, 0):max(xb, 0)] = np.maximum(m[max(ya, 0):max(yb, 0), max(xa, 0):max(xb, 0)], 0.8 * da)
    out = out * (1 - m[..., None]) + m[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
