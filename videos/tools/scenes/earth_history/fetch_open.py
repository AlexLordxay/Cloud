# Open photos for the inserts of «Історія Землі»: Openverse (CC0 / PDM / CC BY only — Flickr etc.), iNaturalist
# (research-grade observations, CC0 / CC BY photos), NASA Image Library (public domain). Every file is saved at once and
# added to assets.json with its author, licence and source (for the description's credits).
#   python3 fetch_open.py [shot …]   -> work/earth_history/assets/<shot>_<n>.jpg, scenes/earth_history/assets.json
import json, os, sys, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
OUT = os.path.join(TOOLS, 'work', 'earth_history', 'assets'); MAN = os.path.join(HERE, 'assets.json')
UA = {'User-Agent': 'NebozvidVideoBot/1.0 (educational video)'}
LIC_OK = {'cc0', 'pdm', 'by', 'cc-by', 'pd', 'public domain'}

SHOTS = {   # shot: [(source, query, n)]
    'lava':        [('ov', 'lava flow Hawaii', 3), ('nasa', 'Kilauea lava', 2)],
    'rainsea':     [('ov', 'rain storm ocean waves', 3)],
    'zircon':      [('ov', 'zircon crystal mineral', 3)],
    'stromatolites': [('ov', 'stromatolites Shark Bay', 3), ('ov', 'stromatolites Hamelin Pool', 2), ('ov', 'fossil stromatolite', 2)],
    'bif':         [('ov', 'banded iron formation', 4)],
    'cyano':       [('ov', 'cyanobacteria microscope', 3), ('ov', 'algae microscope', 2), ('ov', 'diatoms microscope', 2)],
    'redalgae':    [('inat', 'Rhodophyta', 3)],
    'ice':         [('nasa', 'Antarctica ice sheet', 3)],
    'ediacara':    [('ov', 'Dickinsonia fossil', 3), ('ov', 'Charnia fossil', 2), ('ov', 'Ediacaran fossil', 2)],
    'trilobite':   [('ov', 'trilobite fossil', 4)],
    'horseshoe':   [('inat', 'Limulus polyphemus', 3)],
    'moss':        [('inat', 'Bryophyta', 3)],
    'millipede':   [('inat', 'Diplopoda', 3)],
    'fishlegs':    [('ov', 'Tiktaalik fossil', 3), ('ov', 'coelacanth', 2)],
    'horsetail':   [('inat', 'Equisetum', 3), ('inat', 'Cyatheaceae', 3)],
    'dragonfly':   [('inat', 'Anisoptera', 4)],
    'meganeura':   [('ov', 'Meganeura', 3)],
    'coalfern':    [('ov', 'fossil fern coal', 3), ('ov', 'Carboniferous fern fossil', 2)],
    'traps':       [('ov', 'Putorana plateau', 3), ('ov', 'basalt flood lava plateau', 2)],
    'skeleton':    [('ov', 'dinosaur skeleton museum', 4), ('ov', 'Tyrannosaurus skeleton', 2)],
    'footprint':   [('ov', 'dinosaur footprints trackway', 3)],
    'crocodile':   [('inat', 'Crocodylus', 3)],
    'bird':        [('inat', 'Aquila chrysaetos', 3)],
    'chimp':       [('inat', 'Pan troglodytes', 3)],
    'himalaya':    [('nasa', 'Himalaya from International Space Station', 3)],
    'nightearth':  [('nasa', 'city lights at night International Space Station', 4)],
}

def get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def jget(url): return json.loads(get(url))

def ov(q, n):
    u = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode({'q': q, 'license': 'by,cc0,pdm', 'source': 'flickr', 'page_size': 20, 'mature': 'false'})
    out = []
    for r in jget(u).get('results', []):
        if (r.get('width') or 0) < 1000: continue
        out.append(dict(url=r['url'], title=r.get('title') or q, author=r.get('creator') or '', license=f"{r['license'].upper()} {r.get('license_version') or ''}".strip(),
                        license_url=r.get('license_url') or '', source_url=r.get('foreign_landing_url') or '', w=r.get('width'), h=r.get('height')))
    out.sort(key=lambda x: -(x['w'] or 0))
    return out[:n]

def inat(taxon, n):
    u = 'https://api.inaturalist.org/v1/observations?' + urllib.parse.urlencode({'taxon_name': taxon, 'photo_license': 'cc-by,cc0', 'quality_grade': 'research', 'order_by': 'votes', 'per_page': 30, 'photos': 'true'})
    out = []
    for o in jget(u).get('results', []):
        for p in o.get('photos', [])[:1]:
            if p.get('license_code') not in ('cc-by', 'cc0'): continue
            d = p.get('original_dimensions') or {}
            if (d.get('width') or 0) < 1600: continue
            out.append(dict(url=p['url'].replace('square', 'original'), title=f"{(o.get('taxon') or {}).get('name', taxon)} — iNaturalist #{o['id']}",
                            author=p.get('attribution', ''), license=p['license_code'].upper(), license_url='', w=d.get('width'), h=d.get('height'),
                            source_url=f"https://www.inaturalist.org/observations/{o['id']}"))
        if len(out) >= n: break
    return out[:n]

def nasa(q, n):
    u = 'https://images-api.nasa.gov/search?' + urllib.parse.urlencode({'q': q, 'media_type': 'image'})
    out = []
    for it in jget(u)['collection']['items'][:25]:
        d = it['data'][0]; nid = d['nasa_id']
        try: files = jget(it['href'])
        except Exception: continue
        big = [f for f in files if f.endswith(('~orig.jpg', '~large.jpg'))]
        if not big: continue
        out.append(dict(url=big[0].replace('http://', 'https://'), title=d.get('title', q), author=d.get('photographer') or d.get('center') or 'NASA',
                        license='Public domain (NASA)', license_url='https://www.nasa.gov/nasa-brand-center/images-and-media/', w=0, h=0,
                        source_url=f'https://images.nasa.gov/details/{urllib.parse.quote(nid)}'))
        if len(out) >= n: break
    return out

def main(shots):
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(MAN)) if os.path.exists(MAN) else []
    have = {m['source_url'] for m in man}
    for shot in shots:
        k = len([m for m in man if m['shot'] == shot])
        for src, q, n in SHOTS[shot]:
            try: cands = {'ov': ov, 'inat': inat, 'nasa': nasa}[src](q, n)
            except Exception as e: print(shot, src, q, 'ERR', e); continue
            for c in cands:
                if c['source_url'] in have: continue
                f = f'{shot}_{k + 1}.jpg'
                try:
                    data = get(c['url'], 120)
                    if len(data) < 30000 or data[:5] == b'<!DOC': raise ValueError('not an image')
                    open(os.path.join(OUT, f), 'wb').write(data)
                except Exception as e:
                    print(shot, 'download failed', c['url'][:80], e); continue
                k += 1; have.add(c['source_url'])
                man.append(dict(shot=shot, file=f, kind='photo', query=q, **{x: c[x] for x in ('title', 'author', 'license', 'license_url', 'source_url', 'url')}))
                json.dump(man, open(MAN, 'w'), ensure_ascii=False, indent=1)
                print(shot, f, c['license'], c['author'][:40], flush=True)
            time.sleep(1.0)

if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
