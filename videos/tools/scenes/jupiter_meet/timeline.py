# The order of the shots of "Знайомся: Юпітер" and where each begins: shots follow one another, each crossfading
# into the next over XF frames. Lengths are read from shots.js (dur: …), so a retimed shot moves everything after it.
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, XF = 30, 18
ORDER = ['hook', 'zoom', 'spin', 'dive', 'moons', 'ioapp', 'iobreath', 'pele', 'loki', 'europa', 'clipper', 'ganymede', 'dawn', 'outro']


def lengths():
    src = open(os.path.join(HERE, 'shots.js'), encoding='utf-8').read()
    return {m.group(1): float(m.group(2)) for m in re.finditer(r'^\s{4}(\w+): \{ dur: ([\d.]+)', src, re.M)}


def starts():
    """[(shot, first frame, frames)] on the video's timeline."""
    L, out, at = lengths(), [], 0
    for i, s in enumerate(ORDER):
        n = round(L[s] * FPS)
        out.append((s, at, n))
        at += n - XF
    return out


def duration():
    s, at, n = starts()[-1]
    return (at + n) / FPS


if __name__ == '__main__':
    for s, at, n in starts(): print(f'{s:10s} {at / FPS:6.2f}–{(at + n) / FPS:6.2f}')
    print('total', duration())
