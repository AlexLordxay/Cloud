# Paleogeographic maps for «Історія Землі»: the PALEOMAP PaleoDEMs (Scotese & Wright 2018, CC BY 4.0, zenodo 5460860)
# painted with chicxulub/maps.py's paint(), but the land is BARE ROCK before plants (none before ~470 Ma; the first
# forests ~385 Ma; full cover by ~350 Ma), with a south polar ice cap in the late Paleozoic glaciation (~330–270 Ma).
#   python3 paleo.py [ages…]  -> work/earth_history/paleo/ep_<Ma>.png (4096×2048 sRGB)
import os, sys, io, re, zipfile, numpy as np, h5py
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, os.path.join(TOOLS, 'scenes', 'chicxulub'))
from maps import paint, field, fbm
ZIP = os.path.join(TOOLS, 'work', 'chicxulub', 'dl', 'dem6.zip'); OUT = os.path.join(TOOLS, 'work', 'earth_history', 'paleo')
W, H = 4096, 2048
AGES = [540, 520, 500, 480, 470, 450, 430, 410, 390, 370, 350, 330, 300, 280, 260, 250, 240, 230, 220, 200, 180, 160,
        140, 120, 100, 80, 65, 50, 40, 30, 20, 10, 0]

def dem(age):
    with zipfile.ZipFile(ZIP) as z:
        name = [n for n in z.namelist() if '__MACOSX' not in n and re.search(rf'_{age}Ma\.nc$', n)][0]
        with h5py.File(io.BytesIO(z.read(name)), 'r') as f:
            return f['z'][...][:, :-1].astype(np.float32)

def veg(age):
    if age >= 470: return 0.0
    if age >= 385: return 0.25 * (470 - age) / 85          # mosses, liverworts, the first small plants
    return min(1.0, 0.25 + 0.75 * (385 - age) / 35)

def make(age):
    z = dem(age)
    ice = 28.0 if 270 <= age <= 330 else (20.0 if age <= 30 else 0.0)
    col, rel, land = paint(z, W, H, ice=ice)
    v = veg(age)
    if v < 1.0:
        n = field(W, H, lambda P, la: fbm(P, 30, 6, 77))[..., None]
        n2 = field(W, H, lambda P, la: fbm(P, 9, 4, 78))[..., None]
        bare = np.array([150, 124, 100]) * (0.82 + 0.3 * n) + (n2 - 0.5) * np.array([40, 26, 10])
        lum = col.mean(-1, keepdims=True)
        bare = bare * (0.75 + 0.5 * np.clip(lum / 120, 0, 1))
        sheet = (col[..., 0:1] > 215) & (col[..., 2:3] > 225)               # keep the ice white
        k = (1 - v) * land[..., None] * (~sheet)
        col = col * (1 - k) + bare * k
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(OUT, f'ep_{age}.png'))
    print(age, flush=True)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for a in [int(x) for x in sys.argv[1:]] or AGES:
        if not os.path.exists(os.path.join(OUT, f'ep_{a}.png')): make(a)
