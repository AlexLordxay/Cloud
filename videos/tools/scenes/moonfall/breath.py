# The astronaut's breathing, synthesised (no recordings): air noise shaped by a band that sweeps with the breath, a short
# helmet cavity, a faint ventilation hiss and the odd valve click. Three characters, each ~16 s, matching the organ sketches:
#   1  calm, then quickening as the Moon grows; a held breath before the brightening; one long exhale
#   2  slow and deep (awe): in 2.4 s, out 3.2 s, long pauses
#   3  shallow and fast, rising; breath caught (held) in the hush; one shaky exhale
#   0  the film itself (46 s), timed to the shots: python3 scenes/moonfall/breath.py 0 -> work/moonfall/breath_0.wav
#   python3 scenes/moonfall/breath.py [1 2 3]      ->  work/moonfall/breath_<variant>.wav  (stereo, 44.1 kHz)
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.abspath(os.path.join(HERE, '../../work/moonfall'))
BANDS = [300, 520, 900, 1500, 2500, 4200]               # band-pass centres (Hz), an octave wide


def band_tracks(rng, n):
    """White noise split into BANDS; one set per channel."""
    w = rng.standard_normal(n).astype(np.float32)
    out = []
    for fc in BANDS:
        sos = signal.butter(2, [fc / 1.45, fc * 1.45], btype='band', fs=SR, output='sos')
        out.append(signal.sosfilt(sos, w).astype(np.float32))
    return np.array(out)


def shape(tracks, t0, dur, fc0, fc1, env, amp, width=0.75):
    """A breath event: bands weighted around a centre frequency sliding fc0 -> fc1, times an amplitude envelope."""
    n = int(dur * SR)
    u = np.linspace(0, 1, n, endpoint=False)
    fc = fc0 * (fc1 / fc0) ** u                          # log-linear sweep
    y = np.zeros(n, np.float32)
    for k, f in enumerate(BANDS):
        wgt = np.exp(-0.5 * ((np.log2(f) - np.log2(fc)) / width) ** 2)
        y += tracks[k][int(t0 * SR) % (tracks.shape[1] - n):][:n] * wgt
    return y * env(u).astype(np.float32) * amp


def inhale_env(u):
    rise = np.sin(np.pi / 2 * np.minimum(1, u / 0.78)) ** 1.6
    fall = np.where(u > 0.78, np.cos(np.pi / 2 * (u - 0.78) / 0.22) ** 2, 1.0)
    return rise * fall


def exhale_env(u):
    return (1 - np.exp(-u / 0.05)) * np.exp(-2.6 * u) * 1.5


def click(rng, amp=0.3):
    n = int(0.006 * SR)
    c = rng.standard_normal(n) * np.exp(-np.arange(n) / (0.0011 * SR))
    return signal.sosfilt(signal.butter(2, 1800, btype='high', fs=SR, output='sos'), c).astype(np.float32) * amp


def schedule(variant):
    """[(kind, start, duration, level, fc0, fc1)] and the clicks (times)."""
    ev, clicks, t = [], [], 0.0

    def cycle(t, din, dout, gap1=0.12, gap2=0.15, a=1.0, hi=1.0, lo=1.0, click_on=True):
        ev.append(('in', t, din, 0.55 * a, 1100 * hi, 2600 * hi))
        if click_on: clicks.append(t)
        t += din + gap1
        ev.append(('out', t, dout, 0.8 * a, 750 * lo, 380 * lo))
        return t + dout + gap2
    if variant == 0:
        # the film (46 s, timed to shots.js): a gasp at the hook; the rewind as a breath drawn backwards; calm, then
        # quicker and shakier as the Moon comes; a gasp and the breath held through the impact; a long shaky exhale;
        # slow, tired breaths at the end
        ev.append(('in', 0.05, 0.75, 0.75, 1400, 3000)); clicks.append(0.05)
        ev.append(('out', 1.72, 1.2, 0.55, 700, 380, 'rev'))
        t = 3.2
        while t < 31.0:
            P = float(np.interp(t, [3, 15, 23, 29, 31], [4.4, 3.4, 2.4, 1.6, 1.2]))
            a = float(np.interp(t, [3, 23, 31], [0.85, 1.0, 1.1])); hi = float(np.interp(t, [3, 23, 31], [1.0, 1.1, 1.22]))
            ev.append(('in', t, 0.4 * P, 0.55 * a, 1100 * hi, 2600 * hi, 'shaky' if t > 24 else ''))
            if t < 24: clicks.append(t)
            ev.append(('out', t + 0.43 * P, 0.5 * P, 0.8 * a, 750 * hi, 380 * hi, 'shaky' if t > 24 else ''))
            t += P
        while t < 32.6:
            ev.append(('in', t, 0.32, 0.6, 1500, 3200, 'shaky')); ev.append(('out', t + 0.35, 0.42, 0.75, 900, 450, 'shaky')); t += 0.85
        ev.append(('in', 32.75, 0.55, 0.85, 1600, 3400))                        # the gasp; then nothing till it is over
        ev.append(('out', 36.6, 2.6, 0.7, 650, 320, 'shaky'))
        ev.append(('in', 39.6, 1.6, 0.5, 950, 2100)); ev.append(('out', 41.4, 2.4, 0.6, 600, 330))
        ev.append(('in', 44.0, 1.3, 0.35, 900, 2000))
    elif variant == 1:
        t = 0.6
        for din, dout, a in [(1.5, 2.3, 0.9), (1.4, 2.0, 0.95), (1.2, 1.7, 1.0)]:
            t = cycle(t, din, dout, a=a)
        ev.append(('in', t, 1.0, 0.65, 1300, 2800)); clicks.append(t)             # the last breath in, then held
        ev.append(('out', 14.0, 2.0, 0.55, 600, 330))                             # one long exhale on the brightening
    elif variant == 2:
        for t0, din, dout in [(0.5, 2.4, 3.2), (7.2, 2.4, 3.0)]:
            cycle(t0, din, dout, gap1=0.5, a=0.8, hi=0.8, lo=0.85, click_on=False)
        ev.append(('in', 13.5, 1.8, 0.45, 900, 1900))
    else:
        t = 0.4
        for din, dout, a in [(0.9, 1.3, 0.8), (0.8, 1.1, 0.85), (0.7, 0.9, 0.9), (0.6, 0.75, 0.95), (0.5, 0.6, 1.0), (0.42, 0.5, 1.05), (0.36, 0.42, 1.1), (0.3, 0.36, 1.1)]:
            t = cycle(t, din, dout, gap1=0.05, gap2=0.06, a=a, hi=1.25, lo=1.15)
        ev.append(('in', 13.9, 0.5, 0.5, 1500, 3200))
        ev.append(('out', 14.45, 1.5, 0.6, 900, 450))
    return ev, clicks


def render(variant, T=16.0, seed=7):
    rng = np.random.default_rng(seed + variant)
    n = int(T * SR)
    chans = []
    for ch in range(2):
        tr = band_tracks(rng, n + 6 * SR)
        ev, clicks = schedule(variant)
        y = np.zeros(n + 6 * SR, np.float32)
        for e in ev:
            kind, t0, dur, lvl, fc0, fc1 = e[:6]; fxk = e[6] if len(e) > 6 else ''
            seg = shape(tr, t0 + 0.37 * ch, dur, fc0, fc1, inhale_env if kind == 'in' else exhale_env, lvl)
            if fxk == 'rev': seg = seg[::-1].copy()
            if fxk == 'shaky':
                seg *= (0.8 + 0.2 * np.sin(2 * np.pi * 7.0 * np.arange(len(seg)) / SR + t0 * 5)).astype(np.float32)
            if variant == 3 and t0 > 13.9 and kind == 'out':                      # shaky exhale
                seg *= (0.75 + 0.25 * np.sin(2 * np.pi * 6.2 * np.arange(len(seg)) / SR)).astype(np.float32)
            if variant == 3 and kind == 'in':                                     # raspy: soft-clip the edges
                seg = np.tanh(2.2 * seg) / 1.6
            # turbulence: slow random flutter on the level
            fl = signal.sosfilt(signal.butter(1, 9, fs=SR, output='sos'), rng.standard_normal(len(seg))).astype(np.float32)
            seg *= 1 + 0.35 * fl / (fl.std() + 1e-9) * 0.4
            s = int(t0 * SR); y[s:s + len(seg)] += seg
        for ct in clicks:
            s = int(ct * SR); c = click(rng); y[s:s + len(c)] += c
        # ventilation: a faint hiss with a slow swell
        hiss = signal.sosfilt(signal.butter(2, [1800, 5200], btype='band', fs=SR, output='sos'), rng.standard_normal(len(y))).astype(np.float32)
        hiss *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * np.arange(len(y)) / SR + ch)).astype(np.float32) * 0.018
        y += hiss
        chans.append(y[:n])
    mono = (chans[0] + chans[1]) / 2
    y = np.stack([0.7 * mono + 0.3 * chans[0], 0.7 * mono + 0.3 * chans[1]], axis=1)
    # the helmet: a small cavity (short, dark reverb), a bump near 500 Hz, the top rolled off
    ir_n = int(0.05 * SR)
    ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / (0.012 * SR))
    ir = signal.sosfilt(signal.butter(2, [250, 3000], btype='band', fs=SR, output='sos'), ir); ir /= np.abs(ir).sum()
    wet = np.stack([signal.fftconvolve(y[:, c], ir)[:n] for c in range(2)], axis=1)
    y = y + 2.2 * wet
    b, a = signal.iirpeak(500, 1.3, fs=SR)
    y = 0.8 * y + 0.5 * signal.lfilter(b, a, y, axis=0)
    y = signal.sosfilt(signal.butter(2, 7500, btype='low', fs=SR, output='sos'), y, axis=0)
    return (y / max(1e-6, np.abs(y).max()) * 0.5).astype(np.float32)


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    for v in [int(a) for a in sys.argv[1:]] or [1, 2, 3]:
        y = render(v, T=46.5 if v == 0 else 16.0)
        wavfile.write(os.path.join(WORK, f'breath_{v}.wav'), SR, (y * 32767).astype(np.int16))
        print(f'breath_{v}.wav written, peak {np.abs(y).max():.2f}')
