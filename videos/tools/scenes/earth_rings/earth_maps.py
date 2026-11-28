# The Earth 465 million years ago for «У Землі колись могли бути кільця», at 8192 × 4096 (twice earth_history's maps):
# the PALEOMAP PaleoDEM (Scotese & Wright 2018, CC BY 4.0) painted by chicxulub/maps.py's paint() — bare rock before
# land plants — with the seas recoloured (the shelves of the epicontinental seas a muted teal, not a flat cyan sheet),
# plus the land's slopes for the shading and a sea mask.
#   -> work/earth_rings/ep465_col.jpg, ep465_rel.png (R, G = slopes east, north; 128 = flat), ep465_sea.png
import os, sys, io, re, zipfile
import numpy as np, h5py
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(TOOLS, 'scenes', 'chicxulub'))
from maps import paint, field, fbm, ramp
Image.MAX_IMAGE_PIXELS = None
ZIP = os.path.join(TOOLS, 'work', 'chicxulub', 'dl', 'dem6.zip'); WK = os.path.join(TOOLS, 'work', 'earth_rings')
W, H = 8192, 4096
with zipfile.ZipFile(ZIP) as z:
    name = [n for n in z.namelist() if '__MACOSX' not in n and re.search(r'_465Ma\.nc$', n)][0]
    with h5py.File(io.BytesIO(z.read(name)), 'r') as f:
        dem = f['z'][...][:, :-1].astype(np.float32)
col, rel, land = paint(dem, W, H, ice=0.0)
# bare ground (no land plants yet): ochre, grey and rust rock and sand, mottled
n = field(W, H, lambda P, la: fbm(P, 30, 6, 77))[..., None]
n2 = field(W, H, lambda P, la: fbm(P, 9, 4, 78))[..., None]
n3 = field(W, H, lambda P, la: fbm(P, 90, 6, 79))[..., None]
bare = np.array([150, 124, 100]) * (0.80 + 0.32 * n) + (n2 - 0.5) * np.array([46, 30, 12]) + (n3 - 0.5) * np.array([30, 26, 22])
lum = col.mean(-1, keepdims=True)
bare = bare * (0.72 + 0.55 * np.clip(lum / 120, 0, 1))
col = np.where(land[..., None], bare, col)
# the seas, by depth (from the same DEM, upsampled as paint() does: read back from the colour's darkness is unreliable)
from scipy import ndimage
zz = ndimage.zoom(ndimage.gaussian_filter(dem, 0.8, mode='wrap'), (H / dem.shape[0], W / dem.shape[1]), order=1)
d = np.clip(-zz, 0, None)
cs = ramp(d, [0, 30, 90, 200, 500, 1500, 4000],
          [(40, 96, 104), (30, 82, 100), (22, 66, 92), (16, 52, 84), (11, 38, 72), (8, 27, 58), (6, 20, 47)])
cs = cs * (1 + 0.06 * field(W, H, lambda P, la: fbm(P, 14, 5, 41)))[..., None]
sea = ~land
col = np.where(sea[..., None], cs, col)
os.makedirs(WK, exist_ok=True)
Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(WK, 'ep465_col.jpg'), quality=95)
Image.fromarray(np.clip(rel, 0, 255).astype(np.uint8)).save(os.path.join(WK, 'ep465_rel.png'))
Image.fromarray((sea * 255).astype(np.uint8)).save(os.path.join(WK, 'ep465_sea.png'))
print('ok', col.shape)
