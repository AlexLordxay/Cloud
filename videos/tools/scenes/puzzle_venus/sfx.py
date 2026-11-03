# «На якій я планеті?» (Венера) — the small sounds, synthesised (no samples): a soft pop as each clue and option comes
# up, a clock-like tick on each number of the countdown (a deeper one on «1»), and a bright two-note chime at the answer.
#   python3 scenes/puzzle_venus/sfx.py   ->  work/puzzle_venus/sfx.wav
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SC = json.load(open(os.path.join(HERE, 'scene.json'))); B = SC['beats']
OUT = os.path.join(HERE, '../../work/puzzle_venus/sfx.wav')
SR = 44100
OUT_ = SC.get('out', {}); N = int(OUT_.get('duration', SC['duration']) * SR)
mix = np.zeros(N)


def add(x, at, k=1.0):
    i = int(at * SR); j = min(N, i + len(x))
    if i < N: mix[i:j] += k * x[:j - i]


def tone(f, d, decay, harm=((1, 1.0),)):
    t = np.arange(int(d * SR)) / SR
    env = np.exp(-t / decay) * np.minimum(1, t / 0.003)
    return env * sum(a * np.sin(2 * np.pi * f * h * t) for h, a in harm)


def pop(f=900):          # a soft bubble: a short pitch drop
    t = np.arange(int(0.12 * SR)) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-t / 0.02))) / SR
    return np.sin(ph) * np.exp(-t / 0.03) * np.minimum(1, t / 0.002)


def tick(f=1800, d=0.09):
    rng = np.random.default_rng(int(f))
    t = np.arange(int(d * SR)) / SR
    n = rng.standard_normal(len(t)) * np.exp(-t / 0.004)
    return 0.6 * tone(f, d, 0.018, ((1, 1), (2.7, 0.4))) + 0.25 * n


pops = [B['c1'] + 0.2, B['c2'] + 0.2, B['c3'] + 0.2, B['opts'] + 0.2, B['opts'] + 0.65, B['opts'] + 1.1]
for k, at in enumerate(pops): add(pop(700 + 80 * k), at, 0.5)
for at, f in [(B['n3'], 1500), (B['n2'], 1500), (B['n1'], 1100)]:
    add(tick(f), at, 0.7); add(tick(f * 0.75), at + 1.0, 0.35)          # tick … tock
# the answer: a bright chime, a fifth up, with a long shimmer
ch = tone(1318.5, 2.5, 0.7, ((1, 1), (2, 0.3), (3, 0.12))) + 0.8 * np.concatenate([np.zeros(int(0.09 * SR)), tone(1975.5, 2.5, 0.8, ((1, 1), (2, 0.25)))])[:int(2.5 * SR)]
if OUT_.get('answer', True): add(ch, B['ans'], 0.35)
else: add(pop(520), OUT_['cut'][0], 0.6)                      # no answer: just a soft pop for the «?»
mix = mix / max(1e-9, np.abs(mix).max()) * 0.7
st = np.stack([mix, mix], 1)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print('written', OUT)
