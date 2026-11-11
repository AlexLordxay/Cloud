# The cosmic web by the Zel'dovich approximation: particles on a grid moved by the gradient of a Gaussian random
# potential, x = q + D·psi(q) — as D grows, matter streams into sheets, filaments and knots (as in the real Universe).
# Render: perspective splat of the particles into a half-resolution buffer (np.add.at), fog with distance.
import math, os
import numpy as np
import cv2

N = 112                  # particles per side
L = 100.0                # the box (units), periodic
_cache = {}


def field(seed=3, n_index=-1.6, kcut=0.32):
    key = (seed, n_index, kcut)
    if key in _cache: return _cache[key]
    rng = np.random.default_rng(seed)
    k1 = np.fft.fftfreq(N, d=L / N) * 2 * math.pi
    kx, ky, kz = np.meshgrid(k1, k1, k1, indexing='ij')
    k2 = kx * kx + ky * ky + kz * kz; k2[0, 0, 0] = 1.0
    amp = np.sqrt(k2 ** (n_index / 2) * np.exp(-k2 / kcut ** 2)); amp[0, 0, 0] = 0
    delta = np.fft.fftn(rng.standard_normal((N, N, N))) * amp
    psi = []
    for kk in (kx, ky, kz):
        psi.append(np.real(np.fft.ifftn(1j * kk / k2 * delta)).astype(np.float32))
    psi = np.stack([p.ravel() for p in psi], -1)
    psi /= psi.std() / (L / N * 0.95)                  # D = 1: rms displacement ~ one grid spacing (filaments form)
    q = np.stack(np.meshgrid(*(np.arange(N) * L / N,) * 3, indexing='ij'), -1).reshape(-1, 3).astype(np.float32)
    q += rng.uniform(0, L / N, q.shape).astype(np.float32)        # off the lattice (no grid patterns)
    _cache[key] = (q, psi)
    return q, psi


def positions(D, seed=3):
    q, psi = field(seed)
    return (q + D * psi) % L


def densest(P, cell=4.0):
    """the centre of the densest knot"""
    g = (P // cell).astype(int)
    n = int(L // cell)
    idx = g[:, 0] * n * n + g[:, 1] * n + g[:, 2]
    c = np.bincount(idx, minlength=n ** 3)
    b = int(np.argmax(c))
    cell_c = np.array([b // (n * n), (b // n) % n, b % n]) * cell + cell / 2
    near = P[np.all(np.abs(P - cell_c) < cell * 1.5, axis=1)]
    return near.mean(0)


def look(cam, tgt, roll=0.0):
    fw = tgt - cam; fw = fw / np.linalg.norm(fw)
    up0 = np.array([0, 1.0, 0])
    rt = np.cross(up0, fw); rt /= np.linalg.norm(rt); up = np.cross(fw, rt)
    c, s = math.cos(roll), math.sin(roll)
    return fw, rt * c + up * s, -rt * s + up * c


def splat(P, w, cam, fw, rt, up, W, H, fov=math.radians(60), fog=60.0, near=0.5, wrap=True):
    """additive points -> a half-res float buffer; P: (n, 3); w: weights (n,) or scalar"""
    rel = P - cam
    if wrap: rel = (rel + L / 2) % L - L / 2           # the periodic box around the camera
    z = rel @ fw
    ok = z > near
    rel = rel[ok]; z = z[ok]
    ww = w[ok] if np.ndim(w) else np.full(len(z), w, np.float32)
    f = (H / 2) / math.tan(fov / 2)
    x = (rel @ rt) / z * f + W / 2; y = H / 2 - (rel @ up) / z * f
    h2, w2 = H // 2, W // 2
    xi = (x / 2).astype(np.int32); yi = (y / 2).astype(np.int32)
    m = (xi >= 0) & (xi < w2) & (yi >= 0) & (yi < h2)
    buf = np.zeros((h2, w2), np.float32)
    np.add.at(buf, (yi[m], xi[m]), (ww[m] * np.exp(-z[m] / fog) * np.clip(z[m] / 3.0, 0, 1)).astype(np.float32))
    return buf
