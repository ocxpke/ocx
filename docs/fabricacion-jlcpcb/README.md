# OCX v1.0: revisión de fabricación para JLCPCB

Fecha: 2026-11-01 · Herramienta: **KiCad 10.0.8** (`kicad-cli`) · Fuente: `hardware/` del commit `6948262` (sin modificar)

Pedido de referencia: PCB de **4 capas, 1,6 mm, ENIG**, con montaje SMT y THT en la cara superior.

## Resultado

| Bloque | Resultado |
|---|---|
| DRC (reglas del proyecto + paridad con el esquemático) | **0 errores y 0 avisos activos.** Hay 3 avisos y 2 «unconnected» que el proyecto ya tiene excluidos (ver abajo). Paridad esquemático↔PCB: 0 |
| DRC con reglas JLCPCB (`scripts/jlcpcb.kicad_dru`) | **0 violaciones nuevas** |
| ERC | **0 activos.** Hay 4 avisos `footprint_filter` (J1, J4, J6, J7) que el proyecto ya tiene excluidos |
| Capacidades JLCPCB (geometría, `checks/jlcpcb-capacidades.md`) | **0 fallos.** 3 avisos menores |
| BOM/CPL (`checks/bom-cpl.md`) | **0 fallos.** U4, J6, J7 y TP1–TP12 no salen; las 101 piezas montadas tienen LCSC y MPN |
| Pin 1 y polaridad (`checks/pin1-polaridad.md`) | Tabla y lámina para revisar los 15 componentes en la vista 3D de JLC |

**Conclusión:** desde el punto de vista de JLCPCB la placa se puede fabricar tal como está. No hay nada que obligue a tocar `hardware/`. Lo único que queda pendiente es revisar a mano en el visor de JLC el pin 1 de U1, U2, U6, U8, D3 e Y1 (son los componentes en los que un giro rompe algo) y confirmar las cifras de capacidades que se tomaron como supuesto (ver §Supuestos).

## Ficheros

| Ruta | Contenido |
|---|---|
| `ocx-gerber-jlcpcb.zip` | **Zip para subir a JLC**: los 11 Gerber, el `.gbrjob` y los 2 `.drl` |
| `gerbers/` | F/In1/In2/B.Cu, máscara, serigrafía, pasta, Edge.Cuts, `.gbrjob` (extensiones Protel, serigrafía recortada por la máscara) |
| `drill/` | Excellon en mm con PTH y NPTH separados, más los mapas de taladro en Gerber X2 |
| `assembly/ocx-bom-jlcpcb.csv` | **BOM para JLC**, agrupada por LCSC (45 líneas, 101 piezas) |
| `assembly/ocx-cpl-jlcpcb.csv` | **CPL para JLC** (Designator, Mid X, Mid Y, Layer, Rotation) |
| `assembly/ocx-pos.csv` | Posiciones tal como las exporta `kicad-cli` (sin DNP) |
| `assembly/bom-full.csv` | BOM completa sin agrupar, con DNP, LCSC y MPN (es la entrada de las comprobaciones) |
| `checks/drc.{json,rpt}`, `checks/erc.{json,rpt}` | DRC y ERC de `kicad-cli` (todas las severidades, exclusiones incluidas) |
| `checks/drc-jlcpcb.{json,rpt}` | DRC añadiendo las reglas JLC |
| `checks/jlcpcb-capacidades.{md,json}` | Comprobación geométrica contra las capacidades de JLC |
| `checks/bom-cpl.md` | Comprobación de la BOM y del CPL |
| `checks/pin1-polaridad.{md,png}` | Tabla de pin 1 y polaridad, con su lámina |
| `renders/01…11-*.png` | Render de cada capa: las de la cara inferior en espejo, todas con el contorno |
| `renders/3d-top.png`, `3d-bottom.png` | Render 3D, sin modelos de componentes (ver supuestos) |
| `scripts/` | `run_all.sh` regenera todo lo anterior; `dump_board.py` (pcbnew), `check_jlcpcb.py`, `check_bom.py`, `pin1_table.py` y `jlcpcb.kicad_dru` |

## 1. Capacidades JLCPCB (4 capas, 1,6 mm, ENIG)

Medido sobre la geometría real: pistas, pads, vías y **zonas rellenadas por pcbnew**. Tabla completa en `checks/jlcpcb-capacidades.md`.

| Comprobación | Diseño | Límite JLC (supuesto) | Estado |
|---|---|---|---|
| Capas / grosor | 4 / 1,6 mm | 4 / 1,6 | OK |
| Pista mínima (F.Cu, B.Cu; In1/In2 son solo planos) | 0,20 mm | 0,09 (rec. 0,127) | OK |
| Holgura cobre-cobre mínima, en las 4 capas | 0,20 mm | 0,09 (rec. 0,127) | OK |
| Vías (181, todas pasantes) | 0,30 / 0,60 mm, anillo 0,15 | taladro ≥ 0,15 (≥ 0,30 sin sobrecoste), Ø ≥ 0,25, anillo ≥ 0,075 | OK, sin sobrecoste |
| Taladro PTH mínimo | 0,33 mm (vías térmicas del EP de U1) | 0,20 | OK |
| Anillo PTH mínimo | 0,15 mm (vías térmicas de U1); 0,20 mm en la carcasa de J10 | ≥ 0,13 (rec. 0,25) | AVISO: dentro del límite, por debajo del valor recomendado |
| NPTH mínimo / taladro máximo | 0,65 mm (pivotes de J10) / 3,2 mm (agujeros de montaje) | ≥ 0,50 / ≤ 6,3 | OK |
| Ranuras metalizadas (carcasa de J10) | 0,60 mm | ≥ 0,50 | OK |
| Taladro-taladro, mismo net / nets distintos | 0,86 / 0,50 mm | 0,20 / 0,25 | OK |
| Taladro a cobre de otro net | 0,25 mm (NPTH de J10 al plano GND) | 0,20 | OK |
| Presa de máscara mínima, F / B | 0,20 / 0,61 mm | 0,10 (verde) | OK |
| Cobre al borde | 0,50 mm en los planos internos; 0,99 mm en las capas externas | 0,30 | OK |
| Contorno | 1 polígono cerrado y válido de 228,0 × 115,4 mm, esquinas r = 3 mm | — | OK |
| Muesca de la antena | 40,0 × 7,8 mm. Esquinas interiores vivas en (136; 22,3) y (176; 22,3) | anchura ≥ 1,0; radio interior ≥ 0,5 | OK. AVISO: la fresa redondeará las esquinas a r ≈ 0,5–1 mm. No afecta a nada, porque el pad 1 de J2 queda a 0,99 mm y los planos a 0,5 mm |
| Serigrafía | texto ≥ 1,0 mm, trazo ≥ 0,15 mm | 1,0 / 0,15 | OK. AVISO: «Jose Ramirez Giron» usa una fuente TrueType fina (está excluido en el DRC) y puede salir débil |

Otras observaciones:
- **Muesca de la antena:** los planos In1 (GND) e In2 (+3,3 V) llegan a 0,5 mm del borde de la muesca. Es lo esperado, porque la antena del devkit ESP32-S3 queda en el aire sobre la muesca. No hay ninguna zona de exclusión, y no hace falta.
- **Expansión de máscara global = 0:** la apertura es igual al pad y JLC aplica su propia compensación. Es aceptable, pero el valor que JLC suele recomendar es 0,05 mm.
- **Stackup:** el fichero define un preimpregnado de 0,1 mm y un núcleo de 1,24 mm, que es parecido al JLC04161H-3313. Si se quiere controlar la impedancia, hay que elegir ese stackup en el pedido. Para USB Full-Speed no es crítico.
- **Coordenadas:** no hay origen de taladro definido, así que Gerber, Excellon y CPL usan el origen de página y las Y salen negativas. Los tres ficheros son coherentes entre sí, que es lo que necesita JLC.

## 2. BOM y CPL

Detalle en `checks/bom-cpl.md`.
- U4 (PAM8302), J6, J7 y TP1–TP12 tienen DNP en el esquemático y en el PCB, y **no aparecen ni en la BOM ni en el CPL**. ✔
- Las **101 piezas montadas tienen LCSC** con formato `C…` y MPN. LCSC, huella y DNP coinciden entre esquemático y PCB. ✔
- La BOM y el CPL tienen las mismas referencias. Todo va en la cara superior.
- Hay montaje **THT** (con sobrecoste en JLC) en J2, J3, J5 y SW1–SW16. Los 6 agujeros de montaje (REF\*\*) no son piezas.
- Los pulsadores tienen un valor distinto en cada uno (BTN_X, BTN_O…). En la BOM de JLC se han agrupado por LCSC (C52750873, 16 unidades) y el comentario es el MPN.

## 3. Pin 1 y polaridad

Tabla completa con nets en `checks/pin1-polaridad.md` y lámina en `checks/pin1-polaridad.png`. El pad de referencia sale en rojo; la vista es la superior, con «arriba» hacia la muesca.

| Ref | Pieza | Rot. CPL | Pad de referencia respecto al centro | Qué comprobar | Si está girado |
|---|---|---|---|---|---|
| U1 | BT817Q VQFN-64 | 180 | pin 1 abajo-derecha | punto de pin 1 | placa inservible |
| U2 | USBLC6-2SC6 | 270 | pin 1 arriba-derecha | punto de pin 1 (2 = GND, 5 = VBUS) | **180°: GND↔+5V** |
| U5 | MCP23017 SOIC-28 | 270 | pin 1 arriba-derecha | muesca o punto | — |
| U6 | LMR51430 SOT-23-6 | 90 | pin 1 abajo-izquierda (GND) | punto de pin 1 | **180°: VIN↔CB, GND↔FB** |
| U7 | W25Q128 SOIC-8 208 mil | 0 | pin 1 arriba-izquierda | bisel o punto | — |
| U8 | DIO5661 SOT-23-6 | 180 | pin 1 abajo-derecha (LX) | punto de pin 1 | **180°: +5V en LX** |
| D1 | P6SMB6.8CA | 90 | — | bidireccional, **sin polaridad** | — |
| D2 | LED verde 0805 | 0 | cátodo (pad 1) a la izquierda | marca de cátodo | LED apagado |
| D3 | SS210 SMA | 180 | cátodo (pad 1) a la derecha | banda | **conduce al revés** |
| Y1 | 12 MHz 5032 | 90 | pin 1 abajo-derecha | bisel o punto | 180°: inocuo; 90°: el cristal queda a GND |
| J1 | XF2M-4015-1A (40 p) | 0 | pin 1 arriba-izquierda | boca y pin 1 frente al cable del LCD | — |
| J4 | 84953-6 (6 p) | 0 | pin 1 arriba-izquierda | boca y pin 1 frente al cable del CTP | — |
| J10 | USB-C HRO TYPE-C-31-M-12 | 0 | A1 arriba-izquierda | boca hacia el borde inferior; patillas en sus ranuras | — |
| L2 | FNR4030S 22 µH | 0 | pad 1 a la izquierda | punto de devanado (sin polaridad eléctrica) | — |
| L3 | XAL4020 2,2 µH | 270 | pad 1 arriba | punto de devanado (sin polaridad eléctrica) | — |

JLC aplica su propia rotación de librería. Si en su visor el punto del modelo 3D no cae sobre el pad indicado, hay que corregirlo en la web de JLC o en el CPL, en múltiplos de 90°. **No hay que cambiar la huella en KiCad.**

## 4. DRC y ERC

- **DRC** (`checks/drc.rpt`): 3 violaciones y 2 «unconnected», **todas ya excluidas en el proyecto**:
  - 2 × `silk_edge_clearance`: la serigrafía de J10 queda cortada por el borde inferior, porque el conector va enrasado. Es inocuo, JLC recorta la serigrafía.
  - 1 × `text_thickness`: el texto TrueType «Jose Ramirez Giron».
  - 2 × `unconnected_items` en USB_C_D+ / USB_C_D− junto a U2. **No falta ninguna conexión:** es el enrutado *flow-through* del USBLC6-2SC6, en el que los pines 1↔6 y 3↔4 están unidos dentro del chip. La exclusión está justificada.
  - Paridad esquemático↔PCB: 0.
- **ERC** (`checks/erc.rpt`): 4 × `footprint_filter` (J1, J4, J6 y J7 usan huellas FPC que no encajan en el filtro del símbolo genérico Conn_01xNN), todos excluidos. Hay 0 errores de conexión.
- La primera pasada, sin las librerías globales configuradas, daba más de 300 avisos `lib_*_issues`. Era un problema de configuración del contenedor y no del diseño: con las tablas de librerías de KiCad 10 desaparecen. Los informes adjuntos son los de la segunda pasada.

## Supuestos y limitaciones

1. **Documentos del proyecto claude.ai «TFG: OCX»** (`revision-final-esquematico.md`, `bom-lcsc.md`, `revision-01-11-teel.md`): no estaban accesibles desde esta sesión, que es un entorno de Claude Code y no ve el conocimiento del proyecto de claude.ai. La revisión se basa solo en el repositorio. Conviene cruzar a mano `assembly/bom-full.csv` con `bom-lcsc.md`.
2. **Capacidades JLCPCB:** jlcpcb.com estaba bloqueado por la red del entorno. Las cifras son las de la tabla pública de JLC para multicapa según el conocimiento disponible, y están en `CAPS` dentro de `scripts/check_jlcpcb.py` y en `scripts/jlcpcb.kicad_dru`. El diseño las cumple con margen amplio: pistas y holguras de 0,2 frente a 0,09, y vías de 0,3/0,6. Un cambio razonable de esas cifras no cambiaría el veredicto, salvo quizá en el anillo PTH recomendado.
3. **KiCad 10:** el PPA de Launchpad estaba bloqueado. Se usó la imagen Docker oficial `kicad/kicad:10.0` (KiCad 10.0.8) con un *wrapper* `kicad-cli`. Todas las salidas se generaron sobre una **copia** de `hardware/`, porque KiCad escribe un `.kicad_prl` y el DRC de JLC necesita un `.kicad_dru`. `git status` confirma que `hardware/` no ha cambiado.
4. **Render 3D sin componentes:** la imagen Docker no trae los modelos 3D de la librería. Los renders muestran la placa desnuda. La revisión 3D de los componentes se hace en el visor de JLC con la tabla de pin 1.
5. Las ranuras metalizadas de J10 se modelan con su anchura menor en la medida taladro-taladro, que es la opción conservadora para el anillo y optimista para la distancia. El DRC de KiCad, que sí usa la forma real, tampoco da violaciones.
6. La carpeta de destino no venía indicada (`docs/<carpeta indicada>/`), así que se eligió `docs/fabricacion-jlcpcb/`.

## Cómo regenerar

```bash
WORK=$PWD/.fab-work KICAD_PY="docker run --rm -v $PWD:$PWD -w $PWD kicad/kicad:10.0 python3" docs/fabricacion-jlcpcb/scripts/run_all.sh
```

`WORK` tiene que estar dentro de un directorio montado en el contenedor, porque `dump_board.py` lee la copia de la placa desde ahí. Si `pcbnew` está instalado en local, basta con `KICAD_PY=python3`.
