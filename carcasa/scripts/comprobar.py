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
  5. Joysticks: el stick inclinado al máximo en 24 direcciones no toca nada, y el cable
     llega a J6/J7 con una S (forma de una tira elástica empotrada en sus dos extremos)
     con un radio de curvatura suficiente y sin tocar nada.
  6. Tornillos: no tocan componentes ni la antena y agarran lo suficiente.
  7. Voladizos de impresión (informativo).
  8. Cola de la pantalla y alargador: el adaptador y el FFC no tocan la DevKit ni otros
     componentes, y el FFC es lo bastante largo.

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


def elastica(D, H, L, N=120):
    """Forma de equilibrio de una tira elástica de largo L empotrada en horizontal en sus dos
    extremos: sale de (0, 0) hacia +u y llega a (D, -H) también hacia +u. Minimiza la energía
    de flexión con los extremos fijos (Newton sobre las condiciones de Lagrange, N tramos).
    Devuelve (u, z, radio mínimo, inclinación máxima en grados) o None si no hay ninguna S
    (el cable no llega o tendría que dar la vuelta)."""
    if L <= math.hypot(D, H) + 1e-6:
        return None
    h = L / N
    s = (np.arange(N) + 0.5) / N
    base = math.atan2(H, D)
    idx = np.arange(N)

    def residuo(x):
        phi, lu, lz = x[:N], x[N], x[N + 1]
        p = np.concatenate([[0.0], phi, [0.0]])
        F = (2 * p[1:-1] - p[:-2] - p[2:]) / h + lu * h * np.sin(phi) - lz * h * np.cos(phi)
        return np.concatenate([F, [h * np.cos(phi).sum() - D, h * np.sin(phi).sum() + H]])

    def jacobiana(x):
        phi, lu, lz = x[:N], x[N], x[N + 1]
        J = np.zeros((N + 2, N + 2))
        J[idx, idx] = 2 / h + lu * h * np.cos(phi) + lz * h * np.sin(phi)
        J[idx[1:], idx[:-1]] = -1 / h
        J[idx[:-1], idx[1:]] = -1 / h
        J[idx, N], J[idx, N + 1] = h * np.sin(phi), -h * np.cos(phi)
        J[N, idx], J[N + 1, idx] = -h * np.sin(phi), h * np.cos(phi)
        return J

    for amp in (2.0, 1.6, 1.3, 2.4, 1.0, 2.8):
        x = np.concatenate([-amp * base * (1 - np.cos(2 * math.pi * s)) / 2, [0.0, 0.0]])
        for _ in range(80):
            r = residuo(x)
            nr = np.linalg.norm(r)
            if nr < 1e-10:
                break
            try:
                dx = np.linalg.solve(jacobiana(x), -r)
            except np.linalg.LinAlgError:
                break
            a = 1.0
            while a > 1e-4 and np.linalg.norm(residuo(x + a * dx)) >= nr:
                a /= 2
            x = x + a * dx
        phi = x[:N]
        if np.linalg.norm(residuo(x)) < 1e-8 and np.all(np.abs(phi) < math.pi):
            u = np.concatenate([[0.0], np.cumsum(h * np.cos(phi))])
            z = np.concatenate([[0.0], np.cumsum(h * np.sin(phi))])
            curv = np.abs(np.diff(np.concatenate([[0.0], phi, [0.0]]))) / h
            return u, z, 1 / max(curv.max(), 1e-9), math.degrees(-phi.min())
    return None


def tira(pts_yz, x, ancho, e):
    """Volumen de una tira plana (cable o FFC) de `ancho` en x y grosor `e` alrededor de la
    polilínea [(y KiCad, z), ...]."""
    P = np.stack([-np.asarray([p[0] for p in pts_yz], float), np.asarray([p[1] for p in pts_yz], float)], 1)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-6])
    P = P[keep]
    d = np.gradient(P, axis=0)
    t = d / np.linalg.norm(d, axis=1, keepdims=True)
    n = np.stack([-t[:, 1], t[:, 0]], 1) * (e / 2)
    cs = mf.CrossSection([np.concatenate([P + n, (P - n)[::-1]]).tolist()], mf.FillRule.NonZero)
    T = [[0, 0, 1, x - ancho / 2], [1, 0, 0, 0], [0, 1, 0, 0]]
    return mf.Manifold.extrude(cs, ancho).transform(T)


def invade(m, obstaculos):
    """Nombres de los obstáculos [(nombre, manifold)] que `m` invade."""
    bb = bbox(m)
    return [n for n, o in obstaculos if solapan(bb, bbox(o)) and choca(m, o)[1] is not None]


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

    # Cable de cada joystick: sale hacia el norte por el borde del módulo y entra en J6/J7 hacia
    # el norte, con los contactos arriba. Su forma es la de una tira elástica empotrada en los dos
    # extremos (la que toma sola). Tiene que llegar, no doblarse por debajo del radio mínimo y no
    # tocar ninguna pieza, componente ni la placa.
    jf = dict(datos['joy_fpc'])
    sec5 = '5. Joysticks (stick inclinado %g°)' % incl
    for nombre, pieza, conector, zona_propia, salida, yb, za, zb, xc, tacos in datos['cables_joy']:
        D, H, x = salida[1] - yb, za - zb, salida[0]
        excluir = {conector, zona_propia, nombre + '_base', nombre + '_cupula', *tacos}
        zona_caja = caja([x - 8, yb - 8, x + 8, salida[1] + 8], -2, za + 8)
        obst = [(n, M) for n, M in piezas.items() if solapan(bbox(M), bbox(zona_caja))]
        obst += [(z[1], Z) for z, Z in zonas if z[1] not in excluir and solapan(bbox(Z), bbox(zona_caja))]

        def evalua(largo):
            r = elastica(D, H, largo - jf['inserta'])
            if r is None:
                return None
            u, zz, rmin, ang = r
            pts = [(salida[1] - a, za + b) for a, b in zip(u, zz)] + [(yb - jf['inserta'], zb)]
            return rmin, ang, invade(tira(pts, x, jf['ancho'], jf['e']), obst), zz

        def valido(largo):
            r = evalua(largo)
            return r is not None and r[0] >= jf['radio_min'] and not r[2]

        nom = evalua(jf['largo'])
        # largos que caben con el módulo donde está (barrido y luego bisección en los bordes)
        cuerda = jf['inserta'] + math.hypot(D, H)
        rejilla = [cuerda + 0.05 + 0.5 * k for k in range(int((jf['inserta'] + 60 - cuerda) / 0.5))]
        oks = [valido(L) for L in rejilla]
        tramos, ini = [], None
        for L, ok in zip(rejilla + [None], oks + [False]):
            if ok and ini is None:
                ini = L
            if not ok and ini is not None:
                tramos.append([ini, prev])
                ini = None
            prev = L
        rango = None
        if tramos:
            rango = list(next((t for t in tramos if t[0] <= jf['largo'] <= t[1]), tramos[0]))
            malo, bueno = rango[0] - 0.5, rango[0]          # borde inferior
            for _ in range(8):
                m = (malo + bueno) / 2
                malo, bueno = (malo, m) if valido(m) else (m, bueno)
            rango[0] = bueno
            bueno, malo = rango[1], rango[1] + 0.5          # borde superior
            for _ in range(8):
                m = (malo + bueno) / 2
                bueno, malo = (m, malo) if valido(m) else (bueno, m)
            rango[1] = bueno
        txt_rango = (f'Con el módulo aquí caben de {rango[0]:.1f} a {rango[1]:.1f} mm' if rango
                     else 'Con el módulo aquí no cabe ningún largo')
        libre = jf['largo'] - jf['inserta']
        if nom is None:
            anota(sec5, f'cable {nombre} → {conector}', False,
                  f'LARGO {jf["largo"]:g} mm ({libre:g} libres): no llega. Del borde del módulo a la boca hay '
                  f'{math.hypot(D, H):.1f} mm en línea recta. {txt_rango}')
        else:
            rmin, ang, toca, zz = nom
            ok = rmin >= jf['radio_min'] and not toca
            anota(sec5, f'cable {nombre} → {conector}', ok,
                  f'LARGO {jf["largo"]:g} mm ({libre:g} libres + {jf["inserta"]:g} dentro de {conector}): S de '
                  f'{D:.2f} mm hacia el norte y {H:.2f} mm de bajada, radio mínimo {rmin:.1f} mm '
                  f'(≥ {jf["radio_min"]:g}), inclinación máxima {ang:.0f}°, sin dar la vuelta (contactos arriba). '
                  f'{txt_rango}' + (f'. Toca: {", ".join(sorted(set(toca)))}' if toca else ''))
        desvio = abs(x - xc)
        anota(sec5, f'cable {nombre}: entrada', desvio <= 0.3 and D > 0,
              f'sale del borde norte del módulo (y = {salida[1]:.1f}) y entra recto en {conector}: '
              f'desvío lateral {desvio:.2f} mm' if D > 0 else f'el módulo no queda al sur de {conector} (D = {D:.2f} mm)')
        # tacos de espuma: sobre placa libre y sin tocar el cable
        comp = [(z[1], Z) for z, Z in zonas if z[2] not in ('espuma', 'joystick', 'fpc', 'pcb', 'tht', 'antena')]
        cable = tira([(salida[1] - a, za + b) for a, b in zip(*elastica(D, H, libre)[:2])] + [(yb - jf['inserta'], zb)],
                     x, jf['ancho'], jf['e']) if nom else None
        malos = []
        for tn in tacos:
            T = next(Z for z, Z in zonas if z[1] == tn)
            g = invade(T, comp + ([('cable', cable)] if cable else []))
            if g:
                malos.append(f'{tn} toca {", ".join(g)}')
        anota(sec5, f'tacos de {nombre}', not malos,
              f'los {len(tacos)} tacos de espuma apoyan en placa sin componentes y no tocan el cable' if not malos
              else '; '.join(malos))

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

    # ---------------------------------------------------------------- 8
    sec8 = '8. Cola de la pantalla y alargador'
    t = dict(datos['tft'])
    ad, x = t['ad'], t['x']
    baja = t['z_film'] - t['ffc_z_conector']
    anota(sec8, 'sin alargador', None,
          f'la cola, doblada hacia atrás, baja como mucho {t["cola_baja_max"]:g} mm y de la trasera de la pantalla a la '
          f'ranura de J1 hay {baja:.1f} mm (además J1 queda {t["j1_boca"] - t["ancha"][0]:.0f} mm al sur del final de la '
          f'parte ancha): no llega')
    AD = caja(ad, t['ad_z0'], t['z_trasera'])
    componentes = [(z[1], Z) for z, Z in zonas if z[2] not in ('fpc', 'adaptador', 'pantalla', 'antena', 'espuma')]
    toca = invade(AD, componentes + list(piezas.items()))
    dk = t['devkit']
    sep_dk = max(dk[0] - ad[2], ad[0] - dk[2], dk[1] - ad[3], ad[1] - dk[3])
    debajo = [bbox(Z)[1][2] for n, Z in componentes
              if n != 'PCB' and solapan((np.array([ad[0], -ad[3], -50]), np.array([ad[2], -ad[1], t['ad_z0']])), bbox(Z))]
    alto = max(debajo) if debajo else 0.0
    anota(sec8, 'adaptador', not toca and sep_dk > 0,
          f'pegado a la trasera al final de la cola: x {ad[0]:.1f}–{ad[2]:.1f}, y {ad[1]:.1f}–{ad[3]:.1f}, '
          f'z {t["ad_z0"]:.1f}–{t["z_trasera"]:.1f}; a {sep_dk:.1f} mm de la DevKit (x {dk[0]:.0f}–{dk[2]:.0f}, '
          f'hasta 15.9 mm); debajo, lo más alto llega a z = {alto:.1f} ({t["ad_z0"] - alto:.1f} mm de aire)'
          + (f'. Toca: {", ".join(toca)}' if toca else ''))
    cola = tira(t['cola_puntos'], x, t['cola_ancho'], 0.15)
    toca = invade(cola, [(n, Z) for n, Z in componentes + list(piezas.items())])
    anota(sec8, 'cola hasta el adaptador', not toca,
          f'llega plana por la trasera: {t["ancha_largo"]:g} mm de parte ancha + {t["cola_largo"]:g} mm de cola + '
          f'{t["extremo"]:g} mm de extremo ({t["inserta"]:g} dentro del adaptador); baja '
          f'{t["z_film"] - t["ad_ranura_z"]:.1f} mm hasta la boca en los últimos 8 mm (de {t["cola_flexible"]:g} flexibles)'
          + (f'. Toca: {", ".join(toca)}' if toca else ''))
    ffc = tira(t['ffc_puntos'], x, t['ffc_ancho'], t['ffc_e'])
    excl = {'J1', 'Adaptador_TFT', 'FFC_TFT'}
    toca = invade(ffc, [(z[1], Z) for z, Z in zonas if z[1] not in excl] + list(piezas.items()))
    r1, r2 = t['ffc_r']
    ok_largo = t['ffc_largo'] >= t['ffc_largo_min']
    anota(sec8, 'FFC de 40 vías hasta J1', ok_largo and min(r1, r2) >= 1.0 and not toca,
          f'sale del adaptador hacia el norte, vuelve bajo la pantalla a z = {t["ffc_z_tramo"]:.1f} y entra en J1 hacia el '
          f'norte; vueltas de radio {r1:.1f} y {r2:.1f} mm. Hace falta un FFC de {t["ffc_largo_min"]:.0f} mm o más: con '
          f'{t["ffc_largo"]:g} mm la vuelta junto al adaptador llega a y = {t["ffc_y_v1"] - r1:.1f}'
          + ('' if ok_largo else ' (¡demasiado corto!)') + ('. No toca piezas, componentes ni la placa' if not toca
                                                         else f'. Toca: {", ".join(sorted(set(toca)))}'))

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
