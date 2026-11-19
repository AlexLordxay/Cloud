# «А ти уявляєш Сонце так?» — sound effects synthesised from noise and sines (the author's rule: no AI effects).
# Stereo 44.1 kHz -> sfx/*.wav (helpers from nuclear_winter/synth_sfx.py)
#   field.wav   4 s — a summer morning over the field: a soft breeze in the leaves and a few larks
#   lift.wav    5 s — lifting off: air rushing past, rising in pitch, thinning out to nothing (space)
#   rush.wav    3 s — the rush to the Sun: a deep whoosh with a bright tail
#   pour.wav    3 s — the Earths pouring in: a soft granular patter
#   heavy.wav   3 s — the Sun's pan sinking: a slow, heavy creak and thud
#   glow.wav    3 s — the spot lights up on its own: a high glassy shimmer
#   boil.wav    7 s — over the surface: a deep boiling roar with slow swells
#   streak.wav  6 s — riding the light: an airy, rising rush
#   dive.wav    3 s — down to the Earth: a falling whoosh into wind
#   off.wav     2.5 s — the Sun goes out: a sucking, falling tone, then nothing
#   dark.wav    4 s — the darkness reaches the Earth: a deep, soft thud
#   ignite.wav  3 s — the Sun lights up again: a reversed swell into a bright burst
#   python3 synth_sfx.py
import os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(TOOLS, 'scenes', 'nuclear_winter'))
import synth_sfx as S
from synth_sfx import bp, lp, hp, brown, white, lfo, env, stereo, SR
S.OUT = os.path.join(HERE, 'sfx')

def tt(n): return np.arange(n) / SR
def sweep(f0, f1, n, curve=1.0):
    k = (tt(n) / (n / SR)) ** curve
    f = f0 * (f1 / f0) ** k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

def field(n):
    t = tt(n)
    breeze = bp(white(n), 300, 3000) * (0.25 + 0.2 * lfo(n, 0.3)) * 0.18
    leaves = hp(white(n), 2500) * (0.5 + 0.5 * lfo(n, 0.7)) ** 3 * 0.05
    birds = np.zeros(n)
    rng = np.random.default_rng(11)
    for _ in range(9):
        t0 = rng.uniform(0.2, 3.4); d = rng.uniform(0.05, 0.14)
        i0 = int(t0 * SR); m = int(d * SR)
        if i0 + m >= n: continue
        f0 = rng.uniform(3200, 4800); f1 = f0 * rng.uniform(0.8, 1.3)
        ch = sweep(f0, f1, m) * np.sin(np.pi * np.arange(m) / m) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * 38 * np.arange(m) / SR))
        birds[i0:i0 + m] += ch * rng.uniform(0.04, 0.09)
    fade = np.clip(t / 0.3, 0, 1) * np.clip((n / SR - t) / 1.0, 0, 1)
    return (breeze + leaves + birds) * fade

def lift(n):
    t = tt(n); T = n / SR
    shape = np.clip(t / 0.6, 0, 1) * np.clip((T - t) / 2.2, 0, 1) ** 1.5
    x = np.zeros(n); w = white(n)
    for lo, hi, g in ((150, 700, 0.6), (700, 2500, 0.35), (2500, 8000, 0.18)):
        x += bp(w, lo, hi) * g
    tone = sweep(60, 240, n, 1.4) * 0.15
    return (x * (0.7 + 0.3 * lfo(n, 2.3)) + tone) * shape * 0.55

def rush(n):
    t = tt(n); T = n / SR
    shape = np.sin(np.pi * np.clip(t / T, 0, 1)) ** 2
    low = lp(brown(n), 200) * 1.4
    air = bp(white(n), 400, 5000) * 0.45
    tone = sweep(55, 140, n) * 0.35
    return (low + air + tone) * shape

def pour(n):
    t = tt(n); T = n / SR
    x = np.zeros(n); rng = np.random.default_rng(5)
    for _ in range(420):
        i = int(rng.uniform(0, T - 0.05) * SR); m = int(0.012 * SR)
        f = rng.uniform(1800, 5200)
        x[i:i + m] += np.sin(2 * np.pi * f * np.arange(m) / SR) * np.exp(-np.arange(m) / (0.003 * SR)) * rng.uniform(0.02, 0.06)
    return x * np.clip(t / 0.5, 0, 1) * np.clip((T - t) / 0.6, 0, 1)

def heavy(n):
    t = tt(n)
    creak = bp(white(n), 120, 600) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t)) * env(n, 0.3, 1.2) * 0.35
    thud = np.sin(2 * np.pi * np.cumsum(40 * np.exp(-np.maximum(t - 1.55, 0) / 0.6) + 25) / SR) * env(n, 0.01, 0.9, 1.55) * 1.2
    return creak + thud + lp(brown(n), 120) * env(n, 0.05, 1.0, 1.55) * 0.8

def glow(n):
    t = tt(n)
    x = np.zeros(n)
    for f, a in ((2093, 0.5), (2637, 0.35), (3136, 0.3), (4186, 0.2)):
        x += np.sin(2 * np.pi * f * t * (1 + 0.002 * np.sin(2 * np.pi * 5 * t))) * a
    return x * env(n, 0.25, 1.4) * 0.12 + hp(white(n), 6000) * env(n, 0.2, 0.8) * 0.03

def boil(n):
    t = tt(n); T = n / SR
    shape = np.clip(t / 1.0, 0, 1) * np.clip((T - t) / 1.5, 0, 1)
    roar = lp(brown(n), 160) * (0.6 + 0.4 * lfo(n, 0.6)) * 1.6
    bub = bp(white(n), 80, 400) * (0.5 + 0.5 * lfo(n, 6.0)) ** 2 * 0.6
    return (roar + bub) * shape

def streak(n):
    t = tt(n); T = n / SR
    shape = np.clip(t / 0.8, 0, 1) * np.clip((T - t) / 1.2, 0, 1)
    air = bp(white(n), 900, 7000) * (0.6 + 0.4 * lfo(n, 3.1)) * 0.35
    tone = sweep(220, 660, n, 1.2) * 0.06
    return (air + tone) * shape

def dive(n):
    t = tt(n); T = n / SR
    shape = np.sin(np.pi * np.clip(t / T, 0, 1)) ** 1.5
    x = bp(white(n), 300, 4000) * 0.5 + lp(brown(n), 300) * 0.6
    return (x + sweep(300, 70, n) * 0.2) * shape

def off(n):
    t = tt(n)
    suck = bp(white(n), 200, 3000) * np.clip(1 - t / 0.5, 0, 1) ** 2 * 0.5
    tone = sweep(320, 40, n, 0.6) * np.exp(-t / 0.6) * 0.5
    return suck + tone

def dark(n):
    t = tt(n)
    f = 22 + 30 * np.exp(-t / 0.4)
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.02, 1.4) * 1.3
    return thump + lp(brown(n), 90) * env(n, 0.05, 2.2) * 1.0

def ignite(n):
    t = tt(n); T0 = 1.2
    pre = (bp(white(n), 500, 6000) * np.clip(t / T0, 0, 1) ** 3 * (t < T0)) * 0.5
    burst = (lp(brown(n), 250) * 1.4 + bp(white(n), 300, 8000) * 0.5) * env(n, 0.005, 1.2, T0)
    shine = np.sin(2 * np.pi * 1760 * t) * env(n, 0.01, 1.6, T0) * 0.08
    return pre + burst + shine

if __name__ == '__main__':
    os.makedirs(S.OUT, exist_ok=True)
    todo = sys.argv[1:] or ['field', 'lift', 'rush', 'pour', 'heavy', 'glow', 'boil', 'streak', 'dive', 'off', 'dark', 'ignite']
    recipes = {'field': (field, 4), 'lift': (lift, 5), 'rush': (rush, 3), 'pour': (pour, 3), 'heavy': (heavy, 3), 'glow': (glow, 3),
               'boil': (boil, 7), 'streak': (streak, 6), 'dive': (dive, 3), 'off': (off, 2.5), 'dark': (dark, 4), 'ignite': (ignite, 3)}
    for k in todo:
        f_, sec = recipes[k]
        S.save(f'{k}.wav', stereo(f_, int(SR * sec)))
        print(k)
