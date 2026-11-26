# Summer satellite map -> the same place under snow (for the Kyiv shots of «Чому взимку холодно»). Open ground (fields,
# meadows, sand, roofs) turns white; forest stays dark (snow under the trees, dark crowns), the city grey with dark streets;
# the Dnipro freezes at the banks (grey ice) and keeps a dark channel. Input / output: uint8 RGB arrays.
import numpy as np
from scipy import ndimage as nd

def winterize(a, seed=3):
    x = a.astype(np.float32) / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    L = 0.3 * r + 0.55 * g + 0.15 * b
    Lsm = nd.gaussian_filter(L, 2.0); bg = nd.gaussian_filter(b - g, 2.0)
    # water: bluer than green and dark; drop small specks, fill the river
    water = (bg > 0.010) & (Lsm < 0.20)
    lab, nlab = nd.label(water); sizes = nd.sum(water, lab, range(1, nlab + 1))
    water = np.isin(lab, 1 + np.where(sizes > 400)[0])
    water = nd.binary_closing(water, iterations=2)
    water_s = nd.gaussian_filter(water.astype(np.float32), 0.8)
    Ls = nd.gaussian_filter(L, 3.0)
    tex = np.sqrt(nd.gaussian_filter((L - Ls) ** 2, 4.0))
    Lf = nd.median_filter(L, 9); Lf = nd.gaussian_filter(Lf, 3.0); bgf = nd.gaussian_filter(b - g, 5.0)
    forest = np.clip((0.200 - Lf) / 0.025, 0, 1) * np.clip((0.012 - bgf) / 0.01, 0, 1) * (1 - water_s)
    forest = nd.gaussian_filter(forest, 1.5)
    urban = np.clip((tex - 0.035) / 0.03, 0, 1) * (1 - forest) * (1 - water_s)
    openl = np.clip(1 - forest - urban - water_s, 0, 1)
    rng = np.random.default_rng(seed)
    n = nd.gaussian_filter(rng.standard_normal(L.shape).astype(np.float32), 5.0); n = n / (np.abs(n).max() + 1e-6)
    fine = rng.random(L.shape).astype(np.float32)
    snow = np.array([0.90, 0.93, 0.98], np.float32)
    # open land: white, with the field pattern faintly left (edges, tracks, shelter belts darker)
    o = snow * np.clip(0.93 + 1.1 * (L - Ls) - 0.6 * np.maximum(0, Ls - L)[...] + 0.03 * n, 0.55, 1.05)[..., None]
    # forest: dark crowns, snow showing between them
    fk = 0.29 + 0.7 * np.clip(nd.gaussian_filter(L, 1.2) - Ls, -0.06, 0.06) + 0.05 * n + 0.08 * (fine - 0.5) * 0.6
    f = np.stack([fk * 0.92, fk * 0.97, fk * 1.02], -1)
    # city: snowy roofs and yards, dark streets; colour drained
    u = np.clip(0.22 + 1.9 * L, 0, 1)[..., None] * np.array([0.97, 0.99, 1.03], np.float32)
    # river: ice along the banks, a dark open channel in the middle
    dist = nd.distance_transform_edt(water)
    ice = np.clip(1 - (dist - 2) / 10.0, 0, 1) * (0.7 + 0.3 * n)
    w = (np.array([0.09, 0.11, 0.14], np.float32) * (1 - ice[..., None]) + np.array([0.60, 0.65, 0.71], np.float32) * ice[..., None])
    out = o * openl[..., None] + f * forest[..., None] + u * urban[..., None] + w * water_s[..., None]
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)

if __name__ == '__main__':
    import os, sys
    from PIL import Image
    W = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'work', 'winter_sun')
    a = np.load(os.path.join(W, 'kyiv.npy'))
    wv = winterize(a)
    np.save(os.path.join(W, 'kyiv_w.npy'), wv)
    Image.fromarray(np.concatenate([a, wv], 1)).resize((1600, 800)).save(os.path.join(W, 'kyiv_sw.jpg'), quality=88)
    b = np.asarray(Image.open(os.path.join(W, 'kyiv75.jpg')).convert('RGB'))
    np.save(os.path.join(W, 'kyiv75.npy'), b)
    np.save(os.path.join(W, 'kyiv75_w.npy'), winterize(b))
    print('ok')
