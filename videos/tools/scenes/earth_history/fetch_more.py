# More inserts for «Історія Землі»: iNaturalist (taxon ids), Openverse/Flickr, NASA images & videos. Appends to assets.json.
import json, os, sys, time, urllib.parse
import fetch_open as F
man = json.load(open(F.MAN)); have = {m['source_url'] for m in man}
def save(shot, url, meta, ext='jpg'):
    k = len([m for m in man if m['shot'] == shot]); f = f'{shot}_{k + 1}.{ext}'
    try:
        data = F.get(url, 300)
        if len(data) < 30000: return False
        open(os.path.join(F.OUT, f), 'wb').write(data)
    except Exception as e:
        print('fail', shot, str(e)[:60]); return False
    man.append(dict(shot=shot, file=f, kind='video' if ext == 'mp4' else 'photo', **meta)); have.add(meta['source_url'])
    json.dump(man, open(F.MAN, 'w'), ensure_ascii=False, indent=1); print(shot, f, meta['license'], meta['author'][:28], '|', meta['title'][:55], flush=True); return True
def inq(shot, tid, n):
    u = 'https://api.inaturalist.org/v1/observations?' + urllib.parse.urlencode({'taxon_id': tid, 'photo_license': 'cc-by,cc0', 'quality_grade': 'research', 'order_by': 'votes', 'per_page': 30})
    got = 0
    for o in F.jget(u).get('results', []):
        p = o['photos'][0]
        if p.get('license_code') not in ('cc-by', 'cc0') or ((p.get('original_dimensions') or {}).get('width') or 0) < 1600: continue
        su = f"https://www.inaturalist.org/observations/{o['id']}"
        if su in have: continue
        if save(shot, p['url'].replace('square', 'original'), dict(query=str(tid), title=f"{o['taxon']['name']} — iNaturalist #{o['id']}", author=p.get('attribution', ''), license=p['license_code'].upper(), license_url='', source_url=su, url=p['url'])):
            got += 1
            if got >= n: break
def ovq(shot, q, n, minw=900):
    p = {'q': q, 'license': 'by,cc0,pdm', 'source': 'flickr', 'page_size': 20, 'mature': 'false'}
    try: res = F.jget('https://api.openverse.org/v1/images/?' + urllib.parse.urlencode(p)).get('results', [])
    except Exception as e: print('ERR', q, e); return
    got = 0
    for r in res:
        if r.get('foreign_landing_url') in have or (r.get('width') and r['width'] < minw): continue
        if save(shot, r['url'], dict(query=q, title=r.get('title') or q, author=r.get('creator') or '', license=f"{r['license'].upper()} {r.get('license_version') or ''}".strip(), license_url=r.get('license_url') or '', source_url=r.get('foreign_landing_url') or '', url=r['url'])):
            got += 1
            if got >= n: break
    time.sleep(1.5)
def nasa(shot, q, n, video=False):
    u = 'https://images-api.nasa.gov/search?' + urllib.parse.urlencode({'q': q, 'media_type': 'video' if video else 'image'})
    got = 0
    for it in F.jget(u)['collection']['items'][:25]:
        d = it['data'][0]; su = f"https://images.nasa.gov/details/{urllib.parse.quote(d['nasa_id'])}"
        if su in have: continue
        try: files = F.jget(it['href'])
        except Exception: continue
        if video: big = [x for x in files if x.endswith('~medium.mp4')] or [x for x in files if x.endswith('~orig.mp4')]
        else: big = [x for x in files if x.endswith(('~orig.jpg', '~large.jpg'))]
        if not big: continue
        if save(shot, big[0].replace('http://', 'https://'), dict(query=q, title=d.get('title', q), author=d.get('photographer') or d.get('center') or 'NASA', license='Public domain (NASA)', license_url='', source_url=su, url=big[0]), 'mp4' if video else 'jpg'):
            got += 1
            if got >= n: break
JOBS = [
    lambda: inq('moss', 311249, 3), lambda: inq('millipede', 47735, 2), lambda: inq('mudskipper', 67837, 3), lambda: inq('lungfish', 90204, 2),
    lambda: inq('fern', 121943, 3), lambda: inq('treefern', 332906, 2), lambda: inq('whale', 41566, 2), lambda: inq('horse', 209233, 2),
    lambda: inq('monkey', 43443, 2),
    lambda: ovq('burgess', 'Burgess Shale fossil', 3, 600), lambda: ovq('anomalocaris', 'Anomalocaris', 2, 600), lambda: ovq('ammonite', 'ammonite fossil', 2),
    lambda: ovq('archaeopteryx', 'Archaeopteryx fossil', 2, 600), lambda: ovq('tracks', 'dinosaur tracks', 2, 600), lambda: ovq('eruption', 'volcanic eruption lava fountain', 3),
    lambda: ovq('pyramids', 'pyramids of Giza', 2), lambda: ovq('sophia', 'Saint Sophia Cathedral Kyiv', 2), lambda: ovq('skull', 'Homo erectus skull', 2, 600),
    lambda: ovq('ediacara', 'Ediacaran biota fossil', 2, 600), lambda: ovq('tiktaalik', 'Tiktaalik roseae', 2, 600), lambda: ovq('fernfossil', 'fossil fern Carboniferous', 2),
    lambda: nasa('sun', 'Solar Dynamics Observatory sun', 2), lambda: nasa('aurora', 'aurora from space station', 2), lambda: nasa('volcano', 'volcano eruption from International Space Station', 2),
    lambda: nasa('videarth', 'Earth time lapse International Space Station', 3, video=True), lambda: nasa('vidsun', 'Solar Dynamics Observatory', 2, video=True),
]
for j in JOBS:
    try: j()
    except Exception as e: print('job error', e)
