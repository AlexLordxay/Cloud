# Wikimedia Commons through Openverse (licence metadata) + upload.wikimedia.org thumbnails (the API is rate-limited for us;
# thumbnails in standard sizes are allowed). UA carries the channel's site, as Wikimedia's policy asks (author agreed 20.11).
import json, os, sys, time, urllib.parse, urllib.request
import fetch_open as F
UA = {'User-Agent': 'NebozvidVideoBot/1.0 (https://nebozvid.com.ua; educational science video)'}
man = json.load(open(F.MAN)); have = {m['source_url'] for m in man}
def thumb(url, w=1920):
    # https://upload.wikimedia.org/wikipedia/commons/a/ab/Name.jpg -> .../commons/thumb/a/ab/Name.jpg/1920px-Name.jpg
    p = url.split('/wikipedia/commons/')
    if len(p) != 2 or '/thumb/' in url: return url
    name = p[1].split('/')[-1]
    return f"{p[0]}/wikipedia/commons/thumb/{p[1]}/{w}px-{name}"
def save(shot, url, meta):
    k = len([m for m in man if m['shot'] == shot]); f = f'{shot}_{k + 1}.jpg'
    for u in (thumb(url, 1280), thumb(url, 960)):
        time.sleep(20)
        try:
            data = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read()
            if len(data) > 30000 and data[:5] != b'<!DOC': break
        except Exception as e:
            data = None; time.sleep(30)
    if not data: print('fail', shot, url[-60:]); return False
    open(os.path.join(F.OUT, f), 'wb').write(data)
    man.append(dict(shot=shot, file=f, kind='photo', **meta)); have.add(meta['source_url'])
    json.dump(man, open(F.MAN, 'w'), ensure_ascii=False, indent=1); print(shot, f, meta['license'], meta['author'][:28], '|', meta['title'][:60], flush=True); return True
def wq(shot, q, n, minw=1200):
    p = {'q': q, 'license': 'by,cc0,pdm', 'source': 'wikimedia', 'page_size': 20, 'mature': 'false'}
    try: res = F.jget('https://api.openverse.org/v1/images/?' + urllib.parse.urlencode(p)).get('results', [])
    except Exception as e: print('ERR', q, e); return
    got = 0
    for r in res:
        if r.get('foreign_landing_url') in have or (r.get('width') and r['width'] < minw): continue
        if not r['url'].lower().endswith(('.jpg', '.jpeg', '.png')): continue
        if save(shot, r['url'], dict(query=q, title=r.get('title') or q, author=r.get('creator') or '', license=f"{r['license'].upper()} {r.get('license_version') or ''}".strip(),
                                     license_url=r.get('license_url') or '', source_url=r.get('foreign_landing_url') or '', url=r['url'])):
            got += 1
            if got >= n: break
        time.sleep(2)
    time.sleep(2)
for shot, q, n in [('ediacara', 'Dickinsonia', 3), ('ediacara', 'Charnia', 2), ('ediacara', 'Ediacaran', 2), ('tiktaalik', 'Tiktaalik', 3),
                   ('sharkbay', 'Hamelin Pool stromatolites', 3), ('sharkbay', 'Shark Bay stromatolites', 2), ('tracks', 'dinosaur trackway', 3),
                   ('putorana', 'Putorana', 3), ('meganeura', 'Meganeura', 2), ('coelacanth', 'Latimeria', 2), ('kryvyirih', 'Kryvyi Rih iron ore', 3),
                   ('sophia', 'Saint Sophia Cathedral Kyiv', 2), ('gagarin', 'Vostok 1', 2), ('irhoud', 'Jebel Irhoud', 2), ('anomalo', 'Anomalocaris', 2),
                   ('opabinia', 'Opabinia', 1), ('lavaflow', 'pahoehoe lava flow', 3)]:
    wq(shot, q, n)
