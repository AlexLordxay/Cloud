# The star sky behind the neutron star (equirectangular 4096 × 2048): ~60 000 stars (more along the Milky Way),
# the Milky Way's glow with dust lanes, a little colour. -> work/neutron_spoon/sky.jpg
import os, numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
W, H = 4096, 2048
rng = np.random.default_rng(11)
lon = (np.arange(W) + 0.5) / W * 2 * np.pi - np.pi
lat = np.pi / 2 - (np.arange(H) + 0.5) / H * np.pi
LON, LAT = np.meshgrid(lon, lat)
v = np.stack([np.cos(LAT) * np.sin(LON), np.sin(LAT), -np.cos(LAT) * np.cos(LON)], -1)
g = np.array([0.35, 0.80, 0.48]); g /= np.linalg.norm(g)          # the galactic pole (tilted band)
b = np.arcsin(np.clip(v @ g, -1, 1))
def noise(scale, seed):
    r = np.random.default_rng(seed).standard_normal((H // scale + 2, W // scale + 2))
    r = gaussian_filter(r, 1.2, mode='wrap')
    return np.asarray(Image.fromarray(r.astype(np.float32)).resize((W, H), Image.BICUBIC))
n1, n2, n3 = noise(64, 1), noise(16, 2), noise(6, 3)
band = np.exp(-(b / np.radians(11)) ** 2) * (0.75 + 0.25 * np.tanh(n1)) + 0.35 * np.exp(-(b / np.radians(28)) ** 2)
dust = np.clip(0.5 + 0.6 * n2 + 0.3 * n3, 0, 1) * np.exp(-(b / np.radians(5)) ** 2)
glow = band * (1 - 0.75 * dust)
img = np.zeros((H, W, 3), np.float32)
img += glow[..., None] * np.array([0.050, 0.046, 0.042]) * (1 + 0.25 * np.tanh(n3))[..., None]
# stars: uniform + along the band
N = 70000
z = rng.uniform(-1, 1, N); ph = rng.uniform(-np.pi, np.pi, N)
pts = np.stack([np.sqrt(1 - z * z) * np.cos(ph), z, np.sqrt(1 - z * z) * np.sin(ph)], -1)
bb = np.arcsin(pts @ g)
keep = rng.uniform(0, 1, N) < 0.35 + 0.65 * np.exp(-(bb / np.radians(14)) ** 2)
pts = pts[keep]
mag = rng.pareto(1.6, len(pts)) * 0.02
la = np.arcsin(pts[:, 1]); lo = np.arctan2(pts[:, 0], -pts[:, 2])
x = ((lo + np.pi) / (2 * np.pi) * W).astype(int) % W; y = ((np.pi / 2 - la) / np.pi * H).astype(int).clip(0, H - 1)
temp = rng.uniform(0, 1, len(pts))
col = np.where(temp[:, None] < 0.2, [1.0, 0.78, 0.6], np.where(temp[:, None] < 0.75, [1.0, 0.96, 0.92], [0.75, 0.85, 1.0]))
pt = np.zeros((H, W, 3), np.float32)
np.add.at(pt, (y, x), col * np.minimum(mag, 3.0)[:, None])
img += gaussian_filter(pt, (0.6, 0.6, 0)) * 3.4 + gaussian_filter(pt, (2.5, 2.5, 0)) * 0.25
out = np.clip(img, 0, 1) ** (1 / 2.2)
Image.fromarray((out * 255).astype(np.uint8)).save(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'work', 'neutron_spoon', 'sky.jpg'), quality=94)
print('sky.jpg')
