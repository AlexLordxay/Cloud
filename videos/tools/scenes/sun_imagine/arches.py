# Coronal loops and a prominence as point clouds (solar radii, body frame), for sunk.k_splat.
#   loops: an arcade of magnetic loops over the active region (each of a few strands, with bright knots that travel)
#   prominence: a big arch of cool plasma — many fluffy, vertical threads, slowly draining
import math
import numpy as np

def _ll(lat, lon):
    a, b = math.radians(lat), math.radians(lon)
    return np.array([math.cos(a) * math.cos(b), math.cos(a) * math.sin(b), math.sin(a)])

def _slerp(A, B, s):
    om = math.acos(np.clip(A @ B, -1, 1))
    so = math.sin(om)
    return (np.sin((1 - s) * om)[:, None] * A + np.sin(s * om)[:, None] * B) / so

def arcade(lat, lon, n=34, span=0.09, length=0.30, hmin=0.025, hmax=0.11, seed=3, bearing=0.0):
    """footpoint pairs straddling a polarity line through (lat, lon) running east-west; returns list of loops
    (A, B, h, width, brightness, phase)"""
    rng = np.random.default_rng(seed)
    C = _ll(lat, lon)
    east = np.cross([0, 0, 1.0], C); east /= np.linalg.norm(east); north = np.cross(C, east)
    cb, sb = math.cos(bearing), math.sin(bearing)
    east, north = east * cb + north * sb, -east * sb + north * cb
    loops = []
    for i in range(n):
        u = (i / (n - 1) - 0.5) * length + rng.normal(0, 0.01)
        tilt = rng.normal(0.25, 0.25)
        half = span * (0.45 + 0.9 * rng.random())
        a = C + east * (u - tilt * half) + north * half
        b = C + east * (u + tilt * half) - north * half
        a /= np.linalg.norm(a); b /= np.linalg.norm(b)
        h = hmin + (hmax - hmin) * (half / (span * 1.35)) ** 1.2 * (0.7 + 0.6 * rng.random())
        loops.append((a, b, h, 0.0035 + 0.004 * rng.random(), 0.5 + 0.8 * rng.random(), rng.random() * 6.28))
    return loops

def loop_points(loops, t, colour=(1.0, 0.78, 0.42), k=1.0, strands=4, seed=5):
    rng = np.random.default_rng(seed)
    P, C, Rr = [], [], []
    for (A, B, h, w, br, ph) in loops:
        L = math.acos(np.clip(A @ B, -1, 1)) + 2 * h
        m = max(24, int(L / (w * 0.30)))
        s = np.linspace(0, 1, m)
        base = _slerp(A, B, s)
        nrm_ = np.cross(A, B); nrm_ /= np.linalg.norm(nrm_)
        for q in range(strands):
            off = rng.normal(0, w * 0.9)
            r = 1.0 + h * np.sin(np.pi * s) + rng.normal(0, w * 0.4)
            p = base * r[:, None] + nrm_ * off * (0.3 + np.sin(np.pi * s))[:, None]
            # brightness: a slow travelling wave of knots, brighter low down, a gentle flicker
            knots = 0.55 + 0.45 * np.sin(s * 14.0 - t * 1.6 + ph + q * 1.3) ** 2
            foot = 0.6 + 0.4 * np.sin(np.pi * s) ** 0.3
            b_ = br * knots * foot * k * (0.75 + 0.25 * math.sin(t * 0.9 + ph * 3 + q))
            P.append(p); C.append(np.outer(b_, colour)); Rr.append(np.full(m, w * (0.30 + 0.15 * rng.random())))
    return np.concatenate(P), np.concatenate(C), np.concatenate(Rr)

def prominence(lat, lon, t, width=0.34, h=0.16, k=1.0, n=200000, seed=11, colour=(1.0, 0.36, 0.30), bearing=0.0):
    """a hedgerow-and-arch prominence: an arch between two feet, with vertical threads; points drift down slowly"""
    rng = np.random.default_rng(seed)
    C0 = _ll(lat, lon)
    east = np.cross([0, 0, 1.0], C0); east /= np.linalg.norm(east); north = np.cross(C0, east)
    cb, sb = math.cos(bearing), math.sin(bearing)
    east, north = east * cb + north * sb, -east * sb + north * cb
    A = C0 - east * width / 2 + north * 0.03; B = C0 + east * width / 2 - north * 0.03
    A /= np.linalg.norm(A); B /= np.linalg.norm(B)
    s = rng.random(n)
    base = _slerp(A, B, s)
    nrm_ = np.cross(A, B); nrm_ /= np.linalg.norm(nrm_)
    # the arch top (with a lumpy profile) and threads hanging below it
    prof = h * (np.sin(np.pi * s) ** 0.8) * (0.85 + 0.15 * np.sin(s * 9.0 + 1.3))
    hang = rng.random(n) ** 0.6                              # 0 = at the top of the arch, 1 = down at the surface
    drift = (t * 0.012 + rng.random(n)) % 1.0                 # the plasma drains down along the threads
    hh = prof * (1 - 0.92 * ((hang + drift * 0.15) % 1.0)) + 0.004
    thread = np.floor(s * 220) / 220 + rng.normal(0, 0.0006, n)
    base = _slerp(A, B, np.clip(thread, 0, 1))
    off = rng.normal(0, 0.004, n) * (1 + 2 * hang)
    p = base * (1 + hh)[:, None] + nrm_ * off[:, None]
    bright = (0.35 + 0.65 * rng.random(n)) * (0.5 + 0.5 * (1 - hang)) * k * 0.45
    bright *= 0.75 + 0.25 * np.sin(s * 30 + t * 0.7) ** 2
    rad = 0.0016 + 0.0022 * rng.random(n)
    return p, np.outer(bright, colour), rad

def to_world(P, rot):
    return P @ rot.T
