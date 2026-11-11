# «На якій я планеті?» (№2, Меркурій) — the voice laid out with room to breathe: each phrase cut from the recording (NOT sped up;
# a tempo below 1 slows it, pitch kept) and followed by its pause; the beats of the picture follow the phrases.
#   python3 scenes/puzzle_mercury/timeline.py [tempo]            -> writes scene.json (beats, narration, durations)
#   python3 scenes/puzzle_mercury/timeline.py preview <tempo> <out.mp4>   -> the voice alone, to listen to the pace
import json, os, subprocess, sys
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
V, FIX = 'voice_v2.mp3', 'voice_v2.mp3'
# 11.11 — the new format: harder clues, the answer at the end of the same video, no «tomorrow» (voice_v2.mp3, 1,84 кр.)
# (beat it starts, file, from, to, pause after)
PHRASES = [
    ('hook', V, 0.0, 2.34, 0.4),       # Вчорашня відповідь — Венера!
    ('q', V, 2.77, 5.17, 0.5),         # А тепер: на якій я планеті?
    ('c1', V, 5.65, 6.63, 0.3),        # Підказка перша:
    (None, V, 6.99, 11.02, 0.7),       #   від світанку до світанку тут минає два місцеві роки.
    ('c2', V, 11.65, 12.60, 0.3),      # Підказка друга:
    (None, V, 12.85, 15.97, 0.7),      #   рік тут коротший за три земні місяці.
    ('c3', V, 16.53, 17.45, 0.3),      # Підказка третя:
    (None, V, 17.73, 21.57, 0.7),      #   Сонце тут до трьох разів більше, ніж у вас на небі.
    ('o1', V, 22.30, 24.44, 0.4),      # Місяць, Марс чи Меркурій?
    ('write', V, 24.76, 26.61, 0.5),   # Пиши відповідь у коментарях!
]
COUNT = [(V, 27.15, 27.58), (V, 28.06, 28.60), (V, 29.12, 29.57)]   # Три. Два. Один.
CD = 1.1                                                            # s per number
ANS = (V, 30.03, 32.34)                                             # Правильна відповідь — Меркурій!


def layout(tempo=1.0):
    t, B, parts = 0.15, {'walk': 0.0, 'steps': 2}, []
    for beat, f, a, b, gap in PHRASES:
        if beat: B[beat] = round(t - (0.05 if beat != 'hook' else 0), 3)
        parts.append([a, b, round(t, 3), f]); t += (b - a) / tempo + gap
    B['opts'] = B['o1'] - 0.15
    B['o2'] = round(B['o1'] + 0.75, 3); B['o3'] = round(B['o1'] + 1.35, 3)   # the cards as the names are said
    B['n3'] = round(t, 3); B['n2'] = round(B['n3'] + CD, 3); B['n1'] = round(B['n3'] + 2 * CD, 3); B['cd'] = CD
    for k, (f, a, b) in enumerate(COUNT): parts.append([a, b, round(B['n3'] + CD * k + 0.05, 3), f])
    t = B['n3'] + 3 * CD + 0.05
    B['ans'] = round(t - 0.15, 3); parts.append([ANS[1], ANS[2], round(t, 3), ANS[0]]); t += ANS[2] - ANS[1]
    B['bye'] = round(t + 1.2, 3); B['sub'] = B['bye']
    B['end'] = round(B['bye'] + 2.8, 2)
    return B, parts


def preview(tempo, out):
    B, parts = layout(tempo)
    files = [V, FIX]; ins = sum((['-i', os.path.join(HERE, f)] for f in files), [])
    at = f',atempo={tempo}' if tempo != 1 else ''
    g = ''.join(f'[{files.index(f)}:a]atrim={a}:{b},asetpts=PTS-STARTPTS{at},afade=t=in:d=0.02,adelay={int(s * 1000)}:all=1[p{k}];' for k, (a, b, s, f) in enumerate(parts))
    g += ''.join(f'[p{k}]' for k in range(len(parts))) + f'amix=inputs={len(parts)}:normalize=0,apad,atrim=0:{B["end"]},loudnorm=I=-16[a]'
    subprocess.run([FF, '-y', '-loglevel', 'error', *ins, '-f', 'lavfi', '-i', 'color=c=0x1a1208:s=720x1280:r=30', '-filter_complex', g,
                    '-map', f'{len(files)}:v', '-map', '[a]', '-t', str(B['end']), '-c:v', 'libx264', '-tune', 'stillimage', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '160k', out], check=True)
    print(out, B['end'], 's')


if __name__ == '__main__':
    if sys.argv[1:2] == ['preview']: preview(float(sys.argv[2]), sys.argv[3]); sys.exit()
    tempo = float(sys.argv[1]) if sys.argv[1:] else 1.0
    B, parts = layout(tempo)
    p = os.path.join(HERE, 'scene.json'); sc = json.load(open(p))
    sc['beats'] = B
    sc['narration'] = {'file': V, 'level': 1.0, 'tempo': tempo, 'parts': parts}
    sc['out'] = {'answer': True, 'duration': B['end'], 'subscribe': B['sub']}
    sc['duration'] = B['end']
    json.dump(sc, open(p, 'w'), ensure_ascii=False, indent=1); print(json.dumps(B))
