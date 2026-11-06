# «Знайомся: TRAPPIST-1e» — the timeline: the author's voice (voice3.mp3 = voice.mp3 92.4 s + phrases re-recorded for
# the stress, appended: «Найімові́рніше» at 97.6 s, «кам'яна́, і тепла́» at 102.6 s, the new hook «Її називають двійником
# Землі» at 107.4 s — voice4.mp3; NOT sped up) cut at its pauses into
# phrases (silencedetect -32 dB + syllable peaks), laid out with a few breaths where the picture changes, and the
# shots hung on the phrases.
#   python3 timeline.py   -> timeline.json (+ prints the shots)
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

# [from, to] in the recording, the text, an extra pause before it (s)
P = [
    (107.36, 109.54, 'Її називають двійником Землі.', 0.25),                          # re-recorded (voice4.mp3)
    (3.67, 5.73, 'І вона зовсім не схожа на Землю.', 0.0),
    (6.23, 6.87, 'Знайомся:', 0.5),
    (7.25, 8.57, 'Траппіст один е.', 0.0),
    (9.02, 11.13, 'Її попросили показати в коментарях.', None),     # dropped: the comment card says it (captions.py)
    (11.51, 13.99, 'Вона за сорок світлових років від нас.', 0.0),
    (14.37, 15.90, 'Розміром майже як Земля,', 0.0),
    (103.69, 106.57, 'і тепла́ отримує на третину менше, ніж ми.', 0.15),             # the re-recorded take without «кам'яна́» (it dragged)
    (20.38, 22.21, 'Але її зоря — не Сонце,', 0.34),                                  # keeps the later timing (the cut above)
    (22.53, 25.94, 'а тьмяний червоний карлик, ледь більший за Юпітер.', 0.0),
    (26.34, 30.04, 'Планета так близько до зорі, що рік тут триває шість днів.', 0.5),
    (30.55, 31.91, 'Тож якщо тобі тридцять —', 0.0),
    (32.22, 34.63, 'тут тобі було б майже тисяча вісімсот.', 0.0),
    (97.64, 101.79, 'Найімові́рніше, вона завжди повернута до зорі одним боком.', 0.5),  # re-recorded (voice2.mp3)
    (39.17, 40.33, 'Там вічний день:', 0.0),
    (40.84, 42.87, 'зоря нерухомо висить у небі.', 0.0),
    (43.35, 44.46, 'А з другого боку —', 0.0),
    (44.73, 45.63, 'вічна ніч.', 0.0),
    (46.05, 47.69, 'Поруч ще шість планет —', 0.5),
    (47.97, 50.89, 'і всі вони поміщаються всередині орбіти Меркурія.', 0.0),
    (51.39, 55.10, 'Тому сусідні планети на небі бувають завбільшки як наш Місяць —', 0.4),
    (55.39, 57.18, 'і помітно пропливають повз.', 0.0),
    (57.57, 58.84, 'Яка вона насправді,', 0.6),
    (59.15, 60.24, 'поки ніхто не знає.', 0.0),
    (60.72, 62.34, 'Якщо там є повітря й вода,', 0.0),
    (62.60, 64.70, 'вчені припускають планету-око:', 0.0),
    (65.09, 66.39, 'усе вкрите кригою,', 0.0),
    (66.60, 68.57, 'а під зорею — відкритий океан.', 0.0),
    (69.06, 71.75, 'І можливо, на його берегах є життя.', 0.4),
    (72.16, 75.64, 'Тільки рослини під такою зорею, ймовірно, були б не зелені,', 0.6),
    (75.87, 76.67, 'а майже чорні —', 0.0),
    (77.16, 79.28, 'щоб ловити якомога більше світла.', 0.0),
    (79.75, 81.53, 'Але поки це лише мрія.', 0.6),
    (81.97, 84.38, 'Відповідь шукає телескоп «Джеймс Вебб» —', 0.0),
    (84.76, 85.67, 'просто зараз.', 0.0),
    (86.01, 88.92, 'Надішли це тому, хто мріє про другу Землю.', 0.5),
    (89.37, 92.01, 'І напиши, яку планету показати наступною.', 0.0),
]
TAIL = 4.8

SHOTS = [('hook', 0), ('reveal', 1), ('star', 8), ('year', 10), ('lock', 13), ('system', 18), ('sky', 20),
         ('eye', 22), ('life', 28), ('dark', 29), ('dream', 32), ('final', 35)]


def build():
    out, t, prev = [], 0.0, 0.0
    for i, (a, b, txt, extra) in enumerate(P):
        if extra is None:                                                    # a phrase left out (kept for the numbering)
            out.append(dict(i=i, src=[a, b], t0=round(t, 3), t1=round(t, 3), text=txt, skip=True)); continue
        gap = (a - prev if 0 <= a - prev < 1.5 else 0.45) if i else 0.0     # re-recorded phrases sit at the end of the file
        t += gap + extra
        out.append(dict(i=i, src=[a, b], t0=round(t, 3), t1=round(t + b - a, 3), text=txt))
        t += b - a; prev = b
    dur = round(t + TAIL, 2)
    shots = []
    for k, (nm, pi) in enumerate(SHOTS):
        t0 = 0.0 if k == 0 else out[pi]['t0'] - 0.35
        shots.append(dict(name=nm, t0=round(t0, 3)))
    for k, s in enumerate(shots):
        s['t1'] = shots[k + 1]['t0'] if k + 1 < len(shots) else dur
    tl = dict(dur=dur, phrases=out, shots=shots)
    json.dump(tl, open(os.path.join(HERE, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    # scene.json: the narration parts on this timeline
    sc = json.load(open(os.path.join(HERE, 'scene.json'))) if os.path.exists(os.path.join(HERE, 'scene.json')) else {}
    sc.update({'title': 'Знайомся: TRAPPIST-1e', 'duration': dur, 'fps': 30, 'width': 720, 'height': 1280,
               'audio': {'music': 'scene', 'fadeIn': 0.2, 'fadeOut': 2.5},
               'narration': {'file': 'voice4.mp3', 'level': 1.0,
                             'parts': [[max(0.0, p['src'][0] - 0.05), p['src'][1] + 0.08, round(max(0.0, p['t0'] - 0.05), 3)] for p in out if not p.get('skip')]}})
    json.dump(sc, open(os.path.join(HERE, 'scene.json'), 'w'), ensure_ascii=False, indent=1)
    for s in shots:
        print(f"{s['name']:8s} {s['t0']:6.2f} – {s['t1']:6.2f}  ({s['t1'] - s['t0']:.1f} s)")
    for p in out: print(f"  {p['t0']:6.2f} {p['t1']:6.2f}  {p['text']}")
    print('dur', dur)


if __name__ == '__main__':
    build()
