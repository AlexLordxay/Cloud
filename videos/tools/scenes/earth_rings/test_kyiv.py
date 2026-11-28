import math, os, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
import render as RD
WK = os.path.join(TOOLS, 'work', 'earth_rings')
LAT0, LON0 = 50.43, 30.56
ldc = lambda f: np.ascontiguousarray(np.asarray(Image.open(os.path.join(WK, f)).convert('RGB')).astype(np.float32) / 255)
ldg = lambda f: np.ascontiguousarray(np.asarray(Image.open(os.path.join(WK, f)).convert('L')).astype(np.float32) / 255)
CI, CO = ldc('inner_col.png'), ldc('outer_col.png')
WI, WO = ldg('inner_w.png'), ldg('outer_w.png'); LI, LO = ldg('inner_l.png'), ldg('outer_l.png')
ZI = np.ascontiguousarray(np.load(os.path.join(WK, 'inner_z.npy')).astype(np.float32))
ZO = np.ascontiguousarray(np.load(os.path.join(WK, 'outer_z.npy')).astype(np.float32))
MO = ldg('monument.png')
SK = np.ascontiguousarray(np.asarray(Image.open(os.path.join(TOOLS, 'work', 'neutron_spoon', 'sky.jpg')).convert('RGB')).astype(np.float32) / 255)
def nrm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
la, lo = math.radians(LAT0), math.radians(LON0)
E = np.array([-math.sin(lo), math.cos(lo), 0]); N = np.array([-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)])
U = np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])
B = np.ascontiguousarray(np.stack([E, N, U], 1))
def sunv(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
mx, my = 0.227, -0.389
mz = float(RD.ground_h(ZI, ZO, mx, my))
def shot(name, cam, tgt, sun_az, sun_el, fov=55, W=720, H=1280, ss=1, vis=22.0):
    cam = np.array(cam, float)
    fw = nrm(np.subtract(tgt, cam)); rt = nrm(np.cross(fw, [0, 0, 1])); up = np.cross(rt, fw)
    sl = sunv(sun_az, sun_el); se = B @ sl
    P = (RD.R + cam[2]) * U + E * cam[0] + N * cam[1]
    out = np.zeros((H, W, 3), np.float32)
    t0 = time.time()
    RD.kyiv(CI, CO, ZI, ZO, WI, WO, LI, LO, SK, cam, fw, rt, up, math.radians(fov), B, P, sl, se, 1.0, out, ss, 0.0, vis,
            np.array([mx, my, mz, 0.102, 0.044]), MO)
    Image.fromarray((RD.tonemap(RD.bloom(out)) * 255).astype(np.uint8)).save(os.path.join(WK, f'test_{name}.jpg'), quality=92)
    print(name, round(time.time() - t0, 1), 's', flush=True)
if __name__ == '__main__':
    cam = [1.4, 6.5, 0.90]
    tgt = [0.2, -6.0, 0.25]
    shot('dusk', cam, tgt, 305, -4)
    shot('night', cam, tgt, 0, -16)
