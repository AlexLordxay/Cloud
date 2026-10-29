# The video clock of «Що, якби Місяць упав на Землю?»: how many seconds before the impact each moment of the video shows,
# where the Moon is and how it looks from the astronaut (a fixed point above the Earth, 40° of arc from the point under the Moon).
#   python3 scenes/moonfall/timeline.py        prints the table used in script.md
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facts as F

ALT, BETA = 1.0e6, math.radians(40)            # the astronaut: 1 000 km up, 40° of arc from the point under the Moon
RA = F.RE + ALT
A = (RA * math.sin(BETA), RA * math.cos(BETA))  # the Moon falls along +y (Earth's centre at the origin)
UP = (math.sin(BETA), math.cos(BETA))
LIMB_DIP = math.degrees(math.acos(F.RE / RA))   # the horizon lies this far below the local horizontal

# video second -> seconds left before the Moon touches the Earth ("T-minus"); linear between keys, log where "log"
KEYS = [  # (video s, T-minus s, mode of the span that starts here)
    (0.0, 720, 'lin'), (1.7, 720, 'log'), (3.0, F.T_HIT - 600, 'lin'),        # cold open at T-12 min, then the rewind to the stop
    (9.5, 12 * 3600, 'log'), (15.5, 1.5 * 3600, 'log'), (23.0, 22.5 * 60, 'log'), (31.0, 180, 'log'), (33.5, 1.0, 'lin'), (46.0, 1.0, 'lin'),
]


def t_minus(tau):
    for (a, ta, mode), (b, tb, _) in zip(KEYS, KEYS[1:]):
        if tau <= b:
            u = (tau - a) / (b - a) if b > a else 1
            return ta + (tb - ta) * u if mode == 'lin' else math.exp(math.log(ta) + (math.log(tb) - math.log(ta)) * u)
    return KEYS[-1][1]


def moon_z(tm):                                 # distance of the Moon's centre from the Earth's centre
    return max(F.r_at(F.T_HIT - tm), F.RE + F.RM)


def view(z):
    mx, my = -A[0], z - A[1]
    d = math.hypot(mx, my)
    elev = math.degrees(math.asin((mx * UP[0] + my * UP[1]) / d))
    return d, elev, math.degrees(2 * math.atan(F.RM / d))


def fmt(s):
    return f'{s / 86400:.1f} d' if s > 2 * 86400 else f'{s / 3600:.1f} h' if s > 3600 else f'{s / 60:.1f} min' if s > 60 else f'{s:.0f} s'


if __name__ == '__main__':
    print(f'astronaut: {ALT / 1e3:.0f} km up, {BETA and math.degrees(BETA):.0f} deg from the sub-lunar point, horizon {LIMB_DIP:.1f} deg below the horizontal')
    print('  video s  T-minus     Moon z (1000 km)  from the astronaut: dist (1000 km)  elevation  size   tide at the sub-lunar point')
    for tau in (0, 1.7, 3.0, 5.0, 7.0, 9.5, 12.5, 15.5, 19.0, 23.0, 27.0, 31.0, 32.5, 33.5):
        tm = t_minus(tau); z = moon_z(tm); d, el, sz = view(z)
        print(f'  {tau:6.1f}  {fmt(tm):>9}   {z / 1e6:9.1f}          {d / 1e6:9.1f}            {el:6.1f}   {sz:5.1f}   {F.amp0 * (F.R0 / z) ** 3:9.1f} m')
