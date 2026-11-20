"""Katalog: šablony kategorie, produktu, matrací a roštů (design „Dílna ve dne“, research/design-brief.md 4.10 až 4.12).

Přepisuje B.build_category a B.build_product z build.py (tools/make.py tento modul importuje).
Data matrací: data/matrace.json (vyparsováno z data/old-site.json, stránky /matrace/, /rosty/, /toppery.../):
    python3 -I tools/pages_catalog.py parse     -> znovu vytvoří data/matrace.json
Styly: tools/css/catalog.css
"""

import json, re, copy, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B

E = B.E
ROOT = B.ROOT
MAT_FILE = ROOT / 'data/matrace.json'
PICKS = json.load(open(ROOT / 'data/photo-picks.json', encoding='utf-8'))


# ======================================================================================================
# 1) Parsování matrací, roštů a topperů ze starého webu -> data/matrace.json
# ======================================================================================================
PRICE_ANY = re.compile(r'(\d[\d ]{2,})\s*,?\s*-?\s*K[čČ]')

# ruční názvy matrací (index boxu na /matrace/): id, název, podtitulek
MAT_NAMES = {
    2: ('melira', 'Matrace Melira', 'gelová, vrstva GelEffect'),
    3: ('synora', 'Matrace Synora', 'gelová pětizónová'),
    4: ('arella-hard', 'Matrace Arella Hard', 'studená pěna s vysokou tuhostí'),
    5: ('arela', 'Matrace Arela', 'studená pěna, výška 20 cm'),
    6: ('fortis', 'Matrace Fortis', 'vysoké zatížení do 180 kg'),
    7: ('dia-20-hi', 'Matrace Dia 20 Hi', 'hybridní a studená pěna'),
    8: ('gita-plus', 'Matrace Gita Plus', 'studená pěna, výška 20 cm'),
    9: ('nikol', 'Matrace Nikol', 'studená pěna s latexem a 3D mřížkou'),
    10: ('natalie', 'Matrace Natálie', 'studená pěna s latexem'),
    11: ('ela', 'Matrace Ela', 'PUR pěna'),
    12: ('giana', 'Matrace Giana', 'antidekubitní'),
    13: ('simona', 'Matrace Simona', 'vyšší tvrdost, studená pěna'),
    14: ('lenka', 'Matrace Lenka', 'vysokozátěžová'),
    15: ('lea', 'Matrace Lea', 'antibakteriální s ionty stříbra'),
    16: ('berta', 'Matrace Berta', 'vysokozátěžová taštičková, do 150 kg'),
    17: ('andrea', 'Matrace Andrea', 'vysokozátěžová'),
    18: ('gita', 'Matrace Gita', 'studená pěna'),
    19: ('diana', 'Matrace Diana', 'líná pěna'),
    20: ('petra', 'Matrace Petra', 'PUR pěna'),
    21: ('jana', 'Matrace Jana', 'PUR pěna'),
    22: ('klara', 'Matrace Klára', 'vyšší tvrdost'),
    23: ('ola', 'Matrace Ola', 'studená a líná pěna'),
    24: ('karolina', 'Matrace Karolína', 'taštičková a studená pěna'),
}
# senior matrace z produktů: slug produktu -> (id, název, podtitulek)
SENIOR_MATS = {
    'senior-matrace-arela-plus-v-24cm-na-150kg-9250-kc-poptat-objednat': (
        'arela-plus-senior',
        'Senior matrace Arela Plus',
        'studená pěna, tuhý okraj',
    ),
    'senior-matrace-arela-soft-24cm-na-150kg-9250-kc-poptat-objednat': (
        'arela-soft-senior',
        'Senior matrace Arela Soft',
        'měkčí, tuhý okraj',
    ),
    'senior-matrace-caeli-24cm-na-150kg': (
        'caeli-senior',
        'Senior matrace Caeli',
        'gelový efekt, tuhý okraj',
    ),
    'senior-matrace-dia-relax-na-130kg': (
        'dia-relax-senior',
        'Senior matrace Dia Relax',
        'hybridní pěna, tuhý okraj',
    ),
    'senior-matrace-juna-18cm-na-120kg': (
        'juna-senior',
        'Senior matrace Juna',
        'hybridní pěna, tuhý okraj',
    ),
}
# doporučení z textu na /matrace/ -> filtry (jen to, co data opravdu říkají)
TAG_RULES = {
    'senior': {
        'arela-plus-senior',
        'arela-soft-senior',
        'caeli-senior',
        'dia-relax-senior',
        'juna-senior',
        'ola',
        'diana',
        'simona',
    },
    'detske': {'gita', 'gita-plus', 'klara', 'ela'},
}
FILTERS = [
    ('senior', 'Pro seniory'),
    ('antidekubitni', 'Antidekubitní'),
    ('alergici', 'Pro alergiky'),
    ('vysokozatezove', 'Vysokozátěžové'),
    ('detske', 'Dětské'),
    ('gelove', 'Gelové'),
    ('tastickove', 'Taštičkové'),
]


def _int(s):
    return int(re.sub(r'\s', '', s))


def _fmt_title(s):
    s = re.sub(r'\s+', ' ', s).strip(' .–-!:')
    return s


def _clean_li(lis):
    """Sloučí podřádky (zimní strana…), zahodí duplicity a odkazy na starý web."""
    out, seen = [], set()
    for t in lis:
        t = t.strip()
        if not t or re.search(r'(?i)výrobce doporučuje|více zde|https?://', t):
            continue
        low = t.lower()
        if re.match(r'(?i)(zimní|letní|oranžová|modrá|zelená|modrozelená|bílá) strana', t) and out:
            out[-1] = out[-1].rstrip(':') + (': ' if out[-1].endswith(':') else '; ') + t
            continue
        key = re.match(
            r'(?i)(tvrdost|tuhost|výška|zatížení|možnost|hmotnost|materiál potahu|materiál jádra)',
            t,
        )
        if key:
            k = key.group(1).lower()
            if k in seen:
                continue
            seen.add(k)
        out.append(t[:1].upper() + t[1:])
    return out


def _spec_value(specs, pat):
    for t in specs:
        if re.match(pat, t, re.I):
            return t
    return ''


def parse_box(b):
    """Box ze starého webu -> název, ceny, texty, seznam parametrů, obrázky."""
    blocks = b.get('blocks', [])
    heads = [x['text'] for x in blocks if x['t'] == 'h'] or [b.get('heading', '')]
    head = next((h for h in heads if PRICE_ANY.search(h)), heads[-1])
    prices = [_int(m.group(1)) for m in PRICE_ANY.finditer(head)]
    name = PRICE_ANY.split(head)[0]
    name = re.sub(r'(?i)(novinka|unikátní novinka)\s*!*', '', name)
    name = re.sub(r'\s*\.{2,}\s*', ' ', name)
    name = re.sub(r'\s*\d+\s*x\s*\d+\s*cm.*$', '', name)
    ps = [
        x['text'].strip()
        for x in blocks
        if x['t'] == 'p' and x['text'].strip() and not re.search(r'https?://', x['text'])
    ]
    lis = _clean_li([x['text'] for x in blocks if x['t'] == 'li'])
    imgs = [x['src'] for x in blocks if x['t'] == 'img']
    mids = [(B.mid(u), u) for u in imgs if B.mid(u)]
    big = [m for m, u in mids if m in B.CUT and B.media_size(m, 'l')[0] >= 200]
    pic = big[0] if big else next((m for m, u in mids if B.media_size(m, 'l')[0] >= 100), None)
    note = ''
    if len(prices) > 1:
        note = '; '.join(
            f'{a.replace(" ", "").replace("x", " × ")} cm: {B.fmt(_int(c))} Kč'
            for a, c in re.findall(r'(\d+\s*x\s*\d+)\s*cm\s*-\s*(\d[\d ]*)\s*,?\s*-?\s*K[čČ]', head)
        )
    return dict(
        name=_fmt_title(name),
        price=min(prices) if prices else None,
        price_from=len(prices) > 1,
        price_note=note,
        text=ps,
        specs=lis,
        img=pic,
    )


def derive(it):
    specs = it['specs']
    allt = ' '.join(it['text'] + specs)
    m = re.search(
        r'výšk\w*\D{0,24}?(\d{2})\s*cm', ' '.join(specs) + ' ' + ' '.join(it['text']), re.I
    )
    it['height'] = int(m.group(1)) if m else None
    m = re.search(r'(?:zatížení|nosnost)\s*(?:do\s*)?(\d{2,3})\s*kg', allt, re.I)
    it['load'] = int(m.group(1)) if m else None
    firm = _spec_value(specs, r'(tvrdost|tuhost|rozdílná tvrdost|dvojí tvrdost)')
    codes = []
    for c in re.findall(r'\b([TH]\d)\b', firm):
        if c not in codes:
            codes.append(c)
    if not codes:
        for c in re.findall(r'\b([TH]\d)\b', ' '.join(specs[:3])):
            if c not in codes:
                codes.append(c)
    if len(codes) >= 3:
        it['firm'] = ' / '.join(sorted(codes)) + ' na výběr'
    elif codes:
        it['firm'] = ' / '.join(codes)
    else:
        m = re.search(r'(?:tvrdost|tuhost)\s*:?\s*([a-zěščřžýáíé ]+)', firm, re.I)
        it['firm'] = m.group(1).strip() if m else ''
    it['cover'] = _spec_value(specs, r'(materiál potahu|potah|prodyšný pratelný potah)')
    it['layers'] = B.mattress_layers(allt)


def parse_matrace():
    pg = B.PAGES['/matrace/']
    mats = []
    for j, b in enumerate(pg['boxes']):
        if j not in MAT_NAMES:
            continue
        it = parse_box(b)
        mid_, name, sub = MAT_NAMES[j]
        it.update(id=mid_, name=name, sub=sub, product=None)
        derive(it)
        it['alt'] = f'{name}, ukázka složení a řezu matrace'
        mats.append(it)
    for slug, (mid_, name, sub) in SENIOR_MATS.items():
        p = B.PRODUCTS[slug]
        specs = _clean_li([x['text'] for x in p['text'] if x['t'] == 'li'])
        texts = [x['text'].strip() for x in p['text'] if x['t'] == 'p' and x['text'].strip()]
        im = next((B.mid(u) for u in p['images'] if B.mid(u)), None)
        it = dict(
            id=mid_,
            name=name,
            sub=sub,
            price=p['price'],
            price_from=False,
            price_note='',
            text=texts,
            specs=specs,
            img=im,
            product=slug,
            alt=f'{name}, ukázka složení a řezu matrace',
        )
        derive(it)
        mats.append(it)
    for it in mats:
        low = (' '.join(it['text'] + it['specs']) + ' ' + it['name'] + ' ' + it['sub']).lower()
        tags = [t for t, ids in TAG_RULES.items() if it['id'] in ids]
        if 'antidekubitn' in low:
            tags.append('antidekubitni')
        if re.search(r'antialerg|protialerg|antibakteri|protiroztoč', low):
            tags.append('alergici')
        if (it['load'] or 0) >= 180 or 'vysokozátěž' in low:
            tags.append('vysokozatezove')
        if re.search(r'gel', low):
            tags.append('gelove')
        if 'taštičk' in low:
            tags.append('tastickove')
        it['tags'] = [t for t, _ in FILTERS if t in tags]
    # potahy
    cover_box = pg['boxes'][25]
    potahy = []
    for x in cover_box['blocks']:
        if x['t'] == 'p':
            m = re.match(r'(?i)potah\s+(.+?)\s+příplatek\s+(\d[\d ]*)', x['text'])
            if m:
                potahy.append(dict(name='Potah ' + m.group(1).strip(), price=_int(m.group(2))))
    # doporučení
    reco = []
    for x in pg['boxes'][0]['blocks']:
        if x['t'] == 'li' and ' - ' in x['text']:
            need, rest = x['text'].split(' - ', 1)
            reco.append(dict(need=need.strip(), text=rest.strip()))

    # rošty a toppery
    def collect(src, idxs, prefix):
        out = []
        for j in idxs:
            it = parse_box(B.PAGES[src]['boxes'][j])
            if re.fullmatch(r'\s*', it['name']):
                continue
            it['id'] = f'{prefix}{j}'
            it['alt'] = it['name'] + ', foto výrobku'
            derive(it)
            out.append(it)
        return out

    rosty = collect('/rosty/', range(0, 5), 'r')
    toppery = collect('/toppery-chranice-matraci-kliny-polstarky/', range(0, 11), 't')
    data = dict(
        matrace=mats,
        potahy=potahy,
        doporuceni=reco,
        rosty=rosty,
        toppery=toppery,
        filters=[dict(id=i, label=l) for i, l in FILTERS],
    )
    json.dump(data, open(MAT_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return data


# ======================================================================================================
# 2) Pomocné funkce: texty, fotky, karty
# ======================================================================================================
def _load_mat():
    if not MAT_FILE.exists():
        return parse_matrace()
    return json.load(open(MAT_FILE, encoding='utf-8'))


MAT = _load_mat()
MAT_BY_ID = {m['id']: m for m in MAT['matrace']}
MAT_BY_PRODUCT = {m['product']: m for m in MAT['matrace'] if m.get('product')}


def plural(n, a, b, c):
    return a if n == 1 else b if 2 <= n <= 4 else c


ABBR = {
    'tl',
    'roz',
    'v',
    'd',
    'š',
    'hl',
    'ks',
    'fi',
    'tzv',
    'např',
    'sv',
    'č',
    'cca',
    'max',
    'min',
    'resp',
    'obr',
    'p',
    'pol',
    'st',
    'tj',
    'atd',
    'mj',
}
NOISE = re.compile(
    r'(?i)poptávkový|poptat nebo|poptat/objednat|formulář|více zde|viz níže|viz foto|https?://|viz rubrika'
)
PRICEY = re.compile(r'(?i)^(cena|ceny|příplatek)')


PRICE_RAW = re.compile(r'(\d{1,3}(?: \d{3})+|\d{3,})\s*,\s*-\s*K[čČ]')


def clean_text(t):
    t = re.sub(r'\s*(\.{2,}|…)\s*', ' ', t)
    t = PRICE_RAW.sub(
        lambda m: B.fmt(int(m.group(1).replace(' ', ''))) + ' Kč', t
    )  # „1200,-Kč“ -> „1 200 Kč“
    return re.sub(r'\s+', ' ', t).strip()


def split_sentences(t):
    t = clean_text(t)
    out, start = [], 0
    for m in re.finditer(r'([.!?])\s+(?=[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])', t):
        last = re.search(r'(\S+)$', t[start : m.start()])
        w = last.group(1).lower().rstrip('.') if last else ''
        if m.group(1) == '.' and (w in ABBR or re.fullmatch(r'\d{1,2}', w)):
            continue
        out.append(t[start : m.end() - 1].strip())
        start = m.end()
    out.append(t[start:].strip())
    return [s for s in out if s]


def up(s):
    return s[:1].upper() + s[1:]


def nice_title(p):
    t = B.prod_title(p)
    t = re.sub(r'^(?i:novinka)!?\s*', '', t).strip()
    words = []
    for w in t.split(' '):
        if re.fullmatch(r'[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]{4,}', w):
            w = w.capitalize()
        elif w in ('DUB', 'BUK'):
            w = w.lower()
        words.append(w)
    return up(' '.join(words))


def card_text(p, limit=112):
    """Jedna celá věta (nebo celé části věty) pro kartu. Žádné „…“, žádné useknuté slovo."""
    t = B.prod_desc_text(p) or p.get('excerpt', '')
    sents = [s for s in split_sentences(t) if not NOISE.search(s)]
    cand = [s for s in sents if not PRICEY.match(s)] or sents
    if not cand:
        return ''
    cand = [
        s for s in cand if len(s) >= 35
    ] or cand  # úvodní „Akce…!“ a podobné krátké hlášky přeskočit
    s = re.sub(r'^(?i:novinka)!?\s*', '', cand[0]).strip(' .;:,')
    if len(s) > limit:
        parts = s.split(', ')
        acc = parts[0]
        for q in parts[1:]:
            if len(acc) + 2 + len(q) <= limit:
                acc += ', ' + q
            else:
                break
        s = acc
    return up(s) + ('' if s.endswith(('!', '?')) else '.')


def bold_nums(t):
    return re.sub(
        r'(\d[\d  ×,]*\d?(?:\s?(?:Kč|cm|kg|mm|let|týdnů|dřevin|modelů|model|modely|postelí|stolů|kusů|položek|typů|matrací|roštů))?)',
        r'<b>\1</b>',
        E(t),
    )


# ---- fotky: výběr obálky, vyřazené fotky ------------------------------------------------------------
FIXED_ROTATION = {
    '200005143',
    '200005138',
    '200006423',
    '200006424',
    '200006418',
    '200007463',
    '200007123',
}  # opraveno v tools/images.py (fix)


def _excluded_ids():
    out = set()
    for e in PICKS.get('vyradit', []) + PICKS.get('vyradit_rozsahy', []):
        path = e['path'].split('/')[-1]
        if path[:9] in FIXED_ROTATION:
            continue
        if re.match(r'\d{9}-[0-9a-f]{10}\.', path):  # jedna fotka: <id>-<hash>.jpg
            out.add(int(path[:9]))
            continue
        for a, b in re.findall(r'(\d{9})\s*–\s*(\d{9})', path):  # rozsah s pomlčkou „–“
            out.update(range(int(a), int(b) + 1))
        full = re.findall(r'\d{9}', path)
        out.update(int(x) for x in full)
        if full and re.search(r',\s*\d{3}\b', path):
            base = full[0][:6]
            out.update(int(base + n) for n in re.findall(r',\s*(\d{3})\b', path))
    return out


EXCLUDED = _excluded_ids()
# fotky z ceníku ohrádek, na kterých je vidět dítě (v data/photo-picks.json nejsou, souhlas není doložen): 200000723, 200003776, 200003777
EXCLUDED.update({200000723, 200003776, 200003777})


def excluded(i):
    return bool(i) and int(i[:9]) in EXCLUDED


def keep_imgs(imgs):
    """Bez fotek, u kterých není doložen souhlas osob v záběru (research/photo-picks.md, oddíl 6). Když zbyde nic, nechá první."""
    ok = [u for u in imgs if not excluded(B.mid(u))]
    return ok or imgs[:1]


# Obálka produktu: druhá fotka tam, kde je první na limetkové zdi (analýza barev snímků, 5 produktů; ostatní nemají lepší)
COVER_PICK = {
    'jednoluzko-sandra-smrk': '200004727-a18d5a2881',
    'zvysena-postel-richard-buk': '200005117-bd6bbbd6bc',
    'jednoluzko-sona-dub': '200004680-a37dea477d',
    'senior-podpera-bocni-madlo': '200007406-a6107a6109',
}


def prod_images(s):
    p = B.PRODUCTS[s]
    imgs = [
        u
        for u in dict.fromkeys(p.get('images') or ([p['thumb']] if p.get('thumb') else []))
        if B.mid(u)
    ]
    pick = COVER_PICK.get(s)
    if pick:
        imgs.sort(key=lambda u: 0 if B.mid(u) == pick else 1)
    return imgs


def cover_of(s):
    imgs = keep_imgs(prod_images(s))
    return imgs[0] if imgs else None


def pick_photo(slug, k=0):
    """Fotka kategorie z data/photo-picks.json (jedna z 16 vybraných; k = pořadí v alternativách)."""
    if slug == 'matrace':
        return dict(
            src='/img/prodejna-1.jpg',
            w=1400,
            h=1050,
            alt='Postel s matrací a bukovým čelem z lamel v prodejně Stolařství Kubiš v Němčičkách',
        )
    items = PICKS.get('kategorie/' + slug) or []
    if not items:
        n, w, h = B.COVERS[slug]
        return dict(src=f'/img/{n}.jpg', w=w, h=h, alt='')
    it = items[0]
    if k:
        alts = it.get('alternativy') or []
        if k - 1 >= len(alts):
            return None
        path = alts[k - 1]
        full = ROOT / path
        if not full.exists():
            return None
        from PIL import Image

        with Image.open(full) as im:
            w, h = im.size
        return dict(src='/' + path.split('web/', 1)[1], w=w, h=h, alt=it['alt'])
    return dict(src='/' + it['path'].split('web/', 1)[1], w=it['w'], h=it['h'], alt=it['alt'])


def photo_tag(ph, cls='', first=False):
    return (
        f'<div class="ph r32{(" " + cls) if cls else ""}"><img src="{ph["src"]}" width="{ph["w"]}" height="{ph["h"]}" alt="{E(ph["alt"])}"'
        f'{"" if not first else " fetchpriority=high"}{" loading=lazy decoding=async" if not first else ""}></div>'
    )


# ---- karta modelu ----------------------------------------------------------------------------------
def card(s, lazy=True):
    p = B.PRODUCTS[s]
    title = nice_title(p)
    image = cover_of(s)
    cut = image and B.mid(image) in B.CUT
    ph = (
        B.img_tag(image, title, lazy=lazy)
        if image
        else '<span class="noph">Fotografii pošleme na vyžádání</span>'
    )
    ex = card_text(p)
    flags = [f for f in B.prod_flags(p) if f != 'Skladem'] + (
        ['Skladem'] if 'Skladem' in B.prod_flags(p) else []
    )
    pl = B.price_label(p)
    tag = f'<span class="tag">{E(flags[0])}</span>' if flags else ''
    return (
        f'<a class="model" href="/produkty/{s}/" data-fx="lift"><span class="ph{" cut" if cut else ""}">{ph}</span><h3>{E(title)}</h3>'
        f'{f"<p>{E(ex)}</p>" if ex else ""}<span class="meta"><span class="price{"" if p.get("price") else " req"}">{E(pl)}</span>{tag}</span></a>'
    )


def grid(slugs, fold=9, heading=None, limit=12, dense=False):
    """Mřížka karet; při více než `limit` kusech se ukáže prvních `fold`, zbytek je pod tlačítkem (nativní <details>, funguje bez JS)."""
    head = f'<h2 class="block-title">{E(heading)}</h2>' if heading else ''
    if len(slugs) <= max(limit, fold + 2):
        fold = len(slugs)
    first, rest = slugs[:fold], slugs[fold:]
    cls = 'models dense' if dense else 'models'
    out = (
        head
        + f'<div class="{cls}">{"".join(card(x, lazy=k >= 3) for k, x in enumerate(first))}</div>'
    )
    if rest:
        out += (
            f'<details class="more"><summary class="btn btn-2"><span class="w-closed">Zobrazit dalších {len(rest)} {plural(len(rest), "model", "modely", "modelů")}</span>'
            f'<span class="w-open">Skrýt dalších {len(rest)}</span></summary><div class="{cls}">{"".join(card(x) for x in rest)}</div></details>'
        )
    return out


# ---- karta matrace / roštu / toppery (vystřižený kus na kameni) --------------------------------------
MDLG_N = [0]


def kcard(it, link=None, compact=False, with_id=True):
    i = it.get('img')
    if i:
        w, h = B.media_size(i, 's')
        img = f'<img src="{B.media_src(i, "s")}" width="{w}" height="{h}" alt="{E(it.get("alt") or it["name"])}" loading="lazy" decoding="async">'
    else:
        img = ''
    parts = []
    if it.get('height'):
        parts.append(f'výška {it["height"]} cm')
    if it.get('load'):
        parts.append(f'do {it["load"]} kg')
    if it.get('firm'):
        parts.append(f'tuhost {it["firm"]}')
    if not parts and it.get('specs') and it['id'][0] == 'r':
        parts = [x[:1].lower() + x[1:] for x in it['specs'][:3]]
    meta = ' · '.join(parts)
    name = E(it['name'])
    h3 = f'<h3><a href="{link}">{name}</a></h3>' if link else f'<h3>{name}</h3>'
    price = ''
    if it.get('price'):
        price = (
            f'<p class="price">{"od " if it.get("price_from") else ""}{B.fmt(it["price"])} Kč</p>'
        )
    else:
        price = '<p class="price req">cena na poptávku</p>'
    sub = it.get('sub') or (
        card_text({'text': [{'t': 'p', 'text': it['text'][0]}]}, 90)
        if (it.get('text') and it['id'][0] == 't')
        else ''
    )
    det = ''
    did = ''
    if not compact:
        txt = ''.join(f'<p>{E(t)}</p>' for t in it.get('text', []))
        spec = (
            f'<ul>{"".join(f"<li>{E(x)}</li>" for x in it["specs"])}</ul>'
            if it.get('specs')
            else ''
        )
        lay = (
            f'<p><b>Složení:</b> {E(", ".join(it["layers"]))}.</p>'
            if it.get('layers') and it['id'][0] not in 'rt'
            else ''
        )
        note = f'<p><b>Ceny:</b> {E(it["price_note"])}.</p>' if it.get('price_note') else ''
        ask = f'<p><a class="link" href="/poptavka/?model={E(it["name"])}">Poptat: {E(it["name"])}</a></p>'
        fallback = (
            f'<details class="mfallback"><summary>Složení a parametry</summary>'
            f'<div class="mdet">{txt}{lay}{spec}{note}{ask}</div></details>'
        )
        # okno s detailem: velká fotka vlevo, popis vpravo (nativní <dialog>, otevírá ho site.js)
        MDLG_N[0] += 1
        did = f'mdlg-{MDLG_N[0]}'
        if i:
            bw, bh = B.media_size(i, 'l')
            big = (
                f'<img src="{B.media_src(i, "l")}" width="{bw}" height="{bh}" '
                f'alt="{E(it.get("alt") or it["name"])}" loading="lazy" decoding="async">'
            )
        else:
            big = ''
        chips = ''.join(f'<li>{E(x)}</li>' for x in parts)
        specs_html = (
            f'<h3>Parametry</h3><ul class="mspec">{"".join(f"<li>{E(x)}</li>" for x in it["specs"])}</ul>'
            if it.get('specs')
            else ''
        )
        lay_html = (
            f'<h3>Složení</h3><p>{E(", ".join(it["layers"]))}.</p>'
            if it.get('layers') and it['id'][0] not in 'rt'
            else ''
        )
        text_html = ''.join(f'<p>{E(t)}</p>' for t in it.get('text', []))
        price_html = price.replace('class="price', 'class="price mprice')
        note_html = (
            f'<p class="small"><b>Ceny:</b> {E(it["price_note"])}.</p>'
            if it.get('price_note')
            else ''
        )
        chips_html = f'<ul class="mchips">{chips}</ul>' if chips else ''
        dlg = (
            f'<dialog class="mdlg" id="{did}" aria-labelledby="{did}-t">'
            f'<button class="mdlg-close btn btn-2" type="button" data-mclose>Zavřít ✕</button>'
            f'<div class="mdlg-in"><div class="mdlg-ph frame">{big}</div>'
            f'<div class="mdlg-txt"><h2 id="{did}-t">{name}</h2>{price_html}{chips_html}'
            f'{text_html}{specs_html}{lay_html}{note_html}'
            f'<div class="ctas"><a class="btn" href="/poptavka/?model={E(it["name"])}">Poptat</a>'
            f'<a class="btn btn-2" href="tel:{B.TEL1H}">Zavolat {B.TEL1}</a></div>'
            f'</div></div></dialog>'
        )
        det = (
            f'<button class="btn btn-2 mdlg-open" type="button" data-mopen="{did}">'
            f'Detail a parametry</button>{dlg}{fallback}'
        )
    tags = ' '.join(it.get('tags', []))
    if did:
        # celá fotka otevírá okno s detailem
        photo = (
            f'<button type="button" class="ph cut mph" data-mopen="{did}" '
            f'aria-label="Detail: {E(it["name"])}">{img}</button>'
        )
    else:
        photo = f'<div class="ph cut">{img}</div>'
    return (
        f'<article class="kcard"{f" id=m-{it["id"]}" if with_id else ""} data-t="{tags}">{photo}{h3}{f"<p class=ksub>{E(sub)}</p>" if sub else ""}'
        f'{f"<p class=mm>{E(meta)}</p>" if meta else ""}{price}{det}</article>'
    )


# ---- galerie ---------------------------------------------------------------------------------------
def gallery_html(photos, gid, label, first=6):
    seen, tiles = set(), []
    for ph in photos:
        i = B.mid(ph['src'])
        if not i or i in seen or excluded(i):
            continue
        seen.add(i)
        cap = (ph.get('caption') or '').strip()
        alt = cap or f'{label}, fotografie {len(tiles) + 1}'
        w, h = B.media_size(i, 's')
        cut = i in B.CUT
        tiles.append(
            f'<a href="{B.media_src(i, "l")}" data-lb="{gid}" data-cap="{E(alt)}"><img src="{B.media_src(i, "s")}" width="{w}" height="{h}" alt="{E(alt)}" loading="lazy" decoding="async"{" class=cut" if cut else ""}></a>'
        )
    if not tiles:
        return ''
    out = f'<div class="gal-s">{"".join(tiles[:first])}</div>'
    if len(tiles) > first:
        n = len(tiles) - first
        out += (
            f'<details class="more"><summary class="btn btn-2"><span class="w-closed">Zobrazit dalších {n} {plural(n, "fotografii", "fotografie", "fotografií")}</span>'
            f'<span class="w-open">Skrýt další fotografie</span></summary><div class="gal-s">{"".join(tiles[first:])}</div></details>'
        )
    descs = ''.join(
        f'<h3>{E(ph.get("caption", ""))}</h3><p>{B.linkify(ph["description"].strip())}</p>'
        for ph in photos
        if ph.get('description', '').strip() and not excluded(B.mid(ph['src']))
    )
    return out + (f'<div class="prose">{descs}</div>' if descs else '')


def sentence_case(t):
    letters = [ch for ch in t if ch.isalpha()]
    if len(letters) >= 8 and sum(ch.isupper() for ch in letters) / len(letters) > 0.7:
        low = t.lower()
        low = re.sub(r'\b(pur|hr)\b', lambda m: m.group(1).upper(), low)
        return up(low)
    return t


def normalize_box(b):
    """Kopie boxu, kde jsou nadpisy a odstavce psané VELKÝMI PÍSMENY převedeny na normální velikost."""
    b = copy.deepcopy(b)
    if b.get('heading'):
        b['heading'] = sentence_case(b['heading'])
    for x in b.get('blocks', []):
        if x['t'] in ('h', 'p', 'li') and x.get('text'):
            x['text'] = sentence_case(x['text'])
    for it in b.get('items', []):
        if isinstance(it, dict) and it.get('title'):
            it['title'] = sentence_case(it['title'])
    return b


# ======================================================================================================
# 3) Kategorie
# ======================================================================================================
BED_GROUPS = ('potreba', 'typ')
PARENT = {
    'potreba': ('Postele z masivu', '/postele-z-masivu/'),
    'typ': ('Postele z masivu', '/postele-z-masivu/'),
    'nabytek': ('Nábytek z masivu', '/nabytek-z-masivu/'),
}

FACTS = {
    'postele-pro-seniory': '{n} postelí, od {min}. Ložná plocha 55, 60 nebo 65 cm k povrchu matrace, nosnost 400 kg na lůžko, záruka 5 let na typizované postele.',
    'vysokozatezove-postele': '{n} modelů, od {min}. Nosnost 400 kg na lůžko bez příplatku, vybrané modely až 500 kg, masiv tloušťky 40 mm, délky 210 a 220 cm.',
    'postele-pro-handicapovane': 'Postel s ohrádkou od 22 900 Kč bez roštu a matrace. Výšku ohrádky, rozměry i rošt přizpůsobíme uživateli, posuvná dvířka jsou za příplatek 1 800 Kč.',
    'postele-na-miru': '{n} modelů, od {min}. Výroba obvykle do 4 týdnů, podle nákresu, fotky nebo vašich rozměrů, 7 dřevin od smrku po dub.',
    'patrove-a-vysoke-postele': '{n} modelů, od {min}. Palandy vyrábíme od roku 1999, palanda Irena unese 400 kg na lůžko.',
    'jednoluzka': '{n} modelů, od {min}. Základní rozměr 90 × 200 cm, jiný rozměr vyrobíme na přání.',
    'dvouluzka': '{n} modelů, od {min}. Smrk až dub, nosnost nad 400 kg, záruka 5 let na typizované postele.',
    'studentske-postele': '{n} modelů, od {min}. Šířky 120 a 140 cm, s úložným prostorem nebo výsuvnou přistýlkou.',
    'dubove-postele': '{n} modelů, od {min}. Masivní dub o tloušťce 42 mm, olejovaný povrch, nosnost nad 400 kg.',
    'doplnky-k-postelim': '{n} položek, od {min}. Úložné šuplíky na kolečkách, výsuvné přistýlky, zábrany a noční stolky.',
    'komody-a-psaci-stoly': '{n} kusů, od {min}. Zásuvky na plnovýsuvech s tlumením, nosnost zásuvky 40 kg. Šatní skříně z kapacitních důvodů nevyrábíme.',
    'jidelni-stoly': '{n} stolů, od {min}. Dub, buk a borovice, rozměr i povrch upravíme podle vás.',
    'bytove-doplnky': '{n} kusů, od {min}. Výrobky skladem na prodejně v Němčičkách.',
    'dreviny-a-povrchy': 'Smrk, borovice, modřín, olše, buk, jasan a dub. Mořidla a oleje, vodou ředitelné laky.',
    'rosty-a-toppery': 'Pevný masivní rošt s nosností 500 kg od 1 260 Kč. Polohovací, motorové a lamelové rošty, toppery a chrániče matrací.',
    'matrace': '{n} matrací od {min}. Libovolný rozměr, k vyzkoušení na prodejně v Němčičkách po telefonické domluvě.',
}

SUBGROUPS = {
    'komody-a-psaci-stoly': [
        ('Komody a peřináče', r'komod|peřin'),
        ('Psací stoly', r'psac'),
        ('Šatní skříně', r'skř|skrin'),
    ],
    'doplnky-k-postelim': [
        ('Noční stolky', r'noční stol'),
        ('Úložné prostory a přistýlky', r'úložný|přistýlk'),
        ('Zábrany a madla', r'zábran|madlo|podpěr'),
    ],
}
BED_MATS = {
    'postele-pro-seniory': [
        'arela-plus-senior',
        'caeli-senior',
        'dia-relax-senior',
        'juna-senior',
        'arela-soft-senior',
    ],
    'vysokozatezove-postele': ['fortis', 'berta', 'lenka', 'andrea'],
    'postele-pro-handicapovane': ['giana', 'arella-hard', 'dia-20-hi'],
    'studentske-postele': ['gita', 'gita-plus', 'klara'],
}
BED_MATS_NOTE = {
    'postele-pro-seniory': 'Senior matrace mají zpevněný okraj z tuhé pěny, na hraně se nepropadnete. Vyzkoušet je můžete na prodejně v Němčičkách.',
    'vysokozatezove-postele': 'Matrace pro vyšší zatížení: Fortis do 180 kg, Berta do 150 kg. Máte je k vyzkoušení na prodejně.',
    'postele-pro-handicapovane': 'Pro osoby upoutané na lůžko je k dispozici antidekubitní matrace Giana.',
    'studentske-postele': 'Bezzónové matrace pro děti a dospívající, vhodné pro správný růst páteře.',
}


def is_matrace(s):
    p = B.PRODUCTS[s]
    return bool(re.search(r'(?i)matrac', B.prod_title(p))) and not re.search(
        r'(?i)chránič|hranol|potah', B.prod_title(p)
    )


def category_data(c):
    """Projde zdroje kategorie: produkty (bez duplicit), ostatní boxy a galerie ve stejném pořadí jako dřív."""
    slug, group, menu, h1, intro, sources = c
    seen, slugs, rest, headings = set(), [], [], []
    for k, src in enumerate(sources):
        pg = B.PAGES.get(src)
        if not pg:
            continue
        boxes, gal = [], None
        for b in pg['boxes']:
            if 'photogallery' in b['kind']:
                if gal is None:
                    gal = {'kind': b['kind'], 'heading': b.get('heading', ''), 'photos': []}
                    boxes.append(gal)
                gal['photos'] += b.get('photos', [])
            else:
                boxes.append(b)
        for j, b in enumerate(boxes):
            gid = f'g{k}-{j}'
            if 'products' in b['kind']:
                for it in b.get('items', []):
                    x = B.prod_slug(it['url'])
                    if x not in seen:
                        seen.add(x)
                        slugs.append(x)
                continue
            if 'photogallery' in b['kind']:
                lab = re.sub(r'^Fotogalerie:\s*', '', b.get('heading', '') or menu)
                h = gallery_html(b['photos'], gid, lab)
                if h:
                    sig = re.sub(r'data-lb="[^"]*"', '', h)
                    if sig not in seen:
                        seen.add(sig)
                        rest.append((f'Fotogalerie: {sentence_case(lab)}', h, 'gallery'))
                continue
            if src.endswith('/orientacni-cena/'):
                rest.append(('Orientační ceny', handicap_prices(b, gid), 'prices'))
                continue
            nb = normalize_box(b)
            h = B.render_box(nb, gid)
            if not h:
                continue
            sig = re.sub(r'data-lb="[^"]*"', '', h)
            if sig in seen:
                continue
            seen.add(sig)
            heading = nb.get('heading', '') if nb['kind'].startswith('list ') else ''
            rest.append((heading, h, 'box'))
    return slugs, rest


def handicap_prices(b, gid):
    """Strukturovaný přehled cen postelí s ohrádkou z textu „Orientační cena“ (data/old-site.json)."""
    ps = [x['text'].strip() for x in b['blocks'] if x['t'] == 'p']
    rows, cur = [], None
    for t in ps:
        m = re.match(r'(\d)\.\s*Rozměry na matraci\s*(\S+)', t)
        if m:
            cur = {
                'dim': m.group(2).replace('x', ' × ').replace('cm', ' cm'),
                'fence': None,
                'total': None,
                'prices': [],
            }
            rows.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r'Výška ohrádky\s*(\d+)', t)
        if m:
            cur['fence'] = int(m.group(1))
        m = re.match(r'Celková výška postele\s*(\d+)\s*cm(.*)', t)
        if m:
            cur['total'] = int(m.group(1))
            pm = re.search(r'(\d[\d ]{3,})\s*,-\s*K', m.group(2))
            if pm:
                cur['prices'].append((cur['total'], int(pm.group(1).replace(' ', ''))))
        m = re.match(r'Cena z tvrdého materiálu buk\D*(\d[\d ]{3,})\s*,-\s*K', t)
        if m and cur['total']:
            cur['prices'].append((cur['total'], int(m.group(1).replace(' ', ''))))
    items = []
    for r in rows:
        if not r['prices']:
            continue
        for k, (tot, price) in enumerate(r['prices']):
            items.append((r['dim'], r['fence'], tot, price))
    # u každé celkové výšky je cena jen jednou
    uniq, seen = [], set()
    for it in items:
        if it[:3] in seen:
            continue
        seen.add(it[:3])
        uniq.append(it)
    lis = ''.join(
        f'<li><span><b>Rozměr matrace {E(d)}</b><br>Ohrádka {f} cm, celková výška postele {t} cm</span><span class="price">{B.fmt(pr)} Kč</span></li>'
        for d, f, t, pr in uniq
        if f
    )
    notes = [
        x
        for x in ps
        if re.match(r'(Příplatek za posuvná|Ceny jsou uvedeny|Cena vyšších|Postele můžeme)', x)
    ]
    extra = ''.join(f'<p>{E(clean_text(x))}</p>' for x in notes)
    # fotografie s popisky „1. foto v. 140cm“
    tiles, cap = [], ''
    for x in b['blocks']:
        if x['t'] == 'p' and re.match(r'\d\.\s*foto', x['text'].strip()):
            cap = x['text'].strip()
        elif x['t'] == 'img':
            i = B.mid(x['src'])
            if not i or excluded(i):
                cap = ''
                continue
            alt = f'Postel s ohrádkou, {cap[3:].strip()}' if cap else 'Postel s ohrádkou'
            w, h = B.media_size(i, 's')
            tiles.append(
                f'<a href="{B.media_src(i, "l")}" data-lb="{gid}" data-cap="{E(alt)}"><img src="{B.media_src(i, "s")}" width="{w}" height="{h}" alt="{E(alt)}" loading="lazy" decoding="async"></a>'
            )
            cap = ''
    gal = (
        f'<h3>Fotografie postelí s ohrádkou</h3><div class="gal-s">{"".join(tiles)}</div>'
        if tiles
        else ''
    )
    return f'<ul class="vlist">{lis}</ul><div class="prose">{extra}</div>{gal}'


def sec(bg, inner, cls='', sid=''):
    return f'<section class="sec cat {bg}{(" " + cls) if cls else ""}"{f" id={sid}" if sid else ""}><div class="wrap">{inner}</div></section>'


def faq_inner(faq, heading='Časté dotazy'):
    if not faq:
        return ''
    items = ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in faq)
    return f'<h2 style="margin-bottom:var(--s5)">{E(heading)}</h2><div class="faq" data-fx="accordion">{items}</div><p style="margin-top:26px"><a class="link arrow" href="/caste-dotazy/">Všechny časté dotazy</a></p>'


def wall_of(slug):
    """Třída stěny místnosti, do které kategorie patří."""
    return 'wall-' + B.room_of(slug)[3]


def head_section(c, ph, facts_sentence, h1=None, lead=None, cta_label='Poptat na míru'):
    slug, group, menu, h1_, intro, _ = c
    parent = PARENT.get(group)
    items = ([parent] if parent else []) + [(menu, None)]
    room = B.room_of(slug)
    return (
        f'<section class="chead room {wall_of(slug)}"><div class="wrap">{B.crumbs(*items)}'
        f'<div class="chead-grid"><div class="chead-txt"><span class="plate">{E(room[1])}</span>'
        f'<h1>{E(h1 or h1_)}</h1><p class="lead">{E(lead or intro)}</p>'
        f'<div class="ctas"><a class="btn" href="/poptavka/?model={E(menu)}">{E(cta_label)}</a>'
        f'<a class="btn btn-2" href="tel:{B.TEL1H}">Zavolat {B.TEL1}</a></div></div>'
        f'</div></div></section>'
    )


def subnav(c):
    slug, group = c[0], c[1]
    sibs = [x for x in B.CATS if x[1] == group]
    if len(sibs) < 2:
        return ''
    lis = ''.join(
        f'<li><a href="/{x[0]}/"{" aria-current=page" if x[0] == slug else ""}>{E(x[2])}</a></li>'
        for x in sibs
    )
    hub = PARENT.get(group)
    first = (
        f'<li><a href="{hub[1]}">{E("Všechny postele" if group in BED_GROUPS else hub[0])}</a></li>'
        if hub
        else ''
    )
    return f'<nav class="subnav" aria-label="{E(B.GROUPS[group])}"><div class="wrap"><ul>{first}{lis}</ul></div></nav>'


def guide_inner(cp, slug):
    g = cp.get('guide')
    if not g:
        return ''
    ph = pick_photo(slug, 1)
    texts = ''.join(f'<div><h3>{E(t)}</h3><p>{E(x)}</p></div>' for t, x in g)
    fig = (
        f'<div class="ph r45"><img src="{ph["src"]}" width="{ph["w"]}" height="{ph["h"]}" alt="{E(ph["alt"])}" loading="lazy" decoding="async"></div>'
        if ph
        else ''
    )
    cls = 'guide2' if fig else 'guide2 nofig'
    return f'<div class="{cls}"><div><h2>Jak vybrat</h2><div class="cols">{texts}</div></div>{fig}</div>'


def mats_for_bed(slug):
    ids = BED_MATS.get(slug)
    if not ids:
        return ''
    cards = []
    for i in ids:
        it = MAT_BY_ID[i]
        link = f'/produkty/{it["product"]}/' if it.get('product') else f'/matrace/#m-{it["id"]}'
        cards.append(kcard(it, link=link, compact=True, with_id=False))
    return (
        f'<h2>Matrace k této posteli</h2><p class="lead" style="margin:12px 0 var(--s5)">{E(BED_MATS_NOTE[slug])}</p><div class="kgrid c{len(cards)}" data-fx="reveal-group">{"".join(cards)}</div>'
        f'<p style="margin-top:var(--s5)"><a class="link arrow" href="/matrace/">Všechny matrace</a></p>'
    )


def build_category(c):
    slug, group, menu, h1, intro, sources = c
    if slug == 'matrace':
        return build_matrace(c)
    if slug == 'rosty-a-toppery':
        return build_rosty(c)
    B.CURRENT['slug'] = slug
    cp = B.COPY.get(slug, {})
    slugs, rest = category_data(c)
    mats = [x for x in slugs if is_matrace(x)] if group in BED_GROUPS else []
    models = [x for x in slugs if x not in mats]
    prices = [B.PRODUCTS[x]['price'] for x in models if B.PRODUCTS[x].get('price')]
    n = len(models)
    minp = f'{B.fmt(min(prices))} Kč' if prices else ''
    facts = FACTS.get(slug, '{n} modelů, od {min}.').format(n=n, min=minp)
    ph = pick_photo(slug)
    body = [head_section(c, ph, facts), subnav(c)]
    parts = (
        []
    )  # (vnitřek sekce, třída); pozadí se střídá až při skládání, aby nikdy nebyly dvě stejné za sebou
    # hlavní blok: mřížka(y) modelů, případně strukturovaný přehled cen
    prices_html = next((h for hd, h, kind in rest if kind == 'prices'), '')
    dense = n > 16
    grid_html = ''
    if models:
        if slug in SUBGROUPS:
            used, groups = set(), []
            for label, rx in SUBGROUPS[slug]:
                part = [
                    x
                    for x in models
                    if re.search(rx, nice_title(B.PRODUCTS[x]).lower()) and x not in used
                ]
                used.update(part)
                if part:
                    note = ''
                    if label == 'Šatní skříně':
                        note = '<p class="lead" style="margin-bottom:var(--s4)">Výrobu šatních skříní máme z kapacitních důvodů pozastavenou. Ukázky z dřívějších zakázek.</p>'
                    groups.append((label, part, note))
            other = [x for x in models if x not in used]
            if other:
                groups.append(('Další', other, ''))
            grid_html = ''.join(
                f'<h2 class="block-title">{E(lb)}</h2>{nt}{grid(pt, fold=8 if dense else 6, limit=8, dense=dense)}'
                for lb, pt, nt in groups
            )
        else:
            grid_html = grid(models, fold=8 if dense else 9, dense=dense)
    elif prices_html:
        grid_html = f'<h2>Orientační ceny postelí s ohrádkou</h2><p class="lead" style="margin:12px 0 var(--s4)">Každou postel vyrábíme na míru, ceny jsou bez roštu a matrace.</p>{prices_html}'
    if grid_html:
        parts.append((grid_html, ''))
    mh = mats_for_bed(slug)
    if mh:
        parts.append((mh, ''))
    gd = guide_inner(cp, slug)
    if gd:
        parts.append((gd, ''))
    det = [(hd, h) for hd, h, kind in rest if kind != 'prices']
    if det:
        inner = '<h2 style="margin-bottom:var(--s5)">Podrobnosti a fotogalerie</h2>' + ''.join(
            (f'<h3 class="block-title">{E(hd)}</h3>' if hd else '')
            + f'<div class="detail-block">{h}</div>'
            for hd, h in det
        )
        parts.append((inner, 'details'))
    if cp.get('faq'):
        parts.append((faq_inner(cp['faq']), ''))
    for k, (inner, cls) in enumerate(parts):
        body.append(sec('paper' if k % 2 == 0 else wall_of(slug), inner, cls))
    body.append(
        B.cta_band(
            title='Chcete jiný rozměr nebo provedení?',
            text='Napište nebo zavolejte. Vyrobíme podle vašich rozměrů, nákresu nebo fotky.',
            model=menu,
        )
    )
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            B.crumbs_ld(([PARENT[group]] if group in PARENT else []) + [(menu, f'/{slug}/')]),
            {
                "@type": "CollectionPage",
                "name": h1,
                "description": cp.get('desc', intro),
                "url": B.SITE + f'/{slug}/',
            },
        ]
        + ([B.faq_ld(cp['faq'])] if cp.get('faq') else []),
    }
    B.page(
        f'/{slug}/',
        cp.get('title', h1),
        cp.get('desc', intro)[:158],
        '\n'.join(body),
        jsonld=ld,
        og_img=B.SITE + ph['src'],
    )


# ======================================================================================================
# 4) Matrace a rošty
# ======================================================================================================
def build_matrace(c):
    slug, group, menu, h1, intro, sources = c
    B.CURRENT['slug'] = slug
    cp = B.COPY.get(slug, {})
    mats = MAT['matrace']
    prices = [m['price'] for m in mats if m.get('price')]
    facts = FACTS['matrace'].format(n=len(mats), min=f'{B.fmt(min(prices))} Kč')
    ph = pick_photo(slug)
    counts = {f['id']: sum(1 for m in mats if f['id'] in m['tags']) for f in MAT['filters']}
    flt = [f for f in MAT['filters'] if counts[f['id']] >= 2]
    markers = '<span class="mk" id="f-all"></span>' + ''.join(
        f'<span class="mk" id="f-{f["id"]}"></span>' for f in flt
    )
    links = f'<a href="#f-all">Všechny ({len(mats)})</a>' + ''.join(
        f'<a href="#f-{f["id"]}">{E(f["label"])} ({counts[f["id"]]})</a>' for f in flt
    )
    cards = ''.join(
        kcard(m, link=(f'/produkty/{m["product"]}/' if m.get('product') else None)) for m in mats
    )
    sel = (
        f'<h2>Matrace podle potřeby</h2>{markers}<nav class="filters" aria-label="Filtr matrací">{links}</nav>'
        f'<div class="kgrid dense" data-fx="reveal-group">{cards}</div>'
    )
    potahy = ''.join(
        f'<dt>{E(p["name"])}</dt><dd><b>{B.fmt(p["price"])} Kč</b> příplatek</dd>'
        for p in MAT['potahy']
    )
    hr = B.PRODUCTS.get('matracovy-hranol')
    hranol = (
        (
            f'<p style="margin-top:var(--s4)">K matracím nabízíme také <a class="link" href="/produkty/matracovy-hranol/">matracový hranol</a> z PUR pěny se snímatelným potahem, {E(B.price_label(hr))}. '
            f'Vyplní volný prostor mezi dvěma jednolůžky nebo u zdi.</p>'
        )
        if hr
        else ''
    )
    pot = sec(
        wall_of(slug),
        f'<div class="split2"><div><h2>Výběr potahu</h2><p class="lead" style="margin:12px 0 0">Většina matrací má standardní potah prošitý bavlněným nebo vlněným rounem. U všech matrací můžete přiobjednat speciální potah, pokud není uvedený v ceně přímo u matrace.</p>{hranol}</div>'
        f'<dl class="spec">{potahy}</dl></div>',
    )
    reco = ''.join(
        f'<li><h3>{E(up(r["need"]))}</h3><p>{E(up(r["text"]))}</p></li>' for r in MAT['doporuceni']
    )
    guide = sec(
        'paper',
        f'<h2 style="margin-bottom:var(--s3)">Jak vybrat matraci</h2><p class="lead" style="margin-bottom:var(--s5)">Doporučení podle toho, co vás trápí nebo k čemu matraci potřebujete.</p><ul class="reco">{reco}</ul>',
    )
    body = [
        head_section(c, ph, facts, cta_label='Poptat matraci'),
        subnav(c),
        sec('paper', sel, sid='vyber'),
        pot,
        guide,
        sec(wall_of(slug), faq_inner(cp.get('faq'))),
        B.cta_band(
            title='Nenašli jste svou matraci?',
            text='Vyrobíme libovolný rozměr. Zavolejte nebo napište, poradíme podle vašeho spaní a váhy.',
            model='Matrace',
        ),
    ]
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            B.crumbs_ld([(menu, f'/{slug}/')]),
            {
                "@type": "CollectionPage",
                "name": h1,
                "description": cp.get('desc', intro),
                "url": B.SITE + f'/{slug}/',
            },
            B.faq_ld(cp['faq']),
        ],
    }
    B.page(
        f'/{slug}/',
        cp.get('title', h1),
        cp.get('desc', intro)[:158],
        '\n'.join(body),
        jsonld=ld,
        og_img=B.SITE + ph['src'],
    )


def build_rosty(c):
    slug, group, menu, h1, intro, sources = c
    B.CURRENT['slug'] = slug
    cp = B.COPY.get(slug, {})
    slugs, _ = category_data(c)
    cut = [x for x in slugs if (cover_of(x) and B.mid(cover_of(x)) in B.CUT)]
    pevne = [x for x in slugs if x not in cut]
    ph = pick_photo(slug)
    facts = FACTS[slug]
    pol = []
    for x in cut:
        p = B.PRODUCTS[x]
        it = dict(
            id='rp-' + x[:20],
            name=nice_title(p),
            sub='',
            price=p.get('price'),
            price_from=False,
            price_note='',
            specs=[],
            text=[],
            img=B.mid(cover_of(x)),
            alt=nice_title(p) + ', foto výrobku',
            tags=[],
        )
        txt = [t.strip() for t in (b['text'] for b in p['text'] if b['t'] == 'p') if t.strip()]
        it['text'] = [t for t in txt if not NOISE.search(t)]
        it['specs'] = [b['text'].strip() for b in p['text'] if b['t'] == 'li']
        derive(it)
        pol.append((it, f'/produkty/{x}/'))
    lam = [(it, None) for it in MAT['rosty']]
    pol_cards = ''.join(kcard(it, link=lk, with_id=False) for it, lk in pol + lam)
    top_cards = [kcard(it) for it in MAT['toppery']]
    top = f'<div class="kgrid" data-fx="reveal-group">{"".join(top_cards[:8])}</div>'
    if len(top_cards) > 8:
        n = len(top_cards) - 8
        top += (
            f'<details class="more"><summary class="btn btn-2"><span class="w-closed">Zobrazit dalších {n} {plural(n, "položku", "položky", "položek")}</span><span class="w-open">Skrýt dalších {n}</span></summary>'
            f'<div class="kgrid">{"".join(top_cards[8:])}</div></details>'
        )
    body = [
        head_section(c, ph, facts, cta_label='Poptat rošt'),
        subnav(c),
        sec(
            'paper',
            f'<h2>Pevné masivní rošty</h2><p class="lead" style="margin:12px 0 var(--s5)">Rošt s nosností 500 kg ke každé posteli, ceny od 1 260 Kč. Delší a výklopné provedení i rošty na dvoulůžko.</p>{grid(pevne, dense=True)}',
        ),
        sec(
            wall_of(slug),
            f'<h2>Polohovací, motorové a lamelové rošty</h2><p class="lead" style="margin:12px 0 var(--s5)">Ruční polohování popruhy, motorové s dálkovým ovládáním i pružné lamelové rošty Cordo.</p><div class="kgrid" data-fx="reveal-group">{pol_cards}</div>',
        ),
        sec(
            'paper',
            f'<h2>Toppery, chrániče a klíny</h2><p class="lead" style="margin:12px 0 var(--s5)">Podložky na matraci, vodonepropustné chrániče a polštářové klíny.</p>{top}',
        ),
        sec(wall_of(slug), faq_inner(cp.get('faq'))),
        B.cta_band(
            title='Potřebujete rošt na míru?',
            text='Rošty vyrobíme v libovolném rozměru. Napište nebo zavolejte.',
            model='Rošt',
        ),
    ]
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            B.crumbs_ld([(menu, f'/{slug}/')]),
            {
                "@type": "CollectionPage",
                "name": h1,
                "description": cp.get('desc', intro),
                "url": B.SITE + f'/{slug}/',
            },
        ]
        + ([B.faq_ld(cp['faq'])] if cp.get('faq') else []),
    }
    B.page(
        f'/{slug}/',
        cp.get('title', h1),
        cp.get('desc', intro)[:158],
        '\n'.join(body),
        jsonld=ld,
        og_img=B.SITE + ph['src'],
    )


# ======================================================================================================
# 5) Produkt
# ======================================================================================================
SPECIES = [
    (r'jádrov\w* buk|buk\w* jádrov\w*', 'jádrový buk'),
    (r'\bbuk\w*', 'buk'),
    (r'\bdub\w*|\bcelodubov\w*', 'dub'),
    (r'\bsmrk\w*', 'smrk'),
    (r'\bborovic\w*', 'borovice'),
    (r'\bjasan\w*', 'jasan'),
    (r'\bmodřín\w*', 'modřín'),
    (r'\bolš\w*', 'olše'),
    (r'\bbřez\w*', 'bříza'),
]


def species(text):
    found = []
    for rx, label in SPECIES:
        m = re.search(rx, text, re.I)
        if m:
            found.append((m.start(), label))
    found.sort()
    labels = []
    for _, l in found:
        if l == 'buk' and 'jádrový buk' in [x[1] for x in found]:
            continue
        if l not in labels:
            labels.append(l)
    labels = labels[:3]
    return ' nebo '.join(labels) if len(labels) == 2 else ', '.join(labels)


GROUP_RX = [
    ('Cena a příplatky', r'cena|příplatek|kč\b|přiobjednat'),
    ('Povrch', r'\blak|lakov|olej|mořen|moření|mořidl|\bpovrch|nátěr|\bbarv|dekor'),
    ('Rozměry', None),
    ('Konstrukce', None),
]


def classify(cl):
    l = cl.lower()
    if re.search(GROUP_RX[0][1], l):
        return 'Cena a příplatky'
    if re.search(GROUP_RX[1][1], l):
        return 'Povrch'
    dim = re.search(r'výšk|rozměr|roz\.|délk|šířk|šíř|hloubk|\d\s*x\s*\d', l)
    con = re.search(
        r'tl\.|tloušť|nosnost|\bkg\b|\bnoh|bočnic|masiv|materiál|konstruk|zásuvk|plnovýsuv|čep|spoj|pevnost|stabil|rošt|jádro|pěn|vrstv|potah|římsa',
        l,
    )
    if con and not dim:
        return 'Konstrukce'
    if dim or re.search(r'\bcm\b|\bmm\b|\d\s*(cm|mm)', l):
        return 'Rozměry'
    return 'Konstrukce'


def describe(p):
    """Popis produktu rozdělený na krátké odstavce s nadpisy h3 (úvod, konstrukce, rozměry, povrch, cena)."""
    seen_p, paras = set(), []
    for b in p.get('text', []):
        if b['t'] != 'p':
            continue
        t = b['text'].strip()
        if not t or t in seen_p or re.fullmatch(r'[-—_ ]+', t):
            continue
        seen_p.add(t)
        paras.append(clean_text(t))
    sents = []
    for t in paras:
        for s in split_sentences(t):
            if NOISE.search(s):
                s = re.sub(
                    r'(?i)[,;]?\s*(poptávkový|poptat nebo|formulář|více zde|viz níže)[^.]*', '', s
                ).strip(' ,;')
                if not s or NOISE.search(s):
                    continue
            sents.append(s.strip().rstrip('.'))
    intro = ''
    groups = {k: [] for k, _ in GROUP_RX}
    first = True
    for si, s in enumerate(sents):
        clauses = s.split(', ')
        if first:
            first = False
            if len(s) <= 170:
                intro = s
                continue
            intro = (
                clauses[0] if len(clauses[0]) >= 40 or len(clauses) < 2 else ', '.join(clauses[:2])
            )
            clauses = clauses[len(intro.split(', ')) :]
        for cl in clauses:
            if cl.strip():
                groups[classify(cl)].append((si, cl.strip()))
    out = []
    if intro:
        out.append((None, [up(intro) + ('' if intro.endswith(('!', '?')) else '.')]))
    for name in ('Konstrukce', 'Rozměry', 'Povrch', 'Cena a příplatky'):
        items = groups[name]
        if not items:
            continue
        sent, last = [], None
        for si, cl in items:
            if si != last:
                sent.append([cl])
                last = si
            else:
                sent[-1].append(cl)
        out.append(
            (name, [up(', '.join(x)) + ('' if x[-1].endswith(('!', '?')) else '.') for x in sent])
        )
    return out


def surface(p):
    for b in p.get('text', []):
        if b['t'] != 'p':
            continue
        for s in split_sentences(b['text']):
            for cl in s.split(', '):
                l = cl.lower()
                if (
                    re.search(r'\blakov|\blak\b|\blakem|olej|mořen|moření|mořidl|vodouředit', l)
                    and not re.search(GROUP_RX[0][1], l)
                    and len(cl) <= 72
                    and not re.match(r'(?i)na fot|viz|na obr', cl.strip())
                ):
                    return up(cl.strip().rstrip('.'))
    return ''


def params(s, p, group, title):
    rows = []
    mt = MAT_BY_PRODUCT.get(s)
    if mt:
        for o in p.get('options', []):
            if re.search(r'(?i)rozm', o['label']):
                rows.append(('Rozměr matrace', ', '.join(o['values'])))
        if mt.get('height'):
            rows.append(('Výška', f'{mt["height"]} cm'))
        if mt.get('load'):
            rows.append(('Nosnost', f'{mt["load"]} kg'))
        if mt.get('firm'):
            rows.append(('Tuhost', mt['firm']))
        for o in p.get('options', []):
            if not re.search(r'(?i)rozm', o['label']):
                rows.append((up(o['label']), ', '.join(o['values'])))
        return rows
    for o in p.get('options', []):
        lab = up(o['label'])
        if re.fullmatch(r'(?i)rozm\w* na matrac\w*', o['label'].strip()):
            lab = 'Rozměr matrace'
        rows.append((lab, ', '.join(o['values'])))
    bed_or_furn = group not in ('spanek', 'info')
    if bed_or_furn:
        sp = species(B.prod_desc_text(p) + ' ' + title)
        if sp and not any(r[0] == 'Dřevina' for r in rows):
            rows.append(('Dřevina', sp))
        sf = surface(p)
        if sf:
            rows.append(('Povrch', sf))
        flags = B.prod_flags(p)
        rows.append(
            ('Výroba', 'skladem na prodejně' if 'Skladem' in flags else 'obvykle do 4 týdnů')
        )
    return rows[:6]


def thumbs_gallery(imgs, title):
    if not imgs:
        return '<div class="gal"><div class="ph noimg"><span>Fotografii tohoto modelu pošleme na vyžádání. Zavolejte nebo napište.</span></div></div>'
    imgs = imgs[:10]
    ids = [B.mid(u) for u in imgs]
    i0 = ids[0]
    w, h = B.media_size(i0, 'l')
    alt0 = title
    cut0 = ' is-cut' if i0 in B.CUT else ''
    lbattr = f' data-lb="prod" data-cap="{E(title)}"' if len(imgs) == 1 else ''
    main = (
        f'<figure class="fx-thumbs-main{cut0}"><a href="{B.media_src(i0, "l")}"{lbattr}><img src="{B.media_src(i0, "l")}" width="{w}" height="{h}" alt="{E(alt0)}" fetchpriority="high"></a>'
        f'<figcaption>{E(alt0)}</figcaption></figure>'
    )
    if len(imgs) == 1:
        return f'<div class="gal one">{main}</div>'
    lis, lbs = [], []
    for k, (u, i) in enumerate(zip(imgs, ids)):
        alt = title if k == 0 else f'{title}, foto {k + 1}'
        tw, th = B.media_size(i, 's')
        lis.append(
            f'<li><a href="{B.media_src(i, "l")}"{" data-cut=1" if i in B.CUT else ""}><img src="{B.media_src(i, "s")}" width="{tw}" height="{th}" alt="{E(alt)}" loading="lazy" decoding="async"></a></li>'
        )
        lbs.append(
            f'<a href="{B.media_src(i, "l")}" data-lb="prod" data-cap="{E(alt)}" tabindex="-1" aria-hidden="true"></a>'
        )
    script = (
        '<script>(function(){var g=document.querySelector("[data-gal]");if(!g)return;var m=g.querySelector(".fx-thumbs-main"),s=[].slice.call(g.querySelectorAll(".fx-thumbs-strip a")),h=[].slice.call(g.querySelectorAll(".gal-lb a"));'
        'function cur(){for(var i=0;i<s.length;i++)if(s[i].getAttribute("aria-current")==="true")return i;return 0}'
        'function sync(){var a=s[cur()];m.classList.toggle("is-cut",!!(a&&a.dataset.cut))}'
        'if(window.MutationObserver)new MutationObserver(sync).observe(g.querySelector(".fx-thumbs-strip"),{attributes:true,subtree:true,attributeFilter:["aria-current"]});'
        'm.addEventListener("click",function(e){var a=h[cur()]||h[0];if(a){e.preventDefault();e.stopPropagation();a.click()}});sync()})();</script>'
    )
    return f'<div class="gal" data-gal data-fx="thumbs">{main}<ul class="fx-thumbs-strip">{"".join(lis)}</ul><div class="gal-lb">{"".join(lbs)}</div></div>{script}'


CAT_LIST = {}


def cat_list(slug):
    if slug not in CAT_LIST:
        CAT_LIST[slug] = category_data(B.CAT_BY_SLUG[slug])[0]
    return CAT_LIST[slug]


def build_product(s):
    p = B.PRODUCTS[s]
    cat = B.CAT_BY_SLUG.get(B.PROD_CAT.get(s, ''))
    group = cat[1] if cat else ''
    title = nice_title(p)
    imgs = keep_imgs(prod_images(s))
    desc = describe(p)
    lis = [
        b['text'].strip()
        for b in p.get('text', [])
        if b['t'] == 'li' and b['text'].strip() and not NOISE.search(b['text'])
    ]
    mt = MAT_BY_PRODUCT.get(s)
    prose = ''.join(
        (f'<h3>{E(h)}</h3>' if h else '') + ''.join(f'<p>{B.linkify(x)}</p>' for x in ps)
        for h, ps in desc
    )
    if lis:
        prose += (
            '<h3>Parametry</h3><ul class="bul">'
            + ''.join(f'<li>{E(up(x))}</li>' for x in lis)
            + '</ul>'
        )
    prose = prose.replace(
        'Poptat nebo objednat je možné ve formuláři níže.',
        'Poptat nebo objednat můžete ve formuláři níže.',
    )
    rows = params(s, p, group, title)
    dl = (
        f'<dl class="spec sm">{"".join(f"<dt>{E(a)}</dt><dd>{E(b)}</dd>" for a, b in rows)}</dl>'
        if rows
        else ''
    )
    flags = B.prod_flags(p)
    is_bed = group in BED_GROUPS
    if p.get('price'):
        note = (
            'Orientační cena bez roštu a matrace. Přesnou cenu pošleme písemně.'
            if is_bed
            else 'Orientační cena podle ceníku. Přesnou cenu pošleme v písemné nabídce.'
        )
        price = f'<p class="price-big">{B.fmt(p["price"])} Kč</p><p class="note">{note}{" Akční cena." if "Akční cena" in flags else ""}{" Skladem na prodejně." if "Skladem" in flags else ""}</p>'
    else:
        price = f'<p class="price-big req">{E(B.price_label(p))}</p><p class="note">Cenu pošleme v písemné nabídce, stačí zavolat nebo napsat.</p>'
    if is_bed:
        facts = 'Dovoz naším autem a montáž zdarma, po ČR i SR. Na typizované postele dáváme záruku 5 let. K vyzkoušení na prodejně v Němčičkách po telefonické domluvě.'
    elif group == 'spanek':
        facts = 'K vyzkoušení na prodejně v Němčičkách po telefonické domluvě. Libovolný rozměr vyrobíme na přání.'
    else:
        facts = 'Dovoz naším autem po ČR i SR, odborná montáž při dovozu zdarma. Prohlédnout si ho můžete na prodejně v Němčičkách po telefonické domluvě.'
    panel = (
        f'<div class="panel"><h1>{E(title)}</h1>{price}{dl}<div class="ctas"><a class="btn btn-block" href="#poptavka">Poptat tento model</a>'
        f'<a class="btn btn-2 btn-block" href="tel:{B.TEL1H}">Zavolat {B.TEL1}</a></div><p class="small" style="margin-top:var(--s3)">{E(facts)}</p></div>'
    )
    # další modely: čtyři následující ve stejné kategorii a stejného druhu (postel x matrace)
    more = ''
    if cat:
        lst = [x for x in cat_list(cat[0]) if is_matrace(x) == is_matrace(s)]
        if s in lst:
            k = lst.index(s)
            rel = (lst[k + 1 :] + lst[:k])[:4]
        else:
            rel = [x for x in lst if x != s][:4]
        if rel:
            more = sec(
                'stone',
                f'<div class="sec-head"><h2>Další modely v kategorii</h2><a class="link arrow" href="/{cat[0]}/">{E(cat[2])}</a></div><div class="models">{"".join(card(x, lazy=True) for x in rel)}</div>',
            )
    desc_txt = B.prod_desc_text(p)[:155] or f'{title} z masivu od Stolařství Kubiš.'
    crumb_items = (
        ([PARENT[group]] if group in PARENT else [])
        + ([(cat[2], f'/{cat[0]}/')] if cat else [])
        + [(title, None)]
    )
    room_wall = wall_of(cat[0]) if cat else 'wall-paper'
    body = f'''<article>
<section class="sec room {room_wall} prodsec tight"><div class="wrap">{B.crumbs(*crumb_items)}
<div class="prodwrap">
  <div class="p-gal">{thumbs_gallery(imgs, title)}</div>
  <div class="p-panel">{panel}</div>
  <div class="p-desc"><div class="desc">{prose}</div></div>
</div></div></section>
{more}
{B.form_html(model=title, title=f'Poptat: {title}')}
</article>'''
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            B.crumbs_ld(
                ([PARENT[group]] if group in PARENT else [])
                + ([(cat[2], f'/{cat[0]}/')] if cat else [])
                + [(title, f'/produkty/{s}/')]
            ),
            {
                "@type": "Product",
                "name": title,
                "description": B.prod_desc_text(p)[:500],
                "brand": {"@type": "Brand", "name": "Stolařství Kubiš"},
                "image": [B.SITE + B.media_src(B.mid(u), 'l') for u in imgs[:4]],
                **(
                    {
                        "offers": {
                            "@type": "Offer",
                            "price": p['price'],
                            "priceCurrency": "CZK",
                            "availability": (
                                "https://schema.org/InStock"
                                if 'Skladem' in flags
                                else "https://schema.org/MadeToOrder"
                            ),
                            "seller": {"@type": "Organization", "name": "Stolařství Kubiš"},
                        }
                    }
                    if p.get('price')
                    else {}
                ),
            },
        ],
    }
    tkey = B.prod_title(p).lower()
    page_title = f'{title}, {B.price_label(p)}' if B.TITLE_COUNT.get(tkey, 0) > 1 else title
    B.page(
        f'/produkty/{s}/',
        page_title,
        desc_txt,
        body,
        jsonld=ld,
        og_img=B.SITE + B.media_src(B.mid(imgs[0]), 'l') if imgs else None,
    )


B.build_category = build_category
B.build_product = build_product

if __name__ == '__main__' and sys.argv[1:] == ['parse']:
    d = parse_matrace()
    print(
        len(d['matrace']),
        'matrací,',
        len(d['rosty']),
        'roštů,',
        len(d['toppery']),
        'topperů,',
        len(d['potahy']),
        'potahů,',
        len(d['doporuceni']),
        'doporučení',
    )
