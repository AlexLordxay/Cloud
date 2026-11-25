# quick test frames for the Europa renderers: python3 scenes/europa_imagine/still.py <name> ...
import math, os, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import render as RD
W_ = os.path.join(TOOLS, 'work', 'europa_imagine')
ld = lambda f: np.ascontiguousarray(np.asarray(Image.open(f).convert('RGB')).astype(np.float32) / 255)
Z = np.load(os.path.join(W_, 'hf.npy')) / 1000.0; A = np.load(os.path.join(W_, 'alb.npy'))
SK = ld(os.path.join(TOOLS, 'work', 'neutron_spoon', 'sky.jpg')); JT = ld(os.path.join(TOOLS, '..', '..', 'planetarium', 'textures', 'jupiter.jpg'))
GT = ld(os.path.join(W_, 'globe.jpg')); MT = ld(os.path.join(TOOLS, '..', '..', 'planetarium', 'textures', 'moon.jpg'))
def nrm(v): v = np.asarray(v, np.float64); return v / np.linalg.norm(v)
def look(cam, tgt, upv=(0, 0, 1)):
    fw = nrm(np.subtract(tgt, cam)); rt = nrm(np.cross(fw, upv)); up = np.cross(rt, fw); return fw, rt, up
sun = nrm([-0.9, -0.2, 0.33]); jd = nrm([0.35, 0.85, 0.42]); jax = nrm(np.cross(np.cross(jd, [0, 0.3, 1]), jd)) * -1
jang = math.atan(RD.J_R / RD.J_D)
out = np.zeros((1280, 720, 3), np.float32)
def save(name):
    Image.fromarray((RD.tonemap(RD.bloom(out)) * 255).astype(np.uint8)).save(os.path.join(W_, f'st_{name}.jpg'), quality=92)
for name in sys.argv[1:]:
    t0 = time.time()
    if name == 'fly':
        cam = np.array([-30.0, -40.0, 4.0]); fw, rt, up = look(cam, [0, 0, 0.0])
        RD.terrain(Z, A, 200 / 4096, 100.0, SK, JT, cam, fw, rt, up, math.radians(55), sun, jd, jang, jax, 0.0, False, 25.0, 150.0, 1.0, out, 1, float(Z.max()))
    elif name == 'ground':
        cam = np.array([6.02, 15.12, 0.0]); cam[2] = 0.06 + float(Z[int((100 - cam[1]) / (200 / 4096)), int((cam[0] + 100) / (200 / 4096))]); fw, rt, up = look(cam, cam + np.array([0.55, 1.0, 0.17]))
        RD.terrain(Z, A, 200 / 4096, 100.0, SK, JT, cam, fw, rt, up, math.radians(60), sun, jd, jang, jax, 0.0, False, 25.0, 150.0, 1.0, out, 1, float(Z.max()))
    elif name == 'slab':
        cam = np.array([-260.0, -330.0, 210.0]); fw, rt, up = look(cam, [0, 0, -70.0])
        RD.terrain(Z, A, 200 / 4096, 100.0, SK, JT, cam, fw, rt, up, math.radians(50), sun, jd, jang, jax, 0.0, True, 25.0, 150.0, 1.0, out, 1, float(Z.max()))
    elif name.startswith('globe'):
        az, el, dist, cutk = {'globe': (-2.2, 0.42, 9000, 1.0), 'globe2': (-2.0, 0.25, 8200, 0.0), 'globe3': (-2.5, 0.55, 7600, 1.0)}[name]
        cam = np.array([dist * math.cos(el) * math.cos(az), dist * math.cos(el) * math.sin(az), dist * math.sin(el)]); fw, rt, up = look(cam, [0, 0, 0])
        cdir = np.array([math.cos(az + 0.45), math.sin(az + 0.45)])
        jdd = nrm(fw + 0.30 * rt + 0.22 * up); sn = nrm(rt * 0.9 - fw * 0.35 + up * 0.25)
        RD.space(GT, MT, SK, JT, cam, fw, rt, up, math.radians(36), sn, jdd, jang, nrm([0, 0, 1.0]), 0.0, 0.0, np.array([0, 0, 0, 0.0]), cutk, cdir, 1.0, out, 2)
    print(name, round(time.time() - t0, 1), 's'); save(name)
