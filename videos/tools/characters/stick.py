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
INK = (22, 22, 26)                       # the lines: near-black
BG = (255, 255, 255)                     # paper white (the author, 30.10)
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
    # sitting at a desk, facing right, hands forward on the keyboard
    'sit_desk': dict(NEUTRAL, hL=82, kL=-82, hR=88, kR=-88, lean=8, head=4, sL=48, eL=6, sR=54, eR=2, face='smile', look=0.7),
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
    beard: tuple = None                  # a beard colour

    def parts(self, pose, at):
        """Joint positions for a pose; `at` = the pelvis."""
        s = self.size
        L = dict(torso=0.30 * s, neck=0.05 * s, head=0.105 * s, up=0.16 * s, low=0.15 * s, thigh=0.21 * s, shin=0.21 * s)
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
        w = self.width or max(4.0, self.size * 0.032)   # bold lines (the author, 30.10)
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
        if self.hair == 'braid':                                # a braid hanging from the back of the head
            back = -1 if pose.get('look', 0) >= 0 else 1        # the back of the head is opposite to where he looks
            bx, by = c[0] + back * r * 0.85, c[1] - r * 0.05
            for k in range(6):                                  # plaits: alternating little ovals going down
                ox = bx + back * (r * 0.12 * k) + (r * 0.1 if k % 2 else -r * 0.1)
                oy = by + r * 0.32 * k
                cv.ellipse((ox - r * 0.2, oy - r * 0.17, ox + r * 0.2, oy + r * 0.17), fill=self.accent, col=self.col, w=w * 0.45)
            tip = (bx + back * r * 0.75, by + r * 2.0)
            cv.line([(tip[0] - r * 0.12, tip[1] - r * 0.12), (tip[0] + r * 0.12, tip[1] + r * 0.12)], w * 0.7, self.col)
        if self.hair == 'dreads':                               # dreadlocks: thick rope-like strands, mostly at the back
            sway = math.sin(pose.get('t', 0) * 2.3)
            back = -1 if pose.get('look', 0) >= 0 else 1
            for k in range(8):
                a0 = math.radians(back * (35 + k * 17))         # from the top over the back of the head
                sx, sy = c[0] + math.sin(a0) * r * 0.9, c[1] - math.cos(a0) * r * 0.9
                ln = r * (1.35 + 0.3 * ((k * 5) % 3))
                pts = [(sx, sy)]
                for j in range(1, 6):
                    u = j / 5
                    pts.append((sx + back * r * (0.25 + 0.05 * k) * u + math.sin(u * 4 + k + sway) * r * 0.07, sy + ln * u))
                cv.line(pts, w * 1.5, self.col)
                cv.line(pts, w * 0.85, self.accent)
                for j in (2, 4):                               # the rope's bands
                    px, py = pts[j]
                    cv.line([(px - w * 0.5, py), (px + w * 0.5, py)], w * 0.35, self.col)
        if self.hair == 'ponytail':                             # a tail swinging behind the head
            tail = [(c[0] - r * 0.8, c[1] - r * 0.4), (c[0] - r * 1.5, c[1] + r * 0.1), (c[0] - r * 1.3, c[1] + r * 0.9)]
            cv.line(tail, w * 1.6, self.accent)
        cv.circle(c, r, fill=self.face_col, col=self.col)
        cv.circle(c, r, w=w * 0.85, col=self.col)
        if self.hair in ('ponytail', 'bun'):                     # a fringe
            cv.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r), 195, 345, w * 1.2, self.accent)
        elif self.hair == 'dreads':                             # a thick cap on top, the strands start from it
            cv.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r), 180, 360, w * 1.9, self.accent)
            cv.arc((c[0] - r * 1.04, c[1] - r * 1.04, c[0] + r * 1.04, c[1] + r * 1.04), 180, 360, w * 0.5, self.col)
        elif self.hair == 'braid':                              # hair combed back: a cap over the top of the head
            cv.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r), 185, 355, w * 1.5, self.accent)
        if self.beard:                                          # a short beard along the jaw
            k = r - w * 0.8                                     # a thin band inside the jaw line (inside the outline)
            cv.arc((c[0] - k, c[1] - k, c[0] + k, c[1] + k), 25, 155, w * 0.75, self.beard)
        # the face: two dots and a mouth, shifted where the eyes look
        lx = pose.get('look', 0) * r * 0.35
        e = r * 0.11
        for dx in (-0.35, 0.35):
            cv.circle((c[0] + lx + dx * r, c[1] - r * 0.12), e, col=self.col)
        mx, my, mw = c[0] + lx, c[1] + r * 0.35, r * 0.42
        face = pose.get('face', 'smile')
        if face in ('smile', 'grin'):
            fw = w * 0.6                                         # the face is drawn thinner than the body
            if face == 'smile':                                  # a thin, narrow arc (wide thick ones read as a moustache)
                cv.arc((mx - mw * 0.75, my - mw * 0.75, mx + mw * 0.75, my + mw * 0.55), 30, 150, fw, self.col)
            else:                                                # 'grin': an open laughing mouth, a filled half-circle
                cv.d.pieslice(((mx - mw * 0.7) * SS, (my - mw * 0.6) * SS, (mx + mw * 0.7) * SS, (my + mw * 0.6) * SS), 0, 180, fill=self.col)
        elif face == 'sad':
            cv.arc((mx - mw * 0.8, my - mw * 0.1, mx + mw * 0.8, my + mw * 1.0), 205, 335, w * 0.6, self.col)
        elif face == 'o':
            cv.circle((mx, my + r * 0.02), r * 0.14, w=w * 0.5, col=self.col)
        else:                                                   # 'flat', 'meh'
            cv.line([(mx - mw * 0.6, my + (r * 0.05 if face == 'meh' else 0)), (mx + mw * 0.6, my - (r * 0.05 if face == 'meh' else 0))], w * 0.55, self.col)


# ---------- props ----------

def phone(cv, hand, ang, scale=1.0, screen=(120, 170, 230)):
    """A phone in a hand, upright, its screen towards the viewer side."""
    w, h = 34 * scale, 60 * scale
    x, y = hand
    cv.rrect((x - w / 2, y - h * 0.85, x + w / 2, y + h * 0.15), 7 * scale, fill=(25, 28, 40), col=INK, w=4 * scale)
    cv.rrect((x - w / 2 + 4 * scale, y - h * 0.85 + 6 * scale, x + w / 2 - 4 * scale, y + h * 0.15 - 6 * scale), 4 * scale, fill=screen)


def toilet(cv, at, s=1.0, col=INK):
    """A toilet seen from the side; `at` = the middle of the seat top (where a sitting pelvis goes)."""
    x, y = at
    w = 6 * s
    cv.rrect((x + 40 * s, y - 150 * s, x + 95 * s, y - 10 * s), 10 * s, col=col, fill=(236, 240, 246), w=w)       # tank
    cv.rrect((x - 85 * s, y - 8 * s, x + 70 * s, y + 18 * s), 9 * s, col=col, fill=(250, 251, 253), w=w)           # seat
    cv.poly([(x - 70 * s, y + 18 * s), (x + 60 * s, y + 18 * s), (x + 40 * s, y + 110 * s), (x - 30 * s, y + 110 * s)],
            fill=(240, 243, 248), col=col, w=w)                                                                      # bowl
    cv.rrect((x - 45 * s, y + 105 * s, x + 55 * s, y + 125 * s), 6 * s, col=col, fill=(236, 240, 246), w=w)          # foot


def floor(cv, y, col=(180, 184, 194)):
    cv.line([(0, y), (cv.w, y)], 3, col)


def tiles(cv, y0, y1, step=90, col=(226, 230, 238)):
    """A bathroom wall of tiles between y0 and y1."""
    for y in range(int(y0), int(y1), step):
        cv.line([(0, y), (cv.w, y)], 2, col)
    for x in range(0, cv.w + step, step):
        cv.line([(x, y0), (x, y1)], 2, col)


def phone_side(cv, hand, scale=1.0, face=1, screen=(150, 200, 250)):
    """A phone held up to film oneself, seen from behind at an angle: the dark back with the camera, and a sliver of the
    lit screen on the edge turned towards the face (face=1: the face is to the right of the phone, -1: to the left)."""
    x, y = hand
    w, h, sk = 26 * scale, 62 * scale, 7 * scale                # narrow (turned), a little skewed by perspective
    top, bot = y - h * 0.85, y + h * 0.15
    back = [(x - w / 2, top + sk), (x + w / 2, top), (x + w / 2, bot), (x - w / 2, bot - sk)]
    if face < 0: back = [(2 * x - px, py) for px, py in back]
    # the screen's edge: a lit strip on the side towards the face
    ex = x + face * w / 2
    strip = [(ex, top - (0 if face > 0 else sk) + 3 * scale), (ex + face * 9 * scale, top + 4 * scale),
             (ex + face * 9 * scale, bot - 6 * scale), (ex, bot - (0 if face > 0 else sk) - 3 * scale)]
    cv.poly(strip, fill=screen, col=INK, w=3 * scale)
    cv.poly(back, fill=(46, 48, 58), col=INK, w=4 * scale)
    cx = x - face * w * 0.18                                    # the camera block, near the top
    cv.rrect((cx - 8 * scale, top + 9 * scale, cx + 8 * scale, top + 27 * scale), 4 * scale, fill=(30, 31, 38))
    cv.circle((cx, top + 14 * scale), 3 * scale, col=(120, 130, 150))
    cv.circle((cx, top + 22 * scale), 3 * scale, col=(120, 130, 150))


def window(cv, box, t=0.0, sky=(196, 226, 255), body=None, night=0.0, clouds=True):
    """A window: a frame with a cross, sky and a slowly drifting cloud. body = (x, y, kind) puts the Sun ('sun') or the
    Moon ('moon') in the sky; night (0..1) dims the clouds and lights the stars."""
    x0, y0, x1, y1 = box
    cv.rrect(box, 14, fill=sky, col=INK, w=7)
    if night > 0.3:
        for k in range(22):                                       # stars
            sx, sy = x0 + 14 + (k * 53) % (x1 - x0 - 28), y0 + 14 + (k * 37) % (y1 - y0 - 28)
            cv.circle((sx, sy), 3.5, col=(255, 255, 240))
    if body:
        bx, by, kind = body
        if x0 + 30 < bx < x1 - 30 and y0 + 30 < by < y1 - 30:
            if kind == 'sun':
                cv.circle((bx, by), 38, col=(255, 200, 60))
                for k in range(8):
                    a = k * math.pi / 4
                    cv.line([(bx + math.cos(a) * 48, by + math.sin(a) * 48), (bx + math.cos(a) * 62, by + math.sin(a) * 62)], 5, (240, 170, 40))
            else:
                cv.circle((bx, by), 34, col=(244, 242, 220))
                cv.circle((bx + 15, by - 9), 29, col=sky)        # a crescent
    cx = x0 + ((t * 18) % (x1 - x0 + 160)) - 80               # the cloud drifts across
    cc = tuple(int(255 - (255 - 120) * night) for _ in range(3))
    for dx, dy, r in ((0, 0, 28), (30, -12, 34), (64, 2, 26)) if clouds else ():
        if x0 + 10 < cx + dx < x1 - 10:
            cv.circle((cx + dx, y0 + (y1 - y0) * 0.38 + dy), r, col=cc)
    cv.rrect(box, 14, col=INK, w=7)
    cv.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], 7)
    cv.line([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], 7)
    cv.rrect((x0 - 16, y1 - 4, x1 + 16, y1 + 14), 6, fill=(240, 242, 247), col=INK, w=5)   # the sill


def lamp(cv, x, y, s=1.0, t=0.0):
    """A ceiling lamp hanging on a cord: shade, bulb and a few light rays; it sways a little."""
    sway = 4 * math.sin(t * 1.3)
    cv.line([(x, -10), (x + sway, y - 40 * s)], 4)
    bx = x + sway
    cv.poly([(bx - 22 * s, y - 40 * s), (bx + 22 * s, y - 40 * s), (bx + 60 * s, y), (bx - 60 * s, y)], fill=(255, 210, 120), col=INK, w=5)
    cv.circle((bx, y + 10 * s), 16 * s, col=INK, fill=(255, 241, 190))
    cv.circle((bx, y + 10 * s), 16 * s, w=4, col=INK)
    for a in (-50, -25, 0, 25, 50):                              # rays
        dx, dy = math.sin(math.radians(a)), math.cos(math.radians(a))
        cv.line([(bx + dx * 38 * s, y + 10 * s + dy * 38 * s), (bx + dx * 60 * s, y + 10 * s + dy * 60 * s)], 4, (230, 180, 80))


def washer(cv, box, t=0.0):
    """A washing machine: the body, a panel with a knob and buttons, the round door with the drum spinning inside."""
    x0, y0, x1, y1 = box
    w = x1 - x0
    cv.rrect(box, 18, fill=(246, 248, 252), col=INK, w=7)
    cv.line([(x0, y0 + w * 0.22), (x1, y0 + w * 0.22)], 5)
    cv.circle((x0 + w * 0.2, y0 + w * 0.11), w * 0.06, fill=(255, 255, 255), col=INK)
    cv.circle((x0 + w * 0.2, y0 + w * 0.11), w * 0.06, w=4, col=INK)
    for k in range(3):
        cv.rrect((x0 + w * (0.45 + k * 0.14), y0 + w * 0.08, x0 + w * (0.55 + k * 0.14), y0 + w * 0.14), 4, fill=(200, 210, 230), col=INK, w=3)
    c = (x0 + w / 2, y0 + w * 0.22 + (y1 - y0 - w * 0.22) / 2)
    R = w * 0.33
    cv.circle(c, R, fill=(210, 222, 240), col=INK)
    cv.circle(c, R, w=7, col=INK)
    cv.circle(c, R * 0.78, fill=(170, 195, 230), col=(170, 195, 230))
    for k in range(3):                                         # the spinning laundry
        a = t * 9 + k * 2.1
        cv.circle((c[0] + math.cos(a) * R * 0.45, c[1] + math.sin(a) * R * 0.45), R * 0.18, fill=[(240, 140, 160), (255, 214, 120), (140, 200, 170)][k])
    cv.circle(c, R * 0.78, w=4, col=INK)
    cv.rrect((x0 + w * 0.08, y1 - 4, x0 + w * 0.2, y1 + 10), 3, fill=INK)        # feet
    cv.rrect((x1 - w * 0.2, y1 - 4, x1 - w * 0.08, y1 + 10), 3, fill=INK)


def paper_roll(cv, c, s=1.0):
    """A toilet-paper roll on a wall holder, a strip hanging down."""
    x, y = c
    cv.line([(x - 40 * s, y - 34 * s), (x + 40 * s, y - 34 * s)], 6)
    cv.rrect((x - 34 * s, y - 34 * s, x + 34 * s, y + 30 * s), 12 * s, fill=(255, 255, 255), col=INK, w=6)
    cv.rrect((x + 18 * s, y, x + 34 * s, y + 80 * s), 4 * s, fill=(255, 255, 255), col=INK, w=5)
    cv.ellipse((x - 12 * s, y - 14 * s, x + 12 * s, y + 10 * s), col=INK, w=5)


def curtains(cv, box, open_=0.0, col=(250, 214, 140)):
    """Curtains on both sides of a window box (drawn after the window); a rod above."""
    x0, y0, x1, y1 = box
    cv.line([(x0 - 60, y0 - 26), (x1 + 60, y0 - 26)], 8)
    w = 70
    for side in (-1, 1):
        xa = x0 - 50 if side < 0 else x1 - w + 50
        pts = [(xa, y0 - 26), (xa + w, y0 - 26)]
        for k in range(9):                                       # a wavy lower edge, gathered to the side
            yy = y0 - 26 + (y1 - y0 + 80) * k / 8
            pts.append((xa + w + 10 * math.sin(k * 1.4) - (12 if side > 0 else 0), yy))
        pts += [(xa - 6 * side, y1 + 54)]
        cv.poly(pts, fill=col, col=INK, w=5)
        for k in (0.33, 0.66):
            cv.line([(xa + w * k, y0 - 20), (xa + w * k + 6 * math.sin(k * 9), y1 + 40)], 3, (215, 170, 100))


def wall_clock(cv, c, r, hours):
    """A round wall clock; `hours` (any real number) sets both hands."""
    cv.circle(c, r, fill=(255, 255, 255), col=INK)
    cv.circle(c, r, w=8, col=INK)
    for k in range(12):
        a = k * math.pi / 6
        cv.line([(c[0] + math.sin(a) * r * 0.78, c[1] - math.cos(a) * r * 0.78), (c[0] + math.sin(a) * r * 0.88, c[1] - math.cos(a) * r * 0.88)], 4)
    ah, am = hours / 12 * 2 * math.pi, (hours % 1) * 2 * math.pi
    cv.line([c, (c[0] + math.sin(ah) * r * 0.5, c[1] - math.cos(ah) * r * 0.5)], 8)
    cv.line([c, (c[0] + math.sin(am) * r * 0.75, c[1] - math.cos(am) * r * 0.75)], 5)
    cv.circle(c, 7, col=INK)


def office_chair(cv, seat, s=1.0):
    """An office chair seen from the side, facing right; `seat` = the middle of the seat top."""
    x, y = seat
    cv.rrect((x - 75 * s, y, x + 75 * s, y + 24 * s), 10 * s, fill=(90, 96, 120), col=INK, w=6)
    cv.rrect((x - 95 * s, y - 230 * s, x - 70 * s, y + 10 * s), 10 * s, fill=(90, 96, 120), col=INK, w=6)     # the back
    cv.line([(x, y + 24 * s), (x, y + 150 * s)], 9)
    cv.line([(x - 80 * s, y + 175 * s), (x + 80 * s, y + 175 * s)], 9)
    cv.line([(x, y + 150 * s), (x - 70 * s, y + 175 * s)], 7)
    cv.line([(x, y + 150 * s), (x + 70 * s, y + 175 * s)], 7)
    for dx in (-80, 80):
        cv.circle((x + dx * s, y + 186 * s), 12 * s, col=INK)


def mug(cv, base, s=1.0, steam=0.0):
    """A mug standing at `base` (bottom middle); optional steam (0..1)."""
    x, y = base
    cv.rrect((x - 26 * s, y - 56 * s, x + 26 * s, y), 8 * s, fill=(255, 255, 255), col=INK, w=5)
    cv.arc((x + 14 * s, y - 46 * s, x + 46 * s, y - 16 * s), 270, 90, 5)
    cv.rrect((x - 20 * s, y - 50 * s, x + 20 * s, y - 40 * s), 3 * s, fill=(120, 80, 50))
    if steam > 0:
        for k in (-8, 8):
            cv.line([(x + k * s, y - 66 * s), (x + (k + 6) * s, y - 82 * s), (x + k * s, y - 98 * s)], 3, (190, 190, 200))
