#!/usr/bin/env python3
"""Renders PNG de la carcasa (necesita OpenSCAD y, sin pantalla, xvfb-run).

Escribe en carcasa/img/:
  montado.png, montado_trasera.png, explosionado.png, seccion.png, seccion_boot.png,
  seccion_joystick.png (cable del joystick), seccion_tft.png (cola de la pantalla y alargador),
  pieza_<nn>_<nombre>.png (cada STL de stl/) y paso_<nn>.png (montaje).
"""
import glob
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
CARCASA = os.path.abspath(os.path.join(AQUI, '..'))
SCAD = os.path.join(CARCASA, 'scad', 'renders.scad')
IMG = os.path.join(CARCASA, 'img')

CX, CY = 130.0, -72.2   # centro de la consola en coordenadas OpenSCAD


def cam_ojo(ojo, centro):
    return '--camera=' + ','.join(f'{v:.2f}' for v in list(ojo) + list(centro))


TRABAJOS = [
    ('planta.png', {'escena': 'planta'}, cam_ojo((CX, CY - 3, 390), (CX, CY - 3, 0)), (1800, 1000), 'o', False),
    ('montado.png', {'escena': 'montado'}, cam_ojo((CX - 110, CY - 250, 250), (CX, CY, 4)), (1600, 1100), 'p'),
    ('montado_trasera.png', {'escena': 'trasera'}, cam_ojo((CX + 120, CY - 240, -230), (CX, CY, 4)), (1600, 1100), 'p'),
    ('explosionado.png', {'escena': 'explosionado'}, cam_ojo((CX - 230, CY - 330, 240), (CX, CY, 25)), (1600, 1300), 'p'),
    ('seccion.png', {'escena': 'seccion'}, cam_ojo((CX, -49.75 - 170, 9), (CX, -49.75, 9)), (2000, 420), 'o', False),
    ('seccion_boot.png', {'escena': 'seccion_boot'}, cam_ojo((174.6 - 100, -45, 9), (174.6, -45, 9)), (1600, 560), 'o', False),
    ('seccion_joystick.png', {'escena': 'seccion_joy'}, cam_ojo((37.5 - 100, -99, 11.5), (37.5, -99, 11.5)), (1600, 800), 'o', False),
    ('seccion_tft.png', {'escena': 'seccion_tft'}, cam_ojo((108.74 - 100, -84, 11.5), (108.74, -84, 11.5)), (2100, 800), 'o', False),
]
for k in range(1, 11):
    if k < 10:
        TRABAJOS.append((f'paso_{k:02d}.png', {'escena': 'paso', 'paso': k},
                         cam_ojo((CX - 70, 72.2 - 230, 230), (CX, 72.2, 8)), (1400, 950), 'p'))
    else:
        TRABAJOS.append((f'paso_{k:02d}.png', {'escena': 'paso', 'paso': k},
                         cam_ojo((CX - 110, CY - 250, 250), (CX, CY, 4)), (1400, 950), 'p'))


def render(salida, defs, camara, tam, proy, viewall=True):
    cmd = ['xvfb-run', '-a', '-s', '-screen 0 2000x1600x24'] if shutil.which('xvfb-run') and not os.environ.get('DISPLAY') else []
    cmd += ['openscad', '-o', salida, f'--imgsize={tam[0]},{tam[1]}', '--colorscheme=Tomorrow',
            f'--projection={proy}', camara]
    if viewall:
        cmd.append('--viewall')
    for k, v in defs.items():
        cmd += ['-D', f'{k}="{v}"' if isinstance(v, str) else f'{k}={v}']
    cmd.append(SCAD)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(salida):
        raise RuntimeError(r.stderr[-2000:])
    return salida


# Planos de corte: nombre -> (normal, desplazamiento, grosor): se conserva d <= n·p (<= d + grosor si lo hay),
# en coordenadas OpenSCAD. Con grosor se dibuja solo una loncha y el fondo queda limpio.
CORTES = {'y4975': ((0.0, 1.0, 0.0), -49.75, None), 'x1746': ((1.0, 0.0, 0.0), 174.6, None),
          'x375': ((1.0, 0.0, 0.0), 37.5, 30.0), 'x10874': ((1.0, 0.0, 0.0), 108.74, 16.0)}
CAPS_CORTE = ['SW2', 'SW13', 'SW1', 'SW8']


def preparar_cortes():
    """Corta las piezas con manifold3d para que la cara de corte conserve su color."""
    import json
    import numpy as np
    import trimesh
    sys.path.insert(0, AQUI)
    from comprobar import a_manifold, cargar
    datos = json.load(open(os.path.join(CARCASA, 'build', 'datos.json'), encoding='utf-8'))
    piezas = {n: a_manifold(cargar(os.path.join(CARCASA, 'build', 'montaje', n + '.stl'))) for n in datos['PIEZAS']}

    def guarda(m, ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        if m.is_empty():
            m = __import__('manifold3d').Manifold.cube((0.01, 0.01, 0.01)).translate((0, 0, -500))
        mesh = m.to_mesh()
        trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False).export(ruta)

    for clave, (n, d, grosor) in CORTES.items():
        for nombre, m in piezas.items():
            m = m.trim_by_plane(n, d)
            if grosor:
                m = m.trim_by_plane(tuple(-v for v in n), -(d + grosor))
            guarda(m, os.path.join(CARCASA, 'build', 'corte', clave, nombre + '.stl'))
    # primer plano de capuchones: cada uno con su trozo de pieza frontal, cortados por el eje
    import manifold3d as mf
    centros = {r: c for _, r, c, _ in datos['botones']}
    for ref in CAPS_CORTE:
        c = centros[ref]
        frontal = 'frontal_central' if 100 < c[0] < 200 else ('frontal_izquierda' if c[0] < 100 else 'frontal_derecha')
        caja = mf.Manifold.cube((26, 26, 40)).translate((c[0] - 13, -c[1] - 13, -2))
        guarda((piezas[frontal] ^ caja).trim_by_plane((0, 1, 0), -c[1]), os.path.join(CARCASA, 'build', 'corte', 'caps', ref + '_frontal.stl'))
        guarda(piezas['capuchon_' + ref].trim_by_plane((0, 1, 0), -c[1]), os.path.join(CARCASA, 'build', 'corte', 'caps', ref + '_cap.stl'))


def main():
    os.makedirs(IMG, exist_ok=True)
    preparar_cortes()
    trabajos = [(os.path.join(IMG, t[0]),) + tuple(t[1:]) for t in TRABAJOS]
    trabajos.append((os.path.join(IMG, 'capuchones.png'), {'escena': 'capuchones'},
                     cam_ojo((36 - 25, -120, 50), (36, 0, 12)), (1600, 800), 'p', False))
    for stl in sorted(glob.glob(os.path.join(CARCASA, 'stl', '*.stl'))):
        base = os.path.splitext(os.path.basename(stl))[0]
        import trimesh
        lo, hi = trimesh.load(stl, force='mesh').bounds
        c = (lo + hi) / 2
        tam = max(hi - lo)
        ojo = c + tam * __import__('numpy').array([-0.55, -0.95, 0.85])
        trabajos.append((os.path.join(IMG, f'pieza_{base}.png'), {'escena': 'pieza', 'nombre': base},
                         cam_ojo(ojo, c), (1100, 800), 'p'))
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        for s in ex.map(lambda t: render(*t), trabajos):
            print('  ', os.path.relpath(s, CARCASA))


if __name__ == '__main__':
    sys.exit(main())
