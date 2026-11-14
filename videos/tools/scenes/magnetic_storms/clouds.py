# A 4096x2048 cloud map for the close Earth views: the site's 1024x512 map upscaled (Lanczos) and given fine fBm detail
# where there are clouds, so the moonlit cloud deck has no blocky texels.  -> work/magnetic_storms/clouds4k.npy (float16)
import os, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.abspath(os.path.join(TOOLS, '../../planetarium/textures/earth_clouds.png'))
OUT = os.path.join(TOOLS, 'work', 'magnetic_storms', 'clouds4k.npy')
W, H = 4096, 2048

def fbm(seed):
    g = np.random.default_rng(seed); acc = np.zeros((H, W), np.float32); tot = 0
    for s, a in ((256, 0.35), (128, 0.25), (64, 0.18), (32, 0.12), (16, 0.07), (8, 0.03)):
        z = g.random((H // s + 3, W // s + 3)).astype(np.float32)
        z[:, -3:] = z[:, :3]                                   # wraps in longitude
        up = np.asarray(Image.fromarray((z * 255).astype(np.uint8)).resize(((W // s + 3) * s, (H // s + 3) * s), Image.BICUBIC), np.float32) / 255
        acc += up[s:H + s, s:W + s] * a; tot += a
    return acc / tot

if __name__ == '__main__':
    from PIL import ImageFilter
    base = np.asarray(Image.open(SRC).convert('L').filter(ImageFilter.GaussianBlur(1.6)).resize((W, H), Image.BICUBIC), np.float32) / 255
    d = fbm(7)
    c = np.clip((base * 1.35 - 0.12) * (0.45 + 1.1 * d) + (d - 0.5) * 0.25 * base, 0, 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.save(OUT, c.astype(np.float16)); print('clouds', c.shape, c.mean())
