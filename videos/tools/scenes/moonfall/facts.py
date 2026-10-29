# Numbers behind "Що, якби Місяць упав на Землю?": a Moon that suddenly loses its orbital speed and falls straight down.
# Two-body radial fall from rest (Earth + Moon about their common centre), so the Moon's own mass is included.
#   python3 scenes/moonfall/facts.py
import math

G = 6.674e-11
ME, MM = 5.972e24, 7.342e22
RE, RM = 6.371e6, 1.7374e6
R0 = 3.844e8                                   # mean distance (semi-major axis)
MU = G * (ME + MM)
K = math.sqrt(R0 ** 3 / (8 * MU))              # t = K (eta + sin eta),  r = R0/2 (1 + cos eta)


def t_at(r):
    eta = math.acos(2 * r / R0 - 1)
    return K * (eta + math.sin(eta))


def r_at(t):
    lo, hi = 0.0, math.pi                      # eta + sin eta is increasing
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if K * (mid + math.sin(mid)) < t else (lo, mid)
    return R0 / 2 * (1 + math.cos(lo))


def speed_at(r):                               # relative speed of Moon and Earth
    return math.sqrt(2 * MU * (1 / r - 1 / R0))


T_HIT = t_at(RE + RM)
D = 86400.0
rho_e, rho_m = 5514.0, 3344.0
roche_fluid = 2.456 * RE * (rho_e / rho_m) ** (1 / 3)
roche_rigid = 1.26 * RE * (rho_e / rho_m) ** (1 / 3)
amp0 = ME and (MM / ME) * RE ** 4 / R0 ** 3     # equilibrium lunar tide at the sub-lunar point today
E_hit = G * ME * MM / (RE + RM)
E_chx = 4.2e23                                 # Chicxulub, ~1e8 Mt TNT (estimates 1e23-1e24 J)
M_chx = 1.5e15                                 # ~10 km, ~3 g/cm3
E_melt = 2.8e22 * 1.6e6 + 1.4e21 * 2.6e6       # all the crust (2.8e22 kg) heated to ~1200 C and melted + all the oceans boiled away

if __name__ == '__main__':
    print(f'fall from 384 400 km to touching: {T_HIT / D:.3f} d = {T_HIT / 3600:.1f} h  (to the centre: {math.pi * K / D:.3f} d)')
    print(f'Roche limit (centre of Earth): fluid {roche_fluid / 1e3:,.0f} km, rigid {roche_rigid / 1e3:,.0f} km')
    print(f'speed at touching {speed_at(RE + RM) / 1e3:.2f} km/s; at the fluid Roche limit {speed_at(roche_fluid) / 1e3:.2f} km/s')
    print(f'energy {E_hit:.2e} J; Chicxulub {E_chx:.1e} J -> x{E_hit / E_chx:,.0f}; mass ratio x{MM / M_chx:,.0f}')
    print(f'melting the whole crust and boiling the oceans takes ~{E_melt:.0e} J: the fall releases x{E_hit / E_melt:,.0f} of that')
    print(f'equilibrium lunar tide today at the sub-lunar point: {amp0:.2f} m (range {1.5 * amp0:.2f} m)')
    print('\n  d (1000 km)  time since stop        time left       Moon from LEO(400 km)   tide x today   equilibrium height')
    for d in (384.4, 374, 342, 300, 250, 200, 150, 100, 70, 50, 38.44, 30, 20, 18.5, 15, 12, 10, 8.108):
        r = d * 1e6
        r = min(r, R0 * 0.99999) * 1.0
        t = t_at(r)
        dist = max(r - (RE + 4e5), 1.0)
        ang = math.degrees(2 * math.atan(RM / dist))
        k = (R0 / r) ** 3
        left = T_HIT - t
        ts = f'{t / D:5.2f} d'
        ls = f'{left / D:5.2f} d' if left > 6 * 3600 else (f'{left / 3600:5.1f} h' if left > 3600 else f'{left / 60:5.1f} min')
        print(f'  {d:9.1f}    {ts:>9}   ({int(t // D)} d {int(t % D // 3600):2d} h)  {ls:>10}   {ang:9.1f} deg        {k:9.0f}x       {amp0 * k:9.1f} m')
    print('\n  day-by-day position:')
    for day in range(0, 5):
        print(f'   after {day} d: Moon at {r_at(day * D) / 1e6:.1f} thousand km')
    for h in (96, 108, 112, 114, 115, 115.5):
        print(f'   after {h} h: {r_at(h * 3600) / 1e6:.1f} thousand km, {speed_at(r_at(h * 3600)) / 1e3:.2f} km/s')
