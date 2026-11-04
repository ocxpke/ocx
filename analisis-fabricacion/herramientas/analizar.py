#!/usr/bin/env python3
"""Análisis de fabricación de la placa OCX (solo lectura).

Lee la PCB/esquemático de salida/fuente/hardware (lo que exportó generar.sh a
partir del commit) y los CSV que generó kicad-cli, y escribe tablas en
../resultados/. No modifica hardware/ ni genera ficheros para fabricar.

Uso: python3 -I herramientas/analizar.py [directorio_salida] [directorio_resultados]
"""
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from sexp import parse, children, child, prop  # noqa: E402

SALIDA = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "..", "salida"))
RES = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, "..", "resultados"))
FUENTE = os.path.join(SALIDA, "fuente", "hardware")
os.makedirs(RES, exist_ok=True)

FT_CENTER_ESPERADAS = ["J2", "J3", "J5", "J10"] + [f"SW{i}" for i in range(1, 17)]
POLARIDAD = ["U1", "U2", "U5", "U6", "U7", "U8", "D1", "D2", "D3", "Y1", "C40", "J5", "J2", "J3"]
DNP_ESPERADAS = ["U4", "J6", "J7"] + [f"TP{i}" for i in range(1, 13)]


# --------------------------------------------------------------------------- geometría
def rot_local_a_placa(fx, fy, ang, px, py):
    """Coordenadas de placa (Y hacia abajo, como en KiCad) de un punto local de la huella.

    KiCad guarda la posición del pad en el sistema de la huella sin rotar y la
    orientación de la huella en grados, positivo = antihorario visto desde arriba.
    """
    a = math.radians(ang)
    return (fx + px * math.cos(a) + py * math.sin(a),
            fy - px * math.sin(a) + py * math.cos(a))


def bbox_pad(cx, cy, ang, w, h):
    """Caja envolvente alineada a ejes de un pad rectangular/ovalado/circular."""
    a = math.radians(ang)
    hx = abs(w / 2 * math.cos(a)) + abs(h / 2 * math.sin(a))
    hy = abs(w / 2 * math.sin(a)) + abs(h / 2 * math.cos(a))
    return (cx - hx, cy - hy, cx + hx, cy + hy)


def lado_cardinal(dx, dy, tol=0.05):
    """Describe dónde cae (dx,dy) respecto al centro, en vista superior de la placa."""
    v = "arriba" if dy < -tol else ("abajo" if dy > tol else "")
    h = "izquierda" if dx < -tol else ("derecha" if dx > tol else "")
    return "-".join(p for p in (v, h) if p) or "centro"


# --------------------------------------------------------------------------- PCB
pcb = parse(open(os.path.join(FUENTE, "ocxPrototype.kicad_pcb"), encoding="utf-8").read())


class Huella:
    def __init__(self, n):
        self.n = n
        self.ref = prop(n, "Reference")
        self.lib = n[1]
        self.nombre = self.lib.split(":")[-1]
        at = child(n, "at")
        self.x, self.y = float(at[1]), float(at[2])
        self.rot = float(at[3]) if len(at) > 3 else 0.0
        self.capa = child(n, "layer")[1]
        attr = child(n, "attr") or ["attr"]
        self.attr = attr[1:]
        self.dnp = "dnp" in self.attr
        self.excl_pos = "exclude_from_pos_files" in self.attr
        self.excl_bom = "exclude_from_bom" in self.attr
        self.smd = "smd" in self.attr
        self.tht = "through_hole" in self.attr
        self.ft_origin = prop(n, "FT Origin")
        self.lcsc = prop(n, "LCSC")
        self.mpn = prop(n, "MPN")
        self.valor = prop(n, "Value")
        self.pads = []
        for p in children(n, "pad"):
            pat = child(p, "at")
            px, py = float(pat[1]), float(pat[2])
            pang = float(pat[3]) if len(pat) > 3 else 0.0  # orientación absoluta del pad
            size = child(p, "size")
            w, h = float(size[1]), float(size[2])
            net = child(p, "net")
            netname = (net[-1] if net else "") or ""
            layers = child(p, "layers")[1:]
            drill = child(p, "drill")
            bx, by = rot_local_a_placa(self.x, self.y, self.rot, px, py)
            self.pads.append(dict(num=p[1], tipo=p[2], forma=p[3], lx=px, ly=py, ang=pang,
                                  w=w, h=h, net=netname, layers=layers, drill=drill,
                                  bx=bx, by=by, bbox=bbox_pad(bx, by, pang, w, h)))

    # Centro según Fabrication Toolkit: caja envolvente de TODOS los pads
    # (incluidos NPTH y pads mecánicos), calculada con la huella a 0° si su
    # rotación no es múltiplo de 90°, y devuelta a la rotación real.
    def centro_pads_ft(self):
        if not self.pads:
            return self.x, self.y
        if self.rot % 90 != 0:
            bbs = [bbox_pad(p["lx"], p["ly"], p["ang"] - self.rot, p["w"], p["h"]) for p in self.pads]
            cx = (min(b[0] for b in bbs) + max(b[2] for b in bbs)) / 2
            cy = (min(b[1] for b in bbs) + max(b[3] for b in bbs)) / 2
            return rot_local_a_placa(self.x, self.y, self.rot, cx, cy)
        bbs = [p["bbox"] for p in self.pads]
        return ((min(b[0] for b in bbs) + max(b[2] for b in bbs)) / 2,
                (min(b[1] for b in bbs) + max(b[3] for b in bbs)) / 2)

    def centro_pads_electricos(self):
        """Caja envolvente solo de pads numerados con cobre (sin NPTH ni pads de pasta)."""
        ps = [p for p in self.pads if p["num"] and p["tipo"] != "np_thru_hole"]
        bbs = [p["bbox"] for p in ps] or [p["bbox"] for p in self.pads]
        return ((min(b[0] for b in bbs) + max(b[2] for b in bbs)) / 2,
                (min(b[1] for b in bbs) + max(b[3] for b in bbs)) / 2)

    def centro_fab(self):
        """Centro de la caja de las líneas de F.Fab (aprox. el cuerpo de la pieza)."""
        pts = []
        for g in [c for c in self.n[1:] if isinstance(c, list) and c and c[0] in ("fp_line", "fp_rect", "fp_poly", "fp_arc", "fp_circle")]:
            lay = child(g, "layer")
            if not lay or lay[1] != "F.Fab":
                continue
            for k in ("start", "end", "mid", "center"):
                c = child(g, k)
                if c:
                    pts.append((float(c[1]), float(c[2])))
            pl = child(g, "pts")
            if pl:
                pts += [(float(q[1]), float(q[2])) for q in children(pl, "xy")]
        if not pts:
            return None
        lx = (min(q[0] for q in pts) + max(q[0] for q in pts)) / 2
        ly = (min(q[1] for q in pts) + max(q[1] for q in pts)) / 2
        return rot_local_a_placa(self.x, self.y, self.rot, lx, ly)

    def origen_ft(self):
        """Replica _get_origin_from_footprint() de Fabrication Toolkit."""
        tipo = "Anchor" if self.smd else "Center"
        if self.ft_origin is not None:
            o = self.ft_origin.strip().capitalize()
            if o in ("Anchor", "Center"):
                tipo = o
        return tipo

    def pad(self, num):
        return [p for p in self.pads if p["num"] == num]


huellas = [Huella(n) for n in children(pcb, "footprint")]
por_ref = defaultdict(list)
for h in huellas:
    por_ref[h.ref].append(h)


def H(ref):
    return por_ref[ref][0]


# Tabla de rotaciones de Fabrication Toolkit (transformations.csv), copiada
# literalmente de bennymeg/fabrication-toolkit@7f627b6 (2026-09-29) para las
# entradas relevantes. El orden importa: gana la primera que casa.
FT_DB = [
    ("^Bosch_LGA-", 90), ("^CP_EIA-", 180), ("^CP_Elec_", 180), ("^C_Elec_", 180),
    ("^DFN-", 270), ("^D_SOT-23", 180), ("^HTSSOP-", 270), ("^JST_GH_SM", 180),
    ("^JST_PH_S", 180), ("^LQFP-", 270), ("^MSOP-", 270), ("^PowerPAK_SO-8_Single", 270),
    ("^QFN-", 90), ("^R_Array_Concave_", 90), ("^R_Array_Convex_", 90), ("^SC-74-6", 180),
    ("^SOIC-", 270), ("^SOIC-16_", 270), ("^SOIC-8_", 270), ("^SOIC127P798X216-8N", -90),
    ("^SOP-(?!18_)", 270), ("^SOP-18_", 0), ("^SOP-4_", 0), ("^SOT-143", 180),
    ("^SOT-223", 180), ("^SOT-23", 180), ("^SOT-353", 180), ("^SOT-363", 180),
    ("^SOT-89", 180), ("^SSOP-", 270), ("^SW_SPST_B3", 90), ("^TDSON-8-1", 270),
    ("^TO-277", 90), ("^TQFP-", 270), ("^TSOT-23", 180), ("^TSSOP-", 270),
    ("^UDFN-10", 270), ("^USON-10", 270), ("^VSON-8_", 270), ("^VSSOP-10_-", 270),
    ("^VSSOP-8_", 180), ("^VSSOP-8_3.0x3.0mm_P0.65mm", 270), ("^qfn-", 90),
]


def ft_rot_db(nombre, lib):
    for rx, r in FT_DB:
        if re.search(rx, nombre):
            return r, rx
    for rx, r in FT_DB:
        if re.search(rx, lib):
            return r, rx
    return 0, ""


def fmt(v, d=3):
    return f"{v:.{d}f}"


def norm360(a):
    a = a % 360.0
    return 0.0 if abs(a - 360.0) < 1e-9 else a


# --------------------------------------------------------------------------- CSV de kicad-cli
def leer_csv(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


cpl = leer_csv(os.path.join(SALIDA, "cpl", "cpl-kicad-cli.csv"))
cpl_dnp = leer_csv(os.path.join(SALIDA, "cpl", "cpl-kicad-cli-con-dnp.csv"))
bom = leer_csv(os.path.join(SALIDA, "bom", "bom-sin-dnp.csv"))
bom_full = leer_csv(os.path.join(SALIDA, "bom", "bom-completa.csv"))
cpl_por_ref = {r["Ref"]: r for r in cpl}

salida_md = []


def md(s=""):
    salida_md.append(s)


# --------------------------------------------------------------------------- (a) FT Origin
md("## (a) Huellas con «FT Origin» = Center\n")
md("Coordenadas en mm, sistema de KiCad. El CPL de kicad-cli escribe X igual y **Y con el signo cambiado** "
   "(Y hacia arriba); Fabrication Toolkit hace lo mismo y, como esta placa no tiene origen auxiliar "
   "(aux_axis_origin) definido, ambos usan el mismo origen absoluto.\n")
md("| Ref | Huella | Rot | Ancla (CPL kicad-cli) X / Y_CPL | Centro de pads (FT) X / Y_CPL | ΔX / ΔY_CPL | |Δ| | Centro solo pads eléctricos X / Y_CPL | Centro F.Fab (cuerpo) X / Y_CPL |")
md("|---|---|---:|---|---|---|---:|---|---|")
filas_a = []
center_reales = sorted([h.ref for h in huellas if (h.ft_origin or "").strip().capitalize() == "Center"],
                       key=lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0)))
for ref in center_reales:
    h = H(ref)
    cx, cy = h.centro_pads_ft()
    ex, ey = h.centro_pads_electricos()
    c = cpl_por_ref.get(ref)
    ax, ay = (float(c["PosX"]), float(c["PosY"])) if c else (h.x, -h.y)
    dx, dy = cx - ax, (-cy) - ay
    filas_a.append(dict(ref=ref, huella=h.nombre, rot=h.rot, ancla_x=ax, ancla_y_cpl=ay,
                        centro_x=round(cx, 4), centro_y_cpl=round(-cy, 4), dx=round(dx, 4), dy=round(dy, 4),
                        centro_elec_x=round(ex, 4), centro_elec_y_cpl=round(-ey, 4)))
    md(f"| {ref} | {h.nombre} | {h.rot:g} | {fmt(ax)} / {fmt(ay)} | **{fmt(cx)} / {fmt(-cy)}** | "
       f"{fmt(dx)} / {fmt(dy)} | {fmt(math.hypot(dx, dy))} | {fmt(ex)} / {fmt(-ey)} | "
       + (f"{fmt(h.centro_fab()[0])} / {fmt(-h.centro_fab()[1])} |" if h.centro_fab() else "— |"))
    filas_a[-1]["fab_x"], filas_a[-1]["fab_y_cpl"] = (round(h.centro_fab()[0], 4), round(-h.centro_fab()[1], 4)) if h.centro_fab() else (None, None)
md()
extra = set(center_reales) ^ set(FT_CENTER_ESPERADAS)
md(f"Huellas con FT Origin=Center en la placa: {len(center_reales)}. "
   f"Diferencias con la lista esperada: {sorted(extra) if extra else 'ninguna'}.\n")

# Huellas para las que FT elegiría un origen distinto al ancla sin que el campo lo diga
md("### Origen que usaría Fabrication Toolkit en el resto de huellas montadas\n")
md("FT usa por defecto «Anchor» en SMD y «Center» en todo lo demás (THT o sin atributo); "
   "un campo vacío no cambia ese defecto.\n")
md("| Ref | attr | FT Origin (campo) | Origen FT efectivo | |Δ| ancla→centro pads (mm) |")
md("|---|---|---|---|---:|")
for h in sorted(huellas, key=lambda h: h.ref):
    if h.dnp or h.excl_pos or h.ref in center_reales:
        continue
    o = h.origen_ft()
    cx, cy = h.centro_pads_ft()
    d = math.hypot(cx - h.x, cy - h.y)
    if o == "Center" or d > 0.05:
        md(f"| {h.ref} | {' '.join(h.attr)} | {h.ft_origin!r} | {o} | {fmt(d)} |")
md()

# --------------------------------------------------------------------------- (b) pin 1 / polaridad
md("## (b) Pin 1, polaridad y rotación\n")
md("«Pin 1 en placa» = dónde queda el pad 1 respecto al centro de la pieza vista desde arriba, "
   "con la placa orientada como en KiCad (Y hacia abajo de la pantalla). Es lo que hay que ver en el "
   "visor de JLC: el marcador de pin 1 / polaridad del modelo debe caer en ese lado.\n")
md("| Ref | Huella | Rot KiCad (CPL kicad-cli) | Pad 1 → red | Pin 1 en placa | Offset tabla FT | Rot FT (auto‑translate) |")
md("|---|---|---:|---|---|---:|---:|")
pol = {}
for ref in POLARIDAD:
    h = H(ref)
    cx, cy = h.centro_pads_electricos()
    p1 = h.pad("1")[0]
    off, rx = ft_rot_db(h.nombre, h.lib.split(":")[0])
    c = cpl_por_ref.get(ref)
    rot_cpl = float(c["Rot"]) if c else None
    pol[ref] = dict(huella=h.nombre, rot=h.rot, rot_cpl=rot_cpl, pad1_net=p1["net"],
                    pin1=lado_cardinal(p1["bx"] - cx, p1["by"] - cy),
                    ft_off=off, ft_regex=rx, ft_rot=norm360(h.rot + off),
                    pads={p["num"]: p["net"] for p in h.pads if p["num"]})
    md(f"| {ref} | {h.nombre} | {h.rot:g} ({rot_cpl:g}) | {p1['net']} | {pol[ref]['pin1']} | "
       f"{off:+g}{' (' + rx + ')' if rx else ''} | {norm360(h.rot + off):g} |")
md()
md("### Redes por pad\n")
for ref in POLARIDAD:
    pads = pol[ref]["pads"]
    keys = sorted(pads, key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0, k))
    if ref == "U1":
        keys = [k for k in keys if k in ("1", "16", "17", "32", "33", "48", "49", "64", "65")]
    if ref in ("J2", "J3"):
        # orden físico de arriba abajo en la placa
        keys = sorted(keys, key=lambda k: H(ref).pad(k)[0]["by"])
        md(f"- **{ref}** ({H(ref).valor}), de arriba abajo en la placa: "
           + ", ".join(f"{k}={pads[k]}" for k in keys))
        continue
    md(f"- **{ref}** ({H(ref).valor}, {H(ref).mpn}): " + ", ".join(f"{k}={pads[k]}" for k in keys))
md()

# Pads sin número / sin red en U1 (pads de pasta de la pastilla térmica)
u1 = H("U1")
sin_num = [p for p in u1.pads if not p["num"]]
md(f"U1: {len(sin_num)} pads sin número; capas: {sorted(set(tuple(p['layers']) for p in sin_num))}. "
   f"Pad 65 (EP): {[(p['net'], p['w'], p['h'], tuple(p['layers'])) for p in u1.pad('65')]}\n")

# --------------------------------------------------------------------------- (c) BOM/CPL
md("## (c) DNP, BOM y CPL\n")
bom_refs = set()
for r in bom:
    bom_refs.update(x.strip() for x in r["Designator"].split(","))
cpl_refs = {r["Ref"] for r in cpl}
cpl_dnp_refs = {r["Ref"] for r in cpl_dnp}
dnp_pcb = sorted({h.ref for h in huellas if h.dnp})
dnp_sch = sorted({x.strip() for r in bom_full if r["DNP"] for x in r["Designator"].split(",")})
montadas_pcb = {h.ref for h in huellas if not h.dnp and not h.excl_bom}
md(f"- DNP en la PCB (attr dnp): {', '.join(dnp_pcb)}")
md(f"- DNP en el esquemático (BOM completa): {', '.join(dnp_sch)}")
md(f"- DNP esperadas que aparecen en la BOM sin DNP: {sorted(set(DNP_ESPERADAS) & bom_refs) or 'ninguna'}")
md(f"- DNP esperadas que aparecen en el CPL (--exclude-dnp): {sorted(set(DNP_ESPERADAS) & cpl_refs) or 'ninguna'}")
md(f"- DNP esperadas que NO están marcadas DNP en PCB: {sorted(set(DNP_ESPERADAS) - set(dnp_pcb)) or 'ninguna'}; "
   f"en esquemático: {sorted(set(DNP_ESPERADAS) - set(dnp_sch)) or 'ninguna'}")
md(f"- DNP no esperadas: PCB {sorted(set(dnp_pcb) - set(DNP_ESPERADAS)) or 'ninguna'}, "
   f"esquemático {sorted(set(dnp_sch) - set(DNP_ESPERADAS)) or 'ninguna'}")
md(f"- Refs en BOM y no en CPL: {sorted(bom_refs - cpl_refs) or 'ninguna'}; en CPL y no en BOM: {sorted(cpl_refs - bom_refs) or 'ninguna'}")
md(f"- Huellas montadas en PCB que faltan en BOM: {sorted(montadas_pcb - bom_refs) or 'ninguna'}")
md(f"- Nº de piezas montadas: BOM {len(bom_refs)}, CPL {len(cpl_refs)} "
   f"(CPL con DNP: {len(cpl_dnp_refs)}; diferencia = {sorted(cpl_dnp_refs - cpl_refs)})")
sin_lcsc = [r for r in bom if not r["LCSC"].strip()]
sin_mpn = [r for r in bom if not r["MPN"].strip()]
md(f"- Filas de BOM montadas sin LCSC: {[r['Designator'] for r in sin_lcsc] or 'ninguna'}; sin MPN: {[r['Designator'] for r in sin_mpn] or 'ninguna'}")
mal_lcsc = [r["Designator"] for r in bom if r["LCSC"].strip() and not re.fullmatch(r"C\d+", r["LCSC"].strip())]
md(f"- LCSC con formato distinto de C<número>: {mal_lcsc or 'ninguno'}")
# LCSC repetido con valores/huellas distintas, o MPN con varios LCSC
by_lcsc = defaultdict(set)
by_mpn = defaultdict(set)
for r in bom:
    by_lcsc[r["LCSC"]].add((r["Comment"], r["Footprint"].split(":")[-1], r["MPN"]))
    by_mpn[r["MPN"]].add(r["LCSC"])
md(f"- Mismo LCSC con distinto valor/huella/MPN: {[(k, sorted(v)) for k, v in by_lcsc.items() if len({x[1] for x in v}) > 1 or len({x[2] for x in v}) > 1] or 'ninguno'}")
md(f"- Mismo MPN con varios LCSC: {[(k, sorted(v)) for k, v in by_mpn.items() if len(v) > 1] or 'ninguno'}")
# Coherencia de campos esquemático (BOM) vs PCB
dif = []
for r in bom:
    for ref in [x.strip() for x in r["Designator"].split(",")]:
        h = H(ref)
        if (h.lcsc or "") != r["LCSC"] or (h.mpn or "") != r["MPN"]:
            dif.append((ref, r["LCSC"], h.lcsc, r["MPN"], h.mpn))
md(f"- LCSC/MPN distintos entre esquemático y PCB: {dif or 'ninguno'}")
tht = sorted(r for r in cpl_refs if H(r).tht)
md(f"- Piezas THT en el CPL ({len(tht)}): {', '.join(tht)}")
md(f"- Cara de las piezas del CPL: {dict(Counter(r['Side'] for r in cpl))}")
md(f"- Cabecera del CPL de kicad-cli: {list(cpl[0].keys())}")
md()

# DNP según FT (BOM): FT incluye DNP en la BOM salvo que se marque «Exclude DNP».
md("### Qué haría Fabrication Toolkit con las DNP\n")
md("FT nunca pone una DNP en el CPL, pero **sí la mete en la BOM** salvo que se active «Exclude DNP "
   "components from BOM» (por defecto desactivado). El «LCSC Part #» que pondría:\n")
md("| Ref | LCSC | MPN | «LCSC Part #» en BOM de FT |")
md("|---|---|---|---|")
for ref in DNP_ESPERADAS:
    h = H(ref)
    val = None
    for k in ["LCSC Part #", "LCSC Part", "LCSC PN", "LCSC P/N", "LCSC Part No.", "LCSC Part Number",
              "JLCPCB Part #", "JLCPCB Part", "JLCPCB PN", "JLCPCB P/N", "JLCPCB Part No.", "JLCPCB Part Number",
              "LCSC", "JLC", "MPN", "Mpn", "mpn"]:
        v = prop(h.n, k)
        if v:
            val = v
            break
    md(f"| {ref} | {h.lcsc or '—'} | {h.mpn or '—'} | {val or '(vacío)'} |")
md()

# --------------------------------------------------------------------------- reglas / geometría
md("## Geometría de fabricación (medida en la PCB)\n")
segs = children(pcb, "segment") + children(pcb, "arc")
anchos = Counter(float(child(s, "width")[1]) for s in segs)
vias = children(pcb, "via")
via_sz = Counter((float(child(v, "size")[1]), float(child(v, "drill")[1])) for v in vias)
md(f"- Pistas: {len(segs)}; anchos usados (mm: nº): {dict(sorted(anchos.items()))}")
md(f"- Vías: {len(vias)}; (diámetro, taladro): {dict(via_sz)}; anillo mínimo vía = "
   f"{min((d - t) / 2 for d, t in via_sz):.3f} mm" if vias else "- Sin vías")
vtypes = Counter(child(v, "type")[1] if child(v, "type") else "through" for v in vias)
md(f"- Tipos de vía: {dict(vtypes)}")
taladros = Counter()
anillos = []
ranuras = []
for h in huellas:
    for p in h.pads:
        if p["drill"]:
            d = p["drill"][1:]
            if d and d[0] == "oval":
                dx, dy = float(d[1]), float(d[2]) if len(d) > 2 and not isinstance(d[2], list) else float(d[1])
                ranuras.append((h.ref, p["num"], p["tipo"], dx, dy))
                taladros[(p["tipo"], f"{dx}x{dy}")] += 1
                if p["tipo"] == "thru_hole":
                    anillos.append(((min(p["w"], p["h"]) - min(dx, dy)) / 2, h.ref, p["num"]))
            else:
                dd = float(d[0]) if d and not isinstance(d[0], list) else 0
                taladros[(p["tipo"], dd)] += 1
                if p["tipo"] == "thru_hole":
                    anillos.append(((min(p["w"], p["h"]) - dd) / 2, h.ref, p["num"]))
md(f"- Taladros en pads (tipo, Ø): {dict(sorted(taladros.items(), key=str))}")
anillos.sort()
md(f"- Anillo PTH mínimo en pads: {anillos[0][0]:.3f} mm ({anillos[0][1]} pad {anillos[0][2]}); "
   f"los 5 menores: {[(round(a, 3), r, n) for a, r, n in anillos[:5]]}")
md(f"- Ranuras (óvalos): {ranuras}")
# Borde de placa
edge = [g for g in children(pcb, "gr_line") + children(pcb, "gr_arc") + children(pcb, "gr_rect") + children(pcb, "gr_circle")
        if child(g, "layer") and child(g, "layer")[1] == "Edge.Cuts"]
pts = []
for g in edge:
    for k in ("start", "end", "mid", "center"):
        c = child(g, k)
        if c:
            pts.append((float(c[1]), float(c[2])))
if pts:
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    md(f"- Edge.Cuts: {len(edge)} elementos; caja {min(xs):.2f},{min(ys):.2f} → {max(xs):.2f},{max(ys):.2f} "
       f"= {max(xs) - min(xs):.2f} × {max(ys) - min(ys):.2f} mm")
# Textos de serigrafía
txt_bajos = []
for t in children(pcb, "gr_text"):
    lay = child(t, "layer")[1]
    if "Silk" in lay:
        font = child(child(t, "effects"), "font")
        sz = child(font, "size")
        th = child(font, "thickness")
        face = child(font, "face")
        txt_bajos.append((t[1][:30], lay, float(sz[1]), float(sz[2]), float(th[1]) if th else None, face[1] if face else ""))
md(f"- Textos sueltos en serigrafía (texto, capa, alto, ancho, grosor, fuente): {txt_bajos}")
fp_txt_min = []
for h in huellas:
    for pr in children(h.n, "property") + children(h.n, "fp_text"):
        lay = child(pr, "layer")
        if not lay or "Silk" not in lay[1]:
            continue
        hid = child(pr, "hide")
        if hid and (len(hid) < 2 or hid[1] == "yes"):
            continue
        font = child(child(pr, "effects"), "font") if child(pr, "effects") else None
        if not font:
            continue
        sz = child(font, "size")
        th = child(font, "thickness")
        fp_txt_min.append((float(sz[2]), float(th[1]) if th else 0, h.ref, pr[1] if pr[0] == "property" else "fp_text"))
fp_txt_min.sort()
md(f"- Textos visibles de huellas en serigrafía: {len(fp_txt_min)}; menores (alto, grosor, ref, campo): {fp_txt_min[:6]}")
# Stackup
st = child(child(pcb, "setup"), "stackup")
capas = []
for l in children(st, "layer"):
    t = child(l, "type")
    th = child(l, "thickness")
    capas.append((l[1], t[1] if t else "", float(th[1]) if th else None))
tot = sum(c[2] for c in capas if c[2] and "Mask" not in c[0])
md(f"- Stackup en la PCB: {[(c[0], c[2]) for c in capas if c[2]]}; suma sin máscara = {tot:.4f} mm; "
   f"acabado: {child(st, 'copper_finish')[1]}")
md()

# --------------------------------------------------------------------------- Gerber y taladros
md("## Ficheros generados\n")
gdir = os.path.join(SALIDA, "gerber")
for f in sorted(os.listdir(gdir)):
    md(f"- `{f}` ({os.path.getsize(os.path.join(gdir, f))} B)")
for f in ("ocxPrototype-PTH.drl", "ocxPrototype-NPTH.drl"):
    t = open(os.path.join(gdir, f), encoding="utf-8").read()
    tools = re.findall(r"^T(\d+)C([\d.]+)", t, re.M)
    hits = Counter()
    cur = None
    for line in t.splitlines():
        m = re.match(r"^T(\d+)$", line)
        if m:
            cur = m.group(1)
        elif cur and re.match(r"^X[-\d.]+Y[-\d.]+", line):
            hits[cur] += 1
    md(f"- {f}: unidades {'METRIC' if 'METRIC' in t else '?'}, herramientas {[(float(c), hits[n]) for n, c in tools]}, "
       f"ranuras G85: {t.count('G85')}")
md()

# --------------------------------------------------------------------------- rellenos de zona
md("## Rellenos de zona del commit\n")
md("Comparación del cobre exportado con --check-zones (rellena si hace falta) y sin él "
   "(rellenos tal cual están guardados en el commit). Se ignoran cabeceras/atributos.\n")
for f in sorted(os.listdir(os.path.join(SALIDA, "gerber-sin-refill"))):
    if not re.search(r"\.(gtl|gbl|g\d)$", f):
        continue
    a = [l for l in open(os.path.join(SALIDA, "gerber", f)) if not l.startswith(("G04", "%TF"))]
    b = [l for l in open(os.path.join(SALIDA, "gerber-sin-refill", f)) if not l.startswith(("G04", "%TF"))]
    ndif, maxd = 0, 0.0
    if len(a) != len(b):
        md(f"- {f}: **distinto nº de líneas** ({len(a)} vs {len(b)}) → rellenos desactualizados")
        continue
    for la, lb in zip(a, b):
        if la != lb:
            ndif += 1
            ca = [int(v) for v in re.findall(r"[XY](-?\d+)", la)]
            cb = [int(v) for v in re.findall(r"[XY](-?\d+)", lb)]
            if len(ca) == len(cb):
                maxd = max([maxd] + [abs(x - y) / 1e6 for x, y in zip(ca, cb)])
            else:
                maxd = float("inf")
    md(f"- {f}: {ndif} líneas distintas, diferencia máxima de coordenada {maxd * 1000:.4f} µm")
md()

open(os.path.join(RES, "analisis.md"), "w", encoding="utf-8").write("\n".join(salida_md) + "\n")
json.dump(dict(ft_center=filas_a, polaridad=pol), open(os.path.join(RES, "analisis.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print("\n".join(salida_md))
