# Nasazení v4

Obsah složky `web/` nahrajte do kořene hostingu s Apache (kvůli `.htaccess`). Zbytek postupu, kontroly před spuštěním a aktivace formuláře FormSubmit jsou stejné jako ve v1 (viz `../stolarstvikubis/NASAZENI.md`).

## Generování
```bash
python3 -I tools/fetch_originals.py   # stáhne originály fotek ze starého webu do originals/ (dokud web běží)
python3 -I tools/images.py            # web/media: JPEG q90, matrace PNG s průhledností, nikdy se nezvětšuje
python3 -I tools/make.py              # vygeneruje celý web/ (moduly tools/pages_home.py, pages_catalog.py, pages_info.py + CSS v tools/css/)
```
Úvodní stránka, rozcestníky, poradna a texty kategorií jsou v `tools/build.py` (`COPY`, `build_home`, `ARTICLES`). Šablony a vzhled: `tools/site.css`.

## Fotky
Mnoho originálů na starém webu má jen 640–720 px (nahráno z Facebooku). Web je proto zobrazuje v původní velikosti a nezvětšuje je. Pro nejlepší vzhled mají Kubišovi nafotit hlavní modely a matrace znovu (min. 1800 px na delší straně, matrace na bílém pozadí).
