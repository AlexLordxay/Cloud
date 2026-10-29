# Sound effects for «Що, якби Місяць упав на Землю?» (the author asked for them: the Moon tearing into the air and the
# blow on the Earth), made from noise and low tones like the dinosaur video's (scenes/chicxulub/sfx.py, which the author
# liked): a roar swelling as the Moon's front and its rubble plough into the air, crackling, rising in pitch; a breath
# of silence; the blow a moment after the flash — the shock's double crack and a slow whump, echoes, the ground's thump,
# a long rolling rumble from all round; then the plume's roar and the rubble raining down. Times are video seconds.
#   python3 scenes/moonfall/sfx.py  -> work/moonfall/sfx.wav
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'chicxulub'))
import sfx as base

SR = 44100
base.SR = SR                                  # the dinosaur video's helpers, at this film's rate
env, filt, sweep_bp, brown, crackle, reverb, pan = base.env, base.filt, base.sweep_bp, base.brown, base.crackle, base.reverb, base.pan
rng = np.random.default_rng(29)
base.rng = rng
T = 46.5
TOUCH = 33.5                                  # the flash (shots.js: the touch)
HIT = TOUCH + 0.35                            # the blow comes a moment after the light


def make():
    n = int(T * SR); t = np.arange(n) / SR
    out = np.zeros((n, 2))
    # the entry: from ~3 s before, the air under the Moon and its rubble roaring, swelling, rising, crackling
    g = env(t, [(0, 0), (30.4, 0), (31.4, 0.15), (32.6, 0.5), (33.3, 1.0), (33.33, 0.0)])
    roar = sweep_bp(rng.standard_normal(n), t, 110, 750, q=0.9) * g
    low = filt(brown(n), 'low', 140) * g
    crk = filt(crackle(n, 380), 'high', 1500) * env(t, [(0, 0), (31.0, 0), (32.4, 0.3), (33.3, 1), (33.33, 0)])
    e = 0.95 * roar / np.max(np.abs(roar)) + 0.6 * low / np.max(np.abs(low)) + 0.3 * crk / np.max(np.abs(crk))
    out += pan(0.42 * np.tanh(e * 1.6) / 1.6, 0.1 * np.sin(2 * np.pi * 0.3 * t))
    # the blow (as in the dinosaur video: a real far-off blast, not a film bang)
    ti = t - HIT; post = ti >= 0; tt = np.maximum(ti, 0)

    def nwave(at, dur, amp):
        x = np.zeros(n); i0 = int((HIT + at) * SR); m = min(int(dur * SR), n - i0)
        x[i0:i0 + m] = amp * np.linspace(1, -1, m); return x
    crack = filt(nwave(0, 0.11, 1.0) + nwave(0.26, 0.16, 0.7) + nwave(0.03, 0.6, 0.6), 'low', 3200, 2)
    echo = np.zeros(n)
    for d, gn, lp in ((0.4, 0.45, 2000), (0.95, 0.32, 1400), (1.7, 0.22, 950), (2.8, 0.15, 650), (4.2, 0.1, 450)):
        k = int(d * SR); e2 = np.zeros(n); e2[k:] = crack[:n - k]; echo += gn * filt(e2, 'low', lp, 2)
    thump = filt(rng.standard_normal(n), 'low', 70) * np.exp(-tt / 2.0) * post
    roll = np.zeros((n, 2))
    for _ in range(1100):
        at = rng.exponential(2.6) if rng.random() < 0.85 else rng.uniform(0, 10)
        i0 = int((HIT + at) * SR)
        if i0 >= n - SR // 10: continue
        L = rng.uniform(0.06, 0.6); m = min(int(L * SR), n - i0); k = np.arange(m)
        fc = 50 * np.exp(rng.uniform(0, np.log(12)))
        burst = rng.standard_normal(m) * np.exp(-k / (SR * L / 3.5)) * (1 - np.exp(-k / (SR * 0.004)))
        burst = filt(burst, 'band', [fc / 1.6, fc * 1.6], 2) * np.exp(-at / 4.0) * rng.lognormal(0, 0.6)
        ang = (rng.uniform(-0.9, 0.9) + 1) * np.pi / 4
        roll[i0:i0 + m, 0] += burst * np.cos(ang); roll[i0:i0 + m, 1] += burst * np.sin(ang)
    quake = filt(brown(n), 'low', 160) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt + 3 * np.sin(2 * np.pi * 0.6 * tt))) * np.exp(-tt / 6) * post
    rush = sweep_bp(rng.standard_normal(n), t, 2500, 300, q=1.2) * env(ti, [(0, 0), (0.8, 0), (1.8, 0.8), (4, 0.25), (7, 0)])
    roarF = filt(rng.standard_normal(n), 'low', 380) * env(ti, [(0, 0), (0.6, 0.6), (5, 0.45), (9, 0.2), (12, 0.08)])
    debris = filt(crackle(n, 140), 'high', 900) * env(ti, [(0, 0), (2, 0), (3.5, 0.6), (8, 0.35), (12, 0.12)])
    nm = lambda x: x / np.max(np.abs(x))
    cm = np.max(np.abs(crack))
    mono = (1.0 * crack / cm + 0.7 * echo / cm + 0.9 * nm(thump) + 0.35 * nm(quake) + 0.3 * nm(rush) + 0.3 * nm(roarF) + 0.25 * nm(debris))
    imp = 1.0 * roll / np.max(np.abs(roll)) + pan(mono, 0.05 * np.sin(2 * np.pi * 0.11 * t))
    out += np.tanh(imp * 1.15) / 1.15
    # the hush: everything drops for the last moment before the flash
    out *= (1 - 0.9 * env(t, [(0, 0), (TOUCH - 0.18, 0), (TOUCH - 0.08, 1), (HIT, 1), (HIT + 0.001, 0), (T, 0)]))[:, None]
    out = np.stack([reverb(out[:, 0]), reverb(out[:, 1])], 1)
    # phones: a little more of the middle, where their speakers are
    mid = np.stack([filt(out[:, c], 'band', [250, 2500], 2) for c in range(2)], 1)
    out = out + 0.35 * mid
    out *= env(t, [(0, 1), (T - 3.0, 1), (T, 0)])[:, None]
    return out / np.max(np.abs(out)) * 0.89


if __name__ == '__main__':
    tools = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
    dst = os.path.join(tools, 'work', 'moonfall', 'sfx.wav')
    wavfile.write(dst, SR, (make() * 32767).astype(np.int16))
    print(dst)
