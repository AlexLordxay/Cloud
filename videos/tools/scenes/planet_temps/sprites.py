# Planet sprites for «Термометр Сонячної системи»: each planet as a lit globe (NASA / Solar System Scope textures from
# planetarium/textures), limb darkening, a rim of air or a hot / frosty glow, Saturn with its rings.
#   python3 scenes/planet_temps/sprites.py  -> work/planet_temps/<name>.png (RGBA, 2x supersampled then reduced)
import math, os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
TEX = os.path.abspath(os.path.join(TOOLS, '..', '..', 'planetarium', 'textures'))
OUT = os.path.join(TOOLS, 'work', 'planet_temps'); os.makedirs(OUT, exist_ok=True)
L = np.array([-0.55, 0.42, 0.72]); L = L / np.linalg.norm(L)

def tex(name):
    return np.asarray(Image.open(os.path.join(TEX, name)).convert('RGB'), np.float32) / 255.0

def sample(T, lat, lon):
    h, w = T.shape[:2]
    x = ((lon / (2 * np.pi) + 0.5) % 1.0) * w - 0.5; y = np.clip((0.5 - lat / np.pi) * h - 0.5, 0, h - 1.001)
    x0 = np.floor(x).astype(int) % w; y0 = np.floor(y).astype(int); fx = (x - np.floor(x))[..., None]; fy = (y - y0)[..., None]
    x1 = (x0 + 1) % w; y1 = np.minimum(y0 + 1, h - 1)
    return (T[y0, x0] * (1 - fx) + T[y0, x1] * fx) * (1 - fy) + (T[y1, x0] * (1 - fx) + T[y1, x1] * fx) * fy

def globe(name, R, lon0=0.0, tilt=0.0, rim=(0.5, 0.7, 1.0), rim_k=0.6, glow=None, glow_k=0.0, clouds=None,
          ring=None, pad=1.25, soft=0.0, sat=1.1, gain=1.0, night=None):
    """R: radius px (final). Returns RGBA image."""
    s = 2; Rs = R * s
    hw = int(Rs * (ring[1] * 1.02 if ring else pad)); hh = int(Rs * pad)
    yy, xx = np.mgrid[-hh:hh, -hw:hw].astype(np.float32) + 0.5
    x = xx / Rs; y = -yy / Rs
    r2 = x * x + y * y
    inside = r2 < 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    # the body frame: tilt the axis towards the viewer's right, turn by lon0
    ct, st = math.cos(tilt), math.sin(tilt)
    bx = x * ct + y * st; by = -x * st + y * ct; bz = z
    lat = np.arcsin(np.clip(by, -1, 1)); lon = np.arctan2(bx, bz) + lon0
    T = tex(name)
    col = sample(T, lat, lon) ** 2.2
    if clouds is not None:
        C = np.asarray(Image.open(os.path.join(TEX, clouds)).convert('L'), np.float32)[..., None].repeat(3, 2) / 255.0
        c = sample(C, lat, lon)[..., :1]
        col = col * (1 - c * 0.85) + 0.85 * c
    ndl = x * L[0] + y * L[1] + z * L[2]
    lit = np.clip((ndl + soft) / (1 + soft), 0, 1) ** 0.85
    limb = 0.55 + 0.45 * z ** 0.6
    shade = (lit * 1.05 + 0.05) * limb * gain
    img = col * shade[..., None]
    if night is not None:
        # the night side glows in its own colour (Mercury's frozen dark side)
        nk = np.clip(-ndl * 1.4, 0, 1)[..., None] * night[1]
        img = img + np.array(night[0]) * nk * z[..., None]
    # air: a thin bright rim on the lit side
    rimk = np.clip(1 - z, 0, 1) ** 2.2 * np.clip(ndl + 0.35, 0, 1)
    img = img + np.array(rim) * rimk[..., None] * rim_k
    l = img.mean(2, keepdims=True); img = np.clip(l + (img - l) * sat, 0, None)
    rgb = np.zeros((2 * hh, 2 * hw, 3), np.float32); a = np.zeros((2 * hh, 2 * hw), np.float32)
    rgb[inside] = img[inside]; a[inside] = 1.0
    # antialiased edge
    edge = np.clip((1.0 - np.sqrt(r2)) * Rs + 0.5, 0, 1); a = np.maximum(a * edge, 0) ; 
    # glow outside the disc (heat / frost / air)
    d = np.sqrt(r2)
    if glow is not None:
        g = np.exp(-np.clip(d - 1.0, 0, None) / 0.10) * (d > 0.98) * glow_k
        g += np.exp(-np.clip(d - 1.0, 0, None) / 0.035) * (d > 0.98) * glow_k * 0.8
        out_a = np.clip(g, 0, 1)
        rgb = rgb * a[..., None] + np.array(glow) * g[..., None] * (1 - a[..., None])
        a = np.clip(a + out_a * (1 - a), 0, 1)
        rgb = np.where(a[..., None] > 1e-4, rgb / np.maximum(a[..., None], 1e-4), 0)
    if ring is not None:
        rin, rout, tilt_r, rtex = ring
        RT = np.asarray(Image.open(os.path.join(TEX, rtex)).convert('RGBA'), np.float32)[0] / 255.0   # (W, 4) by radius
        # ring plane: seen at tilt_r (rad) from edge-on; ellipse y' = y / sin(tilt_r) in the tilted frame
        rx_ = x * ct + y * st; ry_ = (-x * st + y * ct) / math.sin(tilt_r)
        rr = np.sqrt(rx_ ** 2 + ry_ ** 2)
        u = np.clip((rr - rin) / (rout - rin), 0, 0.999)
        ok = (rr > rin) & (rr < rout)
        ti = (u * (RT.shape[0] - 1)).astype(int)
        rc = RT[ti, :3] ** 2.2 * 1.1; ra = RT[ti, 3] * ok
        # in front of the planet where the ring's near half is (ry_ < 0 is the near side, below the centre)
        front = ry_ < 0
        # the planet's shadow on the far side of the rings (roughly behind the planet from the light)
        sh = (np.abs(rx_ + 0.25) < 0.95) & ~front & (rr < 1.6)
        rc = rc * np.where(sh, 0.35, 1.0)[..., None] * (0.9 + 0.2 * (rx_ < 0))[..., None]
        behind = ~front & (a > 0.99)
        ra_eff = np.where(behind, 0.0, ra)
        rgb = rgb * (1 - ra_eff[..., None]) + rc * ra_eff[..., None]
        a = np.clip(a + ra_eff * (1 - a), 0, 1)
    out = np.dstack([np.clip(rgb, 0, 1) ** (1 / 2.2), a])
    im = Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')
    return im.resize((im.width // s, im.height // s), Image.LANCZOS)

P = {
    'sun':     dict(name='sun.jpg', R=190, rim=(1.0, 0.8, 0.4), rim_k=0.4, glow=(1.0, 0.55, 0.15), glow_k=1.3, soft=40.0, sat=1.15, gain=1.25, pad=1.45),
    'venus':   dict(name='venus_atmosphere.jpg', R=170, rim=(1.0, 0.8, 0.5), rim_k=0.7, glow=(1.0, 0.45, 0.12), glow_k=0.9, soft=0.25, sat=1.15),
    'mercury': dict(name='mercury.jpg', R=120, lon0=1.0, rim=(0.6, 0.6, 0.6), rim_k=0.2, glow=(1.0, 0.55, 0.2), glow_k=0.45, night=((0.10, 0.22, 0.55), 0.55)),
    'earth':   dict(name='earth_day.jpg', R=150, lon0=-1.2, tilt=0.35, clouds='earth_clouds.png', rim=(0.35, 0.6, 1.0), rim_k=1.1, glow=(0.3, 0.55, 1.0), glow_k=0.55, sat=1.15),
    'mars':    dict(name='mars.jpg', R=115, lon0=0.6, rim=(1.0, 0.6, 0.45), rim_k=0.5, glow=(0.9, 0.45, 0.3), glow_k=0.25, sat=1.12),
    'jupiter': dict(name='jupiter.jpg', R=210, lon0=0.3, tilt=0.05, rim=(1.0, 0.9, 0.75), rim_k=0.3, soft=0.15, sat=1.12),
    'saturn':  dict(name='saturn.jpg', R=165, tilt=0.45, rim=(1.0, 0.92, 0.75), rim_k=0.3, soft=0.15, ring=(1.24, 2.27, math.radians(24), 'saturn_ring.png')),
    'uranus':  dict(name='uranus.jpg', R=135, tilt=1.2, rim=(0.6, 0.95, 1.0), rim_k=0.8, glow=(0.5, 0.85, 1.0), glow_k=0.5, soft=0.15, sat=1.2),
    'neptune': dict(name='neptune.jpg', R=135, lon0=0.8, rim=(0.4, 0.6, 1.0), rim_k=0.9, glow=(0.35, 0.55, 1.0), glow_k=0.55, soft=0.15, sat=1.2),
    'pluto':   dict(name='pluto.jpg', R=95, lon0=math.pi, rim=(0.8, 0.85, 1.0), rim_k=0.3, glow=(0.6, 0.8, 1.0), glow_k=0.4),
}
if __name__ == '__main__':
    import sys
    for k in (sys.argv[1:] or P):
        globe(**P[k]).save(os.path.join(OUT, k + '.png')); print(k)
