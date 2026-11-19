#!/usr/bin/env python3
# prints short-term loudness (3 s window, every 10 s) and the largest 1-s step changes of a wav, plus peak
import sys, re, subprocess, numpy as np
p = sys.argv[1]
r = subprocess.run(['ffmpeg', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
rows = [(float(m.group(1)), float(m.group(2)), float(m.group(3))) for m in re.finditer(r't:\s+([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.inf]+)\s+S:\s*(-?[\d.inf]+)', r)]
t = np.array([x[0] for x in rows]); S = np.array([x[2] for x in rows]); M = np.array([x[1] for x in rows])
S = np.where(S < -70, -70, S)
print(' '.join(f'{int(a)}:{S[np.argmin(abs(t-a))]:.0f}' for a in range(5, int(t[-1]), 10)))
S[:40] = S[40]
d = S[10:] - S[:-10]   # change over 1 s (ebur128 prints every 0.1 s)
idx = np.argsort(-abs(d))[:6]
print('largest 1 s short-term changes:', [(round(t[i + 10], 1), round(d[i], 1)) for i in sorted(idx)])
print(r[r.rfind('Summary'):].replace('\n', ' ')[:400])
