#!/usr/bin/env bash
# Regenera las figuras de la placa y el PDF del manual.
# Requisitos: python3, pandoc (>= 2.x) y WeasyPrint (pip install weasyprint).
# Opcional: node + playwright para volver a rasterizar los SVG a PNG.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 herramientas/gen_placa.py

if command -v node >/dev/null && node -e "require('playwright')" 2>/dev/null; then
  for svg in img/*.svg; do
    node herramientas/svg-a-png.js "$svg" "${svg%.svg}.png"
  done
else
  echo "Aviso: sin node+playwright no se regeneran los PNG (se usan los existentes)." >&2
fi

pandoc MANUAL-USUARIO.md \
  --from gfm --to html5 --standalone \
  --metadata pagetitle="OCX: manual de usuario y de mantenimiento" \
  --metadata lang=es \
  --css estilo.css \
  --pdf-engine=weasyprint \
  --resource-path=. \
  -o MANUAL-USUARIO.pdf
echo "Generado manual/MANUAL-USUARIO.pdf"
