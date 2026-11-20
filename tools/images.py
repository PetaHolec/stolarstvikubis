"""Výroba web/media/ z originálů (originals/) v plné kvalitě.

- JPEG: kvalita 90, progresivní, optimalizovaná Huffmanova tabulka, jemné doostření po zmenšení.
  Velká verze <id>.jpg max. 1800 px, náhled <id>-s.jpg max. 800 px. Nic se NIKDY nezvětšuje nad
  rozlišení originálu (rozmazané zvětšování vypadá hůř než menší fotka).
- Matrace a další produktové fotky s bílým pozadím (data/cutout-spec.json): PNG s průhledností
  v původním rozlišení (tools/cutout.py).
Výstup: web/media/*, data/media-sizes.json, data/cutouts.json
Použití: python3 -I tools/images.py
"""

import json, os, sys
from multiprocessing import Pool
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cutout

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'originals'
DST = ROOT / 'web/media'
DST.mkdir(parents=True, exist_ok=True)
MAXL, MAXS, Q = 1800, 800, 90
# Fotky, které mají v EXIFu chybný příznak otočení (pixely jsou už správně, Webnode znovu uložil JPEG bez smazání tagu).
# U nich se exif_transpose nesmí použít, jinak jsou na boku nebo vzhůru nohama. Regenerace jen těchto: python3 -I tools/images.py fix
NO_EXIF = {
    '200001244-4421f4468f',
    '200001245-4e1774e715',
    '200005099-490bd490bf',
    '200005138-7482774829',
    '200005143-024980249b',
    '200006418-a5473a5477',
    '200006423-b785cb785f',
    '200006424-463f6463f9',
    '200007123-9f3b99f3ba',
    '200007463-a8689a868c',
}
# jediná fotka, jejíž pixely jsou na boku (EXIF říká 180°, správně je 90° proti směru hodin): rotace ve stupních
ROTATE = {'200005143-024980249b': 90}


def load(path):
    im = Image.open(path)
    if Path(path).stem in ROTATE:
        im = im.rotate(ROTATE[Path(path).stem], expand=True)
    elif Path(path).stem not in NO_EXIF:
        im = ImageOps.exif_transpose(im)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert('RGB')


def scaled(im, m):
    if max(im.size) <= m:
        return im
    out = im.copy()
    out.thumbnail((m, m), Image.LANCZOS, reducing_gap=3.0)
    return out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=40, threshold=2))


def save_jpg(im, path):
    im.save(
        path,
        'JPEG',
        quality=Q,
        optimize=True,
        progressive=True,
        subsampling=0 if max(im.size) <= 900 else 2,
    )


def job(a):
    path, cut_ids, holes = a
    i = path.stem
    try:
        if i in cut_ids:
            _, sizes, _ = cutout.job((path, str(DST), i, i in holes))
            return i, ('png', sizes)
        im = load(path)
        big, small = scaled(im, MAXL), scaled(im, MAXS)
        save_jpg(big, DST / f'{i}.jpg')
        save_jpg(small, DST / f'{i}-s.jpg')
        return i, ('jpg', {'l': list(big.size), '-s': list(small.size), 'native': list(im.size)})
    except Exception as e:
        return i, ('err', str(e))


if __name__ == '__main__' and sys.argv[1:] == ['fix']:
    # jen opravené soubory: přepíše je v web/media a doplní jejich rozměry do data/media-sizes.json (ostatní nechá být)
    sizes = json.load(open(ROOT / 'data/media-sizes.json'))
    for i in sorted(NO_EXIF):
        im = load(SRC / f'{i}.jpg')
        big, small = scaled(im, MAXL), scaled(im, MAXS)
        save_jpg(big, DST / f'{i}.jpg')
        save_jpg(small, DST / f'{i}-s.jpg')
        sizes[i] = {'l': list(big.size), '-s': list(small.size), 'native': list(im.size)}
        print('opraveno', i, im.size)
    tmp = ROOT / 'data/media-sizes.json.tmp'
    json.dump(sizes, open(tmp, 'w'))
    os.replace(tmp, ROOT / 'data/media-sizes.json')
elif __name__ == '__main__':
    spec = json.load(open(ROOT / 'data/cutout-spec.json'))
    cut_ids, holes = set(spec['ids']), set(spec.get('holes', []))
    files = sorted(SRC.glob('*.*'))
    with Pool(8) as p:
        res = p.map(job, [(f, cut_ids, holes) for f in files], chunksize=8)
    sizes, cuts = {}, {}
    for i, (kind, s) in res:
        if kind == 'err':
            print('ERR', i, s)
            continue
        if kind == 'png':
            if s:
                cuts[i] = {'sizes': s}
        else:
            sizes[i] = s
    # cutout.job vrací velikosti jako tuple; SIZES potřebuje i pro PNG záznam (build.py bere CUT první)
    for i, c in cuts.items():
        sizes.setdefault(i, {'l': list(c['sizes']['l']), '-s': list(c['sizes']['-s'])})
        c['sizes'] = {k: list(v) for k, v in c['sizes'].items()}
    json.dump(sizes, open(ROOT / 'data/media-sizes.json', 'w'))
    json.dump(cuts, open(ROOT / 'data/cutouts.json', 'w'), indent=1)
    print(len(sizes), 'fotek,', len(cuts), 'PNG')
