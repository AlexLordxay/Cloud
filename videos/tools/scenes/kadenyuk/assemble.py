# Lays the picture of the Kadenyuk video onto one timeline (720 × 1280, work/kadenyuk/frames/): the 3D shots
# (render.js → work/kadenyuk/shot_<name>/) and the NASA photos (work/kadenyuk/photos/, a slow push-in each), with
# 0.4 s crossfades at the cuts, plus the map mark on Klishkivtsi. Captions, logo and the end card come after (compose.py).
# Run by frames.sh, i.e. ./make.sh kadenyuk.
import json, os
from PIL import Image, ImageDraw, ImageFont

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'kadenyuk')
W, H, FPS, XF = 720, 1280, 30, 0.2           # XF: half the crossfade
DURATION = json.load(open(os.path.join(os.path.dirname(__file__), 'scene.json')))['duration']

# (cut where this piece starts, what it is); a 3D shot is ('shot', name), a photo is ('photo', file, crop centre
# x from → to (0..1 of the width), zoom from → to)
PIECES = [
    (0.0, ('shot', 'hook')),
    (4.45, ('shot', 'home')),
    (8.3, ('shot', 'night')),
    (14.2, ('photo', 'KSC-97PC1676.jpg', (0.36, 0.38), (1.0, 1.10))),    # thumbs up in the launch suit
    (17.4, ('photo', 'KSC-97PC1697.jpg', (0.52, 0.52), (1.08, 1.0))),    # Columbia lifts off, 19.11.1997
    (21.3, ('photo', 'sts087-332-034.jpg', (0.44, 0.46), (1.0, 1.14))),  # with the Brassica rapa plants
    (28.0, ('photo', 'sts087-385-005.jpg', (0.70, 0.42), (1.05, 1.05))), # a plant sample from the growth facility
    (33.9, ('shot', 'finale')),
]
cuts = [c for c, _ in PIECES] + [DURATION + 1]

_photos, _shots = {}, {}
def photo(f, cx, z):
    if f not in _photos: _photos[f] = Image.open(os.path.join(WORK, 'photos', f)).convert('RGB')
    im = _photos[f]; ih = im.height / z; iw = ih * W / H
    if iw > im.width: iw = im.width; ih = iw * H / W
    x0 = min(max(0, cx * im.width - iw / 2), im.width - iw); y0 = (im.height - ih) / 2
    return im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + iw, y0 + ih))

def shot(name, start, t):
    d = os.path.join(WORK, 'shot_' + name)
    if name not in _shots:
        _shots[name] = (sorted(f for f in os.listdir(d) if f.endswith('.jpg')), json.load(open(os.path.join(d, 'marks.json'))))
    files, marks = _shots[name]
    i = min(len(files) - 1, max(0, round((t - start) * FPS)))
    im = Image.open(os.path.join(d, files[i])).convert('RGB')
    if marks[i]: mark(im, marks[i], t - start)
    return im

F_MARK = ImageFont.truetype(os.path.join(TOOLS, 'fonts', 'Commissioner.ttf'), 40)
def mark(im, xy, t):
    # a dot with a soft pulsing ring and the village's name, coming up once the camera is low enough
    a = min(1.0, max(0.0, (t - 1.2) / 0.8))
    if a <= 0: return
    lay = Image.new('RGBA', im.size); d = ImageDraw.Draw(lay); x, y = xy
    r = 10 + 14 * ((t * 0.9) % 1); ra = int(200 * a * (1 - (t * 0.9) % 1))
    d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 214, 120, ra), width=3)
    d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(255, 214, 120, int(255 * a)), outline=(0, 0, 0, int(160 * a)), width=2)
    d.text((x + 1, y - 26 + 2), 'Клішківці', font=F_MARK, fill=(0, 0, 0, int(170 * a)), anchor='ms')
    d.text((x, y - 26), 'Клішківці', font=F_MARK, fill=(255, 255, 255, int(255 * a)), anchor='ms')
    im.paste(Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB'))

def piece(k, t):
    start, src = PIECES[k]
    s0 = 0 if k == 0 else start - XF                          # a 3D shot starts XF before its cut
    if src[0] == 'shot': return shot(src[1], s0, t)
    _, f, (c0, c1), (z0, z1) = src
    end = cuts[k + 1] + XF; u = (t - s0) / (end - s0)
    return photo(f, c0 + (c1 - c0) * u, z0 + (z1 - z0) * u)

def main():
    out = os.path.join(WORK, 'frames'); os.makedirs(out, exist_ok=True)
    for i in range(round(DURATION * FPS)):
        t = i / FPS
        k = max(j for j in range(len(PIECES)) if cuts[j] - XF <= t)
        img = piece(k, t)
        if k > 0 and t < cuts[k] + XF:                         # in a crossfade: the previous piece under this one
            img = Image.blend(piece(k - 1, t), img, (t - (cuts[k] - XF)) / (2 * XF))
        img.save(os.path.join(out, f'f_{i:05d}.jpg'), quality=94)
        if i % 150 == 0: print('frame', i, flush=True)

if __name__ == '__main__':
    main()
