# Subtitles for YouTube (big_bang.srt) from the voice's timeline: one cue per sentence (the phrases joined until a
# full stop / question mark), the text as spoken (without stress marks).
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx

def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

cues, cur = [], None
for p in fx.TL['phrases']:
    if cur is None: cur = [p['t0'], p['t1'], p['text']]
    else: cur[1] = p['t1']; cur[2] += ' ' + p['text']
    if cur[2].rstrip().endswith(('.', '?', '!', ':')) or len(cur[2]) > 80:
        cues.append(cur); cur = None
if cur: cues.append(cur)
out = os.path.join(fx.BB, '..', '..', '..', 'big_bang.srt')
with open(out, 'w', encoding='utf-8') as f:
    for i, (a, b, t) in enumerate(cues, 1):
        f.write(f'{i}\n{ts(a)} --> {ts(b + 0.2)}\n{t}\n\n')
print(os.path.abspath(out), len(cues))
