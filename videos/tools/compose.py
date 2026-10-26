# Upscales the recorded frames to 1080x1920 and adds the logo, captions, fades and the end card.
#
#   python3 compose.py <scene>      reads work/<scene>/frames, writes work/<scene>/out
import importlib.util, json, math, os, sys
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TOOLS = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(TOOLS, 'fonts')
FPS, W, H = 30, 1080, 1920
SUN = (243, 185, 100)
LOGO_STOPS = [(0.0, (247, 198, 107)), (0.52, (243, 154, 139)), (1.0, (156, 194, 255))]   # same gradient as on the site
F_STAR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def load_scene(name):
    spec = importlib.util.spec_from_file_location('captions', os.path.join(TOOLS, 'scenes', name, 'captions.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.SCENE = json.load(open(os.path.join(TOOLS, 'scenes', name, 'scene.json')))
    return m

def font(file, size, wght):
    f = ImageFont.truetype(os.path.join(FONTS, file), size)
    try:
        f.set_variation_by_axes([wght if a['name'] in (b'Weight', 'Weight') else a['default'] for a in f.get_variation_axes()])
    except Exception:
        pass
    return f

f_hook = font('Unbounded.ttf', 72, 600)
f_cap = font('Commissioner.ttf', 46, 600)
f_end1 = font('Unbounded.ttf', 70, 600)
f_end2 = font('Commissioner.ttf', 44, 500)
f_end3 = font('Commissioner.ttf', 34, 500)
f_tick = font('Unbounded.ttf', 96, 600)
f_name = font('Unbounded.ttf', 64, 600)
f_small = font('Commissioner.ttf', 26, 500)

f_btn = font('Commissioner.ttf', 40, 700)
f_tease = font('Unbounded.ttf', 50, 600)

_hooks = {}
def hook_font(sc):
    # HOOK_SIZE in captions.py: a bigger opening title
    size = getattr(sc, 'HOOK_SIZE', 72)
    if size not in _hooks: _hooks[size] = font('Unbounded.ttf', size, 600)
    return _hooks[size]

def ease(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def fade(t, a, b, d=0.35):
    return max(0.0, min(1.0, (t - a) / d, (b - t) / d))

def draw_block(img, text, fnt, cy, alpha, fill=(255, 255, 255), spacing=14):
    if alpha <= 0: return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    box = d.multiline_textbbox((0, 0), text, font=fnt, align='center', spacing=spacing)
    x, y = (W - (box[2] - box[0])) / 2 - box[0], cy - (box[3] - box[1]) / 2 - box[1]
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).multiline_text((x, y + 3), text, font=fnt, fill=(0, 0, 0, int(230 * alpha)), align='center', spacing=spacing)
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    img.alpha_composite(sh); img.alpha_composite(sh)
    d.multiline_text((x, y), text, font=fnt, fill=fill + (int(255 * alpha),), align='center', spacing=spacing)
    img.alpha_composite(lay)

def logo_layer(size):
    # The site's wordmark: Cormorant Italic Bold with the dawn-to-night gradient; a star replaces the dot of "і".
    f = font('CormorantItalic.ttf', size, 700)
    pre, i_, post = 'Небозв', 'ı', 'д'
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    wpre = d0.textlength(pre, font=f)
    box = d0.textbbox((0, 0), pre + i_ + post, font=f)
    pad = int(size * 0.6)
    w, h = box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad
    ox, oy = pad - box[0], pad - box[1]
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text((ox, oy), pre + i_ + post, font=f, fill=255)
    grad = Image.new('RGB', (w, h)); gd = ImageDraw.Draw(grad)
    x0, x1 = ox + box[0], ox + box[2]
    for x in range(w):
        u = min(1, max(0, (x - x0) / max(1, x1 - x0)))
        for (a, ca), (b, cb) in zip(LOGO_STOPS, LOGO_STOPS[1:]):
            if a <= u <= b:
                k = (u - a) / (b - a); col = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3))
        gd.line([(x, 0), (x, h)], fill=col)
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    lay.paste(grad, (0, 0), mask)
    ib = d0.textbbox((ox + wpre, oy), i_, font=f)
    return lay, ((ib[0] + ib[2]) / 2 + size * 0.05, ib[1] - size * 0.2)

LOGOS = {}
def draw_logo(img, size, cy, alpha, t):
    if alpha <= 0: return
    if size not in LOGOS: LOGOS[size] = logo_layer(size)
    lay, (sx, sy) = LOGOS[size]
    lay = lay.copy()
    sf = ImageFont.truetype(F_STAR, max(6, int(size * 0.36 * (0.86 + 0.14 * math.sin(t * 1.4)))))   # gently twinkling
    star = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(star).text((sx, sy), '✦', font=sf, fill=(255, 255, 255, 255), anchor='mm')
    glow = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(glow).text((sx, sy), '✦', font=sf, fill=(170, 205, 255, 255), anchor='mm')
    lay.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size * 0.08))); lay.alpha_composite(star)
    if alpha < 1: lay.putalpha(lay.getchannel('A').point(lambda v: int(v * alpha)))
    x, y = int((W - lay.size[0]) / 2), int(cy - lay.size[1] / 2)
    shadow = Image.new('RGBA', lay.size, (0, 0, 0, 0)); shadow.putalpha(lay.getchannel('A').point(lambda v: int(v * 0.8)))
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sh.paste(shadow, (x, y + 3))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    img.alpha_composite(lay, (x, y))

# ---- the subscribe button: a red pill with a bell; a tap (a ripple), it turns grey 'Ви підписані' and the bell rings ----
def bell_layer(px, col):
    # a bell icon, drawn 4x and scaled down: a knob, a dome flaring to a rim, the clapper below
    S = 4 * px; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = col + (255,)
    d.ellipse((S * 0.44, S * 0.06, S * 0.56, S * 0.18), fill=c)
    pts = [(S * 0.5 + S * 0.3 * math.sin(a) * (0.55 + 0.45 * (1 - math.cos(a)) / 2), S * 0.15 + S * 0.62 * (1 - math.cos(a)) / 2) for a in [k / 20 * math.pi for k in range(21)]]
    body = [(S * 0.5, S * 0.15)] + [(x, y) for x, y in pts] + [(S * 0.86, S * 0.77), (S * 0.14, S * 0.77)] + [(S - x, y) for x, y in reversed(pts)]
    d.polygon(body, fill=c)
    d.rounded_rectangle((S * 0.1, S * 0.72, S * 0.9, S * 0.8), radius=S * 0.04, fill=c)
    d.ellipse((S * 0.41, S * 0.8, S * 0.59, S * 0.96), fill=c)
    return im.resize((px, px), Image.LANCZOS)

_BELLS = {}
def draw_subscribe(img, cx, cy, tl, dur, align='left', scale=1.0):
    # tl: seconds since the button appeared; it stays dur seconds. align 'left': cx is its left edge, it slides in.
    a_in, a_out = ease(tl / 0.35), 1 - ease((tl - (dur - 0.4)) / 0.4)
    al = max(0.0, min(a_in, a_out))
    if al <= 0: return
    tap = 0.75
    done = tl >= tap
    press = 1 - 0.07 * max(0.0, 1 - abs(tl - tap) / 0.12)
    sc = scale * press
    text = 'Ви підписані' if done else 'Підписатися'
    fill = (62, 66, 76) if done else (229, 31, 31)
    f = f_btn if scale == 1 else font('Commissioner.ttf', int(40 * scale), 700)
    d0 = ImageDraw.Draw(img)
    tw = d0.textlength(text, font=f)
    bh = int(84 * sc); bw = int(tw + 150 * sc); ix = int(56 * sc)
    lay = Image.new('RGBA', (bw + 40, bh + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((20, 20, 20 + bw, 20 + bh), radius=bh // 2, fill=fill + (int(235 * al),))
    key = (ix, done)
    if key not in _BELLS: _BELLS[key] = bell_layer(ix, (255, 255, 255))
    bell = _BELLS[key]
    ang = 24 * math.sin(2 * math.pi * 5 * (tl - tap - 0.05)) * math.exp(-3 * (tl - tap - 0.05)) if tl > tap + 0.05 else 0
    b = bell.rotate(ang, resample=Image.BICUBIC, center=(ix / 2, ix * 0.12))
    if al < 1: b.putalpha(b.getchannel('A').point(lambda v: int(v * al)))
    lay.alpha_composite(b, (20 + int(26 * sc), 20 + (bh - ix) // 2))
    d.text((20 + int(26 * sc) + ix + int(18 * sc), 20 + bh / 2), text, font=f, fill=(255, 255, 255, int(255 * al)), anchor='lm')
    x = int(cx - 40 * (1 - a_in)) if align == 'left' else int(cx - (bw + 40) / 2)
    y = int(cy - (bh + 40) / 2)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); shl = Image.new('RGBA', lay.size, (0, 0, 0, 0)); shl.putalpha(lay.getchannel('A').point(lambda v: int(v * 0.6)))
    sh.paste(shl, (x, y + 4)); img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    img.alpha_composite(lay, (x, y))
    if tap - 0.05 < tl < tap + 0.45:   # the tap: a ripple from the middle of the button
        u = (tl - tap + 0.05) / 0.5; r = 18 + 70 * u * sc
        rp = Image.new('RGBA', img.size, (0, 0, 0, 0)); ex, ey = x + 20 + bw * 0.62, y + 20 + bh / 2
        ImageDraw.Draw(rp).ellipse((ex - r, ey - r, ex + r, ey + r), outline=(255, 255, 255, int(200 * (1 - u) * al)), width=max(2, int(5 * sc)))
        ImageDraw.Draw(rp).ellipse((ex - 14 * sc, ey - 14 * sc, ex + 14 * sc, ey + 14 * sc), fill=(255, 255, 255, int(150 * max(0.0, 1 - u * 2) * al)))
        img.alpha_composite(rp)

def frame(sc, i, src):
    t = i / FPS
    im = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
    # dips to black at cuts, at the start and at the end; the scene dims under the end card
    # FADE_IN = 0 in captions.py: no fade from black, so the first frame (the one the feed shows) is already the picture
    fade_in = getattr(sc, 'FADE_IN', 0.6)
    k = min(1.0, t / fade_in) if fade_in else 1.0
    for c in sc.CUTS:
        # a cut is a time, or (time, half-width) for a longer fade through black
        c, half = c if isinstance(c, tuple) else (c, 0.28)
        k = min(k, abs(t - c) / half)
    if t > sc.END_CARD: k = min(k, 1 - 0.72 * min(1.0, (t - sc.END_CARD) / 0.8))
    k = min(k, max(0.0, (sc.DURATION - t) / 0.5))
    if k < 1: im = Image.eval(im, lambda v: int(v * k))
    img = im.convert('RGBA')
    draw_logo(img, 64, 170, (min(1.0, t) if fade_in else 1.0) * (1 if t < sc.END_CARD else max(0, 1 - (t - sc.END_CARD) / 0.5)) * 0.92, t)
    tick = getattr(sc, 'TICKER', None)
    # a year counter (e.g. a ten-year flight), eased like the scene's date; TICKER is one (t0, t1, y0, y1)
    # or a list of (t0, t1, y0, y1, show from, show to)
    for tk in ([tick + (tick[0] - 0.4, tick[1] + 0.8)] if isinstance(tick, tuple) else tick or []):
        t0, t1, y0, y1, a, b = tk
        if a < t < b:
            year = int(y0 + (y1 - y0) * getattr(sc, 'TICKER_EASE', ease)((t - t0) / (t1 - t0)))   # TICKER_EASE: to follow a scene's own easing
            draw_block(img, str(year), f_tick, 330, fade(t, a, b, 0.4), fill=SUN)
    clock = getattr(sc, 'CLOCK_SHOW', None)
    if clock:
        # time of day on the scene clock (scene.json "clock": [[video s, minutes after 00:00 UTC], ...]), linear between keys
        keys = sc.SCENE['clock']
        m = keys[-1][1]
        for (t0, m0), (t1, m1) in zip(keys, keys[1:]):
            if t <= t1: m = m0 + (m1 - m0) * max(0.0, (t - t0) / (t1 - t0)); break
        m = int(m + sc.CLOCK_UTC_OFFSET * 60) % 1440
        for a, b in clock:
            al = fade(t, a, b, 0.4)
            if al > 0:
                draw_block(img, f'{m // 60:02d}:{m % 60:02d}', f_tick, 330, al, fill=SUN)
                draw_block(img, sc.CLOCK_LABEL, f_end3, 420, al, fill=(200, 208, 224))
    cnt = getattr(sc, 'COUNTER', None)
    if cnt:
        # a live counter: per_s × seconds since the start, e.g. the km the Earth has flown while you watch
        a, b = cnt['show']
        al = fade(t, a, b, 0.4)
        if al > 0:
            draw_block(img, f"{int(cnt['per_s'] * t):,}".replace(',', '\u202f'), f_tick, 330, al, fill=SUN)
            draw_block(img, cnt['label'], f_end3, 420, al, fill=(200, 208, 224))
    for a, b, t0, t1, stop, done in getattr(sc, 'TIMERS', []):
        # a stopwatch that speeds up from t0 and stops at t1 on `stop` seconds (then it turns `done`, a colour):
        # 0:07, 12:30, 8:00:00
        al = ease(fade(t, a, b, 0.3))
        if al > 0:
            x = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
            k = math.log(max(stop, 2.0))                      # the longer the time, the harder it accelerates
            v = int(stop * (math.exp(k * x) - 1) / (math.exp(k) - 1) + 0.5)
            txt = f'{v // 60}:{v % 60:02d}' if v < 3600 else f'{v // 3600}:{v // 60 % 60:02d}:{v % 60:02d}'
            draw_block(img, txt, f_tick, 1190, al, fill=done if x >= 1 else (255, 255, 255))
    for a, b, text in getattr(sc, 'NAMES', []):
        # the name of what is on screen, up top in the sun colour
        al = ease(fade(t, a, b, getattr(sc, 'CAP_FADE', 0.35)))
        if al > 0: draw_block(img, text, f_name, 330, al, fill=SUN)
    for a, b, text in getattr(sc, 'SUBS', []):
        # a quiet second line under the name (e.g. the mass)
        al = ease(fade(t, a, b, getattr(sc, 'CAP_FADE', 0.35)))
        if al > 0: draw_block(img, text, f_end3, 412, al, fill=(200, 208, 224))
    # DRAW in captions.py: a scene's own drawing over the frame (img, t, these helpers), under the captions
    draw = getattr(sc, 'DRAW', None)
    if draw: draw(img, t, globals())
    for a, b, kind, text in sc.CAPTIONS:
        al = ease(fade(t, a, b, getattr(sc, 'CAP_FADE', 0.35)))
        if al <= 0: continue
        if kind == 'hook': draw_block(img, text, hook_font(sc), 520, al, spacing=18)
        else: draw_block(img, text, f_cap, kind if isinstance(kind, (int, float)) else 1400, al)   # a number: own height (rows)
    # SUBSCRIBE_AT in captions.py: a small subscribe button mid-video (top left, clear of the Shorts buttons), 2.4 s
    sub = getattr(sc, 'SUBSCRIBE_AT', None)
    if sub is not None and sub <= t < sub + 2.4:
        draw_subscribe(img, 60, getattr(sc, 'SUBSCRIBE_Y', 290), t - sub, 2.4)
    for a, b, text in getattr(sc, 'CREDITS', []):
        # small print at the bottom (whose picture, artist's view)
        al = ease(fade(t, a, b, 0.5))
        if al > 0: draw_block(img, text, f_small, 1830, al * 0.8, fill=(180, 188, 205))
    if t > sc.END_CARD:
        e = lambda delay: max(0.0, min(1.0, (t - sc.END_CARD - delay) / 0.6))
        draw_block(img, sc.END_TITLE, f_end1, 700, e(0.3), spacing=16)
        draw_logo(img, 120, 920, e(0.9), t)
        draw_block(img, 'посилання в профілі', f_end2, 1050, e(0.9), fill=SUN)
        draw_block(img, 'автор: lord-xay', f_end3, 1130, e(1.5), fill=(200, 208, 224))
        # NEXT_TEASE in captions.py: what comes next, and the subscribe button (it gets tapped) under it
        tease = getattr(sc, 'NEXT_TEASE', None)
        if tease:
            draw_block(img, tease, f_tease, 1280, e(1.1), fill=(255, 255, 255))
            if t > sc.END_CARD + 1.3: draw_subscribe(img, W / 2, 1400, t - sc.END_CARD - 1.3, 99, align='center', scale=1.15)
    return img.convert('RGB')

def _job(args):
    name, f = args
    sc = load_scene(name)
    work = os.path.join(TOOLS, 'work', name)
    frame(sc, int(f[2:7]), os.path.join(work, 'frames', f)).save(os.path.join(work, 'out', f), quality=92)

if __name__ == '__main__':
    name = sys.argv[1]
    work = os.path.join(TOOLS, 'work', name)
    os.makedirs(os.path.join(work, 'out'), exist_ok=True)
    files = sorted(f for f in os.listdir(os.path.join(work, 'frames')) if f.endswith('.jpg'))
    with Pool(os.cpu_count()) as p: p.map(_job, [(name, f) for f in files], chunksize=20)
    print('composed', len(files), 'frames')
