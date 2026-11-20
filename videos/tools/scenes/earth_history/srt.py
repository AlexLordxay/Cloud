# Ukrainian subtitles for YouTube: the narration's sentences at their places in the cut (timeline.json + timing.json) and
# the dinosaur film's phrases (chicxulub/assemble.py layout, as in assemble16.py) after the asteroid act's start.
# Long sentences are split into cues of at most two lines; stress marks are removed.
#   python3 srt.py   -> videos/earth_history.srt
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, os.path.join(HERE, '..', 'chicxulub'))
import assemble as A
MAXC = 84                                   # two lines of ~42 characters

def clean(s): return re.sub(r'\s+', ' ', s.replace('́', '')).strip()

def cues():
    T = json.load(open(os.path.join(HERE, 'timeline.json'))); M = json.load(open(os.path.join(HERE, 'timing.json')))
    out = []
    for a in T['acts']:
        for f, t0, t1, at in a.get('voice', []):
            for s in M[f]:
                if s['start'] >= t0 - 0.01 and s['end'] <= t1 + 0.01:
                    out.append((at + s['start'] - t0, at + s['end'] - t0, clean(s['text'])))
    ast = next(a for a in T['acts'] if a['id'] == 'asteroid')['start']
    A.PHRASES = A.PHRASES[:10]; _, placed = A._layout()
    paras = [clean(p) for p in open(os.path.join(HERE, '..', 'chicxulub', 'voice_text.txt')).read().split('\n') if p.strip()]
    paras[2] = paras[2].replace('удвадцятеро', 'у двадцять разів')      # phrase 3 was re-recorded so (fix3.mp3)
    for (f, a_, b_, at, *_), text in zip(placed, paras):
        out.append((ast + at, ast + at + (b_ - a_), text))
    return sorted(out)

def split(t0, t1, text):
    """cues of at most MAXC characters, cut at word boundaries near equal lengths, preferring a cut after a comma, a
    colon or a dash; a dash never starts a cue"""
    words = text.split(); parts = []
    while len(' '.join(words)) > MAXC:
        n = -(-len(' '.join(words)) // MAXC); goal = len(' '.join(words)) / n
        best = None
        for k in range(1, len(words)):
            if words[k] == '—': continue
            head = ' '.join(words[:k])
            if len(head) > MAXC: break
            cost = abs(len(head) - goal) - (14 if head[-1] in ',:;.!?—' else 0)
            if best is None or cost < best[0]: best = (cost, k)
        k = best[1]; parts.append(' '.join(words[:k])); words = words[k:]
    parts.append(' '.join(words))
    total = sum(len(p) for p in parts); res, t = [], t0
    for p in parts:
        d = (t1 - t0) * len(p) / total; res.append((t, t + d, p)); t += d
    return res

def two_lines(s):
    if len(s) <= 42: return s
    mid = len(s) // 2
    cut = min((i for i, c in enumerate(s) if c == ' ' and s[i + 1] != '—'), key=lambda i: abs(i - mid) - (6 if s[i - 1] in ',:;—' else 0))
    return s[:cut] + '\n' + s[cut + 1:]

def ts(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

if __name__ == '__main__':
    items = [c for t0, t1, x in cues() for c in split(t0, t1, x)]
    lines = []
    for k, (t0, t1, x) in enumerate(items, 1):
        nxt = items[k][0] if k < len(items) else t1 + 3
        end = min(max(t1 + 0.25, t0 + 1.2), nxt - 0.05)        # a short tail, at least 1.2 s on screen, never over the next
        lines += [str(k), f'{ts(t0)} --> {ts(end)}', two_lines(x), '']
    dst = os.path.abspath(os.path.join(TOOLS, '..', 'earth_history.srt'))
    open(dst, 'w').write('\n'.join(lines)); print(dst, len(items), 'cues')
