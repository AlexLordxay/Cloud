# Stick cartoon, scene 2 (~8 s): our guy (with a braid) at the desk. Days and nights fly by in the window, the clock
# spins, mugs pile up while he edits; he presses «Опублікувати», his real video plays on the big monitor (the Moon
# hitting the Earth) — and the views crawl: 0… 1… 3. A cricket. His smile slides off.
#   python3 scenes/stick_desk/render.py [t]   ->  videos/stick_desk.mp4  (with t: one still to work/stick_desk/)
# The clip on the monitor: frames of videos/moonfall_music.mp4 32.6–36.8 s in work/stick_desk/clip (ffmpeg, see HANDOFF).
import math, os, random, subprocess, sys
import numpy as np
from PIL import Image

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, TOOLS)
from characters.stick import (Canvas, Figure, POSES, lerp_pose, ease, tiles, floor, window, curtains, wall_clock,
                              office_chair, mug, lamp, INK, SS)
from characters.feed import draw_feed, font, fmt, _eye, _heart, _bubble, RED, MUTED

W, H, FPS, DUR = 1080, 1920, 30, 8.0
WORK = os.path.join(TOOLS, 'work', 'stick_desk')
OUT = os.path.join(TOOLS, '..', 'stick_desk.mp4')
T_WORK, T_PUB, T_PLAY = 3.4, 3.4, 4.3                   # editing until 3.4 s; the button 3.4–4.3; the video after
BRAID = (92, 60, 38)
HERO = Figure(size=720, hair='dreads', accent=BRAID, beard=(120, 84, 56))
MON = (330, 470, 1050, 930)                              # the monitor's screen (x0, y0, x1, y1)
CLIP = sorted(os.listdir(os.path.join(WORK, 'clip'))) if os.path.isdir(os.path.join(WORK, 'clip')) else []
THUMBS = [Image.open(os.path.join(WORK, f'thumb_{k}.jpg')) for k in ('0.5', '1.5', '2.5')]


def paste(cv, im, x, y, w, h):
    cv.img.paste(im.resize((int(w * SS), int(h * SS)), Image.LANCZOS), (int(x * SS), int(y * SS)))


def sky_at(t):
    """Two days and nights while he works: (sky colour, night 0..1, body in the window, room light 0..1)."""
    if t >= T_WORK:
        return (196, 226, 255), 0.0, None, 1.0
    ph = (t / T_WORK) * 2.0 % 1.0                        # 0..1 = one day+night
    day = 0.5 + 0.5 * math.cos(ph * 2 * math.pi)        # 1 at noon, 0 at midnight
    night = 1 - day
    sky = tuple(int(c1 + (c0 - c1) * day) for c0, c1 in zip((196, 226, 255), (28, 36, 78)))
    kind = 'sun' if day > 0.5 else 'moon'
    u = (ph + 0.25) % 0.5 / 0.5                          # each body crosses the window in half a cycle
    return sky, night, (u, kind), day


def frame(i):
    t = i / FPS
    cv = Canvas(W, H)
    sky, night, body, day = sky_at(t)
    # the room: wall, floor; the room darkens a little at night (a blue veil drawn at the end)
    tiles(cv, 0, 1520, step=120, col=(232, 234, 240))
    cv.rrect((-20, 1520, W + 20, H + 20), 0, fill=(238, 232, 222))
    floor(cv, 1520)
    wb = (70, 110, 390, 410)
    bx = by = None
    if body:
        u, kind = body
        bx = wb[0] + 10 + u * (wb[2] - wb[0] - 20)
        by = wb[3] - 45 - math.sin(u * math.pi) * (wb[3] - wb[1] - 110)
    window(cv, wb, t, sky=sky, body=(bx, by, body[1]) if body else None, night=night)
    curtains(cv, wb)
    hours = 9 + (t / T_WORK) * 48 if t < T_WORK else 9 + 48 + (t - T_WORK) * 0.02
    wall_clock(cv, (930, 240), 95, hours)
    lamp(cv, 640, 250, 0.9, t)
    # the desk, the monitor, the keyboard, the mugs
    desk_y = 1075
    cv.rrect((300, desk_y, 1100, desk_y + 30), 6, fill=(205, 160, 110), col=INK, w=7)
    cv.line([(360, desk_y + 30), (360, 1520)], 10)
    cv.line([(1040, desk_y + 30), (1040, 1520)], 10)
    cv.rrect((640, MON[3] + 10, 740, desk_y), 8, fill=(70, 74, 90), col=INK, w=6)                # the stand
    cv.rrect((560, desk_y - 22, 820, desk_y), 8, fill=(70, 74, 90), col=INK, w=6)
    cv.rrect((MON[0] - 22, MON[1] - 22, MON[2] + 22, MON[3] + 22), 22, fill=(40, 42, 54), col=INK, w=8)
    screen(cv, t)
    cv.rrect((400, desk_y - 18, 580, desk_y), 5, fill=(230, 232, 238), col=INK, w=5)               # keyboard
    n_mugs = min(6, int(t / T_WORK * 6.5)) if t < T_WORK else 6
    for k in range(n_mugs):                              # a row of mugs, the newest steaming
        mug(cv, (860 + k * 38, desk_y), 0.75, steam=1.0 if k == n_mugs - 1 and t < T_WORK else 0)
    # the hero on his chair, typing; at the button he leans in and clicks; then freezes, the smile slides off
    seat = (290, 1160)
    office_chair(cv, seat, 1.2)
    pose = dict(POSES['sit_desk'])
    if t < T_WORK:
        tap = math.sin(t * 38)
        pose['eL'] += 10 * tap
        pose['eR'] -= 10 * math.sin(t * 41 + 1)
        pose['head'] = 4 + 3 * math.sin(t * 2)
        pose['face'] = 'smile' if day > 0.4 else 'flat'                                     # tired at night
    elif t < T_PLAY:
        u = ease((t - T_PUB) / 0.35)
        pose = lerp_pose(pose, dict(pose, sR=80, eR=-30, lean=14, face='grin'), u)              # reaching for the button
        if t > T_PUB + 0.55:
            pose['face'] = 'grin'
    else:
        u = ease((t - T_PLAY) / 0.4)
        pose = lerp_pose(pose, dict(pose, lean=4, face='grin'), u)
        stare = t - T_PLAY
        pose['face'] = 'grin' if stare < 1.3 else ('flat' if stare < 2.6 else 'sad')
        pose['head'] = 4 + min(12, max(0, stare - 2.6) * 10)                                   # the head drops a little
    pose['look'] = pose.get('look', 0.7) * 0.35                  # three-quarters: we see his face
    pose['t'] = t
    HERO.draw(cv, pose, (seat[0] + 10, seat[1] - 14))
    # the caption at the bottom: the days of editing, then the wait
    if t < T_WORK:
        day_n = 1 + int(t / T_WORK * 3)
        cv.d.text((W / 2 * SS, 1700 * SS), f'Монтаж: день {day_n}', font=font(64, 800), fill=INK, anchor='mm')
    elif t >= T_PLAY + 1.3:
        dots = '.' * (1 + int((t - T_PLAY) * 2) % 3)
        cv.d.text((W / 2 * SS, 1700 * SS), 'Чекаємо' + dots, font=font(64, 800), fill=MUTED, anchor='mm')
    # the views pill at the top (the same as the toilet's), only once the video is out
    if t >= T_PLAY:
        draw_feed_views(cv, t)
    img = cv.image()
    if t < T_WORK and night > 0.05:                      # the room at night: a blue veil, lighter where the screen is
        veil = Image.new('RGB', img.size, (20, 26, 60))
        img = Image.blend(img, veil, 0.32 * night)
    return img


def screen(cv, t):
    x0, y0, x1, y1 = MON
    cv.rrect(MON, 10, fill=(24, 26, 34))
    if t < T_WORK:                                       # the editor: a preview, the timeline with clips, a playhead
        th = THUMBS[int(t * 2.5) % 3]
        paste(cv, th, x0 + 260, y0 + 20, 170, 302)
        cv.rrect((x0 + 20, y0 + 30, x0 + 240, y0 + 300), 8, fill=(36, 39, 50))
        for k in range(5):
            cv.rrect((x0 + 34, y0 + 46 + k * 50, x0 + 226, y0 + 80 + k * 50), 5, fill=(52, 56, 72))
        for r, col in enumerate([(120, 170, 240), (240, 170, 90), (140, 210, 160)]):
            yy = y0 + 340 + r * 32
            for k in range(6):
                xs = x0 + 20 + ((k * 150 + r * 47) % 640)
                cv.rrect((xs, yy, xs + 110 + 30 * ((k + r) % 3), yy + 24), 5, fill=col)
        ph = x0 + 20 + (t * 260) % 640
        cv.line([(ph, y0 + 330), (ph, y0 + 440)], 4, (255, 90, 90))
    elif t < T_PLAY:                                     # the big button
        u = (t - T_PUB)
        press = 0.92 if 0.45 < u < 0.6 else 1.0
        bw, bh = 420 * press, 110 * press
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cv.rrect((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), 55 * press, fill=RED)
        cv.d.text((cx * SS, cy * SS), 'Опублікувати', font=font(int(44 * press), 800), fill=(255, 255, 255), anchor='mm')
        # the mouse arrow flying in to the button
        k = ease(min(1, u / 0.45))
        ax, ay = x1 - 60 + (cx + 60 - (x1 - 60)) * k, y1 - 40 + (cy + 20 - (y1 - 40)) * k
        cv.poly([(ax, ay), (ax, ay + 50), (ax + 13, ay + 38), (ax + 24, ay + 60), (ax + 32, ay + 56), (ax + 21, ay + 34), (ax + 38, ay + 34)],
                fill=(255, 255, 255), col=INK, w=3)
    else:                                                # his video plays, a stats panel beside it barely moves
        k = min(len(CLIP) - 1, int((t - T_PLAY) * FPS)) if CLIP else 0
        if CLIP:
            paste(cv, Image.open(os.path.join(WORK, 'clip', CLIP[k])), x0 + 40, y0 + 10, 248, 440)
        sx = x0 + 330
        views, likes = views_at(t), (1 if t - T_PLAY > 2.2 else 0)
        rows = [(lambda c, p: _eye(c, p, 56, col=(230, 232, 240)), fmt(views), 'перегляди'),
                (lambda c, p: _heart(c, p, 56, RED), str(likes), 'вподобання'),
                (lambda c, p: None, '0', 'коментарі')]
        for r, (icon, val, label) in enumerate(rows):
            yy = y0 + 80 + r * 120
            if r == 2:
                cv.rrect((sx - 28, yy - 22, sx + 28, yy + 18), 10, fill=(230, 232, 240))
            else:
                icon(cv, (sx, yy))
            cv.d.text(((sx + 56) * SS, (yy - 8) * SS), val, font=font(58, 900), fill=(255, 255, 255), anchor='lm')
            cv.d.text(((sx + 56) * SS, (yy + 38) * SS), label, font=font(24, 500), fill=(150, 156, 172), anchor='lm')


def views_at(t):
    s = t - T_PLAY
    return 0 if s < 1.0 else 1 if s < 2.4 else 3


def draw_feed_views(cv, t):
    """The same big views pill as in the toilet scene, top centre — here it shows 0… 1… 3."""
    v = views_at(t)
    s = t - T_PLAY
    pop = max(0.0, 1 - abs(s - 1.0) / 0.2) if 0.8 < s < 1.2 else max(0.0, 1 - abs(s - 2.4) / 0.2) if 2.2 < s < 2.6 else 0
    sc = 1 + 0.2 * pop
    f = font(int(92 * sc), 900)
    txt = str(v)
    tw = cv.d.textlength(txt, font=f) / SS
    iw = 96 * sc
    x0 = W / 2 - (tw + iw + 24) / 2
    cv.rrect((x0 - 34, 60 - 0 * sc, x0 + iw + 24 + tw + 34, 60 + 120 * sc), 60 * sc, fill=(255, 255, 255), col=(226, 229, 236), w=4)
    _eye(cv, (x0 + iw / 2, 60 + 60 * sc), iw * 0.9)
    cv.d.text(((x0 + iw + 24) * SS, (62 + 60 * sc) * SS), txt, font=f, fill=INK, anchor='lm')


def sound():
    """Keyboard clicks and a fast tick-tock while he works; a click on the button and a bright "ding"; then silence and
    a cricket."""
    sr = 44100
    n = int(DUR * sr)
    y = np.zeros(n)
    rng = np.random.default_rng(7)
    def add(t0, sig):
        k = int(t0 * sr)
        y[k:k + len(sig)] += sig[:max(0, n - k)]
    for t0 in np.cumsum(rng.uniform(0.05, 0.13, 60)):                          # typing
        if t0 > T_WORK - 0.1: break
        m = int(0.025 * sr)
        add(t0, 0.25 * rng.standard_normal(m) * np.exp(-np.arange(m) / (0.004 * sr)))
    for k in range(int(T_WORK / 0.12)):                                         # tick-tock, fast (time flying)
        m = int(0.01 * sr)
        add(k * 0.12, 0.12 * np.sin(2 * np.pi * (3000 if k % 2 else 2200) * np.arange(m) / sr) * np.exp(-np.arange(m) / (0.002 * sr)))
    m = int(0.03 * sr)
    add(T_PUB + 0.5, 0.5 * rng.standard_normal(m) * np.exp(-np.arange(m) / (0.003 * sr)))   # the click
    m2 = int(0.7 * sr); tt = np.arange(m2) / sr
    add(T_PUB + 0.52, 0.45 * np.exp(-tt / 0.2) * (np.sin(2 * np.pi * 1318 * tt) + 0.5 * np.sin(2 * np.pi * 1976 * tt)))
    for k in range(5):                                                          # the cricket: chirps of 3 pulses
        t0 = T_PLAY + 1.3 + k * 0.62
        for j in range(3):
            m = int(0.035 * sr); tt = np.arange(m) / sr
            add(t0 + j * 0.06, 0.3 * np.sin(2 * np.pi * 4400 * tt) * np.sin(np.pi * tt / (m / sr)))
    y = y / max(1e-6, np.abs(y).max()) * 0.75
    from scipy.io import wavfile
    path = os.path.join(WORK, 'sound.wav')
    wavfile.write(path, sr, (np.stack([y, y], 1) * 32767).astype(np.int16))
    return path


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    if len(sys.argv) > 1:
        frame(int(float(sys.argv[1]) * FPS)).save(os.path.join(WORK, f'still_{sys.argv[1]}.png')); sys.exit()
    for i in range(int(DUR * FPS)):
        frame(i).save(os.path.join(WORK, f'f_{i:04d}.png'))
    snd = sound()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(WORK, 'f_%04d.png'), '-i', snd,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', OUT], check=True)
    print('done:', OUT)
