#!/usr/bin/env python3
"""Comprobación automática de la carcasa OCX.

Lee build/datos.json (exportado por OpenSCAD con pieza="datos"), las piezas en
posición de montaje (build/montaje/*.stl) y las de impresión (stl/*.stl), y
comprueba con booleanas exactas (manifold3d):

  1. Tamaño: ninguna pieza de impresión supera 135 mm en ningún eje.
  2. Choques pieza-componente: ninguna pieza invade una zona prohibida
     (componentes con su altura, DevKit, pantalla, FPC, joysticks, altavoz,
     patillas THT bajo la placa, clavija USB-C y la zona de la antena).
  3. Choques entre piezas montadas (uniones, labios, capuchones...).
  4. Capuchones y empujador de BOOT: recorrido libre hacia abajo (debe
     llegar a pulsar), tope hacia arriba (no se salen) y que no se hundan.
  5. Joysticks: el stick inclinado al máximo en 24 direcciones no toca nada.
  6. Tornillos: no tocan componentes ni la antena y agarran lo suficiente.
  7. Voladizos de impresión (informativo).

Escribe carcasa/COMPROBACIONES.md y sale con código 1 si algo falla.
"""

import glob
import json
import math
import os
import sys

import numpy as np
import trimesh
import manifold3d as mf

AQUI = os.path.dirname(os.path.abspath(__file__))
CARCASA = os.path.abspath(os.path.join(AQUI, '..'))
BUILD = os.path.join(CARCASA, 'build')
TOL_VOL = 1e-3      # mm³: por debajo se considera contacto, no choque
FALLOS = []
FILAS = {}


def anota(seccion, nombre, ok, detalle):
    FILAS.setdefault(seccion, []).append((nombre, ok, detalle))
    if ok is False:
        FALLOS.append(f'{seccion}: {nombre}: {detalle}')


def a_manifold(tm):
    mesh = mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32),
                   tri_verts=np.asarray(tm.faces, dtype=np.uint32))
    m = mf.Manifold(mesh)
    if m.status() != mf.Error.NoError:
        raise RuntimeError(f'malla no cerrada: {m.status()}')
    return m


def cargar(ruta):
    tm = trimesh.load(ruta, force='mesh', process=True)
    tm.merge_vertices()
    return tm


def caja(b, z0, z1):
    x0, y0, x1, y1 = b
    return mf.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, -y1, z0))


def cil(c, r, z0, z1, n=32):
    return mf.Manifold.cylinder(z1 - z0, r, r, n).translate((c[0], -c[1], z0))


def zona_manifold(z):
    if z[0] == 'caja':
        return caja(z[3], z[4], z[5])
    if z[0] == 'cil':
        return cil(z[3], z[4], z[5], z[6])
    if z[0] == 'poli':
        cs = mf.CrossSection([[(p[0], -p[1]) for p in z[3]]])
        return mf.Manifold.extrude(cs, z[5] - z[4]).translate((0, 0, z[4]))
    if z[0] == 'redondeada_y':
        (cx, y0, y1), (an, al), r, cz = z[3], z[4], z[5], z[6]
        largo = y1 - y0
        cils = [mf.Manifold.cylinder(largo, r, r, 24).rotate((90, 0, 0)).translate((cx + sx * (an / 2 - r), -y0, cz + sz * (al / 2 - r)))
                for sx in (-1, 1) for sz in (-1, 1)]
        return mf.Manifold.batch_hull(cils)
    raise ValueError(z[0])


def vol(m):
    return 0.0 if m.is_empty() else m.volume()


def bbox(m):
    b = m.bounding_box()
    return np.array(b[:3]), np.array(b[3:])


def solapan(a, b, margen=0.0):
    (a0, a1), (b0, b1) = a, b
    return bool(np.all(a0 <= b1 + margen) and np.all(b0 <= a1 + margen))


def fmt_caja(m):
    lo, hi = bbox(m)
    # en coordenadas KiCad para que se pueda buscar en la placa
    return f'x {lo[0]:.1f}–{hi[0]:.1f}, y {-hi[1]:.1f}–{-lo[1]:.1f}, z {lo[2]:.1f}–{hi[2]:.1f}'


def choca(a, b):
    if not solapan(bbox(a), bbox(b)):
        return 0.0, None
    i = a ^ b
    v = vol(i)
    return v, (i if v > TOL_VOL else None)


def recorrido_libre(movil, obstaculos, direccion, maximo, paso=0.02):
    """Distancia que se puede mover `movil` en `direccion` (vector) hasta tocar algo."""
    def toca(t):
        m = movil.translate(tuple(np.array(direccion) * t))
        return any(choca(m, o)[0] > TOL_VOL for o in obstaculos)
    if not toca(maximo):
        return maximo
    lo, hi = 0.0, maximo
    if toca(0.0):
        return 0.0
    while hi - lo > paso:
        mid = (lo + hi) / 2
        if toca(mid):
            hi = mid
        else:
            lo = mid
    return lo


def main():
    datos = json.load(open(os.path.join(BUILD, 'datos.json'), encoding='utf-8'))
    piezas_nombres = datos['PIEZAS']
    piezas = {}
    for n in piezas_nombres:
        ruta = os.path.join(BUILD, 'montaje', n + '.stl')
        if not os.path.exists(ruta):
            sys.exit(f'Falta {ruta}: ejecuta construir.py')
        piezas[n] = a_manifold(cargar(ruta))
    frontales = [n for n in piezas_nombres if n.startswith('frontal')]
    traseras = [n for n in piezas_nombres if n.startswith('trasera')]
    limite = datos['limite_pieza']

    # ---------------------------------------------------------------- 1
    for ruta in sorted(glob.glob(os.path.join(CARCASA, 'stl', '**', '*.stl'), recursive=True)):
        tm = cargar(ruta)
        ext = tm.extents
        ok = bool(np.all(ext <= limite + 1e-6))
        anota('1. Tamaño de impresión (≤ %d mm)' % limite, os.path.basename(ruta), ok,
              f'{ext[0]:.1f} × {ext[1]:.1f} × {ext[2]:.1f} mm' + ('' if tm.is_watertight else '  (¡malla abierta!)'))

    # ---------------------------------------------------------------- 2
    zonas = [(z, zona_manifold(z)) for z in datos['zonas']]
    for n, M in piezas.items():
        bb = bbox(M)
        n_ok = 0
        for z, Z in zonas:
            if not solapan(bb, bbox(Z)):
                continue
            v, inter = choca(M, Z)
            if inter is not None:
                anota('2. Choques pieza–componente', f'{n} ↔ {z[1]}', False, f'{v:.2f} mm³ en {fmt_caja(inter)}')
            else:
                n_ok += 1
        anota('2. Choques pieza–componente', n, True, f'sin choques ({n_ok} zonas cercanas revisadas)')

    # ---------------------------------------------------------------- 3
    nombres = list(piezas)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            v, inter = choca(piezas[a], piezas[b])
            if inter is not None:
                anota('3. Choques entre piezas montadas', f'{a} ↔ {b}', False, f'{v:.2f} mm³ en {fmt_caja(inter)}')
    if not any(not ok for _, ok, _ in FILAS.get('3. Choques entre piezas montadas', [])):
        anota('3. Choques entre piezas montadas', f'{len(nombres)} piezas', True,
              f'ningún par se solapa ({len(nombres) * (len(nombres) - 1) // 2} pares)')

    # ---------------------------------------------------------------- 4
    def obstaculos_para(nombre, excluir_refs):
        obs = [piezas[o] for o in piezas if o != nombre]
        for z, Z in zonas:
            if z[2] == 'vastago' and any(z[1].startswith(r + '_') for r in excluir_refs):
                continue
            if z[2] in ('pcb',):
                continue
            obs.append(Z)
        return obs

    juego, rec, sw_alto, zf = datos['cap_juego'], datos['sw_recorrido'], datos['sw_alto'], datos['ZF']
    for n, ref, c, z_top in datos['botones']:
        cap = piezas[n]
        cerca = [o for o in obstaculos_para(n, [ref]) if solapan(bbox(cap), bbox(o), 4.0)]
        abajo = recorrido_libre(cap, cerca, (0, 0, -1), 2.0)
        arriba = recorrido_libre(cap, cerca, (0, 0, 1), 3.0)
        sobresale = z_top - zf
        ok = abajo >= rec + 0.1 and 0.05 <= arriba <= 1.0 and sobresale - rec > 0.3
        anota('4. Capuchones', f'{n} ({ref})', ok,
              f'baja libre {abajo:.2f} mm (clic a {rec} mm) · sube {arriba:.2f} mm hasta el tope · '
              f'sobresale {sobresale:.1f} mm (pulsado {sobresale - rec:.2f})')
    emp = piezas['empujador_boot']
    cerca = [o for o in obstaculos_para('empujador_boot', ['SW16']) if solapan(bbox(emp), bbox(o), 4.0)]
    abajo = recorrido_libre(emp, cerca, (0, 0, -1), 2.0)
    arriba = recorrido_libre(emp, cerca, (0, 0, 1), 3.0)
    ok = abajo >= rec + 0.1 and 0.05 <= arriba <= 1.0
    anota('4. Capuchones', 'empujador_boot (SW16)', ok,
          f'baja libre {abajo:.2f} mm · sube {arriba:.2f} mm hasta el tope (la varilla toca la piel)')

    # ---------------------------------------------------------------- 5
    z_base, pivote, total, cap_d, cap_alto, eje_d, incl = datos['joy']
    for pos, giro, pieza in datos['joysticks']:
        x, y = pos[0], -pos[1]
        zp = z_base + pivote
        stick = (mf.Manifold.cylinder(total - pivote - cap_alto, eje_d / 2, eje_d / 2, 24).translate((0, 0, 0)) +
                 mf.Manifold.cylinder(cap_alto, cap_d / 2, cap_d / 2, 48).translate((0, 0, total - pivote - cap_alto)))
        obst = [piezas[pieza]] + [Z for z, Z in zonas if z[2] not in ('joystick', 'pcb')]
        peor = None
        for k in range(24):
            az = 2 * math.pi * k / 24
            eje = (math.cos(az + math.pi / 2), math.sin(az + math.pi / 2), 0.0)
            # rotación de Rodrigues alrededor del eje horizontal
            th = math.radians(incl)
            K = np.array([[0, -eje[2], eje[1]], [eje[2], 0, -eje[0]], [-eje[1], eje[0], 0]])
            R = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
            T = np.hstack([R, np.array([[x], [y], [zp]])])
            m = stick.transform(T.tolist())
            for o in obst:
                v, inter = choca(m, o)
                if inter is not None:
                    peor = (math.degrees(az), v, fmt_caja(inter))
                    break
            if peor:
                break
        anota('5. Joysticks (stick inclinado %g°)' % incl, f'{pieza} en ({pos[0]:g};{pos[1]:g})', peor is None,
              'libre en 24 direcciones' if peor is None else f'toca a {peor[0]:.0f}°: {peor[1]:.2f} mm³ en {peor[2]}')

    # ---------------------------------------------------------------- 6
    for nombre, p0, p1, d, tipo in datos['tornillos']:
        p0, p1 = np.array(p0), np.array(p1)
        largo = float(np.linalg.norm(p1 - p0))
        eje = (p1 - p0) / largo
        # cilindro alineado con el eje
        z = np.array([0, 0, 1.0])
        v = np.cross(z, eje)
        s, c = np.linalg.norm(v), float(np.dot(z, eje))
        if s < 1e-9:
            R = np.eye(3) if c > 0 else np.diag([1, -1, -1])
        else:
            K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            R = np.eye(3) + K + K @ K * ((1 - c) / s ** 2)
        T = np.hstack([R, p0.reshape(3, 1)])
        torn = mf.Manifold.cylinder(largo, d / 2, d / 2, 16).transform(T.tolist())
        cabeza = mf.Manifold.cylinder(3.0, 2.75, 2.75, 16).translate((0, 0, -3.0)).transform(T.tolist())
        golpes = []
        for zz, Z in zonas:
            if zz[2] == 'pcb' and tipo == 'placa':
                continue
            for parte in (torn, cabeza):
                vv, inter = choca(parte, Z)
                if inter is not None:
                    golpes.append(zz[1])
                    break
        detalle = 'no toca componentes ni la antena' if not golpes else 'toca ' + ', '.join(sorted(set(golpes)))
        if tipo == 'placa':
            agarre = float(p1[2])   # la torreta empieza en z = 0 (cara superior de la placa)
            detalle += f' · rosca dentro de la torreta {agarre:.1f} mm'
            ok_agarre = agarre >= 4.0
        else:
            ok_agarre = True
        anota('6. Tornillería', nombre, not golpes and ok_agarre, detalle)
    for nombre, g in datos['pernos']:
        # g = [xfc, xbc, xft, xbt, xa, xp, xt0, xt1]; la punta debe pasar toda la tuerca
        t0, t1, punta, asiento = g[6], g[7], g[5], g[4]
        lado = 1 if punta > asiento else -1
        pasa = (punta - max(t0, t1)) * lado if lado > 0 else (min(t0, t1) - punta)
        anota('6. Tornillería', f'tuerca {nombre}', pasa >= 0.3, f'el tornillo atraviesa la tuerca y sobresale {pasa:.2f} mm')

    # ---------------------------------------------------------------- 7
    for ruta in sorted(glob.glob(os.path.join(CARCASA, 'stl', '*.stl'))):
        tm = cargar(ruta)
        n = tm.face_normals
        areas = tm.area_faces
        zmin = tm.bounds[0][2]
        cz = tm.triangles_center[:, 2]
        abajo = n[:, 2] < -math.cos(math.radians(45)) - 1e-6
        cama = cz < zmin + 0.05
        vol_area = float(areas[abajo & ~cama].sum())
        plano = abajo & ~cama & (n[:, 2] < -0.999)
        anota('7. Voladizos de impresión (informativo)', os.path.basename(ruta), None,
              f'{vol_area:.0f} mm² hacia abajo con más de 45° (de ellos {float(areas[plano].sum()):.0f} mm² son '
              f'techos planos: puentes de agujeros y ranuras)')

    escribir_informe(datos)
    print(f'Comprobaciones: {len(FALLOS)} fallos')
    for f in FALLOS:
        print('  FALLO', f)
    return 1 if FALLOS else 0


def escribir_informe(datos):
    L = ['# Comprobaciones automáticas de la carcasa', '',
         'Generado por `scripts/comprobar.py` con booleanas exactas (manifold3d) sobre los STL de `build/montaje/`. '
         'No lo edites: se regenera con `python3 carcasa/scripts/construir.py`.', '',
         f'**Resultado: {"TODO CORRECTO" if not FALLOS else f"{len(FALLOS)} FALLOS"}**', '',
         f'Cara frontal en z = {datos["ZF"]:.2f} mm, trasera en z = {datos["Z_TRASERA"]:.2f} mm '
         f'(grosor total {datos["ZF"] - datos["Z_TRASERA"]:.1f} mm). Paredes {datos["pared"]} mm, '
         f'cara frontal {datos["piel"]} mm, tapa trasera {datos["suelo"]} mm, holgura {datos["holgura"]} mm.', '']
    for seccion in sorted(FILAS):
        L += [f'## {seccion}', '', '| Elemento | Estado | Detalle |', '|---|---|---|']
        for nombre, ok, detalle in FILAS[seccion]:
            estado = 'ℹ️' if ok is None else ('✅' if ok else '❌')
            L.append(f'| {nombre} | {estado} | {detalle} |')
        L.append('')
    with open(os.path.join(CARCASA, 'COMPROBACIONES.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    sys.exit(main())
