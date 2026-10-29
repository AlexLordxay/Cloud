# The soundtrack of «Що, якби Місяць упав на Землю?»: no music for now (the author: later), only the astronaut's
# breathing (breath.py, the film schedule) and the suit's soft caution tone in the last minutes before the impact.
#   python3 scenes/moonfall/sound.py   ->  work/moonfall/audio.wav
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import breath

SR = breath.SR
WORK = breath.WORK


def beeps(T):
    # two soft tones (1.4 and 1.05 kHz), once a second from 27.5 s to the gasp: the suit's caution, heard in the helmet
    y = np.zeros(int(T * SR), np.float32)
    n = int(0.09 * SR); env = np.sin(np.pi * np.arange(n) / n) ** 2
    t = 27.5
    while t < 32.7:
        for k, f in enumerate((1400.0, 1050.0)):
            s = int((t + k * 0.12) * SR)
            y[s:s + n] += (np.sin(2 * np.pi * f * np.arange(n) / SR) * env).astype(np.float32)
        t += 1.0
    return y * 0.05


def main():
    T = 46.5
    b = breath.render(0, T=T)
    bp = beeps(T)
    bp = signal.lfilter(*signal.iirpeak(1200, 2.0, fs=SR), bp) * 0.6 + bp * 0.5
    y = b + np.stack([bp, bp], axis=1)
    fade = np.clip((T - np.arange(len(y)) / SR) / 2.0, 0, 1)[:, None]          # out over the end card
    y *= fade
    y = y / max(1e-6, np.abs(y).max()) * 0.8
    os.makedirs(WORK, exist_ok=True)
    wavfile.write(os.path.join(WORK, 'audio.wav'), SR, (y * 32767).astype(np.int16))
    print('audio.wav written')


if __name__ == '__main__':
    main()
