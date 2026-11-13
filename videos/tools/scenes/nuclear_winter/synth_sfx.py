# «Ядерна зима» — sound effects synthesised from noise and sines (no AI: the generated ones had screams in them).
# Stereo, 44.1 kHz, written to sfx/*.wav:
#   blast_synth.wav  8 s — a crack, the pressure thump of the shock wave, a long rolling rumble, a rush of debris and wind
#   fire_synth.wav  16 s — a firestorm: deep roar, gusting whoosh, crackle
#   wind_synth.wav  21 s — cold wind: moaning resonances drifting in pitch, gusts, a hiss of blowing snow
#   python3 synth_sfx.py
import os, numpy as np
from scipy.signal import butter, sosfilt
import imageio_ffmpeg, subprocess

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'sfx')
rng = np.random.default_rng(7)

def bp(x, lo, hi, order=4): return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
def lp(x, f, order=4): return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)
def hp(x, f, order=4): return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)
def brown(n): x = np.cumsum(rng.standard_normal(n)); x -= lp(x, 8, 2); return x / (np.abs(x).max() + 1e-9)
def white(n): return rng.standard_normal(n)
def lfo(n, rate, depth=1.0):
    """slow random modulation (smoothed noise), 0..1"""
    k = max(4, int(n / SR * rate) + 4)
    pts = rng.random(k)
    return np.clip(np.interp(np.linspace(0, k - 1, n), np.arange(k), pts) * depth + (1 - depth) * 0.5, 0, 1)
def env(n, attack, decay, start=0.0):
    t = np.arange(n) / SR - start
    return np.where(t < 0, 0, np.minimum(1, t / max(attack, 1e-4)) * np.exp(-np.maximum(t - attack, 0) / decay))

def stereo(make, n):
    """two decorrelated takes of the same recipe, a touch of cross-feed — width without phasing"""
    L, Rr = make(n), make(n)
    return np.stack([L * 0.85 + Rr * 0.15, Rr * 0.85 + L * 0.15], 1)

def blast(n):
    T0 = 0.30
    crack = hp(white(n), 900) * env(n, 0.0005, 0.018, T0) * 0.9 + hp(white(n), 3000) * env(n, 0.0005, 0.006, T0) * 0.6
    t = np.arange(n) / SR - T0
    f = 22 + 45 * np.exp(-np.maximum(t, 0) / 0.35)                          # a falling pressure thump
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.012, 0.9, T0) * 1.3
    whump = lp(white(n), 380) * env(n, 0.02, 1.4, T0) * 1.6
    rumble = lp(brown(n), 140) * env(n, 0.35, 3.2, T0 + 0.1) * (0.55 + 0.45 * lfo(n, 4)) * 2.2
    rush = bp(white(n), 250, 2200) * env(n, 0.25, 1.6, T0 + 0.25) * (0.5 + 0.5 * lfo(n, 9)) * 0.35
    return crack + thump + whump + rumble + rush

def boom_far(n):
    """a detonation heard from far away: the highs are gone, a soft low thump, then thunder rolling and echoing off the land"""
    T0 = 0.15
    t = np.arange(n) / SR - T0
    f = 30 + 20 * np.exp(-np.maximum(t, 0) / 0.5)
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.06, 0.8, T0) * 1.2
    body = lp(white(n), 220) * env(n, 0.08, 1.0, T0) * 1.2
    roll = np.zeros(n)
    for k, (dt, g) in enumerate([(0.0, 1.0), (0.45, 0.7), (1.1, 0.55), (1.8, 0.4), (2.7, 0.28)]):   # echoes off hills
        roll += lp(brown(n), 110 + 20 * k) * env(n, 0.25, 1.1 + 0.3 * k, T0 + 0.1 + dt) * g
    roll *= (0.6 + 0.4 * lfo(n, 5)) * 2.0
    air = bp(white(n), 120, 600) * env(n, 0.3, 1.6, T0 + 0.2) * 0.25
    return thump + body + roll + air

def fire(n):
    roar = lp(brown(n), 180) * (0.55 + 0.45 * lfo(n, 1.5)) * 1.6
    whoosh = bp(white(n), 180, 1400) * (0.25 + 0.75 * lfo(n, 2.2) ** 2) * 0.35
    cr = np.zeros(n)
    for _ in range(int(n / SR * 26)):                                      # crackle: sparse little bursts
        i = rng.integers(0, n - 2000); L = rng.integers(200, 1600)
        cr[i:i + L] += rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 5)) * rng.uniform(0.2, 1.0)
    crack = bp(cr, 900, 5000) * 0.18
    fade = np.minimum(1, np.arange(n) / (SR * 1.5)) * np.minimum(1, (n - np.arange(n)) / (SR * 2.0))
    return (roar + whoosh + crack) * fade

def wind(n):
    out = np.zeros(n)
    centres = [260, 340, 430, 540, 680]
    weights = [lfo(n, 0.5) ** 3 for _ in centres]                          # the moan wanders between resonances
    for c, w in zip(centres, weights):
        out += bp(white(n), c * 0.94, c * 1.06, 2) * w * 2.2
    body = bp(white(n), 120, 900) * 0.35
    gust = 0.35 + 0.65 * lfo(n, 0.8) ** 1.5
    hiss = hp(white(n), 3500) * 0.05 * (0.4 + 0.6 * lfo(n, 1.2))
    fade = np.minimum(1, np.arange(n) / (SR * 2.5)) * np.minimum(1, (n - np.arange(n)) / (SR * 3.0))
    return (out + body) * gust * fade + hiss * fade

def save(name, x):
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    raw = (x * 32767).astype('<i2').tobytes()
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    os.path.join(OUT, name)], input=raw, check=True)
    print(name, x.shape[0] / SR, 's')

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    # the wavs in sfx/ are the ones the author approved (13.11, «v2»): regenerate only what is named on the command line,
    # e.g. python3 synth_sfx.py boom_far — the noise comes out different on every run
    import sys
    todo = sys.argv[1:] or ['boom_far']
    recipes = {'boom_far': (boom_far, 6), 'blast': (blast, 8), 'fire': (fire, 16), 'wind': (wind, 21)}
    for k in todo:
        f_, sec = recipes[k]; save(f'{k}_synth.wav' if k != 'boom_far' else 'boom_far_synth.wav', stereo(f_, SR * sec))
