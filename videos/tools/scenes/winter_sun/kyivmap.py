# Kyiv round Maidan for the sky-dome shots of «Чому взимку холодно»: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0; contains
# modified Copernicus Sentinel data 2016), Web-Mercator tiles z13 -> one square image in local km (x east, y north).
#   python3 scenes/winter_sun/kyivmap.py   (tiles in work/winter_sun/tiles13)  -> work/winter_sun/kyiv.npy (+ kyiv.jpg)
import math, os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, '..', '..', 'work', 'winter_sun')
LAT0, LON0 = 50.4501, 30.5234
HALF, N, Z = 12.0, 2048, 13
X0, X1, Y0, Y1 = 4786, 4794, 2758, 2766
mos = np.zeros(((Y1 - Y0 + 1) * 256, (X1 - X0 + 1) * 256, 3), np.uint8)
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        mos[(y - Y0) * 256:(y - Y0 + 1) * 256, (x - X0) * 256:(x - X0 + 1) * 256] = np.asarray(Image.open(os.path.join(W, 'tiles13', f'{x}_{y}.jpg')).convert('RGB'))
km = (np.arange(N) + 0.5) / N * 2 * HALF - HALF
gx, gy = np.meshgrid(km, -km)
lat = LAT0 + gy / 111.2
lon = LON0 + gx / (111.32 * math.cos(math.radians(LAT0)))
n = 2 ** Z
px = ((lon + 180) / 360 * n - X0) * 256
py = ((1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / math.pi) / 2 * n - Y0) * 256
x0 = np.clip(np.floor(px).astype(int), 0, mos.shape[1] - 2); y0 = np.clip(np.floor(py).astype(int), 0, mos.shape[0] - 2)
fx = (px - x0)[..., None]; fy = (py - y0)[..., None]
m = mos.astype(np.float32)
out = (m[y0, x0] * (1 - fx) + m[y0, x0 + 1] * fx) * (1 - fy) + (m[y0 + 1, x0] * (1 - fx) + m[y0 + 1, x0 + 1] * fx) * fy
out = np.clip(out, 0, 255).astype(np.uint8)
np.save(os.path.join(W, 'kyiv.npy'), out)
Image.fromarray(out).save(os.path.join(W, 'kyiv.jpg'), quality=90)
print('kyiv', out.shape)
