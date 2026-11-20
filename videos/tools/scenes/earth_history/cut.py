# The cut of «Історія Землі»: the acts (work/earth_history/acts[_<res>]/<act>/f_<frame>.jpg) dissolving into each
# other, the dinosaur insert (work/earth_history/dino16/frames), the photo/video inserts (assets.json + inserts.json),
# the 24-hour clock, the captions (pins), the end card; then the sound: the voice (timeline.json), the dinosaur voice +
# its effects, the score ducked under the voice, our effects; −14 LUFS.
#   EH_RES=960x540 python3 cut.py [draft]   -> videos/earth_history_draft.mp4   (1920x1080 -> videos/earth_history.mp4)
import json, math, os, subprocess, sys
import numpy as np
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter
os.environ.setdefault('EH_RES', '1920x1080')
from eh import *
import acts
from overlay import draw_clock, draw_label, font

TLJ = json.load(open(os.path.join(HERE, 'timeline.json')))
ACT_LIST = TLJ['acts']; DUR = TLJ['duration']; END0 = TLJ['end_card'][0]
XF = acts.XF
OUT = os.path.join(WORK, 'cut_' + os.environ['EH_RES']); DINO = os.path.join(WORK, 'dino16', 'frames')
if not (os.path.isdir(DINO) and os.listdir(DINO)):       # not rendered yet: the vertical film in a 16:9 frame (draft only)
    DINO = os.path.join(WORK, 'dino_draft_' + os.environ['EH_RES'])
S = SCALE

# ---------------------------------------------------------------- the clock: hours of Earth's day at cut time t
def clock_h(t):
    if t < 23.0: return 23.0 + 59 / 60 + 54 / 3600                       # «за шість секунд до півночі»
    if t < 28.5:                                                           # the rewind: the hand spins back to midnight
        return (23.9983 + sm((t - 23.0) / 5.5) * (24.0 - 23.9983 + 24.0 * 0)) % 24 if False else 23.9983 * (1 - sm((t - 23.0) / 5.5))
    for i, a in enumerate(ACT_LIST):
        if a['start'] <= t < a['end']:
            h0, h1 = a['clock']
            k = (t - a['start']) / max(a['end'] - a['start'], 1e-6)
            h = lerp(h0, h1, k)
            # between acts: run quickly on to the next act's start
            if i + 1 < len(ACT_LIST) and t > a['end'] - XF:
                hn = ACT_LIST[i + 1]['clock'][0]
                h = lerp(h, hn, sm((t - (a['end'] - XF)) / XF))
            if a['id'] == 'mammals':                                         # «…за шість секунд до півночі … Ти.»
                h = keys(t, [(a['start'], 23.66), (523.6, 23.966), (529.2, 23.9983), (549.0, 23.9999)])
            return min(h, 23.99999)
    return 23.99999

def ago(h):
    return (1 - h / 24.0) * 4.54e9

# ---------------------------------------------------------------- captions (pins): (t0, t1, text, sub, anchor-fn)
def geo(name, lat, lon):
    def f(t):
        acts.ACTS[name].__wrapped__ if False else None
        c = acts.LASTCAM.get('c')
        return None
    return f

def anchor_globe(name, lat, lon):
    """screen point of (lat, lon) on the globe as the act's camera sees it at cut time t"""
    def f(t):
        a = next(x for x in ACT_LIST if x['id'] == name)
        acts.ACTS[name](t - a['start']) if False else None
        c = cam_for(name, t - a['start'])
        if c is None: return None
        P = ll(lat, lon) * RE
        if nrm(P) @ nrm(c[0] - P * 0) < 0.25: return None
        x, y, z = cm.project(c, P)
        return float(x[0]), float(y[0])
    return f

def cam_for(name, lt):
    """the camera an act used at local time lt (re-derived without rendering)"""
    import inspect
    src = inspect.getsource(acts.ACTS[name])
    if 'ckeys(' not in src: return None
    ks = eval(src.split('ckeys(t, ')[1].split('])')[0] + ']', {'np': np})
    return acts.globe_cam(acts.ckeys(lt, ks))

def anchor_fn(name, key):
    def f(t):
        a = next(x for x in ACT_LIST if x['id'] == name)
        d = acts.ANCH.get(name, lambda lt: {})(t - a['start'])
        return d.get(key)
    return f

def kyiv(t):
    c, home = acts.night_cam(min(t, 15.0))
    x, y, z = cm.project(c, ll(50.45, 30.52) * RE); return float(x[0]), float(y[0])

def act_t(name, lt):
    return next(x for x in ACT_LIST if x['id'] == name)['start'] + lt

CAPS = [
    (1.5, 10.0, 'УКРАЇНА', 'сьогодні', kyiv, (110, -120)),
    (act_t('theia', 0.6), act_t('theia', 3.9), 'ТЕЙЯ', 'планета розміром з Марс', anchor_fn('theia', 'theia'), (150, -110)),
    (act_t('theia', 19.5), act_t('theia', 27.5), 'МІСЯЦЬ', 'у 16 разів ближче, ніж сьогодні', anchor_fn('theia', 'moon'), (170, -120)),
    (act_t('theia', 41.0), act_t('theia', 48.5), 'РЕШТКИ ТЕЙЇ?', 'одна з гіпотез', anchor_fn('theia', 'blob'), (-420, -140)),
    (act_t('snowball', 8.5), act_t('snowball', 15.5), 'ЗЕМЛЯ-СНІЖКА', 'лід до самого екватора', anchor_globe('snowball', 0, 352), (180, -160)),
    (act_t('permian', 5.0), act_t('permian', 13.0), 'СИБІР', 'вулкани заливають лавою', anchor_globe('permian', 60, 60), (170, -130)),
    (act_t('permian', 0.6), act_t('permian', 4.6), 'ПАНГЕЯ', 'усі материки разом', anchor_globe('permian', 5, 25), (180, 120)),
    (act_t('dinos', 12.0), act_t('dinos', 18.5), 'АТЛАНТИКА', 'народжується океан', anchor_globe('dinos', 18, -32), (170, -130)),
    (act_t('mammals', 8.0), act_t('mammals', 13.5), 'ГІМАЛАЇ', 'Індія врізається в Азію', anchor_globe('mammals', 29, 84), (160, -140)),
    (act_t('mammals', 19.5), act_t('mammals', 26.0), 'АФРИКА', 'перші люди — 300 тис. років тому', anchor_globe('mammals', 8, 32), (180, -150)),
]

# ---------------------------------------------------------------- inserts: real photos/clips (inserts.json)
INS = json.load(open(os.path.join(HERE, 'inserts.json'))) if os.path.exists(os.path.join(HERE, 'inserts.json')) else []
ASSETS = os.path.join(WORK, 'assets'); CLIPS = os.path.join(WORK, 'clips_' + os.environ['EH_RES'])

def prep_clips():
    """each video insert as a JPEG sequence at our size and 30 fps (once)"""
    for e in INS:
        if e.get('kind') != 'video': continue
        d = os.path.join(CLIPS, os.path.splitext(e['file'])[0])
        if os.path.isdir(d) and os.listdir(d): continue
        os.makedirs(d, exist_ok=True)
        sp = e.get('speed', 1.0)
        run('-ss', str(e.get('from', 0)), '-i', os.path.join(ASSETS, e['file']), '-vf',
            f'setpts={1 / sp}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}', '-q:v', '3',
            os.path.join(d, 'f_%05d.jpg'))

_PH = {}
def insert_img(e, t):
    u = (t - e['t0']) / max(e['t1'] - e['t0'], 1e-3)
    if e.get('kind') == 'video':
        d = os.path.join(CLIPS, os.path.splitext(e['file'])[0]); fs = sorted(os.listdir(d))
        im = Image.open(os.path.join(d, fs[min(int((t - e['t0']) * FPS), len(fs) - 1)])).convert('RGB')
        z0, z1 = e.get('zoom', [1.0, 1.04])
    else:
        if e['file'] not in _PH:
            if len(_PH) > 4: _PH.clear()
            src = Image.open(os.path.join(ASSETS, e['file'])).convert('RGB')
            sc = max(W * 1.25 / src.width, H * 1.25 / src.height)
            _PH[e['file']] = src.resize((int(src.width * sc), int(src.height * sc)), Image.LANCZOS)
        im = _PH[e['file']]
        z0, z1 = e.get('zoom', [1.0, 1.1])
    z = lerp(z0, z1, u)
    px, py = e.get('pan', [0.0, 0.0])
    w0, h0 = im.size
    k = min(w0 / W, h0 / H) / z; cw, ch = W * k, H * k                 # the largest 16:9 box, then zoomed in
    cx = w0 / 2 + px * (u - 0.5) * (w0 - cw); cy = h0 / 2 + py * (u - 0.5) * (h0 - ch)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return np.asarray(im.resize((W, H), Image.BICUBIC, box=box), np.float32)

def inserts(img, t):
    for e in INS:
        if e['t0'] - 0.05 <= t <= e['t1'] + 0.05 and os.path.exists(os.path.join(ASSETS, e['file'])):
            a = sm((t - e['t0']) / 0.7) * (1 - sm((t - (e['t1'] - 0.7)) / 0.7))
            if a > 0: img = img * (1 - a) + insert_img(e, t) * a
    return img

# ---------------------------------------------------------------- the picture
def act_frame(name, i):
    d = os.path.join(acts.ACTS_DIR if hasattr(acts, 'ACTS_DIR') else ACTS_DIR, name)
    p = os.path.join(ACTS_DIR, name, f'f_{i:05d}.jpg')
    if os.path.exists(p): return np.asarray(Image.open(p).convert('RGB'), np.float32)
    return None

def dino_frame(t):
    a = next(x for x in ACT_LIST if x['id'] == 'asteroid')
    k = int(round((t - a['start']) * FPS))
    files = sorted(os.listdir(DINO)) if os.path.isdir(DINO) else []
    if not files: return None
    f = files[min(max(k, 0), len(files) - 1)]
    im = Image.open(os.path.join(DINO, f)).convert('RGB')
    if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
    return np.asarray(im, np.float32)

def base(i):
    t = i / FPS
    layers = []
    for j, a in enumerate(ACT_LIST):
        s0, s1 = a['start'] - XF / 2, a['end'] + XF / 2
        if s0 <= t < s1:
            w = 1.0
            if j > 0 and t < a['start'] + XF / 2: w = sm((t - s0) / XF)
            layers.append((a['id'], w))
    img = None
    for name, w in layers:
        fr = dino_frame(t) if name == 'asteroid' else act_frame(name, i)
        if fr is None: continue
        img = fr if img is None else img * (1 - w) + fr * w
    if img is None: img = np.zeros((H, W, 3), np.float32)
    return img

def endcard(im, t):
    k = sm((t - END0) / 1.2)
    if k <= 0: return
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, H], fill=(3, 6, 14, int(150 * k)))
    ft = font(int(96 * S), 600); txt = 'НЕБОЗВІД'
    w = d.textlength(txt, font=ft); d.text(((W - w) / 2, H * 0.36), txt, font=ft, fill=(255, 255, 255, int(255 * k)))
    fs = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Regular.otf', int(34 * S))
    for j, s in enumerate(('nebozvid.com.ua', 'Підписуйся — далі ще цікавіше')):
        w = d.textlength(s, font=fs); d.text(((W - w) / 2, H * 0.52 + j * 52 * S), s, font=fs, fill=(220, 228, 240, int(230 * k)))
    im.alpha_composite(ov)

def frame(i):
    t = i / FPS
    img = inserts(base(i), t)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
    if t < END0 - 0.5:
        h = clock_h(t)
        fade = min(1.0, t / 0.8) * (1 - sm((t - (END0 - 1.5)) / 1.0))
        draw_clock(im, h, ago(h), W - 170 * S, 120 * S, 70 * S, alpha=fade)
    for e in INS:
        c = e.get('cap')
        if c and e['t0'] <= t <= e['t1']:
            k = sm((t - e['t0'] - 0.6) / 0.6) * (1 - sm((t - e['t1'] + 1.0) / 0.6))
            ax, ay = c['at'][0] * W, c['at'][1] * H
            draw_label(im, c['text'], ax + c.get('off', [150, -120])[0] * S, ay + c.get('off', [150, -120])[1] * S, int(34 * S), k,
                       sub=c.get('sub'), style='pin', anchor=(ax, ay))
    for t0, t1, txt, sub, af, off in CAPS:
        if t0 - 0.1 <= t <= t1 + 0.6:
            p = af(t)
            if p is None: continue
            k = sm((t - t0) / 0.6) * (1 - sm((t - t1) / 0.6))
            ax, ay = p
            x = min(max(ax + off[0] * S, 40 * S), W - 520 * S); y = min(max(ay + off[1] * S, 40 * S), H - 120 * S)
            draw_label(im, txt, x, y, int(34 * S), k, sub=sub, style='pin', anchor=(ax, ay))
    endcard(im, t)
    im.convert('RGB').save(os.path.join(OUT, f'f_{i:05d}.jpg'), quality=92)

def picture(i0=0, i1=None):
    os.makedirs(OUT, exist_ok=True)
    n = int(round(DUR * FPS)) if i1 is None else i1
    todo = [i for i in range(i0, n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    with Pool(3) as p: p.map(frame, todo, chunksize=20)

# ---------------------------------------------------------------- the sound
def run(*a): subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *a], check=True)

def sound(dst):
    parts = [v for a in ACT_LIST for v in a['voice']]
    ins = sum([['-i', os.path.join(HERE, f)] for f in ('voice_p1.mp3', 'voice_p2.mp3', 'voice_p3.mp3')], [])
    idx = {'voice_p1.mp3': 0, 'voice_p2.mp3': 1, 'voice_p3.mp3': 2}
    ch = [f'[{idx[f]}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.02,'
          f'afade=t=out:st={b - a - 0.08:.3f}:d=0.08,adelay={int(at * 1000)}:all=1[p{i}]' for i, (f, a, b, at) in enumerate(parts)]
    n = len(parts); extra = ''
    ast = next(x for x in ACT_LIST if x['id'] == 'asteroid')['start']
    dv = os.path.join(WORK, 'dino16', 'voice.wav'); ds = os.path.join(WORK, 'dino16', 'sfx.wav')
    k = 3
    for f in (dv, ds):
        if os.path.exists(f):
            ins += ['-i', f]; ch.append(f'[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(ast * 1000)}:all=1[p{n}]'); n += 1; k += 1
    voice = os.path.join(WORK, 'cut_voice.wav')
    run(*ins, '-filter_complex', ';'.join(ch) + ';' + ''.join(f'[p{i}]' for i in range(n)) +
        f'amix=inputs={n}:normalize=0,highpass=f=70,apad,atrim=0:{DUR:.2f}[v]', '-map', '[v]', '-ar', '48000', voice)
    music = os.path.join(WORK, 'music.wav'); sfx = os.path.join(WORK, 'sfx.wav')
    run('-i', voice, '-i', music, '-i', sfx, '-filter_complex',
        '[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit[vo][key];'
        '[1:a]aformat=sample_rates=48000:channel_layouts=stereo[mu0];'
        '[mu0][key]sidechaincompress=threshold=0.03:ratio=4:attack=60:release=700[mu];'
        '[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.9[fx];'
        f'[vo][mu][fx]amix=inputs=3:normalize=0,atrim=0:{DUR:.2f},afade=t=out:st={DUR - 1.2:.2f}:d=1.2,'
        'loudnorm=I=-14:TP=-1.5:LRA=11[a]', '-map', '[a]', '-ar', '48000', dst)

if __name__ == '__main__':
    draft = 'draft' in sys.argv[1:]
    prep_clips()
    picture()
    snd = os.path.join(WORK, 'cut_audio.wav'); sound(snd)
    name = 'earth_history_draft.mp4' if W < 1920 else 'earth_history.mp4'
    dst = os.path.abspath(os.path.join(TOOLS, '..', name))
    run('-framerate', str(FPS), '-i', os.path.join(OUT, 'f_%05d.jpg'), '-i', snd, '-c:v', 'libx264', '-preset', 'medium',
        '-pix_fmt', 'yuv420p', '-crf', '22' if draft or W < 1920 else '18', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
        '-shortest', dst)
    print(dst)
