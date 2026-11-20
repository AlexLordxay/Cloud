# LICENSES.md from inserts.json (what is actually in the video) + assets.json (author, licence, source of each file).
#   python3 licenses.py
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ins = json.load(open(os.path.join(HERE, 'inserts.json')))
man = {m['file']: m for m in json.load(open(os.path.join(HERE, 'assets.json')))}
used = sorted({e['file'] for e in ins}, key=lambda f: min(e['t0'] for e in ins if e['file'] == f))
rows, credits = [], []
for f in used:
    m = man[f]; title = m['title'].replace('|', '/')
    rows.append(f"| {f} | {title[:70]} | {m['author']} | {m['license']} | {m['source_url']} |")
    credits.append(f"— {title[:60]} — {m['author']}, {m['license']}, {m['source_url']}")
out = ['# «Історія Землі» — джерела зображень (вставки)', '', '| Файл | Що | Автор | Ліцензія | Джерело |', '|---|---|---|---|---|', *rows, '',
       '## Для опису YouTube (вставити як є)', '', 'Джерела зображень:', *credits,
       'Палеокарти: PALEOMAP PaleoDEM, C. R. Scotese & N. Wright (2018), CC BY 4.0.',
       'Земля: NASA Blue Marble / Black Marble (суспільне надбання). Музика й звуки — власні.', '']
open(os.path.join(HERE, 'LICENSES.md'), 'w').write('\n'.join(out))
print(len(used), 'files credited')
