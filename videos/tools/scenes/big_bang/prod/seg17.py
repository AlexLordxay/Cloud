# Segment 17 — К32 + К33 (5:48.8–6:18.53, the end).
#   К32 «Через трильйони років астрономи побачать лише свою галактику — і, можливо, ніколи не дізнаються про Великий
#       вибух»: the sky of the far future — one lone galaxy (a real elliptical, NASA/ESA Hubble) in absolute black;
#       «Нам пощастило: ми живемо тоді, коли його ще видно»: out of the dark — our real starry sky (ESO panorama);
#   К33 the end card over the slow drift of the glowing haze of К1 (k1.py, slowed) — the circle closes; the titles are
#       laid on by the assembly («Не проґав наступне відео» · «Підписатися» · «Небозвід»).
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx, k1

T0, T1 = 348.8, 378.6
LUCKY = fx.phrase('Нам пощастило')[0] - 0.6
END = fx.shot('К33')[0]                      # 361.75
_rng = np.random.default_rng(17)
k1.HW, k1.HH, k1.NSTEP = 640, 360, 100
k1.post = lambda lin, t, rng: lin            # the finish is done here
_CL = None


def frame(T):
    global _CL
    W, H = fx.W, fx.H
    img = np.zeros((H, W, 3), np.float32)
    aG = fx.ramp(T, T0 + 0.4, T0 + 2.4) * (1 - fx.ramp(T, LUCKY, LUCKY + 1.6))
    aS = fx.ramp(T, LUCKY, LUCKY + 1.6) * (1 - fx.ramp(T, END - 0.2, END + 1.8))
    aK = fx.ramp(T, END - 0.2, END + 1.8) * (1 - fx.ramp(T, T1 - 2.5, T1 - 0.1))
    if aG > 0:
        im = fx.load('elliptical_galaxy.jpg', 3500)
        bg = np.percentile(im.reshape(-1, 3)[::97], 40, axis=0)
        sc = max(W / im.shape[1], H / im.shape[0]) * (0.8 + 0.01 * (T - T0))
        lay = np.clip(fx.warp(im, im.shape[1] / 2, im.shape[0] / 2, sc) - bg * 1.3, 0, None)
        img += lay * fx.disc_mask(W / 2, H / 2, 0.42 * sc * im.shape[0], 0.5) * (1.4 * aG)   # only the one galaxy
    if aS > 0:
        im = fx.load('milkyway_panorama.jpg', 6000)
        img += fx.warp(im, im.shape[1] * (0.47 + 0.002 * (T - LUCKY)), im.shape[0] * 0.5, H / im.shape[0] * 1.6) * (1.2 * aS)
    if aK > 0:
        if _CL is None: _CL = k1.make_clumps()
        lin = k1.frame(0.35 * (T - END) + 1.0, _CL, _rng).astype(np.float32)
        img += lin * aK * 0.75                 # a little darker: the titles sit on it
    return fx.finish(img, _rng, exposure=1.0, thr=0.6, bk=0.8, vig=0.3, grain=0.011)
