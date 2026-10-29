# Glow round the brightest parts of each frame (the Moon's hot edge, the fire, the flash), as a lens sees them — the
# dinosaur video's bloom — from work/moonfall/shot_film into work/moonfall/frames (with each frame's numbers alongside).
# Frames already done are skipped.   python3 scenes/moonfall/post.py
import os, shutil, sys
from multiprocessing import Pool
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'chicxulub'))
from post import bloom

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
SRC = os.path.join(TOOLS, 'work', 'moonfall', 'shot_film'); DST = os.path.join(TOOLS, 'work', 'moonfall', 'frames')


def one(f):
    out = os.path.join(DST, f)
    if not os.path.exists(out):
        bloom(Image.open(os.path.join(SRC, f)).convert('RGB'), thr=0.6, k=0.8).save(out, quality=93)
    js = f.replace('.jpg', '.json')
    if os.path.exists(os.path.join(SRC, js)): shutil.copy(os.path.join(SRC, js), os.path.join(DST, js))


if __name__ == '__main__':
    os.makedirs(DST, exist_ok=True)
    with Pool(4) as p: p.map(one, sorted(f for f in os.listdir(SRC) if f.endswith('.jpg')), chunksize=8)
    print('glow done')
