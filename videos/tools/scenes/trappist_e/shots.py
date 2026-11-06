# «Знайомся: TRAPPIST-1e» — every frame of the video: the cameras, what is on screen and when, hung on timeline.json.
#   python3 shots.py frames [workers] [k]   -> work/trappist_e/frames/f_%05d.jpg (frames already there are kept)
#   python3 shots.py stills t1,t2,...       -> scratch stills to look at
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, TOOLS]
import render as R
import planet as PL
import still as ST

TL = json.load(open(os.path.join(HERE, 'timeline.json')))
SH = {s['name']: (s['t0'], s['t1']) for s in TL['shots']}
PH = TL['phrases']
DUR = TL['dur']
OUT = os.path.join(PL.WORK, 'frames')
W, H = R.W, R.H

def ease(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def ease2(x):                                   # gentler (sine)
    x = min(1.0, max(0.0, x)); return 0.5 - 0.5 * math.cos(math.pi * x)

def ramp(t, a, b): return min(1.0, max(0.0, (t - a) / (b - a)))

def nrm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

def slerp(a, b, k):
    a, b = nrm(a), nrm(b); d = min(1.0, max(-1.0, float(a @ b)))
    w = math.acos(d)
    if w < 1e-6: return a
    return (math.sin((1 - k) * w) * a + math.sin(k * w) * b) / math.sin(w)

def ph(i): return PH[i]['t0'], PH[i]['t1']

def font(size, wght=600, file='Unbounded.ttf'):
    f = ImageFont.truetype(os.path.join(TOOLS, 'fonts', file), size)
    try: f.set_variation_by_axes([wght if a['name'] in (b'Weight', 'Weight') else a['default'] for a in f.get_variation_axes()])
    except Exception: pass
    return f

def label(img, xy, text, size=17, alpha=1.0, fill=(235, 236, 244), anchor='mm', wght=500, file='Unbounded.ttf'):
    if alpha <= 0: return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    f = font(size, wght, file)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0], xy[1] + 2), text, font=f, anchor=anchor, fill=(0, 0, 0, int(200 * alpha)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
    d.text(xy, text, font=f, anchor=anchor, fill=fill + (int(255 * alpha),))
    img.alpha_composite(lay)

# ---- cameras ----
# the approved still's view (the "eye")
CAM_EYE = PL.s2p(-ST.C); F_EYE = PL.s2p([0, 0, 1]); U_EYE = PL.s2p([0, 1, 0])
SDIR = np.array([1.0, 0.0, 0.0])

def hook_cam(push=0.0, swing=0.0):
    """the crescent with the star above right: the camera behind the night side"""
    pos = np.array([-7.6 + 0.6 * push, -2.9 - 0.9 * swing, 1.7 + 0.2 * swing])
    dp = nrm(-pos); ds = nrm(np.array([PL.A_E, 0, 0]) - pos)
    f = nrm(dp * 0.60 + ds * 0.40)
    up0 = ds - dp; up0 = nrm(up0 - f * (up0 @ f))
    rt = nrm(np.cross(up0, f))
    a = math.radians(24)
    up = nrm(up0 * math.cos(a) - rt * math.sin(a))
    return pos, f, up

def frame_for(pos):
    """the hook's framing for any camera position: the planet low left, the star (or where it hides) up right"""
    dp = nrm(-pos); ds = nrm(np.array([PL.A_E, 0, 0]) - pos)
    f = nrm(dp * 0.60 + ds * 0.40)
    up0 = ds - dp
    if np.linalg.norm(up0 - f * (up0 @ f)) < 1e-6: up0 = np.array([0, 0, 1.0])
    up0 = nrm(up0 - f * (up0 @ f))
    rt = nrm(np.cross(up0, f))
    a = math.radians(24)
    return f, nrm(up0 * math.cos(a) - rt * math.sin(a))

HOOK_END = hook_cam(push=0.8, swing=0.15)[0]
_C1 = nrm(HOOK_END); _A = np.array([-1.0, 0, 0])
_SEP1 = math.degrees(math.acos(float(_C1 @ _A)))
_C0 = slerp(_A, _C1, 5.3 / _SEP1)                       # the star 5.3° from the planet's centre: just hidden behind it

def rise_cam(k):
    """the star rising from behind the planet's limb (k 0..1)"""
    c = slerp(_C0, _C1, k)
    pos = c * (7.95 + (np.linalg.norm(HOOK_END) - 7.95) * k)
    f, up = frame_for(pos)
    return pos, f, up

def view(pos, f, up, fovy=34.0, **kw):
    return R.frame3d(pos, pos + f, fovy, up, **kw)

def nb_at(t_days, f_rel, g_rel):
    return R.neighbours(t_days, {'f': f_rel, 'g': g_rel})

# the neighbours' angles for the wide views: chosen so they stand in the upper part of the eye view (see place())
NB_EYE = None

def place(pos, f, up, fovy, targets):
    """angles (deg) ahead of e for f and g that put them near the given screen points"""
    best = {}
    for nm, (tx, ty) in targets.items():
        bb = None
        for rel in np.arange(-180, 180, 0.25):
            row = R.neighbours(0, {'f': rel, 'g': rel}, names=(nm,))[0]
            v = row[:3] - pos
            if v @ f <= 0: continue
            x, y = R.project(pos, pos + f, fovy, row[:3], up)
            e = math.hypot(x - tx, y - ty) + 0.02 * np.linalg.norm(v)
            if bb is None or e < bb[0]: bb = (e, rel)
        best[nm] = bb[1]
    return best

_NB = {}
def eye_neighbours():
    if 'eye' not in _NB:
        _NB['eye'] = place(CAM_EYE * 1.12, F_EYE, U_EYE, 34.0, {'f': (560, 400), 'g': (430, 270)})
    return _NB['eye']

# ---- the 2D pieces: the star beside the Sun and Jupiter; the system seen from above ----
def sphere_layer(img, cx, cy, rpx, kind, t=0.0):
    """draws a lit or glowing sphere into the HDR image (render resolution)"""
    RH, RW = img.shape[:2]
    x0, x1 = max(0, int(cx - rpx - 2)), min(RW, int(cx + rpx + 3)); y0, y1 = max(0, int(cy - rpx - 2)), min(RH, int(cy + rpx + 3))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    u = (xx + 0.5 - cx) / rpx; v = (yy + 0.5 - cy) / rpx
    rr = u * u + v * v
    cov = np.clip((1 - np.sqrt(rr)) * rpx + 0.5, 0, 1)
    mu = np.sqrt(np.clip(1 - rr, 0, 1))
    if kind == 'sun':
        col = np.array([1.0, 0.80, 0.42]) * 0.78
        gran = 1 - 0.035 * np.clip(np.sin(u * 61 + np.sin(v * 37) * 2) * np.sin(v * 57 + np.sin(u * 29) * 2), 0, 1)
        I = (0.32 + 0.68 * mu ** 0.55)[..., None] * col * gran[..., None]
    elif kind == 'trappist':
        c_ = PL.ST.bb_rgb(2566.0) ** 1.35; c_ = c_ / c_.max()
        I = (0.30 + 0.70 * mu ** 0.7)[..., None] * c_ * 0.62
    else:   # jupiter: bands, lit from the upper left
        lat = np.arcsin(np.clip(-v, -1, 1))
        band = 0.5 + 0.5 * np.sin(lat * 14 + 0.8 * np.sin(lat * 5 + u * 3))
        base = np.array([0.78, 0.68, 0.55]) * (0.75 + 0.25 * band[..., None])
        base = base * (1 - 0.18 * (np.abs(lat) > 1.0)[..., None])
        L = nrm([-0.5, 0.45, 0.75]); nz = mu
        dif = np.clip(u * L[0] + (-v) * L[1] + nz * L[2], 0, 1)
        I = base * (dif[..., None] * 0.95 + 0.03)
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - cov[..., None]) + I * cov[..., None]

def glow(img, cx, cy, rpx, col, k):
    RH, RW = img.shape[:2]
    q = 4
    yy, xx = np.mgrid[0:RH // q, 0:RW // q].astype(np.float32) * q
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(rpx, 1)
    g = (k * np.clip(1 / np.maximum(d, 1.0), 0, 1) ** 2.2).astype(np.float32)
    g = np.asarray(Image.fromarray(g, 'F').resize((RW, RH), Image.BILINEAR), np.float32)
    img += g[..., None] * np.asarray(col, np.float32)

def sky_plate(f=(0.3, 0.9, -0.3), up=(0, 0, 1), gain=0.6):
    pos = np.zeros(3); f = nrm(f)
    TY = math.tan(math.radians(34) / 2); TX = TY * R.RW / R.RH
    r, u, ff = R.cam_basis(pos, pos + f, up)
    mask = np.zeros((R.RH, R.RW), np.float32)
    return R.background(r, u, ff, TX, TY, mask, gain, 0.28)

_PLATE = {}
def plate(name, **kw):
    if name not in _PLATE: _PLATE[name] = sky_plate(**kw)
    return _PLATE[name].copy()

def shot_star(t):
    """«але її зоря — не Сонце, а тьмяний червоний карлик, ледь більший за Юпітер»: the Sun big, TRAPPIST-1 and
    Jupiter to scale beside it; then the view closes in on the two small ones"""
    a, b = SH['star']
    t_sun = ph(8)[0]; t_dw = ph(9)[0]; t_ju = ph(9)[0] + 1.9
    img = plate('star', f=(0.2, 1.0, 0.1), gain=0.45) * 0.5
    RW, RH = R.RW, R.RH
    z = ease2(ramp(t, t_dw + 0.3, t_ju + 1.0))            # 0: the whole Sun; 1: closed in on the pair
    s0, s1 = 520.0, 520.0 * 4.2                             # px per Sun radius
    sc = s0 * (s1 / s0) ** z
    sun_c = np.array([RW * 0.50, RH * 0.40])
    pair = sun_c + np.array([0.0, 1.0 + 0.55]) * s0 * 1.0   # where the pair stands (in Sun radii from its centre, at s0)
    pair_u = np.array([0.0, 1.55])                          # pair position in Sun radii
    focus = pair_u * z                                       # the point the view closes in on
    def to_px(pu): return sun_c + (np.asarray(pu) - focus) * sc + np.array([0, (RH * 0.46 - sun_c[1]) * z])
    k_sun = ease(ramp(t, a, a + 0.6))
    k_dw = ease(ramp(t, t_dw - 0.1, t_dw + 0.5))
    k_ju = ease(ramp(t, t_ju - 0.2, t_ju + 0.4))
    if k_sun > 0:
        c = to_px([0, 0]); tmp = img.copy(); sphere_layer(tmp, c[0], c[1], sc * 1.0, 'sun'); img = img * (1 - k_sun) + tmp * k_sun
        glow(img, c[0], c[1], sc, np.array([1.0, 0.75, 0.4]), 0.035 * k_sun)
    rt, rj = 0.1192, 0.10045
    if k_dw > 0:
        c = to_px([-0.17, 1.55]); tmp = img.copy(); sphere_layer(tmp, c[0], c[1], sc * rt, 'trappist'); img = img * (1 - k_dw) + tmp * k_dw
        glow(img, c[0], c[1], sc * rt, np.array([1.0, 0.42, 0.10]), 0.12 * k_dw)
    if k_ju > 0:
        c = to_px([0.17, 1.55]); tmp = img.copy(); sphere_layer(tmp, c[0], c[1], sc * rj, 'jupiter'); img = img * (1 - k_ju) + tmp * k_ju
    pic = R.finish(img, 0.8).convert('RGBA')
    def lab(pu, dy, txt, k):
        c = to_px(pu) / R.SS; label(pic, (c[0], c[1] + dy), txt, 16, k)
    lab([0, 0], 0, 'Сонце', k_sun * (1 - z) * 0.0)
    c_s = to_px([0, -1.0]) / R.SS; c_b = to_px([0, 1.0]) / R.SS
    if c_s[1] - 30 > 230: label(pic, (c_s[0], c_s[1] - 30), 'Сонце', 22, k_sun)
    elif c_b[1] > 300: label(pic, (W / 2, c_b[1] - 60), 'Сонце', 22, k_sun, fill=(80, 48, 12))
    else: label(pic, (W / 2, max(c_b[1] + 46, 240)), '↑ Сонце', 22, k_sun)
    def lab2(pu, dy, txt, k):
        c = to_px(pu) / R.SS; label(pic, (c[0], c[1] + dy), txt, 20, k)
    lab2([-0.17, 1.55], rt * sc / R.SS + 28, 'TRAPPIST-1', k_dw)
    lab2([0.17, 1.55], rj * sc / R.SS + 28, 'Юпітер', k_ju)
    return pic.convert('RGB')

ORB = ['b', 'c', 'd', 'e', 'f', 'g', 'h']
def system_img(t_days, px_per_au, centre, show_merc=0.0, hi_e=1.0, labels=1.0, plate_name='sys', fade_rest=1.0):
    """the seven orbits from above, planets at their real angles for day t_days (sizes enlarged), the star glowing"""
    img = plate(plate_name, f=(-0.3, -0.9, 0.45), gain=0.5) * 0.45
    RW, RH = R.RW, R.RH
    cx, cy = centre
    # the star
    rs = max(4.0, PL.R_STAR * PL.UNIT / PL.AU_KM * px_per_au)
    sphere_layer(img, cx, cy, max(rs, 7.0), 'trappist'); glow(img, cx, cy, max(rs, 7.0) * 1.6, np.array([1.0, 0.45, 0.12]), 0.9)
    pic = R.finish(img, 0.9).convert('RGBA')
    lay = Image.new('RGBA', pic.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    s = 1 / R.SS
    pos = {}
    for nm in ORB:
        rad, a, Pd = PL.PLANETS[nm]
        rr = a * px_per_au * s
        ang = math.radians(37 * ORB.index(nm) + 15) + 2 * math.pi * t_days / Pd
        isE = nm == 'e'
        col = (255, 196, 120) if isE else (150, 178, 230)
        al = (0.9 if isE else 0.55) * (hi_e if isE else fade_rest)
        d.ellipse((cx * s - rr, cy * s - rr, cx * s + rr, cy * s + rr), outline=col + (int(255 * al),), width=2 if isE else 1)
        x, y = cx * s + rr * math.cos(ang), cy * s - rr * math.sin(ang)
        pos[nm] = (x, y)
    if show_merc > 0:
        rr = 0.3871 * px_per_au * s
        d.ellipse((cx * s - rr, cy * s - rr, cx * s + rr, cy * s + rr), outline=(255, 255, 255, int(200 * show_merc)), width=2)
    pic.alpha_composite(lay)
    # the planets: little lit discs (lit from the star)
    for nm in ORB:
        x, y = pos[nm]
        r_ = (4.0 + 3.0 * PL.PLANETS[nm][0]) * min(1.0, max(0.35, px_per_au / 10300.0))
        isE = nm == 'e'
        sp = Image.new('RGBA', (int(r_ * 6), int(r_ * 6)), (0, 0, 0, 0)); ds = ImageDraw.Draw(sp)
        c0 = sp.size[0] / 2
        col = (255, 214, 160) if isE else (210, 200, 190)
        al = (hi_e if isE else fade_rest) * labels
        ds.ellipse((c0 - r_, c0 - r_, c0 + r_, c0 + r_), fill=col + (int(255 * al),))
        if isE:
            gl = Image.new('RGBA', sp.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse((c0 - r_ * 2.2, c0 - r_ * 2.2, c0 + r_ * 2.2, c0 + r_ * 2.2), fill=(255, 190, 110, int(110 * al)))
            sp = Image.alpha_composite(gl.filter(ImageFilter.GaussianBlur(r_)), sp)
        pic.alpha_composite(sp, (int(x - c0), int(y - c0)))
        kl = labels * min(1.0, max(0.0, (px_per_au - 6000.0) / 3000.0))
        if kl > 0:
            label(pic, (x + r_ + 8, y - r_ - 6), nm, 20 if not isE else 24, al * kl, fill=(255, 214, 160) if isE else (205, 210, 225), anchor='lm')
    return pic, pos

def shot_year(t):
    a, b = SH['year']
    # one year of e in ~3.2 s from the first words, then slower
    t0 = ph(10)[0]
    days = 6.0996 * ease2(ramp(t, t0, t0 + 3.4)) + 0.25 * max(0.0, t - t0 - 3.4)
    px = 10300.0
    pic, pos = system_img(days, px, (R.RW * 0.5, R.RH * 0.53))
    k = ease(ramp(t, a, a + 0.6)) * (1 - ease(ramp(t, b - 0.3, b)))
    return pic.convert('RGB')

def shot_system(t):
    a, b = SH['system']
    t1 = ph(19)[0]
    z = ease2(ramp(t, t1 - 0.2, t1 + 2.4))
    px0, px1 = 10300.0, 1650.0
    px = px0 * (px1 / px0) ** z
    pic, pos = system_img(8.0 + 0.3 * (t - a), px, (R.RW * 0.5, R.RH * 0.53), show_merc=ease(ramp(t, t1 + 0.4, t1 + 1.6)),
                          plate_name='sys')
    rr = 0.3871 * px / R.SS
    label(pic, (W / 2, R.RH * 0.53 / R.SS - rr - 24), 'орбіта Меркурія', 20, ease(ramp(t, t1 + 1.7, t1 + 2.4)), fill=(255, 255, 255))
    label(pic, (W / 2, R.RH * 0.53 / R.SS + 42), 'уся система TRAPPIST-1', 16, ease(ramp(t, t1 + 1.6, t1 + 2.4)) * 0.9, fill=(255, 214, 160), wght=400, file='Commissioner.ttf')
    return pic.convert('RGB')

def eye_wide(push=0.0):
    pos = CAM_EYE * (1.12 - 0.12 * push)
    return pos, F_EYE, U_EYE

def close_cam(k):
    """from the eye view to a close look over the warm ocean (k 0..1)"""
    sub = np.array([1.0, 0.0, 0.0])
    d1 = nrm(nrm(CAM_EYE) * 0.45 + sub * 0.55)
    pos = slerp(nrm(CAM_EYE), d1, k) * (np.linalg.norm(CAM_EYE) + (2.55 - np.linalg.norm(CAM_EYE)) * k)
    f = slerp(F_EYE, nrm(sub * 0.92 + np.array([0, 0.05, -0.12]) - pos), k)
    up = slerp(U_EYE, nrm(U_EYE - f * (U_EYE @ f)), k)
    return pos, nrm(f), nrm(up)

EARTH = (12.05, 14.95)

def frame(t):
    if EARTH[0] <= t < EARTH[1]:
        import earth
        return earth.frame((t - EARTH[0]) / (EARTH[1] - EARTH[0])).convert('RGBA')
    s = next(k for k, (a, b) in SH.items() if a <= t < b) if t < DUR else 'final'
    a, b = SH[s]
    u = (t - a) / (b - a)
    nbe = eye_neighbours()
    if s == 'hook':
        # the first frame: a ring of light round the night side, the star hidden; it rises from behind the limb
        k = ramp(t, 0.0, b) ** 1.45
        pos, f, up = rise_cam(k)
        return view(pos, f, up, nb=nb_at(0, nbe['f'], nbe['g'])).convert('RGBA')
    if s == 'reveal':
        p0, f0, u0 = rise_cam(1.0)
        p1, f1, u1 = eye_wide()
        x = ramp(t, a, a + 12.5); k = 1 - (1 - x) ** 2
        pos = slerp(p0, p1, k) * (np.linalg.norm(p0) + (np.linalg.norm(p1) - np.linalg.norm(p0)) * k)
        f = slerp(f0, f1, k); up = slerp(u0, u1, k)
        return view(pos, f, up, nb=nb_at(0, nbe['f'], nbe['g'])).convert('RGBA')
    if s == 'star': return shot_star(t).convert('RGBA')
    if s == 'year': return shot_year(t).convert('RGBA')
    if s == 'system': return shot_system(t).convert('RGBA')
    if s == 'lock':
        sw = ease2(u)
        ang = math.radians(-8 + 30 * sw)                      # from a little day-side to a little night-side
        pos = np.array([math.sin(ang), -math.cos(ang), 0.16]) * 7.4
        f = nrm(-pos + np.array([0, 0, -0.35])); up = np.array([0, 0, 1.0])
        pic = view(pos, f, up).convert('RGBA')
        k1 = ease(ramp(t, ph(14)[0] - 0.2, ph(14)[0] + 0.4)) * (1 - ease(ramp(t, b - 0.4, b)))
        k2 = ease(ramp(t, ph(16)[0] - 0.2, ph(16)[0] + 0.4)) * (1 - ease(ramp(t, b - 0.4, b)))
        cx, cy = R.project(pos, pos + f, 34.0, [0, 0, 0], up)
        label(pic, (cx - 150, cy - 290), 'вічний день', 22, k1, fill=(255, 214, 160))
        label(pic, (cx + 150, cy - 290), 'вічна ніч', 22, k2, fill=(170, 190, 235))
        return pic
    if s == 'sky':
        # from the night side, straight up: TRAPPIST-1f near opposition, full, as big as our Moon; time-lapse ~40 min
        hours = 0.60 + 0.38 * u
        days = hours / 24
        pos = np.array([-1.02, 0.0, 0.0])
        f = np.array([-1.0, 0.0, 0.0]); up = np.array([0, 0, 1.0])
        rot = 2 * math.pi * days / 6.0996
        nb = R.neighbours(days, {'f': 0.6, 'g': 40.0}, names=('f',))
        pic = view(pos, f, up, fovy=6.0, nb=nb, planet_on=False, star=False, sky_turn=-rot, star_gain=1.6, photo_gain=0.0).convert('RGBA')
        # our Moon for scale, a dashed ring of 0.52°
        fx, fy = R.project(pos, pos + f, 6.0, nb[0][:3], up)
        rpx = math.tan(math.radians(0.26)) / math.tan(math.radians(3.0)) * H / 2
        mx, my = W * 0.5, H * 0.30
        k = ease(ramp(t, ph(20)[0] + 1.6, ph(20)[0] + 2.4))
        d = ImageDraw.Draw(pic)
        for q in range(36):
            if q % 2: continue
            a0 = q / 36 * 360
            d.arc((mx - rpx, my - rpx, mx + rpx, my + rpx), a0, a0 + 10, fill=(230, 230, 240, int(220 * k)), width=2)
        label(pic, (mx, my + rpx + 26), 'наш Місяць — для порівняння', 15, k, wght=400, file='Commissioner.ttf')
        label(pic, (fx, fy - math.tan(math.radians(0.3)) / math.tan(math.radians(3.0)) * H / 2 - 28), 'TRAPPIST-1f', 17, ease(ramp(t, a + 0.3, a + 1.0)))
        return pic
    if s == 'eye':
        pos, f, up = eye_wide(push=ease2(u))
        return view(pos, f, up, nb=nb_at(0, nbe['f'], nbe['g'])).convert('RGBA')
    if s in ('life', 'dark'):
        al, bl_ = SH['life'][0], SH['dark'][1]
        k = ease2(ramp(t, al - 0.3, al + 2.6))
        pos, f, up = close_cam(k)
        drift = (t - al) / (bl_ - al)
        pos = pos * (1 - 0.06 * drift)
        vk = ease(ramp(t, ph(28)[0] + 0.6, ph(28)[0] + 2.2))
        kd = ease(ramp(t, ph(30)[0] - 0.9, ph(30)[0] + 0.7))
        green, dark = np.array([0.05, 0.20, 0.04]), np.array([0.012, 0.010, 0.016])
        vc = green * (1 - kd) + dark * kd
        pic = view(pos, f, up, vk=vk, vegcol=tuple(vc), nb=nb_at(0, nbe['f'], nbe['g'])).convert('RGBA')
        label(pic, (W / 2, 250), 'уява', 20, vk * (1 - kd) * 0.95, fill=(190, 240, 170))
        label(pic, (W / 2, 250), 'гіпотеза вчених', 20, kd * vk * 0.95, fill=(220, 214, 230))
        return pic
    if s == 'dream':
        k = ease2(ramp(t, a, b - 0.4))
        pa, fa, ua = close_cam(1.0); pa = pa * 0.94
        pb, fb, ub = eye_wide(0.0)
        pos = slerp(pa, pb, k) * (np.linalg.norm(pa) + (np.linalg.norm(pb) - np.linalg.norm(pa)) * k)
        f = slerp(fa, fb, k); up = slerp(ua, ub, k)
        vk = 1 - ease(ramp(t, ph(32)[0] + 0.1, ph(32)[0] + 1.9))
        return view(pos, f, up, vk=vk, vegcol=(0.012, 0.010, 0.016), nb=nb_at(0, nbe['f'], nbe['g'])).convert('RGBA')
    # final: back round to the crescent with the star, slowly
    p0, f0, u0 = eye_wide(0.0)
    p1, f1, u1 = hook_cam(push=0.3, swing=-0.2)
    k = ease2(ramp(t, a, b))
    pos = slerp(p0, p1, k) * (np.linalg.norm(p0) + (np.linalg.norm(p1) - np.linalg.norm(p0)) * k)
    return view(pos, slerp(f0, f1, k), slerp(u0, u1, k), nb=nb_at(0, nbe['f'], nbe['g'])).convert('RGBA')

def _job(i):
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return
    frame(i / 30).convert('RGB').save(p, quality=93)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'stills':
        os.makedirs('/tmp/claude-0/-home-user-Cloud/b5c5bcc1-0ba1-54c6-9bde-e14fb8831f2a/scratchpad/st', exist_ok=True)
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [frame(t).convert('RGB').resize((W // 2, H // 2)) for t in ts]
        sheet = Image.new('RGB', (W // 2 * len(ims), H // 2))
        for k, im in enumerate(ims): sheet.paste(im, (k * W // 2, 0))
        sheet.save('/tmp/claude-0/-home-user-Cloud/b5c5bcc1-0ba1-54c6-9bde-e14fb8831f2a/scratchpad/st/sheet.jpg', quality=90)
        print('sheet', ts)
    elif cmd == 'frames':
        from multiprocessing import Pool
        os.makedirs(OUT, exist_ok=True)
        n = int(DUR * 30)
        nw = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        part = int(sys.argv[3]) if len(sys.argv) > 3 else None
        todo = [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
        if part is not None: todo = todo[part::4]
        with Pool(nw) as p:
            for c, _ in enumerate(p.imap_unordered(_job, todo, chunksize=2)):
                if c % 100 == 0: print('frame', c, '/', len(todo), flush=True)
        print('done', n)
