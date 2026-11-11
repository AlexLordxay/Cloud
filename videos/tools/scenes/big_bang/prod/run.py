# Render one production segment: python3 prod/run.py seg01 [--still T] [--every N]
# A segment module defines T0, T1 (global seconds, inclusive frame range) and frame(T) -> uint8 HxWx3.
# Frames go to render/<seg>/f_<global frame>.jpg (resumable: existing frames are skipped).
import importlib, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
import fx

name = sys.argv[1]
seg = importlib.import_module(name)
out = os.path.join(fx.BB, 'render', name)
os.makedirs(out, exist_ok=True)
if '--still' in sys.argv:
    T = float(sys.argv[sys.argv.index('--still') + 1])
    dst = os.path.join(fx.BB, 'test', f'{name}_{T:07.2f}.jpg')
    Image.fromarray(seg.frame(T)).save(dst, quality=92)
    print(dst)
    sys.exit()
every = int(sys.argv[sys.argv.index('--every') + 1]) if '--every' in sys.argv else 1
n0, n1 = int(round(seg.T0 * fx.FPS)), int(round(seg.T1 * fx.FPS))
if hasattr(seg, 'prepare'): seg.prepare()
t0 = time.time(); done = 0
for n in range(n0, n1 + 1, every):
    dst = os.path.join(out, f'f_{n:05d}.jpg')
    if os.path.exists(dst) and not getattr(seg, 'STATEFUL', False):
        continue
    Image.fromarray(seg.frame(n / fx.FPS)).save(dst, quality=94)
    done += 1
    if done % 30 == 0:
        print(name, n, '/', n1, f'{(time.time() - t0) / done:.2f} s/frame', flush=True)
print(name, 'done', flush=True)
