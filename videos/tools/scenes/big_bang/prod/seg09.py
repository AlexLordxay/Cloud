# Segment 9 — К13 + К14 + К15 (2:08.6–2:44.0), the first light.
#   К13 «Триста вісімдесят тисяч років Всесвіт був схожий на розпечений туман: світло не могло летіти прямо — щойно
#       рушить, і вдаряється в електрон»: inside a glowing orange fog (3000 °C, the colour of a lamp's filament),
#       layers drifting past; one ray of light zigzags — scattered again and again, going nowhere;
#   К14 «А потім він охолов до трьох тисяч градусів — як спіраль у лампочці»: a real photograph of a glowing filament
#       of the same colour; «З'явилися перші атоми — і туман розвіявся. Світло вирвалося на волю»: the fog thins away
#       and the rays shoot off straight;
#   К15 «Це найстаріше світло… охололо до мінус двохсот сімдесяти градусів»: the light that is left everywhere cools —
#       orange → red → deep red → dark (it slips into the infrared, then radio).
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx
from noise2 import fbm_grid

T0, T1 = 128.6, 164.0
LAMP0, LAMP1 = fx.phrase('А потім він охолов')[0] + 2.4, fx.phrase("З'явилися перші атоми")[0] + 0.6
CLEAR0, CLEAR1 = fx.phrase("З'явилися перші атоми")[0] + 0.8, fx.phrase('і туман розвіявся')[1]
COOL0, COOL1 = fx.phrase('Це найстаріше світло')[0] - 0.5, fx.phrase('Воно летить до нас')[1] + 0.3
_rng = np.random.default_rng(9)
_walk = np.random.default_rng(90)
# the scattered photon: a random walk (kinks every ~0,35 s), in screen space
_N = int((T1 - T0) / 0.35) + 4
_DIR = _walk.uniform(0, 2 * math.pi, _N)
# the free rays after the clearing
NR = 46
R_A = _walk.uniform(0, 2 * math.pi, NR); R_T = _walk.uniform(0, 7.0, NR); R_X = _walk.uniform(0.15, 0.85, NR) * fx.W
R_Y = _walk.uniform(0.15, 0.85, NR) * fx.H


def photon(T):
    """the photon's path up to time T (points), zigzagging"""
    pts = [(fx.W * 0.42, fx.H * 0.55)]
    t = T0
    k = 0
    while t < T:
        dt = min(0.35, T - t)
        a = _DIR[k]; sp = 260.0
        x, y = pts[-1]
        pts.append((x + math.cos(a) * sp * dt, y + math.sin(a) * sp * dt))
        # keep it in the middle of the frame
        x, y = pts[-1]
        pts[-1] = (fx.W * 0.5 + (x - fx.W * 0.5) * 0.92, fx.H * 0.5 + (y - fx.H * 0.5) * 0.92)
        t += dt; k += 1
    return pts


def frame(T):
    W, H = fx.W, fx.H
    t = T - T0
    a = np.zeros((270, 480), np.float32); b = np.zeros((270, 480), np.float32)
    zo = 1.0 + 0.09 * max(0.0, T - (COOL0 - 4.0))          # К15: the camera draws back — the ripples shrink
    fbm_grid(a, 0.06 * t - 1.1 * zo, 0.01 * t - 0.62 * zo, 2.2 * zo / 480, 2.2 * zo / 480, 0.12 * t + 40.0, 5, 0.55, 2.05, 9, 1.0)
    fbm_grid(b, -0.12 * t + 5.0, 0.0, 3.8 * zo / 480, 3.8 * zo / 480, 0.2 * t + 47.0, 4, 0.55, 2.1, 9, 0.6)
    dens = (0.6 * a + 0.4 * b)
    clear = fx.ramp(T, CLEAR0, CLEAR1)
    fogL = (0.10 + 2.2 * np.clip(dens - 0.32, 0, 1) ** 1.5) * (1 - 0.94 * clear)
    # colour of the glow: 3000 °C (orange-white) cooling to red and to dark
    cool = fx.ramp(T, COOL0, COOL1)
    tint = np.array([1.0, 0.52 - 0.40 * cool, 0.20 - 0.18 * cool], np.float32)
    # what stays after the clearing: the glow that fills everything, with faint ripples (the future Planck spots)
    glowL = (0.085 * (1 - cool) ** 1.4) * clear * (0.75 + 0.6 * np.clip(dens - 0.2, 0, 1))
    lum = cv2.resize(fogL + glowL, (W, H))
    img = lum[..., None] * tint
    # the scattered photon (before the clearing): a bright head, a short trail along its zigzag
    if T < CLEAR1:
        pts = photon(T)
        trail = np.zeros((H // 2, W // 2), np.float32)
        tail = pts[-5:]
        for k in range(len(tail) - 1):
            p0 = (int(tail[k][0] / 2), int(tail[k][1] / 2)); p1 = (int(tail[k + 1][0] / 2), int(tail[k + 1][1] / 2))
            cv2.line(trail, p0, p1, (0.15 + 0.85 * k / len(tail)) ** 2, 2, cv2.LINE_AA)
        trail = cv2.GaussianBlur(trail, (0, 0), 2.2)
        head = np.zeros_like(trail); cv2.circle(head, (int(pts[-1][0] / 2), int(pts[-1][1] / 2)), 2, 1.0, -1, cv2.LINE_AA)
        trail += cv2.GaussianBlur(head, (0, 0), 2.5) * 6
        img += (cv2.resize(trail, (W, H)) * 1.8 * (1 - clear))[..., None] * np.array([1.0, 0.9, 0.75], np.float32)
    # the free rays: once the fog clears, light flies straight — long streaks shooting outward
    fr = fx.ramp(T, CLEAR0 + 0.6, CLEAR1) * (1 - cool)
    if fr > 0:
        rays = np.zeros((H // 2, W // 2), np.float32)
        for i in range(NR):
            s = (T - CLEAR0 - R_T[i]) * 650
            if s < 0 or s > 2600: continue
            ca, sa = math.cos(R_A[i]), math.sin(R_A[i])
            hx, hy = R_X[i] + ca * s, R_Y[i] + sa * s
            L = min(s, 420.0)
            for k in range(10):                               # a streak: bright head, a tail fading behind it
                a0, a1 = L * k / 10, L * (k + 1) / 10
                cv2.line(rays, (int((hx - ca * a0) / 2), int((hy - sa * a0) / 2)),
                         (int((hx - ca * a1) / 2), int((hy - sa * a1) / 2)), 0.5 * (1 - k / 10) ** 2, 1, cv2.LINE_AA)
            cv2.circle(rays, (int(hx / 2), int(hy / 2)), 1, 1.0, -1, cv2.LINE_AA)
        rays = cv2.GaussianBlur(rays, (0, 0), 0.8)
        img += (cv2.resize(rays, (W, H)) * 1.8 * fr)[..., None] * np.array([1.0, 0.82, 0.55], np.float32)
    # the lamp's filament, a real photo of the same colour
    la = fx.ramp(T, LAMP0, LAMP0 + 1.0) * (1 - fx.ramp(T, LAMP1 - 1.0, LAMP1))
    if la > 0 and os.path.exists(os.path.join(fx.ASSETS, 'lamp_filament.jpg')):
        im = fx.load('lamp_filament.jpg', 3000)
        sc = max(W / im.shape[1], H / im.shape[0]) * (1.15 + 0.03 * (T - LAMP0))
        img = img * (1 - 0.85 * la) + fx.warp(im, im.shape[1] / 2, im.shape[0] / 2, sc) * (1.3 * la)
    fin = fx.ramp(T, T0, T0 + 0.8)
    return fx.finish(img * (0.2 + 0.8 * fin), _rng, exposure=1.0, thr=0.55, vig=0.28, grain=0.012)
