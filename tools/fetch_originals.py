"""Stáhne ORIGINÁLY všech fotek ze starého webu (největší dostupná verze) do originals/<id>.<ext>.

Použití: python3 -I tools/fetch_originals.py
Z originálů pak tools/images.py vyrobí web/media/ v plné kvalitě (bez dvojího JPEG kódování).
"""

import json, re, sys, subprocess
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'originals'
OUT.mkdir(exist_ok=True)
ID = re.compile(r'/(\d{9}-[0-9a-f]{10})(?:-public)?/')
PREV = re.compile(r'system_preview_(?:small|detail|big)_')


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def collect():
    data = json.load(open(ROOT / 'data/old-site.json', encoding='utf-8'))
    found = {}
    for s in strings(data):
        if 'clvaw-cdnwnd.com' not in s or not re.search(r'\.(jpe?g|png|webp|gif)$', s, re.I):
            continue
        m = ID.search(s)
        if not m:
            continue
        u = PREV.sub('', s).split('?')[0]
        found.setdefault(m.group(1), u)
    return found


def fetch(item):
    i, u = item
    ext = u.rsplit('.', 1)[-1].lower().replace('jpeg', 'jpg')
    dst = OUT / f'{i}.{ext}'
    if dst.exists() and dst.stat().st_size > 500:
        return i, 'cached'
    url = quote(u, safe=':/%')
    r = subprocess.run(
        [
            'curl',
            '-sfL',
            '--max-time',
            '60',
            '--retry',
            '2',
            '-A',
            'Mozilla/5.0',
            '-o',
            str(dst),
            url,
        ]
    )
    if r.returncode != 0 or not dst.exists() or dst.stat().st_size < 500:
        dst.unlink(missing_ok=True)
        return i, 'ERR ' + u
    return i, 'ok'


if __name__ == '__main__':
    found = collect()
    print(len(found), 'unikátních fotek')
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(fetch, found.items()))
    bad = [r for r in res if r[1].startswith('ERR')]
    print('ok', sum(r[1] != 'ERR' and not r[1].startswith('ERR') for r in res), 'chyb', len(bad))
    for b in bad[:20]:
        print(b)
