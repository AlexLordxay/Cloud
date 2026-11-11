# Segment 8 — К12 (1:54.2–2:09.4): «А за перші хвилини Всесвіт, гарячіший, ніж надра Сонця, зварив перші ядра: на три
# чверті водень, на чверть гелій. І все. Заліза, кисню, золота ще не існувало.»
# The grains of seg07 fuse — brief flashes as nuclei form — the camera draws back into an even, hot glow; over it a
# fine glass-thin periodic table fades in: only H and He are lit (~75 % / ~25 % by mass), every other cell dark; at
# «Заліза, кисню, золота» Fe, O and Au glimmer as empty outlines — they do not exist yet.
import math, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx
from noise2 import fbm_grid

T0, T1 = 114.2, 129.4
TAB0 = fx.phrase('зварив перші ядра')[0] - 0.4
H_LAB, HE_LAB = fx.phrase('на три чверті')[0], fx.phrase('на чверть гелій')[0]
FE = fx.phrase('Заліза, кисню')[0]
_rng = np.random.default_rng(8)
SYM = ('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr '
       'Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt '
       'Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv '
       'Ts Og').split()


def cells():
    """(symbol, column 0..17, row 0..9) in the standard layout (rows 8–9: lanthanides, actinides)"""
    out = []
    z = 0
    plan = [[(0, 0), (17, 17)], [(0, 1), (12, 17)], [(0, 1), (12, 17)], [(0, 17)], [(0, 17)], [(0, 1), (2, 2), (3, 17)],
            [(0, 1), (2, 2), (3, 17)]]
    for row, spans in enumerate(plan):
        for a, b in spans:
            for col in range(a, b + 1):
                if row >= 5 and col == 2:                   # La / Ac stay in the main table, the f-block below
                    out.append((SYM[z], col, row)); z += 1
                    for k in range(14):
                        out.append((SYM[z], 3 + k, row + 3)); z += 1
                    continue
                out.append((SYM[z], col, row)); z += 1
    return out


CELLS = cells()
CS = 70                                               # cell size (px)
OX, OY = (fx.W - 18 * CS) / 2, 118


def cell_xy(col, row):
    y = OY + row * CS + (24 if row >= 7 else 0)
    return OX + col * CS, y


_er = np.random.default_rng(80)
NF = 900
F_T = _er.uniform(T0 - 0.5, T0 + 5.5, NF); F_X = _er.uniform(0, fx.W, NF); F_Y = _er.uniform(0, fx.H, NF)
F_P = np.exp(_er.normal(0, 0.5, NF))


def frame(T):
    W, H = fx.W, fx.H
    t = T - T0
    a = np.zeros((270, 480), np.float32)
    fbm_grid(a, 0.02 * t, 0.0, 2.4 / 480, 2.4 / 480, 0.2 * t + 20.0, 4, 0.55, 2.05, 9, 0.8)
    glow = (0.018 + 0.13 * np.clip(a - 0.25, 0, 1)) * (0.35 + 0.65 * fx.ramp(T, T0, T0 + 4.0))
    img = cv2.resize(np.dstack([glow * 0.80, glow * 0.86, glow * 1.0]).astype(np.float32), (W, H))
    # the remaining grains fusing: short flashes
    half = np.zeros((H // 2, W // 2), np.float32)
    age = T - F_T
    on = (age > 0) & (age < 0.5)
    if on.any():
        p = np.exp(-((age[on] - 0.12) / 0.1) ** 2) * F_P[on] * 10
        xi = (F_X[on] / 2).astype(int).clip(0, W // 2 - 1); yi = (F_Y[on] / 2).astype(int).clip(0, H // 2 - 1)
        np.add.at(half, (yi, xi), p.astype(np.float32))
    grains = (1 - fx.ramp(T, T0, T0 + 5.0)) * 0.9
    if grains > 0:
        g = np.random.default_rng(81)
        xi = g.integers(0, W // 2, 2600); yi = g.integers(0, H // 2, 2600)
        np.add.at(half, (yi, xi), np.float32(grains))
    half = cv2.GaussianBlur(half, (0, 0), 1.0)
    img += cv2.resize(half, (W, H))[..., None] * np.array([0.98, 0.95, 1.0], np.float32)
    # the lit cells: H and He
    tab = fx.ramp(T, TAB0, TAB0 + 1.6) * (1 - fx.ramp(T, T1 - 1.0, T1))
    for sym, col, row in CELLS[:2]:
        x, y = cell_xy(col, row)
        lit = tab * (0.75 + 0.1 * math.sin(T * 2.0 + col))
        c = np.array([0.55, 0.75, 1.0], np.float32) if sym == 'H' else np.array([1.0, 0.85, 0.6], np.float32)
        img[int(y) + 2:int(y + CS) - 2, int(x) + 2:int(x + CS) - 2] += c * 0.55 * lit
    out = fx.finish(img, _rng, exposure=1.0, thr=0.5, vig=0.26, grain=0.011).astype(np.float32) / 255
    if tab > 0:
        m = np.zeros((H, W), np.float32)
        items = []
        ghost = fx.ramp(T, FE, FE + 0.8)
        for sym, col, row in CELLS:
            x, y = cell_xy(col, row)
            lit = sym in ('H', 'He')
            missing = sym in ('Fe', 'O', 'Au')
            al = tab * (0.9 if lit else 0.16 + (0.5 * ghost * (0.75 + 0.25 * math.sin(T * 4)) if missing else 0))
            x0, y0, x1, y1 = int(x) + 2, int(y) + 2, int(x + CS) - 2, int(y + CS) - 2
            m[y0, x0:x1] = np.maximum(m[y0, x0:x1], al); m[y1, x0:x1] = np.maximum(m[y1, x0:x1], al)
            m[y0:y1, x0] = np.maximum(m[y0:y1, x0], al); m[y0:y1, x1] = np.maximum(m[y0:y1, x1], al)
            items.append((x + CS / 2, y + CS / 2, sym, 24 if not lit else 28, al * (1.0 if lit else 1.3),
                          fx.FONT_L if not lit else fx.FONT_M, 'mm'))
        hx, hy = cell_xy(0, 0); ex, ey = cell_xy(17, 0)
        items.append((hx + CS + 14, hy + CS / 2, '≈ 75 %', 28, tab * fx.ramp(T, H_LAB, H_LAB + 0.6), fx.FONT_L, 'lm'))
        items.append((ex - 14, ey + CS / 2, '≈ 25 %', 28, tab * fx.ramp(T, HE_LAB, HE_LAB + 0.6), fx.FONT_L, 'rm'))
        m = np.maximum(m * 0.55, fx.text_mask(items))
        out = out * (1 - m[..., None]) + m[..., None] * np.array([0.92, 0.95, 1.0], np.float32)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
