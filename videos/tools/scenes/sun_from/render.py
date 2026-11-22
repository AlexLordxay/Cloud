# «Сонце з…» — 9-second loop, the screen split in three: the Sun from Mercury, Earth and Uranus at the SAME field of view,
# so its size is honest: Mercury 0.387 AU → 2.6× the size we see; Uranus 19.2 AU → 19× smaller (a dazzling point).
# Everything is drawn here (numpy): periodic noise textures, so ground, sea and clouds drift one tile per loop → seamless.
#   python3 render.py frames   -> work/sun_from/frames/f_00000.jpg …      python3 render.py still 4.5 -> work/sun_from/still.jpg
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'sun_from'); FONTS = os.path.join(TOOLS, 'fonts')
W, H, PH = 1080, 1920, 640           # frame, panel height
T, FPS = 9.0, 30
HZ = 405                             # horizon row inside a panel
RE = 40.0                            # the Sun's radius as seen from Earth, px (same lens everywhere)
rng = np.random.default_rng(7)

def pnoise(n, beta, seed):
    """Periodic fractal noise n×n in 0..1 (spectral synthesis)."""
    r = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    f[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j * r.normal(size=(n, n))) / f ** (beta / 2)
    spec[0, 0] = 0
    a = np.real(np.fft.ifft2(spec)); a = (a - a.min()) / (a.max() - a.min())
    return a.astype(np.float32)

N = 512
TEX_A = pnoise(N, 2.6, 1)    # big soft shapes
TEX_B = pnoise(N, 1.8, 2)    # fine detail
TEX_C = pnoise(N, 3.2, 3)    # very soft (clouds)

def samp(tex, u, v):
    """Bilinear sample, u, v in tiles (wrap)."""
    x = (u % 1.0) * N; y = (v % 1.0) * N
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    x0 %= N; y0 %= N; x1 = (x0 + 1) % N; y1 = (y0 + 1) % N
    return (tex[y0, x0] * (1 - fx) * (1 - fy) + tex[y0, x1] * fx * (1 - fy) + tex[y1, x0] * (1 - fx) * fy + tex[y1, x1] * fx * fy)

yy, xx = np.mgrid[0:PH, 0:W].astype(np.float32)

def lerp(a, b, k): return a + (b - a) * k
def col(c): return np.array(c, np.float32) / 255
def grad(stops, k):
    """Colour gradient: stops [(pos, (r,g,b)) …] sampled at k (array)."""
    out = np.zeros(k.shape + (3,), np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (k >= p0) & (k <= p1); w = ((k - p0) / (p1 - p0))[..., None]
        out[m] = (col(c0) + (col(c1) - col(c0)) * w)[m]
    out[k < stops[0][0]] = col(stops[0][1]); out[k > stops[-1][0]] = col(stops[-1][1])
    return out

def sun_disc(img, cx, cy, r, color, limb=0.55, below=None):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    mu = np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))
    a = np.clip(r + 0.8 - d, 0, 1)                         # anti-aliased edge
    if below is not None: a = a * below
    I = (1 - limb * (1 - mu))[..., None] * col(color)
    return img * (1 - a[..., None]) + I * a[..., None]

def glow(img, cx, cy, sig, color, amp):
    g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sig ** 2))[..., None]
    return img + g * col(color) * amp

def stars(seed, n, bright):
    r = np.random.default_rng(seed); s = np.zeros((PH, W), np.float32)
    ys = r.integers(0, HZ - 10, n); xs = r.integers(0, W, n); s[ys, xs] = r.uniform(0.2, 1, n) * bright
    return np.asarray(Image.fromarray((s * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32)[..., None] / 255 * 2.2

STARS_M = stars(11, 260, 0.9)

def persp(y0):
    """Per-row depth for rows below the horizon y0: 0 at the horizon … 1 at the panel bottom."""
    k = np.clip((yy - y0) / (PH - y0), 1e-3, 1)
    return 1 / (k + 0.035), k

# ---------------- Mercury: black sky, white Sun 2.6×, a backlit cratered ridge drifting past ----------------
def mercury(t):
    ph = t / T
    img = np.zeros((PH, W, 3), np.float32) + col((3, 3, 6))
    img += STARS_M * 0.5
    cx, cy, r = 760.0, HZ - 40.0, RE * 2.58
    img = glow(img, cx, cy, 150, (255, 250, 240), 0.10)   # lens glow only — there is no air to scatter light
    img = glow(img, cx, cy, 60, (255, 250, 240), 0.18)
    img = sun_disc(img, cx, cy, r, (255, 253, 247), limb=0.25)
    img = np.where(((xx - cx) ** 2 + (yy - cy) ** 2 < r * r)[..., None], img * 1.25, img)
    # ridge: 1-D periodic profile, drifting one tile per loop
    u = xx[0] / W * 0.55 + ph
    ridge = HZ - 10 - 70 * (samp(TEX_A, u, 0.31) - 0.5) * 2 - 22 * (samp(TEX_B, u * 3, 0.77) - 0.5)
    far = HZ - 30 - 40 * (samp(TEX_A, xx[0] / W * 0.9 + ph * 0.4, 0.63) - 0.5) * 2   # distant hills, slower (parallax)
    hills = yy >= far[None, :]
    img = np.where(hills[..., None], col((20, 19, 19)) + np.exp(-np.clip(yy - far[None, :], 0, None) / 2.5)[..., None] * col((230, 220, 200)) * 0.35, img)
    ground = yy >= ridge[None, :]
    depth, k = persp(HZ - 30)
    gu = (xx - W / 2) / W * depth * 0.18 + ph * 0.55 * 1.0
    gv = depth * 0.05
    tex = 0.6 * samp(TEX_B, gu * 2, gv * 2) + 0.4 * samp(TEX_A, gu, gv)
    base = (0.04 + 0.22 * tex ** 1.5) * (0.6 + 0.6 * k)                      # mostly in shadow: we look into the Sun
    rim = np.exp(-np.clip(yy - ridge[None, :], 0, None) / 4.0) * 1.0     # sunlit edge of the ridge
    h1 = samp(TEX_B, gu * 5, gv * 5); h2 = samp(TEX_B, gu * 5, gv * 5 - 0.006)
    lit = np.clip((h1 - h2) * 45, 0, 1) ** 2.5 * (0.25 + 0.75 * (1 - k)) ** 2            # crater rims catching the low Sun
    gcol = base[..., None] * col((150, 145, 140)) + rim[..., None] * col((255, 245, 225)) * 0.55 + lit[..., None] * col((235, 228, 215)) * 0.3
    img = np.where(ground[..., None], gcol, img)
    return img

# ---------------- Earth: sunset over the sea, the Sun ×1, a glitter path ----------------
SKY_E = [(0.0, (34, 42, 86)), (0.45, (120, 80, 110)), (0.8, (235, 125, 70)), (1.0, (255, 180, 105))]
def earth(t):
    ph = t / T
    k = np.clip(yy / HZ, 0, 1)
    img = grad(SKY_E, k)
    cx, cy, r = 540.0, HZ - 14.0, RE
    img = glow(img, cx, cy, 230, (255, 150, 80), 0.35)
    img = glow(img, cx, cy, 70, (255, 190, 120), 0.45)
    flat = np.clip((HZ - yy) / 1.0, 0, 1)                                  # the sea hides the lower part
    d = np.sqrt((xx - cx) ** 2 + ((yy - cy) / 0.92) ** 2)                  # a little flattened by refraction
    a = np.clip(r + 0.8 - d, 0, 1) * flat
    img = img * (1 - a[..., None]) + col((255, 222, 160))[None, None] * 1.3 * a[..., None]
    # sea
    depth, kk = persp(HZ)
    u = (xx - W / 2) / W * depth * 0.35
    v = depth * 0.06 - ph
    wv = 0.6 * samp(TEX_B, u * 2, v * 6) + 0.4 * samp(TEX_A, u * 0.7, v * 2)
    sea = grad([(0, (210, 120, 80)), (0.08, (120, 70, 70)), (0.5, (40, 32, 48)), (1, (14, 14, 26))], kk)
    sea = sea * (0.7 + 0.6 * wv[..., None])
    width = r * 0.7 + kk * 220
    path = np.exp(-((xx - cx) / width) ** 2)
    gl = samp(TEX_B, u * 14, v * 40 + 0.37) * samp(TEX_B, u * 9 + 0.5, v * 25 - ph)
    glint = np.clip((gl - 0.36) * 9, 0, 1) * path * (1 - 0.3 * kk)
    sea = sea + glint[..., None] * col((255, 210, 150)) * 1.4 + (path * 0.18 * (1 - kk))[..., None] * col((255, 170, 100))
    img = np.where((yy > HZ)[..., None], sea, img)
    return img

# ---------------- Uranus: cyan haze over cloud tops, the Sun 19× smaller — a dazzling point ----------------
SKY_U = [(0.0, (10, 34, 52)), (0.55, (40, 105, 125)), (1.0, (150, 212, 216))]
def uranus(t):
    ph = t / T
    k = np.clip(yy / HZ, 0, 1)
    img = grad(SKY_U, k)
    cx, cy = 560.0, HZ - 95.0
    img = glow(img, cx, cy, 120, (210, 240, 255), 0.10)
    img = glow(img, cx, cy, 22, (235, 248, 255), 0.55)
    img = glow(img, cx, cy, 5, (255, 255, 255), 1.6)
    img = sun_disc(img, cx, cy, RE / 19.2, (255, 255, 255), limb=0.0)
    # thin diffraction spikes (a camera's, so the point reads as the Sun)
    for ang in (0, 90):
        a = math.radians(ang)
        dx, dy = xx - cx, yy - cy
        along = dx * math.cos(a) + dy * math.sin(a); across = -dx * math.sin(a) + dy * math.cos(a)
        sp = np.exp(-(across / 1.1) ** 2) * np.exp(-np.abs(along) / 55)
        img = img + sp[..., None] * col((230, 245, 255)) * 0.9
    # cloud tops
    depth, kk = persp(HZ)
    u = (xx - W / 2) / W * depth * 0.25 + ph * 0.25
    v = depth * 0.03 - ph * 0.75
    c = 0.55 * samp(TEX_C, u, v * 2) + 0.45 * samp(TEX_A, u * 2, v * 5)
    shade = np.clip((c - 0.3) * 3.2, 0, 1)
    cl = grad([(0, (165, 222, 226)), (0.25, (110, 180, 190)), (1, (40, 90, 108))], kk)
    cl = cl * (0.6 + 0.6 * shade[..., None])
    haze = np.exp(-kk * 9)[..., None]
    cl = cl * (1 - haze) + col((160, 218, 222)) * haze
    img = np.where((yy > HZ)[..., None], cl, img)
    return img

def font(name, size): return ImageFont.truetype(os.path.join(FONTS, name), size)
F_TITLE = ImageFont.truetype('/usr/share/fonts/opentype/inter/InterDisplay-Black.otf', 78)
F_NAME = ImageFont.truetype('/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf', 44)
F_K = ImageFont.truetype('/usr/share/fonts/opentype/inter/InterDisplay-Black.otf', 58)
F_LOGO = font('CormorantItalic.ttf', 40)
GOLD = (255, 205, 90)

def text_layer():
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    def put(x, y, s, f, fill, anchor='la', spacing=0):
        if spacing:
            for ch in s:
                d.text((x, y), ch, font=f, fill=fill, anchor=anchor); x += d.textlength(ch, font=f) + spacing
        else: d.text((x, y), s, font=f, fill=fill, anchor=anchor)
    put(W / 2, 54, 'Небозвід', F_LOGO, (240, 205, 160, 235), 'ma')
    put(W / 2, 112, 'СОНЦЕ З…', F_TITLE, GOLD, 'ma')
    put(48, 250, 'МЕРКУРІЯ', F_NAME, (255, 255, 255), spacing=6)
    put(48, 306, 'у 2,6 раза більше', F_K, GOLD)
    put(48, PH + 46, 'ЗЕМЛІ', F_NAME, (255, 255, 255), spacing=6)
    put(48, 2 * PH + 46, 'УРАНА', F_NAME, (255, 255, 255), spacing=6)
    put(48, 2 * PH + 102, 'у 19 разів менше', F_K, GOLD)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sh.paste((0, 0, 0, 190), (0, 0), L.split()[3])
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6))); out.alpha_composite(L)
    return out
TXT = None

def tonemap(a): return 1 - np.exp(-np.clip(a, 0, None) * 1.25)

def frame(t):
    global TXT
    if TXT is None: TXT = text_layer()
    panels = [mercury(t), earth(t), uranus(t)]
    a = np.concatenate(panels, 0)
    a = np.clip(a, 0, None); a = a / (1 + 0.0 * a)
    a = np.clip(np.where(a > 0.92, 0.92 + (1 - np.exp(-(a - 0.92) * 6)) * 0.08, a), 0, 1)   # soft shoulder for the suns
    g = rng.normal(0, 0.008, a.shape[:2] + (1,)).astype(np.float32)                         # a little grain
    im = Image.fromarray((np.clip(a + g, 0, 1) * 255).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(im)
    for y in (PH, 2 * PH): d.rectangle((0, y - 2, W, y + 1), fill=(0, 0, 0, 255))
    im.alpha_composite(TXT)
    return im.convert('RGB')

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'still'
    os.makedirs(WORK, exist_ok=True)
    if mode == 'still':
        t = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
        frame(t).save(os.path.join(WORK, 'still.jpg'), quality=92); print('still', t)
    else:
        fd = os.path.join(WORK, 'frames'); os.makedirs(fd, exist_ok=True)
        n = int(T * FPS)
        for i in range(n):
            frame(i / FPS).save(os.path.join(fd, f'f_{i:05d}.jpg'), quality=93)
            if i % 30 == 0: print('frame', i, '/', n, flush=True)
