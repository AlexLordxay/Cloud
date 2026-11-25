# «А ти уявляєш Європу так?» — the data:
#   * globe.jpg (8192 × 4096): the USGS Voyager + Galileo SSI global mosaic (500 m/px, grey) coloured like Galileo's
#     true-colour views: clean ice white with a touch of blue, older/darker ground and the lineae reddish-brown;
#   * the flight patch (200 × 200 km round 24° N on the mosaic's detailed Galileo strip, 4096² ≈ 49 m/px):
#     height (m) and albedo. The real lineae of the mosaic become double ridges (raised flanks, a trough in the middle,
#     as Galileo saw them), plus ridged plains (fine parallel ridges), chaos blocks where the ground is mottled,
#     and rough ice down to the pixel. Heights are ×3 for the eye (real double ridges are ~100–300 m).
#   python3 scenes/europa_imagine/prep.py   -> work/europa_imagine/{globe.jpg, hf.npy, alb.npy}
import math, os
import numpy as np
from PIL import Image
from scipy import ndimage as nd
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
W = os.path.join(TOOLS, 'work', 'europa_imagine')
src = Image.open(os.path.join(W, 'europa_500m.tif'))
A = np.asarray(src).astype(np.float32) / 255.0
H0, W0 = A.shape
# the black no-data cap at the south pole -> the mean of the row above it
A[A < 0.02] = np.nan
col = np.nanmean(A, axis=1); last = np.where(~np.isnan(col))[0].max()
A[last:, :] = col[last]
A = np.where(np.isnan(A), np.nanmean(A), A)

def colourise(L, k=1.0):
    # L: 0..1 brightness -> RGB (Galileo true-colour-like): dark = reddish brown, mid = tan, bright = white, faint blue
    c0 = np.array([0.52, 0.38, 0.29]); c1 = np.array([0.80, 0.75, 0.68]); c2 = np.array([0.96, 0.97, 0.99])
    t = np.clip((L - 0.25) / 0.6, 0, 1)[..., None]
    lo = c0 + (c1 - c0) * np.clip(t * 2, 0, 1); hi = c1 + (c2 - c1) * np.clip(t * 2 - 1, 0, 1)
    return np.where(t < 0.5, lo, hi)

if not os.path.exists(os.path.join(W, 'globe.jpg')):
    g = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).resize((8192, 4096), Image.LANCZOS)).astype(np.float32) / 255
    # stretch contrast a little (the mosaic is flat grey)
    g = np.clip((g - 0.5) * 1.5 + 0.58, 0, 1)
    rgb = colourise(g)
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(os.path.join(W, 'globe.jpg'), quality=93)
    print('globe.jpg')

# ---- the flight patch ----
R_E = 1560.8
LAT0 = 90 - 3600 / H0 * 180; LON0 = 8400 / W0 * 360           # mosaic coords of the centre (detailed area)
N, HALF = 4096, 100.0
km = (np.arange(N) + 0.5) / N * 2 * HALF - HALF
X, Y = np.meshgrid(km, -km)                                     # x east, y north; row 0 = north
lat = LAT0 + Y / (R_E * math.pi / 180); lon = LON0 + X / (R_E * math.pi / 180 * math.cos(math.radians(LAT0)))
py = (90 - lat) / 180 * H0; px = lon / 360 * W0
L = nd.map_coordinates(A, [py, px], order=3, mode='nearest').astype(np.float32)
L = np.clip((L - np.median(L)) * 1.15 + 0.66, 0, 1)
px_km = 2 * HALF / N
rng = np.random.default_rng(4)
def noise(scale, seed):
    r = np.random.default_rng(seed).standard_normal((N // scale + 2, N // scale + 2)).astype(np.float32)
    return np.asarray(Image.fromarray(r).resize((N + 2 * scale, N + 2 * scale), Image.BICUBIC))[scale:scale + N, scale:scale + N]
# double ridges: long gently curving lines across the patch, three sizes, crossing each other (younger ones on top),
# laid along the directions of the real lineae here (~20–35° and ~150° on the mosaic)
dark = nd.grey_closing(L, size=(int(4 / px_km),) * 2) - L
S = np.clip(nd.gaussian_filter(dark, 2.0) / (np.percentile(dark, 99.7) + 1e-6), 0, 1)
def lines_mask(n, seed, length, wav):
    r = np.random.default_rng(seed); m = np.zeros((N, N), bool)
    for _ in range(n):
        a = r.uniform(0, math.pi) if r.uniform() < 0.6 else r.choice([0.5, 2.65]) + r.normal(0, 0.15)
        c = r.normal(0, 0.006); L_ = r.uniform(*length)
        x, y = r.uniform(-120, 120), r.uniform(-120, 120); ds = px_km * 0.5; steps = int(L_ / ds)
        xs = np.empty(steps); ys = np.empty(steps); ph = r.uniform(0, 6.3); wl = r.uniform(8, 25)
        for i in range(steps):
            xs[i] = x; ys[i] = y
            a += c * ds + wav * math.sin(ph + i * ds / wl * 6.283) * ds / wl
            x += math.cos(a) * ds; y += math.sin(a) * ds
        ii = ((xs + HALF) / px_km).astype(int); jj = ((HALF - ys) / px_km).astype(int)
        ok = (ii >= 0) & (ii < N) & (jj >= 0) & (jj < N); m[jj[ok], ii[ok]] = True
    return m
h = np.zeros((N, N), np.float32); prof_all = np.zeros((N, N), np.float32); crest = np.zeros((N, N), np.float32)
# oldest first: fine ridged plains, then ever bigger and younger double ridges cutting across them
for n, seed, w, a_, length, wav in [(520, 1, 0.16, 22, (8, 50), 0.6), (220, 2, 0.30, 55, (20, 120), 0.5),
                                     (60, 3, 0.62, 130, (60, 260), 0.35), (10, 4, 1.2, 250, (180, 400), 0.25)]:
    d = nd.distance_transform_edt(~lines_mask(n, seed, length, wav)) * px_km
    pr = np.exp(-((d - w) / (0.6 * w)) ** 2) - 0.28 * np.exp(-(d / (0.32 * w)) ** 2)
    hh = a_ * nd.gaussian_filter(pr, 1.2) * (0.8 + 0.4 * np.random.default_rng(seed).uniform())
    zone = d < 2.2 * w
    h = np.where(zone, hh + 0.25 * h * (d > 1.6 * w), h)               # the younger ridge replaces what it crosses
    prof_all = np.where(zone, np.exp(-(d / (1.8 * w)) ** 2) * min(1.0, a_ / 130), prof_all)
    crest = np.maximum(crest, np.exp(-((d - w) / (0.3 * w)) ** 2) * min(1.0, a_ / 130))
prof = prof_all
# ridged plains: fine parallel ridges, sharp crests, in broad patches
gy, gx = np.mgrid[0:N, 0:N].astype(np.float32)
X_, Y_ = X, Y
warp = noise(256, 11) * 2.0
for k, (ang, per, a_, seed) in enumerate([(0.5, 0.55, 6, 21), (2.65, 0.8, 7, 22)]):
    m = np.clip(noise(900, seed) * 1.2 - 0.3, 0, 1)
    ph = (X_ * math.cos(ang) + Y_ * math.sin(ang)) / per * 2 * math.pi + warp * (k + 1)
    h += a_ * m * (1 - np.abs(np.sin(ph))) ** 6 * (1 + 0.5 * noise(40, seed + 5))
# gentle swells
h += 45 * noise(400, 61) + 15 * noise(60, 62) + 2.5 * noise(3, 63)
# one patch of chaos terrain: broken, tilted ice rafts in a darker matrix (like Conamara Chaos)
cx0, cy0, rad = 52.0, -48.0, 22.0
rr = np.sqrt((X - cx0) ** 2 + (Y - cy0) ** 2)
mk = np.clip((rad - rr) / 6.0, 0, 1) * np.clip(1 + 0.4 * noise(200, 71), 0, 1)
cell = 2.6 / px_km
jx = noise(64, 31) * cell * 0.4; jy = noise(64, 32) * cell * 0.4
ci = np.floor((gx + jx) / cell); cj = np.floor((gy + jy) / cell)
hc = (np.sin(ci * 12.9898 + cj * 78.233) * 43758.5453) % 1.0
hd = (np.sin(ci * 39.3468 + cj * 11.135) * 24634.6345) % 1.0
fx = ((gx + jx) / cell) % 1.0; fy = ((gy + jy) / cell) % 1.0
edge = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
raft = (hd > 0.35) * np.clip(edge / 0.08, 0, 1) * (140 + 160 * hc + 90 * (fx - 0.5) * (hc - 0.5) * 4)
matrix = 35 * noise(6, 72) - 60
h = h * (1 - mk) + (raft + matrix * (raft == 0)) * mk
h = nd.gaussian_filter(h, 0.7) * 3.0                            # ×3 for the eye
np.save(os.path.join(W, 'hf.npy'), h.astype(np.float32))
# albedo: the mosaic's brightness, the troughs and lineae brown, the ridge crests frosty white
alb = colourise(np.clip(0.60 + 0.9 * (L - 0.66) + 0.08 * noise(40, 52) + 0.05 * noise(10, 53) - 0.30 * prof + 0.10 * crest - 0.2 * mk * (raft == 0), 0, 1))
alb *= (1 + 0.04 * noise(4, 51))[..., None]
np.save(os.path.join(W, 'alb.npy'), np.clip(alb, 0, 1).astype(np.float32))
print('patch', N, 'px,', 2 * HALF, 'km; h', float(h.min()), float(h.max()))
Image.fromarray((np.clip(alb, 0, 1) * 255).astype(np.uint8)).resize((1024, 1024)).save(os.path.join(W, 'alb_th.jpg'))
hs = (h - h.min()) / (h.max() - h.min())
Image.fromarray((hs * 255).astype(np.uint8)).resize((1024, 1024)).save(os.path.join(W, 'hf_th.jpg'))
