# «Великий вибух був не вибухом» — the assembly: the rendered segments laid end to end on the voice's timeline with
# dissolves wherever two segments overlap (no cuts), the thin HUD (time since the beginning, temperature), small
# credits for the real images, «художня візуалізація», the «Підписатися» button at 0:25, the end card; the voice
# (voice_tl.mp3) mixed with the score (music.wav, ducked under the voice), −14 LUFS.
#   python3 prod/assemble.py [--preview] [--from S --to S]    -> videos/big_bang.mp4 (preview: test/preview.mp4, 960p)
import importlib, json, math, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fx

BB = fx.BB
W, H, FPS = fx.W, fx.H, fx.FPS
DUR = fx.TL['duration']
SEGS = ['seg01', 'seg02', 'seg03', 'seg04', 'seg05', 'seg06', 'seg07', 'seg08', 'seg09', 'seg10', 'seg11', 'seg12',
        'seg13', 'seg14', 'seg15', 'seg16', 'seg17']
PREVIEW = '--preview' in sys.argv


def seg_ranges():
    out = []
    for s in SEGS:
        src = open(os.path.join(BB, 'prod', s + '.py'), encoding='utf-8').read()
        ns = {}
        # T0/T1 without importing (cheap): evaluate the module's T0, T1 line in the light of fx
        for line in src.splitlines():
            if line.startswith('T0, T1 = '):
                exec(line, {'fx': fx, 'math': math}, ns); break
        out.append((s, ns['T0'], ns['T1']))
    return out


RANGES = seg_ranges()


def sources(T):
    """[(segment, weight)] for time T: dissolve across each overlap"""
    act = [(s, a, b) for s, a, b in RANGES if a - 1e-6 <= T <= b + 1e-6]
    if not act: return []
    if len(act) == 1: return [(act[0][0], 1.0)]
    act.sort(key=lambda x: x[1])
    (s0, a0, b0), (s1, a1, b1) = act[-2], act[-1]
    k = fx.smooth((T - a1) / max(b0 - a1, 1e-3))
    return [(s0, 1 - k), (s1, k)]


def load_frame(seg, n):
    p = os.path.join(BB, 'render', seg, f'f_{n:05d}.jpg')
    if not os.path.exists(p):
        # nearest rendered frame (a segment may be missing a frame at its very edge)
        for d in (1, -1, 2, -2):
            q = os.path.join(BB, 'render', seg, f'f_{n + d:05d}.jpg')
            if os.path.exists(q): p = q; break
        else:
            return None
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255


# ------------------------------------------------------------------------------------------------ titles
def years(y):
    s = f'{int(round(y)):,}'.replace(',', ' ')
    return s


def hud(T):
    """(main, sub) of the HUD at T and its alpha"""
    def counter(t, a, b, y0, y1, fmt):
        k = min(max((t - a) / (b - a), 0), 1)
        return fmt(math.exp(math.log(y0) * (1 - k) + math.log(y1) * k))
    E = [
        (8.6, 31.6, lambda t: ('13 800 000 000 років тому', '')),
        (36.3, 43.5, lambda t: ('10⁻³⁶ секунди після початку', '')),
        (49.8, 60.3, lambda t: ('розтягнення: щонайменше ×10²⁶', '')),
        (80.5, 106.4, lambda t: ('0,000 001 секунди', '≈ 10 трлн °C')),
        (108.4, 114.3, lambda t: ('0,000 03 секунди', '≈ 2 трлн °C')),
        (114.6, 128.5, lambda t: ('3 хвилини', '≈ 1 млрд °C')),
        (130.1, 156.9, lambda t: ('380 000 років', '≈ 3000 °C')),
        (157.3, 163.3, lambda t: ('сьогодні', '−270 °C')),
        (195.9, 214.2, lambda t: (counter(t, 196.5, 213.5, 4e5, 1e8, lambda y: years(round(y, -3 if y < 1e6 else -5)) + ' років'), '')),
        (216.7, 239.2, lambda t: ('100–200 млн років', '')),
        (266.0, 293.2, lambda t: (counter(t, 266.5, 292.5, 1e9, 9e9, lambda y: f'{y / 1e9:.1f}'.replace('.', ',') + ' млрд років'), '')),
        (295.0, 306.0, lambda t: ('9,2 млрд років', '4,6 млрд років тому')),
        (334.5, 348.6, lambda t: ('сьогодні', '13,8 млрд років')),
        (349.0, 357.2, lambda t: ('через трильйони років', '')),
    ]
    for a, b, f in E:
        if a - 0.6 <= T <= b + 0.6:
            al = fx.smooth((T - (a - 0.6)) / 0.6) * (1 - fx.smooth((T - b) / 0.6))
            m, s = f(T)
            return m, s, al
    return None


CREDITS = [  # (t0, t1, text) — small, lower left, for the real images (full credits: posts.md / the description)
    (50.8, 51.8, 'Фото: A. Klepnev (CC BY 4.0)'),
    (51.9, 54.0, 'Фото: NASA, NASA/SDO'),
    (54.6, 60.0, 'Фото: ESO / S. Brunier'),
    (60.6, 70.5, 'Галактики: NASA, ESA, HUDF Team'),
    (71.0, 77.0, 'Фото: ESO (NGC 1232)'),
    (142.8, 146.0, 'Фото: Carlos Delgado (CC BY-SA 4.0)'),
    (163.4, 175.2, 'Фото: NASA'),
    (181.2, 197.0, 'Карта: ESA / Planck Collaboration'),
    (264.0, 275.6, 'Візуалізація: модель космічної павутини'),
    (276.0, 281.0, 'Фото: ESO / S. Brunier'),
    (281.0, 285.2, 'Фото: NASA, ESA, Hubble Heritage Team'),
    (285.4, 293.4, 'Фото: Lviatour (CC BY-SA 4.0)'),
    (293.6, 302.2, 'Фото: ESO'),
    (302.4, 305.4, 'Зображення: ALMA (ESO/NAOJ/NRAO)'),
    (305.6, 308.6, 'Фото: NASA'),
    (309.0, 318.4, 'Фото: B. Wetzel, H. Schaefer (NCI)'),
    (332.8, 337.0, 'Фото: NASA Earth Observatory'),
    (339.6, 343.4, 'Фото: NASA, ESA, HUDF Team'),
    (349.2, 357.4, 'Фото: NASA, ESA, Hubble Heritage (NGC 1132)'),
    (357.8, 362.0, 'Фото: ESO / S. Brunier'),
]
ART = [(0.0, 8.3), (21.6, 32.4)]          # «художня візуалізація» (the glowing haze: an artist's impression)
SUB = (25.0, 28.6)                         # the «Підписатися» button
END = 362.4                                # the end card
QUESTION = (fx.phrase('Яке космічне питання')[0] - 0.2, 371.5)

_font = {}


def font(path, size):
    if (path, size) not in _font: _font[(path, size)] = ImageFont.truetype(path, size)
    return _font[(path, size)]


_cache = {}


def layer(key, draw_fn):
    """an RGBA layer drawn once and cached (title states change rarely)"""
    if key not in _cache:
        if len(_cache) > 60: _cache.clear()
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(im))
        a = np.asarray(im).astype(np.float32) / 255
        _cache[key] = (a[..., :3], a[..., 3:])
    return _cache[key]


def over(img, key, fn, alpha):
    if alpha <= 0.003: return img
    rgb, a = layer(key, fn)
    a = a * alpha
    return img * (1 - a) + rgb * a


def subscribe_pill(d, cx, cy, scale=1.0):
    w, h = int(330 * scale), int(70 * scale)
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=h // 2, fill=(229, 45, 39, 235))
    d.text((cx, cy + 1), 'ПІДПИСАТИСЯ', font=font(fx.FONT_M, int(28 * scale)), fill=(255, 255, 255, 255), anchor='mm')


def titles(img, T):
    h = hud(T)
    if h:
        m, s, al = h
        img = over(img, ('hud', m, s), lambda d: (d.text((80, 64), m, font=font(fx.FONT_XL, 38), fill=(235, 240, 255, 225)),
                                                  d.text((82, 116), s, font=font(fx.FONT_L, 26), fill=(215, 222, 240, 190)) if s else None), al)
    for a, b, txt in CREDITS:
        if a - 0.5 <= T <= b + 0.5:
            al = fx.smooth((T - (a - 0.5)) / 0.5) * (1 - fx.smooth((T - b) / 0.5))
            img = over(img, ('cr', txt), lambda d: d.text((80, H - 56), txt, font=font(fx.FONT_L, 22), fill=(220, 225, 240, 150)), al)
    for a, b in ART:
        if a <= T <= b + 0.5:
            al = fx.smooth((T - a) / 0.5) * (1 - fx.smooth((T - b) / 0.5))
            img = over(img, ('art',), lambda d: d.text((W - 80, H - 56), 'художня візуалізація', font=font(fx.FONT_L, 22),
                                                    fill=(220, 225, 240, 150), anchor='ra'), al)
    if SUB[0] <= T <= SUB[1]:
        al = fx.smooth((T - SUB[0]) / 0.45) * (1 - fx.smooth((T - (SUB[1] - 0.45)) / 0.45))
        img = over(img, ('sub',), lambda d: subscribe_pill(d, W - 80 - 165, H - 130, 0.9), al)
    if T >= END:
        al = fx.smooth((T - END) / 1.2) * (1 - fx.smooth((T - (DUR - 1.2)) / 1.1))
        def card(d):
            d.text((W / 2, H / 2 - 150), 'Небозвід', font=font(fx.FONT_XL, 84), fill=(240, 244, 255, 240), anchor='mm')
            d.text((W / 2, H / 2 - 62), 'Не проґав наступне відео', font=font(fx.FONT_L, 34), fill=(225, 230, 245, 215), anchor='mm')
            subscribe_pill(d, W / 2, H / 2 + 30, 1.0)
            d.text((W / 2, H - 70), 'Зображення: NASA · ESA · CSA · STScI · ESO · ALMA (ESO/NAOJ/NRAO) · NASA/CXC/SAO · '
                                    'ESA/Planck Collaboration', font=font(fx.FONT_L, 20), fill=(210, 215, 235, 150), anchor='mm')
        img = over(img, ('end',), card, al)
    if QUESTION[0] <= T <= QUESTION[1] + 0.6:
        al = fx.smooth((T - QUESTION[0]) / 0.6) * (1 - fx.smooth((T - QUESTION[1]) / 0.6))
        img = over(img, ('q',), lambda d: d.text((W / 2, H / 2 + 130), 'Яке космічне питання розібрати наступним? Пиши в коментарях',
                                                 font=font(fx.FONT_L, 30), fill=(230, 235, 250, 220), anchor='mm'), al)
    return img


# ------------------------------------------------------------------------------------------------ audio
def mix_audio(out_wav):
    voice = os.path.join(BB, 'voice_tl.mp3')
    music = os.path.join(BB, 'music.wav')
    if not os.path.exists(music) and os.path.exists(os.path.join(BB, 'music.mp3')):
        music = os.path.join(BB, 'music.mp3')
    if os.path.exists(music):
        fc = ('[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.0,asplit=2[v][vk];'
              '[1:a]aresample=48000,volume=0.85[m];'
              '[m][vk]sidechaincompress=threshold=0.03:ratio=5:attack=40:release=600:makeup=1[md];'
              '[v][md]amix=inputs=2:duration=longest:normalize=0,'
              f'atrim=0:{DUR},loudnorm=I=-14:TP=-1.5:LRA=11[a]')
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', voice, '-i', music, '-filter_complex', fc, '-map', '[a]',
               '-ar', '48000', out_wav]
    else:
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', voice, '-af', f'pan=stereo|c0=c0|c1=c0,apad,atrim=0:{DUR},loudnorm=I=-14:TP=-1.5',
               '-ar', '48000', out_wav]
    subprocess.run(cmd, check=True)


def main():
    t_from = float(sys.argv[sys.argv.index('--from') + 1]) if '--from' in sys.argv else 0.0
    t_to = float(sys.argv[sys.argv.index('--to') + 1]) if '--to' in sys.argv else DUR
    ow, oh = (960, 540) if PREVIEW else (W, H)
    out = os.path.join(BB, 'test', 'preview.mp4') if PREVIEW else os.path.join(BB, '..', '..', '..', 'big_bang.mp4')
    out = os.path.abspath(out)
    wav = os.path.join(BB, 'render', 'final_audio.wav')
    mix_audio(wav)
    enc = ['-c:v', 'libx264', '-preset', 'veryfast' if PREVIEW else 'slow', '-crf', '24' if PREVIEW else '19',
           '-pix_fmt', 'yuv420p', '-tune', 'film'] + ([] if PREVIEW else ['-maxrate', '16M', '-bufsize', '32M'])
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{ow}x{oh}',
                          '-r', str(FPS), '-i', '-', '-ss', str(t_from), '-to', str(t_to), '-i', wav] + enc +
                         ['-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
    n0, n1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    missing = set()
    last = np.zeros((H, W, 3), np.float32)
    for n in range(n0, n1):
        T = n / FPS
        img = None
        for seg, wgt in sources(T):
            fr = load_frame(seg, n)
            if fr is None: missing.add(seg); continue
            img = fr * wgt if img is None else img + fr * wgt
        if img is None: img = last * 0.0
        last = img
        img = titles(img, T)
        u8 = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
        if PREVIEW: u8 = cv2.resize(u8, (ow, oh), interpolation=cv2.INTER_AREA)
        p.stdin.write(u8.tobytes())
        if n % 300 == 0: print(f'{T:7.1f} s', flush=True)
    p.stdin.close(); p.wait()
    print('done', out, 'missing:', sorted(missing))


if __name__ == '__main__':
    main()
