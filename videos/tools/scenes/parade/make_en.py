# «Planet parade» — the ENGLISH cut (13.11.2026, for an Instagram trial reel): a copy of make.py with every word on screen
# in English, the author's voice in English (voice_en.mp3, Higgsfield ElevenLabs v4, 6.21 cr.) and, so it is a new video and
# not a repost, its own timeline: each English sentence keeps its natural pace, and the picture runs on a smooth time warp
# (PCHIP through the sentence starts) back onto the Ukrainian cut's clock — so the cameras, the badges and the cuts still
# land on their words. Also new: the hook (a pull-back from Venus over the horizon to the whole dawn sky), longer
# dissolves, a 5 % closer frame and a slightly different grade, the organ two semitones up, the wordmark «Nebozvıd».
#   python3 scenes/parade/make_en.py            -> frames + sound + videos/parade_en.mp4
#   python3 scenes/parade/make_en.py test 3 30  -> work/parade_en/test_<t>.jpg   (t on the NEW clock)
#   python3 scenes/parade/make_en.py sound      -> the sound only, then encode
# Needs the site's frames with English labels: node rec.js parade_site_en video
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, TOOLS); sys.path.insert(0, HERE)
import compose as C
WORK = os.path.join(TOOLS, 'work', 'parade_en'); SITE = os.path.join(TOOLS, 'work', 'parade_site_en', 'frames')
VIDEOS = os.path.abspath(os.path.join(TOOLS, '..'))
FF = __import__('imageio_ffmpeg').get_ffmpeg_exe()
SC = json.load(open(os.path.join(HERE, 'scene.json'))); B = SC['beats']; DUR = SC['duration']; FPS = 30
C.LOGO_PARTS = ('Nebozv', 'ı', 'd'); C.SUB_TEXT = ('Follow', 'Following')
DUR_OLD = DUR                                                      # B, the cameras and the badges stay on the old clock

# ---------------- the English voice and the time warp ----------------
# the 19 sentences in voice_en.mp3 (silencedetect −35 dB; the same sentences as timeline_voice.json)
EN_T0 = [0.0, 6.29, 7.21, 9.04, 16.80, 18.93, 23.03, 29.72, 34.06, 40.58, 42.08, 48.64, 50.50, 57.14, 61.48, 64.00, 71.39, 76.28, 81.10]
EN_T1 = [5.73, 6.94, 8.58, 16.45, 18.40, 22.52, 29.20, 33.56, 39.96, 41.70, 48.17, 50.08, 56.87, 60.89, 63.61, 71.14, 76.02, 80.69, 84.63]
# extra pause before sentence k (1-based) where the picture needs the time: Jupiter's 1 321 Earths, the sky opening,
# the meteors, the card and the close
EXTRA = {10: 0.8, 11: 0.5, 15: 0.3, 17: 0.5, 18: 0.3, 19: 0.3}
OFF = [sum(v for k, v in EXTRA.items() if k <= i + 1) for i in range(19)]
NEW_T0 = [a + o for a, o in zip(EN_T0, OFF)]
OLD_T0 = [x['t0'] for x in json.load(open(os.path.join(HERE, 'timeline_voice.json')))['sentences']]
DUR = round(EN_T1[-1] + OFF[-1] + 2.2, 2)                          # the close holds ~2 s after the last word
from scipy.interpolate import PchipInterpolator
_WX = [0.0] + NEW_T0[1:] + [DUR]; _WY = [0.0] + OLD_T0[1:] + [DUR_OLD]
_WARP = PchipInterpolator(_WX, _WY)
def old(t): return float(_WARP(min(max(t, 0.0), DUR)))             # new clock -> the Ukrainian cut's clock
_GRID = np.linspace(0, DUR, 4000); _GOLD = _WARP(_GRID)
def new(t): return float(np.interp(t, _GOLD, _GRID))               # and back (for the music's beats and the sounds)

METEOR_K = 0.15
W, H = 1080, 1920
GOLD, BLUE, GREEN, RED = (247, 198, 107), (156, 194, 255), (130, 230, 170), (255, 130, 100)

fq = lambda s, w=700: C.font('Unbounded.ttf', s, w)
fc = lambda s, w=600: C.font('Commissioner.ttf', s, w)


def sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def win(t, a, b, d=0.35): return max(0.0, min(sm((t - a) / d), 1 - sm((t - b) / d)))


def shadowed(img, lay, blur=9, k=0.85):
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh.putalpha(lay.getchannel('A').point(lambda v: int(v * k)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur))); img.alpha_composite(lay)


def text(img, s, f, x, y, a, fill=(255, 255, 255), anchor='mm', blur=9):
    if a <= 0: return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).text((x, y), s, font=f, fill=fill + (int(255 * a),), anchor=anchor)
    shadowed(img, lay, blur)


def pill(img, s, f, x, y, a, bg=(20, 16, 12), fg=(255, 255, 255), border=GOLD):
    if a <= 0: return
    d0 = ImageDraw.Draw(img); tw = d0.textlength(s, font=f); h = f.size * 1.55; w = tw + h
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), radius=h / 2, fill=bg + (int(200 * a),), outline=border + (int(230 * a),), width=3)
    d.text((x, y + 1), s, font=f, fill=fg + (int(255 * a),), anchor='mm'); shadowed(img, lay, 12, 0.5)


# ---------------- the camera over the sky: keys (t, az, alt, vfov), eased between ----------------
SKYKEYS = [(0.0, 127, 17, 44), (3.9, 139, 40, 104), (7.1, 138, 41, 101),
           (45.0, 139, 41, 104), (47.3, 137, 36, 96), (49.6, 125, 13, 50), (55.9, 126, 14, 46), (58.4, 184, 52.5, 21), (62.95, 184, 53, 18),
           (67.3, 176, 44, 88), (79.4, 179, 47, 84), (81.2, 139, 40, 104), (97.0, 138, 41, 100)]


def skycam(t):
    K = SKYKEYS
    if t <= K[0][0]: return K[0][1:]
    for (a, *p), (b, *q) in zip(K, K[1:]):
        if t <= b:
            if b - a < 1e-6: return q
            u = sm((t - a) / (b - a)) if b - a < 6 else (t - a) / (b - a)
            return tuple(x + (y - x) * u for x, y in zip(p, q))
    return K[-1][1:]


# meteors: (t0, dur, az, alt, length°, kind) — moving away from the Leonid radiant (az ≈ 178°, alt ≈ 61°)
METEORS = [(1.3, 0.55, 134, 27, 14, 'n'), (50.8, 0.5, 150, 30, 16, 'n'),
           (68.2, 0.45, 198, 52, 22, 'n'), (69.6, 0.5, 160, 50, 26, 'n'), (71.0, 0.42, 190, 40, 18, 'n'), (72.6, 0.8, 168, 47, 34, 'f'),
           (74.6, 0.45, 205, 46, 22, 'n'), (76.2, 0.5, 150, 42, 24, 'n'), (77.9, 0.45, 185, 55, 20, 'n'),
           (82.0, 0.5, 196, 38, 20, 'n'), (86.5, 0.5, 128, 40, 18, 'n'), (92.6, 0.85, 165, 46, 32, 'f')]

_SKY = None; _LINE = None
def sky():
    global _SKY
    if _SKY is None:
        from sky_ua import SkyUA; _SKY = SkyUA()
    return _SKY
def line():
    global _LINE
    if _LINE is None:
        from lineup import Lineup; _LINE = Lineup()
    return _LINE


def seg(t):
    if t < B['site']: return 'hook'
    if t < B['lineup']: return 'site'
    if t < B['sky1']: return 'lineup'
    if t < B['site2']: return 'sky1'
    if t < B['sky2']: return 'site2'
    return 'sky2'


def site_frame(local):
    i = int(round(local * FPS)); p = os.path.join(SITE, f'f_{i:05d}.jpg')
    while not os.path.exists(p) and i > 0: i -= 1; p = os.path.join(SITE, f'f_{i:05d}.jpg')
    return Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)


# ---------------- the sky overlays ----------------
NAMES = {'Venus': 'VENUS', 'Mercury': 'MERCURY', 'Mars': 'MARS', 'Jupiter': 'JUPITER'}
def planet_labels(img, scr, t, which):
    if 'Mars' in scr and 'Jupiter' in scr and math.dist(scr['Mars'], scr['Jupiter']) < 60:
        a = max(which.get('Mars', 0), which.get('Jupiter', 0)); which = {k: v for k, v in which.items() if k not in ('Mars', 'Jupiter')}
        if a > 0:
            x, y = scr['Jupiter']; tx = min(max(x - 210, 200), W - 200)
            lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).line([(x - 22, y - 10), (tx + 120, y - 44)], fill=(255, 255, 255, int(150 * a)), width=2); shadowed(img, lay, 4, 0.6)
            text(img, 'MARS & JUPITER', fc(36, 700), tx, y - 58, a, (255, 205, 175))
    for n, a in which.items():
        if a <= 0 or n not in scr: continue
        x, y = scr[n]
        if not (0 < x < W and 0 < y < H): continue
        dx = {'Mars': -70, 'Jupiter': 70}.get(n, 0); dy = {'Mars': -46, 'Jupiter': 46, 'Mercury': 46}.get(n, -48)
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.line([(x + dx * 0.25, y + dy * 0.3), (x + dx * 0.8, y + dy * 0.72)], fill=(255, 255, 255, int(150 * a)), width=2)
        shadowed(img, lay, 4, 0.6)
        col = {'Mars': (255, 170, 140), 'Venus': (255, 240, 210)}.get(n, (240, 236, 228))
        tx = min(max(x + dx, 110), W - 110)
        text(img, NAMES[n], fc(36, 700), tx, y + dy, a, col)


def compass(img, s, cam, a):
    if a <= 0: return
    from sky_ua import enu
    for az, name in ((90, 'EAST'), (135, 'SOUTHEAST'), (180, 'SOUTH'), (225, 'SOUTHWEST')):
        x, y, z = s.project(enu(az, 0.0)[None, :], cam)
        if z[0] <= 0 or not (60 < x[0] < W - 60) or not (0 < y[0] < H): continue
        text(img, name, fc(30, 700), float(x[0]), float(y[0]) + 46, a * 0.9, (205, 215, 235))


def finger(img, cx, top, w, a, angle=16):
    """an index finger at arm's length (only the finger, leaning in from the lower right — no hand, so it reads one way
    only), its tip covering the point (cx, top + w/2); backlit: dark warm skin, a faint warm rim from the dawn, the nail"""
    if a <= 0: return
    S = 2; L = int(H * 1.3); fw = int(w * S); pad = fw
    tmp = Image.new('RGBA', (fw + 2 * pad, L * S // 1 + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(tmp)
    x0, y0 = pad, pad
    d.rounded_rectangle((x0, y0, x0 + fw, y0 + L * S), radius=fw // 2, fill=(46, 32, 28, int(245 * a)))
    d.rounded_rectangle((x0 + fw * 0.2, y0 + fw * 0.1, x0 + fw * 0.8, y0 + fw * 0.85), radius=int(fw * 0.28), fill=(66, 48, 42, int(245 * a)))      # the nail
    for k in (1.9, 3.3):                                                                                                                     # knuckle creases
        yy = y0 + fw * k; d.arc((x0 + fw * 0.12, yy - fw * 0.1, x0 + fw * 0.88, yy + fw * 0.1), 200, 340, fill=(80, 58, 50, int(210 * a)), width=4)
    rim = Image.new('RGBA', tmp.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(rim)
    dr.rounded_rectangle((x0 - 3, y0 - 3, x0 + fw + 3, y0 + L * S), radius=fw // 2 + 3, outline=(255, 185, 135, int(110 * a)), width=5)
    tmp = Image.alpha_composite(rim.filter(ImageFilter.GaussianBlur(4)), tmp)
    tmp = tmp.resize((tmp.size[0] // S, tmp.size[1] // S), Image.LANCZOS)
    tipx, tipy = pad / S + w / 2, pad / S + w / 2                         # the tip's centre in tmp
    rot = tmp.rotate(angle, resample=Image.BICUBIC, expand=True)
    mk = Image.new('L', tmp.size, 0); ImageDraw.Draw(mk).ellipse((tipx - 3, tipy - 3, tipx + 3, tipy + 3), fill=255)   # find where the tip went
    mk = np.asarray(mk.rotate(angle, resample=Image.BILINEAR, expand=True)); ty, tx = np.unravel_index(np.argmax(mk), mk.shape)
    img.alpha_composite(rot, (int(cx - tx), int(top + w / 2 - ty)))


def sky_frame(t):
    s = sky(); az, alt, fov = skycam(t)
    im = s.render(az, alt, fov, t, meteors=METEORS).convert('RGBA')
    cam = s.camera(az, alt, fov); scr = s.screen
    if t < B['site']:                                   # the hook: the four named one by one as the voice says «чотири планети»
        lab = {n: sm((t - (4.5 + 0.35 * i)) / 0.4) for i, n in enumerate(['Venus', 'Mercury', 'Mars', 'Jupiter'])}
        planet_labels(im, scr, t, lab); compass(im, s, cam, sm((t - 1.0) / 0.6))
    elif t < B['site2']:
        compass(im, s, cam, win(t, B['sky1'] + 0.5, B['south'] + 0.8))
        lab = {'Venus': win(t, B['venusL'], B['south'] + 0.6), 'Mercury': win(t, B['mercuryL'], B['south'] + 0.6),
               'Mars': win(t, B['ruler'] - 0.4, B['site2'] + 1), 'Jupiter': win(t, B['ruler'] - 0.4, B['site2'] + 1)}
        planet_labels(im, scr, t, lab)
        if t > B['ruler'] and 'Mars' in scr and 'Jupiter' in scr:   # the 1.2° between them
            a = win(t, B['ruler'], B['finger'] + 0.4); (x1, y1), (x2, y2) = scr['Mars'], scr['Jupiter']
            lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2; nx, ny = -(y2 - y1), (x2 - x1); L = math.hypot(nx, ny) or 1; nx, ny = nx / L * 40, ny / L * 40
            d.line([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny)], fill=GOLD + (int(230 * a),), width=3)
            for (xx, yy) in ((x1, y1), (x2, y2)): d.line([(xx + nx * 0.6, yy + ny * 0.6), (xx + nx * 1.3, yy + ny * 1.3)], fill=GOLD + (int(230 * a),), width=3)
            shadowed(im, lay, 4, 0.5); text(im, '1.2°', fq(44), mx + nx * 2.3, my + ny * 2.3, a, GOLD)
        if t > B['finger'] and 'Mars' in scr:
            (x1, y1), (x2, y2) = scr['Mars'], scr['Jupiter']
            fp = cam[3]; w = fp * math.tan(math.radians(1.8))
            k = sm((t - B['finger']) / 0.9) * (1 - sm((t - (B['site2'] - 0.35)) / 0.3))
            top = (min(y1, y2) - w * 0.55) * k + (H + 40) * (1 - k)
            finger(im, (x1 + x2) / 2, top, w, min(1.0, k * 1.5))
            text(im, "a finger at arm's length ≈ 1.5–2°", fc(36, 700), W / 2, 560, win(t, B['finger'] + 0.8, B['site2']), (240, 236, 228))
    else:                                                # sky2: the meteors, the card, the close
        if t < B['card'] + 0.4:
            from sky_ua import enu
            rx, ry, rz = s.project(enu(*s.radiant)[None, :], cam)
            a = win(t, B['leonids'] - 0.3, B['card'])
            if rz[0] > 0 and a > 0:
                lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); x, y = float(rx[0]), float(ry[0])
                d.ellipse((x - 26, y - 26, x + 26, y + 26), outline=GREEN + (int(220 * a),), width=3); shadowed(im, lay, 4, 0.5)
                text(im, 'radiant — in Leo', fc(34, 700), x, y - 58, a, GREEN)
    return im


# ---------------- the lineup with its facts ----------------
def lineup_frame(t):
    L = line(); lt = t - B['lineup']
    LB = {k: B[k] - B['lineup'] for k in ('mercury', 'venus', 'mars', 'jupiter')}
    im = L.render(lt, LB).convert('RGBA'); P = L.pos
    def under(n, s, a, col=(255, 255, 255), f=None, dy=34):
        if n in P and a > 0: x, y, r, k = P[n]; text(im, s, f or fc(32, 700), x, y + r + dy, a * k, col)
    kz = sm((lt - LB['jupiter'] + 0.2) / 1.6)
    nm = 1 - kz
    under('mercury', 'Mercury', nm); under('venus', 'Venus', nm); under('earth', 'Earth', nm * 0.8, BLUE); under('mars', 'Mars', nm)
    # the facts, as each is said
    pill(im, '1 year = 88 days', fc(40, 700), W / 2, 1060, win(lt, LB['mercury'] + 1.4, LB['venus'] - 0.1))
    pill(im, '+465 °C (869 °F) under the clouds', fc(40, 700), W / 2, 1060, win(lt, LB['venus'] + 1.6, LB['mars'] - 0.1), border=RED)
    pill(im, 'Earth — for scale', fc(30, 600), W / 2, 1150, win(lt, LB['venus'] + 0.8, LB['mars'] - 0.1), fg=BLUE, border=BLUE)
    pill(im, 'red color = rust', fc(40, 700), W / 2, 1060, win(lt, LB['mars'] + 1.2, LB['jupiter'] - 0.1), border=RED)
    if 'jupiter' in P:
        x, y, r, k = P['jupiter']
        text(im, 'JUPITER', fq(54), x, y - r - 60, k * sm((lt - LB['jupiter'] - 1.2) / 0.5), GOLD)
        pill(im, '11 times wider than Earth', fc(40, 700), W / 2, y + r + 70 if y + r + 70 < 1640 else 1600, win(lt, LB['jupiter'] + 1.6, LB['jupiter'] + 4.6))
        # «понад 1 300 Земель»: little Earths fill Jupiter's disc, a counter running up
        kf = sm((lt - LB['jupiter'] - 4.4) / 2.6)
        if kf > 0:
            e = L.globe('earth', max(3, r / 11.2), lt); er = e.size[0] / 2
            pts = []; step = er * 2.02
            for j in range(-12, 13):
                for i in range(-12, 13):
                    px = x + (i + 0.5 * (j % 2)) * step; py = y + j * step * 0.866
                    if (px - x) ** 2 + (py - y) ** 2 < (r - er) ** 2: pts.append((px, py))
            pts.sort(key=lambda p: (p[1], p[0]))
            n = int(len(pts) * kf)
            for (px, py) in pts[:n]: im.alpha_composite(e, (int(px - er), int(py - er)))
            cnt = int(1321 * kf)
            pill(im, f'≈ {cnt:,} Earths inside', fc(40, 700), W / 2, 1600, sm((lt - LB['jupiter'] - 4.4) / 0.4), border=BLUE)
    return im


# ---------------- the titles over everything ----------------
def titled(im, t):
    im = im.convert('RGBA')
    if 'shade' not in _CACHE:
        sa = np.zeros((H, W), np.uint8); n = 700
        sa[:n] = (np.clip(1 - np.arange(n) / n, 0, 1) ** 1.6 * 120)[:, None].astype(np.uint8)
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh.putalpha(Image.fromarray(sa)); _CACHE['shade'] = sh
    im.alpha_composite(_CACHE['shade'])
    C.draw_logo(im, 50, 88, 0.92, t)
    # the hook
    a = 1 - sm((t - B['site'] + 0.3) / 0.3)
    if a > 0:
        s = 1 + 0.05 * (1 - sm(t / 0.5))
        text(im, 'NOVEMBER 16', fq(int(58 * s)), W / 2, 230, a, GOLD)
        text(im, '4 PLANETS', fq(int(108 * s)), W / 2, 345, a)
        text(im, 'AT DAWN', fq(int(70 * s)), W / 2, 450, a)
    # the view from above
    text(im, 'VIEW FROM ABOVE', fq(50), W / 2, 205, win(t, B['site'] + 0.4, B['lineup'] - 0.2))
    text(im, 'November 16, 2026 · Nebozvid 3D map', fc(34, 600), W / 2, 268, win(t, B['site'] + 0.6, B['lineup'] - 0.2), (220, 225, 235))
    pill(im, 'all four on the same side of the Sun', fc(38, 700), W / 2, 345, win(t, B['site'] + 6.4, B['lineup'] - 0.2))
    # the parade
    text(im, 'MEET THE PARADE', fq(50), W / 2, 205, win(t, B['lineup'] + 0.2, B['sky1'] - 0.2))
    text(im, 'sizes to the same scale', fc(32, 600), W / 2, 266, win(t, B['lineup'] + 0.6, B['sky1'] - 0.2), (200, 205, 215))
    # the sky over Ukraine
    text(im, 'THE SKY AT DAWN', fq(52), W / 2, 205, win(t, B['sky1'] + 0.2, B['site2'] - 0.1))
    text(im, 'November 16 · seen from Ukraine, 50° N', fc(36, 700), W / 2, 268, win(t, B['sky1'] + 0.4, B['site2'] - 0.1), GOLD)
    pill(im, 'brightest point in the sky after the Moon', fc(36, 700), W / 2, 1600, win(t, 51.2, B['mercuryL'] - 0.1))
    # the gap
    text(im, 'IN REALITY — FAR APART', fq(50), W / 2, 205, win(t, B['site2'] + 0.2, B['sky2'] - 0.1))
    text(im, 'Mars is close to us, Jupiter far beyond it', fc(32, 600), W / 2, 268, win(t, B['site2'] + 0.4, B['sky2'] - 0.1), (220, 225, 235))
    # the Leonids
    text(im, 'LEONID METEOR SHOWER', fq(48), W / 2, 205, win(t, B['sky2'] + 0.2, B['card'] - 0.1), GREEN)
    text(im, 'dust from comet Tempel–Tuttle', fc(36, 700), W / 2, 268, win(t, B['leonids'] + 1.0, B['card'] - 0.1), (225, 240, 230))
    pill(im, '71 km/s — the fastest meteors', fc(40, 700), W / 2, 1600, win(t, B['speed'], B['card'] - 0.1), border=GREEN)
    # when and how
    ka = win(t, B['card'] + 0.3, B['cta'] + 0.1)
    if ka > 0:
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle((90, 230, 990, 760), radius=36, fill=(10, 12, 22, int(175 * ka)), outline=GOLD + (int(200 * ka),), width=3)
        im.alpha_composite(lay)
        text(im, 'HOW TO SEE IT', fq(50), W / 2, 300, ka, GOLD)
        rows = [('When', 'November 16–22', 0.0), ('What time', '≈ 40 minutes before sunrise', 1.2), ('Where', 'southeast and south', 6.1), ('You need', 'a clear sky — no telescope', 6.7)]
        for i, (k, v, dt) in enumerate(rows):
            a = ka * sm((t - B['card'] - 0.4 - dt) / 0.35)
            text(im, k, fc(32, 600), 150, 400 + i * 92, a, (190, 200, 220), anchor='lm'); text(im, v, fc(38, 700), 150, 440 + i * 92, a, anchor='lm')
    # the close
    kc = win(t, B['cta'] + 0.1, DUR_OLD + 1)
    text(im, 'SAVE THIS,', fq(64), W / 2, 330, kc, GOLD); text(im, "so you don't oversleep", fc(44, 700), W / 2, 410, kc)
    text(im, 'and send it to someone to watch with', fc(38, 600), W / 2, 480, kc * sm((t - B['cta'] - 1.2) / 0.4), (225, 230, 240))
    if t > B['cta'] + 2.6: C.draw_subscribe(im, W / 2, 590, t - B['cta'] - 2.6, DUR_OLD - B['cta'] - 2.6 + 1, align='center')
    return im.convert('RGB')


_CACHE = {}
def grade(im):
    """the English cut's own look: 5 % closer (centre crop) and a touch cooler shadows, warmer highlights"""
    im = im.convert('RGB'); z = 1.05; cw, ch = int(W / z), int(H / z)
    im = im.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    lum = a.mean(-1, keepdims=True)
    a = a + (np.array([-0.012, 0.0, 0.022]) * (1 - lum) + np.array([0.02, 0.008, -0.012]) * lum) * 0.9
    a = np.clip(a, 0, 1) ** 0.97
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8))


def frame(i):
    t = old(i / FPS); sg = seg(t)                         # everything below runs on the Ukrainian cut's clock
    if sg in ('hook', 'sky1', 'sky2'): im = sky_frame(t)
    elif sg == 'site': im = site_frame(t - B['site'] + SC['site_offset']['site'])
    elif sg == 'site2': im = site_frame(t - B['site2'] + SC['site_offset']['site2'])
    else: im = lineup_frame(t)
    # dissolves at the cuts — 0.55 s here (0.3 s in the Ukrainian cut)
    for cut in (B['site'], B['lineup'], B['sky1'], B['site2'], B['sky2']):
        if cut <= t < cut + 0.55:
            prev = frame_raw(cut - 1 / FPS); im = Image.blend(prev.convert('RGB'), im.convert('RGB'), sm((t - cut) / 0.55))
    return titled(grade(im), t)


def frame_raw(t):
    sg = seg(t)
    if sg in ('hook', 'sky1', 'sky2'): return sky_frame(t)
    if sg == 'site': return site_frame(t - B['site'] + SC['site_offset']['site'])
    if sg == 'site2': return site_frame(t - B['site2'] + SC['site_offset']['site2'])
    return lineup_frame(t)


def job(i):
    o = os.path.join(WORK, 'out', f'f_{i:05d}.jpg')
    if os.path.exists(o) and 'keep' in sys.argv: return
    frame(i).save(o, quality=92)
    if i % 150 == 0: print('frame', i, flush=True)


def frames():
    os.makedirs(os.path.join(WORK, 'out'), exist_ok=True)
    n = int(round(DUR * FPS))
    with Pool(4) as p: p.map(job, range(n), chunksize=8)


def voice():
    """voice_en.mp3 cut between the sentences (in the middle of each pause) and laid on the new clock"""
    cuts = [0.0] + [(EN_T1[k] + EN_T0[k + 1]) / 2 for k in range(18)] + [EN_T1[-1] + 0.25]
    ins, parts = ['-i', os.path.join(HERE, 'voice_en.mp3')], []
    split = f'[0:a]asplit=19' + ''.join(f'[c{k}]' for k in range(19))
    for k in range(19):
        parts.append(f'[c{k}]atrim={cuts[k]:.3f}:{cuts[k + 1]:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,adelay={int((cuts[k] + OFF[k]) * 1000)}:all=1[v{k}]')
    graph = split + ';' + ';'.join(parts) + ';' + ''.join(f'[v{k}]' for k in range(19)) + f'amix=inputs=19:normalize=0,apad,atrim=0:{DUR:.2f}[a]'
    out = os.path.join(WORK, 'voice.wav')
    subprocess.run([FF, '-y', '-loglevel', 'error', *ins, '-filter_complex', graph, '-map', '[a]', '-ar', '44100', out], check=True)
    return out


def sound():
    # the organ on the new clock, two semitones up (music.js reads scene_en.json)
    nb = {k: (round(new(v), 2) if not isinstance(v, list) else [round(new(x), 2) for x in v]) for k, v in B.items()}
    json.dump({'duration': DUR, 'beats': nb, 'tr': 2}, open(os.path.join(WORK, 'scene_en.json'), 'w'), indent=1)
    env = dict(os.environ, PARADE_SCENE=os.path.join(WORK, 'scene_en.json'), PARADE_MUSIC=os.path.join(WORK, 'music.wav'))
    subprocess.run(['node', os.path.join(HERE, 'music.js')], check=True, cwd=TOOLS, env=env)
    v = voice()
    SR = 44100; N = int(DUR * SR); mix = np.zeros(N); mixm = np.zeros(N)
    def add(x, at, k, mix=mix):
        i0 = int(at * SR); j0 = min(N, i0 + len(x));
        if i0 < N: mix[i0:j0] += k * x[:j0 - i0]
    tt = np.arange(int(1.2 * SR)) / SR
    for m in nb['meteors']:
        f0 = 2600 + 300 * ((m * 7) % 3); x = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt / 0.35) * np.minimum(1, tt / 0.01)
        x += 0.5 * np.sin(2 * np.pi * f0 * 1.5 * tt) * np.exp(-tt / 0.25); add(x, m, 0.12, mixm)
    tp = np.arange(int(0.12 * SR)) / SR; pop = np.sin(2 * np.pi * np.cumsum(900 * (1 + 0.6 * np.exp(-tp / 0.02))) / SR) * np.exp(-tp / 0.03)
    for at in [B['mercury'] + 1.4, B['venus'] + 1.6, B['mars'] + 1.2, B['jupiter'] + 1.6, B['ruler'], B['card'] + 0.4, B['card'] + 1.6, B['card'] + 6.5, B['card'] + 7.1]: add(pop, new(at), 0.25)
    sc = 0.6 / max(1e-9, np.abs(mix + mixm).max()); mix = (mix + METEOR_K * mixm) * sc
    st = np.stack([mix, mix], 1)
    import wave
    with wave.open(os.path.join(WORK, 'sfx.wav'), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
    mixf = ('[0:a]apad,atrim=0:%.2f,asplit=2[v][sc];[1:a]volume=2.6[m];[m][sc]sidechaincompress=threshold=0.04:ratio=4:attack=60:release=700[md];'
            '[2:a]volume=0.5[fx];[md][v][fx]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st=%.2f:d=1.4,atrim=0:%.2f[a]') % (DUR, DUR - 1.4, DUR)
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', v, '-i', os.path.join(WORK, 'music.wav'), '-i', os.path.join(WORK, 'sfx.wav'),
                    '-filter_complex', mixf, '-map', '[a]', '-ar', '44100', os.path.join(WORK, 'mix.wav')], check=True)


def encode():
    out = os.path.join(VIDEOS, 'parade_en.mp4')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(WORK, 'out', 'f_%05d.jpg'), '-i', os.path.join(WORK, 'mix.wav'),
                    '-map', '0:v', '-map', '1:a', '-map_metadata', '-1', '-t', f'{DUR:.2f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p',
                    '-profile:v', 'high', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out], check=True)
    print('written', out)


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    if sys.argv[1:2] == ['test']:
        for a in sys.argv[2:]: frame(int(round(float(a) * FPS))).save(os.path.join(WORK, f'test_{a}.jpg'), quality=90)
        sys.exit()
    if 'sound' not in sys.argv[1:]: frames()
    sound(); encode()
