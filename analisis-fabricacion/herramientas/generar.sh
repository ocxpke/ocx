#!/usr/bin/env bash
# Genera Gerber, taladros, BOM, CPL, DRC y ERC de la placa OCX a partir de un
# commit (por defecto origin/main) usando kicad-cli dentro de kicad/kicad:10.0.
#
# NO toca hardware/: exporta el árbol del commit con `git archive` a un
# directorio de trabajo y ejecuta allí kicad-cli. Las salidas son SOLO para
# comprobación (no se deben subir a JLC desde aquí).
#
# Uso: herramientas/generar.sh [commit] [directorio_salida]
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$AQUI" rev-parse --show-toplevel)"
COMMIT="${1:-origin/main}"
SALIDA="$(realpath -m "${2:-$AQUI/../salida}")"
IMAGEN="kicad/kicad:10.0"
PROY="ocxPrototype"

rm -rf "$SALIDA"
mkdir -p "$SALIDA"/{fuente,gerber,gerber-plotparams,gerber-sin-refill,bom,cpl,informes}

SHA="$(git -C "$REPO" rev-parse "$COMMIT")"
echo "$SHA" > "$SALIDA/COMMIT"
git -C "$REPO" archive "$SHA" hardware | tar -x -C "$SALIDA/fuente"

# Copia de trabajo con las reglas de JLC (fichero .kicad_dru junto al proyecto).
# Solo existe en la copia: hardware/ no se modifica.
mkdir -p "$SALIDA/fuente-jlc"
cp -a "$SALIDA/fuente/hardware/." "$SALIDA/fuente-jlc/"
cp "$AQUI/jlcpcb-4capas.kicad_dru" "$SALIDA/fuente-jlc/$PROY.kicad_dru"

# Se ejecuta con el usuario "kicad" de la imagen, cuyo HOME ya trae las tablas
# globales de librerías (sin ellas el DRC/ERC llena el informe de
# lib_footprint_issues / lib_symbol_issues ajenos a la placa).
chmod -R a+rwX "$SALIDA"
kc() {
  docker run --rm -v "$SALIDA:/w" -w /w "$IMAGEN" kicad-cli "$@"
}
F=/w/fuente/hardware
J=/w/fuente-jlc

kicad_version="$(kc version)"
echo "$kicad_version" > "$SALIDA/KICAD_VERSION"
echo "kicad-cli $kicad_version, commit $SHA"

# 1. Gerber: ajustes recomendados por JLC (extensiones Protel, restar máscara de
#    la serigrafía, sin X2/netlist para evitar avisos de su visor). Capas
#    explícitas para no depender de los plot params guardados en la placa.
kc pcb export gerbers -o /w/gerber \
  -l F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask --no-x2 --no-netlist --precision 6 --check-zones \
  $F/$PROY.kicad_pcb

# Además, con los plot params guardados en la placa, para compararlos.
kc pcb export gerbers -o /w/gerber-plotparams --board-plot-params $F/$PROY.kicad_pcb

# Cobre sin --check-zones: si difiere del anterior, los rellenos guardados en el
# commit no están al día (analizar.py compara ambos).
kc pcb export gerbers -o /w/gerber-sin-refill -l F.Cu,In1.Cu,In2.Cu,B.Cu \
  --subtract-soldermask --no-x2 --no-netlist --precision 6 \
  $F/$PROY.kicad_pcb

# 2. Taladros: Excellon, mm, decimal, PTH y NPTH separados, óvalos "alternate"
#    (lo que pide JLC), origen absoluto (igual que los Gerber), mapa en Gerber X2.
kc pcb export drill -o /w/gerber/ --format excellon --drill-origin absolute \
  --excellon-units mm --excellon-zeros-format decimal --excellon-oval-format alternate \
  --excellon-separate-th --generate-map --map-format gerberx2 \
  --generate-report --report-path /w/informes/taladros.rpt \
  $F/$PROY.kicad_pcb

# 3. BOM desde el esquemático (todas las filas, con DNP marcado) y sin DNP.
CAMPOS='Reference,Value,Footprint,LCSC,MPN,${QUANTITY},${DNP},${EXCLUDE_FROM_BOM}'
ETIQ='Designator,Comment,Footprint,LCSC,MPN,Qty,DNP,ExclBOM'
kc sch export bom -o /w/bom/bom-completa.csv --fields "$CAMPOS" --labels "$ETIQ" \
  --group-by 'Value,Footprint,LCSC,MPN,${DNP}' --ref-range-delimiter '' \
  $F/$PROY.kicad_sch
kc sch export bom -o /w/bom/bom-sin-dnp.csv --fields "$CAMPOS" --labels "$ETIQ" \
  --group-by 'Value,Footprint,LCSC,MPN' --ref-range-delimiter '' --exclude-dnp \
  $F/$PROY.kicad_sch

# 4. CPL (posiciones). kicad-cli usa el ANCLA de cada huella (no "FT Origin").
kc pcb export pos -o /w/cpl/cpl-kicad-cli.csv --format csv --units mm --side both --exclude-dnp \
  $F/$PROY.kicad_pcb
kc pcb export pos -o /w/cpl/cpl-kicad-cli-con-dnp.csv --format csv --units mm --side both \
  $F/$PROY.kicad_pcb

# 5. ERC y DRC.
kc sch erc -o /w/informes/erc.json --format json --severity-all --severity-exclusions \
  $F/$PROY.kicad_sch || true
kc sch erc -o /w/informes/erc.rpt --format report --severity-all --severity-exclusions \
  $F/$PROY.kicad_sch || true
# DRC con las reglas del proyecto (tal cual está en main)
kc pcb drc -o /w/informes/drc-proyecto.json --format json --severity-all --severity-exclusions \
  --schematic-parity --refill-zones $F/$PROY.kicad_pcb || true
# DRC con las reglas de JLC añadidas (copia de trabajo)
kc pcb drc -o /w/informes/drc-jlc.json --format json --severity-all --severity-exclusions \
  --schematic-parity --refill-zones $J/$PROY.kicad_pcb || true
kc pcb drc -o /w/informes/drc-jlc.rpt --format report --severity-all --severity-exclusions \
  --schematic-parity --refill-zones $J/$PROY.kicad_pcb || true

echo "Salidas en $SALIDA"

# Copia de los informes DRC/ERC (no son ficheros de fabricación) junto a los resultados.
RESULT="$AQUI/../resultados/drc-erc"
mkdir -p "$RESULT"
cp "$SALIDA"/informes/*.json "$SALIDA"/informes/*.rpt "$RESULT"/
cp "$SALIDA/COMMIT" "$SALIDA/KICAD_VERSION" "$RESULT"/
