# Segment 2 — К3 + the start of К4 (0:08.27–0:22.0). Continues seg01's last frame (247) without a cut:
#   К3: the glowing space shrinks into a dazzling point («усе, що ти бачиш у небі»); beside it a hydrogen atom
#       emerges (the exact 1s cloud, k3.Atom) with «атом водню · 0,1 нм»;
#   К4 («І почало розтягуватися — одразу всюди»): the atom and the labels fade, the point returns to the centre,
#       «inhales» and blooms into light that fills the frame — seg03's flight dissolves in under the bloom.
import math, os, sys
import numpy as np
import cv2
from scipy import special
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, k3

T0, T1 = 248 / fx.FPS, 22.0
TB = 247 / fx.FPS                 # local time 0 = seg01's last frame
K4 = fx.shot('К4')[0] - TB         # local time К4 starts (11,5)
STATEFUL = True                   # the atom's shimmer: render frames in order
_atom = None
_tex = None
_rng = np.random.default_rng(3)


def texture():
    global _tex
    if _tex is None:
        t = fx.to_lin(np.asarray(Image.open(os.path.join(fx.BB, 'render', 'seg01', 'f_00247.jpg')).convert('RGB')))
        # extend the frame beyond its edges with a soft, blurred continuation of the haze (no hard frame edge, no
        # visible mirror seams) — the shrinking disc shows a little of it at the start of the pull-back
        H, W = t.shape[:2]
        ext = cv2.copyMakeBorder(t, H, H, W, W, cv2.BORDER_REFLECT)
        soft = cv2.GaussianBlur(ext, (0, 0), 45)
        m = np.zeros(ext.shape[:2], np.float32); m[H:2 * H, W:2 * W] = 1
        m = cv2.GaussianBlur(m, (0, 0), 40)[..., None]
        m[H + 60:2 * H - 60, W + 60:2 * W - 60] = 1
        _tex = (ext * m + soft * (1 - m)).astype(np.float32)
    return _tex


def layout(t):
    pull = 1.0 - 0.18 * fx.smooth((t - k3.A_IN0) / (k3.A_IN1 + 1.0 - k3.A_IN0))
    k = pull * (1.0 + 0.03 * t)                                   # a steady push in
    side = fx.smooth((t - (k3.A_IN0 - 0.4)) / 2.6) * (1 - fx.ramp(t, K4 + 0.1, K4 + 1.5))
    p = (fx.W / 2 - 250.0 * side * k + 14 * math.sin(0.4 * t), fx.H / 2 + 10 * math.sin(0.33 * t))
    a = (fx.W / 2 + 330.0 * k + 3 * math.sin(0.3 * t + 1), fx.H / 2 - 10 * k)
    return p, a, k


def frame(T):
    global _atom
    if _atom is None: _atom = k3.Atom(np.random.default_rng(5))
    t = T - TB
    H, W = fx.H, fx.W
    img = np.zeros((H, W, 3), np.float32)
    p, a, k = layout(t)
    # the pull-back (К3): seg01's last frame inside a disc that shrinks exponentially into the point
    if t < k3.PULL + 0.6:
        q = fx.smooth(t / k3.PULL) ** 1.4 if t < k3.PULL else 1.0
        # the texture's zoom starts at exactly 1 (seg01's last frame, no jump); the disc is a little larger
        zoom = math.exp(math.log(2.0 / (math.hypot(W, H) / 2)) * q)
        rad = 1.25 * zoom * math.hypot(W, H) / 2
        if rad > 2.6:
            boost = min((1.0 / max(zoom, 1e-3)) ** 0.55, 18.0)
            fade = 1.0 - fx.smooth((t - (k3.PULL - 0.5)) / 0.7)
            tx = texture()
            layer = fx.warp(tx, tx.shape[1] / 2, tx.shape[0] / 2, zoom, sx=p[0], sy=p[1])
            img += layer * fx.disc_mask(p[0], p[1], rad, 0.18) ** 1.5 * (boost * fade)
    # the point
    pw = 6.0 * fx.smooth((t - (k3.PULL - 0.6)) / 0.7) * (1.0 + 0.06 * math.sin(7.0 * t) + 0.04 * math.sin(11.3 * t))
    pw += 10.0 * math.exp(-((t - k3.PULL) / 0.35) ** 2)
    pw *= 1.0 + 1.5 * fx.ramp(t, K4 + 0.3, K4 + 0.8)                 # it «inhales»
    k3.glow_point(img, p[0], p[1], pw)
    # the bloom: light unfolding from the point and filling everything
    if t > K4 + 0.6:
        R = 4.0 * math.exp(5.2 * (t - (K4 + 0.6)))
        if R > 4:
            yy, xx = np.ogrid[0:H, 0:W]
            d = np.sqrt((xx - p[0]) ** 2 + (yy - p[1]) ** 2) / R
            light = (np.exp(-d * d * 1.6) * 3.2 + np.clip(1 - d, 0, 1) * 1.2).astype(np.float32)
            img += light[..., None] * np.array([1.0, 0.86, 0.62], np.float32)
    # the atom
    _atom.step()
    fadeout = 1 - fx.ramp(t, K4 - 0.1, K4 + 0.9)
    alpha = fx.smooth((t - k3.A_IN0) / (k3.A_IN1 - k3.A_IN0)) * fadeout
    if alpha > 0: _atom.draw(img, a[0], a[1], k3.A0 * k, alpha, 4.5 * t)      # (turns: 0,22 rad/s — its volume shows)
    out = fx.finish(img, _rng, exposure=1.0, thr=0.5, vig=0.25, grain=0.010).astype(np.float32) / 255
    # labels
    items = []
    al = fx.ramp(t, k3.P_LABEL, k3.P_LABEL + 0.7) * fadeout
    items.append((p[0], p[1] + 46, 'усе, що ти бачиш у небі', 30, al * 0.8, fx.FONT_L, 'mt'))
    al = fx.ramp(t, k3.A_LABEL, k3.A_LABEL + 0.7) * fadeout
    sc = k3.A0 * k; yb = a[1] + 4.7 * sc
    items.append((a[0], yb + 18, 'атом водню', 30, al * 0.8, fx.FONT_L, 'mt'))
    items.append((a[0], yb - 12, '0,1 нм', 24, al * 0.65, fx.FONT_L, 'mb'))
    m = fx.text_mask(items)
    if al > 0:                                                        # the scale bar (2 Bohr radii)
        x0, x1, yi = int(a[0] - sc), int(a[0] + sc), int(yb)
        m[yi:yi + 2, x0:x1] = np.maximum(m[yi:yi + 2, x0:x1], 0.66 * al)
        for xx in (x0, x1 - 2):
            m[yi - 7:yi + 8, xx:xx + 2] = np.maximum(m[yi - 7:yi + 8, xx:xx + 2], 0.66 * al)
    out = out * (1 - m[..., None]) + m[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
