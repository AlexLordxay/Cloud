# Segment 7 — К9 + К10 + К11 (1:19.0–1:55.0), the hot soup.
#   К9  «Далі — вогняна каша. Немає навіть атомів — лише кварки й глюони»: out of the white — the quark-gluon plasma,
#       a dense flowing «liquid light» (blue-white: trillions of degrees; honest colour), two layers drifting at
#       different speeds (depth);
#   К10 «Частинки й античастинки народжувалися й знищували одна одну…»: a storm of tiny annihilation flashes; then the
#       storm thins, the soup dims («Усе інше згоріло в спалахах») and only rare survivors stay alight — «1 на мільярд»;
#   К11 «За кілька десятків мільйонних часток секунди кварки злиплися в протони й нейтрони»: what is left condenses into
#       countless tiny bright grains, like dew out of a mist.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx
from noise2 import fbm_grid

T0, T1 = 79.0, 115.0
SW, SH = 480, 270
STORM0, STORM1, BURN = 85.6, 96.0, 104.5          # flashes begin, peak ends, the soup has burnt out
COND0, COND1 = 107.5, 113.5
_rng = np.random.default_rng(7)

# the annihilation events (deterministic): time, x, y, size, power
_er = np.random.default_rng(70)
_rate = lambda T: 260.0 * fx.ramp(T, STORM0 - 0.5, STORM0 + 2.0) * (1 - 0.97 * fx.ramp(T, STORM1, BURN))
_ts = []
_T = STORM0 - 0.5
while _T < BURN + 2:
    r = _rate(_T)
    if r > 0.5:
        n = _er.poisson(r / 30.0)
        _ts.extend([_T + _er.uniform(0, 1 / 30)] * n)
    _T += 1 / 30
EV_T = np.array(_ts); NE = len(EV_T)
EV_X = _er.uniform(0, fx.W, NE); EV_Y = _er.uniform(0, fx.H, NE)
EV_S = np.exp(_er.normal(0, 0.4, NE)) * 2.2; EV_P = np.exp(_er.normal(0, 0.5, NE))
EV_A = _er.uniform(0, 2 * math.pi, NE)
# the survivors (one in a billion) and the condensed grains
NS = 46
SV_X = _er.uniform(80, fx.W - 80, NS); SV_Y = _er.uniform(60, fx.H - 60, NS); SV_P = _er.uniform(0.6, 1.2, NS)
SV_X[0], SV_Y[0] = fx.W * 0.62, fx.H * 0.44         # the one that gets the label
NG = 5200
GR_X = _er.uniform(0, fx.W, NG); GR_Y = _er.uniform(0, fx.H, NG); GR_T = _er.uniform(COND0, COND1, NG)
GR_P = np.exp(_er.normal(0, 0.35, NG)) * 0.55


def plasma(T):
    t = T - T0
    z = 1.0 + 0.02 * t
    a = np.zeros((SH, SW), np.float32); b = np.zeros((SH, SW), np.float32)
    fbm_grid(a, -1.0 + 0.05 * t, -0.56, 2.0 / SW / z, 2.0 / SW / z, 0.35 * t, 5, 0.55, 2.05, 2, 1.4)
    fbm_grid(b, 4.0 - 0.09 * t, 2.0 + 0.03 * t, 3.6 / SW / z, 3.6 / SW / z, 0.6 * t + 3.0, 4, 0.55, 2.1, 2, 0.8)
    f = 0.65 * a + 0.35 * b
    hot = np.clip((f - 0.30) / 0.45, 0, 1)
    return hot


def splat(buf, xs, ys, pw, sig):
    """add points (x, y, power) into a half-res buffer as tiny Gaussian dots"""
    h, w = buf.shape
    xi = np.clip((xs * w / fx.W).astype(int), 0, w - 1); yi = np.clip((ys * h / fx.H).astype(int), 0, h - 1)
    tmp = np.zeros_like(buf)
    np.add.at(tmp, (yi, xi), pw)
    buf += cv2.GaussianBlur(tmp, (0, 0), sig)


def frame(T):
    W, H = fx.W, fx.H
    hot = plasma(T)
    soup = 1.0 - 0.88 * fx.ramp(T, STORM1 - 1.0, BURN)            # the soup burns out
    soup *= 1.0 - 0.9 * fx.ramp(T, COND0 - 1.0, COND1)
    L = (0.015 + 1.7 * hot ** 2.8) * soup
    col = np.empty((SH, SW, 3), np.float32)                     # white-hot cores, blue-violet edges
    col[..., 0] = L * (0.32 + 0.68 * hot); col[..., 1] = L * (0.48 + 0.52 * hot); col[..., 2] = L * 1.0
    img = cv2.resize(col, (W, H), interpolation=cv2.INTER_CUBIC)
    # the flashes (pairs born and annihilating): a short life each — two dots part, then one flash
    half = np.zeros((H // 2, W // 2), np.float32)
    live = np.nonzero((EV_T <= T) & (EV_T > T - 0.45))[0]
    if len(live):
        age = (T - EV_T[live]) / 0.45
        sep = EV_S[live] * 3.0 * np.minimum(age / 0.55, 1.0)
        pre = (age < 0.55)
        for sgn in (-1, 1):
            splat(half, EV_X[live] + sgn * sep * np.cos(EV_A[live]), EV_Y[live] + sgn * sep * np.sin(EV_A[live]),
                  (EV_P[live] * 3.0 * pre).astype(np.float32), 0.8)
        fl = np.exp(-((age - 0.62) / 0.12) ** 2) * EV_P[live] * 22.0
        splat(half, EV_X[live], EV_Y[live], fl.astype(np.float32), 1.6)
    # the survivors
    sv = fx.ramp(T, STORM1 - 3.0, STORM1 + 1.0) * (1 - fx.ramp(T, COND1, COND1 + 1.5))
    if sv > 0:
        tw = 1 + 0.15 * np.sin(T * 3.1 + np.arange(NS))
        splat(half, SV_X, SV_Y, (SV_P * tw * 2.4 * sv).astype(np.float32), 1.3)
    # the condensed grains (protons and neutrons)
    g = np.clip((T - GR_T) / 0.8, 0, 1)
    if g.any():
        splat(half, GR_X, GR_Y, (GR_P * g * 1.6).astype(np.float32), 0.9)
    pts = cv2.resize(half, (W, H), interpolation=cv2.INTER_LINEAR)
    img += pts[..., None] * np.array([0.95, 0.93, 1.0], np.float32)
    # out of the white
    wht = 1 - fx.ramp(T, T0, T0 + 1.0)
    img = img + wht * 4.0
    out = fx.finish(img, _rng, exposure=1.0, thr=0.6, vig=0.24, grain=0.011).astype(np.float32) / 255
    al = fx.ramp(T, 91.4, 92.2) * (1 - fx.ramp(T, 96.6, 97.4))
    if al > 0:
        m = fx.text_mask([(SV_X[0] + 26, SV_Y[0] - 14, '1 на мільярд', 30, al * 0.85, fx.FONT_L, 'lm')])
        out = out * (1 - m[..., None]) + m[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
