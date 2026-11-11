# Segment 14 — К24 + К25 + К25б + К26 (4:23.2–4:54.0).
#   К24 ВАУ №5 «А гравітація ткала далі — космічну павутину: нитки завдовжки в сотні мільйонів світлових років, а у
#       вузлах — галактики»: a far, slowly turning 3D cosmic web (Zel'dovich, the structure fully grown), warm points of
#       galaxies along the threads, knots glowing;
#   К25 «Одна з них — наш Чумацький Шлях»: into a knot… the real Milky Way from inside (ESO/S. Brunier panorama);
#   К25б «Він і досі росте: за свою історію він поглинув кілька менших галактик»: the Antennae — two galaxies merging
#       (NASA/ESA Hubble);
#   К26 «До нас наближається сусідка Андромеда. Ще недавно зіткнення вважали неминучим, а тепер науковці сперечаються»:
#       the real Andromeda galaxy, a slow approach, no graphics.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, web

T0, T1 = 263.2, 294.0
MW0 = fx.phrase('Одна з них')[0] - 0.4
ANT0 = fx.phrase('за свою історію')[0] - 0.6
AND0 = fx.phrase('До нас наближається')[0] - 0.8
_rng = np.random.default_rng(14)
_P = None
_W8 = None


def parts():
    global _P, _W8
    if _P is None:
        _P = web.positions(2.4, seed=5)
        r = np.random.default_rng(15)
        _W8 = np.exp(r.normal(0, 0.8, len(_P))).astype(np.float32)        # galaxies of all brightnesses
    return _P, _W8


def web_img(T):
    W, H = fx.W, fx.H
    P, w8 = parts()
    c = np.array([50.0, 50.0, 50.0])
    t = T - T0
    # inside the (periodic) web: a slow flight with a turning gaze; towards the end, into a knot
    cam = c + np.array([4.0 * math.sin(0.05 * t), 1.5 * math.sin(0.07 * t), -30.0 + 1.6 * t])
    tgt = cam + np.array([math.sin(0.25 + 0.02 * t) * 10, 3.0 - 0.05 * t, math.cos(0.25 + 0.02 * t) * 10])
    fw, rt, up = web.look(cam, tgt, 0.04 * math.sin(0.1 * t))
    buf = web.splat(P, w8, cam, fw, rt, up, W, H, fog=35.0, wrap=True)
    soft = cv2.GaussianBlur(buf, (0, 0), 2.2); sharp = cv2.GaussianBlur(buf, (0, 0), 0.6)
    L = 0.22 * np.clip(soft / 0.55, 0, 3) ** 2.4 + 0.13 * np.clip(sharp / 1.6, 0, 3) ** 1.5
    img = cv2.resize(L, (W, H))[..., None] * np.array([1.0, 0.86, 0.68], np.float32)
    return img


def photo(name, T, t0, maxd, z0=1.05, dz=0.015, gain=1.1, cx=0.5, cy=0.5):
    im = fx.load(name, maxd)
    h, w = im.shape[:2]
    sc = max(fx.W / w, fx.H / h) * (z0 + dz * (T - t0))
    return fx.warp(im, w * cx, h * cy, sc) * gain


def frame(T):
    a_web = 1 - fx.ramp(T, MW0, MW0 + 1.4)
    a_mw = fx.ramp(T, MW0, MW0 + 1.4) * (1 - fx.ramp(T, ANT0, ANT0 + 1.2))
    a_ant = fx.ramp(T, ANT0, ANT0 + 1.2) * (1 - fx.ramp(T, AND0, AND0 + 1.4))
    a_and = fx.ramp(T, AND0, AND0 + 1.4)
    img = np.zeros((fx.H, fx.W, 3), np.float32)
    if a_web > 0: img += web_img(T) * a_web * fx.ramp(T, T0, T0 + 1.2)
    if a_mw > 0:
        im = fx.load('milkyway_panorama.jpg', 6000)
        h, w = im.shape[:2]
        sc = fx.H / h * 1.9
        img += fx.warp(im, w * (0.42 + 0.004 * (T - MW0)), h * 0.5, sc) * (1.2 * a_mw)
    if a_ant > 0: img += photo('antennae.jpg', T, ANT0, 3900, 1.0, 0.02) * a_ant
    if a_and > 0 and os.path.exists(os.path.join(fx.ASSETS, 'andromeda.jpg')):
        img += photo('andromeda.jpg', T, AND0, 5000, 1.0, 0.012) * a_and
    return fx.finish(img, _rng, exposure=1.0, thr=0.75, bk=0.7, vig=0.26, grain=0.010)
