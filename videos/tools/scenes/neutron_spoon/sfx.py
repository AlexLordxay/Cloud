# «Ложка нейтронної зорі» — the synthesised effects on one track (work/neutron_spoon/sfx.wav), then the final mix:
# music (ducked by the voice and the effects) + effects (ducked under the voice) + voice -> -14 LUFS, put onto the
# picture of videos/neutron_spoon.mp4 (the video stream is copied). Run after ./make.sh neutron_spoon:
#   python3 scenes/neutron_spoon/sfx.py
#   * the pulsar: a click each time a beam sweeps past (two per turn), as radio pulsars sound when their signal is
#     played as audio; at 0.45 turns a second a slow heartbeat, spun up to 716 they fuse into a tone (~1.4 kHz), kept quiet;
#   * a low hum from the star's surroundings; soft whooshes at the three flash cuts; a heavy thud when the spoon lands.
import json, math, os, subprocess
import numpy as np
import imageio_ffmpeg
from scipy.signal import butter, lfilter

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'neutron_spoon'); VIDEO = os.path.join(TOOLS, '..', 'neutron_spoon.mp4')
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']
SR = 44100
N = int(SR * (DUR + 1))
t = np.arange(N) / SR
rng = np.random.default_rng(5)

def rate(x):
    if x < 22.5: return 0.45
    if x < 26.0:
        u = min(1.0, max(0.0, (x - 22.5) / 3.5)); e = 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
        return min(716.0, 0.45 * math.exp(math.log(716 / 0.45) * e))
    return 716.0

def bp(x, lo, hi, order=2):
    b, a = butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band'); return lfilter(b, a, x)

def env(x0, x1, a=0.05, r=0.3):
    e = np.clip((t - x0) / a, 0, 1) * np.clip((x1 - t) / r, 0, 1); return e

out = np.zeros((N, 2))
# --- the pulsar clicks: phase integral of 2 × rate (two beams), a click at each whole number ---
ph = np.cumsum(np.array([2 * rate(x) for x in t[::32]]).repeat(32)[:N]) / SR
idx = np.nonzero(np.diff(np.floor(ph)) > 0)[0]
click = np.zeros(N)
for i in idx:
    r = rate(i / SR)
    L = int(SR * (0.06 if r < 3 else 0.012 if r < 40 else 0.004))
    k = np.arange(L) / SR
    tone = np.sin(2 * np.pi * 900 * k) * 0.5 + rng.standard_normal(L) * 0.5
    seg = tone * np.exp(-k / (L / SR / 4))
    j = min(N, i + L); click[i:j] += seg[:j - i]
click = bp(click, 300, 4000)
# the ticks at 20 % of the first cut; the buzz they fuse into (from ~25 s) at 10 % (author: «пилосос», but keep a sound)
lvl = np.interp(t, [0, 2, 22.0, 24.5, 26.5, 27.6, 29.5, 31, DUR], [0.10, 0.10, 0.10, 0.20, 0.24, 0.20, 0.08, 0.05, 0.0])
lvl *= np.interp(t, [0, 24.3, 25.3, DUR], [0.2, 0.2, 0.1, 0.1])
click *= lvl / (np.abs(click).max() + 1e-9) * 3.0
out[:, 0] += click; out[:, 1] += click
# --- a low hum: filtered noise, swelling near the star ---
hum = bp(rng.standard_normal(N), 40, 160) * 0.5
hum *= np.interp(t, [0, 1, 8, 8.3, 14.6, 14.7, 22.1, 26, 27, DUR], [0.02, 0.05, 0.06, 0.03, 0.03, 0.015, 0.03, 0.08, 0.05, 0.0])
hum *= np.interp(t, [0, 24.3, 25.3, DUR], [1.0, 1.0, 0.1, 0.1])
out[:, 0] += hum; out[:, 1] += np.roll(hum, 300)
# --- whooshes into the flash cuts ---
for c in (8.3, 14.7, 22.1):
    w = bp(rng.standard_normal(N), 400, 6000) * np.exp(-((t - c) / 0.25) ** 2) * (t < c + 0.6)
    sweep = bp(rng.standard_normal(N), 150, 900) * np.exp(-((t - c - 0.15) / 0.35) ** 2)
    out[:, 0] += 0.20 * w + 0.15 * sweep; out[:, 1] += 0.20 * np.roll(w, 400) + 0.15 * sweep
# --- the spoon lands: a deep thud and a metallic ring ---
x0 = 18.75; k = np.clip(t - x0, 0, None); on = t >= x0
thud = (np.sin(2 * np.pi * (42 + 30 * np.exp(-k * 8)) * k) * np.exp(-k * 3.2) + bp(rng.standard_normal(N), 60, 400) * np.exp(-k * 18) * 0.6) * on
ring = (np.sin(2 * np.pi * 1180 * k) * 0.5 + np.sin(2 * np.pi * 1740 * k) * 0.3 + np.sin(2 * np.pi * 2630 * k) * 0.2) * np.exp(-k * 2.2) * on
out[:, 0] += 0.55 * thud + 0.05 * ring; out[:, 1] += 0.55 * thud + 0.05 * np.roll(ring, 200)
# a quieter thud as the people's pan bottoms out
x1 = 19.05; k = np.clip(t - x1, 0, None); on = t >= x1
out[:, 0] += 0.18 * np.sin(2 * np.pi * 55 * k) * np.exp(-k * 5) * on; out[:, 1] += 0.18 * np.sin(2 * np.pi * 55 * k) * np.exp(-k * 5) * on

out = np.clip(out, -1, 1)
sfx = os.path.join(WORK, 'sfx.wav')
import wave
with wave.open(sfx, 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((out * 32767).astype('<i2').tobytes())
print('sfx.wav')

if os.path.exists(VIDEO):
    music, voice = os.path.join(WORK, 'audio.wav'), os.path.join(WORK, 'voice.wav')
    mix = ('[1:a]volume=2.0,asplit=3[v][sc][sc2];[2:a]volume=1.6,asplit=2[fx][fxsc];'
           '[0:a]volume=0.7[m0];[m0][sc]sidechaincompress=threshold=0.04:ratio=3:attack=60:release=800[m1];'
           '[m1][fxsc]sidechaincompress=threshold=0.08:ratio=2.5:attack=20:release=600[m];'
           '[fx][sc2]sidechaincompress=threshold=0.05:ratio=2:attack=40:release=700[fxd];'
           f'[m][fxd][v]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=13,afade=t=out:st={DUR - 1.5}:d=1.5[a]')
    tmp = VIDEO + '.tmp.mp4'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', music, '-i', voice, '-i', sfx, '-i', VIDEO, '-filter_complex', mix,
                    '-map', '[a]', '-map', '3:v', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-movflags', '+faststart', '-t', str(DUR), tmp], check=True)
    os.replace(tmp, VIDEO)
    print('mixed: videos/neutron_spoon.mp4')
