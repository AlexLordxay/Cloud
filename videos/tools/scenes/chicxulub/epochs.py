# The Earth from the end of the Cretaceous to today, for the finale of "Що сталося з Землею, коли вимерли динозаври":
# the PALEOMAP PaleoDEMs every 5 million years (Scotese & Wright 2018, zenodo 5460860, CC BY 4.0) painted as maps.py
# paints the K–Pg boundary (with the Antarctic ice sheet from ~34 million years ago), 2048 × 1024, and how the ground
# moves from each map to the next younger one (optical flow on the relief: the continents' drift), for the morph in
# world.js.
#   work/chicxulub/maps/ep_<Ma>.jpg     colour
#   work/chicxulub/maps/ep_<Ma>_r.png   slopes east (R) and north (G) of the land, 128 = flat; water (B)
#   work/chicxulub/maps/ep_<Ma>_f.png   the flow to the next younger map, in pixels: R = 128 + 2 × east, G = 128 + 2 × south
#   work/chicxulub/maps/ep_now.jpg      the Earth of today as it is: NASA's Blue Marble Next Generation (July 2004, with
#                                       topography and bathymetry; Visible Earth, NASA Goddard), the last step after 0 Ma
#   work/chicxulub/maps/ep_flat_f.png   no flow (from 0 Ma to the Blue Marble: the same ground, only seen truly)
#
#   python3 scenes/chicxulub/epochs.py          (after maps.py, which fetches the DEMs)
#   python3 scenes/chicxulub/epochs.py check    (a strip of each morph at its middle: work/chicxulub/epochs_check.jpg)
import os, sys, re, zipfile, io, subprocess, numpy as np, h5py, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maps import paint, DL, OUT, WORK

W, H = 2048, 1024
BM = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73751/world.topo.bathy.200407.3x5400x2700.jpg'
AGES = list(range(65, -1, -5))


def dem(age):
    with zipfile.ZipFile(os.path.join(DL, 'dem6.zip')) as z:
        name = [n for n in z.namelist() if '__MACOSX' not in n and re.search(rf'_{age}Ma\.nc$', n)][0]
        with h5py.File(io.BytesIO(z.read(name)), 'r') as f:
            return f['z'][...][:, :-1].astype(np.float32)                  # north is the first row; the repeated 180° column off


def flow(za, zb):
    # the relief as a picture (the coasts stand out most), wrapped east–west so the flow runs on across 180°
    def pic(z):
        z = cv2.resize(z, (W, H), interpolation=cv2.INTER_AREA)
        g = np.clip((z + 5000) / 8000, 0, 1) * 0.6 + (z > 0) * 0.4
        return np.pad((g * 255).astype(np.uint8), ((0, 0), (128, 128)), mode='wrap')
    f = cv2.calcOpticalFlowFarneback(pic(za), pic(zb), None, 0.5, 6, 41, 6, 7, 1.5, cv2.OPTFLOW_FARNEBACK_GAUSSIAN)
    return f[:, 128:-128]


if __name__ == '__main__':
    if sys.argv[1:] == ['check']:
        # each morph halfway, as world.js draws it: the older map pushed half way along the flow, the younger pulled back
        rows = []
        for a, b in zip(AGES, AGES[1:]):
            A = np.asarray(Image.open(os.path.join(OUT, f'ep_{a}.jpg'))).astype(np.float32)
            B = np.asarray(Image.open(os.path.join(OUT, f'ep_{b}.jpg'))).astype(np.float32)
            F = (np.asarray(Image.open(os.path.join(OUT, f'ep_{a}_f.png')))[..., :2].astype(np.float32) - 128) / 2
            y, x = np.mgrid[0:H, 0:W].astype(np.float32)
            wa = cv2.remap(A, x - 0.5 * F[..., 0], y - 0.5 * F[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            wb = cv2.remap(B, x + 0.5 * F[..., 0], y + 0.5 * F[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            rows.append(np.concatenate([A, (wa + wb) / 2, B], 1)[::4, ::4])
        Image.fromarray(np.clip(np.concatenate(rows, 0), 0, 255).astype(np.uint8)).save(os.path.join(WORK, 'epochs_check.jpg'), quality=85)
        sys.exit()
    bm = os.path.join(WORK, 'nasa', 'bm_topo_bathy_200407.jpg')
    if not os.path.exists(bm):
        os.makedirs(os.path.dirname(bm), exist_ok=True)
        subprocess.run(['curl', '-sS', '-o', bm, BM], check=True)
    Image.open(bm).convert('RGB').resize((W, H), Image.LANCZOS).save(os.path.join(OUT, 'ep_now.jpg'), quality=92)
    Image.new('RGB', (64, 32), (128, 128, 128)).save(os.path.join(OUT, 'ep_flat_f.png'))
    zs = {}
    for age in AGES:
        zs[age] = dem(age)
        col, rel, land = paint(zs[age], W, H, ice=0 if age > 35 else (18 if age == 35 else 24))
        Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(OUT, f'ep_{age}.jpg'), quality=92)
        rel[..., 2] = (~land) * 255
        Image.fromarray(rel.astype(np.uint8)).save(os.path.join(OUT, f'ep_{age}_r.png'))
        print(age, 'Ma painted', flush=True)
    for a, b in zip(AGES, AGES[1:]):
        f = flow(zs[a], zs[b])
        enc = np.clip(128 + 2 * f, 0, 255).astype(np.uint8)
        Image.fromarray(np.dstack([enc, np.full((H, W), 128, np.uint8)])).save(os.path.join(OUT, f'ep_{a}_f.png'))
        print(a, '->', b, 'flow max', float(np.abs(f).max()), 'px', flush=True)
