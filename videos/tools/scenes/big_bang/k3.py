# «Великий вибух» — К3 (0:08.2–0:19.7, 11,5 s; voice: «Тринадцять мільярдів вісімсот мільйонів років тому все, що ти
# бачиш у небі, за найпоширенішою теорією вміщалося в шматочок простору, менший за атом.»)
#   0–2,2 s  — a sharp pull-back: the glowing space of К1 (its last frame) shrinks into a tiny dazzling point;
#   3,8 s    — under the point, small: «усе, що ти бачиш у небі»;
#   7,8–10 s — the camera draws back a little more and a hydrogen atom emerges beside the point, dwarfing it: the
#              electron's 1s probability cloud, physically exact — a glow of the projected |psi|^2 (2R K1(2R)) and a
#              shimmer of sampled positions (each dot = where the electron could be found, r ~ Gamma(3, a0/2));
#   10,2 s   — «атом водню» and a thin scale bar «0,1 нм» (2 Bohr radii = 0,106 nm).
#   HUD: «13 800 000 000 років тому» from 0,3 s (the voice). (The real patch was ~1e-28 cm: the point is a symbol.)
#   python3 k3.py --still 10.8   -> test/k3_still_10.80.jpg
#   python3 k3.py                -> test/k3/f_####.jpg + test/k3.mp4
import json, math, os, sys, subprocess
import numpy as np
from scipy import ndimage, special
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'test')
W, H, FPS = 1920, 1080, 30
_TL = json.load(open(os.path.join(HERE, 'timeline.json'), encoding='utf-8'))
_S = next(s for s in _TL['shots'] if s['name'].startswith('К3 '))
DUR = round(_S['t1'] - _S['t0'], 2)
FONT = '/usr/share/fonts/opentype/inter/Inter-Light.otf'
FONT_HUD = '/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf'

PULL = 2.2                     # the pull-back
P_LABEL = 3.8                  # «усе, що ти бачиш у небі»
A_IN0, A_IN1 = 7.8, 10.0       # the atom emerges
A_LABEL = 10.2                 # «атом водню», «0,1 нм»
A0 = 78.0                      # px per Bohr radius at the end (the atom ~ 560 px across)
NDOT = 7000


def smooth(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * (3 - 2 * k)


def tonemap(a):
    x = (a * (2.51 * a + 0.03)) / (a * (2.43 * a + 0.59) + 0.14)
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def k1_last():
    # the last frame of К1 (rendered once and kept)
    src = os.path.join(OUT, 'k3_from_k1.jpg')
    if not os.path.exists(src):
        import k1
        rng = np.random.default_rng(1)
        Image.fromarray(k1.frame(k1.DUR - 1 / k1.FPS, k1.make_clumps(), rng)).save(src, quality=95)
    return (np.asarray(Image.open(src)).astype(np.float32) / 255) ** 2.2


# --------------------------------------------------------------------------------------------- the composition
def layout(t):
    # the camera draws back a little as the atom emerges: everything scales about the frame's centre, and drifts
    pull = 1.0 - 0.18 * smooth((t - A_IN0) / (A_IN1 + 1.0 - A_IN0))
    drift = 1.0 + 0.012 * t
    k = pull * drift
    cx, cy = W / 2, H / 2
    # the point: centre before the atom, then to the left; the atom to the right
    side = smooth((t - (A_IN0 - 0.4)) / 2.6)
    p = (cx + (-250.0 * side) * k + 6 * math.sin(0.4 * t), cy + 4 * math.sin(0.33 * t))
    a = (cx + 330.0 * k + 3 * math.sin(0.3 * t + 1), cy - 10 * k)
    return p, a, k


def glow_point(img, x, y, power, core=2.2):
    yy, xx = np.ogrid[0:H, 0:W]
    r2 = (xx - x) ** 2 + (yy - y) ** 2
    img += power * np.exp(-r2 / (2 * core * core))[..., None] * np.array([1.0, 0.93, 0.80])
    img += power * 0.020 * (1.0 / (1.0 + r2 / (14.0 ** 2)))[..., None] * np.array([1.0, 0.86, 0.64])
    img += power * 0.004 * (1.0 / (1.0 + r2 / (90.0 ** 2)))[..., None] * np.array([1.0, 0.80, 0.55])


class Atom:
    def __init__(self, rng):
        self.rng = rng
        self.pos = self.sample(NDOT)

    def sample(self, n):
        r = self.rng.gamma(3.0, 0.5, n)                 # P(r) ~ r^2 exp(-2r/a0), r in a0
        v = self.rng.normal(0, 1, (n, 3)); v /= np.linalg.norm(v, axis=1)[:, None]
        return v * r[:, None]

    def step(self):
        # «measurements»: a part of the dots re-drawn every frame — the cloud shimmers but its shape is exact
        m = self.rng.uniform(0, 1, NDOT) < 0.12
        self.pos[m] = self.sample(int(m.sum()))

    def draw(self, img, cx, cy, scale, alpha, t):
        if alpha <= 0:
            return
        # the glow: |psi_1s|^2 projected along the line of sight: Sigma(R) ~ 2R K1(2R) (=1 at R=0)
        R0 = 5.5 * scale
        x0, x1 = int(max(cx - R0, 0)), int(min(cx + R0, W)); y0, y1 = int(max(cy - R0, 0)), int(min(cy + R0, H))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        R = np.hypot(xx - cx, yy - cy) / scale
        R = np.maximum(R, 1e-4)
        sig = 2 * R * special.k1(2 * R)
        img[y0:y1, x0:x1] += (alpha * 0.30 * sig)[..., None] * np.array([0.30, 0.58, 1.00])
        # the dots
        ang = 0.05 * t
        c, s = math.cos(ang), math.sin(ang)
        p = self.pos
        x = p[:, 0] * c + p[:, 2] * s; y = p[:, 1]
        px = (cx + x * scale).astype(int); py = (cy + y * scale).astype(int)
        ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        dots = np.zeros((H, W), np.float32)
        np.add.at(dots, (py[ok], px[ok]), 1.0)
        dots = ndimage.gaussian_filter(dots, 0.8)
        img += (alpha * 2.2 * dots)[..., None] * np.array([0.62, 0.84, 1.00])


def text_layer(t, p, a, k):
    lay = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(lay)
    # HUD: the time
    al = smooth((t - 0.3) / 0.8)
    if al > 0:
        f = ImageFont.truetype(FONT_HUD, 40)
        d.text((96, 70), '13 800 000 000 років тому', font=f, fill=int(225 * al))
    # the point's label
    al = smooth((t - P_LABEL) / 0.7)
    if al > 0:
        f = ImageFont.truetype(FONT, 30)
        s = 'усе, що ти бачиш у небі'
        w = d.textlength(s, font=f)
        d.text((p[0] - w / 2, p[1] + 46), s, font=f, fill=int(200 * al))
    # the atom's label and scale bar (2 a0 = 0,106 nm)
    al = smooth((t - A_LABEL) / 0.7)
    if al > 0:
        f = ImageFont.truetype(FONT, 30)
        sc = A0 * k
        s = 'атом водню'
        w = d.textlength(s, font=f)
        yb = a[1] + 3.9 * sc
        d.text((a[0] - w / 2, yb + 18), s, font=f, fill=int(200 * al))
        d.line([(a[0] - sc, yb), (a[0] + sc, yb)], fill=int(170 * al), width=2)
        for xx in (a[0] - sc, a[0] + sc):
            d.line([(xx, yb - 7), (xx, yb + 7)], fill=int(170 * al), width=2)
        f2 = ImageFont.truetype(FONT, 24)
        s2 = '0,1 нм'
        w2 = d.textlength(s2, font=f2)
        d.text((a[0] - w2 / 2, yb - 36), s2, font=f2, fill=int(160 * al))
    return np.asarray(lay).astype(np.float32) / 255


def frame(t, atom, K1img, rng):
    img = np.zeros((H, W, 3), np.float32)
    p, a, k = layout(t)
    if t < PULL + 0.6:
        # the pull-back: the K1 picture inside a disc that shrinks exponentially into the point
        q = smooth(t / PULL) if t < PULL else 1.0
        rad = math.exp(math.log(1.25 * math.hypot(W, H) / 2) * (1 - q) + math.log(2.5) * q)
        if rad > 2.6:
            zoom = rad / (math.hypot(W, H) / 2)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            u = (xx - p[0]) / zoom + W / 2; v = (yy - p[1]) / zoom + H / 2
            inside = np.hypot(xx - p[0], yy - p[1]) / rad
            mask = np.clip((1.0 - inside) / 0.18, 0, 1) ** 1.5
            samp = np.stack([ndimage.map_coordinates(K1img[..., c], [v.ravel(), u.ravel()], order=1, mode='reflect')
                             .reshape(H, W) for c in range(3)], -1)
            boost = (1.0 / max(zoom, 1e-3)) ** 0.55          # the light concentrates as it shrinks
            fade = 1.0 - smooth((t - (PULL - 0.5)) / 0.7)
            img += samp * mask[..., None] * min(boost, 18.0) * fade
    # the point (its glare grows as the space collapses into it, then settles and breathes)
    pw = 6.0 * smooth((t - (PULL - 0.6)) / 0.7) * (1.0 + 0.06 * math.sin(7.0 * t) + 0.04 * math.sin(11.3 * t))
    pw += 10.0 * math.exp(-((t - PULL) / 0.35) ** 2)        # the flash at the moment of collapse
    if pw > 0:
        glow_point(img, p[0], p[1], pw)
    # the atom
    atom.step()
    alpha = smooth((t - A_IN0) / (A_IN1 - A_IN0))
    atom.draw(img, a[0], a[1], A0 * k, alpha, t)
    # bloom, tone, text, grain, vignette
    b = np.clip(img - 0.5, 0, None)
    img = img + sum(wt * ndimage.gaussian_filter(b, (r, r, 0)) for r, wt in ((4, 0.30), (18, 0.25), (60, 0.20)))
    yy, xx = np.ogrid[0:H, 0:W]
    vig = 1 - 0.25 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
    out = tonemap(img * vig[..., None])
    txt = text_layer(t, p, a, k)
    out = out * (1 - txt[..., None]) + txt[..., None] * np.array([0.93, 0.95, 1.0])
    g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    out = out + np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None] * 0.010
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    os.makedirs(os.path.join(OUT, 'k3'), exist_ok=True)
    rng = np.random.default_rng(3)
    atom = Atom(np.random.default_rng(5))
    K1img = k1_last()
    if '--still' in sys.argv:
        t = float(sys.argv[sys.argv.index('--still') + 1])
        Image.fromarray(frame(t, atom, K1img, rng)).save(os.path.join(OUT, f'k3_still_{t:.2f}.jpg'), quality=93)
        return
    n = int(round(DUR * FPS))
    for i in range(n):
        dst = os.path.join(OUT, 'k3', f'f_{i:04d}.jpg')
        Image.fromarray(frame(i / FPS, atom, K1img, rng)).save(dst, quality=93)   # (the atom's shimmer is stateful)
        if i % 30 == 0: print(i, '/', n, flush=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(OUT, 'k3', 'f_%04d.jpg'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                    os.path.join(OUT, 'k3.mp4')], check=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
