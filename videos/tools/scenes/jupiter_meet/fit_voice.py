# Sets "Знайомся: Юпітер" to the author's voice: the fourteen phrases (seconds in voice.mp3, found from its pauses) are
# laid 0.45 s apart (2 s before the closing question), sped up by TEMPO, one phrase per shot; each shot is lengthened or
# shortened so the cut sits in the middle of the pause after its phrase (shots crossfade over timeline.XF frames).
# Writes the narration into scene.json and the shot lengths into shots.js (the "dur: …" of each shot).
#
#   python3 scenes/jupiter_meet/fit_voice.py
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from timeline import ORDER, FPS, XF

TEMPO, GAP, LAST_GAP, LEAD, TAIL = 1.07, 0.45, 2.0, 0.15, 4.4
PHRASES = [(0.00, 4.77), (4.98, 15.06), (15.42, 21.00), (21.24, 32.48), (32.74, 40.36), (40.66, 44.34), (44.61, 54.39),
           (54.58, 61.86), (62.10, 68.20), (68.49, 76.07), (76.30, 82.59), (82.98, 90.11), (90.45, 97.75), (98.00, 102.40)]


def plan():
    parts, at = [], LEAD
    for i, (a, b) in enumerate(PHRASES):
        if i: at += LAST_GAP if i == len(PHRASES) - 1 else GAP
        parts.append([a, b, round(at, 3)])
        at += (b - a) / TEMPO
    ends = [p[2] + (p[1] - p[0]) / TEMPO for p in parts]
    # cuts: the middle of each pause (the last one 0.8 s into the long pause, so the dawn sky stays a moment)
    cuts = [(ends[i] + parts[i + 1][2]) / 2 for i in range(len(parts) - 2)] + [ends[-2] + 0.8]
    total = ends[-1] + TAIL
    frames, prev = [], 0
    for i, c in enumerate(cuts + [total]):
        f = round(c * FPS)
        n = f - prev + (XF // 2 if i < len(cuts) else 0) + (XF // 2 if i else 0)
        frames.append(n); prev = f
    return parts, ends, frames, total


if __name__ == '__main__':
    parts, ends, frames, total = plan()
    sj = os.path.join(HERE, 'scene.json'); d = json.load(open(sj))
    d['narration'] = {'file': 'voice.mp3', 'level': 1.0, 'tempo': TEMPO, 'parts': parts}
    d['duration'] = round(total, 2)
    json.dump(d, open(sj, 'w'), ensure_ascii=False, indent=2); open(sj, 'a').write('\n')
    src = open(os.path.join(HERE, 'shots.js'), encoding='utf-8').read()
    for name, n in zip(ORDER, frames):
        src, k = re.subn(r'(^\s{4}' + name + r': \{ dur: )[\d.]+', lambda m: m.group(1) + f'{n / FPS:.3f}', src, flags=re.M)
        assert k == 1, name
    open(os.path.join(HERE, 'shots.js'), 'w', encoding='utf-8').write(src)
    for name, n, p, e in zip(ORDER, frames, parts, ends): print(f'{name:9s} {n / FPS:6.2f} s   phrase {p[2]:6.2f}–{e:6.2f}')
    print('total', round(total, 2))
