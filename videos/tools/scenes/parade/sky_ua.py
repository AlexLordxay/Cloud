# Planet parade, 16 Nov 2026: the morning sky over Ukraine (Kyiv, 6:20 local = 04:20 UTC), drawn in 2D: the real stars
# to magnitude 6 (data/sky, coloured by B–V), the planets where astronomy-engine puts them (Mercury and Venus low in the
# south-east, Mars and Jupiter 1.2° apart high in the south), the dawn glow under the Sun (−9°, below the ESE horizon),
# a dark rural horizon, and Leonid meteors from their radiant in Leo. A view is a rectilinear camera (az, alt, vfov).
#
#   from sky_ua import SkyUA; s = SkyUA(); img = s.render(az, alt, vfov, t, meteors=[...])   -> PIL RGB 1080×1920
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import astronomy as A

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
W, H = 1080, 1920
D2R = math.pi / 180
LAT, LON = 50.45, 30.52
WHEN = A.Time.Make(2026, 11, 16, 4, 20, 0)
OBS = A.Observer(LAT, LON, 170)


def enu(az, alt):
    """unit vectors (x east, y up, z north) for azimuth/altitude in degrees (arrays ok)"""
    az, alt = np.radians(az), np.radians(alt)
    return np.stack([np.cos(alt) * np.sin(az), np.sin(alt), np.cos(alt) * np.cos(az)], -1)


def bv_rgb(bv):
    bv = np.clip(bv, -0.4, 2.0)
    r = np.clip(0.75 + 0.25 * (bv + 0.4) / 1.2, 0, 1)
    g = np.clip(0.82 + 0.1 * np.cos((bv - 0.5) * 1.6), 0, 1)
    b = np.clip(1.0 - 0.45 * np.clip(bv - 0.2, 0, None), 0, 1)
    return np.stack([r, g, b], -1)


class SkyUA:
    def __init__(self):
        d = json.load(open(os.path.join(TOOLS, 'data', 'sky', 'stars.6.json')))['features']
        ra = np.array([f['geometry']['coordinates'][0] for f in d]) % 360
        de = np.array([f['geometry']['coordinates'][1] for f in d])
        self.mag = np.array([f['properties']['mag'] for f in d])
        self.col = bv_rgb(np.array([float(f['properties'].get('bv') or 0.6) for f in d]))
        # equatorial → horizontal at WHEN (local sidereal time; precession ignored: a fraction of a degree)
        lst = (A.SiderealTime(WHEN) * 15 + LON) % 360
        ha = np.radians((lst - ra) % 360); dec = np.radians(de); lat = LAT * D2R
        alt = np.arcsin(np.sin(dec) * np.sin(lat) + np.cos(dec) * np.cos(lat) * np.cos(ha))
        az = np.arctan2(-np.sin(ha) * np.cos(dec), np.cos(lat) * np.sin(dec) - np.sin(lat) * np.cos(dec) * np.cos(ha))
        self.salt, self.saz = np.degrees(alt), np.degrees(az) % 360
        self.svec = enu(self.saz, self.salt)
        self.lst = lst
        # the planets and the Sun
        self.pl = {}
        for n in ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Sun']:
            b = getattr(A.Body, n); eq = A.Equator(b, WHEN, OBS, True, True)
            hz = A.Horizon(WHEN, OBS, eq.ra, eq.dec, A.Refraction.Normal)
            self.pl[n] = (hz.azimuth, hz.altitude, A.Illumination(b, WHEN).mag if n != 'Sun' else -26.7)
        # the Leonid radiant (RA 152°, Dec +22°)
        ha = math.radians((lst - 152) % 360); dec = math.radians(22)
        alt = math.asin(math.sin(dec) * math.sin(lat) + math.cos(dec) * math.cos(lat) * math.cos(ha))
        az = math.atan2(-math.sin(ha) * math.cos(dec), math.cos(lat) * math.sin(dec) - math.sin(lat) * math.cos(dec) * math.cos(ha))
        self.radiant = (math.degrees(az) % 360, math.degrees(alt))
        # a horizon silhouette: gentle fields, a tree line and a few village roofs (fixed, by azimuth)
        rng = np.random.default_rng(7); azs = np.arange(0, 360, 0.1)
        h = 0.45 + 0.22 * np.sin(np.radians(azs) * 3 + 1) + 0.15 * np.sin(np.radians(azs) * 7 + 2)
        trees = np.zeros_like(azs)
        for _ in range(900):                    # a tree line: many small overlapping crowns, in clumps
            c = rng.uniform(0, 360)
            if np.sin(np.radians(c) * 5 + 0.7) + 0.4 * np.sin(np.radians(c) * 13) < -0.2: continue    # gaps between the groves
            w, hh = rng.uniform(0.25, 0.8), rng.uniform(0.5, 1.5)
            d0 = np.abs(((azs - c) + 180) % 360 - 180) / w; trees = np.maximum(trees, hh * np.sqrt(np.clip(1 - d0 * d0, 0, 1)))
        h = h + trees
        trees2 = np.zeros_like(azs)
        for _ in range(2500):                   # the crowns' ragged edges: smaller bumps on top of the groves
            c = rng.uniform(0, 360); w, hh = rng.uniform(0.08, 0.25), rng.uniform(0.1, 0.45)
            d0 = np.abs(((azs - c) + 180) % 360 - 180) / w; trees2 = np.maximum(trees2, hh * np.sqrt(np.clip(1 - d0 * d0, 0, 1)))
        h = h + trees2 * (trees > 0.3)
        for _ in range(16):                     # poplars: tall and narrow
            c = rng.uniform(0, 360); d0 = np.abs(((azs - c) + 180) % 360 - 180) / 0.18
            h = np.maximum(h, np.where(d0 < 1, 0.6 + 2.6 * np.sqrt(np.clip(1 - d0 ** 2, 0, 1)) ** 0.6, 0))
        for _ in range(10):                     # a few village houses: a wall and a gable roof
            c, w = rng.uniform(0, 360), rng.uniform(0.7, 1.3)
            d0 = np.abs(((azs - c) + 180) % 360 - 180) / w
            h = np.maximum(h, np.where(d0 < 1, 0.9 + 0.55 * (1 - d0), 0))
            ch = c + w * 0.45; d1 = np.abs(((azs - ch) + 180) % 360 - 180) / 0.06    # a chimney
            h = np.maximum(h, np.where(d1 < 1, 1.65, 0))
        # a small church with a dome and a cross, on the south-east (under Venus — a picture-postcard spot)
        c = 141.0; d0 = np.abs(azs - c)
        h = np.maximum(h, np.where(d0 < 0.9, 1.5, 0))                                        # the body
        h = np.maximum(h, np.where(d0 < 0.45, 1.5 + 0.55 * np.sqrt(np.clip(1 - (d0 / 0.45) ** 2, 0, 1)), 0))   # the dome
        h = np.maximum(h, np.where(d0 < 0.03, 2.55, 0)); h = np.maximum(h, np.where((d0 < 0.12) & (d0 > 0.0), np.where(np.abs(d0) < 0.12, 0, 0), 0))
        self.hz_az, self.hz_h = azs, h * 1.35

    def camera(self, az, alt, vfov, roll=0.0):
        f = enu(az, alt); up0 = np.array([0, 1.0, 0])
        r = np.cross(up0, f); r /= np.linalg.norm(r); u = np.cross(f, r)
        if roll: c, s = math.cos(roll * D2R), math.sin(roll * D2R); r, u = c * r + s * u, -s * r + c * u
        fp = (H / 2) / math.tan(vfov / 2 * D2R)
        return f, r, u, fp

    def project(self, v, cam):
        f, r, u, fp = cam
        z = v @ f; x = v @ r; y = v @ u
        with np.errstate(divide='ignore', invalid='ignore'):
            px = W / 2 + x / z * fp * -1 * -1; py = H / 2 - y / z * fp
        return px, py, z

    def render(self, az, alt, vfov, t=0.0, meteors=(), twinkle=True, sky_boost=0.0):
        """meteors: [(t0, dur, az0, alt0, len_deg, kind)] — kind 'n' (normal) or 'f' (fireball: a flare and a long train)"""
        cam = self.camera(az, alt, vfov); f, r, u, fp = cam
        # ---------------- the sky: twilight with the Sun 8° below the ESE horizon ----------------
        gw, gh = 135, 240
        xs = (np.arange(gw) + 0.5) / gw * W - W / 2; ys = H / 2 - (np.arange(gh) + 0.5) / gh * H
        X, Y = np.meshgrid(xs, ys)
        dirs = f[None, None, :] * fp + X[..., None] * r[None, None, :] + Y[..., None] * u[None, None, :]
        dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
        h = np.degrees(np.arcsin(np.clip(dirs[..., 1], -1, 1)))
        paz = (np.degrees(np.arctan2(dirs[..., 0], dirs[..., 2])) + 360) % 360
        saz = self.pl['Sun'][0]
        daz = np.abs(((paz - saz) + 180) % 360 - 180)
        hp = np.clip(h, 0, 90)
        gsun = np.exp(-(daz / 58.0) ** 2)                      # how much this direction is on the Sun's side
        lin = lambda c: np.array(c) ** 2.2
        zen, hor = lin([0.06, 0.09, 0.19]), lin([0.2, 0.27, 0.42])
        base = zen + (hor - zen) * np.exp(-hp / 22.0)[..., None]
        band = np.exp(-hp / 3.2)[..., None] * gsun[..., None] * lin([0.98, 0.52, 0.24]) * 1.05            # the orange rim
        cream = np.exp(-hp / 9.0)[..., None] * gsun[..., None] ** 0.8 * lin([0.92, 0.74, 0.46]) * 0.75     # the creamy glow above it
        teal = np.exp(-hp / 24.0)[..., None] * gsun[..., None] ** 0.6 * lin([0.42, 0.62, 0.7]) * 0.32      # the pale band higher up
        shadow = (1 - gsun)[..., None] * np.exp(-hp / 6.0)[..., None] * lin([0.16, 0.16, 0.3]) * 0.6        # the Earth's shadow, opposite
        haze = np.exp(-hp / 1.2)[..., None] * (0.35 + 0.65 * gsun[..., None]) * lin([0.55, 0.5, 0.48]) * 0.35  # haze on the horizon
        towns = np.zeros_like(h)
        for taz, k in ((206, 0.5), (252, 0.3), (318, 0.35), (35, 0.25)):                                   # far towns' light domes
            towns += k * np.exp(-((((paz - taz) + 180) % 360 - 180) / 9.0) ** 2) * np.exp(-hp / 3.0)
        sky = base * (1 - 0.35 * (1 - gsun[..., None]) * np.exp(-hp / 6.0)[..., None]) + band + cream + teal + shadow + haze
        sky += towns[..., None] * lin([0.55, 0.36, 0.2]) * 0.35
        sky *= 1 + sky_boost
        img = np.asarray(Image.fromarray(np.clip(sky * 255 * 1.0, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
        lum = img.mean(-1)
        # ---------------- stars: dimmed by the twilight and by the air near the horizon ----------------
        px, py, z = self.project(self.svec, cam)
        ok = (z > 0.05) & (px > -4) & (px < W + 4) & (py > -4) & (py < H + 4) & (self.salt > 1.0)
        lay = np.zeros((H, W, 3), np.float32)
        rng = np.random.default_rng(int(t * 30) + 11)
        airm = 1 / np.sin(np.radians(np.clip(self.salt, 1, 90)))
        for x0, y0, m, c, X0 in zip(px[ok], py[ok], self.mag[ok], self.col[ok], airm[ok]):
            ix, iy = int(x0), int(y0)
            if not (0 <= ix < W and 0 <= iy < H): continue
            m_eff = m + 0.28 * (X0 - 1)                                   # extinction
            vis = np.clip((0.33 - lum[iy, ix]) / 0.28, 0, 1)            # the brighter the sky there, the fewer stars show
            a = 10 ** (-0.4 * (m_eff - 3.0)) * vis
            if a < 0.02: continue
            if twinkle: a *= 1 + (0.12 + 0.25 * min(1, (X0 - 1) / 4)) * (rng.random() - 0.5) * 2
            a = min(a, 2.2); rad = 1 if m_eff > 2.5 else 2
            y1, y2, x1, x2 = max(0, iy - rad), min(H, iy + rad + 1), max(0, ix - rad), min(W, ix + rad + 1)
            yy, xx = np.mgrid[y1:y2, x1:x2]; k = np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (0.55 + 0.45 * rad))
            cc = c * np.array([1.0, 1.0 - 0.06 * min(1, X0 / 5), 1.0 - 0.15 * min(1, X0 / 5)])     # reddened low down
            lay[y1:y2, x1:x2] += (k * a * 0.85)[..., None] * cc
        img = img + lay
        # ---------------- meteors ----------------
        rv = enu(*self.radiant)
        flash = 0.0
        for mt in meteors:
            m0, dur, a0, h0, L = mt[:5]; kind = mt[5] if len(mt) > 5 else 'n'
            k = (t - m0) / dur
            train_life = 2.6 if kind == 'f' else 1.1
            if k < 0 or (t - m0 - dur) > train_life: continue
            p0 = enu(a0, h0); dv = p0 - rv * (p0 @ rv); dv /= np.linalg.norm(dv)
            pts = lambda q: p0 + dv * math.radians(L) * q          # q: 0..1 along the path (spherical drift is negligible)
            kk = min(k, 1.0)
            n = 60
            qs = np.linspace(max(0, kk - (0.55 if kind == 'f' else 0.4)), kk, n)
            P = np.stack([pts(q) for q in qs]); sx, sy, sz = self.project(P, cam)
            if (sz <= 0).any(): continue
            layer = Image.new('L', (W, H), 0); dl = ImageDraw.Draw(layer)
            core = Image.new('L', (W, H), 0); dc = ImageDraw.Draw(core)
            alive = k <= 1.0
            if alive:
                for i in range(n - 1):
                    w = (i + 1) / n
                    dl.line([(sx[i], sy[i]), (sx[i + 1], sy[i + 1])], fill=int(255 * w ** 1.6), width=int(2 + 5 * w * (1.6 if kind == 'f' else 1)))
                    dc.line([(sx[i], sy[i]), (sx[i + 1], sy[i + 1])], fill=int(255 * w ** 2.2), width=max(1, int(1 + 2 * w)))
            # the persistent train: the whole path so far, glowing faintly green and fading after the meteor is gone
            q1 = kk; Q = np.linspace(0, q1, 50); P2 = np.stack([pts(q) for q in Q]); tx, ty, tz = self.project(P2, cam)
            age = max(0.0, t - m0 - dur * 0.6)
            tr_a = (1 - min(1, age / train_life)) ** 1.5 * (0.5 if kind == 'f' else 0.22)
            trl = Image.new('L', (W, H), 0); dt = ImageDraw.Draw(trl)
            for i in range(49): dt.line([(tx[i], ty[i]), (tx[i + 1], ty[i + 1])], fill=int(255 * tr_a * (0.3 + 0.7 * i / 49)), width=int(3 + 6 * min(1, age / train_life)))
            L1 = np.asarray(layer.filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32) / 255
            L2 = np.asarray(core.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
            L3 = np.asarray(trl.filter(ImageFilter.GaussianBlur(3.0 + 4 * min(1, age / train_life)))).astype(np.float32) / 255
            bright = 1.6 if kind == 'f' else 1.0
            img += L1[..., None] * np.array([0.55, 0.95, 0.7]) * 0.9 * bright + L2[..., None] * np.array([1.0, 1.0, 0.95]) * 1.6 * bright
            img += L3[..., None] * np.array([0.35, 0.85, 0.55]) * 0.8
            if alive:                                   # the head: a bright point, flaring for a fireball
                hx, hy = sx[-1], sy[-1]; fl = 1 + (2.5 * math.sin(math.pi * min(1, max(0, (k - 0.55) / 0.4))) if kind == 'f' else 0)
                R0 = 30; y1, y2, x1, x2 = max(0, int(hy - R0)), min(H, int(hy + R0)), max(0, int(hx - R0)), min(W, int(hx + R0))
                if y2 > y1 and x2 > x1:
                    yy, xx = np.mgrid[y1:y2, x1:x2]; d2 = (xx - hx) ** 2 + (yy - hy) ** 2
                    img[y1:y2, x1:x2] += (np.exp(-d2 / 6.0) * 1.6 * fl + np.exp(-d2 / 90.0) * 0.35 * fl)[..., None] * np.array([0.8, 1.0, 0.85])
                if kind == 'f': flash = max(flash, 0.06 * math.sin(math.pi * min(1, max(0, (k - 0.5) / 0.5))))
        if flash > 0: img += flash * np.array([0.6, 0.75, 0.7])
        # ---------------- planets: steady points, a modest glow (no glare), dimmed and yellowed low down ----------------
        PCOL = {'Mercury': (1.0, 0.9, 0.76), 'Venus': (1.0, 0.97, 0.9), 'Mars': (1.0, 0.66, 0.46), 'Jupiter': (1.0, 0.95, 0.86)}
        self.screen = {}
        for n, (paz_, palt_, pm) in self.pl.items():
            if n == 'Sun': continue
            x, y, zz = self.project(enu(paz_, palt_)[None, :], cam)
            if zz[0] <= 0: continue
            x, y = float(x[0]), float(y[0]); self.screen[n] = (x, y)
            if not (-40 < x < W + 40 and -40 < y < H + 40): continue
            X0 = 1 / math.sin(math.radians(max(1, palt_)))
            m_eff = pm + 0.28 * (X0 - 1)
            a = 10 ** (-0.4 * (m_eff + 1.0))                  # Venus ≈ 6, Jupiter ≈ 2.8, Mars ≈ 0.5, Mercury ≈ 1
            core = 1.3 + 0.55 * math.log1p(a)
            c = np.array(PCOL[n]) * np.array([1.0, 1 - 0.05 * min(1, X0 / 6), 1 - 0.14 * min(1, X0 / 6)])
            R0 = 60; y1, y2, x1, x2 = max(0, int(y - R0)), min(H, int(y + R0 + 1)), max(0, int(x - R0)), min(W, int(x + R0 + 1))
            if y2 <= y1 or x2 <= x1: continue
            yy, xx = np.mgrid[y1:y2, x1:x2]; d2 = (xx - x) ** 2 + (yy - y) ** 2
            prof = np.exp(-d2 / (core ** 2)) * 1.7 + np.exp(-d2 / ((core * 3.2) ** 2)) * 0.16 * min(2.0, a) + np.exp(-d2 / ((core * 9) ** 2)) * 0.035 * min(2.0, a)
            img[y1:y2, x1:x2] += prof[..., None] * c
        img = np.clip(img, 0, None)
        out = (1 - np.exp(-img * 1.35)) / (1 - math.exp(-1.35))
        out = np.clip(out, 0, 1) ** (1 / 1.0)
        im = Image.fromarray((out * 255).astype(np.uint8)).convert('RGBA')
        # ---------------- the land: a supersampled silhouette, darkest at the bottom ----------------
        S = 2; mask = Image.new('L', (W * S, H * S), 0); dm = ImageDraw.Draw(mask)
        pts = []
        for cx in np.arange(0, W + 1, 2):
            v = f * fp + (cx - W / 2) * r; azc = (math.degrees(math.atan2(v[0], v[2])) + 360) % 360
            hh = float(np.interp(azc, self.hz_az, self.hz_h))
            vv = enu(azc, hh); x, y, zz = self.project(vv[None, :], cam)
            pts.append((cx * S, (float(y[0]) if zz[0] > 0 else H + 10) * S))
        dm.polygon([(0, H * S + 4)] + pts + [(W * S, H * S + 4)], fill=255)
        mask = mask.resize((W, H), Image.LANCZOS)
        ground = np.zeros((H, W, 3), np.float32)
        gy = np.linspace(0, 1, H)[:, None]
        ground[:] = (np.array([0.035, 0.038, 0.05]) * (1 - gy) + np.array([0.012, 0.012, 0.016]) * gy)[:, None, :] if False else 0
        # the land: a touch of the twilight near the horizon (on the Sun's side), fading to black at the bottom
        ys_h = min(p[1] for p in pts) / S
        gy = np.clip((np.arange(H) - ys_h) / 420.0, 0, 1)[:, None]
        warm = np.array([26, 20, 22], np.float32); dark = np.array([5, 5, 8], np.float32)
        gcol = (warm * (1 - gy) ** 2 + dark * (1 - (1 - gy) ** 2))[:, None, :] * np.ones((1, W, 1), np.float32)
        ground_im = Image.fromarray(gcol.astype(np.uint8)).convert('RGBA'); ground_im.putalpha(mask)
        im.alpha_composite(ground_im)
        return im.convert('RGB')


if __name__ == '__main__':
    s = SkyUA()
    print({k: (round(v[0], 1), round(v[1], 1), round(v[2], 1)) for k, v in s.pl.items()}, 'radiant', [round(x, 1) for x in s.radiant])
    out = os.path.join(TOOLS, 'work', 'parade'); os.makedirs(out, exist_ok=True)
    for name, (az, alt, fov) in {'wide': (152, 30, 100), 'se': (128, 14, 50), 's': (186, 50, 40)}.items():
        s.render(az, alt, fov, 0.5, meteors=[(0.0, 0.8, 170, 40, 14)]).save(os.path.join(out, f'sky_{name}.jpg'), quality=92)
    print('ok')
