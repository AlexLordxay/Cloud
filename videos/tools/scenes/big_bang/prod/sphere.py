# A textured sphere seen from outside (orthographic-ish, with a little perspective-free shading): for every pixel of
# its disc the surface normal -> (longitude, latitude) after a rotation -> the equirectangular texture (cv2.remap).
import math
import numpy as np
import cv2


def rot(yaw, pitch, roll=0.0):
    cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def draw(tex, W, H, cx, cy, R, M, limb=0.25):
    """tex: equirect HxWx3 float32 (lon 0..360 across, lat +90 top); returns (image, alpha)"""
    x0, x1 = int(max(cx - R - 2, 0)), int(min(cx + R + 2, W)); y0, y1 = int(max(cy - R - 2, 0)), int(min(cy + R + 2, H))
    img = np.zeros((H, W, 3), np.float32); al = np.zeros((H, W), np.float32)
    if x1 <= x0 or y1 <= y0: return img, al
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xx - cx) / R; ny = -(yy - cy) / R
    r2 = nx * nx + ny * ny
    inside = r2 < 1.0
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    v = np.stack([nx, ny, nz], -1) @ M                 # into the texture's frame
    lon = np.arctan2(v[..., 0], v[..., 2]); lat = np.arcsin(np.clip(v[..., 1], -1, 1))
    th, tw = tex.shape[:2]
    mx = ((lon / (2 * math.pi)) % 1.0) * tw; my = (0.5 - lat / math.pi) * th
    s = cv2.remap(tex, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    edge = np.clip((1 - np.sqrt(r2)) * R / 1.5, 0, 1)            # antialiased rim
    shade = (1 - limb) + limb * nz
    img[y0:y1, x0:x1] = s * (shade * edge * inside)[..., None]
    al[y0:y1, x0:x1] = edge * inside
    return img, al
