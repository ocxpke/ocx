#!/usr/bin/env python3
"""Tabla de pin 1 / polaridad y lamina de dibujos para revisar la vista 3D de
JLCPCB (o el visor de CPL de su web).

Uso: python3 pin1_table.py board.json ocx-cpl-jlcpcb.csv salida.md salida.png
"""
import csv
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly

REFS = ["U1", "U2", "U5", "U6", "U7", "U8", "D1", "D2", "D3", "Y1",
        "J1", "J4", "J10", "L2", "L3"]

# Pad de referencia (el que hay que localizar en el 3D) y que comprobar.
INFO = {
    "U1": ("1", "Punto de pin 1 del VQFN-64 sobre el pad marcado. EP centrado.",
           "Un giro de 90/180 deja el BT817 inservible."),
    "U2": ("1", "Punto de pin 1 del SOT-23-6. Pin 2 = GND, pin 5 = VBUS.",
           "Girado 180 grados intercambia GND (2) y +5V (5): cortocircuito a traves de los diodos."),
    "U5": ("1", "Muesca/punto del SOIC-28 en el extremo del pad 1.", ""),
    "U6": ("1", "Punto de pin 1 del SOT-23-6 (DDC). 1 = GND, 2 = SW, 3 = VIN, 4 = FB, 5 = EN, 6 = CB.",
           "Girado 180 grados: VIN<->CB y GND<->FB; el regulador no arranca o se destruye."),
    "U7": ("1", "Punto/bisel del SOIC-8 208 mil en el pad 1 (/CS).", ""),
    "U8": ("1", "Punto de pin 1 del SOT-23-6. 1 = LX, 2 = GND, 6 = VIN (+5V).", "Girado 180 grados pone +5V en el LX y GND en el pad 5."),
    "D1": ("1", "TVS bidireccional (CA): sin polaridad. Basta con que asiente en los dos pads.", ""),
    "D2": ("1", "LED: pad 1 = CATODO (K). La marca verde/T del encapsulado debe ir al pad 1.", ""),
    "D3": ("1", "Schottky SMA: pad 1 = CATODO (K). La banda debe quedar sobre el pad 1.",
           "Al reves conduce en directa la salida a la entrada."),
    "Y1": ("1", "Cristal 5032 4 pines: 1 y 3 = cristal, 2 y 4 = GND. Bisel/punto en el pad 1.",
           "Un giro de 180 es inocuo (1<->3, 2<->4); uno de 90 pone el cristal a GND."),
    "J1": ("1", "FPC 40 p (XF2M-4015-1A): pad 1 coincide con el pin 1 del LCD; boca hacia el cable.", ""),
    "J4": ("1", "FPC 6 p (84953-6): pad 1 coincide con el pin 1 del panel tactil; boca hacia el cable.", ""),
    "J10": ("A1", "USB-C: boca del conector hacia el borde de la placa; patillas de carcasa en sus ranuras.", ""),
    "L2": ("1", "Inductancia sin polaridad electrica; el punto (inicio de devanado) va al pad 1.", ""),
    "L3": ("1", "Inductancia sin polaridad electrica; el punto (inicio de devanado) va al pad 1.", ""),
}


def quadrant(dx, dy, tol=0.15):
    v = "arriba" if dy < -tol else ("abajo" if dy > tol else "centro")
    h = "izquierda" if dx < -tol else ("derecha" if dx > tol else "centro")
    if v == "centro" and h == "centro":
        return "centro"
    if v == "centro":
        return h
    if h == "centro":
        return v
    return f"{v}-{h}"


def main(board_json, cpl, md, png):
    d = json.load(open(board_json))
    fps = {f["ref"]: f for f in d["footprints"]}
    pads = {}
    for p in d["pads"]:
        pads.setdefault(p["ref"], []).append(p)
    cplrows = {r["Designator"]: r for r in csv.DictReader(open(cpl))}

    lines = ["# Pin 1 y polaridad para comparar con la vista 3D de JLCPCB", "",
             "Generado por `scripts/pin1_table.py`. Vista superior (como la muestra JLC), Y hacia abajo "
             "como en KiCad: «arriba» = hacia el borde superior de la placa (lado de la muesca de la antena).",
             "Rotacion = la que va en el CPL (`ocx-cpl-jlcpcb.csv`). Dibujo de cada huella en "
             "[`pin1-polaridad.png`](pin1-polaridad.png): pad de referencia en rojo, nets en los pads clave.", "",
             "| Ref | Valor | LCSC | Huella | Rot. CPL | Centro CPL (mm) | Pad ref. | Pad ref. respecto al centro | Nets (pad ref. / otros) | Que comprobar en el 3D | Riesgo si esta girado |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    n = len(REFS)
    cols = 5
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4.2))
    for ax, ref in zip(axes.flat, REFS):
        f = fps[ref]
        pl = pads[ref]
        key, what, risk = INFO[ref]
        kp = [p for p in pl if p["num"] == key]
        if not kp:
            kp = [p for p in pl if p["num"] == "1"]
        kp = kp[0]
        dx, dy = kp["pos"][0] - f["pos"][0], kp["pos"][1] - f["pos"][1]
        q = quadrant(dx, dy)
        c = cplrows.get(ref, {})
        others = sorted({(p["num"], p["net"].split("/")[-1]) for p in pl if p["num"] and p["num"] != key},
                        key=lambda x: (len(x[0]), x[0]))
        if len(others) > 6:
            others_s = f"{len(others)} pads"
        else:
            others_s = ", ".join(f"{a}:{b or 'NC'}" for a, b in others)
        nets = f"**{key}:{kp['net'].split('/')[-1] or 'NC'}** / {others_s}"
        lines.append(f"| {ref} | {f['value']} | {f['lcsc']} | {f['fpid'].split(':')[-1]} | {c.get('Rotation', '?')} | "
                     f"{c.get('Mid X', '')}, {c.get('Mid Y', '')} | {key} | {q} (dx={dx:+.2f}, dy={dy:+.2f}) | {nets} | {what} | {risk} |")
        # dibujo
        allx, ally = [], []
        for p in pl:
            for ln, ps in p["cu_poly"].items():
                if ln not in ("F.Cu", "B.Cu"):
                    continue
                for poly in ps:
                    ring = poly[0]
                    isk = p is kp
                    ax.add_patch(MplPoly(ring, closed=True, fc="#d62728" if isk else "#c9a227",
                                         ec="k", lw=0.4, alpha=0.95 if isk else 0.75))
                    allx += [x for x, y in ring]
                    ally += [y for x, y in ring]
                break
            if p["drill"][0] > 0:
                ax.add_patch(plt.Circle(p["pos"], min(p["drill"]) / 2, fc="white", ec="k", lw=0.3))
        if allx:
            pad = 0.6
            ax.set_xlim(min(allx) - pad, max(allx) + pad)
            ax.set_ylim(max(ally) + pad, min(ally) - pad)  # Y hacia abajo
        ax.plot(*f["pos"], "+", color="blue", ms=10)
        ax.annotate(key, kp["pos"], color="white", ha="center", va="center", fontsize=7, weight="bold")
        ax.set_aspect("equal")
        ax.set_title(f"{ref}  {f['value']}\nrot {c.get('Rotation', '?')}  pad {key}: {q}", fontsize=9)
        ax.tick_params(labelsize=6)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle("OCX - pad de referencia (rojo) y centro de colocacion (+ azul), vista superior", fontsize=12)
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    lines += ["", "Notas:",
              "- JLC aplica su propia rotacion de libreria; si en su visor el punto de pin 1 del modelo 3D no cae en el pad indicado, "
              "corregir la rotacion en la web de JLC (o en el CPL) en multiplos de 90 grados, nunca la huella en KiCad.",
              "- En diodos KiCad numera el catodo como pad 1 (D2, D3). D1 es bidireccional.",
              "- J10: ademas del pin A1, comprobar que la boca del USB-C sobresale/enrasa con el borde inferior."]
    open(md, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:5])
