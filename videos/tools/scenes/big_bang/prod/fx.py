# «Великий вибух» — shared tools for the production renders: the timeline, a filmic finish (bloom, ACES tone map,
# vignette, grain) done fast with OpenCV, image loading in linear light, Ken-Burns warps and text.
import json, math, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None

BB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # videos/tools/scenes/big_bang
ASSETS = os.path.join(BB, 'assets')
W, H, FPS = 1920, 1080, 30
TL = json.load(open(os.path.join(BB, 'timeline.json'), encoding='utf-8'))
FONT_L = '/usr/share/fonts/opentype/inter/Inter-Light.otf'
FONT_XL = '/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf'
FONT_M = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'


def shot(prefix):
    s = next(s for s in TL['shots'] if s['name'].startswith(prefix + ' '))
    return s['t0'], s['t1']


def phrase(prefix):
    p = next(p for p in TL['phrases'] if p['text'].startswith(prefix))
    return p['t0'], p['t1']


def smooth(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * (3 - 2 * k)


def smoother(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * k * (k * (6 * k - 15) + 10)


def lerp(a, b, k): return a + (b - a) * k


def ramp(t, a, b): return smooth((t - a) / (b - a)) if b != a else float(t >= a)


# ------------------------------------------------------------------------------------------------ light & finish
_LUT = ((np.arange(256) / 255.0) ** 2.2).astype(np.float32)


def to_lin(u8): return _LUT[u8]


def tonemap(a):
    x = (a * (2.51 * a + 0.03)) / (a * (2.43 * a + 0.59) + 0.14)
    np.clip(x, 0, 1, out=x)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def blur(img, sigma):
    if sigma <= 0: return img
    if sigma < 6:
        return cv2.GaussianBlur(img, (0, 0), sigma)
    f = max(1, int(sigma / 3))                       # wide blurs at low resolution
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(1, w // f), max(1, h // f)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / f)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def bloom(lin, thr=0.35, radii=((3, 0.35), (14, 0.30), (55, 0.30)), k=1.0):
    b = np.clip(lin - thr, 0, None).astype(np.float32)
    return lin + k * sum(wt * blur(b, r) for r, wt in radii)


_VIG = {}


def vignette(strength=0.26, p=1.4):
    key = (strength, p)
    if key not in _VIG:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        _VIG[key] = (1 - strength * r ** p)[..., None].astype(np.float32)
    return _VIG[key]


def finish(lin, rng, exposure=1.0, bl=True, thr=0.35, bk=1.0, vig=0.26, grain=0.011):
    lin = lin.astype(np.float32, copy=False)
    if bl: lin = bloom(lin, thr=thr, k=bk)
    lin = lin * vignette(vig) * exposure
    out = tonemap(lin)
    if grain:
        g = rng.standard_normal((H // 2, W // 2), dtype=np.float32)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)
        out += g[..., None] * grain * (0.4 + 0.6 * np.sqrt(np.clip(out, 0, 1)))
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------------------------------------ images
_IMG = {}


def load(name, maxdim=None):
    """an asset in linear light, float32 RGB (cached)"""
    key = (name, maxdim)
    if key not in _IMG:
        im = Image.open(os.path.join(ASSETS, name) if not os.path.isabs(name) else name).convert('RGB')
        if maxdim and max(im.size) > maxdim:
            s = maxdim / max(im.size)
            im = im.resize((int(im.size[0] * s), int(im.size[1] * s)), Image.LANCZOS)
        _IMG[key] = to_lin(np.asarray(im))
    return _IMG[key]


def warp(img, cx, cy, scale, rot=0.0, sx=W / 2, sy=H / 2, out=None, gain=1.0, border=0.0):
    """draw img so that its point (cx, cy) lands at screen (sx, sy), scale = screen px per image px, rot (rad)"""
    c, s = math.cos(rot) * scale, math.sin(rot) * scale
    M = np.array([[c, -s, sx - (c * cx - s * cy)], [s, c, sy - (s * cx + c * cy)]], np.float32)
    interp = cv2.INTER_AREA if scale < 0.6 else cv2.INTER_CUBIC
    if scale < 0.6:                                      # minify through a pre-blurred copy (no aliasing)
        interp = cv2.INTER_LINEAR
        img = blur(img, 0.45 / scale)
    r = cv2.warpAffine(img, M, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=(border,) * 3)
    if gain != 1.0: r *= gain
    if out is not None:
        out += r
        return out
    return r


def disc_mask(cx, cy, rad, soft=0.15):
    yy, xx = np.ogrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(rad, 1e-3)
    return np.clip((1.0 - d) / soft, 0, 1).astype(np.float32)[..., None]


# ------------------------------------------------------------------------------------------------ text
def text_mask(items):
    """items: (x, y, text, size, alpha, font, anchor) — returns a float alpha layer"""
    lay = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(lay)
    for x, y, txt, size, al, font, anchor in items:
        if al <= 0.002: continue
        f = ImageFont.truetype(font, size)
        d.text((x, y), txt, font=f, fill=int(255 * min(al, 1.0)), anchor=anchor)
    return np.asarray(lay).astype(np.float32) / 255
