# «Ядерна зима» — the sound effects (Higgsfield Mirelo SFX, sfx/*.mp3, mono) made wide and deep, laid on the timeline,
# and the final mix: music (ducked by the voice and the blasts) + effects (ducked under the voice) + voice → -14 LUFS,
# put onto the picture of videos/nuclear_winter.mp4 (the video stream is copied).   Run after ./make.sh nuclear_winter:
#   python3 scenes/nuclear_winter/mix_sfx.py
import os, subprocess, json
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'nuclear_winter'); SFX = os.path.join(HERE, 'sfx')
VIDEO = os.path.join(TOOLS, '..', 'nuclear_winter.mp4')
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']

# (file, start on the timeline s, gain dB, pitch factor, fade in s, fade out at s from its start or None, length s or None)
CUES = [('boom_far.mp3', 0.70, -3, 1.00, 0, None, None)]                               # the hook's far flash
for i, (t, g, p) in enumerate([(11.0, -9, 1.05), (11.6, -11, 0.92), (12.1, -8, 1.10), (12.6, -12, 0.88),
                               (13.0, -10, 1.0), (14.15, -9, 0.95), (14.6, -12, 1.08), (15.05, -11, 0.9)]):
    CUES.append(('boom_far.mp3', t - 0.2, g, p, 0, None, None))                       # the cascade, each a little different
CUES += [('blast_close.mp3', 12.2, 1, 1.0, 0, None, None),                             # crack at ~13.75 s, the close one
         ('firestorm.mp3', 16.0, -9, 1.0, 1.2, 6.8, 8.0), ('firestorm.mp3', 22.6, -10, 0.94, 1.5, 6.6, 8.0),
         ('firestorm.mp3', 28.4, -13, 0.9, 1.5, 3.0, 4.6),                              # fire → fading into the smoke
         ('wind_cold.mp3', 34.0, -8, 1.0, 2.0, 8.6, 10.0), ('wind_cold.mp3', 42.4, -9, 0.95, 2.0, 8.0, 10.0),
         ('wind_cold.mp3', 50.0, -14, 0.9, 1.5, 2.5, 4.5)]                              # the winter, dying away by 54.5 s

def chain(i, f, t, g, p, fi, fo, ln):
    s = f'[{i}:a]aformat=sample_rates=44100:channel_layouts=mono,asetrate={int(44100 * p)},aresample=44100'
    if ln: s += f',atrim=0:{ln}'
    if fi: s += f',afade=t=in:d={fi}'
    if fo: s += f',afade=t=out:st={fo}:d={(ln or 8) - fo}'
    # depth: a little sub on the booms; width: split into two slightly different channels; space: a big-hall echo
    if 'boom' in f or 'blast' in f: s += ',bass=g=5:f=60:w=0.8'
    s += f',volume={g}dB,pan=stereo|c0=c0|c1=c0,stereowiden=delay=18:feedback=0.25:crossfeed=0.35:drymix=0.85'
    s += ',aecho=0.85:0.6:70|140|260:0.30|0.22|0.14'
    s += f',adelay={int(t * 1000)}:all=1[s{i}]'
    return s

def main():
    ins, parts = [], []
    for i, c in enumerate(CUES):
        ins += ['-i', os.path.join(SFX, c[0])]
        parts.append(chain(i, *c))
    n = len(CUES)
    graph = ';'.join(parts) + ';' + ''.join(f'[s{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0,apad,atrim=0:{DUR + 1}[out]'
    sfx = os.path.join(WORK, 'sfx.wav')
    subprocess.run([FF, '-y', '-loglevel', 'error', *ins, '-filter_complex', graph, '-map', '[out]', sfx], check=True)
    # the final mix (as make.sh, plus the effects): music ducked by voice and by the effects, effects ducked by the voice
    music, voice = os.path.join(WORK, 'audio.wav'), os.path.join(WORK, 'voice.wav')
    mix = ('[1:a]volume=2.0,asplit=3[v][sc][sc2];[2:a]asplit=2[fx][fxsc];'
           '[0:a]volume=0.8[m0];[m0][sc]sidechaincompress=threshold=0.04:ratio=3:attack=60:release=800[m1];'
           '[m1][fxsc]sidechaincompress=threshold=0.08:ratio=2.5:attack=20:release=600[m];'
           '[fx][sc2]sidechaincompress=threshold=0.05:ratio=2:attack=40:release=700[fxd];'
           f'[m][fxd][v]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=13,afade=t=out:st={DUR - 1.5}:d=1.5[a]')
    tmp = VIDEO + '.tmp.mp4'
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', music, '-i', voice, '-i', sfx, '-i', VIDEO, '-filter_complex', mix,
                    '-map', '[a]', '-map', '3:v', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-movflags', '+faststart', '-t', str(DUR), tmp], check=True)
    os.replace(tmp, VIDEO)
    print('mixed: videos/nuclear_winter.mp4')

if __name__ == '__main__':
    main()
