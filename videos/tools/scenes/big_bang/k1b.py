# «Великий вибух» — К1, the HONEST variant (to compare with k1.py): what the early Universe really was — an even,
# blinding glow filling all of space, the same in every direction, with no clumps, no voids, no edge and no centre.
# The only structure: ripples of density/temperature ~1 part in 100 000 — shown here with their contrast amplified
# (as the Planck maps do), ripples that STRETCH as space expands while the camera flies through.
# Colour: the visible part of a blackbody of billions of degrees — blue-white (the limit of a hot body's colour),
# not gold and not fire.
#
# How: the same comoving camera as k1.py (a = exp(HUB t), V, the faint tremor). The glow is ray-marched as an
# emitting + absorbing medium (the photons' mean free path MFP): an even medium gives an even brightness; the ripples
# (a smooth, near scale-invariant random field in comoving coordinates) modulate the emission, so near ripples look
# large and soft, far ones small and fine — depth without any made-up objects.
#   python3 k1b.py --still 0      -> test/k1b_still_0.00.jpg      (and --still 2.8, --still 5.5)
#   python3 k1b.py                -> test/k1b/f_####.jpg + test/k1b.mp4
import math, os, sys, subprocess
import numpy as np
from numba import njit, prange
from scipy import ndimage
from PIL import Image
from k1 import vnoise, _h, ROT, basis, scale, cam_c, tonemap, W, H, FPS, DUR, FOV

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'test')
HW, HH = W // 2, H // 2
MFP = 0.55                 # how far one sees into the glow (units)
SMAX = 6.0
NSTEP = 120
AMP = 0.55 
CON = 4.5                # the ripples' contrast in the picture (amplified: in reality ~0.00001)
# the glow's colour (linear RGB): a blackbody of very high temperature — blue-white
BASE = np.array([0.74, 0.84, 1.00])


@njit(cache=True)
def ripple(x, y, z):
    # a smooth near scale-invariant random field (sum of rotated value-noise octaves), mean ~0, ~[-1, 1]
    r0, r1, r2, r3, r4, r5, r6, r7, r8 = ROT
    f = 0.0; amp = 1.0; fr = 0.85; norm = 0.0
    for o in range(5):
        x, y, z = r0 * x + r1 * y + r2 * z, r3 * x + r4 * y + r5 * z, r6 * x + r7 * y + r8 * z
        f += amp * (vnoise(x * fr + 11.1 * o, y * fr, z * fr) - 0.5)
        norm += amp; amp *= 0.80; fr *= 2.07
    return f / norm * 4.0


@njit(parallel=True, cache=True)
def march(img, cc0, cc1, cc2, fw, rt, up, a, tanh, aspect, nstep, smax, mfp, amp, jit):
    h, w = img.shape[0], img.shape[1]
    for py in prange(h):
        for px in range(w):
            sx = (2.0 * (px + 0.5) / w - 1.0) * tanh * aspect
            sy = (1.0 - 2.0 * (py + 0.5) / h) * tanh
            dx = fw[0] + rt[0] * sx + up[0] * sy
            dy = fw[1] + rt[1] * sx + up[1] * sy
            dz = fw[2] + rt[2] * sx + up[2] * sy
            n = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= n; dy /= n; dz /= n
            T = 1.0; lum = 0.0; tint = 0.0
            u0 = _h(px, py, jit)
            for k in range(nstep):
                q0 = (k + u0) / nstep; q1 = (k + 1 + u0) / nstep
                s = smax * q0 * q0; ds = smax * (q1 * q1 - q0 * q0)
                x = cc0 + dx * s / a; y = cc1 + dy * s / a; z = cc2 + dz * s / a
                d = ripple(x, y, z)
                e = 1.0 + amp * d                     # hotter spots glow brighter (and bluer)
                wgt = T * (1.0 - math.exp(-ds / mfp))
                lum += wgt * e; tint += wgt * d
                T *= math.exp(-ds / mfp)
            lum += T                                   # beyond: the same even glow
            img[py, px, 0] = lum; img[py, px, 1] = tint


def frame(t, rng):
    a = scale(t); cc = cam_c(t); fw, rt, up = basis(t)
    tanh = math.tan(FOV / 2); aspect = W / H
    buf = np.zeros((HH, HW, 2), np.float32)
    march(buf, cc[0], cc[1], cc[2], fw, rt, up, a, tanh, aspect, NSTEP, SMAX, MFP, AMP, int(t * FPS) & 1023)
    big = np.stack([ndimage.zoom(buf[..., c], 2, order=1) for c in range(2)], -1)
    big = ndimage.gaussian_filter(big, (0.6, 0.6, 0))
    lum, tint = big[..., 0], big[..., 1]
    # brightness: the even glow sits high; the ripples carry the contrast. Hot spots a touch bluer, cool a touch warmer.
    # the ripples' contrast is amplified (as on the Planck maps): ×CON around the mean glow
    L = 0.13 * np.clip(1.0 + CON * (lum - 1.0), 0.05, None) ** 2.0
    col = BASE[None, None, :] * L[..., None]
    col[..., 0] *= 1 - 0.10 * tint; col[..., 2] *= 1 + 0.06 * tint
    # a soft glare (the light is everywhere) and a gentle vignette for depth
    glare = ndimage.gaussian_filter(col, (40, 40, 0))
    x = 0.85 * col + 0.30 * glare
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.3
    x = x * v[..., None]
    out = tonemap(x * 1.35)
    g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)
    out = out + g[..., None] * 0.010
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    os.makedirs(os.path.join(OUT, 'k1b'), exist_ok=True)
    rng = np.random.default_rng(1)
    if '--still' in sys.argv:
        t = float(sys.argv[sys.argv.index('--still') + 1])
        Image.fromarray(frame(t, rng)).save(os.path.join(OUT, f'k1b_still_{t:.2f}.jpg'), quality=93)
        return
    n = int(round(DUR * FPS))
    for i in range(n):
        dst = os.path.join(OUT, 'k1b', f'f_{i:04d}.jpg')
        if os.path.exists(dst):
            continue
        Image.fromarray(frame(i / FPS, rng)).save(dst, quality=93)
        if i % 10 == 0: print(i, '/', n, flush=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(OUT, 'k1b', 'f_%04d.jpg'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                    os.path.join(OUT, 'k1b.mp4')], check=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
