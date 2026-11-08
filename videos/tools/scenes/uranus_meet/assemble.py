# «Знайомся: Уран» — lays the shots end to end on the voice's timeline (timeline.json): short dissolves between them,
# the flight under the ring whiting out into the clouds, and frost growing over the lens at «−224» (ice crystals from
# the edges inwards: a Voronoi net of cracks, feathery grain, the picture blurred under the ice).
#   python3 assemble.py [workers]    -> work/uranus_meet/frames/f_%05d.jpg (for compose.py)
import json, os, sys, math
import numpy as np
from multiprocessing import Pool
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'uranus_meet')
OUT = os.path.join(WORK, 'frames')
W, H, FPS = 720, 1280, 30
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
ORDER = TL['order']
DIP = {'mystery': 14, 'voyager': 12}       # through black: out of the bright clouds into space; off the cliff's floor
XF = {'scale': 10, 'herschel': 8, 'orbit': 8, 'ringdive': 8, 'under': 0, 'clouds': 0, 'mystery': 0, 'moons': 8,
      'mirphoto': 8, 'rockfall': 6, 'voyager': 0, 'skynow': 10, 'final': 10}

def shot_frame(name, i):
    d = os.path.join(WORK, 'shots', name)
    ext = '.png' if name == 'clouds' else '.jpg'
    n = len([f for f in os.listdir(d) if f.endswith(ext)])
    i = max(0, min(n - 1, i))
    return Image.open(os.path.join(d, f'f_{i:05d}{ext}')).convert('RGB')

_frost = {}
def frost_maps():
    if not _frost:
        from scipy.spatial import cKDTree
        from scipy.ndimage import gaussian_filter
        r = np.random.default_rng(17)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        pts = np.stack([xx.ravel(), yy.ravel()], 1)
        lines = np.zeros((H, W), np.float32)
        for n, w, a in ((140, 1.6, 1.0), (700, 1.0, 0.45)):
            P = np.stack([r.uniform(0, W, n), r.uniform(0, H, n)], 1)
            d, _ = cKDTree(P).query(pts, k=2)
            e = (d[:, 1] - d[:, 0]).reshape(H, W)
            lines += a * np.exp(-e / w)
        grain = gaussian_filter(r.normal(0, 1, (H, W)).astype(np.float32), 1.2)
        feather = gaussian_filter(r.normal(0, 1, (H, W)).astype(np.float32), (0.8, 6.0))   # streaky crystals
        noise = gaussian_filter(r.normal(0, 1, (H, W)).astype(np.float32), 40); noise /= noise.std()
        edge = np.minimum(np.minimum(xx, W - xx) / W, np.minimum(yy, H - yy) / W)          # 0 at the frame's edge
        _frost.update(lines=np.clip(lines, 0, 1.5), grain=grain, feather=feather, grow=edge * 2.0 + 0.10 * noise)
    return _frost

def frost(img, k):
    """k 0..1: how far the frost has grown in from the edges"""
    if k <= 0: return img
    F = frost_maps()
    m = np.clip((k * 0.85 - F['grow']) / 0.08, 0, 1)[..., None]
    a = np.asarray(img, np.float32)
    b = np.asarray(img.filter(ImageFilter.GaussianBlur(7)), np.float32)
    ice = np.clip(0.30 * F['lines'] + 0.38 * np.abs(F['feather']) ** 1.5 + 0.08 * F['grain'], 0, 1.2)[..., None]
    out = a * (1 - 0.45 * m) + b * 0.45 * m
    out = out + m * (ice * np.array([200.0, 228.0, 245.0]) * 0.6 + 10.0)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

def frame(g):
    t = g / FPS
    k = 0
    while k + 1 < len(ORDER) and t >= ORDER[k + 1]['t0']: k += 1
    s = ORDER[k]; name = s['name']
    i = g - int(round(s['t0'] * FPS))
    img = shot_frame(name, i)
    if name == 'clouds':
        lt = i / FPS
        if lt < 0.6:                                    # out of the white of the Sun under the ring
            img = Image.blend(Image.new('RGB', (W, H), (235, 250, 255)), img, min(1.0, lt / 0.6) ** 0.8)
        t14 = TL['phrases'][14]['t0'] - s['t0']         # «Тут найхолодніше…»
        kf = (lt - (t14 - 0.3)) / (s['t1'] - s['t0'] - t14 + 0.3)
        if kf > 0: img = frost(img, 0.72 * min(1.0, kf) ** 0.8)
    # dips to black: the end of the shot before, and the start of this one
    n0 = DIP.get(name, 0)
    if n0 and i < n0:
        img = Image.eval(img, lambda v, a=(i + 1) / (n0 + 1): int(v * a ** 1.3))
    if k + 1 < len(ORDER):
        nx = ORDER[k + 1]; n1 = DIP.get(nx['name'], 0)
        left = int(round(nx['t0'] * FPS)) - g
        if n1 and left <= n1:
            img = Image.eval(img, lambda v, a=(left - 0.5) / (n1 + 0.5): int(v * max(0.0, a) ** 1.3))
    xf = XF.get(name, 0)
    if k > 0 and xf and i < xf:
        p = ORDER[k - 1]
        pi = g - int(round(p['t0'] * FPS))
        prev = shot_frame(p['name'], pi)
        img = Image.blend(prev, img, (i + 1) / (xf + 1))
    return img

def job(g):
    p = os.path.join(OUT, f'f_{g:05d}.jpg')
    frame(g).save(p, quality=94)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    n = int(round(TL['dur'] * FPS))
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    with Pool(nw) as pool: pool.map(job, range(n), chunksize=16)
    print('assembled', n, 'frames')
