# The cover's picture for «А ти уявляєш Титан так?», rendered at 1080 × 1920: the long-lens view of Titan in front of Saturn
# (as the video's first shot) moved down to leave room for the title.   -> work/titan_imagine/cover_raw.png (then cover.py)
import math, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import frames as F
import render as RD
d = 47000.0; el = 0.13; az = F.SAZ + 0.05
cam = np.array([d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)])
sdir = F.nrm(F.S_POS - cam); tdir = F.nrm(-cam)
fw, rt, up = F.look(cam, cam + F.nrm(sdir * 0.50 + tdir * 0.50))
fw, rt, up = F.look(cam, cam + F.nrm(fw + up * 0.040))          # tilt up: both bodies lower in the frame
out = np.zeros((1920, 1080, 3), np.float32)
RD.space(F.TT, F.LK, F.ST, F.RG, F.MT, F.SK, cam, fw, rt, up, math.radians(31.0), F.SUN, F.S_POS, F.EX, F.EY, F.EZ,
         np.zeros(3), 0.0, 0.0, 1.0, out, 3)
Image.fromarray((RD.tonemap(RD.bloom(out)) * 255).astype(np.uint8)).save(os.path.join(F.WK, 'cover_raw.png'))
print('ok')
