# The cut of "Що сталося з Землею, коли вимерли динозаври": the shots (work/chicxulub/<shot>.mp4, from preview.sh) one
# after another, each dissolving into the next; the author's voice (voice.mp3) phrase by phrase, each where its shot is
# (equal short pauses, 2 s before the closing question); the site's cinematic music under it, ducking under the voice;
# the sound of the entry and the impact (sfx.py) under those two shots. Everything at -14 LUFS.
#   python3 scenes/chicxulub/assemble.py            -> work/chicxulub/cut.mp4 (and cut_audio.wav)
import os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.abspath(os.path.join(HERE, '../../work/chicxulub'))
XF = 0.8                                                   # each dissolve, s
SHOTS = [('hook', 6), ('kpg_earth', 11), ('approach', 10), ('entry', 7.5), ('impact', 10), ('crater', 10),
         ('tsunami', 8), ('tsunami_globe', 9), ('fire_rain', 12), ('darkness', 15.5), ('finale', 26)]
START = {}
t = 0.0
for name, d in SHOTS:
    START[name] = t; t += d - XF
END = t + XF
# the phrases: (from, to) in voice.mp3, and where on the cut — (shot, seconds into it), or (None, seconds into the cut)
# where the recording's own pauses already fit; see script.md
PHRASES = [((0.00, 5.42), (None, 0.1)), ((6.03, 16.65), (None, 6.03)), ((17.17, 25.40), (None, 17.17)),
           ((25.94, 32.31), (None, 25.94)), ((32.82, 41.57), (None, 32.82)), ((42.05, 49.59), (None, 42.05)),
           ((50.05, 61.71), (None, 50.05)), ((62.19, 71.50), ('fire_rain', 0.9)), ((71.94, 86.87), ('darkness', 0.5)),
           ((87.36, 103.58), ('finale', 1.3))]
QUESTION = (104.13, 108.75)                                # 2 s after the last phrase


def run(*a): subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *a], check=True)


if __name__ == '__main__':
    # the picture: the dissolves
    ins, chain, prev = [], [], '0:v'
    for i, (name, d) in enumerate(SHOTS):
        ins += ['-i', os.path.join(WORK, name + '.mp4')]
        if i:
            out = f'v{i}'; chain.append(f'[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={START[name]:.3f}[{out}]'); prev = out
    picture = os.path.join(WORK, 'cut_picture.mp4')
    run(*ins, '-filter_complex', ';'.join(chain), '-map', f'[{prev}]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', picture)
    # the voice, phrase by phrase
    parts, at_last = [], 0
    for (a, b), (shot, off) in PHRASES:
        at = START[shot] + off if shot else off; parts.append((a, b, at)); at_last = at + (b - a)
    parts.append((*QUESTION, at_last + 2.0))
    chains = [f'[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={b - a - 0.04:.3f}:d=0.04,adelay={int(at * 1000)}:all=1[p{i}]'
              for i, (a, b, at) in enumerate(parts)]
    voice = os.path.join(WORK, 'cut_voice.wav')
    run('-i', os.path.join(HERE, 'voice.mp3'), '-filter_complex', ';'.join(chains) + ';' + ''.join(f'[p{i}]' for i in range(len(parts)))
        + f'amix=inputs={len(parts)}:normalize=0,highpass=f=70,apad,atrim=0:{END:.2f},aformat=sample_rates=48000:channel_layouts=stereo[v]',
        '-map', '[v]', voice)
    # the music (the site's, for the whole cut) and the sound of the entry and the impact
    music = os.path.join(WORK, 'cut_music.wav')
    subprocess.run(['node', os.path.join(HERE, 'site_music.js'), 'cinematic', f'{END:.2f}', music], check=True)
    sfx = os.path.join(WORK, 'sfx.wav')
    if not os.path.exists(sfx): subprocess.run(['python3', os.path.join(HERE, 'sfx.py'), sfx], check=True)
    audio = os.path.join(WORK, 'cut_audio.wav')
    run('-i', voice, '-i', music, '-i', sfx, '-filter_complex',
        '[0:a]loudnorm=I=-16:TP=-2,aformat=sample_rates=48000:channel_layouts=stereo,asplit[vo][key];'
        '[1:a]loudnorm=I=-25:TP=-6,aformat=sample_rates=48000:channel_layouts=stereo[mu0];'
        '[mu0][key]sidechaincompress=threshold=0.05:ratio=3:attack=80:release=600[mu];'
        f'[2:a]volume=0.8,adelay={int(START["entry"] * 1000)}:all=1,aformat=sample_rates=48000:channel_layouts=stereo[fx];'
        f'[vo][mu][fx]amix=inputs=3:normalize=0,atrim=0:{END:.2f},afade=t=out:st={END - 1.5:.2f}:d=1.5,loudnorm=I=-14:TP=-1.5:LRA=11[a]',
        '-map', '[a]', '-ar', '48000', audio)
    run('-i', picture, '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
        os.path.join(WORK, 'cut.mp4'))
    print('cut.mp4', f'{END:.1f} s')
