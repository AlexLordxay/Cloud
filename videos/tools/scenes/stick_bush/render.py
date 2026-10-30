# Stick cartoon, the bush (~6.2 s): a guy rides in on a bike, drops it, dives behind a bush (only his head shows —
# strain, then relief), steps out, looks down at the 💩 and films it — and the views, likes and comments go wild.
#   python3 scenes/stick_bush/render.py [t]   ->  videos/stick_bush.mp4   (with t: one still to work/stick_bush/)
import math, os, subprocess, sys
from PIL import Image

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, TOOLS)
from characters.stick import Canvas, Figure, POSES, ease, lerp_pose, phone_side, INK, SS
from characters.feed import draw_feed, _heart, emoji
from characters import viral

W, H, FPS, DUR = 1080, 1920, 30, 6.2
WORK = os.path.join(TOOLS, 'work', 'stick_bush')
OUT = os.path.join(TOOLS, '..', 'stick_bush.mp4')
GROUND = 1330
GUY = Figure(size=900, hair='', accent=(90, 90, 90))
BS = 1.35                                                     # the bike's scale
T_PARK, T_BUSH, T_OUT, T_FILM = 1.0, 1.5, 2.4, 2.8            # parked; behind the bush; steps out; films
BUSH = (60, 470)                                               # the bush's x range
POOP = (540, GROUND - 6)
COMMENTS = [(T_FILM + 0.15, '@vlad', 'ахахахах 💀'), (T_FILM + 0.55, '@olia', 'я не можу 😂😂'), (T_FILM + 0.9, '@stas', 'ЛЕГЕНДА'),
            (T_FILM + 1.25, '@marta', 'це мистецтво'), (T_FILM + 1.6, '@denys', '💩💩💩'), (T_FILM + 1.9, '@ira', 'на рекомендаціях!!'),
            (T_FILM + 2.2, '@kostia', 'підписався'), (T_FILM + 2.5, '@nina', 'ору 🤣'), (T_FILM + 2.8, '@yarik', 'шедевр 👑'),
            (T_FILM + 3.1, '@oksana', 'ще одне!!')]
HEARTS = viral.hearts(21, 50, T_FILM, DUR - 0.2, 780, 960)


def views_at(t):
    return viral.grow(t, T_FILM, DUR - 0.4, 8_400_000, start=2000) if t >= T_FILM else 0


def bike(cv, bx, t, moving):
    """A bicycle; bx = the middle between the wheels; the wheels' spokes turn while it moves."""
    r, y = 70 * BS, GROUND - 70 * BS
    ang = (bx / r) if moving else 0
    for wx in (bx - 95 * BS, bx + 95 * BS):
        cv.circle((wx, y), r, w=8, col=INK)
        for k in range(3):
            a = ang + k * math.pi / 3
            cv.line([(wx - math.cos(a) * r, y - math.sin(a) * r), (wx + math.cos(a) * r, y + math.sin(a) * r)], 3, (120, 124, 134))
    seat, bar, crank = (bx + 35 * BS, y - 120 * BS), (bx - 70 * BS, y - 150 * BS), (bx, y)        # facing left
    col = (230, 80, 70)
    for a_, b_ in ((bx + 95 * BS, y), (seat[0], seat[1] + 10)), ((bx + 95 * BS, y), crank), (crank, (seat[0], seat[1] + 10)), \
                  ((seat[0], seat[1] + 10), (bar[0] + 10, bar[1] + 30)), (crank, (bar[0] + 10, bar[1] + 30)), ((bar[0] + 10, bar[1] + 30), (bx - 95 * BS, y)):
        cv.line([a_, b_], 9, col)
    cv.line([(bar[0] + 10, bar[1] + 30), bar], 7)
    cv.line([(bar[0] + 18, bar[1]), (bar[0] - 22, bar[1] - 6)], 8)
    cv.rrect((seat[0] - 26, seat[1] - 6, seat[0] + 30, seat[1] + 8), 6, fill=INK)
    return seat, bar, crank


def bush(cv, x0, x1, shake=0.0):
    """A round bush of overlapping leafy blobs."""
    cx = (x0 + x1) / 2
    blobs = [(-0.38, 0.02, 0.32), (0.0, -0.12, 0.38), (0.36, 0.0, 0.33), (-0.15, 0.12, 0.3), (0.2, 0.14, 0.3)]
    w = x1 - x0
    for dx, dy, r in blobs:
        cv.circle((cx + dx * w + shake * math.sin(dx * 9), GROUND - 150 + dy * w), r * w, fill=(96, 170, 90), col=(96, 170, 90))
    for dx, dy, r in blobs:
        cv.circle((cx + dx * w + shake * math.sin(dx * 9), GROUND - 150 + dy * w), r * w, w=7, col=INK)
    for dx, dy, r in blobs:                                   # fill again, so the inner outlines vanish
        cv.circle((cx + dx * w + shake * math.sin(dx * 9), GROUND - 150 + dy * w), r * w - 7, fill=(96, 170, 90), col=(96, 170, 90))
    for k in range(7):
        lx, ly = cx - w * 0.35 + k * w * 0.11, GROUND - 190 + (k % 3) * 40
        cv.arc((lx - 14, ly - 8, lx + 14, ly + 14), 200, 340, 4, (60, 120, 60))


def scenery(cv, t):
    cv.rrect((-20, -20, W + 20, GROUND), 0, fill=(206, 232, 255))
    cv.circle((160, 300), 80, col=(255, 210, 80))
    for k, (cx, cy) in enumerate(((200, 420), (620, 300))):
        cx += (t * 12) % 60
        for dx, dy, r in ((0, 0, 40), (40, -16, 48), (86, 4, 36)):
            cv.circle((cx + dx, cy + dy), r, col=(255, 255, 255))
    cv.rrect((-20, GROUND, W + 20, H + 20), 0, fill=(150, 205, 120))
    cv.line([(-20, GROUND), (W + 20, GROUND)], 6)
    cv.rrect((-20, GROUND + 70, W + 20, GROUND + 190), 0, fill=(205, 205, 210))          # the road
    for k in range(7):
        cv.rrect((k * 180 - 40, GROUND + 124, k * 180 + 60, GROUND + 136), 4, fill=(255, 255, 255))
    for x in (80, 1010):                                                                  # a few tufts of grass
        for k in range(3):
            cv.line([(x + k * 14, GROUND), (x + k * 14 - 6, GROUND - 24)], 4, (70, 140, 70))


def frame(i):
    t = i / FPS
    cv = Canvas(W, H)
    scenery(cv, t)
    # the bike: rides in, then stands parked
    bx = 1000 + (830 - 1000) * ease(min(1.0, t / T_PARK))   # rides in from the right, already in frame on the first frame
    seat, bar, crank = bike(cv, bx, t, t < T_PARK)
    pose = dict(POSES['stand'], look=0.6, face='smile')
    if t < T_PARK:                                            # pedalling
        a = t * 14
        pose.update(hL=-78 - 18 * math.sin(a), kL=105 - 28 * math.cos(a), hR=-78 + 18 * math.sin(a), kR=105 + 28 * math.cos(a),
                    lean=18, sL=-60, eL=-10, sR=-66, eR=-6, face='smile', look=-0.8)       # facing left
        at = (seat[0], seat[1] - 6)
        GUY.draw(cv, pose, at)
    elif t < T_BUSH:                                          # running to the bush
        u = ease((t - T_PARK) / (T_BUSH - T_PARK))
        a = t * 20
        pose.update(hL=30 * math.sin(a), kL=20 + 20 * max(0, math.sin(a)), hR=-30 * math.sin(a), kR=20 + 20 * max(0, -math.sin(a)),
                    lean=12, sL=-40 * math.sin(a), eL=40, sR=40 * math.sin(a), eR=40, face='o', look=-0.8)   # running left
        at = (760 + (265 - 760) * u, GROUND - 0.42 * GUY.size - 8 * abs(math.sin(a)))
        GUY.draw(cv, pose, at)
    elif t < T_OUT:                                           # behind the bush: squatting, only the head shows
        s = t - T_BUSH
        pose.update(hL=95, kL=-160, hR=100, kR=-165, lean=6, sL=40, eL=60, sR=50, eR=60,
                    face='o' if s < 0.5 else 'smile', look=0.0, head=6 * math.sin(s * 30) if s < 0.5 else 0)
        GUY.draw(cv, pose, (265, GROUND - 0.42 * GUY.size + 210))
    else:                                                     # out, to the right of the bush; looks down at it and films
        u = ease((t - T_OUT) / 0.35)
        x = 265 + (690 - 265) * u
        pose.update(lean=10 * u, head=24 * u, look=-0.8, face='grin' if t > T_FILM else 'o')   # bends towards the 💩
        if t >= T_FILM - 0.3:
            k = ease((t - T_FILM + 0.3) / 0.3)
            pose.update(sR=-60 * k + 20 * (1 - k), eR=-30 * k, sL=25, eL=10)
        GUY.draw(cv, pose, (x, GROUND - 0.42 * GUY.size - 4),
                 held=(lambda c, h, a: phone_side(c, h, 2.2, face=1)) if t >= T_FILM - 0.3 else None)
    bush(cv, *BUSH, shake=6 * math.sin(t * 40) if T_BUSH <= t < T_BUSH + 0.6 else 0)
    if t >= T_OUT:                                            # the 💩, with a couple of flies
        im = emoji('💩', 96)
        cv.img.paste(im, (int((POOP[0] - im.width / SS / 2) * SS), int((POOP[1] - 96) * SS)), im)
        for k in range(2):
            a = t * 9 + k * 3
            fx, fy = POOP[0] + 50 * math.cos(a), POOP[1] - 110 + 22 * math.sin(a * 1.7)
            cv.circle((fx, fy), 6, col=INK)
            cv.ellipse((fx - 12, fy - 12, fx, fy - 2), fill=(220, 230, 245), col=INK, w=2)
            cv.ellipse((fx, fy - 12, fx + 12, fy - 2), fill=(220, 230, 245), col=INK, w=2)
    if t >= T_FILM:                                           # the feed: only once he is filming
        viral.draw_hearts(cv, t, HEARTS, _heart, y0=1350)
        stats = dict(views=views_at(t), pop=viral.milestone_pop(views_at, t, DUR), likes=viral.grow(t, T_FILM, DUR - 0.3, 1_200_000),
                     comments=viral.grow(t, T_FILM, DUR - 0.3, 88_000), saves=viral.grow(t, T_FILM, DUR - 0.3, 41_000),
                     shares=viral.grow(t, T_FILM, DUR - 0.3, 260_000))
        draw_feed(cv, t, stats, user='@pryroda_kliche', caption='природа кличе 🌳💩 #рек', comments=COMMENTS,
                  liked=True, progress=(t - T_FILM) / (DUR - T_FILM), avatar=1)
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
