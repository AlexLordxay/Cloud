# The cut of "Що сталося з Землею, коли вимерли динозаври": the shots (work/chicxulub/shot_<shot>/, from preview.sh) one
# after another, each dissolving into the next, the last frame held under the end card; the author's voice phrase by
# phrase, each where its shot is, never closer than PAUSE to the one before (2 s before the closing question); the
# site's cinematic music under it, ducking under the voice; the sound of the entry and the impact (sfx.py). Then
# compose.py puts on the logo, the captions (captions.py) and the end card at 1080 × 1920. Everything at -14 LUFS.
#   python3 scenes/chicxulub/assemble.py          -> videos/dinosaurs.mp4  (frames in work/chicxulub/frames, out)
#   python3 scenes/chicxulub/assemble.py draft    -> work/chicxulub/cut.mp4 (720p, no captions)
import os, shutil, subprocess, sys
from multiprocessing import Pool
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
WORK = os.path.join(TOOLS, 'work', 'chicxulub')
FPS, XF, PAUSE, ASK = 30, 0.8, 0.45, 2.0             # frame rate; each dissolve; between phrases; before the question
# (shot, rendered length): each is shown at least that long, and longer (a touch slower, unseen) where its phrase needs
# it, so no phrase or caption runs over into the next shot
SHOTS = [('hook', 6), ('kpg_earth', 11), ('approach', 10), ('entry', 7.5), ('impact', 10), ('crater', 10),
         ('tsunami', 8), ('tsunami_globe', 9), ('fire_rain', 12), ('darkness', 15.5), ('finale', 26)]
# the phrases: the file, where the words start and end in it, where its trailing breath ends (a cut there clips no
# ending), the shot it starts on and how far into it, and the shot it must end within. Phrases 3, 6, 7 re-recorded for
# the stress (fix3/6/7.mp3; in 3 "удвадцятеро" became "у двадцять разів").
PHRASES = [('voice.mp3', 0.00, 5.42, 5.72, 'hook', 0.1, 'hook'),
           ('voice.mp3', 6.03, 16.65, 16.91, 'kpg_earth', 0.6, 'kpg_earth'),
           ('fix3.mp3', 0.00, 8.80, 8.98, 'approach', 0.9, 'approach'),
           ('voice.mp3', 25.94, 32.31, 32.56, 'entry', 0.9, 'entry'),
           ('voice.mp3', 32.82, 41.57, 41.81, 'impact', 0.9, 'impact'),
           ('fix6.mp3', 0.00, 8.28, 8.43, 'crater', 0.6, 'crater'),
           ('fix7.mp3', 0.00, 11.97, 12.19, 'tsunami', 0.5, 'tsunami_globe'),
           ('voice.mp3', 62.19, 71.50, 71.72, 'fire_rain', 0.9, 'fire_rain'),
           ('voice.mp3', 71.94, 86.87, 87.11, 'darkness', 0.5, 'darkness'),
           ('voice.mp3', 87.36, 103.58, 103.85, 'finale', 1.3, 'finale'),
           ('voice.mp3', 104.13, 108.62, 108.75, 'finale', 0, 'finale')]


def _layout():
    """Lay out the shots and the phrases together: each phrase starts where it wants on its shot, never closer than
    PAUSE (ASK before the question) to the one before; a shot is stretched until its phrases end 0.3 s before the next
    shot begins to dissolve in. Returns {shot: (start, length on the cut)}, [(file, from, to with breath, at, end)]."""
    lay, ph, t, end, j = {}, [], 0.0, -PAUSE, 0
    for name, r in SHOTS:
        lay[name] = [t, r]
        while j < len(PHRASES) and PHRASES[j][4] == name:
            f, a, b, tail, _, off, until = PHRASES[j]
            at = max(t + off, end + (ASK if j == len(PHRASES) - 1 else PAUSE)); end = at + b - a
            ph.append((f, a, tail, at, end, until)); j += 1
        for p in ph:
            if p[5] == name: lay[name][1] = max(lay[name][1], p[4] + 0.3 - lay[name][0] + XF)
        t = lay[name][0] + lay[name][1] - XF
    return {k: tuple(v) for k, v in lay.items()}, [p[:5] for p in ph]


LAYOUT, _PLACED = _layout()
START = {k: v[0] for k, v in LAYOUT.items()}
SHOTS_END = max(s + d for s, d in LAYOUT.values())


def placed():
    """Each phrase: (file, from, to with its breath, at on the cut, words end on the cut)."""
    return _PLACED


END_CARD = placed()[-1][4] + 0.3
DURATION = END_CARD + 5.0


def run(*a): subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *a], check=True)


def _frame(i):
    # frame i of the cut: the shot showing, dissolving into the next one where they overlap; the last frame held
    t = i / FPS
    layers = []
    for name, r in SHOTS:
        d = LAYOUT[name][1]; s = t - START[name]
        if -1e-6 <= s < d:
            n = len(os.listdir(os.path.join(WORK, 'shot_' + name)))
            layers.append((name, min(int(s * r / d * FPS + 1e-6), n - 1), min(1.0, s / XF) if name != 'hook' else 1.0))
    if not layers:
        name = SHOTS[-1][0]; layers = [(name, len(os.listdir(os.path.join(WORK, 'shot_' + name))) - 1, 1.0)]
    img = None
    for name, k, a in layers:
        im = Image.open(os.path.join(WORK, 'shot_' + name, f'f_{k:05d}.jpg')).convert('RGB')
        img = im if img is None else Image.blend(img, im, a)
    img.save(os.path.join(WORK, 'frames', f'f_{i:05d}.jpg'), quality=95)


def picture():
    d = os.path.join(WORK, 'frames'); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    with Pool(os.cpu_count()) as p: p.map(_frame, range(int(round(DURATION * FPS))), chunksize=30)


def audio(dst):
    parts = placed()
    ins = sum([['-i', os.path.join(HERE, f)] for f in sorted({p[0] for p in parts})], [])
    idx = {f: i for i, f in enumerate(sorted({p[0] for p in parts}))}
    chains = [f'[{idx[f]}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.02,'
              f'afade=t=out:st={b - a - 0.12:.3f}:d=0.12,adelay={int(at * 1000)}:all=1[p{i}]' for i, (f, a, b, at, _) in enumerate(parts)]
    voice = os.path.join(WORK, 'cut_voice.wav')
    run(*ins, '-filter_complex', ';'.join(chains) + ';' + ''.join(f'[p{i}]' for i in range(len(parts)))
        + f'amix=inputs={len(parts)}:normalize=0,highpass=f=70,apad,atrim=0:{DURATION:.2f},aformat=sample_rates=48000:channel_layouts=stereo[v]',
        '-map', '[v]', voice)
    music = os.path.join(WORK, 'cut_music.wav')
    subprocess.run(['node', os.path.join(HERE, 'site_music.js'), 'cinematic', f'{DURATION:.2f}', music], check=True)
    sfx = os.path.join(WORK, 'sfx.wav')
    if not os.path.exists(sfx): subprocess.run(['python3', os.path.join(HERE, 'sfx.py'), sfx], check=True)
    run('-i', voice, '-i', music, '-i', sfx, '-filter_complex',
        '[0:a]loudnorm=I=-16:TP=-2,aformat=sample_rates=48000:channel_layouts=stereo,asplit[vo][key];'
        '[1:a]loudnorm=I=-25:TP=-6,aformat=sample_rates=48000:channel_layouts=stereo[mu0];'
        '[mu0][key]sidechaincompress=threshold=0.05:ratio=3:attack=80:release=600[mu];'
        f'[2:a]volume=0.8,adelay={int(START["entry"] * 1000)}:all=1,aformat=sample_rates=48000:channel_layouts=stereo[fx];'
        f'[vo][mu][fx]amix=inputs=3:normalize=0,atrim=0:{DURATION:.2f},afade=t=out:st={DURATION - 1.5:.2f}:d=1.5,'
        'loudnorm=I=-14:TP=-1.5:LRA=11[a]', '-map', '[a]', '-ar', '48000', dst)


if __name__ == '__main__':
    draft = sys.argv[1:] == ['draft']
    picture()
    snd = os.path.join(WORK, 'cut_audio.wav'); audio(snd)
    if draft:
        run('-framerate', str(FPS), '-i', os.path.join(WORK, 'frames', 'f_%05d.jpg'), '-i', snd, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-crf', '18', '-c:a', 'aac', '-b:a', '192k', '-shortest', os.path.join(WORK, 'cut.mp4'))
        print('cut.mp4', f'{DURATION:.1f} s'); sys.exit()
    subprocess.run(['python3', os.path.join(TOOLS, 'compose.py'), 'chicxulub'], check=True)
    dst = os.path.abspath(os.path.join(TOOLS, '..', 'dinosaurs.mp4'))
    run('-framerate', str(FPS), '-i', os.path.join(WORK, 'out', 'f_%05d.jpg'), '-i', snd, '-c:v', 'libx264', '-preset', 'slow',
        '-pix_fmt', 'yuv420p', '-crf', '19', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', dst)
    print(dst, f'{DURATION:.1f} s')
