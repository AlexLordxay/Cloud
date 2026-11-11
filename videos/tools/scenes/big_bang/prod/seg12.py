# Segment 12 — К19 + К20 + К21 + the first supernova (3:17.5–3:59.8).
#   К19 «Але невидима темна матерія — її вп'ятеро більше, ніж звичайної, — уже стягувала газ у нитки»: in the dark, a
#       barely visible 3D web grows (Zel'dovich approximation: matter streaming into sheets, threads and knots);
#   К20 «Через сто — двісті мільйонів років у темряві спалахнула перша зоря»: in a knot the gas gathers and glows dark
#       red… and on «спалахнула» — the blinding blue-white flash of the first star; its light picks out the threads;
#   К21 «Лише з водню й гелію, у десятки, а може, й сотні разів важча за Сонце»: the star close, a tiny yellow Sun for
#       scale (radius ~1/10 — a model; «Таких зір ще ніхто не бачив напряму» — a small note);
#   «Вони жили лише кілька мільйонів років — і вибухали»: the star blows up — a white flash (seg13 continues).
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, web
from noise2 import fbm_grid

T0, T1 = 197.5, 240.2
p60 = fx.phrase('Через сто')
FLASH = p60[0] + (p60[1] - p60[0]) * 15 / 21          # «спалахнула»
NOTE = fx.phrase('Таких зір')[0]
BOOM = fx.phrase('і вибухали')[0] + 0.15
_rng = np.random.default_rng(12)
_P = {}


def D_at(T): return 0.5 + 1.3 * fx.smooth((T - 199.0) / 15.0)


def parts(T):
    D = round(D_at(T), 3)
    if D not in _P:
        if len(_P) > 4: _P.clear()
        _P[D] = web.positions(D)
    return _P[D]


NODE = None


def node():
    global NODE
    if NODE is None: NODE = web.densest(web.positions(1.8))
    return NODE


def camera(T):
    n = node()
    k = fx.smoother((T - 199.0) / (FLASH + 3.0 - 199.0))
    dist = 55.0 * (1 - k) + 20.0 * k
    dist *= 1 - 0.55 * fx.smoother((T - (FLASH + 1.0)) / 8.0)      # К21: closer to the star
    yaw = 0.9 + 0.035 * (T - T0)
    pitch = 0.25 + 0.05 * math.sin(0.05 * (T - T0))
    cam = n + dist * np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)])
    return cam, n


def frame(T):
    W, H = fx.W, fx.H
    P = parts(T)
    cam, n = camera(T)
    fw, rt, up = web.look(cam, n, 0.05 * math.sin(0.1 * T))
    vis = fx.ramp(T, 200.4, 205.0)
    # the dark matter: faint blue threads
    lit = 0.0
    w = np.float32(1.0)
    if T > FLASH - 0.05:                                         # the star's light picks out the threads near it
        lit = fx.ramp(T, FLASH - 0.05, FLASH + 0.4) * (1 - 0.6 * fx.ramp(T, BOOM, BOOM + 0.6))
        r2 = ((P - n + web.L / 2) % web.L - web.L / 2) ** 2
        w = (1.0 + 2.5 * lit / (1.0 + r2.sum(-1) / 9.0)).astype(np.float32)
    dist = float(np.linalg.norm(cam - n))
    fog = 22.0 + 48.0 * min(max((dist - 8.0) / 47.0, 0.0), 1.0)
    norm = 0.22 + 0.27 * min(max((dist - 8.0) / 47.0, 0.0), 1.0)
    buf = web.splat(P, w, cam, fw, rt, up, W, H, fog=fog)
    buf = cv2.GaussianBlur(buf, (0, 0), 2.0)
    buf = (0.20 + 0.12 * lit) * vis * np.clip(buf / norm, 0, 40) ** 2.0             # contrast: the threads over the thin field
    img = cv2.resize(buf, (W, H))[..., None] * np.array([0.45, 0.6, 1.0], np.float32)
    # the knot: gas gathering, glowing dark red, then the flash and the star
    rel = n - cam; z = rel @ fw
    f = (H / 2) / math.tan(math.radians(30))
    sx, sy = W / 2 + (rel @ rt) / z * f, H / 2 - (rel @ up) / z * f
    yy, xx = np.ogrid[0:H, 0:W]
    d2 = (xx - sx) ** 2 + (yy - sy) ** 2
    g = fx.ramp(T, 211.0, FLASH) * (1 - fx.ramp(T, FLASH, FLASH + 0.6))
    if g > 0:
        rg = 70 * (1 - 0.6 * g)
        img += (np.exp(-d2 / (2 * rg * rg)) * 0.9 * g).astype(np.float32)[..., None] * np.array([1.0, 0.30, 0.10], np.float32)
    if T >= FLASH:
        k = T - FLASH
        flash = 14.0 * math.exp(-k / 0.5) + 0.0
        Rs = 6 + 150 * fx.smoother((T - (FLASH + 1.0)) / 8.0)       # the star's disc (px)
        rr = np.sqrt(d2) / max(Rs, 1)
        disc = np.clip(1 - rr, 0, 1)
        limb = np.sqrt(disc)                                         # limb darkening
        star = (limb * 3.2 + np.exp(-d2 / (2 * (Rs * 1.3) ** 2)) * 0.35 + flash * np.exp(-d2 / (2 * 40 ** 2)))
        boom = fx.ramp(T, BOOM, BOOM + 0.7)
        star = star * (1 - boom) + boom * 9.0 * np.exp(-d2 / (2 * (Rs * (1.5 + 30 * boom)) ** 2))
        img += star.astype(np.float32)[..., None] * np.array([0.78, 0.86, 1.0], np.float32)
        sun_a = fx.ramp(T, FLASH + 3.0, FLASH + 4.5) * (1 - fx.ramp(T, BOOM - 1.5, BOOM - 0.5))
        if sun_a > 0:                                                # the Sun, for scale
            ux, uy = sx + Rs * 2.4, sy + Rs * 0.4
            du = np.sqrt((xx - ux) ** 2 + (yy - uy) ** 2) / max(Rs / 10.0, 1.0)
            img += (np.sqrt(np.clip(1 - du, 0, 1)) * 2.4 * sun_a).astype(np.float32)[..., None] * np.array([1.0, 0.82, 0.5], np.float32)
    out = fx.finish(img, _rng, exposure=1.0, thr=0.9, bk=0.6, vig=0.28, grain=0.012).astype(np.float32) / 255
    items = []
    if T >= FLASH:
        Rs = 6 + 150 * fx.smoother((T - (FLASH + 1.0)) / 8.0)
        sun_a = fx.ramp(T, FLASH + 3.6, FLASH + 4.6) * (1 - fx.ramp(T, BOOM - 1.5, BOOM - 0.5))
        items.append((sx + Rs * 2.4, sy + Rs * 0.4 + Rs / 10 + 14, 'Сонце', 26, sun_a * 0.8, fx.FONT_L, 'mt'))
        na = fx.ramp(T, NOTE, NOTE + 0.8) * (1 - fx.ramp(T, BOOM - 1.5, BOOM - 0.5))
        items.append((W / 2, H - 70, 'модель: такі зорі ще не спостерігали напряму', 24, na * 0.6, fx.FONT_L, 'mm'))
    if items:
        m = fx.text_mask(items)
        out = out * (1 - m[..., None]) + m[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
