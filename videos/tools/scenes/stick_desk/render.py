# Stick cartoon, our hero (dreadlocks, a beard) at the desk, in two parts (the author, 30.10):
#   A (~4 s): days and nights fly by in the window, the clock spins, mugs pile up; he edits — frames of his real videos
#             jump on the monitor. He does not publish yet.          -> videos/stick_desk_a.mp4
#   C (~3.2 s): between the girl and the bush — still editing, days 2–3, more mugs, more tired. -> videos/stick_desk_c.mp4
#   B (~8.4 s): still working (days 3–4); at last he wipes his forehead («фух»), his eyes turn to stars, «Опублікувати»…
#             his video plays (the Moon hitting the Earth), and the views crawl: 0… 1… 3. A cricket. The smile slides off.
#                                                                      -> videos/stick_desk_b.mp4
#   python3 scenes/stick_desk/render.py a|b [t]     (with t: one still to work/stick_desk/)
# Frames on the monitor: work/stick_desk/clip (moonfall_music.mp4 32.6–36.8 s) and work/stick_desk/thumbs (12 stills
# from the videos) — made with ffmpeg, see HANDOFF.
import math, os, subprocess, sys
import numpy as np
from PIL import Image

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, TOOLS)
from characters.stick import (Canvas, Figure, POSES, lerp_pose, ease, tiles, floor, window, curtains, wall_clock,
                              office_chair, mug, lamp, INK, SS)
from characters.feed import font, fmt, _eye, _heart, RED, MUTED

W, H, FPS = 1080, 1920, 30
PART = (sys.argv[1] if len(sys.argv) > 1 else 'a').lower()
WORK = os.path.join(TOOLS, 'work', 'stick_desk')
OUT = os.path.join(TOOLS, '..', f'stick_desk_{PART}.mp4')
# the timeline of each part: work until T_WORK, then (B) wipe, stars, the button, the video
# MUGS: (mugs at the start, at the end of the work); TIRED: his face while working (more tired part by part)
if PART == 'a':
    DUR, T_WORK, T_WIPE, T_STAR, T_PUB, T_PLAY, DAY0, DAYS, MUGS, TIRED = 4.0, 4.0, 99, 99, 99, 99, 0.0, 1.5, (0, 4), 0
elif PART == 'c':                                         # between the girl and the bush: still at it (the author, 30.10)
    DUR, T_WORK, T_WIPE, T_STAR, T_PUB, T_PLAY, DAY0, DAYS, MUGS, TIRED = 3.2, 3.2, 99, 99, 99, 99, 1.5, 1.0, (4, 7), 1
else:
    DUR, T_WORK, T_WIPE, T_STAR, T_PUB, T_PLAY, DAY0, DAYS, MUGS, TIRED = 8.4, 1.8, 1.8, 2.6, 3.2, 4.1, 2.5, 1.0, (7, 9), 1
BROWN = (92, 60, 38)
HERO = Figure(size=720, hair='dreads', accent=BROWN, beard=(120, 84, 56))
MON = (440, 590, 1000, 930)                               # the monitor's screen (smaller, the author)
CLIP = sorted(os.listdir(os.path.join(WORK, 'clip'))) if os.path.isdir(os.path.join(WORK, 'clip')) else []
THUMBS = [Image.open(os.path.join(WORK, 'thumbs', f)) for f in sorted(os.listdir(os.path.join(WORK, 'thumbs')))]


def paste(cv, im, x, y, w, h):
    cv.img.paste(im.resize((int(w * SS), int(h * SS)), Image.LANCZOS), (int(x * SS), int(y * SS)))


def sky_at(t):
    """Days and nights while he works: (sky colour, night 0..1, (u, 'sun'|'moon') in the window, daylight 0..1)."""
    if t >= T_WORK:
        return (196, 226, 255), 0.0, None, 1.0
    ph = (DAY0 + t / T_WORK * DAYS) % 1.0                # 0..1 = one day+night; 0 = noon
    day = 0.5 + 0.5 * math.cos(ph * 2 * math.pi)
    sky = tuple(int(c1 + (c0 - c1) * day) for c0, c1 in zip((196, 226, 255), (28, 36, 78)))
    u = (ph + 0.25) % 0.5 / 0.5                          # each body crosses the window in half a cycle
    return sky, 1 - day, (u, 'sun' if day > 0.5 else 'moon'), day


def frame(i):
    t = i / FPS
    cv = Canvas(W, H)
    sky, night, body, day = sky_at(t)
    tiles(cv, 0, 1520, step=120, col=(232, 234, 240))
    cv.rrect((-20, 1520, W + 20, H + 20), 0, fill=(238, 232, 222))
    floor(cv, 1520)
    wb = (70, 110, 390, 410)
    bxy = None
    if body:
        u, kind = body
        bxy = (wb[0] + 10 + u * (wb[2] - wb[0] - 20), wb[3] - 45 - math.sin(u * math.pi) * (wb[3] - wb[1] - 110), kind)
    window(cv, wb, t, sky=sky, body=bxy, night=night)
    curtains(cv, wb)
    hours = 9 + (DAY0 + min(t, T_WORK) / T_WORK * DAYS) * 24 + max(0, t - T_WORK) * 0.05
    wall_clock(cv, (930, 240), 95, hours)
    lamp(cv, 640, 250, 0.9, t)
    # the desk, the monitor, the keyboard, the mugs
    desk_y = 1075
    cv.rrect((300, desk_y, 1100, desk_y + 30), 6, fill=(205, 160, 110), col=INK, w=7)
    cv.line([(360, desk_y + 30), (360, 1520)], 10)
    cv.line([(1040, desk_y + 30), (1040, 1520)], 10)
    mx = (MON[0] + MON[2]) / 2
    cv.rrect((mx - 45, MON[3] + 10, mx + 45, desk_y), 8, fill=(70, 74, 90), col=INK, w=6)          # the stand
    cv.rrect((mx - 120, desk_y - 22, mx + 120, desk_y), 8, fill=(70, 74, 90), col=INK, w=6)
    cv.rrect((MON[0] - 20, MON[1] - 20, MON[2] + 20, MON[3] + 20), 20, fill=(40, 42, 54), col=INK, w=8)
    screen(cv, t)
    cv.rrect((400, desk_y - 18, 580, desk_y), 5, fill=(230, 232, 238), col=INK, w=5)               # keyboard
    n_mugs = MUGS[0] + min(MUGS[1] - MUGS[0], int(min(t, T_WORK) / T_WORK * (MUGS[1] - MUGS[0] + 0.99)))
    for k in range(n_mugs):                              # a row of mugs (two rows when there are many), the newest steaming
        mug(cv, (1062 - (k % 5) * 40, desk_y - (k // 5) * 48), 0.72, steam=1.0 if k == n_mugs - 1 and t < T_WORK else 0)
    # the hero
    seat = (290, 1160)
    office_chair(cv, seat, 1.2)
    pose = hero_pose(t, day)
    pose['look'] = pose.get('look', 0.7) * 0.35          # three-quarters: we see his face
    pose['t'] = t
    over = ('R',) if T_WIPE <= t < T_WIPE + 1.0 else ()   # the wiping hand goes over the face (drawn by wipe_arm)
    HERO.draw(cv, pose, (seat[0] + 10, seat[1] - 14), over=over, arm_fn=lambda J, side: wipe_arm(J, t))
    # the caption at the bottom
    if t < T_WORK:
        day_n = 1 + int(DAY0 + t / T_WORK * DAYS)
        cv.d.text((W / 2 * SS, 1700 * SS), f'Монтаж: день {day_n}', font=font(64, 800), fill=INK, anchor='mm')
    elif T_WIPE <= t < T_PUB:
        cv.d.text((W / 2 * SS, 1700 * SS), 'Фух… готово!', font=font(64, 800), fill=INK, anchor='mm')
    elif t >= T_PLAY + 1.3:
        cv.d.text((W / 2 * SS, 1700 * SS), 'Чекаємо' + '.' * (1 + int((t - T_PLAY) * 2) % 3), font=font(64, 800), fill=MUTED, anchor='mm')
    if t >= T_PLAY:
        views_pill(cv, t)
    img = cv.image()
    if t < T_WORK and night > 0.05:                      # the room at night: a blue veil
        img = Image.blend(img, Image.new('RGB', img.size, (20, 26, 60)), 0.32 * night)
    return img


def hero_pose(t, day):
    pose = dict(POSES['sit_desk'])
    typing = dict(pose)
    typing['eL'] += 10 * math.sin(t * 38)
    typing['eR'] -= 10 * math.sin(t * 41 + 1)
    typing['head'] = 4 + 3 * math.sin(t * 2)
    typing['face'] = ('smile' if day > 0.4 else 'flat') if not TIRED else ('flat' if day > 0.4 else 'sad')   # tired at night
    if TIRED: typing['head'] += 6                        # the head hangs a little lower
    if t < T_WORK:
        return typing
    if t < T_STAR:                                       # «фух»: sits back; the arm is drawn by wipe_arm
        s = t - T_WIPE
        return lerp_pose(typing, dict(pose, face='flat' if s < 0.75 else 'smile', head=-6, lean=0), ease(s / 0.25))
    if t < T_PUB:                                        # starry eyes
        return dict(pose, face='stars', head=-4)
    if t < T_PLAY:                                       # reaching for the button
        return lerp_pose(dict(pose, face='stars'), dict(pose, sR=80, eR=-30, lean=14, face='stars'), ease((t - T_PUB) / 0.35))
    stare = t - T_PLAY
    p = lerp_pose(dict(pose, sR=80, eR=-30, lean=14), dict(pose, lean=4), ease(stare / 0.4))
    p['face'] = 'stars' if stare < 0.8 else 'grin' if stare < 1.6 else 'flat' if stare < 2.8 else 'sad'
    p['head'] = 4 + min(14, max(0, stare - 2.8) * 10)
    return p


def wipe_arm(J, t):
    """The arm wiping the brow, drawn by hand (a stick arm can't reach): from the keyboard up to the brow, the hand slides
    across the forehead front to back, then back down to the keyboard."""
    c, r = J['head'], J['hr']
    sh = J['arms']['R'][0]
    rest = HERO.parts(dict(POSES['sit_desk']), J['pelvis'])['arms']['R']
    s = t - T_WIPE
    el = (c[0] + r * 1.25, c[1] - r * 0.25)
    if s < 0.25:                                         # up to the brow
        k = ease(s / 0.25)
        return [sh, mix(rest[1], el, k), mix(rest[2], (c[0] + r * 0.75, c[1] - r * 0.62), k)]
    if s < 0.75:                                         # across the forehead
        u = ease((s - 0.25) / 0.5)
        return [sh, el, (c[0] + r * (0.75 - 1.6 * u), c[1] - r * 0.62 + r * 0.08 * math.sin(u * math.pi))]
    k = ease((s - 0.75) / 0.25)                          # back down
    return [sh, mix(el, rest[1], k), mix((c[0] - r * 0.85, c[1] - r * 0.62), rest[2], k)]


def mix(a, b, k):
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)


def screen(cv, t):
    x0, y0, x1, y1 = MON
    sw, sh = x1 - x0, y1 - y0
    cv.rrect(MON, 10, fill=(24, 26, 34))
    if t < T_PUB:                                        # the editor: media bin, a preview with jumping frames, the timeline
        th = THUMBS[int(t * 5) % len(THUMBS)]
        pw, ph_ = 126, 224
        paste(cv, th, x0 + sw * 0.5 - pw / 2 + 60, y0 + 14, pw, ph_)
        cv.rrect((x0 + 14, y0 + 18, x0 + 190, y0 + 230), 8, fill=(36, 39, 50))
        for k in range(4):
            paste(cv, THUMBS[(k * 3 + int(t * 2)) % len(THUMBS)], x0 + 24 + (k % 2) * 82, y0 + 26 + (k // 2) * 102, 74, 94)
        for r, col in enumerate([(120, 170, 240), (240, 170, 90), (140, 210, 160)]):
            yy = y0 + 250 + r * 26
            for k in range(6):
                xs = x0 + 14 + ((k * 120 + r * 41 + int(t * 40)) % (sw - 120))
                cv.rrect((xs, yy, xs + 80 + 26 * ((k + r) % 3), yy + 20), 5, fill=col)
        ph = x0 + 14 + (t * 220) % (sw - 28)
        cv.line([(ph, y0 + 242), (ph, y0 + 336)], 4, (255, 90, 90))
    elif t < T_PLAY:                                     # the big button, the arrow flies in and clicks
        u = t - T_PUB
        press = 0.92 if 0.45 < u < 0.6 else 1.0
        bw, bh = 360 * press, 96 * press
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cv.rrect((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), 48 * press, fill=RED)
        cv.d.text((cx * SS, cy * SS), 'Опублікувати', font=font(int(40 * press), 800), fill=(255, 255, 255), anchor='mm')
        k = ease(min(1, u / 0.45))
        ax, ay = x1 - 50 + (cx + 50 - (x1 - 50)) * k, y1 - 30 + (cy + 16 - (y1 - 30)) * k
        cv.poly([(ax, ay), (ax, ay + 46), (ax + 12, ay + 35), (ax + 22, ay + 55), (ax + 30, ay + 51), (ax + 20, ay + 31), (ax + 35, ay + 31)],
                fill=(255, 255, 255), col=INK, w=3)
    else:                                                # his video plays; the stats beside it barely move
        if CLIP:
            k = min(len(CLIP) - 1, int((t - T_PLAY) * FPS))
            paste(cv, Image.open(os.path.join(WORK, 'clip', CLIP[k])), x0 + 24, y0 + 12, 180, 316)
        sx = x0 + 250
        rows = [(lambda c, p: _eye(c, p, 48, col=(230, 232, 240)), fmt(views_at(t)), 'перегляди'),
                (lambda c, p: _heart(c, p, 48, RED), '1' if t - T_PLAY > 2.2 else '0', 'вподобання'),
                (None, '0', 'коментарі')]
        for r, (icon, val, label) in enumerate(rows):
            yy = y0 + 64 + r * 102
            if icon: icon(cv, (sx, yy))
            else: cv.rrect((sx - 24, yy - 18, sx + 24, yy + 16), 9, fill=(230, 232, 240))
            cv.d.text(((sx + 48) * SS, (yy - 8) * SS), val, font=font(52, 900), fill=(255, 255, 255), anchor='lm')
            cv.d.text(((sx + 48) * SS, (yy + 32) * SS), label, font=font(22, 500), fill=(150, 156, 172), anchor='lm')


def views_at(t):
    s = t - T_PLAY
    return 0 if s < 1.0 else 1 if s < 2.4 else 3


def views_pill(cv, t):
    """The same big views pill as in the toilet scene, top centre — here it shows 0… 1… 3."""
    s = t - T_PLAY
    pop = max(0.0, 1 - min(abs(s - 1.0), abs(s - 2.4)) / 0.2)
    sc = 1 + 0.2 * pop
    f = font(int(92 * sc), 900)
    txt = str(views_at(t))
    tw = cv.d.textlength(txt, font=f) / SS
    iw = 96 * sc
    x0 = W / 2 - (tw + iw + 24) / 2
    cv.rrect((x0 - 34, 60, x0 + iw + 24 + tw + 34, 60 + 120 * sc), 60 * sc, fill=(255, 255, 255), col=(226, 229, 236), w=4)
    _eye(cv, (x0 + iw / 2, 60 + 60 * sc), iw * 0.9)
    cv.d.text(((x0 + iw + 24) * SS, (62 + 60 * sc) * SS), txt, font=f, fill=INK, anchor='lm')


def sound():
    """Typing and a fast tick-tock while he works; (B) a sigh-whoosh at the wipe, a sparkle at the stars, the click and
    a "ding" at the button; then silence and a cricket."""
    sr = 44100
    n = int(DUR * sr)
    y = np.zeros(n)
    rng = np.random.default_rng(7)

    def add(t0, sig):
        k = int(t0 * sr)
        if k < n: y[k:k + len(sig)] += sig[:n - k]
    for t0 in np.cumsum(rng.uniform(0.05, 0.13, 80)):
        if t0 > T_WORK - 0.1: break
        m = int(0.025 * sr)
        add(t0, 0.25 * rng.standard_normal(m) * np.exp(-np.arange(m) / (0.004 * sr)))
    for k in range(int(T_WORK / 0.12)):
        m = int(0.01 * sr)
        add(k * 0.12, 0.12 * np.sin(2 * np.pi * (3000 if k % 2 else 2200) * np.arange(m) / sr) * np.exp(-np.arange(m) / (0.002 * sr)))
    if PART == 'b':
        m = int(0.6 * sr); tt = np.arange(m) / sr                                # «фух»: a soft falling breath of noise
        breath = np.convolve(rng.standard_normal(m), np.ones(30) / 30, mode='same') * np.sin(np.pi * tt / tt[-1]) ** 2
        add(T_WIPE + 0.2, 0.5 * breath)
        for j, f in enumerate((1568, 2093, 2637)):                               # sparkle
            m = int(0.25 * sr); tt = np.arange(m) / sr
            add(T_STAR + j * 0.07, 0.25 * np.exp(-tt / 0.08) * np.sin(2 * np.pi * f * tt))
        m = int(0.03 * sr)
        add(T_PUB + 0.5, 0.5 * rng.standard_normal(m) * np.exp(-np.arange(m) / (0.003 * sr)))
        m2 = int(0.7 * sr); tt = np.arange(m2) / sr
        add(T_PUB + 0.52, 0.45 * np.exp(-tt / 0.2) * (np.sin(2 * np.pi * 1318 * tt) + 0.5 * np.sin(2 * np.pi * 1976 * tt)))
        for k in range(6):                                                       # the cricket
            for j in range(3):
                m = int(0.035 * sr); tt = np.arange(m) / sr
                add(T_PLAY + 1.3 + k * 0.6 + j * 0.06, 0.3 * np.sin(2 * np.pi * 4400 * tt) * np.sin(np.pi * tt / (m / sr)))
    y = y / max(1e-6, np.abs(y).max()) * 0.75
    from scipy.io import wavfile
    path = os.path.join(WORK, f'sound_{PART}.wav')
    wavfile.write(path, sr, (np.stack([y, y], 1) * 32767).astype(np.int16))
    return path


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    if len(sys.argv) > 2:
        frame(int(float(sys.argv[2]) * FPS)).save(os.path.join(WORK, f'still_{PART}_{sys.argv[2]}.png')); sys.exit()
    fr = os.path.join(WORK, f'frames_{PART}')
    os.makedirs(fr, exist_ok=True)
    for i in range(int(DUR * FPS)):
        frame(i).save(os.path.join(fr, f'f_{i:04d}.png'))
    snd = sound()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(fr, 'f_%04d.png'), '-i', snd,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', OUT], check=True)
    print('done:', OUT)
