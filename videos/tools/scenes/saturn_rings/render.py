# «Кільця Сатурна» — every frame (1080x1920). Saturn is ray-traced here: an oblate globe (polar radius 0.902) with the
# site's texture, the rings in their plane (saturn_ring.png spans 1.24–2.27 Saturn radii, as on the site) with the rings'
# shadow on the globe and the globe's shadow on the rings; stars, labels and the globe sprite come from real_motion/render.py.
#   A  0–4.3    the rings turn edge-on and vanish («1612 року кільця Сатурна зникли»)
#   B  4.0–8.7  Galileo's view (a simulation: a small blurry telescope image) 1610 → 1612
#   C  8.4–14.2 the camera sinks into the ring plane; then D2 13.8–17.9 Hubble's edge-on picture (PIA01273)
#   D  17.6–27.2 ring rain along the magnetic field lines (artist's visualisation), then the rings fade away
#   E  27.0–33.9 the rings gathered into one ball beside Saturn (~316 km — true scale), the camera zooms in to it
#   F  33.6–39.7 Daphnis: Cassini PIA21056 → the wave shadows of 2009, PIA11656
#   G  39.4–50.2 «The Day the Earth Smiled», Cassini PIA17172
#   python3 render.py [workers] [frame …] -> work/saturn_rings/frames/f_%05d.jpg
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(TOOLS, 'scenes', 'real_motion')]
import render as R
from render import sm, ramp, win, lerp, nrm, stars_bg, to_img, over, add, label, A, W, H, glowdot, lines
R.PLF['ice'] = 'enceladus.jpg'
OUT = os.path.join(TOOLS, 'work', 'saturn_rings', 'frames')
FPS = 30
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']
C_POL = 0.902                     # Saturn's polar / equatorial radius
R_IN, R_OUT = 1.24, 2.27

def asset(name):
    key = 'sat:' + name
    if key not in R._A:
        Image.MAX_IMAGE_PIXELS = None
        R._A[key] = Image.open(os.path.join(HERE, 'assets', name)).convert('RGB')
    return R._A[key]

def ring_tex():
    if 'sat:ring' not in R._A:
        r = np.asarray(Image.open(os.path.join(R.TEX, 'saturn_ring.png')).convert('RGBA'), np.float32) / 255
        r = r[r.shape[0] // 2]
        col = r[:, :3] / max(1e-3, r[:, :3].mean()) * np.array([0.78, 0.70, 0.58])     # warm, as Cassini sees them
        R._A['sat:ring'] = (np.clip(col, 0, 1.4), r[:, 3])
    return R._A['sat:ring']

def ring_at(rho):
    col, al = ring_tex(); n = len(al)
    k = (rho - R_IN) / (R_OUT - R_IN); on = (k >= 0) & (k <= 1)
    i = (np.clip(k, 0, 1) * (n - 1)).astype(int)
    return col[i], al[i] * on

def saturn(cam_pos, target, fov, sun, ring_k=1.0, spin=0.0, up=(0, 0, 1), bg=None, scale=1.0):
    """ray-traced Saturn (+rings) over bg (H x W x 3 float); camera in Saturn radii; sun: unit vector to the Sun"""
    S = nrm(sun); o = np.asarray(cam_pos, float)
    f = nrm(np.asarray(target, float) - o); r = nrm(np.cross(f, up)); u = np.cross(r, f)
    k = (H / 2) / math.tan(math.radians(fov) / 2)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    X = (xs - W / 2) / k; Y = -(ys - H / 2) / k
    d = f[None, None, :] + X[..., None] * r + Y[..., None] * u
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    img = np.zeros((H, W, 3), np.float32) if bg is None else bg.copy()
    # the globe: scale z by 1/c → unit sphere
    oc = o * np.array([1, 1, 1 / C_POL]); dc = d * np.array([1, 1, 1 / C_POL])
    a = (dc ** 2).sum(-1); b = (dc * oc).sum(-1); c = (oc ** 2).sum() - 1
    disc = b * b - a * c
    hit = disc > 0
    tp = np.where(hit, (-b - np.sqrt(np.maximum(disc, 0))) / a, np.inf)
    hit &= tp > 0
    # the rings
    dz = d[..., 2]
    okz = np.abs(dz) > 1e-7
    tr = np.where(okz, -o[2] / np.where(okz, dz, 1), 1e9)
    P_r = o + tr[..., None] * d
    rho = np.hypot(P_r[..., 0], P_r[..., 1])
    rcol, ral = ring_at(rho)
    ral = ral * (tr > 0) * okz * (tr < 1e8) * ring_k
    # planet colour
    P = o + np.where(hit, tp, 0)[..., None] * d
    N = P * np.array([1, 1, 1 / C_POL ** 2]); N /= np.linalg.norm(N, axis=-1, keepdims=True) + 1e-9
    lat = np.arcsin(np.clip(P[..., 2] / np.linalg.norm(P, axis=-1).clip(1e-6), -1, 1)); lon = np.arctan2(P[..., 1], P[..., 0]) + spin
    tex = A('tex:saturn.jpg'); th, tw = tex.shape[:2]
    pc = tex[((0.5 - lat / np.pi) * (th - 1)).astype(int).clip(0, th - 1), (((lon / (2 * np.pi)) % 1) * (tw - 1)).astype(int).clip(0, tw - 1)]
    mu = (N * S).sum(-1); lam = np.clip(mu, 0, 1)
    view = np.clip(-(N * d).sum(-1), 0, 1)
    shade = 0.012 + 1.05 * lam ** 0.8 * (0.55 + 0.45 * view ** 0.3)
    # the rings' shadow on the globe
    if abs(S[2]) > 1e-4:
        ts = -P[..., 2] / S[2]
        Q = P + ts[..., None] * S
        _, qa = ring_at(np.hypot(Q[..., 0], Q[..., 1]))
        shade = shade * (1 - 0.88 * qa * (ts > 0) * ring_k)
    # ring-shine onto the night side, a faint warm glow
    shade = shade + 0.035 * ring_k * np.clip(-mu, 0, 1) * (abs(S[2]) > 0.02)
    pcol = pc * shade[..., None] * 1.08
    # ring colour: lit face reflects, unlit face lets light through the thin parts
    same = np.sign(o[2]) == np.sign(S[2]) if abs(S[2]) > 1e-4 else False
    elev = abs(S[2]) ** 0.35
    if same: rlit = rcol * (0.18 + 0.95 * elev)
    else: rlit = rcol * (0.12 + 1.6 * elev * (1 - ral) * ral * 3.0)[..., None]
    # the globe's shadow on the rings
    Pr = np.where(okz[..., None], P_r, 0)
    ocs = Pr * np.array([1, 1, 1 / C_POL]); Sc = S * np.array([1, 1, 1 / C_POL])
    a2 = (Sc ** 2).sum(); b2 = (ocs * Sc).sum(-1); c2 = (ocs ** 2).sum(-1) - 1
    disc2 = b2 * b2 - a2 * c2
    shadow = (disc2 > 0) & ((-b2 - np.sqrt(np.maximum(disc2, 0))) / a2 > 0)
    rlit = rlit * np.where(shadow, 0.04, 1.0)[..., None]
    # compose: rings in front of the globe, or the globe hiding the rings behind it
    front = ral > 0
    ring_front = front & (~hit | (tr < tp))
    out = np.where(hit[..., None], pcol, img)
    out = np.where(ring_front[..., None], rlit * ral[..., None] + out * (1 - ral[..., None]), out)
    return out * scale

def cam_orbit(dist, elev_deg, az_deg=-90.0, target=(0, 0, 0)):
    e, az = math.radians(elev_deg), math.radians(az_deg)
    return np.array(target) + dist * np.array([math.cos(e) * math.cos(az), math.cos(e) * math.sin(az), math.sin(e)])

SUN = nrm([0.85, -0.35, 0.36])                   # the Sun ~21° above the rings, from the right-front

# ---------------------------------------------------------------- A: the rings turn edge-on
def shot_A(t):
    el = lerp(20.0, 0.0, sm((t - 0.2) / 3.6))
    pos = cam_orbit(9.4 - 0.3 * t, el, -90 + 4 * t)
    bg = stars_bg(dx=t * 4, dy=60, k=0.7)
    return to_img(saturn(pos, (0, 0, 0), 52, SUN, spin=0.05 * t, bg=bg))

# ---------------------------------------------------------------- B: through Galileo's telescope (a simulation)
def shot_B(t):
    tilt = 11.0 if t < 6.4 else lerp(11.0, 0.0, sm((t - 6.4) / 0.9))
    pos = cam_orbit(60, tilt, -90)
    img = saturn(pos, (0, 0, 0), 30, nrm([0.3, -1, math.sin(math.radians(tilt))]), spin=0.0)
    # a small 20x lens of 1610: blur, a soft chromatic halo, a shimmer of the air
    sh = 2.0 * math.sin(t * 9.0) + 1.2 * math.sin(t * 13.7)
    im = to_img(img).filter(ImageFilter.GaussianBlur(9 + 1.5 * math.sin(t * 7)))
    a = np.asarray(im, np.float32) / 255
    halo = np.asarray(im.filter(ImageFilter.GaussianBlur(28)), np.float32) / 255
    a = a * 1.15 + halo * np.array([0.25, 0.18, 0.35])
    a = np.roll(a, int(sh), axis=1)
    yy, xx = np.mgrid[0:H, 0:W]; rr = np.hypot(xx - W / 2, yy - 900)
    a = a * np.clip((430 - rr) / 30, 0, 1)[..., None] + np.clip((rr - 430) / 6, 0, 1)[..., None] * 0.0
    ring = (np.abs(rr - 432) < 3).astype(np.float32) * 0.25
    return to_img(a + ring[..., None] * np.array([0.7, 0.7, 0.75]))

# ---------------------------------------------------------------- C: sinking into the ring plane
def shot_C(t):
    el = lerp(14.0, 0.0, sm((t - 8.5) / 4.6))
    pos = cam_orbit(7.4 - 0.15 * (t - 8.4), el, -70 + 1.5 * (t - 8.4))
    bg = stars_bg(dx=200 + t * 3, dy=40, k=0.65)
    return to_img(saturn(pos, (0.2, 0, 0), 50, SUN, spin=0.05 * t, bg=bg))

def shot_D2(t):
    """Hubble's edge-on Saturn (PIA01273, 892x459): fitted to the width, slowly pushed in"""
    im = asset('PIA01273.jpg'); z = 1.0 + 0.12 * sm((t - 13.8) / 4.1)
    w = W * 1.9 * z; h = w * im.size[1] / im.size[0]
    big = im.resize((int(w), int(h)), Image.LANCZOS)
    cv = Image.new('RGB', (W, H), (0, 0, 0)); cv.paste(big, (int(W / 2 - w * 0.5), int(820 - h / 2)))
    return cv

# ---------------------------------------------------------------- D: ring rain, then the rings fade away
FIELD = []
for L_ in np.linspace(1.35, 1.9, 4):
    lam_end = math.acos(1 / math.sqrt(L_))
    for phi in np.radians(np.arange(-75, 76, 30)) - math.pi / 2:
        for hemi in (1, -1):
            lams = np.linspace(0, lam_end, 60) * hemi
            rr = L_ * np.cos(lams) ** 2
            FIELD.append(np.stack([rr * np.cos(lams) * np.cos(phi), rr * np.cos(lams) * np.sin(phi), rr * np.sin(lams)], 1))

def visible(P, o):
    """points not hidden behind the globe, seen from o"""
    d = P - o; L = np.linalg.norm(d, axis=-1, keepdims=True); d = d / L
    oc = o * np.array([1, 1, 1 / C_POL]); dc = d * np.array([1, 1, 1 / C_POL])
    a = (dc ** 2).sum(-1); b = (dc * oc).sum(-1); c = (oc ** 2).sum() - 1
    disc = b * b - a * c
    t0 = (-b - np.sqrt(np.maximum(disc, 0))) / a
    return ~((disc > 0) & (t0 > 0) & (t0 < L[..., 0] - 1e-3))

def shot_D(t):
    pos = cam_orbit(7.6 - 0.08 * (t - 17.6), 17.0, -100 + 1.2 * (t - 17.6))
    fade = 1 - sm((t - 22.6) / 3.8)
    bg = stars_bg(dx=120 + t * 3, dy=100, k=0.65)
    img = saturn(pos, (0, 0, 0), 50, SUN, ring_k=fade, spin=0.05 * t, bg=bg)
    rk = win(t, 18.2, 25.6, 0.8)
    if rk > 0:
        cam = R.Cam(pos, (0, 0, 0), fov=50)
        segs = []
        for j, Fp in enumerate(FIELD):
            vis = visible(Fp, pos)
            x, y, z = cam.proj(Fp)
            ph = (t * 0.5 + j * 0.137) % 1.0                  # a drop sliding down each line
            n = len(Fp)
            for q in range(n - 1):
                if not (vis[q] and vis[q + 1]): continue
                pos_k = q / (n - 1)
                glow = 0.07 + 0.9 * math.exp(-((pos_k - ph) / 0.05) ** 2)   # faint lines, a bright drop sliding down
                segs.append(([(x[q], y[q]), (x[q + 1], y[q + 1])], rk * glow * 0.6))
        lines(img, segs, (0.5, 0.72, 1.0), width=1, k=0.9)
    return to_img(img)

# ---------------------------------------------------------------- E: the rings gathered into one icy ball
BALL = np.array([1.9, -2.4, 1.0]); BALL_R = 158.0 / 60268.0      # a ball of 316 km, Saturn radii
_PARTS = None
def parts():
    global _PARTS
    if _PARTS is None:
        rng = np.random.default_rng(5); col, al = ring_tex()
        rr = rng.uniform(R_IN, R_OUT, 9000); keep = rng.random(9000) < ring_at(rr)[1]
        rr = rr[keep][:3000]; ph = rng.uniform(0, 2 * np.pi, len(rr))
        _PARTS = np.stack([rr * np.cos(ph), rr * np.sin(ph), np.zeros_like(rr)], 1), rng.uniform(0, 0.35, len(rr))
    return _PARTS

def shot_E(t):
    gather = sm((t - 27.5) / 2.6)
    pan = sm((t - 29.9) / 1.3)                                  # turn to the ball…
    zoom = sm((t - 30.9) / 2.7)                                 # …and fly in to it
    pos0 = cam_orbit(9.0, 20.0, -95)
    # swing round onto the Saturn–ball line (Saturn right behind the ball), then fly in along it
    d0 = np.linalg.norm(pos0 - BALL)
    dirn = R.nrm(lerp(R.nrm(pos0 - BALL), R.nrm(BALL), pan))
    dist = math.exp(lerp(math.log(d0), math.log(0.6), zoom))
    pos = BALL + dirn * dist
    tgt = lerp(np.array([0.3, 0, 0]), BALL, pan)
    fov = math.exp(lerp(math.log(52), math.log(3.6), zoom))
    bg = stars_bg(dx=60 + t * 2, dy=150, k=0.65)
    img = saturn(pos, tgt, fov, SUN, ring_k=1 - gather, spin=0.05 * t, bg=bg)
    cam = R.Cam(pos, tgt, fov=fov)
    if 0 < gather < 1:
        P0, delay = parts()
        g = np.clip((gather - delay) / (1 - delay.max() + 1e-6), 0, 1)[:, None]
        g = g * g * (3 - 2 * g)
        Pp = P0 * (1 - g) + BALL * g
        x, y, z = cam.proj(Pp)
        dots = np.zeros((H, W), np.float32)
        ok = (x >= 1) & (x < W - 1) & (y >= 1) & (y < H - 1)
        np.add.at(dots, (y[ok].astype(int), x[ok].astype(int)), 0.6)
        dots = np.asarray(Image.fromarray(np.clip(dots * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255 * 2.5
        img += dots[..., None] * np.array([1.0, 0.92, 0.8]) * (1 - sm((gather - 0.85) / 0.15))
    x, y, z = cam.proj(BALL); rpx = cam.k * BALL_R / z[0]
    kb = sm((t - 29.4) / 0.8)
    if kb > 0:
        if rpx >= 1.5: over(img, R.globe('ice', rpx, cam.r, cam.u, -cam.f, SUN, spin=0.3), x[0], y[0])
        glowdot(img, x[0], y[0], 2.2, (1.0, 0.98, 0.92), 1.4 * kb * (1 - sm((rpx - 1) / 3)))
    small = kb * (1 - sm((rpx - 4) / 8))
    im = to_img(img).convert('RGBA')
    if small > 0:
        dd = ImageDraw.Draw(im); rr_ = 26
        dd.ellipse((x[0] - rr_, y[0] - rr_, x[0] + rr_, y[0] + rr_), outline=(255, 235, 200, int(220 * small)), width=3)
    label(im, x[0], y[0] + max(rpx, 26) + 44, '~300 км', 30, a=kb * sm((t - 30.2) / 0.6))
    return im.convert('RGB')

# ---------------------------------------------------------------- F: Daphnis (Cassini)
def kb_crop(im, t0, t1, t, cx, cy, z0, z1):
    """a portrait window of a picture, centred near (cx, cy) (fractions), zooming z0 → z1"""
    k = sm((t - t0) / (t1 - t0)); z = lerp(z0, z1, k)
    sw, sh = im.size; h = sh / z; w = h * W / H
    if w > sw: w = sw / z; h = w * H / W
    x0 = min(max(cx * sw - w / 2, 0), sw - w); y0 = min(max(cy * sh - h / 2, 0), sh - h)
    return im.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BICUBIC)

def shot_F(t):
    a = kb_crop(asset('PIA21056.jpg'), 33.6, 37.4, t, 0.66, 0.74, 1.0, 1.25)
    b = kb_crop(asset('PIA11656.jpg'), 36.6, 39.7, t, 0.55, 0.45, 1.0, 1.15)
    return Image.blend(a, b, sm((t - 36.6) / 0.8))

# ---------------------------------------------------------------- G: the Day the Earth Smiled (Cassini, 2013)
def shot_G(t):
    im = asset('PIA17172.jpg')
    # from the globe, pull back a little and drift across the rings
    k = sm((t - 39.4) / 7.0)
    return kb_crop(im, 39.4, 47.0, t, lerp(0.47, 0.53, k), 0.5, 1.0, 1.12)

SHOTS = [(0.0, 4.3, shot_A), (3.8, 8.9, shot_B), (8.2, 14.3, shot_C), (13.6, 17.9, shot_D2), (17.2, 27.2, shot_D),
         (27.0, 34.0, shot_E), (33.3, 39.9, shot_F), (39.1, 99, shot_G)]          # dissolves of 0.5–0.8 s

_BAND = {}
def bands(cap_y=1445):
    """a soft darkening behind the name lines (y 290–450) and the captions (cap_y ± 110), so white text reads on bright shots"""
    if cap_y not in _BAND:
        y = np.arange(H, dtype=np.float32)
        b = 0.5 * np.exp(-((y - 370) / 110) ** 2) + 0.6 * np.exp(-((y - cap_y) / 150) ** 2)
        _BAND[cap_y] = (1 - b)[:, None, None]
    return _BAND[cap_y]

def frame(t):
    act = [(a, b, f) for a, b, f in SHOTS if a <= t <= b]
    if len(act) == 1: im = act[0][2](t)
    else:
        (a1, b1, f1), (a2, b2, f2) = act[0], act[-1]
        im = Image.blend(f1(t), f2(t), sm((t - a2) / (b1 - a2)))
    a = np.asarray(im, np.float32) / 255
    lum = a.mean(-1, keepdims=True)
    k = win(t, 33.75, 39.15, 0.4)                     # Daphnis: the caption goes up (the moon sits low in the picture)
    band = bands(1445) * (1 - k) + bands(640) * k
    return to_img(a * (1 - (1 - band) * np.clip(lum * 2.2, 0, 1)))       # only where the picture is bright

def job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return
    frame(i / FPS).save(p + '.tmp.jpg', quality=93); os.replace(p + '.tmp.jpg', p)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * FPS)
    todo = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()) as pool:
        for c, _ in enumerate(pool.imap_unordered(job, todo, chunksize=2)):
            if c % 60 == 0: print('frame', c, '/', len(todo), flush=True)
    print('frames done', n)
