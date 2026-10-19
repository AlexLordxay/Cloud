# Lays the 3D flights over the real relief (terrain.js, work/moon_meet/shot_<name>/) onto the recorded site frames
# of "Знайомся: Місяць", with short crossfades where they meet the site's Earth and Moon. Run by make.sh after rec.js.
import os
from PIL import Image

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'moon_meet')
FPS, XF = 30, 8                                   # crossfade length in frames
# (shot, first frame on the timeline, fade in from the site, fade out to the site)
LAYERS = [('hook', 0, False, True), ('apollo', 829, True, True), ('tycho', 1330, True, False), ('earth', 1577, False, True)]


def main():
    frames = os.path.join(WORK, 'frames')
    for name, at, fin, fout in LAYERS:
        src = sorted(f for f in os.listdir(os.path.join(WORK, 'shot_' + name)) if f.endswith('.jpg'))
        n = len(src)
        before = Image.open(os.path.join(frames, f'f_{at - 1:05d}.jpg')).convert('RGB') if fin and at > 0 else None
        after_last = Image.open(os.path.join(WORK, 'shot_' + name, src[-1])).convert('RGB')
        for i, f in enumerate(src):
            img = Image.open(os.path.join(WORK, 'shot_' + name, f)).convert('RGB')
            if before is not None and i < XF: img = Image.blend(before, img, (i + 1) / (XF + 1))
            img.save(os.path.join(frames, f'f_{at + i:05d}.jpg'), quality=94)
        if fout:                                  # the site's next shot comes up out of the flight's last frame
            for j in range(XF):
                p = os.path.join(frames, f'f_{at + n + j:05d}.jpg')
                if not os.path.exists(p): break
                Image.blend(after_last, Image.open(p).convert('RGB'), (j + 1) / (XF + 1)).save(p, quality=94)
        print(name, n, 'frames laid at', at / FPS, 's')


if __name__ == '__main__':
    main()
