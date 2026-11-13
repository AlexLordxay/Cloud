# «Ядерна зима: що каже наука» — every frame (1080x1920) of one continuous camera flight, no cuts:
#   high over the Arctic at night (city lights round the rim) → a cascade of detonations across the northern hemisphere
#   (flash, light on the clouds, shock ring, rising cap) → the camera dives to one of them: the fireball and the mushroom
#   cloud, then fire columns → back up to orbit: smoke plumes everywhere → the soot spreads round the planet over weeks
#   (week counter in captions.py) → the Earth dims and browns, snow spreads in summer, fields die → far away, a dim grey
#   world → it must not happen: the Earth turns back to blue.
# Science: soot 150 Tg, lofted to the stratosphere, global in weeks, >8 °C cooling (Robock 2007, Coupe 2019, Xia 2022).
# Geometry: Earth radius 1, Earth-fixed frame (z = north). Maps: work/nuclear_winter/{day,night}.npy (textures.py).
#   python3 render.py [workers] [frame …]   -> work/nuclear_winter/frames/f_%05d.jpg
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(TOOLS, 'scenes', 'real_motion')]
import render as R
from render import sm, ramp, win, lerp, nrm, stars_bg
WORK = os.path.join(TOOLS, 'work', 'nuclear_winter'); OUT = os.path.join(WORK, 'frames')
W, H, FPS = 1080, 1920, 30
DUR = json.load(open(os.path.join(HERE, 'scene.json')))['duration']

def ll(lat, lon):
    a, b = math.radians(lat), math.radians(lon)
    return np.array([math.cos(a) * math.cos(b), math.cos(a) * math.sin(b), math.sin(a)])

DEC, SUBLON = -18.0, 125.0                      # mid-November: the Sun over the tropics south, the Americas and Europe at night
SUN = ll(DEC, SUBLON)

# ---------------------------------------------------------------- maps (shared through mmap)
_M = {}
def maps():
    if not _M:
        _M['day'] = np.load(os.path.join(WORK, 'day.npy'), mmap_mode='r')
        _M['night'] = np.load(os.path.join(WORK, 'night.npy'), mmap_mode='r')
        # coarse helpers (2048x1024): land mask, city lights, clouds
        d = np.asarray(_M['day'][::8, ::8], np.float32) / 255
        n = np.asarray(_M['night'][::8, ::8], np.float32) / 255
        land = ((d[..., 2] < d[..., 0] * 1.05 + 0.04) | (d.mean(-1) > 0.55)).astype(np.float32)
        land = np.asarray(Image.fromarray((land * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
        _M['land'] = land
        lights = np.clip((n - 0.20) / 0.6, 0, 1); lights[:24] = 0; lights[-24:] = 0
        _M['lights_c'] = lights
        cl = np.asarray(Image.open(os.path.join(R.TEX, 'earth_clouds.png')).convert('L').resize((2048, 1024), Image.BICUBIC), np.float32) / 255
        rng = np.random.default_rng(11); det = np.zeros((1024, 2048), np.float32)
        for s, a in ((256, 0.5), (64, 0.3), (16, 0.2)):
            z = rng.random((1024 // s + 2, 2048 // s + 2)).astype(np.float32)
            det += np.asarray(Image.fromarray((z * 255).astype(np.uint8)).resize((2048 + 2 * s, 1024 + 2 * s), Image.BICUBIC), np.float32)[s:1024 + s, s:2048 + s] / 255 * a
        _M['clouds'] = np.clip((cl * 1.3 - 0.15) * (0.6 + 0.8 * det), 0, 1)
        # the polar caps: clouds on a flat map seen from above the pole (no seam, no pinch at the pole), matched to the
        # cloud cover of the 60–75° band
        band = _M['clouds'][int(1024 * 15 / 180):int(1024 * 30 / 180)].mean()
        cap = np.zeros((1024, 1024), np.float32)
        for s_, a_ in ((128, 0.5), (48, 0.3), (16, 0.2)):
            z = rng.random((1024 // s_ + 2, 1024 // s_ + 2)).astype(np.float32)
            cap += np.asarray(Image.fromarray((z * 255).astype(np.uint8)).resize((1024 + 2 * s_, 1024 + 2 * s_), Image.BICUBIC), np.float32)[s_:1024 + s_, s_:1024 + s_] / 255 * a_
        cap = np.clip((cap - cap.mean()) * 2.4 + band, 0, 1)
        _M['cap'] = cap
    return _M

def sample(img, u, v, bil=True):
    """img: H x W (x C) array (0..255 or float); u, v in [0,1) (u wraps)"""
    h, w = img.shape[:2]
    x = (u % 1.0) * w - 0.5; y = np.clip(v * h - 0.5, 0, h - 1.001)
    if not bil:
        return np.asarray(img[y.astype(int), x.astype(int) % w], np.float32)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0); fy = (y - y0)
    x0 %= w; x1 = (x0 + 1) % w; y1 = np.minimum(y0 + 1, h - 1)
    a = np.asarray(img[y0, x0], np.float32); b = np.asarray(img[y0, x1], np.float32)
    c = np.asarray(img[y1, x0], np.float32); d = np.asarray(img[y1, x1], np.float32)
    if a.ndim > fx.ndim: fx, fy = fx[..., None], fy[..., None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy

# ---------------------------------------------------------------- the events
rng = np.random.default_rng(2026)
def pick_targets(n):
    """n points among the city lights of 25–65 °N (all continents alike), spread out"""
    L = maps()['lights_c']; h, w = L.shape
    lat = 90 - (np.arange(h) + 0.5) / h * 180
    wts = L * ((lat > 25) & (lat < 65))[:, None]
    p = (wts / wts.sum()).ravel()
    idx = rng.choice(len(p), size=n * 6, p=p)
    pts = []
    for i in idx:
        y, x = divmod(i, w); la, lo = 90 - (y + 0.5) / h * 180, (x + 0.5) / w * 360 - 180
        v = ll(la, lo)
        if all(np.dot(v, q) < math.cos(math.radians(3.2)) for q, _, _ in pts):
            pts.append((v, la, lo))
        if len(pts) == n: break
    return pts

FOCUS_LL = (45.5, -99.0)                          # the close-up: open country, no city to recognise
FOCUS = ll(*FOCUS_LL)
_EV = None
def events():
    """flashes: (unit vector, t0, energy); the cascade speeds up from 10.9 s to 15.4 s; one at the focus at 13.6 s"""
    global _EV
    if _EV is None:
        pts = pick_targets(140)
        # what the camera sees while the cascade runs: most flashes there (in frame), a few beyond the limb's glow
        seen = lambda v, t: float(v @ nrm(cam_at(t)[0])) > 0.45
        vis = [q for q in pts if seen(q[0], 11.8)]; rest = [q for q in pts if not seen(q[0], 11.8)]
        pick = vis[:46] + rest[:14]
        ts = 10.9 + 4.5 * np.sort(rng.random(len(pick))) ** 0.6
        _EV = [(v, float(t0), float(rng.uniform(0.6, 1.3))) for (v, la, lo), t0 in zip(pick, ts)]
        _EV.append((FOCUS, 13.6, 1.6))
        # the hook: one flash at 0.9 s, well inside the frame — among the lights nearest the middle of the view
        p0, g0, up0, fov0 = cam_at(0.9); fwd = nrm(g0 - p0)
        def score(v):
            d = nrm(v - p0); return float(d @ fwd) if seen(v, 0.9) else -9
        hook = max(pts, key=lambda q: score(q[0]))[0]
        _EV.insert(0, (hook, 0.9, 1.4))
    return _EV

def flash_curve(dt):
    """light of a detonation dt s after it: a blinding first flash, a second slower pulse, then the fireball's glow"""
    if dt < 0: return 0.0, 0.0
    first = math.exp(-dt / 0.06) * 6.0
    second = (1 - math.exp(-dt / 0.35)) * math.exp(-dt / 1.1) * 2.2
    glow = math.exp(-dt / 3.5) * 0.35 * (dt > 0.2)
    white = first + second * 0.6
    return white + second + glow, min(1.0, dt / 1.2)          # intensity, "orangeness"

# ---------------------------------------------------------------- the world's state over time
def state(t):
    """weeks of spreading, soot cover, snow, dead fields, city lights left, 'restoration' at the end"""
    weeks = 4.0 * sm((t - 28.6) / 5.4) + 2.0 * sm((t - 34.0) / 10.0)
    restore = sm((t - 58.6) / 3.2)
    soot = min(1.0, weeks / 4.0) * (1 - restore)
    snow = sm((t - 37.5) / 6.5) * (1 - restore)
    crops = sm((t - 45.0) / 5.0) * (1 - restore)
    dim = (0.62 * sm((t - 33.6) / 3.0)) * (1 - restore)             # the Sun's light reaching the ground
    out = sm((t - 12.0) / 10.0) * 0.6 + 0.35 * sm((t - 24.0) / 12.0)  # city lights going out
    return dict(weeks=weeks, soot=soot, snow=snow, crops=crops, dim=dim, lights_out=min(0.95, out) * (1 - restore), restore=restore)

def soot_map(weeks, lat, lon):
    """soot column 0..1 at (lat, lon) arrays: fire sources → zonal band in ~2 weeks → whole hemisphere → the south"""
    if weeks <= 0: return np.zeros_like(lat)
    D = np.zeros_like(lat)
    sl = math.radians(min(180.0, 6 + 70 * weeks ** 1.4))           # zonal spread (wraps round the globe)
    sy = 3.0 + 7.0 * weeks                                          # meridional spread, degrees
    for v, t0, e in events()[1:]:
        la = math.degrees(math.asin(v[2])); lo = math.degrees(math.atan2(v[1], v[0]))
        dlon = np.radians((lon - lo - 25 * weeks + 180) % 360 - 180)   # carried east
        D += e * np.exp(-(dlon / sl) ** 2) * np.exp(-((lat - la) / sy) ** 2)
    band = np.exp(-((lat - 45) / (12 + 14 * weeks)) ** 2) * sm(weeks / 3.0)
    south = sm((weeks - 3.0) / 3.0) * np.exp(-((lat + 25) / 35) ** 2)
    return np.clip(D * 0.25 * min(1, weeks * 2) + band * 0.95 + south * 0.7, 0, 1)

# ---------------------------------------------------------------- the Earth, ray-traced
ATM = 1.018            # the visible atmosphere's top (exaggerated a little, as in every orbital photo)
def earth(o, f, r, u, k, t, S, st, flashes, bg):
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    X = (xs - W / 2) / k; Y = -(ys - H / 2) / k
    d = f[None, None] + X[..., None] * r + Y[..., None] * u
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    b = (d * o).sum(-1); c = (o * o).sum() - 1
    disc = b * b - c
    hit = (disc > 0) & (-b - np.sqrt(np.maximum(disc, 0)) > 0)
    tp = -b - np.sqrt(np.maximum(disc, 0))
    P = o + np.where(hit, tp, 0)[..., None] * d
    lat = np.degrees(np.arcsin(np.clip(P[..., 2], -1, 1))); lon = np.degrees(np.arctan2(P[..., 1], P[..., 0]))
    U = (lon + 180) / 360; V = (90 - lat) / 180
    M = maps()
    out = bg.copy()
    hm = hit
    if hm.any():
        Uh, Vh, lat_h, lon_h = U[hm], V[hm], lat[hm], lon[hm]
        Ph = P[hm]; dh = d[hm]
        day = (sample(M['day'], Uh, Vh) / 255) ** 2.0
        night = sample(M['night'], Uh, Vh) / 255
        land = sample(M['land'], Uh, Vh)
        pm = np.clip((84 - np.abs(lat_h)) / 18, 0, 1)                              # near the poles: the planar cap clouds
        capc = sample(M['cap'], (Ph[:, 0] * 1.6 + 1) / 2 % 1.0, np.clip((Ph[:, 1] * 1.6 + 1) / 2, 0, 0.999))
        cl = sample(M['clouds'], Uh, Vh) * pm + capc * (1 - pm)
        mu = Ph @ S
        lit = np.clip((mu + 0.10) / 0.95, 0, 1) ** 1.3                            # a soft twilight band, no hard circle
        view = np.clip(-(Ph * dh).sum(-1), 0, 1)
        # the world's wounds
        if st['soot'] > 0:
            wisp = sample(M['clouds'], (Uh + 0.37 + 0.02 * st['weeks']) % 1.0, np.clip(Vh * 0.97 + 0.01, 0, 0.999))
            soot = soot_map(st['weeks'], lat_h, lon_h) * st['soot'] * (0.55 + 0.6 * wisp)
            soot = np.clip(soot, 0, 0.92)
        else: soot = np.zeros_like(lat_h)
        if st['crops'] > 0:
            green = np.clip((day[:, 1] - day[:, 0]) * 6, 0, 1) * land * np.exp(-((np.abs(lat_h) - 40) / 22) ** 2)
            dead = np.array([0.20, 0.15, 0.09]) ** 2.0
            day = day * (1 - green[:, None] * st['crops'] * 0.85) + dead * green[:, None] * st['crops'] * 0.85
        if st['snow'] > 0:
            edge = 64 - 22 * st['snow']                                  # snow line creeping south in July
            s_ = sm(1) * np.clip((np.abs(lat_h) * np.sign(lat_h + 1e-6) - edge) / 6 + 0.5, 0, 1) * land
            s_ = np.maximum(s_, np.clip((lat_h - edge + 8) / 10, 0, 1) * land * 0.0)
            day = day * (1 - s_[:, None] * 0.9) + np.array([0.85, 0.88, 0.92]) * s_[:, None] * 0.9
        sun_k = 1 - st['dim']
        ground = day * (lit * sun_k)[:, None] * 1.25
        # oceans: a soft sun glint
        refl = 2 * mu[:, None] * Ph - S
        spec = np.clip(-(refl * dh).sum(-1), 0, 1) ** 60 * (1 - land) * 0.6 * sun_k * (mu > 0)
        ground = ground + spec[:, None] * np.array([1.0, 0.95, 0.85])
        # city lights on the night side, going out after the war
        lights = np.clip((night - 0.22) / 0.55, 0, 1) ** 1.6
        nightk = np.clip(-mu * 6 + 0.25, 0, 1)
        far = 1 + 0.5 * float(np.clip((np.linalg.norm(o) - 1.5) / 2.0, 0, 1))      # exposure for the far views
        ground = ground + lights[:, None] * np.array([1.0, 0.70, 0.36]) * 1.6 * far * nightk[:, None] * (1 - st['lights_out']) * (1 - cl[:, None] * 0.6)
        # clouds (dimmed with the Sun), then the soot over them (stratospheric: dark brown, a little lit)
        ccol = np.array([1.0, 1.0, 1.0]) * (lit * sun_k * 1.05 + 0.012)[:, None]
        g = ground * (1 - cl[:, None] * 0.85) + ccol * cl[:, None] * 0.85
        # moonlight / airglow so the night side is not pure black
        g = g + (day * 0.0025 + cl[:, None] * 0.004) * nightk[:, None]
        # the detonations: light falling on clouds and ground round each one
        for fv, inten, orng in flashes:
            d2 = np.clip(1 - Ph @ fv, 0, 2) * 2 * 6371.0 ** 2               # (distance in km)^2
            fall = inten * 0.45 * 20.0 ** 2 / (d2 + 20.0 ** 2) + min(inten, 6.0) * 0.06 * 160.0 ** 2 / (d2 + 160.0 ** 2)   # + the flash scattered over the cloud deck
            col = np.array([0.85, 0.92, 1.0]) * (1 - orng) + np.array([1.0, 0.55, 0.22]) * orng
            g = g + fall[:, None] * col * (0.35 + 0.9 * cl[:, None])
        soot_col = np.array([0.20, 0.14, 0.09]) * (lit * sun_k * 0.9 + 0.02)[:, None]
        g = g * (1 - soot[:, None] * 0.82) + soot_col * soot[:, None] * 0.82
        # the air seen edge-on near the limb
        haze = (1 - view) ** 3 * np.clip(mu * 2 + 0.3, 0, 1) * sun_k
        hcol = np.array([0.30, 0.55, 1.0]) * (1 - st['soot']) + np.array([0.35, 0.25, 0.16]) * st['soot']
        g = g * (1 - haze[:, None] * 0.55) + hcol * haze[:, None] * 0.55
        out[hm] = g
    # the limb: a glowing shell of air (blue on the day side; brown, thick and dark once the soot is up)
    bb = np.sqrt(np.maximum(c - b * b + 1, 0))                          # closest approach of each ray to the centre
    tc = -b
    shell = (~hit | True) & (bb < ATM) & (tc > 0)
    if shell.any():
        Pc = o + tc[..., None] * d
        Pc = Pc / np.maximum(np.linalg.norm(Pc, axis=-1, keepdims=True), 1e-9)   # the ray through the centre: no 0/0
        mu_c = (Pc * S).sum(-1)
        h_ = np.clip((bb - 1) / (ATM - 1), 0, 1)
        dens = np.exp(-h_ * 3.2) * np.clip((ATM - bb) / (ATM - 1), 0, 1) * (~hit)
        day_c = np.clip(mu_c * 3 + 0.35, 0, 1)
        blue = np.array([0.25, 0.5, 1.0]); red = np.array([1.0, 0.45, 0.2])
        tw = np.exp(-(mu_c / 0.12) ** 2)[..., None]
        col = blue * (1 - tw) + red * tw
        sootc = np.array([0.30, 0.20, 0.12])
        col = col * (1 - st['soot']) + sootc * st['soot']
        k_ = (dens * day_c * (1 - st['dim'] * 0.6) * 1.1)[..., None]
        out = out + col * k_ * shell[..., None]
        # airglow: the thin green-gold line round the night limb (as in every ISS night photo)
        hg = (bb - 1) / (ATM - 1)
        ag = np.exp(-((hg - 0.62) / 0.07) ** 2) * (~hit) * np.clip(-mu_c * 4, 0, 1) * (1 - 0.7 * st['soot']) * float(np.clip((np.linalg.norm(o) - 1.15) / 0.5, 0, 1))
        out = out + ag[..., None] * np.array([0.30, 0.55, 0.25]) * 0.22 * shell[..., None]
    return out, hit, P

# ---------------------------------------------------------------- volumetric-looking puffs (mushroom cloud, smoke)
_PUFF = []
def puff_tex(i=0):
    """4 soft, lumpy puff sprites (alpha, 'top-lit' mask), 128 px"""
    if not _PUFF:
        S = 128; yy, xx = (np.mgrid[0:S, 0:S] - S / 2 + 0.5) / (S / 2)
        rr = np.sqrt(xx * xx + yy * yy)
        for v in range(4):
            g = np.random.default_rng(40 + v)
            n = np.zeros((S, S), np.float32)
            for s_, a in ((40, 0.45), (20, 0.3), (10, 0.17), (5, 0.08)):
                z = g.random((S // s_ + 2, S // s_ + 2)).astype(np.float32)
                n += np.asarray(Image.fromarray((z * 255).astype(np.uint8)).resize((S + 2 * s_, S + 2 * s_), Image.BICUBIC), np.float32)[s_:S + s_, s_:S + s_] / 255 * a
            a_ = np.clip((1 - rr ** 1.5) * 1.5, 0, 1) * np.clip(n * 2.0 - 0.45 + (1 - rr) * 0.5, 0, 1)
            top = np.clip(0.5 - yy * 0.55 + (n - 0.5) * 0.6, 0, 1)
            _PUFF.append((a_.astype(np.float32), top.astype(np.float32)))
    return _PUFF[i % 4]

def draw_puffs(img, puffs):
    """puffs: list of (x, y, radius px, depth, rgb_top, rgb_bottom, alpha), drawn far → near"""
    for idx, (x, y, rp, z, ct, cb, al) in enumerate(sorted(puffs, key=lambda p: -p[3])):
        a0, top = puff_tex(int(x * 7 + y * 3) % 4)
        if rp < 0.7 or al <= 0.01: continue
        n = max(3, int(rp * 2))
        if x + n < 0 or x - n > W or y + n < 0 or y - n > H: continue
        A_ = np.asarray(Image.fromarray((a0 * 255).astype(np.uint8)).resize((n, n), Image.BILINEAR), np.float32) / 255 * al
        T_ = np.asarray(Image.fromarray((top * 255).astype(np.uint8)).resize((n, n), Image.BILINEAR), np.float32)[..., None] / 255
        col = np.array(ct) * T_ + np.array(cb) * (1 - T_)
        x0 = int(x - n / 2); y0 = int(y - n / 2)
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + n), min(H, y0 + n)
        if xa >= xb or ya >= yb: continue
        sa = A_[ya - y0:yb - y0, xa - x0:xb - x0, None]; sc = col[ya - y0:yb - y0, xa - x0:xb - x0]
        img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - sa) + sc * sa

def tangent(v):
    e = nrm(np.cross([0, 0, 1], v)); n_ = np.cross(v, e)
    return e, n_

KM = 1 / 6371.0
_MUSH = None
def mushroom_puffs():
    """the puffs of one mushroom cloud in the local frame (east, north, up; km), with a phase each for the rolling cap"""
    global _MUSH
    if _MUSH is None:
        g = np.random.default_rng(9); P = []
        for i in range(420):                         # the cap: a rolling torus
            a = g.uniform(0, 2 * math.pi); b = g.uniform(0, 2 * math.pi)
            P.append(('cap', a, b, g.uniform(0.7, 1.15)))
        for i in range(170):                         # the stem
            P.append(('stem', g.uniform(0, 2 * math.pi), g.uniform(0, 1), g.uniform(0.7, 1.2)))
        for i in range(140):                         # the skirt of dust at the foot
            P.append(('base', g.uniform(0, 2 * math.pi), g.uniform(0.2, 1), g.uniform(0.7, 1.3)))
        _MUSH = P
    return _MUSH

def mushroom(dt, v, cam, scale_km=1.0):
    """projected puffs of the cloud dt s after the detonation at v (unit vector) — time compressed: it rises in ~6 s"""
    if dt <= 0: return []
    e, n_ = tangent(v)
    rise = 1 - math.exp(-dt / 2.2)
    H_cap = (4 + 34 * rise) * scale_km                    # cap centre height, km
    Rcap = (2 + 13 * rise) * scale_km; rtube = Rcap * 0.45
    fire = math.exp(-dt / 2.5)
    out = []
    for kind, a, b, s in mushroom_puffs():
        if kind == 'cap':
            roll = b + dt * 0.8
            rr_ = Rcap + rtube * math.cos(roll); hh = H_cap + rtube * 0.8 * math.sin(roll)
            p = (rr_ * math.cos(a), rr_ * math.sin(a), hh); rad = rtube * 0.95 * s
            warm = 0.5 + 0.5 * math.sin(roll)                # the underside glows
        elif kind == 'stem':
            hh = b * H_cap * 0.92; w_ = (0.25 + 0.2 * (1 - b)) * Rcap * 0.55
            p = (w_ * math.cos(a), w_ * math.sin(a), hh); rad = w_ * 1.3 * s; warm = 1 - b
        else:
            rr_ = (0.4 + b * 1.6) * Rcap * rise; p = (rr_ * math.cos(a), rr_ * math.sin(a), 1.2 * scale_km * s); rad = Rcap * 0.3 * s; warm = 0.15
        X = v * (1 + p[2] * KM) + e * p[0] * KM + n_ * p[1] * KM
        x, y, z = cam.proj(X)
        if z[0] <= 0.0001: continue
        rp = cam.k * rad * KM / z[0]
        # night: the cloud is lit only from within — a hot orange core and underside, dark smoky tops
        hot = np.array([1.0, 0.45, 0.12]) * (3.2 * fire * warm ** 2.2 + 0.08 * fire)
        smoke = np.array([0.045, 0.040, 0.037]) * (0.6 + 0.4 * s)
        top = smoke + hot * 0.18; bot = smoke * 0.7 + hot
        out.append((float(x[0]), float(y[0]), rp, float(z[0]), tuple(top), tuple(bot), 0.9))
    return out

def fire_plumes(t, cam, near_only=False):
    """smoke columns rising from the burning cities (pyrocumulus), each a chain of dark puffs carried east as they rise"""
    out = []
    for i, (v, t0, e) in enumerate(events()[1:]):
        dt = t - t0 - 1.2
        if dt <= 0: continue
        e1, n1 = tangent(v)
        grow = 1 - math.exp(-dt / 4.0)
        top = 30 * grow                                    # km — into the stratosphere
        for j in range(9):
            q = (j + 0.5) / 9
            hh = top * q; drift = 18 * q * q * grow
            X = v * (1 + hh * KM) + e1 * drift * KM + n1 * (math.sin(i * 7 + j) * 2) * KM
            x, y, z = cam.proj(X)
            if z[0] <= 0: continue
            rad = (4 + 10 * q) * (0.6 + 0.6 * e)
            rp = cam.k * rad * KM / z[0]
            glow = math.exp(-q * 4) * (0.8 + 0.2 * math.sin(t * 9 + i))
            out.append((float(x[0]), float(y[0]), rp, float(z[0]), (0.16, 0.13, 0.11), (0.16 + 0.9 * glow, 0.10 + 0.35 * glow, 0.05 + 0.08 * glow), 0.75))
    return out

# ---------------------------------------------------------------- the camera: one continuous flight
def cam_at(t):
    """position, look-at, up — keyframes eased in between (positions slerped on the sphere + radius in log)"""
    F = FOCUS
    eF, nF = tangent(F)
    keys = [
        # t, position, target, up, fov — the night hemisphere from over the Atlantic, the limb and stars above
        (0.0, ll(76, -40) * 3.5, ll(62, -40) * 0.2, ll(0, 140), 46),
        (10.6, ll(74, -55) * 3.2, ll(60, -55) * 0.25, ll(0, 125), 46),
        (12.6, ll(52, -85) * 2.1, ll(46, -92) * 0.6, [0, 0, 1], 42),
        # the dive: low, a little east of the focus, looking west along the ground at it
        (15.2, F * (1 + 140 * KM) + eF * 330 * KM - nF * 60 * KM, F * (1 + 14 * KM), F, 44),
        (19.6, F * (1 + 120 * KM) + eF * 260 * KM - nF * 50 * KM, F * (1 + 20 * KM), F, 46),
        # back up to orbit: the burning hemisphere
        (24.0, ll(32, -70) * 2.2, ll(45, -60) * 0.5, [0, 0, 1], 44),
        # round to the terminator and the day side as the soot spreads (the whole disk in frame)
        (31.0, ll(30, 30) * 5.4, [0, 0, 0], [0, 0, 1], 40),
        (37.0, ll(25, 75) * 5.6, [0, 0, 0], [0, 0, 1], 40),
        # closer over the farmland (mid-latitude day side)
        (46.0, ll(30, 95) * 2.5, ll(42, 100) * 0.7, [0, 0, 1], 44),
        (52.6, ll(30, 108) * 2.5, ll(42, 112) * 0.7, [0, 0, 1], 44),
        # far away: a dim small world
        (57.5, ll(25, 120) * 7.0, [0, 0, 0], [0, 0, 1], 36),
        (68.5, ll(25, 132) * 6.6, [0, 0, 0], [0, 0, 1], 36),
    ]
    for (t0, p0, g0, u0, f0), (t1, p1, g1, u1, f1) in zip(keys, keys[1:]):
        if t <= t1:
            k = sm((t - t0) / (t1 - t0))
            r0, r1 = np.linalg.norm(p0), np.linalg.norm(p1)
            p = R.slerp(p0 / r0, p1 / r1, k) if hasattr(R, 'slerp') else nrm(lerp(p0 / r0, p1 / r1, k))
            p = p * math.exp(lerp(math.log(r0), math.log(r1), k))
            g = lerp(np.asarray(g0, float), np.asarray(g1, float), k)
            up = nrm(lerp(np.asarray(u0, float), np.asarray(u1, float), k))
            return p, g, up, lerp(f0, f1, k)
    p0, g0, u0, f0 = keys[-1][1:]
    return p0, np.asarray(g0, float), nrm(np.asarray(u0, float)), f0

def slerp(a, b, k):
    a, b = nrm(a), nrm(b); om = math.acos(max(-1.0, min(1.0, float(a @ b))))
    if om < 1e-6: return a
    return (math.sin((1 - k) * om) * a + math.sin(k * om) * b) / math.sin(om)
R.slerp = slerp

def glow(img, cx, cy, r, col, k):
    """a fireball's light: a hot core and a wide soft halo, on a sprite big enough that its edge is never seen"""
    s = int(r * 16 + 8); yy, xx = np.mgrid[0:s, 0:s] - s / 2 + 0.5
    d = np.sqrt(xx * xx + yy * yy)
    g = np.exp(-(d / r) ** 2) + 0.22 * np.exp(-(d / (2.6 * r)) ** 2) + 0.05 * np.exp(-(d / (6 * r)) ** 2)
    g = g * np.clip(1 - d / (s / 2), 0, 1) ** 2
    R.add(img, g[..., None] * np.asarray(col) * k, cx, cy)

# ---------------------------------------------------------------- post: bloom, flare, tone map
def bloom(img):
    """float bloom (no 8-bit steps): the bright parts blurred at three sizes on a 1/4-size copy; a horizontal streak
    through the hottest cores (blurred along x only, so it never makes a box)"""
    from scipy.ndimage import gaussian_filter, uniform_filter1d
    bright = np.clip(img - 1.1, 0, 12).astype(np.float32)
    if bright.max() <= 0: return img
    small = bright.reshape(H // 4, 4, W // 4, 4, 3).mean((1, 3))
    acc = np.zeros_like(small)
    for r_, k_ in ((1.5, 0.8), (6, 0.5), (20, 0.35)):
        acc += gaussian_filter(small, (r_, r_, 0)) * k_
    out = img + np.repeat(np.repeat(acc, 4, 0), 4, 1)
    core = np.clip(img - 3.0, 0, 8).astype(np.float32).mean(-1)
    if core.max() > 0:
        cs = core.reshape(H // 4, 4, W // 4, 4).mean((1, 3))
        st = uniform_filter1d(uniform_filter1d(cs, 41, axis=1), 41, axis=1)
        out += np.repeat(np.repeat(st, 4, 0), 4, 1)[..., None] * np.array([0.55, 0.7, 1.0]) * 1.2
    return out

def tonemap(x):
    y = 1 - np.exp(-x * 1.15)
    return np.clip(y, 0, 1) ** (1 / 1.9)

# ---------------------------------------------------------------- one frame
def frame(t):
    p, g, up, fov = cam_at(t)
    f = nrm(g - p); r = nrm(np.cross(f, up)); u = np.cross(r, f)
    k = (H / 2) / math.tan(math.radians(fov) / 2)
    cam = R.Cam(p, g, fov=fov, up=up)
    st = state(t)
    # flashes now
    fl = []
    for v, t0, e in events():
        inten, orng = flash_curve(t - t0)
        if inten > 0.01: fl.append((v, inten * e, orng))
    bg = stars_bg(dx=t * 3, dy=t * 2, k=0.6) ** 1.6 * 0.6
    img, hit, P = earth(p, f, r, u, k, t, SUN, st, fl, bg)
    # the fireballs themselves (bright cores above the ground) and the shock rings on the clouds
    for v, t0, e in events():
        dt = t - t0
        if dt < 0 or dt > 9: continue
        inten, orng = flash_curve(dt)
        X = v * (1 + (1.5 + 30 * (1 - math.exp(-dt / 2.2)) * 0.8) * KM)        # rides up inside the cap
        x, y, z = cam.proj(X)
        if z[0] <= 0: continue
        # occluded by the planet?
        dvec = X - p; dist = np.linalg.norm(dvec); dn = dvec / dist
        bq = dn @ p; cq = p @ p - 1; disc = bq * bq - cq
        if disc > 0 and (-bq - math.sqrt(disc)) < dist - 2 * KM: continue
        size = max(1.2, k * (0.8 + 1.4 * min(dt, 2)) * KM / z[0], 3.0 * min(inten, 6.0) ** 0.6 * (dt < 1.5))
        col = np.array([0.9, 0.95, 1.0]) * (1 - orng) + np.array([1.0, 0.6, 0.25]) * orng
        glow(img, x[0], y[0], size, col, min(8.0, inten * e * 1.2))
        # the shock ring racing out over the clouds (seen from orbit), 0.3–3 s
        if 0.15 < dt < 3.5:
            ring_km = 6 + 90 * (dt - 0.15) ** 0.7
            e1, n1 = tangent(v)
            ang = np.linspace(0, 2 * np.pi, 90)
            pts = np.array([v * (1 + 6 * KM) + (e1 * math.cos(a) + n1 * math.sin(a)) * ring_km * KM for a in ang])
            xx, yy, zz = cam.proj(pts)
            a_ = 0.5 * math.exp(-(dt - 0.15) / 1.2) * e
            R.lines(img, [([(xx[j], yy[j]), (xx[j + 1], yy[j + 1])], a_) for j in range(len(ang) - 1) if zz[j] > 0], (0.9, 0.95, 1.0), width=2, k=1.0)
    # mushroom clouds and fire plumes (only where they are big enough to matter)
    puffs = []
    for v, t0, e in events():
        dt = t - t0
        if 0 < dt < 14:
            X = v; x, y, z = cam.proj(X)
            if z[0] > 0 and cam.k * 40 * KM / z[0] > 6:
                puffs += mushroom(dt, v, cam, scale_km=0.8 + 0.4 * e)
    if t > 13.0 and t < 40:
        fp = [q for q in fire_plumes(t, cam) if q[2] > 1.0]
        fade = 1 - sm((t - 34) / 5)
        puffs += [(x, y, rp, z, ct, cb, a * fade) for x, y, rp, z, ct, cb, a in fp]
    if puffs: draw_puffs(img, puffs)
    img = bloom(np.nan_to_num(img, nan=0.0, posinf=12.0, neginf=0.0))   # one NaN would spread over the whole bloom
    # a soft vignette
    yy, xx = np.mgrid[0:H, 0:W]; vig = 1 - 0.35 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2
    img = img * vig[..., None]
    return R.to_img(tonemap(img))

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
