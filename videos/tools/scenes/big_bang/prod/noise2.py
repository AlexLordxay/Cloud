# Shared numba fields for the 2D renders: a rotated value-noise fBm over (x, y, z) for every pixel of a grid.
import math
import numpy as np
from numba import njit, prange
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from k1 import vnoise, ROT


@njit(parallel=True, cache=True)
def fbm_grid(out, x0, y0, sx, sy, z, octaves, gain, lac, ridged_from, warp):
    """out[h, w] = fBm at (x0 + j*sx, y0 + i*sy, z); octaves rotated; optional domain warp; ridges from an octave on"""
    h, w = out.shape
    r0, r1, r2, r3, r4, r5, r6, r7, r8 = ROT
    for i in prange(h):
        for j in range(w):
            x = x0 + j * sx; y = y0 + i * sy; zz = z
            if warp > 0:
                wx = vnoise(x * 0.5 + 5.2, y * 0.5, zz * 0.5) - 0.5
                wy = vnoise(x * 0.5, y * 0.5 + 1.3, zz * 0.5 + 7.1) - 0.5
                x += warp * wx; y += warp * wy
            f = 0.0; amp = 1.0; norm = 0.0; fr = 1.0
            px, py, pz = x, y, zz
            for o in range(octaves):
                px, py, pz = r0 * px + r1 * py + r2 * pz, r3 * px + r4 * py + r5 * pz, r6 * px + r7 * py + r8 * pz
                n = vnoise(px * fr + 3.7 * o, py * fr, pz * fr)
                if o >= ridged_from:
                    n = 1.0 - abs(2.0 * n - 1.0)
                f += amp * n; norm += amp; amp *= gain; fr *= lac
            out[i, j] = f / norm
