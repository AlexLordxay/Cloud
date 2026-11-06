# «Знайомся: TRAPPIST-1e» — the insert on «Вона за сорок світлових років від нас»: a fast flight away from the Earth
# (Ukraine in the afternoon light, the site's textures: day, night lights, clouds, oceans' glint), the Earth shrinking
# to a dot while the stars streak past. u = 0..1 over the insert (~2.8 s).
import math, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [HERE, TOOLS]
import render as R

TEX = os.path.join(os.path.dirname(os.path.dirname(TOOLS)), 'planetarium', 'textures')
_T = {}
def tex():
    if not _T:
        L = lambda f, m='RGB': np.asarray(Image.open(os.path.join(TEX, f)).convert(m), np.float32) / 255
        _T['day'] = L('earth_day.jpg') ** 2.2
        _T['night'] = L('earth_night.jpg') ** 2.2
        _T['spec'] = L('earth_specular.jpg', 'L')
        _T['cl'] = np.asarray(Image.open(os.path.join(TEX, 'earth_clouds.png')).convert('L').resize((2048, 1024), Image.BICUBIC), np.float32) / 255
    return _T

def ll(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])

def samp(img, lat, lon):
    h, w = img.shape[:2]
    fx = (lon + np.pi) / (2 * np.pi) * w - 0.5; fy = (np.pi / 2 - lat) / np.pi * h - 0.5
    x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int); ax = fx - x0; ay = fy - y0
    x0m, x1m = x0 % w, (x0 + 1) % w; y0c, y1c = np.clip(y0, 0, h - 1), np.clip(y0 + 1, 0, h - 1)
    if img.ndim == 3: ax, ay = ax[:, None], ay[:, None]
    return (img[y0c, x0m] * (1 - ax) + img[y0c, x1m] * ax) * (1 - ay) + (img[y1c, x0m] * (1 - ax) + img[y1c, x1m] * ax) * ay

SUN = ll(2.0, -18.0)                      # the subsolar point over the Atlantic: Ukraine in the afternoon, dusk to the east
VIEW = ll(46.5, 30.5)                     # the camera looks down on Ukraine

def frame(u):
    T = tex()
    RW, RH = R.RW, R.RH
    # distance in Earth radii: from close to a dot, faster and faster
    d = 3.3 * math.exp(7.4 * u ** 1.45)
    speed = 7.4 * 1.45 * u ** 0.45        # d ln(d) / du
    fovy = 34.0
    TY = math.tan(math.radians(fovy) / 2); TX = TY * RW / RH
    pos = VIEW * d
    f = -VIEW; up0 = np.array([0, 0, 1.0]); r = np.cross(up0, f); r /= np.linalg.norm(r); upv = np.cross(f, r)
    # the stars: the sky in this direction (any fixed one), radially smeared as the speed grows
    mask = np.zeros((RH, RW), np.float32)
    bg = R.background(r, upv, f, TX, TY, mask, 2.2, 0.45, R.GAL @ R.rotz(1.1))
    streak = min(0.45, 0.010 * speed ** 1.7)
    if streak > 0.003:
        acc = np.zeros_like(bg); n = 28
        for k in range(n):
            s = 1 + streak * k / (n - 1)
            im = Image.fromarray(np.clip(bg * 255 / 2, 0, 255).astype(np.uint8))
            w2, h2 = int(RW * s), int(RH * s)
            im = im.resize((w2, h2), Image.BICUBIC).crop(((w2 - RW) // 2, (h2 - RH) // 2, (w2 - RW) // 2 + RW, (h2 - RH) // 2 + RH))
            acc += np.asarray(im, np.float32) / 255 * 2
        bg = acc / n * (1 + 2.5 * streak)
    img = bg
    # the Earth
    ys, xs = np.mgrid[0:RH, 0:RW].astype(np.float32)
    px = ((xs + 0.5) / RW * 2 - 1) * TX; py = (1 - (ys + 0.5) / RH * 2) * TY
    D = f[None, None, :] + px[..., None] * r + py[..., None] * upv
    D /= np.linalg.norm(D, axis=-1, keepdims=True)
    b = D @ pos; c = pos @ pos - 1.0
    disc = b * b - c
    hit = (disc > 0) & (b < 0)
    HS = 0.025
    h2 = pos @ pos - b * b
    near = (b < 0) & (h2 < (1 + HS * 4) ** 2)
    if near.any():
        idx = np.nonzero(near)
        Dn = D[idx]; bn = b[idx]; h2n = h2[idx]
        col = np.zeros((len(bn), 3), np.float32)
        hn = (disc[idx] > 0)
        # surface
        t = -bn[hn] - np.sqrt(np.maximum(disc[idx][hn], 0))
        P = pos + Dn[hn] * t[:, None]
        lat = np.arcsin(np.clip(P[:, 2], -1, 1)); lon = np.arctan2(P[:, 1], P[:, 0])
        mu = P @ SUN
        day = samp(T['day'], lat, lon); night = samp(T['night'], lat, lon); spec = samp(T['spec'], lat, lon); cl = samp(T['cl'], lat, lon)
        lit = np.clip(mu, 0, 1)[:, None]
        term = np.clip((mu + 0.06) / 0.16, 0, 1)[:, None]
        sunc = np.array([1.0, 0.97, 0.92])
        warm = np.clip(1 - mu / 0.25, 0, 1)[:, None] * term
        lightc = sunc * (1 - warm) + np.array([1.0, 0.62, 0.38]) * warm
        surf = day * lit * lightc * 1.6
        # the oceans' glint
        V = -Dn[hn]; Hh = SUN[None, :] + V; Hh /= np.linalg.norm(Hh, axis=1, keepdims=True)
        nh = np.clip((P * Hh).sum(1), 0, 1)
        surf += (spec * nh ** 120 * 1.2 * term[:, 0])[:, None] * sunc
        # city lights on the night side
        surf += night * np.clip(-mu * 6, 0, 1)[:, None] * np.array([1.0, 0.78, 0.5]) * 0.9
        # clouds
        clc = (cl * 0.95)[:, None]
        surf = surf * (1 - clc) + clc * lit * lightc * 1.7
        # the blue haze, stronger towards the limb
        path = np.sqrt(np.maximum((1 + HS) ** 2 - h2n[hn], 0)) - np.sqrt(np.maximum(1 - h2n[hn], 0))
        k = (0.06 * (path / HS) ** 1.5 * np.clip(mu + 0.15, 0, 1))[:, None]
        surf = surf * (1 - np.clip(k, 0, 0.6)) + np.array([0.35, 0.55, 1.0]) * k
        col[hn] = surf
        # the halo outside the limb
        ho = ~hn
        m = pos + Dn[ho] * (-bn[ho])[:, None]
        mm = m / np.linalg.norm(m, axis=1, keepdims=True)
        lm = np.clip((mm @ SUN + 0.15) / 0.5, 0, 1)
        path = 2 * np.sqrt(np.maximum((1 + HS) ** 2 - h2n[ho], 0))
        kk = 0.05 * (path / HS) ** 1.2 * lm + 0.02 * np.exp(-(np.sqrt(h2n[ho]) - 1) / (HS * 0.8)) * lm
        col[ho] = np.array([0.35, 0.55, 1.0]) * kk[:, None]
        sub = img[idx]
        cov = hn.astype(np.float32)[:, None]
        img[idx] = sub * (1 - cov) + col * cov + col * (1 - cov)
    # a point of light for the Earth when it gets smaller than a pixel or two
    rp = math.asin(min(1.0, 1 / d)) / (2 * TY / RH)
    if rp < 3:
        cx, cy = RW / 2, RH / 2
        yy, xx = np.mgrid[int(cy) - 12:int(cy) + 13, int(cx) - 12:int(cx) + 13]
        g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 2.2 ** 2)) * min(1.0, (3 - rp) / 2) * 1.4
        img[int(cy) - 12:int(cy) + 13, int(cx) - 12:int(cx) + 13] += g[..., None] * np.array([0.55, 0.75, 1.0])
    return R.finish(img, 0.8)

if __name__ == '__main__':
    out = '/tmp/claude-0/-home-user-Cloud/b5c5bcc1-0ba1-54c6-9bde-e14fb8831f2a/scratchpad/earth.jpg'
    us = [0.0, 0.3, 0.55, 0.75, 0.9, 1.0]
    ims = [frame(u).resize((240, 427)) for u in us]
    sh = Image.new('RGB', (240 * len(ims), 427))
    for k, im in enumerate(ims): sh.paste(im, (240 * k, 0))
    sh.save(out); print(out)
