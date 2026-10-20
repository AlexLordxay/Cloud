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
DELAY = 0.7
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

    # the impact, heard at HIT: a moment's hush before it, then the blow
    ti = t - HIT; post = ti >= 0
    tt = np.maximum(ti, 0)
    click = rng.standard_normal(n) * np.exp(-tt / 0.006) * post
    sub = np.sin(2 * np.pi * (55 * tt - 15 * tt ** 2 / 2.5) * (tt < 2.5) + 2 * np.pi * 21 * tt * (tt >= 2.5)) * np.exp(-tt / 2.2) * post
    blast = filt(rng.standard_normal(n), 'low', 1800) * np.exp(-tt / 0.9) * post
    # phones can't play the sub-bass: its overtones (a driven sub) and a low-mid boom carry the blow on small speakers
    subH = np.tanh(3.5 * sub) - 0.6 * sub
    boom = filt(filt(rng.standard_normal(n), 'high', 90), 'low', 450) * np.exp(-tt / 1.4) * post
    body = sweep_bp(rng.standard_normal(n), t, 1200, 90, q=0.7) * np.exp(-tt / 2.8) * post
    rum_env = np.exp(-tt / 7.0) * (0.7 + 0.3 * filt(rng.standard_normal(n), 'low', 0.6, 2) * 8)
    rumble = filt(brown(n), 'low', 110) * np.clip(rum_env, 0, 1.2) * post
    rush = sweep_bp(rng.standard_normal(n), t, 2500, 300, q=1.2) * env(ti, [(0, 0), (0.8, 0), (1.6, 0.8), (3.5, 0.2), (6, 0)])
    roarF = filt(rng.standard_normal(n), 'low', 380) * env(ti, [(0, 0), (0.5, 0.6), (4, 0.45), (10, 0.15)])
    debris = filt(crackle(n, 120), 'high', 900) * env(ti, [(0, 0), (1.5, 0), (3, 0.6), (8, 0.3), (10, 0.1)])
    imp = (0.9 * click + 0.55 * sub + 0.9 * subH + 1.7 * boom / np.max(np.abs(boom)) + 1.3 * blast / np.max(np.abs(blast))
           + 1.3 * body / np.max(np.abs(body)) + 0.6 * rumble + 0.5 * rush / np.max(np.abs(rush))
           + 0.45 * roarF / np.max(np.abs(roarF)) + 0.35 * debris / np.max(np.abs(debris)))
    imp = np.tanh(imp * 2.2) / 2.2                                    # driven harder: denser, louder on small speakers
    out += pan(imp, 0.05 * np.sin(2 * np.pi * 0.11 * t))
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
