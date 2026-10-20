# Sound for "Що сталося з Землею, коли вимерли динозаври", made from noise and low tones (no recordings), in step with
# the shots: a quiet low bed; the asteroid's roar in the air, swelling and sweeping right to left as it falls, crackling;
# a breath of silence; the impact — a click, a sub-bass blow felt more than heard, a gritty blast and a long rolling
# rumble — then the blast's rush, the fireball's roar and falling debris crackling. Heard "as from the ground",
# deep and heavy rather than a film bang: up where the camera is there is no air to carry any of it.
#   python3 scenes/chicxulub/sfx.py [out.wav]      -> work/chicxulub/sfx.wav (entry 7.5 s + impact 10 s)
import os, sys, numpy as np
from scipy import signal

SR = 48000
ENTRY, IMPACT = 7.5, 10.0                     # shot lengths (s); the impact comes at the end of the entry
# we watch from far off: the sound reaches us a little after the light (the author: the blow came too soon), so the
# whole track runs DELAY late — the flash in the roar's last moment, the hush and the blow after it
DELAY = 2.2
HIT = ENTRY + DELAY
rng = np.random.default_rng(66)


def env(t, pts):
    # a piecewise-linear envelope through (time, value) points
    a = np.array(pts, float); return np.interp(t, a[:, 0], a[:, 1])


def filt(x, kind, f, order=4):
    sos = signal.butter(order, f, btype=kind, fs=SR, output='sos'); return signal.sosfilt(sos, x)


def sweep_bp(x, t, f0, f1, q=1.5, block=0.02):
    # band-pass whose centre glides from f0 to f1 (log), done block by block with state carried over
    out = np.zeros_like(x); n = int(block * SR); zi = None
    for i in range(0, len(x), n):
        k = (t[min(i, len(t) - 1)] - t[0]) / max(t[-1] - t[0], 1e-9)
        fc = f0 * (f1 / f0) ** k; bw = fc / q
        sos = signal.butter(2, [max(fc - bw / 2, 20), min(fc + bw / 2, SR / 2 - 100)], btype='band', fs=SR, output='sos')
        if zi is None or zi.shape != (sos.shape[0], 2): zi = np.zeros((sos.shape[0], 2))
        out[i:i + n], zi = signal.sosfilt(sos, x[i:i + n], zi=zi)
    return out


def brown(n):
    b = np.cumsum(rng.standard_normal(n)); b -= filt(b, 'low', 2, 1); return b / np.max(np.abs(b))


def crackle(n, rate, decay=0.004):
    # sparse random clicks, each a tiny decaying burst
    x = np.zeros(n); k = rng.random(n) < rate / SR; x[k] = rng.standard_normal(k.sum())
    ir = np.exp(-np.arange(int(decay * SR * 5)) / (decay * SR)) * rng.standard_normal(int(decay * SR * 5))
    return signal.fftconvolve(x, ir)[:n]


def reverb(x, secs=3.2, wet=0.35):
    n = int(secs * SR); ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * secs / 6.9))
    ir = filt(ir, 'low', 3000, 2); ir /= np.sqrt(np.sum(ir ** 2))
    return (1 - wet) * x + wet * signal.fftconvolve(x, ir)[:len(x)]


def pan(x, p):
    # p from -1 (left) to 1 (right), equal power
    a = (np.asarray(p) + 1) * np.pi / 4; return np.stack([x * np.cos(a), x * np.sin(a)], 1)


def make():
    total = ENTRY + IMPACT; n = int(total * SR); t = np.arange(n) / SR
    out = np.zeros((n, 2))
    # the bed: a deep, slowly breathing drone
    bed = filt(brown(n), 'low', 90) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)) + 0.3 * np.sin(2 * np.pi * 41 * t) * env(t, [(0, 0), (1, 1), (total, 1)])
    out += pan(bed * 0.06, 0)

    # the entry: air glowing from ~1.5 s, a roar swelling to the end, rising in pitch, sweeping right → left
    te = t[t < HIT]; ne = len(te); tv = te - DELAY                 # tv: the picture's time the sound belongs to
    g = env(tv, [(0, 0), (1.5, 0.05), (3.5, 0.35), (6.0, 0.8), (7.35, 1.0), (7.5, 0.0)])
    roar = sweep_bp(rng.standard_normal(ne), te, 160, 900, q=0.9) * g
    low = filt(brown(ne), 'low', 140) * g
    crk = filt(crackle(ne, 40 + 400 * 1), 'high', 1500) * env(tv, [(0, 0), (3, 0.1), (7.3, 1), (7.5, 0)])
    e = 0.95 * roar / np.max(np.abs(roar)) + 0.6 * low + 0.32 * crk / np.max(np.abs(crk))
    e = np.tanh(e * 1.6) / 1.6
    out[:ne] += pan(0.45 * e, env(tv, [(0, 0.7), (7.5, -0.3)]))

    # the impact, heard at HIT — built like a real far-off blast, not a film bang: the shock front's double crack
    # (N-waves: the pressure leaps up, falls through, snaps back) and a slow whump; the ground's thump; echoes of the
    # crack off the land, the sea floor and the layers of the air, later, fainter, duller; then the rumble rolling in
    # from all round — hundreds of short low bursts at random moments and places, thinning out over seconds, as thunder
    # rolls; the ground trembling; the highs lost on the way. After it the blast's rush, the fireball's roar, debris.
    ti = t - HIT; post = ti >= 0; tt = np.maximum(ti, 0)

    def nwave(at, dur, amp):
        x = np.zeros(n); i0 = int((HIT + at) * SR); m = min(int(dur * SR), n - i0)
        x[i0:i0 + m] = amp * np.linspace(1, -1, m); return x
    crack = filt(nwave(0, 0.09, 1.0) + nwave(0.21, 0.13, 0.7) + nwave(0.02, 0.45, 0.6), 'low', 3500, 2)
    echo = np.zeros(n)
    for d, gn, lp in ((0.33, 0.45, 2200), (0.78, 0.32, 1500), (1.45, 0.22, 1000), (2.4, 0.15, 700), (3.6, 0.1, 500)):
        k = int(d * SR); e = np.zeros(n); e[k:] = crack[:n - k]; echo += gn * filt(e, 'low', lp, 2)
    thump = filt(rng.standard_normal(n), 'low', 70) * np.exp(-tt / 1.6) * post
    roll = np.zeros((n, 2))
    for g in range(800):
        at = rng.exponential(1.8) if rng.random() < 0.85 else rng.uniform(0, 9)
        i0 = int((HIT + at) * SR)
        if i0 >= n - SR // 10: continue
        L = rng.uniform(0.06, 0.5); m = min(int(L * SR), n - i0); k = np.arange(m)
        fc = 50 * np.exp(rng.uniform(0, np.log(12)))                        # 50–600 Hz, evenly per octave
        burst = rng.standard_normal(m) * np.exp(-k / (SR * L / 3.5)) * (1 - np.exp(-k / (SR * 0.004)))
        burst = filt(burst, 'band', [fc / 1.6, fc * 1.6], 2) * np.exp(-at / 3.0) * rng.lognormal(0, 0.6)
        ang = (rng.uniform(-0.9, 0.9) + 1) * np.pi / 4
        roll[i0:i0 + m, 0] += burst * np.cos(ang); roll[i0:i0 + m, 1] += burst * np.sin(ang)
    quake = filt(brown(n), 'low', 160) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * tt + 3 * np.sin(2 * np.pi * 0.7 * tt))) * np.exp(-tt / 5) * post
    rush = sweep_bp(rng.standard_normal(n), t, 2500, 300, q=1.2) * env(ti, [(0, 0), (0.8, 0), (1.6, 0.8), (3.5, 0.2), (6, 0)])
    roarF = filt(rng.standard_normal(n), 'low', 380) * env(ti, [(0, 0), (0.5, 0.6), (4, 0.45), (10, 0.15)])
    debris = filt(crackle(n, 120), 'high', 900) * env(ti, [(0, 0), (1.5, 0), (3, 0.6), (8, 0.3), (10, 0.1)])
    nm = lambda x: x / np.max(np.abs(x))
    cm = np.max(np.abs(crack))
    mono = (1.0 * crack / cm + 0.7 * echo / cm + 0.9 * nm(thump) + 0.35 * nm(quake)
            + 0.3 * nm(rush) + 0.28 * nm(roarF) + 0.22 * nm(debris))
    imp = 1.0 * roll / np.max(np.abs(roll)) + pan(mono, 0.05 * np.sin(2 * np.pi * 0.11 * t))
    imp = np.tanh(imp * 1.15) / 1.15                                 # only the very peaks rounded: the blast keeps its punch
    out += imp
    # the hush: everything drops for the last ~0.15 s before contact
    out *= (1 - 0.85 * env(t, [(0, 0), (HIT - 0.16, 0), (HIT - 0.06, 1), (HIT, 1), (HIT + 0.001, 0), (total, 0)]))[:, None]

    out = np.stack([reverb(out[:, 0]), reverb(out[:, 1])], 1)
    fade = env(t, [(0, 0), (0.5, 1), (total - 1.0, 1), (total, 0)])
    out *= fade[:, None]
    return out / np.max(np.abs(out)) * 0.89


if __name__ == '__main__':
    tools = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
    dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tools, 'work', 'chicxulub', 'sfx.wav')
    from scipy.io import wavfile
    wavfile.write(dst, SR, (make() * 32767).astype(np.int16))
    print(dst)
