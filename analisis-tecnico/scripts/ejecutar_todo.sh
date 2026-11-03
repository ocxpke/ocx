#!/usr/bin/env bash
# Reproduce todos los resultados y figuras del INFORME.md.
# Requisitos: python3 con numpy, scipy y matplotlib; ngspice (>= 42) y atlc (4.6.1) en el PATH.
#   Ubuntu/Debian: sudo apt install ngspice atlc && pip install numpy scipy matplotlib
set -euo pipefail
cd "$(dirname "$0")"
python3 si_geometria.py                 # geometría real: par USB, tramos paralelos, plano de referencia
python3 si_impedancias.py --atlc --mc 300   # atlc + solver propio + Monte Carlo de fabricación (~15 min)
python3 si_diafonia.py                  # matrices L/C y diafonía en el dominio del tiempo
python3 pdn_5v.py                       # caídas en +5V y tabla extremo a extremo
python3 pdn_planos.py                   # planos +3,3 V (In2) y GND (In1)
python3 mc_tolerancias.py               # Monte Carlo: buck, retroiluminado, filtro de audio
python3 hotplug_barridos.py             # hot-plug USB en ngspice (412 simulaciones)
python3 termico.py                      # modelo térmico de la placa
python3 figuras.py                      # figuras PNG
