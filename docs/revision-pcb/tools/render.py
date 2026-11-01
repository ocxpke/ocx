"""Matplotlib renderer for board captures (top view, KiCad-like colours)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle, PathPatch
from matplotlib.path import Path
from shapely.geometry import box, Polygon, MultiPolygon, GeometryCollection, LineString

BG = '#0d2a14'
COL = {'In1.Cu': '#3a6ea5', 'In2.Cu': '#a5763a', 'B.Cu': '#3f8fff', 'F.Cu': '#d9483b',
       'pad': '#d7b740', 'silk': '#f2f2f2', 'crt': '#ff4fd8', 'fab': '#9aa3ad', 'edge': '#f5e663'}


def _polys(g):
    if g is None or g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if hasattr(g, 'geoms'):
        out = []
        for x in g.geoms:
            out += _polys(x)
        return out
    return []


def _ring_path(coords):
    coords = list(coords)
    codes = [Path.MOVETO] + [Path.LINETO] * (len(coords) - 2) + [Path.CLOSEPOLY]
    return coords, codes


def _draw_geom(ax, g, **kw):
    for p in _polys(g):
        verts, codes = _ring_path(p.exterior.coords)
        for i in p.interiors:
            v, c = _ring_path(i.coords)
            verts += v; codes += c
        ax.add_patch(PathPatch(Path(verts, codes), **kw))


def draw_board(ax, B, view, show_planes=True, light=False, planes=None, plane_alpha=0.18):
    vb = box(*view)
    ax.set_facecolor('#222')
    _draw_geom(ax, B.outline.intersection(vb.buffer(5)), facecolor=BG, edgecolor=COL['edge'], lw=0.8, zorder=0)
    if show_planes:
        for z in B.zones:
            if planes and z['layer'] not in planes:
                continue
            g = z['fill'].intersection(vb.buffer(1))
            _draw_geom(ax, g, facecolor=COL[z['layer']], edgecolor='none', alpha=plane_alpha, zorder=1)
    for s in B.segments:
        if not LineString([s['a'], s['b']]).intersects(vb.buffer(2)):
            continue
        g = LineString([s['a'], s['b']]).buffer(s['w'] / 2, 8)
        _draw_geom(ax, g, facecolor=COL[s['layer']], edgecolor='none', alpha=0.75 if s['layer'] == 'F.Cu' else 0.45,
                   zorder=3 if s['layer'] == 'F.Cu' else 2)
    for v in B.vias:
        if vb.buffer(2).contains(box(v['x'], v['y'], v['x'], v['y']).centroid):
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color='#c0c0c0', zorder=4))
            ax.add_patch(Circle((v['x'], v['y']), v['drill'] / 2, color='#111', zorder=5))
    for f in B.footprints:
        if not any(p.geom.intersects(vb.buffer(3)) for p in f.pads) and not (view[0] - 10 < f.x < view[2] + 10 and view[1] - 10 < f.y < view[3] + 10):
            continue
        for g in f.graphics:
            if g.kind == 'text':
                if g.layer == 'F.SilkS' and not g.hidden:
                    ax.text(g.at[0], g.at[1], g.text, color=COL['silk'], fontsize=_fs(ax, g.size, view), rotation=g.angle,
                            ha='center', va='center', zorder=9, family='DejaVu Sans Mono', clip_on=True)
                elif g.layer == 'F.Fab' and not g.hidden and g.text != f.ref:
                    ax.text(g.at[0], g.at[1], g.text, color=COL['fab'], fontsize=_fs(ax, g.size, view) * 0.8, rotation=g.angle,
                            ha='center', va='center', zorder=6, style='italic', alpha=0.8, clip_on=True)
                continue
            if g.layer == 'F.SilkS':
                _draw_geom(ax, g.geom(), facecolor=COL['silk'], edgecolor='none', zorder=8)
            elif g.layer == 'F.CrtYd':
                _draw_geom(ax, g.geom(), facecolor=COL['crt'], edgecolor='none', alpha=0.7, zorder=7)
            elif g.layer == 'F.Fab':
                _draw_geom(ax, g.geom(), facecolor=COL['fab'], edgecolor='none', alpha=0.5, zorder=6)
        for p in f.pads:
            if not p.on_cu and p.kind != 'np_thru_hole':
                continue
            _draw_geom(ax, p.geom, facecolor=COL['pad'], edgecolor='none', zorder=5)
            if p.drill:
                ax.add_patch(Circle((p.x, p.y), p.drill / 2, color='#111', zorder=6))


def _fs(ax, size_mm, view):
    w = view[2] - view[0]
    return max(3.0, size_mm * 72 / 25.4 * (ax.figure.get_size_inches()[0] * 0.9 * 25.4) / w / 1.4)


def _marks(ax, marks):
    for m in marks:
        if m[0] == 'circle':
            ax.add_patch(Circle(m[1], m[2], fill=False, ec='#00f0ff', lw=2.2, zorder=20))
        elif m[0] == 'geom':
            for p in _polys(m[1]):
                ax.add_patch(MPoly(list(p.exterior.coords), closed=True, fill=False, ec='#00f0ff', lw=2.0, zorder=20))


def plot(B, bounds, marks, path, title='', extra=None, planes=None, plane_alpha=0.18):
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    # keep a sane aspect
    if w / h > 2.2:
        c = (y0 + y1) / 2; h = w / 2.2; y0, y1 = c - h / 2, c + h / 2
    if h / w > 1.6:
        c = (x0 + x1) / 2; w = h / 1.6; x0, x1 = c - w / 2, c + w / 2
    view = (x0, y0, x1, y1)
    fig, ax = plt.subplots(figsize=(7.5, 7.5 * (y1 - y0) / (x1 - x0) + 0.6), dpi=110)
    draw_board(ax, B, view, show_planes=True, planes=planes, plane_alpha=plane_alpha)
    if extra:
        for k, g in extra.items():
            if g.intersects(box(*view)):
                ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fill=False, ec='#7dff7d' if k == 'devkit' else '#ffa500',
                                   lw=1.2, ls='--', zorder=15))
    _marks(ax, marks)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0)
    ax.set_aspect('equal')
    ax.tick_params(labelsize=7)
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def overview(B, findings, path, devkit, screen):
    x0, y0, x1, y1 = B.outline.bounds
    view = (x0 - 3, y0 - 3, x1 + 3, y1 + 3)
    fig, ax = plt.subplots(figsize=(16, 8.6), dpi=110)
    draw_board(ax, B, view, show_planes=False)
    for g, c, lab in ((devkit, '#7dff7d', 'DevKit (supuesto)'), (screen, '#ffa500', 'Pantalla (supuesto)')):
        ax.add_patch(MPoly(list(g.exterior.coords), closed=True, fill=False, ec=c, lw=1.5, ls='--', zorder=15))
        ax.text(g.bounds[0] + 1, g.bounds[1] + 2, lab, color=c, fontsize=9, zorder=16)
    colors = {'bloqueante': '#ff2d2d', 'revisar': '#ffd400', 'bien': '#35d435'}
    for f in findings:
        if not f.get('bounds') or f['id'] in ('altura-pantalla', 'serigrafia-botones'):
            continue
        bx = f['bounds']
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        ax.add_patch(Circle((cx, cy), 1.6, fill=False, ec=colors[f['sev']], lw=2, zorder=20))
        ax.text(cx + 1.8, cy - 1.2, f['id'], color=colors[f['sev']], fontsize=6.5, zorder=21,
                bbox=dict(facecolor='#000', alpha=0.55, lw=0, pad=0.5))
    ax.set_xlim(view[0], view[2]); ax.set_ylim(view[3], view[1]); ax.set_aspect('equal')
    ax.set_title('OCX v1.0: vista superior con los hallazgos (rojo = bloqueante, amarillo = revisar, verde = bien)', fontsize=11)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
