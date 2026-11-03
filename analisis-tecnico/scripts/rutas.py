"""Rutas comunes del análisis (relativas al repositorio)."""
from pathlib import Path
import tempfile
BASE = Path(__file__).resolve().parent              # analisis-tecnico/scripts
REPO = BASE.parents[1]                               # raíz del repositorio
PCB = REPO / 'hardware' / 'ocxPrototype.kicad_pcb'
RES = BASE.parent / 'resultados'
FIG = BASE.parent / 'figuras'
TMP = Path(tempfile.gettempdir()) / 'ocx_analisis'   # ficheros intermedios (BMP de atlc, netlists)
for d in (RES, FIG, TMP):
    d.mkdir(parents=True, exist_ok=True)
