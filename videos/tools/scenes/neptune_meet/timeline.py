# «Знайомся: Нептун» — the timeline: the author's voice (voice.mp3, 93.2 s, NOT sped up) cut at its pauses into phrases,
# laid out with a few longer breaths where the picture needs them (the jump, the hush before the diamonds), and the
# shots hung on the phrases.
#   python3 scenes/neptune_meet/timeline.py   -> timeline.json + work/neptune_meet/voice.wav
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, '..', '..', 'work', 'neptune_meet')
FF = __import__('imageio_ffmpeg').get_ffmpeg_exe()

# the phrases in the recording (silencedetect -35 dB, 0.3 s): [from, to, text, extra pause before it (s)]
P = [
    (0.00, 2.74, 'На Нептуні йдуть дощі з діамантів.', 0.25),
    (3.05, 4.57, 'Стрибнемо — подивимось?', 0.0),
    (5.20, 6.23, 'Це Нептун —', 0.75),
    (6.61, 11.34, 'найдальша планета від Сонця. Він майже вчетверо ширший за Землю,', 0.0),
    (11.79, 14.78, 'а світло Сонця летить сюди чотири години.', 0.0),
    (15.30, 17.58, 'І він не синій, як на старих фото,', 0.3),
    (17.90, 19.20, 'а блідо-блакитний.', 0.0),
    (19.66, 22.23, 'Синім його колись зробили для контрасту.', 0.0),
    (22.91, 25.04, 'Нептун спершу знайшли на папері:', 0.3),
    (25.58, 29.91, 'тисяча вісімсот сорок шостого року вчений вирахував, де він має бути,', 0.0),
    (30.38, 32.07, '— і його побачили саме там.', 0.0),
    (32.53, 35.42, 'Відтоді він облетів Сонце лише раз:', 0.3),
    (35.80, 38.48, 'рік тут — сто шістдесят п\'ять наших.', 0.0),
    (39.07, 41.38, 'Поверхні тут немає — лише хмари.', 0.6),
    (41.77, 43.89, 'І падаєш ти майже як на Землі:', 0.0),
    (44.32, 45.93, 'тяжіння тут трохи більше.', 0.0),
    (46.58, 49.17, 'Сонце звідси — просто яскрава зірка.', 0.3),
    (49.52, 52.67, 'Але світить, як чотириста повних Місяців.', 0.0),
    (53.31, 55.86, 'Тут найшвидший вітер у Сонячній системі —', 0.3),
    (56.21, 58.31, 'дві тисячі кілометрів на годину.', 0.0),
    (58.65, 62.03, 'Він доніс би тебе з Києва до Львова за чверть години.', 0.0),
    (62.63, 64.44, 'За бортом мінус двісті.', 0.3),
    (64.88, 68.21, 'А нижчі хмари, ймовірно, пахнуть тухлими яйцями —', 0.0),
    (68.73, 69.80, 'це сірководень.', 0.0),
    (70.30, 74.28, 'Що глибше — то темніше, гарячіше й тісніше.', 0.3),
    (74.70, 76.80, 'Можливо, тут б\'ють блискавки.', 0.0),
    (77.29, 81.93, 'А на глибині тисяч кілометрів тиск стискає вуглець у кристали —', 1.2),
    (82.30, 83.83, 'і вони падають дощем.', 0.0),
    (84.42, 85.52, 'Так вважають учені.', 0.0),
    (85.95, 87.72, 'Дна ти не побачиш —', 0.5),
    (88.07, 89.06, 'його немає.', 0.0),
    (89.73, 91.58, 'Яку планету показати наступною?', 0.4),
    (92.05, 93.23, 'Пиши в коментарях.', 0.0),
]
TAIL = 3.4

# the shots: name, first phrase (index into P); a shot runs until the next one starts
SHOTS = [('hook', 0), ('globe', 2), ('color', 5), ('paper', 8), ('orbit', 11), ('jump', 13), ('sun', 16),
         ('wind', 18), ('cold', 21), ('deep', 24), ('diamonds', 26), ('final', 29)]


def build():
    out, t, prev = [], 0.0, 0.0
    for i, (a, b, txt, extra) in enumerate(P):
        gap = a - prev if i else 0.0
        t += gap + extra
        out.append(dict(i=i, src=[a, b], t0=round(t, 3), t1=round(t + b - a, 3), text=txt))
        t += b - a; prev = b
    dur = round(t + TAIL, 2)
    shots = []
    for k, (nm, pi) in enumerate(SHOTS):
        t0 = 0.0 if k == 0 else out[pi]['t0'] - (0.35 if nm != 'diamonds' else 1.0)
        shots.append(dict(name=nm, t0=round(t0, 3)))
    for k, s in enumerate(shots):
        s['t1'] = shots[k + 1]['t0'] if k + 1 < len(shots) else dur
    tl = dict(dur=dur, phrases=out, shots=shots)
    json.dump(tl, open(os.path.join(HERE, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    # the voice laid out on the timeline (each phrase cut with 20 ms fades)
    os.makedirs(WORK, exist_ok=True)
    parts, fl = [], []
    for k, p in enumerate(out):
        a, b = p['src']
        a0, b0 = max(0.0, a - 0.06), b + 0.08
        d = int(round((p['t0'] - (a - a0)) * 1000))
        fl.append(f"[0:a]atrim={a0:.3f}:{b0:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={b0 - a0 - 0.03:.3f}:d=0.03,adelay={d}|{d}[p{k}]")
        parts.append(f'[p{k}]')
    fl.append(''.join(parts) + f'amix=inputs={len(parts)}:normalize=0,apad=whole_dur={dur}[v]')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', os.path.join(HERE, 'voice.mp3'), '-filter_complex', ';'.join(fl),
                    '-map', '[v]', '-ar', '44100', '-ac', '2', '-t', f'{dur:.2f}', os.path.join(WORK, 'voice.wav')], check=True)
    for s in shots:
        print(f"{s['name']:9s} {s['t0']:6.2f} – {s['t1']:6.2f}  ({s['t1'] - s['t0']:.1f} s)")
    print('dur', dur)


if __name__ == '__main__':
    build()
