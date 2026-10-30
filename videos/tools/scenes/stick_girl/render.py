# Stick cartoon, the girl (~5 s): in her room, by a ring light, she bends over and films her behind on the phone,
# twerking — and the views, likes and comments go wild (the feed overlay, as in the toilet scene).
#   python3 scenes/stick_girl/render.py [t]   ->  videos/stick_girl.mp4   (with t: one still to work/stick_girl/)
import math, os, subprocess, sys
from PIL import Image

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, TOOLS)
from characters.stick import Canvas, Figure, POSES, ease, phone_side, floor, INK, PINK, SS
from characters.feed import draw_feed, _heart
from characters import viral

W, H, FPS, DUR = 1080, 1920, 30, 5.0
WORK = os.path.join(TOOLS, 'work', 'stick_girl')
OUT = os.path.join(TOOLS, '..', 'stick_girl.mp4')
GIRL = Figure(size=820, hair='ponytail', behind=1.8, accent=PINK)
BASE = dict(POSES['stand'], lean=-50, head=30, hL=4, kL=-16, hR=14, kR=-20, sL=70, eL=0, sR=-100, eR=10, face='grin', look=-0.6)
COMMENTS = [(-1.0, '@dima_k', 'ого 😳'), (-0.4, '@sasha', '🍑🍑🍑'), (0.3, '@max', 'богиня 😍'), (0.8, '@oleh', 'ще!!!'),
            (1.3, '@ira', 'де купити такі лосини?'), (1.7, '@bodya', '🔥🔥🔥'), (2.1, '@roman', 'підписався не думаючи'),
            (2.5, '@vika', 'ну ти даєш 😂'), (2.9, '@yura', 'ммм'), (3.3, '@taras', 'шедевр'), (3.7, '@ania', '🍑🔥'),
            (4.1, '@petro', 'рекомендації знають своє'), (4.5, '@lesia', 'аплодую 👏')]
HEARTS = viral.hearts(11, 60, -0.5, 4.8, 620, 1000)


def views_at(t):
    return viral.grow(t, 0.0, 4.4, 5_100_000, start=3000)


def ring_light(cv, c, r, t):
    """A ring light on a tripod: a glowing ring, the stand and three legs."""
    x, y = c
    cv.line([(x, y + r), (x, y + r + 520)], 8)
    for dx in (-90, 0, 90):
        cv.line([(x, y + r + 470), (x + dx, y + r + 600)], 7)
    glow = 0.5 + 0.5 * math.sin(t * 3)
    cv.circle(c, r + 14, w=10, col=(255, 236, 200))
    cv.circle(c, r, w=26, col=(255, 250, 235))
    cv.circle(c, r, w=6, col=INK)
    cv.circle(c, r - 26, w=6, col=INK)
    cv.circle(c, r + 26 + 6 * glow, w=3, col=(255, 220, 150))


def frame(i):
    t = i / FPS
    cv = Canvas(W, H)
    # the room: a pink wall with a heart poster, the floor, a rug, the ring light
    cv.rrect((-20, -20, W + 20, 1250), 0, fill=(255, 240, 244))
    cv.rrect((-20, 1250, W + 20, H + 20), 0, fill=(246, 239, 235))
    floor(cv, 1250)
    cv.ellipse((160, 1215, 860, 1300), fill=(250, 200, 214), col=INK, w=5)
    cv.rrect((640, 260, 860, 520), 10, fill=(255, 255, 255), col=INK, w=6)
    _heart(cv, (750, 395), 120, (254, 44, 85))
    ring_light(cv, (180, 520), 120, t)
    # the girl: twerking — the hips bob fast, knees bend, the behind bounces; the phone stays up
    bob = abs(math.sin(t * 13))
    pose = dict(BASE)
    pose['kL'] = -16 - 18 * bob
    pose['kR'] = -20 - 18 * bob
    pose['lean'] = -50 - 6 * bob
    pose['head'] = 30 + 4 * math.sin(t * 6)
    pose['face'] = 'grin' if int(t * 4) % 4 else 'o'
    pose['t'] = t
    GIRL.behind = 1.8 + 0.12 * bob
    GIRL.draw(cv, pose, (470, 960 + 22 * bob), held=lambda c, h, a: phone_side(c, h, 2.6, face=1))
    viral.draw_hearts(cv, t, HEARTS, _heart, y0=1300)
    v = views_at(t)
    stats = dict(views=v, pop=viral.milestone_pop(views_at, t, DUR), likes=viral.grow(t, 0.0, 4.5, 812_000),
                 comments=viral.grow(t, 0.0, 4.5, 47_300), saves=viral.grow(t, 0.0, 4.5, 133_000), shares=viral.grow(t, 0.0, 4.5, 96_400))
    draw_feed(cv, t, stats, user='@nastya.fit', caption='ранкова розминка 🍑 #рек #топ', comments=COMMENTS,
              liked=True, progress=t / DUR, avatar=3)
    return cv.image()


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    if len(sys.argv) > 1:
        frame(int(float(sys.argv[1]) * FPS)).save(os.path.join(WORK, f'still_{sys.argv[1]}.png')); sys.exit()
    for i in range(int(DUR * FPS)):
        frame(i).save(os.path.join(WORK, f'f_{i:04d}.png'))
    snd = viral.sound(os.path.join(WORK, 'sound.wav'), DUR, [c[0] for c in COMMENTS], views_at)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(WORK, 'f_%04d.png'), '-i', snd,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', OUT], check=True)
    print('done:', OUT)
