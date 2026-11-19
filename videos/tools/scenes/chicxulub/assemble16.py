# The 16:9 cut of "Що сталося з Землею, коли вимерли динозаври" for the long video «Історія Землі»: the same shots
# (work/chicxulub/shot16_<shot>/, rendered by render.js with CX_W/CX_H; post.py glow on them) laid out as in assemble.py
# (_layout), the same voice phrases but without the last one (the closing question); the cut ends 2.0 s after the end
# of phrase 10. No captions, logo, end card or music. Frames are 1920 × 1080 (shots rendered smaller are resized with
# Lanczos).
#   python3 scenes/chicxulub/assemble16.py   -> work/earth_history/dino16/{frames/, voice.wav, sfx.wav, preview.mp4}
import os, shutil, subprocess, sys
from multiprocessing import Pool
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble as A
from assemble import FPS, XF, SHOTS, HERE, TOOLS, WORK, run
A.PHRASES = A.PHRASES[:10]                       # the closing question is dropped
LAYOUT, PLACED = A._layout()
START = {k: v[0] for k, v in LAYOUT.items()}
DURATION = PLACED[-1][4] + 2.0
OUT = os.path.join(TOOLS, 'work', 'earth_history', 'dino16')
SIZE = (1920, 1080)


def _frame(i):
    t = i / FPS; layers = []
    for name, r in SHOTS:
        d = LAYOUT[name][1]; s = t - START[name]
        if -1e-6 <= s < d:
            n = len(os.listdir(os.path.join(WORK, 'shot16_' + name)))
            layers.append((name, min(int(s * r / d * FPS + 1e-6), n - 1), min(1.0, s / XF) if name != 'hook' else 1.0))
    if not layers:
        name = SHOTS[-1][0]; layers = [(name, len(os.listdir(os.path.join(WORK, 'shot16_' + name))) - 1, 1.0)]
    img = None
    for name, k, a in layers:
        im = Image.open(os.path.join(WORK, 'shot16_' + name, f'f_{k:05d}.jpg')).convert('RGB')
        if im.size != SIZE: im = im.resize(SIZE, Image.LANCZOS)
        img = im if img is None else Image.blend(img, im, a)
    img.save(os.path.join(OUT, 'frames', f'f_{i:05d}.jpg'), quality=95)


def picture():
    d = os.path.join(OUT, 'frames'); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    with Pool(os.cpu_count()) as p: p.map(_frame, range(int(round(DURATION * FPS))), chunksize=30)


def audio():
    parts = PLACED; files = sorted({p[0] for p in parts}); idx = {f: i for i, f in enumerate(files)}
    ins = sum([['-i', os.path.join(HERE, f)] for f in files], [])
    chains = [f'[{idx[f]}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.02,'
              f'afade=t=out:st={b - a - 0.12:.3f}:d=0.12,adelay={int(at * 1000)}:all=1[p{i}]' for i, (f, a, b, at, _) in enumerate(parts)]
    run(*ins, '-filter_complex', ';'.join(chains) + ';' + ''.join(f'[p{i}]' for i in range(len(parts)))
        + f'amix=inputs={len(parts)}:normalize=0,highpass=f=70,apad,atrim=0:{DURATION:.2f},aformat=sample_rates=48000:channel_layouts=stereo[v]',
        '-map', '[v]', os.path.join(OUT, 'voice.wav'))
    raw = os.path.join(WORK, 'sfx.wav')
    if not os.path.exists(raw): subprocess.run(['python3', os.path.join(HERE, 'sfx.py'), raw], check=True)
    run('-i', raw, '-af', f'volume=0.8,adelay={int(START["entry"] * 1000)}:all=1,aformat=sample_rates=48000:channel_layouts=stereo,'
        f'apad,atrim=0:{DURATION:.2f}', os.path.join(OUT, 'sfx.wav'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    if sys.argv[1:] != ['audio']: picture()
    audio()
    run('-framerate', str(FPS), '-i', os.path.join(OUT, 'frames', 'f_%05d.jpg'), '-i', os.path.join(OUT, 'voice.wav'),
        '-i', os.path.join(OUT, 'sfx.wav'), '-filter_complex', '[1:a][2:a]amix=inputs=2:normalize=0[a]', '-map', '0:v', '-map', '[a]',
        '-vf', 'scale=1280:720:flags=lanczos', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
        '-shortest', os.path.join(OUT, 'preview.mp4'))
    print('dino16', f'{DURATION:.2f} s', {k: (round(v[0], 1), round(v[1], 1)) for k, v in LAYOUT.items()})
