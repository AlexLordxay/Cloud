# Planet parade — «who comes to the parade»: Mercury, Venus (with the Earth beside it for scale), Mars and then Jupiter,
# all to the SAME scale of size (diameters: Mercury 0.383, Venus 0.949, Earth 1, Mars 0.532, Jupiter 11.21 Earths) —
# a comparison of sizes, not where they are. The small ones come in close up, one by one; then the view pulls back and
# Jupiter rises from below, eleven Earths across. Globes from the site's textures, lit from the left, turning slowly.
#   from lineup import Lineup; L = Lineup(); img = L.render(t, beats)   (t: seconds into the shot)
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.abspath(os.path.join(HERE, '../../../../planetarium/textures'))
W, H = 1080, 1920
SIZE = {'mercury': 0.383, 'venus': 0.949, 'earth': 1.0, 'mars': 0.532, 'jupiter': 11.21}
FILE = {'mercury': 'mercury_2k.jpg', 'venus': 'venus_atmosphere_2k.jpg', 'earth': 'earth_day_2k.jpg', 'mars': 'mars_2k.jpg', 'jupiter': 'jupiter_2k.jpg'}
SPIN = {'mercury': 0.02, 'venus': 0.01, 'earth': 0.12, 'mars': 0.1, 'jupiter': 0.25}


def sm(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


class Lineup:
    def __init__(self):
        self.tex = {k: np.asarray(Image.open(os.path.join(TEX, f)).convert('RGB'), np.float32) / 255 for k, f in FILE.items()}
        rng = np.random.default_rng(3)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.2, 1.0)) for _ in range(420)]

    def globe(self, name, r, t):
        """an RGBA globe of radius r px"""
        tex = self.tex[name]; th, tw = tex.shape[:2]
        S = int(2 * r + 6); y, x = (np.mgrid[0:S, 0:S] - S / 2 + 0.5) / r
        rr = x * x + y * y; z = np.sqrt(np.clip(1 - rr, 0, 1))
        lat = np.arcsin(np.clip(-y, -1, 1)); lon = np.arctan2(x, z) + SPIN[name] * t
        u = ((lon / (2 * np.pi) + 0.5) % 1) * (tw - 1); v = (0.5 - lat / np.pi) * (th - 1)
        col = tex[v.astype(int).clip(0, th - 1), u.astype(int).clip(0, tw - 1)]
        L = np.array([-0.62, 0.25, 0.74]); L /= np.linalg.norm(L)
        lam = np.clip(x * L[0] + (-y) * L[1] + z * L[2], 0, 1)
        shade = 0.06 + 0.98 * lam ** 0.85
        rgb = np.clip(col * shade[..., None], 0, 1)
        a = np.clip((1 - np.sqrt(rr)) * r / 1.2, 0, 1)
        return Image.fromarray(np.dstack([rgb * 255, a * 255]).astype(np.uint8), 'RGBA')

    def render(self, t, B):
        """B: {'mercury': t, 'venus': t, 'mars': t, 'jupiter': t} — when each comes in (s into the shot)"""
        im = Image.new('RGB', (W, H), (3, 4, 9)); d = ImageDraw.Draw(im)
        for x, y, b in self.stars: c = int(120 * b); d.point((x, y), fill=(c, c, int(c * 1.1)))
        im = im.convert('RGBA')
        # the scale: px per Earth diameter — close up for the small four, then pulled back for Jupiter
        kz = sm((t - B['jupiter'] + 0.2) / 1.6)
        E = 255 * (1 - kz) + 82 * kz
        # the small row: centred, its y rising as Jupiter comes up
        order = ['mercury', 'venus', 'earth', 'mars']
        gap = E * 0.18; widths = [SIZE[n] * E for n in order]
        # the row is centred on the planets already in (it slides over smoothly as each one joins)
        ins = [sm((t - (B['venus'] if n == 'earth' else B[n])) / 0.6) for n in order]
        total = sum(w * k for w, k in zip(widths, ins)) + gap * max(0.0, sum(ins) - 1)
        x = W / 2 - total / 2; rowy = 760 * (1 - kz) + 470 * kz
        self.pos = {}
        for n, w in zip(order, widths):
            t0 = B['venus'] if n == 'earth' else B[n]
            k = sm((t - t0) / 0.5)
            if k > 0:
                g = self.globe(n, max(2, w / 2 * (0.85 + 0.15 * k)), t)
                if n == 'earth': g.putalpha(g.getchannel('A').point(lambda v: int(v * 0.55 * k)))   # the Earth: only for scale
                elif k < 1: g.putalpha(g.getchannel('A').point(lambda v: int(v * k)))
                im.alpha_composite(g, (int(x + w / 2 - g.size[0] / 2), int(rowy - g.size[1] / 2)))
            self.pos[n] = (x + w / 2, rowy, w / 2, k)
            kk = ins[order.index(n)]; x += (w + gap) * kk
        # Jupiter: rises from below the frame to the middle
        kj = sm((t - B['jupiter']) / 1.8)
        if kj > 0:
            R = SIZE['jupiter'] * E / 2
            g = self.globe('jupiter', R, t)
            cy = (H + R + 40) * (1 - kj) + 1180 * kj
            im.alpha_composite(g, (int(W / 2 - g.size[0] / 2), int(cy - g.size[1] / 2)))
            self.pos['jupiter'] = (W / 2, cy, R, kj)
        return im.convert('RGB')


if __name__ == '__main__':
    L = Lineup(); B = {'mercury': 0.3, 'venus': 1.6, 'mars': 3.4, 'jupiter': 5.2}
    out = os.path.join(HERE, '../../work/parade'); os.makedirs(out, exist_ok=True)
    ims = [L.render(t, B).resize((270, 480)) for t in (1.0, 3.0, 4.6, 6.0, 8.5)]
    s = Image.new('RGB', (270 * 5, 480))
    for i, im in enumerate(ims): s.paste(im, (i * 270, 0))
    s.save(os.path.join(out, 'lineup_sheet.jpg'))
    print('ok')
