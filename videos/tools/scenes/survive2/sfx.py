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


def sun(dur=4.8):
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
    finish(stereo(m, 0.4), 'sun.wav', dur)


def neptune(dur=6.5):
    n = int(dur * SR); t = np.arange(n) / SR
    gust = ramp(t, 3.4, 3.9)
    # the wind: a few bands whose loudness and pitch wander, a howl that whistles
    g1 = 0.65 + 0.35 * np.sin(2 * np.pi * 0.37 * t + 1) * np.sin(2 * np.pi * 0.23 * t)
    w = lp(noise(n), 400, 4) * 0.8 * g1 + bp(noise(n), 500, 1400) * 0.35 * g1
    howl = np.zeros(n)
    for f0, ph in ((620, 0), (880, 2), (1240, 4)):
        howl += sosfilt(butter(2, [f0 * 0.97, f0 * 1.03], 'bandpass', fs=SR, output='sos'), noise(n)) * 0.6 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.31 * t + ph))
    wind = (w + howl * 0.5) * (0.8 + 1.4 * gust)
    frost = ramp(t, 0.25, 3.0) * (1 - ramp(t, 3.7, 3.8))
    ticks = crackle(n, 3 + 25 * frost, 2000, 10000, 0.002) * 0.9
    creak = bp(noise(n), 150, 400) * 0.25 * frost * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t) ** 8)
    crack = crackle(n, 2 + 160 * ramp(t, 3.05, 3.65) * (1 - ramp(t, 3.7, 3.75)), 1500, 12000, 0.003) * 1.6
    s = int(3.72 * SR)
    shat = np.zeros(n)
    L = int(0.6 * SR)
    burst = hp(noise(L), 1200) * np.exp(-np.arange(L) / (0.07 * SR)) * 2.5
    burst += lp(noise(L), 300) * np.exp(-np.arange(L) / (0.12 * SR)) * 2.0
    shat[s:s + L] += burst[:max(0, min(L, n - s))]
    shat += pings(n, 3.72, 140, 1.4) * 0.5
    m = wind * 2.2 + ticks * 1.5 + creak * 2 + crack + shat * 0.8
    finish(stereo(m, 0.5), 'nep.wav', dur)


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    sun()
    neptune()
