#!/usr/bin/env python3
"""Genera los diagramas de la placa OCX a partir de hardware/ocxPrototype.kicad_pcb.

Lee el contorno (Edge.Cuts), las pistas de serigrafía y los pads de cada
footprint, y dibuja dos SVG con etiquetas:

  manual/img/placa-controles.svg   -> botones, joysticks, USB, LED (usuario)
  manual/img/placa-servicio.svg    -> conectores, puntos de prueba, CI (mantenimiento)

Uso:  python3 manual/herramientas/gen_placa.py
No necesita KiCad: incluye un lector mínimo de S-expressions.
"""
import math
import os
import re
from xml.sax.saxutils import escape

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PCB = os.path.join(RAIZ, "hardware", "ocxPrototype.kicad_pcb")
SALIDA = os.path.join(RAIZ, "manual", "img")

# ---------------------------------------------------------------- lector S-expr
_TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(texto):
    pila = [[]]
    for m in _TOK.finditer(texto):
        abre, cierra, cad, atomo = m.groups()
        if abre:
            pila.append([])
        elif cierra:
            x = pila.pop()
            pila[-1].append(x)
        elif cad is not None:
            pila[-1].append(cad.replace('\\"', '"'))
        elif atomo is not None:
            pila[-1].append(atomo)
    return pila[0][0]


def hijos(nodo, nombre):
    return [x for x in nodo if isinstance(x, list) and x and x[0] == nombre]


def hijo(nodo, nombre):
    r = hijos(nodo, nombre)
    return r[0] if r else None


# ---------------------------------------------------------------- geometría
class Footprint:
    def __init__(self, nodo):
        at = hijo(nodo, "at")
        self.x, self.y = float(at[1]), float(at[2])
        self.rot = float(at[3]) if len(at) > 3 else 0.0
        props = {p[1]: p[2] for p in hijos(nodo, "property")}
        self.ref = props.get("Reference", "")
        self.valor = props.get("Value", "")
        self.nodo = nodo

    def a_placa(self, dx, dy):
        a = math.radians(self.rot)
        return (self.x + dx * math.cos(a) + dy * math.sin(a),
                self.y - dx * math.sin(a) + dy * math.cos(a))

    def pads(self):
        for p in hijos(self.nodo, "pad"):
            at = hijo(p, "at")
            size = hijo(p, "size")
            cx, cy = self.a_placa(float(at[1]), float(at[2]))
            ang = float(at[3]) if len(at) > 3 else self.rot
            yield p[1], p[2], p[3], cx, cy, float(size[1]), float(size[2]), ang

    def centro(self):
        pts = [(cx, cy) for _, t, _, cx, cy, *_ in self.pads() if t != "np_thru_hole"]
        if not pts:
            return self.x, self.y
        xs, ys = zip(*pts)
        return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

    def caja(self):
        pts = []
        for _, _, _, cx, cy, w, h, _ in self.pads():
            r = max(w, h) / 2
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        xs, ys = zip(*pts)
        return min(xs), min(ys), max(xs), max(ys)

    def serigrafia(self):
        """Devuelve trazos de F.SilkS como listas de puntos en coordenadas de placa."""
        for g in self.nodo:
            if not (isinstance(g, list) and g and str(g[0]).startswith("fp_")):
                continue
            capa = hijo(g, "layer")
            if not capa or capa[1] != "F.SilkS":
                continue
            tipo = g[0]
            if tipo == "fp_line":
                s, e = hijo(g, "start"), hijo(g, "end")
                yield [self.a_placa(float(s[1]), float(s[2])), self.a_placa(float(e[1]), float(e[2]))]
            elif tipo == "fp_rect":
                s, e = hijo(g, "start"), hijo(g, "end")
                x0, y0, x1, y1 = float(s[1]), float(s[2]), float(e[1]), float(e[2])
                yield [self.a_placa(*p) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))]
            elif tipo == "fp_circle":
                c, e = hijo(g, "center"), hijo(g, "end")
                cx, cy = float(c[1]), float(c[2])
                r = math.hypot(float(e[1]) - cx, float(e[2]) - cy)
                yield [self.a_placa(cx + r * math.cos(t / 24 * 2 * math.pi),
                                    cy + r * math.sin(t / 24 * 2 * math.pi)) for t in range(25)]
            elif tipo == "fp_arc":
                s, m, e = hijo(g, "start"), hijo(g, "mid"), hijo(g, "end")
                yield [self.a_placa(float(p[1]), float(p[2])) for p in (s, m, e)]
            elif tipo == "fp_poly":
                pts = hijo(g, "pts")
                lst = [self.a_placa(float(xy[1]), float(xy[2])) for xy in hijos(pts, "xy")]
                if lst:
                    yield lst + [lst[0]]


def cargar():
    pcb = parse(open(PCB, encoding="utf-8").read())
    fps = [Footprint(f) for f in hijos(pcb, "footprint")]
    textos = []
    for t in hijos(pcb, "gr_text"):
        at = hijo(t, "at")
        if hijo(t, "layer")[1] == "F.SilkS":
            textos.append((t[1], float(at[1]), float(at[2])))
    bordes = []
    for g in pcb:
        if isinstance(g, list) and g and g[0] in ("gr_line", "gr_arc") and hijo(g, "layer")[1] == "Edge.Cuts":
            bordes.append(g)
    return fps, textos, bordes


def contorno_svg(bordes):
    """Une los segmentos de Edge.Cuts en un único path cerrado."""
    segs = []
    for g in bordes:
        s, e = hijo(g, "start"), hijo(g, "end")
        p0, p1 = (float(s[1]), float(s[2])), (float(e[1]), float(e[2]))
        mid = hijo(g, "mid")
        segs.append((p0, p1, (float(mid[1]), float(mid[2])) if mid else None))

    def cerca(a, b):
        return abs(a[0] - b[0]) < 1e-3 and abs(a[1] - b[1]) < 1e-3

    p0, p1, m = segs.pop(0)
    orden = [(p0, p1, m)]
    actual = p1
    while segs:
        for i, (a, b, mm) in enumerate(segs):
            if cerca(a, actual):
                orden.append((a, b, mm)); actual = b; segs.pop(i); break
            if cerca(b, actual):
                orden.append((b, a, mm)); actual = a; segs.pop(i); break
        else:
            break
    d = f"M {orden[0][0][0]:.3f} {orden[0][0][1]:.3f} "
    for a, b, mm in orden:
        if mm is None:
            d += f"L {b[0]:.3f} {b[1]:.3f} "
        else:
            # centro y radio del arco a partir de tres puntos
            (x1, y1), (x2, y2), (x3, y3) = a, mm, b
            dd = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
            ux = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1) + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / dd
            uy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3) + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / dd
            r = math.hypot(x1 - ux, y1 - uy)
            cruz = (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)
            barrido = 1 if cruz > 0 else 0
            d += f"A {r:.3f} {r:.3f} 0 0 {barrido} {b[0]:.3f} {b[1]:.3f} "
    return d + "Z"


# ---------------------------------------------------------------- dibujo
FUENTE = "DejaVu Sans, Liberation Sans, Arial, sans-serif"
VERDE = "#1f5f3a"
COBRE = "#c8a245"
SERIGRAFIA = "#f4f4f0"
TINTA = "#1d2733"
GRUPOS = {
    "cruceta": "#2f6fdb",
    "accion": "#d0452f",
    "gatillo": "#7a4bc2",
    "sistema": "#e08a00",
    "servicio": "#c0392b",
    "conector": "#0b7d8c",
    "info": "#44505c",
}


class Lienzo:
    def __init__(self, vb):
        self.vb = vb
        self.capas = []

    def add(self, s):
        self.capas.append(s)

    def texto(self, x, y, t, tam=3.2, color=TINTA, ancla="start", peso="normal", extra=""):
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FUENTE}" font-size="{tam}" '
                 f'fill="{color}" text-anchor="{ancla}" font-weight="{peso}" {extra}>{escape(t)}</text>')

    def svg(self, titulo):
        x0, y0, w, h = self.vb
        cuerpo = "\n".join(self.capas)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" '
                f'width="{w * 4:.0f}" height="{h * 4:.0f}">\n<title>{escape(titulo)}</title>\n'
                f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#ffffff"/>\n{cuerpo}\n</svg>\n')


def dibujar_placa(lz, fps, textos, bordes, atenuar=()):
    lz.add(f'<path d="{contorno_svg(bordes)}" fill="{VERDE}" stroke="#0e2e1c" stroke-width="0.5"/>')
    for f in fps:
        tenue = f.ref in atenuar
        for trazo in f.serigrafia():
            pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in trazo)
            lz.add(f'<polyline points="{pts}" fill="none" stroke="{SERIGRAFIA}" stroke-width="0.15" '
                   f'opacity="{0.35 if tenue else 0.8}"/>')
        for num, tipo, forma, cx, cy, w, h, ang in f.pads():
            if tipo == "np_thru_hole" or f.ref.startswith("REF"):
                r = w / 2
                lz.add(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="#ffffff" stroke="#888" stroke-width="0.2"/>')
                continue
            if forma == "circle":
                lz.add(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{w / 2:.2f}" fill="{COBRE}"/>')
            else:
                rx = min(w, h) / 2 if forma == "oval" else (min(w, h) * 0.25 if forma == "roundrect" else 0)
                lz.add(f'<rect x="{cx - w / 2:.3f}" y="{cy - h / 2:.3f}" width="{w:.3f}" height="{h:.3f}" rx="{rx:.3f}" '
                       f'fill="{COBRE}" transform="rotate({-ang:.1f} {cx:.3f} {cy:.3f})"/>')
    for t, x, y in textos:
        lz.texto(x, y + 1.0, t, tam=2.6, color=SERIGRAFIA, ancla="middle", peso="bold")


def boton(lz, fp, simbolo, color, tam=3.6):
    cx, cy = fp.centro()
    lz.add(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="3.7" fill="{color}" stroke="#ffffff" stroke-width="0.6"/>')
    lz.texto(cx, cy + tam * 0.36, simbolo, tam=tam, color="#ffffff", ancla="middle", peso="bold")


def etiqueta(lz, desde, hasta, lineas, color, ancla="start", tam=3.2, punto=True, codo=None):
    """Línea guía desde un punto de la placa hasta un texto de una o varias líneas.

    `codo` es un punto intermedio opcional para que la guía rodee otros elementos."""
    (x0, y0), (x1, y1) = desde, hasta
    pts = [desde] + ([codo] if codo else []) + [hasta]
    lz.add('<polyline points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in pts) +
           f'" fill="none" stroke="{color}" stroke-width="0.35"/>')
    if punto:
        lz.add(f'<circle cx="{x0:.2f}" cy="{y0:.2f}" r="0.9" fill="{color}" stroke="#fff" stroke-width="0.25"/>')
    paso = tam * 1.2
    if ancla == "middle":
        dx = 0
        y_ini = (y1 - 1.2 - (len(lineas) - 1) * paso) if y1 < y0 else (y1 + tam * 1.05)
    else:
        dx = 1.2 if ancla == "start" else -1.2
        y_ini = y1 + tam * 0.35
    for i, (t, peso) in enumerate(lineas):
        lz.texto(x1 + dx, y_ini + i * paso, t, tam=tam if i == 0 else tam * 0.85,
                 color=TINTA if i == 0 else "#4a5560", ancla=ancla, peso=peso)


def marco(lz, x0, y0, x1, y1, color, texto=None, vertical=False):
    lz.add(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="{color}" fill-opacity="0.18" '
           f'stroke="{color}" stroke-width="0.6" stroke-dasharray="2 1.2" rx="1"/>')
    if texto:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rot = f'transform="rotate(-90 {cx:.2f} {cy:.2f})"' if vertical else ""
        lz.texto(cx, cy + 1.2, texto, tam=3.0, color="#ffffff", ancla="middle", peso="bold", extra=rot)


def chip(lz, x, y, t, color=TINTA):
    w = len(t) * 1.55 + 2
    lz.add(f'<rect x="{x - w / 2:.2f}" y="{y - 2.2:.2f}" width="{w:.2f}" height="3.4" rx="0.8" fill="#ffffff" '
           f'fill-opacity="0.92" stroke="{color}" stroke-width="0.25"/>')
    lz.texto(x, y + 0.3, t, tam=2.4, color=color, ancla="middle", peso="bold")


def leyenda_pie(lz, y, t):
    lz.texto(130, y, t, tam=2.8, color="#4a5560", ancla="middle", extra='font-style="italic"')


# ---------------------------------------------------------------- figura 1: controles
def figura_controles(fps, textos, bordes):
    F = {f.ref: f for f in fps}
    lz = Lienzo((-58, -14, 376, 178))
    dibujar_placa(lz, fps, textos, bordes)

    # zona DevKit
    marco(lz, 142.2, 17.0, 169.9, 79.0, "#ffffff", "ESP32-S3-DevKitC-1", vertical=True)

    C = GRUPOS
    for ref, sim, g in [("SW2", "↑", "cruceta"), ("SW3", "→", "cruceta"), ("SW4", "←", "cruceta"),
                        ("SW5", "↓", "cruceta"), ("SW10", "X", "accion"), ("SW11", "O", "accion"),
                        ("SW12", "□", "accion"), ("SW13", "△", "accion"), ("SW1", "TL", "gatillo"),
                        ("SW15", "TR", "gatillo"), ("SW6", "SEL", "sistema"), ("SW7", "V−", "sistema"),
                        ("SW8", "V+", "sistema"), ("SW9", "⌂", "sistema"), ("SW14", "RST", "servicio"),
                        ("SW16", "BOOT", "servicio")]:
        boton(lz, F[ref], sim, C[g], tam=3.6 if len(sim) <= 2 else 2.3)

    def c(ref):
        return F[ref].centro()

    # izquierda
    IZ = 10
    etiqueta(lz, (c("SW2")[0] - 3.7, c("SW2")[1]), (IZ, c("SW2")[1]), [("SW2 · Cruceta arriba", "bold")], C["cruceta"], "end")
    etiqueta(lz, (c("SW4")[0] - 3.7, c("SW4")[1]), (IZ, c("SW4")[1]), [("SW4 · Cruceta izquierda", "bold")], C["cruceta"], "end")
    etiqueta(lz, (c("SW5")[0] - 3.7, c("SW5")[1]), (IZ, c("SW5")[1]), [("SW5 · Cruceta abajo", "bold")], C["cruceta"], "end")
    etiqueta(lz, (c("SW3")[0], c("SW3")[1] + 3.7), (IZ, 70), [("SW3 · Cruceta derecha", "bold")], C["cruceta"], "end",
             codo=(c("SW3")[0], 70))
    etiqueta(lz, c("J6"), (IZ, 84), [("J6 · Joystick izquierdo", "bold"), ("eje X/Y + pulsador L3", "normal")], C["conector"], "end")
    etiqueta(lz, c("J5"), (IZ, 112), [("J5 · Altavoz", "bold"), ("JST PH 2 vías", "normal")], C["conector"], "end")

    # derecha
    DE = 250
    etiqueta(lz, (c("SW13")[0] + 3.7, c("SW13")[1]), (DE, c("SW13")[1]), [("SW13 · Triángulo △", "bold")], C["accion"])
    etiqueta(lz, (c("SW11")[0] + 3.7, c("SW11")[1]), (DE, c("SW11")[1]), [("SW11 · Círculo O", "bold")], C["accion"])
    etiqueta(lz, (c("SW10")[0] + 3.7, c("SW10")[1]), (DE, c("SW10")[1]), [("SW10 · X", "bold")], C["accion"])
    etiqueta(lz, (c("SW12")[0], c("SW12")[1] + 3.7), (DE, 70), [("SW12 · Cuadrado □", "bold")], C["accion"],
             codo=(c("SW12")[0], 70))
    etiqueta(lz, c("J7"), (DE, 84), [("J7 · Joystick derecho", "bold"), ("eje X/Y + pulsador R3", "normal")], C["conector"])
    etiqueta(lz, c("D2"), (DE, 106), [("D2 · LED verde", "bold"), ("encendido = hay 3,3 V", "normal")], C["info"])

    # arriba
    etiqueta(lz, (c("SW1")[0], c("SW1")[1] - 3.7), (c("SW1")[0], 2), [("SW1 · Gatillo izquierdo (T_L)", "bold")], C["gatillo"], "middle")
    etiqueta(lz, (c("SW15")[0], c("SW15")[1] - 3.7), (c("SW15")[0], 2), [("SW15 · Gatillo derecho (T_R)", "bold")], C["gatillo"], "middle")
    etiqueta(lz, (c("SW14")[0], c("SW14")[1] - 3.7), (104, 2), [("SW14 · RESET", "bold")], C["servicio"], "middle")
    etiqueta(lz, (156, 18.5), (156, -5), [("Muesca «ANTENA»", "bold"), ("la antena de la DevKit va aquí", "normal")], C["info"], "middle")
    etiqueta(lz, (c("SW16")[0] + 3.7, c("SW16")[1]), (180, 2), [("SW16 · BOOT", "bold")], C["servicio"], "middle")

    # abajo
    abajo = [("SW6", "SW6 · SELECT", 96), ("SW7", "SW7 · VOL−", 121), ("SW8", "SW8 · VOL+", 146), ("SW9", "SW9 · HOME", 171)]
    for ref, t, x in abajo:
        etiqueta(lz, (c(ref)[0], c(ref)[1] + 3.7), (x, 140), [(t, "bold")], C["sistema"], "middle")
    etiqueta(lz, (c("J10")[0], 129.0), (212, 140), [("J10 · USB-C", "bold"), ("5 V + programación", "normal")], C["conector"], "middle")

    leyenda_pie(lz, 160, "Vista de la cara de componentes (frontal). Generado desde hardware/ocxPrototype.kicad_pcb · cotas en mm, placa 228 × 115,4 mm")
    return lz.svg("OCX v1.0 — mapa de controles")


# ---------------------------------------------------------------- figura 2: servicio
def figura_servicio(fps, textos, bordes):
    F = {f.ref: f for f in fps}
    lz = Lienzo((-58, -14, 376, 178))
    dibujar_placa(lz, fps, textos, bordes)

    def c(ref):
        return F[ref].centro()

    C = GRUPOS
    def resalta(ref, color, m=0.8):
        x0, y0, x1, y1 = F[ref].caja()
        lz.add(f'<rect x="{x0 - m:.2f}" y="{y0 - m:.2f}" width="{x1 - x0 + 2 * m:.2f}" height="{y1 - y0 + 2 * m:.2f}" '
               f'fill="none" stroke="{color}" stroke-width="0.7" rx="0.8"/>')

    for ref in ("J1", "J4", "J5", "J6", "J7", "J10", "J2", "J3"):
        resalta(ref, "#5fe0ff")
    for ref in ("TP1", "TP2", "TP3", "TP11", "TP12", "TP4", "C40", "D1", "D2"):
        resalta(ref, "#ffd54a", 0.5)
    for ref in ("SW14", "SW16"):
        boton(lz, F[ref], "RST" if ref == "SW14" else "BOOT", C["servicio"], tam=2.3)

    # pin 1 de los zócalos de la DevKit
    for ref in ("J2", "J3"):
        for num, _, _, cx, cy, *_ in F[ref].pads():
            if num == "1":
                lz.add(f'<rect x="{cx - 1.3:.2f}" y="{cy - 1.3:.2f}" width="2.6" height="2.6" fill="none" stroke="#ff4fa3" stroke-width="0.5"/>')
    chip(lz, 139.0, 21.0, "J2 pin 1 = 3V3", "#b0186a")
    chip(lz, 177.0, 81.5, "J3 pin 1 = GND", "#b0186a")

    # circuitos integrados (etiquetas sobre la placa)
    for ref, t, dx, dy in [("U1", "U1 BT817 (gráficos)", 0, 8.5), ("U7", "U7 flash W25Q128", -8, -6),
                           ("U5", "U5 MCP23017 (botones)", 7, 9.5), ("U4", "U4 PAM8302A (audio)", 0, -6),
                           ("U6", "U6 LMR51430 (3,3 V)", -2, -6), ("U8", "U8 DIO5661 (retroilum.)", 0, -6),
                           ("U2", "U2 USBLC6 (ESD)", 5, -9)]:
        x, y = c(ref)
        chip(lz, x + dx, y + dy, t)

    IZ, DE = 10, 250
    etiqueta(lz, c("J6"), (IZ, 80), [("J6 · FPC joystick izq.", "bold"), ("5 vías, 0,5 mm, cable por el sur", "normal")], C["conector"], "end")
    etiqueta(lz, c("TP11"), (IZ, 96), [("TP11 / TP12 · Retroiluminación", "bold"), ("¡hasta ~21 V con pantalla encendida!", "normal")], C["servicio"], "end")
    etiqueta(lz, c("J5"), (IZ, 112), [("J5 · Altavoz", "bold"), ("pin 1 = +, pin 2 = −", "normal")], C["conector"], "end")
    etiqueta(lz, c("SW14"), (IZ, 32), [("SW14 · RESET", "bold"), ("reinicia el ESP32-S3 (EN)", "normal")], C["servicio"], "end")
    etiqueta(lz, (c("J2")[0], 66), (IZ, 66), [("J2 / J3 · Zócalos DevKit", "bold"), ("2 × 22 pines, 2,54 mm", "normal")], C["conector"], "end")

    etiqueta(lz, c("J7"), (DE, 80), [("J7 · FPC joystick der.", "bold"), ("5 vías, 0,5 mm, cable por el sur", "normal")], C["conector"])
    etiqueta(lz, c("SW16"), (DE, 52), [("SW16 · BOOT", "bold"), ("modo descarga (GPIO0)", "normal")], C["servicio"])
    etiqueta(lz, c("C40"), (DE, 100), [("C40 · 100 µF", "bold"), ("amortigua el pico al enchufar", "normal")], C["info"])
    etiqueta(lz, c("D2"), (DE, 116), [("D2 · LED 3,3 V", "bold")], C["info"])
    etiqueta(lz, c("TP4"), (DE, 66), [("TP4 · 1,2 V (núcleo BT817)", "bold")], C["info"])

    etiqueta(lz, (156, 18.5), (156, -5), [("Muesca «ANTENA»", "bold"), ("nada metálico encima", "normal")], C["info"], "middle")

    etiqueta(lz, c("J1"), (92, 140), [("J1 · FPC pantalla", "bold"), ("40 vías, 0,5 mm", "normal")], C["conector"], "middle")
    etiqueta(lz, c("J4"), (128, 140), [("J4 · FPC táctil", "bold"), ("6 vías, 1 mm", "normal")], C["conector"], "middle")
    etiqueta(lz, c("TP2"), (174, 140), [("TP1 +5 V · TP2 GND · TP3 +3,3 V", "bold"), ("(de derecha a izquierda)", "normal")], C["info"], "middle")
    etiqueta(lz, c("D1"), (203, 152), [("D1 · TVS 6,8 V", "bold")], C["info"], "middle")
    etiqueta(lz, (c("J10")[0], 129.0), (231, 140), [("J10 · USB-C", "bold"), ("única entrada de energía", "normal")], C["conector"], "middle")

    leyenda_pie(lz, 162, "Vista de la cara de componentes. Cian: conectores · amarillo: puntos de prueba y protección · generado desde hardware/ocxPrototype.kicad_pcb")
    return lz.svg("OCX v1.0 — conectores y puntos de servicio")


def main():
    fps, textos, bordes = cargar()
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, fn in (("placa-controles.svg", figura_controles), ("placa-servicio.svg", figura_servicio)):
        ruta = os.path.join(SALIDA, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(fn(fps, textos, bordes))
        print("escrito", os.path.relpath(ruta, RAIZ))


if __name__ == "__main__":
    main()
