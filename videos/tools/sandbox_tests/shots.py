# contact sheet of a dbg6 run: python3 shots.py <dir> [cols] [crop_h]
import sys, glob, os
from PIL import Image, ImageDraw
d = sys.argv[1]; cols = int(sys.argv[2]) if len(sys.argv) > 2 else 4; ch = int(sys.argv[3]) if len(sys.argv) > 3 else 600
fs = sorted(glob.glob(os.path.join(d, 's*.png')))
w = 300; h = int(ch * w / 390)
S = Image.new('RGB', (w * cols, h * ((len(fs) + cols - 1) // cols)))
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB').crop((0, 0, 390, ch)).resize((w, h)); ImageDraw.Draw(im).text((4, 4), os.path.basename(f)[1:-4], fill=(255, 255, 0))
    S.paste(im, ((i % cols) * w, (i // cols) * h))
S.save(os.path.join(d, 'sheet.jpg'), quality=88)
