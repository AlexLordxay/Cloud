# «А ти уявляєш Титан так?» — every frame (720 × 1280, 30 fps) from render.py, shot by shot, with crossfades.
# Labels for captions.py -> work/titan_imagine/labels.json.
#   python3 scenes/titan_imagine/frames.py [from to]     (frames already made are kept)
#   python3 scenes/titan_imagine/frames.py stills 2,10,…  -> work/titan_imagine/still_<t>.jpg
# Voice phrases (video time, scene.json): 0.3, 4.05, 6.14, 10.42, 16.43, 25.84, 33.61 s.
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import render as RD
WK = os.path.join(TOOLS, 'work', 'titan_imagine'); OUT = os.path.join(WK, 'w3d'); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 720, 1280, 30, 41.5
TEX = os.path.join(TOOLS, '..', '..', 'planetarium', 'textures')
ld = lambda f: np.ascontiguousarray(np.asarray(Image.open(f).convert('RGB')).astype(np.float32) / 255)
TT = ld(os.path.join(TEX, 'titan_surface.jpg')); LK = ld(os.path.join(TEX, 'titan_lakes.png'))
ST = ld(os.path.join(TEX, 'saturn.jpg')); MT = ld(os.path.join(TEX, 'mercury.jpg'))
RG = np.ascontiguousarray(np.asarray(Image.open(os.path.join(TEX, 'saturn_ring.png')).convert('RGBA')).astype(np.float32)[:1] / 255)
SK = ld(os.path.join(TOOLS, 'work', 'neutron_spoon', 'sky.jpg'))
G = {}
for nm in ('coast', 'dunes'):
    G[nm] = tuple(np.ascontiguousarray(np.load(os.path.join(WK, f'{nm}_{k}.npy')).astype(np.float64)) for k in 'zaw')
HALF = 20000.0; CELL = 2 * HALF / 2047

# Dragonfly (NASA/APL), metres, x forward, z up: an octocopter lander ~3.9 m long, four arms with coaxial rotor pairs
# (1.35 m rotors), the MMRTG at the back, the high-gain dish on top, skids. Materials: see render.df_shade.
DF_B = np.array([
    (0.0, 0.0, 0.0, 1.55, 0.72, 0.42, 1),            # body
    (0.0, 0.0, -0.47, 1.45, 0.66, 0.06, 2),           # lower deck
    (1.58, 0.0, -0.05, 0.05, 0.42, 0.16, 3),          # forward cameras / instrument plate
    (-1.85, 0.0, 0.05, 0.32, 0.30, 0.30, 4),          # MMRTG
    (-1.55, 0.0, 0.05, 0.05, 0.36, 0.36, 2),          # its mount
    *[(sx * 1.35, sy * 1.12, 0.28, 0.07, 0.42, 0.05, 2) for sx in (-1, 1) for sy in (-1, 1)],   # arms
    *[(sx * 0.95, sy * 0.62, -0.72, 0.03, 0.03, 0.24, 3) for sx in (-1, 1) for sy in (-1, 1)],  # skid struts
    *[(0.0, sy * 0.62, -0.97, 1.35, 0.035, 0.035, 3) for sy in (-1, 1)],                         # skids
    (0.55, 0.0, 0.43, 0.45, 0.45, 0.02, 6),           # gold blanket patch
], np.float64)
DF_C = np.array([
    *[(sx * 1.35, sy * 1.55, 0.0, 0.09, 0.05, 0.70, 3) for sx in (-1, 1) for sy in (-1, 1)],    # rotor hubs
    *[(sx * 1.35, sy * 1.55, zz, 0.675, 0.0, 0.015, 9) for sx in (-1, 1) for sy in (-1, 1) for zz in (0.12, 0.66)],  # rotors
    (-0.35, 0.0, 0.42, 0.50, 0.0, 0.10, 5),           # high-gain dish (flat)
], np.float64)

def nrm(v): v = np.asarray(v, np.float64); return v / np.linalg.norm(v)
def look(cam, tgt, upv=(0, 0, 1)):
    fw = nrm(np.subtract(tgt, cam)); rt = nrm(np.cross(fw, upv)); up = np.cross(rt, fw); return fw, rt, up
def cl(x): return min(1.0, max(0.0, x))
def sm(x): x = cl(x); return x * x * (3 - 2 * x)
def ease(x): x = cl(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, k): return a + (b - a) * k
def lerpv(a, b, k): return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * k
def hat(nm, x, y):
    Z, _, WL = G[nm]
    i = int(np.clip((x + HALF) / CELL, 0, 2046)); j = int(np.clip((y + HALF) / CELL, 0, 2046))
    return max(float(Z[j, i]), float(WL[j, i]))

# ---------------- space: Titan at the origin, Saturn's ring plane = z = 0 (Titan orbits in it)
S_DIR = nrm([0.30, 1.0, 0.0]); S_POS = S_DIR * 1221870.0
# Saturn's axis tipped 24° toward the camera side (an artistic liberty, asked by the author: seen from Titan, which orbits
# in the ring plane, the rings are almost edge-on — tipped, they show open, lit from above)
RING_TILT = math.radians(24)
EZ = nrm(np.array([0.0, 0, 1]) * math.cos(RING_TILT) - S_DIR * math.sin(RING_TILT))
EX = nrm(np.cross(EZ, S_DIR)); EY = nrm(np.cross(EZ, EX))
SUN = nrm([-0.85, -0.30, 0.12])

def proj(cam, fw, rt, up, fov, p, r):
    d = np.asarray(p, float) - cam; z = float(np.dot(d, fw))
    if z <= 0: return None
    f = (H / 2) / math.tan(math.radians(fov) / 2)
    return [W / 2 + float(np.dot(d, rt)) / z * f, H / 2 - float(np.dot(d, up)) / z * f, r / z * f]

SAZ = math.atan2(S_DIR[1], S_DIR[0]) + math.pi        # the azimuth of the point opposite Saturn

def shot_open(t):
    # 0–3.9: the long-lens view: Titan in front, Saturn with its rings behind, both large; a slow drift
    d = 47000.0 - 700.0 * t; el = 0.13
    az = SAZ + 0.05 + 0.004 * t
    cam = np.array([d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)])
    sdir = nrm(S_POS - cam); tdir = nrm(-cam)
    fw, rt, up = look(cam, cam + nrm(sdir * 0.42 + tdir * 0.58))
    # rendered at the final 1080 × 1920 (not upscaled): the first frame has to be sharp
    return ('space', dict(cam=cam, fw=fw, rt=rt, up=up, fov=30.0, mpos=np.zeros(3), mvis=0.0, expo=1.0, ss=2, res=(1920, 1080))), {}

def shot_globe(t):
    # 6.0–16.6: Titan with Saturn behind it (the camera a little below the ring plane, so Saturn rises above Titan);
    # 8.4–10.6 pull back, Mercury beside it at true scale; 11.0– push in to the limb and its haze layers
    az = SAZ + 0.10 + 0.010 * (t - 6)
    d = lerp(26000, 38000, ease((t - 8.2) / 2.0))
    d = lerp(d, 10000, ease((t - 11.0) / 4.8))
    el = 0.20
    cam = np.array([d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)])
    fw0, rt0, up0 = look(cam, [0, 0, 0])
    mpos = -rt0 * 6600.0                                        # Mercury to the left of Titan, 6600 km between centres
    kx = ease((t - 8.2) / 2.0) * (1 - ease((t - 11.0) / 3.0))
    tgt = mpos * 0.5 * kx + up0 * 2600 * (1 - kx)
    # the push-in ends looking at Titan's limb (the right edge)
    kl = ease((t - 11.0) / 4.8)
    tgt = tgt * (1 - kl) + (rt0 * RD.R_T * 0.95 + up0 * 600) * kl
    fw, rt, up = look(cam, tgt)
    mvis = sm((t - 8.3) / 0.9) * (1 - sm((t - 10.9) / 0.7))
    fov = 40.0
    lab = {}
    if mvis > 0.5:
        lab['ti'] = proj(cam, fw, rt, up, fov, [0, 0, 0], RD.R_T); lab['me'] = proj(cam, fw, rt, up, fov, mpos, RD.R_M)
    if t < 8.6:
        lab['sat'] = proj(cam, fw, rt, up, fov, S_POS, RD.S_REQ)
    return ('space', dict(cam=cam, fw=fw, rt=rt, up=up, fov=fov, mpos=mpos, mvis=mvis, expo=1.0, ss=1)), lab

def shot_end(t):
    k = (t - 33.4) / (DUR - 33.4)
    az = SAZ - 0.12 - 0.02 * k; d = lerp(17000, 23000, ease(k)); el = 0.24
    cam = np.array([d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)])
    fw0, rt0, up0 = look(cam, [0, 0, 0])
    fw, rt, up = look(cam, up0 * 3200)
    return ('space', dict(cam=cam, fw=fw, rt=rt, up=up, fov=44.0, mpos=np.zeros(3), mvis=0.0, expo=1.0, ss=1)), {}

# ---------------- the surface
SUN_S = nrm([-0.45, 0.60, 0.30])

def shot_fly(t):
    # 0–6.4: low over the methane sea toward the shore, the valleys drowned into inlets ahead
    k = t / 6.4
    p0 = np.array([-6900.0, -5200.0]); p1 = np.array([-7300.0, -2600.0])
    xy = lerpv(p0, p1, k)
    alt = lerp(240.0, 120.0, sm(k))
    cam = np.array([xy[0], xy[1], alt])
    ahead = xy + nrm(p1 - p0) * 3000
    tgt = np.array([ahead[0] + 300 * math.sin(t * 0.4), ahead[1], lerp(-60, -40, k)])
    fw, rt, up = look(cam, tgt, upv=(0.05 * math.sin(t * 0.7), 0, 1))
    return ('surface', dict(g='coast', cam=cam, fw=fw, rt=rt, up=up, fov=62, expo=0.72, fogk=1 / 22000, dvis=0)), {}

def shot_river(t):
    # 16.2–26.0: down through the haze over the valleys, then along a river out to the sea, in the rain
    k = (t - 16.2) / 9.8
    p0 = np.array([-3300.0, 9000.0]); p1 = np.array([-3900.0, -2500.0])
    xy = lerpv(p0, p1, ease(k) * 0.7 + k * 0.3)
    alt = lerp(2600.0, 140.0, ease(min(1, k * 1.5))) + hat('coast', *xy) * (1 - k) * 0
    cam = np.array([xy[0], xy[1], max(alt, hat('coast', *xy) + 90)])
    look_at = np.array([xy[0] - 150, xy[1] - lerp(1500, 4000, k), lerp(-500, 0, sm(k * 1.4))])
    fw, rt, up = look(cam, look_at)
    fog = lerp(1 / 7000, 1 / 20000, sm(k * 1.6))
    return ('surface', dict(g='coast', cam=cam, fw=fw, rt=rt, up=up, fov=58, expo=0.72, fogk=fog, dvis=0,
                            haze=1 - sm(k * 5.0))), {}

def df_pose(t):
    # Dragonfly cruising east along the dune field, ~70 m above the crests (it can fly up to ~4 km, ~10 m/s)
    x = -6000 + 10.0 * (t - 25.6)
    y = -2000.0
    z = 195.0
    return np.array([x, y, z])

def rotz_pitch(yaw, pitch, roll=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch); cr, sr = math.cos(roll), math.sin(roll)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]); Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Rz @ Ry @ Rx

def shot_dunes(t):
    # 25.6–34.0: above the dunes; the camera behind Dragonfly at its height, looking north-east over it, so the dune rows
    # recede to the hazy horizon; it swings toward the drone's side and pulls back
    k = (t - 25.6) / 8.4
    dp = df_pose(t)
    ang = lerp(math.pi + 0.75, math.pi + 1.25, ease(k))      # from south-west to south-south-west of the drone
    dist = lerp(9.0, 20.0, ease(k))
    cam = dp + np.array([dist * math.cos(ang), dist * math.sin(ang), lerp(1.5, 4.0, ease(k))])
    fov = 52.0
    away = nrm(np.array([dp[0] - cam[0], dp[1] - cam[1], 0.0]))
    tgt = dp + away * 400.0 + np.array([0, 0, -150.0 + 0 * k])
    fw, rt, up = look(cam, tgt)
    R = rotz_pitch(0.0, 0.10, 0.02 * math.sin(t * 1.3))
    return ('surface', dict(g='dunes', cam=cam, fw=fw, rt=rt, up=up, fov=fov, expo=0.72, fogk=1 / 30000,
                            dvis=1.0, dpos=dp, dR=R)), {'df': proj(cam, fw, rt, up, fov, dp, 2.0)}

SHOTS = [(0.0, 3.9, shot_open), (3.5, 6.4, shot_fly), (6.0, 16.6, shot_globe), (16.2, 26.0, shot_river), (25.6, 34.0, shot_dunes),
         (33.6, DUR + 0.1, shot_end)]
XF = 0.4

def render_shot(kind, P, t):
    out = np.zeros(P.get('res', (H, W)) + (3,), np.float32)
    if kind == 'space':
        RD.space(TT, LK, ST, RG, MT, SK, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), SUN, S_POS, EX, EY, EZ,
                 np.asarray(P['mpos'], float), float(P['mvis']), 0.0, P['expo'], out, P.get('ss', 1))
    else:
        Z, A, WL = G[P['g']]
        dpos = np.asarray(P.get('dpos', np.zeros(3)), float); dR = np.ascontiguousarray(P.get('dR', np.eye(3)), dtype=np.float64)
        RD.surface(Z, A, WL, CELL, HALF, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), SUN_S, P['expo'], out, 1,
                   P['fogk'], t, DF_B, DF_C, dpos, dR, float(P['dvis']), t * 37.0)
        hz = P.get('haze', 0.0)
        if hz > 0:
            # inside the haze, high up: everything washes toward the orange glow
            out = out * (1 - 0.85 * hz) + np.array([0.62, 0.34, 0.13], np.float32) * 0.85 * hz
    return out

def rain(img, t, k):
    # methane rain: big drops (up to ~1 cm) falling slowly (~1.6 m/s, Lorenz 1993) — soft short streaks
    if k <= 0: return img
    rng = np.random.default_rng(int(t * 30) % 3 + 7)
    lay = Image.new('L', (W, H), 0); d = ImageDraw.Draw(lay)
    base = np.random.default_rng(5)
    n = 170
    xs = base.uniform(0, W, n); ys0 = base.uniform(0, H, n); sp = base.uniform(0.3, 1.0, n)
    for i in range(n):
        y = (ys0[i] + t * 140 * sp[i]) % (H + 60) - 30
        x = xs[i] + 25 * math.sin(t * 0.5 + i)
        L = 4 + 14 * sp[i]; w = 1
        d.line([(x, y), (x - 2, y + L)], fill=int(120 * sp[i] * k), width=w)
    a = np.asarray(lay.filter(ImageFilter.GaussianBlur(1.1))).astype(np.float32)[..., None] / 255
    return img * (1 - 0.25 * a) + a * np.array([1.0, 0.78, 0.55], np.float32) * 0.55

def upsize(a, shape):
    return np.stack([np.asarray(Image.fromarray(a[..., c]).resize((shape[1], shape[0]), Image.LANCZOS)) for c in range(3)], -1)

def frame(t):
    acc = None; wsum = 0.0; labs = {}
    for a, b, fn in SHOTS:
        if a <= t < b:
            w = min(1.0, (t - a) / XF if a > 0 else 1.0, (b - t) / XF if b < DUR else 1.0)
            if w <= 0: continue
            (kind, P), lab = fn(t)
            img = render_shot(kind, P, t)
            if fn is shot_river: img = rain(img, t, sm((t - 19.8) / 1.0))
            if acc is not None and img.shape != acc.shape:
                big = img if img.shape[0] > acc.shape[0] else acc
                if img.shape[0] < big.shape[0]: img = upsize(img, big.shape)
                else: acc = upsize(acc, big.shape)
            acc = img * w if acc is None else acc + img * w; wsum += w
            if w >= 0.5: labs = lab
    img = acc / max(wsum, 1e-6)
    return (RD.tonemap(RD.bloom(img)) * 255).astype(np.uint8), labs

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stills':
        for t in map(float, sys.argv[2].split(',')):
            import time; t0 = time.time()
            im, _ = frame(t); Image.fromarray(im).save(os.path.join(WK, f'still_{t}.jpg'), quality=92)
            print('still', t, round(time.time() - t0, 1), 's', flush=True)
        sys.exit()
    n0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0; n1 = int(sys.argv[2]) if len(sys.argv) > 2 else int(round(DUR * FPS))
    lp = os.path.join(WK, f'labels_{n0}.json'); labels = json.load(open(lp)) if os.path.exists(lp) else {}
    for i in range(n0, n1):
        f = os.path.join(OUT, f'f_{i:05d}.jpg')
        if os.path.exists(f) and str(i) in labels: continue
        im, lab = frame(i / FPS)
        Image.fromarray(im).save(f, quality=93); labels[str(i)] = lab
        if i % 30 == 0:
            json.dump(labels, open(lp, 'w')); print('frame', i, flush=True)
    json.dump(labels, open(lp, 'w'))
