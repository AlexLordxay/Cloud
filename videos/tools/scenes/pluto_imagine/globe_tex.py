# The whole-Pluto colour map for world3d.js (8192 × 4096, equirectangular, longitude 0…360° east left → right, as the
# USGS mosaics): detail from the New Horizons global mosaic (work/pluto_imagine/mosaic8.tif, 300 m/px, downloaded once
# from planetarymaps.usgs.gov), colour from the site's map (planetarium/textures/pluto.jpg, longitude 0 in its middle),
# and where the flyby saw little (the far side: nodata or blurry), the site's map alone.
#   python3 scenes/pluto_imagine/globe_tex.py -> work/pluto_imagine/globe.jpg
import os
import numpy as np, tifffile
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(TOOLS, 'work', 'pluto_imagine')
W, H = 8192, 4096
m = tifffile.imread(os.path.join(WORK, 'mosaic8.tif'))
print('mosaic', m.shape, m.dtype, flush=True)
mim = Image.fromarray(m)
valid = Image.fromarray(((m > 0) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
lum = np.asarray(mim.resize((W, H), Image.LANCZOS), np.float32)
ok = np.asarray(valid, np.float32) / 255
site = np.asarray(Image.open(os.path.join(TOOLS, '..', '..', 'planetarium', 'textures', 'pluto.jpg')).convert('RGB').resize((W, H), Image.BICUBIC), np.float32)
site = np.roll(site, W // 2, axis=1)                         # its longitude 0 sits in the middle; ours at the left edge
slum = site.mean(axis=2)
chroma = site / np.maximum(slum, 1)[..., None]
chroma = np.dstack([np.asarray(Image.fromarray(np.clip(chroma[..., k] * 100, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32) / 100 for k in range(3)])
# the mosaic's brightness matched to the site map's broad brightness (the mosaic's photometry varies across the flyby)
blur = lambda a, r: np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)
lb = blur(np.where(ok > 0.5, lum, slum), 40)
detail = np.where(ok > 0.5, lum / np.maximum(lb, 1), 1.0)
detail = np.clip(detail, 0.4, 1.8)
L = blur(slum, 40) * (1 + (detail - 1) * 0.9)
L = slum * (1 - ok) + L * ok
col = chroma * L[..., None]
Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(WORK, 'globe.jpg'), quality=93)
Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).resize((2048, 1024), Image.LANCZOS).save(os.path.join(WORK, 'globe_small.jpg'), quality=90)
print('globe.jpg written', flush=True)
