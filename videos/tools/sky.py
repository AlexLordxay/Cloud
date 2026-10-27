# The real night sky in 2D, for the zodiac videos: stars to magnitude 6 (coloured by B–V), the Milky Way, constellation
# figures and IAU borders (data/sky, d3-celestial), the ecliptic and the Sun on it. A view is an azimuthal equidistant
# projection round any point of the sky, seen from inside (east to the left), so a camera can glide from the whole
# zodiac (centred on the ecliptic pole: the zodiac is a ring) down to one constellation.
#
#   from sky import Sky; s = Sky(); img = s.render(view)       # view: see Sky.render
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TOOLS = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(TOOLS, 'data', 'sky')
EPS = math.radians(23.4393)
D2R = math.pi / 180

# The 13 constellations the Sun crosses, in order along the ecliptic, with their Ukrainian names
ZODIAC = [('Psc', 'Риби'), ('Ari', 'Овен'), ('Tau', 'Телець'), ('Gem', 'Близнята'), ('Cnc', 'Рак'), ('Leo', 'Лев'),
          ('Vir', 'Діва'), ('Lib', 'Терези'), ('Sco', 'Скорпіон'), ('Oph', 'Змієносець'), ('Sgr', 'Стрілець'),
          ('Cap', 'Козеріг'), ('Aqr', 'Водолій')]
UA = dict(ZODIAC)


def vec(ra, dec):
    ra, dec = ra * D2R, dec * D2R
    return np.array([math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)])


def ecl(lam, beta=0.0):
    """ecliptic longitude/latitude (deg) -> equatorial unit vector"""
    l, b = lam * D2R, beta * D2R
    x, y, z = math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b)
    return np.array([x, y * math.cos(EPS) - z * math.sin(EPS), y * math.sin(EPS) + z * math.cos(EPS)])


def radec(v):
    return math.degrees(math.atan2(v[1], v[0])) % 360, math.degrees(math.asin(max(-1, min(1, v[2]))))


ECL_POLE = ecl(0, 90)


def slerp(a, b, k):
    d = max(-1.0, min(1.0, float(a @ b))); w = math.acos(d)
    if w < 1e-6: return a.copy()
    return (math.sin((1 - k) * w) * a + math.sin(k * w) * b) / math.sin(w)


def bv_rgb(bv):
    """B–V colour index -> a gentle star colour"""
    bv = max(-0.4, min(2.0, bv))
    t = (bv + 0.4) / 2.4
    stops = [(0.0, (155, 176, 255)), (0.25, (202, 216, 255)), (0.4, (248, 247, 255)), (0.55, (255, 244, 234)),
             (0.7, (255, 210, 161)), (1.0, (255, 160, 100))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(int(c0[i] + (c1[i] - c0[i]) * k) for i in range(3))
    return stops[-1][1]


class Sky:
    def __init__(self, W=1080, H=1920, ss=2):
        self.W, self.H, self.ss = W, H, ss
        L = lambda f: json.load(open(os.path.join(DATA, f)))
        st = L('stars.6.json')['features']
        self.star_v = np.array([vec(*f['geometry']['coordinates']) for f in st])
        self.star_mag = np.array([f['properties']['mag'] for f in st])
        self.star_col = np.array([bv_rgb(float(f['properties'].get('bv') or 0.6)) for f in st], float)
        rng = np.random.default_rng(7)
        self._faint_n = 60000
        self.lines = {f['id']: [[vec(*p) for p in seg] for seg in f['geometry']['coordinates']] for f in L('constellations.lines.json')['features']}
        self.label = {f['id']: vec(*f['geometry']['coordinates']) for f in L('constellations.json')['features']}
        self.borders = {}
        for f in L('constellations.borders.json')['features']:
            for cid in f['ids'].split(','):
                self.borders.setdefault(cid, []).extend([[vec(*p) for p in seg] for seg in f['geometry']['coordinates']])
        # the Milky Way as a soft RA/Dec brightness map (RA 0..360 across, Dec +90..-90 down), from galactic latitude:
        # a band brightest towards the centre (Sagittarius), mottled, with the dark Great Rift along its middle
        MW, MH = 2048, 1024
        ra = (np.arange(MW) + 0.5) / MW * 360; dec = 90 - (np.arange(MH) + 0.5) / MH * 180
        RA, DE = np.meshgrid(np.radians(ra), np.radians(dec))
        V = np.stack([np.cos(DE) * np.cos(RA), np.cos(DE) * np.sin(RA), np.sin(DE)], -1)
        ngp, gc = vec(192.8595, 27.1283), vec(266.4050, -28.9362)
        gy = np.cross(ngp, gc)
        bgal = np.degrees(np.arcsin(np.clip(V @ ngp, -1, 1)))
        lgal = np.degrees(np.arctan2(V @ gy, V @ gc))                    # -180..180, 0 at the centre
        noise = np.zeros((MH, MW), np.float32)
        for sc_, amp in ((48, 0.5), (16, 0.3), (6, 0.2)):
            nz = Image.fromarray((rng.random((MH // sc_ + 2, MW // sc_ + 2)) * 255).astype(np.uint8)).resize((MW, MH), Image.BICUBIC)
            noise += np.asarray(nz, np.float32) / 255 * amp
        width = 7 + 5 * np.exp(-(lgal / 30) ** 2)                            # thicker round the bulge
        band = np.exp(-(bgal / width) ** 2) * (0.45 + 0.9 * np.exp(-(lgal / 45) ** 2) + 0.15 * np.cos(np.radians(lgal)))
        rift = np.exp(-((bgal - 1.5) / 2.2) ** 2) * np.exp(-((lgal - 30) / 40) ** 2) * 0.55
        mwv = band * (0.3 + 1.2 * noise ** 1.5) * (1 - rift)
        self.mwmap = np.clip(mwv / np.percentile(mwv, 99.7), 0, 1).astype(np.float32)
        # faint stars below the catalogue (mag 6-8.5): random, half of them following the Milky Way
        u = rng.normal(size=(self._faint_n * 3, 3)); u /= np.linalg.norm(u, axis=1)[:, None]
        ra = np.degrees(np.arctan2(u[:, 1], u[:, 0])) % 360; dec = np.degrees(np.arcsin(u[:, 2]))
        w = self.mwmap[np.clip(((90 - dec) / 180 * MH).astype(int), 0, MH - 1), np.clip((ra / 360 * MW).astype(int), 0, MW - 1)]
        keep = rng.random(len(u)) < 0.25 + 0.75 * np.clip(w * 2.5, 0, 1)
        self.faint_v = u[keep][:self._faint_n]
        self.faint_b = (10 ** (-0.4 * (rng.uniform(6.0, 8.5, len(self.faint_v)) - 6.0))).astype(np.float32)
        self.faint_c = np.array([bv_rgb(x) for x in rng.normal(0.6, 0.35, len(self.faint_v))], np.float32)
        F = os.path.join(TOOLS, 'fonts')
        self._fonts = {}
        def font(size, bold=True):
            key = (size, bold)
            if key not in self._fonts:
                f = ImageFont.truetype(os.path.join(F, 'Unbounded.ttf' if bold else 'Commissioner.ttf'), size * ss)
                try: f.set_variation_by_axes([600])
                except Exception: pass
                self._fonts[key] = f
            return self._fonts[key]
        self.font = font

    # projection: centre c (unit vector), scale (px per radian, at final size), roll (deg) -> function v -> (x, y, ok)
    def proj(self, c, scale, roll=0.0, cx=None, cy=None):
        c = c / np.linalg.norm(c)
        Z = np.array([0.0, 0.0, 1.0])
        a = np.cross(Z, c); a = a / np.linalg.norm(a) if np.linalg.norm(a) > 1e-9 else np.array([0.0, 1.0, 0.0])
        b = np.cross(c, a)
        cr, sr = math.cos(roll * D2R), math.sin(roll * D2R)
        s = scale * self.ss
        cx = (self.W / 2 if cx is None else cx) * self.ss; cy = (self.H / 2 if cy is None else cy) * self.ss
        def f(V):
            V = np.atleast_2d(V)
            z = np.clip(V @ c, -1, 1); rho = np.arccos(z)
            xt, yt = V @ a, V @ b
            n = np.hypot(xt, yt) + 1e-12
            X, Y = -rho * xt / n, rho * yt / n
            X, Y = X * cr - Y * sr, X * sr + Y * cr
            return cx + X * s, cy - Y * s, rho < 2.6
        return f

    def unproj(self, c, scale, roll, X, Y):
        """screen pixels (at the supersampled size) -> unit vectors of the sky (the inverse of proj)"""
        c = c / np.linalg.norm(c)
        Z = np.array([0.0, 0.0, 1.0])
        a = np.cross(Z, c); a = a / np.linalg.norm(a) if np.linalg.norm(a) > 1e-9 else np.array([0.0, 1.0, 0.0])
        b = np.cross(c, a)
        s = scale * self.ss
        Xs, Ys = (X - self.W * self.ss / 2) / s, -(Y - self.H * self.ss / 2) / s
        cr, sr = math.cos(roll * D2R), math.sin(roll * D2R)
        Xp, Yp = Xs * cr + Ys * sr, -Xs * sr + Ys * cr
        rho = np.hypot(Xp, Yp) + 1e-12
        t = (-Xp / rho)[..., None] * a + (Yp / rho)[..., None] * b
        return np.cos(rho)[..., None] * c + np.sin(rho)[..., None] * t

    def render(self, v):
        """v: dict(centre (vec), scale, roll, stars=1, mw=1, lines=0.35, zlines=0.8, hi={id: k}, borders={id: k},
        ecliptic=0.6, labels=1, zlabel={id: k}, sun=lambda or None, sun_k=1, glow=[(vec, radius px, (r,g,b), k)])"""
        W, H, ss = self.W * self.ss, self.H * self.ss, self.ss
        P = self.proj(v['centre'], v['scale'], v.get('roll', 0.0))
        img = np.zeros((H, W, 3), np.float32)
        # background: deep night blue, a touch lighter low down
        yy = np.linspace(0, 1, H)[:, None, None]
        img += np.array([3, 5, 12], np.float32) * (1 - yy) + np.array([8, 12, 28], np.float32) * yy
        base = Image.fromarray(img.astype(np.uint8))
        # Milky Way: the RA/Dec brightness map, sampled through the inverse projection (at a quarter of the size)
        img = np.asarray(base, np.float32)
        if v.get('mw', 1) > 0:
            q = 4; w, h = W // q, H // q
            X, Y = np.meshgrid((np.arange(w) + 0.5) * q, (np.arange(h) + 0.5) * q)
            dirs = self.unproj(v['centre'], v['scale'], v.get('roll', 0.0), X, Y)
            ra = np.degrees(np.arctan2(dirs[..., 1], dirs[..., 0])) % 360
            dec = np.degrees(np.arcsin(np.clip(dirs[..., 2], -1, 1)))
            mh, mw_ = self.mwmap.shape
            m = self.mwmap[np.clip(((90 - dec) / 180 * mh).astype(int), 0, mh - 1), np.clip((ra / 360 * mw_).astype(int), 0, mw_ - 1)]
            m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)[:, :, None] / 255
            m = m ** 1.5
            img = img + m * v.get('mw', 1) * np.array([46, 50, 68], np.float32)
        # glows (e.g. the Sun's corona, a supernova) under the stars
        for g in v.get('glow', []):
            gv, rad, col, k = g
            x, y, ok = P(gv)
            if not ok[0] or k <= 0: continue
            r = rad * ss; x0, y0 = int(x[0]), int(y[0])
            ys, xs = np.ogrid[-int(3 * r):int(3 * r) + 1, -int(3 * r):int(3 * r) + 1]
            gk = np.exp(-(xs * xs + ys * ys) / (2 * r * r)).astype(np.float32) * k
            self._add(img, x0, y0, gk, np.array(col, np.float32))
        # faint stars: tiny splats
        x, y, ok = P(self.faint_v)
        sel = ok & (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
        if sel.any():
            xi, yi = x[sel].astype(int), y[sel].astype(int); val = (self.faint_b[sel] * 70 * v.get('stars', 1.0))[:, None] * self.faint_c[sel] / 255
            for dx in (0, 1):
                for dy in (0, 1):
                    np.add.at(img, (yi + dy, xi + dx), val)
        # stars: a gaussian dot each, size and brightness by magnitude; a soft halo on the brightest
        x, y, ok = P(self.star_v)
        sel = ok & (x > -20) & (x < W + 20) & (y > -20) & (y < H + 20)
        sk = v.get('stars', 1.0) * v.get('star_gain', 1.0)
        size_k = v.get('star_size', min(2.6, max(1.0, (v['scale'] / 400) ** 0.4)))
        for i in np.nonzero(sel)[0]:
            mag = self.star_mag[i]
            b = 10 ** (-0.4 * (mag - 1.0))                       # flux, 1 at magnitude 1
            r = (0.8 + 0.5 * max(0.0, 6.0 - mag)) * ss * size_k
            amp = min(2.4, 0.6 + 1.3 * b ** 0.5) * sk
            n = int(3 * r) + 1
            ys, xs = np.ogrid[-n:n + 1, -n:n + 1]
            dx, dy = x[i] - int(x[i]), y[i] - int(y[i])
            kern = np.exp(-((xs - dx) ** 2 + (ys - dy) ** 2) / (2 * r * r)).astype(np.float32) * amp
            self._add(img, int(x[i]), int(y[i]), kern, self.star_col[i])
            if mag < 1.8:
                R = r * 5
                n = int(2.5 * R) + 1
                ys, xs = np.ogrid[-n:n + 1, -n:n + 1]
                kern = np.exp(-(xs * xs + ys * ys) / (2 * R * R)).astype(np.float32) * 0.12 * min(2.0, b) * sk
                self._add(img, int(x[i]), int(y[i]), kern, self.star_col[i])
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)

        def poly(points, col, width, dash=None):
            x, y, ok = P(np.array(points))
            seg = []
            for a, b, o in zip(x, y, ok):
                if o: seg.append((float(a), float(b)))
                else:
                    if len(seg) > 1: d.line(seg, fill=col, width=width)
                    seg = []
            if len(seg) > 1:
                if dash:
                    for j in range(len(seg) - 1):
                        if (j // dash) % 2 == 0: d.line([seg[j], seg[j + 1]], fill=col, width=width)
                else:
                    d.line(seg, fill=col, width=width, joint='curve')

        def dense(points, step=1.0):          # great-circle points between the vertices, so lines curve with the map
            out_ = []
            for p, q in zip(points, points[1:]):
                ang = math.degrees(math.acos(max(-1, min(1, float(p @ q)))))
                n = max(1, int(ang / step))
                out_ += [slerp(p, q, j / n) for j in range(n)]
            return out_ + [points[-1]]
        # IAU borders of chosen constellations (dashed)
        for cid, k in v.get('borders', {}).items():
            if k <= 0: continue
            for seg in self.borders.get(cid, []):
                poly(dense(seg, 0.5), (130, 200, 255, int(170 * k)), 2 * ss, dash=4)
        # ecliptic: the Sun's yearly path
        if v.get('ecliptic', 0) > 0:
            poly([ecl(l) for l in np.arange(0, 361, 1.0)], (243, 185, 100, int(150 * v['ecliptic'])), 2 * ss, dash=3)
        # constellation figures: faint everywhere, the zodiac brighter, highlights brightest
        zids = {z for z, _ in ZODIAC}
        hi = v.get('hi', {})
        for cid, segs in self.lines.items():
            k = hi.get(cid, 0)
            if cid in zids:
                a = v.get('zlines', 0.8) * (1 - k); col = (230, 205, 160)
            else:
                a = v.get('lines', 0.3) * (1 - k); col = (150, 170, 210)
            for seg in segs:
                pts = dense(seg)
                if a > 0.01: poly(pts, col + (int(160 * a),), int(1.5 * ss))
                if k > 0.01: poly(pts, (120, 220, 255, int(235 * k)), 3 * ss)
        out.alpha_composite(lay)
        # the Sun on the ecliptic
        sun = v.get('sun')
        if sun is not None and v.get('sun_k', 1) > 0:
            x, y, ok = P(ecl(sun))
            if ok[0]:
                k = v.get('sun_k', 1); g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
                r = v.get('sun_r', 26) * ss
                for j, (rr, al) in enumerate([(r * 3.2, 40), (r * 2.0, 70), (r * 1.3, 130)]):
                    dg.ellipse((x[0] - rr, y[0] - rr, x[0] + rr, y[0] + rr), fill=(255, 190, 90, int(al * k)))
                g = g.filter(ImageFilter.GaussianBlur(r * 0.6))
                dg = ImageDraw.Draw(g); dg.ellipse((x[0] - r, y[0] - r, x[0] + r, y[0] + r), fill=(255, 244, 214, int(255 * k)))
                out.alpha_composite(g)
        # names of the zodiac constellations
        lab = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(lab)
        fsz = v.get('label_size', 30)
        for cid, name in ZODIAC:
            k = v.get('zlabel', {}).get(cid, v.get('labels', 1.0))
            if k <= 0.01: continue
            x, y, ok = P(self.label[cid])
            if not ok[0]: continue
            big = hi.get(cid, 0)
            f = self.font(int(fsz * (1 + 0.45 * big)), bold=True)
            col = (130, 220, 255) if big > 0.5 else (240, 214, 170)
            dl.text((x[0] + 3 * ss, y[0] + 4 * ss), name, font=f, fill=(0, 0, 0, int(180 * k)), anchor='mm')
            dl.text((x[0], y[0]), name, font=f, fill=col + (int(255 * k),), anchor='mm')
        out.alpha_composite(lab)
        return out.convert('RGB').resize((self.W, self.H), Image.LANCZOS)

    @staticmethod
    def _add(img, x0, y0, kern, col):
        H, W = img.shape[:2]; n = kern.shape[0] // 2
        ya, yb, xa, xb = y0 - n, y0 + n + 1, x0 - n, x0 + n + 1
        ka, kb, kc, kd = 0, kern.shape[0], 0, kern.shape[1]
        if ya < 0: ka -= ya; ya = 0
        if xa < 0: kc -= xa; xa = 0
        if yb > H: kb -= yb - H; yb = H
        if xb > W: kd -= xb - W; xb = W
        if ya >= yb or xa >= xb: return
        img[ya:yb, xa:xb] += kern[ka:kb, kc:kd, None] * col[None, None, :]
