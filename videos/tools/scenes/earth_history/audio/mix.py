#!/usr/bin/env python3
# Rough preview mix: narration placed from timeline.json, music ducked under the voice (sidechain), sfx, -14 LUFS.
#   python3 scenes/earth_history/audio/mix.py   -> work/earth_history/audio_preview.mp3
import subprocess, os
from common import *
ins = ['-i', os.path.join(WORK, 'music.wav'), '-i', os.path.join(WORK, 'sfx.wav')]
files = {}
parts = []; labels = []
for a in TL['acts']:
    for f, fr, to, at in a['voice']:
        if f not in files:
            files[f] = len(files) + 2; ins += ['-i', os.path.join(SCN, f)]
        k = len(labels)
        parts.append(f"[{files[f]}:a]atrim={fr}:{to},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,adelay={int(at*1000)}:all=1[v{k}]")
        labels.append(f'[v{k}]')
g = ';'.join(parts) + ';' + ''.join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest,apad=whole_dur={DUR}[voice];"
g += "[voice]asplit=2[vo][vsc];"
g += "[0:a][vsc]sidechaincompress=threshold=0.02:ratio=4:attack=300:release=900:makeup=1[md];"
g += f"[md][1:a][vo]amix=inputs=3:normalize=0:duration=longest,atrim=0:{DUR},loudnorm=I=-14:TP=-1.5:LRA=11[o]"
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + ins + ['-filter_complex', g, '-map', '[o]', '-ar', '48000', '-b:a', '192k',
               os.path.join(WORK, 'audio_preview.mp3')], check=True)
print('audio_preview.mp3')
