#!/usr/bin/env python3
"""Comprueba la geometria volcada por dump_board.py contra las capacidades de
JLCPCB (4 capas, 1,6 mm, ENIG).

Uso: python3 check_jlcpcb.py board.json salida.md salida.json

Las cifras de CAPS son SUPUESTOS tomados de la tabla publica de capacidades de
JLCPCB (multicapa); jlcpcb.com no era accesible desde el entorno donde se
genero el informe, asi que hay que confirmarlas antes de pedir.
"""
import json
import math
import sys
from collections import defaultdict

from shapely.geometry import LineString, Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import set_precision

# --- Capacidades JLCPCB (mm). Editar si cambian. ---------------------------
CAPS = {
    "layers": 4,
    "thickness": 1.6,
    "track_min": 0.09,          # multicapa, 1 oz exterior / 0,5 oz interior
    "track_rec": 0.127,
    "clearance_min": 0.09,      # pista-pista / pad-pista multicapa
    "clearance_rec": 0.127,
    "via_drill_min": 0.15,      # < 0,30 mm puede tener sobrecoste
    "via_drill_free": 0.30,
    "via_diam_min": 0.25,
    "via_annular_min": 0.075,
    "via_annular_rec": 0.15,
    "pth_drill_min": 0.20,
    "pth_annular_min": 0.13,
    "pth_annular_rec": 0.25,
    "npth_drill_min": 0.50,
    "drill_max": 6.30,
    "plated_slot_min": 0.50,
    "hole_to_hole_min": 0.20,   # mismo net (vias)
    "hole_to_hole_diffnet": 0.25,
    "pth_hole_to_hole": 0.45,   # pads PTH
    "hole_to_copper_min": 0.20, # borde de taladro a cobre de otro net
    "mask_dam_min": 0.10,       # verde; otros colores ~0,13
    "copper_edge_min": 0.30,    # fresado (0,40 con V-cut)
    "router_slot_min": 1.00,
    "router_inner_radius": 0.50,
    "silk_line_min": 0.15,
    "silk_text_h_min": 1.00,
}

R = []  # filas de resultado


def add(cat, item, value, limit, ok, note=""):
    R.append({"cat": cat, "item": item, "value": value, "limit": limit,
              "status": ok, "note": note})


def rings_to_poly(rings):
    if len(rings[0]) < 3:
        return None
    return Polygon(rings[0], [r for r in rings[1:] if len(r) >= 3])


def polyset_geom(ps):
    polys = [p for p in (rings_to_poly(r) for r in ps) if p is not None]
    if not polys:
        return None
    g = unary_union([p.buffer(0) for p in polys])
    return g


def arc_points(s, m, e, n=16):
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return [s, e]
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a1 = math.atan2(y1 - uy, x1 - ux)
    a2 = math.atan2(y2 - uy, x2 - ux)
    a3 = math.atan2(y3 - uy, x3 - ux)

    def norm(a):
        return a % (2 * math.pi)
    # sentido que pasa por el punto medio
    ccw = norm(a2 - a1) < norm(a3 - a1)
    span = norm(a3 - a1) if ccw else -norm(a1 - a3)
    return [(ux + r * math.cos(a1 + span * i / n), uy + r * math.sin(a1 + span * i / n)) for i in range(n + 1)]


def main(src, md_out, json_out):
    d = json.load(open(src))
    st = d["settings"]
    cu_layers = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

    # ---------------- Stackup
    add("Stackup", "Capas de cobre", st["copper_layers"], CAPS["layers"],
        "OK" if st["copper_layers"] == CAPS["layers"] else "FALLO")
    add("Stackup", "Grosor (mm)", st["thickness"], CAPS["thickness"],
        "OK" if abs(st["thickness"] - CAPS["thickness"]) < 1e-6 else "FALLO",
        "Acabado ENIG: se elige en el pedido, no esta en los Gerber.")

    # ---------------- Contorno
    outline = [rings_to_poly(r) for r in d["outline"]]
    board = unary_union(outline)
    add("Contorno", "Contornos cerrados (Edge.Cuts)", len(outline), 1,
        "OK" if len(outline) == 1 and board.is_valid else "FALLO",
        "Un unico poligono cerrado y valido." if board.is_valid else "Poligono invalido")
    minx, miny, maxx, maxy = board.bounds
    add("Contorno", "Dimensiones (mm)", f"{maxx-minx:.2f} x {maxy-miny:.2f}", "-", "INFO")
    # vertices concavos (esquinas interiores) -> el fresado las redondea
    ext = list(board.exterior.coords)[:-1]
    if not board.exterior.is_ccw:
        ext = ext[::-1]
    concave = []
    n = len(ext)
    for i in range(n):
        a, b, c = ext[i - 1], ext[i], ext[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        la = math.hypot(b[0] - a[0], b[1] - a[1])
        lc = math.hypot(c[0] - b[0], c[1] - b[1])
        if cross < -1e-6 and la > 0.3 and lc > 0.3:  # esquina viva concava
            concave.append(b)
    notch = None
    if len(concave) >= 2:
        xs = sorted(p[0] for p in concave)
        ys = sorted(p[1] for p in concave)
        # La muesca es la zona entre las esquinas interiores y el borde
        notch_w = xs[-1] - xs[0]
        notch_d = ys[-1] - miny
        notch = Polygon([(xs[0], miny), (xs[-1], miny), (xs[-1], ys[-1]), (xs[0], ys[-1])])
        add("Muesca antena", "Anchura x profundidad (mm)", f"{notch_w:.2f} x {notch_d:.2f}",
            f">= {CAPS['router_slot_min']} de ancho", "OK" if notch_w >= CAPS["router_slot_min"] else "FALLO",
            f"Esquinas interiores en {', '.join('(%.1f, %.1f)' % p for p in concave)}")
        add("Muesca antena", "Radio de esquinas interiores", "0 (vivas)",
            f">= {CAPS['router_inner_radius']}", "AVISO",
            "La fresa dejara radio ~0,5 mm (o mayor segun fresa). Es aceptable si nada "
            "depende de una esquina viva; si se quiere controlar, dibujar r=0,5-1 mm.")

    # ---------------- Pistas
    by_layer = defaultdict(list)
    for t in d["tracks"]:
        by_layer[t["layer"]].append(t["width"])
    for ln in cu_layers:
        if by_layer[ln]:
            w = min(by_layer[ln])
            add("Pistas", f"Anchura minima {ln}", w, CAPS["track_min"],
                "OK" if w >= CAPS["track_rec"] else ("AVISO" if w >= CAPS["track_min"] else "FALLO"))
        else:
            add("Pistas", f"Anchura minima {ln}", "sin pistas", CAPS["track_min"], "OK",
                "Capa solo con plano")

    # ---------------- Vias
    vd = min(v["drill"] for v in d["vias"])
    vD = min(v["diam"] for v in d["vias"])
    va = min((v["diam"] - v["drill"]) / 2 for v in d["vias"])
    add("Vias", f"Taladro minimo ({len(d['vias'])} vias)", vd, CAPS["via_drill_min"],
        "OK" if vd >= CAPS["via_drill_free"] else ("AVISO" if vd >= CAPS["via_drill_min"] else "FALLO"),
        "Sin sobrecoste por via pequena" if vd >= CAPS["via_drill_free"] else "Sobrecoste")
    add("Vias", "Diametro minimo", vD, CAPS["via_diam_min"], "OK" if vD >= CAPS["via_diam_min"] else "FALLO")
    add("Vias", "Anillo minimo", round(va, 4), CAPS["via_annular_min"],
        "OK" if va >= CAPS["via_annular_rec"] else ("AVISO" if va >= CAPS["via_annular_min"] else "FALLO"))
    types = sorted({v["type"] for v in d["vias"]})
    add("Vias", "Tipos de via", ",".join(map(str, types)), "pasante", "OK" if types == [4] else "AVISO",
        "Todas pasantes (sin ciegas/enterradas/microvias)." if types == [4] else "")
    add("Vias", "Tenting", f"F={st['tent_vias_front']} B={st['tent_vias_back']}", "-", "INFO",
        "Vias cubiertas de mascara en ambas caras.")

    # ---------------- Taladros de pads
    pth = [p for p in d["pads"] if p["attr"] == 0 and p["drill"][0] > 0]
    npth = [p for p in d["pads"] if p["attr"] == 3 and p["drill"][0] > 0]
    rnd = [p for p in pth if not p["drill_oblong"]]
    slots = [p for p in pth if p["drill_oblong"]]
    pmin = min(rnd, key=lambda p: p["drill"][0])
    add("Taladros", "PTH redondo minimo", pmin["drill"][0], CAPS["pth_drill_min"],
        "OK" if pmin["drill"][0] >= CAPS["pth_drill_min"] else "FALLO", f"{pmin['ref']} pad {pmin['num']}")
    allholes = [max(p["drill"]) for p in pth + npth] + [v["drill"] for v in d["vias"]]
    add("Taladros", "Taladro maximo", max(allholes), CAPS["drill_max"],
        "OK" if max(allholes) <= CAPS["drill_max"] else "FALLO")
    if npth:
        nmin = min(npth, key=lambda p: min(p["drill"]))
        add("Taladros", "NPTH minimo", min(nmin["drill"]), CAPS["npth_drill_min"],
            "OK" if min(nmin["drill"]) >= CAPS["npth_drill_min"] else "FALLO", f"{nmin['ref']} pad {nmin['num']}")
    if slots:
        smin = min(slots, key=lambda p: min(p["drill"]))
        add("Taladros", f"Ranura metalizada minima ({len(slots)})", min(smin["drill"]), CAPS["plated_slot_min"],
            "OK" if min(smin["drill"]) >= CAPS["plated_slot_min"] else "FALLO",
            f"{smin['ref']} (carcasa USB-C)" if smin["ref"].startswith("J10") else smin["ref"])
    # anillos PTH
    worst = None
    for p in pth:
        ar = min((p["size"][0] - p["drill"][0]) / 2, (p["size"][1] - p["drill"][1]) / 2)
        if worst is None or ar < worst[0]:
            worst = (ar, p)
    ar, p = worst
    add("Taladros", "Anillo PTH minimo", round(ar, 4), CAPS["pth_annular_min"],
        "OK" if ar >= CAPS["pth_annular_rec"] else ("AVISO" if ar >= CAPS["pth_annular_min"] else "FALLO"),
        f"{p['ref']} pad {p['num']} ({p['size'][0]}/{p['drill'][0]} mm)"
        + (" - vias termicas del EP, se fabrican como vias" if p["ref"] == "U1" else ""))
    thr = [p for p in pth if p["ref"] != "U1"]
    if thr:
        ar2, p2 = min(((min((q["size"][0] - q["drill"][0]) / 2, (q["size"][1] - q["drill"][1]) / 2), q) for q in thr),
                      key=lambda x: x[0])
        add("Taladros", "Anillo PTH minimo (componentes)", round(ar2, 4), CAPS["pth_annular_min"],
            "OK" if ar2 >= CAPS["pth_annular_rec"] else ("AVISO" if ar2 >= CAPS["pth_annular_min"] else "FALLO"),
            f"{p2['ref']} pad {p2['num']}")

    # ---------------- Hole to hole
    holes = []  # (geom, net, kind, label)
    for v in d["vias"]:
        holes.append((Point(v["pos"]).buffer(v["drill"] / 2, 16), v["net"], "via", f"via {v['net']} @{v['pos']}"))
    for p in pth + npth:
        if p["drill_oblong"]:
            # aproxima ranura como segmento con extremos redondeados
            w, h = p["drill"]
            r = min(w, h) / 2
            # orientacion: usar el poligono de cobre para la direccion principal es complejo;
            # se toma un circulo del diametro menor (estimacion optimista conservadora: radio menor)
            g = Point(p["pos"]).buffer(r, 16)
        else:
            g = Point(p["pos"]).buffer(p["drill"][0] / 2, 16)
        holes.append((g, p["net"] or f"_np_{p['ref']}_{p['num']}", "npth" if p["attr"] == 3 else "pth",
                      f"{p['ref']} pad {p['num']}"))
    tree = STRtree([h[0] for h in holes])
    mn_same, mn_diff = (9e9, None), (9e9, None)
    for i, (g, net, kind, lab) in enumerate(holes):
        for j in tree.query(g.buffer(1.0)):
            if j <= i:
                continue
            g2, net2, kind2, lab2 = holes[j]
            if kind == "pth" and kind2 == "pth" and lab.split()[0] == lab2.split()[0] and lab.startswith("U1"):
                pass
            dist = g.distance(g2)
            if net == net2:
                if dist < mn_same[0]:
                    mn_same = (dist, f"{lab} / {lab2}")
            elif dist < mn_diff[0]:
                mn_diff = (dist, f"{lab} / {lab2}")
    add("Taladros", "Distancia taladro-taladro (mismo net)", round(mn_same[0], 3), CAPS["hole_to_hole_min"],
        "OK" if mn_same[0] >= CAPS["hole_to_hole_min"] else "FALLO", mn_same[1] or "")
    add("Taladros", "Distancia taladro-taladro (nets distintos)", round(mn_diff[0], 3), CAPS["hole_to_hole_diffnet"],
        "OK" if mn_diff[0] >= CAPS["hole_to_hole_diffnet"] else "FALLO", mn_diff[1] or "")

    # ---------------- Cobre por capa
    copper = {ln: [] for ln in cu_layers}  # (geom, net, label)
    for t in d["tracks"]:
        pts = arc_points(t["start"], t["mid"], t["end"]) if t["arc"] else [t["start"], t["end"]]
        if pts[0] == pts[-1] and len(pts) == 2:
            g = Point(pts[0]).buffer(t["width"] / 2, 16)
        else:
            g = LineString(pts).buffer(t["width"] / 2, 16)
        copper[t["layer"]].append((g, t["net"], f"pista {t['net']} {t['width']}mm"))
    for v in d["vias"]:
        for ln in cu_layers:
            copper[ln].append((Point(v["pos"]).buffer(v["diam"] / 2, 16), v["net"], f"via {v['net']}"))
    for p in d["pads"]:
        for ln, ps in p["cu_poly"].items():
            g = polyset_geom(ps)
            if g is not None:
                copper[ln].append((g, p["net"] or f"_nc_{p['ref']}_{p['num']}", f"{p['ref']} pad {p['num']}"))
    for z in d["zones"]:
        for ln, ps in z["fill"].items():
            g = polyset_geom(ps)
            if g is not None:
                copper[ln].append((g, z["net"], f"plano {z['net']}"))

    edge = board.boundary
    edge_items = []
    for ln in cu_layers:
        items = copper[ln]
        geoms = [i[0] for i in items]
        tree = STRtree(geoms)
        best = (9e9, "")
        for i, (g, net, lab) in enumerate(items):
            for j in tree.query(g.buffer(CAPS["clearance_rec"] + 0.3)):
                if j <= i:
                    continue
                g2, net2, lab2 = items[j]
                if net == net2:
                    continue
                dist = g.distance(g2)
                if dist < best[0]:
                    best = (dist, f"{lab} / {lab2}")
        add("Holguras", f"Cobre-cobre minima {ln}", round(best[0], 3) if best[0] < 9e8 else ">0.43",
            CAPS["clearance_min"],
            "OK" if best[0] >= CAPS["clearance_rec"] else ("AVISO" if best[0] >= CAPS["clearance_min"] else "FALLO"),
            best[1])
        # cobre al borde
        emin = (9e9, "")
        for g, net, lab in items:
            dist = g.distance(edge)
            if not board.buffer(1e-3).contains(g):
                dist = -g.difference(board).area  # sale fuera
            if dist < emin[0]:
                emin = (dist, lab)
            if dist < CAPS["copper_edge_min"]:
                edge_items.append((ln, lab, round(dist, 3)))
        add("Cobre al borde", f"Minimo {ln}", round(emin[0], 3), CAPS["copper_edge_min"],
            "OK" if emin[0] >= CAPS["copper_edge_min"] else "FALLO", emin[1])

    # taladro a cobre de otro net (critico en capas internas)
    hc = (9e9, "")
    for ln in cu_layers:
        items = copper[ln]
        tree = STRtree([i[0] for i in items])
        for g, net, kind, lab in holes:
            for j in tree.query(g.buffer(0.5)):
                g2, net2, lab2 = items[j]
                if net2 == net:
                    continue
                if lab2.startswith(lab.split(" pad")[0] + " pad") and lab2 == lab:
                    continue
                dist = g.distance(g2)
                if dist < hc[0]:
                    hc = (dist, f"{ln}: {lab} / {lab2}")
    add("Holguras", "Taladro a cobre de otro net", round(hc[0], 3), CAPS["hole_to_copper_min"],
        "OK" if hc[0] >= CAPS["hole_to_copper_min"] else "FALLO", hc[1])

    # antena: cobre cerca de la muesca
    if notch is not None:
        near = []
        zone = notch.buffer(3.0).intersection(board)
        for ln in cu_layers:
            for g, net, lab in copper[ln]:
                if g.intersects(zone):
                    near.append((ln, lab, round(g.distance(notch), 2)))
        planes = sorted({(a, b) for a, b, c in near if b.startswith("plano")})
        mind = min((c for a, b, c in near), default=None)
        add("Muesca antena", "Cobre a <3 mm del borde de la muesca", len(near), "-", "INFO",
            f"distancia minima {mind} mm; planos implicados: {', '.join(a for a, b in planes) or 'ninguno'}")

    # ---------------- Mascara
    for side in ("F.Mask", "B.Mask"):
        ops = []
        for p in d["pads"]:
            if side in p["mask_poly"]:
                g = polyset_geom(p["mask_poly"][side])
                if g is not None:
                    ops.append((g, f"{p['ref']} pad {p['num']}", p["ref"]))
        tree = STRtree([o[0] for o in ops])
        small = []
        best = (9e9, "")
        for i, (g, lab, ref) in enumerate(ops):
            for j in tree.query(g.buffer(1.0)):
                if j <= i:
                    continue
                g2, lab2, ref2 = ops[j]
                dist = g.distance(g2)
                if dist <= 1e-6:
                    continue  # aperturas que se tocan: no hay presa
                if dist < best[0]:
                    best = (dist, f"{lab} / {lab2}")
                if dist < CAPS["mask_dam_min"]:
                    small.append(ref)
        refs = sorted(set(small))
        add("Mascara", f"Presa minima {side} ({len(ops)} aperturas)",
            round(best[0], 3) if best[0] < 9e8 else "-", CAPS["mask_dam_min"],
            "OK" if best[0] >= CAPS["mask_dam_min"] else "AVISO",
            (best[1] + ("; presas < minimo en: " + ", ".join(refs) +
                        " (JLC las elimina: pads sin presa entre ellos)" if refs else "")))
    add("Mascara", "Expansion global de mascara", st["mask_expansion"], "0-0.05", "INFO",
        "0 mm: la apertura coincide con el pad; JLC aplica su propia compensacion.")

    # ---------------- Serigrafia
    silk = [t for t in d["texts"] if t["layer"].endswith("Silkscreen")]
    if silk:
        h = min(t["h"] for t in silk)
        stroke = [t for t in silk if t["th"] > 0]
        th = min(t["th"] for t in stroke) if stroke else None
        add("Serigrafia", "Altura minima de texto", h, CAPS["silk_text_h_min"],
            "OK" if h >= CAPS["silk_text_h_min"] else "AVISO")
        add("Serigrafia", "Grosor minimo de trazo (fuente KiCad)", th, CAPS["silk_line_min"],
            "OK" if th is None or th >= CAPS["silk_line_min"] else "AVISO",
            "Textos TrueType: %s" % ", ".join(t["text"] for t in silk if t["th"] == 0))

    # ---------------- Salida
    json.dump({"caps": CAPS, "results": R, "edge_items": edge_items}, open(json_out, "w"), indent=1)
    lines = ["# Comprobacion de capacidades JLCPCB (4 capas, 1,6 mm, ENIG)", "",
             "Generado por `scripts/check_jlcpcb.py` a partir de la geometria de `hardware/ocxPrototype.kicad_pcb`"
             " (zonas rellenadas por pcbnew). Limites en mm; ver supuestos en el README.", "",
             "| Categoria | Comprobacion | Valor | Limite JLC | Estado | Nota |", "|---|---|---|---|---|---|"]
    for r in R:
        lines.append(f"| {r['cat']} | {r['item']} | {r['value']} | {r['limit']} | {r['status']} | {r['note']} |")
    if edge_items:
        lines += ["", "## Cobre a menos de %.2f mm del borde" % CAPS["copper_edge_min"], "",
                  "| Capa | Elemento | Distancia (mm, negativa = sale fuera) |", "|---|---|---|"]
        for ln, lab, dist in edge_items:
            lines.append(f"| {ln} | {lab} | {dist} |")
    open(md_out, "w").write("\n".join(lines) + "\n")
    bad = [r for r in R if r["status"] == "FALLO"]
    print("\n".join(lines))
    print("FALLOS:", len(bad))


if __name__ == "__main__":
    main(*sys.argv[1:4])
