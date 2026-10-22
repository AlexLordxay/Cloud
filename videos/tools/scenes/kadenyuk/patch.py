# A detailed day map of the region under the orbit (Red Sea → Ukraine): level-3 chunks of the site's Blue Marble
# pyramid (16 × 8 chunks of 2048 px, ≈1.2 km/px), stitched into work/kadenyuk/patch.jpg. Its box (lon/lat) is printed.
import os
from PIL import Image
T = os.path.join(os.path.dirname(__file__), '../../../../planetarium/textures/earth/3')
OUT = os.path.join(os.path.dirname(__file__), '../../work/kadenyuk/patch.jpg')
X, Y = range(8, 11), range(1, 4)             # lon 0..67.5 E, lat 67.5..0 N
im = Image.new('RGB', (2048 * len(X), 2048 * len(Y)))
for i, x in enumerate(X):
    for j, y in enumerate(Y):
        im.paste(Image.open(f'{T}/{x}_{y}.jpg').convert('RGB'), (2048 * i, 2048 * j))
im.save(OUT, quality=92)
print(OUT, 'lon', X[0] * 22.5 - 180, (X[-1] + 1) * 22.5 - 180, 'lat', 90 - (Y[-1] + 1) * 22.5, 90 - Y[0] * 22.5)
