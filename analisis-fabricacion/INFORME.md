# Análisis de fabricación: OCX (JLCPCB, 4 capas)

> **Solo análisis.** Nada de esta carpeta está pensado para subirse a JLC. Las
> herramientas regeneran Gerber, taladros, BOM y CPL en `salida/`, que está en
> `.gitignore`, solo para comprobarlos. `hardware/` no se ha tocado.

- **Commit analizado:** `origin/main` = `b7c4baae2adced6d72cf64719c117a9d4fc91adb` («Fab v1.1: Fix joystick pinout, add VBUS cap and joysticks buttons pull-ups»).
- **Herramienta:** `kicad-cli` 10.0.8, imagen Docker `kicad/kicad:10.0`.
- **Pedido previsto:** 4 capas, 1,6 mm, JLC04161H-2116, ENIG, montaje SMT y THT por la cara superior.

## Resumen

No he encontrado ningún error de diseño. DRC y ERC salen limpios salvo exactamente las exclusiones que esperabas. BOM y CPL excluyen las 15 DNP, las 104 piezas montadas llevan LCSC y MPN, y la polaridad (redes de pin 1) es correcta en todas las piezas revisadas.

Lo que hay que vigilar está en el **CPL**, no en la placa:

1. **El CPL de `kicad-cli` no sirve tal cual para las 20 huellas con `FT Origin=Center`.** Usa el ancla, que en estas huellas THT es el pin 1. J2/J3 quedarían desplazados 26,67 mm y los pulsadores 3,95 mm. El de Fabrication Toolkit (FT) sí respeta el campo.
2. **J10 (USB‑C) es la excepción.** Su ancla *ya es* el centro del cuerpo. Con `Center`, FT mueve la coordenada 1,46 mm hacia el interior de la placa, al centro de los pads. Hay que comprobar en el visor cuál de las dos cuadra con el modelo de JLC.
3. **Las rotaciones son las de KiCad.** Siguiendo la tabla de FT, U2, U5, U6, U7, U8 y C40 casi seguro necesitan corrección. U1 (VQFN) no aparece en esa tabla. Hay que mirarlas una a una en el visor; la tabla de (b) dice dónde debe quedar el pin 1 de cada una.
4. **Si usas FT, activa «Exclude DNP components from BOM».** Viene desactivado por defecto, y entonces U4, J6 y J7 salen en la BOM con su MPN en la columna «LCSC Part #».

## Tabla de resultados

| # | Comprobación | Resultado | Detalle |
|---|---|---|---|
| 1 | Generación Gerber/taladros/BOM/CPL | OK | Sin errores. Las 4 capas de cobre, máscaras, pastas, serigrafías, Edge.Cuts y el job file. PTH y NPTH van en Excellon separados (mm, decimal) y las 4 ranuras de J10 como G85. |
| 2 | Rellenos de zona guardados en el commit | OK | El cobre con y sin `--check-zones` difiere como mucho 1 nm (redondeo). Los rellenos están al día. |
| 3 | Contorno | OK | Edge.Cuts cerrado (el DRC no da error de contorno), 228,0 × 115,4 mm, con la entalladura de la antena. |
| 4 | DRC, reglas del proyecto | OK | 0 violaciones sin excluir. Excluidas: 2 `unconnected_items` en U2 (pines 1‑6 y 3‑4), 2 `silk_edge_clearance` de J10 y 1 `text_thickness` (TrueType «Jose Ramirez Giron»). Paridad esquemático‑PCB: 0. |
| 5 | DRC, reglas de JLC (`herramientas/jlcpcb-4capas.kicad_dru`) | OK | 0 violaciones nuevas. Valores reales: pista mín. 0,20 mm, separación ≥ 0,15 mm, vías 0,3/0,6 mm (anillo 0,15, sin sobrecoste), anillo PTH mín. 0,15 mm (vías térmicas de U1, 0,33/0,63), ranuras PTH de 0,6 mm, NPTH ≥ 0,65 mm, cobre‑borde 0,5 mm. ⚠ Los valores de JLC del fichero de reglas son de memoria (ver Limitaciones). |
| 6 | ERC | OK | 0 violaciones sin excluir. Excluidas: los 4 `footprint_filter` de los FPC (J1, J4, J6, J7). |
| 7 | Serigrafía | OK | Texto mínimo 1,0 mm / 0,15 mm. El texto TrueType de 1,5 mm está excluido del DRC; solo comprobar en el visor que se lee. |
| 8 | (a) Lista de `FT Origin=Center` | OK | Exactamente J2, J3, J5, J10, SW1–SW16. Ninguna huella más usaría «Center» en FT. Los SMD sin el campo tienen el ancla en el centro de pads (< 0,05 mm). |
| 9 | (a) CPL de `kicad-cli` en esas 20 huellas | **FALLO** (si se sube ese CPL) | Pone el ancla: J2/J3 desplazados 26,67 mm, SW 3,95 mm, J5 1,0 mm, J10 1,46 mm respecto al centro de pads. Con el CPL de FT, OK (salvo J10, fila 10). |
| 10 | (a) J10: ¿centro de pads o ancla? | AVISO | El ancla coincide con el centro del cuerpo (F.Fab). FT pondrá el centro de pads, 1,46 mm desplazado. Decidir en el visor. |
| 11 | (a) J5: centro de pads ≠ cuerpo | AVISO | El cuerpo del JST PH está 0,4 mm descentrado respecto a los pines. Comprobar en el visor. |
| 12 | (b) Redes de pin 1 / polaridad | OK | U2 (1/6 = D+, 2 = GND, 3/4 = D−, 5 = VBUS), U5, U6, U7, D3 (cátodo a VLED+), D2 (cátodo a R9, ánodo a +3,3 V), Y1 (1/3 cristal, 2/4 GND), C40 (pad 1 = +5 V) y D1 cuadran con el pinout de cada pieza. U8: el pinout del DIO5661 no lo he podido comprobar con su hoja de datos. |
| 13 | (b) Rotaciones para JLC | AVISO | Ver la tabla de (b). En U2 y U6, un error de 180° cambia GND por VBUS/VIN. En Y1, un error de 90° pone el cristal a GND. |
| 14 | (b) J2/J3 (DevKit) | OK | J3 está girado 180°, pero de arriba abajo da GND, TX, RX…, GND, GND, como el J3 del ESP32‑S3‑DevKitC‑1. J2 da 3V3, 3V3, RST…, 5V (sin conectar), GND. Coherente. |
| 15 | (c) DNP fuera de BOM y CPL (`kicad-cli`) | OK | U4, J6, J7 y TP1–TP12 están marcados DNP en esquemático y PCB. No salen en `bom-sin-dnp.csv` ni en el CPL con `--exclude-dnp`. |
| 16 | (c) LCSC y MPN de las piezas montadas | OK | 104 piezas en 61 filas, todas con LCSC (formato C+número) y MPN. Esquemático y PCB coinciden. Ningún LCSC con dos MPN ni al revés. BOM y CPL tienen las mismas referencias. |
| 17 | (c) DNP en la BOM de Fabrication Toolkit | AVISO | Por defecto FT mete las DNP en la BOM. U4 iría como «PAM8302AADCR» y J6/J7 como «SFV5R-4STE1HLF» en «LCSC Part #». Activa «Exclude DNP». |
| 18 | (c) Formato del CPL de `kicad-cli` | AVISO | Cabeceras `Ref,Val,Package,PosX,PosY,Rot,Side` (JLC espera `Designator,Mid X,Mid Y,Layer,Rotation`) y rotaciones negativas (−90). Hay que mapear columnas al subirlo. FT ya usa el formato de JLC. |
| 19 | Stackup en KiCad frente a JLC04161H-2116 | AVISO | En KiCad es genérico: prepreg 0,10, núcleo 1,24, cobre interior 35 µm, acabado «None». No afecta a la fabricación (JLC usa el apilado que elijas en el pedido); solo afecta a cálculos de impedancia hechos en KiCad. |
| 20 | Plot params guardados en la placa | AVISO (menor) | Sin extensiones Protel, con X2 y sin restar máscara a la serigrafía. Solo importa si exportas desde la GUI con esos ajustes: JLC los acepta, pero recomienda Protel y restar máscara. FT fija sus propios ajustes. |
| 21 | Versión | AVISO (informativo) | La serigrafía dice «OCX v1.0» y el commit es «Fab v1.1». Confirma que pides este commit. |

## (a) `FT Origin = Center`: coordenada que debería ir en el CPL

**Por qué difieren.** `kicad-cli pcb export pos` escribe la *posición de la huella*, es decir, su ancla (origen de la librería), y no lee campos de usuario. En las huellas THT de la librería de KiCad, el ancla es el pin 1. Fabrication Toolkit (`_get_footprint_position`, bennymeg/fabrication-toolkit@7f627b6) funciona así:

- Por defecto usa «Anchor» si la huella es SMD y «Center» si no lo es.
- El campo `FT Origin` (Anchor/Center) sustituye a ese defecto. Si el campo está vacío, se queda el defecto.
- «Center» es el centro de la caja envolvente de **todos** los pads, incluidos NPTH y pads mecánicos. Si la rotación no es múltiplo de 90°, la calcula con la huella a 0°.

Las dos herramientas cambian el signo de Y y, como la placa no tiene origen auxiliar, usan el mismo origen absoluto que los Gerber.

JLC coloca la pieza según el origen de *su* modelo, que normalmente es el centro del cuerpo. Por eso añado el centro de F.Fab como referencia del cuerpo.

Coordenadas en mm, tal como irían en el CPL (Y negativa):

| Ref | Rot | CPL `kicad-cli` (ancla) | **CPL esperado (FT, centro de pads)** | Δ | Centro del cuerpo (F.Fab) | Comentario |
|---|---:|---|---|---:|---|---|
| J2 | 0 | 144.600 / −24.140 | **144.600 / −50.810** | 26.67 | 144.600 / −50.810 | Pin 1 → centro del zócalo |
| J3 | 180 | 167.460 / −77.480 | **167.460 / −50.810** | 26.67 | 167.460 / −50.810 | Ídem |
| J5 | 90 | 65.639 / −111.456 | **65.639 / −110.456** | 1.00 | 65.984 / −110.661 | Cuerpo 0,4 mm descentrado |
| J10 | 0 | 208.480 / −126.250 | **208.480 / −124.790** | 1.46 | 208.480 / −126.250 | ⚠ Aquí el ancla *es* el cuerpo |
| SW1 | 180 | 40.500 / −30.000 | **37.250 / −27.750** | 3.95 | = FT | |
| SW2 | 180 | 40.500 / −42.000 | **37.250 / −39.750** | 3.95 | = FT | |
| SW3 | 180 | 50.500 / −52.000 | **47.250 / −49.750** | 3.95 | = FT | |
| SW4 | 180 | 30.500 / −52.000 | **27.250 / −49.750** | 3.95 | = FT | |
| SW5 | 180 | 40.500 / −62.000 | **37.250 / −59.750** | 3.95 | = FT | |
| SW6 | 0 | 120.850 / −120.500 | **124.100 / −122.750** | 3.95 | = FT | |
| SW7 | 0 | 130.900 / −120.500 | **134.150 / −122.750** | 3.95 | = FT | |
| SW8 | 0 | 140.600 / −120.500 | **143.850 / −122.750** | 3.95 | = FT | |
| SW9 | 0 | 150.550 / −120.500 | **153.800 / −122.750** | 3.95 | = FT | |
| SW10 | 180 | 224.900 / −62.000 | **221.650 / −59.750** | 3.95 | = FT | |
| SW11 | 180 | 234.900 / −52.000 | **231.650 / −49.750** | 3.95 | = FT | |
| SW12 | 180 | 214.900 / −52.000 | **211.650 / −49.750** | 3.95 | = FT | |
| SW13 | 180 | 224.900 / −42.000 | **221.650 / −39.750** | 3.95 | = FT | |
| SW14 | 180 | 130.550 / −33.750 | **127.300 / −31.500** | 3.95 | = FT | |
| SW15 | 180 | 224.900 / −30.000 | **221.650 / −27.750** | 3.95 | = FT | |
| SW16 | 0 | 171.350 / −54.950 | **174.600 / −57.200** | 3.95 | = FT | |

En los pulsadores (4 pines en rectángulo de 6,5 × 4,5 mm) un giro de 90° no encaja en los taladros y uno de 180° es equivalente, así que solo importa la posición. Los zócalos 1×22 no tienen polaridad.

## (b) Pin 1, polaridad y rotación probable en JLC

«Pin 1 en placa» indica dónde cae el pad 1 respecto al centro de la pieza, vista desde arriba y con la placa orientada como en KiCad: la entalladura de la antena arriba y el USB‑C abajo a la derecha. En el visor de JLC, el punto de pin 1 o la marca de polaridad del modelo tiene que caer en ese lado. Lo mismo, dibujado: `resultados/mapa-pin1-y-origen.png`.

La columna «FT auto‑translate» es la rotación que pondría FT con su tabla `transformations.csv`. Esa tabla es empírica de la comunidad y no es una garantía: el modelo concreto de cada código LCSC puede ser distinto.

| Ref | Pieza | Rot KiCad | Pad 1 → red | **Pin 1 en placa** | FT auto‑translate | Riesgo si sale girada |
|---|---|---:|---|---|---:|---|
| U1 | BT817Q, VQFN‑64 | 180 | B7 | **abajo‑derecha** | 180 (la regla `^QFN-` no casa con «VQFN-», así que no corrige) | Alto. Probablemente necesite ±90; ajustar hasta que el punto quede abajo‑derecha |
| U2 | USBLC6‑2SC6, SOT‑23‑6 | −90 | D+ | **arriba‑derecha** | 90 | Crítico: con 180° se cambian GND (2) y VBUS (5) |
| U5 | MCP23017, SOIC‑28W | −90 | GPB0 | **arriba‑derecha** | 180 | Alto |
| U6 | LMR51430, SOT‑23‑6 | 90 | GND | **abajo‑izquierda** | 270 | Crítico: con 180° el pin GND del chip cae en el pad de FB, VIN en el de CB y EN en el de SW |
| U7 | W25Q128JVS, SOIC‑8 | 0 | /CS | **arriba‑izquierda** | 270 | Alto |
| U8 | DIO5661, SOT‑23‑6 | 180 | LX | **abajo‑derecha** | 0 | Alto |
| D1 | P6SMB6.8CA, SMB | 90 | +5V | (abajo) | 90 | Ninguno: bidireccional |
| D2 | LED verde 0805 | 0 | K | cátodo a la **izquierda** | 0 | Medio: LED al revés. La marca de cátodo de los modelos de LED de JLC varía |
| D3 | SS210, SMA | 180 | VLED+ (K) | cátodo (banda) a la **derecha** | 180 | Alto: diodo del boost al revés |
| Y1 | 12 MHz, 5032‑4 pines | 90 | X1 | **abajo‑derecha** | 90 | Con 90° de error X1/X2 quedan a GND. Con 180° no pasa nada (1↔3, 2↔4) |
| C40 | 100 µF polímero (MA16V100M6X6) | 0 | +5V | «+» a la **izquierda** | 180 | Alto: condensador polarizado invertido |
| J5 | JST PH 2 pines | 90 | Pin 1 | **abajo** | 90 | Medio: altavoz invertido (sin daño) |

## (c) DNP, BOM y CPL

- **DNP** (esquemático y PCB coinciden): U4, J6, J7, TP1–TP12. Ninguna sale en `bom-sin-dnp.csv` ni en el CPL con `--exclude-dnp` (104 refs; con DNP serían 119).
- **Montadas:** 104 piezas en 61 líneas de BOM, todas con LCSC y MPN, coherentes entre esquemático y PCB. Hay 19 THT (J2, J3, J5, SW1–SW16) en BOM y CPL, como hace falta para el montaje THT.
- **Fabrication Toolkit:** las DNP no salen en el CPL, pero sí en la BOM si no activas «Exclude DNP». U4, J6 y J7 llevarían su MPN como código LCSC, porque no tienen campo LCSC y FT recurre al MPN.
- **Observación, no error:** J5 (salida de altavoz) se monta y su amplificador U4 es DNP. Supongo que U4 se soldará a mano.

## (d) DRC y ERC

Informes completos en `resultados/drc-erc/`:

- `drc-proyecto.json`: reglas del proyecto.
- `drc-jlc.json` / `.rpt`: reglas del proyecto más `jlcpcb-4capas.kicad_dru`.
- `erc.json` / `.rpt`.

Se ejecutaron con `--refill-zones --schematic-parity --severity-all --severity-exclusions`. Las exclusiones encontradas son exactamente las esperadas:

| Exclusión | Esperada | Encontrada |
|---|---|---|
| `unconnected_items` U2 (D+ 1↔6, D− 3↔4) | 2 | 2 |
| `silk_edge_clearance` J10 | 2 | 2 |
| `text_thickness` texto TrueType | 1 | 1 |
| `footprint_filter` FPC (ERC) | 4 | 4 (J1, J4, J6, J7) |

Antes hice una prueba con una regla «canario» deliberadamente imposible para confirmar que `kicad-cli` carga el fichero de reglas de JLC. El informe `drc-jlc.rpt` cita la regla «JLC serigrafía grosor de trazo».

## Qué comprobar en el visor de JLC

**Fila 9: CPL de `kicad-cli` (FALLO si se usa).** No subas ese CPL sin corregir las 20 huellas. Con cualquier CPL, en la vista de colocación:

- Los 4 pines de cada SW1–SW16 deben caer en sus 4 taladros, con el cuerpo centrado entre ellos.
- J2 y J3 deben cubrir las 22 filas de taladros cada uno, no empezar en el pin 1 y salirse 26,67 mm por arriba (J2) o por abajo (J3).
- J5 debe tener sus dos pines en los taladros.

**Fila 10: J10.** Comprueba que las 12 patas SMD (A1…B12) caen sobre la fila de pads y que los 2 tetones de plástico y las 4 pestañas del blindaje caen en sus taladros:

- Si con la coordenada de FT (−124.790) todo queda 1,46 mm hacia dentro de la placa, el modelo de JLC usa el centro del cuerpo. Entonces vale la del ancla (−126.250).
- Si queda bien con la de FT, perfecto.

Fíjate también en que el frontal del conector quede alineado con el borde de la placa.

**Fila 11: J5.** Comprueba que los dos pines caen en los taladros y que el cuerpo queda hacia el lado del pin 1 según el modelo.

**Fila 13: rotaciones.** Para cada fila de la tabla (b), el marcador de pin 1 o polaridad del modelo tiene que quedar en la posición indicada. En concreto:

- **U2, U6:** un giro de 180° no se ve como «raro», porque el SOT‑23‑6 es simétrico. Fíjate en el punto.
- **Y1:** la marca o chaflán del pin 1 debe quedar abajo‑derecha. Con 90° de error las patas siguen encajando pero el cristal queda a GND.
- **C40:** la banda negra (−) del condensador debe quedar a la **derecha**, hacia la red GND.
- **D3:** la banda de cátodo a la derecha. **D2:** la marca de cátodo a la izquierda.

**Filas 17‑18: BOM/CPL.** Tras subirlos, la lista de piezas que JLC va a montar debe tener 104 referencias y no incluir U4, J6, J7 ni TP*. Si usas el CSV de `kicad-cli`, asigna las columnas: `Ref`→Designator, `PosX`→Mid X, `PosY`→Mid Y, `Rot`→Rotation, `Side`→Layer.

**General:**

- Que todas las piezas tengan stock y cuáles son «extended». No lo he podido consultar; las más delicadas son U1 (C20613585) y los pulsadores (C52750873).
- Que la foto o el dibujo de C40 (MA16V100M6X6) sea un SMD de 6,3 mm compatible con la huella CP_Elec_6.3x5.8.
- Que el pedido diga 4 capas, 1,6 mm, JLC04161H‑2116 y ENIG.

## Limitaciones

- **Reglas de JLC.** jlcpcb.com no era accesible desde el entorno de análisis (fallo de DNS). Los mínimos de `jlcpcb-4capas.kicad_dru` son los de la tabla de capacidades multicapa que conozco: pista/separación 0,09 mm; vía 0,15/0,25 mm con sobrecoste por debajo de 0,3; anillo de vía 0,05; anillo PTH 0,13; NPTH 0,5; taladro‑taladro 0,5 entre redes distintas; taladro‑cobre 0,2; cobre‑borde 0,3; serigrafía 1,0/0,15. La placa está holgadamente por encima de todos (pista 0,20, separación ≥ 0,15, vía 0,3/0,6, anillos 0,15, borde 0,5), así que un cambio pequeño en esos valores no cambia el resultado. Aun así, confírmalos en su web.
- **Rotaciones.** Sin acceso a los modelos de JLC, la «rotación probable» se basa en la tabla de FT. La verificación definitiva es el visor.
- **Pinouts.** He comprobado que las redes de cada pin cuadran con el pinout de cada pieza. El del DIO5661 (U8) no lo he podido contrastar con su hoja de datos.

## Contenido y cómo reproducirlo

```
analisis-fabricacion/
├── INFORME.md                      este informe
├── herramientas/
│   ├── generar.sh                  git archive del commit → kicad-cli en Docker (Gerber, taladros, BOM, CPL, DRC, ERC)
│   ├── jlcpcb-4capas.kicad_dru     reglas JLC (solo se copian a una copia de trabajo)
│   ├── sexp.py                     lector de S-expressions de KiCad
│   ├── analizar.py                 (a)(b)(c), geometría, rellenos → resultados/analisis.md/.json
│   └── mapa.py                     resultados/mapa-pin1-y-origen.png
├── resultados/                     tablas, mapa e informes DRC/ERC
└── salida/                         (ignorada por git) Gerber/BOM/CPL regenerados SOLO para comprobar
```

```bash
analisis-fabricacion/herramientas/generar.sh origin/main
```

```bash
python3 -I analisis-fabricacion/herramientas/mapa.py
```

`mapa.py` ejecuta también `analizar.py`. `generar.sh` necesita Docker y la imagen `kicad/kicad:10.0`.
