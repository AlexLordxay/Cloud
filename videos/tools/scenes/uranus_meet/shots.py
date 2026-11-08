# «Знайомся: Уран» — the 3D shots from space (uranus.py) and along the ring (ringfly.py): where the camera is, frame by
# frame. Each shot is a function of its own time t (seconds from its start) returning a PIL image (720x1280);
# its length comes from timeline.py (fitted to the voice), DUR here are the defaults.
#
#   python3 shots.py stills <shot> t1,t2,…      -> work/uranus_meet/st_<shot>_<t>.jpg
#   python3 shots.py video <shot> [n k]         -> work/uranus_meet/frames/<shot>/f_<frame>.jpg (every n-th from k)
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import uranus as U
import ringfly as R

RE = U.RE
S26 = U.sun_dir_2026()
NORB = np.array([0.4717, 0.871, -0.1352]); NORB /= np.linalg.norm(NORB)     # Uranus' orbit normal in its own frame
SIDE = np.cross(NORB, S26); SIDE /= np.linalg.norm(SIDE)
FPS = 30

DUR = {'moons': 3.5, 'rockfall': 4.0, 'hook': 4.2, 'scale': 6.0, 'orbit': 6.5, 'ringdive': 8.0, 'under': 2.8, 'mystery': 6.0, 'voyager': 5.5,
       'final': 6.0}
try:
    DUR.update(json.load(open(os.path.join(HERE, 'timeline.json')))['shots'])
except Exception:
    pass

def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)

def ease3(x):
    x = min(1.0, max(0.0, x)); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def lerp(a, b, k): return a + (b - a) * k

def rot_about(v, axis, ang):
    axis = axis / np.linalg.norm(axis); v = np.asarray(v, float)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * (axis @ v) * (1 - math.cos(ang))

def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

# ---------------------------------------------------------------------------------------------------- the shots
def shot_hook(t):
    """racing in from the Sun's side: the planet in the middle of its rings like a target; then the camera swings a
    quarter round its orbit — and there it is, lying on its side, the rings standing upright"""
    d = DUR['hook']
    t1 = 1.7
    if t < t1:
        k = t / t1
        dist = 1.1e6 * (240000 / 1.1e6) ** (1 - (1 - k) ** 2.2)
        cdir = unit(S26 + 0.10 * SIDE + 0.04 * NORB)
    else:
        k = ease3((t - t1) / (d - t1 - 0.2))
        dist = lerp(240000, 205000, k)
        cdir = unit(rot_about(unit(S26 + 0.10 * SIDE + 0.04 * NORB), NORB, -math.radians(84) * k))
    cam = cdir * dist
    return U.frame(cam, (0, 0, 0), up=NORB, fovy=40, sun=S26, rot=0.25 * t, ring_k=18, bloom=1.0)

def shot_scale(t):
    """the Earth beside Uranus at the same distance: four times smaller across"""
    d = DUR['scale']
    k = ease(t / d)
    vdir = unit(rot_about(S26, NORB, math.radians(-42)) + 0.18 * NORB)
    upv = unit(NORB - vdir * (NORB @ vdir))
    earth = -upv * (RE + 6371 + 12000.0)
    tgt = earth * lerp(0.05, 0.45, k)
    cam = tgt + vdir * lerp(105000, 175000, k)
    sph = [[*earth, 6371.0, 0, 1.3 + 0.05 * t, 0.4]]
    return U.frame(cam, tgt, up=NORB, fovy=40, sun=S26, rot=0.25 * t + 0.4, ring_k=16, spheres=sph)

ORB_D = 5.5 * RE          # the diagram: Uranus' orbit drawn 10 radii from the Sun (not to scale)
def orbit_state(t):
    d = DUR['orbit']
    k = ease(t / d)
    year = lerp(2028.0, 2070.0, k)
    th = (year - 2026.9) / 84.02 * 2 * math.pi
    e1 = -S26; e2 = unit(np.cross(NORB, e1))
    PU = ORB_D * (math.cos(th) * e1 + math.sin(th) * e2)            # Uranus relative to the Sun (inertial)
    C = NORB * 13.5 * RE - e1 * 5.5 * RE + e2 * 1.0 * RE                   # the camera, relative to the Sun
    return year, PU, C, e1, e2

def shot_orbit(t):
    """the Sun in the middle, Uranus going half round it (42 years): its north pole first in daylight, then in the dark"""
    year, PU, C, e1, e2 = orbit_state(t)
    cam = C - PU
    sunpos = -PU
    tgt = sunpos * 0.55
    sph = [[*sunpos, 1.35 * RE, 2, 0.1 * t, 0.0]]
    img = U.frame(cam, tgt, up=NORB, fovy=52, sun=unit(sunpos), rot=0.0, ring_k=26, spheres=sph, bloom=1.4,
                  star_gain=0.6)
    # the orbit (dashed) and the axis through the poles, drawn on top
    TY = math.tan(math.radians(52) / 2)
    dr = ImageDraw.Draw(img, 'RGBA')
    def proj(p):
        r, u, f = U.TR.cam_basis(cam, tgt, NORB)
        v = np.asarray(p, float) - cam
        z = v @ f
        if z <= 0: return None
        TX = TY * U.W / U.H
        return ((v @ r) / z / TX + 1) / 2 * U.W, (1 - (v @ u) / z / TY) / 2 * U.H
    pts = []
    for a in np.linspace(0, 2 * math.pi, 241):
        P = ORB_D * (math.cos(a) * e1 + math.sin(a) * e2) - PU
        pts.append(proj(P))
    for i in range(0, 240, 2):
        if pts[i] and pts[i + 1]:
            dr.line([pts[i], pts[i + 1]], fill=(170, 200, 230, 90), width=2)
    a0, a1 = proj(np.array([0, 0, -1.9 * RE])), proj(np.array([0, 0, 1.9 * RE]))
    if a0 and a1:
        dr.line([a0, a1], fill=(255, 255, 255, 150), width=2)
        x, y = a1
        lit = unit(sunpos)[2] > 0                          # the north pole in daylight?
        c = (255, 214, 120, 240) if lit else (90, 120, 200, 240)
        dr.ellipse([x - 9, y - 9, x + 9, y + 9], fill=c, outline=(255, 255, 255, 200), width=2)
    return img

# the ring: local frame (metres): X along the ring, Y outward, Z north; Uranus is at -Y
def ringdive_cam(t):
    d = DUR['ringdive']
    t1 = 4.6
    if t < t1:
        k = t / t1
        e = ease3(k)
        h = 2.6e6 * (14.0 / 2.6e6) ** (k ** 0.85)
        x = lerp(-2400.0, 0.0, e)
        pitch = lerp(-38.0, 6.0, ease(k ** 1.2))
        yaw = lerp(-62.0, -78.0, e)
    else:
        k = (t - t1)
        h = 14.0 - 3.0 * math.sin(k * 0.9)
        x = 130.0 * k
        pitch = 6.0 - 1.5 * k
        yaw = -78.0 + 4.0 * k
    py, pr = math.radians(pitch), math.radians(yaw)
    look = np.array([math.cos(py) * math.cos(pr), math.cos(py) * math.sin(pr), math.sin(py)])
    return np.array([x, 0.0, h]), look

def shot_ringdive(t):
    cam, look = ringdive_cam(t)
    roll = 4.0 * math.sin(t * 0.7)
    return R.ring_frame(cam, look, fovy=84, roll=roll)

def shot_under(t):
    """down through the sheet and up at the Sun: it blazes through the gaps, the dust round it glowing"""
    d = DUR['under']
    c0, l0 = ringdive_cam(DUR['ringdive'])
    k = ease3(t / d)
    S = R.dir_to_local(U.sun_dir_2026())
    cam = c0 + np.array([130.0 * t, 0.0, 0.0]); cam[2] = lerp(c0[2], -22.0, ease(t / (d * 0.55)))
    look = unit(lerp(l0, unit(S + np.array([0.22, 0.10, 0.0])), k))
    up = unit(lerp(np.array([0, 0, 1.0]), np.array([1.0, 0, 0]), k))
    fl = lerp(0.2, 1.6, k)
    img = R.ring_frame(cam, look, up=up, fovy=lerp(84, 78, k), dust_k=k * 1.2, flare=fl)
    if t > d - 0.5:                                       # white-out into the next shot
        w = (t - (d - 0.5)) / 0.5
        img = Image.blend(img, Image.new('RGB', img.size, (235, 250, 255)), w ** 1.5)
    return img

def shot_mystery(t):
    """the night side: a thin cyan crescent, the rings lit from behind — a cold, dark world"""
    d = DUR['mystery']
    k = ease(t / d)
    cdir = unit(-S26 + lerp(0.10, 0.17, k) * SIDE + 0.05 * NORB)
    cam = cdir * lerp(185000, 165000, k)
    tgt = SIDE * lerp(6000, 9000, k)
    return U.frame(cam, tgt, up=NORB, fovy=44, sun=S26, sun_int=220.0, ring_k=10, dust_k=6.0, rot=0.2 * t,
                   star_gain=0.9, bloom=1.3)

def shot_final(t):
    """pulling away: the planet and its rings shrink into the stars"""
    d = DUR['final']
    k = ease(t / d)
    cdir = unit(rot_about(unit(S26 + 0.35 * SIDE), NORB, math.radians(-25 - 10 * k)))
    cam = cdir * 200000 * (6.0 ** (k ** 1.5))
    return U.frame(cam, (0, 0, 0), up=NORB, fovy=40, sun=S26, rot=0.25 * t, ring_k=18)

# ---------------------------------------------------------------------------------------------------- the moons
MOONS = [('Міранда', 235.8, 1, 0.0), ('Аріель', 578.9, 3, 1.0), ('Умбріель', 584.7, 4, 2.0), ('Титанія', 788.9, 3, 3.0),
         ('Оберон', 761.4, 4, 4.0)]
def shot_moons(t):
    """the five big moons in a row in front of the planet (not their real places: a line-up), their names"""
    from PIL import ImageFont
    d = DUR['moons']
    k = ease(t / d)
    vdir = unit(rot_about(S26, NORB, math.radians(-30)) + 0.1 * NORB)
    upv = unit(NORB - vdir * (NORB @ vdir)); right = unit(np.cross(vdir, upv))
    cam = vdir * 330000 + right * lerp(-9000, 9000, k)
    sph, pos = [], []
    for i, (nm, rad, tex, q) in enumerate(MOONS):
        a = (i - 2) / 2.0
        p = vdir * (330000 - 16000 - 3500 * i) + right * (a * 3000 - 900) + upv * (2400 - 600 * a * a - 3600 * (i % 2))
        sph.append([*p, rad, tex, 0.7 * i + 0.05 * t, 0.2]); pos.append((nm, p, rad))
    img = U.frame(cam, cam - vdir * 330000 + right * lerp(-9000, 9000, k), up=upv, fovy=40, sun=S26, ring_k=16,
                  spheres=sph, rot=0.25 * t)
    # the names under them
    f = ImageFont.truetype(os.path.join(U.TOOLS, 'fonts', 'Commissioner.ttf'), 30)
    try: f.set_variation_by_axes([600])
    except Exception: pass
    dr = ImageDraw.Draw(img)
    r_, u_, f_ = U.TR.cam_basis(cam, cam - vdir * 330000 + right * lerp(-9000, 9000, k), upv)
    TY = math.tan(math.radians(20)); TX = TY * U.W / U.H
    al = int(255 * min(1.0, t / 0.5, (d - t) / 0.4))
    for nm, p, rad in pos:
        v = p - cam; z = v @ f_
        x = ((v @ r_) / z / TX + 1) / 2 * U.W; y = (1 - (v @ u_) / z / TY) / 2 * U.H
        ry = rad / z / TY / 2 * U.H
        w = dr.textlength(nm, font=f)
        dr.text((x - w / 2 + 2, y + ry + 12 + 2), nm, font=f, fill=(0, 0, 0))
        dr.text((x - w / 2, y + ry + 12), nm, font=f, fill=(235, 240, 245))
    return img

# ---------------------------------------------------------------------------------------------------- Miranda: the fall
G_MIR = 7.9e-5        # km/s², Miranda's gravity
def shot_rockfall(t):
    """beside a rock falling down Verona Rupes: 20 km take ~12 minutes; the clock races"""
    import miranda as M
    from PIL import ImageFont
    d = DUR['rockfall']
    k = t / d
    sim = 711.0 * k ** 1.7
    e = M.edge_y(0.0, M.PERM); z0 = M.ground(0.0, e - 0.004)
    dz = 0.3 + 0.5 * G_MIR * sim * sim
    zr = z0 - dz
    prof = min(0.999, dz / M.HC)
    sc = 1.0 - (1.0 - prof) ** (1 / 1.12)
    yr = e + sc * M.RUN + 0.035
    rk = [0.0, yr, zr, 0.002, 3.0]
    pull = 1.0 + 40.0 * k ** 3
    cam = np.array([0.06 * pull, yr + 0.06 * pull, zr + 0.03 * pull])
    tgt = np.array([0.0, yr - 0.02 * pull ** 0.5, zr - 0.05 * pull])
    img = M.cliff_frame(cam, tgt, fovy=60 + 8 * k, rock=rk)
    # the clock (minutes of the real fall)
    f = ImageFont.truetype(os.path.join(U.TOOLS, 'fonts', 'Unbounded.ttf'), 64)
    try: f.set_variation_by_axes([600])
    except Exception: pass
    mm, ss = int(sim // 60), int(sim % 60)
    txt = f"{mm}:{ss:02d}"
    dr = ImageDraw.Draw(img)
    w = dr.textlength(txt, font=f)
    dr.text(((U.W - w) / 2 + 3, 150 + 3), txt, font=f, fill=(0, 0, 0))
    dr.text(((U.W - w) / 2, 150), txt, font=f, fill=(255, 214, 140))
    f2 = ImageFont.truetype(os.path.join(U.TOOLS, 'fonts', 'Commissioner.ttf'), 30)
    lab = f"падає {dz:.1f} км".replace('.', ',')
    w2 = dr.textlength(lab, font=f2)
    dr.text(((U.W - w2) / 2 + 2, 235 + 2), lab, font=f2, fill=(0, 0, 0)); dr.text(((U.W - w2) / 2, 235), lab, font=f2, fill=(230, 235, 240))
    return img

# ---------------------------------------------------------------------------------------------------- Voyager 2, 1986
S86 = unit(np.array([0.139, 0.0, -0.990]))         # the Sun from Uranus in January 1986: over the south pole
SIDE86 = unit(np.cross(np.array([0.0, 1.0, 0.0]), S86))
def voyager_geom(t):
    d = DUR['voyager']
    k = t / d
    PV = unit(S86 + 0.55 * SIDE86 + 0.15 * np.array([0, 1.0, 0])) * lerp(150000, 135000, k)   # the craft (km)
    to_u = unit(-PV)
    side = unit(np.cross(to_u, np.array([0, 1.0, 0])))
    upv = unit(np.cross(side, to_u))
    a = lerp(-0.45, 0.25, ease(k))
    off = (-to_u * 15.0 + upv * 4.6 + side * (3.0 * math.sin(a)))       # the camera, m from the craft (below it)
    # aim so that the craft sits at (sx, sy) of the half-frame (right and low), Uranus beyond it
    TY = math.tan(math.radians(20)); TX = TY * U.W / U.H
    dc = unit(-off); f = dc
    for _ in range(6):
        r = unit(np.cross(upv, f)); u = np.cross(f, r)
        f = unit(dc - 0.05 * TX * r + 0.50 * TY * u)
    tgt_m = off + f * 30.0
    return PV, off, tgt_m, upv

def voyager_quat():
    """the craft's +y (the dish) towards the Sun/Earth, its booms across the view"""
    from scipy.spatial.transform import Rotation
    PV, off, tgt, upv = voyager_geom(0.0)
    side = unit(np.cross(unit(-PV), np.array([0, 1.0, 0])))
    y = S86; x = unit(side - y * (side @ y)); z = np.cross(x, y)
    return Rotation.from_matrix(np.stack([x, y, z], 1)).as_quat().tolist()

def voyager_spec():
    frames = []
    n = int(round(DUR['voyager'] * FPS))
    for fi in range(n):
        t = fi / FPS
        PV, off, tgt, upv = voyager_geom(t)
        frames.append({'f': fi, 'cam': [*off, *tgt, *upv], 'fov': 40, 'quat': voyager_quat(), 'sun': S86.tolist(),
                       'fill': unit(-PV).tolist(), 'fillK': 0.5, 'expo': 0.72})
    json.dump({'W': U.W, 'H': U.H, 'frames': frames}, open(os.path.join(U.WORK, 'voyager_spec.json'), 'w'))

def shot_voyager(t):
    PV, off, tgt, upv = voyager_geom(t)
    cam = PV + off / 1000.0; target = PV + tgt / 1000.0
    bg = U.frame(cam, target, up=upv, fovy=40, sun=S86, cap=0.0, ring_k=16, rot=0.2 * t, star_gain=0.8)
    fi = int(round(t * FPS))
    p = os.path.join(U.WORK, 'voyager', f'v_{fi:05d}.png')
    if os.path.exists(p):
        v = Image.open(p).convert('RGBA')
        bg = bg.convert('RGBA'); bg.alpha_composite(v); bg = bg.convert('RGB')
    return bg

SHOTS = {'voyager': shot_voyager, 'moons': shot_moons, 'rockfall': shot_rockfall, 'hook': shot_hook, 'scale': shot_scale, 'orbit': shot_orbit, 'ringdive': shot_ringdive, 'under': shot_under,
         'mystery': shot_mystery, 'final': shot_final}

if __name__ == '__main__' and sys.argv[1] == 'vspec':
    voyager_spec(); print('spec'); sys.exit()
if __name__ == '__main__':
    mode, name = sys.argv[1], sys.argv[2]
    fn = SHOTS[name]
    if mode == 'stills':
        for t in map(float, sys.argv[3].split(',')):
            fn(t).save(os.path.join(U.WORK, f'st_{name}_{t}.jpg'), quality=90)
            print(name, t, flush=True)
    else:
        nw, kw = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1, 0)
        out = os.path.join(U.WORK, 'shots', name); os.makedirs(out, exist_ok=True)
        n = int(round(DUR[name] * FPS))
        for fi in range(n):
            if fi % nw != kw: continue
            p = os.path.join(out, f'f_{fi:05d}.jpg')
            if os.path.exists(p): continue
            fn(fi / FPS).save(p, quality=93)
            print(name, fi, flush=True)
