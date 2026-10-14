# Lays the narration onto the video timeline: each phrase of the recorded voice is cut out and placed under its caption.
#
#   python3 voice.py <scene>      reads scenes/<scene>/<narration.file>, writes work/<scene>/voice.wav
#
# scene.json "narration": {"file": ..., "level": gain, "tempo": speed, "parts": [[from, to, at], ...]} — seconds in the
# recording (from, to) and on the video timeline (at). Phrase edges get a few ms of fade so the cuts don't click.
# "tempo" (optional, e.g. 1.1) speeds the speech up without changing the pitch, when the recording is longer than the video.
import json, os, subprocess, sys
import imageio_ffmpeg

TOOLS = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1]
scene = os.path.join(TOOLS, 'scenes', name)
cfg = json.load(open(os.path.join(scene, 'scene.json')))
nar = cfg['narration']
work = os.path.join(TOOLS, 'work', name)
os.makedirs(work, exist_ok=True)

chains, labels = [], []
for i, (a, b, at) in enumerate(nar['parts']):
    tempo = nar.get('tempo', 1.0)
    d = (b - a) / tempo
    chains.append(f'[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,atempo={tempo},afade=t=in:d=0.02,afade=t=out:st={d - 0.04:.3f}:d=0.04,'
                  f'adelay={int(at * 1000)}:all=1[p{i}]')
    labels.append(f'[p{i}]')
graph = ';'.join(chains) + f';{"".join(labels)}amix=inputs={len(labels)}:normalize=0,' \
        f'highpass=f=70,volume={nar.get("level", 1.0)},apad,atrim=0:{cfg["duration"] + 1},aformat=sample_rates=44100:channel_layouts=stereo[v]'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', os.path.join(scene, nar['file']),
                '-filter_complex', graph, '-map', '[v]', os.path.join(work, 'voice.wav')], check=True)
print('voice.wav written')
