# Segment 1 — К1 + К2 (0:00–0:08.23): the flight through the glowing haze of the young Universe (the approved К1,
# k1.py variant А), then К2: the gaze swings ~120° — the same in every direction, no edge, no centre. Ends at frame
# 247 exactly; seg02 (К3) starts its pull-back from this very frame (seamless).
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import k1, fx

T0, T1 = 0.0, 247 / fx.FPS
PAN0, PAN1, PAN = 4.8, 8.0, math.radians(120)
_base = k1.basis


def basis(t):
    fw, rt, up = _base(t)
    a = PAN * fx.smoother((t - PAN0) / (PAN1 - PAN0))
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])          # yaw about the world's up
    return R @ fw, R @ rt, R @ up


k1.basis = basis
k1.HW, k1.HH, k1.NSTEP = 720, 405, 120          # the haze is soft: marched at 3/8 resolution (speed)
k1.post = lambda lin, t, rng: fx.finish(lin, rng, exposure=1.05, vig=0.28, grain=0.012)
_CL = None
_rng = np.random.default_rng(1)


def frame(T):
    global _CL
    if _CL is None: _CL = k1.make_clumps()
    return k1.frame(T, _CL, _rng)
