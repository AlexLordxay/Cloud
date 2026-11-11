# Segment 4 — К5 (Act 1 opens, 0:32.0–0:43.8): «Що було до цього — не знає ніхто. Але приблизно через одну трильйонну
# від трильйонної від трильйонної секунди почалося найдивніше.» Out of the haze into darkness: the restless «quantum
# foam» of the vacuum — faint threads of light that flicker in and out like heat-haze, a slow push in; at the end a
# single hydrogen atom (the same exact 1s cloud as К3) condenses in the middle — the atom that К6 will inflate.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, k3
from noise2 import fbm_grid

T0, T1 = 32.0, 43.8
STATEFUL = True
SW, SH = 960, 540
ATOM_IN = (40.6, 43.0)
_atom = None
_rng = np.random.default_rng(4)


def foam(T):
    t = T - T0
    zoom = 1.0 + 0.035 * t                                  # the slow push in
    s = 5.0 / SW / zoom
    a = np.zeros((SH, SW), np.float32); b = np.zeros((SH, SW), np.float32)
    fbm_grid(a, -1.6 / zoom, -0.9 / zoom, s, s, 0.55 * t, 5, 0.58, 2.1, 1, 0.9)
    fbm_grid(b, -1.6 / zoom + 9.0, -0.9 / zoom, s * 2.3, s * 2.3, 0.9 * t + 4.0, 4, 0.6, 2.2, 0, 0.4)
    thread = np.clip((a - 0.62) / 0.22, 0, 1) ** 2.2          # thin bright threads
    veil = np.clip(b - 0.35, 0, 1)                            # a soft veil
    return thread, veil


def frame(T):
    global _atom
    if _atom is None: _atom = k3.Atom(np.random.default_rng(7))
    t = T - T0
    thread, veil = foam(T)
    fin = fx.ramp(T, 32.0, 33.6)                              # out of the haze's dissolve
    dim = 1 - 0.65 * fx.ramp(T, ATOM_IN[0], ATOM_IN[1])
    lum = (thread * 0.16 + veil * 0.035) * fin * dim
    col = np.empty((SH, SW, 3), np.float32)
    col[..., 0] = lum * 0.62; col[..., 1] = lum * 0.74; col[..., 2] = lum * 1.0 + veil * 0.012
    img = cv2.resize(col, (fx.W, fx.H), interpolation=cv2.INTER_LINEAR)
    # sparks: virtual particles flashing in and out
    n = 30
    xs = _rng.uniform(0, fx.W, n); ys = _rng.uniform(0, fx.H, n); pw = _rng.uniform(0.2, 1.0, n) * fin * dim
    sp = np.zeros((fx.H, fx.W), np.float32)
    xi = np.clip(xs.astype(int), 0, fx.W - 1); yi = np.clip(ys.astype(int), 0, fx.H - 1)
    sp[yi, xi] = pw * 6
    sp = cv2.GaussianBlur(sp, (0, 0), 1.6)
    img += sp[..., None] * np.array([0.7, 0.8, 1.0], np.float32)
    _atom.step()
    al = fx.ramp(T, ATOM_IN[0], ATOM_IN[1])
    if al > 0:
        _atom.draw(img, fx.W / 2, fx.H / 2, 52.0 * (1 + 0.035 * t) / 1.4, al, t)
    return fx.finish(img, _rng, exposure=1.0, thr=0.4, vig=0.3, grain=0.012)
