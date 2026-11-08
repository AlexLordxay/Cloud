# «Знайомся: Уран» — the timeline: the author's voice (voice.mp3, 90.1 s, Eleven v4, NOT sped up) cut at its pauses
# (silencedetect -38/-34 dB) into phrases, laid out with breaths where the picture changes: the hook's swing, the
# flight under the ring (a pause for the "wow"), 2 s before the last question; the shots hang on the phrases.
#   python3 timeline.py   -> timeline.json, scene.json (+ prints the shots)
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

# [from, to] in the recording, the text, an extra pause before it (s)
P = [
    (0.00, 2.11, 'Ця планета лежить на боці.', 0.25),                       # 0
    (2.54, 3.99, 'Знайомся: Уран.', 1.6),                                    # 1
    (4.28, 6.80, 'Він учетверо ширший за Землю.', 0.0),                     # 2
    (7.17, 10.13, 'І це перша планета, яку знайшли в телескоп.', 0.0),      # 3
    (10.68, 13.43, 'Вільям Гершель спершу подумав, що це комета.', 0.0),    # 4
    (13.78, 16.93, 'А планету мало не назвали «Зорею Георга» —', 0.0),       # 5
    (17.31, 18.80, 'на честь англійського короля.', 0.0),                   # 6
    (19.28, 22.94, 'Через цей нахил на полюсах сорок два роки триває день —', 0.4),   # 7
    (23.29, 25.46, 'а потім сорок два роки ніч.', 0.0),                     # 8
    (25.89, 28.38, 'Його кільця зовсім не як у Сатурна:', 0.4),             # 9
    (28.83, 30.80, 'темні, як вугілля, і вузькі.', 0.0),                    # 10
    (31.12, 34.16, 'А між ними — сотні кілометрів порожнечі.', 0.0),        # 11
    (34.67, 37.05, 'Поверхні тут немає — лише хмари.', 3.0),                # 12 (after the flight under the ring)
    (37.34, 40.62, 'А світло Сонця летить сюди майже три години.', 0.0),    # 13
    (41.16, 44.05, 'Тут найхолодніше повітря Сонячної системи —', 0.0),     # 14
    (44.52, 46.47, 'мінус двісті двадцять чотири.', 0.0),                   # 15
    (46.78, 49.10, 'Холодніше, ніж на далекому Нептуні.', 0.0),             # 16
    (49.62, 50.53, 'І це загадка:', 0.3),                                   # 17
    (50.95, 53.51, 'Уран майже не віддає власного тепла.', 0.0),            # 18
    (53.99, 56.28, 'Чому — учені досі не знають.', 0.0),                    # 19
    (56.66, 59.93, 'Супутники Урана названо на честь героїв Шекспіра.', 0.0),          # 20
    (60.42, 66.03, 'На Міранді є урвище двадцять кілометрів заввишки — удвічі вище за Еверест.', 0.0),  # 21
    (66.29, 68.98, 'Камінь падав би з нього хвилин дванадцять.', 0.0),      # 22
    (69.40, 74.47, 'Зблизька Уран бачив лише один апарат — «Вояджер-два», сорок років тому.', 0.5),   # 23
    (74.91, 78.26, 'Двадцять п\'ятого листопада Уран найближче до нас.', 0.0),          # 24
    (78.58, 81.22, 'Візьми бінокль і шукай біля Волосожара.', 0.0),         # 25
    (81.70, 84.16, 'Надішли тому, з ким підеш шукати Уран.', 0.0),          # 26
    (84.66, 87.41, 'Сусід Урана, Нептун, уже на каналі.', 2.0),             # 27
    (87.74, 90.12, 'А яку планету показати наступною?', 0.0),               # 28
]
TAIL = 4.6

# shot, the phrase it starts with (its start minus LEAD), or an absolute offset from a phrase
SHOTS = [('hook', None), ('scale', 1), ('herschel', 4), ('orbit', 7), ('ringdive', 9), ('under', 'u'), ('clouds', 12),
         ('mystery', 17), ('moons', 20), ('mirphoto', 21), ('rockfall', 22), ('voyager', 23), ('skynow', 24),
         ('final', 27)]
LEAD = 0.3


def build():
    out, t, prev = [], 0.0, 0.0
    for i, (a, b, txt, extra) in enumerate(P):
        gap = (a - prev if 0 <= a - prev < 1.5 else 0.45) if i else 0.0
        t += gap + extra
        out.append(dict(i=i, src=[a, b], t0=round(t, 3), t1=round(t + b - a, 3), text=txt))
        t += b - a; prev = b
    dur = round(t + TAIL, 2)
    shots = []
    for k, (nm, pi) in enumerate(SHOTS):
        if pi is None: t0 = 0.0
        elif pi == 'u': t0 = out[11]['t1'] + 0.35          # under the ring: right after «порожнечі»
        else: t0 = out[pi]['t0'] - LEAD
        shots.append(dict(name=nm, t0=round(t0, 3)))
    for k, s in enumerate(shots):
        s['t1'] = shots[k + 1]['t0'] if k + 1 < len(shots) else dur
    tl = dict(dur=dur, phrases=out, shots={s['name']: round(s['t1'] - s['t0'], 3) for s in shots}, order=shots)
    json.dump(tl, open(os.path.join(HERE, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    sc = json.load(open(os.path.join(HERE, 'scene.json'))) if os.path.exists(os.path.join(HERE, 'scene.json')) else {}
    sc.update({'title': 'Знайомся: Уран', 'duration': dur, 'fps': 30, 'width': 720, 'height': 1280,
               'audio': {'music': 'scene', 'fadeIn': 0.2, 'fadeOut': 2.5},
               'narration': {'file': 'voice.mp3', 'level': 1.0,
                             'parts': [[max(0.0, p['src'][0] - 0.05), p['src'][1] + 0.08, round(max(0.0, p['t0'] - 0.05), 3)] for p in out]}})
    json.dump(sc, open(os.path.join(HERE, 'scene.json'), 'w'), ensure_ascii=False, indent=1)
    for s in shots:
        print(f"{s['name']:9s} {s['t0']:6.2f} – {s['t1']:6.2f}  ({s['t1'] - s['t0']:.1f} s)")
    for p in out: print(f"  {p['t0']:6.2f} {p['t1']:6.2f}  {p['text']}")
    print('dur', dur)


if __name__ == '__main__':
    build()
