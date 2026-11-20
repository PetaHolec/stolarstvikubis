#!/bin/sh
# Vytvoří samostatný výstupní adresář web-<jmeno>/ se symlinky na fotky a písma (pro paralelní práci bez kolizí).
# Použití: sh tools/mkout.sh home   ->  KUBIS_WEB=$PWD/web-home python3 -I tools/make.py
set -e
cd "$(dirname "$0")/.."
d="web-$1"; mkdir -p "$d"
for n in media img fonts fonts.css favicon.svg apple-touch-icon.png; do [ -e "$d/$n" ] || ln -s "../web/$n" "$d/$n"; done
echo "$PWD/$d"
