# «Знайомся: Нептун» — the shots: where the camera is, what the astronaut does and how he is lit, frame by frame, for
# the clouds (clouds.py, the background) and the three.js layer (layer.js: the astronaut, the planet from space, the
# diamonds); then the frames are laid together (comp) for compose.py.
#
#   python3 scenes/neptune_meet/shots.py clouds <shot> [n k]   -> work/neptune_meet/bg/<shot>/f_<frame>.png
#   python3 scenes/neptune_meet/shots.py spec                  -> work/neptune_meet/layer_spec.json
#   node scenes/neptune_meet/layer.js work/neptune_meet/layer_spec.json work/neptune_meet/layer [n k]
#   python3 scenes/neptune_meet/shots.py flat                  -> the flat shots (flat.py) into work/neptune_meet/flat
#   python3 scenes/neptune_meet/shots.py comp [n k]            -> work/neptune_meet/frames/f_<frame>.jpg (720×1280)
#   python3 scenes/neptune_meet/shots.py still <t> …           -> work/neptune_meet/still_<t>.jpg (quick look, low res)
#
# World: the clouds' (z up, metres). The layer is three.js (y up); T3() turns one into the other.
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clouds as C

WORK = C.WORK
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
FPS = 30
DUR = TL['dur']
NF = int(round(DUR * FPS))
SH = {s['name']: s for s in TL['shots']}
PH = TL['phrases']
W, H = 720, 1280
FOV = 66.0
# the clouds' resolution per shot (the dark, blurred backgrounds can be small)
RES = {'jump': (540, 960), 'sun': (540, 960), 'wind': (450, 800), 'deep': (540, 960),
       'hook': (360, 640), 'cold': (270, 480), 'diamonds': (360, 640), 'final': (360, 640)}
CLOUD_SHOTS = list(RES)
DEEP_BG = ('hook', 'diamonds', 'final')


def ph(i):
    return PH[i]['t0']


def sm(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def ease(x):
    x = min(1.0, max(0.0, x)); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, k):
    return a + (b - a) * k


def nrm(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)


def T3(v):
    return [float(v[0]), float(v[2]), float(-v[1])]


def quat_from_cols(x, y, z):
    m = np.array([x, y, z]).T
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2; return [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    if m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; return [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    if m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; return [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; return [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]


def body_quat(head, back):
    # the figure's frame from where his head points and where his back faces (world vectors, any length)
    head = nrm(head); back = nrm(back - head * np.dot(back, head)); xl = np.cross(head, back)
    return quat_from_cols(np.array(T3(xl)), np.array(T3(head)), np.array(T3(back)))


def n1(t, f, p):
    return math.sin(t * f + p) * 0.6 + math.sin(t * f * 1.73 + p * 2.1) * 0.3 + math.sin(t * f * 2.91 + p * 0.7) * 0.1


def light_at(p, deep_extra=0.0, lit=None):
    # how the figure is lit at world point p: the Sun through the methane (bluer the deeper) and the cloud's shade
    if lit is None:
        lit = 1.0
        M = C.NEAR
        i, j, k = int((p[0] - M[0]) / M[3]), int((p[1] - M[1]) / M[3]), int((p[2] - M[2]) / M[3])
        if 0 <= i < int(M[4]) and 0 <= j < int(M[5]) and 0 <= k < int(M[6]):
            v = SUNV[k, j, i] / 255.0; lit = math.exp(-v * v * C.TAUMAX)
    depth = C.ZTOP + 380 - p[2]
    g = [C.gas(depth / C.SUN[2], c) for c in range(3)]
    ga = [C.gas(depth, c) for c in range(3)]
    amb = [0.08, 0.16, 0.32]
    dk = 1 - deep_extra
    return dict(sun=T3(C.SUN), sunC=[1.3 * g[c] * lit * dk for c in range(3)], sky=[1.35 * amb[c] * ga[c] * dk for c in range(3)],
                gnd=[0.75 * amb[c] * ga[c] * dk for c in range(3)], rim=[0.25 * ga[0] * dk, 0.4 * ga[1] * dk, 0.6 * ga[2] * dk])


SUNV = None


# ---------------------------------------------------------------------------------------------------------- the shots
# Each returns, for shot-local time t: {'cloud': (pos, f, r, u, flash) or None, 'layer': {...} or None, 'post': {...}}

def dive_pose(f, u, r, t, k_dive=1.0):
    # the figure in front of the camera: upright with his back to us (k_dive 0) or diving head first (1), swaying
    sw = 0.3 * n1(t, 0.55, 0.3)
    c, s = math.cos(sw), math.sin(sw)
    u2 = u * c + r * s
    head = nrm(lerp(u2, 0.62 * f - 0.78 * u2, k_dive))
    back = nrm(lerp(-f, -(0.78 * f + 0.62 * u2), k_dive))
    return head, back


def shot_jump(t):
    D = SH['jump']['t1'] - SH['jump']['t0']
    k = t / D
    mx, my, _ = C.shaft(C.ZTOP - 300)
    e = ease(k)
    pos = np.array([lerp(-1000, mx - 300, e), lerp(-1250, my - 350, e), lerp(C.ZTOP + 1500, C.ZTOP + 520, k ** 1.5)])
    far = np.array([pos[0] + 3000, pos[1] + 3600, C.ZTOP + 650])
    dn = np.array([pos[0] + 700, pos[1] + 800, C.ZTOP - 900])
    w = 0.75 * ease((k - 0.15) / 0.85)
    f, r, u = C.look(pos, far * (1 - w) + dn * w, roll=0.12 * e)
    kd = ease((t - 0.4) / 1.8)          # he leans into the dive
    head, back = dive_pose(f, u, r, t, kd)
    dist = lerp(5.0, 6.5, kd)
    ap = pos + f * dist - u * lerp(1.0, 0.6, kd)
    lay = dict(cam=T3(pos) + T3(pos + f) + T3(u), fov=FOV, expo=1.0,
               astro=dict(on=True, pos=T3(ap), quat=body_quat(head, back), pt=t + 40, flow=dict(spread=lerp(0.5, 1.0, kd))),
               light=light_at(ap))
    return dict(cloud=(pos, f, r, u, None), layer=lay, post={})


def shot_sun(t):
    # above the deck, falling on his back… no: he falls belly down above us; we look up past him at the sky — the Sun a
    # hard little star among the cirrus, him dark against it with a bright rim
    pos = np.array([300.0, -200.0, C.ZTOP + 650 - 30 * t])
    sd = nrm(C.SUN)
    tgt = pos + nrm(sd * 1.0 + np.array([0, 0, -0.35])) * 1000
    f, r, u = C.look(pos, tgt, roll=0.35 + 0.04 * t)
    ap = pos + f * 5.2 - r * 1.0 - u * 0.7
    head = nrm(u * 0.9 + r * 0.35 * math.sin(t * 0.35 + 0.5))
    back = f
    L = light_at(ap, lit=1.0)
    L['rim'] = [1.0, 0.95, 0.9]
    L['gnd'] = [v * 3.0 for v in L['gnd']]   # the bright cloud deck below lights him from underneath
    lay = dict(cam=T3(pos) + T3(pos + f) + T3(u), fov=FOV, expo=1.0,
               astro=dict(on=True, pos=T3(ap), quat=body_quat(head, back), pt=t + 60, flow=dict(spread=0.9, look=[0.0, 0.3])),
               light=L)
    return dict(cloud=(pos, f, r, u, None), layer=lay, post=dict(sunstar=True))


WIND_LINE = None   # (y, z) of the wind's line through the field, chosen by pick_wind()


def shot_wind(t):
    # carried sideways over the tops of the deck: we look across the wind and down; the cloud streams past (blurred along
    # the motion), he tumbles slowly with his limbs fluttering
    D = SH['wind']['t1'] - SH['wind']['t0']
    pos = np.array([2500 + 330 * t, 3500.0, C.ZTOP + 480 - 6 * t])
    f, r, u = C.look(pos, pos + nrm([0.1, 1.0, -0.42]) * 100, roll=0.06 * n1(t, 0.8, 1))
    roll = 0.45 * t + 0.4 * n1(t, 0.5, 2)
    c, s_ = math.cos(roll), math.sin(roll)
    head = u * c + r * s_
    back = -f * 0.8 + (u * -s_ + r * c) * 0.2
    ap = pos + f * 5.2 - u * 0.3 + r * 0.25 * n1(t, 1.3, 0)
    L = light_at(ap, lit=1.0)
    lay = dict(cam=T3(pos) + T3(pos + f) + T3(u), fov=FOV, expo=1.0,
               astro=dict(on=True, pos=T3(ap), quat=body_quat(head, back), pt=t + 80, flow=dict(spread=0.7, wind=1.0)),
               light=L)
    return dict(cloud=(pos, f, r, u, None), layer=lay, post=dict(mblur=30, streaks=True))


def shot_cold(t):
    # close on him: the frost creeps over the suit and the visor; he folds his arms in; the clouds behind, blurred
    D = SH['cold']['t1'] - SH['cold']['t0']
    pos = np.array([5800.0 + 40 * t, 3500.0, C.ZTOP + 330 - 5 * t])
    f, r, u = C.look(pos, pos + nrm([0.2, 1, -0.22]) * 100, roll=0.0)
    lay_cam = [0, 0.15 + 0.03 * t, 2.25 - 0.05 * t, 0, 0.2, 0, 0, 1, 0]
    fr = sm((t - (ph(21) - SH['cold']['t0']) + 0.2) / 2.4)
    hug = ease((t - (ph(21) - SH['cold']['t0']) - 0.2) / 2.2) * 0.75
    lay = dict(cam=lay_cam, fov=34, expo=1.1,
               astro=dict(on=True, pos=[0.0, -0.45, 0], quat=[0, math.sin(math.pi / 2 - 0.15), 0, math.cos(math.pi / 2 - 0.15)],
                          pt=t + 120, flow=dict(spread=0.2 * (1 - hug), hug=hug, look=[0.15 * n1(t, 0.4, 0), -0.3]), frost=0.35 * fr),
               light=dict(sun=[0.4, 0.8, 0.5], sunC=[0.35, 0.6, 0.95], sky=[0.1, 0.2, 0.42], gnd=[0.05, 0.1, 0.22], rim=[0.3, 0.5, 0.8]))
    return dict(cloud=(pos, f, r, u, None), layer=lay, post=dict(bgblur=7, bgdim=0.9))


DECKB_FIELD = C.DECKB


def flashes(t, seed, rate, t_from=0.0):
    # lightning: strokes now and then, each flickering twice or thrice over ~0.35 s; returns (strength, index)
    rng = np.random.default_rng(seed)
    times = []; tt = t_from + rng.uniform(0.2, 1.0)
    while tt < 40: times.append(tt); tt += rng.uniform(0.7, 1.8) / rate
    best, idx = 0.0, -1
    for i, a in enumerate(times):
        dt = t - a
        if 0 <= dt < 0.45:
            v = math.exp(-dt * 9) + 0.7 * math.exp(-max(0, dt - 0.12) * 14) * (dt > 0.12) + 0.4 * math.exp(-max(0, dt - 0.25) * 16) * (dt > 0.25)
            if v > best: best, idx = v, i
    return best, idx


def shot_deep(t):
    D = SH['deep']['t1'] - SH['deep']['t0']
    z0 = C.ZTOP + 300
    z = z0 - 180 * t - 15 * t * t
    sx, sy, _ = C.shaft(z)
    mx, my, _ = C.shaft(C.ZTOP - 300)
    bl = sm(t / 1.0)
    pos = np.array([lerp(mx - 40, sx, bl), lerp(my - 30, sy, bl), z])
    tx, ty, _ = C.shaft(z - 500)
    f, r, u = C.look(pos, np.array([tx + 50 * math.sin(t * 0.4), ty, z - 500]), roll=0.2 + 0.08 * t)
    head, back = dive_pose(f, u, r, t, 1.0)
    ap = pos + f * 6.5 - u * 0.6
    tb = ph(25) - SH['deep']['t0']           # «Можливо, тут б'ють блискавки»
    fl, idx = flashes(t, 4, 1.0, tb - 0.3) if t > tb - 0.3 else (0.0, -1)
    flash = None
    if fl > 0:
        rng = np.random.default_rng(100 + idx)
        ang = rng.uniform(0, 6.28); dd = rng.uniform(250, 600)
        flash = np.array([pos[0] + dd * math.cos(ang), pos[1] + dd * math.sin(ang), z - rng.uniform(150, 500), fl * 40.0])
    dk = 0.6 * sm((t - 2.5) / (D - 2.5))
    L = light_at(ap, deep_extra=dk)
    if fl > 0:
        L['rim'] = [L['rim'][0] + 0.6 * fl, L['rim'][1] + 0.7 * fl, L['rim'][2] + 0.9 * fl]
    lay = dict(cam=T3(pos) + T3(pos + f) + T3(u), fov=FOV, expo=1.0,
               astro=dict(on=True, pos=T3(ap), quat=body_quat(head, back), pt=t + 160, flow=dict(spread=1.0)), light=L)
    return dict(cloud=(pos, f, r, u, flash), layer=lay, post=dict(expo=1 - 0.3 * sm((t - 2.5) / (D - 2.5))))


def deep_bg(t, seed, fl_rate=0.35):
    # the dark depths (for the diamonds, the hook and the end): low in the field, looking across, drifting down slowly;
    # now and then far lightning shows the shapes of the clouds
    z = 260 - 3 * t
    sx, sy, _ = C.shaft(z)
    pos = np.array([sx, sy, z])
    f, r, u = C.look(pos, pos + nrm([math.cos(0.3 + 0.01 * t), math.sin(0.3 + 0.01 * t), 0.12]) * 100)
    fl, idx = flashes(t, seed, fl_rate)
    flash = None
    if fl > 0:
        rng = np.random.default_rng(seed * 100 + idx)
        ang = 0.3 + rng.uniform(-0.6, 0.6); dd = rng.uniform(500, 900)
        flash = np.array([pos[0] + dd * math.cos(ang), pos[1] + dd * math.sin(ang), z + rng.uniform(-100, 250), fl * 30.0])
    return pos, f, r, u, flash


def gem_layer(t, cam, astro, lamp, n, k=1.0, glint=1.0, box=(0, 0, 0, 5, 6, 5), deep=1.0):
    return dict(cam=cam, fov=44, expo=1.25,
                astro=dict(astro, lamp=lamp),
                light=dict(sun=[0.2, 1, 0.1], sunC=[0.03, 0.06, 0.12], sky=[0.05, 0.1, 0.22], gnd=[0.01, 0.02, 0.06], rim=[0.06, 0.14, 0.32], deep=deep),
                gems=dict(on=True, t=t, n=n, box=list(box), fall=1.1, k=k, glint=glint))


def shot_hook(t):
    # the first frame: close on him in the dark, diamonds falling past and flashing in his lamp; he looks up at them.
    # «Стрибнемо — подивимось?»: the camera pulls back and up fast, into a white flash (→ the globe)
    tp = ph(1)
    pull = ease((t - tp - 0.4) / 1.4)
    cam = [0.35 - 0.2 * pull, 0.35 + 3.0 * pull ** 2, 1.55 + 4.5 * pull ** 1.5, 0.05, 0.25 + 0.5 * pull, 0, 0, 1, 0]
    look = [0.25 * n1(t, 0.5, 1) - 0.15, 0.35 + 0.08 * n1(t, 0.4, 2)]
    astro = dict(on=True, pos=[0, -0.75, 0], quat=[0, math.sin((math.pi - 0.45) / 2), 0, math.cos((math.pi - 0.45) / 2)], pt=t + 5,
                 flow=dict(spread=0.35, reach=0.55 * ease((t - 0.8) / 1.6), look=look))
    lay = gem_layer(t + 3, cam, astro, 7.0, 650, box=(0, 0.5, 0, 3.2, 4.0, 3.2))
    return dict(cloud=deep_bg(t + 20, 7), layer=lay, post=dict(bgblur=3, expo=4.0, white=ease((t - tp - 1.2) / 0.5)))


def shot_diamonds(t):
    # the climax: in the deep dark his lamp lights a rain of diamonds; he reaches out to one; the camera circles him
    a0 = SH['diamonds']['t0']
    on = sm((t - (ph(26) - a0) - 0.6) / 2.5)          # they come in with «тиск стискає вуглець у кристали»
    rain = sm((t - (ph(27) - a0) + 0.4) / 1.5)         # … «і вони падають дощем»: many more
    n = int(80 + 520 * on + 280 * rain)
    ang = 0.6 - 0.09 * t
    R = 3.4 - 0.12 * t
    cam = [R * math.sin(ang), 0.6 + 0.08 * t, R * math.cos(ang), 0, 0.15, 0, 0, 1, 0]
    reach = ease((t - (ph(27) - a0) + 0.6) / 2.0)
    look = [-0.3 * reach + 0.12 * n1(t, 0.5, 0), 0.25 + 0.15 * reach]
    astro = dict(on=True, pos=[0, -0.6, 0], quat=[0, math.sin((math.pi - 0.75) / 2), 0, math.cos((math.pi - 0.75) / 2)], pt=t + 200,
                 flow=dict(spread=0.4 * (1 - reach), reach=reach, look=look))
    lamp = 1.0 + 7.0 * sm((t - 0.3) / 1.2)
    lay = gem_layer(t, cam, astro, lamp, n, k=1.0, glint=1.0 + 0.6 * rain, box=(0, 0.6, 0, 4.5, 5.5, 4.5))
    return dict(cloud=deep_bg(t + 60, 9, 0.25), layer=lay, post=dict(bgblur=3, expo=4.0))


def shot_final(t):
    # «Дна ти не побачиш — його немає»: he sinks away below us into the dark, his lamp a dwindling light among the last
    # glints; the end card comes over it
    D = SH['final']['t1'] - SH['final']['t0']
    sink = ease(t / 6.5)
    cam = [0, 1.2, 2.8, 0, -1.0 - 4 * sink, 0, 0, 1, 0]
    astro = dict(on=True, pos=[0.2 * math.sin(t * 0.3), -0.6 - 16 * sink ** 1.4, -2.0 * sink], quat=[math.sin(-0.35 * sink), 0, 0, math.cos(-0.35 * sink)],
                 pt=t + 260, flow=dict(spread=0.85, look=[0.0, -0.3]))
    lay = gem_layer(t + 12, cam, astro, 6.0 * (1 - 0.6 * sink), int(500 * (1 - 0.7 * sm(t / 6))), glint=0.8, box=(0, -4, 0, 5, 9, 5))
    return dict(cloud=deep_bg(t + 100, 11, 0.12), layer=lay, post=dict(bgblur=3, expo=4.0, bgdim=1 - 0.6 * sm(t / D)))


def shot_globe(t):
    # Neptune from space (the real pale colour), Triton, the rings; he floats in front with his back to us. With «вчетверо
    # ширший за Землю» the Earth fades in beside it, to scale
    a0 = SH['globe']['t0']
    D = SH['globe']['t1'] - a0
    k = t / D
    sun = nrm([0.75, 0.18, 0.62])
    dist = lerp(165000, 140000, ease(k))
    cam_km = [dist * 0.18, 16000 - 4000 * k, dist, 0, 1500, 0, 0, 1, 0]
    te = ph(3) - a0 + 2.6                              # «… ширший за Землю»
    ek = sm((t - te) / 0.8) * (1 - sm((t - (ph(4) - a0) - 1.2) / 0.8))
    space = dict(on=True, cam=cam_km, pale=1.0, nepRot=0.003 * t, triton=[-60000, 26000, 60000],
                 earth=dict(on=ek > 0.01, pos=[20323, 25421, -5635], k=ek), stars=True, expo=1.0)
    cam = [0.0, 0.25, 3.4 - 0.15 * k, 0.0, 0.15, -10, 0, 1, 0]
    astro = dict(on=True, pos=[-0.75 + 0.05 * n1(t, 0.3, 0), -1.3 + 0.04 * n1(t, 0.25, 1), -2.2], quat=[0, math.sin(-0.3), 0, math.cos(-0.3)],
                 pt=t + 300, flow=dict(spread=0.25, look=[0.1 * n1(t, 0.3, 2) - 0.2, 0.08]))
    lay = dict(t=t, cam=cam, fov=40, expo=1.0, astro=astro, space=space,
               light=dict(sun=T3_dir(sun), sunC=[1.25, 1.22, 1.18], sky=[0.015, 0.02, 0.03], gnd=[0.02, 0.04, 0.08], rim=[0.15, 0.3, 0.55]))
    return dict(cloud=None, layer=lay, post=dict(earth_label=ek, sun=sun, cam_km=cam_km))


def T3_dir(v):
    # a direction already in three.js axes (the globe is built there directly)
    return [float(v[0]), float(v[1]), float(v[2])]


SHOT_FN = {'hook': shot_hook, 'globe': shot_globe, 'jump': shot_jump, 'sun': shot_sun, 'wind': shot_wind,
           'cold': shot_cold, 'deep': shot_deep, 'diamonds': shot_diamonds, 'final': shot_final}


def shot_of(fi):
    t = fi / FPS
    for s in TL['shots']:
        if s['t0'] <= t < s['t1']:
            return s['name'], t - s['t0']
    s = TL['shots'][-1]; return s['name'], t - s['t0']


def pick_wind():
    # the line for the wind shot: a y, z in the field where the line x = -850 … 850 crosses the least cloud
    den = np.load(os.path.join(WORK, 'near_den.npy'), mmap_mode='r')
    M = C.NEAR; best = None
    xs = np.arange(-850, 851, 10)
    for z in range(1150, 1700, 50):
        for y in range(-700, 701, 50):
            occ = 0.0
            for dx in xs:
                for dz in (-15, 0, 15):
                    for dy in (-15, 0, 15):
                        i = int((dx - M[0]) / M[3]); j = int((y + dy - M[1]) / M[3]); k = int((z + dz - 18 * 5 - M[2]) / M[3])
                        occ += den[k, j, i]
            # and some cloud not far away (so there is something to stream past)
            near = sum(int(den[int((z - M[2]) / M[3]), int((y + 120 - M[1]) / M[3]), int((dx - M[0]) / M[3])]) for dx in xs[::5])
            score = occ - 0.02 * near
            if best is None or score < best[0]:
                best = (score, y, z)
    return best[1], best[2]


def wind_line():
    global WIND_LINE
    fn = os.path.join(WORK, 'wind_line.json')
    if not os.path.exists(fn):
        json.dump(list(pick_wind()), open(fn, 'w'))
    WIND_LINE = tuple(json.load(open(fn)))


def load_sun():
    global SUNV
    if SUNV is None:
        SUNV = np.load(os.path.join(WORK, 'near_sun.npy'), mmap_mode='r')


def frames_of(name):
    s = SH[name]
    return range(int(round(s['t0'] * FPS)), int(round(s['t1'] * FPS)))


def render_clouds(name, nw=1, kw=0):
    from PIL import Image
    vols = C.load()
    wind_line(); load_sun()
    out = os.path.join(WORK, 'bg', name); os.makedirs(out, exist_ok=True)
    w, h = RES[name]
    for fi in frames_of(name):
        if fi % nw != kw: continue
        fn = os.path.join(out, f'f_{fi:05d}.png')
        if os.path.exists(fn): continue
        _, t = shot_of(fi)
        pos, f, r, u, flash = SHOT_FN[name](t)['cloud']
        img = np.zeros((h, w, 3), np.float64)
        C.render(*vols, img, pos, f, r, u, math.radians(FOV), 1.0, fi, 3 if name in DEEP_BG else 1, np.zeros(4) if flash is None else np.asarray(flash, float))
        np.save(fn[:-4] + '.npy', img.astype(np.float16))   # linear, for the post (blur, glare) before the tone curve
        Image.fromarray(C.tonemap(img)).save(fn)
        print(name, fi, flush=True)


def spec():
    wind_line(); load_sun()
    fr = []
    for fi in range(NF):
        name, t = shot_of(fi)
        if name not in SHOT_FN: continue
        L = SHOT_FN[name](t)['layer']
        if L is None: continue
        L['f'] = fi; L.setdefault('t', t)
        fr.append(L)
    json.dump(dict(W=W, H=H, frames=fr), open(os.path.join(WORK, 'layer_spec.json'), 'w'))
    print(len(fr), 'layer frames')


# ---------------------------------------------------------------------------------------------------------- laying it together
FLAT = ('color', 'paper', 'orbit')


def project(d, f, r, u, fov, w, h):
    z = np.dot(d, f)
    if z <= 1e-6: return None
    tf = math.tan(math.radians(fov) / 2)
    x = np.dot(d, r) / z / (tf * w / h); y = np.dot(d, u) / z / tf
    return (x * 0.5 + 0.5) * w, (0.5 - y * 0.5) * h


def sun_glare(img, px, py, k=1.0):
    # the Sun from 30 au: a hard white point with a small halo and thin spikes (in linear light, before the tone curve)
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - px, yy - py
    r2 = dx * dx + dy * dy
    s = w / 540.0
    g = 60.0 * np.exp(-r2 / (2.2 * s) ** 2) + 2.2 * np.exp(-r2 / (14 * s) ** 2) + 0.35 * np.exp(-np.sqrt(r2) / (60 * s))
    for a in (0.35, 0.35 + math.pi / 2, 0.35 + math.pi / 4, 0.35 - math.pi / 4):
        ca, sa = math.cos(a), math.sin(a)
        along = dx * ca + dy * sa; across = -dx * sa + dy * ca
        g += (0.9 if a in (0.35, 0.35 + math.pi / 2) else 0.35) * np.exp(-np.abs(along) / (90 * s)) * np.exp(-(across / (1.1 * s)) ** 2)
    img += (g * k)[..., None] * np.array([1.0, 0.97, 0.92])[None, None, :]


def blur_lin(a, sig):
    from scipy.ndimage import gaussian_filter
    return np.stack([gaussian_filter(a[..., c], sig) for c in range(3)], -1)


def comp_frame(fi):
    from PIL import Image, ImageDraw, ImageFilter
    if SUNV is None: wind_line(); load_sun()
    name, t = shot_of(fi)
    if name in FLAT:
        return Image.open(os.path.join(WORK, 'flat', f'f_{fi:05d}.jpg')).convert('RGB')
    S = SHOT_FN[name](t)
    P = S['post']
    if S['cloud'] is not None:
        a = np.load(os.path.join(WORK, 'bg', name, f'f_{fi:05d}.npy')).astype(np.float32)
        h, w = a.shape[:2]
        if P.get('sunstar'):
            pos, f, r, u, _ = S['cloud']
            q = project(nrm(C.SUN), f, r, u, FOV, w, h)
            if q: sun_glare(a, q[0], q[1])
        if P.get('bgblur'): a = blur_lin(a, P['bgblur'] * w / 360.0)
        if P.get('mblur'):
            from scipy.ndimage import uniform_filter1d
            a = uniform_filter1d(a, int(P['mblur'] * w / 540.0), axis=1, mode='nearest')
        a *= P.get('expo', 1.0) * P.get('bgdim', 1.0)
        bg = Image.fromarray(C.tonemap(a)).resize((W, H), Image.LANCZOS)
        if w < 600: bg = bg.filter(ImageFilter.GaussianBlur(0.6))
    else:
        bg = Image.new('RGB', (W, H), (0, 0, 0))
    im = bg.convert('RGBA')
    lf = os.path.join(WORK, 'layer', f'a_{fi:05d}.png')
    if os.path.exists(lf):
        im.alpha_composite(Image.open(lf).convert('RGBA'))
    if P.get('streaks'):
        # ice needles rushing past in the wind, on the near side of him too
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        rng = np.random.default_rng(5)
        for i in range(70):
            y = rng.uniform(0, H); sp = rng.uniform(1500, 4200); L = rng.uniform(60, 260); ph = rng.uniform(0, 3)
            x = W + 300 - ((t + ph) * sp) % (W + 600)
            al = int(rng.uniform(40, 130))
            d.line([x, y, x + L, y - L * 0.06], fill=(220, 235, 255, al), width=int(rng.uniform(1, 3)))
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.0)))
    if P.get('earth_label', 0) > 0.05:
        c = S['post']['cam_km']; pos = np.array(c[:3]); tg = np.array(c[3:6]); upv = np.array(c[6:9])
        f = nrm(tg - pos); r = nrm(np.cross(f, upv)); u = np.cross(r, f)
        q = project(np.array([20323, 25421, -5635]) - pos, f, r, u, 40, W, H)
        if q:
            from flat import label
            label(im, 'Земля', q[0] - 4, q[1] + 52, 28, fill=(200, 225, 255), alpha=P['earth_label'])
    if P.get('white', 0) > 0:
        im = Image.blend(im, Image.new('RGBA', (W, H), (235, 245, 255, 255)), min(1.0, P['white']))
    return im.convert('RGB')


def comp(nw=1, kw=0):
    out = os.path.join(WORK, 'frames'); os.makedirs(out, exist_ok=True)
    for fi in range(NF):
        if fi % nw != kw: continue
        comp_frame(fi).save(os.path.join(out, f'f_{fi:05d}.jpg'), quality=94)
        if fi % 150 == 0: print('comp', fi, flush=True)


def flat_all():
    import flat
    out = os.path.join(WORK, 'flat'); os.makedirs(out, exist_ok=True)
    c0 = SH['color']['t0']; Tc = dict(pale=ph(6) - c0, why=ph(7) - c0)
    p0 = SH['paper']['t0']; Tp = dict(sky=ph(9) - p0 + 1.5, seen=ph(10) - p0)
    o0 = SH['orbit']['t0']; To = dict(go=ph(11) - o0 + 0.3, end=PH[12]['t1'] - o0 - 0.2)
    for nm, T, fn in (('color', Tc, flat.shot_color), ('paper', Tp, flat.shot_paper), ('orbit', To, flat.shot_orbit)):
        for fi in frames_of(nm):
            fn(fi / FPS - SH[nm]['t0'], T).save(os.path.join(out, f'f_{fi:05d}.jpg'), quality=94)
        print('flat', nm, flush=True)


def preview(times):
    # quick look: the clouds small, the layer at 360×640, laid together like comp (no titles)
    import subprocess
    from PIL import Image
    global W, H
    vols = C.load(); wind_line(); load_sun()
    pv = os.path.join(WORK, 'pv'); os.makedirs(pv, exist_ok=True)
    fr = []
    for t in times:
        fi = int(round(t * FPS)); name, lt = shot_of(fi)
        if name in FLAT: continue
        S = SHOT_FN[name](lt)
        if S['cloud'] is not None:
            pos, f, r, u, flash = S['cloud']
            img = np.zeros((480, 270, 3), np.float64)
            C.render(*vols, img, pos, f, r, u, math.radians(FOV), 1.0, fi, 3 if name in DEEP_BG else 1, np.zeros(4) if flash is None else np.asarray(flash, float))
            os.makedirs(os.path.join(WORK, 'bg', name), exist_ok=True)
            np.save(os.path.join(pv, f'bg_{fi:05d}.npy'), img.astype(np.float16))
        L = S['layer']; L['f'] = fi; L.setdefault('t', lt); fr.append(L)
    json.dump(dict(W=360, H=640, frames=fr), open(os.path.join(pv, 'spec.json'), 'w'))
    subprocess.run(['node', os.path.join(HERE, 'layer.js'), os.path.join(pv, 'spec.json'), pv], check=True, env=dict(os.environ, FORCE='1'))
    ims = []
    for t in times:
        fi = int(round(t * FPS)); name, lt = shot_of(fi)
        if name in FLAT: continue
        S = SHOT_FN[name](lt); P = S['post']
        bgf = os.path.join(pv, f'bg_{fi:05d}.npy')
        if S['cloud'] is not None:
            a = np.load(bgf).astype(np.float32)
            if P.get('sunstar'):
                pos, f, r, u, _ = S['cloud']; q = project(nrm(C.SUN), f, r, u, FOV, 270, 480)
                if q: sun_glare(a, q[0], q[1], 1.0)
            if P.get('bgblur'): a = blur_lin(a, P['bgblur'] * 270 / 360.0)
            if P.get('mblur'):
                from scipy.ndimage import uniform_filter1d
                a = uniform_filter1d(a, max(1, int(P['mblur'] * 270 / 540.0)), axis=1, mode='nearest')
            a *= P.get('expo', 1.0) * P.get('bgdim', 1.0)
            bg = Image.fromarray(C.tonemap(a)).resize((360, 640), Image.LANCZOS)
        else:
            bg = Image.new('RGB', (360, 640))
        im = bg.convert('RGBA'); im.alpha_composite(Image.open(os.path.join(pv, f'a_{fi:05d}.png')).convert('RGBA'))
        if P.get('white', 0) > 0: im = Image.blend(im, Image.new('RGBA', (360, 640), (235, 245, 255, 255)), min(1.0, P['white']))
        ims.append(im.convert('RGB'))
    sh = Image.new('RGB', (360 * len(ims), 640))
    for i, im in enumerate(ims): sh.paste(im, (i * 360, 0))
    sh.save(os.path.join(WORK, 'sheet.png'))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'clouds':
        nw, kw = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1, 0)
        render_clouds(sys.argv[2], nw, kw)
    elif cmd == 'spec':
        spec()
    elif cmd == 'comp':
        nw, kw = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1, 0)
        comp(nw, kw)
    elif cmd == 'flat':
        flat_all()
    elif cmd == 'preview':
        preview([float(x) for x in sys.argv[2].split(',')])
    elif cmd == 'wind':
        wind_line(); print(WIND_LINE)
