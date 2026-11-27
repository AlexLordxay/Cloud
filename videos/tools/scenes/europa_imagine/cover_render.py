# The cover's picture for «А ти уявляєш Європу так?», rendered anew at 1080 × 1920 (not a video frame: in the video the
# cut-open globe runs off the right edge). Europa whole, cut open (ice shell, the ocean, rock, iron core), Jupiter whole
# behind it to the upper right, room for the title above.   -> work/europa_imagine/cover_raw.png (then cover.py)
import math, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import frames as FR
import render as RD
W, H, FOV = 1080, 1920, 50.0
f = (H / 2) / math.tan(math.radians(FOV) / 2)
d = RD.R_E / math.sin(math.atan(340 / f))                 # Europa ~340 px in radius
az, el = -2.1, 0.40
cam = FR.sph(d, az, el)
fw0, rt0, up0 = FR.look(cam, [0, 0, 0])
# aim so that Europa sits a little left of centre and below it
fw, rt, up = FR.look(cam, cam + (fw0 + (90 / f) * rt0 + (230 / f) * up0) * d)
jd = FR.nrm(fw + (215 / f) * rt + (215 / f) * up)        # Jupiter's centre upper right, partly behind Europa
sn = FR.nrm(rt * 0.9 - fw * 0.35 + up * 0.25)
out = np.zeros((H, W, 3), np.float32)
RD.space(FR.GT, FR.MT, FR.SK, FR.JT, cam, fw, rt, up, math.radians(FOV), sn, jd, FR.JANG, FR.nrm([0, 0, 1.0]), 0.0, 0.0,
         np.zeros(4), 1.0, np.array([math.cos(az + 0.45), math.sin(az + 0.45)]), 0.78, out, 3, np.zeros(4), FR.BOX)
img = (RD.tonemap(RD.bloom(out)) * 255).astype(np.uint8)
Image.fromarray(img).save(os.path.join(FR.WK, 'cover_raw.png'))
print('ok')
