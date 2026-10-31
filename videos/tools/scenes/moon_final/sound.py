# The finale's sound: the astronaut's breathing in the helmet (moonfall's breath.py, a schedule of its own) and the
# organ (music.js). Walking: steady, a little effortful; he looks up at the Earth — a breath caught and held; a soft
# breath out; one more in, and as his head sinks a long, shaky sigh; a last quiet breath under the question.
# Levelled to the cartoon it follows (videos/stick_story.mp4, about -18.5 LUFS).
#   node scenes/moon_final/music.js && python3 scenes/moon_final/sound.py   ->  work/moon_final/audio.wav
import os, sys, subprocess
import numpy as np
from scipy.io import wavfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'moonfall'))
import breath

T = 13.0
SR = breath.SR
WORK = os.path.abspath(os.path.join(HERE, '../../work/moon_final'))
# (kind, start, length, level, band from, band to[, effect]) as in breath.py
EVENTS = [
    ('in', 0.10, 0.75, 0.50, 1100, 2500), ('out', 0.95, 1.00, 0.70, 750, 380),
    ('in', 2.15, 0.75, 0.50, 1100, 2500), ('out', 3.00, 1.00, 0.70, 750, 380),
    ('in', 4.20, 0.70, 0.45, 1100, 2500), ('out', 4.95, 0.55, 0.55, 750, 380),
    ('in', 5.45, 0.90, 0.60, 1300, 2900),                       # the Earth: a breath caught, held
    ('out', 7.00, 1.20, 0.45, 700, 360),
    ('in', 8.05, 0.80, 0.45, 1000, 2200),
    ('out', 8.95, 2.40, 0.85, 650, 300, 'shaky'),               # the sigh, as the head sinks
    ('in', 11.60, 1.00, 0.35, 900, 2000),
]
CLICKS = [0.10, 2.15, 4.20]
TARGET = -18.5


def loudness(path):
    ff = __import__('imageio_ffmpeg').get_ffmpeg_exe()
    r = subprocess.run([ff, '-hide_banner', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(r.rsplit('I:', 1)[1].split('LUFS')[0])


def main():
    breath.schedule = lambda v: (EVENTS, CLICKS)
    br = breath.render(0, T=T, seed=31)                        # peak 0.5
    sr, org = wavfile.read(os.path.join(WORK, 'organ.wav'))
    org = org.astype(np.float32) / 32767
    org = org[:len(br)] / max(1e-6, np.abs(org).max()) * 0.32
    mix = br * 0.9 + org
    out = os.path.join(WORK, 'audio.wav')
    wavfile.write(out, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    g = 10 ** ((TARGET - loudness(out)) / 20)
    mix = mix * g
    print(f'gain {20 * np.log10(g):+.1f} dB, peak {np.abs(mix).max():.2f}')
    wavfile.write(out, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    print('written', out, f'{loudness(out):.1f} LUFS')


if __name__ == '__main__':
    main()
