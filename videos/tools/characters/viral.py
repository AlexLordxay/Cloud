# What every "viral" scene of the stick cartoon shares: counters racing up on a log scale, the milestone bump,
# hearts floating up, and the sound (comment pops, a "ding" at 10K / 100K / 1M, a rising whoosh).
import math, os, random
import numpy as np


def grow(t, t0, t1, top, start=None):
    """A counter racing up on a log scale from `start` (default top/2000) to `top` between t0 and t1 — busy from frame 0."""
    x = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    a = math.log10(start or top / 2000)
    return 10 ** (a + (math.log10(top) - a) * x ** 1.15)


MILESTONES = [10_000, 100_000, 1_000_000]


def crossing(f, m, t0=0.0, t1=10.0):
    """When the counter f(t) passes m (bisection)."""
    lo, hi = t0, t1
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < m else (lo, mid)
    return hi


def milestone_pop(f, t, t1=10.0):
    """0..1 bump just after the views pass 10K, 100K, 1M."""
    best = 0.0
    for m in MILESTONES:
        age = t - crossing(f, m, 0.0, t1)
        if 0 <= age < 0.35: best = max(best, math.sin(age / 0.35 * math.pi))
    return best


def hearts(seed, n, t0, t1, x0, x1):
    random.seed(seed)
    return [(random.uniform(t0, t1), random.uniform(x0, x1), random.uniform(0.8, 1.3)) for _ in range(n)]


def draw_hearts(cv, t, items, heart_fn, y0=1400, cols=((254, 44, 85), (243, 140, 160))):
    for (t0, x, sc) in items:
        age = t - t0
        if 0 <= age < 1.6:
            heart_fn(cv, (x + 30 * math.sin(age * 5 + x), y0 - age * 650), 52 * sc * (1 - age / 2.2), cols[int(x) % 2])


def sound(path, dur, comment_times, f_views, extra=None, sr=44100):
    """Pops for the comments, a "ding" when the views pass 10K/100K/1M, a soft rising whoosh; `extra(y, sr)` adds more."""
    n = int(dur * sr)
    y = np.zeros(n)
    rnd = random.Random(5)

    def add(t0, sig):
        k = int(t0 * sr)
        if 0 <= k < n: y[k:k + len(sig)] += sig[:n - k]
    for t0 in comment_times:
        if t0 < 0: continue
        m = int(0.08 * sr)
        add(t0, 0.35 * np.exp(-np.arange(m) / (0.012 * sr)) * np.sin(2 * np.pi * (900 + 600 * rnd.random()) * np.arange(m) / sr))
    for m_ in MILESTONES:
        tc = crossing(f_views, m_, 0.0, dur)
        if tc < dur - 0.05:
            m = int(0.6 * sr); tt = np.arange(m) / sr
            add(tc, 0.5 * np.exp(-tt / 0.18) * (np.sin(2 * np.pi * 1318 * tt) + 0.5 * np.sin(2 * np.pi * 1976 * tt)))
    tt = np.arange(n) / sr
    noise = np.convolve(np.random.default_rng(1).standard_normal(n), np.ones(40) / 40, mode='same')
    y += 0.12 * noise * np.clip((tt + 0.5) / dur, 0, 1) ** 2
    if extra: extra(y, sr)
    y = y / max(1e-6, np.abs(y).max()) * 0.7
    from scipy.io import wavfile
    wavfile.write(path, sr, (np.stack([y, y], 1) * 32767).astype(np.int16))
    return path
