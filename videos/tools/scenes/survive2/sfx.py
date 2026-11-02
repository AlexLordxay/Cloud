# «Скільки ти протримаєшся…» v2 — draft sound effects for the two test shots (2.11.2026), synthesised (no samples):
#   sun:     a roar that swells with the heat, fire crackling as the char climbs, a rushing whoosh while he comes apart,
#            then only the roar and the tinkle of sparks
#   neptune: wind howling (gusting, rising at the gust), small ice ticks as the frost grows, the crust cracking,
#            the shatter (a hard crack and a shower of glassy pings), the wind taking him away
# Times match page.js (SUN and NEP). Writes work/survive2/sun.wav and nep.wav (48 kHz stereo).
#   python3 scenes/survive2/sfx.py
import os
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '..', '..', 'work', 'survive2')
rng = np.random.default_rng(7)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)


def ramp(t, a, b):
    u = np.clip((t - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def noise(n):
    return rng.standard_normal(n)


def crackle(n, density, lo=900, hi=9000, decay=0.004):
    """sparse random clicks, each a short decaying burst; density: clicks per second (array or scalar)"""
    out = np.zeros(n)
    dens = np.broadcast_to(density, (n,))
    p = dens / SR
    hits = np.nonzero(rng.random(n) < p)[0]
    L = int(decay * 6 * SR)
    env = np.exp(-np.arange(L) / (decay * SR))
    for h in hits:
        b = noise(L) * env * (0.3 + rng.random() ** 2)
        e = min(n, h + L)
        out[h:e] += b[:e - h]
    return bp(out, lo, hi)


def pings(n, t0, count, spread):
    """glassy pings: short decaying sines at random high pitches, scattered after t0"""
    out = np.zeros(n)
    for _ in range(count):
        st = int((t0 + spread * rng.random() ** 1.6) * SR)
        f = 2500 + 6000 * rng.random()
        L = int(0.25 * SR)
        tt = np.arange(L) / SR
        s = np.sin(2 * np.pi * f * tt) * np.exp(-tt / (0.02 + 0.06 * rng.random())) * (0.2 + 0.8 * rng.random())
        e = min(n, st + L)
        if st < n:
            out[st:e] += s[:e - st]
    return out


def stereo(m, width=0.3):
    d = int(0.012 * SR)
    r = np.concatenate([np.zeros(d), m[:-d]])
    return np.stack([m * (1 - width * 0.5) + r * width * 0.5, r * (1 - width * 0.5) + m * width * 0.5], 1)


def finish(x, name, dur):
    n = len(x)
    t = np.arange(n) / SR
    x = x * ramp(t, 0, 0.05)[:, None] * (1 - ramp(t, dur - 0.3, dur))[:, None]
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.12          # loudness to about -18 dB RMS, then a soft limiter
    x = np.tanh(x * 1.6) / 1.6 * 0.95
    wavfile.write(os.path.join(WORK, name), SR, (x * 32767).astype(np.int16))
    print(name, f'{dur:.1f} s')


def sun(dur=4.8, out='sun.wav'):
    n = int(dur * SR); t = np.arange(n) / SR
    heat = ramp(t, 0.1, 1.3)
    roar = lp(noise(n), 180, 4) * (0.6 + 0.6 * heat) * (1 - 0.5 * ramp(t, 3.6, 4.8))
    roar += bp(noise(n), 200, 900) * 0.25 * heat * (1 - 0.6 * ramp(t, 3.6, 4.8))
    burn = ramp(t, 0.5, 1.2) * (1 - ramp(t, 3.3, 3.9))
    fire = crackle(n, 30 + 260 * burn, 700, 7000, 0.003) * 1.6 * burn
    fire += bp(noise(n), 300, 2500) * 0.35 * burn * (0.7 + 0.3 * np.sin(2 * np.pi * 3.1 * t) * np.sin(2 * np.pi * 1.3 * t))
    melt = ramp(t, 1.45, 2.2) * (1 - ramp(t, 3.2, 4.0))
    whoosh = sum(bp(noise(n), f, f * 1.8) for f in (400, 900, 2000)) * 0.35 * melt * (0.6 + 0.4 * ramp(t, 1.45, 3.4))
    sparks = crackle(n, 4 + 60 * ramp(t, 2.4, 3.2) * (1 - ramp(t, 4.0, 4.8)), 3000, 12000, 0.0015) * 0.8
    m = roar * 1.0 + fire + whoosh + sparks
    if out: finish(stereo(m, 0.4), out, dur)
    return m


def neptune(dur=6.5, sh=3.72, g0=3.4, fr=(0.25, 3.0), cr=(3.05, 3.65), out='nep.wav'):
    n = int(dur * SR); t = np.arange(n) / SR
    gust = ramp(t, g0, g0 + 0.5)
    # the wind: a few bands whose loudness and pitch wander, a howl that whistles
    g1 = 0.65 + 0.35 * np.sin(2 * np.pi * 0.37 * t + 1) * np.sin(2 * np.pi * 0.23 * t)
    w = lp(noise(n), 400, 4) * 0.8 * g1 + bp(noise(n), 500, 1400) * 0.35 * g1
    howl = np.zeros(n)
    for f0, ph in ((620, 0), (880, 2), (1240, 4)):
        howl += sosfilt(butter(2, [f0 * 0.97, f0 * 1.03], 'bandpass', fs=SR, output='sos'), noise(n)) * 0.6 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.31 * t + ph))
    wind = (w + howl * 0.5) * (0.8 + 1.4 * gust)
    frost = ramp(t, *fr) * (1 - ramp(t, sh - 0.02, sh + 0.08))
    ticks = crackle(n, 3 + 25 * frost, 2000, 10000, 0.002) * 0.9
    creak = bp(noise(n), 150, 400) * 0.25 * frost * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t) ** 8)
    crack = crackle(n, 2 + 160 * ramp(t, *cr) * (1 - ramp(t, sh - 0.02, sh + 0.03)), 1500, 12000, 0.003) * 1.6
    s = int(sh * SR)
    shat = np.zeros(n)
    L = int(0.6 * SR)
    burst = hp(noise(L), 1200) * np.exp(-np.arange(L) / (0.07 * SR)) * 2.5
    burst += lp(noise(L), 300) * np.exp(-np.arange(L) / (0.12 * SR)) * 2.0
    shat[s:s + L] += burst[:max(0, min(L, n - s))]
    shat += pings(n, sh, 140, 1.4) * 0.5
    m = wind * 2.2 + ticks * 1.5 + creak * 2 + crack + shat * 0.8
    if out: finish(stereo(m, 0.5), out, dur)
    return m


def rms(x): return np.sqrt(np.mean(x ** 2)) + 1e-9


def thud(n, at, k=1.0, f=90):
    out = np.zeros(n); s = int(at * SR); L = int(0.7 * SR); tt = np.arange(L) / SR
    b = (np.sin(2 * np.pi * f * tt * (1 - 0.4 * tt)) * np.exp(-tt / 0.12) + lp(noise(L), 250) * np.exp(-tt / 0.05) * 0.8) * k
    e = min(n, s + L); out[s:e] += b[:e - s]; return out


def full():
    """All the effects on the timeline (timeline.json, spec.py): per world its air, each death's sounds, the stopwatch."""
    import json, sys
    sys.path.insert(0, HERE); import spec
    TL = json.load(open(os.path.join(HERE, 'timeline.json')))
    DUR = TL['dur']; N = int(DUR * SR); mix = np.zeros(N); T = np.arange(N) / SR
    sh = {s['world']: s for s in TL['shots']}

    def put(x, at, gain):
        a = int(at * SR); e = min(N, a + len(x)); mix[a:e] += x[:e - a] * gain

    def seg(w):
        s = sh[w]; n = int((s['t1'] - s['t0']) * SR); return n, np.arange(n) / SR

    # Venus (the hook and the shot): the thick hot air rumbling, the visor cracking, the crunch, he falls, the haze
    for w, cr, crush, fall in (('venus_hook', (0.0, 2.9), 2.95, 3.6), ('venus', (3.5, 3.95), 3.6, 4.6)):
        n, t = seg(w)
        air = lp(noise(n), 160, 4) * 1.0 + bp(noise(n), 200, 700) * 0.25
        cracks = crackle(n, 3 + 140 * ramp(t, *cr) * (1 - ramp(t, cr[1], cr[1] + 0.05)), 1500, 12000, 0.003) * 1.3
        crunch = thud(n, crush, 1.1, 70) + crackle(n, 400 * (ramp(t, crush, crush + 0.05) - ramp(t, crush + 0.25, crush + 0.35)), 600, 6000, 0.004) * 1.2
        put(air / rms(air) * 0.05 + cracks + crunch + thud(n, fall, 1.0, 60), s0 := sh[w]['t0'], 1.0)
    # the Moon: near silence (his breath), a soft thump as he lands is past the cut
    n, t = seg('moon'); put(bp(noise(n), 300, 1200) * 0.012 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 3.6) ** 2), sh['moon']['t0'], 1.0)
    # Mercury: no air — only what carries through the suit: the cooling fan straining, a hiss rising, the visor, the fall
    n, t = seg('mercury')
    hiss = bp(noise(n), 2000, 7000) * 0.06 * ramp(t, 1.0, 6.2) * (1 - ramp(t, 7.2, 7.6))
    fan = np.sin(2 * np.pi * (180 + 60 * ramp(t, 1.0, 5.5)) * t) * 0.03 * (1 - ramp(t, 5.4, 5.8))
    cracks = crackle(n, 3 + 120 * ramp(t, 5.0, 6.0) * (1 - ramp(t, 6.0, 6.05)), 1500, 12000, 0.003)
    put(hiss + fan + cracks + thud(n, 5.95, 0.6, 80) + thud(n, 7.05, 1.2, 55), sh['mercury']['t0'], 1.0)
    # Mars: a thin wind, the storm's far roar
    n, t = seg('mars'); wd = lp(noise(n), 500, 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.2 * t)) + lp(noise(n), 90, 4) * 0.8
    put(wd / rms(wd) * 0.04, sh['mars']['t0'], 1.0)
    # Jupiter: the rush of falling, deepening; thunder at each bolt; the static when the signal goes
    n, t = seg('jupiter')
    rush = (bp(noise(n), 300, 2500) * (0.5 + 0.5 * ramp(t, 0, 6)) + lp(noise(n), 120, 4) * (0.5 + ramp(t, 3, 7)))
    rush = rush / rms(rush) * 0.035
    thunder = np.zeros(n)
    for bt in (1.6, 3.3, 4.5, 5.9, 6.6):
        thunder += crackle(n, 900 * (ramp(t, bt, bt + 0.02) - ramp(t, bt + 0.15, bt + 0.25)), 800, 9000, 0.004) * 0.5 + thud(n, bt + 0.25, 0.8, 45)
    lost = t > spec.LOST
    stat = hp(noise(n), 800) * 0.25 * lost + np.sin(2 * np.pi * 1000 * t) * 0.08 * ((t > spec.LOST) & (t < spec.LOST + 0.25))
    rush = rush * (1 - 0.9 * lost); thunder = thunder * (1 - lost)
    put(rush + thunder + stat, sh['jupiter']['t0'], 1.0)
    # Titan: a soft dense wind; the wings' beats
    n, t = seg('titan'); wd = lp(noise(n), 300, 2) * 0.03
    beat = bp(noise(n), 150, 600) * 0.12 * np.maximum(0, np.sin(2 * np.pi * 1.3 * (t - 4.9))) ** 6 * ramp(t, 5.6, 6.2)
    put(wd + beat, sh['titan']['t0'], 1.0)
    # Neptune and the Sun: the test shots' sounds, retimed to the voice
    nm = neptune(sh['neptune']['t1'] - sh['neptune']['t0'], 4.72, 4.4, (0.3, 3.5), (3.9, 4.6), None); put(nm / rms(nm) * 0.07, sh['neptune']['t0'], 1.0)
    sm = sun(sh['sun']['t1'] - sh['sun']['t0'] + 0.6, None); sm *= np.minimum(1, np.arange(len(sm)) / (0.05 * SR)); put(sm / rms(sm) * 0.08, sh['sun']['t0'], 1.0)
    # the stopwatch: ticks while it runs (faster as it races), then a stop: a low buzz (red) or a bright ding (green)
    for w, (a, b, v, col, _) in spec.TIMERS.items():
        t0 = sh[w]['t0']
        if b - a > 0.2:
            k = 0.0
            while a + k < b - 0.05:
                put(bp(noise(int(0.012 * SR)), 2500, 6000) * 0.25, t0 + a + k, 1.0)
                u = k / (b - a); k += 0.16 - 0.11 * u
        L = int(0.35 * SR); tt = np.arange(L) / SR
        if col == spec.RED: tone = (np.sign(np.sin(2 * np.pi * 110 * tt)) * 0.5 + np.sin(2 * np.pi * 220 * tt)) * np.exp(-tt / 0.12) * 0.08
        else: tone = (np.sin(2 * np.pi * 1318.5 * tt) + 0.6 * np.sin(2 * np.pi * 1975.5 * tt) * (tt > 0.08)) * np.exp(-tt / 0.15) * 0.1
        put(lp(tone, 4000), t0 + b, 1.0)
    x = stereo(mix, 0.4)
    x = np.tanh(x * 1.5) / 1.5
    wavfile.write(os.path.join(WORK, 'sfx_full.wav'), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    print('sfx_full.wav', DUR)


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    import sys
    if sys.argv[1:2] == ['full']: full()
    else: sun(); neptune()
