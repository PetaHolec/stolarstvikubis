"""Kompletní stažení obsahu starého webu stolarstvikubis.cz (Webnode) do data/old-site.json.

Použití:  python3 -I tools/scrape.py data/old-site.json
Stahuje: všechny stránky z levého menu, produkty (název, cena, celý popis, fotky),
fotogalerie (včetně stránkování a popisků), články, texty stránek a recenze z úvodní stránky.
"""

import sys, re, json, html, subprocess
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

BASE = 'https://www.stolarstvikubis.cz/'
CDN_PREVIEW = re.compile(r'system_preview_(?:small|detail|big)_')


def get(url):
    r = subprocess.run(
        ['curl', '-sL', '--max-time', '30', '-A', 'Mozilla/5.0', url], capture_output=True
    )
    return r.stdout.decode('utf-8', 'ignore')


def full_img(src):
    return CDN_PREVIEW.sub('', html.unescape(src)).split('?')[0]


def clean(t):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return re.sub(r'\s+', ' ', t).strip()


def blocks_from_wsw(h):
    """Převede wysiwyg HTML na jednoduché bloky: p / h / li / img (zachová pořadí, bez duplicit)."""
    h = re.sub(r'(?is)<(script|style|iframe|form).*?</\1>', '', h)
    h = re.sub(r'(?is)<!--.*?-->', '', h)
    h = re.sub(
        r'(?is)<img[^>]+src="([^"]+)"[^>]*>',
        lambda m: '\n\u00a7I\u00a7' + full_img(m.group(1)) + '\n',
        h,
    )
    h = re.sub(r'(?is)<h[1-6][^>]*>', '\n\u00a7H\u00a7', h)
    h = re.sub(r'(?is)<li[^>]*>', '\n\u00a7L\u00a7', h)
    h = re.sub(r'(?is)<br\s*/?>|</?(p|div|tr|table|ul|ol|h[1-6]|li|blockquote)[^>]*>', '\n', h)
    h = html.unescape(re.sub(r'<[^>]+>', '', h))
    out = []
    for line in h.split('\n'):
        line = re.sub(r'[ \t\xa0]+', ' ', line).strip()
        if not line or set(line) <= set('—-_ '):
            continue
        if line.startswith('\u00a7I\u00a7'):
            out.append({'t': 'img', 'src': line[3:]})
        elif line.startswith('\u00a7H\u00a7'):
            t = line[3:].strip()
            if t:
                out.append({'t': 'h', 'text': t})
        elif line.startswith('\u00a7L\u00a7'):
            t = line[3:].strip()
            if t:
                out.append({'t': 'li', 'text': t})
        else:
            out.append({'t': 'p', 'text': line})
    return out


def middle(h):
    starts = [
        i
        for i in (h.find('<div class="content topBar">'), h.find('<div class="content middleBar">'))
        if i >= 0
    ]
    if not starts:
        return ''
    seg = h[min(starts) :]
    for marker in ('<!-- LEFT BAR -->', '<div class="box contact'):
        j = seg.find(marker)
        if j > 0:
            seg = seg[:j]
    return seg


def split_boxes(seg):
    idx = [m.start() for m in re.finditer(r'<div class="box ', seg)] + [len(seg)]
    for a, b in zip(idx, idx[1:]):
        chunk = seg[a:b]
        cls = re.match(r'<div class="box ([^"]+)"', chunk).group(1)
        yield cls, chunk


def next_page(chunk, url):
    m = re.search(r'<a href="([^"]+)"[^>]*rel="next"', chunk)
    return urljoin(url, html.unescape(m.group(1))) if m else None


PRICE = re.compile(r'(\d[\d\s.]*\d|\d+)\s*,-\s*K[čČ]|(\d[\d\s.]*\d)\s*K[čČ]', re.I)


def parse_price(title):
    m = PRICE.search(title.replace('\xa0', ' '))
    if not m:
        return None
    v = (m.group(1) or m.group(2)).replace(' ', '').replace('.', '')
    try:
        return int(v)
    except ValueError:
        return None


def nice_title(t):
    t = re.sub(r'(?i)poptat\s*/\s*objednat', '', t)
    t = re.sub(r'\s*\.{2,}\s*', ' ', t)
    t = re.sub(r'\s*\d[\d\s.]*,-\s*K[čČ]\s*', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' -–')
    return t


def parse_products(chunk, url):
    items = []
    for m in re.finditer(
        r'(?s)<div class="product mode-\d[^"]*">(.*?)<!-- / class="product', chunk
    ):
        p = m.group(1)
        a = re.search(r'<h3 class="heading"><a href="([^"]+)">(.*?)</a>', p, re.S)
        if not a:
            continue
        thumb = re.search(r'<img src="([^"]+)"', p)
        ex = re.search(r'(?s)<div class="wsw">(.*?)</div>', p)
        raw = clean(a.group(2))
        items.append(
            {
                'url': urljoin(url, a.group(1)),
                'raw_title': raw,
                'title': nice_title(raw),
                'price': parse_price(raw),
                'thumb': full_img(thumb.group(1)) if thumb else None,
                'excerpt': clean(ex.group(1)) if ex else '',
            }
        )
    return items


def parse_photos(chunk, url):
    out = []
    for m in re.finditer(r'(?s)<div class="photo mode-\d">(.*?)<!-- / class="photo', chunk):
        p = m.group(1)
        img = re.search(r'<img src="([^"]+)"', p)
        href = re.search(r'<a class="thumbnail" href="([^"]+)"', p)
        cap = re.search(r'<span class="text"><a[^>]*>(.*?)</a>', p, re.S)
        if img:
            out.append(
                {
                    'src': full_img(img.group(1)),
                    'caption': clean(cap.group(1)) if cap else '',
                    'detail': urljoin(url, href.group(1)) if href else None,
                }
            )
    return out


def parse_articles(chunk, url):
    out = []
    for m in re.finditer(r'(?s)<h3[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', chunk):
        out.append({'url': urljoin(url, m.group(1)), 'title': clean(m.group(2))})
    return out


def scrape_page(url, depth=0):
    h = get(url)
    title = re.search(r'id="navCurrentPage">(.*?)<', h)
    page = {
        'url': url,
        'title': clean(title.group(1)) if title else '',
        'html_title': clean(
            (re.search(r'<title>(.*?)</title>', h, re.S) or [None, ''])[1]
            if re.search(r'<title>(.*?)</title>', h, re.S)
            else ''
        ),
        'boxes': [],
    }
    for cls, chunk in split_boxes(middle(h)):
        h2 = re.search(r'<h[12][^>]*>(.*?)</h[12]>', chunk, re.S)
        box = {'kind': cls, 'heading': clean(h2.group(1)) if h2 else ''}
        if cls.startswith('detail wysiwyg') or cls.startswith('detail'):
            w = re.search(r'(?s)<div class="wsw">(.*)', chunk)
            box['blocks'] = blocks_from_wsw(w.group(1) if w else chunk)
            if box['blocks']:
                page['boxes'].append(box)
        elif 'products' in cls:
            items, u, ch = [], url, chunk
            while True:
                items += parse_products(ch, u)
                nx = next_page(ch, u)
                if not nx or nx == u:
                    break
                u = nx
                hh = get(u)
                ch = next((c for k, c in split_boxes(middle(hh)) if 'products' in k), '')
            box['items'] = items
            page['boxes'].append(box)
        elif 'photogallery' in cls:
            photos, u, ch = [], url, chunk
            while True:
                photos += parse_photos(ch, u)
                nx = next_page(ch, u)
                if not nx or nx == u:
                    break
                u = nx
                hh = get(u)
                ch = next((c for k, c in split_boxes(middle(hh)) if 'photogallery' in k), '')
            box['photos'] = photos
            page['boxes'].append(box)
        elif 'articles' in cls:
            box['items'] = parse_articles(chunk, url)
            if box['items']:
                page['boxes'].append(box)
        elif 'discussion' in cls or 'contact' in cls or 'form' in cls:
            continue
        else:
            w = re.search(r'(?s)<div class="wsw">(.*)', chunk)
            if w:
                box['blocks'] = blocks_from_wsw(w.group(1))
                page['boxes'].append(box)
    return page


def scrape_product(item):
    h = get(item['url'])
    seg = middle(h)
    d = re.search(
        r'(?s)<div class="box detail products">(.*?)<div class="box discussion|<div class="box detail products">(.*)',
        seg,
    )
    body = d.group(1) or d.group(2) if d else seg
    h1 = re.search(r'<h1>(.*?)</h1>', body, re.S)
    main = re.search(r'class="thumbnail"[^>]*><img src="([^"]+)"', body)
    w = re.search(r'(?s)<div class="wsw">(.*?)<!-- / WSW -->', body)
    blocks = blocks_from_wsw(w.group(1)) if w else []
    imgs = ([full_img(main.group(1))] if main else []) + [
        b['src'] for b in blocks if b['t'] == 'img'
    ]
    text = [b for b in blocks if b['t'] != 'img']
    # možnosti z poptávkového formuláře (rozměry, dřevina…)
    opts = []
    form = re.search(r'(?s)<div class="box discussion">(.*?)</form>', seg)
    if form:
        for g in re.finditer(
            r'(?s)class="groupLabel[^"]*">(.*?)</label>\s*<div class="choicesGroup">(.*?)</div>\s*</div>',
            form.group(1),
        ):
            vals = [
                clean(v)
                for v in re.findall(r'(?s)<label for="[^"]+" class="">(.*?)</label>', g.group(2))
            ]
            lab = clean(g.group(1)).rstrip(' *')
            if vals and 'Zvolte' not in lab:
                opts.append({'label': lab, 'values': vals})
    item.update(
        {
            'h1': clean(h1.group(1)) if h1 else item['raw_title'],
            'images': list(dict.fromkeys(imgs)),
            'text': text,
            'options': opts,
        }
    )
    return item


def scrape_photo_detail(p):
    h = get(p['detail'])
    seg = middle(h)
    d = re.search(r'(?s)<div class="wsw">(.*?)<!-- / WSW -->', seg) or re.search(
        r'(?s)<p class="text">(.*?)</p>', seg
    )
    p['description'] = clean(d.group(1)) if d else ''
    return p


def main(out):
    home = get(BASE)
    menu = []
    for m in re.finditer(
        r'<li[^>]*>\s*<a href="(/[^"]*)"[^>]*>(?:<span>)?(.*?)(?:</span>)?</a>', home
    ):
        u, t = urljoin(BASE, m.group(1)), clean(m.group(2))
        if t and u not in [x[0] for x in menu] and not re.search(r'/(home|sitemap|rss)/?$', u):
            menu.append((u, t))
    print(len(menu), 'menu pages', file=sys.stderr)
    with ThreadPoolExecutor(8) as ex:
        pages = list(ex.map(lambda x: scrape_page(x[0]), menu))
    for pg, (_, t) in zip(pages, menu):
        pg['menu_title'] = t
    homepage = scrape_page(BASE)
    # produkty
    allp = [
        it
        for pg in pages + [homepage]
        for b in pg['boxes']
        if 'items' in b and 'products' in b['kind']
        for it in b['items']
    ]
    uniq = {}
    for it in allp:
        uniq.setdefault(it['url'], it)
    print(len(uniq), 'products', file=sys.stderr)
    with ThreadPoolExecutor(8) as ex:
        details = {d['url']: d for d in ex.map(scrape_product, [dict(v) for v in uniq.values()])}
    for pg in pages + [homepage]:
        for b in pg['boxes']:
            if 'items' in b and 'products' in b['kind']:
                b['items'] = [details[it['url']] for it in b['items']]
    # popisy dřevin (detail fotky)
    for pg in pages:
        if 'ukazka-drevin' in pg['url']:
            for b in pg['boxes']:
                if 'photos' in b:
                    with ThreadPoolExecutor(8) as ex:
                        b['photos'] = list(ex.map(scrape_photo_detail, b['photos']))
        # články (detail)
        for b in pg['boxes']:
            if 'articles' in b['kind']:
                for a in b['items']:
                    hh = middle(get(a['url']))
                    w = re.search(r'(?s)<div class="wsw">(.*?)<!-- / WSW -->', hh)
                    a['blocks'] = blocks_from_wsw(w.group(1)) if w else []
    json.dump(
        {'menu': menu, 'home': homepage, 'pages': pages},
        open(out, 'w'),
        ensure_ascii=False,
        indent=1,
    )
    nimg = sum(len(d['images']) for d in details.values()) + sum(
        len(b.get('photos', [])) for pg in pages for b in pg['boxes']
    )
    print('pages', len(pages), 'products', len(details), 'images', nimg, file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1])
