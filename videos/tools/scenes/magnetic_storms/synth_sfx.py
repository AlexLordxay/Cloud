# «Магнітні бурі» — sound effects synthesised from noise and sines (author's rule: no AI effects). Stereo 44.1 kHz -> sfx/*.wav
#   flare.wav    6 s — the flare: a deep swelling rumble and a slow rising rush
#   cme.wav      5 s — the plasma cloud flying past: a wide airy rush sweeping down in pitch
#   impact.wav   5 s — hitting the magnetic shield: a soft low thump and a ringing electric shimmer
#   flow.wav     7 s — the solar wind flowing round the shield: a quiet hiss with slow swells
#   shimmer.wav  4 s — the aurora: very quiet high shimmer
#   static.wav   5 s — storm effects: radio static, crackles and drop-outs
#   sparks.wav   5 s — 1859: telegraph sounder clicks and electric sparks
#   python3 synth_sfx.py
import os, sys, numpy as np, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(TOOLS, 'scenes', 'nuclear_winter'))
import synth_sfx as S
from synth_sfx import bp, lp, hp, brown, white, lfo, env, stereo, SR
OUT = os.path.join(HERE, 'sfx')

def flare(n):
    t = np.arange(n) / SR
    swell = np.clip(t / 1.6, 0, 1) ** 2 * np.exp(-np.maximum(t - 2.2, 0) / 1.6)
    rumble = lp(brown(n), 120) * swell * (0.6 + 0.4 * lfo(n, 4)) * 2.2
    f = 28 + 10 * np.clip(t / 2, 0, 1)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * swell * 0.6
    rush = bp(white(n), 300, 2500) * swell * 0.25
    return rumble + tone + rush

def cme(n):
    t = np.arange(n) / SR; T = n / SR
    shape = np.sin(np.pi * np.clip(t / T, 0, 1)) ** 1.5
    x = np.zeros(n); hop = 2048
    w = white(n)
    for i in range(0, n, hop):                       # a band sweeping down (Doppler-like pass)
        c = 3500 * (1 - i / n) + 250
        seg = bp(w[max(0, i - 4096):i + hop], c * 0.6, min(c * 1.6, 18000), 2)[-(min(hop, n - i)):]
        x[i:i + len(seg)] = seg
    return (x * 0.5 + lp(brown(n), 200) * 0.6) * shape * (0.7 + 0.3 * lfo(n, 6))

def impact(n):
    t = np.arange(n) / SR; T0 = 0.05
    f = 26 + 30 * np.exp(-np.maximum(t - T0, 0) / 0.3)
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.02, 0.9, T0) * 1.1
    body = lp(white(n), 260) * env(n, 0.03, 0.8, T0) * 0.9
    ring = np.zeros(n)
    for fr, a in ((220, 0.3), (331, 0.2), (447, 0.14), (662, 0.08)):
        ring += np.sin(2 * np.pi * fr * t * (1 + 0.002 * np.sin(2 * np.pi * 5 * t))) * a
    ring *= env(n, 0.3, 1.8, T0) * 0.35
    return thump + body + ring

def flow(n):
    t = np.arange(n) / SR; T = n / SR
    fade = np.clip(t / 1.2, 0, 1) * np.clip((T - t) / 1.5, 0, 1)
    return (bp(white(n), 1500, 7000) * 0.18 + bp(white(n), 200, 900) * 0.25) * (0.5 + 0.5 * lfo(n, 1.5)) * fade

def shimmer(n):
    t = np.arange(n) / SR; T = n / SR
    fade = np.clip(t / 1.0, 0, 1) * np.clip((T - t) / 1.2, 0, 1)
    x = np.zeros(n)
    for fr in (1760, 2217, 2637, 3520):
        x += np.sin(2 * np.pi * fr * t + 3 * np.sin(2 * np.pi * 0.7 * t + fr)) * (0.5 + 0.5 * lfo(n, 3))
    return (x * 0.04 + hp(white(n), 6000) * 0.03) * fade

def static(n):
    t = np.arange(n) / SR; T = n / SR
    fade = np.clip(t / 0.6, 0, 1) * np.clip((T - t) / 1.0, 0, 1)
    hiss = bp(white(n), 800, 6000) * 0.2 * (0.3 + 0.7 * (lfo(n, 10) > 0.45))
    cr = np.zeros(n); rng = np.random.default_rng(3)
    for _ in range(140):
        i = rng.integers(0, n - 400); cr[i:i + 40] += rng.standard_normal(40) * rng.uniform(0.2, 0.7)
    return (hiss + hp(cr, 1500)) * fade

def sparks(n):
    t = np.arange(n) / SR; x = np.zeros(n); rng = np.random.default_rng(11)
    # telegraph sounder: clack (down) and click (up), irregular like a message
    tt = 0.25
    while tt < n / SR - 0.6:
        d = rng.choice([0.08, 0.24]); i0 = int(tt * SR); i1 = int((tt + d) * SR)
        for i, g in ((i0, 0.8), (i1, 0.5)):
            m = min(n - i, 900); x[i:i + m] += bp(rng.standard_normal(m), 1200, 4200, 2) * np.exp(-np.arange(m) / 90) * g
        tt += d + rng.choice([0.08, 0.08, 0.24, 0.5])
    # sparks: short bright arcs
    for _ in range(9):
        i = int(rng.uniform(0.6, n / SR - 0.4) * SR); m = int(rng.uniform(0.05, 0.18) * SR)
        x[i:i + m] += hp(rng.standard_normal(m), 2500) * np.exp(-np.arange(m) / (m / 3)) * rng.uniform(0.4, 0.9)
    return x * 0.8

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, fn, sec in (('flare', flare, 6), ('cme', cme, 5), ('impact', impact, 5), ('flow', flow, 7),
                          ('shimmer', shimmer, 4), ('static', static, 5), ('sparks', sparks, 5)):
        x = stereo(fn, int(sec * SR)); x = x / (np.abs(x).max() + 1e-9) * 0.9
        S.write = getattr(S, 'write', None)
        import wave
        with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
        print(name)
