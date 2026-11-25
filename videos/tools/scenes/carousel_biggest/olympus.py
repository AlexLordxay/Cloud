# Гора Олімп під кутом: справжня карта висот MOLA (MGS, NASA; MEGDR 128 пікс./°, плитка megt44n180hb), трасування
# променів над рельєфом (numba), висоти ×EX, низьке Сонце, марсіанське небо. -> work/carousel_biggest/olympus.jpg
#   python3 scenes/carousel_biggest/olympus.py [EX]
import math, os, sys
import numpy as np
from numba import njit, prange
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
DL = os.path.join(TOOLS, 'work', 'carousel_biggest', 'dl')
EX = float(sys.argv[1]) if len(sys.argv) > 1 else 2.5
a = np.fromfile(os.path.join(DL, 'megt44n180hb.img'), '>i2').reshape(5632, 11520)
LAT0, LON0 = 18.65, 226.2
r0, r1 = int((44 - 30) * 128), int((44 - 7) * 128); c0, c1 = int((214 - 180) * 128), int((238 - 180) * 128)
Z = a[r0:r1, c0:c1].astype(np.float32) / 1000.0            # km
Z -= np.median(Z)
KM = 3389.5 * math.pi / 180 / 128                            # km per pixel (lat)
kx = KM * math.cos(math.radians(LAT0))
ny, nx = Z.shape
# map coords: x east km, y north km; origin at the summit
cx, cy = (LON0 - 214) * 128, (30 - LAT0) * 128
Z = Z * EX
# albedo: smooth noise for dust variation
rng = np.random.default_rng(3)
nz = rng.standard_normal((ny // 8 + 1, nx // 8 + 1)).astype(np.float32)
nz = np.ascontiguousarray(np.asarray(Image.fromarray(nz).resize((nx, ny), Image.BICUBIC)), dtype=np.float32)
W, H, SS = 1080, 1350, 2

@njit(fastmath=True)
def hgt(Z, px, py):
    ny, nx = Z.shape
    if px < 0 or py < 0 or px >= nx - 1 or py >= ny - 1: return -1e9
    i, j = int(px), int(py); fx, fy = px - i, py - j
    return (Z[j, i] * (1 - fx) + Z[j, i + 1] * fx) * (1 - fy) + (Z[j + 1, i] * (1 - fx) + Z[j + 1, i + 1] * fx) * fy

@njit(parallel=True, fastmath=True)
def render(Z, nz, cam, fw, rt, up, fov, kx, KM, cx, cy, sun, out, W, H):
    tanf = math.tan(fov / 2)
    for py_ in prange(H):
        for px_ in range(W):
            u = (2 * (px_ + 0.5) / W - 1) * tanf * W / H; v = (1 - 2 * (py_ + 0.5) / H) * tanf
            dx = fw[0] + rt[0] * u + up[0] * v; dy = fw[1] + rt[1] * u + up[1] * v; dz = fw[2] + rt[2] * u + up[2] * v
            dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
            t = 1.0; hit = False
            for s in range(4000):
                X = cam[0] + dx * t; Y = cam[1] + dy * t; Zc = cam[2] + dz * t
                h = hgt(Z, cx + X / kx, cy - Y / KM)
                if h < -1e8 and t > 50: break
                if Zc < h:
                    t0 = t - max(0.25, t * 0.002)
                    for k in range(10):
                        tm = (t0 + t) / 2
                        if cam[2] + dz * tm < hgt(Z, cx + (cam[0] + dx * tm) / kx, cy - (cam[1] + dy * tm) / KM): t = tm
                        else: t0 = tm
                    hit = True; break
                t += max(0.25, t * 0.002)
                if t > 2500: break
            if hit:
                X = cam[0] + dx * t; Y = cam[1] + dy * t; Zc = cam[2] + dz * t
                mx = cx + X / kx; my = cy - Y / KM
                gx = (hgt(Z, mx + 1, my) - hgt(Z, mx - 1, my)) / (2 * kx)
                gy = -(hgt(Z, mx, my + 1) - hgt(Z, mx, my - 1)) / (2 * KM)
                nl = math.sqrt(gx * gx + gy * gy + 1); n0 = -gx / nl; n1 = -gy / nl; n2 = 1 / nl
                lam = max(0.0, n0 * sun[0] + n1 * sun[1] + n2 * sun[2])
                sh = 1.0; qx = X + n0 * 0.05; qy = Y + n1 * 0.05; qz = Zc + n2 * 0.05
                for k in range(70):
                    st = 0.6 + k * 0.25
                    qx += sun[0] * st; qy += sun[1] * st; qz += sun[2] * st
                    hh = hgt(Z, cx + qx / kx, cy - qy / KM)
                    if hh < -1e8: break
                    if qz < hh: sh = 0.22; break
                al = 1.0 + 0.06 * nz[int(my), int(mx)]
                slope = 1.0 - n2
                li = 0.06 + 1.45 * lam * sh
                r = (0.62 * al * (1 - 0.35 * slope) + 0.08 * slope) * li + 0.06
                g = (0.36 * al * (1 - 0.35 * slope) + 0.05 * slope) * li + 0.035
                b = (0.20 * al * (1 - 0.35 * slope) + 0.04 * slope) * li + 0.025
                hz = (1.0 - math.exp(-t / 2600.0)) * 0.85
                r = r * (1 - hz) + 0.62 * hz; g = g * (1 - hz) + 0.45 * hz; b = b * (1 - hz) + 0.33 * hz
            else:
                el = max(dz, 0.0); k3 = (1 - el) ** 3
                r = 0.66 * k3 + 0.20 * (1 - k3); g = 0.48 * k3 + 0.14 * (1 - k3); b = 0.34 * k3 + 0.12 * (1 - k3)
            out[py_, px_, 0] = r; out[py_, px_, 1] = g; out[py_, px_, 2] = b

def look(cam, tgt):
    fw = tgt - cam; fw /= np.linalg.norm(fw)
    rt = np.cross(fw, [0, 0, 1.0]); rt /= np.linalg.norm(rt); up = np.cross(rt, fw)
    return fw, rt, up

cam = np.array([300.0, -600.0, 210.0]); tgt = np.array([0.0, -40.0, -85.0])
fw, rt, up = look(cam, tgt)
sun = np.array([-0.85, 0.35, 0.33]); sun /= np.linalg.norm(sun)
out = np.zeros((H * SS, W * SS, 3), np.float32)
render(Z, nz, cam, fw, rt, up, math.radians(46), kx, KM, cx, cy, sun, out, W * SS, H * SS)
img = np.clip(out, 0, 1) ** (1 / 1.25)
im = Image.fromarray((img * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
im.save(os.path.join(TOOLS, 'work', 'carousel_biggest', 'olympus.jpg'), quality=93)
print('olympus.jpg')
