"""Úvodní stránka a rozcestníky (/postele-z-masivu/, /nabytek-z-masivu/) pro design „Dílna ve dne“.

Modul přepisuje funkce z build.py (viz make.py). Vše se bere z dat build.py (ceny, počty, názvy),
ručně psané jsou jen věty s údaji a výběr modelů a fotek.
"""

import re
from pathlib import Path
import build as B

try:
    from PIL import Image
except Exception:  # bez PIL se rozměry /img/ fotek vezmou z COVERS
    Image = None

E, fmt = B.E, B.fmt
NB = ' '


# ---------------------------------------------------------------- pomocné funkce
def kc(n):
    return f'{fmt(n).replace(" ", NB)}{NB}Kč'


def pic(path, alt='', size='l', lazy=True, cls='', pos=None):
    """<img> pro fotku z web/media (podle id) nebo web/img (podle názvu); vždy s width/height."""
    m = re.search(r'(\d{9}-[0-9a-f]{10})', path)
    i = m.group(1) if m else None
    if i and (i in B.SIZES or i in B.CUT):
        w, h = B.media_size(i, size)
        src = B.media_src(i, size)
        if i in B.CUT:
            cls = (cls + ' cut').strip()
    else:
        name = Path(path).name
        f = B.ROOT / 'web' / 'img' / name
        if Image is not None and f.exists():
            w, h = Image.open(f).size
        else:
            w, h = next(
                ((c[1], c[2]) for c in B.COVERS.values() if c[0] + '.jpg' == name), (1400, 1050)
            )
        src = '/img/' + name
    attrs = f' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    st = f' style="object-position:{pos}"' if pos else ''
    return f'<img src="{src}" width="{w}" height="{h}" alt="{E(alt)}"{attrs}{f" class=\"{cls}\"" if cls else ""}{st}>'


def prod_img(s, alt='', size='s', lazy=True):
    p = B.PRODUCTS[s]
    u = next((u for u in (*(p.get('images') or []), p.get('thumb')) if B.mid(u)), None)
    return B.img_tag(u, alt, size=size, lazy=lazy) if u else ''


def cat_slugs(slug):
    """Slugy produktů kategorie ve stejném pořadí jako na stránce kategorie."""
    out = []
    for src in B.CAT_BY_SLUG[slug][5]:
        pg = B.PAGES.get(src)
        if not pg:
            continue
        for b in pg['boxes']:
            if 'products' in b['kind']:
                for it in b.get('items', []):
                    s = B.prod_slug(it['url'])
                    if s in B.PRODUCTS and s not in out:
                        out.append(s)
    return out


NOT_BED = re.compile(
    r'(?i)matrac|rošt|hranol|topper|chránič|stůl|stolek|skříň|komod|madlo|zábran|přistýlk|úložný prostor|šuplík'
)


def is_bed(s):
    return not NOT_BED.search(B.prod_title(B.PRODUCTS[s]))


def beds(slug):
    return [s for s in cat_slugs(slug) if is_bed(s)]


def price_of(s):
    return B.PRODUCTS[s].get('price')


def min_price(slugs):
    ps = [price_of(s) for s in slugs if price_of(s)]
    return min(ps) if ps else None


def ohradka_slugs():
    return [
        s for s, p in B.PRODUCTS.items() if 'ohrádk' in B.prod_title(p).lower() and p.get('price')
    ]


PRICE_RE = re.compile(r'(\d[\d ]{2,})\s*,-\s*K[čČ]')


def mattresses():
    """Matrace z textu stránky /matrace/ (stránka je strukturovaná jen jako text): název, cena, výška, zátěž, id fotky."""
    out = []
    pg = B.PAGES.get('/matrace/')
    for b in (pg['boxes'] if pg else []):
        if 'wysiwyg' not in b['kind']:
            continue
        blocks = b.get('blocks', [])
        head = ' '.join(x['text'] for x in blocks if x['t'] == 'h')
        m = PRICE_RE.search(head)
        if not m or not re.search(r'(?i)matrac', head):
            continue
        name = re.sub(r'(?i)^\s*novinka!?\s*', '', head[: m.start()]).strip(' .…')
        lis = ' '.join(x['text'] for x in blocks if x['t'] == 'li')
        h = re.search(r'(?i)výška[^0-9]{0,25}(\d+)\s*cm', lis)
        z = re.search(r'(?i)zatížení\s*do\s*(\d+)\s*kg', lis)
        img = next(
            (
                B.mid(x['src']) if 'src' in x else B.mid(x.get('url', ''))
                for x in blocks
                if x['t'] == 'img'
            ),
            None,
        )
        out.append(
            dict(
                name=name,
                price=int(m.group(1).replace(' ', '')),
                h=h and h.group(1),
                z=z and z.group(1),
                img=img,
            )
        )
    return out


def mat_by(mats, key):
    return next(m for m in mats if key.lower() in m['name'].lower())


def link_list(items, cls='hub-mod'):
    """items: [(slug, krátký název)] -> seznam odkazů s cenou z dat."""
    lis = ''.join(
        f'<li><a class="link" href="/produkty/{s}/">{E(n)}</a> <span class="mp">{kc(price_of(s))}</span></li>'
        for s, n in items
        if s in B.PRODUCTS and price_of(s)
    )
    return f'<ul class="{cls}">{lis}</ul>'


def sentence_date(d):
    return '. '.join(str(int(x)) for x in d.split('.'))


def review_bits(revs):
    """Tři recenze pro úvod: (věta/věty, podpis). Texty jsou doslovné úryvky z recenzí."""

    def find(w):
        return next((r for r in revs if w in ' '.join(r['lines']).lower()), None)

    out = []
    r = find('natálk')
    if r:
        txt = next(
            (s.strip() for s in re.split(r'(?<=[.!?])\s+', r['lines'][0]) if 'Natálka' in s),
            r['lines'][0],
        )
        out.append((txt, f'{r["lines"][-1]}, {sentence_date(r["date"])}'))
    r = find('konečně můžeme vstát')
    if r:
        out.append((' '.join(r['lines'][:3]), f'{r["lines"][-1]}, {sentence_date(r["date"])}'))
    r = find('třetí postel')
    if r:
        t = r['lines'][0]
        m = re.match(r'(.*[.!?])\s+(\S+)$', t)
        out.append(
            (m.group(1), f'{m.group(2)}, {sentence_date(r["date"])}')
            if m
            else (t, sentence_date(r['date']))
        )
    return out


# ---------------------------------------------------------------- úvodní stránka
HOME_FAQ_Q = [
    'Jaká je nejlevnější postel z masivu u vás?',
    'Je v ceně postele rošt a matrace?',
    'Kolik postel unese?',
    'Jak dlouho budu na postel čekat?',
    'Kolik stojí doprava?',
    'Můžu si matraci vyzkoušet?',
]


def home_faq():
    allf = {q: a for _, items in B.FAQ_GROUPS for q, a in items}
    low = min_price(beds('jednoluzka'))
    allf[HOME_FAQ_Q[0]] = (
        f'Jednolůžka ze smrku nebo borovice začínají zhruba na {kc(low)} bez roštu a matrace. Buk a dub jsou dražší, ale trvanlivější.'
    )
    return [(q, allf[q]) for q in HOME_FAQ_Q]


BED_ROWS = [  # slug, název, údaj
    ('postele-pro-seniory', 'Pro seniory', '55 / 60 / 65 cm'),
    ('vysokozatezove-postele', 'Vysokozátěžové', '400 až 500 kg'),
    ('postele-pro-handicapovane', 'S ohrádkou, pro handicapované', None),
    ('postele-na-miru', 'Na míru a čalouněné', None),
    ('patrove-a-vysoke-postele', 'Patrové a vysoké', None),
    ('jednoluzka', 'Jednolůžka a dvoulůžka', None),
]


def bed_from(slug):
    if slug == 'postele-pro-handicapovane':
        return min_price(ohradka_slugs())
    return min_price(beds(slug))


def all_beds():
    seen = []
    for c in B.CATS:
        if c[1] in ('potreba', 'typ') and c[0] != 'doplnky-k-postelim':
            for s in beds(c[0]):
                if s not in seen:
                    seen.append(s)
    return seen


# ---------------------------------------------------------------- stavební kameny „domu“
ROOM = {r[0]: r for r in B.ROOMS}  # klíč -> (klíč, název, popis, stěna, slugy)


def plate(name):
    return f'<span class="plate">{E(name)}</span>'


def ptitle(slug, note=''):
    return f'{E(B.prod_title(B.PRODUCTS[slug]))}{E(note)} · {kc(price_of(slug))}'


def frame(img, caption, cls=''):
    """Fotka v dřevěném rámu s popiskem pod ní; img je hotové <img>."""
    return f'<figure class="frame {cls}">{img}<figcaption>{caption}</figcaption></figure>'


def ph(img, ratio='r43'):
    return f'<span class="ph {ratio}">{img}</span>'


def tags(items, cls='tags'):
    """Papírové cedulky s názvem a cenou modelu."""
    lis = ''.join(
        f'<li><a href="/produkty/{s}/"><span>{E(n)}</span> <b>{kc(price_of(s))}</b></a></li>'
        for s, n in items
        if s in B.PRODUCTS and price_of(s)
    )
    return f'<ul class="{cls}">{lis}</ul>'


def stand_list(items):
    """Řádky s názvem a cenou (jídelní lístek, seznam v obýváku)."""
    lis = ''.join(
        f'<li><a href="/produkty/{s}/"><span class="nm">{E(n)}</span><span class="dots" aria-hidden="true"></span><b class="price">{kc(price_of(s))}</b></a></li>'
        for s, n in items
        if s in B.PRODUCTS and price_of(s)
    )
    return f'<ul class="stand">{lis}</ul>'


def room_open(key, extra_cls='', wall=None):
    r = ROOM[key]
    return (
        f'<section class="room wall-{wall or r[3]} {extra_cls}" id="{r[0]}" aria-label="{E(r[1])}">'
    )


# ---------------------------------------------------------------- úvodní stránka
def build_home(revs):
    mats = mattresses()
    fortis, dia = mat_by(mats, 'Fortis'), mat_by(mats, 'DIA 20')
    mat_from = min(m['price'] for m in mats)
    rost_slug = 'pevny-rost-polohovatelny-terus-plus'
    rost_from = min_price(cat_slugs('rosty-a-toppery'))
    beds_all = all_beds()
    beds_n = len(beds_all) // 10 * 10
    beds_from = min_price(beds_all)
    det_from = min_price(beds('patrove-a-vysoke-postele') + beds('studentske-postele'))
    jid_from = min_price(cat_slugs('jidelni-stoly'))
    kom_from = min_price(cat_slugs('komody-a-psaci-stoly'))

    # --- vchod: jen velký text, rohožka
    s1 = f'''<section class="room wall-paper h-entry" aria-label="Vchod"><div class="wrap h-entry-in">
  <h1 data-fx="headline">Postele a nábytek z masivu z Němčiček u Brna</h1>
  <p class="lead">Rodinné stolařství od roku 1999. Buk, jádrový buk a dub, od postelí pro seniory po jídelní stoly. Dovezeme a smontujeme.</p>
  <div class="ctas"><a class="doormat" href="#lozince">Pojďte dál</a><a class="btn btn-2" href="tel:{B.TEL1H}">Zavolat {B.TEL1}</a></div>
</div></section>'''

    # --- ložnice: text a seznam vlevo, velký rám vpravo, pod tím police s matracemi
    rows = ''
    for slug, name, dt in BED_ROWS:
        frm = bed_from(slug)
        dt = f'<span class="dt">{E(dt)}</span>' if dt else ''
        price = f'<span class="price">od{NB}{kc(frm)}</span>' if frm else ''
        href = f'/{slug}/' if slug != 'jednoluzka' else '/postele-z-masivu/#podle-typu'
        rows += (
            f'<li><a href="{href}"><span class="nm"><h3>{E(name)}</h3>{dt}</span>{price}</a></li>'
        )

    def shelf_item(href, img, name, spec, price):
        return f'<a class="shelf-it" href="{href}"><span class="ph cut r32">{img}</span><b>{E(name)}</b>{f"<span>{E(spec)}</span>" if spec else ""}<span class="price">{kc(price)}</span></a>'

    def mspec(m):
        return ', '.join(
            x for x in (m['h'] and f'výška {m["h"]} cm', m['z'] and f'do {m["z"]} kg') if x
        )

    rost = B.PRODUCTS[rost_slug]
    s2 = f'''{room_open('lozince', 'h-loz')}
  <div class="wrap h-split" data-fx="reveal">
    <div class="rtx">{plate(ROOM['lozince'][1])}
      <h2>Postele od {kc(beds_from)}, podle toho, kdo na nich spí</h2>
      <p>Přes {beds_n} modelů. Ložná plocha má 55, 60 nebo 65 cm, nosnost je 400 kg na lůžko bez příplatku.</p>
      <ul class="h-rows">{rows}</ul></div>
    <div class="rfr">{frame(ph(pic('web/media/200005193-ed062ed065.jpg', 'Postel typ Pavla z masivu s ovčí kožešinou před cihlovou zdí', size='l', pos='50% 60%'), 'r32'), ptitle('postel-typ-pavla'))}</div>
  </div>
  <div class="wrap h-split h-shelf" data-fx="reveal">
    <div class="stx"><h3>Matrace a rošty k posteli</h3>
      <p>Přes {len(mats)} matrací od {kc(mat_from)} v libovolném rozměru, k vyzkoušení na prodejně. Pevný masivní rošt unese 500 kg a stojí od {kc(rost_from)}.</p>
      <p><a class="link arrow" href="/matrace/">Matrace</a> · <a class="link arrow" href="/rosty-a-toppery/">Rošty</a></p></div>
    <div class="shelf">
      {shelf_item('/matrace/', B.img_tag('https://x/%s/' % fortis['img'], 'Matrace Fortis, řez pěnovými vrstvami'), fortis['name'], mspec(fortis), fortis['price'])}
      {shelf_item('/matrace/', B.img_tag('https://x/%s/' % dia['img'], 'Matrace DIA 20 Hi, řez pěnovými vrstvami'), dia['name'], mspec(dia), dia['price'])}
      {shelf_item(f'/produkty/{rost_slug}/', prod_img(rost_slug, 'Polohovatelný pevný rošt Terus Plus'), B.prod_title(rost), 'polohovatelný', price_of(rost_slug))}
    </div>
  </div>
</section>'''

    # --- dětský pokoj: shluk dvou rámů vlevo, text a cedulky vpravo
    s3 = f'''{room_open('detsky', 'h-det')}
  <div class="wrap h-split" data-fx="reveal">
    <div class="cluster">
      <div class="a">{frame(ph(pic('web/media/200007097-0880308805.jpg', 'Patrová palanda Irena z masivu se žebříkem a komodou před cihlovou zdí', size='l'), 'r32'), ptitle('patrova-palanda-irena'))}</div>
      <div class="b tilt">{frame(ph(pic('web/media/200005241-5a8e65a8ea.jpg', 'Bílá studentská postel Lada s rohovým opěradlem a polštáři', size='s', pos='40% 50%'), 'r43'), ptitle('studentska-postel-lada-s-120cm'))}</div>
    </div>
    <div class="rtx">{plate(ROOM['detsky'][1])}
      <h2>Palandy a studentské postele od {kc(det_from)}</h2>
      <p>Palandy jsou náš první výrobek z roku 1999. Irena unese 400 kg na lůžko, takže se hodí i pro dospělé.</p>
      {tags([('patrova-palanda-irena', 'Palanda Irena'), ('vysoka-postel-gizell', 'Vysoká postel Gizell'), ('jeden-a-pul-luzko-dita', 'Dita 1,5 lůžko'), ('studentska-postel-magda', 'Studentská Magda')])}
      <p class="more"><a class="link arrow" href="/patrove-a-vysoke-postele/">Patrové a vysoké</a> · <a class="link arrow" href="/studentske-postele/">Studentské</a></p></div>
  </div>
</section>'''

    # --- jídelna: text a jídelní lístek vlevo, rám vpravo
    s4 = f'''{room_open('jidelna', 'h-jid')}
  <div class="wrap h-split" data-fx="reveal">
    <div class="rtx">{plate(ROOM['jidelna'][1])}
      <h2>Jídelní stoly od {kc(jid_from)}</h2>
      <p>Deska je olejovaná Adler Legno, vhodným i na potraviny. Rozměr stolu přizpůsobíme vaší jídelně.</p>
      <div class="menu"><h3>Jídelní lístek</h3>{stand_list([('konferencni-stolek-mark-2450-kc', 'Konferenční stolek Mark'), ('borovicovy-jidelni-stul-oskar-3500-kc', 'Borovicový stůl Oskar'), ('dubovy-jidelni-stul-denisa-7200-kc', 'Dubový stůl Denisa')])}</div>
      <p class="more"><a class="link arrow" href="/jidelni-stoly/">Všechny jídelní stoly</a></p></div>
    <div class="rfr">{frame(ph(pic('web/media/200005134-0a9840a987.jpg', 'Dubový jídelní stůl Denisa s deskou z lepených prken a černými ocelovými nohami', size='l'), 'r43'), ptitle('dubovy-jidelni-stul-denisa-7200-kc'))}</div>
  </div>
</section>'''

    # --- obývák a pracovna: dva rámy vlevo (druhý níž), text vpravo
    s5 = f'''{room_open('obyvak', 'h-obv')}
  <div class="wrap h-split" data-fx="reveal">
    <div class="figs">
      {frame(ph(pic('web/media/200006994-1152311524.jpg', 'Zásuvková komoda KPC z masivu před cihlovou zdí', size='s'), 'r45'), ptitle('zasuvkova-komoda-kpc'))}
      {frame(ph(pic('web/media/200000314-9172f91bc1.jpg', 'Smrková zásuvková komoda s osmi zásuvkami a dřevěnými knoflíky', size='s'), 'r45'), f'Smrková zásuvková komoda · komody od {kc(kom_from)}', 'off')}
    </div>
    <div class="rtx">{plate(ROOM['obyvak'][1])}
      <h2>Komody a psací stoly od {kc(kom_from)}</h2>
      <p>Zásuvky jedou na plnovýsuvech s tlumením a unesou 40 kg. Materiál je smrk, borovice nebo buk, rozměry podle vás.</p>
      {stand_list([('komoda-na-luzkoviny-perinac', 'Komoda na lůžkoviny'), ('zasuvkova-komoda-kpc', 'Komoda KPC'), ('psaci-stul-robin-9670-kc', 'Psací stůl Robin'), ('odkladaci-stolek-na-koleckach', 'Odkládací stolek'), ('vesakova-stena-1280-kc', 'Věšáková stěna')])}
      <div class="ctas"><a class="btn" href="/nabytek-z-masivu/">Nábytek na zakázku</a></div></div>
  </div>
</section>'''

    # --- dílna: postup, co platí, recenze, prodejna, dotazy
    rb = review_bits(revs)
    big = (
        f'<div class="big"><figure><blockquote><p>„{E(rb[0][0])}“</p></blockquote><figcaption>{E(rb[0][1])}</figcaption></figure><a class="link arrow" href="/realizace-a-recenze/">Všech {len(revs)} recenzí</a></div>'
        if rb
        else ''
    )
    small = ''.join(
        f'<figure><blockquote><p>„{E(t)}“</p></blockquote><figcaption>{E(sg)}</figcaption></figure>'
        for t, sg in rb[1:]
    )
    hf = home_faq()
    det = ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in hf)
    s6 = f'''{room_open('dilna', 'h-dil')}
  <div class="wrap">
    <div class="h-split h-rules" data-fx="reveal">
      <div class="c0">{plate(ROOM['dilna'][1])}<h2>Jak objednávka probíhá a co u nás platí</h2></div>
      <div class="c1"><ol class="h-steps"><li><b>Poptávka.</b> Zavolejte nebo napište, doptáme se na rozměr, dřevinu a na to, kdo bude na posteli spát.</li>
      <li><b>Nabídka.</b> Pošleme písemně popis, materiál, rozměry, cenu a termín. Po vašem souhlasu vystavíme zálohový list.</li>
      <li><b>Výroba.</b> Postel na míru děláme obvykle do 4 týdnů.</li>
      <li><b>Dovoz a montáž.</b> Přivezeme ji vlastním autem a na místě smontujeme.</li></ol></div>
      <div class="c2"><dl class="spec">
        <dt>Nosnost postelí</dt><dd><b>400 kg</b> na lůžko bez příplatku, vybrané modely z buku a dubu 500 kg</dd>
        <dt>Výška ložné plochy</dt><dd><b>55 cm</b> klasická, <b>60 cm</b> senior, <b>65 cm</b> pro vyšší postavy (k povrchu matrace)</dd>
        <dt>Materiál</dt><dd>masiv o tloušťce <b>40 mm</b>, buk, jasan, dub, u dubových postelí 42 mm</dd>
        <dt>Povrch</dt><dd>vodou ředitelné laky a mořidla, dub olejem</dd>
        <dt>Záruka</dt><dd><b>5 let</b> na typizované postele, u atypických a ostatního nábytku zpravidla 2 roky</dd>
        <dt>Výroba</dt><dd>postel nebo nábytek na míru zhruba <b>do 4 týdnů</b></dd>
        <dt>Doprava</dt><dd>vlastním autem po ČR i SR, <b>14 Kč/km</b> tam i zpět, nejméně 300 Kč. Montáž při dovozu zdarma.</dd>
      </dl></div>
    </div>
    <div class="dsub h-rev" data-fx="reveal"><div class="h-rev-grid">{big}<div class="small-q">{small}</div></div></div>
    <div class="dsub h-split h-shop" data-fx="reveal">
      <div class="rfr">{frame(ph(pic('web/img/prodejna-2.jpg', 'Postele a matrace v ukázkové prodejně v Němčičkách', size='l'), 'r43'), 'Ukázková prodejna v Němčičkách')}</div>
      <div class="rtx"><h2>Prodejna v Němčičkách</h2>
        <p>Postele, nábytek a matrace od českých výrobců si můžete prohlédnout a vyzkoušet u nás v Němčičkách č. 5, 664 66 Němčičky u Židlochovic. <b>Návštěvu domluvte předem telefonem.</b></p>
        <dl class="hours"><dt>Po–Pá</dt><dd>15–20 h, po domluvě</dd><dt>So–Ne</dt><dd>9–20 h, po domluvě</dd></dl>
        <a class="h-tel" href="tel:{B.TEL1H}">{B.TEL1}</a>
        <div class="ctas"><a class="btn" href="/prodejna-nemcicky/">Mapa a adresa</a><a class="btn btn-2" href="/poptavka/">Napsat dotaz</a></div></div>
    </div>
    <div class="dsub h-split h-faq" data-fx="reveal">
      <div class="head"><h2>Časté dotazy</h2><p><a class="link arrow" href="/caste-dotazy/">Všechny časté dotazy</a></p></div>
      <div class="faq" data-fx="accordion" data-fx-single>{det}</div>
    </div>
  </div>
</section>'''

    s7 = B.form_html(
        title='Napište nám, co potřebujete',
        intro='Rozměr, dřevinu a pro koho postel bude. Ozveme se a pošleme nabídku.',
    )

    body = '\n'.join([s1, s2, s3, s4, s5, s6, s7])
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "FurnitureStore",
                "@id": B.SITE + "/#firma",
                "name": "Stolařství Kubiš",
                "url": B.SITE + "/",
                "description": "Rodinné stolařství z Němčiček u Brna vyrábějící nábytek z masivu na míru, hlavně postele: zvýšené postele pro seniory, vysokozátěžové postele s nosností až 500 kg, postele s ohrádkou pro handicapované.",
                "telephone": "+420604107577",
                "email": B.MAIL,
                "foundingDate": "1999",
                "founder": {"@type": "Person", "name": "Petr Kubiš"},
                "image": B.SITE + "/img/og.jpg",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "Němčičky 5",
                    "addressLocality": "Němčičky",
                    "postalCode": "664 66",
                    "addressRegion": "Jihomoravský kraj",
                    "addressCountry": "CZ",
                },
                "geo": {"@type": "GeoCoordinates", "latitude": 49.04952, "longitude": 16.50048},
                "areaServed": {"@type": "Country", "name": "Česká republika"},
                "sameAs": ["https://www.facebook.com/stolarstvikubis"],
            },
            B.faq_ld(hf),
        ],
    }
    B.page(
        '/',
        'Postele a nábytek z masivu na míru od výrobce',
        'Rodinné stolařství z Němčiček u Brna. Postele pro seniory, s nosností až 500 kg a s ohrádkou, komody, stoly a matrace. Z buku a dubu na míru, doprava a montáž po celé ČR.',
        body,
        jsonld=ld,
        suffix=False,
        canonical=B.SITE + '/',
    )


# ---------------------------------------------------------------- rozcestníky
def hub_row(slug, title, sentence, photo, models, n_label, rev=False):
    if slug == 'postele-pro-handicapovane':
        frm = min_price(ohradka_slugs())
    elif slug in ('komody-a-psaci-stoly', 'jidelni-stoly', 'bytove-doplnky', 'doplnky-k-postelim'):
        frm = min_price(cat_slugs(slug))
    else:
        frm = min_price(beds(slug))
    ph_path, ph_alt, pos = photo
    price = f'<p class="hub-from">od <span class="price">{kc(frm)}</span></p>' if frm else ''
    href = f'/{slug}/'
    return f'''<article class="hub-row{" rev" if rev else ""}">
  <div class="hr-fr">{frame(ph(pic(ph_path, ph_alt, size='s', pos=pos), 'r32'), E(title) + (f' · od {kc(frm)}' if frm else ''))}</div>
  <div class="hub-tx"><h3 class="t3"><a href="{href}">{E(title)}</a></h3><p>{sentence}</p>{price}{link_list(models)}
    <div class="ctas"><a class="btn btn-2" href="{href}">{E(n_label)}</a></div></div>
</article>'''


def n_label(slug, extra=None):
    n = len(extra if extra is not None else beds(slug))
    return f'Zobrazit {n} modelů' if n >= 5 else 'Zobrazit modely'


def hub_head(h1, lead, crumb):
    return f'''<section class="room wall-paper hub-head"><div class="wrap">{crumb}
  <div class="hub-head-grid"><h1>{E(h1)}</h1><p class="lead">{lead}</p></div></div></section>'''


def hub_room(key, heading, rows, wall=None, extra=''):
    r = ROOM[key]
    return f'''<section class="room wall-{wall or r[3]} hub-room" {extra}><div class="wrap" data-fx="reveal">{plate(r[1])}<h2>{E(heading)}</h2><div class="hub-rows">{rows}</div></div></section>'''


def build_hub_postele():
    nj, nd = len(beds('jednoluzka')), len(beds('dvouluzka'))

    def row(slug, title, sent, photo, models, rev, extra=None):
        return hub_row(slug, title, sent, photo, models, n_label(slug, extra), rev)

    P = lambda path, alt, pos=None: (path, alt, pos)
    potreba = ''.join(
        [
            row(
                'postele-pro-seniory',
                'Pro seniory',
                'Ložná plocha 55, 60 nebo 65 cm k povrchu matrace, nosnost 400 kg na lůžko.',
                P(
                    'web/media/200007894-df33cdf33f.jpg',
                    'Bílá zvýšená senior postel Luneta s polštáři a matrací s potahem Aloe Vera',
                ),
                [
                    ('senior-postel-luneta', 'Luneta'),
                    ('senior-postel-buk-antik', 'Antik'),
                    ('senior-postel-pavla-buk-8150-kc-poptat-objednat', 'Pavla'),
                ],
                False,
            ),
            row(
                'vysokozatezove-postele',
                'Vysokozátěžové a prodloužené',
                'Nosnost 400 kg na lůžko bez příplatku, vybrané modely z buku a dubu 500 kg, délky 210 a 220 cm.',
                P(
                    'web/media/200007689-152ca152cb.jpg',
                    'Rustikální dvoulůžko z jádrového buku s masivními nohami a viditelnou kresbou dřeva',
                ),
                [
                    ('prodlouzena-petra-d-210cm', 'Prodloužená Petra 210 cm'),
                    ('bukova-postel-v-65cm-viktorie', 'Viktorie 65 cm'),
                    ('robustni-zvysene-dvouluzko-luxi', 'Zvýšené dvoulůžko Luxi'),
                ],
                True,
            ),
            row(
                'postele-pro-handicapovane',
                'S ohrádkou, pro handicapované',
                'Vysoká ohrádka na míru, posuvná dvířka za příplatek 1 800 Kč, polohovací a motorové rošty.',
                P(
                    'web/media/200007201-9391793919.jpg',
                    'Postel s vysokou dřevěnou ohrádkou a posuvnými dvířky v ložnici s plyšovými hračkami',
                ),
                [
                    ('jednoluzko-s-ohradkou-eva', 'Jednolůžko EVA s ohrádkou'),
                    ('jednoluzko-eva-bila-s-ohradkou', 'Jednolůžko EVA bílá'),
                ],
                False,
                extra=ohradka_slugs(),
            ),
            row(
                'postele-na-miru',
                'Na míru, čalouněné a atypické',
                'Podle nákresu, fotky nebo vašich rozměrů, výroba obvykle do 4 týdnů.',
                P(
                    'web/media/200003844-0746108402.jpg',
                    'Dvoulůžko z masivu v bílé s čalouněným šedým čelem, atypická zakázka',
                ),
                [
                    ('bile-dvouluzko-anita-kc', 'Bílé dvoulůžko Anita'),
                    ('dvouluzko-benedita', 'Dvoulůžko Benedikta'),
                    (
                        'dvou-a-pul-luzko-220x200cm-adriana-15400-kc',
                        'Dva a půl lůžko Adriana 220 × 200 cm',
                    ),
                ],
                True,
            ),
        ]
    )
    deti = ''.join(
        [
            row(
                'patrove-a-vysoke-postele',
                'Patrové a vysoké',
                'Palandy jsou náš první výrobek z roku 1999. Palanda Irena unese 400 kg na lůžko, vysoká postel Gizell má 6 zásuvek.',
                P(
                    'web/media/200008373-53f9853f9a.jpg',
                    'Patrová postel z masivu se žebříkem, úložnou zásuvkou a komodou před cihlovou zdí',
                ),
                [
                    ('patrova-palanda-irena', 'Palanda Irena'),
                    ('vysoka-postel-gizell', 'Vysoká postel Gizell'),
                    ('triluzkova-palanda-velma-buk', 'Třílůžková palanda Velma'),
                ],
                False,
            ),
            row(
                'studentske-postele',
                'Studentské a 1,5 lůžka',
                'Šířky 120 a 140 cm, s úložným prostorem nebo výsuvnou přistýlkou.',
                P(
                    'web/media/200005241-5a8e65a8ea.jpg',
                    'Bílá studentská postel Lada 120 cm s rohovým opěradlem a polštáři',
                ),
                [
                    ('jeden-a-pul-luzko-dita', 'Dita 1,5 lůžko'),
                    ('studentska-postel-magda', 'Magda'),
                    ('studentska-postel-lada-s-120cm', 'Lada 120 cm'),
                ],
                True,
            ),
        ]
    )
    typ = ''.join(
        [
            row(
                'jednoluzka',
                'Jednolůžka',
                f'{nj} modelů od klasiky po pohovkové postele, základní rozměr 90 × 200 cm.',
                P(
                    'web/media/200005144-dd269dd26c.jpg',
                    'Jednolůžko Lucie se zaoblenými rohy ze smrku s ovčí kožešinou',
                ),
                [
                    ('jednoluzko-dita', 'Dita'),
                    ('jednoluzko-lucie-zaoblene-rohy', 'Lucie'),
                    ('jednoluzko-pavla', 'Pavla'),
                ],
                False,
            ),
            row(
                'dvouluzka',
                'Dvoulůžka',
                f'{nd} modelů ze smrku, buku, jádrového buku, jasanu a dubu, nosnost nad 400 kg.',
                P(
                    'web/media/200006413-181a7181aa.jpg',
                    'Dvoulůžko z masivního buku s latěmi v čele, pohled z rohu v ložnici',
                ),
                [
                    ('dvouluzko-marta-bo', 'Marta BO'),
                    ('dvouluzko-magda-2', 'Magda'),
                    ('dvouluzko-martina', 'Martina'),
                ],
                True,
            ),
            row(
                'dubove-postele',
                'Dubové postele',
                'Masiv o tloušťce 42 mm, povrch olejem, nosnost dvoulůžek nad 400 kg.',
                P(
                    'web/img/dub-dvouluzko.jpg',
                    'Dubové dvoulůžko z masivu s lištovým čelem v interiéru s cihlovou zdí',
                ),
                [
                    ('jednoluzko-dita-dub', 'Jednolůžko Dita'),
                    ('jednoluzko-sona-dub', 'Jednolůžko Soňa'),
                    ('dvouluzko-magda-dub', 'Dvoulůžko Magda'),
                ],
                False,
            ),
            row(
                'doplnky-k-postelim',
                'Doplňky k postelím',
                'Úložné šuplíky na kolečkách, výsuvné přistýlky, noční stolky, zábrany a madla.',
                P(
                    'web/img/pristylka.jpg',
                    'Postel s výsuvnou přistýlkou z masivu, druhé lůžko vysunuté pod postelí',
                ),
                [
                    ('senior-podpera-bocni-madlo', 'Senior madlo'),
                    ('ulozny-prostor-polovicni', 'Úložný prostor poloviční'),
                    ('vysuvna-pristylka-pod-postel', 'Přistýlka pod postel'),
                ],
                True,
                extra=cat_slugs('doplnky-k-postelim'),
            ),
        ]
    )
    faq = [
        (
            'Jaká je nejlevnější postel z masivu u vás?',
            f'Jednolůžka ze smrku nebo borovice začínají zhruba na {kc(min_price(beds("jednoluzka")))} bez roštu a matrace. Buk a dub jsou dražší, ale trvanlivější.',
        ),
        (
            'Je u postele rošt a matrace?',
            'Ceny v katalogu jsou bez roštu a matrace. Pevný masivní rošt (od 1 260 Kč) i matraci můžete přiobjednat.',
        ),
        (
            'Můžu postel vidět a vyzkoušet?',
            'Ano, na prodejně v Němčičkách u Židlochovic, po telefonické domluvě.',
        ),
    ]
    wood = f'''<section class="room wall-stone hub-room h-wood" aria-label="Dílna"><div class="wrap h-split" data-fx="reveal"><div class="rtx">{plate(ROOM['dilna'][1])}<h2>Buk, jádrový buk nebo dub?</h2>
<p>Smrk a borovice jsou cenově nejdostupnější. Buk je tvrdý a světlý, jádrový buk má výraznou tmavou kresbu, kterou nikdo nezopakuje. Dub je nejtvrdší a nejodolnější. Pro vysokou nosnost doporučujeme buk, jasan nebo dub.</p>
<p><a class="link arrow" href="/dreviny-a-povrchy/">Srovnání dřevin a povrchů</a></p></div>
<div class="rfr">{frame(ph(pic('web/img/detail-buk.jpg', 'Detail nohy postele z jádrového buku s kresbou dřeva', size='s'), 'r32'), 'Detail bukové nohy s kresbou dřeva')}</div></div></section>'''
    body = f'''{hub_head('Postele z masivu na míru', 'Rodinná výroba z buku, jádrového buku, dubu a dalších dřevin. Vyberte podle potřeby, nebo podle typu. Vše vyrobíme i v jiném rozměru.', B.crumbs(('Postele z masivu', None)))}
{hub_room('lozince', 'Podle potřeby', potreba)}
{hub_room('detsky', 'Patrové a studentské postele', deti)}
{hub_room('lozince', 'Podle typu', typ, wall='paper', extra='id="podle-typu"')}
{wood}
{B.faq_html(faq)}
{B.cta_band()}'''
    B.page(
        '/postele-z-masivu/',
        'Postele z masivu na míru: katalog',
        'Katalog postelí z masivu: pro seniory, vysokozátěžové, s ohrádkou, na míru, patrové, jednolůžka a dvoulůžka. Výrobce z Němčiček u Brna.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [B.crumbs_ld([('Postele z masivu', '/postele-z-masivu/')]), B.faq_ld(faq)],
        },
    )


def build_hub_nabytek():
    def row(slug, title, sent, photo, models, rev):
        made = [s for s in cat_slugs(slug) if 'skříň' not in B.prod_title(B.PRODUCTS[s]).lower()]
        return hub_row(slug, title, sent, photo, models, n_label(slug, made), rev)

    P = lambda path, alt, pos=None: (path, alt, pos)
    jid = row(
        'jidelni-stoly',
        'Jídelní a konferenční stoly',
        'Deska olejovaná Adler Legno vhodným i na potraviny, rozměr přizpůsobíme.',
        P(
            'web/media/200005136-3b0be3b0c2.jpg',
            'Dubový jídelní stůl Denisa s deskou z lepených prken a černými ocelovými nohami',
        ),
        [
            ('konferencni-stolek-mark-2450-kc', 'Konferenční stolek Mark'),
            ('borovicovy-jidelni-stul-oskar-3500-kc', 'Jídelní stůl Oskar'),
            ('dubovy-jidelni-stul-denisa-7200-kc', 'Dubový stůl Denisa'),
        ],
        False,
    )
    obv = ''.join(
        [
            row(
                'komody-a-psaci-stoly',
                'Komody a psací stoly',
                'Zásuvky na plnovýsuvech s tlumením, nosnost zásuvky 40 kg, materiál smrk, borovice nebo buk.',
                P(
                    'web/media/200000314-9172f91bc1.jpg',
                    'Smrková zásuvková komoda s osmi zásuvkami a dřevěnými knoflíky',
                ),
                [
                    ('komoda-na-luzkoviny-perinac', 'Komoda na lůžkoviny'),
                    ('zasuvkova-komoda-kpc', 'Komoda KPC'),
                    ('psaci-stul-robin-9670-kc', 'Psací stůl Robin'),
                ],
                True,
            ),
            row(
                'bytove-doplnky',
                'Bytové doplňky',
                'Odkládací a květinové stolky a věšáková stěna ze smrku nebo borovice.',
                P(
                    'web/media/200001277-e19cfe296c.jpg',
                    'Rohový stolek z masivu s policí v obývacím koutě',
                ),
                [
                    ('odkladaci-stolek-na-koleckach', 'Odkládací stolek na kolečkách'),
                    ('rohovy-stolek', 'Rohový stolek'),
                    ('vesakova-stena-1280-kc', 'Věšáková stěna'),
                ],
                False,
            ),
        ]
    )
    loz = row(
        'doplnky-k-postelim',
        'Doplňky k postelím',
        'Noční stolky, úložné šuplíky na kolečkách, výsuvné přistýlky, zábrany a madla.',
        P(
            'web/img/pristylka.jpg',
            'Postel s výsuvnou přistýlkou z masivu, druhé lůžko vysunuté pod postelí',
        ),
        [
            ('nocni-stolek-ida', 'Noční stolek Ida'),
            ('ulozny-prostor-polovicni', 'Úložný prostor poloviční'),
            ('vysuvna-pristylka-pod-postel', 'Přistýlka pod postel'),
        ],
        True,
    )
    body = f'''{hub_head('Nábytek z masivu na zakázku', 'Komody, psací a jídelní stoly, odkládací stolky. Vyrábíme podle vašich rozměrů z buku, dubu nebo smrku. Šatní skříně momentálně z kapacitních důvodů nevyrábíme.', B.crumbs(('Nábytek z masivu', None)))}
{hub_room('jidelna', 'Stoly do jídelny', jid)}
{hub_room('obyvak', 'Komody a stolky do obýváku a pracovny', obv)}
{hub_room('lozince', 'K postelím', loz)}
{B.cta_band(title='Potřebujete nábytek na míru?', text='Pošlete rozměry nebo fotku, připravíme nabídku.')}'''
    B.page(
        '/nabytek-z-masivu/',
        'Nábytek z masivu na zakázku',
        'Komody, psací a jídelní stoly a drobný nábytek z masivu na zakázku. Vyrábíme v Němčičkách u Židlochovic.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [B.crumbs_ld([('Nábytek z masivu', '/nabytek-z-masivu/')])],
        },
    )


B.build_home = build_home
B.build_hub_postele = build_hub_postele
B.build_hub_nabytek = build_hub_nabytek
