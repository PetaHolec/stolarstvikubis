# Stolařství Kubiš v2: struktura webu a SEO (kde je co a proč)

Cíl: každá stránka odpovídá na jeden hledací záměr a žádné dvě stránky si nekonkurují. Žádné opakování klíčových slov: fráze je v title, H1 a úvodu, jinde se píše přirozeně. Čísla (výška, nosnost, záruka) jsou na viditelném místě, protože podle nich lidé i AI vyhledávače rozhodují.

## Co zjistila analýza konkurence
| Konkurent | Co dělá | Slabina, kterou využíváme |
|---|---|---|
| Blanář nábytek (blanar.cz) | Velkovýrobce, „200 000 postelí ročně“, H1 „Příběhy našich postelí vytváříte Vy“ | Ani slovo o seniorech, nosnosti, atypu. Anonymní. |
| masivni-postele.cz | Prodejna v Mladé Boleslavi, title „postele, matrace, rošty“, žádný H1 | Tenký obsah, žádné parametry ani příběh. |
| ATOL nábytek (Kroměříž) | Obecný nábytkář, v katalogu uvádí buk a dub | Postele jsou jedna z mnoha kategorií. |
| nejremeslnici.cz | Portál: H1 „Postele z masivu Praha“, recenze, ceny v kategorii | Vede na lokální frázi, ale výrobce na ní není vlastním webem. |
| Kaufland, Favi, Homago | E-shopy a vyhledávače s nosností 150–250 kg | Nikdo neuvádí 400–500 kg ani výšku pro seniory. |

Závěr: nikdo neobsadil „zvýšená postel pro seniory z masivu“, „vysokozátěžová postel 500 kg“ ani „postel s ohrádkou pro dospělé“. Tyhle tři věty jsou tahouny webu, homepage je jen rozcestník.

## Mapa stránek a jejich fráze
| URL | Hledací záměr (title/H1) | Obsah, který tam musí být |
|---|---|---|
| `/` | postele z masivu na míru od výrobce, značka | H1, 5 čísel, 4 situace (odkazy na segmenty), proč masiv, příběh Lanett, postup objednávky, 3 recenze, prodejna, FAQ (JSON-LD) |
| `/postele-z-masivu/` | katalog postelí z masivu | rozcestník: podle potřeby / podle typu, srovnání dřevin, FAQ |
| `/postele-pro-seniory/` | zvýšené postele pro seniory | fakta 55/60/65 cm, modely a ceny, rady k výběru, FAQ |
| `/vysokozatezove-postele/` | vysokozátěžová postel, nosnost 500 kg | fakta 400/500 kg, 40 mm, prodloužené délky, matrace pro těžší osoby |
| `/postele-pro-handicapovane/` | postel s ohrádkou pro dospělé a děti | ohrádky, polohování, příplatky, antidekubitní matrace |
| `/postele-na-miru/` | atypická / čalouněná postel na míru | postup, termín 4 týdny, podle nákresu nebo fotky |
| `/patrove-a-vysoke-postele/` | patrová postel z masivu | palandy, vysoké postele se zásuvkami |
| `/jednoluzka/`, `/dvouluzka/`, `/studentske-postele/`, `/dubove-postele/` | typ postele (obecné dotazy) | modely s cenami, jádrový buk, FAQ |
| `/nabytek-z-masivu/` + komody, jídelní stoly, bytové doplňky | nábytek z masivu na zakázku | rozcestník + modely |
| `/matrace/`, `/rosty-a-toppery/` | matrace od českých výrobců, pevný rošt 500 kg | PNG výřezy, vrstvy, ceny |
| `/dreviny-a-povrchy/` | buk, jádrový buk, dub | srovnání, moření, oleje |
| `/poradna/…` (3 články) | jak vysoká postel pro seniora, nosnost postele, buk nebo dub | odpověď na jednu otázku, odkaz na kategorii |
| `/prodejna-nemcicky/` | prodejna postelí a matrací u Brna | adresa, hodiny po domluvě, mapa |
| `/doprava-a-montaz/`, `/o-nas/`, `/kontakt/`, `/realizace-a-recenze/` | důvěra a konverze | 44 recenzí, fotky realizací |
| `/produkty/{model}/` (206) | název modelu | Product schema, cena, popis, poptávka |

## Pravidla proti přeplácanosti
- Jedna stránka, jeden záměr. Homepage necílí na „senioři“ ani „nosnost“, jen na ně odkazuje.
- Title ≤ 60 znaků, description ≤ 158, jeden H1. Fráze v H1 není zopakována v každém odstavci.
- Staré přeplácané URL z Webnode se 301 přesměrují (`.htaccess`), slučují se: dřeviny + dekory, rošty + toppery.
- Čísla v „fakta“ pásu u každé kategorie (citují je AI vyhledávače). `llms.txt` a povolení AI botů v `robots.txt`.
- Strukturovaná data: FurnitureStore (home), BreadcrumbList, CollectionPage, FAQPage, Product, Article. AggregateRating záměrně není (vlastní recenze Google nezobrazuje).

## Co musí potvrdit majitel
- Texty poradny a „Jak vybrat“ jsou složené jen z faktů ze starého webu a ceníku. Před spuštěním je projít a podepsat jménem Petra Kubiše.
- Otevírací doba prodejny (web říká Po–Pá 15–20, kontaktní blok 8–20).
- Přesné GPS bodu domu č. p. 5 (v kódu je střed z Mapy.cz).
