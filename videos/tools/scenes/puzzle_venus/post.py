# «На якій я планеті?» (Венера) — finishes the frames (render.js, 720×1280) at 1080×1920 with the titles: the logo, the
# question, the three clues as they are told, the options А/Б/В, «пиши в коментарях», the 3-2-1 countdown (2 s per
# number, a ring running down), the answer (Б lights up, Venus's globe, «ВЕНЕРА!»), «наступна загадка — завтра» and the
# subscribe button; then the sound: the organ (music.js) and the small sounds (sfx.py) — and the voice, once recorded
# (scene.json "narration": [[from, to, at], …] cut from voice.mp3, NOT sped up), ducking the music, at −14 LUFS.
#   python3 scenes/puzzle_venus/post.py          -> videos/puzzle_venus.mp4
#   python3 scenes/puzzle_venus/post.py sound    -> only the sound redone (the titled frames kept)
#   python3 scenes/puzzle_venus/post.py test 1 5 -> titles over the stills (work/puzzle_venus/titled_<t>.jpg)
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, TOOLS)
import compose as C

WORK = os.path.join(TOOLS, 'work', 'puzzle_venus')
VIDEOS = os.path.abspath(os.path.join(TOOLS, '..'))
FF = __import__('imageio_ffmpeg').get_ffmpeg_exe()
SC = json.load(open(os.path.join(HERE, 'scene.json'))); B = SC['beats']
W, H, FPS, DUR = 1080, 1920, 30, SC['duration']
GOLD, GREEN = (247, 198, 107), (110, 225, 130)

f_q = C.font('Unbounded.ttf', 96, 700)
f_q2 = C.font('Unbounded.ttf', 52, 600)
f_clue = C.font('Commissioner.ttf', 43, 600)
f_num = C.font('Unbounded.ttf', 40, 700)
f_opt = C.font('Unbounded.ttf', 46, 600)
f_write = C.font('Commissioner.ttf', 44, 700)
f_cd = C.font('Unbounded.ttf', 150, 700)
f_ans = C.font('Unbounded.ttf', 104, 700)
f_sub = C.font('Commissioner.ttf', 40, 600)
f_bye = C.font('Unbounded.ttf', 50, 600)

CLUES = [('1', 'Небо оранжево-жовте, Сонця майже не видно', B['c1']),
         ('2', 'Тиск — як на глибині 900 м під водою', B['c2']),
         ('3', 'Спекотніше, ніж у печі: +465 °C', B['c3'])]
OPTS = [('А', 'МАРС'), ('Б', 'ВЕНЕРА'), ('В', 'ТИТАН')]
RIGHT = 1
CLUE_Y, OPT_Y, OPT_H, OPT_W = (300, 372, 444), (300, 404, 508), 88, 580
CD_C, CD_R = (540, 660), 96


def ease(x): return C.ease(x)
def k_in(t, a, d=0.3): return ease((t - a) / d)
def k_win(t, a, b, d=0.3): return max(0.0, min(ease((t - a) / d), 1 - ease((t - b) / d)))


def shadowed(img, lay, blur=10, k=0.8):
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh.putalpha(lay.getchannel('A').point(lambda v: int(v * k)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur))); img.alpha_composite(lay)


def text(img, s, f, cx, cy, alpha, fill=(255, 255, 255), anchor='mm'):
    if alpha <= 0: return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((cx, cy), s, font=f, fill=fill + (int(255 * alpha),), anchor=anchor)
    shadowed(img, lay, 9, 0.85)


def clue(img, i, t, alpha):
    n, s, t0 = CLUES[i]
    if alpha <= 0: return
    d0 = ImageDraw.Draw(img); tw = d0.textlength(s, font=f_clue); x0 = (W - tw - 64) / 2
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); cy = CLUE_Y[i]
    slide = 30 * (1 - k_in(t, t0 + 0.2, 0.35))
    d.ellipse((x0 + slide, cy - 24, x0 + 48 + slide, cy + 24), fill=GOLD + (int(255 * alpha),))
    d.text((x0 + 24 + slide, cy + 1), n, font=f_num, fill=(40, 24, 8, int(255 * alpha)), anchor='mm')
    d.text((x0 + 64 + slide, cy), s, font=f_clue, fill=(255, 255, 255, int(255 * alpha)), anchor='lm')
    shadowed(img, lay, 9, 0.9)


def option(img, i, t, alpha, state):
    # state: 0 plain, 1 the right one lit, -1 dimmed
    if alpha <= 0: return
    L, name = OPTS[i]; cy = OPT_Y[i]
    pop = 1 + 0.12 * math.sin(math.pi * min(1.0, max(0.0, (t - B['ans']) / 0.4))) if state == 1 else 1
    w, h = OPT_W * pop, OPT_H * pop
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    bg = (40, 150, 80) if state == 1 else (20, 14, 10)
    a = alpha * (0.45 if state == -1 else 1)
    if state == 1:
        gl = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(gl).rounded_rectangle((540 - w / 2 - 14, cy - h / 2 - 14, 540 + w / 2 + 14, cy + h / 2 + 14), radius=h / 2 + 14, fill=GREEN + (int(150 * a),))
        img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(16)))
    d.rounded_rectangle((540 - w / 2, cy - h / 2, 540 + w / 2, cy + h / 2), radius=h / 2, fill=bg + (int(185 * a),),
                        outline=(GREEN if state == 1 else GOLD) + (int(230 * a),), width=4)
    d.ellipse((540 - w / 2 + 14, cy - h / 2 + 12, 540 - w / 2 + 14 + h - 24, cy + h / 2 - 12), fill=(GREEN if state == 1 else GOLD) + (int(255 * a),))
    d.text((540 - w / 2 + 14 + (h - 24) / 2, cy + 2), L, font=f_num, fill=(30, 20, 8, int(255 * a)), anchor='mm')
    d.text((540 + 30, cy + 2), name, font=f_opt, fill=(255, 255, 255, int(255 * a)), anchor='mm')
    shadowed(img, lay, 12, 0.6)


def arrow(img, cx, cy, alpha, t):
    if alpha <= 0: return
    y = cy + 8 * math.sin(t * 6)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); c = GOLD + (int(255 * alpha),)
    d.rectangle((cx - 7, y - 26, cx + 7, y + 4), fill=c); d.polygon([(cx - 24, y), (cx + 24, y), (cx, y + 28)], fill=c)
    shadowed(img, lay, 6, 0.8)


def countdown(img, t):
    for n, t0 in ((3, B['n3']), (2, B['n2']), (1, B['n1'])):
        if not (t0 <= t < t0 + 2.0): continue
        u = (t - t0) / 2.0
        a = min(1.0, (t - t0) / 0.15) * (1 - ease((t - t0 - 1.8) / 0.2) if n == 1 else 1)
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); (cx, cy), r = CD_C, CD_R
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(20, 14, 10, int(150 * a)))
        d.arc((cx - r, cy - r, cx + r, cy + r), 0, 360, fill=(255, 255, 255, int(70 * a)), width=10)
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (1 - u), fill=GOLD + (int(255 * a),), width=10)
        s = 1 + 0.25 * (1 - ease((t - t0) / 0.25))
        fz = C.font('Unbounded.ttf', int(130 * s), 700)
        d.text((cx, cy + 4), str(n), font=fz, fill=(255, 255, 255, int(255 * a)), anchor='mm')
        shadowed(img, lay, 12, 0.7)


# Venus from space: the cloud tops (the site's texture), lit from the side, turning slowly
_GLOBE = {}
def globe(r, t):
    key = (r, int(t * 10))
    if key in _GLOBE: return _GLOBE[key]
    if 'tex' not in _GLOBE: _GLOBE['tex'] = np.asarray(Image.open(os.path.join(TOOLS, '../../planetarium/textures/venus_atmosphere_2k.jpg')).convert('RGB'), np.float32) / 255
    tex = _GLOBE['tex']; th, tw = tex.shape[:2]
    S = 2 * r + 80; y, x = (np.mgrid[0:S, 0:S] - S / 2 + 0.5) / r
    rr = x * x + y * y; inside = rr < 1; z = np.sqrt(np.clip(1 - rr, 0, 1))
    lat = np.arcsin(np.clip(-y, -1, 1)); lon = np.arctan2(x, z) + 0.15 * t
    u = ((lon / (2 * np.pi) + 0.5) % 1) * (tw - 1); v = (0.5 - lat / np.pi) * (th - 1)
    col = tex[v.astype(int).clip(0, th - 1), u.astype(int).clip(0, tw - 1)]
    L = np.array([-0.55, -0.35, 0.76]); L /= np.linalg.norm(L)
    lam = np.clip(x * L[0] + (-y) * -L[1] * -1 + z * L[2], 0, 1)
    shade = (0.12 + 0.95 * lam ** 0.8) * (0.6 + 0.4 * z ** 0.3)
    rgb = np.clip(col * shade[..., None] * np.array([1.08, 0.98, 0.82]), 0, 1)
    a = np.clip((1 - np.sqrt(rr)) * r / 1.5, 0, 1)
    im = np.dstack([rgb * 255, a * 255]).astype(np.uint8)
    g = Image.fromarray(im, 'RGBA')
    halo = Image.new('RGBA', g.size, (0, 0, 0, 0)); hd = ImageDraw.Draw(halo)
    hd.ellipse((40 - 14, 40 - 14, S - 40 + 14, S - 40 + 14), fill=(255, 210, 140, 110))
    out = Image.alpha_composite(halo.filter(ImageFilter.GaussianBlur(18)), g)
    _GLOBE[key] = out; return out


def titled(im, t):
    img = im.convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
    # a soft dark band behind the titles at the top
    if 'shade' not in _GLOBE:
        sa = np.zeros((H, W), np.uint8); n = 820
        sa[:n] = (np.clip(1 - np.arange(n) / n, 0, 1) ** 1.6 * 120)[:, None].astype(np.uint8)
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh.putalpha(Image.fromarray(sa)); _GLOBE['shade'] = sh
    img.alpha_composite(_GLOBE['shade'])
    C.draw_logo(img, 52, 92, 0.92, t)
    ans, bye = B['ans'], B['bye']
    # the question: big over the first seconds (on the very first frame), then small at the top until the answer
    kb = 1 - ease((t - B['c1'] + 0.3) / 0.3)
    if kb > 0:
        s = 1 + 0.06 * (1 - ease(t / 0.4))
        fq = f_q if s == 1 else C.font('Unbounded.ttf', int(96 * s), 700)
        text(img, 'НА ЯКІЙ Я', fq, 540, 300, kb); text(img, 'ПЛАНЕТІ?', fq, 540, 420, kb, GOLD)
    text(img, 'НА ЯКІЙ Я ПЛАНЕТІ?', f_q2, 540, 200, k_win(t, B['c1'] - 0.2, ans + 0.6))
    # the clues, one by one; they make way for the options
    for i in range(3):
        a = k_win(t, CLUES[i][2] + 0.2, B['opts'], 0.3)
        if i < 2: a *= 1 - 0.35 * k_in(t, CLUES[i + 1][2] + 0.2)          # the earlier ones a little dimmer
        clue(img, i, t, a)
    # the options
    for i in range(3):
        t0 = B['opts'] + 0.2 + 0.45 * i
        a = k_win(t, t0, ans + 0.9, 0.25)
        st = 0 if t < ans else (1 if i == RIGHT else -1)
        option(img, i, t, a, st)
    # «write in the comments», until the countdown
    kw = k_win(t, B['write'], B['n3'] + 0.2, 0.3)
    text(img, 'Пиши відповідь у коментарях', f_write, 540, 640, kw); arrow(img, 540, 712, kw, t)
    countdown(img, t)
    # the answer: Venus's globe and its name
    ka = k_win(t, ans + 1.15, bye, 0.4)
    if ka > 0:
        r = int(150 * (0.85 + 0.15 * ease((t - ans - 1.15) / 0.5)))
        g = globe(r, t)
        if ka < 1: g = g.copy(); g.putalpha(g.getchannel('A').point(lambda v: int(v * ka)))
        img.alpha_composite(g, (540 - g.size[0] // 2, 340 - g.size[1] // 2))
        text(img, 'ВЕНЕРА!', f_ans, 540, 570, ka, GOLD)
        text(img, '+465 °C · тиск ×92 · Сонця не видно', f_sub, 540, 655, ka * k_in(t, ans + 1.6, 0.4))
    # goodbye
    kz = k_win(t, bye, DUR + 1, 0.4)
    text(img, 'Наступна загадка —', f_bye, 540, 300, kz); text(img, 'ЗАВТРА', f_bye, 540, 375, kz, GOLD)
    if t > bye + 0.6: C.draw_subscribe(img, 540, 500, t - bye - 0.6, DUR - bye - 0.6 + 1, align='center')
    return img.convert('RGB')


def _job(f):
    i, o = os.path.join(WORK, 'frames', f'f_{f:05d}.jpg'), os.path.join(WORK, 'out', f'f_{f:05d}.jpg')
    if not os.path.exists(i): return
    titled(Image.open(i), f / FPS).save(o, quality=93)


def frames():
    os.makedirs(os.path.join(WORK, 'out'), exist_ok=True)
    with Pool(os.cpu_count()) as p: p.map(_job, range(int(round(DUR * FPS))), chunksize=16)
    print('titled')


def sound():
    nar = SC.get('narration')
    ins = ['-i', os.path.join(WORK, 'music.wav'), '-i', os.path.join(WORK, 'sfx.wav')]
    if nar:
        ins += ['-i', os.path.join(HERE, nar['file'])]
        parts = ''.join(f'[2:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={b - a - 0.04:.3f}:d=0.04,adelay={int(at * 1000)}:all=1[p{k}];'
                        for k, (a, b, at) in enumerate(nar['parts']))
        mix = (parts + ''.join(f'[p{k}]' for k in range(len(nar['parts']))) + f'amix=inputs={len(nar["parts"])}:normalize=0,highpass=f=70,apad,volume={nar.get("level", 1.0)}[vo];'
               '[vo]asplit=2[v][sc];[0:a]volume=2.6[m];[m][sc]sidechaincompress=threshold=0.04:ratio=4:attack=60:release=700[md];'
               '[1:a]volume=0.5[fx];[md][v][fx]amix=inputs=3:normalize=0')
    else:
        mix = '[0:a]volume=2.6[m];[1:a]volume=0.5[fx];[m][fx]amix=inputs=2:normalize=0'
    mix += f',loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={DUR - 1.2:.2f}:d=1.2,atrim=0:{DUR}[a]'
    subprocess.run([FF, '-y', '-loglevel', 'error', *ins, '-filter_complex', mix, '-map', '[a]', '-ar', '44100', os.path.join(WORK, 'mix.wav')], check=True)


def encode():
    out = os.path.join(VIDEOS, 'puzzle_venus.mp4')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(WORK, 'out', 'f_%05d.jpg'), '-i', os.path.join(WORK, 'mix.wav'),
                    '-map', '0:v', '-map', '1:a', '-t', f'{DUR:.2f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p',
                    '-profile:v', 'high', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out], check=True)
    print('written', out)


if __name__ == '__main__':
    if sys.argv[1:2] == ['test']:
        for a in sys.argv[2:]:
            titled(Image.open(os.path.join(WORK, f'still_{a}.jpg')), float(a)).save(os.path.join(WORK, f'titled_{a}.jpg'), quality=90)
        sys.exit()
    if 'sound' not in sys.argv[1:]: frames()
    sound(); encode()
