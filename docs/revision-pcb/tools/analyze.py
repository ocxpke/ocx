#!/usr/bin/env python3
"""DFM / assembly review of hardware/ocxPrototype.kicad_pcb.

Usage:  python3 analyze.py [path/to/board.kicad_pcb] [outdir]
Writes findings.json, findings.md and PNG captures to <outdir> (default ../).
Read-only: never writes to hardware/.
"""
import json, math, os, sys, itertools, collections
from shapely.geometry import Point, Polygon, LineString, box, MultiPolygon, GeometryCollection
from shapely.ops import unary_union, nearest_points
from board import Board
import render

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '../../../hardware/ocxPrototype.kicad_pcb')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..')
CAP = os.path.join(OUT, 'capturas')
os.makedirs(CAP, exist_ok=True)
for _f in os.listdir(CAP):
    if _f.endswith('.png'):
        os.remove(os.path.join(CAP, _f))

B = Board(PCB)
findings = []


def add(cat, sev, title, where, detail, bounds=None, marks=None, ident=None, render_opts=None):
    f = dict(render_opts=render_opts or {}, id=ident or f'{cat}-{len([x for x in findings if x["cat"] == cat]) + 1:02d}', cat=cat, sev=sev,
             title=title, where=where, detail=detail, bounds=bounds, marks=marks or [])
    findings.append(f)
    return f


# ---------------------------------------------------------------- assumptions
# Component body heights above the top of the PCB (mm). Source: manufacturer
# datasheets of the MPN in the board (max/nominal seated height).
HEIGHT_BY_MPN = {
    'FH2.54-09-22PZD': 8.5,            # female header (DevKit socket)
    'MLD-TS-6X6X5-J': 5.0,             # 6x6x5 tact switch
    'B2B-PH-K-S(LF)(SN)': 6.0,         # JST PH vertical
    'TYPE-C-31-M-12': 3.31,            # HRO USB-C mid-mount
    'XF2M-4015-1A': 1.2,               # Omron FPC 0.5 mm
    '84953-6': 2.0,                    # TE FPC 1.0 mm (approx.)
    'SFV5R-4STE1HLF': 2.0,             # Amphenol FPC 0.5 mm (approx.)
    'FNR4030S220MT': 3.0,
    'XAL4020-222MEC': 2.1,
    'P6SMB6.8CA/TR13': 2.45,
    'SS210': 2.45,
    'X503212MSB4SI': 1.2,
    'MCP23017-E/SO': 2.65,
    'W25Q128JVSIQ': 2.16,
    'PAM8302AADCR': 1.75,
    'BT817Q-R': 1.0,
    'LMR51430YDDCR': 1.1, 'DIO5661ST6': 1.45, 'USBLC6-2SC6': 1.45,
    'KT-0805G': 0.8,
}
HEIGHT_BY_FP = {'C_0402': 0.55, 'R_0402': 0.4, 'C_0603': 0.9, 'C_0805': 1.45, 'R_0805': 0.6, 'L_0805': 1.0,
                'C_1206': 1.8, 'TestPoint_Pad': 0.0, 'TestPoint_Keystone': 5.0}


def height(fp):
    if fp.mpn in HEIGHT_BY_MPN:
        return HEIGHT_BY_MPN[fp.mpn], 'MPN'
    for k, v in HEIGHT_BY_FP.items():
        if k in fp.lib:
            return v, 'footprint'
    return None, None


# DevKit (ESP32-S3-DevKitC-1 v1.1): 25.4 mm wide, ~63 mm long (assumed), pin rows
# 22.86 mm apart. Its antenna end points at the edge cutout (J2 pin 1 side).
J2, J3 = B.fp['J2'], B.fp['J3']
xs = sorted([J2.pads[0].x, J3.pads[0].x])
pin_y = sorted(p.y for p in J2.pads)
DEVKIT = box(sum(xs) / 2 - 12.7, pin_y[0] - 8.2, sum(xs) / 2 + 12.7, pin_y[-1] + 1.5)
DEVKIT_BOTTOM = 8.5          # mm above our PCB (user statement: ~8.5 mm)
DEVKIT_STACK = 8.5 + 1.6 + 3.3   # socket + DevKit PCB + WROOM shield / USB connectors

# Display NHD-5.0-800480AF-ASXP-CTP: outline 120.7 x 75.8 mm. Position not
# drawn in the PCB -> assumed centred on the board, landscape.
cx = (B.outline.bounds[0] + B.outline.bounds[2]) / 2
cy = (B.outline.bounds[1] + B.outline.bounds[3]) / 2
SCREEN = box(cx - 120.7 / 2, cy - 75.8 / 2, cx + 120.7 / 2, cy + 75.8 / 2)


def fp_body(fp):
    c = fp.courtyard()
    if c is not None:
        return c
    return unary_union([p.geom for p in fp.pads])


def fmt(x):
    return f'{x:.2f}'


def bnd(g, m=2.0):
    x0, y0, x1, y1 = g.bounds if hasattr(g, 'bounds') else g
    return (x0 - m, y0 - m, x1 + m, y1 + m)


# =========================================================== 1. acid traps
def check_acid_traps():
    nodes = collections.defaultdict(list)
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    for i, s in enumerate(B.segments):
        if math.dist(s['a'], s['b']) < s['w']:
            continue   # stub hidden inside the track width: no wedge in the copper
        nodes[(s['layer'], s['net'], key(s['a']))].append((i, s['a'], s['b']))
        nodes[(s['layer'], s['net'], key(s['b']))].append((i, s['b'], s['a']))
    # T-junctions: endpoint lying on the interior of another segment of same net/layer
    by_ln = collections.defaultdict(list)
    for i, s in enumerate(B.segments):
        by_ln[(s['layer'], s['net'])].append((i, s))
    for (layer, net, pt), lst in list(nodes.items()):
        P = Point(pt)
        for j, s in by_ln[(layer, net)]:
            if any(j == i for i, _, _ in lst):
                continue
            L = LineString([s['a'], s['b']])
            if L.distance(P) < 1e-3 and P.distance(Point(s['a'])) > 1e-3 and P.distance(Point(s['b'])) > 1e-3:
                lst.append((j, pt, s['a']))
                lst.append((j, pt, s['b']))
    pad_cu = collections.defaultdict(list)
    for p in B.all_pads():
        if p.on_cu:
            pad_cu[p.net].append(p.geom)
    via_cu = collections.defaultdict(list)
    for v in B.vias:
        via_cu[v['net']].append(Point(v['x'], v['y']).buffer(v['size'] / 2))
    traps = []
    for (layer, net, pt), lst in nodes.items():
        if len(lst) < 2:
            continue
        dirs = []
        for i, a, b in lst:
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360
            dirs.append((ang, i))
        dirs.sort()
        for k in range(len(dirs)):
            a1, i1 = dirs[k]
            a2, i2 = dirs[(k + 1) % len(dirs)]
            d = (a2 - a1) % 360
            if len(dirs) == 2 and k == 1:
                break
            if 0.5 < d < 89.5:
                # wedge point: ~0.6 mm away along the bisector; covered by pad/via copper -> not a trap
                bis = math.radians(a1 + d / 2)
                w = max(B.segments[i1]['w'], B.segments[i2]['w'])
                probe = Point(pt[0] + math.cos(bis) * (w / 2 / math.sin(math.radians(d / 2)) + 0.05),
                              pt[1] + math.sin(bis) * (w / 2 / math.sin(math.radians(d / 2)) + 0.05))
                node = Point(pt)
                covered = any(g.contains(probe) or g.buffer(0.05).contains(node) for g in pad_cu[net] + via_cu[net])
                if covered:
                    continue
                traps.append(dict(layer=layer, net=net, pt=pt, angle=d, w=w))
    # merge duplicates
    seen = set(); out = []
    for t in sorted(traps, key=lambda t: t['angle']):
        k = (t['layer'], round(t['pt'][0], 2), round(t['pt'][1], 2))
        if k in seen:
            continue
        seen.add(k); out.append(t)
    return out


# ===================================================== 2. copper / mask slivers
def check_slivers():
    res = []
    for z in B.zones:
        fill = z['fill']
        for r, lab in ((0.2, '<0.40 mm'),):
            opened = fill.buffer(-r, 8).buffer(r, 8)
            thin = fill.difference(opened.buffer(0.02))
            pieces = [g for g in getattr(thin, 'geoms', [thin]) if g.area > 0.15]
            for g in pieces:
                # length estimate of a thin piece ~ area / width
                mrr = g.minimum_rotated_rectangle
                xs_, ys_ = mrr.exterior.coords.xy
                e = sorted([math.dist((xs_[i], ys_[i]), (xs_[i + 1], ys_[i + 1])) for i in range(4)])
                res.append(dict(kind='zone', layer=z['layer'], net=z['net'], geom=g, area=g.area,
                                length=e[-1], width=g.area / max(e[-1], 1e-6)))
    # mask web between pads of different nets (mask expansion = 0 in setup)
    mask = []
    pads = [p for p in B.all_pads() if any('Mask' in l for l in p.layers) and p.on_cu]
    for f in B.footprints:
        fps = [p for p in f.pads if p in pads]
        for a, b in itertools.combinations(fps, 2):
            if a.net == b.net:
                continue
            d = a.geom.distance(b.geom)
            if d < 0.1:
                mask.append(dict(fp=f.ref, a=a, b=b, d=d))
    return res, mask


# ============================================= 3. pads / planes thermal relief
def check_thermal():
    out = []
    planes = {(z['layer'], z['net']): z['fill'] for z in B.zones}
    gap = 0.5
    # 3a: THT pads (and vias inside pads) on a plane net: is the plane connection a relief or solid?
    for p in B.all_pads():
        if p.kind != 'thru_hole':
            continue
        for (layer, net), fill in planes.items():
            if p.net != net:
                continue
            ring = p.geom.buffer(gap * 0.5).exterior.buffer(0.05)
            cov = fill.intersection(ring).area / ring.area if ring.area else 0
            out.append(dict(kind='tht', pad=p, layer=layer, cov=cov))
    # 3b: big SMD pads tied to a plane/power net by vias in or touching the pad
    big = []
    for p in B.all_pads():
        if p.kind != 'smd' or not p.on_cu:
            continue
        vias_in = [v for v in B.vias if v['net'] == p.net and
                   p.geom.distance(Point(v['x'], v['y'])) < v['size'] / 2 + 0.05]
        tr = [s for s in B.segments if s['layer'] == 'F.Cu' and s['net'] == p.net and
              (p.geom.distance(Point(s['a'])) < 0.01 or p.geom.distance(Point(s['b'])) < 0.01)]
        big.append(dict(pad=p, vias=vias_in, tracks=tr))
    return out, big


def tombstone_risk(big):
    """Two-terminal small chips whose pads have very different copper attached."""
    res = []
    by_fp = collections.defaultdict(list)
    for d in big:
        by_fp[d['pad'].fp.ref].append(d)
    for ref, lst in by_fp.items():
        fp = B.fp[ref]
        if len(fp.pads) != 2 or not any(k in fp.lib for k in ('0402', '0603', '0805')):
            continue
        def heat(d):
            return sum(s['w'] for s in d['tracks']) + 0.6 * len(d['vias']) + \
                (1.5 if d['vias'] and d['pad'].net in ('GND', '+3.3V') else 0)
        if len(lst) != 2:
            continue
        h = [heat(d) for d in lst]
        if max(h) >= 1.2 and max(h) >= 3 * max(min(h), 0.2):
            res.append(dict(fp=fp, h=h, lst=lst))
    return res


# =========================================================== 4. spacing
def check_spacing():
    res = []
    bodies = {f.ref: fp_body(f) for f in B.footprints if not f.ref.startswith('REF')}
    refs = list(bodies)
    for a, b in itertools.combinations(refs, 2):
        A, Bb = bodies[a], bodies[b]
        if A is None or Bb is None:
            continue
        if A.intersects(Bb):
            ov = A.intersection(Bb)
            if ov.area > 0.01:
                res.append(dict(a=a, b=b, overlap=ov.area, geom=ov, gap=0))
                continue
        fa, fb = B.fp[a], B.fp[b]
        pa = [p for p in fa.pads if p.on_cu]; pb = [p for p in fb.pads if p.on_cu]
        if not pa or not pb or A.distance(Bb) > 1.0:
            continue
        d, p1, p2 = min(((x.geom.distance(y.geom), x, y) for x in pa for y in pb), key=lambda t: t[0])
        if d < 0.35:
            res.append(dict(a=a, b=b, overlap=0, geom=unary_union([p1.geom, p2.geom]).buffer(0.2), gap=d, pads=(p1, p2)))
    # edge clearance of copper
    edge = []
    ring = B.outline.exterior
    for p in B.all_pads():
        if not p.on_cu:
            continue
        d = p.geom.distance(ring) if B.outline.contains(p.geom.centroid) else -p.geom.distance(ring)
        if d < 0.5:
            edge.append(dict(pad=p, d=d))
    # mounting holes keep-out (M3 head ~ 6 mm diameter + 0.5)
    mh = []
    for f in B.footprints:
        if 'MountingHole' not in f.lib:
            continue
        keep = Point(f.x, f.y).buffer(3.5)
        for g in B.footprints:
            if g is f or 'MountingHole' in g.lib:
                continue
            body = bodies.get(g.ref)
            if body is not None and body.intersects(keep):
                mh.append(dict(hole=(f.x, f.y), fp=g.ref, d=Point(f.x, f.y).distance(body)))
        for s in B.segments:
            if s['layer'] in ('F.Cu', 'B.Cu') and LineString([s['a'], s['b']]).buffer(s['w'] / 2).intersects(keep):
                mh.append(dict(hole=(f.x, f.y), fp='pista ' + s['net'], d=Point(f.x, f.y).distance(LineString([s['a'], s['b']])) - s['w'] / 2))
    return res, edge, mh


# =========================================================== 5. THT vs SMD
def check_tht_smd():
    res = []
    smd_pads = [p for p in B.all_pads() if p.kind == 'smd' and p.on_cu]
    for f in B.footprints:
        if not f.is_tht and not any(p.kind == 'thru_hole' for p in f.pads):
            continue
        for p in f.pads:
            if p.kind != 'thru_hole':
                continue
            best = None
            for q in smd_pads:
                if q.fp is f:
                    continue
                d = p.geom.distance(q.geom)
                if best is None or d < best[0]:
                    best = (d, q)
            if best and best[0] < 3.0:
                res.append(dict(tht=p, smd=best[1], d=best[0]))
    # keep worst per (tht fp, smd fp)
    agg = {}
    for r in res:
        k = (r['tht'].fp.ref, r['smd'].fp.ref)
        if k not in agg or r['d'] < agg[k]['d']:
            agg[k] = r
    return sorted(agg.values(), key=lambda r: r['d'])


# =========================================================== 6. heights
def check_heights():
    under_dk, under_scr = [], []
    for f in B.footprints:
        if 'MountingHole' in f.lib or f.ref in ('J2', 'J3'):
            continue
        body = fp_body(f)
        h, src = height(f)
        if body is None:
            continue
        if body.intersects(DEVKIT):
            under_dk.append(dict(fp=f, h=h, src=src, part=body.intersection(DEVKIT).area / body.area))
        if body.intersects(SCREEN):
            under_scr.append(dict(fp=f, h=h, src=src, part=body.intersection(SCREEN).area / body.area))
    return under_dk, under_scr


# =========================================================== 7. silkscreen
def silk_geom(f, layer='F.SilkS'):
    gs = [g.geom() for g in f.graphics if g.layer == layer and g.kind != 'text']
    gs = [g for g in gs if g is not None]
    return unary_union(gs) if gs else None


def pin1_marker(f):
    """Is there silkscreen that identifies pad 1?  Compare silk density near
    pad 1 against the pad that is point-symmetric to it through the centre."""
    p1 = [p for p in f.pads if p.num in ('1', 'A1')]
    if not p1:
        return None
    p1 = p1[0]
    silk = silk_geom(f)
    if silk is None:
        return dict(ok=False, why='sin serigrafía', p1=p1)
    # mirror point
    mx, my = 2 * f.x - p1.x, 2 * f.y - p1.y
    if f.ref in ('J2', 'J3'):
        # rows: compare with the last pin of the same row
        pl = max(f.pads, key=lambda p: math.dist((p.x, p.y), (p1.x, p1.y)))
        mx, my = pl.x, pl.y
    r = max(p1.w, p1.h) / 2 + 1.0
    a1 = silk.intersection(Point(p1.x, p1.y).buffer(r)).area
    a2 = silk.intersection(Point(mx, my).buffer(r)).area
    filled = any(g.fill for g in f.graphics if g.layer == 'F.SilkS' and g.kind == 'poly')
    ok = a1 > 1.3 * a2 + 0.02 or (filled and a1 > a2)
    return dict(ok=ok, a1=a1, a2=a2, p1=p1, filled=filled)


def text_box(g):
    n = len(g.text)
    w = g.size * (0.9 * n) ; h = g.size
    from shapely import affinity
    bx = box(g.at[0] - w / 2, g.at[1] - h / 2, g.at[0] + w / 2, g.at[1] + h / 2)
    return affinity.rotate(bx, -g.angle, origin=g.at)


def check_silk():
    res = dict(pin1=[], texts=[], over_pads=[], overlap=[], off_board=[], button_names=[], polarity=[])
    for f in B.footprints:
        if f.ref[0] in 'UJY' or f.ref.startswith('SW'):
            if f.ref.startswith('SW'):
                continue
            res['pin1'].append(dict(fp=f, **(pin1_marker(f) or dict(ok=None))))
    # text sizes & visibility
    texts = []
    for f in B.footprints:
        for g in f.graphics:
            if g.kind == 'text' and g.layer == 'F.SilkS' and not g.hidden:
                texts.append(g)
    for g in B.gr:
        if g.kind == 'text' and g.layer == 'F.SilkS':
            texts.append(g)
    for g in texts:
        if g.size < 0.8 or (g.thick and g.thick < 0.15 and g.owner is not None):
            res['texts'].append(dict(t=g, why=f'tamaño {g.size} mm / trazo {g.thick} mm'))
    # silk over exposed copper (pads): fab clips it
    mask_open = unary_union([p.geom for p in B.all_pads() if any('Mask' in l for l in p.layers)])
    for f in B.footprints:
        s = silk_geom(f)
        if s is None:
            continue
        ov = s.intersection(mask_open)
        if ov.area > 0.02:
            res['over_pads'].append(dict(fp=f, area=ov.area, geom=ov))
    # reference text over other parts' pads / other texts
    boxes = [(g, text_box(g)) for g in texts if g.owner is not None]
    for (g1, b1), (g2, b2) in itertools.combinations(boxes, 2):
        if b1.intersects(b2) and b1.intersection(b2).area > 0.1:
            res['overlap'].append(dict(a=g1, b=g2, area=b1.intersection(b2).area))
    for g, b in boxes:
        ov = b.intersection(mask_open)
        if ov.area > 0.15:
            res['overlap'].append(dict(a=g, b=None, area=ov.area))
        if not B.outline.contains(b):
            res['off_board'].append(dict(t=g))
    # button names
    for f in B.footprints:
        if not f.ref.startswith('SW'):
            continue
        name = f.value
        silk_texts = [g.text for g in f.graphics if g.kind == 'text' and g.layer == 'F.SilkS' and not g.hidden]
        board_texts = [g.text for g in B.gr if g.kind == 'text' and g.layer == 'F.SilkS'
                       and math.dist(g.at, (f.x, f.y)) < 10]
        res['button_names'].append(dict(fp=f, name=name, silk=silk_texts + board_texts,
                                        ok=any(name in t or t in name for t in silk_texts + board_texts if t != f.ref)))
    # polarity of diodes
    for ref in ('D1', 'D2', 'D3'):
        f = B.fp[ref]
        import sexp as S
        fun = {p[1]: S.val(p, 'pinfunction') for p in S.find(f.node, 'pad')}
        k_pad = [p for p in f.pads if fun.get(p.num, '').startswith('K')]
        bidir = 'CA' in f.value or all(fun.get(p.num, '').startswith('A') for p in f.pads)
        silk = silk_geom(f)
        sides = []
        for p in f.pads:
            sides.append(silk.intersection(Point(p.x, p.y).buffer(max(p.w, p.h) / 2 + 1.2)).area if silk else 0)
        marked = None
        if sides and max(sides) > 1.3 * min(sides):
            marked = f.pads[sides.index(max(sides))]
        res['polarity'].append(dict(fp=f, k=k_pad[0] if k_pad else None, bidir=bidir, marked=marked, sides=sides,
                                    pins={p.num: (fun.get(p.num), p.net) for p in f.pads}))
    return res


# ===================================================================== run
traps = check_acid_traps()
slivers, maskwebs = check_slivers()
tht_planes, smdpads = check_thermal()
tomb = tombstone_risk(smdpads)
spacing, edge, mh = check_spacing()
tht_smd = check_tht_smd()
under_dk, under_scr = check_heights()
silk = check_silk()

# ---------------------------------------------------------------- findings
# 1 acid traps
for t in traps:
    sev = 'revisar' if t['angle'] < 60 else 'bien'
    if sev == 'bien':
        continue
    x, y = t['pt']
    add('acido', sev, f'Ángulo agudo {t["angle"]:.0f}° en {t["layer"]} ({t["net"]})', f'({fmt(x)}, {fmt(y)})',
        f'Dos pistas de la red {t["net"]} (ancho {t["w"]} mm) se unen formando una cuña de {t["angle"]:.0f}°. '
        'Con el grabado moderno de JLCPCB no suele dar problemas, pero conviene suavizarlo a ≥90° (o con una lágrima).',
        bounds=(x - 2.5, y - 2.5, x + 2.5, y + 2.5), marks=[('circle', (x, y), 0.6)])
n_traps_60_90 = sum(1 for t in traps if t['angle'] >= 60)

# 2 slivers
for s in slivers:
    g = s['geom']
    sev = 'revisar' if s['width'] < 0.3 and s['length'] > 1.0 else 'bien'
    if sev == 'bien':
        continue
    c = g.centroid
    add('astilla', sev, f'Cuello estrecho en plano {s["net"]} ({s["layer"]})', f'({fmt(c.x)}, {fmt(c.y)})',
        f'Tramo de relleno de ~{s["width"]:.2f} mm de ancho y {s["length"]:.1f} mm de largo. '
        'No es una astilla suelta (el relleno ya respeta min_thickness 0,25 mm), pero es un estrechamiento '
        'del plano que conviene ensanchar o eliminar con una keep-out.',
        bounds=bnd(g, 3), marks=[('geom', g)])
for m in sorted(maskwebs, key=lambda m: m['d'])[:0]:
    pass

# 3 thermal
solid = [t for t in tht_planes if t['cov'] > 0.85]
for t in solid:
    p = t['pad']
    add('termico', 'revisar', f'Pad THT {p} unido sin alivio al plano {p.net} ({t["layer"]})', f'({fmt(p.x)}, {fmt(p.y)})',
        f'El anillo alrededor del pad está cubierto al {t["cov"]*100:.0f} %: el relleno lo toca de forma maciza '
        '(probablemente por vías o pistas cercanas que llenan los huecos entre radios).',
        bounds=(p.x - 4, p.y - 4, p.x + 4, p.y + 4), marks=[('circle', (p.x, p.y), max(p.w, p.h) / 2 + 0.6)])

big_planes = []
for d in smdpads:
    p = d['pad']
    if p.area < 2.0 or not d['vias']:
        continue
    big_planes.append(d)

tomb_f = []
for t in tomb:
    f = t['fp']
    a, b = t['lst']
    tomb_f.append(add('termico', 'revisar', f'{f.ref}: cobre asimétrico entre pads (riesgo de tombstoning)', f'{f.ref} ({fmt(f.x)}, {fmt(f.y)})',
                      f'Pad {a["pad"].num} ({a["pad"].net}): {len(a["tracks"])} pistas (∑ancho {sum(s["w"] for s in a["tracks"]):.2f} mm), '
                      f'{len(a["vias"])} vía(s) en el pad. Pad {b["pad"].num} ({b["pad"].net}): {len(b["tracks"])} pistas '
                      f'(∑ancho {sum(s["w"] for s in b["tracks"]):.2f} mm), {len(b["vias"])} vía(s). '
                      'En reflujo un lado se calienta antes que el otro.',
                      bounds=bnd(fp_body(f), 2.5), marks=[('geom', fp_body(f))]))

# 3c thermal vias of exposed pads: relief spokes in the plane instead of solid
ep_vias = collections.defaultdict(list)
for t in tht_planes:
    p = t['pad']
    if p.drill and p.drill < 0.5 and any(q.kind == 'smd' and q.num == p.num and q.area > 10 for q in p.fp.pads):
        ep_vias[(p.fp.ref, t['layer'])].append(t)
for (ref, layer), lst in ep_vias.items():
    f = B.fp[ref]
    ep = max((q for q in f.pads if q.kind == 'smd'), key=lambda q: q.area)
    cov = sum(t['cov'] for t in lst) / len(lst)
    sev = 'revisar' if cov < 0.85 else 'bien'
    add('termico', sev, f'{ref}: {len(lst)} vías térmicas del EP conectadas con radios al plano {lst[0]["pad"].net} ({layer})',
        f'{ref} ({fmt(f.x)}, {fmt(f.y)})',
        f'Las vías de la almohadilla expuesta son pads de huella con la conexión a zona heredada (alivio térmico): '
        f'el plano cubre solo ~{cov*100:.0f} % del anillo de cada vía. Para disipar conviene conexión maciza '
        '(zone_connect "solid" en esas vías / en la huella). Además las vías están en el pad sin tapar: '
        'parte de la pasta se irá por ellas (con 0,33 mm es aceptable; opción de "via-in-pad" taponado en JLCPCB si se quiere evitar).',
        bounds=bnd(ep.geom, 2.5), marks=[('geom', ep.geom)], render_opts=dict(planes=('In1.Cu',), plane_alpha=0.55))

# 4 spacing
for s in spacing:
    sev = 'bloqueante' if s['overlap'] > 0.5 else 'revisar'
    A, Bf = B.fp[s['a']], B.fp[s['b']]
    if s['overlap']:
        txt = f'Courtyards de {s["a"]} y {s["b"]} solapan {s["overlap"]:.2f} mm².'
    else:
        p1, p2 = s['pads']
        txt = (f'Courtyards sin solape, pero los pads {p1} y {p2} quedan a {s["gap"]:.2f} mm. '
               'Con pads HandSolder y pasta puede formarse puente o desplazarse una pieza; JLCPCB recomienda ≥0,3–0,5 mm pad-pad entre componentes.')
    add('separacion', sev, f'{s["a"]} ↔ {s["b"]}' + ('' if s['overlap'] else f': pads a {s["gap"]:.2f} mm'), f'({fmt(A.x)}, {fmt(A.y)}) / ({fmt(Bf.x)}, {fmt(Bf.y)})',
        txt,
        bounds=bnd(unary_union([fp_body(A), fp_body(Bf)]), 1.5), marks=[('geom', s['geom'])])
for e in edge:
    p = e['pad']
    sev = 'bien' if p.fp.ref == 'J10' else ('bloqueante' if e['d'] < 0.3 else 'revisar')
    if sev == 'bien':
        continue
    add('separacion', sev, f'Pad {p} a {e["d"]:.2f} mm del borde', f'({fmt(p.x)}, {fmt(p.y)})',
        'JLCPCB pide ≥0,3 mm de cobre a borde (fresado).', bounds=(p.x - 4, p.y - 4, p.x + 4, p.y + 4),
        marks=[('circle', (p.x, p.y), 1)])
for m in mh:
    x, y = m['hole']
    add('separacion', 'revisar', f'{m["fp"]} dentro de la zona de cabeza de tornillo M3 en ({x}, {y})', f'({x}, {y})',
        f'Queda a {m["d"]:.2f} mm del centro del taladro; una cabeza M3/arandela ocupa Ø5,5–7 mm.',
        bounds=(x - 6, y - 6, x + 6, y + 6), marks=[('circle', (x, y), 3.5)])

# 5 THT vs SMD
for r in tht_smd:
    p, q, d = r['tht'], r['smd'], r['d']
    sev = 'revisar' if d < 1.0 else 'bien'
    if sev == 'bien':
        continue
    add('tht_smd', sev, f'{p.fp.ref} (THT) a {d:.2f} mm de {q.fp.ref} (SMD)', f'({fmt(p.x)}, {fmt(p.y)})',
        f'Pad THT {p} a {d:.2f} mm del pad SMD {q}. Con soldadura manual del THT por la cara inferior no '
        'interfiere, pero la punta del soldador / boquilla selectiva y el cuerpo del THT quedan muy cerca del SMD.',
        bounds=bnd(unary_union([p.geom, q.geom]), 3), marks=[('circle', (p.x, p.y), max(p.w, p.h) / 2 + 0.3),
                                                         ('circle', (q.x, q.y), max(q.w, q.h) / 2 + 0.3)])

# 6 heights
lim = DEVKIT_BOTTOM - 1.0
for u in sorted(under_dk, key=lambda u: -(u['h'] or 0)):
    f, h = u['fp'], u['h']
    if h is None:
        sev = 'revisar'
    elif h > DEVKIT_BOTTOM - 0.3:
        sev = 'bloqueante'
    elif h > lim:
        sev = 'revisar'
    else:
        sev = 'bien'
    u['sev'] = sev
    if sev == 'bien':
        continue
    add('altura', sev, f'{f.ref} ({f.mpn}) bajo la DevKit: {h} mm', f'({fmt(f.x)}, {fmt(f.y)})',
        f'Altura {h} mm frente a ~{DEVKIT_BOTTOM} mm de hueco bajo la DevKit (margen < 1 mm).',
        bounds=bnd(DEVKIT, 2), marks=[('geom', fp_body(f))])
SW_UNDER = [u for u in under_scr if u['fp'].ref in ('SW14', 'SW16')]
for u in SW_UNDER:
    f = u['fp']
    add('altura', 'revisar', f'{f.ref} ({f.value}) queda bajo la pantalla', f'({fmt(f.x)}, {fmt(f.y)})',
        'Con la pantalla montada el pulsador no es accesible (solo con la pantalla quitada o con un agujero en la carcasa/pantalla).',
        bounds=bnd(unary_union([fp_body(f), DEVKIT.intersection(box(*bnd(fp_body(f), 8)))]), 4), marks=[('geom', fp_body(f))])
scr_max = max(under_scr, key=lambda u: u['h'] or 0)
add('altura', 'revisar', f'Hueco mínimo bajo la pantalla ≈ {DEVKIT_STACK:.1f} mm (DevKit)', 'zona central',
    f'La pantalla (120,7 × 75,8 mm) no cabe entre los grupos de botones sin solaparse con la DevKit. '
    f'La pila socket {DEVKIT_BOTTOM} + PCB DevKit 1,6 + módulo/USB ~3,3 ≈ {DEVKIT_STACK:.1f} mm '
    f'marca la separación mínima PCB→trasera de la pantalla. Sin la DevKit el más alto sería '
    f'{max((u for u in under_scr if u["fp"].ref not in ("J2","J3")), key=lambda u: u["h"] or 0)["fp"].ref}.',
    bounds=bnd(B.outline, 2), marks=[('geom', SCREEN.exterior.buffer(0.4)), ('geom', DEVKIT.exterior.buffer(0.4))],
    ident='altura-pantalla')

# 7 silk
# Pin-1 markers flagged by the heuristic were checked visually on the capture.
PIN1_MANUAL = {
    'J2': ('bien', 'Esquina en L junto al pin 1 y pad cuadrado (marca de la librería KiCad).'),
    'J3': ('bien', 'Esquina en L junto al pin 1 y pad cuadrado. Ojo: J3 está girado 180°, su pin 1 queda abajo y el de J2 arriba.'),
    'J5': ('bien', 'Esquina en L junto al pin 1 y pad 1 rectangular; el conector JST PH está polarizado por la carcasa.'),
    'Y1': ('bien', 'La huella 5032 marca el pin 1 con la línea lateral extra en la esquina del pin 1 (abajo-derecha en la captura). '
                   'Además, girar el cristal 180° es inocuo (1↔3 y 2↔4 = GND); solo 90° sería un error.'),
    'J10': ('bien', 'USB-C: no necesita marca de pin 1, la carcasa y los pines de anclaje fijan la orientación.'),
}
for p in silk['pin1']:
    f = p['fp']
    if p.get('ok') is None:
        continue
    if not p['ok'] and f.ref in PIN1_MANUAL:
        sev, note = PIN1_MANUAL[f.ref]
        add('serigrafia', sev, f'{f.ref}: marca de pin 1 (revisada a mano)', f'({fmt(f.x)}, {fmt(f.y)})',
            'El script no la distingue por simetría de la serigrafía; revisión visual: ' + note,
            bounds=(p['p1'].x - 3.5, p['p1'].y - 3.5, p['p1'].x + 3.5, p['p1'].y + 3.5),
            marks=[('circle', (p['p1'].x, p['p1'].y), max(p['p1'].w, p['p1'].h) / 2 + 0.5)])
        continue
    if not p['ok']:
        sev = 'revisar' if f.dnp or f.ref.startswith('J') else 'bloqueante'
        if f.ref in ('J2', 'J3'):
            sev = 'revisar'
        add('serigrafia', sev, f'{f.ref}: sin marca de pin 1 clara', f'({fmt(f.x)}, {fmt(f.y)})',
            f'La serigrafía alrededor del pad 1 no se distingue de la del pad opuesto '
            f'(área cerca pin1 {p.get("a1", 0):.2f} mm² vs {p.get("a2", 0):.2f} mm²).',
            bounds=bnd(fp_body(f), 2), marks=[('circle', (p['p1'].x, p['p1'].y), max(p['p1'].w, p['p1'].h) / 2 + 0.5)])
for d in silk['polarity']:
    f = d['fp']
    k = d['k']
    if d['bidir']:
        add('serigrafia', 'revisar' if d['marked'] else 'bien', f'{f.ref} ({f.value}) bidireccional con marca de cátodo',
            f'({fmt(f.x)}, {fmt(f.y)})',
            'El TVS es bidireccional (CA), así que la orientación no importa eléctricamente, pero la huella D_SMB '
            'dibuja la marca de cátodo; puede inducir dudas en montaje/inspección. Opcional: huella sin marca o nota "BIDIR".',
            bounds=bnd(fp_body(f), 2), marks=[('geom', fp_body(f))])
    elif d['marked'] is not None and k is not None and d['marked'] is k:
        add('serigrafia', 'bien', f'{f.ref} ({f.value}): marca en el cátodo (pad {k.num} = {k.net})', f'({fmt(f.x)}, {fmt(f.y)})',
            'La serigrafía cierra el lado del pad K. Es la marca estándar de KiCad (corchete), sin barra ni "K"; '
            'se lee bien pero es discreta.', bounds=bnd(fp_body(f), 2), marks=[('circle', (k.x, k.y), max(k.w, k.h) / 2 + 0.4)])
    else:
        add('serigrafia', 'bloqueante', f'{f.ref}: marca de polaridad ausente o en el ánodo', f'({fmt(f.x)}, {fmt(f.y)})',
            str(d['pins']), bounds=bnd(fp_body(f), 2), marks=[('geom', fp_body(f))])
# DevKit orientation: two identical 1x22 sockets accept the DevKit rotated 180 deg
dk_silk = [g for g in B.gr if g.layer == 'F.SilkS' and g.kind != 'text' and DEVKIT.buffer(2).intersects(g.geom())]
dk_txt = [g.text for f in (J2, J3) for g in f.graphics if g.kind == 'text' and g.layer == 'F.SilkS' and not g.hidden]
add('serigrafia', 'revisar' if not dk_silk else 'bien', 'Sin contorno ni orientación de la DevKit en serigrafía', 'J2/J3',
    'Los dos zócalos 1×22 son iguales y la DevKit entra también girada 180°: con ello 5V/3V3/GND caen en pines '
    'equivocados y se puede dañar la placa. En la serigrafía solo aparece ' + ', '.join(dk_txt) +
    '; los nombres ESP32_S3_DEVKIT_LEFT/RIGHT están en F.Fab. Recomendado: contorno de la DevKit, flecha "ANTENA →" '
    'hacia el recorte y rótulos 3V3/5V/GND en los extremos de los zócalos. Prioridad alta (montaje manual).',
    bounds=bnd(DEVKIT, 3), marks=[('geom', DEVKIT.exterior.buffer(0.3))], ident='serigrafia-devkit')
names_missing = [b for b in silk['button_names'] if not b['ok']]
if names_missing:
    xs_ = [b['fp'] for b in names_missing]
    add('serigrafia', 'revisar', f'{len(names_missing)}/{len(silk["button_names"])} pulsadores sin su nombre en serigrafía',
        'SW1–SW16',
        'En F.SilkS solo aparece la referencia (SW1, SW10…). El nombre funcional (BTN_X, BTN_A_UP, SW_Boot…) está en '
        'F.Fab, que no se fabrica. Para montar, probar y depurar conviene ver el nombre: ' +
        ', '.join(f'{b["fp"].ref}={b["name"]}' for b in names_missing) + '.',
        bounds=(196, 22, 244, 72), marks=[('geom', fp_body(f)) for f in xs_], ident='serigrafia-botones')
for o in silk['over_pads']:
    f = o['fp']
    if o['area'] < 0.05:
        continue
    add('serigrafia', 'revisar', f'{f.ref}: serigrafía sobre pads ({o["area"]:.2f} mm²)', f'({fmt(f.x)}, {fmt(f.y)})',
        'El fabricante recorta la tinta sobre cobre expuesto; si es la marca de pin 1, puede desaparecer.',
        bounds=bnd(fp_body(f), 1.5), marks=[('geom', o['geom'].buffer(0.15))])
seen = set()
for o in silk['overlap']:
    a, b = o['a'], o['b']
    k = (a.owner.ref, b.owner.ref if b else 'pad')
    if k in seen:
        continue
    seen.add(k)
    if b is None:
        add('serigrafia', 'revisar', f'Texto "{a.text}" pisa pads', f'({fmt(a.at[0])}, {fmt(a.at[1])})',
            'La referencia cae sobre cobre expuesto y quedará recortada o ilegible.',
            bounds=(a.at[0] - 4, a.at[1] - 3, a.at[0] + 4, a.at[1] + 3), marks=[('geom', text_box(a))])
    else:
        add('serigrafia', 'revisar', f'Textos "{a.text}" y "{b.text}" se solapan', f'({fmt(a.at[0])}, {fmt(a.at[1])})',
            'Referencias superpuestas: no se pueden leer en montaje.',
            bounds=bnd(unary_union([text_box(a), text_box(b)]), 2.5), marks=[('geom', text_box(a)), ('geom', text_box(b))])
for t in silk['texts']:
    g = t['t']
    add('serigrafia', 'revisar', f'Texto pequeño "{g.text}"', f'({fmt(g.at[0])}, {fmt(g.at[1])})', t['why'] + ' (JLCPCB: ≥0,8 mm alto, ≥0,15 mm trazo).',
        bounds=(g.at[0] - 4, g.at[1] - 3, g.at[0] + 4, g.at[1] + 3))
for t in silk['off_board']:
    g = t['t']
    add('serigrafia', 'revisar', f'Texto "{g.text}" fuera del contorno', f'({fmt(g.at[0])}, {fmt(g.at[1])})', '',
        bounds=(g.at[0] - 4, g.at[1] - 3, g.at[0] + 4, g.at[1] + 3))

# ---------------------------------------------------------------- captures
for f in findings:
    if f['bounds']:
        fn = f'{f["id"]}.png'
        render.plot(B, f['bounds'], f['marks'], os.path.join(CAP, fn), title=f'{f["id"]}: {f["title"]}',
                    extra=dict(devkit=DEVKIT, screen=SCREEN), **f['render_opts'])
        f['img'] = f'capturas/{fn}'
render.overview(B, findings, os.path.join(CAP, 'vista-general.png'), DEVKIT, SCREEN)

# ---------------------------------------------------------------- summary data
def _min_gaps():
    import itertools as it
    best_part = (9, None, None); best_mask = (9, None, None)
    pads = [p for p in B.all_pads() if p.on_cu]
    for x, y in it.combinations(pads, 2):
        if abs(x.x - y.x) > 4 or abs(x.y - y.y) > 4:
            continue
        d = x.geom.distance(y.geom)
        if x.fp is not y.fp and d < best_part[0]:
            best_part = (d, str(x), str(y))
        if x.fp is y.fp and x.net != y.net and d < best_mask[0]:
            best_mask = (d, str(x), str(y))
    cy = [fp_body(f) for f in B.footprints if 'MountingHole' not in f.lib]
    ov = sum(1 for a_, b_ in itertools.combinations(cy, 2) if a_ is not None and b_ is not None and a_.intersection(b_).area > 0.01)
    return best_part, best_mask, ov
_gp, _gm, _ov = _min_gaps()
summary = dict(min_pad_gap_between_parts=_gp, min_mask_web_same_part=_gm, courtyard_overlaps=_ov,
    edge_pads=[(str(e['pad']), round(e['d'], 2)) for e in edge], mounting_hole_conflicts=len(mh),
    acid_traps_total=len(traps), acid_traps_lt60=sum(1 for t in traps if t['angle'] < 60), acid_traps_60_90=n_traps_60_90,
    slivers=len([f for f in findings if f['cat'] == 'astilla']),
    tht_on_planes=len(tht_planes), tht_on_planes_solid=len(solid),
    tht_planes_detail=[dict(pad=str(t['pad']), net=t['pad'].net, layer=t['layer'], cov=round(t['cov'], 2)) for t in tht_planes],
    big_pads_with_vias=[dict(pad=str(d['pad']), net=d['pad'].net, area=round(d['pad'].area, 2), vias=len(d['vias'])) for d in big_planes],
    maskwebs=len(maskwebs), maskweb_fps=sorted({m['fp'] for m in maskwebs}),
    maskweb_min=min((m['d'] for m in maskwebs), default=None),
    spacing_pairs=len(spacing), tht_smd=[dict(tht=str(r['tht']), smd=str(r['smd']), d=round(r['d'], 2)) for r in tht_smd],
    under_devkit=[dict(ref=u['fp'].ref, mpn=u['fp'].mpn, h=u['h'], src=u['src'], frac=round(u['part'], 2)) for u in under_dk],
    under_screen=[dict(ref=u['fp'].ref, mpn=u['fp'].mpn, h=u['h']) for u in sorted(under_scr, key=lambda u: -(u['h'] or 0))],
    pin1=[dict(ref=p['fp'].ref, ok=p.get('ok'), a1=round(p.get('a1', 0), 3), a2=round(p.get('a2', 0), 3)) for p in silk['pin1']],
    polarity=[dict(ref=d['fp'].ref, value=d['fp'].value, pins=d['pins'], bidir=d['bidir'],
                   marked=str(d['marked']) if d['marked'] else None) for d in silk['polarity']],
    buttons=[dict(ref=b['fp'].ref, name=b['name'], silk=b['silk']) for b in silk['button_names']],
    devkit_box=list(DEVKIT.bounds), screen_box=list(SCREEN.bounds),
)
for f in findings:
    f.pop('marks', None); f.pop('render_opts', None)
json.dump(dict(findings=findings, summary=summary), open(os.path.join(OUT, 'findings.json'), 'w'), indent=1,
          ensure_ascii=False, default=str)
cnt = collections.Counter(f['sev'] for f in findings)
print('findings:', dict(cnt))
for f in findings:
    print(f'[{f["sev"]:10}] {f["id"]:16} {f["title"]}')
print(json.dumps({k: v for k, v in summary.items() if k not in ('tht_planes_detail',)}, ensure_ascii=False, default=str)[:6000])
