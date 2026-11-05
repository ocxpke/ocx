#!/usr/bin/env python3
"""Estima tiempo y filamento de cada STL de stl/ con PrusaSlicer (CLI) y el
perfil aproximado perfil/finder_pla_0.2.ini. Escribe build/estimacion.json.

Uso: python3 carcasa/scripts/estimar_impresion.py
"""
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
CARCASA = os.path.abspath(os.path.join(AQUI, '..'))
PERFIL = os.path.join(CARCASA, 'perfil', 'finder_pla_0.2.ini')


def segundos(txt):
    s = 0
    for n, u in re.findall(r'(\d+)\s*([dhms])', txt):
        s += int(n) * {'d': 86400, 'h': 3600, 'm': 60, 's': 1}[u]
    return s


def main():
    exe = shutil.which('prusa-slicer')
    if not exe:
        raise SystemExit('No encuentro prusa-slicer')
    pre = ['xvfb-run', '-a'] if shutil.which('xvfb-run') and not os.environ.get('DISPLAY') else []
    res = {}
    with tempfile.TemporaryDirectory() as tmp:
        for stl in sorted(glob.glob(os.path.join(CARCASA, 'stl', '*.stl'))):
            base = os.path.basename(stl)
            g = os.path.join(tmp, base + '.gcode')
            r = subprocess.run(pre + [exe, '--export-gcode', '--load', PERFIL, '--center', '70,70', '-o', g, stl],
                               capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(g):
                print('  fallo al laminar', base, r.stderr[-500:])
                continue
            txt = open(g, encoding='utf-8', errors='replace').read()
            gramos = float(re.search(r'; (?:total )?filament used \[g\] = ([\d.]+)', txt).group(1))
            metros = float(re.search(r'; (?:total )?filament used \[mm\] = ([\d.]+)', txt).group(1)) / 1000
            t = re.search(r'; estimated printing time \(normal mode\) = (.+)', txt).group(1)
            res[base] = {'gramos': round(gramos, 1), 'metros': round(metros, 2), 'tiempo': t.strip(), 'segundos': segundos(t)}
            print(f'  {base:32s} {gramos:6.1f} g  {metros:6.2f} m  {t.strip()}')
    tot_g = sum(v['gramos'] for v in res.values())
    tot_s = sum(v['segundos'] for v in res.values())
    print(f'  TOTAL {tot_g:.0f} g, {tot_s / 3600:.1f} h')
    os.makedirs(os.path.join(CARCASA, 'build'), exist_ok=True)
    with open(os.path.join(CARCASA, 'build', 'estimacion.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
