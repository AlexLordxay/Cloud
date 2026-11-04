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
        for _ in range(10):                     # a few village houses: a wall and a gable roof
            c, w = rng.uniform(0, 360), rng.uniform(0.7, 1.3)
            d0 = np.abs(((azs - c) + 180) % 360 - 180) / w
            h = np.maximum(h, np.where(d0 < 1, 0.9 + 0.55 * (1 - d0), 0))
        self.hz_az, self.hz_h = azs, h

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

    def render(self, az, alt, vfov, t=0.0, meteors=(), twinkle=True):
        cam = self.camera(az, alt, vfov); f, r, u, fp = cam
        # --- the sky: a dawn gradient by each pixel's direction (computed on a coarse grid, upsampled)
        gw, gh = 108, 192
        xs = (np.arange(gw) + 0.5) / gw * W - W / 2; ys = H / 2 - (np.arange(gh) + 0.5) / gh * H
        X, Y = np.meshgrid(xs, ys)
        dirs = f[None, None, :] * fp + X[..., None] * r[None, None, :] + Y[..., None] * u[None, None, :]
        dirs /= np.linalg.norm(dirs, axis=-1, keepdims=True)
        palt = np.degrees(np.arcsin(np.clip(dirs[..., 1], -1, 1)))
        saz, salt, _ = self.pl['Sun']; sv = enu(saz, salt)
        cosS = np.clip(dirs @ sv, -1, 1); ang = np.degrees(np.arccos(cosS))
        hgt = np.clip(palt, 0, 90) / 90
        zen = np.array([0.012, 0.02, 0.06]); hor = np.array([0.05, 0.08, 0.16])
        sky = zen + (hor - zen) * (1 - hgt[..., None]) ** 3
        glow = np.exp(-ang / 38.0)[..., None] * np.exp(-np.clip(palt, 0, 90) / 14)[..., None]
        sky += glow * np.array([0.42, 0.22, 0.12]) * 0.55 + (glow ** 2.5) * np.array([0.5, 0.32, 0.12]) * 0.5
        sky = np.clip(sky, 0, 1)
        img = np.asarray(Image.fromarray((sky * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
        # how much the dawn washes out the stars (by pixel)
        wash = np.asarray(Image.fromarray((np.clip(glow[..., 0] * 1.6, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
        # --- stars
        px, py, z = self.project(self.svec, cam)
        ok = (z > 0.05) & (px > -4) & (px < W + 4) & (py > -4) & (py < H + 4) & (self.salt > 0)
        lay = np.zeros((H, W, 3), np.float32)
        mags = self.mag[ok]; cols = self.col[ok]; X0 = px[ok]; Y0 = py[ok]
        rng = np.random.default_rng(int(t * 30) + 11)
        for x0, y0, m, c in zip(X0, Y0, mags, cols):
            ix, iy = int(x0), int(y0)
            if not (0 <= ix < W and 0 <= iy < H): continue
            a = 10 ** (-0.4 * (m - 3.0)) * (1 - 0.8 * wash[iy, ix])
            if twinkle: a *= 0.88 + 0.24 * rng.random()
            a = min(a, 3.0); rad = 1 if m > 3.2 else 2
            y1, y2, x1, x2 = max(0, iy - rad), min(H, iy + rad + 1), max(0, ix - rad), min(W, ix + rad + 1)
            yy, xx = np.mgrid[y1:y2, x1:x2]; k = np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (0.6 + 0.5 * rad))
            lay[y1:y2, x1:x2] += (k * a * 0.9)[..., None] * c
        img = img + lay
        # --- meteors: [(t0, dur, az0, alt0, len_deg)] streaks moving away from the radiant
        rv = enu(*self.radiant)
        for (m0, dur, a0, h0, L) in meteors:
            k = (t - m0) / dur
            if not (0 <= k <= 1.15): continue
            p0 = enu(a0, h0); dirv = p0 - rv * (p0 @ rv); dirv /= np.linalg.norm(dirv)
            head = p0 + dirv * math.radians(L) * min(k, 1.0); tail = p0 + dirv * math.radians(L) * max(0, k - 0.45)
            hx, hy, hz = self.project(head[None, :], cam); tx, ty, tz = self.project(tail[None, :], cam)
            if hz[0] <= 0 or tz[0] <= 0: continue
            ml = Image.new('L', (W, H), 0); dm = ImageDraw.Draw(ml)
            br = 255 * (1 - max(0, k - 1) / 0.15) * min(1, k / 0.1)
            n = 24
            for i in range(n):
                u0 = i / n; u1 = (i + 1) / n
                xa, ya = tx[0] + (hx[0] - tx[0]) * u0, ty[0] + (hy[0] - ty[0]) * u0
                xb, yb = tx[0] + (hx[0] - tx[0]) * u1, ty[0] + (hy[0] - ty[0]) * u1
                dm.line([(xa, ya), (xb, yb)], fill=int(br * u1 ** 1.5), width=3)
            mlf = np.asarray(ml.filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32) / 255
            img += mlf[..., None] * np.array([0.95, 0.98, 1.0]) * 2.2
        # --- planets: bright points with a soft glow (Venus the brightest), drawn over the stars
        glowL = np.zeros((H, W, 3), np.float32)
        PCOL = {'Mercury': (1.0, 0.92, 0.82), 'Venus': (1.0, 0.98, 0.92), 'Mars': (1.0, 0.62, 0.42), 'Jupiter': (1.0, 0.95, 0.85)}
        self.screen = {}
        for n, (paz, palt_, pm) in self.pl.items():
            if n == 'Sun': continue
            x, y, zz = self.project(enu(paz, palt_)[None, :], cam)
            if zz[0] <= 0: continue
            x, y = float(x[0]), float(y[0]); self.screen[n] = (x, y)
            if not (-60 < x < W + 60 and -60 < y < H + 60): continue
            a = 10 ** (-0.4 * (pm + 1.5)); core = 2.0 + 1.6 * min(3, a)
            R0 = 150
            y1, y2, x1, x2 = max(0, int(y - R0)), min(H, int(y + R0 + 1)), max(0, int(x - R0)), min(W, int(x + R0 + 1))
            if y2 <= y1 or x2 <= x1: continue
            yy, xx = np.mgrid[y1:y2, x1:x2]; d2 = (xx - x) ** 2 + (yy - y) ** 2
            c = np.array(PCOL[n])
            glowL[y1:y2, x1:x2] += (np.exp(-d2 / (core ** 2)) * 3.0 + np.exp(-d2 / ((core * 4) ** 2)) * 0.3 * min(2.5, a) + np.exp(-d2 / ((core * 9) ** 2)) * 0.06 * min(2.5, a))[..., None] * c
        img = img + glowL
        # --- the ground: below the silhouette, dark, a faint dawn tint on the side of the Sun
        img = np.clip(img, 0, None)
        out = (1 - np.exp(-img * 1.25)) / (1 - math.exp(-1.25))        # soft shoulder
        out = np.clip(out, 0, 1)
        im = Image.fromarray((out * 255).astype(np.uint8))
        # silhouette polygon: for each screen column, find the horizon height in pixels (sample along az)
        dr = ImageDraw.Draw(im)
        cols = np.arange(0, W + 1, 6)
        pts = []
        for cx in cols:
            # the direction of this column on the horizon plane: solve for az by stepping in the camera's horizontal
            v = f * fp + (cx - W / 2) * r; azc = (math.degrees(math.atan2(v[0], v[2])) + 360) % 360
            hh = float(np.interp(azc, self.hz_az, self.hz_h))
            vv = enu(azc, hh); x, y, zz = self.project(vv[None, :], cam)
            pts.append((cx, float(y[0]) if zz[0] > 0 else H + 10))
        poly = [(0, H + 2)] + pts + [(W, H + 2)]
        dr.polygon(poly, fill=(6, 7, 10))
        return im


if __name__ == '__main__':
    s = SkyUA()
    print({k: (round(v[0], 1), round(v[1], 1), round(v[2], 1)) for k, v in s.pl.items()}, 'radiant', [round(x, 1) for x in s.radiant])
    out = os.path.join(TOOLS, 'work', 'parade'); os.makedirs(out, exist_ok=True)
    for name, (az, alt, fov) in {'wide': (152, 30, 100), 'se': (128, 14, 50), 's': (186, 50, 40)}.items():
        s.render(az, alt, fov, 0.5, meteors=[(0.0, 0.8, 170, 40, 14)]).save(os.path.join(out, f'sky_{name}.jpg'), quality=92)
    print('ok')
