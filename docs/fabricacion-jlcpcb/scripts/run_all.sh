#!/usr/bin/env bash
# Regenera todas las salidas de docs/fabricacion-jlcpcb/ a partir de hardware/.
# Trabaja sobre una COPIA temporal de hardware/ (KiCad escribe .kicad_prl y aqui
# se anade un .kicad_dru), de modo que hardware/ no se toca.
#
# Requisitos: kicad-cli 10 (en este entorno, wrapper sobre la imagen Docker
# oficial kicad/kicad:10.0) y, en el host, python3 con shapely y matplotlib,
# rsvg-convert y zip.
#   KICAD_PY="docker run --rm -v $PWD:$PWD -w $PWD kicad/kicad:10.0 python3"
#   (o "python3" si pcbnew esta instalado localmente)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$ROOT/docs/fabricacion-jlcpcb
WORK=${WORK:-$(mktemp -d)}
KICAD_PY=${KICAD_PY:-python3}
PCB=ocxPrototype.kicad_pcb
SCH=ocxPrototype.kicad_sch

mkdir -p "$WORK" && rm -rf "$WORK/hw" && cp -r "$ROOT/hardware" "$WORK/hw"
mkdir -p "$OUT"/{gerbers,drill,assembly,checks,renders}
cd "$WORK/hw"

# --- Fabricacion
kicad-cli pcb export gerbers -o "$OUT/gerbers/" \
  -l F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask --use-drill-file-origin $PCB
kicad-cli pcb export drill -o "$OUT/drill/" --format excellon --drill-origin plot \
  --excellon-units mm --excellon-separate-th --generate-map --map-format gerberx2 $PCB
(cd "$OUT" && rm -f ocx-gerber-jlcpcb.zip && zip -qj ocx-gerber-jlcpcb.zip gerbers/* drill/*.drl)

# --- Montaje
kicad-cli pcb export pos -o "$OUT/assembly/ocx-pos.csv" --format csv --units mm --side both \
  --use-drill-file-origin --exclude-dnp $PCB
kicad-cli sch export bom -o "$OUT/assembly/bom-full.csv" \
  --fields 'Reference,Value,Footprint,LCSC,MPN,${DNP},${EXCLUDE_FROM_BOM},${EXCLUDE_FROM_BOARD}' \
  --labels 'Reference,Value,Footprint,LCSC,MPN,DNP,ExclBOM,ExclBoard' --ref-range-delimiter '' $SCH

# --- DRC / ERC (reglas del proyecto)
kicad-cli pcb drc -o "$OUT/checks/drc.json" --format json --severity-all --schematic-parity $PCB || true
kicad-cli pcb drc -o "$OUT/checks/drc.rpt" --severity-all --schematic-parity $PCB || true
kicad-cli sch erc -o "$OUT/checks/erc.json" --format json --severity-all $SCH || true
kicad-cli sch erc -o "$OUT/checks/erc.rpt" --severity-all $SCH || true
# --- DRC con reglas JLCPCB (solo en la copia)
cp "$OUT/scripts/jlcpcb.kicad_dru" ocxPrototype.kicad_dru
kicad-cli pcb drc -o "$OUT/checks/drc-jlcpcb.json" --format json --severity-all $PCB || true
kicad-cli pcb drc -o "$OUT/checks/drc-jlcpcb.rpt" --severity-all $PCB || true
# Quitar las reglas JLC: el volcado rellena zonas y debe usar las reglas del proyecto
rm -f ocxPrototype.kicad_dru

# --- Geometria y comprobaciones por script
$KICAD_PY "$OUT/scripts/dump_board.py" "$WORK/hw/$PCB" "$WORK/board.json"
python3 "$OUT/scripts/check_jlcpcb.py" "$WORK/board.json" "$OUT/checks/jlcpcb-capacidades.md" "$OUT/checks/jlcpcb-capacidades.json"
python3 "$OUT/scripts/check_bom.py" "$OUT/assembly/bom-full.csv" "$OUT/assembly/ocx-pos.csv" "$WORK/board.json" "$OUT/assembly" "$OUT/checks/bom-cpl.md"
python3 "$OUT/scripts/pin1_table.py" "$WORK/board.json" "$OUT/assembly/ocx-cpl-jlcpcb.csv" "$OUT/checks/pin1-polaridad.md" "$OUT/checks/pin1-polaridad.png"

# --- Renders
i=1
for L in F.Cu In1.Cu In2.Cu B.Cu F.Mask B.Mask F.Silkscreen B.Silkscreen F.Paste B.Paste Edge.Cuts; do
  extra=""; case $L in B.*) extra="--mirror";; esac
  kicad-cli pcb export svg -o "$WORK/$L.svg" --layers "$L,Edge.Cuts" --mode-single --page-size-mode 2 \
    --exclude-drawing-sheet --drill-shape-opt 2 $extra $PCB
  rsvg-convert -w 2400 -b white "$WORK/$L.svg" -o "$OUT/renders/$(printf %02d $i)-${L/./_}.png"
  i=$((i+1))
done
for side in top bottom; do
  kicad-cli pcb render -o "$OUT/renders/3d-$side.png" --side $side --width 2400 --height 1300 \
    --zoom 1.9 --quality high --background opaque $PCB
done
echo "Listo: $OUT"
