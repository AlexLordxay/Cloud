# Earth maps for «А ти уявляєш Сонце так?» from the site's tiles (planetarium/textures/earth, equirectangular):
#   day.npy    NASA Blue Marble, level 2 (8 x 4 tiles of 2048)          -> 16384 x 8192 RGB
#   night.npy  NASA Black Marble, level n3 (16 x 8 tiles)              -> 16384 x 8192 L
#   ua.npy     Blue Marble level 4 over Ukraine: tiles x 16–20, y 3–4  -> 10240 x 4096 RGB (lon 0…56.25 E, lat 56.25…33.75 N)
#   clouds.npy earth_clouds.png (1024 x 512) — only for the views from space
#   python3 textures.py
import os, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.abspath(os.path.join(TOOLS, '../../planetarium/textures/earth'))
TEX = os.path.abspath(os.path.join(TOOLS, '../../planetarium/textures'))
OUT = os.path.join(TOOLS, 'work', 'sun_imagine'); os.makedirs(OUT, exist_ok=True)

def build(level, xs, ys, mode, size=None):
    big = Image.new(mode, (len(xs) * 2048, len(ys) * 2048))
    for a, x in enumerate(xs):
        for b, y in enumerate(ys):
            big.paste(Image.open(os.path.join(SRC, level, f'{x}_{y}.jpg')).convert(mode), (a * 2048, b * 2048))
    return big.resize(size, Image.LANCZOS) if size and big.size != size else big

if __name__ == '__main__':
    np.save(os.path.join(OUT, 'day.npy'), np.asarray(build('2', range(8), range(4), 'RGB'), np.uint8)); print('day')
    np.save(os.path.join(OUT, 'night.npy'), np.asarray(build('n3', range(16), range(8), 'L', (16384, 8192)), np.uint8)); print('night')
    np.save(os.path.join(OUT, 'ua.npy'), np.asarray(build('4', range(16, 21), range(3, 5), 'RGB'), np.uint8)); print('ua')
    np.save(os.path.join(OUT, 'clouds.npy'), np.asarray(Image.open(os.path.join(TEX, 'earth_clouds.png')).convert('L'), np.uint8)); print('clouds')
