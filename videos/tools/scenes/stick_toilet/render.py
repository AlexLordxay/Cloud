# Stick cartoon, scene 1 (~6 s): a guy on the toilet films himself, and the views, likes and comments go wild.
#   python3 scenes/stick_toilet/render.py   ->  videos/stick_toilet.mp4
# Characters and props: characters/stick.py. Sound: soft pops for the comments and a rising "whoosh" (numpy).
import math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, TOOLS)
from characters.feed import draw_feed, _heart as fheart
from characters.stick import Canvas, Figure, POSES, lerp_pose, ease, phone_side, toilet, tiles, floor, window, lamp, washer, paper_roll, INK, PINK, SS

W, H, FPS, DUR = 1080, 1920, 30, 6.0
WORK = os.path.join(TOOLS, 'work', 'stick_toilet')
OUT = os.path.join(TOOLS, '..', 'stick_toilet.mp4')
FONT = os.path.join(TOOLS, 'fonts', 'Commissioner.ttf')
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
RED = (235, 64, 80)


def font(size, wght=700):
    f = ImageFont.truetype(FONT, size * SS)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


F_BIG, F_MID, F_CMT = font(64), font(40, 600), font(34, 500)
_EMO = {}


def emoji(ch, px):
    """A colour emoji as an RGBA image px high (Noto draws them at 109 px; scaled)."""
    k = (ch, px)
    if k not in _EMO:
        f = ImageFont.truetype(EMOJI, 109)
        im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=f, embedded_color=True, anchor='mm')
        im = im.crop(im.getbbox())
        _EMO[k] = im.resize((int(im.width * px * SS / im.height), px * SS), Image.LANCZOS)
    return _EMO[k]


def fmt(n):
    if n >= 1e6: return f'{n / 1e6:.1f}M'.replace('.0M', 'M')
    if n >= 1e3: return f'{n / 1e3:.1f}K'.replace('.0K', 'K')
    return str(int(n))


def grow(t, t0, t1, top, start=None):
    """A counter racing up on a log scale from `start` (default top/2000) to `top` between t0 and t1 — busy from frame 0."""
    x = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    a = math.log10(start or top / 2000)
    return 10 ** (a + (math.log10(top) - a) * x ** 1.15)


MILESTONES = [10_000, 100_000, 1_000_000]

# the free (left) arm: (time, shoulder, elbow, wiggle) — between keys the angles ease; `wiggle` swings the forearm a
# little (a wave) so the hand is never frozen
ARM_KEYS = [(0.0, 135, 25, 24), (1.4, 135, 25, 24), (1.9, 100, 75, 6), (3.1, 100, 75, 6), (3.6, 160, -60, 30), (4.8, 160, -60, 30)]


def arm_at(t):
    keys = ARM_KEYS
    if t <= keys[0][0]: k0 = k1 = keys[0]; u = 0
    elif t >= keys[-1][0]: k0 = k1 = keys[-1]; u = 0
    else:
        j = max(i for i, k in enumerate(keys) if k[0] <= t)
        k0, k1 = keys[j], keys[j + 1]
        u = ease((t - k0[0]) / (k1[0] - k0[0]))
    s = k0[1] + (k1[1] - k0[1]) * u
    e = k0[2] + (k1[2] - k0[2]) * u
    wig = k0[3] + (k1[3] - k0[3]) * u
    return s + 0.3 * wig * math.sin(t * 9), e + wig * math.sin(t * 9)


def views_at(t):
    return grow(t, 0.0, 5.2, 2_400_000, start=1200)


def milestone_pop(t):
    """0..1 bump just after the views pass 10K, 100K, 1M."""
    best = 0.0
    for m in MILESTONES:
        lo, hi = 0.0, 5.2                                        # when were they passed (bisection)
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if views_at(mid) < m else (lo, mid)
        age = t - hi
        if 0 <= age < 0.35: best = max(best, math.sin(age / 0.35 * math.pi))
    return best


GUY = Figure(size=900)
COMMENTS = [(-1.0, 'де ти це знімаєш 😂'), (-0.5, 'ору'), (0.2, 'ахахах 😂'), (0.8, 'ЛЕГЕНДА'), (1.4, 'ще!!! 🔥'), (2.0, 'лайк не дивлячись'), (2.6, 'хто тут з туалету? 🚽'),
            (3.1, 'шедевр 😍'), (3.5, 'ору 🤣🤣'), (3.85, 'підписався!'), (4.1, '🔥🔥🔥'), (4.35, 'король контенту 👑'),
            (4.6, 'ахахах'), (4.8, 'ще одне!!'), (5.0, '😂😂😂')]
FEED_COMMENTS = [(t0, n, x) for (t0, x), n in zip(COMMENTS, ['@ira_k', '@maks.ua', '@sonechko', '@den4ik', '@olya.v', '@taras_1',
    '@nastya', '@vovan', '@kateryna', '@bodya', '@lilu', '@ostap', '@marta.m', '@yulia', '@petro'])]
random.seed(3)
HEARTS = [(random.uniform(-0.5, 5.8), random.uniform(640, 1020), random.uniform(0.8, 1.3)) for _ in range(46)]


def heart(cv, c, s, col=RED):
    x, y = c
    r = s * 0.3
    cv.circle((x - r, y - r * 0.3), r, col=col)
    cv.circle((x + r, y - r * 0.3), r, col=col)
    cv.poly([(x - 2 * r, y - r * 0.05), (x + 2 * r, y - r * 0.05), (x, y + s * 0.62)], fill=col)


def eye(cv, c, s):
    x, y = c
    cv.ellipse((x - s * 0.6, y - s * 0.35, x + s * 0.6, y + s * 0.35), col=INK, w=s * 0.1)
    cv.circle((x, y), s * 0.17, col=INK)


def bubble_icon(cv, c, s):
    x, y = c
    cv.rrect((x - s * 0.55, y - s * 0.4, x + s * 0.55, y + s * 0.3), s * 0.18, col=INK, w=s * 0.1)
    cv.poly([(x - s * 0.25, y + s * 0.25), (x - s * 0.05, y + s * 0.25), (x - s * 0.35, y + s * 0.55)], fill=INK)


def text_with_emoji(cv, xy, s, f, fill=INK):
    """Text left-aligned at xy (middle height); emoji drawn as images."""
    x, y = xy[0] * SS, xy[1] * SS
    for part in s.split(' '):
        if part and ord(part[0]) > 0x2500:
            for ch in part:
                im = emoji(ch, 36)
                cv.img.paste(im, (int(x), int(y - im.height / 2)), im)
                x += im.width + 4 * SS
        else:
            cv.d.text((x, y), part, font=f, fill=fill, anchor='lm')
            x += cv.d.textlength(part, font=f)
        x += cv.d.textlength(' ', font=f)


def frame(i):
    t = i / FPS
    cv = Canvas(W, H)
    # the bathroom: tiled wall, floor, the toilet (the lower part of the frame is the feed's: author, comments)
    tiles(cv, 0, 1340)
    cv.rrect((-20, 1340, W + 20, H + 20), 0, fill=(246, 247, 250))
    floor(cv, 1340)
    seat = (400, 1080)
    window(cv, (70, 300, 330, 560), t)
    lamp(cv, 700, 370, 1.1, t)
    washer(cv, (640, 1000, 900, 1335), t)
    paper_roll(cv, (720, 860), 0.9)
    toilet(cv, seat, 2.1)
    # the guy: films himself and talks, bouncing more and more as the numbers climb. The free hand goes smoothly through
    # a few gestures (keyframes, eased): a wave, a thumbs-up to the camera, a fist pump; at the end — both arms up
    hype = min(1.0, t / 4.0)
    bounce = abs(math.sin(t * (6 + 6 * hype))) * (6 + 22 * hype)
    pose = dict(POSES['sit_phone'])
    pose['lean'] = -6 + 6 * math.sin(t * 3.4)
    pose['head'] = 9 * math.sin(t * 5.1)
    pose['face'] = 'o' if (int(t * 7) % 3 == 0) else 'grin'
    pose['look'] = -0.7
    sL, eL = arm_at(t)
    pose['sL'], pose['eL'] = sL, eL
    if t > 4.8:                                                  # victory: both arms up, the phone too
        v = ease((t - 4.8) / 0.3)
        pose = lerp_pose(pose, dict(pose, sL=138, eL=12, sR=-138, eR=-12, face='grin', look=0, head=0, lean=0), v)
    GUY.draw(cv, pose, (seat[0] + 36, seat[1] - 26 - bounce), held=lambda c, h, a: phone_side(c, h, 2.8, face=1))
    # hearts floating up the right side, like a live stream
    for (t0, x, sc) in HEARTS:
        age = t - t0
        if 0 <= age < 1.6:
            y = 1400 - age * 650
            fheart(cv, (x - 60 + 30 * math.sin(age * 5 + x), y), 52 * sc * (1 - age / 2.2), RED if int(x) % 3 else PINK)
    stats = dict(views=views_at(t), pop=milestone_pop(t), likes=grow(t, 0.0, 5.3, 418_000), comments=grow(t, 0.0, 5.3, 31_200),
                 saves=grow(t, 0.0, 5.3, 52_700), shares=grow(t, 0.0, 5.3, 88_100))
    draw_feed(cv, t, stats, user='@korol_unitazu', caption='день з життя легенди 🚽 #рек #топ', comments=FEED_COMMENTS,
              liked=True, progress=t / DUR, avatar=0)
    # fade in / out at the edges
    return cv.image()                                           # no fades: the first frame is the hook, the end cuts


def sound():
    """Pops for the comments, a soft whoosh that rises with the numbers."""
    sr = 44100
    n = int(DUR * sr)
    y = np.zeros(n)
    tt = np.arange(n) / sr
    for t0, _ in COMMENTS:
        if t0 < 0: continue
        k = int(t0 * sr)
        m = int(0.08 * sr)
        e = np.exp(-np.arange(m) / (0.012 * sr))
        y[k:k + m] += 0.35 * e * np.sin(2 * np.pi * (900 + 600 * random.random()) * np.arange(m) / sr)
    for m in MILESTONES:                                         # a bright "ding" when the views pass 10K, 100K, 1M
        lo, hi = 0.0, 5.2
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if views_at(mid) < m else (lo, mid)
        k = int(hi * sr); m2 = int(0.6 * sr)
        tt2 = np.arange(m2) / sr
        y[k:k + m2] += 0.5 * np.exp(-tt2 / 0.18) * (np.sin(2 * np.pi * 1318 * tt2) + 0.5 * np.sin(2 * np.pi * 1976 * tt2))
    rng = np.random.default_rng(1)
    noise = np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode='same')
    y += 0.12 * noise * np.clip((tt + 0.5) / 5.0, 0, 1) ** 2
    y = y / max(1e-6, np.abs(y).max()) * 0.7
    from scipy.io import wavfile
    path = os.path.join(WORK, 'sound.wav')
    wavfile.write(path, sr, (np.stack([y, y], 1) * 32767).astype(np.int16))
    return path


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only:                                                     # a still: python3 render.py 3.5
        frame(int(float(only) * FPS)).save(os.path.join(WORK, f'still_{only}.png')); sys.exit()
    for i in range(int(DUR * FPS)):
        frame(i).save(os.path.join(WORK, f'f_{i:04d}.png'))
    snd = sound()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(WORK, 'f_%04d.png'), '-i', snd,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', OUT], check=True)
    print('done:', OUT)
