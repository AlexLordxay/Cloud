# Align the voice text to the recordings: sentence boundaries -> pauses (DP over the detected gaps, by character share).
# -> timing.json: per part, per paragraph, per sentence: (start, end) in seconds within voice_pN.mp3
import json, re, numpy as np
G = json.load(open('gaps.json'))
DUR = {'voice_p1.mp3': 160.69, 'voice_p2.mp3': 171.04, 'voice_p3.mp3': 134.57}
res = {}
for i in (1, 2, 3):
    f = f'voice_p{i}.mp3'; paras = [p.strip() for p in open(f'voice_part{i}.txt').read().split('\n\n') if p.strip()]
    sents = []
    for pi, p in enumerate(paras):
        for s in re.split(r'(?<=[.?!])\s+', p):
            if s: sents.append((pi, s))
    L = np.array([len(s) + 6 for _, s in sents], float); cum = np.cumsum(L) / L.sum()
    gaps = G[f]; first_on = 0.05; T = DUR[f] - 0.2
    # expected boundary times (after sentence k)
    exp = first_on + cum[:-1] * (T - first_on)
    n, m = len(exp), len(gaps)
    INF = 1e9; D = np.full((n + 1, m + 1), INF); D[0, :] = 0; B = np.zeros((n + 1, m + 1), int)
    mid = [(a + a + d) / 2 if False else a + 0.0 for a, d in [(g[0], g[1] - g[0]) for g in gaps]]
    for k in range(1, n + 1):
        best, bj = INF, -1
        for j in range(1, m + 1):
            if D[k - 1, j - 1] < best: best, bj = D[k - 1, j - 1], j - 1
            g0, g1 = gaps[j - 1]
            cost = (g0 - exp[k - 1]) ** 2 - 0.6 * (g1 - g0)          # prefer long pauses near the expected place
            D[k, j] = best + cost; B[k, j] = bj
    j = int(np.argmin(D[n, 1:])) + 1; picks = []
    for k in range(n, 0, -1):
        picks.append(j - 1); j = B[k, j]
    picks = picks[::-1]
    bounds = [0.0] + [gaps[p][0] for p in picks] + [DUR[f]]
    starts = [0.0] + [gaps[p][1] for p in picks]
    out = []
    for k, (pi, s) in enumerate(sents):
        out.append({'para': pi, 'text': s, 'start': round(starts[k], 2), 'end': round(bounds[k + 1], 2)})
    res[f] = out
    for o in out: print(i, o['para'], o['start'], o['end'], o['text'][:60])
json.dump(res, open('timing.json', 'w'), ensure_ascii=False, indent=1)
