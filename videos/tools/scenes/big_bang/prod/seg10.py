# Segment 10 — К16 + К16б (2:43.4–3:00.2).
#   К16 «Його випадково знайшли в шістдесят п'ятому році: двоє радіоастрономів спершу думали, що в антені шумить голубиний
#       послід. А отримали за це Нобелівську премію»: the real Holmdel Horn Antenna (NASA) — a slow push in;
#   К16б «І частину „снігу“ на старому телевізорі без сигналу ти бачив сам»: the static of an old cathode-ray screen — the
#       curved glass, the scan lines, the flicker; then the snow dissolves into the dark (К17's 2 s of silence).
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx

T0, T1 = 163.4, 180.2
TV0 = fx.phrase('І частину')[0] - 0.4
TV1 = fx.phrase('І частину')[1] + 0.6
_rng = np.random.default_rng(10)
_yy, _xx = np.mgrid[0:fx.H, 0:fx.W].astype(np.float32)
_u = (_xx - fx.W / 2) / (fx.W / 2); _v = (_yy - fx.H / 2) / (fx.H / 2)
_r2 = _u * _u + _v * _v
# barrel distortion of the tube and its rounded corners
_mx = (fx.W / 2 + _u * (1 + 0.06 * _r2) * fx.W / 2 * 0.96).astype(np.float32)
_my = (fx.H / 2 + _v * (1 + 0.06 * _r2) * fx.H / 2 * 0.96).astype(np.float32)
_mask = (np.clip((1.0 - np.maximum(np.abs(_u * 1.02) ** 8 + np.abs(_v * 1.03) ** 8, 0)) / 0.08, 0, 1)).astype(np.float32)


def snow(T):
    W, H = fx.W, fx.H
    n = _rng.random((H // 3, W // 3), dtype=np.float32) ** 1.4
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_NEAREST)
    n = cv2.GaussianBlur(n, (0, 0), 0.9)
    lines = 0.82 + 0.18 * np.sin(_yy * math.pi / 2.0)                 # scan lines
    roll = 0.9 + 0.1 * np.sin((_yy / H + T * 0.7) * 2 * math.pi)       # a slow brightness roll
    img = n * lines * roll
    img = cv2.remap(img, _mx, _my, cv2.INTER_LINEAR, borderValue=0) * _mask
    glass = np.exp(-((_u + 0.35) ** 2 + (_v + 0.45) ** 2) / 0.08) * 0.08   # a faint reflection on the glass
    out = (img * 0.55 + glass)[..., None] * np.array([0.92, 0.96, 1.0], np.float32)
    return out * (1 - 0.35 * _r2[..., None])


def frame(T):
    W, H = fx.W, fx.H
    img = np.zeros((H, W, 3), np.float32)
    aA = 1 - fx.ramp(T, TV0, TV0 + 1.2)
    aT = fx.ramp(T, TV0, TV0 + 1.2) * (1 - fx.ramp(T, TV1 - 0.6, TV1 + 0.2))
    if aA > 0:
        im = fx.load('holmdel_horn.jpg', 4000)
        h, w = im.shape[:2]
        sc = max(W / w, H / h) * (1.04 + 0.012 * (T - T0))
        img += fx.warp(im, w * 0.5, h * 0.5, sc) * (1.0 * aA)
    if aT > 0:
        img += snow(T) * aT
    return fx.finish(img, _rng, exposure=1.0, thr=0.85, bk=0.5, vig=0.28, grain=0.012)
