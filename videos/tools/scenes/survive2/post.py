# Finishes «Скільки ти протримаєшся на кожній планеті?» v2: the frames (render.js, 720×1280) brought up to 1080×1920
# with the titles (spec.py): the world and its conditions, a stopwatch that races to the estimate and stops red (he did
# not make it) or green (he lives), the hook's question, Jupiter's «зв'язок втрачено» over static, the closing question;
# then the sound: the voice (placed by timeline.py, NOT sped up) over the organ (music.js, ducked under the voice) and
# the effects (sfx.py full), at -14 LUFS.
#   python3 scenes/survive2/post.py         ->  videos/survive2.mp4
#   python3 scenes/survive2/post.py sound   ->  the same with the titled frames kept (only the sound redone)
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spec

TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
WORK = os.path.join(TOOLS, 'work', 'survive2')
VIDEOS = os.path.abspath(os.path.join(TOOLS, '..'))
FF = __import__('imageio_ffmpeg').get_ffmpeg_exe()
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
W, H, FPS, DUR = 1080, 1920, 30, TL['dur']
FONT = os.path.join(TOOLS, 'fonts', 'Unbounded.ttf')
FONT2 = os.path.join(TOOLS, 'fonts', 'Commissioner.ttf')
_fonts = {}


def font(f, s):
    if (f, s) not in _fonts: _fonts[(f, s)] = ImageFont.truetype(f, s)
    return _fonts[(f, s)]


def text_layer(lines, f, size, y, color=(255, 255, 255), spacing=1.15, alpha=255, mono=False):
    """Centred lines with a soft dark halo, as an RGBA layer (mono: each character in a fixed cell, for the stopwatch)."""
    fo = font(f, size)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('L', (W, H), 0); ds = ImageDraw.Draw(sh)
    for k, line in enumerate(lines):
        yy = y + k * size * spacing
        if mono:
            cell = d.textlength('0', font=fo) * 1.02; colon = cell * 0.55
            ws = [colon if c == ':' else cell for c in line]; x = (W - sum(ws)) / 2
            for c, w in zip(line, ws):
                cx = x + (w - d.textlength(c, font=fo)) / 2
                d.text((cx, yy), c, font=fo, fill=color + (alpha,)); ds.text((cx, yy), c, font=fo, stroke_width=max(2, size // 12), fill=220)
                x += w
        else:
            w = d.textlength(line, font=fo); x = (W - w) / 2
            d.text((x, yy), line, font=fo, fill=color + (alpha,)); ds.text((x, yy), line, font=fo, stroke_width=max(2, size // 14), fill=210)
    halo = sh.filter(ImageFilter.GaussianBlur(size * 0.2))
    base = Image.new('RGBA', (W, H), (0, 0, 0, 0)); base.putalpha(halo.point(lambda v: int(v * 0.85)))
    return Image.alpha_composite(base, lay)


def fade(lay, k):
    if k >= 1: return lay
    l = lay.copy(); l.putalpha(l.getchannel('A').point(lambda a: int(a * max(0.0, k)))); return l


def static(seed, k):
    rng = np.random.default_rng(seed)
    n = rng.integers(0, 255, (H // 4, W // 4), dtype=np.uint8)
    lines = (np.sin(np.arange(H // 4) * 0.9 + seed) * 40).astype(np.int16)[:, None]
    n = np.clip(n.astype(np.int16) + lines, 0, 255).astype(np.uint8)
    im = Image.fromarray(n).resize((W, H), Image.NEAREST).convert('RGBA')
    im.putalpha(int(255 * k)); return im


_L = {}


def layers():
    if _L: return _L
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sa = np.zeros((H, W), np.uint8)
    sa[:700] = (np.clip(1 - np.arange(700) / 700.0, 0, 1) ** 1.5 * 110)[:, None].astype(np.uint8); shade.putalpha(Image.fromarray(sa))
    _L.update(shade=shade,
              names={w: text_layer([nm], FONT, 58, 150) for w, (nm, _) in spec.NAMES.items()},
              conds={w: text_layer([c], FONT2, 40, 236, alpha=235) for w, (_, c) in spec.NAMES.items() if c},
              labels={w: text_layer([v[4]], FONT2, 40, 444, color=v[3]) for w, v in spec.TIMERS.items() if v[4]},
              hook=text_layer(spec.HOOK[1].split('\n'), FONT, 60, 1180, spacing=1.25),
              lost=text_layer(['ЗВ\'ЯЗОК ВТРАЧЕНО'], FONT, 60, 900, color=(255, 90, 70)),
              earth_line=text_layer([spec.EARTH_LINE[1]], FONT, 64, 330, color=spec.GREEN),
              q1=text_layer(spec.QUESTION[1].split('\n'), FONT, 64, 1080, spacing=1.25), q2=text_layer([spec.QUESTION[2]], FONT2, 46, 1290),
              note=text_layer([spec.NOTE], FONT2, 28, 1500, alpha=200),
              credits={w: text_layer([c], FONT2, 26, 1540, alpha=200) for w, c in spec.CREDITS.items()}, cache={})
    return _L


def titled(im, t, f):
    L = layers()
    shot = next(s for s in TL['shots'] if s['t0'] <= t < s['t1'] or s is TL['shots'][-1])
    w, lt = shot['world'], t - shot['t0']
    im = im.convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
    im = Image.alpha_composite(im, L['shade'])
    k = min(1.0, lt / 0.25)
    if w == 'jupiter' and lt > spec.LOST:            # the signal is gone: static, the line
        kk = min(1.0, (lt - spec.LOST) / 0.12)
        im = Image.alpha_composite(im, static(f, 0.85 * kk))
        im = Image.alpha_composite(im, fade(L['lost'], kk))
    im = Image.alpha_composite(im, fade(L['names'][w], k))
    if w in L['conds']: im = Image.alpha_composite(im, fade(L['conds'][w], k))
    if w in spec.TIMERS:
        a, b, v, col, _ = spec.TIMERS[w]
        stopped = lt >= b
        val = v if stopped else math.floor(spec.timer_value(w, lt))
        blink = w == 'sun' and int(lt * 4) % 2 == 1
        c = col if stopped else (255, 255, 255)
        key = (spec.fmt(val), c)
        if key not in L['cache']: L['cache'][key] = text_layer([key[0]], FONT, 104, 300, color=c, mono=True)
        if not blink: im = Image.alpha_composite(im, fade(L['cache'][key], k))
        if stopped and w in L['labels']: im = Image.alpha_composite(im, fade(L['labels'][w], (lt - b) / 0.3))
    if w == 'earth' and lt > spec.EARTH_LINE[0]: im = Image.alpha_composite(im, fade(L['earth_line'], (lt - spec.EARTH_LINE[0]) / 0.4))
    if w == 'venus_hook' and lt > spec.HOOK[0]: im = Image.alpha_composite(im, fade(L['hook'], (lt - spec.HOOK[0]) / 0.3))
    if w == 'earth' and lt > spec.QUESTION[0]:
        kq = (lt - spec.QUESTION[0]) / 0.4
        im = Image.alpha_composite(im, fade(L['q1'], kq)); im = Image.alpha_composite(im, fade(L['q2'], kq - 0.5))
    if w != 'earth' and not (w == 'venus_hook' and lt >= spec.HOOK[0]): im = Image.alpha_composite(im, L['note'])
    if w in L['credits']: im = Image.alpha_composite(im, L['credits'][w])
    return im.convert('RGB')


def frames():
    src = os.path.join(WORK, 'frames'); out = os.path.join(WORK, 'out'); os.makedirs(out, exist_ok=True)
    n = int(round(DUR * FPS))
    for f in range(n):
        titled(Image.open(os.path.join(src, f'f_{f:05d}.jpg')), f / FPS, f).save(os.path.join(out, f'f_{f:05d}.jpg'), quality=93)
        if f % 300 == 0: print('titles', f, '/', n, flush=True)


def encode():
    out = os.path.join(VIDEOS, 'survive2.mp4')
    mix = ('[1:a]volume=2.6[m];[0:a]asplit=2[v][sc];[m][sc]sidechaincompress=threshold=0.04:ratio=4:attack=60:release=700[md];'
           '[2:a]volume=0.36[fx];[md][v][fx]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st=%.2f:d=1.0[a]' % (DUR - 1.0))
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', os.path.join(WORK, 'voice.wav'), '-i', os.path.join(WORK, 'music.wav'),
                    '-i', os.path.join(WORK, 'sfx_full.wav'), '-framerate', str(FPS), '-i', os.path.join(WORK, 'out', 'f_%05d.jpg'),
                    '-filter_complex', mix, '-map', '3:v', '-map', '[a]', '-t', f'{DUR:.2f}',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                    '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-movflags', '+faststart', out], check=True)
    print('written', out)


if __name__ == '__main__':
    if sys.argv[1:2] == ['test']:                     # titles over the stills: post.py test 2.8 17 …
        for a in sys.argv[2:]:
            titled(Image.open(os.path.join(WORK, f'still_{a}.jpg')), float(a), 0).save(os.path.join(WORK, f'titled_{a}.jpg'), quality=90)
        sys.exit()
    if 'sound' not in sys.argv[1:]: frames()
    encode()
