# Glow round the brightest parts of a frame (the fireball, the flash), as a camera lens and the eye see them:
# the light above a threshold blurred at three widths and added back, in linear light.
#   python3 scenes/chicxulub/post.py in.jpg [out.jpg]       (one frame; in place if no out)
#   python3 scenes/chicxulub/post.py work/chicxulub/shot_X  (every frame of a shot, in place)
import os, sys, numpy as np
from multiprocessing import Pool
from PIL import Image
from scipy import ndimage


def bloom(img, thr=0.55, k=0.9):
    a = (np.asarray(img).astype(np.float32) / 255) ** 2.2
    b = np.clip(a - thr, 0, None)
    h, w = a.shape[:2]; s = w / 720
    glow = sum(wt * ndimage.gaussian_filter(b, (r * s, r * s, 0)) for r, wt in ((4, 0.6), (16, 0.5), (60, 0.45)))
    out = 1 - np.exp(-(a + glow * k) * 1.6) / 1.0
    out = np.clip(out / (1 - np.exp(-1.6)), 0, 1) ** (1 / 2.2)
    return Image.fromarray((out * 255).astype(np.uint8))


def one(job):
    src, dst = job
    bloom(Image.open(src).convert('RGB')).save(dst, quality=93)


if __name__ == '__main__':
    src = sys.argv[1]
    if os.path.isdir(src):
        fs = sorted(os.path.join(src, f) for f in os.listdir(src) if f.endswith('.jpg'))
        with Pool(4) as p: p.map(one, [(f, f) for f in fs])
    else:
        one((src, sys.argv[2] if len(sys.argv) > 2 else src))
