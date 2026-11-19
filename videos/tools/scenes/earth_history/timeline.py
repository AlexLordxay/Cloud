# Master timeline of «Історія Землі»: acts, where each voice paragraph sits on the cut, the dinosaur insert.
#   python3 timeline.py  -> timeline.json  {acts: [{id, title, start, end, voice: [(file, from, to, at)], clock: [h0, h1]}], duration}
import json
T = json.load(open('timing.json'))
def para(f, i):
    s = [x for x in T[f] if x['para'] == i]; return s[0]['start'], s[-1]['end']
# fix the tail of p3 (the splice): «А якщо хочеш…» ends at 132.35, «І підписуйся…» 132.45–134.57
ACTS = [  # id, title, voice (file, paragraph) or 'dino', pause before (s), clock hours at start/end
    ('hook', 'Гачок', [('voice_p1.mp3', 0)], 0.6, (23.9983, 23.9983)),
    ('birth', 'Народження', [('voice_p1.mp3', 1)], 1.4, (0.0, 0.10)),
    ('theia', 'Тейя і Місяць', [('voice_p1.mp3', 2)], 1.0, (0.10, 0.70)),
    ('oceans', 'Перші океани', [('voice_p1.mp3', 3)], 1.2, (0.70, 3.0)),
    ('life', 'Життя', [('voice_p1.mp3', 4)], 1.2, (5.2, 8.0)),
    ('oxygen', 'Кисень', [('voice_p2.mp3', 0)], 1.2, (8.0, 11.6)),
    ('boring', 'Нудний мільярд', [('voice_p2.mp3', 1)], 1.2, (12.0, 19.5)),
    ('snowball', 'Земля-сніжка', [('voice_p2.mp3', 2)], 1.2, (20.0, 20.6)),
    ('ediacara', 'Перші великі істоти', [('voice_p2.mp3', 3)], 1.0, (20.8, 21.05)),
    ('cambrian', 'Кембрійський вибух', [('voice_p2.mp3', 4)], 1.0, (21.1, 21.45)),
    ('land', 'Вихід на суходіл', [('voice_p2.mp3', 5)], 1.0, (21.45, 22.1)),
    ('coal', 'Вугільні ліси', [('voice_p2.mp3', 6)], 1.0, (22.3, 22.6)),
    ('permian', 'Пангея і вимирання', [('voice_p3.mp3', 0)], 1.0, (22.6, 22.7)),
    ('dinos', 'Динозаври', [('voice_p3.mp3', 1)], 1.2, (22.75, 23.64)),
    ('asteroid', 'Астероїд', 'dino', 0.6, (23.65, 23.66)),
    ('mammals', 'Ссавці і люди', [('voice_p3.mp3', 2)], 0.8, (23.66, 23.9999)),
    ('future', 'Майбутнє', [('voice_p3.mp3', 3)], 1.4, (24.0, 24.0)),
]
DINO_LEN, END_CARD = 116.0, 7.0
t, acts = 0.0, []
for aid, title, v, pause, clk in ACTS:
    t += pause; start = t; vs = []
    if v == 'dino':
        t += DINO_LEN
    else:
        for f, p in v:
            a, b = para(f, p)
            if f == 'voice_p3.mp3' and p == 3: b = 134.57
            vs.append((f, a, b, round(t, 3))); t += b - a
    acts.append({'id': aid, 'title': title, 'start': round(start - pause * 0.5, 3), 'voice': vs, 'clock': clk})
for i, a in enumerate(acts):
    a['end'] = acts[i + 1]['start'] if i + 1 < len(acts) else round(t + 1.0, 3)
acts[0]['start'] = 0.0
dur = round(t + 1.0 + END_CARD, 2)
json.dump({'acts': acts, 'duration': dur, 'end_card': [round(t + 1.0, 2), dur]}, open('timeline.json', 'w'), ensure_ascii=False, indent=1)
for a in acts: print(f"{a['id']:10s} {a['start']:7.2f} – {a['end']:7.2f}  ({a['end'] - a['start']:5.1f} с)")
print('duration', dur, 's =', int(dur // 60), 'хв', round(dur % 60), 'с')
