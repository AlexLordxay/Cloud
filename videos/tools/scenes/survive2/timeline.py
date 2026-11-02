# «Скільки ти протримаєшся на кожній планеті?» v2 — the timeline, from the author's voice (voice.mp3, 61.4 s, NOT sped up).
# The sentences are cut at the pauses (silencedetect, -38 dB) and laid back with extra silence after some of them, where
# a death needs time to play out (the voice keeps its own pace; only the gaps between sentences grow).
#   python3 scenes/survive2/timeline.py   -> work/survive2/voice.wav (placed), scenes/survive2/timeline.json
# timeline.json: the sentences at their new times, and the shots (render.js reads them, post.py titles them).
import json, os, subprocess
import numpy as np
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '..', '..', 'work', 'survive2')
FF = __import__('imageio_ffmpeg').get_ffmpeg_exe()
SR = 48000

# (start, end) in voice.mp3, the text
SENT = [
    (0.00, 0.95, 'Три секунди.'),
    (1.27, 3.56, 'Саме стільки ти протримаєшся на Венері.'),
    (3.94, 5.25, 'А на інших планетах?'),
    (5.62, 9.33, 'На Місяці спокійно: скафандр тримає, доки є кисень.'),
    (9.81, 11.20, 'Години вісім.'),
    (11.61, 15.30, 'На Меркурії ґрунт розжарений до чотирьохсот тридцяти градусів.'),
    (15.70, 18.65, 'Хвилин десять — і скафандр не впорається з жаром.'),
    (19.09, 22.06, 'На Венері тиск — як майже кілометр під водою.'),
    (22.42, 24.22, 'Скафандр сплющить за мить.'),
    (24.57, 28.63, 'На Марсі холодно й повітря майже немає, але скафандр тримає.'),
    (28.98, 29.91, 'Тут можна жити.'),
    (30.34, 33.86, 'На Юпітері стати ні на що — ти падаєш крізь хмари.'),
    (34.10, 37.65, 'Зонд «Галілео» протримався тут п\'ятдесят вісім хвилин.'),
    (38.05, 40.29, 'А на Титані тиск майже як на Землі.'),
    (40.56, 42.63, 'Не вистачає лише тепла й кисню.'),
    (42.96, 45.26, 'А ще тут можна літати, як птах.'),
    (45.62, 49.78, 'На Нептуні мінус двісті й найшвидший вітер у Сонячній системі.'),
    (50.18, 51.01, 'Хвилин п\'ять.'),
    (51.44, 53.25, 'А на Сонці — ні секунди.'),
    (53.62, 57.62, 'І лише на одній планеті можна жити без скафандра — на нашій.'),
    (58.01, 59.79, 'На якій планеті протримався б ти?'),
    (60.26, 61.39, 'Пиши в коментарях.'),
]
# extra silence (s) after sentence i
GAP = {2: 0.3, 6: 1.2, 8: 1.0, 12: 1.0, 15: 0.6, 17: 1.3, 18: 2.4, 19: 0.4}
TAIL = 1.4


def place():
    raw = os.path.join(WORK, 'voice_raw.wav')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', os.path.join(HERE, 'voice.mp3'), '-ar', str(SR), '-ac', '1', raw], check=True)
    sr, x = wavfile.read(raw); x = x.astype(np.float32) / 32768
    cuts = [0.0] + [(SENT[i][1] + SENT[i + 1][0]) / 2 for i in range(len(SENT) - 1)] + [len(x) / SR]
    out, sents, shift = [], [], 0.0
    for i, (a, b, text) in enumerate(SENT):
        seg = x[int(cuts[i] * SR):int(cuts[i + 1] * SR)]
        out.append(seg)
        sents.append({'i': i, 't0': round(a + shift, 3), 't1': round(b + shift, 3), 'text': text})
        g = GAP.get(i, 0.0)
        if g: out.append(np.zeros(int(g * SR), np.float32)); shift += g
    y = np.concatenate(out + [np.zeros(int(TAIL * SR), np.float32)])
    wavfile.write(os.path.join(WORK, 'voice.wav'), SR, (np.stack([y, y], 1) * 32767).astype(np.int16))
    return sents, len(y) / SR


def shots(S, dur):
    st = lambda i: S[i]['t0']
    cut = lambda i: round(st(i) - 0.18, 2)          # a cut lands just before the sentence that names the next world
    B = [0, cut(3), cut(5), cut(7), cut(9), cut(11), cut(13), cut(16), cut(18), cut(19), round(dur, 2)]
    W = ['venus_hook', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'titan', 'neptune', 'sun', 'earth']
    return [{'t0': B[k], 't1': B[k + 1], 'world': W[k]} for k in range(len(W))]


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    S, dur = place()
    sh = shots(S, dur)
    json.dump({'dur': round(dur, 2), 'sentences': S, 'shots': sh}, open(os.path.join(HERE, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    for s in sh: print(f"{s['world']:11s} {s['t0']:6.2f} – {s['t1']:6.2f}  ({s['t1'] - s['t0']:.2f} s)")
    print('dur', round(dur, 2))
