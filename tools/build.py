"""Generátor webu Stolařství Kubiš v2.

Vstup:  data/old-site.json (tools/scrape.py), data/media-sizes.json, web/index.html (příběhová úvodní stránka)
Výstup: web/<kategorie>/index.html, web/produkty/<model>/index.html, textové stránky, galerie,
        web/css/site.css + pages.css, web/js/site.js, sitemap.xml, robots.txt, .htaccess, 404.html
Použití: python3 -I tools/build.py
"""

import json, re, os, html, shutil, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
import os

WEB = Path(os.environ['KUBIS_WEB']) if os.environ.get('KUBIS_WEB') else ROOT / 'web'
DATA = json.load(open(ROOT / 'data/old-site.json', encoding='utf-8'))
SIZES = json.load(open(ROOT / 'data/media-sizes.json'))
_cut_file = ROOT / 'data/cutouts.json'
CUT = (
    json.load(open(_cut_file)) if _cut_file.exists() else {}
)  # fotky s odstraněným bílým pozadím (PNG)
SITE = 'https://www.stolarstvikubis.cz'
TODAY = datetime.date(2026, 11, 19).isoformat()
TEL1, TEL1H = '604 107 577', '+420604107577'
TEL2, TEL2H = '732 606 965', '+420732606965'
MAIL = 'petrkubis@stolarstvikubis.cz'
FORM_ACTION = 'https://formsubmit.co/' + MAIL

E = html.escape
PAGES = {p['url'].replace(SITE, ''): p for p in DATA['pages']}


def fmt(n):
    return f'{n:,}'.replace(',', ' ')


def mid(url):
    m = re.search(r'/(\d{9}-[0-9a-f]{10})(?:-public)?/', url or '')
    return m.group(1) if m and m.group(1) in SIZES else None


def media_src(i, size='s'):
    ext = 'png' if i in CUT else 'jpg'
    return f'/media/{i}-s.{ext}' if size == 's' else f'/media/{i}.{ext}'


def media_size(i, size='s'):
    if i in CUT:
        return CUT[i]['sizes']['-s' if size == 's' else 'l']
    return SIZES[i]['-s' if size == 's' else 'l']


def img_tag(url, alt='', cls='', size='s', lazy=True):
    i = mid(url)
    if not i:
        return ''
    w, h = media_size(i, size)
    src = media_src(i, size)
    if i in CUT:
        cls = (cls + ' cut').strip()
    elif max(media_size(i, 'l')) < 520:
        cls = (cls + ' small').strip()
    return f'<img src="{src}" width="{w}" height="{h}" alt="{E(alt)}"{" loading=\"lazy\" decoding=\"async\"" if lazy else ""}{f" class=\"{cls}\"" if cls else ""}>'


def lb_link(url, alt, group, cap=''):
    i = mid(url)
    if not i:
        return ''
    return f'<a href="{media_src(i, "l")}" data-lb="{group}" data-cap="{E(cap or alt)}">{img_tag(url, alt)}</a>'


# ---------------------------------------------------------------- skládání matrací
LAYER_KEYS = [
    (r'aloe', 'potah Aloe Vera'),
    (r'silver|stříbr', 'potah Silver'),
    (r'bambus', 'potah bambus'),
    (r'potah', 'snímatelný potah'),
    (r'geleffect|gelov|\bgel', 'gelová vrstva'),
    (r'paměťov|memory', 'paměťová pěna'),
    (r'líná pěn|línou pěn|líné pěn', 'líná pěna'),
    (r'studen\w* pěn', 'studená pěna'),
    (r'\bhr\b|hr pěn', 'HR pěna'),
    (r'pur pěn|polyuretan', 'PUR pěna'),
    (r'latex', 'latex'),
    (r'3d', '3D mřížka'),
    (r'taštičk', 'taštičkové pružiny'),
    (r'kokos', 'kokosová vrstva'),
    (r'tuhý okraj|tuhým okrajem|pevný okraj|pevným okrajem', 'tuhý okraj'),
    (r'zón', 'tvarované zóny'),
]


def mattress_layers(text):
    t = text.lower()
    found = []
    for pat, label in LAYER_KEYS:
        m = re.search(pat, t)
        if m:
            found.append((m.start(), label))
    labels = [l for _, l in sorted(found)]
    if any(l.startswith('potah ') for l in labels) and 'snímatelný potah' in labels:
        labels.remove('snímatelný potah')
    covers = [l for l in labels if l.startswith('potah ')]
    if len(covers) > 1:  # více potahů = výběr, ne více vrstev
        at = labels.index(covers[0])
        labels = [l for l in labels if not l.startswith('potah ')]
        labels.insert(at, 'potah ' + ' / '.join(c[6:] for c in covers))
    return labels[:7]


def mattress_height(text):
    for m in re.finditer(
        r'(?:výšk\w*|výška|v\.|vysoká)\s*(?:matrace\s*)?(?:je\s*)?(\d{2})\s*cm', text, re.I
    ):
        v = int(m.group(1))
        if 8 <= v <= 35:
            return v
    return None


def mattress_figure(url, alt, group, text):
    i = mid(url)
    w, h = media_size(i, 'l')
    src = media_src(i, 'l')
    layers = mattress_layers(text)
    hh = mattress_height(text)
    chips = ''.join(f'<span>{E(l)}</span>' for l in layers)
    return (
        f'<figure class="assemble"><a class="as-stage" href="{src}" data-lb="{group}" data-cap="{E(alt)}" style="max-width:{w}px"><img src="{src}" width="{w}" height="{h}" alt="{E(alt)}" loading="lazy" decoding="async"></a>'
        + (
            f'<span class="as-kota mono" aria-hidden="true"><i></i><b>{hh}</b> cm</span>'
            if hh
            else ''
        )
        + (
            f'<figcaption class="as-layers"><span class="as-lbl">Z čeho se skládá:</span>{chips}</figcaption>'
            if chips
            else ''
        )
        + '</figure>'
    )


CURRENT = {'slug': None}


URL_RE = re.compile(r'(https?://[^\s,)]+|www\.[^\s,)]+)')


def linkify(t):
    out, last = [], 0
    for m in URL_RE.finditer(t):
        out.append(E(t[last : m.start()]))
        u = m.group(0).rstrip('.')
        href = u if u.startswith('http') else 'https://' + u
        if 'stolarstvikubis.cz' in href and not href.rstrip('/').endswith('.cz'):
            out.append(E(u))
        else:
            out.append(f'<a href="{E(href)}" target="_blank" rel="noopener">{E(u)}</a>')
        last = m.end() - (len(m.group(0)) - len(u))
    out.append(E(t[last:]))
    return ''.join(out)


PRICE_RE = re.compile(r'(\d[\d ]{2,})\s*,-\s*K[čČ]', re.I)


def blocks_html(blocks, group, skip_text=(), with_images=True):
    """Texty + obrázky ze starého webu → (prose_html, [img urls])."""
    parts, imgs, ul = [], [], []

    def flush():
        if ul:
            parts.append('<ul>' + ''.join(ul) + '</ul>')
            ul.clear()

    for b in blocks:
        if b['t'] == 'img':
            imgs.append(b['src'])
            continue
        t = b['text'].strip()
        if not t or t in skip_text or re.fullmatch(r'[-—_ ]+', t):
            continue
        t = re.sub(r'^-{5,}', '', t).strip()
        if b['t'] == 'li':
            ul.append(f'<li>{linkify(t)}</li>')
            continue
        flush()
        if b['t'] == 'h':
            parts.append(f'<h3>{linkify(t)}</h3>')
        else:
            parts.append(f'<p>{linkify(t)}</p>')
    flush()
    return '\n'.join(parts), imgs


def thumbs_html(imgs, group, alt):
    seen, out = set(), []
    for u in imgs:
        i = mid(u)
        if not i or i in seen:
            continue
        seen.add(i)
        out.append(lb_link(u, alt, group))
    return ''.join(out)


# ---------------------------------------------------------------- struktura webu v2
# slug, skupina, menu, H1, úvod (lead), zdroje na starém webu
CATS = [
    (
        'jednoluzka',
        'typ',
        'Jednolůžka',
        'Jednolůžka z masivu',
        'Jednolůžka z buku, dubu i smrku od klasiky po pohovkové postele a postele s úložným prostorem. Rozměr, výšku ložné plochy i dřevinu přizpůsobíme.',
        ['/postele-z-masivu/', '/fotogalerie/jednoluzka/'],
    ),
    (
        'dvouluzka',
        'typ',
        'Dvoulůžka',
        'Dvoulůžka z masivu',
        'Manželské postele ze smrku, borovice, buku, jádrového buku, jasanu a dubu. Nosnost nad 400 kg, varianty s vestavným úložným prostorem, každý model i v jiném rozměru.',
        ['/dvouluzka/', '/fotogalerie/dvouluzka/'],
    ),
    (
        'postele-pro-seniory',
        'potreba',
        'Pro seniory',
        'Postele pro seniory, ze kterých se dobře vstává',
        'Zvýšené postele z masivu s ložnou plochou 55, 60 nebo 65 cm k povrchu matrace. Pro kloubní potíže kyčlí a kolen, bolesti zad a těžké vstávání.',
        ['/postele-pro-seniory-zvysene-a-matrace-pro-seniory/'],
    ),
    (
        'vysokozatezove-postele',
        'potreba',
        'Vysokozátěžové a prodloužené',
        'Vysokozátěžové a prodloužené postele z masivu',
        'Postele z tvrdých dřevin s nosností 400 kg na lůžko bez příplatku, vybrané modely až 500 kg. Prodloužené délky 210 a 220 cm.',
        ['/postele-pro-seniory-postele-pro-nadmerne-postele-zvysene-vysokozatezove-postele/'],
    ),
    (
        'postele-pro-handicapovane',
        'potreba',
        'S ohrádkou, pro handicapované',
        'Postele s ohrádkou pro handicapované děti i dospělé',
        'Postele s vysokou ohrádkou, posuvnými dvířky a polohovacími nebo motorovými rošty. Vyrábíme je na míru podle potřeb uživatele.',
        ['/postele-pro-handicapovane/', '/postele-pro-handicapovane/orientacni-cena/'],
    ),
    (
        'postele-na-miru',
        'potreba',
        'Na míru, čalouněné a atypické',
        'Postele na míru: atypické, nadrozměrné a čalouněné',
        'Nestandardní šířka, délka, čalouněné čelo nebo kontinentální typ. Vyrobíme podle nákresu, fotky nebo vašich rozměrů, obvykle do 4 týdnů.',
        ['/atypicke-postele/'],
    ),
    (
        'patrove-a-vysoke-postele',
        'potreba',
        'Patrové a vysoké',
        'Patrové a vysoké postele z masivu',
        'Palandy, se kterými jsme v roce 1999 začínali, a vysoké postele se zásuvkami a úložným prostorem. Robustní i pro dospělé.',
        [
            '/patrove-a-vysoke-postele-s-uloznymi-prostory/',
            '/vysoke-postele-s-velkymi-prostory/',
            '/fotogalerie/patrove-palandy/',
        ],
    ),
    (
        'studentske-postele',
        'typ',
        'Studentské a 1,5 lůžka',
        'Studentské postele a jeden a půl lůžka',
        'Postele o šířce 120 a 140 cm, s úložným prostorem nebo výsuvnou přistýlkou.',
        ['/jeden-a-pul-luzka-ceny/'],
    ),
    (
        'dubove-postele',
        'typ',
        'Dubové postele',
        'Dubové postele z masivu',
        'Robustní dvoulůžka z masivního dubu o tloušťce 42 mm. Dub je nejtvrdší dřevina z naší nabídky a roky vydrží vzhled i pevnost.',
        ['/dubovy-nabytek/'],
    ),
    (
        'doplnky-k-postelim',
        'typ',
        'Doplňky k postelím',
        'Doplňky k postelím: šuplíky, přistýlky, zábrany',
        'Úložné šuplíky na kolečkách, výsuvné přistýlky, zábrany, senior madla a noční stolky.',
        ['/nocni-stolky-ulozne-supliky/'],
    ),
    (
        'komody-a-psaci-stoly',
        'nabytek',
        'Komody a psací stoly',
        'Komody, skříňky a psací stoly z masivu',
        'Zásuvkové komody, peřináče, psací a pracovní stoly z masivu. Zásuvky na plnovýsuvech s tlumením. Šatní skříně momentálně z kapacitních důvodů nevyrábíme.',
        [
            '/komody/',
            '/fotogalerie/komody/',
            '/fotogalerie/psaci-stoly/',
            '/fotogalerie/satni-skrine/',
        ],
    ),
    (
        'jidelni-stoly',
        'nabytek',
        'Jídelní a konferenční stoly',
        'Jídelní a konferenční stoly z masivu',
        'Masivní jídelní stoly a konferenční stolky. Rozměr i povrchovou úpravu přizpůsobíme.',
        ['/jidelni-a-konferencni-stoly/'],
    ),
    (
        'bytove-doplnky',
        'nabytek',
        'Bytové doplňky',
        'Bytové doplňky a drobný nábytek z masivu',
        'Odkládací a květinové stolky, věšákové stěny a další drobný nábytek.',
        ['/bytove-doplnky/'],
    ),
    (
        'matrace',
        'spanek',
        'Matrace',
        'Matrace od českých výrobců',
        'Přes 20 typů matrací, včetně vysokozátěžových, senior a antidekubitních. Libovolný rozměr. Vyzkoušet je můžete na prodejně v Němčičkách.',
        ['/matrace/'],
    ),
    (
        'rosty-a-toppery',
        'spanek',
        'Rošty a toppery',
        'Rošty, toppery a chrániče matrací',
        'Pevné masivní rošty s nosností až 500 kg, výklopné, polohovací a motorové rošty, lamelové rošty Cordo, toppery a chrániče.',
        ['/rosty-pevne-masivni/', '/rosty/', '/toppery-chranice-matraci-kliny-polstarky/'],
    ),
    (
        'dreviny-a-povrchy',
        'info',
        'Dřeviny a povrchy',
        'Dřeviny a povrchové úpravy: čím se naše postele liší',
        'Smrk, borovice, modřín, olše, buk, jasan a dub. Tvrdost, zbarvení, moření a oleje.',
        ['/ukazka-drevin/', '/dekory-moreni-na-drevinach/'],
    ),
]
CAT_BY_SLUG = {c[0]: c for c in CATS}
OLD2CAT = {src: c[0] for c in CATS for src in c[5]}
GROUPS = {
    'potreba': 'Postele podle potřeby',
    'typ': 'Postele podle typu',
    'nabytek': 'Nábytek z masivu',
    'spanek': 'Matrace a rošty',
    'info': 'Informace',
}

TEXT_PAGES = [
    ('o-nas', 'O nás', 'Rodinné stolařství v Němčičkách', '/o-nas/'),
    (
        'prodejna-nemcicky',
        'Prodejna v Němčičkách',
        'Ukázková prodejna v Němčičkách u Židlochovic',
        '/prodejna-nabytku-a-bytovych-doplnku/',
    ),
    ('doprava-a-montaz', 'Doprava a montáž', 'Doprava a montáž po celé ČR i SR', '/doprava/'),
    (
        'obchodni-podminky',
        'Obchodní podmínky',
        'Obchodní podmínky a jak u nás objednávat',
        '/obchodni-podminky-jak-poptavat-a-objednavat/',
    ),
    ('kontakt', 'Kontakt', 'Kontakt', '/kontakt/'),
]

# fotky pro dlaždice a hlavičky (web/img, vysoká kvalita)
COVERS = {
    'jednoluzka': ('jednoluzko', 1400, 933),
    'dvouluzka': ('buk-dvouluzko', 1400, 1089),
    'postele-pro-seniory': ('senior-luneta', 1049, 1400),
    'vysokozatezove-postele': ('martina', 1400, 1082),
    'postele-pro-handicapovane': ('ohradka-1', 1400, 1050),
    'postele-na-miru': ('lanett-2', 1400, 1072),
    'patrove-a-vysoke-postele': ('palanda-ulozna', 1200, 799),
    'studentske-postele': ('pavla-dub', 1400, 933),
    'dubove-postele': ('dub-dvouluzko', 1200, 800),
    'doplnky-k-postelim': ('pristylka', 1200, 800),
    'komody-a-psaci-stoly': ('komoda-smrk', 1200, 900),
    'jidelni-stoly': ('stul-denisa', 1200, 900),
    'bytove-doplnky': ('odkladaci-stolek', 1200, 900),
    'matrace': ('prodejna-1', 1400, 1050),
    'rosty-a-toppery': ('smrk-rost', 1400, 933),
    'dreviny-a-povrchy': ('detail-buk', 1400, 1050),
}

# SEO a obsah kategorií: title, description, fakta, rady k výběru, časté dotazy.
# Jen fakta ze starého webu a od majitelů; čísla sedí s ceníkem.
COPY = {
    'postele-pro-seniory': dict(
        title='Zvýšené postele pro seniory z masivu',
        desc='Zvýšené postele z buku a dubu pro seniory. Ložná plocha 55, 60 nebo 65 cm, senior matrace s tuhým okrajem, záruka 5 let, doprava a montáž po celé ČR.',
        facts=[
            ('55 / 60 / 65 cm', 'výška ložné plochy k povrchu matrace'),
            ('400 kg', 'nosnost na lůžko bez příplatku'),
            ('5 let', 'záruka na typizované postele'),
        ],
        guide=[
            (
                'Jakou výšku zvolit',
                'Klasická postel má ložnou plochu ve výšce 55 cm, seniorská 60 cm. Pro vyšší postavy ji zvedneme na 65 cm. Cílem je, aby se dalo sednout a vstát bez zbytečné námahy.',
            ),
            (
                'Matrace, která drží okraj',
                'Zdravotní senior matrace mají zpevněný okraj z tuhé pěny, takže se na hraně nepropadnete. Střed jádra je z hybridní nebo studené pěny. Vyzkoušet je můžete na prodejně.',
            ),
            (
                'Opora a zábrana',
                'Podpěrnou zábranu nebo madlo (750 Kč) zhotovíme pevně zčepované, ne přišroubované, takže se nekývá.',
            ),
        ],
        faq=[
            (
                'Jak vysoká má být postel pro seniora?',
                'Nejčastěji 60 cm k povrchu matrace. Klasická výška je 55 cm a pro vyšší postavy děláme 65 cm. Výšku upravíme podle vaší postavy a zvolené matrace.',
            ),
            (
                'Pro koho je zvýšená postel vhodná?',
                'Pro uživatele s kloubními problémy kyčlí a kolen, s bolestmi zad a s těžkým vstáváním.',
            ),
            (
                'Vyrábíte i jiný rozměr než 90 × 200 cm?',
                'Ano. Jsme zakázkové stolařství, takže šířku, délku i dřevinu uděláme podle potřeby.',
            ),
        ],
    ),
    'vysokozatezove-postele': dict(
        title='Vysokozátěžové postele z masivu, až 500 kg',
        desc='Vysokozátěžové a prodloužené postele z masivního buku, jasanu a dubu. Nosnost 400 kg na lůžko, vybrané modely 500 kg, délka až 220 cm. Záruka 5 let.',
        facts=[
            ('400 kg', 'nosnost na lůžko bez příplatku'),
            ('až 500 kg', 'u vybraných modelů z buku a dubu'),
            ('40 mm', 'tloušťka masivu'),
            ('210 / 220 cm', 'prodloužené délky'),
        ],
        guide=[
            (
                'Proč naše postele unesou víc',
                'Stavíme z tvrdých dřevin (buk, jasan, dub) a z masivu o tloušťce 40 mm. K tomu patří pevný masivní rošt s nosností 500 kg.',
            ),
            (
                'Prodloužené a nadrozměrné',
                'Pro vysoké postavy vyrábíme délky 210 a 220 cm i víc, šířky podle potřeby. Rozměr nás nijak neomezuje.',
            ),
            (
                'Matrace pro těžší osoby',
                'Vysokozátěžové matrace Fortis (do 180 kg) a Berta (do 150 kg) máte k vyzkoušení na prodejně.',
            ),
        ],
        faq=[
            (
                'Jakou nosnost mají vaše postele?',
                'Vysokozátěžové postele unesou 400 kg na lůžko bez příplatku, vybrané modely z tvrdého buku a dubu až 500 kg. Přesnou nosnost najdete u každého modelu.',
            ),
            (
                'Z čeho jsou postele s vyšší nosností?',
                'Z tvrdých dřevin, tedy buku, jasanu a dubu, o tloušťce materiálu 40 mm, s pevným masivním roštem.',
            ),
            ('Dáte záruku?', 'Na typizované postele dáváme 5 let.'),
        ],
    ),
    'postele-pro-handicapovane': dict(
        title='Postele s ohrádkou pro handicapované',
        desc='Postele s vysokou ohrádkou z buku pro děti i dospělé s postižením. Posuvná dvířka, polohovací a motorové rošty, rozměry a výška na míru. Vyrábíme v Němčičkách.',
        facts=[
            ('ohrádka na míru', 'výška podle potřeby uživatele'),
            ('buk', 'masiv, bezpečné povrchové úpravy'),
            ('polohování', 'ruční i motorové rošty'),
            ('1 800 Kč', 'příplatek za posuvná dvířka'),
        ],
        guide=[
            (
                'Ohrádka podle uživatele',
                'Výšku, rozteč příček i provedení dvířek přizpůsobíme tomu, kdo bude v posteli spát. Postele s ohrádkou vyrábíme pro děti i pro dospělé.',
            ),
            (
                'Polohování a ovládání',
                'K ohrádce nabízíme polohovatelné rošty Terus a motorový Terus M s elektrickým ovládáním.',
            ),
            (
                'Matrace pro ležící',
                'Pro osoby upoutané na lůžko je k dispozici antidekubitní matrace Giana.',
            ),
        ],
        faq=[
            (
                'Vyrábíte postele s ohrádkou pro dospělé?',
                'Ano, na míru pro dospělé i pro děti s postižením, včetně polohovacích roštů s elektrickým ovládáním.',
            ),
            (
                'Lze ohrádku zvýšit?',
                'Ano. Celková výška postele s ohrádkou je podle požadavku například 140 nebo 160 cm.',
            ),
            (
                'Jak se objednává?',
                'Zavolejte nebo pošlete poptávku. Domluvíme rozměry a provedení a pošleme písemnou nabídku s cenou.',
            ),
        ],
    ),
    'postele-na-miru': dict(
        title='Postele na míru: atypické a čalouněné',
        desc='Atypické, nadrozměrné a čalouněné postele na míru. Podle nákresu, fotky nebo rozměrů, výroba obvykle do 4 týdnů, doprava a montáž po celé ČR.',
        facts=[
            ('do 4 týdnů', 'obvyklá doba výroby'),
            ('podle nákresu', 'nebo podle fotky od zákazníka'),
            ('7 dřevin', 'smrk až dub, moření i barvy'),
        ],
        guide=[
            (
                'Co všechno uděláme jinak',
                'Šířku, délku, výšku čela a ložné plochy, čalouněné čelo, kontinentální typ nebo provensálský styl. Pokud postel nejde koupit, uděláme ji.',
            ),
            (
                'Jak to probíhá',
                'Pošlete rozměry, nákres nebo fotku. Připravíme písemnou nabídku s materiálem, cenou a termínem.',
            ),
        ],
        faq=[
            ('Jak dlouho trvá výroba na míru?', 'Obvykle do 4 týdnů od potvrzení objednávky.'),
            (
                'Vyrobíte postel podle fotky?',
                'Ano, vyrábíme i podle nákresu nebo fotky od zákazníka.',
            ),
        ],
    ),
    'patrove-a-vysoke-postele': dict(
        title='Patrové a vysoké postele z masivu',
        desc='Patrové postele (palandy) a vysoké postele se zásuvkami z masivního buku. Robustní provedení i pro dospělé, nosnost 400 kg. Záruka 5 let.',
        facts=[
            ('od 1999', 'palandy jsou naše první výrobek'),
            ('400 kg', 'palanda Irena i pro dospělé'),
            ('6 zásuvek', 'vysoká postel Gizell'),
        ],
        guide=[
            (
                'Palanda, kde se nehoupe nic',
                'Začínali jsme patrovými postelemi a vestavnými patry. Dodnes je děláme z masivu a pevně zčepované.',
            ),
            (
                'Vysoká postel s úložným prostorem',
                'Pod ložnou plochou je místo na zásuvky nebo skříňku. Hodí se do dětského i studentského pokoje.',
            ),
        ],
        faq=[
            (
                'Vyrábíte patrovou postel pro dospělé?',
                'Ano. Palanda Irena je dimenzovaná i pro dospělé, nosnost 400 kg.',
            ),
            ('Jde vyrobit třílůžkovou palandu?', 'Ano, třílůžkovou palandu Velma děláme z buku.'),
        ],
    ),
    'jednoluzka': dict(
        title='Jednolůžka z masivu',
        desc='Jednolůžka z masivu od 6 880 Kč: buk, dub, smrk i jádrový buk. Rozměr, výšku i moření uděláme podle vás. Doprava a montáž po celé ČR.',
        facts=[
            ('25 modelů', 'od klasiky po pohovkové postele'),
            ('90 × 200 cm', 'základní rozměr, jiný na přání'),
        ],
        guide=[
            (
                'Jak vybrat jednolůžko',
                'Rozhoduje dřevina (smrk je nejlevnější, buk a dub nejtrvanlivější), výška ložné plochy a to, zda chcete úložný prostor. Poradíme telefonicky nebo na prodejně.',
            )
        ],
        faq=[
            (
                'Dá se jednolůžko vyrobit v jiném rozměru?',
                'Ano, každý model vyrábíme i v jiném rozměru.',
            ),
            (
                'Je v ceně rošt a matrace?',
                'Ne. Ceny jsou bez roštu a matrace, které můžete přiobjednat.',
            ),
        ],
    ),
    'dvouluzka': dict(
        title='Dvoulůžka z masivu',
        desc='Dvoulůžka z masivního buku, jádrového buku, jasanu a dubu od 15 100 Kč. Nosnost nad 400 kg, vestavný úložný prostor, záruka 5 let.',
        facts=[('24 modelů', 'smrk až dub'), ('400+ kg', 'nosnost'), ('5 let', 'záruka')],
        guide=[
            (
                'Jádrový buk',
                'Jádrový buk má tmavé jádro a výrazný kontrast s okolním dřevem, každý kus je jiný. Takové jsou naše Martina nebo Lanett.',
            )
        ],
        faq=[
            (
                'Jak dlouho se na dvoulůžko čeká?',
                'Postel na míru vyrobíme zhruba do 4 týdnů, některé postele máme skladem na prodejně.',
            ),
            ('Mají postele úložný prostor?', 'Ano, u vybraných modelů je vestavný úložný prostor.'),
        ],
    ),
    'studentske-postele': dict(
        title='Studentské postele a 1,5 lůžka',
        desc='Postele o šířce 120 a 140 cm z masivu, s úložným prostorem nebo výsuvnou přistýlkou. Od 9 440 Kč, doprava a montáž po celé ČR.',
        facts=[('120 / 140 cm', 'šířky')],
        guide=[],
        faq=[],
    ),
    'dubove-postele': dict(
        title='Dubové postele z masivu',
        desc='Dubová dvoulůžka z masivního dubu o tloušťce 42 mm. Olejovaný povrch, nosnost nad 400 kg, záruka 5 let.',
        facts=[('42 mm', 'tloušťka masivu'), ('dub', 'nejtvrdší dřevina v nabídce')],
        guide=[],
        faq=[],
    ),
    'doplnky-k-postelim': dict(
        title='Doplňky k postelím',
        desc='Úložné šuplíky na kolečkách, výsuvné přistýlky, zábrany a noční stolky z masivu.',
        facts=[],
        guide=[],
        faq=[],
    ),
    'komody-a-psaci-stoly': dict(
        title='Komody a psací stoly z masivu',
        desc='Zásuvkové komody, peřináče a psací stoly z masivu na míru. Plnovýsuvy s tlumením, nosnost zásuvky 40 kg.',
        facts=[('40 kg', 'nosnost zásuvky'), ('plnovýsuv', 's tlumením')],
        guide=[],
        faq=[],
    ),
    'jidelni-stoly': dict(
        title='Jídelní a konferenční stoly z masivu',
        desc='Dubové, bukové a borovicové jídelní stoly a konferenční stolky. Povrch olejem Adler Legno, vhodný i pro potraviny.',
        facts=[],
        guide=[],
        faq=[],
    ),
    'bytove-doplnky': dict(
        title='Bytové doplňky z masivu',
        desc='Odkládací a květinové stolky, věšákové stěny a drobný nábytek z masivu.',
        facts=[],
        guide=[],
        faq=[],
    ),
    'matrace': dict(
        title='Matrace od českých výrobců, k vyzkoušení',
        desc='Přes 20 typů matrací od 3 340 Kč: PUR, studená pěna, latex, taštičkové, gelové, senior a antidekubitní. Libovolný rozměr, k vyzkoušení na prodejně v Němčičkách.',
        facts=[
            ('20+ typů', 'matrací od českých výrobců'),
            ('libovolný rozměr', 'na míru'),
            ('na prodejně', 'k vyzkoušení'),
        ],
        guide=[
            (
                'Matrace podle potřeby',
                'Pro každou potřebu máme jinou matraci: senior s tuhým okrajem, vysokozátěžové, antidekubitní pro ležící, antibakteriální pro alergiky, taštičkové na chalupu. Detail najdete níže u každé.',
            )
        ],
        faq=[
            (
                'Můžu si matraci vyzkoušet?',
                'Ano, na prodejně v Němčičkách. Návštěvu domluvte předem telefonicky.',
            ),
            ('Vyrobíte matraci na míru?', 'Ano, libovolné rozměry.'),
        ],
    ),
    'rosty-a-toppery': dict(
        title='Rošty, toppery a chrániče matrací',
        desc='Pevné masivní rošty do 500 kg, polohovací a motorové rošty, lamelové rošty Cordo, toppery a vodonepropustné chrániče.',
        facts=[('500 kg', 'nosnost pevného roštu')],
        guide=[],
        faq=[],
    ),
    'dreviny-a-povrchy': dict(
        title='Dřeviny a povrchy: buk, dub, jasan',
        desc='Smrk, borovice, modřín, olše, buk, jasan a dub. Moření, barvy a oleje na našich postelích. Vodou ředitelné laky.',
        facts=[('7 dřevin', 'smrk až dub'), ('15+ dekorů', 'moření')],
        guide=[],
        faq=[],
    ),
}

TEL1, TEL1H = '604 107 577', '+420604107577'


FAQ_GROUPS = [
    (
        'Objednávka a platba',
        [
            (
                'Jak probíhá objednávka?',
                'Pošlete poptávku e-mailem, telefonicky, přes formulář nebo osobně na prodejně v Němčičkách. Písemně vám pošleme nabídku s popisem, materiálem, rozměry, cenou a termínem. Když souhlasíte, vystavíme potvrzení objednávky se zálohou a od toho dne běží termín výroby.',
            ),
            (
                'Co je potvrzení objednávky?',
                'Zálohový list s pořadovým číslem, kde je popis zakázky, cena, způsob platby, splatnost zálohy a termín zhotovení. Když ho od nás nedostanete, objednávku nemáme zaevidovanou.',
            ),
            (
                'Jak se platí?',
                'Hotově při předání, nebo převodem na účet tak, aby byla platba připsaná před dovozem, zpravidla nejméně 3 dny předem. Lze platit i po částech, ale celá částka musí být zaplacená před dodáním. Kartou bohužel platit nejde.',
            ),
            (
                'Můžu od objednávky odstoupit?',
                'U standardních neatypických postelí kdykoli, i při předání, bez udání důvodu a bez pokut. Zaplatíte jen dopravu, pokud už proběhla. U atypických postelí a jiného nábytku je odstoupení možné po dohodě.',
            ),
            (
                'Může se termín výroby posunout?',
                'Může, z technických nebo osobních důvodů. V takovém případě vás předem kontaktujeme a můžete od zakázky odstoupit.',
            ),
            (
                'Vyrobíte nábytek podle mého nákresu nebo fotky?',
                'Ano. Jsme zakázkové stolařství, takže vyrábíme podle rozměrů, typů i dodaných nákresů nebo fotek.',
            ),
        ],
    ),
    (
        'Doprava a montáž',
        [
            (
                'Kolik stojí doprava?',
                'Vozíme vlastním autem za 14 Kč/km tam i zpět, nejméně 300 Kč. Na delší vzdálenosti dáváme slevu.',
            ),
            ('Je montáž v ceně?', 'Při dovozu naším autem je odborná montáž zdarma.'),
            (
                'Vozíte i na Slovensko?',
                'Ano, po celé České republice i na Slovensko. Přepravní služby nepoužíváme.',
            ),
            (
                'Pomůžete s výnosem do patra?',
                'Ano, za příplatek podle obtížnosti. Musí se uvést předem při objednávce, protože montážní technik jezdí sám a na těžší kus bere druhého pomocníka. Příplatek platí i při výnosu z auta do domu, když ho nemůžete zajistit sami.',
            ),
            ('Můžu si postel vyzvednout osobně?', 'Ano, v Němčičkách č. 5 po předchozí domluvě.'),
        ],
    ),
    (
        'Postele',
        [
            (
                'Jak vysoká má být postel pro seniora?',
                'Nabízíme 55 cm (klasická), 60 cm (senior) a 65 cm (pro vyšší postavy), vždy k povrchu matrace. Výšku můžete vyzkoušet na prodejně a upravíme ji.',
            ),
            (
                'Kolik postel unese?',
                'Vysokozátěžové postele unesou 400 kg na lůžko bez příplatku, vybrané modely z tvrdého buku a dubu 500 kg. Přesná nosnost je u každého modelu.',
            ),
            (
                'Jak dlouho budu na postel čekat?',
                'Postel na míru vyrobíme zhruba do 4 týdnů. Některé postele máme skladem na prodejně, ty jsou k odběru hned.',
            ),
            (
                'Jakou dáváte záruku?',
                'Na typizované postele z ceníku 5 let. U atypických a luxusních postelí, postelí s vysokou ohrádkou a skříňového nábytku zpravidla 2 roky. Doba je vždy uvedená u výrobku.',
            ),
            (
                'Z jakých dřevin postele vyrábíte?',
                'Ze smrku, borovice, modřínu, olše, buku, jádrového buku, jasanu a dubu. Na vyšší zátěž doporučujeme buk, jasan nebo dub.',
            ),
            (
                'Kolik stojí moření nebo barva?',
                'Moření je u jednolůžka +700 Kč, u dvoulůžka +1 200 Kč. Bílá barva +1 700 Kč a +3 000 Kč, krycí hluboká zelená +1 500 Kč a +3 000 Kč.',
            ),
            (
                'Je v ceně postele rošt a matrace?',
                'Ne. Ceny jsou bez roštu a matrace. Pevný masivní rošt stojí od 1 260 Kč, matrace od 3 340 Kč.',
            ),
            (
                'Vyrábíte postele s ohrádkou pro dospělé?',
                'Ano, na míru pro dospělé i pro děti s postižením, včetně polohovacích roštů s elektrickým ovládáním. Posuvná dvířka jsou za příplatek 1 800 Kč.',
            ),
            ('Dělají se postele delší než 200 cm?', 'Ano, délky 210 a 220 cm i víc.'),
            (
                'Co používáte na povrch?',
                'Vodou ředitelné laky a mořidla, dub ošetřujeme olejem. Vnitřní část pod roštem necháváme bez laku.',
            ),
            (
                'Vyrábíte i šatní skříně?',
                'Teď ne, z kapacitních důvodů je nevyrábíme. Komody, psací a jídelní stoly a drobný nábytek ano.',
            ),
        ],
    ),
    (
        'Nábytek',
        [
            (
                'Vyrábíte i jiný nábytek než postele?',
                'Ano. Jsme zakázkové stolařství, takže z masivu vyrobíme komody, noční stolky, psací a jídelní stoly, konferenční stolky, palandy i drobný nábytek. Klidně podle vašeho nákresu nebo fotky. Šatní skříně teď z kapacitních důvodů nevyrábíme.',
            ),
            ('Jak jsou řešené zásuvky u komod?', 'Na plnovýsuvech s tlumením, s nosností 40 kg.'),
        ],
    ),
    (
        'Matrace a rošty',
        [
            (
                'Můžu si matraci vyzkoušet?',
                'Ano, matrace od českých výrobců máte k vyzkoušení na prodejně v Němčičkách. Návštěvu prosím domluvte předem.',
            ),
            (
                'Jaká matrace se hodí pro seniora?',
                'S tuhým okrajem, který drží hranu stabilní. Máme například Arela Plus a Soft, Dia Relax, Juna a gelovou Caeli.',
            ),
            (
                'Máte matraci pro těžší osoby?',
                'Ano, vysokozátěžové matrace Fortis (do 180 kg) a Berta (do 150 kg).',
            ),
            (
                'Jaký rošt zvolit?',
                'Pevný masivní rošt unese 500 kg. K dispozici jsou také lamelové rošty Cordo, polohovatelné Terus a motorové.',
            ),
        ],
    ),
    (
        'Prodejna',
        [
            (
                'Kde prodejna je a kdy je otevřeno?',
                'Němčičky 5, 664 66 Němčičky u Židlochovic. Po–Pá 15–20 h a So–Ne 9–20 h, vždy po předchozí domluvě na telefonu 604 107 577.',
            ),
            (
                'Mají postele skladem?',
                'Některé ano, ale kvůli poptávce se mohou rozprodat, proto návštěvu raději domluvte předem.',
            ),
        ],
    ),
]
HOME_FAQ_IDX = [
    'Vyrábíte i jiný nábytek než postele?',
    'Jak vysoká má být postel pro seniora?',
    'Kolik postel unese?',
    'Vyrábíte postele s ohrádkou pro dospělé?',
    'Jak dlouho budu na postel čekat?',
    'Kolik stojí doprava?',
    'Je montáž v ceně?',
    'Jak se platí?',
    'Jakou dáváte záruku?',
    'Je v ceně postele rošt a matrace?',
    'Můžu si matraci vyzkoušet?',
]
_F = {q: a for _, items in FAQ_GROUPS for q, a in items}
HOME_FAQ = [(q, _F[q]) for q in HOME_FAQ_IDX]


def faq_extra(slug, items):
    COPY[slug]['faq'] = [(q, _F[q]) if a is None and q in _F else (q, a) for q, a in items]


faq_extra(
    'studentske-postele',
    [
        (
            'Jak široké jsou studentské postele?',
            'Máme šířky 120 a 140 cm. Další šířku vyrobíme na přání.',
        ),
        (
            'Jde doplnit úložný prostor nebo přistýlku?',
            'Ano. Vyrábíme verze s úložným prostorem i s výsuvnou přistýlkou. Přistýlka pod postel stojí od 5 110 Kč ze smrku.',
        ),
        ('Je v ceně postele rošt a matrace?', None),
    ],
)
faq_extra(
    'dubove-postele',
    [
        (
            'Jak silný je masiv u dubových postelí?',
            'Dubová dvoulůžka mají tloušťku materiálu 42 mm.',
        ),
        ('Jak je dub povrchově upravený?', 'Dub ošetřujeme olejem.'),
        (
            'Jakou nosnost mají dubové postele?',
            'Nosnost dvoulůžek je nad 400 kg. Přesná hodnota je u každého modelu.',
        ),
    ],
)
faq_extra(
    'doplnky-k-postelim',
    [
        (
            'Kolik stojí senior madlo?',
            'Podpěrná zábrana nebo boční madlo stojí 750 Kč a je pevně zčepované.',
        ),
        ('Kolik stojí úložné šuplíky na kolečkách?', 'Poloviční 2 650 Kč, velký 4 180 Kč.'),
        (
            'Kolik stojí výsuvná přistýlka?',
            'Ze smrku 5 110 Kč, z buku 5 720 Kč, z jasanu 6 160 Kč a z dubu 7 550 Kč.',
        ),
        (
            'Máte dětské zábrany?',
            'Ano. Nasazovací dětská zábrana stojí 500–800 Kč, celodélková 750–950 Kč.',
        ),
    ],
)
faq_extra(
    'komody-a-psaci-stoly',
    [
        ('Jak jsou zásuvky řešené?', 'Na plnovýsuvech s tlumením, s nosností 40 kg.'),
        ('Vyrábíte i šatní skříně?', None),
        (
            'Vyrobíte psací stůl podle rozměrů?',
            'Ano, psací stoly včetně rohových a s kontejnerem děláme na míru. Cenu pošleme v nabídce.',
        ),
    ],
)
faq_extra(
    'jidelni-stoly',
    [
        (
            'Je povrch stolu vhodný pro potraviny?',
            'Dubový stůl Denisa ošetřujeme olejem Adler Legno, který je vhodný i pro potraviny.',
        ),
        ('Vyrobíte stůl na míru?', 'Ano, rozměr i povrchovou úpravu přizpůsobíme.'),
        (
            'Jak stůl dostanu domů?',
            'Vozíme vlastním autem po ČR i SR za 14 Kč/km tam i zzpět, nejméně 300 Kč. Osobní odběr je možný v Němčičkách po domluvě.',
        ),
    ],
)
faq_extra(
    'bytove-doplnky',
    [
        ('Vyrobíte drobný nábytek podle mých rozměrů?', 'Ano, i podle nákresu nebo fotky.'),
        (
            'Jak drobný nábytek dostanu domů?',
            'Vozíme vlastním autem po ČR i SR za 14 Kč/km tam i zpět, nejméně 300 Kč. Osobní odběr je možný v Němčičkách po domluvě.',
        ),
    ],
)
faq_extra(
    'rosty-a-toppery',
    [
        ('Jakou nosnost mají pevné rošty?', 'Pevný masivní rošt unese 500 kg a stojí od 1 260 Kč.'),
        (
            'Máte polohovací a motorové rošty?',
            'Ano. Polohovatelný rošt Terus stojí 3 000 a 3 250 Kč, motorový Terus M 7 300 Kč. Lamelový Cordo 2 300 Kč, motorový 7 230 Kč.',
        ),
        (
            'Jaký je rozdíl mezi pevným a lamelovým roštem?',
            'Pevný masivní rošt má nosnost 500 kg. Lamelové rošty Cordo jsou pružné a jsou i polohovatelné.',
        ),
    ],
)
faq_extra(
    'dreviny-a-povrchy',
    [
        ('Z jakých dřevin postele vyrábíte?', None),
        ('Kolik stojí moření nebo barva?', None),
        ('Co používáte na povrch?', None),
    ],
)
COPY['matrace']['faq'] = [
    (q, _F[q])
    for q in [
        'Můžu si matraci vyzkoušet?',
        'Jaká matrace se hodí pro seniora?',
        'Máte matraci pro těžší osoby?',
    ]
] + [('Vyrobíte matraci na míru?', 'Ano, libovolné rozměry. Ceny matrací začínají na 3 340 Kč.')]


# Web jako domácnost: každá kategorie patří do místnosti.
# (klíč, název, krátký popis, barva stěny, slugy kategorií)
ROOMS = [
    (
        'lozince',
        'Ložnice',
        'Postele, matrace a rošty',
        'sage',
        [
            'postele-pro-seniory',
            'vysokozatezove-postele',
            'postele-pro-handicapovane',
            'postele-na-miru',
            'jednoluzka',
            'dvouluzka',
            'dubove-postele',
            'doplnky-k-postelim',
            'matrace',
            'rosty-a-toppery',
        ],
    ),
    (
        'detsky',
        'Dětský pokoj',
        'Patrové a studentské postele',
        'butter',
        ['patrove-a-vysoke-postele', 'studentske-postele'],
    ),
    ('jidelna', 'Jídelna', 'Jídelní a konferenční stoly', 'clay', ['jidelni-stoly']),
    (
        'obyvak',
        'Obývák a pracovna',
        'Komody, psací stoly, drobný nábytek',
        'sky',
        ['komody-a-psaci-stoly', 'bytove-doplnky'],
    ),
    ('dilna', 'Dílna', 'Kdo postele vyrábí a jak to funguje', 'stone', ['dreviny-a-povrchy']),
]
ROOM_OF = {slug: room for room in ROOMS for slug in room[4]}


def room_of(slug):
    """Místnost (klíč, název, popis, barva stěny, slugy) pro slug kategorie; výchozí je Dílna."""
    return ROOM_OF.get(slug, ROOMS[-1])


def nav_items():
    s = lambda slug, note='': f'<a href="/{slug}/">{E(CAT_BY_SLUG[slug][2])}</a>'
    potreba = (
        s('postele-pro-seniory')
        + s('vysokozatezove-postele')
        + s('postele-pro-handicapovane')
        + s('postele-na-miru')
    )
    typ = s('jednoluzka') + s('dvouluzka') + s('dubove-postele') + s('doplnky-k-postelim')
    spanek = s('matrace') + s('rosty-a-toppery')
    lozince = (
        '<h4>Postele podle potřeby</h4><h4>Podle typu a spánek</h4>'
        f'<div>{potreba}</div><div>{typ}{spanek}</div>'
        '<a href="/postele-z-masivu/" style="grid-column:1/-1"><b>Všechny postele a jak vybrat</b></a>'
    )
    detsky = s('patrove-a-vysoke-postele') + s('studentske-postele')
    jidelna = s('jidelni-stoly')
    obyvak = (
        '<a href="/nabytek-z-masivu/"><b>Nábytek z masivu</b></a>'
        + s('komody-a-psaci-stoly')
        + s('bytove-doplnky')
    )
    dilna = (
        '<a href="/o-nas/">O nás</a><a href="/prodejna-nemcicky/">Prodejna v Němčičkách</a>'
        '<a href="/doprava-a-montaz/">Doprava a montáž</a><a href="/realizace-a-recenze/">Realizace a recenze</a>'
        '<a href="/galerie/">Fotogalerie</a><a href="/poradna/">Poradna</a>'
        '<a href="/caste-dotazy/">Časté dotazy</a>'
        + s('dreviny-a-povrchy')
        + '<a href="/obchodni-podminky/">Obchodní podmínky</a><a href="/kontakt/">Kontakt</a>'
    )
    return [
        ('lozince', 'Ložnice', lozince, True),
        ('detsky', 'Dětský pokoj', detsky, False),
        ('jidelna', 'Jídelna', jidelna, False),
        ('obyvak', 'Obývák a pracovna', obyvak, False),
        ('dilna', 'Dílna', dilna, False),
    ]


def nav_html():
    items = nav_items()
    lis = ''.join(
        f'<li class="has-sub"><button type="button" aria-expanded="false" aria-controls="m-{k}">{E(t)}</button><div class="sub{" wide" if w else ""}" id="m-{k}">{s}</div></li>'
        for k, t, s, w in items
    )
    drawer = ''.join(
        f'<details name="rubrika"{" open" if k == "lozince" else ""}><summary>{E(t)}</summary><div class="drawer-links">{re.sub(r"<h4>(.*?)</h4>", r"<b>\1</b>", re.sub(r"</?div>", "", s))}</div></details>'
        for k, t, s, _ in items
    )
    return f'''<a class="skip" href="#obsah">Přeskočit na obsah</a>
<header class="top" data-fx="header"><div class="wrap">
  <a class="logo" href="/" aria-label="Stolařství Kubiš, úvodní stránka"><b>Stolařství Kubiš</b></a>
  <nav class="main" aria-label="Hlavní menu"><ul>{lis}</ul></nav>
  <a class="tel" href="tel:{TEL1H}">{TEL1}</a>
  <a class="btn" href="/poptavka/">Poptat</a>
  <button class="burger" type="button" aria-expanded="false" aria-controls="drawer">Menu</button>
</div></header>
<dialog class="drawer" id="drawer" aria-label="Hlavní menu">
  <div class="drawer-head"><a class="logo" href="/"><b>Stolařství Kubiš</b></a><button type="button" class="close">Zavřít ✕</button></div>
  <nav aria-label="Rubriky">{drawer}</nav>
  <h3 class="dh">Kontakt</h3><ul><li><a href="tel:{TEL1H}">{TEL1}</a> prodej a matrace</li><li><a href="tel:{TEL2H}">{TEL2}</a> výroba a projekty</li><li><a href="/poptavka/">Napsat poptávku</a></li></ul>
</dialog>'''


CREDIT_URL = 'https://skocdal.cz/'  # adresa webu Skočdál, např. 'https://...' (prázdné = jen text bez odkazu)


def footer_html():
    CREDIT = 'Tvorba webu: ' + (
        f'<a href="{CREDIT_URL}" target="_blank" rel="noopener">SkočDál</a>'
        if CREDIT_URL
        else 'SkočDál'
    )
    li = lambda slugs: ''.join(
        f'<li><a href="/{x}/">{E(CAT_BY_SLUG[x][2])}</a></li>' for x in slugs
    )
    return f'''<footer class="band"><div class="wrap">
  <div class="top-row">
    <div><a class="big-tel" href="tel:{TEL1H}">{TEL1}</a><p style="margin-top:8px">Prodej, matrace a návštěvy prodejny. Výroba a projekty: <a href="tel:{TEL2H}" style="color:#fff">{TEL2}</a></p></div>
    <address><span>STOLAŘSTVÍ Petr Kubiš, IČO 69752460</span><span>Němčičky 5, 664 66 Němčičky u Židlochovic</span><a href="mailto:{MAIL}">{MAIL}</a></address>
  </div>
  <div class="grid">
    <div><h4>Postele</h4><ul>{li(['postele-pro-seniory', 'vysokozatezove-postele', 'postele-pro-handicapovane', 'postele-na-miru', 'patrove-a-vysoke-postele', 'jednoluzka', 'dvouluzka'])}<li><a href="/postele-z-masivu/">Všechny postele</a></li></ul></div>
    <div><h4>Nábytek a spánek</h4><ul><li><a href="/nabytek-z-masivu/">Nábytek z masivu</a></li>{li(['komody-a-psaci-stoly', 'jidelni-stoly', 'matrace', 'rosty-a-toppery', 'dreviny-a-povrchy'])}</ul></div>
    <div><h4>Informace</h4><ul><li><a href="/o-nas/">O nás</a></li><li><a href="/prodejna-nemcicky/">Prodejna v Němčičkách</a></li><li><a href="/doprava-a-montaz/">Doprava a montáž</a></li><li><a href="/realizace-a-recenze/">Realizace a recenze</a></li><li><a href="/poradna/">Poradna</a></li><li><a href="/caste-dotazy/">Časté dotazy</a></li><li><a href="/galerie/">Fotogalerie</a></li><li><a href="/obchodni-podminky/">Obchodní podmínky</a></li><li><a href="/ochrana-osobnich-udaju/">Ochrana osobních údajů</a></li><li><a href="/kontakt/">Kontakt</a></li><li><a href="https://www.facebook.com/stolarstvikubis/" target="_blank" rel="noopener">Facebook</a></li></ul></div>
  </div>
  <div class="legal"><span>© 1999–2026 STOLAŘSTVÍ Petr Kubiš</span><span>Ceny jsou vč. DPH, pokud není uvedeno jinak. Platná je cena v písemné nabídce.</span><span><a href="/ochrana-osobnich-udaju/">Ochrana osobních údajů</a> · <span class="ftr__credit">{CREDIT}</span></span></div>
</div></footer>
<div class="mbar"><a class="btn btn-2" href="tel:{TEL1H}">Zavolat {TEL1}</a><a class="btn" href="/poptavka/">Poptat</a></div>'''


def form_html(
    model='',
    title='Poptejte u nás',
    intro='Stačí pár řádků. Ozveme se, doptáme se a pošleme nabídku. Nic vás nezavazuje.',
):
    return f'''<section class="sec forest" id="poptavka" aria-labelledby="h-form"><div class="wrap form-grid">
  <div>
    
    <h2 id="h-form">{E(title)}</h2>
    <p class="lead" style="margin-top:16px">{E(intro)}</p>
    <a class="contact-big" href="tel:{TEL1H}">{TEL1}</a>
    <p>Prodej, matrace a návštěvy prodejny. Telefon zvedá přímo rodina.</p>
    <dl class="contact-list"><dt>Výroba a projekty</dt><dd><a href="tel:{TEL2H}">{TEL2}</a></dd><dt>E-mail</dt><dd><a href="mailto:{MAIL}">{MAIL}</a></dd><dt>Adresa</dt><dd>Němčičky 5, 664 66 Němčičky u Židlochovic</dd></dl>
  </div>
  <form class="inq" data-inquiry novalidate action="{FORM_ACTION}" method="post">
    <input type="text" name="_honey" style="display:none" tabindex="-1" autocomplete="off" aria-hidden="true">
    {f'<input type="hidden" name="model" value="{E(model)}">' if model else ''}
    <div><label for="f-name">Jméno</label><input type="text" id="f-name" name="jmeno" placeholder="např. Jana Nováková" autocomplete="name"></div>
    <div><label for="f-tel">Telefon</label><input type="tel" id="f-tel" name="telefon" placeholder="Zavoláme, je to rychlejší" autocomplete="tel" required><div class="err" hidden>Doplňte prosím telefon, jinak se vám nemůžeme ozvat.</div></div>
    <div><label for="f-mail">E-mail <small>nepovinné</small></label><input type="email" id="f-mail" name="email" autocomplete="email"></div>
    <div><label for="f-place">Místo dodání <small>obec nebo PSČ</small></label><input type="text" id="f-place" name="misto" placeholder="např. Přerov"></div>
    <div class="full"><label for="f-msg">Co potřebujete</label><textarea id="f-msg" name="zprava" placeholder="Rozměr, dřevina, výška ložné plochy, pro koho postel bude…">{E("Mám zájem o: " + model + chr(10)) if model else ""}</textarea></div>
    <div class="full"><button class="btn btn-primary" type="submit">Odeslat poptávku</button>
      <p class="note">Údaje použijeme jen k vyřízení poptávky. Více v <a href="/ochrana-osobnich-udaju/">zásadách ochrany osobních údajů</a>.</p></div>
    <div class="ok-msg full" hidden role="status"><strong>Děkujeme, máme to.</strong> Ozveme se co nejdřív, obvykle telefonem. Když spěcháte, volejte <a href="tel:{TEL1H}">{TEL1}</a>.</div>
    <div class="err-msg full" hidden role="alert">Zprávu se nepodařilo odeslat. Zkuste to prosím znovu, nebo zavolejte na <a href="tel:{TEL1H}">{TEL1}</a>.</div>
  </form>
</div></section>'''


def relative_assets(doc, path):
    if path == '/404.html':
        return doc
    prefix = '../' * len(path.strip('/').split('/')) if path.strip('/') else './'
    return re.sub(r'(?P<attr>\b(?:src|href|action)=")/(?!/)', lambda m: m['attr'] + prefix, doc)


def page(
    path,
    title,
    desc,
    body,
    jsonld=None,
    canonical=None,
    og_img=None,
    noindex=False,
    head_extra='',
    suffix=True,
):
    canonical = canonical or SITE + path
    og = og_img or SITE + '/img/og.jpg'
    full_title = f'{title} | Stolařství Kubiš' if suffix else title
    ld = (
        f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>'
        if jsonld
        else ''
    )
    doc = f'''<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(full_title)}</title>
<meta name="description" content="{E(desc)}">
{'<meta name="robots" content="noindex">' if noindex else f'<link rel="canonical" href="{canonical}">'}
<meta name="theme-color" content="#F7F4EE">
<meta property="og:type" content="website"><meta property="og:locale" content="cs_CZ"><meta property="og:site_name" content="Stolařství Kubiš">
<meta property="og:title" content="{E(full_title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{og}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/fonts/Literata-400-800-latin-ext.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/fonts/Literata-400-800-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/fonts/SourceSans3-600-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/fonts.css"><link rel="stylesheet" href="/css/site.css">
{ld}
{head_extra}
</head>
<body>
{nav_html()}
<main id="obsah">
{body}
</main>
{footer_html()}
<script src="/js/site.js" defer></script>
</body>
</html>
'''
    out = WEB / path.strip('/') / 'index.html' if path.endswith('/') else WEB / path.lstrip('/')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(relative_assets(doc, path), encoding='utf-8')
    if not noindex:
        SITEMAP.append(canonical)


SITEMAP = [SITE + '/']


def crumbs(*items):
    parts = ['<a href="/">Úvod</a>']
    for label, href in items:
        parts.append('<span aria-hidden="true">/</span>')
        parts.append(
            f'<a href="{href}">{E(label)}</a>'
            if href
            else f'<span aria-current="page">{E(label)}</span>'
        )
    return '<nav class="crumbs" aria-label="Drobečková navigace">' + ''.join(parts) + '</nav>'


def crumbs_ld(items):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + h}
            for i, (n, h) in enumerate([('Úvod', '/')] + items)
        ],
    }


def faq_html(faq, heading='Časté dotazy', more=False):
    if not faq:
        return ''
    items = ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in faq)
    return f'<section class="sec stone"><div class="wrap"><h2 style="margin-bottom:var(--s5)">{E(heading)}</h2><div class="faq" data-fx="accordion">{items}</div>{'<p style="margin-top:26px"><a class="link arrow" href="/caste-dotazy/">Všechny časté dotazy</a></p>' if more else ''}</div></section>'


def faq_ld(faq):
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    }


def cta_band(
    title='Nenašli jste přesně to, co hledáte?',
    text='Jsme zakázkové stolařství. Vyrobíme podle vašich rozměrů, nákresu nebo fotky.',
    model='',
):
    q = f'?model={E(model)}' if model else ''
    return f'<section class="band cta-band"><div class="wrap"><div><h2>{E(title)}</h2><p style="margin-top:10px">{E(text)}</p></div><div class="ctas"><a class="btn" href="/poptavka/{q}">Poptat na míru</a><a class="btn btn-2" href="tel:{TEL1H}">Zavolat {TEL1}</a></div></div></section>'


def cover_img(slug, lazy=False, cls=''):
    name, w, h = COVERS[slug]
    return f'<img src="/img/{name}.jpg" width="{w}" height="{h}" alt=""{"" if lazy else " fetchpriority=high"}{" loading=lazy decoding=async" if lazy else ""}{f" class={cls}" if cls else ""}>'


# ---------------------------------------------------------------- produkty
PRODUCTS = {}  # slug -> dict
PROD_CAT = {}  # slug -> category slug (první výskyt)


TR = str.maketrans(
    'áäčďéěíľĺňóôřšťúůýžÁÄČĎÉĚÍĽĹŇÓÔŘŠŤÚŮÝŽ', 'aacdeeillnoorstuuyzAACDEEILLNOORSTUUYZ'
)


def slugify(t):
    return re.sub(r'[^a-z0-9]+', '-', t.translate(TR).lower()).strip('-')


SLUG_FIX = {}
ONREQ_RE = re.compile(
    r'\s*[-–]?\s*(?:cena\s+)?na\s+(?:poptávku|potávku|vyžádání)(?:\s+viz\s+níže)?\.?\s*$', re.I
)


def norm_item(it):
    """Opraví produkty, které mají na starém webu název jen „poptat/objednat“ nebo cenu v názvu."""
    if it.get('_norm'):
        return
    it['_norm'] = True
    raw = it['raw_title']
    if re.fullmatch(r'\s*poptat\s*/\s*objednat\s*', raw, re.I) and it.get('text'):
        first = next((b for b in it['text'] if b['t'] != 'img'), None)
        if first:
            it['raw_title'] = raw = first['text']
            it['h1'] = raw
            it['text'] = [b for b in it['text'] if b is not first]
            m = re.search(r'(\d[\d ]{2,})\s*,-\s*[kK][čČ]', raw)
            it['price'] = int(m.group(1).replace(' ', '')) if m else None
    t = re.sub(r'(?i)poptat\s*/\s*objednat', '', raw)
    t = re.sub(r'\s*\.{2,}\s*', ' ', t)
    t = re.sub(r'\s*\d[\d .]*,-\s*[kK][čČ].*$', '', t)
    t = ONREQ_RE.sub('', t)
    t = re.sub(r'\s+', ' ', t).strip(' -–!:')
    it['title'] = t


for _pg in DATA['pages'] + [DATA['home']]:
    for _b in _pg['boxes']:
        for _it in _b.get('items', []) if 'products' in _b.get('kind', '') else []:
            norm_item(_it)


def prod_slug(url):
    s = url.rstrip('/').rsplit('/', 1)[-1]
    return SLUG_FIX.get(s, s)


_ALL_RAW = {
    i['url'].rstrip('/').rsplit('/', 1)[-1]
    for _pg in DATA['pages'] + [DATA['home']]
    for _b in _pg['boxes']
    for i in (_b.get('items', []) if 'products' in _b.get('kind', '') else [])
}
for _pg in DATA['pages'] + [DATA['home']]:
    for _b in _pg['boxes']:
        for _it in _b.get('items', []) if 'products' in _b.get('kind', '') else []:
            _raw = _it['url'].rstrip('/').rsplit('/', 1)[-1]
            if _raw not in SLUG_FIX and (
                not re.fullmatch(r'[a-z0-9-]+', _raw) or _raw.startswith('poptat-objednat')
            ):
                cand = slugify(_it.get('title') or _raw) or 'produkt'
                base, k = cand, 2
                while cand in SLUG_FIX.values() or (cand != _raw and cand in _ALL_RAW):
                    cand = f'{base}-{k}'
                    k += 1
                SLUG_FIX[_raw] = cand
for c in CATS:
    for src in c[5]:
        pg = PAGES.get(src)
        if not pg:
            continue
        for b in pg['boxes']:
            for it in b.get('items', []) if 'products' in b['kind'] else []:
                s = prod_slug(it['url'])
                PRODUCTS.setdefault(s, it)
                PROD_CAT.setdefault(s, c[0])
# produkty z úvodní stránky starého webu (pokud jsou)
for b in DATA['home']['boxes']:
    for it in b.get('items', []) if 'products' in b.get('kind', '') else []:
        PRODUCTS.setdefault(prod_slug(it['url']), it)


def prod_title(p):
    t = p['title'] or p.get('h1') or p['raw_title']
    t = re.sub(r'\s*-?\s*AKČNÍ CENA.*$', '', t, flags=re.I)
    t = re.sub(r'!?SKLADEM!?.*$', '', t, flags=re.I).strip(' -–!')
    t = t.replace('  ', ' ')
    return t[:1].upper() + t[1:] if t else 'Model'


def prod_flags(p):
    raw = p['raw_title'] + ' ' + p.get('h1', '')
    f = []
    if re.search(r'SKLADEM', raw, re.I):
        f.append('Skladem')
    if re.search(r'AKČNÍ|akční cena', raw, re.I):
        f.append('Akční cena')
    if re.search(r'NOVINKA', raw, re.I):
        f.append('Novinka')
    return f


def prod_desc_text(p):
    return ' '.join(b['text'] for b in p.get('text', []) if b['t'] != 'img')


def price_label(p):
    if p.get('price'):
        return f'{fmt(p["price"])} Kč'
    txt = prod_desc_text(p)
    if re.search(r'(?i)mořidl|moření|barv|lazur', p['raw_title']):
        nums = sorted({int(x.replace(' ', '')) for x in re.findall(r'(\d[\d ]{2,})\s*,-\s*K', txt)})
        if nums:
            return 'příplatek ' + ' / '.join(fmt(n) for n in nums[:2]) + ' Kč'
    return 'cena na poptávku'


def render_box(b, gid, skip=()):
    """Jeden box ze starého webu: produkty / galerie / text."""
    if 'products' in b['kind']:
        cards = ''.join(prod_card(prod_slug(it['url'])) for it in b.get('items', []))
        return f'<div class="prod-grid">{cards}</div>' if cards else ''
    if 'photogallery' in b['kind']:
        seen, links, descriptions = set(), [], []
        for ph in b.get('photos', []):
            i = mid(ph['src'])
            if not i or i in seen:
                continue
            seen.add(i)
            cap = ph.get('caption', '')
            links.append(
                f'<figure style="margin:0">{lb_link(ph["src"], cap or "Fotografie z dílny Stolařství Kubiš", gid, cap).replace("</a>", (f"<figcaption>{E(cap)}</figcaption>" if cap else "") + "</a>")}</figure>'
            )
            description = ph.get('description', '').strip()
            if description:
                descriptions.append(f'<h3>{E(cap)}</h3><p>{linkify(description)}</p>')
        details = f'<div class="prose">{"".join(descriptions)}</div>' if descriptions else ''
        return f'<div class="gal-grid">{"".join(links)}</div>{details}' if links else ''
    if 'articles' in b['kind']:
        out = []
        for a in b['items']:
            prose, imgs = blocks_html(a.get('blocks', []), gid, skip_text=(a['title'],))
            article_id = urlsplit(a['url']).path.strip('/').split('/')[-1]
            thumbs = thumbs_html(imgs, gid, a['title'])
            media = f'<div class="thumbs">{thumbs}</div>' if thumbs else ''
            out.append(
                f'<article class="entry{" noimg" if not thumbs else ""}" id="{E(article_id)}">{media}<div><h3>{E(a["title"])}</h3><div class="prose">{prose}</div></div></article>'
            )
        return '<div class="entries">' + ''.join(out) + '</div>'
    blocks = b.get('blocks', [])
    head = b.get('heading', '')
    prose, imgs = blocks_html(blocks, gid, skip_text=(head,) + tuple(skip))
    if not prose and not imgs:
        return ''
    m = PRICE_RE.search(head)
    price = f'<span class="price-tag">{m.group(1).strip()} Kč</span>' if m else ''
    clean_head = re.sub(r'\s+', ' ', PRICE_RE.sub('', head).replace('...', '')).strip(' .–-')
    first = next((u for u in imgs if mid(u)), None)
    is_mat = (
        first
        and mid(first) in CUT
        and (CURRENT['slug'] == 'matrace' or re.search(r'(?i)matrac', head))
        and not re.search(r'(?i)chráni|topper|potah|klín|polštář|nabídka matrac|výběr', head)
    )
    if is_mat:
        alt = clean_head or 'Matrace'
        rest = [u for u in imgs if mid(u) != mid(first)]
        txt = head + ' ' + ' '.join(b.get('text', '') for b in blocks if b['t'] != 'img')
        left = mattress_figure(first, alt, gid, txt) + (
            f'<div class="thumbs small">{thumbs_html(rest, gid, alt)}</div>' if rest else ''
        )
        return f'<article class="entry mat"><div class="as-col">{left}</div><div>{f"<h3>{E(clean_head)}</h3>" if clean_head else ""}{price}<div class="prose">{prose}</div></div></article>'
    th = thumbs_html(imgs, gid, clean_head or 'Foto')
    return f'<article class="entry{" noimg" if not th else ""}">{f"<div class=thumbs>{th}</div>" if th else ""}<div>{f"<h3>{E(clean_head)}</h3>" if clean_head else ""}{price}<div class="prose">{prose}</div></div></article>'


# ---------------------------------------------------------------- recenze, novinky, galerie
def parse_reviews():
    box = max(DATA['home']['boxes'], key=lambda b: len(b.get('blocks', [])))
    revs, cur = [], None
    date_re = re.compile(r'^(\d{1,2}\.\s?\d{1,2}\.\s?\d{4})\s*(.*)$')
    for b in box['blocks']:
        if b['t'] == 'img':
            continue
        t = b['text'].strip()
        m = date_re.match(t)
        if m:
            cur = {'date': m.group(1).replace(' ', ''), 'ok': False, 'lines': []}
            revs.append(cur)
            if m.group(2):
                cur['lines'].append(m.group(2))
            continue
        if cur is None:
            continue
        if t.lower() in ('spokojený', 'spokojeny'):
            cur['ok'] = True
            continue
        cur['lines'].append(t)
    return [r for r in revs if r['lines']]


# ---------------------------------------------------------------- karta modelu, produkt
def model_card(s):
    p = PRODUCTS[s]
    title = prod_title(p)
    image = next((u for u in (*(p.get('images') or []), p.get('thumb')) if mid(u)), None)
    ex = prod_desc_text(p) or p.get('excerpt', '')
    flags = ''.join(f'<span class="flag">{E(f)}</span>' for f in prod_flags(p))
    cut = image and mid(image) in CUT
    ph = img_tag(image, title) if image else 'Fotografie na vyžádání'
    pl = price_label(p)
    return f'''<a class="model" href="/produkty/{s}/" data-fx="lift"><span class="ph{' cut' if cut else ''}">{ph}{f'<span class="flags">{flags}</span>' if flags else ''}</span><h3>{E(title)}</h3>{f'<p>{E(ex)}</p>' if ex else ''}<span class="meta"><span class="price{'' if p.get('price') else ' req'}">{E(pl)}</span></span></a>'''


def build_product(s):
    p = PRODUCTS[s]
    cat = CAT_BY_SLUG.get(PROD_CAT.get(s, ''))
    title = prod_title(p)
    imgs = [
        u
        for u in dict.fromkeys(p.get('images') or ([p['thumb']] if p.get('thumb') else []))
        if mid(u)
    ]
    prose, _ = blocks_html(p.get('text', []), 'p', skip_text=(p.get('h1', ''), p['raw_title']))
    prose = prose.replace(
        'Poptat nebo objednat je možné ve formuláři níže.',
        'Poptat nebo objednat můžete ve formuláři níže.',
    )
    gallery = ''
    if imgs:
        i0 = mid(imgs[0])
        w, h = media_size(i0, 'l')
        is_cut = i0 in CUT
        is_mat = (
            is_cut
            and re.search(r'(?i)matrac', title + ' ' + p['raw_title'])
            and not re.search(r'(?i)chránič|hranol|potah', title)
        )
        if is_mat:
            main = mattress_figure(imgs[0], title, 'prod', title + ' ' + prod_desc_text(p))
        else:
            main = f'<a class="main{" cutwrap" if is_cut else ""}" href="{media_src(i0, "l")}" data-lb="prod" data-cap="{E(title)}"><img src="{media_src(i0, "l")}" width="{w}" height="{h}" alt="{E(title)}" fetchpriority="high"></a>'
        thumbs = ''.join(
            f'<a href="{media_src(mid(u), "l")}" data-lb="prod" data-cap="{E(title)}">{img_tag(u, f"{title}, foto {k + 2}")}</a>'
            for k, u in enumerate(imgs[1:])
        )
        gallery = f'<div class="gallery">{main}{f"<div class=thumbs-row>{thumbs}</div>" if thumbs else ""}</div>'
    opts = ''.join(
        f'<dt>{E(o["label"])}</dt><dd>{E(", ".join(o["values"]))}</dd>'
        for o in p.get('options', [])
    )
    flags = ' '.join(
        f'<span class="flag" style="position:static">{E(f)}</span>' for f in prod_flags(p)
    )
    related = [x for x, cslug in PROD_CAT.items() if cat and cslug == cat[0] and x != s][:4]
    desc_txt = prod_desc_text(p)[:155] or f'{title} z masivu od Stolařství Kubiš.'
    crumb_items = ([(cat[2], f'/{cat[0]}/')] if cat else []) + [(title, None)]
    details = (
        f'<section class="wrap details"><div><h2>Popis a parametry</h2><div class="prose">{prose}</div></div>{f"<div><h2>Možnosti</h2><dl class=opts>{opts}</dl></div>" if opts else ""}</section>'
        if prose or opts
        else ''
    )
    more = ''
    if related:
        more = f'<section class="sec paper"><div class="wrap"><div class="sec-head"><h2>Další modely v kategorii</h2><a class="link arrow" href="/{cat[0]}/">{E(cat[2])}</a></div><div class="models">{"".join(model_card(x) for x in related)}</div></div></section>'
    body = f'''<article>
<div class="wrap">{crumbs(*crumb_items)}
<div class="product">
  {gallery or '<div class="gallery"></div>'}
  <div class="panel">
    {f'<div>{flags}</div>' if flags else ''}
    <h1>{E(title)}</h1>
    <div class="price">{E(price_label(p))}<small>Orientační cena podle ceníku, bez roštu a matrace, pokud není uvedeno jinak. Přesnou cenu pošleme v písemné nabídce.</small></div>
    <div class="ctas"><a class="btn btn-primary" href="#poptavka">Poptat tento model</a><a class="btn btn-ghost" href="tel:{TEL1H}">{TEL1}</a></div>
    <ul class="perks"><li>Rozměr, výšku i dřevinu upravíme na přání</li><li>Dovoz naším autem a montáž zdarma, po ČR i SR</li><li>Na typizované postele záruka 5 let</li><li>K vyzkoušení na prodejně v Němčičkách</li></ul>
  </div>
</div></div>
{details}
{more}
{form_html(model=title, title=f'Poptat: {title}')}
</article>'''
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            crumbs_ld(([(cat[2], f'/{cat[0]}/')] if cat else []) + [(title, f'/produkty/{s}/')]),
            {
                "@type": "Product",
                "name": title,
                "description": prod_desc_text(p)[:500],
                "brand": {"@type": "Brand", "name": "Stolařství Kubiš"},
                "image": [SITE + media_src(mid(u), 'l') for u in imgs[:4]],
                **(
                    {
                        "offers": {
                            "@type": "Offer",
                            "price": p['price'],
                            "priceCurrency": "CZK",
                            "availability": (
                                "https://schema.org/InStock"
                                if 'Skladem' in prod_flags(p)
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
    tkey = title.lower()
    page_title = f'{title}, {price_label(p)}' if TITLE_COUNT.get(tkey, 0) > 1 else title
    page(
        f'/produkty/{s}/',
        page_title,
        desc_txt,
        body,
        jsonld=ld,
        og_img=SITE + media_src(mid(imgs[0]), 'l') if imgs else None,
    )


# ---------------------------------------------------------------- kategorie
def build_category(c):
    slug, group, menu, h1, intro, sources = c
    CURRENT['slug'] = slug
    cp = COPY.get(slug, {})
    siblings = ''.join(
        f'<a href="/{x[0]}/"{" aria-current=page" if x[0] == slug else ""}>{E(x[2])}</a>'
        for x in CATS
        if x[1] == group
    )
    cover = cover_img(slug)
    model_html, prices, rest = [], [], []
    SEEN = set()
    for k, src in enumerate(sources):
        pg = PAGES.get(src)
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
                slugs = [prod_slug(it['url']) for it in b.get('items', [])]
                slugs = [x for x in slugs if x not in SEEN]
                SEEN.update(slugs)
                if not slugs:
                    continue
                prices += [PRODUCTS[x]['price'] for x in slugs if PRODUCTS[x].get('price')]
                heading = b.get('heading', '') if b['kind'].startswith('list products') else ''
                model_html.append(
                    (f'<h2 class="block-title">{E(heading)}</h2>' if heading else '')
                    + f'<div class="models">{"".join(model_card(x) for x in slugs)}</div>'
                )
                continue
            h = render_box(b, gid)
            if not h:
                continue
            sig = re.sub(r'data-lb="[^"]*"', '', h)
            if sig in SEEN:
                continue
            SEEN.add(sig)
            heading = b.get('heading', '') if b['kind'].startswith('list photogallery') else ''
            if 'photogallery' in b['kind']:
                heading = re.sub(
                    r'^Fotogalerie:\s*', 'Fotogalerie · ', heading or 'Fotogalerie'
                ).rstrip(' ·')
            rest.append((f'<h2 class="block-title">{E(heading)}</h2>' if heading else '') + h)
    nprod = len([x for x in SEEN if x in PRODUCTS])
    facts = list(cp.get('facts', []))
    if len(prices) >= 3 and slug not in ('dreviny-a-povrchy',):
        facts.insert(0, (f'od {fmt(min(prices))} Kč', f'{nprod} modelů v nabídce'))
    keyfacts = ''.join(f'<li><b>{E(a)}</b> {E(b)}</li>' for a, b in facts)
    chips = (
        f'<nav class="chips" aria-label="{E(GROUPS[group])}">{siblings}</nav>'
        if group in ('potreba', 'typ', 'nabytek', 'spanek')
        else ''
    )
    guide = ''
    if cp.get('guide'):
        guide = f'<section class="sec paper"><div class="wrap"><h2 style="margin-bottom:32px">Jak vybrat</h2><div class="guide">{"".join(f"<div><h3>{E(t)}</h3><p>{E(x)}</p></div>" for t, x in cp["guide"])}</div></div></section>'
    rest_html = '\n'.join(rest)
    rest_html = re.sub(r'(</article>)\s*(<article class="entry)', r'\1\2', rest_html)
    rest_html = re.sub(
        r'((?:<article class="entry.*?</article>)+)',
        r'<div class="entries">\1</div>',
        rest_html,
        flags=re.S,
    )
    details = (
        f'<section class="sec"><div class="wrap"><h2 style="margin-bottom:12px">Podrobnosti a fotogalerie</h2><div style="margin-top:28px">{rest_html}</div></div></section>'
        if rest_html.strip()
        else ''
    )
    body = f'''<section class="page-head"><div class="wrap">
  {crumbs((menu, None))}
  <div class="grid">
    <div><h1>{E(h1)}</h1><p class="lead">{E(intro)}</p>{f'<ul class="keyfacts">{keyfacts}</ul>' if keyfacts else ''}</div>
    <div>{cover}</div>
  </div>
</div></section>
<section class="wrap" style="padding-bottom:clamp(40px,6vw,80px)">{chips}{"".join(model_html)}</section>
{guide}
{details}
{faq_html(cp.get('faq'), more=True)}
{cta_band(title='Chcete jiný rozměr nebo provedení?', text='Napište nebo zavolejte. Vyrobíme podle vašich rozměrů, nákresu nebo fotky.', model=menu)}'''
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            crumbs_ld([(menu, f'/{slug}/')]),
            {
                "@type": "CollectionPage",
                "name": h1,
                "description": cp.get('desc', intro),
                "url": SITE + f'/{slug}/',
            },
        ]
        + ([faq_ld(cp['faq'])] if cp.get('faq') else []),
    }
    page(
        f'/{slug}/',
        cp.get('title', h1),
        cp.get('desc', intro)[:158],
        body,
        jsonld=ld,
        og_img=SITE + '/img/' + COVERS[slug][0] + '.jpg',
    )


def tile(href, img, title, text, num='', w=1200, h=900):
    return f'<a class="tile" href="{href}"><img src="/img/{img}.jpg" width="{w}" height="{h}" alt="" loading="lazy" decoding="async"><span class="b"><h3>{E(title)}</h3><p>{E(text)}</p>{f"<span class=num>{E(num)}</span>" if num else ""}</span></a>'


def cat_tile(slug, text, num=''):
    n, w, h = COVERS[slug]
    return tile(f'/{slug}/', n, CAT_BY_SLUG[slug][2], text, num, w, h)


def build_hub_postele():
    t = lambda slug, text, num='': cat_tile(slug, text, num)
    potreba = ''.join(
        [
            t(
                'postele-pro-seniory',
                'Zvýšená ložná plocha pro snadné vstávání, matrace s tuhým okrajem.',
                '55 / 60 / 65 cm',
            ),
            t(
                'vysokozatezove-postele',
                'Tvrdé dřeviny, masiv 40 mm, pevné rošty. I prodloužené délky.',
                '400–500 kg',
            ),
            t(
                'postele-pro-handicapovane',
                'Ohrádky, posuvná dvířka, polohovací a motorové rošty.',
                'na míru',
            ),
            t(
                'postele-na-miru',
                'Atypické rozměry, čalouněná čela, nadrozměrné postele.',
                'do 4 týdnů',
            ),
            t(
                'patrove-a-vysoke-postele',
                'Palandy a vysoké postele se zásuvkami.',
                'i pro dospělé',
            ),
        ]
    )
    typ = ''.join(
        [
            t('jednoluzka', 'Od klasiky po pohovkové postele.'),
            t('dvouluzka', 'Manželské postele od smrku po dub.'),
            t('studentske-postele', 'Šířky 120 a 140 cm.'),
            t('dubove-postele', 'Masivní dub o tloušťce 42 mm.'),
            t('doplnky-k-postelim', 'Šuplíky, přistýlky, zábrany.'),
        ]
    )
    faq = [
        (
            'Jaká je nejlevnější postel z masivu u vás?',
            'Jednolůžka ze smrku nebo borovice začínají zhruba na 6 880 Kč bez roštu a matrace. Buk a dub jsou dražší, ale trvanlivější.',
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
    body = f'''<section class="wrap page-intro">{crumbs(('Postele z masivu', None))}
<h1>Postele z masivu na míru</h1>
<p class="lead">Rodinná výroba z buku, jádrového buku, dubu a dalších dřevin. Vyberte podle toho, co potřebujete, nebo podle typu. Vše vyrobíme i v jiném rozměru.</p></section>
<section class="wrap" style="padding-bottom:56px"><h2 style="margin-bottom:24px">Podle potřeby</h2><div class="tiles big">{potreba}</div></section>
<section class="sec paper"><div class="wrap"><h2 style="margin-bottom:24px">Podle typu</h2><div class="tiles big">{typ}</div></div></section>
<section class="sec"><div class="wrap split"><div><h2>Buk, jádrový buk nebo dub?</h2>
<p>Smrk a borovice jsou cenově nejdostupnější. Buk je tvrdý a světlý, jádrový buk má výraznou tmavou kresbu, kterou nikdo nezopakuje. Dub je nejtvrdší a nejodolnější. Pro vysokou nosnost doporučujeme buk, jasan nebo dub.</p>
<div class="ctas"><a class="link arrow" href="/dreviny-a-povrchy/">Srovnání dřevin a povrchů</a></div></div><img src="/img/detail-buk.jpg" width="1400" height="1050" alt="Detail nohy postele z jádrového buku" loading="lazy"></div></section>
{faq_html(faq)}
{cta_band()}'''
    page(
        '/postele-z-masivu/',
        'Postele z masivu na míru: katalog',
        'Katalog postelí z masivu: pro seniory, vysokozátěžové, s ohrádkou, na míru, patrové, jednolůžka a dvoulůžka. Výrobce z Němčiček u Brna.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [crumbs_ld([('Postele z masivu', '/postele-z-masivu/')]), faq_ld(faq)],
        },
    )


def build_hub_nabytek():
    t = cat_tile
    body = f'''<section class="wrap page-intro">{crumbs(('Nábytek z masivu', None))}
<h1>Nábytek z masivu na zakázku</h1>
<p class="lead">Komody, psací a jídelní stoly, odkládací stolky. Vyrábíme podle vašich rozměrů z buku, dubu nebo smrku. Šatní skříně momentálně z kapacitních důvodů nevyrábíme.</p></section>
<section class="wrap" style="padding-bottom:clamp(48px,7vw,96px)"><div class="tiles big">{t('komody-a-psaci-stoly', 'Zásuvkové komody, peřináče, psací stoly.')}{t('jidelni-stoly', 'Dub, buk i borovice, povrch vhodný na potraviny.')}{t('bytove-doplnky', 'Odkládací stolky, věšákové stěny.')}</div></section>
{cta_band(title='Potřebujete nábytek na míru?', text='Pošlete rozměry nebo fotku, připravíme nabídku.')}'''
    page(
        '/nabytek-z-masivu/',
        'Nábytek z masivu na zakázku',
        'Komody, psací a jídelní stoly a drobný nábytek z masivu na zakázku. Vyrábíme v Němčičkách u Židlochovic.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [crumbs_ld([('Nábytek z masivu', '/nabytek-z-masivu/')])],
        },
    )


# ---------------------------------------------------------------- textové stránky
MAP_NEMCICKY = 'https://mapy.cz/zakladni?q=49.04952%2C16.50048'


def intro_block(menu, title, lead='', eyebrow=''):
    return f'<section class="wrap page-intro">{crumbs((menu, None))}<h1>{E(title)}</h1>{f"<p class=lead>{lead}</p>" if lead else ""}</section>'


def build_contact():
    body = f'''{intro_block('Kontakt', 'Kontakt', 'Zavolejte kvůli výběru postele, návštěvě prodejny nebo zakázce na míru. Telefon zvedá přímo rodina.')}
<div class="wrap contact-cols">
  <section><dl><dt>Prodej, matrace, návštěvy</dt><dd><a href="tel:{TEL1H}">{TEL1}</a></dd><dt>Výroba a projekty</dt><dd><a href="tel:{TEL2H}">{TEL2}</a></dd><dt>E-mail</dt><dd><a href="mailto:{MAIL}">{MAIL}</a></dd></dl>
  <div class="ctas"><a class="btn btn-primary" href="/poptavka/">Napsat poptávku</a></div></section>
  <section><img src="/img/prodejna-1.jpg" alt="Ukázková prodejna v Němčičkách s postelí a cihlovou zdí" width="1400" height="1050">
  <h2 style="font-size:1.5rem">Dílna a ukázková prodejna</h2>
  <address style="font-style:normal;margin:10px 0"><strong>STOLAŘSTVÍ Petr Kubiš</strong><br>Němčičky 5, 664 66 Němčičky u Židlochovic<br>IČO 69752460</address>
  <p><a class="link" href="{MAP_NEMCICKY}" target="_blank" rel="noopener">Ukázat na mapě</a> · <a class="link" href="/prodejna-nemcicky/">Návštěva prodejny</a></p></section>
</div>'''
    page(
        '/kontakt/',
        'Kontakt',
        'Telefon, e-mail a adresa dílny a prodejny Stolařství Kubiš v Němčičkách u Židlochovic.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [crumbs_ld([('Kontakt', '/kontakt/')])],
        },
    )


TEXT_COPY = {
    'o-nas': (
        'Rodinná firma, která postele nejen prodává, ale sama staví. Od roku 1999 v Němčičkách u Židlochovic.',
        'Příběh',
    ),
    'prodejna-nemcicky': (
        'Postele, nábytek a matrace si můžete prohlédnout a vyzkoušet osobně. Návštěvu prosím domluvte předem.',
        'Prodejna',
    ),
    'doprava-a-montaz': (
        'Vlastním autem vozíme po celé České republice i na Slovensko a postel na místě smontujeme. Montáž je při dovozu zdarma.',
        'Služby',
    ),
    'obchodni-podminky': (
        'Jak poptávat, objednávat a platit. Postup od poptávky po montáž.',
        'Informace',
    ),
}
TEXT_TITLES = {
    'o-nas': (
        'O nás: rodinné stolařství z Němčiček',
        'Rodinné stolařství Kubiš z Němčiček u Židlochovic vyrábí nábytek z masivu od roku 1999. Postele pro seniory, vysokozátěžové, s ohrádkou a na míru.',
    ),
    'prodejna-nemcicky': (
        'Prodejna postelí a matrací v Němčičkách u Brna',
        'Ukázková prodejna Stolařství Kubiš v Němčičkách u Židlochovic (Brno-venkov). Postele z masivu a matrace k vyzkoušení po domluvě.',
    ),
    'doprava-a-montaz': (
        'Doprava a montáž nábytku po celé ČR a SR',
        'Doprava vlastním autem 14 Kč/km tam i zpět (min. 300 Kč), montáž zdarma. Po celé ČR i SR. Výnos do pater po domluvě.',
    ),
    'obchodni-podminky': (
        'Obchodní podmínky a jak objednávat',
        'Jak poptávat a objednávat nábytek ve Stolařství Kubiš: nabídka, záloha, výroba, dovoz a montáž, záruka.',
    ),
}


def build_text(slug, menu, h1, src):
    if slug == 'kontakt':
        build_contact()
        return
    pg = PAGES.get(src, {'boxes': []})
    secs = [
        render_box(b, f't{j}', skip=(h1, menu, pg.get('title', '')))
        for j, b in enumerate(pg['boxes'])
    ]
    content = '\n'.join(x for x in secs if x)
    content = re.sub(
        r'((?:<article class="entry.*?</article>)+)',
        r'<div class="entries">\1</div>',
        content,
        flags=re.S,
    )
    lead, eyebrow = TEXT_COPY[slug]
    side = f'''<aside class="side-card"><h2>Kontakt</h2><p><strong>STOLAŘSTVÍ Petr Kubiš</strong><br>Němčičky 5, 664 66 Němčičky u Židlochovic<br>IČO 69752460</p><p>Prodej a matrace: <a href="tel:{TEL1H}">{TEL1}</a><br>Výroba a projekty: <a href="tel:{TEL2H}">{TEL2}</a><br><a href="mailto:{MAIL}">{MAIL}</a></p><a class="btn btn-primary" href="/poptavka/">Napsat poptávku</a></aside>'''
    top = ''
    if slug == 'prodejna-nemcicky':
        top = f'''<img src="/img/prodejna-1.jpg" alt="Ukázková prodejna v Němčičkách s postelí a cihlovou zdí" width="1400" height="1050" style="border-radius:10px;margin-bottom:28px">
<dl class="hours" style="margin-bottom:28px"><dt>Po–Pá</dt><dd>15:00–20:00, pouze po domluvě předem</dd><dt>So–Ne</dt><dd>9:00–20:00, pouze po domluvě předem</dd><dt>Domluva</dt><dd><a class="link" href="tel:{TEL1H}">{TEL1}</a></dd><dt>Adresa</dt><dd>Němčičky 5, 664 66 Němčičky u Židlochovic · <a class="link" href="{MAP_NEMCICKY}" target="_blank" rel="noopener">mapa</a></dd></dl>'''
    if slug == 'o-nas':
        top = '<img src="/img/detail-buk.jpg" alt="Detail nohy postele z jádrového buku" width="1400" height="1050" style="border-radius:10px;margin-bottom:28px">'
    after = ''
    if slug == 'prodejna-nemcicky':
        after = '<div class="wrap photo-pair"><img src="/img/prodejna-2.jpg" alt="Postele a matrace v ukázkové prodejně" width="1400" height="1243" loading="lazy"><img src="/img/prodejna-3.jpg" alt="Postel s laťkovým čelem na prodejně" width="1050" height="1400" loading="lazy"></div>'
    body = f'''{intro_block(menu, h1, lead, eyebrow)}
<div class="wrap text-page"><div>{top}{content}</div>{side}</div>{after}'''
    ttl, desc = TEXT_TITLES[slug]
    ld = [crumbs_ld([(menu, f'/{slug}/')])]
    page(f'/{slug}/', ttl, desc, body, jsonld={"@context": "https://schema.org", "@graph": ld})


def build_gdpr():
    title = 'Ochrana osobních údajů'
    body = f'''{intro_block(title, title, 'Jak zacházíme s údaji, které nám pošlete v poptávce nebo objednávce. Platí od 19. 11. 2026.')}
<div class="wrap text-page"><div class="prose">
<h2>Kdo je správce</h2><p>STOLAŘSTVÍ Petr Kubiš, IČO 69752460, Němčičky 5, 664 66 Němčičky u Židlochovic. Kontakt: <a href="mailto:{MAIL}">{MAIL}</a>, tel. <a href="tel:{TEL1H}">{TEL1}</a>.</p>
<h2>Jaké údaje zpracováváme</h2><p>Jméno a příjmení, telefon, e-mail, adresu dodání a to, co nám o své zakázce napíšete (rozměry, požadavky, případně fotky nebo nákresy).</p>
<h2>Proč a na jakém základě</h2><ul>
<li>Abychom mohli odpovědět na poptávku, připravit nabídku a vyrobit a dodat objednaný nábytek (plnění smlouvy a jednání o ní, čl. 6 odst. 1 písm. b) GDPR).</li>
<li>Abychom splnili účetní a daňové povinnosti (právní povinnost, čl. 6 odst. 1 písm. c) GDPR).</li>
<li>Abychom mohli vyřídit záruku a reklamaci a evidovat zakázky (oprávněný zájem, čl. 6 odst. 1 písm. f) GDPR).</li></ul>
<p>Obchodní sdělení vám bez vašeho souhlasu neposíláme.</p>
<h2>Jak dlouho</h2><p>Poptávky, ze kterých nevznikla objednávka, mažeme nejpozději po jednom roce. Údaje k zakázkám uchováváme po dobu záruky a dále po dobu, kterou ukládají účetní a daňové předpisy (u daňových dokladů až 10 let).</p>
<h2>Komu údaje předáváme</h2><p>Nikomu je neprodáváme. Nábytek vozíme vlastním autem, přepravní služby nepoužíváme. Poptávkový formulář na webu doručuje zprávu e-mailem přes službu FormSubmit (formsubmit.co); dále se údaje mohou nacházet u poskytovatele e-mailu a webhostingu. Jinak je předáváme jen tehdy, když to ukládá zákon.</p>
<h2>Cookies</h2><p>Web nepoužívá analytické ani reklamní cookies a nesleduje vás. Písma i skripty načítáme z našeho serveru, ne od třetích stran.</p>
<h2>Vaše práva</h2><p>Máte právo na přístup ke svým údajům, jejich opravu, výmaz, omezení zpracování, přenositelnost a právo vznést námitku. Stačí napsat na <a href="mailto:{MAIL}">{MAIL}</a>. Pokud si myslíte, že s údaji zacházíme špatně, můžete podat stížnost u Úřadu pro ochranu osobních údajů (<a href="https://uoou.gov.cz" target="_blank" rel="noopener">uoou.gov.cz</a>).</p>
</div><aside class="side-card"><h2>Dotaz k osobním údajům</h2><p><a href="mailto:{MAIL}">{MAIL}</a><br><a href="tel:{TEL1H}">{TEL1}</a></p></aside></div>'''
    page(
        '/ochrana-osobnich-udaju/',
        title,
        'Jak Stolařství Kubiš zpracovává osobní údaje z poptávek a objednávek.',
        body,
    )


# ---------------------------------------------------------------- recenze, novinky, galerie
def build_reviews():
    revs = parse_reviews()
    reviews = []
    for review in revs:
        date = datetime.datetime.strptime(review['date'], '%d.%m.%Y').date()
        status = '<span class="ok">Spokojený</span>' if review['ok'] else ''
        quote = ''.join(f'<p>{linkify(line)}</p>' for line in review['lines'])
        reviews.append(
            f'<figure class="review"><figcaption><time datetime="{date.isoformat()}">{E(review["date"])}</time>{status}</figcaption><blockquote>{quote}</blockquote></figure>'
        )
    gal = render_box(
        next(b for b in PAGES['/reference/']['boxes'] if 'photogallery' in b['kind']), 'ref'
    )
    body = f'''{intro_block('Realizace a recenze', 'Realizace a recenze zákazníků', f'{len(revs)} recenzí od zákazníků z celé republiky od roku 2013. Píšou je sami zákazníci a my na nich nic neupravujeme.', 'Reference')}
<div class="wrap" style="padding-bottom:clamp(48px,7vw,96px)">
<nav class="chips" aria-label="Obsah stránky"><a href="#recenze">Recenze zákazníků</a><a href="#realizace">Fotografie realizací</a></nav>
<section aria-labelledby="recenze"><h2 class="block-title" id="recenze">Recenze zákazníků</h2><div class="feature-review">{reviews[0]}</div><div class="reviews">{"".join(reviews[1:])}</div></section>
<section aria-labelledby="realizace"><h2 class="block-title" id="realizace">Fotografie realizací</h2>{gal}</section></div>
<section class="band cta-band"><div class="wrap"><div><h2>Byli jste u nás spokojeni?</h2><p style="margin-top:10px">Napište pár řádků, rádi je přidáme mezi ostatní.</p></div><div class="ctas"><a class="btn btn-primary" href="mailto:{MAIL}?subject=Recenze">Napsat recenzi</a></div></div></section>'''
    page(
        '/realizace-a-recenze/',
        'Realizace a recenze zákazníků',
        f'{len(revs)} recenzí zákazníků Stolařství Kubiš od roku 2013 a fotografie realizací postelí z masivu.',
        body,
    )
    return revs


EXPIRED = {1: 'Akce skončila', 4: 'Akce skončila', 5: 'Akce skončila'}
SKIP_HOME = {14}


def build_news():
    boxes = DATA['home']['boxes']
    rev_box = max(range(len(boxes)), key=lambda i: len(boxes[i].get('blocks', [])))
    out = []
    for i, b in enumerate(boxes):
        if i == rev_box or i in SKIP_HOME or 'articles' in b['kind']:
            continue
        h = render_box(b, f'n{i}')
        if not h:
            continue
        badge = f'<span class="badge">{EXPIRED[i]}</span>' if i in EXPIRED else ''
        out.append(f'<div class="news-item">{badge}{h}</div>')
    for b in [b for b in boxes if 'articles' in b['kind']]:
        out.append(render_box(b, 'na'))
    body = f'''{intro_block('Novinky', 'Novinky z dílny', 'Nové modely, kusy skladem a co se u nás děje. Aktuality sdílíme i na <a class="link" href="https://www.facebook.com/stolarstvikubis/" target="_blank" rel="noopener">Facebooku</a>.')}
<div class="wrap" style="padding-bottom:clamp(48px,7vw,96px)"><div class="entries">{"".join(out)}</div></div>'''
    page(
        '/novinky/',
        'Novinky',
        'Novinky ze Stolařství Kubiš: nové modely postelí, matrace a kusy skladem.',
        body,
    )


def build_gallery():
    secs, nav = [], []
    sources = [
        ('Dvoulůžka', '/fotogalerie/dvouluzka/'),
        ('Jednolůžka', '/fotogalerie/jednoluzka/'),
        ('Vysoké postele s úložnými prostory', '/vysoke-postele-s-velkymi-prostory/'),
        ('Patrové palandy', '/fotogalerie/patrove-palandy/'),
        ('Postele s ohrádkou', '/postele-pro-handicapovane/'),
        ('Komody', '/fotogalerie/komody/'),
        ('Psací stoly', '/fotogalerie/psaci-stoly/'),
        ('Šatní skříně', '/fotogalerie/satni-skrine/'),
        ('Realizace u zákazníků', '/reference/'),
        ('Lanett v odvážných barvách', None),
    ]
    total = 0
    for k, (name, src) in enumerate(sources):
        boxes = (
            [b for b in PAGES.get(src, {'boxes': []})['boxes'] if 'photogallery' in b['kind']]
            if src
            else [b for b in DATA['home']['boxes'] if 'photogallery' in b['kind']]
        )
        merged = {'kind': 'list photogallery', 'photos': [p for b in boxes for p in b['photos']]}
        h = render_box(merged, f'gal{k}')
        if not h:
            continue
        n = h.count('data-lb=')
        total += n
        anchor = slugify(name)
        nav.append(f'<li><a href="#{anchor}">{E(name)} <span class="mono">{n}</span></a></li>')
        secs.append(
            f'<section class="album" aria-labelledby="{anchor}"><header><h2 id="{anchor}">{E(name)}</h2><p class="mono">{n} fotografií</p></header>{h}</section>'
        )
    body = f'''{intro_block('Fotogalerie', 'Fotogalerie postelí a nábytku', f'{total} fotografií z naší dílny a od zákazníků. Klikněte na fotku pro zvětšení.')}
<div class="wrap" style="padding-bottom:clamp(48px,7vw,96px)"><ul class="album-index">{"".join(nav)}</ul>{"".join(secs)}</div>'''
    page(
        '/galerie/',
        'Fotogalerie postelí a nábytku z masivu',
        f'{total} fotografií postelí, palend, komod a stolů z masivu ze Stolařství Kubiš.',
        body,
    )


def build_inquiry():
    body = f'''{intro_block('Poptávka', 'Poptávka', 'Napište, co potřebujete. Ozveme se a pošleme nabídku s cenou a termínem.')}
{form_html(title='Co pro vás můžeme vyrobit?', intro='Postel, komodu, matraci nebo nábytek z masivu na míru. Stačí pár řádků.')}'''
    page(
        '/poptavka/',
        'Poptávka',
        'Poptejte postel nebo nábytek z masivu na míru. Ozveme se a pošleme nabídku.',
        body,
    )


def build_404():
    body = f'''<div class="wrap missing"><div><h1 style="margin:14px 0 18px">Tahle stránka se nám ztratila v pilinách</h1><p class="lead">Možná jste přišli ze starého odkazu. Zkuste katalog nebo nám rovnou zavolejte.</p>
<div class="ctas" style="margin-top:24px"><a class="btn btn-primary" href="/">Úvodní stránka</a><a class="btn btn-ghost" href="/postele-z-masivu/">Katalog postelí</a><a class="btn btn-ghost" href="tel:{TEL1H}">{TEL1}</a></div></div>
<img src="/img/detail-buk.jpg" alt="" width="1400" height="1050"></div>'''
    page('/404.html', 'Stránka nenalezena', 'Stránka nenalezena.', body, noindex=True)


def build_faq_page():
    allq = [x for _, items in FAQ_GROUPS for x in items]
    nav = ''.join(f'<a href="#{slugify(g)}">{E(g)}</a>' for g, _ in FAQ_GROUPS)
    secs = ''.join(
        f'<section class="faq-group" id="{slugify(g)}"><h2>{E(g)}</h2><div class="faq">{"".join(f"<details><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in items)}</div></section>'
        for g, items in FAQ_GROUPS
    )
    body = f'''{intro_block('Časté dotazy', 'Časté dotazy', f'Odpovědi na to, na co se nás zákazníci ptají nejčastěji: objednávka, platba, doprava, záruka, výška a nosnost postelí. Nenašli jste svou otázku? Zavolejte na <a class="link" href="tel:{TEL1H}">{TEL1}</a>.')}
<div class="wrap" style="padding-bottom:clamp(48px,7vw,96px)"><nav class="chips" aria-label="Témata">{nav}</nav>{secs}</div>
{cta_band(title='Nenašli jste odpověď?', text='Napište nebo zavolejte, rádi poradíme.')}'''
    page(
        '/caste-dotazy/',
        'Časté dotazy: objednávka, platba, doprava, záruka',
        'Odpovědi na časté dotazy k objednávce, platbě, dopravě, záruce, výšce a nosnosti postelí ze Stolařství Kubiš.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [crumbs_ld([('Časté dotazy', '/caste-dotazy/')]), faq_ld(allq)],
        },
    )


# ---------------------------------------------------------------- poradna (texty ze starého webu a ceníku, ke schválení majiteli)
ARTICLES = [
    (
        'vyska-postele-pro-seniory',
        'Jak vysoká má být postel pro seniora',
        'Postel pro seniora by měla mít ložnou plochu 55 až 65 cm nad podlahou. Jak vybrat výšku a na co dalšího myslet.',
        'Výška postele rozhoduje o tom, jak snadno se z ní vstává. U běžných postelí je ložná plocha dole, u seniorských zvýšená.',
        [
            (
                'Tři výšky, ze kterých vybíráme',
                '<p>Měříme výšku od podlahy k povrchu matrace. Klasická postel má 55 cm, seniorská 60 cm a pro vyšší postavy ji zvedáme na 65 cm. Výšku upravíme podle postavy i podle tloušťky matrace, takže na hraně sedíte rovně a nohy máte pevně na zemi.</p>',
            ),
            (
                'Pro koho je vyšší postel vhodná',
                '<p>Pro uživatele s kloubními problémy kyčlí a kolen, při bolestech zad a při těžkém vstávání. Vyšší ložná plocha zkracuje cestu nahoru a zmenšuje zátěž na kolena.</p>',
            ),
            (
                'Na co dalšího myslet',
                '<ul><li><b>Matrace s tuhým okrajem.</b> Zpevněný okraj z tuhé pěny drží hranu stabilní a zvyšuje bezpečnost při usedání.</li><li><b>Opora.</b> Podpěrná zábrana nebo madlo (750 Kč) je pevně zčepované, nekývá se.</li><li><b>Nosnost.</b> Naše postele unesou 400 kg na lůžko, vybrané modely 500 kg.</li></ul>',
            ),
        ],
        'postele-pro-seniory',
    ),
    (
        'nosnost-postele',
        'Nosnost postele: co znamená 400 a 500 kg',
        'Z čeho se staví postel s vysokou nosností: tvrdé dřeviny, masiv o tloušťce 40 mm a pevný rošt. Co rozhoduje a na co se ptát.',
        'Nosnost postele není jen číslo v katalogu. Závisí na dřevině, tloušťce materiálu, spojích a roštu.',
        [
            (
                'Dřevina',
                '<p>Vysokozátěžové postele děláme z tvrdých dřevin: buk, jasan a dub. Smrk a borovice jsou měkčí a pro vysokou zátěž je nedoporučujeme.</p>',
            ),
            (
                'Tloušťka a spoje',
                '<p>Používáme masiv o tloušťce 40 mm. Spoje jsou čepované a pevné, nejde o spojení několika šroubů, které se časem uvolní.</p>',
            ),
            (
                'Rošt a matrace',
                '<p>Pevný masivní rošt má nosnost 500 kg. K tomu patří odpovídající matrace: vysokozátěžové Fortis (do 180 kg) a Berta (do 150 kg) si můžete vyzkoušet na prodejně.</p>',
            ),
            (
                'Co dostanete',
                '<p>Nosnost 400 kg na lůžko je u nás bez příplatku, u vybraných modelů z tvrdého buku a dubu až 500 kg. Na typizované postele dáváme záruku 5 let.</p>',
            ),
        ],
        'vysokozatezove-postele',
    ),
    (
        'buk-jadrovy-buk-nebo-dub',
        'Buk, jádrový buk nebo dub: kterou dřevinu vybrat',
        'Srovnání dřevin, které na postele používáme: smrk, borovice, modřín, olše, buk, jasan a dub. Tvrdost, vzhled a cena.',
        'Vyrábíme ze sedmi dřevin. Každá se hodí na něco jiného.',
        [
            (
                'Smrk a borovice',
                '<p>Nejdostupnější, světlé, s viditelnou kresbou. Hodí se do dětských pokojů a tam, kde nejde o maximální zátěž.</p>',
            ),
            (
                'Buk a jádrový buk',
                '<p>Tvrdý a světlý. Jádrový buk má navíc tmavé jádro, takže každý kus vypadá jinak. Takové jsou naše postele Martina a Lanett.</p>',
            ),
            (
                'Jasan a dub',
                '<p>Nejtvrdší dřeviny z nabídky. Dub ošetřujeme olejem, dubová dvoulůžka mají masiv o tloušťce 42 mm.</p>',
            ),
            (
                'Povrch',
                '<p>Používáme vodou ředitelné laky a mořidla. Vnitřní roštovou část záměrně nelakujeme, aby dřevo dýchalo. Moření stojí u jednolůžka +700 Kč, u dvoulůžka +1 200 Kč.</p>',
            ),
        ],
        'dreviny-a-povrchy',
    ),
]


def build_poradna():
    cards = ''.join(
        f'<a class="tile" href="/poradna/{s}/"><span class="b"><h3>{E(t)}</h3><p>{E(d)}</p><span class="num">číst dál →</span></span></a>'
        for s, t, d, *_ in ARTICLES
    )
    body = f'''{intro_block('Poradna', 'Poradna: jak vybrat postel z masivu', 'Krátké rady k výběru výšky, nosnosti a dřeviny. Z toho, co děláme každý den.', 'Poradna')}
<div class="wrap" style="padding-bottom:clamp(48px,7vw,96px)"><div class="tiles big">{cards}</div></div>'''
    page(
        '/poradna/',
        'Poradna: jak vybrat postel z masivu',
        'Rady k výběru postele z masivu: výška pro seniory, nosnost, dřeviny. Od rodinného stolařství Kubiš.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [crumbs_ld([('Poradna', '/poradna/')])],
        },
    )
    for s, t, d, lead, sections, link in ARTICLES:
        sec = ''.join(f'<h2>{E(h)}</h2>{x}' for h, x in sections)
        body = f'''<section class="wrap page-intro">{crumbs(('Poradna', '/poradna/'), (t, None))}<h1>{E(t)}</h1><p class="lead">{E(lead)}</p></section>
<div class="wrap text-page"><article class="prose">{sec}<p><a class="link arrow" href="/{link}/">{E(CAT_BY_SLUG[link][2])}: modely a ceny</a></p></article>
<aside class="side-card"><h2>Poradíme osobně</h2><p>Zavolejte nebo přijeďte vyzkoušet postel a matraci na prodejnu v Němčičkách.</p><a class="btn btn-primary" href="tel:{TEL1H}">{TEL1}</a><a class="link" href="/poptavka/">Napsat poptávku</a></aside></div>'''
        ld = {
            "@context": "https://schema.org",
            "@graph": [
                crumbs_ld([('Poradna', '/poradna/'), (t, f'/poradna/{s}/')]),
                {
                    "@type": "Article",
                    "headline": t,
                    "description": d,
                    "inLanguage": "cs",
                    "author": {"@type": "Organization", "name": "Stolařství Kubiš"},
                    "dateModified": TODAY,
                },
            ],
        }
        page(f'/poradna/{s}/', t, d, body, jsonld=ld)


# ---------------------------------------------------------------- úvodní stránka


def pick_reviews(revs):
    want = ['konečně můžeme vstát', 'natálka', 'třetí postel']
    out = []
    for w in want:
        r = next((x for x in revs if w in ' '.join(x['lines']).lower()), None)
        if r:
            out.append(r)
    for r in revs:
        if len(out) >= 3:
            break
        if r not in out and sum(len(l) for l in r['lines']) > 60:
            out.append(r)
    return out[:3]


FEATURED = [
    'senior-postel-luneta',
    'dvouluzko-magda-2',
    'patrova-palanda-irena',
    'jednoluzko-lucie-zaoblene-rohy',
    'zasuvkova-komoda-kpc',
    'psaci-stul-robin-9670-kc',
    'dubovy-jidelni-stul-denisa-7200-kc',
    'rohovy-stolek-dekor-orech',
]


def build_home(revs):
    quotes = ''.join(
        f'<figure class="quote"><blockquote>{" ".join(E(l) for l in r["lines"][:4])}</blockquote><figcaption>Zákazník, {E(r["date"])}</figcaption></figure>'
        for r in pick_reviews(revs)
    )
    t = cat_tile
    seg = ''.join(
        [
            t(
                'postele-pro-seniory',
                'Zvýšená ložná plocha, ze které se snadno vstává. Matrace s tuhým okrajem.',
                '55 / 60 / 65 cm',
            ),
            t(
                'vysokozatezove-postele',
                'Tvrdé dřeviny, masiv 40 mm a pevné rošty. I prodloužené délky.',
                'až 500 kg',
            ),
            t(
                'postele-pro-handicapovane',
                'Vysoké ohrádky, posuvná dvířka a polohovací rošty pro děti i dospělé.',
                'na míru',
            ),
            t(
                'postele-na-miru',
                'Nadrozměrné, čalouněné a atypické. Podle nákresu nebo fotky.',
                'do 4 týdnů',
            ),
        ]
    )
    typ = ''.join(
        [
            t('jednoluzka', 'Klasika i pohovkové postele.'),
            t('dvouluzka', 'Od smrku po jádrový buk a dub.'),
            t('patrove-a-vysoke-postele', 'Palandy a postele se zásuvkami.'),
            t('dubove-postele', 'Masivní dub, 42 mm.'),
            t('komody-a-psaci-stoly', 'Komody a psací stoly na míru.'),
            t('matrace', 'K vyzkoušení na prodejně.'),
        ]
    )
    featured = ''.join(model_card(x) for x in FEATURED if x in PRODUCTS)

    def row(slug, text):
        n, w, h = COVERS[slug]
        return f'<li><a href="/{slug}/"><img src="/img/{n}.jpg" width="{w}" height="{h}" alt="" loading="lazy" decoding="async"><span><b>{E(CAT_BY_SLUG[slug][2])}</b><em>{E(text)}</em></span></a></li>'

    rows = ''.join(
        [
            row(
                'postele-pro-seniory',
                'Ložná plocha 55, 60 nebo 65 cm, aby se dalo snadno vstát. K tomu senior matrace s tuhým okrajem.',
            ),
            row(
                'vysokozatezove-postele',
                'Z buku, jasanu nebo dubu, nosnost 400 kg na lůžko, vybrané modely 500 kg. Délky 210 a 220 cm.',
            ),
            row(
                'postele-pro-handicapovane',
                'Vysoká ohrádka, posuvná dvířka, polohovací nebo motorový rošt. Pro děti i dospělé.',
            ),
            row(
                'postele-na-miru', 'Nestandardní rozměr, čalouněné čelo, podle nákresu nebo fotky.'
            ),
            row(
                'patrove-a-vysoke-postele',
                'Palandy a vysoké postele se zásuvkami. Palanda Irena je i pro dospělé.',
            ),
        ]
    )
    rows_n = ''.join(
        [
            row(
                'komody-a-psaci-stoly',
                'Zásuvkové komody, peřináče a psací stoly. Zásuvky na plnovýsuvech s tlumením.',
            ),
            row(
                'jidelni-stoly',
                'Dubové, bukové a borovicové stoly. Povrch olejem, který je vhodný i na potraviny.',
            ),
            row('bytove-doplnky', 'Odkládací a květinové stolky, věšákové stěny.'),
            row(
                'doplnky-k-postelim',
                'Úložné šuplíky, výsuvné přistýlky, noční stolky, zábrany a madla.',
            ),
        ]
    )
    rows_m = ''.join(
        [
            row(
                'matrace', 'Přes 20 typů od českých výrobců, od 3 340 Kč. K vyzkoušení na prodejně.'
            ),
            row(
                'rosty-a-toppery',
                'Pevné rošty do 500 kg, polohovací, motorové a lamelové. Toppery a chrániče.',
            ),
        ]
    )
    body = f'''<section class="hero"><div class="wrap">
  <div class="txt">
  <h1>Postele a nábytek z masivu, které sami vyrábíme v Němčičkách u Brna</h1>
  <p class="lead">Jsme rodinné stolařství od roku 1999. Vyrábíme postele pro seniory, pro těžší uživatele, s ohrádkou i na míru, k tomu komody, stoly a další nábytek z buku, jádrového buku a dubu. Prodáváme také matrace a rošty. Vše dovezeme a smontujeme.</p>
  <div class="ctas"><a class="btn btn-primary" href="/postele-z-masivu/">Postele</a><a class="btn btn-ghost" href="/nabytek-z-masivu/">Nábytek</a><a class="link" href="/poptavka/">Napsat poptávku</a></div></div>
  <figure><img src="/img/lanett-2.jpg" width="1400" height="1072" alt="Dvoulůžko Lanett z jádrového buku v ukázkové prodejně" fetchpriority="high"></figure>
</div></section>
<section class="sec"><div class="wrap list-wrap"><div><h2>Co vyrábíme a prodáváme</h2><p class="lead">Postele jsou naše hlavní práce, ale jsme zakázkové stolařství. Cokoli z masivu uděláme podle vašich rozměrů, nákresu nebo fotky.</p></div>
<div><h3 class="rows-h">Postele</h3><ul class="rows">{rows}</ul>
<h3 class="rows-h">Nábytek z masivu</h3><ul class="rows">{rows_n}</ul>
<h3 class="rows-h">Matrace a rošty</h3><ul class="rows">{rows_m}</ul></div></div></section>
<section class="sec paper"><div class="wrap"><div class="sec-head"><h2>Hotové modely a ceny</h2><a class="link arrow" href="/postele-z-masivu/">Celý katalog</a></div><div class="models">{featured}</div><p class="note-line">Ceny jsou podle ceníku. U postelí jsou bez roštu a matrace, pevný masivní rošt stojí od 1 260 Kč.</p></div></section>
<section class="sec"><div class="wrap list-wrap"><div><h2>Co u nás platí</h2></div>
<dl class="spec"><dt>Nosnost postelí</dt><dd>400 kg na lůžko bez příplatku, vybrané modely z buku a dubu 500 kg</dd>
<dt>Výška ložné plochy</dt><dd>55 cm klasická, 60 cm senior, 65 cm pro vyšší postavy (k povrchu matrace)</dd>
<dt>Materiál</dt><dd>masiv o tloušťce 40 mm, buk, jasan, dub, u dubových postelí 42 mm</dd>
<dt>Povrch</dt><dd>vodou ředitelné laky a mořidla, dub olejem</dd>
<dt>Záruka</dt><dd>5 let na typizované postele, u atypických a ostatního nábytku zpravidla 2 roky</dd>
<dt>Výroba</dt><dd>postel nebo nábytek na míru zhruba do 4 týdnů</dd>
<dt>Doprava</dt><dd>vlastním autem po ČR i SR, 14 Kč/km tam i zpět, nejméně 300 Kč. Montáž při dovozu zdarma.</dd></dl></div></section>
<section class="sec paper"><div class="wrap split"><img src="/img/lanett.jpg" width="1137" height="1400" alt="Postel Lanett z jádrového buku s šafránovým čalouněním" loading="lazy" style="aspect-ratio:4/4.6">
<div><h2>Lanett z jádrového buku</h2><p>Paní Vašková s dcerou chtěly dvoulůžko v barvách hluboké severské přírody a světlého šafránu. Takovou kombinaci jsme nikdy nedělali a váhali jsme. Když jsme postel složili, výsledek nás překvapil.</p><p>Jádrový buk má tmavé jádro a světlé okolní dřevo, takže je každý kus jiný. Podobně vznikla i dvoulůžka Martina.</p>
<div class="ctas"><a class="btn" href="/realizace-a-recenze/">Další realizace a recenze</a><a class="link" href="/galerie/">Fotogalerie</a></div></div></div></section>
<section class="sec"><div class="wrap list-wrap"><div><h2>Jak objednávka probíhá</h2></div>
<ol class="plain"><li><b>Poptávka.</b> Zavolejte nebo napište, doptáme se na rozměr, dřevinu a na to, kdo bude na posteli spát.</li><li><b>Nabídka.</b> Pošleme písemně popis, materiál, rozměry, cenu a termín. Po vašem souhlasu vystavíme zálohový list.</li><li><b>Výroba.</b> Postel na míru děláme obvykle do 4 týdnů.</li><li><b>Dovoz a montáž.</b> Přivezeme ji vlastním autem a na místě smontujeme.</li></ol></div></section>
<section class="sec paper"><div class="wrap list-wrap"><div><h2>Recenze zákazníků</h2><p><a class="link arrow" href="/realizace-a-recenze/">Všech {len(revs)} recenzí</a></p></div><div class="quotes">{quotes}</div></div></section>
<section class="sec"><div class="wrap split rev"><div><h2>Prodejna v Němčičkách</h2><p>Postele, nábytek a matrace od českých výrobců si můžete prohlédnout a vyzkoušet u nás v Němčičkách u Židlochovic. Návštěvu prosím domluvte předem telefonem.</p>
<dl class="hours"><dt>Po–Pá</dt><dd>15–20 h, po domluvě</dd><dt>So–Ne</dt><dd>9–20 h, po domluvě</dd><dt>Telefon</dt><dd><a class="link" href="tel:{TEL1H}">{TEL1}</a></dd></dl>
<div class="ctas"><a class="btn" href="/prodejna-nemcicky/">Mapa a adresa</a><a class="link" href="/matrace/">Matrace</a></div></div><img src="/img/prodejna-2.jpg" width="1400" height="1243" alt="Postele a matrace v ukázkové prodejně v Němčičkách" loading="lazy"></div></section>
{faq_html(HOME_FAQ, more=True)}
{form_html(title='Napište nám, co potřebujete', intro='Rozměr, dřevinu a pro koho postel bude. Ozveme se a pošleme nabídku.')}'''
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "FurnitureStore",
                "@id": SITE + "/#firma",
                "name": "Stolařství Kubiš",
                "url": SITE + "/",
                "description": "Rodinné stolařství z Němčiček u Brna vyrábějící nábytek z masivu na míru, hlavně postele: zvýšené postele pro seniory, vysokozátěžové postele s nosností až 500 kg, postele s ohrádkou pro handicapované.",
                "telephone": "+420604107577",
                "email": MAIL,
                "foundingDate": "1999",
                "founder": {"@type": "Person", "name": "Petr Kubiš"},
                "image": SITE + "/img/og.jpg",
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
            faq_ld(HOME_FAQ),
        ],
    }
    page(
        '/',
        'Postele a nábytek z masivu na míru od výrobce',
        'Rodinné stolařství z Němčiček u Brna. Postele pro seniory, s nosností až 500 kg a s ohrádkou, komody, stoly a matrace. Z buku a dubu na míru, doprava a montáž po celé ČR.',
        body,
        jsonld=ld,
        suffix=False,
        canonical=SITE + '/',
    )


# ---------------------------------------------------------------- statické soubory
CSS_ORDER = ['base.css', 'effects.css', 'rooms.css', 'home.css', 'catalog.css', 'info.css']


def write_static():
    (WEB / 'css').mkdir(exist_ok=True)
    (WEB / 'js').mkdir(exist_ok=True)
    css = ''.join(
        (ROOT / 'tools/css' / n).read_text(encoding='utf-8') + '\n'
        for n in CSS_ORDER
        if (ROOT / 'tools/css' / n).exists()
    )
    (WEB / 'css/site.css').write_text(css, encoding='utf-8')
    js = (
        (ROOT / 'tools/site.js').read_text(encoding='utf-8')
        + '\n'
        + (ROOT / 'tools/js/effects.js').read_text(encoding='utf-8')
    )
    (WEB / 'js/site.js').write_text(js, encoding='utf-8')
    (WEB / 'robots.txt').write_text(
        f'User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nAllow: /\nUser-agent: OAI-SearchBot\nAllow: /\nUser-agent: PerplexityBot\nAllow: /\nUser-agent: ClaudeBot\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n',
        encoding='utf-8',
    )
    urls = ''.join(
        f'<url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>' for u in dict.fromkeys(SITEMAP)
    )
    (WEB / 'sitemap.xml').write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n',
        encoding='utf-8',
    )
    llms = f'''# Stolařství Kubiš

> Rodinné stolařství z Němčiček u Židlochovic (Brno-venkov), které od roku 1999 vyrábí postele a další nábytek z masivu na míru (komody, stoly) a prodává matrace a rošty. Zvýšené postele pro seniory (55/60/65 cm), vysokozátěžové postele (400 kg, vybrané 500 kg), postele s ohrádkou pro handicapované, atypické postele. Záruka 5 let, doprava a montáž po ČR i SR.

## Hlavní stránky
- [Postele z masivu]({SITE}/postele-z-masivu/)
- [Postele pro seniory]({SITE}/postele-pro-seniory/)
- [Vysokozátěžové postele]({SITE}/vysokozatezove-postele/)
- [Postele s ohrádkou]({SITE}/postele-pro-handicapovane/)
- [Postele na míru]({SITE}/postele-na-miru/)
- [Matrace]({SITE}/matrace/)
- [Poradna]({SITE}/poradna/)
- [Prodejna v Němčičkách]({SITE}/prodejna-nemcicky/)
- [Kontakt]({SITE}/kontakt/)

## Kontakt
Němčičky 5, 664 66 Němčičky u Židlochovic. Tel. {TEL1}, {TEL2}. {MAIL}
'''
    (WEB / 'llms.txt').write_text(llms, encoding='utf-8')


OLD_V1 = {
    'zvysene-prodlouzene-vysokozatezove': 'vysokozatezove-postele',
    'postele-s-ohradkou': 'postele-pro-handicapovane',
    'atypicke-postele': 'postele-na-miru',
    'dubovy-nabytek': 'dubove-postele',
    'komody-skrinky-psaci-stoly': 'komody-a-psaci-stoly',
    'jidelni-a-konferencni-stoly': 'jidelni-stoly',
    'rosty': 'rosty-a-toppery',
    'toppery-a-chranice': 'rosty-a-toppery',
    'dekory-moreni': 'dreviny-a-povrchy',
    'dreviny': 'dreviny-a-povrchy',
    'prodejna': 'prodejna-nemcicky',
    'doprava': 'doprava-a-montaz',
    'reference': 'realizace-a-recenze',
}


def write_redirects():
    red = [
        'RewriteEngine On',
        'ErrorDocument 404 /404.html',
        '',
        '# https a www',
        'RewriteCond %{HTTPS} off [OR]',
        'RewriteCond %{HTTP_HOST} !^www\\. [NC]',
        'RewriteRule ^(.*)$ https://www.stolarstvikubis.cz/$1 [R=301,L]',
        '',
        '# staré adresy z Webnode -> nové stránky',
    ]
    m = {
        **{
            src: f'/{slug}/' for src, slug in OLD2CAT.items() if not src.startswith('/fotogalerie/')
        },
        '/home/': '/',
        '/poptavkovy-formular/': '/poptavka/',
        '/napiste-nam/': '/poptavka/',
        '/o-nas/': '/o-nas/',
        '/prodejna-nabytku-a-bytovych-doplnku/': '/prodejna-nemcicky/',
        '/doprava/': '/doprava-a-montaz/',
        '/obchodni-podminky-jak-poptavat-a-objednavat/': '/obchodni-podminky/',
        '/gdpr/': '/ochrana-osobnich-udaju/',
        '/kontakt/': '/kontakt/',
        '/reference/': '/realizace-a-recenze/',
        '/fotogalerie/dvouluzka/': '/dvouluzka/',
        '/fotogalerie/jednoluzka/': '/jednoluzka/',
        '/fotogalerie/patrove-palandy/': '/patrove-a-vysoke-postele/',
        '/fotogalerie/satni-skrine/': '/galerie/',
        '/fotogalerie/psaci-stoly/': '/komody-a-psaci-stoly/',
        '/fotogalerie/komody/': '/komody-a-psaci-stoly/',
    }
    m.pop('/postele-z-masivu/', None)  # nový rozcestník katalogu
    for old, new in sorted(m.items()):
        if old == new:
            continue
        red.append(
            f'RewriteRule ^{re.escape(old.strip("/")).replace(chr(92) + "-", "-").replace(chr(92) + "/", "/")}/?$ {new} [R=301,L,NE]'
        )
    for old, new in OLD_V1.items():
        red.append(f'RewriteRule ^{old}/?$ /{new}/ [R=301,L]')
    for old, new in SLUG_FIX.items():
        red.append(
            f'RewriteRule ^products/{re.escape(unquote(old))}/?$ /produkty/{new}/ [R=301,L,NE]'
        )
    article_pages = {
        '/ukazka-drevin/': '/dreviny-a-povrchy/',
        '/fotogalerie/psaci-stoly/': '/komody-a-psaci-stoly/',
        '/postele-pro-handicapovane/': '/postele-pro-handicapovane/',
        '/': '/novinky/',
    }
    for source, target in article_pages.items():
        source_page = PAGES[source] if source != '/' else DATA['home']
        for box in source_page['boxes']:
            if 'articles' in box['kind']:
                for article in box['items']:
                    old = urlsplit(article['url']).path.strip('/')
                    anchor = old.rsplit('/', 1)[-1]
                    red.append(f'RewriteRule ^{re.escape(old)}/?$ {target}#{anchor} [R=301,L,NE]')
    red += [
        'RewriteRule ^products/([^/]+)/?$ /produkty/$1/ [R=301,L]',
        'RewriteRule ^album/ /galerie/ [R=301,L]',
        'RewriteRule ^news/ /novinky/ [R=301,L]',
        'RewriteRule ^(sitemap|rss)/?$ /sitemap.xml [R=301,L]',
        '',
        '# cache a komprese',
        '<IfModule mod_expires.c>',
        'ExpiresActive On',
        'ExpiresByType image/jpeg "access plus 1 year"',
        'ExpiresByType image/png "access plus 1 year"',
        'ExpiresByType font/woff2 "access plus 1 year"',
        'ExpiresByType text/css "access plus 1 week"',
        'ExpiresByType application/javascript "access plus 1 week"',
        '</IfModule>',
        '<IfModule mod_deflate.c>',
        'AddOutputFilterByType DEFLATE text/html text/css application/javascript image/svg+xml application/json text/plain',
        '</IfModule>',
    ]
    (WEB / '.htaccess').write_text('\n'.join(red) + '\n', encoding='utf-8')


TITLE_COUNT = {}


def clean_web():
    keep = {'media', 'img', 'fonts', 'fonts.css', 'favicon.svg', 'apple-touch-icon.png'}
    for p in WEB.iterdir():
        if p.name in keep:
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()


def main():
    clean_web()
    TITLE_COUNT.clear()
    for _s, _p in PRODUCTS.items():
        TITLE_COUNT[prod_title(_p).lower()] = TITLE_COUNT.get(prod_title(_p).lower(), 0) + 1
    for s in PRODUCTS:
        build_product(s)
    for c in CATS:
        build_category(c)
    build_hub_postele()
    build_hub_nabytek()
    for text_page in TEXT_PAGES:
        build_text(*text_page)
    build_gdpr()
    revs = build_reviews()
    build_news()
    build_gallery()
    build_inquiry()
    build_poradna()
    build_faq_page()
    build_404()
    build_home(revs)
    write_static()
    write_redirects()
    print(
        'produkty',
        len(PRODUCTS),
        'kategorie',
        len(CATS),
        'stránek v sitemap',
        len(set(SITEMAP)),
        'recenzí',
        len(revs),
    )


if __name__ == '__main__':
    main()
