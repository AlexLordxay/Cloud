# "Скільки добиратися до Місяця?" — a short wordless-style race: five lanes from the Earth to the Moon (on foot, by car,
# by plane, by Apollo, by light), each with its travel time counting up. Plain 2D frames drawn with PIL, 1080 × 1920,
# piped to ffmpeg; the sound (a soft pad, whooshes, a bell on each arrival) is synthesised here too.
#
#   python3 scenes/moontrip/make.py            -> videos/moontrip.mp4
#   python3 scenes/moontrip/make.py still 9.5  -> work/moontrip/still_9.5.png
#
# Times for the mean Earth–Moon distance, 384 400 km, non-stop: walking 5 km/h ≈ 8,8 years; a car at 100 km/h ≈ 160 days;
# a plane at 900 km/h ≈ 18 days; Apollo 11 — about 3 days (launch 16.07.1969 → lunar orbit 19.07); light — 1,28 s.
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
TEX = os.path.join(TOOLS, '../../planetarium/textures')
WORK = os.path.join(TOOLS, 'work/moontrip'); os.makedirs(WORK, exist_ok=True)
OUT = os.path.join(TOOLS, '../moontrip.mp4')
W, H, FPS, DUR = 1080, 1920, 30, 22.0
FONT = os.path.join(TOOLS, 'fonts/Unbounded.ttf'); BRAND = os.path.join(TOOLS, 'fonts/CormorantItalic.ttf')
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'

def plural(n, one, few, many):
    n = abs(int(n)); return one if n % 10 == 1 and n % 100 != 11 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many

# the lanes, slowest at the top: icon, final value, how the counter reads at value v, when it starts, how long it travels
LANES = [
    ('🚶', 8.8, lambda v: f"{int(v)} {plural(v, 'рік', 'роки', 'років')}" if v < 8.8 else '≈ 9 років', 1.4, 2.6),
    ('🚗', 160, lambda v: f"{int(v)} {plural(v, 'день', 'дні', 'днів')}", 4.6, 2.6),
    ('✈️', 18, lambda v: f"{int(v)} {plural(v, 'день', 'дні', 'днів')}", 7.8, 2.6),
    ('🚀', 3, lambda v: f"{int(v)} {plural(v, 'день', 'дні', 'днів')}", 11.0, 2.6),
    ('light', 1.28, lambda v: f"{v:.1f} с".replace('.', ','), 14.4, 0.6),
]
X0, X1 = 175, 905                 # Earth and Moon centres
ROW0, ROWD = 470, 285             # first lane's y and the step

# ---- the bodies: textured spheres, lit from the upper left (drawn at 2× and shrunk for smooth edges)
def sphere(tex, r, lon0, light=(-0.55, 0.45, 0.70), clouds=None, rim=None):
    img = np.asarray(Image.open(tex).convert('RGB'), dtype=np.float32) / 255
    cl = np.asarray(Image.open(clouds).convert('L').resize((img.shape[1], img.shape[0])), dtype=np.float32) / 255 if clouds else None
    n = 2 * r * 2; y, x = np.mgrid[0:n, 0:n]; x = (x + 0.5) / (n / 2) - 1; y = 1 - (y + 0.5) / (n / 2)
    rr = x * x + y * y; inside = rr <= 1; z = np.sqrt(np.clip(1 - rr, 0, 1))
    lat = np.arcsin(np.clip(y, -1, 1)); lon = np.radians(lon0) + np.arctan2(x, z)
    u = ((lon / (2 * np.pi) + 0.5) % 1) * (img.shape[1] - 1); v = (0.5 - lat / np.pi) * (img.shape[0] - 1)
    col = img[v.astype(int), u.astype(int)]
    if cl is not None: c = cl[v.astype(int), u.astype(int)][..., None]; col = col * (1 - 0.8 * c) + 0.95 * c
    L = np.array(light); L = L / np.linalg.norm(L)
    sh = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1)[..., None]
    col = col * (0.06 + 1.0 * sh ** 0.8)
    if rim: col = col + np.array(rim) * ((1 - z) ** 3)[..., None] * (0.3 + sh) * 0.9
    a = np.clip((1 - np.sqrt(rr)) * n / 2, 0, 1) * inside
    out = np.dstack([np.clip(col, 0, 1) ** (1 / 1.1), a]) * 255
    return Image.fromarray(out.astype(np.uint8), 'RGBA').resize((2 * r, 2 * r), Image.LANCZOS)

def glow(r, color, size):   # a soft halo behind a body
    n = 2 * size; y, x = np.mgrid[0:n, 0:n]; d = np.hypot(x - size, y - size)
    a = np.clip(1 - (d - r) / (size - r), 0, 1) ** 2.2 * (d > r * 0.8)
    return Image.fromarray(np.dstack([np.full_like(d, c) for c in color] + [a * 150]).astype(np.uint8), 'RGBA')

EARTH = sphere(os.path.join(TEX, 'earth_day_2k.jpg'), 92, 25, clouds=os.path.join(TEX, 'earth_clouds.png'), rim=(0.25, 0.5, 1.0))
MOON = sphere(os.path.join(TEX, 'moon_2k.jpg'), 50, 0)
EGLOW = glow(92, (70, 140, 255), 135)

# ---- the icons (Noto Color Emoji), turned to face right
def icon(ch, size=104):
    f = ImageFont.truetype(EMOJI, 109); im = Image.new('RGBA', (160, 160)); ImageDraw.Draw(im).text((16, 16), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    if ch in ('🚶', '🚗'): im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if ch in ('✈️', '🚀'): im = im.rotate(-45, resample=Image.BICUBIC, expand=True); im = im.crop(im.getbbox())
    k = size / max(im.size); return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
ICONS = {ch: icon(ch) for ch, *_ in LANES if ch != 'light'}
ICONS['💡'] = icon('💡', 64)

# ---- the still background: deep blue to black, stars
def background():
    g = np.linspace(0, 1, H)[:, None]
    bg = np.dstack([10 + 8 * (1 - g), 14 + 14 * (1 - g), 30 + 30 * (1 - g)]) * np.ones((1, W, 1))
    rng = np.random.default_rng(7); im = Image.fromarray(bg.astype(np.uint8), 'RGB').convert('RGBA'); d = ImageDraw.Draw(im)
    for _ in range(420):
        x, y, b = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.25, 1) ** 2
        r = 0.6 + 1.6 * b; d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(60 + 190 * b)))
    return im
BG = background()

ease = lambda t: 0 if t <= 0 else 1 if t >= 1 else t * t * (3 - 2 * t)
F_TITLE, F_NUM, F_BRAND = ImageFont.truetype(FONT, 66), ImageFont.truetype(FONT, 50), ImageFont.truetype(BRAND, 46)

def text_c(d, xy, s, font, fill, anchor='mm', stroke=0):
    if len(fill) > 3 and fill[3] <= 0: return
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0, fill[3] if len(fill) > 3 else 255))

def frame(t):
    im = BG.copy(); d = ImageDraw.Draw(im, 'RGBA')
    fade = ease(t / 0.6) * (1 - ease((t - (DUR - 0.7)) / 0.7))       # in at the start, out at the end (the loop)
    A = lambda a: int(255 * a * fade)
    # title
    text_c(d, (W // 2, 200), 'Скільки добиратися', F_TITLE, (255, 255, 255, A(1)))
    text_c(d, (W // 2, 285), 'до Місяця?', F_TITLE, (255, 214, 120, A(1)))
    for i, (ch, final, fmt, t0, dur) in enumerate(LANES):
        y = ROW0 + i * ROWD
        appear = ease((t - 0.3 - 0.12 * i) / 0.5) * fade
        if appear <= 0: continue
        # the dotted track
        for x in range(X0 + 110, X1 - 60, 22): d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 255, 255, int(60 * appear)))
        p = ease((t - t0) / dur)
        lay = Image.new('RGBA', (W, H)); ld = ImageDraw.Draw(lay, 'RGBA')
        if ch == 'light':
            bulb = ICONS['💡']; lay.alpha_composite(bulb, (X0 + 150 - bulb.width // 2, y - 95 - bulb.height // 2))
            if p > 0:   # a beam that shoots across, with a glow
                xe = X0 + 95 + (X1 - 50 - X0 - 95) * p
                ld.line((X0 + 95, y, xe, y), fill=(255, 240, 180, 255), width=8)
                ld.ellipse((xe - 14, y - 14, xe + 14, y + 14), fill=(255, 255, 230, 255))
                g = lay.filter(ImageFilter.GaussianBlur(18)); lay = Image.alpha_composite(g, lay); lay = Image.alpha_composite(lay, g)
        else:
            ic = ICONS[ch]; xe = X0 + 120 + (X1 - 210 - X0) * p
            lay.alpha_composite(ic, (int(xe - ic.width / 2), int(y - ic.height / 2)))
        if appear < 1: lay.putalpha(lay.getchannel('A').point(lambda a: int(a * appear)))
        im.alpha_composite(lay)
        im.alpha_composite(_faded(EGLOW, appear), (X0 - 135, y - 135))
        im.alpha_composite(_faded(EARTH, appear), (X0 - 92, y - 92))
        im.alpha_composite(_faded(MOON, appear), (X1 - 50, y - 50))
        # the counter, above the track near the Moon; gold once arrived
        if t >= t0:
            done = p >= 1; v = final * p
            s = fmt(final if done else v)
            col = (255, 214, 120, A(1)) if done else (255, 255, 255, A(0.9))
            if ch == 'light' and done: col = (255, 236, 150, A(1))
            text_c(d, ((X0 + X1) // 2 + 40, y - 92), s, F_NUM, col, stroke=3)
    text_c(d, (W // 2, H - 150), 'Небозві́д', F_BRAND, (255, 214, 160, A(0.85 * ease((t - 16) / 1))))
    return im.convert('RGB')

def _faded(img, a):
    if a >= 1: return img
    c = img.copy(); c.putalpha(c.getchannel('A').point(lambda v: int(v * a))); return c

# ---- sound
def sound(path):
    sr = 48000; n = int(DUR * sr); t = np.arange(n) / sr; out = np.zeros(n)
    # a soft pad: A minor add9, slowly breathing, fading in/out with the picture
    for f, a in ((110, .5), (164.8, .35), (220, .3), (261.6, .25), (329.6, .2), (493.9, .12)):
        out += a * np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.13 * t) * 0.6) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t + f))
    env = np.clip(t / 1.5, 0, 1) * np.clip((DUR - t) / 1.0, 0, 1); out *= 0.05 * env
    rng = np.random.default_rng(3)
    for i, (ch, final, fmt, t0, dur) in enumerate(LANES):
        # a whoosh while travelling: band-limited noise swelling and fading
        m = int(dur * sr); s0 = int(t0 * sr); nz = np.convolve(rng.standard_normal(m + 64), np.ones(64) / 64, 'same')[:m]
        w = np.sin(np.pi * np.arange(m) / m) ** 2
        out[s0:s0 + m] += nz * w * (0.10 if ch != 'light' else 0.25)
        # the bell on arrival, rising lane by lane
        s1 = int((t0 + dur) * sr); k = np.arange(min(int(2.5 * sr), n - s1)) / sr; f = 523.25 * 2 ** (i * 2 / 12)
        bell = (np.sin(2 * np.pi * f * k) + 0.4 * np.sin(2 * np.pi * 2.76 * f * k) * np.exp(-k * 6)) * np.exp(-k * 2.2)
        out[s1:s1 + len(k)] += bell * (0.16 if ch != 'light' else 0.24)
    out = np.tanh(out * 1.5) / 1.5
    st = np.stack([out, out], 1); st = (st / max(1e-9, np.abs(st).max()) * 0.8 * 32767).astype(np.int16)
    with wave.open(path, 'wb') as wf: wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(st.tobytes())

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'still':
        p = os.path.join(WORK, f'still_{sys.argv[2]}.png'); frame(float(sys.argv[2])).save(p); print(p); sys.exit()
    wav = os.path.join(WORK, 'sound.wav'); sound(wav)
    ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-i', wav, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow',
                           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        ff.stdin.write(frame(i / FPS).tobytes())
        if i % 60 == 0: print('frame', i, flush=True)
    ff.stdin.close(); ff.wait(); print(OUT)
