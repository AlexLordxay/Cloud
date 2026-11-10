# «Великий вибух» — a check of the timeline: the voice re-laid by timeline.json (voice_tl.mp3) and a plain animatic
# (animatic.mp4, 1280×720, 10 fps): the act, the shot, the clock and the phrase as a subtitle — to listen to the pauses
# and see that every phrase and shot falls where it should. Not the film itself.
#   python3 timeline.py && python3 animatic.py
import json, os, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
tl = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))

raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(HERE, tl['voice']), '-f', 'f32le', '-ac', '1',
                      '-ar', str(SR), '-'], capture_output=True, check=True).stdout
src = np.frombuffer(raw, np.float32)
out = np.zeros(int((tl['duration'] + 1) * SR), np.float32)
F = int(0.012 * SR)                                   # 12 ms fades at the cuts (the cuts are in silence anyway)
ramp = np.linspace(0, 1, F, dtype=np.float32)
for p in tl['phrases']:
    a, b = int((p['src'][0] - 0.08) * SR), int((p['src'][1] + 0.12) * SR)   # keep the breath around the phrase
    a = max(a, 0); seg = src[a:b].copy()
    seg[:F] *= ramp; seg[-F:] *= ramp[::-1]
    t = int((p['t0'] - 0.08) * SR) if p['i'] else 0
    out[t:t + len(seg)] += seg
out = out[:int(tl['duration'] * SR)]
wav = os.path.join(HERE, 'voice_tl.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', wav],
               input=out.tobytes(), check=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-b:a', '192k', os.path.join(HERE, 'voice_tl.mp3')], check=True)


def ts(x): return f'{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}'


ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1280', 'PlayResY: 720', '', '[V4+ Styles]',
       'Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow',
       'Style: Sub,DejaVu Sans,34,&H00FFFFFF,&H00000000,&H00000000,0,2,80,80,60,1,2,0',
       'Style: Shot,DejaVu Sans,30,&H0080D0FF,&H00000000,&H00000000,1,8,60,60,150,1,1,0',
       'Style: Act,DejaVu Sans,26,&H00A0A0A0,&H00000000,&H00000000,0,7,40,40,30,1,1,0',
       '', '[Events]', 'Format: Layer, Start, End, Style, Text']
for p in tl['phrases']: ass.append(f"Dialogue: 0,{ts(p['t0'])},{ts(p['t1'] + 0.25)},Sub,{p['text']}")
for s in tl['shots']: ass.append(f"Dialogue: 0,{ts(s['t0'])},{ts(s['t1'])},Shot,{s['name']}")
acts = tl['acts']
for k, a in enumerate(acts):
    t1 = acts[k + 1]['t0'] if k + 1 < len(acts) else tl['duration']
    ass.append(f"Dialogue: 0,{ts(a['t0'])},{ts(t1)},Act,Акт {a['name']}")
open(os.path.join(HERE, 'animatic.ass'), 'w', encoding='utf-8').write('\n'.join(ass) + '\n')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f"color=c=0x0b0d14:s=1280x720:r=10:d={tl['duration']}",
                '-i', wav, '-vf', "ass=animatic.ass,drawtext=font='DejaVu Sans':fontsize=26:fontcolor=0xa0a0a0:x=w-tw-40:y=30:"
                "text='%{pts\\:hms}'", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28', '-c:a', 'aac', '-b:a', '128k',
                '-shortest', 'animatic.mp4'], cwd=HERE, check=True)
os.remove(wav)
print('voice_tl.mp3, animatic.mp4:', tl['duration'], 's')
