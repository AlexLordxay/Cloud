# A zodiac video: draws every frame from sky.py (no browser) -> work/<scene>/frames/f_%05d.jpg, 720x1280.
# Skips frames that already exist, so a stopped run carries on.   python3 frames.py [workers]
import json, math, os, sys
from multiprocessing import Pool
here = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(here))
sys.path[:0] = [TOOLS, here]
from PIL import ImageDraw
from sky import Sky, ecl
import timeline as T

W, H = 720, 1280
OUT = os.path.join(TOOLS, 'work', os.path.basename(here), 'frames')
DUR = json.load(open(os.path.join(here, 'scene.json')))['duration']
_sky = None

def draw(i):
    global _sky
    p = os.path.join(OUT, f'f_{i:05d}.jpg')
    if os.path.exists(p): return
    if _sky is None: _sky = Sky(W, H, 2)
    t = i / 30
    v = T.view(t)
    img = _sky.render(v)
    k, off = T.sectors(t)
    if k > 0.01:
        # the Babylonian signs: a border every 30° across the ecliptic, the sign's name inside the ring
        P = _sky.proj(v['centre'], v['scale'], v['roll'])
        lay = img.convert('RGBA'); ov = lay.copy(); ov.putalpha(0); d = ImageDraw.Draw(ov)
        f = _sky.font(11)
        for j in range(12):
            lam = off + 30 * j
            x, y, ok = P(__import__('numpy').array([ecl(lam, b) for b in range(-22, 23, 2)]))
            d.line(list(zip((x / 2).tolist(), (y / 2).tolist())), fill=(255, 196, 120, int(230 * k)), width=3)
            x, y, ok = P(ecl(lam + 15, 24))
            d.text((float(x[0]) / 2, float(y[0]) / 2), T.SIGNS[j], font=f, anchor='mm', fill=(255, 214, 160, int(255 * k)))
        lay.alpha_composite(ov); img = lay.convert('RGB')
    if hasattr(T, 'overlay'):
        # the scene's own drawing on the sky (markers, meteors), with the projection of this frame
        img = T.overlay(img, _sky.proj(v['centre'], v['scale'], v['roll']), t, _sky)
    img.save(p, quality=93)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * 30)
    todo = [i for i in range(n) if not os.path.exists(os.path.join(OUT, f'f_{i:05d}.jpg'))]
    if len(sys.argv) > 2: todo = [int(a) for a in sys.argv[2:]]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()) as pool:
        for c, _ in enumerate(pool.imap_unordered(draw, todo, chunksize=4)):
            if c % 100 == 0: print('frame', c, '/', len(todo), flush=True)
    print('frames done', n)
