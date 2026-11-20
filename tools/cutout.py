"""Odstranění bílého pozadí produktových fotek → PNG s průhledností (jen PIL, bez numpy).

Princip: pozadí = bílé pixely spojené s okrajem fotky (flood fill), takže bílé části
samotného výrobku (potah matrace) zůstanou. Hrana se změkčí podle jasu, aby nezůstal bílý lem.

Použití: python3 tools/cutout.py <zdroj_orig_dir> <web/media> <seznam_id.json> [data/cutouts.json]
"""

import sys, os, json
from multiprocessing import Pool
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

T_BG = 244  # minimální jas kanálu, aby pixel mohl být pozadím
SAT = 12  # max. rozdíl mezi kanály (bílá/šedá, ne barevná)
EDGE = 42  # šířka přechodu jasu na hraně (255 → 255-EDGE = plně kryté)
MAXL = 1800  # velikost velkého PNG (nikdy se nezvětšuje nad originál)
MAXS = 800  # velikost náhledu


def cut(im, holes=False):
    im = ImageOps.exif_transpose(im).convert('RGB')
    if max(im.size) > MAXL:
        im.thumbnail((MAXL, MAXL), Image.LANCZOS)
    r, g, b = im.split()
    mn = ImageChops.darker(ImageChops.darker(r, g), b)
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    sat = ImageChops.subtract(mx, mn)
    cand = ImageChops.multiply(
        mn.point(lambda v: 255 if v >= T_BG else 0), sat.point(lambda v: 255 if v <= SAT else 0)
    )
    w, h = cand.size
    px = cand.load()
    border = (
        [(x, 0) for x in range(w)]
        + [(x, h - 1) for x in range(w)]
        + [(0, y) for y in range(h)]
        + [(w - 1, y) for y in range(h)]
    )
    for pt in border:
        if px[pt] == 255:
            ImageDraw.floodfill(cand, pt, 128, thresh=0)
    bg = cand.point(lambda v: 255 if v == 128 else 0)
    if holes:
        # uzavřené čistě bílé plochy (např. prostor mezi lamelami roštu)
        pure = ImageChops.multiply(
            mn.point(lambda v: 255 if v >= 250 else 0), sat.point(lambda v: 255 if v <= 6 else 0)
        )
        pure = ImageChops.subtract(pure, bg)
        pp = pure.load()
        area = w * h
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                if pp[x, y] == 255:
                    ImageDraw.floodfill(pure, (x, y), 100, thresh=0)
                    reg = pure.point(lambda v: 255 if v == 100 else 0)
                    n = reg.histogram()[255]
                    if n > area * 0.012:
                        bg = ImageChops.lighter(bg, reg)
                    pure = Image.composite(Image.new('L', pure.size, 50), pure, reg)
                    pp = pure.load()
    # pás kolem pozadí: průhlednost podle jasu (vyhlazená hrana bez bílého lemu)
    grown = bg.filter(ImageFilter.MaxFilter(5))
    band = ImageChops.subtract(grown, bg)
    edge_alpha = mn.point(lambda v: max(0, min(255, (255 - v) * 255 // EDGE)))
    alpha = Image.new('L', im.size, 255)
    alpha = Image.composite(edge_alpha, alpha, band)
    alpha = Image.composite(Image.new('L', im.size, 0), alpha, bg)
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    # ořez na obsah s malým okrajem
    box = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    out = im.copy()
    out.putalpha(alpha)
    if box:
        pad = int(max(w, h) * 0.02)
        box = (
            max(0, box[0] - pad),
            max(0, box[1] - pad),
            min(w, box[2] + pad),
            min(h, box[3] + pad),
        )
        out = out.crop(box)
    removed = sum(bg.histogram()[255:]) / (w * h)
    return out, removed


def job(args):
    src, dst, i, holes = args
    try:
        out, removed = cut(Image.open(src), holes)
        sizes = {}
        for suf, m in (('', MAXL), ('-s', MAXS)):
            c = out.copy()
            if max(c.size) > m:
                c.thumbnail((m, m), Image.LANCZOS)
            c.save(os.path.join(dst, f'{i}{suf}.png'), optimize=True)
            sizes['l' if not suf else '-s'] = c.size
        return i, sizes, round(removed, 3)
    except Exception as e:
        return i, None, str(e)


if __name__ == '__main__':
    src_dir, dst, ids_file = sys.argv[1:4]
    out_json = sys.argv[4] if len(sys.argv) > 4 else None
    spec = json.load(open(ids_file))
    ids = spec['ids'] if isinstance(spec, dict) else spec
    hole_ids = set(spec.get('holes', [])) if isinstance(spec, dict) else set()
    with Pool(8) as p:
        res = p.map(job, [(os.path.join(src_dir, i + '.src'), dst, i, i in hole_ids) for i in ids])
    ok = {i: {'sizes': s, 'removed': r} for i, s, r in res if s}
    for i, s, r in res:
        if not s:
            print('ERR', i, r)
    if out_json:
        json.dump(ok, open(out_json, 'w'), indent=1)
    print(len(ok), 'PNG')
