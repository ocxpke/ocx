#!/usr/bin/env python3
"""Extrae del .kicad_pcb la geometría que necesita la carcasa.

Lee hardware/ocxPrototype.kicad_pcb (KiCad 10) y escribe:
  - carcasa/scad/pcb_data.scad : datos para OpenSCAD (no editar a mano)
  - carcasa/build/pcb_data.json: los mismos datos para los scripts de Python

Qué saca:
  - contorno de la placa (Edge.Cuts, líneas y arcos) como polígono cerrado
  - agujeros de montaje (huellas MountingHole)
  - todas las huellas: referencia, valor, posición, giro, caja del courtyard,
    caja de F.Fab, centro de los pads y pads pasantes (para las soldaduras
    que asoman por debajo)
  - una altura de "zona prohibida" por componente (tabla ALTURAS de abajo,
    son supuestos: revisa SUPUESTOS.md)

Todas las coordenadas son las del .kicad_pcb (mm, Y hacia abajo).
Uso:  python3 carcasa/scripts/extraer_pcb.py [ruta.kicad_pcb]
"""

import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kicad_sexpr import parse, children, child, value, floats  # noqa: E402

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PCB_POR_DEFECTO = os.path.join(RAIZ, 'hardware', 'ocxPrototype.kicad_pcb')
SALIDA_SCAD = os.path.join(RAIZ, 'carcasa', 'scad', 'pcb_data.scad')
SALIDA_JSON = os.path.join(RAIZ, 'carcasa', 'build', 'pcb_data.json')

# Altura máxima (mm sobre la cara superior de la placa) por tipo de huella.
# Se usa para las zonas prohibidas de la comprobación de interferencias.
# Valores de hoja de datos típicos redondeados hacia arriba (ver SUPUESTOS.md).
ALTURAS = [
    (r'PinSocket_1x22', 8.5),            # zócalo hembra (dato del enunciado)
    (r'SW_PUSH_6mm', 5.0),               # MLD-TS-6X6X5-J: 5 mm con el vástago
    (r'CP_Elec_6.3x5.8', 6.0),           # C40 (dato del enunciado)
    (r'JST_PH_B2B-PH-K', 6.0),           # cabezal JST PH vertical
    (r'USB_C_Receptacle_HRO_TYPE-C-31-M-12', 3.3),
    (r'TestPoint_Keystone_5000', 5.0),   # lazo de prueba en miniatura
    (r'TestPoint_Pad', 0.2),
    (r'Omron_XF2M', 2.0),
    (r'TE_84953', 2.6),
    (r'TE_0-1734839', 2.0),
    (r'L_Sunlord_SWPA4030S', 3.0),
    (r'L_Coilcraft_XxL4020', 2.1),
    (r'SOIC-28W', 2.65),
    (r'SOIC-8_5.3x5.3', 2.2),
    (r'SOIC-8', 1.75),
    (r'SOT-23', 1.45),
    (r'VQFN', 1.0),
    (r'D_SMB', 2.45),
    (r'D_SMA', 2.4),
    (r'Crystal_SMD_5032', 1.3),
    (r'_1206_', 1.8),
    (r'_0805_', 1.3),
    (r'_0603_', 1.0),
    (r'_0402_', 0.7),
    (r'MountingHole', 0.0),
]

# Cuánto asoman por debajo las patillas THT (mm bajo la cara inferior).
ASOMA_THT = 2.0


# Grupo de cada huella (para colores y para tratar aparte pulsadores y zócalos)
GRUPOS = [
    (r'SW_PUSH', 'pulsador'),
    (r'PinSocket', 'zocalo'),
    (r'JST|USB_C|FFC|FPC|TE_|Omron', 'conector'),
    (r'MountingHole', 'agujero'),
    (r'', 'smd'),
]


def grupo_de(lib):
    for patron, g in GRUPOS:
        if re.search(patron, lib):
            return g


def altura_de(lib):
    for patron, h in ALTURAS:
        if re.search(patron, lib):
            return h
    raise SystemExit(f'Sin altura definida para la huella {lib}: añádela a ALTURAS')


def a_placa(at, u, v):
    """Coordenadas locales de la huella -> coordenadas de placa (KiCad)."""
    x, y = at[0], at[1]
    a = math.radians(at[2] if len(at) > 2 else 0.0)
    return (x + u * math.cos(a) + v * math.sin(a),
            y - u * math.sin(a) + v * math.cos(a))


def arco_puntos(s, m, e, paso_grados=6.0):
    """Discretiza un arco definido por inicio, punto medio y fin."""
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a1 = math.atan2(y1 - uy, x1 - ux)
    a2 = math.atan2(y2 - uy, x2 - ux)
    a3 = math.atan2(y3 - uy, x3 - ux)

    def norm(a):
        return a % (2 * math.pi)
    # sentido: el que pasa por el punto medio
    ccw = norm(a2 - a1) < norm(a3 - a1)
    barrido = norm(a3 - a1) if ccw else -norm(a1 - a3)
    n = max(2, int(abs(math.degrees(barrido)) / paso_grados))
    pts = [(ux + r * math.cos(a1 + barrido * i / n), uy + r * math.sin(a1 + barrido * i / n)) for i in range(n + 1)]
    return pts, (ux, uy, r)


def contorno(pcb):
    segs = []
    arcos = []
    for g in pcb[1:]:
        if not isinstance(g, list) or not g or g[0] not in ('gr_line', 'gr_arc', 'gr_rect', 'gr_circle', 'gr_poly'):
            continue
        if value(g, 'layer') != 'Edge.Cuts':
            continue
        if g[0] == 'gr_line':
            segs.append([tuple(floats(g, 'start')[:2]), tuple(floats(g, 'end')[:2])])
        elif g[0] == 'gr_arc':
            pts, circ = arco_puntos(tuple(floats(g, 'start')[:2]), tuple(floats(g, 'mid')[:2]), tuple(floats(g, 'end')[:2]))
            segs.append(pts)
            arcos.append(circ)
        else:
            raise SystemExit(f'Edge.Cuts con {g[0]}: no soportado todavía')
    # Encadenar los tramos por sus extremos
    tol = 1e-3
    cadena = list(segs.pop(0))
    while segs:
        fin = cadena[-1]
        for i, s in enumerate(segs):
            if math.dist(s[0], fin) < tol:
                cadena += list(s[1:])
                segs.pop(i)
                break
            if math.dist(s[-1], fin) < tol:
                cadena += list(reversed(s))[1:]
                segs.pop(i)
                break
        else:
            raise SystemExit('El contorno Edge.Cuts no está cerrado o tiene varias islas')
    if math.dist(cadena[0], cadena[-1]) < tol:
        cadena.pop()
    return cadena, arcos


def prop(fp, nombre):
    for p in children(fp, 'property'):
        if p[1] == nombre:
            return p[2]
    return ''


def caja_de_capa(fp, at, capas):
    pts = []
    for g in fp[1:]:
        if not (isinstance(g, list) and g and g[0] in ('fp_line', 'fp_rect', 'fp_poly', 'fp_circle', 'fp_arc')):
            continue
        if value(g, 'layer') not in capas:
            continue
        loc = []
        if g[0] in ('fp_line', 'fp_rect'):
            s, e = floats(g, 'start')[:2], floats(g, 'end')[:2]
            loc += [s, e]
            if g[0] == 'fp_rect':
                loc += [[s[0], e[1]], [e[0], s[1]]]
        elif g[0] == 'fp_poly':
            loc += [[float(p[1]), float(p[2])] for p in child(g, 'pts')[1:]]
        elif g[0] == 'fp_circle':
            c, e = floats(g, 'center'), floats(g, 'end')
            r = math.dist(c[:2], e[:2])
            loc += [[c[0] + r * math.cos(t), c[1] + r * math.sin(t)] for t in [k * math.pi / 8 for k in range(16)]]
        elif g[0] == 'fp_arc':
            p, _ = arco_puntos(tuple(floats(g, 'start')[:2]), tuple(floats(g, 'mid')[:2]), tuple(floats(g, 'end')[:2]))
            loc += p
        pts += [a_placa(at, u, v) for (u, v) in loc]
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)]


def huellas(pcb):
    res = []
    for fp in children(pcb, 'footprint'):
        lib = fp[1]
        at = floats(fp, 'at')
        if len(at) < 3:
            at.append(0.0)
        capa = value(fp, 'layer')
        pads = []
        for p in children(fp, 'pad'):
            pat = floats(p, 'at')
            bx, by = a_placa(at, pat[0], pat[1])
            tam = floats(p, 'size') or [0, 0]
            dr = child(p, 'drill')
            taladro = 0.0
            if dr:
                nums = [float(v) for v in dr[1:] if isinstance(v, str) and re.match(r'^-?\d+(\.\d+)?$', v)]
                taladro = max(nums) if nums else 0.0
            pads.append({'num': p[1], 'tipo': p[2], 'x': round(bx, 3), 'y': round(by, 3),
                         'tam': [round(t, 3) for t in tam[:2]], 'taladro': taladro})
        centro_pads = None
        nums = [q for q in pads if q['num'] not in ('', 'MP', 'SH')]
        if nums:
            centro_pads = [round(sum(q['x'] for q in nums) / len(nums), 3), round(sum(q['y'] for q in nums) / len(nums), 3)]
        res.append({
            'ref': prop(fp, 'Reference'),
            'valor': prop(fp, 'Value'),
            'mpn': prop(fp, 'MPN'),
            'huella': lib.split(':')[-1],
            'capa': capa,
            'x': at[0], 'y': at[1], 'giro': at[2],
            'courtyard': caja_de_capa(fp, at, ('F.CrtYd', 'B.CrtYd')),
            'fab': caja_de_capa(fp, at, ('F.Fab', 'B.Fab')),
            'centro_pads': centro_pads,
            'pads': pads,
            'altura': altura_de(lib),
            'grupo': grupo_de(lib),
        })
    return res


def scad_num(v):
    return ('%.4f' % v).rstrip('0').rstrip('.') if isinstance(v, float) else str(v)


def scad_val(v):
    if isinstance(v, str):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return scad_num(float(v))
    if v is None:
        return 'undef'
    return '[' + ', '.join(scad_val(x) for x in v) + ']'


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else PCB_POR_DEFECTO
    with open(ruta, encoding='utf-8') as f:
        pcb = parse(f.read())

    grosor = float(value(child(pcb, 'general'), 'thickness'))
    poligono, arcos = contorno(pcb)
    xs = [p[0] for p in poligono]
    ys = [p[1] for p in poligono]
    bbox = [min(xs), min(ys), max(xs), max(ys)]
    radios = sorted({round(c[2], 3) for c in arcos})

    fps = huellas(pcb)
    agujeros = []
    componentes = []
    tht = []
    for h in fps:
        if 'MountingHole' in h['huella']:
            p = h['pads'][0]
            agujeros.append([h['x'], h['y'], p['taladro']])
            continue
        if h['capa'] != 'F.Cu':
            raise SystemExit(f"{h['ref']} está en {h['capa']}: la carcasa supone componentes solo arriba")
        componentes.append(h)
        for p in h['pads']:
            # Patillas pasantes reales (se excluyen vías térmicas y taladros sin cobre)
            if p['tipo'] == 'thru_hole' and p['taladro'] >= 0.5:
                tht.append([h['ref'], p['x'], p['y'], round(max(p['tam']) / 2, 3)])

    # La muesca de la antena: el tramo del contorno que entra hacia el interior
    # desde el borde superior (y mínima).
    ymin = bbox[1]
    muesca = None
    for i in range(len(poligono)):
        a, b = poligono[i], poligono[(i + 1) % len(poligono)]
        if abs(a[1] - ymin) < 1e-3 and abs(b[1] - ymin) > 1 and abs(a[0] - b[0]) < 1e-3:
            # bajada vertical desde el borde superior
            x0 = a[0]
            ybajo = b[1]
            # busca la subida
            for j in range(len(poligono)):
                c, d = poligono[j], poligono[(j + 1) % len(poligono)]
                if abs(c[1] - ybajo) < 1e-3 and abs(d[1] - ymin) < 1e-3 and abs(c[0] - d[0]) < 1e-3:
                    muesca = [min(x0, c[0]), ymin, max(x0, c[0]), ybajo]
            break

    datos = {
        'origen': os.path.relpath(ruta, RAIZ),
        'grosor': grosor,
        'contorno': [[round(x, 4), round(y, 4)] for x, y in poligono],
        'bbox': [round(v, 4) for v in bbox],
        'radios_esquina': radios,
        'muesca_antena': muesca,
        'agujeros': agujeros,
        'componentes': componentes,
        'tht': tht,
    }
    os.makedirs(os.path.dirname(SALIDA_JSON), exist_ok=True)
    with open(SALIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=1, ensure_ascii=False)

    L = []
    L.append('// GENERADO por carcasa/scripts/extraer_pcb.py a partir de %s' % datos['origen'])
    L.append('// No lo edites a mano: vuelve a ejecutar el script si cambia la placa.')
    L.append('// Coordenadas del .kicad_pcb (mm, eje Y hacia abajo).')
    L.append('')
    L.append('PCB_GROSOR = %s;' % scad_num(grosor))
    L.append('PCB_BBOX = %s;   // [xmin, ymin, xmax, ymax]' % scad_val(datos['bbox']))
    L.append('PCB_ANCHO = %s;' % scad_num(bbox[2] - bbox[0]))
    L.append('PCB_ALTO = %s;' % scad_num(bbox[3] - bbox[1]))
    L.append('PCB_RADIO_ESQUINA = %s;' % scad_num(max(radios) if radios else 0.0))
    L.append('PCB_MUESCA_ANTENA = %s;   // [xmin, ymin, xmax, ymax]' % scad_val(muesca))
    L.append('PCB_CONTORNO = %s;' % scad_val(datos['contorno']))
    L.append('// Agujeros de montaje: [x, y, diámetro]')
    L.append('PCB_AGUJEROS = %s;' % scad_val(agujeros))
    L.append('// Componentes: [ref, valor, huella, x, y, giro, courtyard[x0,y0,x1,y1], fab[x0,y0,x1,y1], centro_pads[x,y], altura, grupo]')
    L.append('PCB_COMPONENTES = [')
    for h in componentes:
        L.append('  %s,' % scad_val([h['ref'], h['valor'], h['huella'], h['x'], h['y'], h['giro'],
                                     h['courtyard'], h['fab'], h['centro_pads'], h['altura'], h['grupo']]))
    L.append('];')
    L.append('// Patillas pasantes que asoman por debajo: [ref, x, y, radio del pad]')
    L.append('PCB_THT = %s;' % scad_val(tht))
    L.append('PCB_ASOMA_THT = %s;' % scad_num(ASOMA_THT))
    os.makedirs(os.path.dirname(SALIDA_SCAD), exist_ok=True)
    with open(SALIDA_SCAD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')

    # Resumen por consola (sirve para comprobar los datos del enunciado)
    print(f'Placa: {bbox[2]-bbox[0]:.2f} x {bbox[3]-bbox[1]:.2f} mm, grosor {grosor} mm, '
          f'radios de esquina {radios}')
    print(f'Muesca de la antena: x {muesca[0]:g}-{muesca[2]:g}, y {muesca[1]:g}-{muesca[3]:g}')
    print('Agujeros:', ', '.join(f'({x:g};{y:g}) Ø{d:g}' for x, y, d in agujeros))
    for h in componentes:
        if re.match(r'^(SW|J|C40$|D2$)', h['ref']):
            c = h['centro_pads']
            print(f"  {h['ref']:5s} {h['valor'][:22]:22s} en ({h['x']:g};{h['y']:g}) giro {h['giro']:g}"
                  f"  centro pads ({c[0]:g};{c[1]:g})  alto {h['altura']:g}")
    print(f'{len(componentes)} componentes, {len(tht)} patillas THT, escrito {os.path.relpath(SALIDA_SCAD, RAIZ)}')


if __name__ == '__main__':
    main()
