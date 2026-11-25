# «А ти уявляєш Європу так?» — every frame (720 × 1280, 30 fps) from the renderers in render.py, shot by shot, with
# crossfades where one shot hands over to the next. Labels for captions.py -> work/europa_imagine/labels.json.
#   python3 scenes/europa_imagine/frames.py [from to]     (frames already made are kept)
#   python3 scenes/europa_imagine/frames.py stills 2,10,…  -> work/europa_imagine/still_<t>.jpg
# Voice (scene.json parts) at 0.3, 4.67, 7.19, 14.07, 21.74, 27.27, 33.63, 42.18 s.
import json, math, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import render as RD
import ground as GR
import probe as PR
WK = os.path.join(TOOLS, 'work', 'europa_imagine'); OUT = os.path.join(WK, 'w3d'); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 720, 1280, 30, 48.5
ld = lambda f: np.ascontiguousarray(np.asarray(Image.open(f).convert('RGB')).astype(np.float32) / 255)
TEX = os.path.join(TOOLS, '..', '..', 'planetarium', 'textures')
Z = np.ascontiguousarray(np.load(os.path.join(WK, 'hf.npy')) / 1000.0); A = np.ascontiguousarray(np.load(os.path.join(WK, 'alb.npy')))
HMAX = float(Z.max()); PK = 200 / Z.shape[0]
SK = ld(os.path.join(TOOLS, 'work', 'neutron_spoon', 'sky.jpg')); JT = ld(os.path.join(TEX, 'jupiter.jpg'))
GT = ld(os.path.join(WK, 'globe.jpg')); MT = ld(os.path.join(TEX, 'moon.jpg'))
JANG = math.atan(RD.J_R / RD.J_D)
# «Europa Clipper» in metres (cx, cy, cz, half x, y, z, material): body, antenna, two 5-panel wings, radar rods, boom
_B = [(0, 0, 0, 0.85, 0.85, 1.7, 1), (0, 0, -2.2, 0.6, 0.6, 0.6, 4), (0, 0, 1.95, 1.5, 1.5, 0.06, 2), (0, 0, 2.1, 0.12, 0.12, 0.3, 4)]
for sx in (-1, 1):
    _B.append((sx * 1.4, 0, 0.3, 0.55, 0.12, 0.12, 4))
    for k in range(5):
        c = 2.2 + k * 2.68 + 1.3
        _B.append((sx * c, 0, 0.3, 1.3, 2.05, 0.04, 3))
    _B.append((sx * 8.8, 2.35, 0.3, 7.6, 0.03, 0.03, 4)); _B.append((sx * 8.8, -2.35, 0.3, 7.6, 0.03, 0.03, 4))
_B.append((0, -4.8, -0.6, 0.04, 4.0, 0.04, 4))
BOX = np.array(_B, np.float64)

def nrm(v): v = np.asarray(v, np.float64); return v / np.linalg.norm(v)
def look(cam, tgt, upv=(0, 0, 1)):
    fw = nrm(np.subtract(tgt, cam)); rt = nrm(np.cross(fw, upv)); up = np.cross(rt, fw); return fw, rt, up
def cl(x): return min(1.0, max(0.0, x))
def sm(x): x = cl(x); return x * x * (3 - 2 * x)
def ease(x): x = cl(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, k): return a + (b - a) * k
def lerpv(a, b, k): return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * k
def zat(x, y): return float(Z[int((100 - y) / PK), int((x + 100) / PK)])
def sph(d, az, el): return np.array([d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)])

# the terrain shots share one Sun and one Jupiter (Europa is locked: Jupiter hangs still in its sky)
SUN_T = nrm([-0.9, -0.2, 0.40]); JD_T = nrm([0.35, 0.85, 0.42])
JAX_T = nrm(np.cross(np.cross(JD_T, [0, 0.3, 1]), JD_T)) * -1
SUN_G = nrm([-0.9, -0.2, 0.26])     # standing on the ice: a lower Sun, longer shadows

# ---------------- the shots: (start, end, function t -> (kind, params)) ----------------
def shot_globe(t):
    # 0–7.6: the cut-open globe, closing at 4.6–5.9; 7.0–14.0: pulled back, the Moon beside it at true scale
    az = -2.2 + 0.05 * t; el = lerp(0.42, 0.18, sm((t - 4.6) / 3.0))
    dist = lerp(7800, 9300, sm(t / 7.0))
    dist = lerp(dist, 22500, ease((t - 7.2) / 2.2))
    cam = sph(dist, az, el)
    tgt = lerpv([0, 0, 0], [2350, 0, 0] if False else [0, 0, 0], 0)
    fw, rt, up = look(cam, [0, 0, 0])
    # the Moon: to the right of Europa as seen from the camera, 3800 km between the centres (both fit the frame)
    mp = rt * 3800.0
    tgt = mp * 0.5 * ease((t - 7.2) / 2.2)
    fw, rt, up = look(cam, tgt)
    cut = 1.0 - sm((t - 4.6) / 1.3)
    jd = nrm(fw + 0.13 * rt + 0.205 * up)
    sn = nrm(rt * 0.9 - fw * 0.35 + up * 0.25)
    moon = np.array([mp[0], mp[1], mp[2], 1.0 if t > 7.3 else 0.0])
    lab = {}
    if t > 7.3:
        lab['eu'] = proj(cam, fw, rt, up, 36, [0, 0, 0], RD.R_E); lab['mo'] = proj(cam, fw, rt, up, 36, mp, 1737.4)
    return ('space', dict(cam=cam, fw=fw, rt=rt, up=up, fov=36, sun=sn, jd=jd, moon=moon, cut=cut,
                          cdir=np.array([math.cos(az + 0.45), math.sin(az + 0.45)]), expo=0.78)), lab

def shot_fly(t):
    # 13.6–21.9: down from 40 km to ~1.5 km over the ridged plains, heading north-east toward the chaos patch
    k = (t - 13.6) / 8.3
    p0, p1 = np.array([-70.0, -82.0]), np.array([22.0, 8.0])
    xy = lerpv(p0, p1, ease(k) * 0.85 + k * 0.15)
    alt = lerp(40.0, 2.6, ease(min(1, k * 1.25)))
    cam = np.array([xy[0], xy[1], alt + max(0.0, zat(*np.clip(xy, -99, 99)))])
    ahead = lerpv(xy, xy + (p1 - p0) * 0.4, 1)
    tgt = np.array([ahead[0], ahead[1], lerp(-30.0, 0.2, ease(min(1, k * 1.2)))])
    fw, rt, up = look(cam, tgt)
    return ('ground', dict(cam=cam, fw=fw, rt=rt, up=up, fov=lerp(48, 58, k), expo=1.0, sun=SUN_T)), {}

def shot_slab(t):
    # 21.4–27.5: the block cut out of the ice: the shell and the ocean below it
    k = (t - 21.4) / 6.1
    cam = sph(lerp(520, 470, sm(k)), lerp(-2.35, -1.95, k), lerp(0.30, 0.24, k)) + np.array([0, 0, -60.0])
    tgt = np.array([0, 0, -80.0])
    fw, rt, up = look(cam, tgt)
    lab = {'ice': proj(cam, fw, rt, up, 44, corner(cam, -12.0), 0), 'ocean': proj(cam, fw, rt, up, 44, corner(cam, -100.0), 0),
           'top': proj(cam, fw, rt, up, 44, corner(cam, 0.0), 0), 'bot': proj(cam, fw, rt, up, 44, corner(cam, -175.0), 0)}
    return ('terrain', dict(cam=cam, fw=fw, rt=rt, up=up, fov=44, slab=True, expo=1.0)), lab

def corner(cam, z):
    # the vertical edge of the block nearest the camera
    return [100.0 * np.sign(cam[0]), 100.0 * np.sign(cam[1]), z]

def shot_ground(t):
    # 27.1–33.8: standing on the ice (eye 12 m up) below a double ridge; the view lifts from the ice to Jupiter
    k = (t - 27.1) / 6.7
    base = np.array([6.02, 15.12]) + np.array([0.20, 0.10]) * k
    cam = np.array([base[0], base[1], GND_EYE + float(GR.base(Z, base[0], base[1], PK, 100.0))])
    tgt = cam + np.array([0.55, 1.0, lerp(0.05, 0.30, ease(k))])
    fw, rt, up = look(cam, tgt)
    lab = {'jup': proj(cam, fw, rt, up, 60, cam + JD_T * 1e6, 1e6 * math.tan(JANG))}
    return ('ground', dict(cam=cam, fw=fw, rt=rt, up=up, fov=60, expo=1.0)), lab
GND_EYE = 0.012

def shot_clipper(t):
    # 33.4–40.8: «Europa Clipper» (modelled to scale: 30.5 m across the arrays) gliding over Europa, Jupiter behind
    k = (t - 33.4) / 7.4
    # Europa below: the spacecraft 600 km up, moving along +y; the camera trails beside it
    alt = 600.0
    sc = np.array([0.0, lerp(-0.12, 0.12, k), RD.R_E + alt]) * 1.0
    sc = np.array([0.0, (RD.R_E + alt) * math.sin(lerp(-0.004, 0.004, k)), (RD.R_E + alt) * math.cos(lerp(-0.004, 0.004, k))])
    cam = sc + np.array([0.020, -0.022 + 0.010 * k, 0.016])
    fw, rt, up = look(cam, sc + np.array([-0.002, 0.004, -0.012]), upv=(0, 0, 1))
    sn = nrm([0.7, -0.3, 0.35])
    jd = nrm(fw - 0.05 * rt + 0.50 * up)
    return ('probe', dict(cam=cam, fw=fw, rt=rt, up=up, fov=58, sun=sn, jd=jd, expo=0.95, sc=sc)), {'sc': proj(cam, fw, rt, up, 50, sc, 0.015)}

def shot_end(t):
    k = (t - 40.6) / 7.9
    cam = sph(lerp(8500, 12500, ease(k)), -1.6 + 0.06 * k, 0.15)
    fw, rt, up = look(cam, [0, 0, 0])
    jd = nrm(fw + 0.10 * rt + 0.24 * up); sn = nrm(rt * 0.9 - fw * 0.3 + up * 0.25)
    return ('space', dict(cam=cam, fw=fw, rt=rt, up=up, fov=38, sun=sn, jd=jd, moon=np.zeros(4), cut=0.0,
                          cdir=np.array([1.0, 0.0]), expo=0.78)), {}

SHOTS = [(0.0, 14.1, shot_globe), (13.6, 21.9, shot_fly), (21.4, 27.6, shot_slab), (27.1, 33.9, shot_ground),
         (33.4, 40.9, shot_clipper), (40.4, DUR + 0.1, shot_end)]
XF = 0.5   # crossfade length

def proj(cam, fw, rt, up, fov, p, r):
    d = np.asarray(p, float) - cam; z = float(np.dot(d, fw))
    if z <= 0: return None
    f = (H / 2) / math.tan(math.radians(fov) / 2)
    return [W / 2 + float(np.dot(d, rt)) / z * f, H / 2 - float(np.dot(d, up)) / z * f, r / z * f]

def render_shot(kind, P, ss):
    out = np.zeros((H, W, 3), np.float32)
    if kind == 'ground':
        GR.ground(Z, A, PK, 100.0, SK, JT, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), P.get('sun', SUN_G), JD_T, JANG, JAX_T, 0.0,
                  P['expo'], out, ss, HMAX)
    elif kind == 'probe':
        PR.clipper(GT, SK, JT, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), P['sun'], P['jd'], JANG,
                   nrm([0, 0, 1.0]), 0.0, P['expo'], out, ss, P['sc'], PR.BOX, PR.CYL, PR.DISH)
    elif kind == 'terrain':
        RD.terrain(Z, A, PK, 100.0, SK, JT, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), SUN_T, JD_T, JANG, JAX_T, 0.0,
                   P['slab'], 25.0, 150.0, P['expo'], out, ss, HMAX)
    else:
        clip = P.get('clip'); cl_ = np.zeros(4) if clip is None else np.array([clip[0], clip[1], clip[2], 1.0])
        RD.space(GT, MT, SK, JT, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), P['sun'], P['jd'], JANG,
                 nrm([0, 0, 1.0]), 0.0, 0.0, P['moon'], P['cut'], P['cdir'], P['expo'], out, ss, cl_, BOX)
    return out

def frame(t, ss=2):
    acc = None; wsum = 0.0; labs = {}
    for a, b, fn in SHOTS:
        if a <= t < b:
            w = min(1.0, (t - a) / XF if a > 0 else 1.0, (b - t) / XF if b < DUR else 1.0)
            if w <= 0: continue
            (kind, P), lab = fn(t)
            img = render_shot(kind, P, ss)
            acc = img * w if acc is None else acc + img * w; wsum += w
            if w >= 0.5: labs = lab
    img = acc / max(wsum, 1e-6)
    return (RD.tonemap(RD.bloom(img)) * 255).astype(np.uint8), labs

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stills':
        for t in map(float, sys.argv[2].split(',')):
            im, _ = frame(t, 1); Image.fromarray(im).save(os.path.join(WK, f'still_{t}.jpg'), quality=92); print('still', t)
        sys.exit()
    n0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0; n1 = int(sys.argv[2]) if len(sys.argv) > 2 else int(round(DUR * FPS))
    lp = os.path.join(WK, 'labels.json'); labels = json.load(open(lp)) if os.path.exists(lp) else {}
    for i in range(n0, n1):
        f = os.path.join(OUT, f'f_{i:05d}.jpg')
        if os.path.exists(f) and str(i) in labels: continue
        im, lab = frame(i / FPS)
        Image.fromarray(im).save(f, quality=93); labels[str(i)] = lab
        if i % 30 == 0:
            json.dump(labels, open(lp, 'w')); print('frame', i, flush=True)
    json.dump(labels, open(lp, 'w'))
