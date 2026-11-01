#!/usr/bin/env python3
"""Comprueba BOM y fichero de posiciones para el montaje de JLCPCB y genera
los ficheros en el formato que pide JLC.

Uso: python3 check_bom.py bom-full.csv ocx-pos.csv board.json <dir_salida_assembly> <informe.md>

- bom-full.csv: `kicad-cli sch export bom` sin agrupar, con LCSC/MPN/DNP.
- ocx-pos.csv:  `kicad-cli pcb export pos --exclude-dnp`.
"""
import csv
import json
import re
import sys
from collections import OrderedDict

MUST_EXCLUDE = ["U4", "J6", "J7"] + [f"TP{i}" for i in range(1, 13)]
LCSC_RE = re.compile(r"^C\d+$")


def main(bom_full, pos, board_json, outdir, md):
    rows = list(csv.DictReader(open(bom_full)))
    posrows = list(csv.DictReader(open(pos)))
    board = json.load(open(board_json))
    fps = {f["ref"]: f for f in board["footprints"]}

    fitted = [r for r in rows if r["DNP"] != "DNP" and r["ExclBOM"] == ""]
    fitted_refs = {r["Reference"] for r in fitted}
    pos_refs = {r["Ref"] for r in posrows}

    res = []

    def chk(name, ok, detail=""):
        res.append((name, "OK" if ok else "FALLO", detail))

    # 1. Exclusiones obligatorias
    for ref in MUST_EXCLUDE:
        r = next((x for x in rows if x["Reference"] == ref), None)
        in_bom = ref in fitted_refs
        in_pos = ref in pos_refs
        chk(f"{ref} fuera de BOM y CPL", r is not None and not in_bom and not in_pos,
            "no existe en el esquematico" if r is None else
            f"DNP={r['DNP'] or 'no'}; en BOM={in_bom}; en CPL={in_pos}")

    # 2. LCSC en todo lo demas
    missing = [r["Reference"] for r in fitted if not r["LCSC"].strip()]
    badfmt = [f"{r['Reference']}={r['LCSC']}" for r in fitted if r["LCSC"].strip() and not LCSC_RE.match(r["LCSC"].strip())]
    chk(f"Todas las referencias montadas ({len(fitted)}) tienen LCSC", not missing, ", ".join(missing))
    chk("Formato de codigo LCSC (C + digitos)", not badfmt, ", ".join(badfmt))
    nompn = [r["Reference"] for r in fitted if not r["MPN"].strip()]
    chk("Todas las referencias montadas tienen MPN", not nompn, ", ".join(nompn))

    # 3. Coherencia esquema <-> PCB
    diff = []
    for r in rows:
        f = fps.get(r["Reference"])
        if f is None:
            diff.append(f"{r['Reference']}: no esta en el PCB")
            continue
        if f["lcsc"] != r["LCSC"]:
            diff.append(f"{r['Reference']}: LCSC sch={r['LCSC']} pcb={f['lcsc']}")
        if f["fpid"] != r["Footprint"]:
            diff.append(f"{r['Reference']}: huella sch={r['Footprint']} pcb={f['fpid']}")
        if f["dnp"] != (r["DNP"] == "DNP"):
            diff.append(f"{r['Reference']}: DNP sch/pcb distinto")
    chk("LCSC, huella y DNP iguales en esquematico y PCB", not diff, "; ".join(diff))

    # 4. BOM <-> CPL
    only_bom = sorted(fitted_refs - pos_refs)
    only_pos = sorted(pos_refs - fitted_refs)
    chk("Toda referencia de la BOM tiene posicion", not only_bom, ", ".join(only_bom))
    chk("Toda posicion tiene linea de BOM", not only_pos, ", ".join(only_pos))
    sides = sorted({r["Side"] for r in posrows})
    chk("Componentes solo en la cara superior", sides == ["top"], ",".join(sides))
    ignored = sorted(set(fps) - fitted_refs - set(MUST_EXCLUDE))
    res.append(("Huellas sin montaje (agujeros, logos...)", "INFO", ", ".join(ignored)))

    # 5. Generar BOM JLC agrupada por LCSC
    groups = OrderedDict()
    for r in sorted(fitted, key=lambda r: (r["LCSC"], natural(r["Reference"]))):
        g = groups.setdefault(r["LCSC"], {"Comment": r["Value"], "Designator": [], "Footprint": r["Footprint"].split(":")[-1],
                                         "LCSC Part #": r["LCSC"], "MPN": r["MPN"], "values": set()})
        g["Designator"].append(r["Reference"])
        g["values"].add(r["Value"])
    with open(f"{outdir}/ocx-bom-jlcpcb.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "MPN", "Quantity"])
        for g in groups.values():
            comment = g["Comment"] if len(g["values"]) == 1 else g["MPN"]
            w.writerow([comment, ",".join(sorted(g["Designator"], key=natural)), g["Footprint"],
                        g["LCSC Part #"], g["MPN"], len(g["Designator"])])
    tht = sorted({r["Reference"] for r in fitted if fps[r["Reference"]]["attr"] & 1}, key=natural)
    res.append((f"Lineas BOM JLC: {len(groups)} referencias LCSC, {len(fitted)} componentes", "INFO",
                "Montaje THT (coste extra en JLC): " + ", ".join(tht)))

    # 6. CPL JLC
    with open(f"{outdir}/ocx-cpl-jlcpcb.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in sorted(posrows, key=lambda r: natural(r["Ref"])):
            rot = float(r["Rot"]) % 360
            w.writerow([r["Ref"], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm",
                        "Top" if r["Side"] == "top" else "Bottom", f"{rot:g}"])

    lines = ["# Comprobacion de BOM y CPL para montaje JLCPCB", "",
             "Generado por `scripts/check_bom.py`.", "",
             "| Comprobacion | Estado | Detalle |", "|---|---|---|"]
    for n, s, dd in res:
        lines.append(f"| {n} | {s} | {dd} |")
    open(md, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("FALLOS:", sum(1 for x in res if x[1] == "FALLO"))


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


if __name__ == "__main__":
    main(*sys.argv[1:6])
