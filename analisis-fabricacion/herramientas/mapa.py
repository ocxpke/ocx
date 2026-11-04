#!/usr/bin/env python3
"""Dibuja la cara superior (vista desde arriba, igual que el visor de JLC) con:
  - pads de todas las huellas (gris; DNP en gris claro con contorno discontinuo),
  - pad 1 de las piezas con polaridad en rojo y su referencia,
  - para las huellas FT Origin=Center: «x» azul = ancla (lo que pone el CPL de
    kicad-cli) y «o» verde = centro de pads (lo que pone Fabrication Toolkit).

Solo lectura. Uso: python3 -I herramientas/mapa.py [salida] [resultados]
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.argv = sys.argv[:3]
import analizar as A  # noqa: E402  (reutiliza el modelo de huellas; reescribe resultados/analisis.*)

ESC = 10  # px por mm
X0, Y0, X1, Y1 = 14.0, 12.5, 246.0, 132.0


def P(x, y):
    return ((x - X0) * ESC, (y - Y0) * ESC)


def fuente(tam):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, tam)
    return ImageFont.load_default()


img = Image.new("RGB", (int((X1 - X0) * ESC), int((Y1 - Y0) * ESC) + 60), "white")
d = ImageDraw.Draw(img)
F = fuente(14)
FG = fuente(18)

# Borde de placa
for g in A.children(A.pcb, "gr_line"):
    if A.child(g, "layer")[1] == "Edge.Cuts":
        s, e = A.child(g, "start"), A.child(g, "end")
        d.line([P(float(s[1]), float(s[2])), P(float(e[1]), float(e[2]))], fill="black", width=3)
for g in A.children(A.pcb, "gr_arc"):
    if A.child(g, "layer")[1] == "Edge.Cuts":
        pts = [A.child(g, k) for k in ("start", "mid", "end")]
        d.line([P(float(p[1]), float(p[2])) for p in pts], fill="black", width=3)


def poligono_pad(p):
    a = math.radians(p["ang"])
    hw, hh = p["w"] / 2, p["h"] / 2
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx, ly = sx * hw, sy * hh
        pts.append(P(p["bx"] + lx * math.cos(a) + ly * math.sin(a), p["by"] - lx * math.sin(a) + ly * math.cos(a)))
    return pts


pol = set(A.POLARIDAD)
for h in A.huellas:
    for p in h.pads:
        if not any(l in ("F.Cu", "*.Cu") for l in p["layers"]):
            continue
        col = (225, 225, 225) if h.dnp else (150, 150, 150)
        if h.ref in pol and p["num"] == "1":
            col = (220, 0, 0)
        if p["forma"] == "circle":
            r = p["w"] / 2 * ESC
            cx, cy = P(p["bx"], p["by"])
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        else:
            d.polygon(poligono_pad(p), fill=col)

for h in A.huellas:
    if h.ref in pol:
        cx, cy = h.centro_pads_electricos()
        x, y = P(cx, cy)
        d.text((x + 6, y + 6), h.ref, fill=(160, 0, 0), font=F)
    if (h.ft_origin or "").strip().capitalize() == "Center":
        ax, ay = P(h.x, h.y)
        cx, cy = P(*h.centro_pads_ft())
        d.line([ax - 7, ay - 7, ax + 7, ay + 7], fill=(0, 70, 220), width=3)
        d.line([ax - 7, ay + 7, ax + 7, ay - 7], fill=(0, 70, 220), width=3)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=(0, 150, 0), width=3)
        d.line([ax, ay, cx, cy], fill=(0, 150, 0), width=1)
        if h.ref not in pol:
            d.text((cx + 8, cy - 18), h.ref, fill=(0, 110, 0), font=F)

yl = int((Y1 - Y0) * ESC) + 10
d.text((10, yl), "Cara superior vista desde arriba.  Rojo = pad 1 / polo + (C40) / cátodo (D2, D3).   "
       "x azul = ancla (CPL kicad-cli)   o verde = centro de pads (FT Origin=Center)", fill="black", font=FG)
os.makedirs(A.RES, exist_ok=True)
out = os.path.join(A.RES, "mapa-pin1-y-origen.png")
img.save(out, optimize=True)
print(out)
