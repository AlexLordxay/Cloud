# Shared helpers for the Earth-history score and sfx (pure numpy/scipy, everything synthesized here).
import json, os, subprocess, re
import numpy as np
from scipy import signal

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
SCN = os.path.dirname(HERE)
WORK = os.path.abspath(os.path.join(SCN, '../../work/earth_history'))
os.makedirs(WORK, exist_ok=True)
TL = json.load(open(os.path.join(SCN, 'timeline.json')))
DUR = TL['duration']
N = int(round(DUR * SR))
ACT = {a['id']: (a['start'], a['end']) for a in TL['acts']}
TIM = json.load(open(os.path.join(SCN, 'timing.json')))
END_CARD = TL['end_card'][0]


def vt(fname, t):
    """time inside a voice file -> time on the cut"""
    for a in TL['acts']:
        for f, fr, to, at in a['voice']:
            if f == fname and fr - 0.6 <= t <= to + 0.6:
                return at + t - fr
    raise ValueError((fname, t))


def sent(fname, i):
    s = TIM[fname][i]
    return vt(fname, s['start']), vt(fname, s['end'])


def interp(pts):
    a = np.array(pts, float)
    return lambda t: np.interp(t, a[:, 0], a[:, 1])


def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def sos_f(x, kind, f, order=2):
    sos = signal.butter(order, f, btype=kind, fs=SR, output='sos'); return signal.sosfilt(sos, x)


def wav_write(path, L, R):
    import scipy.io.wavfile as w
    y = np.stack([L, R], 1)
    w.write(path, SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))


def ebur(path):
    r = subprocess.run(['ffmpeg', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    s = r[r.rfind('Summary'):]
    I = float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1))
    TP = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1))
    return I, TP


def normalize(L, R, lufs, tp_ceiling=-2.5, tmp='/tmp/_norm.wav'):
    """gain to the target integrated loudness, then a smooth look-ahead limiter to keep true peak under the ceiling"""
    wav_write(tmp, L, R)
    I, _ = ebur(tmp)
    g = 10 ** ((lufs - I) / 20)
    L, R = L * g, R * g
    ceil = 10 ** (tp_ceiling / 20)
    pk = np.maximum(np.abs(L), np.abs(R))
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    if need.min() < 1:
        w = int(0.4 * SR)                      # hold the reduction 0.4 s each way, smoothed: no audible pumping
        from scipy.ndimage import minimum_filter1d
        need = minimum_filter1d(need, w)
        need = signal.oaconvolve(need, np.hanning(w) / np.hanning(w).sum(), mode='same')
        L, R = L * need, R * need
        print('limiter max reduction dB', 20 * np.log10(need.min()))
    return L, R, g
