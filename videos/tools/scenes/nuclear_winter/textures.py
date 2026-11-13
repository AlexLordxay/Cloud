# Builds the Earth maps for «Ядерна зима» from the site's tiles (planetarium/textures/earth: NASA Blue Marble level 2 =
# 8x4 tiles, Black Marble n3 = 16x8 tiles, equirectangular) -> work/nuclear_winter/{day,night}.npy (uint8, 16384x8192),
# loaded with mmap so the render workers share them.   python3 textures.py
import os, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.abspath(os.path.join(TOOLS, '../../planetarium/textures/earth'))
OUT = os.path.join(TOOLS, 'work', 'nuclear_winter'); os.makedirs(OUT, exist_ok=True)
W, H = 16384, 8192

def build(level, nx, ny, mode):
    big = Image.new(mode, (nx * 2048, ny * 2048))
    for x in range(nx):
        for y in range(ny):
            p = os.path.join(SRC, level, f'{x}_{y}.jpg')
            big.paste(Image.open(p).convert(mode), (x * 2048, y * 2048))
    return big.resize((W, H), Image.LANCZOS) if big.size != (W, H) else big

if __name__ == '__main__':
    np.save(os.path.join(OUT, 'day.npy'), np.asarray(build('2', 8, 4, 'RGB'), np.uint8)); print('day')
    np.save(os.path.join(OUT, 'night.npy'), np.asarray(build('n3', 16, 8, 'L'), np.uint8)); print('night')
