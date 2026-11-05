# «Знайомся: Нептун» — the test clip for the author: the clouds (clouds.py) with the astronaut (astro.js) falling in them.
#   python3 scenes/neptune_meet/test.py spec      -> work/neptune_meet/test/spec.json (the figure, frame by frame)
#   python3 scenes/neptune_meet/test.py comp      -> work/neptune_meet/test/c_<f>.png and ../../videos/neptune_test.mp4
import sys, os, math, json, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clouds as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(C.WORK, 'test')
os.makedirs(OUT, exist_ok=True)
FPS, DUR = 30, 10.0
W, H = 720, 1280


def T3(v):
    # world (z up) -> three.js (y up)
    return [float(v[0]), float(v[2]), float(-v[1])]


def quat_from_cols(x, y, z):
    m = np.array([x, y, z]).T
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2; w = 0.25 * s
        qx = (m[2, 1] - m[1, 2]) / s; qy = (m[0, 2] - m[2, 0]) / s; qz = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; w = (m[2, 1] - m[1, 2]) / s
        qx = 0.25 * s; qy = (m[0, 1] + m[1, 0]) / s; qz = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; w = (m[0, 2] - m[2, 0]) / s
        qx = (m[0, 1] + m[1, 0]) / s; qy = 0.25 * s; qz = (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; w = (m[1, 0] - m[0, 1]) / s
        qx = (m[0, 2] + m[2, 0]) / s; qy = (m[1, 2] + m[2, 1]) / s; qz = 0.25 * s
    return [qx, qy, qz, w]


def sample(vol, M, p):
    # nearest voxel of a uint8 grid at world point p (or None outside)
    i = int((p[0] - M[0]) / M[3]); j = int((p[1] - M[1]) / M[3]); k = int((p[2] - M[2]) / M[3])
    if 0 <= i < vol.shape[2] and 0 <= j < vol.shape[1] and 0 <= k < vol.shape[0]:
        v = vol[k, j, i] / 255.0
        return v * v * C.TAUMAX
    return None


def figure(t):
    # the figure in front of the camera, diving head first: head away from us and down the frame, his back to us;
    # set relative to the camera, so he stays steady however the camera turns; a slow sway round the line of sight
    pos, f, r, u = C.cam_at(t)
    dist = 7.0
    ap = pos + f * dist - u * 0.6
    sw = 0.35 * math.sin(t * 0.6) + 0.1 * math.sin(t * 1.7)
    c, s = math.cos(sw), math.sin(sw)
    u2 = u * c + r * s
    head = 0.62 * f - 0.78 * u2
    back = -(0.78 * f + 0.62 * u2)
    xl = np.cross(head, back)
    q = quat_from_cols(np.array(T3(xl)), np.array(T3(head)), np.array(T3(back)))
    return pos, f, u, ap, q


def spec():
    sunv = C.load()[1]
    fr = []
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        pos, f, u, ap, q = figure(t)
        ts = sample(sunv, C.NEAR, ap)
        lit = math.exp(-ts) if ts is not None else 1.0
        depth = C.ZTOP + 380 - ap[2]
        g = [C.gas(depth / C.SUN[2], ch) for ch in range(3)]
        ga = [C.gas(depth, ch) for ch in range(3)]
        amb = [0.08, 0.16, 0.32]
        fr.append(dict(f=fi, cam=T3(pos) + T3(pos + f) + T3(u), fov=66, pos=T3(ap), quat=q, pt=t,
                       sun=T3(C.SUN), sunC=[1.3 * g[c] * lit for c in range(3)],
                       sky=[1.35 * amb[c] * ga[c] for c in range(3)], gnd=[0.7 * amb[c] * ga[c] for c in range(3)],
                       rim=[0.25 * ga[0], 0.4 * ga[1], 0.6 * ga[2]], spread=1.0))
    json.dump(dict(W=W, H=H, frames=fr), open(os.path.join(OUT, 'spec.json'), 'w'))


def comp():
    from PIL import Image
    for fi in range(int(DUR * FPS)):
        fn = os.path.join(OUT, f'c_{fi:05d}.png')
        if os.path.exists(fn):
            continue
        bg = Image.open(os.path.join(C.WORK, 'cl', f'f_{fi:05d}.png')).convert('RGBA')
        fg = Image.open(os.path.join(OUT, f'a_{fi:05d}.png')).convert('RGBA')
        bg.alpha_composite(fg)
        bg.convert('RGB').save(fn)
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    dst = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'neptune_test.mp4'))
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(OUT, 'c_%05d.png'),
                    '-vf', 'scale=1080:1920:flags=lanczos', '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p', dst], check=True)
    print(dst)


if __name__ == '__main__':
    {'spec': spec, 'comp': comp}[sys.argv[1]]()
