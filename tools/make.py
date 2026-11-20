"""Vstupní bod sestavení webu v4.

Použití:
    python3 -I tools/make.py

Postup:
  1. Web se vygeneruje do dočasné složky mimo projekt (iCloud a Finder tak nevytvářejí
     kopie typu "index 2.html").
  2. Všechny HTML, CSS a JS soubory se zformátují (odsazení 2 mezery, řádky do 100 znaků).
  3. Do složky web/ se zkopírují jen soubory, které se skutečně změnily, a smažou se
     zastaralé. Fotky, písma a favicon (media, img, fonts) se nikdy nemění.

Moduly pages_home.py, pages_catalog.py a pages_info.py přepisují funkce z build.py při importu.
Když modul spadne, použije se výchozí šablona z build.py.
"""

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
# KUBIS_OUT: jiná cílová složka (paralelní práce); fotky a písma se do ní odkazují symlinky
WEB = Path(os.environ["KUBIS_OUT"]) if os.environ.get("KUBIS_OUT") else ROOT / "web"
ASSETS = ["media", "img", "fonts", "fonts.css", "favicon.svg", "apple-touch-icon.png"]
PRETTIER = ["npx", "--yes", "prettier@3.10.1", "--config", str(TOOLS / "prettierrc.json")]


def link_assets(target):
    """Do jiné cílové složky než web/ vloží odkazy na fotky a písma z web/."""
    if target == ROOT / "web":
        return
    target.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        link = target / name
        if not link.exists() and not link.is_symlink():
            link.symlink_to(ROOT / "web" / name)


def build_into(out):
    """Vygeneruje web do složky out (assety jsou jen odkazy na fotky v cílové složce)."""
    for name in ASSETS:
        link = out / name
        if not link.exists():
            link.symlink_to(WEB / name)
    os.environ["KUBIS_WEB"] = str(out)
    sys.path.insert(0, str(TOOLS))
    import build as B

    for name in ("pages_home", "pages_catalog", "pages_info"):
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name != name:
                traceback.print_exc()
        except Exception:
            print(f"!! modul {name} selhal, používá se výchozí šablona", file=sys.stderr)
            traceback.print_exc()
    B.main()


def format_output(out):
    """Zformátuje HTML, CSS a JS (jen soubory, které web sám generuje, ne fotky)."""
    patterns = ["**/*.html", "css/*.css", "js/*.js"]
    files = [str(p) for pattern in patterns for p in out.glob(pattern) if not p.is_symlink()]
    for i in range(0, len(files), 100):
        subprocess.run(
            PRETTIER + ["--write", "--log-level", "warn"] + files[i : i + 100], check=True
        )


def publish(out):
    """Zkopíruje do web/ jen změněné soubory (porovnání podle obsahu) a smaže zastaralé."""
    cmd = ["rsync", "-rc", "--delete"]
    for name in ASSETS:
        cmd += ["--exclude", "/" + name]
    subprocess.run(cmd + [str(out) + "/", str(WEB) + "/"], check=True)


def main():
    link_assets(WEB)
    out = Path(tempfile.mkdtemp(prefix="kubis-web-"))
    try:
        build_into(out)
        format_output(out)
        publish(out)
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    main()
