# «На якій я планеті?» (№2, Меркурій) — the voice laid out with room to breathe: each phrase cut from the recording (NOT sped up;
# a tempo below 1 slows it, pitch kept) and followed by its pause; the beats of the picture follow the phrases.
#   python3 scenes/puzzle_mercury/timeline.py [tempo]            -> writes scene.json (beats, narration, durations)
#   python3 scenes/puzzle_mercury/timeline.py preview <tempo> <out.mp4>   -> the voice alone, to listen to the pace
import json, os, subprocess, sys
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FF = imageio_ffmpeg.get_ffmpeg_exe()
V, FIX = 'voice.mp3', 'voice.mp3'
# (beat it starts, file, from, to, pause after)
PHRASES = [
    ('hook', V, 0.0, 2.36, 0.55),      # Вчорашня відповідь — Венера!
    ('q', V, 2.72, 3.75, 0.9),         # А де я тепер?
    ('c1', V, 4.08, 5.18, 0.5),        # Підказка перша:
    (None, V, 5.5, 8.8, 1.1),          #   Сонце тут майже втричі більше, ніж у вас на небі.
    ('c2', V, 9.18, 10.18, 0.5),       # Підказка друга:
    (None, V, 10.48, 12.5, 1.1),       #   небо чорне навіть удень.
    ('c3', V, 12.86, 13.88, 0.5),      # Підказка третя:
    (None, V, 14.2, 17.45, 0.35),      #   удень тут плюс чотириста тридцять,
    (None, V, 17.55, 19.63, 1.0),      #   а вночі — мінус сто вісімдесят градусів.
    ('o1', V, 19.97, 20.73, 0.6),      # Місяць,
    ('o2', V, 20.74, 21.42, 0.6),      # Марс
    ('o3', V, 21.43, 22.22, 0.8),      # чи Меркурій?
    ('write', V, 22.48, 24.21, 0.6),   # Пиши відповідь у коментарях!
]
COUNT = [(V, 24.55, 25.0), (V, 25.36, 25.96), (V, 26.28, 26.8)]   # Три. Два. Один. — 2 s each
TAIL = [('cut', V, 27.1, 30.16, 0.55),  # Правильну відповідь скажу завтра, у новій загадці.
        ('sub', V, 30.45, 32.24, 1.3)]  # Підпишись, щоб не пропустити!


def layout(tempo=1.0):
    t, B, parts = 0.15, {'walk': 0.0, 'steps': 2}, []
    for beat, f, a, b, gap in PHRASES:
        if beat: B[beat] = round(t - (0.05 if beat != 'hook' else 0), 3)
        parts.append([a, b, round(t, 3), f]); t += (b - a) / tempo + gap
    B['opts'] = B['o1'] - 0.15
    B['n3'] = round(t, 3); B['n2'] = B['n3'] + 2; B['n1'] = B['n3'] + 4
    for k, (f, a, b) in enumerate(COUNT): parts.append([a, b, round(B['n3'] + 2 * k + 0.05, 3), f])
    t = B['n3'] + 6.05
    for beat, f, a, b, gap in TAIL:
        B[beat] = round(t - 0.15, 3); parts.append([a, b, round(t, 3), f]); t += (b - a) / tempo + gap
    B['end'] = round(t, 2)
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
    sc['out'] = {'answer': False, 'duration': B['end'], 'subscribe': B['sub']}
    sc['duration'] = B['end']
    json.dump(sc, open(p, 'w'), ensure_ascii=False, indent=1); print(json.dumps(B))
