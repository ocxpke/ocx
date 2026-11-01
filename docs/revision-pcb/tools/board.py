"""Geometry model of a KiCad 10 .kicad_pcb built with a minimal S-expression
parser (no pcbnew needed). Coordinates in mm, KiCad convention (Y down)."""
import math
from shapely.geometry import Point, Polygon, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
import sexp


def rot(x, y, deg):
    # KiCad: positive angle = counter-clockwise on screen (Y axis points down)
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def fnum(node, key, i=1, default=0.0):
    v = sexp.val(node, key, None, i)
    return float(v) if v is not None else default


class Pad:
    def __init__(self, fp, n):
        self.fp = fp
        self.num = n[1]
        self.kind = n[2]          # smd / thru_hole / np_thru_hole / connect
        self.shape = n[3]
        at = sexp.first(n, 'at')
        lx, ly = float(at[1]), float(at[2])
        self.angle = float(at[3]) if len(at) > 3 else 0.0   # absolute angle
        dx, dy = rot(lx, ly, fp.rot)
        self.x, self.y = fp.x + dx, fp.y + dy
        sz = sexp.first(n, 'size')
        self.w, self.h = float(sz[1]), float(sz[2])
        self.layers = sexp.first(n, 'layers')[1:]
        dr = sexp.first(n, 'drill')
        self.drill = None
        if dr is not None:
            nums = [d for d in dr[1:] if not isinstance(d, list) and d != 'oval']
            self.drill = float(nums[0]) if nums else None
        net = sexp.first(n, 'net')
        self.net = net[-1] if net is not None else ''
        zc = sexp.val(n, 'zone_connect')
        self.zone_connect = int(zc) if zc is not None else None
        self.rr = fnum(n, 'roundrect_rratio', default=0.0)
        self.on_cu = any(l in ('F.Cu', '*.Cu', 'B.Cu') for l in self.layers)
        self.geom = self._geom()

    def _geom(self):
        w, h = self.w, self.h
        if self.shape == 'circle':
            g = Point(0, 0).buffer(w / 2, 32)
        elif self.shape == 'oval':
            r = min(w, h) / 2
            if w >= h:
                g = LineString([(-w / 2 + r, 0), (w / 2 - r, 0)]).buffer(r, 16)
            else:
                g = LineString([(0, -h / 2 + r), (0, h / 2 - r)]).buffer(r, 16)
            if w == h:
                g = Point(0, 0).buffer(r, 32)
        elif self.shape == 'roundrect' and self.rr > 0:
            r = self.rr * min(w, h)
            g = box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, 8)
        else:
            g = box(-w / 2, -h / 2, w / 2, h / 2)
        g = affinity.rotate(g, -self.angle, origin=(0, 0))  # y-down -> negate
        return affinity.translate(g, self.x, self.y)

    @property
    def area(self):
        return self.geom.area

    def __repr__(self):
        return f'{self.fp.ref}.{self.num}'


class Graphic:
    def __init__(self, kind, layer, pts=None, width=0.0, fill=False, circle=None, text=None,
                 at=None, size=1.0, thick=0.15, angle=0.0, hidden=False, owner=None):
        self.kind, self.layer, self.pts, self.width, self.fill = kind, layer, pts, width, fill
        self.circle, self.text, self.at, self.size, self.thick = circle, text, at, size, thick
        self.angle, self.hidden, self.owner = angle, hidden, owner

    def geom(self):
        if self.kind == 'text':
            return None
        if self.kind == 'circle':
            (cx, cy), r = self.circle
            c = Point(cx, cy).buffer(r, 48)
            return c if self.fill else c.exterior.buffer(max(self.width, 0.01) / 2)
        if self.fill and len(self.pts) >= 3:
            return Polygon(self.pts).buffer(self.width / 2)
        return LineString(self.pts).buffer(max(self.width, 0.01) / 2, cap_style=1)


def arc_points(s, m, e, n=24):
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return [s, e]
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a1, a2, a3 = (math.atan2(p[1] - uy, p[0] - ux) for p in (s, m, e))
    def norm(a): return a % (2 * math.pi)
    # choose direction passing through mid
    ccw_span = norm(a3 - a1)
    if norm(a2 - a1) <= ccw_span:
        span = ccw_span
    else:
        span = ccw_span - 2 * math.pi
    return [(ux + r * math.cos(a1 + span * i / n), uy + r * math.sin(a1 + span * i / n)) for i in range(n + 1)]


class Footprint:
    def __init__(self, n):
        self.node = n
        self.lib = n[1]
        at = sexp.first(n, 'at')
        self.x, self.y = float(at[1]), float(at[2])
        self.rot = float(at[3]) if len(at) > 3 else 0.0
        self.layer = sexp.val(n, 'layer')
        self.props = {p[1]: p for p in sexp.find(n, 'property')}
        self.ref = self.props['Reference'][2]
        self.value = self.props['Value'][2]
        self.lcsc = self.props.get('LCSC', [None, None, None])[2]
        self.mpn = self.props.get('MPN', [None, None, None])[2]
        attr = sexp.first(n, 'attr')
        self.attr = attr[1:] if attr else []
        m = sexp.first(n, 'model')
        self.model = m[1].split('/')[-1] if m else None
        self.pads = [Pad(self, p) for p in sexp.find(n, 'pad')]
        self.graphics = []
        self._load_graphics()

    def tp(self, x, y):
        dx, dy = rot(float(x), float(y), self.rot)
        return self.x + dx, self.y + dy

    def _stroke(self, g):
        st = sexp.first(g, 'stroke')
        return float(sexp.val(st, 'width', 0)) if st else fnum(g, 'width')

    def _load_graphics(self):
        n = self.node
        for g in n:
            if not isinstance(g, list):
                continue
            k = g[0]
            layer = sexp.val(g, 'layer')
            if k == 'fp_line':
                s, e = sexp.first(g, 'start'), sexp.first(g, 'end')
                self.graphics.append(Graphic('line', layer, [self.tp(*s[1:3]), self.tp(*e[1:3])], self._stroke(g), owner=self))
            elif k == 'fp_rect':
                s, e = sexp.first(g, 'start'), sexp.first(g, 'end')
                x1, y1, x2, y2 = float(s[1]), float(s[2]), float(e[1]), float(e[2])
                pts = [self.tp(x1, y1), self.tp(x2, y1), self.tp(x2, y2), self.tp(x1, y2), self.tp(x1, y1)]
                fill = sexp.val(g, 'fill') in ('yes', 'solid')
                self.graphics.append(Graphic('poly', layer, pts, self._stroke(g), fill, owner=self))
            elif k == 'fp_poly':
                pts = [self.tp(p[1], p[2]) for p in sexp.find(sexp.first(g, 'pts'), 'xy')]
                fill = sexp.val(g, 'fill') in ('yes', 'solid')
                self.graphics.append(Graphic('poly', layer, pts + [pts[0]], self._stroke(g), fill, owner=self))
            elif k == 'fp_circle':
                c, e = sexp.first(g, 'center'), sexp.first(g, 'end')
                cx, cy = self.tp(*c[1:3])
                r = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
                fill = sexp.val(g, 'fill') in ('yes', 'solid')
                self.graphics.append(Graphic('circle', layer, None, self._stroke(g), fill, circle=((cx, cy), r), owner=self))
            elif k == 'fp_arc':
                s, m, e = (sexp.first(g, x) for x in ('start', 'mid', 'end'))
                pts = arc_points(self.tp(*s[1:3]), self.tp(*m[1:3]), self.tp(*e[1:3]))
                self.graphics.append(Graphic('line', layer, pts, self._stroke(g), owner=self))
            elif k in ('fp_text', 'property'):
                if k == 'property' and g[1] not in ('Reference', 'Value'):
                    if sexp.val(g, 'hide') == 'yes' or sexp.first(g, 'at') is None:
                        continue
                text = g[2]
                if k == 'property':
                    text = g[2]
                text = text.replace('${REFERENCE}', self.ref).replace('${VALUE}', self.value)
                at = sexp.first(g, 'at')
                if at is None:
                    continue
                ef = sexp.first(g, 'effects')
                font = sexp.first(ef, 'font') if ef else None
                size = float(sexp.first(font, 'size')[1]) if font and sexp.first(font, 'size') else 1.0
                thick = float(sexp.val(font, 'thickness', 0.15)) if font else 0.15
                hidden = (sexp.val(g, 'hide') == 'yes') or (ef is not None and sexp.val(ef, 'hide') == 'yes')
                ang = float(at[3]) if len(at) > 3 else 0.0
                self.graphics.append(Graphic('text', layer, None, 0, text=text, at=self.tp(at[1], at[2]),
                                             size=size, thick=thick, angle=ang, hidden=hidden, owner=self))

    def layer_geom(self, layer):
        gs = [g.geom() for g in self.graphics if g.layer == layer and g.kind != 'text']
        gs = [g for g in gs if g is not None]
        return unary_union(gs) if gs else None

    def courtyard(self):
        """Courtyard as filled polygon (outline closed)."""
        lines = [g for g in self.graphics if g.layer in ('F.CrtYd', 'B.CrtYd') and g.kind != 'text']
        if not lines:
            return None
        polys = []
        segs = []
        for g in lines:
            if g.kind == 'circle':
                (cx, cy), r = g.circle
                polys.append(Point(cx, cy).buffer(r, 48))
            elif g.kind == 'poly':
                polys.append(Polygon(g.pts))
            else:
                segs.append(LineString(g.pts))
        if segs:
            from shapely.ops import polygonize
            u = unary_union(segs)
            polys += list(polygonize(u))
        if not polys:
            return None
        # keep outer hull of polygons (union fills interior)
        u = unary_union(polys)
        return u

    @property
    def is_tht(self):
        return 'through_hole' in self.attr

    @property
    def is_smd(self):
        return 'smd' in self.attr

    @property
    def dnp(self):
        return 'dnp' in self.attr


class Board:
    def __init__(self, path):
        self.tree = sexp.parse(open(path, encoding='utf-8').read())
        b = self.tree
        self.footprints = [Footprint(f) for f in sexp.find(b, 'footprint')]
        self.fp = {f.ref: f for f in self.footprints}
        self.segments = []
        for s in sexp.find(b, 'segment'):
            st, en = sexp.first(s, 'start'), sexp.first(s, 'end')
            self.segments.append(dict(a=(float(st[1]), float(st[2])), b=(float(en[1]), float(en[2])),
                                      w=fnum(s, 'width'), layer=sexp.val(s, 'layer'), net=sexp.val(s, 'net')))
        self.vias = []
        for v in sexp.find(b, 'via'):
            at = sexp.first(v, 'at')
            self.vias.append(dict(x=float(at[1]), y=float(at[2]), size=fnum(v, 'size'), drill=fnum(v, 'drill'),
                                  net=sexp.val(v, 'net'), layers=sexp.first(v, 'layers')[1:]))
        self.zones = []
        for z in sexp.find(b, 'zone'):
            fills = []
            for fp_ in sexp.find(z, 'filled_polygon'):
                pts = [(float(p[1]), float(p[2])) for p in sexp.find(sexp.first(fp_, 'pts'), 'xy')]
                fills.append(Polygon(pts).buffer(0))
            self.zones.append(dict(net=sexp.val(z, 'net'), layer=sexp.val(z, 'layer'),
                                   fill=unary_union(fills) if fills else None, node=z))
        # board-level graphics
        self.gr = []
        for g in b:
            if not isinstance(g, list):
                continue
            if g[0] == 'gr_line':
                s, e = sexp.first(g, 'start'), sexp.first(g, 'end')
                self.gr.append(Graphic('line', sexp.val(g, 'layer'), [(float(s[1]), float(s[2])), (float(e[1]), float(e[2]))],
                                       fnum(sexp.first(g, 'stroke'), 'width')))
            elif g[0] == 'gr_arc':
                s, m, e = (sexp.first(g, x) for x in ('start', 'mid', 'end'))
                pts = arc_points(*[(float(p[1]), float(p[2])) for p in (s, m, e)])
                self.gr.append(Graphic('line', sexp.val(g, 'layer'), pts, fnum(sexp.first(g, 'stroke'), 'width')))
            elif g[0] == 'gr_text':
                at = sexp.first(g, 'at')
                ef = sexp.first(g, 'effects'); font = sexp.first(ef, 'font')
                self.gr.append(Graphic('text', sexp.val(g, 'layer'), text=g[1], at=(float(at[1]), float(at[2])),
                                       size=float(sexp.first(font, 'size')[1])))
        self.outline = self._outline()

    def _outline(self):
        from shapely.ops import polygonize
        lines = [LineString(g.pts) for g in self.gr if g.layer == 'Edge.Cuts' and g.kind == 'line']
        # snap endpoints (tiny gaps of 5e-5 mm in the file)
        u = unary_union([l.buffer(0.01) for l in lines])
        poly = Polygon(u.exterior) if hasattr(u, 'exterior') else max(u.geoms, key=lambda g: g.area)
        return Polygon(poly.exterior).buffer(-0.01)

    def all_pads(self):
        for f in self.footprints:
            for p in f.pads:
                yield p
