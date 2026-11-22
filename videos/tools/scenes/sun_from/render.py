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

# ---------------- Mercury: black sky, white Sun 2.6×, a still cratered plain (no air, no water — nothing moves) ----------------
def _mercury_ground():
    """Static regolith with craters and rocks, lit from behind by the low Sun (we look towards it): dark ground,
    bright rims and stone tops, shadows falling towards the camera."""
    y0 = HZ - 30
    depth, k = persp(y0)
    gu = (xx - W / 2) / W * depth * 0.18
    gv = depth * 0.05
    tex = 0.5 * samp(TEX_B, gu * 6, gv * 6) + 0.3 * samp(TEX_B, gu * 2, gv * 2) + 0.2 * samp(TEX_A, gu, gv)
    shade = (0.06 + 0.2 * tex) * (0.55 + 0.6 * k)
    h1 = samp(TEX_B, gu * 9, gv * 9); h2 = samp(TEX_B, gu * 9, gv * 9 - 0.004)
    shade += np.clip((h1 - h2) * 30, 0, 1) ** 2 * 0.10 * (1 - 0.6 * k)                   # grainy sunlit edges
    r = np.random.default_rng(5)
    def put_ellipse(cx, cy, rx, ry):
        return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    def sstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
    # rocks: small lumps with a bright top edge and a short shadow towards us
    for _ in range(120):
        kc = r.uniform(0.06, 0.95)
        cy = y0 + kc * (PH - y0); cx = r.uniform(0, W)
        rx = r.uniform(2.5, 11.0) * (0.35 + 1.6 * kc); ry = rx * r.uniform(0.45, 0.7)
        e = put_ellipse(cx, cy, rx, ry); q = np.sqrt(e)
        body = sstep((1 - q) / 0.3)
        top = np.exp(-((q - 0.85) / 0.18) ** 2) * sstep((cy - yy) / ry + 0.2)
        sh = sstep(1 - np.sqrt(put_ellipse(cx, cy + ry * 1.3, rx * 1.05, ry * 1.6))) * sstep((yy - cy) / ry)
        shade = shade * (1 - 0.5 * sh) * (1 - 0.45 * body) + top * body.clip(0.3, 1) * 0.22
    # a few low crater rims on the plain, seen edge-on against the light: thin bright arcs over dark ground
    for _ in range(9):
        kc = r.uniform(0.12, 0.75); cy = y0 + kc * (PH - y0); cx = r.uniform(80, W - 80)
        rx = r.uniform(60, 220) * (0.4 + kc); ry = rx * (0.08 + 0.3 * kc)
        q = np.sqrt(put_ellipse(cx, cy, rx, ry))
        far = sstep(0.5 - (yy - cy) / (ry * 1.4))
        shade = shade * (1 - 0.35 * sstep((1 - q) / 0.3)) + np.exp(-((q - 1) / 0.05) ** 2) * far * 0.11
    return shade

def _mercury_static():
    img = np.zeros((PH, W, 3), np.float32) + col((3, 3, 6))
    img += STARS_M * 0.5
    cx, cy, r = 760.0, HZ - 40.0, RE * 2.58
    img = glow(img, cx, cy, 150, (255, 250, 240), 0.10)   # lens glow only — there is no air to scatter light
    img = glow(img, cx, cy, 60, (255, 250, 240), 0.18)
    img = sun_disc(img, cx, cy, r, (255, 253, 247), limb=0.25)
    img = np.where(((xx - cx) ** 2 + (yy - cy) ** 2 < r * r)[..., None], img * 1.25, img)
    u = xx[0] / W * 0.55
    far = HZ - 30 - 40 * (samp(TEX_A, xx[0] / W * 0.9, 0.63) - 0.5) * 2                 # distant hills
    img = np.where((yy >= far[None, :])[..., None], col((16, 15, 15)) + np.exp(-np.clip(yy - far[None, :], 0, None) / 2.5)[..., None] * col((230, 220, 200)) * 0.35, img)
    ridge = HZ - 10 - 70 * (samp(TEX_A, u, 0.31) - 0.5) * 2 - 22 * (samp(TEX_B, u * 3, 0.77) - 0.5)
    ground = yy >= ridge[None, :]
    shade = _mercury_ground()
    rim = np.exp(-np.clip(yy - ridge[None, :], 0, None) / 4.0)                            # sunlit edge of the ridge
    gcol = shade[..., None] * col((165, 158, 150)) + rim[..., None] * col((255, 245, 225)) * 0.55
    return np.where(ground[..., None], gcol, img)

MERC = None
def mercury(t):
    """Nothing moves on Mercury (no air, no water): the panel is one still picture."""
    global MERC
    if MERC is None: MERC = _mercury_static()
    return MERC


WAVES = None
def _waves():
    r = np.random.default_rng(21); ws = []
    for i in range(26):
        lam = 0.012 * (1.55 ** (i % 13)) * r.uniform(0.85, 1.15)          # wavelength in ground units (Z ~ depth)
        ang = r.normal(0, 0.45)                                           # direction mostly towards the viewer
        kx, kz = math.sin(ang) * 2 * math.pi / lam, math.cos(ang) * 2 * math.pi / lam
        amp = 0.010 * lam ** 0.85 / 0.012 ** 0.85 * 0.012                 # gentle: steepness falls with size
        n = int(r.integers(1, 4)) * (1 if r.random() < 0.5 else -1)       # whole cycles per loop
        ws.append((kx, kz, amp, 2 * math.pi * n / T, r.uniform(0, 2 * math.pi)))
    return ws

SEA_Y0 = HZ
_dep, _kk = None, None
def sea_layer(t, sx, sr):
    global WAVES, _dep, _kk
    if WAVES is None: WAVES = _waves()
    if _dep is None: _dep, _kk = persp(SEA_Y0)
    depth, kk = _dep, _kk
    X = (xx - W / 2) / W * depth * 1.2; Z = depth
    fz = depth ** 2 / (PH - SEA_Y0) * 1.0; fx = depth / W * 1.2          # ground size of one pixel
    sz = np.zeros_like(xx); sx_ = np.zeros_like(xx)
    for kx, kz, a, w, p in WAVES:
        att = np.exp(-((kz * fz) ** 2 + (kx * fx) ** 2) * 0.6)            # fade waves smaller than a pixel
        c = np.cos(kx * X + kz * Z - w * t + p) * a * att
        sz += c * kz; sx_ += c * kx
    # reflected sky: tilt of the facet changes which part of the sky we see
    refl_k = np.clip(1 - (0.10 + 0.9 * kk) * 0.55 - sz * 0.9, 0, 1)
    skyc = grad(SKY_E, refl_k)
    fres = 0.18 + 0.82 * np.exp(-kk * 3.5)                                 # grazing angles mirror the sky
    deep = col((14, 20, 34))
    sea = deep * (1 - fres[..., None]) + skyc * fres[..., None]
    sea = sea * (0.85 + 1.6 * sz[..., None]).clip(0.4, 1.6)
    # Sun's path: glints where the slope towards the viewer matches what's needed to bounce the low Sun into the eye
    need = 0.02 + kk * 0.20
    width = sr * 0.6 + kk * 260
    lateral = np.exp(-((xx - sx) / width) ** 2)
    g = np.exp(-((sz - need) / (0.016 + 0.045 * kk)) ** 2) * np.exp(-((sx_ - (xx - sx) / W * 0.12) / 0.05) ** 2)
    glint = (g ** 1.6) * lateral * (1.9 - 0.9 * kk)
    sea = sea + glint[..., None] * col((255, 222, 170)) * 1.8
    sea = sea + (np.exp(-((xx - sx) / (sr * 1.0 + kk * 140)) ** 2) * np.exp(-kk * 4) * 0.45)[..., None] * col((255, 190, 120))
    return sea

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
    # sea: a sum of directional sine swells (looping: every wave makes a whole number of cycles in T), filtered by the
    # pixel footprint so the far ones fade into a smooth mirror instead of aliasing; the water reflects the sky (more
    # at grazing angles), and the Sun's path is many small glints where a facet tilts just right.
    sea = sea_layer(t, cx, r)
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
