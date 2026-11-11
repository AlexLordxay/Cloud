# Segment 11 — К17 + К18 (2:59.4–3:21.2).
#   К17 ВАУ №3: 2 s of silence, then the real map of the oldest light — the Planck 2018 SMICA CMB map (ESA/Planck
#       Collaboration; data via NASA/IPAC IRSA) — on a SPHERE (the sky all around us), turning slowly
#       («Ось так це світло бачить телескоп „Планк“»); a thin scale «−0,0003 °C … +0,0003 °C» («Різниця між плямами —
#       менше за тисячну частку градуса»); the camera closes in on the spots («Саме з них виросли всі галактики»).
#   К18 (Act 4, «А далі — темрява»): the map reddens and dies out into black.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, sphere

T0, T1 = 179.4, 201.2
SCALE_AT = fx.phrase('Різниця між плямами')[0]
GROW_AT = fx.phrase('Саме з них')[0]
DARK0, DARK1 = fx.shot('К18')[0], fx.shot('К18')[0] + 5.5
_rng = np.random.default_rng(11)
_tex = None


def planck_colours(T):
    """the Planck colour scale: dark blue - blue - white - orange - red - dark red, over ±300 µK"""
    k = np.clip((T + 300.0) / 600.0, 0, 1)
    stops = np.array([0.0, 0.18, 0.36, 0.5, 0.64, 0.82, 1.0])
    cols = np.array([[0.00, 0.02, 0.25], [0.02, 0.25, 0.85], [0.45, 0.75, 1.0], [0.95, 0.95, 0.88],
                     [1.0, 0.62, 0.20], [0.85, 0.15, 0.05], [0.35, 0.02, 0.02]], np.float32)
    out = np.empty(k.shape + (3,), np.float32)
    for c in range(3): out[..., c] = np.interp(k, stops, cols[:, c])
    return out ** 2.2


def texture():
    global _tex
    if _tex is None:
        m = np.load(os.path.join(fx.ASSETS, 'planck_cmb_equirect.npy'))
        m = cv2.resize(m, (4096, 2048), interpolation=cv2.INTER_AREA)
        _tex = planck_colours(m).astype(np.float32)
    return _tex


def frame(T):
    W, H = fx.W, fx.H
    t = T - T0
    appear = fx.ramp(T, T0 + 1.6, T0 + 4.0)
    R = 380 + 22 * t + 1400 * fx.smoother((T - GROW_AT) / (DARK0 + 2.0 - GROW_AT))
    cx, cy = W / 2, H / 2 + 10
    M = sphere.rot(0.10 * t + 0.6, 0.35 + 0.02 * t, 0.15)
    img, al = sphere.draw(texture(), W, H, cx, cy, R, M, limb=0.35)
    # a soft glow round the sphere (its light)
    halo = cv2.GaussianBlur(al, (0, 0), 24) * 0.06
    img = img * 0.62 + halo[..., None] * np.array([0.7, 0.75, 0.9], np.float32)
    # К18: the light cools out of sight — redden, then dark
    d = fx.ramp(T, DARK0, DARK1)
    if d > 0:
        lum = img.mean(-1, keepdims=True)
        img = img * (1 - d) + lum * np.array([1.0, 0.25, 0.08], np.float32) * (1 - d) ** 2 * d * 2
    img *= appear
    out = fx.finish(img, _rng, exposure=1.0, thr=0.9, vig=0.24, grain=0.011).astype(np.float32) / 255
    sa = fx.ramp(T, SCALE_AT, SCALE_AT + 0.8) * (1 - fx.ramp(T, GROW_AT + 1.0, GROW_AT + 1.8))
    if sa > 0:                                          # the colour scale
        x0, x1, yb = int(W / 2 - 300), int(W / 2 + 300), 64
        bar = planck_colours(np.linspace(-300, 300, x1 - x0)[None, :].repeat(10, 0)) ** (1 / 2.2)
        out[yb:yb + 10, x0:x1] = out[yb:yb + 10, x0:x1] * (1 - sa) + bar * sa
        m = fx.text_mask([(x0 - 16, yb + 5, '−0,0003 °C', 26, sa * 0.85, fx.FONT_L, 'rm'),
                          (x1 + 16, yb + 5, '+0,0003 °C', 26, sa * 0.85, fx.FONT_L, 'lm')])
        out = out * (1 - m[..., None]) + m[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
