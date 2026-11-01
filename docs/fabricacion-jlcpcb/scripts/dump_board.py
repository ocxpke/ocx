#!/usr/bin/env python3
"""Vuelca la geometria de fabricacion de un .kicad_pcb a JSON (corre dentro de
kicad/kicad:10.0, que trae el modulo pcbnew).

Uso: python3 dump_board.py <placa.kicad_pcb> <salida.json>

Todas las cotas en mm. Los poligonos se exportan como listas de anillos
[[x,y],...] (outline primero y luego agujeros) para analizarlos con shapely
fuera del contenedor.
"""
import json
import sys

import pcbnew

IU = 1e6  # nm por mm


def mm(v):
    return round(v / IU, 6)


def pt(p):
    return [mm(p.x), mm(p.y)]


def polyset(ps):
    out = []
    for i in range(ps.OutlineCount()):
        rings = []
        o = ps.Outline(i)
        rings.append([pt(o.CPoint(j)) for j in range(o.PointCount())])
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h)
            rings.append([pt(hh.CPoint(j)) for j in range(hh.PointCount())])
        out.append(rings)
    return out


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    # Rellena zonas para tener el cobre real (no modifica el fichero de origen).
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    ds = board.GetDesignSettings()
    lid = board.GetLayerID
    cu_layers = [n for n in ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")]
    maxerr = ds.m_MaxError

    data = {
        "settings": {
            "copper_layers": board.GetCopperLayerCount(),
            "thickness": mm(ds.GetBoardThickness()),
            "min_clearance": mm(ds.m_MinClearance),
            "min_track": mm(ds.m_TrackMinWidth),
            "min_via_annular": mm(ds.m_ViasMinAnnularWidth),
            "min_via_size": mm(ds.m_ViasMinSize),
            "min_through_drill": mm(ds.m_MinThroughDrill),
            "hole_to_hole": mm(ds.m_HoleToHoleMin),
            "hole_clearance": mm(ds.m_HoleClearance),
            "copper_edge": mm(ds.m_CopperEdgeClearance),
            "mask_expansion": mm(ds.m_SolderMaskExpansion),
            "mask_min_width": mm(ds.m_SolderMaskMinWidth),
            "tent_vias_front": bool(ds.m_TentViasFront),
            "tent_vias_back": bool(ds.m_TentViasBack),
        },
        "tracks": [], "vias": [], "pads": [], "footprints": [], "zones": [],
        "texts": [], "outline": None,
    }

    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, False)
    data["outline"] = polyset(outline)

    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            data["vias"].append({
                "pos": pt(t.GetPosition()), "drill": mm(t.GetDrillValue()),
                "diam": mm(t.GetWidth(lid("F.Cu"))), "net": t.GetNetname(),
                "type": int(t.GetViaType()),
            })
        elif t.Type() == pcbnew.PCB_ARC_T:
            data["tracks"].append({
                "arc": True, "start": pt(t.GetStart()), "mid": pt(t.GetMid()),
                "end": pt(t.GetEnd()), "width": mm(t.GetWidth()),
                "layer": t.GetLayerName(), "net": t.GetNetname()})
        else:
            data["tracks"].append({
                "arc": False, "start": pt(t.GetStart()), "end": pt(t.GetEnd()),
                "width": mm(t.GetWidth()), "layer": t.GetLayerName(),
                "net": t.GetNetname()})

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fields = {f.GetName(): f.GetText() for f in fp.GetFields()}
        data["footprints"].append({
            "ref": ref, "value": fp.GetValue(),
            "fpid": fp.GetFPIDAsString(), "pos": pt(fp.GetPosition()),
            "rot": fp.GetOrientationDegrees(),
            "side": "bottom" if fp.IsFlipped() else "top",
            "dnp": bool(fp.IsDNP()), "excl_bom": bool(fp.IsExcludedFromBOM()),
            "excl_pos": bool(fp.IsExcludedFromPosFiles()),
            "attr": int(fp.GetAttributes()),
            "lcsc": fields.get("LCSC", ""), "mpn": fields.get("MPN", ""),
        })
        for pad in fp.Pads():
            layers = [n for n in cu_layers if pad.IsOnLayer(lid(n))]
            mask = [n for n in ("F.Mask", "B.Mask") if pad.IsOnLayer(lid(n))]
            cu_poly = {}
            for ln in layers:
                ps = pcbnew.SHAPE_POLY_SET()
                pad.TransformShapeToPolygon(ps, lid(ln), 0, maxerr,
                                            pcbnew.ERROR_INSIDE)
                if ps.OutlineCount():
                    cu_poly[ln] = polyset(ps)
            mask_poly = {}
            for ln in mask:
                ps = pcbnew.SHAPE_POLY_SET()
                exp = pad.GetSolderMaskExpansion(lid(ln))
                pad.TransformShapeToPolygon(ps, lid(ln), exp, maxerr,
                                            pcbnew.ERROR_OUTSIDE)
                mask_poly[ln] = polyset(ps)
            ds_ = pad.GetDrillSize()
            data["pads"].append({
                "ref": ref, "num": pad.GetNumber(), "net": pad.GetNetname(),
                "pos": pt(pad.GetPosition()), "attr": int(pad.GetAttribute()),
                "size": [mm(pad.GetSizeX()), mm(pad.GetSizeY())],
                "drill": [mm(ds_.x), mm(ds_.y)],
                "drill_oblong": pad.GetDrillShape() == pcbnew.PAD_DRILL_SHAPE_OBLONG,
                "layers": layers, "mask_layers": mask,
                "cu_poly": cu_poly, "mask_poly": mask_poly,
            })

    for z in board.Zones():
        entry = {"name": z.GetZoneName(), "net": z.GetNetname(),
                 "rule_area": bool(z.GetIsRuleArea()), "fill": {},
                 "min_thickness": mm(z.GetMinThickness()),
                 "clearance": mm(z.GetLocalClearance() or 0),
                 "layers": [board.GetLayerName(l) for l in z.GetLayerSet().Seq()]}
        if z.GetIsRuleArea():
            entry["outline"] = polyset(z.Outline())
            entry["keepout"] = {"tracks": z.GetDoNotAllowTracks(),
                                "vias": z.GetDoNotAllowVias(),
                                "zones": z.GetDoNotAllowZoneFills(),
                                "pads": z.GetDoNotAllowPads(),
                                "footprints": z.GetDoNotAllowFootprints()}
        else:
            for ln in cu_layers:
                if z.IsOnLayer(lid(ln)):
                    entry["fill"][ln] = polyset(z.GetFilledPolysList(lid(ln)))
        data["zones"].append(entry)

    for d in board.GetDrawings():
        if isinstance(d, pcbnew.PCB_TEXT):
            data["texts"].append({"text": d.GetText(), "layer": d.GetLayerName(),
                                  "h": mm(d.GetTextHeight()),
                                  "th": mm(d.GetTextThickness())})
    for fp in board.GetFootprints():
        for d in fp.GraphicalItems():
            if isinstance(d, pcbnew.PCB_TEXT) and d.IsVisible():
                data["texts"].append({"text": d.GetText(), "layer": d.GetLayerName(),
                                      "h": mm(d.GetTextHeight()),
                                      "th": mm(d.GetTextThickness()),
                                      "ref": fp.GetReference()})
        for f in fp.GetFields():
            if f.IsVisible() and f.GetLayerName().endswith("Silkscreen"):
                data["texts"].append({"text": f.GetShownText(False),
                                      "layer": f.GetLayerName(),
                                      "h": mm(f.GetTextHeight()),
                                      "th": mm(f.GetTextThickness()),
                                      "ref": fp.GetReference()})

    with open(dst, "w") as fh:
        json.dump(data, fh)
    print("pads=%d tracks=%d vias=%d zones=%d fps=%d" % (
        len(data["pads"]), len(data["tracks"]), len(data["vias"]),
        len(data["zones"]), len(data["footprints"])))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
