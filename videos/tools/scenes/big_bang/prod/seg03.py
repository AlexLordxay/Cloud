# Segment 3 — К4 (0:21.0–0:32.6): out of the point's bloom — the flight through the stretching haze again
# («І почало розтягуватися — одразу всюди. Зараз я покажу, як це було…»), another region of the same space (the camera
# starts offset sideways), a slow sideways turn of the gaze. Dissolves out into the dark of seg04 (Act 1).
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import k1, fx

T0, T1 = 21.0, 32.6
TS = 21.0
_cam = k1.cam_c
_base = k1.basis
OFF = np.array([8.5, -3.0, 6.0])


def cam_c(t): return _cam(t) + OFF


def basis(t):
    fw, rt, up = _base(t + 3.0)
    a = math.radians(-35) * fx.smoother(t / 11.0)
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return R @ fw, R @ rt, R @ up


k1.cam_c = cam_c
k1.basis = basis
k1.HW, k1.HH, k1.NSTEP = 720, 405, 120
k1.post = lambda lin, t, rng: fx.finish(lin, rng, exposure=1.05, vig=0.28, grain=0.012)
_CL = None
_rng = np.random.default_rng(2)


def frame(T):
    global _CL
    if _CL is None: _CL = k1.make_clumps()
    return k1.frame(T - TS, _CL, _rng)
