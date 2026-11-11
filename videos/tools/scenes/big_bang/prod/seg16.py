# Segment 16 — К31 (Act 8, 5:32.6–5:49.2): «А Всесвіт розтягується й досі — і дедалі швидше. Далекі галактики вже тікають
# від нас швидше за світло. Законів фізики це не порушує: вони не летять крізь простір — росте сам простір.»
# One continuous pull-back, every layer real: the night side of the Earth (NASA Black Marble — Europe, Ukraine's
# lights) → the Milky Way around us (ESO panorama) → the deep field of galaxies (Hubble UDF) → the cosmic web → and the
# sphere of the oldest light (Planck) — the circle closes.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, web, sphere

T0, T1 = 332.6, 349.6
E = (332.6, 337.2); M = (336.4, 339.8); G = (339.0, 343.6); WB = (342.8, 346.8); PL = (346.0, 349.6)
UA = (4230.0, 1960.0)                 # Ukraine in earth_night.jpg (8192²)
_rng = np.random.default_rng(16)


def zoomout(t, a, b, s0, s1):
    k = (t - a) / (b - a)
    return math.exp(math.log(s0) * (1 - k) + math.log(s1) * k)


def frame(T):
    W, H = fx.W, fx.H
    img = np.zeros((H, W, 3), np.float32)
    aE = 1 - fx.ramp(T, M[0], E[1])
    aM = fx.ramp(T, M[0], E[1]) * (1 - fx.ramp(T, G[0], M[1]))
    aG = fx.ramp(T, G[0], M[1]) * (1 - fx.ramp(T, WB[0], G[1]))
    aW = fx.ramp(T, WB[0], G[1]) * (1 - fx.ramp(T, PL[0], WB[1]))
    aP = fx.ramp(T, PL[0], WB[1])
    if aE > 0:
        im = fx.load('earth_night.jpg', 8192)
        sc = zoomout(T, E[0], E[1] + 0.8, 0.9, 0.035)
        k = fx.smoother((T - E[0]) / (E[1] - E[0]))
        cx = UA[0] + (4096 - UA[0]) * k; cy = UA[1] + (4096 - UA[1]) * k
        img += fx.warp(im, cx, cy, sc) * (1.6 * aE)
    if aM > 0:
        im = fx.load('milkyway_panorama.jpg', 6000)
        img += fx.warp(im, im.shape[1] * 0.5, im.shape[0] * 0.5, fx.H / im.shape[0] * zoomout(T, M[0], M[1], 3.2, 1.05)) * (1.2 * aM)
    if aG > 0:
        im = fx.load('hudf.jpg', 6200)
        img += fx.warp(im, im.shape[1] * 0.5, im.shape[0] * 0.5, zoomout(T, G[0], G[1], 1.6, 0.22)) * (1.3 * aG)
    if aW > 0:
        from seg14 import parts
        P, w8 = parts()
        c = np.array([50.0, 50.0, 50.0])
        dist = 20 + 70 * fx.smoother((T - WB[0]) / (WB[1] - WB[0]))
        cam = c + np.array([0.3, 0.25, -1.0]) / np.linalg.norm([0.3, 0.25, -1.0]) * dist
        fw, rt, up = web.look(cam, c)
        buf = web.splat(P, w8, cam, fw, rt, up, W, H, fog=120.0, wrap=False)
        soft = cv2.GaussianBlur(buf, (0, 0), 2.0)
        L = 0.18 * np.clip(soft / (0.55 * (1 + dist / 40)), 0, 4) ** 2.0
        img += cv2.resize(L, (W, H))[..., None] * np.array([1.0, 0.86, 0.68], np.float32) * aW
    if aP > 0:
        from seg11 import texture
        R = zoomout(T, PL[0], PL[1], 1400, 300)
        s, al = sphere.draw(texture(), W, H, W / 2, H / 2, R, sphere.rot(0.2 + 0.08 * (T - PL[0]), 0.4, 0.15), limb=0.35)
        img = img * (1 - al[..., None] * aP) + s * (0.62 * aP)
    return fx.finish(img, _rng, exposure=1.0, thr=0.8, bk=0.6, vig=0.26, grain=0.010)
