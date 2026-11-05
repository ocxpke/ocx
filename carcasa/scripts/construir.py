#!/usr/bin/env python3
"""Genera todo lo de carcasa/ a partir del .kicad_pcb y de scad/parametros.scad.

Pasos:
  1. extraer_pcb.py       -> scad/pcb_data.scad
  2. OpenSCAD "datos"     -> build/datos.json (zonas prohibidas, posiciones...)
  3. OpenSCAD por pieza   -> build/montaje/<pieza>.stl  (posición de montaje)
                             stl/<nn>_<pieza>.stl       (orientación de impresión)
  4. comprobar.py         -> COMPROBACIONES.md (sale con error si algo choca)
  5. renders.py           -> img/*.png            (opcional: --sin-renders)

Uso:  python3 carcasa/scripts/construir.py [--solo pieza1,pieza2] [--sin-renders] [-j 4]
Necesita OpenSCAD (2021.01 o posterior) en el PATH y, para las comprobaciones,
los paquetes de Python numpy, trimesh y manifold3d.
"""

import argparse
import ast
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
CARCASA = os.path.abspath(os.path.join(AQUI, '..'))
SCAD = os.path.join(CARCASA, 'scad', 'carcasa.scad')
BUILD = os.path.join(CARCASA, 'build')
STL = os.path.join(CARCASA, 'stl')

# Nombre de fichero de cada pieza (orden de la lista de impresión)
NOMBRES = {
    'probeta': '00_probeta_ajustes',
    'frontal_izquierda': '01_frontal_izquierda',
    'frontal_central': '02_frontal_central',
    'frontal_derecha': '03_frontal_derecha',
    'trasera_izquierda': '04_trasera_izquierda',
    'trasera_derecha': '05_trasera_derecha',
    'pisapantalla_izq': '06_pisapantalla_izq',
    'pisapantalla_der': '07_pisapantalla_der',
    'empujador_boot': '08_empujador_boot',
    'bandeja_capuchones': '09_bandeja_capuchones',
}
# Función de cada pulsador (para el nombre de los capuchones sueltos)
FUNCION = {'SW1': 'gatillo_L', 'SW2': 'arriba', 'SW3': 'derecha', 'SW4': 'izquierda', 'SW5': 'abajo',
           'SW6': 'select', 'SW7': 'vol_menos', 'SW8': 'vol_mas', 'SW9': 'home', 'SW10': 'X_cruz',
           'SW11': 'O_circulo', 'SW12': 'C_cuadrado', 'SW13': 'T_triangulo', 'SW15': 'gatillo_R'}


def openscad():
    exe = shutil.which('openscad')
    if not exe:
        sys.exit('No encuentro "openscad" en el PATH')
    return exe


def ejecutar_scad(salida, defs, registro=None):
    cmd = [openscad(), '-o', salida]
    for k, v in defs.items():
        cmd += ['-D', f'{k}={json.dumps(v) if isinstance(v, str) else v}']
    cmd.append(SCAD)
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if registro:
        with open(registro, 'w') as f:
            f.write(' '.join(cmd) + '\n' + r.stdout + r.stderr)
    errores = [l for l in r.stderr.splitlines() if 'ERROR' in l or 'WARNING' in l]
    if r.returncode != 0 or not os.path.exists(salida):
        raise RuntimeError(f'OpenSCAD falló para {defs}:\n' + r.stderr[-3000:])
    return time.time() - t, errores


def leer_datos():
    os.makedirs(BUILD, exist_ok=True)
    eco = os.path.join(BUILD, 'datos.echo')
    ejecutar_scad(eco, {'pieza': 'datos'})
    texto = open(eco, encoding='utf-8').read()
    m = re.search(r'ECHO: DATOS = (\[.*\])\s*$', texto, re.S)
    if not m:
        sys.exit('No encuentro DATOS en la salida de OpenSCAD')
    lit = m.group(1).replace('true', 'True').replace('false', 'False').replace('undef', 'None')
    datos = dict(ast.literal_eval(lit))
    with open(os.path.join(BUILD, 'datos.json'), 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=1, ensure_ascii=False)
    return datos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', default='', help='lista de piezas separadas por comas')
    ap.add_argument('--sin-renders', action='store_true')
    ap.add_argument('--sin-comprobar', action='store_true')
    ap.add_argument('-j', type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()

    subprocess.run([sys.executable, os.path.join(AQUI, 'extraer_pcb.py')], check=True)
    datos = leer_datos()
    piezas = datos['PIEZAS']
    if args.solo:
        piezas = [p for p in piezas if p in args.solo.split(',')]
    os.makedirs(os.path.join(BUILD, 'montaje'), exist_ok=True)
    os.makedirs(os.path.join(BUILD, 'logs'), exist_ok=True)
    os.makedirs(STL, exist_ok=True)

    trabajos = []
    for p in piezas:
        trabajos.append((os.path.join(BUILD, 'montaje', p + '.stl'), {'pieza': p, 'modo': 'montaje'},
                         os.path.join(BUILD, 'logs', p + '_montaje.log')))
        if p in NOMBRES:
            trabajos.append((os.path.join(STL, NOMBRES[p] + '.stl'), {'pieza': p, 'modo': 'impresion'},
                             os.path.join(BUILD, 'logs', p + '_impresion.log')))
        elif p.startswith('capuchon_'):
            # capuchones sueltos, boca abajo, por si hay que reimprimir alguno
            ref = p.split('_')[1]
            os.makedirs(os.path.join(STL, 'capuchones'), exist_ok=True)
            trabajos.append((os.path.join(STL, 'capuchones', f'{p}_{FUNCION.get(ref, ref)}.stl'),
                             {'pieza': p, 'modo': 'impresion'}, os.path.join(BUILD, 'logs', p + '_impresion.log')))
    if not args.solo or 'probeta' in args.solo:
        trabajos.append((os.path.join(STL, NOMBRES['probeta'] + '.stl'), {'pieza': 'probeta'},
                         os.path.join(BUILD, 'logs', 'probeta.log')))
    if not args.solo or 'bandeja_capuchones' in args.solo:
        trabajos.append((os.path.join(STL, NOMBRES['bandeja_capuchones'] + '.stl'), {'pieza': 'bandeja_capuchones'},
                         os.path.join(BUILD, 'logs', 'bandeja_capuchones.log')))

    def hacer(t):
        salida, defs, reg = t
        dt, errs = ejecutar_scad(salida, defs, reg)
        return salida, dt, errs

    with ThreadPoolExecutor(max_workers=args.j) as ex:
        for salida, dt, errs in ex.map(hacer, trabajos):
            print(f'  {os.path.relpath(salida, CARCASA):45s} {dt:6.1f} s' + (f'  ({len(errs)} avisos)' if errs else ''))
            for e in errs[:5]:
                print('      ', e)

    # STL de impresión: centrados en la cama, apoyados en z = 0 y en binario
    import trimesh
    for ruta in sorted(glob.glob(os.path.join(STL, '**', '*.stl'), recursive=True)):
        if True:
            tm = trimesh.load(ruta, force='mesh')
            lo, hi = tm.bounds
            tm.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
            tm.export(ruta)

    if not args.sin_comprobar:
        r = subprocess.run([sys.executable, os.path.join(AQUI, 'comprobar.py')])
        if r.returncode != 0:
            print('ATENCIÓN: las comprobaciones han encontrado problemas (ver COMPROBACIONES.md)')
    if not args.sin_renders:
        subprocess.run([sys.executable, os.path.join(AQUI, 'renders.py')], check=True)


if __name__ == '__main__':
    main()
