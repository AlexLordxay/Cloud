# «У Землі колись могли бути кільця» — the data, fetched once into work/earth_rings:
#   * Kyiv from above: Sentinel-2 cloudless 2016 (EOX IT Services, CC BY 4.0; contains modified Copernicus Sentinel data
#     2016): Web-Mercator tiles z14 (~6 m/px) within ±13 km of the camera's area, z12 within ±70 km;
#   * the relief: AWS Terrain Tiles (Terrarium encoding; SRTM and others, Mapzen / Amazon), z12 within ±70 km;
#   * the PaleoDEMs (PALEOMAP, Scotese & Wright 2018, CC BY 4.0, zenodo 5460860) for the Earth 470 Ma.
#   python3 scenes/earth_rings/fetch.py
import math, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.dirname(os.path.dirname(HERE))
WK = os.path.join(TOOLS, 'work', 'earth_rings'); os.makedirs(WK, exist_ok=True)
LAT0, LON0 = 50.43, 30.56

def tile_xy(lat, lon, z):
    n = 2 ** z; x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def rng(z, half_km):
    dlat = half_km / 111.2; dlon = half_km / (111.32 * math.cos(math.radians(LAT0)))
    x0, y0 = tile_xy(LAT0 + dlat, LON0 - dlon, z); x1, y1 = tile_xy(LAT0 - dlat, LON0 + dlon, z)
    return int(x0), int(x1), int(y0), int(y1)

def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    subprocess.run(['curl', '-sSf', '--retry', '3', '-o', path, url], check=False)

jobs = []
for z, half in ((14, 13.0), (12, 70.0)):
    d = os.path.join(WK, f's2_{z}'); os.makedirs(d, exist_ok=True)
    x0, x1, y0, y1 = rng(z, half)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            jobs.append((f'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg', os.path.join(d, f'{x}_{y}.jpg')))
d = os.path.join(WK, 'dem_12'); os.makedirs(d, exist_ok=True)
x0, x1, y0, y1 = rng(12, 70.0)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        jobs.append((f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/12/{x}/{y}.png', os.path.join(d, f'{x}_{y}.png')))
print(len(jobs), 'tiles', flush=True)
with ThreadPoolExecutor(8) as ex: list(ex.map(lambda j: get(*j), jobs))
dl = os.path.join(TOOLS, 'work', 'chicxulub', 'dl'); os.makedirs(dl, exist_ok=True)
z = os.path.join(dl, 'dem6.zip')
if not os.path.exists(z) or os.path.getsize(z) < 207000000:
    subprocess.run(['curl', '-sSL', '-C', '-', '-o', z,
                    'https://zenodo.org/api/records/5460860/files/Scotese_Wright_2018_Maps_1-88_6minX6min_PaleoDEMS_nc.zip/content'], check=True)
print('done', flush=True)
