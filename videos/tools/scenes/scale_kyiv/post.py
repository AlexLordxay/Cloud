# Lays the satellite pull-back (intro.py) over the first recorded frames of scale_kyiv and crossfades it into the 3D
# Earth, which follows the same ground span below it (cam.js). Over the second before the crossfade the satellite
# picture is eased to the 3D frame's brightness and colour, so the hand-over shows no jump. Run by make.sh after rec.js.
import os
from PIL import Image, ImageStat

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(TOOLS, 'work', 'scale_kyiv')
FPS, SAT, FADE, TONE = 30, 5.8, 0.8, 1.2       # seconds: end of the satellite part, crossfade, colour easing before it
smooth = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)


def gains(sat, rec):
    """Per-channel factors that bring the satellite frame to the recorded frame's average colour."""
    a, b = ImageStat.Stat(sat).mean, ImageStat.Stat(rec).mean
    return [min(1.3, max(0.8, bb / max(aa, 1.0))) for aa, bb in zip(a, b)]   # only a gentle nudge


def main():
    intro = sorted(f for f in os.listdir(os.path.join(WORK, 'intro')) if f.endswith('.jpg'))
    # the colour target: the recorded frame where the crossfade ends
    end = min(len(intro) - 1, int(round(SAT * FPS)) - 1)
    g_end = gains(Image.open(os.path.join(WORK, 'intro', intro[end])).convert('RGB'),
                  Image.open(os.path.join(WORK, 'frames', f'f_{end:05d}.jpg')).convert('RGB'))
    for i, f in enumerate(intro):
        t = i / FPS
        rec_path = os.path.join(WORK, 'frames', f'f_{i:05d}.jpg')
        if not os.path.exists(rec_path): break
        sat = Image.open(os.path.join(WORK, 'intro', f)).convert('RGB')
        k = smooth((t - (SAT - FADE - TONE)) / TONE)                      # colour easing
        g = [1 + (x - 1) * k for x in g_end]
        sat = Image.merge('RGB', [ch.point(lambda v, m=m: min(255, int(v * m))) for ch, m in zip(sat.split(), g)])
        mix = smooth((t - (SAT - FADE)) / FADE)                            # crossfade into the 3D frame
        out = sat if mix <= 0 else Image.blend(sat, Image.open(rec_path).convert('RGB'), mix)
        out.save(rec_path, quality=94)
    print('intro laid over', len(intro), 'frames')


if __name__ == '__main__':
    main()
