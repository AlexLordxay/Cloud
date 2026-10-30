# Stick-figure characters for little cartoons: a jointed "puppet" drawn with Pillow, posed by angles, plus simple props.
# A figure is drawn once per frame from a pose; animation = poses blended over time (lerp_pose). Drawn at SS× and scaled
# down for smooth lines.
#
#   from characters.stick import Figure, POSES, lerp_pose, Canvas
#   cv = Canvas(1080, 1920); GUY.draw(cv, POSES['sit_phone'], (540, 1200)); img = cv.image()
#
# Angles are in degrees, measured from straight down, positive = towards screen right (so an arm at 0 hangs down,
# at 90 points right, at 180 points up). Each limb's lower part is relative to its upper part.
import math
from dataclasses import dataclass, field
from PIL import Image, ImageDraw

SS = 2                                   # supersampling
INK = (238, 241, 248)                    # the lines
BG = (10, 13, 26)                        # Небозвід night
SUN = (243, 185, 100)
ICE = (156, 194, 255)
PINK = (243, 140, 160)


class Canvas:
    """An RGB canvas drawn at SS× size; image() gives the final, smoothed frame."""
    def __init__(self, w, h, bg=BG):
        self.w, self.h = w, h
        self.img = Image.new('RGB', (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.img)

    def P(self, x, y):
        return (x * SS, y * SS)

    def line(self, pts, w, col=INK):
        pts = [self.P(*p) for p in pts]
        self.d.line(pts, fill=col, width=int(w * SS), joint='curve')
        r = w * SS / 2                                          # round caps
        for x, y in (pts[0], pts[-1]):
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=col)

    def circle(self, c, r, w=None, col=INK, fill=None):
        x, y = self.P(*c); r *= SS
        self.d.ellipse((x - r, y - r, x + r, y + r), outline=None if w is None else col, width=0 if w is None else int(w * SS),
                       fill=fill if fill is not None else (col if w is None else None))

    def ellipse(self, box, col=INK, fill=None, w=None):
        x0, y0, x1, y1 = box
        self.d.ellipse((x0 * SS, y0 * SS, x1 * SS, y1 * SS), fill=fill, outline=col if w else None, width=int((w or 0) * SS))

    def rrect(self, box, r, col=INK, fill=None, w=None):
        x0, y0, x1, y1 = box
        self.d.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), radius=r * SS, fill=fill,
                                 outline=col if w else None, width=int((w or 0) * SS))

    def arc(self, box, a0, a1, w, col=INK):
        x0, y0, x1, y1 = box
        self.d.arc((x0 * SS, y0 * SS, x1 * SS, y1 * SS), a0, a1, fill=col, width=int(w * SS))

    def poly(self, pts, fill, col=None, w=None):
        self.d.polygon([self.P(*p) for p in pts], fill=fill, outline=col, width=int((w or 0) * SS) if w else 1)

    def text(self, xy, s, font, fill=INK, anchor='mm'):
        self.d.text(self.P(*xy), s, font=font, fill=fill, anchor=anchor)

    def image(self):
        return self.img.resize((self.w, self.h), Image.LANCZOS)


def _dir(a):
    """Unit vector for an angle measured from straight down, positive towards screen right."""
    r = math.radians(a)
    return math.sin(r), math.cos(r)


def _add(p, a, l):
    dx, dy = _dir(a)
    return (p[0] + dx * l, p[1] + dy * l)


# A pose: body lean, head tilt, arms (shoulder, elbow) and legs (hip, knee) for the figure's left (L, screen right when
# facing us) and right (R); face: the expression; look: -1..1 where the eyes look.
NEUTRAL = dict(lean=0, head=0, sL=-20, eL=-10, sR=20, eR=10, hL=-8, kL=0, hR=8, kR=0, face='smile', look=0, crouch=0)

POSES = {
    'stand': dict(NEUTRAL),
    'wave': dict(NEUTRAL, sR=150, eR=30, face='grin'),
    'shrug': dict(NEUTRAL, sL=-60, eL=-110, sR=60, eR=110, head=-8, face='meh'),
    'facepalm': dict(NEUTRAL, sR=150, eR=62, head=14, lean=5, face='flat'),
    'point': dict(NEUTRAL, sR=95, eR=0, face='o'),
    'shock': dict(NEUTRAL, sL=-150, eL=-20, sR=150, eR=20, face='o'),
    'sad': dict(NEUTRAL, lean=6, head=22, sL=-12, eL=0, sR=12, eR=0, face='sad', look=0.3),
    # sitting (on a toilet, a chair): the thighs forward, the shins down; phone held up in front of the face
    'sit_phone': dict(NEUTRAL, hL=-82, kL=82, hR=-88, kR=88, sL=-150, eL=95, sR=-130, eR=85, face='grin', look=-0.6),
    'sit_sad': dict(NEUTRAL, hL=-82, kL=82, hR=-88, kR=88, lean=-14, head=-22, sL=-60, eL=40, sR=-50, eR=30, face='sad', look=-0.5),
    # selfie from behind, bent forward (the "booty" video)
    'twerk': dict(NEUTRAL, lean=-48, head=30, hL=4, kL=-14, hR=14, kR=-18, sL=-30, eL=10, sR=-205, eR=-15, face='grin', look=-0.9),
}


def lerp_pose(a, b, t):
    """Blend two poses; t in 0..1 (eased by the caller). Text fields switch at the middle."""
    out = {}
    for k in a:
        if isinstance(a[k], (int, float)) and isinstance(b.get(k), (int, float)):
            out[k] = a[k] + (b[k] - a[k]) * t
        else:
            out[k] = a[k] if t < 0.5 else b.get(k, a[k])
    return out


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


@dataclass
class Figure:
    """A stick figure. size = body height in px (head top to feet, standing). Extras: hair, hips (a bigger behind), colour."""
    size: float = 400
    col: tuple = INK
    hair: str = ''                       # '' | 'ponytail' | 'bun'
    behind: float = 0.0                  # 0: a stick; >0: a round behind at the hips (×head size)
    accent: tuple = SUN                  # hair / details
    width: float = 0                     # line width (0: from size)
    face_col: tuple = BG
    dress: tuple = None                  # a dress colour (front views)

    def parts(self, pose, at):
        """Joint positions for a pose; `at` = the pelvis."""
        s = self.size
        L = dict(torso=0.30 * s, neck=0.05 * s, head=0.085 * s, up=0.16 * s, low=0.15 * s, thigh=0.21 * s, shin=0.21 * s)
        p = at
        lean = pose['lean']
        chest = _add(p, 180 + lean, L['torso'])
        neck = _add(chest, 180 + lean + pose['head'] * 0.3, L['neck'])
        head = _add(neck, 180 + lean + pose['head'], L['head'])
        sh = _add(p, 180 + lean, L['torso'] * 0.92)
        arms = {}
        for side in 'LR':
            u = lean + pose['s' + side]
            el = _add(sh, u, L['up'])
            ha = _add(el, u + pose['e' + side], L['low'])
            arms[side] = (sh, el, ha)
        legs = {}
        for side in 'LR':
            u = pose['h' + side]
            kn = _add(p, u, L['thigh'])
            ft = _add(kn, u + pose['k' + side], L['shin'])
            legs[side] = (p, kn, ft)
        return dict(pelvis=p, chest=chest, neck=neck, head=head, hr=L['head'], arms=arms, legs=legs)

    def draw(self, cv, pose, at, held=None):
        """Draw the figure; `held` = a function(cv, hand_xy, angle) drawing a prop in the right hand (e.g. a phone)."""
        J = self.parts(pose, at)
        w = self.width or max(3.0, self.size * 0.022)
        bent = abs(pose['lean']) > 25
        for side in 'LR':
            cv.line(J['legs'][side], w, self.col)
        if self.behind and bent:                                # side view, bent: a round behind sticking out at the back
            r = J['hr'] * self.behind
            back = -1 if pose['lean'] < 0 else 1                # the back is opposite to where the body bends
            cx, cy = J['pelvis'][0] + back * r * 0.55, J['pelvis'][1] - r * 0.05
            cv.circle((cx + back * r * 0.25, cy + r * 0.35), r * 0.62, fill=self.accent, col=self.accent)
            cv.circle((cx, cy - r * 0.05), r * 0.72, fill=self.accent, col=self.accent)
        if self.dress and not bent:                             # front view: a dress, from the waist to above the knees
            top = _add(J['pelvis'], 180 + pose['lean'], self.size * 0.12)
            hw = self.size * (0.05 + 0.03 * (self.behind > 0))
            bw = self.size * 0.13
            by = J['pelvis'][1] + self.size * 0.09
            cv.poly([(top[0] - hw, top[1]), (top[0] + hw, top[1]), (J['pelvis'][0] + bw, by), (J['pelvis'][0] - bw, by)],
                    fill=self.dress, col=self.dress)
        cv.line([J['pelvis'], J['neck']], w, self.col)
        for side in 'LR':
            cv.line(J['arms'][side], w, self.col)
        if held:
            sh, el, ha = J['arms']['R']
            held(cv, ha, math.degrees(math.atan2(ha[0] - el[0], ha[1] - el[1])))
        self._head(cv, J, pose, w)
        return J

    def _head(self, cv, J, pose, w):
        c, r = J['head'], J['hr']
        if self.hair == 'ponytail':                             # a tail swinging behind the head
            tail = [(c[0] - r * 0.8, c[1] - r * 0.4), (c[0] - r * 1.5, c[1] + r * 0.1), (c[0] - r * 1.3, c[1] + r * 0.9)]
            cv.line(tail, w * 1.6, self.accent)
        cv.circle(c, r, fill=self.face_col, col=self.col)
        cv.circle(c, r, w=w, col=self.col)
        if self.hair:                                           # a fringe
            cv.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r), 190, 350, w * 1.4, self.accent)
        # the face: two dots and a mouth, shifted where the eyes look
        lx = pose.get('look', 0) * r * 0.35
        e = r * 0.13
        for dx in (-0.35, 0.35):
            cv.circle((c[0] + lx + dx * r, c[1] - r * 0.12), e, col=self.col)
        mx, my, mw = c[0] + lx, c[1] + r * 0.35, r * 0.42
        face = pose.get('face', 'smile')
        if face in ('smile', 'grin'):
            cv.arc((mx - mw, my - mw * 0.9, mx + mw, my + mw * 0.6), 20, 160, w * (1.0 if face == 'smile' else 1.3), self.col)
        elif face == 'sad':
            cv.arc((mx - mw * 0.8, my - mw * 0.1, mx + mw * 0.8, my + mw * 1.0), 200, 340, w, self.col)
        elif face == 'o':
            cv.circle((mx, my + r * 0.02), r * 0.15, w=w * 0.8, col=self.col)
        else:                                                   # 'flat', 'meh'
            cv.line([(mx - mw * 0.6, my + (r * 0.05 if face == 'meh' else 0)), (mx + mw * 0.6, my - (r * 0.05 if face == 'meh' else 0))], w * 0.8, self.col)


# ---------- props ----------

def phone(cv, hand, ang, scale=1.0, screen=(40, 50, 80)):
    """A phone in a hand, upright, its screen towards the viewer side."""
    w, h = 34 * scale, 60 * scale
    x, y = hand
    cv.rrect((x - w / 2, y - h * 0.85, x + w / 2, y + h * 0.15), 7 * scale, fill=(25, 28, 40), col=INK, w=2.5 * scale)
    cv.rrect((x - w / 2 + 4 * scale, y - h * 0.85 + 6 * scale, x + w / 2 - 4 * scale, y + h * 0.15 - 6 * scale), 4 * scale, fill=screen)


def toilet(cv, at, s=1.0, col=INK):
    """A toilet seen from the side; `at` = the middle of the seat top (where a sitting pelvis goes)."""
    x, y = at
    w = 3.5 * s
    cv.rrect((x + 40 * s, y - 150 * s, x + 95 * s, y - 10 * s), 10 * s, col=col, fill=(200, 210, 228), w=w)       # tank
    cv.rrect((x - 85 * s, y - 8 * s, x + 70 * s, y + 18 * s), 9 * s, col=col, fill=(225, 232, 245), w=w)           # seat
    cv.poly([(x - 70 * s, y + 18 * s), (x + 60 * s, y + 18 * s), (x + 40 * s, y + 110 * s), (x - 30 * s, y + 110 * s)],
            fill=(210, 220, 238), col=col, w=w)                                                                      # bowl
    cv.rrect((x - 45 * s, y + 105 * s, x + 55 * s, y + 125 * s), 6 * s, col=col, fill=(200, 210, 228), w=w)          # foot


def floor(cv, y, col=(60, 70, 100)):
    cv.line([(0, y), (cv.w, y)], 3, col)


def tiles(cv, y0, y1, step=90, col=(28, 34, 56)):
    """A bathroom wall of tiles between y0 and y1."""
    for y in range(int(y0), int(y1), step):
        cv.line([(0, y), (cv.w, y)], 2, col)
    for x in range(0, cv.w + step, step):
        cv.line([(x, y0), (x, y1)], 2, col)
