"""Informační stránky webu v4 (design „Dílna ve dne“): kontakt, textové stránky, recenze, novinky, galerie,
poptávka, 404, časté dotazy, poradna. Přepisuje funkce z build.py přiřazením na modul B (viz make.py).
Styly: tools/css/info.css. Texty ze starého webu zůstávají beze změny, jen se přehledně uspořádají.
"""

import re, traceback
import build as B

E = B.E
TEL1, TEL1H, TEL2, TEL2H, MAIL = B.TEL1, B.TEL1H, B.TEL2, B.TEL2H, B.MAIL


def override(name):
    """Nahradí funkci B.<name>; při chybě v nové verzi použije původní z build.py."""
    orig = getattr(B, name)

    def deco(fn):
        def wrapper(*a, **k):
            try:
                return fn(*a, **k)
            except Exception:
                print(f'!! pages_info.{name} selhala, použita výchozí verze', flush=True)
                traceback.print_exc()
                return orig(*a, **k)

        setattr(B, name, wrapper)
        return fn

    return deco


# ---------------------------------------------------------------- drobné součástky
def img(name, w, h, alt, lazy=True, cls=''):
    return (
        f'<img src="/img/{name}.jpg" width="{w}" height="{h}" alt="{E(alt)}"'
        f'{" loading=\"lazy\" decoding=\"async\"" if lazy else " fetchpriority=\"high\""}{f" class=\"{cls}\"" if cls else ""}>'
    )


IMGS = {
    'prodejna-1': (1400, 1050, 'Ukázková prodejna v Němčičkách s postelí a cihlovou zdí'),
    'prodejna-2': (1400, 1243, 'Postele a matrace v ukázkové prodejně v Němčičkách'),
    'prodejna-3': (1050, 1400, 'Postel s laťkovým čelem v ukázkové prodejně'),
    'detail-buk': (1400, 1050, 'Detail nohy postele z jádrového buku s výraznou kresbou'),
}


def photo(name, ratio='r32', cap='', lazy=True, alt=None, fx='', tilt=''):
    """Fotka v dřevěném rámu (.frame z rooms.css); tilt = 'l' nebo 'r' pro mírný náklon na desktopu."""
    w, h, a = IMGS[name]
    cls = 'frame i-fig' + (f' i-tilt-{tilt}' if tilt else '')
    return (
        f'<figure class="{cls}"{f" data-fx=\"{fx}\"" if fx else ""}><span class="ph {ratio}">{img(name, w, h, alt if alt is not None else a, lazy)}</span>'
        f'{f"<figcaption>{E(cap)}</figcaption>" if cap else ""}</figure>'
    )


def tel_link(h, n, cls=''):
    return f'<a{f" class=\"{cls}\"" if cls else ""} href="tel:{h}">{n}</a>'


def map_link(cls='btn btn-2', text='Mapa a trasa'):
    return f'<a class="{cls}" href="{B.MAP_NEMCICKY}" target="_blank" rel="noopener">{text}</a>'


def hours_table(caption='Otevírací doba', times=('15–20 h', '9–20 h')):
    # POZOR: časy a „po domluvě“ pocházejí ze starého webu; před spuštěním potvrdit s majiteli.
    return (
        f'<table class="i-table i-hours"><caption>{E(caption)}</caption><tbody>'
        f'<tr><th scope="row">Po–Pá</th><td>{times[0]}</td></tr>'
        f'<tr><th scope="row">So–Ne</th><td>{times[1]}</td></tr></tbody></table>'
    )


def form_only(model=''):
    """Poptávkový formulář bez tmavého obalu (stejné pole, name atributy, data-inquiry a FormSubmit jako v build.form_html)."""
    h = B.form_html(model=model)
    m = re.search(r'<form.*?</form>', h, re.S)
    if not m:
        raise RuntimeError('formulář nenalezen v B.form_html')
    return m.group(0)


def side_card(title='Kontakt', hours=True, toc=None, extra=''):
    tocs = ''
    if toc:
        tocs = (
            '<nav aria-label="Obsah stránky" class="i-toc"><h2>Na stránce</h2><ul>'
            + ''.join(f'<li><a href="#{a}">{E(t)}</a></li>' for a, t in toc)
            + '</ul></nav>'
        )
    return (
        f'<aside class="side-card">{tocs}<h2>{E(title)}</h2>'
        f'<p><strong>STOLAŘSTVÍ Petr Kubiš</strong><br>Němčičky 5, 664 66 Němčičky u Židlochovic<br>IČO 69752460</p>'
        f'<p>Prodej a matrace: {tel_link(TEL1H, TEL1)}<br>Výroba a projekty: {tel_link(TEL2H, TEL2)}<br><a href="mailto:{MAIL}">{MAIL}</a></p>'
        f'{"<p>Po–Pá 15–20 h, So–Ne 9–20 h, vždy po domluvě předem.</p>" if hours else ""}{extra}'
        f'<a class="btn btn-primary" href="/poptavka/">Napsat poptávku</a></aside>'
    )


def text_blocks(src):
    box = B.PAGES[src]['boxes'][0]
    out = [(b['t'], b['text'].strip()) for b in box['blocks'] if b['t'] != 'img']
    return out[1:]  # bez nadpisu boxu; indexy odpovídají pořadí odstavců na starém webu


def P(text):
    return f'<p>{B.linkify(text)}</p>'


def sentences(t):
    return re.split(r'(?<=[.)]) (?=[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])', t)


def ld_crumbs(menu, slug):
    return {"@context": "https://schema.org", "@graph": [B.crumbs_ld([(menu, f'/{slug}/')])]}


def room(inner, wall='paper', cls='', attrs=''):
    """Sekce = místnost se stěnou a podlahovou lištou."""
    return f'<section class="room wall-{wall}{f" {cls}" if cls else ""}"{attrs}>{inner}</section>'


def head(plate, menu, title, lead='', wall='stone', crumb=None, extra=''):
    """Hlavička stránky: vycentrovaná, na stěně, nad nadpisem mosazná cedulka s názvem místnosti."""
    c = crumb or B.crumbs((menu, None))
    return (
        f'<section class="room i-head wall-{wall}"><div class="wrap">{c}<span class="plate">{E(plate)}</span>'
        f'<h1>{E(title)}</h1>{f"<p class=\"lead\">{lead}</p>" if lead else ""}{extra}</div></section>'
    )


def faq_room(items, heading, wall='sky', more=False):
    """Časté dotazy jako místnost s accordionem (bez JS všechny odpovědi vidět v details)."""
    det = ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in items)
    mo = (
        '<p class="i-faq-more"><a class="link arrow" href="/caste-dotazy/">Všechny časté dotazy</a></p>'
        if more
        else ''
    )
    return room(
        f'<div class="wrap i-faqbox"><h2>{E(heading)}</h2><div class="faq" data-fx="accordion">{det}</div>{mo}</div>',
        wall,
    )


# ---------------------------------------------------------------- kontakt
@override('build_contact')
def build_contact():
    # Otevírací doba: Po–Pá 15–20 h, So–Ne 9–20 h vždy po domluvě (ze starého webu). Časy potvrdit s majiteli.
    body = f'''{head('Vchod', 'Kontakt', 'Kontakt', 'Zavolejte kvůli výběru postele, návštěvě prodejny nebo zakázce na míru. Telefon zvedá přímo rodina, návštěvu prosíme domluvit předem.', wall='clay')}
{room(f"""<div class="wrap">
  <div class="i-phones">
    <div class="i-phone"><h2 class="c-label">Prodej, matrace, návštěvy</h2><a class="c-tel" href="tel:{TEL1H}">{TEL1}</a></div>
    <div class="i-phone"><h2 class="c-label">Výroba a projekty</h2><a class="c-tel" href="tel:{TEL2H}">{TEL2}</a></div>
  </div>
  <div class="c-cols i-cinfo">
    <div class="c-info">
      <div class="c-block"><h2 class="c-label">E-mail</h2><a class="c-mail" href="mailto:{MAIL}">{MAIL}</a></div>
      <div class="c-block">{hours_table()}<p class="small">Vždy po předchozí domluvě telefonem. V jinou dobu se také domluvíme.</p></div>
      <div class="c-block"><h2 class="c-label">Adresa</h2><address>STOLAŘSTVÍ Petr Kubiš<br>Němčičky 5, 664 66 Němčičky u Židlochovic<br>IČO 69752460</address>
        <div class="ctas">{map_link()}<a class="link" href="/prodejna-nemcicky/">O prodejně</a></div></div>
    </div>
    <div class="i-formpanel" id="napiste"><h2>Napište, co potřebujete</h2><p class="lead">Rozměr, dřevinu a pro koho postel bude. Ozveme se a pošleme nabídku.</p>{form_only()}</div>
  </div>
</div>""", 'paper')}
{room(f"""<div class="wrap i-split">
  {photo('prodejna-1', 'r32', 'Prodejna a dílna v Němčičkách', lazy=True, fx='reveal', tilt='l')}
  <div><h2>Pojďte dál</h2><p>Postele a matrace si můžete prohlédnout a vyzkoušet přímo v Němčičkách. Návštěvu prosíme domluvit předem telefonem.</p><a class="doormat" href="/prodejna-nemcicky/">O prodejně</a></div>
</div>""", 'sage')}'''
    B.page(
        '/kontakt/',
        'Kontakt',
        'Telefon, e-mail, otevírací doba a adresa dílny a prodejny Stolařství Kubiš v Němčičkách u Židlochovic. Poptávkový formulář.',
        body,
        jsonld=ld_crumbs('Kontakt', 'kontakt'),
    )


# ---------------------------------------------------------------- textové stránky
def page_onas():
    t = text_blocks('/o-nas/')
    txt = {i: x[1] for i, x in enumerate(t)}  # 0 = první odstavec po nadpisu
    s = sentences(txt[2])
    if len(s) >= 4:
        para3 = (
            P(' '.join(s[:2]))
            + '<p>'
            + B.linkify(s[2]).replace(
                '"Ukázka dřevin"', '„<a href="/dreviny-a-povrchy/">Ukázka dřevin</a>“'
            )
            + ' '
            + B.linkify(s[3])
            + '</p>'
        )
    else:
        para3 = P(txt[2])
    main = f'''{photo('detail-buk', 'r32', 'Detail nohy postele z jádrového buku, výrazná kresba jádrového dřeva', lazy=False, tilt='r')}
<div class="i-prose">
<h2 id="od-1999">Od roku 1999</h2>{P(txt[0])}{P(txt[1])}
<h2 id="vyroba">Co a z čeho vyrábíme</h2>{para3}
<h2 id="prodejna">Prodejna od jara 2013</h2>{P(txt[3])}
<p class="i-sign">{E(txt[4])}<br><strong>{E(txt[5])}</strong></p>
</div>
<dl class="spec i-kostce"><dt>Založeno</dt><dd>1999, jako truhlářství se zaměřením na výrobu nábytku</dd><dt>První výrobky</dt><dd>patrové palandy a vestavná patra</dd><dt>Materiál</dt><dd>přírodní masivní dřevo</dd><dt>Ukázková prodejna</dt><dd>od jara 2013, Němčičky 5</dd></dl>'''
    after = room(
        f'''<div class="wrap i-split">
  <div><h2>Přijeďte se podívat</h2><p>Postele, nábytek a matrace od českých výrobců si můžete prohlédnout a vyzkoušet přímo v Němčičkách. Návštěvu prosím domluvte předem telefonem na {tel_link(TEL1H, TEL1)}.</p><div class="ctas"><a class="btn" href="/prodejna-nemcicky/">Prodejna v Němčičkách</a>{map_link()}</div></div>
  {photo('prodejna-2', 'r54', 'Ukázková prodejna v Němčičkách', tilt='l')}
</div>''',
        'sage',
    )
    return (
        main,
        side_card(
            toc=[
                ('od-1999', 'Od roku 1999'),
                ('vyroba', 'Co a z čeho vyrábíme'),
                ('prodejna', 'Prodejna od jara 2013'),
            ]
        ),
        after,
    )


def page_prodejna():
    t = text_blocks('/prodejna-nabytku-a-bytovych-doplnku/')
    txt = {i: x[1] for i, x in enumerate(t)}
    # t[2] = „Prodejní doba:“, t[3], t[4] řádky s časy, t[5] věta o jiné době, t[6] telefony
    main = f'''{photo('prodejna-1', 'r32', 'Ukázková prodejna v Němčičkách s postelí a cihlovou zdí', lazy=False, tilt='r')}
<div class="i-prose">
<h2 id="vystava">Co je na prodejně vystavené</h2>{P(txt[0])}
<h2 id="zakazky">Zakázky a matrace</h2>{P(txt[1])}
<h2 id="doba">Prodejní doba</h2>
<table class="i-table i-hours i-wide"><tbody><tr><th scope="row">Po–Pá</th><td>15:00–20:00</td><td>pouze po domluvě předem</td></tr><tr><th scope="row">So–Ne</th><td>9:00–20:00</td><td>pouze po domluvě předem</td></tr></tbody></table>
{P(txt[5])}
<h2 id="kontakt">Telefon a e-mail</h2><p>Domluvte návštěvu na {tel_link(TEL1H, TEL1)} nebo {tel_link(TEL2H, TEL2)}, případně napište na <a href="mailto:{MAIL}">{MAIL}</a>.</p>
<div class="ctas">{map_link('btn')}<a class="btn btn-2" href="/poptavka/">Napsat poptávku</a></div>
</div>'''
    side = (
        f'<aside class="side-card"><h2>Adresa</h2><p><strong>STOLAŘSTVÍ Petr Kubiš</strong><br>Němčičky 5, 664 66 Němčičky u Židlochovic<br>IČO 69752460</p>'
        f'{hours_table("Prodejní doba", ("15–20 h", "9–20 h"))}<p>Vždy po domluvě předem na {tel_link(TEL1H, TEL1)}.</p>{map_link("btn")}</aside>'
    )
    after = room(
        f'''<div class="wrap i-pair">{photo('prodejna-2', 'r54', 'Postele a matrace v ukázkové prodejně', tilt='l')}{photo('prodejna-3', 'r45', 'Postel s laťkovým čelem na prodejně', tilt='r')}</div>''',
        'sage',
    )
    return main, side, after


def page_doprava():
    t = text_blocks('/doprava/')
    txt = {i: x[1] for i, x in enumerate(t)}
    vynos = re.sub(r'^Výnos:\s*', '', txt[1])
    rows = [
        (
            'Doprava naším autem',
            '14 Kč za km',
            'tam i zpět, po celé ČR i SR. Při větších vzdálenostech se cena dopravného může snížit.',
        ),
        (
            'Nejnižší cena dopravy',
            '300 Kč',
            'u kratších vzdáleností je cena fixní, nejméně 300 Kč za výjezd.',
        ),
        ('Odborná montáž', 'zdarma', 'při dovozu naším autem, se zárukou 5 let.'),
        (
            'Výnos do patra nebo z auta do domu',
            'příplatek',
            'cenu nabídneme podle obtížnosti na poptávku. Je nutné uvést předem u objednávky.',
        ),
        ('Osobní odběr', 'po domluvě', 'Němčičky č. 5, Brno-venkov, kdykoli po domluvě předem.'),
        ('Přepravní služby', 'nepoužíváme', 'vozíme jen vlastním autem.'),
    ]
    trs = ''.join(
        f'<tr><th scope="row">{E(a)}</th><td class="v">{E(b)}</td><td>{E(c)}</td></tr>'
        for a, b, c in rows
    )
    main = f'''<table class="i-table i-prices"><caption>Kolik doprava a montáž stojí</caption><thead><tr><th scope="col">Služba</th><th scope="col">Cena</th><th scope="col">Podmínky</th></tr></thead><tbody>{trs}</tbody></table>
<div class="i-prose">
<h2 id="doprava">Doprava</h2>{P(txt[0])}
<h2 id="vynos">Výnos</h2>{P(vynos)}
<h2 id="odber">Přepravní služby a osobní odběr</h2>{P(txt[2])}{P(txt[3])}
</div>'''
    faq = next(items for g, items in B.FAQ_GROUPS if g == 'Doprava a montáž')
    after = faq_room(faq, 'Časté dotazy k dopravě') + B.cta_band(
        title='Kolik bude doprava k vám?',
        text='Napište obec nebo PSČ. Cenu a termín pošleme v nabídce.',
    )
    return (
        main,
        side_card(
            toc=[('doprava', 'Doprava'), ('vynos', 'Výnos'), ('odber', 'Osobní odběr')], hours=False
        ),
        after,
    )


def page_op():
    t = text_blocks('/obchodni-podminky-jak-poptavat-a-objednavat/')
    x = {
        i: v[1] for i, v in enumerate(t)
    }  # x[0] = „Jsme zakázkové stolařství…“ (nadpis h0 je mimo seznam)

    def num(s):
        return re.sub(r'^\d\.\s*', '', s)

    step1 = E(num(x[2])).replace('604107577', tel_link(TEL1H, TEL1))

    def term(s):
        a, sep, b = s.partition(' - ')
        if not sep:
            a, par, b = s.partition(' (')
            return f'<li><strong>{E(a)}</strong>{(" (" + E(b)) if par else ""}</li>'
        return f'<li><strong>{E(a)}</strong> – {E(b)}</li>'

    left = ''.join(term(x[i]) for i in (7, 8, 9, 10, 11, 12))
    right = ''.join(term(x[i]) for i in (14, 15, 16))
    main = f'''<div class="i-prose"><p class="i-lead">{E(x[0])}</p></div>
<dl class="spec i-kostce"><dt>Záruka</dt><dd>5 let na typizované postele z orientačního ceníku, zpravidla 2 roky na atypické a luxusní postele, vysoké ohrádky a skříňový nábytek</dd><dt>Platba</dt><dd>hotově při předání nebo na účet, zpravidla nejméně 3 dny před dodáním. Kartou platit nelze.</dd><dt>Odstoupení</dt><dd>u standardních neatypických postelí kdykoli, i při předání, bez pokut</dd><dt>Montáž</dt><dd>při našem dovozu bezplatná</dd></dl>
<div class="i-prose">
<h2 id="postup">{E(x[1].rstrip(':'))}</h2></div>
<ol class="i-steps">
<li>{step1}</li>
<li>{E(num(x[3]))}</li>
<li>{E(num(x[5]))}<div class="i-note i-doc"><h3>Co je na potvrzení objednávky</h3><div class="i-doc-cols"><div><h4>Záhlaví vlevo</h4><ul>{left}</ul></div><div><h4>Záhlaví vpravo</h4><ul>{right}</ul></div></div></div></li>
</ol>
<div class="i-prose">
<p class="i-note"><strong>Termín výroby.</strong> {E(x[4])}</p>
<h2 id="dokonceni">{E(x[17])}</h2>{P(x[18])}{P(x[19])}{P(x[20])}<p><strong>{E(x[21])}</strong></p>
<h2 id="platba">{E(x[22])}</h2>{P(x[23])}
<h3>Odstoupení od zakázky</h3>{P(x[24])}
<h2 id="zaruka">{E(x[25])}</h2>{P(x[26])}{P(x[27])}
</div>'''
    toc = [
        ('postup', 'Jak poptávat a objednávat'),
        ('dokonceni', 'Dokončení výroby'),
        ('platba', 'Platba a odstoupení'),
        ('zaruka', 'Záruka'),
    ]
    return (
        main,
        side_card(toc=toc, hours=False),
        B.cta_band(
            title='Máte k podmínkám dotaz?', text='Zavolejte nebo napište, rádi vysvětlíme.'
        ),
    )


TEXT_PAGES_FN = {
    'o-nas': page_onas,
    'prodejna-nemcicky': page_prodejna,
    'doprava-a-montaz': page_doprava,
    'obchodni-podminky': page_op,
}


@override('build_text')
def build_text(slug, menu, h1, src):
    if slug == 'kontakt':
        B.build_contact()
        return
    main, side, after = TEXT_PAGES_FN[slug]()
    lead, _ = B.TEXT_COPY[slug]
    plate = 'Prodejna' if slug == 'prodejna-nemcicky' else 'Dílna'
    wall = 'clay' if slug == 'prodejna-nemcicky' else 'stone'
    body = f'''{head(plate, menu, h1, lead, wall)}
{room(f'<div class="wrap text-page i-text"><div class="i-main">{main}</div>{side}</div>', 'paper', 'i-body')}
{after}'''
    ttl, desc = B.TEXT_TITLES[slug]
    B.page(f'/{slug}/', ttl, desc, body, jsonld=ld_crumbs(menu, slug))


@override('build_gdpr')
def build_gdpr():
    title = 'Ochrana osobních údajů'
    body = f'''{head('Dílna', title, title, 'Jak zacházíme s údaji, které nám pošlete v poptávce nebo objednávce. Platí od 19. 11. 2026.')}
<section class="room wall-paper i-body"><div class="wrap text-page i-text"><div class="i-prose i-main">
<h2 id="spravce">Kdo je správce</h2><p>STOLAŘSTVÍ Petr Kubiš, IČO 69752460, Němčičky 5, 664 66 Němčičky u Židlochovic. Kontakt: <a href="mailto:{MAIL}">{MAIL}</a>, tel. <a href="tel:{TEL1H}">{TEL1}</a>.</p>
<h2 id="udaje">Jaké údaje zpracováváme</h2><p>Jméno a příjmení, telefon, e-mail, adresu dodání a to, co nám o své zakázce napíšete (rozměry, požadavky, případně fotky nebo nákresy).</p>
<h2 id="proc">Proč a na jakém základě</h2><ul>
<li>Abychom mohli odpovědět na poptávku, připravit nabídku a vyrobit a dodat objednaný nábytek (plnění smlouvy a jednání o ní, čl. 6 odst. 1 písm. b) GDPR).</li>
<li>Abychom splnili účetní a daňové povinnosti (právní povinnost, čl. 6 odst. 1 písm. c) GDPR).</li>
<li>Abychom mohli vyřídit záruku a reklamaci a evidovat zakázky (oprávněný zájem, čl. 6 odst. 1 písm. f) GDPR).</li></ul>
<p>Obchodní sdělení vám bez vašeho souhlasu neposíláme.</p>
<h2 id="jak-dlouho">Jak dlouho</h2><p>Poptávky, ze kterých nevznikla objednávka, mažeme nejpozději po jednom roce. Údaje k zakázkám uchováváme po dobu záruky a dále po dobu, kterou ukládají účetní a daňové předpisy (u daňových dokladů až 10 let).</p>
<h2 id="predani">Komu údaje předáváme</h2><p>Nikomu je neprodáváme. Nábytek vozíme vlastním autem, přepravní služby nepoužíváme. Poptávkový formulář na webu doručuje zprávu e-mailem přes službu FormSubmit (formsubmit.co); dále se údaje mohou nacházet u poskytovatele e-mailu a webhostingu. Jinak je předáváme jen tehdy, když to ukládá zákon.</p>
<h2 id="cookies">Cookies</h2><p>Web nepoužívá analytické ani reklamní cookies a nesleduje vás. Písma i skripty načítáme z našeho serveru, ne od třetích stran.</p>
<h2 id="prava">Vaše práva</h2><p>Máte právo na přístup ke svým údajům, jejich opravu, výmaz, omezení zpracování, přenositelnost a právo vznést námitku. Stačí napsat na <a href="mailto:{MAIL}">{MAIL}</a>. Pokud si myslíte, že s údaji zacházíme špatně, můžete podat stížnost u Úřadu pro ochranu osobních údajů (<a href="https://uoou.gov.cz" target="_blank" rel="noopener">uoou.gov.cz</a>).</p>
</div>
<aside class="side-card"><nav aria-label="Obsah stránky" class="i-toc"><h2>Na stránce</h2><ul><li><a href="#spravce">Kdo je správce</a></li><li><a href="#udaje">Jaké údaje zpracováváme</a></li><li><a href="#proc">Proč a na jakém základě</a></li><li><a href="#jak-dlouho">Jak dlouho</a></li><li><a href="#predani">Komu údaje předáváme</a></li><li><a href="#cookies">Cookies</a></li><li><a href="#prava">Vaše práva</a></li></ul></nav>
<h2>Dotaz k osobním údajům</h2><p><a href="mailto:{MAIL}">{MAIL}</a><br>{tel_link(TEL1H, TEL1)}</p></aside></div></section>'''
    B.page(
        '/ochrana-osobnich-udaju/',
        title,
        'Jak Stolařství Kubiš zpracovává osobní údaje z poptávek a objednávek.',
        body,
    )


# ---------------------------------------------------------------- fotky pro galerie
def _excluded():
    """Čísla (prvních 9 číslic) fotek vyřazených v research/photo-picks.md, oddíl 6 (lidé, děti, otočené, špatné)."""
    try:
        txt = (B.ROOT / 'research/photo-picks.md').read_text(encoding='utf-8')
        sec = txt.split('## 6.')[1].split('## 7.')[0].split('Další upozornění')[0]
    except Exception:
        return set()
    out = {int(m) for m in re.findall(r'\b(\d{9})\b', sec)}
    for a, b in re.findall(r'(\d{9})–(\d{9})', sec):
        out.update(range(int(a), int(b) + 1))
    for base, tail in re.findall(r'(\d{9})((?:,\s*\d{3}\b)+)', sec):
        for d in re.findall(r'\d{3}', tail):
            out.add(int(base[:6] + d))
    return out


EXCL = _excluded()


def photo_ids(photos):
    seen, out = set(), []
    for ph in photos:
        i = B.mid(ph['src'])
        if not i or i in seen or int(i[:9]) in EXCL:
            continue
        seen.add(i)
        out.append((i, ph))
    return out


def thumb(i, ph, group, alt):
    w, h = B.media_size(i, 's')
    cut = i in B.CUT
    cap = (ph.get('caption') or '').strip()
    return (
        f'<a class="ph{" cut" if cut else ""}" href="{B.media_src(i, "l")}" data-lb="{group}" data-cap="{E(cap or alt)}">'
        f'<img src="{B.media_src(i, "s")}" width="{w}" height="{h}" alt="{E(cap or alt)}" loading="lazy" decoding="async"></a>'
    )


def scroller(items, group, alt, label):
    return (
        f'<div class="i-scroll" data-fx="scroller" data-fx-label="{E(label)}">'
        + ''.join(thumb(i, ph, group, alt) for i, ph in items)
        + '</div>'
    )


def grid_more(items, group, alt, first=12):
    a, b = items[:first], items[first:]
    g = '<div class="i-grid">' + ''.join(thumb(i, ph, group, alt) for i, ph in a) + '</div>'
    if b:
        g += (
            f'<details class="i-more"><summary><span class="o">Zobrazit dalších {len(b)} fotografií</span><span class="c">Skrýt dalších {len(b)} fotografií</span></summary>'
            f'<div class="i-grid">'
            + ''.join(thumb(i, ph, group, alt) for i, ph in b)
            + '</div></details>'
        )
    return g


def album_view(items, group, alt, label):
    return scroller(items, group, alt, label) if len(items) <= 36 else grid_more(items, group, alt)


# ---------------------------------------------------------------- recenze a realizace
@override('build_reviews')
def build_reviews():
    revs = B.parse_reviews()
    feat = next((r for r in revs if 'natálk' in ' '.join(r['lines']).lower()), revs[0])
    fig = []
    for r in revs:
        d = B.datetime.datetime.strptime(r['date'], '%d.%m.%Y').date()
        status = '<span class="ok">Spokojený</span>' if r['ok'] else ''
        quote = ''.join(f'<p>{B.linkify(l)}</p>' for l in r['lines'])
        fig.append(
            (
                r,
                f'<figure class="review"><figcaption><time datetime="{d.isoformat()}">{E(r["date"])}</time>{status}</figcaption><blockquote>{quote}</blockquote></figure>',
            )
        )
    others = ''.join(h for r, h in fig if r is not feat)
    fl = feat['lines']
    sign = fl[-1] if len(fl) > 2 else ''
    big_text = fl[:-1] if sign else fl
    big = f'<figure class="i-big" data-fx="reveal"><blockquote><p class="i-big-q">{B.linkify(big_text[0])}</p>{"".join(f"<p>{B.linkify(l)}</p>" for l in big_text[1:])}</blockquote><figcaption>{E(sign)}{", " if sign else ""}<time datetime="{B.datetime.datetime.strptime(feat['date'], '%d.%m.%Y').date().isoformat()}">{E(feat["date"])}</time></figcaption></figure>'
    ref = next(b for b in B.PAGES['/reference/']['boxes'] if 'photogallery' in b['kind'])
    items = photo_ids(ref['photos'])
    gal = album_view(
        items,
        'ref',
        'Realizace postele nebo nábytku u zákazníka',
        'Fotografie realizací, posouvejte do stran',
    )
    body = f'''{head('Dílna', 'Realizace a recenze', 'Realizace a recenze zákazníků', 'Recenze od zákazníků z celé republiky od roku 2013. Píšou je sami zákazníci a my na nich nic neupravujeme.', extra='<nav class="i-jumpbar" aria-label="Obsah stránky"><a href="#recenze">Recenze zákazníků</a><a href="#realizace">Fotografie realizací</a></nav>')}
{room(f'<div class="wrap"><h2 id="h-rec" class="i-sr">Recenze zákazníků</h2>{big}</div>', 'butter', '', ' id="recenze" aria-labelledby="h-rec"')}
{room(f'<div class="wrap"><div class="reviews i-notes">{others}</div></div>', 'sage', '', ' aria-label="Další recenze"')}
{room(f'<div class="wrap"><div class="sec-head"><h2 id="h-real">Fotografie realizací</h2><a class="link arrow" href="/galerie/">Celá fotogalerie</a></div>{gal}</div>', 'sky', '', ' id="realizace" aria-labelledby="h-real"')}
<section class="band cta-band"><div class="wrap"><div><h2>Byli jste u nás spokojeni?</h2><p style="margin-top:10px">Napište pár řádků, rádi je přidáme mezi ostatní.</p></div><div class="ctas"><a class="btn" href="mailto:{MAIL}?subject=Recenze">Napsat recenzi</a></div></div></section>'''
    B.page(
        '/realizace-a-recenze/',
        'Realizace a recenze zákazníků',
        f'{len(revs)} recenzí zákazníků Stolařství Kubiš od roku 2013 a fotografie realizací postelí z masivu.',
        body,
    )
    return revs


# ---------------------------------------------------------------- novinky
@override('build_news')
def build_news():
    boxes = B.DATA['home']['boxes']
    rev_box = max(range(len(boxes)), key=lambda i: len(boxes[i].get('blocks', [])))
    live, old = [], []
    for i, b in enumerate(boxes):
        if i == rev_box or i in B.SKIP_HOME or 'articles' in b['kind']:
            continue
        h = B.render_box(b, f'n{i}')
        if not h:
            continue
        (old if i in B.EXPIRED else live).append(f'<div class="news-item i-news">{h}</div>')
    for b in [b for b in boxes if 'articles' in b['kind']]:
        live.append(B.render_box(b, 'na'))
    old_html = (
        (
            room(
                f'<div class="wrap"><h2 style="margin-bottom:var(--s4)">Skončené akce</h2><p class="lead" style="margin-bottom:var(--s5)">Tyto nabídky už neplatí, nechali jsme je tu pro přehled. Aktuální ceny najdete v katalogu nebo v písemné nabídce.</p><div class="entries">{"".join(old)}</div></div>',
                'stone',
                '',
                ' id="skoncene"',
            )
        )
        if old
        else ''
    )
    body = f'''{head('Dílna', 'Novinky', 'Novinky z dílny', 'Nové modely, kusy skladem a co se u nás děje. Aktuality sdílíme i na <a class="link" href="https://www.facebook.com/stolarstvikubis/" target="_blank" rel="noopener">Facebooku</a>.')}
{room(f'<div class="wrap"><div class="entries i-newslist">{"".join(live)}</div></div>', 'paper')}
{old_html}
{B.cta_band(title='Hledáte konkrétní kus?', text='Zavolejte, řekneme, co máme skladem a co vyrobíme na míru.')}'''
    B.page(
        '/novinky/',
        'Novinky',
        'Novinky ze Stolařství Kubiš: nové modely postelí, matrace a kusy skladem.',
        body,
    )


# ---------------------------------------------------------------- galerie
@override('build_gallery')
def build_gallery():
    sources = [
        ('Dvoulůžka', '/fotogalerie/dvouluzka/', '/dvouluzka/'),
        ('Jednolůžka', '/fotogalerie/jednoluzka/', '/jednoluzka/'),
        (
            'Vysoké postele s úložnými prostory',
            '/vysoke-postele-s-velkymi-prostory/',
            '/patrove-a-vysoke-postele/',
        ),
        ('Patrové palandy', '/fotogalerie/patrove-palandy/', '/patrove-a-vysoke-postele/'),
        ('Postele s ohrádkou', '/postele-pro-handicapovane/', '/postele-pro-handicapovane/'),
        ('Komody', '/fotogalerie/komody/', '/komody-a-psaci-stoly/'),
        ('Psací stoly', '/fotogalerie/psaci-stoly/', '/komody-a-psaci-stoly/'),
        ('Šatní skříně', '/fotogalerie/satni-skrine/', None),
        ('Realizace u zákazníků', '/reference/', '/realizace-a-recenze/'),
        ('Lanett v odvážných barvách', None, '/postele-na-miru/'),
    ]
    albums, total = [], 0
    for k, (name, src, link) in enumerate(sources):
        boxes = (
            [b for b in B.PAGES.get(src, {'boxes': []})['boxes'] if 'photogallery' in b['kind']]
            if src
            else [b for b in B.DATA['home']['boxes'] if 'photogallery' in b['kind']]
        )
        items = photo_ids([p for b in boxes for p in b['photos']])
        if not items:
            continue
        total += len(items)
        albums.append((k, name, link, items))
    cards, secs = [], []
    for n, (k, name, link, items) in enumerate(albums):
        anchor = B.slugify(name)
        i0, p0 = items[0]
        w, h = B.media_size(i0, 's')
        cards.append(
            f'<li><a class="frame" href="#{anchor}"><span class="ph"><img src="{B.media_src(i0, "s")}" width="{w}" height="{h}" alt="" loading="lazy" decoding="async"></span><h3>{E(name)}</h3><span class="small">{len(items)} fotografií</span></a></li>'
        )
        note = (
            '<p class="small i-album-note">Šatní skříně teď z kapacitních důvodů nevyrábíme. Fotky jsou z dřívějších zakázek.</p>'
            if name == 'Šatní skříně'
            else ''
        )
        more = f'<a class="link arrow" href="{link}">Modely a ceny</a>' if link else ''
        wall = ('sage', 'butter', 'clay', 'sky')[n % 4]
        secs.append(
            f'<section class="room wall-{wall} album-sec" id="{anchor}" aria-labelledby="h-{anchor}"><div class="wrap"><div class="sec-head"><div><h2 id="h-{anchor}">{E(name)}</h2><p class="small">{len(items)} fotografií. Kliknutím zvětšíte.</p></div>{more}</div>{note}'
            f'{album_view(items, f"gal{k}", name, f"Album {name}, posouvejte do stran")}</div></section>'
        )
    body = f'''{head('Dílna', 'Fotogalerie', 'Fotogalerie postelí a nábytku', 'Fotografie z naší dílny a od zákazníků. Klikněte na fotku pro zvětšení.')}
{room(f'<div class="wrap"><h2 class="i-sr">Přehled alb</h2><ul class="i-albums" data-fx="reveal-group">{"".join(cards)}</ul></div>', 'paper')}
{"".join(secs)}'''
    B.page(
        '/galerie/',
        'Fotogalerie postelí a nábytku z masivu',
        f'{total} fotografií postelí, palend, komod a stolů z masivu ze Stolařství Kubiš.',
        body,
    )


# ---------------------------------------------------------------- poptávka
@override('build_inquiry')
def build_inquiry():
    body = f'''{head('Vchod', 'Poptávka', 'Poptávka', 'Napište, co potřebujete. Ozveme se a pošleme písemnou nabídku s popisem, materiálem, rozměry, cenou a termínem.', wall='clay')}
<section class="room wall-paper"><div class="wrap c-cols">
  <div class="i-prose c-info">
    <h2>Co do zprávy napsat</h2>
    <ul><li>Rozměr postele nebo nábytku. Jiný rozměr než základní vyrobíme.</li><li>Dřevinu a povrch (moření, barva, olej), pokud už víte.</li><li>Výšku ložné plochy: 55, 60 nebo 65 cm.</li><li>Pro koho postel bude: nosnost, ohrádka, polohovací rošt.</li><li>Obec nebo PSČ, kam se bude dovážet.</li></ul>
    <h2>Jak to bude dál</h2>
    <ol><li>Ozveme se, doptáme se a pošleme písemnou nabídku.</li><li>Po vašem souhlasu vystavíme zálohový list. Od toho dne běží termín výroby.</li><li>Postel na míru vyrobíme obvykle do 4 týdnů.</li><li>Dovezeme ji vlastním autem a na místě smontujeme. Montáž při dovozu je zdarma.</li></ol>
    <p>Spěcháte? Volejte {tel_link(TEL1H, TEL1)}, telefon zvedá přímo rodina.</p>
  </div>
  <div class="i-formpanel"><h2>Napište, co potřebujete</h2>{form_only()}</div>
</div></section>
{faq_room(B.HOME_FAQ[:6], 'Než napíšete', 'sky', more=True)}'''
    B.page(
        '/poptavka/',
        'Poptávka',
        'Poptejte postel nebo nábytek z masivu na míru. Ozveme se a pošleme nabídku.',
        body,
    )


# ---------------------------------------------------------------- 404
@override('build_404')
def build_404():
    rows = [
        ('/postele-z-masivu/', 'Postele z masivu', 'katalog a ceny'),
        ('/nabytek-z-masivu/', 'Nábytek z masivu', 'komody, psací a jídelní stoly'),
        ('/matrace/', 'Matrace a rošty', 'k vyzkoušení na prodejně'),
        ('/caste-dotazy/', 'Časté dotazy', 'objednávka, doprava, záruka'),
        ('/kontakt/', 'Kontakt', 'telefon, adresa, otevírací doba'),
    ]
    jump = ''.join(
        f'<li><a href="{h}"><span>{E(t)}</span><small>{E(d)}</small></a></li>' for h, t, d in rows
    )
    body = f'''<section class="room wall-stone"><div class="wrap i-404"><div><span class="plate">Vchod</span><h1>Tuto stránku jsme nenašli</h1><p class="lead">Odkaz je možná starý nebo je v adrese překlep. Vyberte, co hledáte, nebo nám zavolejte.</p>
<ul class="i-jump">{jump}</ul>
<div class="ctas" style="margin-top:var(--s4)"><a class="btn" href="/">Úvodní stránka</a><a class="btn btn-2" href="tel:{TEL1H}">Zavolat {TEL1}</a></div></div>
{photo('detail-buk', 'r54', 'Detail nohy postele z jádrového buku', lazy=False, tilt='r')}</div></section>'''
    B.page('/404.html', 'Stránka nenalezena', 'Stránka nenalezena.', body, noindex=True)


# ---------------------------------------------------------------- časté dotazy
@override('build_faq_page')
def build_faq_page():
    allq = [x for _, items in B.FAQ_GROUPS for x in items]
    nav = ''.join(f'<a href="#{B.slugify(g)}">{E(g)}</a>' for g, _ in B.FAQ_GROUPS)
    secs = []
    for n, (g, items) in enumerate(B.FAQ_GROUPS):
        det = ''.join(
            f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in items
        )
        secs.append(
            f'<section class="room wall-{("sage", "butter", "clay", "sky")[n % 4]} faq-sec" id="{B.slugify(g)}" aria-labelledby="h-{B.slugify(g)}"><div class="wrap i-faqrow"><div class="i-faqh"><h2 id="h-{B.slugify(g)}">{E(g)}</h2><p class="small">{len(items)} {"otázka" if len(items) == 1 else "otázky" if len(items) < 5 else "otázek"}</p></div><div class="faq" data-fx="accordion">{det}</div></div></section>'
        )
    body = f'''{head('Dílna', 'Časté dotazy', 'Časté dotazy', f'Odpovědi na to, na co se nás zákazníci ptají nejčastěji: objednávka, platba, doprava, záruka, výška a nosnost postelí. Nenašli jste svou otázku? Zavolejte na <a class="link" href="tel:{TEL1H}">{TEL1}</a>.')}
<nav class="i-topics" aria-label="Témata"><div class="wrap">{nav}</div></nav>
{"".join(secs)}
{B.cta_band(title='Nenašli jste odpověď?', text='Napište nebo zavolejte, rádi poradíme.')}'''
    B.page(
        '/caste-dotazy/',
        'Časté dotazy: objednávka, platba, doprava, záruka',
        'Odpovědi na časté dotazy k objednávce, platbě, dopravě, záruce, výšce a nosnosti postelí ze Stolařství Kubiš.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [B.crumbs_ld([('Časté dotazy', '/caste-dotazy/')]), B.faq_ld(allq)],
        },
    )


# ---------------------------------------------------------------- poradna
@override('build_poradna')
def build_poradna():
    rows = []
    for n, (s, t, d, lead, sections, link) in enumerate(B.ARTICLES):
        name, w, h = B.COVERS[link]
        figure = f'<a class="ph r32 i-cover" href="/poradna/{s}/" tabindex="-1" aria-hidden="true"><img src="/img/{name}.jpg" width="{w}" height="{h}" alt="" loading="lazy" decoding="async"></a>'
        text = f'<div class="i-bt"><h2><a href="/poradna/{s}/">{E(t)}</a></h2><p>{E(lead)}</p><p><a class="link arrow" href="/poradna/{s}/">Číst celý článek</a></p></div>'
        rows.append(f'<article class="i-book i-spine-{n % 4}">{figure}{text}</article>')
    body = f'''{head('Dílna', 'Poradna', 'Poradna: jak vybrat postel z masivu', 'Krátké rady k výběru výšky, nosnosti a dřeviny. Z toho, co děláme každý den.')}
{room(f'<div class="wrap i-shelf">{"".join(rows)}</div>', 'butter')}
{B.cta_band(title='Nevíte, kterou postel vybrat?', text='Zavolejte, poradíme výšku, nosnost i dřevinu podle toho, kdo na posteli bude spát.')}'''
    B.page(
        '/poradna/',
        'Poradna: jak vybrat postel z masivu',
        'Rady k výběru postele z masivu: výška pro seniory, nosnost, dřeviny. Od rodinného stolařství Kubiš.',
        body,
        jsonld={
            "@context": "https://schema.org",
            "@graph": [B.crumbs_ld([('Poradna', '/poradna/')])],
        },
    )
    for n, (s, t, d, lead, sections, link) in enumerate(B.ARTICLES):
        cat = B.CAT_BY_SLUG[link]
        name, w, h = B.COVERS[link]
        sec = ''.join(f'<h2>{E(hh)}</h2>{x}' for hh, x in sections)
        others = [a for a in B.ARTICLES if a[0] != s]
        more = ''.join(
            f'<li><a href="/poradna/{a[0]}/"><h3>{E(a[1])}</h3><p>{E(a[3])}</p></a></li>'
            for a in others
        )
        body = f'''<div data-fx="progress"></div>
{head('Dílna', 'Poradna', t, E(lead), crumb=B.crumbs(('Poradna', '/poradna/'), (t, None)))}
<section class="room wall-paper i-body"><div class="wrap text-page i-text i-article"><article class="i-main"><figure class="frame i-fig i-tilt-r"><span class="ph r32"><img src="/img/{name}.jpg" width="{w}" height="{h}" alt="" fetchpriority="high"></span></figure>
<div class="i-prose">{sec}<p class="i-related">Související: <a class="link arrow" href="/{link}/">{E(cat[2])}, modely a ceny</a></p></div></article>
<aside class="side-card"><h2>Poradíme osobně</h2><p>Zavolejte nebo přijeďte vyzkoušet postel a matraci na prodejnu v Němčičkách. Návštěvu domluvte předem.</p><a class="btn btn-primary" href="tel:{TEL1H}">{TEL1}</a><a class="link" href="/poptavka/">Napsat poptávku</a><a class="link" href="/{link}/">{E(cat[2])}</a></aside></div></section>
{room(f'<div class="wrap"><h2 style="margin-bottom:var(--s4)">Další rady z poradny</h2><ul class="i-more-art">{more}</ul></div>', 'sage')}'''
        ld = {
            "@context": "https://schema.org",
            "@graph": [
                B.crumbs_ld([('Poradna', '/poradna/'), (t, f'/poradna/{s}/')]),
                {
                    "@type": "Article",
                    "headline": t,
                    "description": d,
                    "inLanguage": "cs",
                    "author": {"@type": "Organization", "name": "Stolařství Kubiš"},
                    "dateModified": B.TODAY,
                },
            ],
        }
        B.page(f'/poradna/{s}/', t, d, body, jsonld=ld)
