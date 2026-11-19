# Test clip: the Earth freezes over (Snowball Earth) while the camera keeps orbiting — checks smoothness (no jumps).
# python3 test_snowball.py  -> test/p3_snowball.mp4 (3.5 s, 1920x1080, 30 fps)
import math, os, sys, subprocess
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import test_frames as tf
cm, earthk = tf.cm, tf.earthk
from overlay import draw_clock, draw_stamp
W, H = cm.W, cm.H
M = earthk.maps()
day = np.asarray(M['day'][::4, ::4], np.float32) / 255.0            # 4096 x 2048
lat = np.linspace(90, -90, day.shape[0])[:, None] * np.ones((1, day.shape[1]))
lon = np.linspace(-180, 180, day.shape[1])[None, :] * np.ones((day.shape[0], 1))
P = np.stack([np.cos(np.radians(lat)) * np.cos(np.radians(lon)), np.cos(np.radians(lat)) * np.sin(np.radians(lon)), np.sin(np.radians(lat))], -1)
edge_n = (tf.fbm3(P * 6.0, 5) - 0.5) * 14.0                         # a ragged ice edge (degrees)
ice_tex = 0.80 + 0.12 * tf.fbm3(P * 30.0 + 2.0, 4)
ICE = np.stack([ice_tex * 0.93, ice_tex * 0.97, ice_tex * 1.0], -1)
FR = int(3.5 * 30); OUT = os.path.join(HERE, 'test', 'snow'); os.makedirs(OUT, exist_ok=True)

def frame(i):
    t = i / 30.0; k = cm.sm(t / 3.2)
    front = 62.0 - 62.0 * k                                          # ice front latitude, poles -> equator
    m = np.clip((np.abs(lat) + edge_n - front) / 6.0, 0, 1)[..., None]
    tex = day * (1 - m) + ICE * m
    M['day'] = np.ascontiguousarray((np.clip(tex, 0, 1) * 255).astype(np.uint8))
    lo = 20.0 + 14.0 * t / 3.5
    up = cm.ll(8.0, lo); o = up * (earthk.RE * 3.4)
    c = cm.cam(o, [0, 0, 0], [0, 0, 1], 38.0)
    img = np.zeros((H, W, 3), np.float32)
    cm.sky(img, c, tf.GAL, 0.6, stars=1.0, band=0.3)
    sun = cm.ll(15.0, lo - 55.0)
    earthk.earth(img, c, sun, sun_k=18.0, disc_k=0.0, cloud_k=0.5 * (1 - k), night_k=0.0, fields=0.0, home=(8.0, lo), expo=0.75)
    img = cm.vignette(cm.tonemap(cm.bloom(img, 0.9, 0.4), 1.0), 0.25)
    im = Image.fromarray(cm.to_u8(img)).convert('RGBA')
    h = 20.0 + (13.0 / 60.0) * cm.sm(t / 3.5); ya = (1 - (h / 24.0)) * 4.54e9
    draw_clock(im, h, ya, W - 170, 120, 70)
    draw_stamp(im, 'ЗЕМЛЯ-СНІЖКА', 520, 860, 60, cm.ramp(t, 1.2, 1.6))
    im.convert('RGB').save(os.path.join(OUT, '%04d.png' % i))

if __name__ == '__main__':
    for i in range(FR): frame(i)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', os.path.join(OUT, '%04d.png'), '-c:v', 'libx264',
                    '-crf', '18', '-pix_fmt', 'yuv420p', os.path.join(HERE, 'test', 'p3_snowball.mp4')], check=True)
    print('done')
