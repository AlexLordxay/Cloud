# Lays the recorded worlds (work/hoverla/frames, drawn on black) over the author's photo of Hoverla at dusk.
# The worlds are added as light, as the real Moon shows in a dusk sky, and dimmed where thin clouds cross them; the sky
# darkens as the dusk deepens and stars come out; the mountains stay in front. During the Sun the land warms up.
#   python3 scenes/hoverla/post.py      (run by make.sh after rec.js; rewrites the frames at 1080×1920)
import glob, os, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, '..', '..', 'work', 'hoverla', 'frames')
FPS, W, H = 30, 1080, 1920
sys.path.insert(0, HERE)
from captions import SUN_A, SUN_B

plate = np.asarray(Image.open(os.path.join(HERE, 'plate.jpg')).convert('RGB'), np.float32) / 255
mask = np.asarray(Image.open(os.path.join(HERE, 'skymask.png')), np.float32)[..., None] / 255
# thin clouds: what stands out of the smooth sky gradient (a heavy blur of the sky)
lum = plate.mean(2)
smooth = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40)), np.float32) / 255
cloud = np.clip((np.abs(lum - smooth) - 0.012) * 9, 0, 1)[..., None] * mask
# stars: fixed random points, fainter towards the horizon, never on the land
rng = np.random.default_rng(7)
stars = np.zeros((H, W), np.float32)
n = 900
ys, xs = rng.integers(0, 1000, n), rng.integers(0, W, n)
stars[ys, xs] = rng.uniform(0.15, 1.0, n) ** 2.2
stars = np.asarray(Image.fromarray((stars * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 * 3.5
stars *= np.clip(1 - np.arange(H)[:, None] / 950, 0, 1) ** 0.7
stars = (stars[..., None] * np.array([0.9, 0.95, 1.0], np.float32)) * mask


def sm(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def frame(path):
    i = int(os.path.basename(path)[2:7]); t = i / FPS
    w = np.asarray(Image.open(path).convert('RGB').resize((W, H), Image.BICUBIC), np.float32) / 255
    dusk = sm((t - 3.0) / 31.0)                         # 0 at the start .. 1 when Jupiter has been up a while
    sun = min(sm((t - SUN_A + 0.8) / 1.6), 1 - sm((t - SUN_B + 1.5) / 3.0))
    sky = plate * (1 - 0.5 * dusk) + stars * dusk * (1 - sun) + 0.78 * w * (1 - 0.75 * cloud)
    # the Sun is far brighter than the dusk: over the sky it takes its own colour rather than adding to it
    sky = sky * (1 - sun) + w * 1.25 * sun
    land = plate * (1 - 0.25 * dusk) * (1 + sun * np.array([0.55, 0.35, 0.12], np.float32))
    out = sky * mask + land * (1 - mask)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path, quality=93)


if __name__ == '__main__':
    files = sorted(glob.glob(os.path.join(FRAMES, 'f_*.jpg')))
    with Pool() as p: p.map(frame, files, chunksize=8)
    print('photo laid under', len(files), 'frames')
