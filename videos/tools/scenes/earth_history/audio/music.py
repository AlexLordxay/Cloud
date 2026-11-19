#!/usr/bin/env python3
# Score for «Історія Землі»: ONE continuous piece, synthesized with numpy/scipy only (no samples, no AI tools).
#   python3 scenes/earth_history/audio/music.py     -> work/earth_history/music.wav  (48 kHz stereo, = timeline duration)
# (the whole chain: ./render.sh). Shared drone on A for the whole video; chords crossfade (>= 4 s) into one another,
# every layer's level is a smooth curve; only two accents are loud: the Theia impact and the Siberian eruption.
# Cue list: cues.md.
import sys
import numpy as np
from scipy import signal
from common import *

rng = np.random.default_rng(2024)
dL = np.zeros(N, np.float32); dR = np.zeros(N, np.float32); wet = np.zeros(N, np.float32)
A = lambda n: (np.arange(n) / SR)

# ---------------------------------------------------------------- accents / anchors on the cut
T_IMPACT = sent('voice_p1.mp3', 11)[0] + 3.6        # «врізається»: sentence starts 54.61, the word ~3.6 s in
T_ERUPT = sent('voice_p3.mp3', 1)[0] + 2.4         # «прориваються вулкани»
T_OX = vt('voice_p2.mp3', 42.61)                   # «кожен твій вдих»
T_6S = vt('voice_p3.mp3', 72.68)                   # «за шість секунд до півночі»
T_TY = vt('voice_p3.mp3', 77.87)                   # «Ти.»
T_BOOM_CAMBR = vt('voice_p2.mp3', 110.48)          # «І раптом — вибух»
T_MOON = vt('voice_p1.mp3', 68.33)
T_THAW = vt('voice_p2.mp3', 91.45)
T_ANTH = vt('voice_p3.mp3', 113.37)                # «ми — не кінець історії»
T_RESOLVE = END_CARD

# ---------------------------------------------------------------- wavetables
TL_N = 4096
def table(harm):
    x = np.arange(TL_N + 1) / TL_N; y = np.zeros(TL_N + 1)
    for n, a in harm: y += a * np.sin(2 * np.pi * n * x + 0.7 * n)
    return (y / np.abs(y).max()).astype(np.float32)
TAB = {
    'sine': table([(1, 1)]),
    'soft': table([(k, 1 / k ** 2.2) for k in range(1, 12)]),
    'bright': table([(k, 1 / k ** 1.15) for k in range(1, 22)]),
    'horn': table([(1, 1), (2, .8), (3, .7), (4, .45), (5, .3), (6, .18), (7, .1), (8, .06)]),
    'hollow': table([(k, 1 / k ** 1.6) for k in range(1, 16, 2)]),
}
def osc(tab, f, n, ph0=0.0):
    ph = (ph0 + np.cumsum(np.broadcast_to(np.asarray(f, np.float64), (n,))) / SR) % 1.0
    idx = ph * TL_N; i0 = idx.astype(np.int32); fr = (idx - i0).astype(np.float32)
    t = TAB[tab]; return t[i0] * (1 - fr) + t[i0 + 1] * fr
mf = lambda m: 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)

def put(t0, x, level=1.0, pan=0.0, send=0.3, curve=None):
    """add mono x starting at t0 s into the dry bus (constant-power pan) and the reverb send"""
    i0 = int(round(t0 * SR)); i1 = i0 + len(x)
    if i1 <= 0 or i0 >= N: return
    a = max(0, -i0); b = len(x) - max(0, i1 - N); x = x[a:b]; i0 = max(i0, 0)
    n = len(x); x = x * level
    if curve is not None: x = x * curve((i0 + np.arange(n)) / SR).astype(np.float32)
    th = (pan + 1) * np.pi / 4
    dL[i0:i0 + n] += x * np.cos(th); dR[i0:i0 + n] += x * np.sin(th); wet[i0:i0 + n] += x * send

def env_ads(n, att, rel, hold_end=None):
    """amplitude: smoothstep in over att, flat, smoothstep out over the last rel samples"""
    e = np.ones(n, np.float32)
    na = min(int(att * SR), n); nr = min(int(rel * SR), n)
    if na: e[:na] = smooth(np.arange(na) / na)
    if nr: e[n - nr:] *= smooth(np.arange(nr, 0, -1) / nr)
    return e

# ---------------------------------------------------------------- layer level curves (0..~1); every move is slow
L_ = {}
def lv(name, pts): L_[name] = interp(pts)
G = lambda n: L_[n]

# master loudness per act (dB, piecewise, ramps >= 4 s)
master_db = interp([
    (0, -4), (8, -1), (28, -1), (40, 0), (54, 0), (58.2, 0), (62, -2), (100, -2), (108, 1), (118, 3), (132, -1), (140, -3), (160, -2),
    (172, -1), (185, -3), (200, -5), (212, -3), (230, -2), (242, 1), (250, 3), (262, 2), (274, 1), (280, -2), (292, 0), (305, -1),
    (330, -1), (338, -1), (346, -2), (352, -3), (385, -2), (392, -3), (398, -11), (470, -11), (485, -8), (500, -4), (508, -3), (528, -3),
    (534, -3), (545, -7), (570, -7), (586, -8), (592.8, -10), (597, -17), (599.76, -35)])

# ---------------------------------------------------------------- pad chords
CH = {
    'Am': [45, 52, 57, 60, 64], 'Am9': [45, 52, 60, 64, 71], 'F': [41, 48, 57, 60, 65], 'Fma7': [41, 48, 57, 64, 69],
    'C': [48, 55, 60, 64, 67], 'G': [43, 50, 59, 62, 67], 'Dm': [50, 57, 62, 65], 'Dm9': [38, 50, 57, 65, 72],
    'D': [50, 57, 62, 66], 'Dly': [50, 57, 61, 66, 69], 'A': [45, 52, 57, 61, 64], 'Asus2': [45, 52, 57, 59, 64],
    'Aadd9': [45, 52, 59, 61, 64, 69], 'E': [40, 47, 56, 59, 64], 'Bm': [47, 54, 59, 62, 66], 'F#m': [42, 49, 57, 61, 66],
    'Em': [40, 47, 55, 59, 64], 'Bb': [46, 53, 58, 62, 65], 'Fm': [41, 48, 56, 60], 'Gm': [43, 50, 58, 62],
    'Asus4': [45, 52, 57, 62, 64], 'low': [45, 52], 'lowfifth': [33, 40, 45, 52], 'Em7': [40, 47, 55, 62, 67],
    'Cma7': [48, 55, 59, 64, 67, 71], 'Gadd': [43, 50, 59, 62, 69], 'Esus': [40, 45, 47, 52, 59],
}
XF = 4.0
def pad_chords(plan, level=1.0, tab='soft', bright=0.25, curve=None, send=0.5, vib=0.0, att=None):
    """plan = [(t, chord), ...] + final end time; each chord fades in over XF s centred on its start, out the same way"""
    for k in range(len(plan) - 1):
        t, ch = plan[k]; t_next = plan[k + 1][0]
        ta = t - XF / 2 if k > 0 else t - 1.0
        tb = t_next + XF / 2
        n = int((tb - ta) * SR)
        e = env_ads(n, XF if k > 0 else 5.0, XF)
        for j, m in enumerate(CH[ch]):
            f = mf(m); lowm = m < 52
            x = np.zeros(n, np.float32)
            for dt in (-0.07, 0.0, 0.08):
                fv = f * 2 ** (dt * 1.0 / 12) * (1 + vib * 0.003 * np.sin(2 * np.pi * (0.2 + 0.07 * j) * A(n)))
                x += osc(tab, fv, n, rng.random())
            if bright > 0 and not lowm:
                x += bright * osc('bright', f * 1.002, n, rng.random()) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.05 + .02 * j) * A(n) + j))
            put(ta, x * e * (0.11 if lowm else 0.075), level, pan=rng.uniform(-.5, .5) if not lowm else 0, send=send, curve=curve)

# ---------------------------------------------------------------- continuous drone on A (shared by the whole piece)
def drone(curve):
    n = N; t = A(n)
    x = np.zeros(n, np.float32)
    for m, a in ((33, 1.0), (40, 0.5), (45, 0.45), (52, 0.22)):
        f = mf(m)
        for dt in (-.05, .05):
            x += a * 0.5 * osc('soft', f * 2 ** (dt / 12) * (1 + 0.0007 * np.sin(2 * np.pi * 0.03 * t)), n, rng.random())
    e = curve(t).astype(np.float32)
    e *= smooth(t / 5.0) * smooth((DUR - 0.8 - t) / 2.5)
    x *= e * 0.30
    dL[:] += x; dR[:] += x; wet[:] += x * 0.25

# ---------------------------------------------------------------- instruments (short notes)
def pluck(t0, m, level=1.0, dur=1.6, pan=0.0, send=0.5, curve=None, bright=1.0):
    n = int(dur * SR); t = A(n); f = float(mf(m)); x = np.zeros(n, np.float32)
    for r, a, d in ((1, 1, 1.0), (2.0, .45 * bright, .6), (3.01, .25 * bright, .35), (4.2, .12 * bright, .2)):
        if f * r > 11000: continue
        x += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (d * dur / 4))
    x *= np.minimum(1, t / 0.004)
    put(t0, x * 0.2, level, pan, send, curve)

def bell(t0, m, level=1.0, dur=8.0, pan=0.0, send=0.9, curve=None, glass=False):
    n = int(dur * SR); t = A(n); f = float(mf(m)); x = np.zeros(n, np.float32)
    parts = ((1, 1, 1.0), (2.756, .5, .6), (5.404, .3, .35), (8.93, .16, .2)) if glass else \
            ((1, 1, 1.0), (2.0, .55, .7), (2.41, .3, .5), (3.0, .25, .45), (4.16, .12, .25))
    for r, a, d in parts:
        if f * r > 14000: continue
        x += a * np.sin(2 * np.pi * f * r * t + rng.random() * 6) * np.exp(-t / (d * dur / 4.5))
    x *= smooth(t / 0.006)
    put(t0, x * 0.16, level, pan, send, curve)

def horn(t0, t1, m, level, att=1.2, rel=1.5, pan=0.0, send=0.5, curve=None, vib=0.004, tab='horn'):
    n = int((t1 - t0 + rel) * SR); t = A(n); f = mf(m)
    fv = f * (1 + vib * smooth((t - 0.6) / 1.0) * np.sin(2 * np.pi * 5.0 * t))
    x = osc(tab, fv, n) + 0.6 * osc(tab, fv * 1.004, n, .3)
    x *= env_ads(n, att, rel)
    put(t0, x * 0.1, level, pan, send, curve)

def tom(t0, f0=75, level=1.0, dur=1.0, send=0.3, att=0.012, curve=None):
    n = int(dur * SR); t = A(n)
    fr = f0 * (1 + 0.5 * np.exp(-t / 0.05)); ph = 2 * np.pi * np.cumsum(fr) / SR
    x = np.sin(ph) * np.exp(-t / (dur / 5)) * smooth(t / att)
    nz = sos_f(rng.standard_normal(n).astype(np.float32), 'low', 400) * np.exp(-t / 0.05) * smooth(t / att) * 0.4
    put(t0, (x + nz) * 0.5, level, rng.uniform(-.2, .2), send, curve)

def shaker(t0, level=1.0, curve=None):
    n = int(0.12 * SR); t = A(n)
    x = sos_f(rng.standard_normal(n).astype(np.float32), 'high', 5000) * np.exp(-t / 0.03) * smooth(t / 0.01)
    put(t0, x * 0.1, level, rng.uniform(-.6, .6), 0.15, curve)

def tick(t0, f=1700, level=1.0, curve=None, pan=0.0):
    n = int(0.12 * SR); t = A(n)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012) + 0.5 * np.sin(2 * np.pi * f * 2.3 * t) * np.exp(-t / 0.006)
    x *= smooth(t / 0.0015)
    put(t0, x * 0.2, level, pan, 0.45, curve)

def noise_bed(t0, t1, kind, fc, level, curve=None, att=3.0, rel=3.0, send=0.3, q=None, pan_w=0.0):
    """filtered noise texture over [t0,t1] (smooth in/out); stereo-decorrelated"""
    n = int((t1 - t0) * SR)
    for ch in (0, 1):
        x = rng.standard_normal(n).astype(np.float32)
        if kind == 'bp':
            x = sos_f(x, 'bandpass', [fc[0], fc[1]], 2)
        else:
            x = sos_f(x, kind, fc, 2)
        x *= env_ads(n, att, rel) * level * 0.1
        if curve is not None: x *= curve((int(t0 * SR) + np.arange(n)) / SR).astype(np.float32)
        i0 = int(t0 * SR); (dL if ch == 0 else dR)[i0:i0 + n] += x[:min(n, N - i0)]
        wet[i0:i0 + n] += 0.5 * x[:min(n, N - i0)] * send

def glide(t0, t1, f0, f1, level, tab='soft', att=2.0, rel=2.0, send=0.4, pan=0.0):
    n = int((t1 - t0 + rel) * SR); t = A(n); k = np.clip(t / (t1 - t0), 0, 1)
    f = f0 * (f1 / f0) ** k
    x = osc(tab, f, n) + 0.7 * osc(tab, f * 1.006, n, .4)
    put(t0, x * env_ads(n, att, rel) * 0.1, level, pan, send)

# ================================================================ THE SCORE ====================================
def score():
    a = ACT
    # ---- drone: shared pitch centre. Levels: low in the hook, deep in birth/theia, absent-ish in the cold, soft in the end
    drone(interp([(0, 0), (6, .25), (28, .35), (40, .8), (58, 1.0), (75, .6), (100, .5), (128, .35), (163, .5), (205, .7),
                  (212, .4), (243, .2), (258, .15), (264, .35), (276, .5), (298, .35), (338, .5), (344, .8), (362, .7),
                  (385, .8), (393, .5), (430, .4), (505, .4), (510, .4), (527, .15), (533, .08), (536, .4), (549, .5),
                  (580, .5), (593, .35), (597, 0), (599.76, 0)]))

    # ---- HOOK 0-28: mysterious, intimate; clock pulse; rewind swell 6.2-8.3
    plan = [(2, 'Am9'), (11, 'Fma7'), (20, 'Am9'), (30, 'Asus2')]
    pad_chords(plan, 0.7, curve=interp([(0, 0), (6, .35), (28, .5), (40, .5), (50, 0)]), bright=0.05)
    t, k = 1.6, 0
    while t < 44:                                           # soft clock: tick / tock, slow fade in and out
        c = interp([(0, 0), (3, .5), (23, .55), (28, .35), (36, .1), (44, 0)])
        tick(t, 1700 if k % 2 == 0 else 1250, 0.9, curve=c, pan=-0.2 + 0.4 * (k % 2))
        t += 0.8; k += 1
    for tb, m in ((3.0, 81), (9.0, 84), (13.5, 76), (18.0, 81), (23.5, 88)):       # sparse high glass drops
        bell(tb, m, 0.5, dur=7, glass=True, pan=rng.uniform(-.7, .7))
    # rewind: a reversed bell cluster + noise rising, softly closed by a warm chord entrance (pad Fma7 at 11 s already near)
    rev = np.zeros(int(3.0 * SR), np.float32); tt = A(len(rev))
    for m in (57, 64, 69, 76, 81):
        f = float(mf(m)); rev += np.sin(2 * np.pi * f * tt + rng.random() * 6) * np.exp(-tt / 0.55)
    rev = rev[::-1].copy()
    nz = sos_f(rng.standard_normal(len(rev)).astype(np.float32), 'bandpass', [900, 6000], 2)
    sw = np.linspace(0, 1, len(rev)) ** 2.5
    rev = (rev * 0.07 + nz * sw * 0.55 * 0.1)
    rev *= smooth(np.arange(len(rev)) / (0.8 * SR)) * smooth((len(rev) - np.arange(len(rev))) / (0.55 * SR))
    put(5.8, rev, 1.0, 0, 0.8)

    # ---- BIRTH 28.17-54: deep, dark; slow rumble of the forming planet
    noise_bed(a['hook'][1] - 3, a['theia'][0] + 3, 'low', 90, 2.2, curve=interp([(25, 0), (34, .7), (46, 1.0), (58, 1.4), (62, .3), (70, 0)]),
              att=4, rel=5, send=0.1)
    pad_chords([(30, 'low'), (42, 'lowfifth'), (50, 'Bb'), (58.2, 'low')], 0.7, tab='soft', bright=0.0, send=0.35,
               curve=interp([(26, 0), (34, .6), (50, .9), (58, .5), (64, 0)]))
    for tb, m in ((33, 45), (39, 40), (45, 38), (50, 37), (54, 33)):   # low, rare, slow plucks
        pluck(tb, m, 0.8, dur=3.5, send=0.7, bright=.4)
    # tension 46..58.2: a rising cluster, a quickening pulse
    glide(44, 58.0, 110, 311, 0.55, tab='soft', att=6, rel=0.25)
    glide(46, 58.0, 116.5, 330, 0.3, tab='soft', att=6, rel=0.25)
    t = 48.0; gap = 1.2
    while t < T_IMPACT - 0.3:
        tom(t, 52, 0.12 + 0.5 * (t - 48) / 10, dur=1.2); gap = max(0.45, gap * 0.9); t += gap

    # ---- THEIA ACCENT 1: deep cinematic boom at T_IMPACT, long ringing aftermath, then awe
    boom(T_IMPACT)
    pad_chords([(T_IMPACT + 3, 'Am9'), (68, 'Dly'), (82, 'Fma7'), (92, 'Am9'), (a['oceans'][0] + 3, 'Dm9')], 0.75, bright=.1, send=.7,
               curve=interp([(T_IMPACT, 0), (T_IMPACT + 5, .5), (66, .6), (80, .8), (100, .7), (108, 0)]))
    for tb, m in ((T_MOON + 0.5, 81), (T_MOON + 4, 88), (T_MOON + 9.5, 84), (79, 76), (86, 81), (95, 88)):
        bell(tb, m, 0.6, dur=9, pan=rng.uniform(-.6, .6))

    # ---- OCEANS 103-128.7: calmer, flowing arpeggio
    flow = [74, 77, 81, 84, 81, 77, 69, 72]
    t, k = a['oceans'][0] + 2, 0
    while t < a['life'][0] + 3:
        c = interp([(100, 0), (108, .6), (122, .6), (130, .2), (134, 0)])
        if rng.random() < 0.85: pluck(t, flow[k % 8] + (0 if (k // 8) % 2 == 0 else -2), 0.8 * c(t), dur=2.2, pan=rng.uniform(-.7, .7), send=0.7, bright=.5)
        t += 0.62; k += 1

    # ---- LIFE 128.7-163.45: gentle, wondering; the first light melody (pentatonic, high)
    pad_chords([(a['life'][0] - 1, 'Dm9'), (136, 'Fma7'), (146, 'C'), (154, 'G'), (162, 'Am9'), (170, 'Fma7')], 0.75, bright=.2, send=.6,
               curve=interp([(124, 0), (132, .7), (150, .85), (166, .6), (172, 0)]))
    mel = [(131.6, 84, 3), (134.2, 88, 3), (137.0, 91, 4), (141.0, 88, 3), (145.0, 84, 3), (148.0, 91, 4), (151.4, 93, 4), (154.8, 88, 3),
           (158.0, 84, 4), (161.5, 81, 6)]
    for tb, m, d in mel: bell(tb, m, 0.8, dur=7, pan=0.25)
    t = 130.0
    while t < 164:
        c = interp([(128, 0), (136, .4), (156, .4), (166, 0)])
        pluck(t, [69, 72, 76, 79, 76, 72][int((t - 130) / 1.1) % 6], 0.35 * c(t), dur=2, pan=-0.4, send=.8, bright=.4)
        t += 1.1

    # ---- OXYGEN 163.45-211.36: slow build, a little ominous, resolves on «кожен твій вдих»
    ox0 = a['oxygen'][0]
    pad_chords([(ox0 - 1, 'Am'), (174, 'Fma7'), (184, 'Dm'), (192, 'Bb'), (200, 'E'), (T_OX - 0.5, 'Aadd9'), (T_OX + 12, 'Aadd9')],
               0.85, bright=.3, send=.6, curve=interp([(160, 0), (170, .5), (190, .85), (200, 1.0), (T_OX + 3, .9), (T_OX + 8, .6), (T_OX + 12, 0)]))
    t = ox0 + 4
    while t < T_OX - 1:                                    # a slow, slightly quickening ostinato in the low-mid
        c = interp([(160, 0), (175, .5), (198, 1.0), (T_OX - 1, .2)])
        pluck(t, [45, 52, 57, 52][int((t - ox0) / 1.3) % 4] - (1 if 190 < t < 202 and int((t - ox0) / 1.3) % 4 == 2 else 0), 0.55 * c(t), dur=2.4, pan=0, send=.4, bright=.5)
        t += 1.3 - 0.4 * (t - ox0) / 50
    for tb, m in ((T_OX + 0.4, 69), (T_OX + 2.2, 76), (T_OX + 4.6, 81), (T_OX + 7.5, 85)):
        bell(tb, m, 0.7, dur=9)

    # ---- BORING BILLION 211.36-242.78: patient, nearly ambient
    pad_chords([(a['boring'][0], 'Aadd9'), (222, 'Dly'), (232, 'Asus2'), (242, 'Aadd9'), (252, 'Asus2')], 0.8, bright=.1, send=.7,
               curve=interp([(a['boring'][0] - 2, 0), (a['boring'][0] + 5, .55), (238, .5), (246, .3), (256, 0)]))
    for tb, m in ((216, 76), (223, 81), (230, 74), (236.5, 79)): bell(tb, m, 0.35, dur=10)

    # ---- SNOWBALL 242.78-264.21: cold, glassy, sparse; thaw at «Врятували вулкани»
    sb0, sb1 = a['snowball']
    pad_chords([(sb0 - 1, 'low'), (T_THAW - 1, 'low')], 0.0)             # (no warm pad here: the cold has no low end)
    for tb, m in ((sb0 + 1.0, 93), (sb0 + 4.0, 96), (sb0 + 6.5, 88), (sb0 + 9.5, 100), (sb0 + 12, 91), (sb0 + 13.5, 96), (sb0 + 16.5, 84)):
        bell(tb, m, 0.5, dur=8, glass=True, pan=rng.uniform(-.8, .8), send=1.0)
    for m, tb, d in ((86, sb0 - 1, 14), (89, sb0 + 1, 14)):             # high icy sines, hanging
        glide(tb, tb + d, mf(m), mf(m) * 1.002, 0.22, tab='sine', att=5, rel=5, send=1.0, pan=rng.uniform(-.4, .4))
    pad_chords([(T_THAW - 2, 'Asus2'), (sb1 + 2, 'Aadd9'), (sb1 + 12, 'Dm9')], 0.8, bright=.15, send=.7,
               curve=interp([(T_THAW - 3, 0), (T_THAW + 5, .4), (sb1, .6), (sb1 + 5, .2), (sb1 + 10, 0)]))
    for tb, m in ((T_THAW + 3, 81), (T_THAW + 6.5, 85), (T_THAW + 10.5, 88)): bell(tb, m, 0.5, dur=8)

    # ---- EDIACARA 264.21-275.74: mysterious, soft
    ed0 = a['ediacara'][0]
    pad_chords([(ed0, 'Dm9'), (270, 'Am9'), (278, 'Dm9')], 0.55, bright=.1, send=.8, curve=interp([(ed0 - 2, 0), (ed0 + 4, .55), (276, .5), (285, .3), (292, 0)]))
    for tb, m in ((ed0 + 1, 72), (ed0 + 5, 76), (ed0 + 8.5, 69)): bell(tb, m, 0.45, dur=9, pan=rng.uniform(-.5, .5))

    # ---- CAMBRIAN 275.74-298.01: «І раптом — вибух»: pulse and rhythm rise, no hard hit
    cb0, cb1 = a['cambrian']
    perc_c = interp([(T_BOOM_CAMBR - 1, 0), (T_BOOM_CAMBR + 6, .45), (T_BOOM_CAMBR + 14, .8), (cb1 - 4, .8), (cb1 + 8, .4), (cb1 + 16, 0)])
    pad_chords([(cb0, 'Am'), (284, 'F'), (291, 'C'), (298, 'G'), (306, 'Am')], 0.85, bright=.25, send=.5,
               curve=interp([(cb0 - 2, 0), (cb0 + 6, .5), (cb1 - 3, .8), (cb1 + 10, .6), (cb1 + 18, 0)]))
    bt = 0.5
    t = T_BOOM_CAMBR
    ar = [57, 64, 69, 72, 76, 72, 69, 64]; k = 0
    while t < cb1 + 12:
        c = perc_c(t)
        if c > 0.01:
            if k % 8 in (0, 5): tom(t, 68 if k % 8 == 0 else 80, 0.45 * c, dur=0.9, send=.25, att=0.02)
            if k % 2 == 1: shaker(t, 0.8 * c)
            if k % 2 == 0 and rng.random() < .8 or k % 4 == 3:
                pluck(t, ar[k % 8] + (12 if k > 24 and k % 3 == 0 else 0), 0.7 * c, dur=1.2, pan=rng.uniform(-.8, .8), send=.4)
        t += bt / 1; k += 1

    # ---- LAND 298-314: lush, organic; pulse eases, a reed-flute melody
    ld0, ld1 = a['land']
    mel = [(300, 76, 4.5), (305, 79, 3), (308.5, 81, 4.5), (314, 79, 4), (319, 76, 5)]
    for tb, m, d in mel: horn(tb, tb + d, m, 0.55, att=0.7, rel=1.6, pan=0.3, send=0.6, tab='hollow', vib=0.006)
    pad_chords([(ld0 + 4, 'Fma7'), (312, 'Cma7'), (322, 'Fma7'), (332, 'Gadd'), (342, 'Am')], 0.8, bright=.25, send=.5,
               curve=interp([(ld0, 0), (ld0 + 6, .7), (335, .75), (345, 0)]))

    # ---- COAL 314-338: lush, warm, wet; marimba-like plucks and a low organic line
    cl0, cl1 = a['coal']
    t, k = cl0 + 0.5, 0
    seq = [64, 67, 71, 74, 71, 67, 62, 66]
    while t < cl1 + 2:
        c = interp([(cl0 - 1, 0), (cl0 + 5, .55), (cl1 - 2, .5), (cl1 + 3, 0)])
        if rng.random() < 0.75: pluck(t, seq[k % 8] + (12 if k % 16 > 8 else 0), 0.5 * c(t), dur=2.0, pan=rng.uniform(-.6, .6), send=.5, bright=.6)
        t += 0.75; k += 1
    for tb, m, d in ((318, 52, 6), (326, 50, 6), (333, 48, 7)): horn(tb, tb + d, m, 0.5, att=1.5, rel=2.0, send=.4, tab='hollow', vib=0.004)

    # ---- PERMIAN 338.22-363.71: dark, heavy, sorrowful; ACCENT 2: the eruption
    pm0, pm1 = a['permian']
    pad_chords([(pm0 - 1, 'Am'), (346, 'Fm'), (352, 'Bb'), (358, 'Gm'), (364, 'Am'), (372, 'Dm')], 0.9, bright=.1, send=.6, tab='soft',
               curve=interp([(pm0 - 3, 0), (pm0 + 6, .7), (T_ERUPT + 6, 1.0), (pm1 + 3, .8), (pm1 + 12, 0)]))
    for tb, m, d in ((pm0 + 2, 57, 6), (pm0 + 9, 56, 6), (T_ERUPT + 6, 53, 7), (T_ERUPT + 14, 52, 8)):   # a low sorrowful cello-like line
        horn(tb, tb + d, m, 0.7, att=1.2, rel=2.5, pan=-0.2, send=.5, tab='soft', vib=0.007)
    eruption(T_ERUPT)

    # ---- DINOS 363.71-392.87: grand but restrained; tension builds to the end
    dn0, dn1 = a['dinos']
    pad_chords([(dn0 - 0.5, 'Dm'), (372, 'Bb'), (378, 'F'), (383, 'Gm'), (388, 'Bb'), (393, 'E'), (400, 'low')], 0.95, bright=.35, send=.6,
               curve=interp([(dn0 - 4, 0), (dn0 + 6, .7), (380, .9), (dn1 + 4, 1.0), (dn1 + 12, .4), (dn1 + 20, 0)]))
    hm = [(dn0 + 2, dn0 + 8, 62), (dn0 + 8, dn0 + 14, 65), (dn0 + 14, dn0 + 20, 69), (dn0 + 20, dn0 + 24, 67), (dn0 + 24, dn0 + 29, 65)]
    for tb, te, m in hm: horn(tb, te, m, 0.8, att=1.0, rel=1.4, pan=-0.2, send=.6)
    t, k = dn0 + 4, 0
    while t < dn1 + 1:                                      # restrained taiko-ish pulse, quickening to the end
        c = interp([(dn0, 0), (dn0 + 8, .35), (dn1 - 14, .45), (dn1 - 4, .8), (dn1 + 4, .5), (dn1 + 12, 0)])
        step = 2.4 if t < dn1 - 14 else 2.4 - 1.4 * (t - (dn1 - 14)) / 14
        tom(t, 62 if k % 2 == 0 else 74, 0.4 * c(t), dur=1.6, send=.5, att=0.03)
        t += step; k += 1
    glide(dn1 - 12, dn1 + 2, mf(57), mf(70), 0.3, tab='soft', att=9, rel=3)      # rising tension into the asteroid

    # ---- ASTEROID 392.87-509.57: low level under its own effects: tense -> mournful -> hopeful
    as0, as1 = a['asteroid']
    pad_chords([(as0 + 2, 'low'), (418, 'lowfifth'), (434, 'Dm'), (450, 'Am'), (462, 'F'), (474, 'Dm'), (486, 'F'), (496, 'C'),
                (as1 + 2, 'Am'), (as1 + 14, 'Am')], 0.9, bright=.1, send=.7,
               curve=interp([(as0, 0), (as0 + 8, .8), (460, .9), (480, .9), (as1 + 4, .8), (as1 + 14, 0)]))
    t, k = as0 + 3, 0
    while t < 432:                                          # a nervous, slow-accelerating clock
        c = interp([(as0, 0), (as0 + 8, .5), (420, .7), (432, 0)])
        tick(t, 900 if k % 2 == 0 else 800, 0.9 * c(t), pan=0)
        t += max(0.5, 1.1 - 0.012 * (t - as0)); k += 1
    glide(402, 430, 220, 233, 0.35, tab='soft', att=10, rel=8)
    for tb, te, m in ((438, 446, 57), (448, 457, 53), (459, 468, 52), (470, 480, 50)):
        horn(tb, te, m, 0.7, att=1.4, rel=3, send=.7, tab='soft', vib=0.007)
    for tb, m in ((488, 76), (493, 81), (498, 84), (503, 88), (507, 93)): bell(tb, m, 0.7, dur=9, pan=rng.uniform(-.5, .5))

    # ---- MAMMALS 509.57-549.04: warm, rising, human; hush at «за шість секунд до півночі», warm chord on «Ти.»
    mm0, mm1 = a['mammals']
    pad_chords([(mm0 + 1, 'Am'), (520, 'F'), (T_6S - 5, 'C'), (T_6S + 1.0, 'C')], 0.9, bright=.3, send=.55,
               curve=interp([(mm0 - 3, 0), (mm0 + 5, .55), (T_6S - 6, .9), (T_6S - 1, .15), (T_6S + 1.5, 0)]))
    t, k = mm0 + 4, 0
    seq = [57, 64, 69, 72, 69, 64]
    while t < T_6S - 1:
        c = interp([(mm0, 0), (mm0 + 8, .4), (T_6S - 6, .8), (T_6S - 1, 0)])
        pluck(t, seq[k % 6] + (12 if k % 12 > 5 else 0), 0.6 * c(t), dur=1.8, pan=rng.uniform(-.5, .5), send=.5)
        t += 0.9; k += 1
    ty_plan = [(T_TY - 0.9, 'Aadd9'), (T_TY + 9, 'D'), (T_TY + 17, 'F#m'), (mm1 + 4, 'Bm')]
    pad_chords(ty_plan, 1.0, bright=.4, send=.8, curve=interp([(T_TY - 2, 0), (T_TY + 2, 1.0), (T_TY + 16, 1.0), (mm1 + 12, .8)]))
    bell(T_TY - 0.1, 76, 1.0, dur=10); bell(T_TY + 0.2, 81, 0.8, dur=10); bell(T_TY + 1.8, 88, 0.6, dur=10)
    for tb, m in ((T_TY + 5, 81), (T_TY + 8, 85), (T_TY + 12, 88), (T_TY + 16, 83)): bell(tb, m, 0.5, dur=8)

    # ---- FUTURE 549.04-592.76: wide, hopeful, reflective; a full gentle swell, then rest into the end card
    fu0, fu1 = a['future']
    pad_chords([(mm1 + 4, 'Bm'), (558, 'G'), (566, 'D'), (T_ANTH - 1, 'Dly'), (578, 'Bm'), (584, 'G'), (T_RESOLVE - 3, 'Dly'),
                (T_RESOLVE + 0.5, 'Aadd9'), (T_RESOLVE + 12, 'Aadd9')], 1.0, bright=.4, send=.85,
               curve=interp([(mm1 + 3, .8), (560, .9), (572, 1.0), (584, .9), (T_RESOLVE, .7), (T_RESOLVE + 3, .55), (596, .2), (598.8, 0)]))
    fm = [(552, 81), (556, 85), (560.5, 88), (565, 90), (569, 88), (T_ANTH + 1.5, 93), (577, 90), (581, 88), (585, 85), (T_RESOLVE - 1, 88)]
    for tb, m in fm: bell(tb, m, 0.55, dur=9, pan=rng.uniform(-.4, .4), send=1.0)
    t, k = 556, 0
    while t < T_RESOLVE - 2:                                # a very light, wide arpeggio under the swell
        c = interp([(552, 0), (562, .5), (582, .5), (T_RESOLVE - 2, 0)])
        pluck(t, [69, 76, 81, 85, 81, 76][k % 6] + (0 if (k // 6) % 2 == 0 else -2), 0.4 * c(t), dur=2.4, pan=rng.uniform(-.8, .8), send=.9, bright=.4)
        t += 1.0; k += 1
    # end card: warm A major resolution (bells decay), nothing after it but the fade
    bell(T_RESOLVE - 0.2, 69, .7, dur=9); bell(T_RESOLVE + 0.2, 76, .6, dur=9); bell(T_RESOLVE + 1.0, 81, .5, dur=9)

def boom(T):
    n = int(14 * SR); t = A(n)
    sub = np.sin(2 * np.pi * np.cumsum(28 + 52 * np.exp(-t / 0.9)) / SR) * np.exp(-t / 2.8) * smooth(t / 0.006)
    body = np.sin(2 * np.pi * np.cumsum(46 + 130 * np.exp(-t / 0.22)) / SR) * np.exp(-t / 0.9) * smooth(t / 0.004)
    nz = sos_f(rng.standard_normal(n).astype(np.float32), 'low', 420, 2) * np.exp(-t / 1.2) * smooth(t / 0.003)
    crack = sos_f(rng.standard_normal(n).astype(np.float32), 'bandpass', [900, 4500], 2) * np.exp(-t / 0.12) * smooth(t / 0.002)
    x = 1.0 * sub + 0.7 * body + 0.45 * nz + 0.12 * crack
    put(T, x * 0.7, 1.0, 0, 0.35)
    # the ringing aftermath: gong-like inharmonic partials on A, long and wide
    n2 = int(22 * SR); t2 = A(n2); g = np.zeros(n2, np.float32)
    for r, a_, d in ((1, 1, 1.0), (1.51, .6, .9), (2.0, .7, .8), (2.74, .45, .7), (3.9, .3, .5), (5.4, .2, .4)):
        for dt in (0, 0.9):
            g += a_ * np.sin(2 * np.pi * (110 * r + dt * r) * t2) * np.exp(-t2 / (6.0 * d)) * 0.5
    g *= smooth(t2 / 0.05)
    put(T + 0.02, g * 0.12, 1.0, 0, 1.0)
    glide(T + 0.1, T + 8, 55, 54, 0.9, tab='soft', att=0.4, rel=6)

def eruption(T):
    n = int(16 * SR); t = A(n)
    nz = sos_f(rng.standard_normal(n).astype(np.float32), 'low', 160, 2)
    nz = nz * smooth(t / 1.6) * np.exp(-np.maximum(t - 1.6, 0) / 4.5)
    sub = np.sin(2 * np.pi * np.cumsum(38 + 14 * np.exp(-t / 2.5)) / SR) * smooth(t / 1.2) * np.exp(-np.maximum(t - 1.2, 0) / 4.0)
    put(T - 0.8, (nz * 1.5 + sub * 1.1) * 0.6, 1.0, 0, 0.3)
    for k in range(3): tom(T + 0.6 + k * 0.9, 48, 0.8, dur=2.5, send=.6, att=0.04)
    glide(T, T + 10, 73.4, 73.4, 0.5, tab='horn', att=1.5, rel=6, send=.5)       # a heavy, low brass-like swell on D

if __name__ == '__main__':
    score()
    # reverb: a dark generated hall (6 s), different noise for L / R, convolved with the send bus
    ir_n = int(6.0 * SR); tt = A(ir_n); irs = []
    for c in range(2):
        z = rng.standard_normal(ir_n)
        lo = sos_f(z, 'low', 1800, 2) * np.exp(-tt / 1.9); hi = sos_f(z, 'high', 1800, 2) * np.exp(-tt / 0.7)
        ir = (lo + 0.5 * hi) * smooth(tt / 0.03); irs.append(ir / np.sqrt((ir ** 2).sum()))
    wl = signal.oaconvolve(wet, irs[0].astype(np.float32))[:N]; wr = signal.oaconvolve(wet, irs[1].astype(np.float32))[:N]
    L = dL + wl * 1.0; R = dR + wr * 1.0
    g = 10 ** (master_db(A(N)) / 20).astype(np.float32) if False else (10 ** (master_db(A(N)) / 20)).astype(np.float32)
    L *= g; R *= g
    # clean ending: fade the last 3 s completely to zero
    fo = smooth((DUR - 0.3 - A(N)) / 2.7).astype(np.float32); L *= fo; R *= fo
    # gentle DC / sub-rumble guard
    L = sos_f(L, 'high', 22, 2); R = sos_f(R, 'high', 22, 2)
    L, R, gain = normalize(L, R, -20.0)
    wav_write(os.path.join(WORK, 'music.wav'), L, R)
    print('music.wav', ebur(os.path.join(WORK, 'music.wav')), 'impact', round(T_IMPACT, 2), 'erupt', round(T_ERUPT, 2))
