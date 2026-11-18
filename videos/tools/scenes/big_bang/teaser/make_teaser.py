"""Шортс-тизер 9:16 з довгого «Великого вибуху»: python3 make_teaser.py -> videos/big_bang_teaser.mp4"""
import os, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.normpath(os.path.join(HERE, '../../../..'))
SRC = os.path.join(V, 'big_bang.mp4'); SRT = os.path.join(V, 'big_bang.srt'); OUT = os.path.join(V, 'big_bang_teaser.mp4')
# (аудіо від, до) ; відео — те саме, крім останнього шматка, де картинка йде з «туману» 23,5 с
A = [(0.00, 23.40), (43.55, 58.30), (60.35, 79.05), (27.25, 32.00)]
VID = [(0.00, 23.40), (43.55, 58.30), (60.35, 75.80), (23.50, 31.50 + 2.6)]   # останній: заповнення + кінцева картка 2,6 с
TAIL = 2.6
# --- субтитри (ASS) за новою шкалою часу
def ts(s):
    h, m, r = s.split(':'); sec, ms = r.split(','); return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
subs = []
for b in open(SRT, encoding='utf-8').read().strip().split('\n\n'):
    L = b.split('\n'); t0, t1 = [ts(x.strip()) for x in L[1].split('-->')]; subs.append((t0, t1, ' '.join(L[2:])))
def chunks(text, t0, t1, maxc=24):
    words, out, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > maxc and cur: out.append(cur); cur = w
        else: cur = (cur + ' ' + w).strip()
    out.append(cur); tot = sum(len(c) for c in out); res, t = [], t0
    for c in out:
        d = (t1 - t0) * len(c) / tot; res.append((t, t + d, c)); t += d
    return res
events, off = [], 0.0
for (a0, a1) in A:
    for (t0, t1, tx) in subs:
        if t0 >= a0 - 0.05 and t1 <= a1 + 0.1:
            for (c0, c1, c) in chunks(tx, t0, t1): events.append((off + c0 - a0, off + c1 - a0, c))
    off += a1 - a0
total = off + TAIL
def at(t): h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60; return f'{h}:{m:02d}:{s:05.2f}'
ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1080', 'PlayResY: 1920', '', '[V4+ Styles]',
       'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
       'Style: Sub,Inter Display Bold,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,4,3,2,90,90,560,1',
       'Style: Logo,Inter Display SemiBold,40,&H008CD6FF,&H008CD6FF,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,2,2,8,40,40,150,1',
       'Style: End1,Inter Display Black,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,5,3,5,60,60,0,1',
       'Style: End2,Inter Display SemiBold,54,&H0028CDFF,&H0028CDFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,4,3,5,60,60,0,1',
       '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
ass.append(f'Dialogue: 0,{at(0)},{at(total)},Logo,,0,0,0,,НЕБОЗВІД')
for (t0, t1, c) in events: ass.append(f'Dialogue: 0,{at(t0)},{at(t1)},Sub,,0,0,0,,{c}')
e0 = total - TAIL
ass.append(f'Dialogue: 0,{at(e0)},{at(total)},End1,,0,0,0,,{{\\fad(300,0)\\pos(540,880)}}Повна версія — 6 хв')
ass.append(f'Dialogue: 0,{at(e0)},{at(total)},End2,,0,0,0,,{{\\fad(300,0)\\pos(540,1000)}}на YouTube · @nebozvid')
ap = os.path.join(HERE, 'teaser.ass'); open(ap, 'w', encoding='utf-8').write('\n'.join(ass) + '\n')
# --- маска країв (ховає обрізані підписи горизонтального кадру)
from PIL import Image
import numpy as np
x = np.arange(1080); a = (1 - np.clip(np.minimum(x, 1079 - x) / 80, 0, 1)) * 255
mk = np.zeros((1920, 1080, 4), np.uint8); mk[..., 3] = a[None, :].astype(np.uint8)
mp = os.path.join(HERE, 'edge_mask.png'); Image.fromarray(mk, 'RGBA').save(mp)
# --- відео й звук
fc, inputs = [], []
for i, (v0, v1) in enumerate(VID):
    fc.append(f'[0:v]trim={v0}:{v1},setpts=PTS-STARTPTS,crop=608:1080:656:0,scale=1080:1920:flags=lanczos,setsar=1,fps=30[v{i}]')
for i, (a0, a1) in enumerate(A):
    fc.append(f'[0:a]atrim={a0}:{a1},asetpts=PTS-STARTPTS[a{i}]')
# точний стик без зсуву: concat; м'якість — короткі fade на межах
dur = [v1 - v0 for v0, v1 in VID]
for i in range(len(VID)):
    d = dur[i]; fc.append(f'[v{i}]fade=t=in:st=0:d=0.25,fade=t=out:st={d-0.25:.3f}:d=0.25[w{i}]')
for i in range(len(A)):
    d = A[i][1] - A[i][0]; fc.append(f'[a{i}]afade=t=in:st=0:d=0.08,afade=t=out:st={d-0.12:.3f}:d=0.12[b{i}]')
fc.append(''.join(f'[w{i}]' for i in range(len(VID))) + f'concat=n={len(VID)}:v=1:a=0[vc]')
fc.append(''.join(f'[b{i}]' for i in range(len(A))) + f'concat=n={len(A)}:v=0:a=1,apad=pad_dur={TAIL},afade=t=out:st={total-1.2:.3f}:d=1.2[ac]')
fc.append(f"[vc][1:v]overlay=0:0:enable='lt(t,20.8)+between(t,23.4,38.2)',ass={ap}[vs]")
cmd = ['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-loop', '1', '-i', mp, '-filter_complex', ';'.join(fc), '-map', '[vs]', '-map', '[ac]', '-t', f'{total:.3f}',
       '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT]
subprocess.run(cmd, check=True); print(OUT, round(total, 2), 's')
