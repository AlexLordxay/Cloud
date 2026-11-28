import math, os, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE)
import render as RD
WK = os.path.join(TOOLS, 'work', 'earth_rings')
ET = np.ascontiguousarray(np.asarray(Image.open(os.path.join(TOOLS, 'work', 'earth_history', 'paleo', 'ep_465.png')).convert('RGB')).astype(np.float32) / 255)
SK = np.ascontiguousarray(np.asarray(Image.open(os.path.join(TOOLS, 'work', 'neutron_spoon', 'sky.jpg')).convert('RGB')).astype(np.float32) / 255)
def nrm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def shot(name, cam, tgt, sun, rot=0.0, ringk=1.0, fov=40, W=720, H=1280, ice=0.0):
    cam = np.array(cam, float); fw = nrm(np.subtract(tgt, cam)); rt = nrm(np.cross(fw, [0, 0, 1])); up = np.cross(rt, fw)
    out = np.zeros((H, W, 3), np.float32); dep = np.zeros((H, W), np.float32)
    t0 = time.time()
    RD.space(ET, SK, cam, fw, rt, up, math.radians(fov), nrm(sun), rot, ringk, 1.0, out, dep, 1, 0.34, ice, 0.0)
    Image.fromarray((RD.tonemap(RD.bloom(out)) * 255).astype(np.uint8)).save(os.path.join(WK, f'test_{name}.jpg'), quality=92)
    print(name, round(time.time() - t0, 1), 's', flush=True)
if __name__ == '__main__':
    d = 60000.0; el = math.radians(18); az = math.radians(-30)
    cam = [d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)]
    shot('ring', [d * 0.35, -d * 0.9, -d * 0.30], [0, 0, 0], [-0.6, -0.55, -0.45], rot=0.4)
    shot('ring2', [d * 0.2, -d, d * 0.10], [0, 0, 0], [0.7, 0.3, 0.35], rot=2.0, fov=30)
