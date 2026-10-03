# Fills the unimaged parts of the Pluto, Charon and Triton maps.
#
#   python3 fill_unmapped.py            ->  ../textures/{pluto,charon,triton}.jpg rewritten in place
#
# New Horizons (2015) and Voyager 2 (1989) each saw only one side of these worlds; the published mosaics paint the rest
# a single flat colour, which on the globe reads as a smooth plastic half with a hard edge. Here that area is filled
# with ground borrowed from the imaged side of the same body: the mirror latitude, half a turn round in longitude
# (other offsets where that is unimaged too), brought to the brightness of the neighbouring imaged ground and blended
# in over a wide, soft seam. It is an artistic reconstruction: the site's descriptions say so.
# Run it on the original maps (git history), not on its own output: it finds the gaps by their exact flat colour.
import os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'textures')
FILL = {'pluto': (141, 118, 100), 'charon': (128, 121, 115), 'triton': (153, 155, 144)}


def grow(mask, px):
    """Dilate a boolean mask by ~px pixels."""
    im = Image.fromarray((mask * 255).astype(np.uint8))
    while px > 0:
        k = min(px, 6) * 2 + 1
        im = im.filter(ImageFilter.MaxFilter(k))
        px -= min(px, 6)
    return np.asarray(im) > 127


def areas(mask, keep):
    """The connected parts of a mask (wrapping round in longitude) for which keep(size, touches a pole) is true."""
    H, W = mask.shape
    out, seen = np.zeros_like(mask), np.zeros_like(mask)
    for y0, x0 in zip(*np.where(mask)):
        if seen[y0, x0]: continue
        comp, stack, pole = [], [(y0, x0)], False
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop(); comp.append((y, x))
            pole |= y in (0, H - 1)
            for yy, xx in ((y - 1, x), (y + 1, x), (y, (x - 1) % W), (y, (x + 1) % W)):
                if 0 <= yy < H and mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True; stack.append((yy, xx))
        if keep(len(comp), pole):
            ys, xs = zip(*comp); out[list(ys), list(xs)] = True
    return out


def blur(a, r):
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255


for name, fill in FILL.items():
    path = os.path.join(TEX, name + '.jpg')
    img = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)
    H, W = img.shape[:2]
    # The flat colour (JPEG noise aside): areas of it reaching a pole, or big ones; small patches of imaged ground that
    # happen to share the colour stay as they are.
    flat = np.abs(img - np.array(fill, np.float32)).max(2) < 3
    gap = areas(flat, lambda n, pole: pole or n > 6000)
    # Holes inside it (JPEG specks) closed, then grown over the source's own soft edge.
    gap = np.asarray(Image.fromarray((gap * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))) > 127
    gap = grow(gap, 14)
    # Ground to borrow: mirror latitude, shifted round in longitude; where that is a gap too, try other shifts.
    mirror = img[::-1]
    mgap = gap[::-1]
    src = np.zeros_like(img)
    have = np.zeros((H, W), bool)
    for shift in (W // 2, W // 3, 2 * W // 3, W // 6, 5 * W // 6, 0):
        s, sg = np.roll(mirror, shift, axis=1), np.roll(mgap, shift, axis=1)
        take = ~have & ~sg
        src[take] = s[take]
        have |= take
    # Anything still empty (gap at both a latitude and its mirror): the nearest imaged row of the same column.
    for x in np.where((~have & gap).any(0))[0]:
        col = ~gap[:, x]
        ys = np.where(col)[0]
        for y in np.where(~have[:, x] & gap[:, x])[0]:
            src[y, x] = img[ys[np.argmin(np.abs(ys - y))], x]
    # Brightness: the borrowed ground takes on the mean colour of the imaged ground along the seam.
    ring = grow(gap, 60) & ~gap
    for ch in range(3):
        src[..., ch] *= img[..., ch][ring].mean() / max(1e-3, src[..., ch][gap].mean())
    w = blur(gap.astype(np.float32), 18)[..., None]
    out = img * (1 - w) + src * w
    Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(path, quality=84, optimize=True, progressive=True)
    print(name, 'filled', round(gap.mean() * 100, 1), '% of the map')
