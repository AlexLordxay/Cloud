# Lays the rendered shots (work/jupiter_meet/shot_<name>/) end to end into work/jupiter_meet/frames/, each crossfading
# into the next (timeline.py). Run by frames.sh after the shots are rendered.
import os, shutil, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import starts, XF

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'jupiter_meet')


def main():
    out = os.path.join(WORK, 'frames')
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    seq = starts()
    for i, (name, at, n) in enumerate(seq):
        src = os.path.join(WORK, 'shot_' + name)
        files = sorted(f for f in os.listdir(src) if f.endswith('.jpg'))
        assert len(files) >= n, (name, len(files), n)
        for j in range(n):
            dst = os.path.join(out, f'f_{at + j:05d}.jpg')
            img = Image.open(os.path.join(src, files[j])).convert('RGB')
            if i > 0 and j < XF and os.path.exists(dst):          # crossfade from the previous shot's tail
                img = Image.blend(Image.open(dst).convert('RGB'), img, (j + 1) / (XF + 1))
            img.save(dst, quality=94)
        print(name, n, 'frames at', round(at / 30, 2), 's')


if __name__ == '__main__':
    main()
