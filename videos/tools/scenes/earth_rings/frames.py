# «У Землі колись могли бути кільця» — every frame from render.py, shot by shot, with crossfades.
#   python3 scenes/earth_rings/frames.py [from to]       (frames already made are kept; labels -> labels_<from>.json)
#   python3 scenes/earth_rings/frames.py stills 2,10,…    -> work/earth_rings/still_<t>.jpg
# Voice (scene.json, video time): 0.15 hook · 3.95 «над Києвом» · 6.7 asteroid · 14.05 torn apart · 17.45 ring ·
# 20.75 craters · 27.3 «саме туди падали» · 30.15 ten of millions of years, cooling · 37.0 question; end card 40.3.
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import render as RD
WK = os.path.join(TOOLS, 'work', 'earth_rings'); OUT = os.path.join(WK, 'w3d'); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 1080, 1920, 30, 44.5            # rendered at the final size
R = RD.R
ldc = lambda f: np.ascontiguousarray(np.asarray(Image.open(f).convert('RGB')).astype(np.float32) / 255)
ldg = lambda f: np.ascontiguousarray(np.asarray(Image.open(f).convert('L')).astype(np.float32) / 255)
CI, CO = ldc(os.path.join(WK, 'inner_col.png')), ldc(os.path.join(WK, 'outer_col.png'))
WI, WO = ldg(os.path.join(WK, 'inner_w.png')), ldg(os.path.join(WK, 'outer_w.png'))
LI, LO = ldg(os.path.join(WK, 'inner_l.png')), ldg(os.path.join(WK, 'outer_l.png'))
ZI = np.ascontiguousarray(np.load(os.path.join(WK, 'inner_z.npy')).astype(np.float32))
ZO = np.ascontiguousarray(np.load(os.path.join(WK, 'outer_z.npy')).astype(np.float32))
MO = ldg(os.path.join(WK, 'monument.png'))
SK = ldc(os.path.join(TOOLS, 'work', 'neutron_spoon', 'sky.jpg'))
ET = ldc(os.path.join(TOOLS, 'work', 'earth_history', 'paleo', 'ep_465.png'))

def nrm(v): v = np.asarray(v, np.float64); return v / np.linalg.norm(v)
def look(cam, tgt, upv=(0, 0, 1)):
    fw = nrm(np.subtract(tgt, cam)); rt = nrm(np.cross(fw, upv)); up = np.cross(rt, fw); return fw, rt, up
def cl(x): return min(1.0, max(0.0, x))
def sm(x): x = cl(x); return x * x * (3 - 2 * x)
def ease(x): x = cl(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, k): return a + (b - a) * k
def lerpv(a, b, k): return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * k
def proj(cam, fw, rt, up, fov, p, r=0.0):
    d = np.asarray(p, float) - cam; z = float(np.dot(d, fw))
    if z <= 0: return None
    f = (H / 2) / math.tan(math.radians(fov) / 2)
    return [W / 2 + float(np.dot(d, rt)) / z * f, H / 2 - float(np.dot(d, up)) / z * f, r / z * f]

# ---------------- Kyiv (local km: x east, y north, z up; origin 50.43° N 30.56° E)
LAT0, LON0 = 50.43, 30.56
la, lo = math.radians(LAT0), math.radians(LON0)
EE = np.array([-math.sin(lo), math.cos(lo), 0]); NN = np.array([-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)])
UU = np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])
BM = np.ascontiguousarray(np.stack([EE, NN, UU], 1))
def sunv(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
MON = np.array([0.227, -0.389, float(RD.ground_h(ZI, ZO, 0.227, -0.389)), 0.102, 0.044])

def kyiv_view(cam, az, pitch, fov, sun_az, sun_el, vis):
    cam = np.asarray(cam, float)
    d = np.array([math.sin(math.radians(az)) * math.cos(math.radians(pitch)), math.cos(math.radians(az)) * math.cos(math.radians(pitch)), math.sin(math.radians(pitch))])
    fw, rt, up = look(cam, cam + d)
    return ('kyiv', dict(cam=cam, fw=fw, rt=rt, up=up, fov=fov, sl=sunv(sun_az, sun_el), vis=vis))

def shot_dusk(t):
    # 0–6.6: dusk over the Dnipro, the ring across the south-western sky; a slow drone glide forward and up
    k = t / 6.6
    cam = lerpv([3.4, 7.4, 1.35], [2.7, 6.0, 1.45], ease(k) * 0.6 + k * 0.4)
    return kyiv_view(cam, lerp(203, 210, k), lerp(-1.0, 0.0, k), 64, 305, -4.0, 30.0), {}

def shot_night(t):
    # 36.8–end: midnight; the Earth's shadow falls across the ring in the south, its edge red; city lights
    k = (t - 36.8) / (DUR - 36.8)
    cam = lerpv([2.2, 6.6, 1.35], [1.8, 5.6, 1.45], ease(k))
    return kyiv_view(cam, lerp(188, 184, k), lerp(-1.5, -0.8, k), 64, 0, -16.0, 34.0), {}

# ---------------- space: the Earth 465 Ma (Earth-centred, z = spin axis, the ring in z = 0)
SUN = nrm([-0.62, -0.62, 0.38])
# the asteroid's flyby: a hyperbola (e 1.35, perigee 1.75 R) inclined 6° to the equator
EC, RPG = 1.35, 1.75 * R; PP = RPG * (1 + EC)
OMG = math.radians(-128); INC = math.radians(6)          # perigee on the day side
def orbit(th, dr=0.0):
    r = PP / (1 + EC * math.cos(th)) * (1 + dr)
    x, y = r * math.cos(th), r * math.sin(th)
    x, y = x * math.cos(OMG) - y * math.sin(OMG), x * math.sin(OMG) + y * math.cos(OMG)
    return np.array([x, y * math.cos(INC), y * math.sin(INC)])
def th_at(t):
    # 6.5 -> 14: inbound; 14 -> 17.5: through perigee (the breakup); 17.5 -> 20.5: away (the debris spreading)
    if t < 14.0: return lerp(-1.95, -0.85, sm((t - 6.5) / 7.5) * 0.5 + (t - 6.5) / 7.5 * 0.5)
    if t < 17.5: return lerp(-0.85, 0.75, (t - 14.0) / 3.5)
    return lerp(0.75, 1.30, cl((t - 17.5) / 3.0))
TH_BREAK = -0.45

rng = np.random.default_rng(7)
NF = 2600
F_U = rng.uniform(-1, 1, NF) * np.abs(rng.uniform(-1, 1, NF)) ** 0.5
F_DR = rng.normal(0, 1, NF); F_DZ = rng.normal(0, 1, NF)
F_SZ = np.clip(0.04 * (rng.pareto(1.5, NF) + 1), 0.04, 0.9)          # radii, km
F_SZ[:8] = [4.2, 3.4, 2.8, 2.3, 1.9, 1.6, 1.4, 1.2]                    # the biggest chunks of the 12-km rock
F_U[:8] = [-0.02, 0.05, -0.09, 0.12, -0.15, 0.2, -0.25, 0.3]
F_SEED = rng.uniform(0, 50, NF); F_RING = rng.uniform(1.42, 2.65, NF); F_PH = rng.uniform(0, 1, NF)

def fragments(t, ringk_arc, near=False):
    th = th_at(t)
    if th < TH_BREAK and not (near and t >= 14.4):
        # still whole: one lumpy asteroid ~12 km across, dark (an L-chondrite rock)
        p = orbit(th)
        return np.array([[p[0], p[1], p[2], 6.0, 0.09, 3.3, 0.55, 0.0]])
    P = np.zeros((NF, 8))
    if near:
        # close up (13.8–17.6): the rock coming apart: chunks drifting along the orbit, a cloud of debris, stretching
        c = orbit(th); v = nrm(orbit(th + 0.01) - c); n_ = nrm(c); z_ = np.cross(v, n_)
        S = 260.0 * sm((t - 14.4) / 3.4) ** 1.3 + 4.0 * cl((t - 14.4) / 0.4)
        P[:, :3] = c + np.outer(F_U * S, v) + np.outer(F_DR * S * 0.10, n_) + np.outer(F_DZ * S * 0.06, z_)
    else:
        s = (th - TH_BREAK)                                   # how far past the breakup
        spread = 0.22 * s ** 1.6
        for i in range(NF):
            thi = th + spread * F_U[i] - 0.05 * s * abs(F_U[i])
            p = orbit(thi, 0.012 * s * F_DR[i])
            p[2] += 60.0 * s * F_DZ[i]
            P[i, :3] = p
    # the ring forming: fragments sliding from the stream onto circular orbits round the equator
    if ringk_arc:
        a0, ln = ringk_arc
        for i in range(NF):
            q = cl((t - 17.4) / 3.0 - F_PH[i] * 0.5)
            if q <= 0: continue
            ang = a0 + ln * F_PH[i]
            pr = np.array([F_RING[i] * R * math.cos(ang), F_RING[i] * R * math.sin(ang), 0.0])
            P[i, :3] = P[i, :3] * (1 - sm(q)) + pr * sm(q)
    P[:, 3] = F_SZ; P[:, 4] = 0.10; P[:, 5] = F_SEED; P[:, 6] = 0.6
    P[:, 7] = 0.0
    return P

def space_view(cam, tgt, fov, ringk=1.0, rot=0.0, arc=(0.0, 7.0), band=0.0, ice=0.0, cov=0.34, parts=None, upv=(0, 0, 1), sun=SUN):
    fw, rt, up = look(cam, tgt, upv)
    return ('space', dict(cam=np.asarray(cam, float), fw=fw, rt=rt, up=up, fov=fov, ringk=ringk, rot=rot, arc=arc, band=band,
                          ice=ice, cov=cov, parts=parts, sun=sun))

def shot_approach(t):
    # 6.3–14.2: the young Earth (465 Ma) and the asteroid coming in; the camera rides beside the rock
    th = th_at(t); a = orbit(th); v = nrm(orbit(th + 0.01) - a)
    side = nrm(np.cross(v, [0, 0, 1]))
    k = (t - 6.3) / 7.9
    # behind the rock as seen from the Earth: the Earth always beyond it
    out_ = nrm(a)
    cam = a + out_ * lerp(75, 110, k) + side * lerp(22, 34, k) + np.array([0, 0, lerp(10, 16, k)])
    tgt = a - out_ * 40.0
    lab = {}
    return space_view(cam, tgt, 46, ringk=0.0, rot=1.2 + 0.01 * t, parts=fragments(t, 0)), lab

def shot_break(t):
    # 13.8–17.6: inside the Roche limit, close up: the rock cracks and the pieces drift apart along the orbit;
    # the Earth's limb fills the background
    k = (t - 13.8) / 3.8
    th = th_at(t); a = orbit(th); v = nrm(orbit(th + 0.01) - a); n_ = nrm(a); z_ = np.cross(v, n_)
    cam = a - v * lerp(35, 230, ease(k)) + n_ * lerp(55, 330, ease(k)) + z_ * lerp(20, 110, ease(k))
    tgt = a - n_ * lerp(60, 380, ease(k)) + v * lerp(10, 90, k)   # the pieces in front, the Earth's lit face behind
    return space_view(cam, tgt, 48, ringk=0.0, rot=1.25 + 0.01 * t, parts=fragments(t, 0, near=True)), {}

def shot_ring(t):
    # 17.3–20.7: the debris spreads all round: the ring closing; the camera pulls back and up
    k = (t - 17.3) / 3.4
    a0 = math.atan2(orbit(0.6)[1], orbit(0.6)[0])
    arc = (a0, lerp(0.6, 6.4, sm(k * 1.05)))
    cam = nrm(np.array([0.30, -1.0, lerp(0.55, 0.42, k)])) * lerp(52000, 64000, ease(k))
    return space_view(cam, [0, 0, -1500], 40, ringk=1.0, rot=1.3 + 0.02 * t, arc=arc, parts=fragments(t, arc)), {}

def craters():
    # 21 marks for the 21 Ordovician craters: on land within ±30° of the equator of the 465 Ma map (the paper's
    # paleo-positions are not drawn exactly: the marks only show the band)
    rr = np.random.default_rng(21); out = []
    h, w = ET.shape[:2]
    while len(out) < 21:
        lat = rr.uniform(-27, 27); lon = rr.uniform(-180, 180)
        c = ET[int((90 - lat) / 180 * (h - 1)), int((lon + 180) / 360 * (w - 1))]
        if c[0] > c[2] * 1.05:
            if all(abs(lat - a) + abs(lon - b) > 9 for a, b in out): out.append((lat, lon))
    return out
CRATERS = craters()

def shot_band(t):
    # 20.5–30.2: closer: the band ±30° lights up, 21 craters mark it; debris falling from the ring's inner edge into it
    k = (t - 20.5) / 9.7
    az = lerp(-1.95, -1.60, k); el = lerp(0.62, 0.50, k); d = lerp(31000, 27000, ease(k))
    cam = np.array([d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)])
    band = sm((t - 23.6) / 1.2)
    rot = 1.35 + 0.025 * (t - 20.5)
    lab = {'craters': [], 'streaks': []}
    fw, rt, up = look(cam, [0, 0, -400])
    for i, (lat, lon) in enumerate(CRATERS):
        if t < 21.0 + i * 0.13: continue
        # the map's lon -> the globe: lon_globe = lon_map - rot
        lg = math.radians(lon) - rot; lt = math.radians(lat)
        p = R * np.array([math.cos(lt) * math.cos(lg), math.cos(lt) * math.sin(lg), math.sin(lt)])
        if np.dot(p / R, nrm(cam - p)) < 0.08: continue          # on the far side
        q = proj(cam, fw, rt, up, 40, p)
        if q: lab['craters'].append([q[0], q[1], cl((t - 21.0 - i * 0.13) / 0.4)])
    if t > 27.0:
        sr = np.random.default_rng(int(t * 30))
        for j in range(26):
            ph = (t * 0.7 + j * 0.37) % 1.0
            ang = -2.6 + j * 0.24 + 0.1 * math.sin(j)
            r0 = 1.36 * R; r1 = R * 1.01
            lat_e = math.radians(((j * 37) % 50) - 25)
            p0 = np.array([r0 * math.cos(ang), r0 * math.sin(ang), 0.0])
            p1 = R * np.array([math.cos(lat_e) * math.cos(ang + 0.4), math.cos(lat_e) * math.sin(ang + 0.4), math.sin(lat_e)])
            a_ = proj(cam, fw, rt, up, 40, p0 + (p1 - p0) * max(0, ph - 0.25)); b_ = proj(cam, fw, rt, up, 40, p0 + (p1 - p0) * ph)
            if a_ and b_ and np.dot(p1 / R, nrm(cam - p1)) > 0.05: lab['streaks'].append([a_[0], a_[1], b_[0], b_[1], cl((t - 27.0) / 0.5)])
    return space_view(cam, [0, 0, -400], 40, ringk=1.0, rot=rot, band=band * (1 - sm((t - 29.6) / 0.6))), lab

def shot_ice(t):
    # 30.0–37.0: from a little below the ring plane: the ring's shadow across the southern (winter) hemisphere and
    # the ice cap spreading over Gondwana round the south pole
    k = (t - 30.0) / 7.0
    az = lerp(-2.45, -2.20, k); el = lerp(-0.62, -0.70, k); d = lerp(30000, 33000, ease(k))
    cam = np.array([d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)])
    ice = lerp(0.0, 36.0, sm((t - 31.5) / 5.0))
    # (the southern summer here: the Sun south of the ring plane lights the ring's southern face and the ice)
    return space_view(cam, [0, 0, -1200], 40, ringk=1.0, rot=0.9 + 0.02 * (t - 30.0), ice=ice, cov=0.30,
                      sun=nrm([-0.62, -0.62, -0.42])), {'ice': ice}

SHOTS = [(0.0, 6.6, shot_dusk), (6.3, 14.2, shot_approach), (13.8, 17.6, shot_break), (17.3, 20.7, shot_ring),
         (20.5, 30.2, shot_band), (30.0, 37.0, shot_ice), (36.7, DUR + 0.1, shot_night)]
XF = 0.35

def render_shot(kind, P, t, ss):
    out = np.zeros((H, W, 3), np.float32)
    if kind == 'kyiv':
        cam = P['cam']; se = BM @ P['sl']
        Pe = (R + cam[2]) * UU + EE * cam[0] + NN * cam[1]
        RD.kyiv(CI, CO, ZI, ZO, WI, WO, LI, LO, SK, cam, P['fw'], P['rt'], P['up'], math.radians(P['fov']), BM, Pe, P['sl'], se,
                1.0, out, ss, t, P['vis'], MON, MO)
    else:
        dep = np.full((H, W), 1e30, np.float32)
        a0, ln = P['arc']
        RD.space(ET, SK, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), P['sun'], P['rot'], P['ringk'], 1.0, out, dep, ss,
                 P['cov'], P['ice'], 0.0, a0, ln, P['band'])
        if P['parts'] is not None:
            RD.splat(out, dep, P['cam'], P['fw'], P['rt'], P['up'], math.radians(P['fov']), np.ascontiguousarray(P['parts']), P['sun'], 1)
    return out

def draw_marks(img, lab):
    # crater marks and falling debris, drawn over the tone-mapped frame
    if not lab: return img
    im = Image.fromarray(img).convert('RGBA'); lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for x, y, a in lab.get('craters', []):
        r = 16 + 18 * (1 - a)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 214, 120, int(240 * a)), width=5)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(255, 240, 200, int(255 * a)))
    for x0, y0, x1, y1, a in lab.get('streaks', []):
        d.line([x0, y0, x1, y1], fill=(255, 190, 120, int(200 * a)), width=6)
        d.line([x0, y0, x1, y1], fill=(255, 245, 220, int(230 * a)), width=2)
        d.ellipse([x1 - 7, y1 - 7, x1 + 7, y1 + 7], fill=(255, 240, 210, int(250 * a)))
    glow = lay.filter(ImageFilter.GaussianBlur(6))
    im.alpha_composite(glow); im.alpha_composite(lay)
    return np.asarray(im.convert('RGB'))

def frame(t, ss=1):
    acc = None; wsum = 0.0; labs = {}
    for a, b, fn in SHOTS:
        if a <= t < b:
            w = min(1.0, (t - a) / XF if a > 0 else 1.0, (b - t) / XF if b < DUR else 1.0)
            if w <= 0: continue
            (kind, P), lab = fn(t)
            img = render_shot(kind, P, t, ss)
            acc = img * w if acc is None else acc + img * w; wsum += w
            if w >= 0.5: labs = lab
    img = acc / max(wsum, 1e-6)
    img = (RD.tonemap(RD.bloom(img, 1.5)) * 255).astype(np.uint8)
    img = draw_marks(img, labs)
    return img, {k: v for k, v in labs.items() if k not in ('craters', 'streaks')}

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stills':
        import time
        for t in map(float, sys.argv[2].split(',')):
            t0 = time.time(); im, _ = frame(t)
            Image.fromarray(im).save(os.path.join(WK, f'still_{t}.jpg'), quality=92); print('still', t, round(time.time() - t0, 1), 's', flush=True)
        sys.exit()
    n0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0; n1 = int(sys.argv[2]) if len(sys.argv) > 2 else int(round(DUR * FPS))
    lp = os.path.join(WK, f'labels_{n0}.json'); labels = json.load(open(lp)) if os.path.exists(lp) else {}
    for i in range(n0, n1):
        f = os.path.join(OUT, f'f_{i:05d}.jpg')
        if os.path.exists(f) and str(i) in labels: continue
        im, lab = frame(i / FPS, 2 if i < 200 else 1)
        Image.fromarray(im).save(f, quality=93); labels[str(i)] = lab
        if i % 30 == 0:
            json.dump(labels, open(lp, 'w')); print('frame', i, flush=True)
    json.dump(labels, open(lp, 'w'))
