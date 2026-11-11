# Segment 15 — К27 + К28 + К29 + К30 (Act 7 «Ти», 4:53.3–5:34.0).
#   К27 «Минуло дев'ять мільярдів років. Покоління зір народжувалися й вибухали, розсіюючи все, що зварили»: a real dark
#       cloud of dust and gas (ESO) — a slow approach; «З цього пилу народилися Сонце і Земля»: the real disc round a
#       young star (ALMA, HL Tauri), its centre glowing up;
#   К28 the Earth (NASA, «Blue Marble»);
#   К29 «Тож залізо у твоїй крові — а його вистачить на маленький цвях — зварене в зорях, яких давно немає»: red blood
#       cells under an electron microscope; «залізо в тілі ≈ 3 г»;
#   К30 «А от водень у тобі — з самого Великого вибуху»: the cells dissolve into the hydrogen atom of К3 (the same exact
#       1s cloud) — «водень · 13,8 млрд років»; «Надішли це тому, хто теж зроблений із зоряного пилу»: out to the stars.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, k3

T0, T1 = 293.3, 334.0
STATEFUL = True
DISC0 = fx.phrase("З цього пилу")[0] - 0.6
EARTH0 = fx.phrase("З цього пилу")[1] - 0.4
BLOOD0 = fx.phrase('Тож залізо')[0] + 0.4
FE_LAB = fx.phrase('а його вистачить')[0]
H0 = fx.phrase('А от водень')[0] - 0.2
H_LAB = fx.phrase('з самого Великого')[0]
SHARE = fx.phrase('Надішли це тому')[0] - 0.3
_rng = np.random.default_rng(15)
_atom = None


def photo(name, T, t0, maxd, z0=1.05, dz=0.015, gain=1.1, cx=0.5, cy=0.5, rot=0.0):
    im = fx.load(name, maxd)
    h, w = im.shape[:2]
    sc = max(fx.W / w, fx.H / h) * (z0 + dz * (T - t0))
    return fx.warp(im, w * cx, h * cy, sc, rot) * gain


def frame(T):
    global _atom
    if _atom is None: _atom = k3.Atom(np.random.default_rng(9))
    W, H = fx.W, fx.H
    a_cl = 1 - fx.ramp(T, DISC0, DISC0 + 1.6)
    a_d = fx.ramp(T, DISC0, DISC0 + 1.6) * (1 - fx.ramp(T, EARTH0, EARTH0 + 1.2))
    a_e = fx.ramp(T, EARTH0, EARTH0 + 1.2) * (1 - fx.ramp(T, BLOOD0, BLOOD0 + 1.2))
    a_b = fx.ramp(T, BLOOD0, BLOOD0 + 1.2) * (1 - fx.ramp(T, H0, H0 + 2.0))
    a_h = fx.ramp(T, H0, H0 + 2.0)
    img = np.zeros((H, W, 3), np.float32)
    if a_cl > 0: img += photo('dark_cloud.jpg', T, T0, 4200, 1.0, 0.03, 1.15) * a_cl
    if a_d > 0:
        img += photo('hltau_alma.jpg', T, DISC0, 1800, 0.95, 0.04, 1.2) * a_d
        g = fx.ramp(T, DISC0 + 1.0, EARTH0)                   # the young Sun lighting up in the middle
        yy, xx = np.ogrid[0:H, 0:W]
        d2 = (xx - W / 2) ** 2 + (yy - H / 2) ** 2
        img += (np.exp(-d2 / (2 * 18.0 ** 2)) * 6 * g + np.exp(-d2 / (2 * 120.0 ** 2)) * 0.25 * g).astype(np.float32)[..., None] * np.array([1.0, 0.85, 0.6], np.float32) * a_d
    if a_e > 0:
        from seg05 import disc_of
        im, cx, cy, r = disc_of('earth_bluemarble.jpg')
        img += fx.warp(im, cx, cy, (430 + 14 * (T - EARTH0)) / r, 0.02 * (T - EARTH0)) * (1.1 * a_e)
    if a_b > 0 and os.path.exists(os.path.join(fx.ASSETS, 'red_blood_cells.jpg')):
        img += photo('red_blood_cells.jpg', T, BLOOD0, 3500, 1.05, 0.02, 1.0) * a_b
    if a_h > 0:
        mw = fx.load('milkyway_panorama.jpg', 6000)
        out_k = fx.ramp(T, SHARE, T1)
        img += fx.warp(mw, mw.shape[1] * 0.55, mw.shape[0] * 0.5, fx.H / mw.shape[0] * (2.6 - 0.9 * out_k)) * (0.25 + 0.75 * out_k) * a_h
        _atom.step()
        _atom.draw(img, W / 2, H / 2, 60.0 * (1 - 0.6 * out_k), a_h * (1 - 0.7 * out_k), T)
    out = fx.finish(img, _rng, exposure=1.0, thr=0.75, bk=0.7, vig=0.26, grain=0.010).astype(np.float32) / 255
    items = [(W / 2, H - 90, 'залізо в тілі людини ≈ 3 г', 28, fx.ramp(T, FE_LAB, FE_LAB + 0.8) * (1 - fx.ramp(T, H0 - 0.6, H0)) * 0.8, fx.FONT_L, 'mm'),
             (W / 2, H / 2 + 300 * (1 - 0.6 * fx.ramp(T, SHARE, T1)), 'водень · 13,8 млрд років', 30,
              fx.ramp(T, H_LAB, H_LAB + 0.8) * (1 - fx.ramp(T, SHARE + 0.5, SHARE + 1.5)) * 0.85, fx.FONT_L, 'mt')]
    m = fx.text_mask(items)
    out = out * (1 - m[..., None]) + m[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
