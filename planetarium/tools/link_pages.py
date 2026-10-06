# Short links with their own card, for the videos: nebozvid.com.ua/saturn, /67p, /eclipse, /orionids.
# Each is a tiny page: the card tags (title, description, picture) for Telegram, Instagram, Facebook… and an instant
# jump to the site at that body (/#saturn). The pictures are made with og_card.py into ../og/<slug>.jpg.
#
#   python3 link_pages.py      → ../<slug>/index.html
import html, os

SITE = 'https://nebozvid.com.ua'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PAGES = [
    # slug, hash on the site, card title, card description
    ('saturn', 'saturn', 'Сатурн у 3D — Небозвід',
     'Кільця, шестикутний вихор на полюсі й Титан під серпанком. Покрути Сатурн сам — там, де він є саме зараз.'),
    ('67p', '67p', 'Комета 67P/Чурюмова–Герасименко — Небозвід',
     'Комета, відкрита в Києві 1969 року. Ядро-«качечка», зонд Rosetta й посадка Philae — у 3D.'),
    ('eclipse', 'eclipse', 'Повне сонячне затемнення 2 серпня 2027 — Небозвід',
     'Тінь Місяця через пів планети: Іспанія, Сахара, Луксор. Подивись, як і коли воно пройде, — у 3D.'),
    ('orionids', 'orionids', 'Оріоніди й комета Галлея — Небозвід',
     'Щожовтня Земля пролітає крізь пил комети Галлея. Пік зорепаду — 21–22 жовтня. Подивись її орбіту в 3D.'),
]

TEMPLATE = '''<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Небозвід">
<meta property="og:locale" content="uk_UA">
<meta property="og:url" content="{site}/{slug}/">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{site}/og/{slug}.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<!-- A short link: the card above is for previews, visitors go straight to the site. -->
<meta http-equiv="refresh" content="0; url=/#{hash}">
<script>location.replace("/#{hash}");</script>
</head>
<body style="margin:0;background:#04060c;color:#8f9ab4;font:15px system-ui,sans-serif;display:grid;place-content:center;height:100vh">
<a href="/#{hash}" style="color:#f3b964">Відкрити Небозвід</a>
</body>
</html>
'''

for slug, hsh, title, desc in PAGES:
    os.makedirs(os.path.join(OUT, slug), exist_ok=True)
    with open(os.path.join(OUT, slug, 'index.html'), 'w') as f:
        f.write(TEMPLATE.format(site=SITE, slug=slug, hash=hsh, title=html.escape(title), desc=html.escape(desc)))
print('pages:', ', '.join(p[0] for p in PAGES))
