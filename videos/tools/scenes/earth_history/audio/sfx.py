#!/usr/bin/env python3
# Sound effects for «Історія Землі», all synthesized from noise and tones (no recordings, no AI tools).
#   python3 scenes/earth_history/audio/sfx.py    -> work/earth_history/sfx.wav (48 kHz stereo, = timeline duration, ~ -24 LUFS)
# Silent during the asteroid insert (it has its own track). Cue list: cues.md.
import numpy as np
from scipy import signal
from common import *
from music import T_IMPACT, T_ERUPT, T_OX, T_THAW

rng = np.random.default_rng(77)
L = np.zeros(N, np.float32); R = np.zeros(N, np.float32)
A = lambda n: np.arange(n) / SR
WN = lambda n: rng.standard_normal(n).astype(np.float32)

def add(t0, x, level=1.0, pan=0.0, x2=None):
    """x (and optionally a decorrelated x2 for the right channel) at t0"""
    i0 = int(round(t0 * SR)); n = len(x)
    a = max(0, -i0); b = n - max(0, i0 + n - N)
    if b <= a: return
    i0 = max(i0, 0); sl = slice(i0, i0 + b - a)
    th = (pan + 1) * np.pi / 4
    xr = x if x2 is None else x2
    L[sl] += x[a:b] * level * (np.cos(th) if x2 is None else 1); R[sl] += xr[a:b] * level * (np.sin(th) if x2 is None else 1)

def bed(t0, t1, fn, level, pts, att=3, rel=3):
    """stereo texture: fn(n) gives a mono signal; two decorrelated copies, level curve pts = [(t, v)] on the cut"""
    n = int((t1 - t0) * SR); c = interp(pts)(t0 + A(n)).astype(np.float32)
    e = smooth(A(n) / att) * smooth((n / SR - A(n)) / rel)
    add(t0, fn(n) * c * e, level, x2=fn(n) * c * e)

def lowp(x, f, o=2): return sos_f(x, 'low', f, o)
def hp(x, f, o=2): return sos_f(x, 'high', f, o)
def bp(x, a, b, o=2): return sos_f(x, 'bandpass', [a, b], o)

def rumble(n, lo=22, hi=110, wob=0.15):
    x = lowp(hp(WN(n), lo, 2), hi, 3); t = A(n)
    return x * (0.65 + 0.35 * np.sin(2 * np.pi * wob * t + rng.random() * 6)) * 6

def tick(t0, level=1.0, f=1500):
    n = int(0.09 * SR); t = A(n)
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.008) + 0.6 * bp(WN(n), 1500, 5000) * np.exp(-t / 0.003) * 3) * smooth(t / 0.001)
    add(t0, x * 0.2, level, pan=rng.uniform(-.3, .3))

def thump(t0, f0, level, dur=2.0, crack=0.2):
    n = int(dur * SR); t = A(n)
    x = np.sin(2 * np.pi * np.cumsum(f0 * (0.5 + 0.5 * np.exp(-t / 0.15))) / SR) * np.exp(-t / (dur / 5)) * smooth(t / 0.004)
    x += crack * lowp(WN(n), 900) * np.exp(-t / 0.08) * 4
    add(t0, x * 0.5, level, pan=rng.uniform(-.5, .5))

def crackles(t0, dur, rate, level, decay=None, hf=(1500, 6000)):
    """sparse little ticks (cooling rock, debris, ice): density falls as exp(-t/decay)"""
    t = 0.0
    while t < dur:
        d = rate * (np.exp(-t / decay) if decay else 1.0)
        t += rng.exponential(1 / max(d, 0.02))
        if t >= dur: break
        n = int(rng.uniform(0.004, 0.03) * SR); tt = A(n)
        fa = rng.uniform(*hf); x = bp(WN(n), fa * .5, fa * 1.4, 2) * np.exp(-tt / (n / SR / 4)) * 3
        add(t0 + t, x * 0.2, level * rng.uniform(.2, 1.0), pan=rng.uniform(-.9, .9))

def bubble(t0, level):
    f = rng.uniform(350, 1400); n = int(0.09 * SR); t = A(n)
    x = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * t / 0.09 * 1.0)) / SR) * np.exp(-t / 0.03) * smooth(t / 0.003)
    add(t0, x * 0.2, level * rng.uniform(.3, 1), pan=rng.uniform(-.9, .9))

def creak(t0, dur, level):
    n = int(dur * SR); t = A(n)
    f = rng.uniform(120, 260) * (1 + rng.uniform(.2, .6) * np.sin(np.pi * t / dur))      # a slow pitch bend
    pulse = (np.sin(2 * np.pi * np.cumsum(f) / SR) > 0.3).astype(np.float32) * (0.6 + 0.4 * np.sin(2 * np.pi * 37 * t))
    x = bp(pulse + 0.3 * WN(n), 700, 2600, 2) * np.sin(np.pi * t / dur) ** 2
    add(t0, x * 0.4, level, pan=rng.uniform(-.8, .8))

def thunder(t0, dur, level):
    n = int(dur * SR); t = A(n)
    x = lowp(WN(n), 140, 3) * 6; env = np.zeros(n, np.float32)
    for k in range(rng.integers(3, 6)):
        c = rng.uniform(0, dur * 0.6); env += rng.uniform(.3, 1) * smooth((t - c) / 0.8) * np.exp(-np.maximum(t - c, 0) / rng.uniform(1.5, 3))
    env *= smooth(t / 1.0) * smooth((dur - t) / 2)
    add(t0, x * env * 0.5, level, pan=rng.uniform(-.5, .5))

def main():
    a = ACT
    # act-change ticks: two very soft clock ticks just before each cut (not into the asteroid insert / its end)
    for k in TL['acts']:
        if k['id'] in ('hook', 'asteroid'): continue
        tick(k['start'] + 0.05, 0.5, 1500); tick(k['start'] + 0.55, 0.38, 1200)
    # hook: rewind whoosh (time running backwards) 6.2-8.4 s — a reversed breath of noise with fast reversed ticks
    n = int(2.7 * SR); t = A(n); sw = np.linspace(0, 1, n) ** 2
    x = np.zeros(n, np.float32); step = 2500
    for i in range(0, n - step, step):
        f = 400 * 2 ** (4.5 * sw[i]); x[i:i + step] = bp(WN(step), f, f * 1.6, 2) * 1.0
    x = x * sw * 5 * smooth(t / 0.4) * smooth((n / SR - t) / 0.5)
    add(5.9, x * 0.5, 1.0, x2=np.roll(x, 300) * 0.5)
    for k in range(14):                                  # reversed ticks accelerating
        tick(6.1 + 2.0 * (1 - (1 - k / 14) ** 1.7) + 0.1, 0.35 * (0.4 + k / 14), 1800 - 60 * k)
    # birth: low rumble + small distant impacts
    bed(a['birth'][0] - 2, a['theia'][0] + 8, lambda n: rumble(n, 22, 100), 0.7,
        [(26, 0), (34, .5), (46, 1.0), (T_IMPACT - 0.3, 1.5), (T_IMPACT + 1, .2), (T_IMPACT + 8, 0)], 4, 5)
    for tb in (32.5, 38.2, 41.9, 46.4, 49.5, 51.8, 53.1, 54.4, 55.5, 56.3, 56.9):
        thump(tb, rng.uniform(45, 80), 0.18 + 0.01 * (tb - 32) * 0.4, dur=1.8)
    crackles(31, 22, 0.35, 0.07, hf=(800, 3000))
    # THEIA ACCENT 1 (with the music): sub-boom + debris crackle, then the cooling hiss
    thump(T_IMPACT, 55, 1.6, dur=7.0, crack=0.3)
    n = int(14 * SR); t = A(n)
    sub = np.sin(2 * np.pi * np.cumsum(26 + 40 * np.exp(-t / 1.1)) / SR) * np.exp(-t / 3.2) * smooth(t / 0.01)
    add(T_IMPACT, sub * 1.1, 1.0)
    crackles(T_IMPACT + 0.1, 16, 55, 0.5, decay=4.0, hf=(1200, 8000))
    bed(T_IMPACT + 1.5, 82, lambda n: bp(WN(n), 2500, 9500, 2) * 3, 0.14,
        [(T_IMPACT + 1.5, 0), (T_IMPACT + 5, 1.0), (66, .8), (75, .4), (82, 0)], 3, 8)
    crackles(T_IMPACT + 6, 40, 3.0, 0.12, decay=25, hf=(1500, 5000))
    # oceans: rain + distant thunder
    o0, o1 = a['oceans']
    bed(o0 - 1.5, o1 + 3, lambda n: hp(lowp(WN(n), 9000, 2), 900, 2) * 3.0, 0.10, [(o0, 0), (o0 + 5, 1.0), (o1 - 5, 1.0), (o1 + 3, 0)], 4, 4)
    bed(o0 - 1.5, o1 + 3, lambda n: bp(WN(n), 180, 700, 2) * 2.5, 0.08, [(o0, 0), (o0 + 6, 1.0), (o1 - 5, .8), (o1 + 3, 0)], 4, 4)
    for tb in (o0 + 5, o0 + 13, o0 + 20): thunder(tb, rng.uniform(7, 10), 0.6)
    # life: underwater ambience
    l0, l1 = a['life']
    bed(l0 - 2, l1 + 3, lambda n: lowp(WN(n), 320, 3) * 5 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.11 * A(n))), 0.5,
        [(l0 - 1, 0), (l0 + 3, 1.0), (l1 - 2, 1.0), (l1 + 3, 0)], 4, 4)
    for tb in np.sort(rng.uniform(l0 + 3, l1 - 3, 9)): bubble(tb, 0.25)
    # oxygen: bubbles, thickening, thinning out at «кожен твій вдих»
    ox0, ox1 = a['oxygen']; tb = ox0 + 1.5
    while tb < T_OX + 1:
        dens = interp([(ox0, 0.6), (ox0 + 20, 2.5), (190, 6), (200, 6), (T_OX, 3.0)])(tb)
        tb += rng.exponential(1 / dens)
        bubble(tb, 0.4)
    bed(ox0 + 3, T_OX + 4, lambda n: lowp(WN(n), 260, 3) * 3, 0.25, [(ox0, 0), (ox0 + 6, 1), (T_OX, .7), (T_OX + 4, 0)], 4, 4)
    # snowball: ice creaking and cracking, a thin wind; the thaw's first drips
    s0, s1 = a['snowball']
    bed(s0 - 1, s1, lambda n: bp(WN(n), 300, 1400, 2) * 3, 0.1, [(s0 - 1, 0), (s0 + 4, 1), (T_THAW - 2, 1), (s1, 0)], 3, 3)
    for tb in np.sort(rng.uniform(s0 + 2, T_THAW + 3, 9)): creak(tb, rng.uniform(.6, 1.8), 0.4)
    for tb in np.sort(rng.uniform(s0 + 1, T_THAW + 1, 8)):
        n = int(0.5 * SR); t = A(n); x = (bp(WN(n), 1500, 7000) * np.exp(-t / 0.02) * 4 + np.sin(2 * np.pi * 2300 * t) * np.exp(-t / 0.15)) * smooth(t / 0.0008)
        add(tb, x * 0.2, 0.5, pan=rng.uniform(-.8, .8))
    for tb in np.sort(rng.uniform(T_THAW + 2, s1 + 1, 7)):                            # drips
        bubble(tb, 0.25)
    # ediacara + cambrian: underwater, brighter as life explodes
    e0, e1 = a['ediacara'][0], a['cambrian'][1]
    bed(e0 - 1, e1 + 3, lambda n: lowp(WN(n), 380, 3) * 5 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.09 * A(n))), 0.35,
        [(e0 - 1, 0), (e0 + 4, .8), (a['cambrian'][0], 1.0), (e1 - 2, .8), (e1 + 3, 0)], 4, 4)
    for tb in np.sort(rng.uniform(e0, e1 - 2, 16)): bubble(tb, 0.2)
    # land: light wind
    ld0, ld1 = a['land']
    def wind(n):
        g = lowp(WN(n), 0.4, 2); g = (g / (np.abs(g).max() + 1e-9))
        return bp(WN(n), 250, 1800, 2) * 5 * (0.4 + 0.6 * smooth(g * 2 + 0.5))
    bed(ld0 - 1, ld1 + 6, wind, 0.18, [(ld0 - 1, 0), (ld0 + 5, 1), (ld1 + 3, .7), (ld1 + 6, 0)], 3, 4)
    # coal: swamp — crickets/insects (no birds), wing buzz, water drips
    c0, c1 = a['coal']; tc = np.arange(1)
    n = int((c1 - c0 + 4) * SR); t = A(n)
    for k, (fc, rate) in enumerate(((3600, 22), (4300, 17), (2900, 13))):
        ph = rng.random() * 6
        gate = (np.sin(2 * np.pi * (rate / 9 + .02 * k) * t + ph) > 0.2).astype(np.float32)
        gate = lowp(gate, 40, 1)
        chirp = np.sin(2 * np.pi * fc * t + 3 * np.sin(2 * np.pi * rate * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t) ) * gate
        env = interp([(0, 0), (4, 1), (n / SR - 5, 1), (n / SR, 0)])(t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t + k))
        add(c0 - 2, chirp * env * 0.12, 1.0, pan=-0.6 + 0.6 * k)
    bed(c0 - 1, c1 + 3, lambda n: bp(WN(n), 120, 260, 2) * 2 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * A(n))), 0.08, [(c0 - 1, 0), (c0 + 6, 1), (c1, 1), (c1 + 3, 0)], 3, 3)
    bed(c0 - 1, c1 + 3, lambda n: bp(WN(n), 150, 600, 2) * 2.0, 0.07, [(c0 - 1, 0), (c0 + 4, 1), (c1, .6), (c1 + 3, 0)], 3, 3)
    for tb in np.sort(rng.uniform(c0, c1, 10)): bubble(tb, 0.2)
    # permian: volcanic rumble, ACCENT 2 (heavy eruption) at T_ERUPT, ash hiss
    p0, p1 = a['permian']
    bed(p0 - 1, p1 + 5, lambda n: rumble(n, 20, 90, 0.1), 0.55, [(p0 - 1, 0), (p0 + 3, .5), (T_ERUPT - 2, .8), (T_ERUPT + 3, 1.0), (p1, .7), (p1 + 5, 0)], 4, 5)
    n = int(16 * SR); t = A(n)
    er = lowp(WN(n), 130, 3) * 7 * smooth(t / 1.4) * np.exp(-np.maximum(t - 1.4, 0) / 5.5)
    er2 = lowp(WN(n), 130, 3) * 7 * smooth(t / 1.4) * np.exp(-np.maximum(t - 1.4, 0) / 5.5)
    sub = np.sin(2 * np.pi * np.cumsum(30 + 20 * np.exp(-t / 3)) / SR) * smooth(t / 1.0) * np.exp(-np.maximum(t - 1.0, 0) / 4.5)
    add(T_ERUPT - 0.6, (er + sub * 1.6) * 0.5, 1.4, x2=(er2 + sub * 1.6) * 0.5)
    bed(T_ERUPT, T_ERUPT + 22, lambda n: bp(WN(n), 600, 5000, 2) * 2.5, 0.15, [(T_ERUPT, 0), (T_ERUPT + 3, 1), (T_ERUPT + 12, .5), (T_ERUPT + 22, 0)], 2, 8)
    crackles(T_ERUPT + 1, 14, 20, 0.35, decay=6, hf=(800, 5000))
    # mammals: a very faint night-city hum at the end, reaching over into the beginning of the future
    m0, m1 = a['mammals']; f0 = a['future'][0]
    def city(n):
        t = A(n); h = np.sin(2 * np.pi * 50 * t) * 0.5 + np.sin(2 * np.pi * 100 * t) * 0.3 + np.sin(2 * np.pi * 150 * t) * 0.1
        return h * 0.8 + bp(WN(n), 150, 900, 2) * 2.0 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t))
    bed(m1 - 11, f0 + 8, city, 0.2, [(m1 - 11, 0), (m1 - 3, .7), (f0 + 2, .6), (f0 + 8, 0)], 4, 5)

if __name__ == '__main__':
    main()
    from common import normalize
    # a gentle high-pass for rumble-free DC, then loudness
    L2 = sos_f(L, 'high', 18, 2); R2 = sos_f(R, 'high', 18, 2)
    L2, R2, g = normalize(L2, R2, -24.0)
    wav_write(os.path.join(WORK, 'sfx.wav'), L2, R2)
    print('sfx.wav', ebur(os.path.join(WORK, 'sfx.wav')))
