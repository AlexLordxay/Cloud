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
            year = int(y0 + (y1 - y0) * ease((t - t0) / (t1 - t0)))
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
    for a, b, text in getattr(sc, 'NAMES', []):
        # the name of what is on screen, up top in the sun colour
        al = ease(fade(t, a, b, getattr(sc, 'CAP_FADE', 0.35)))
        if al > 0: draw_block(img, text, f_name, 330, al, fill=SUN)
    for a, b, text in getattr(sc, 'SUBS', []):
        # a quiet second line under the name (e.g. the mass)
        al = ease(fade(t, a, b, getattr(sc, 'CAP_FADE', 0.35)))
        if al > 0: draw_block(img, text, f_end3, 412, al, fill=(200, 208, 224))
    for a, b, kind, text in sc.CAPTIONS:
        al = ease(fade(t, a, b, getattr(sc, 'CAP_FADE', 0.35)))
        if al <= 0: continue
        if kind == 'hook': draw_block(img, text, hook_font(sc), 520, al, spacing=18)
        else: draw_block(img, text, f_cap, kind if isinstance(kind, (int, float)) else 1400, al)   # a number: own height (rows)
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
