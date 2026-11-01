# Comprobacion de capacidades JLCPCB (4 capas, 1,6 mm, ENIG)

Generado por `scripts/check_jlcpcb.py` a partir de la geometria de `hardware/ocxPrototype.kicad_pcb` (zonas rellenadas por pcbnew). Limites en mm; ver supuestos en el README.

| Categoria | Comprobacion | Valor | Limite JLC | Estado | Nota |
|---|---|---|---|---|---|
| Stackup | Capas de cobre | 4 | 4 | OK |  |
| Stackup | Grosor (mm) | 1.6 | 1.6 | OK | Acabado ENIG: se elige en el pedido, no esta en los Gerber. |
| Contorno | Contornos cerrados (Edge.Cuts) | 1 | 1 | OK | Un unico poligono cerrado y valido. |
| Contorno | Dimensiones (mm) | 228.00 x 115.40 | - | INFO |  |
| Muesca antena | Anchura x profundidad (mm) | 40.00 x 7.80 | >= 1.0 de ancho | OK | Esquinas interiores en (136.0, 22.3), (176.0, 22.3) |
| Muesca antena | Radio de esquinas interiores | 0 (vivas) | >= 0.5 | AVISO | La fresa dejara radio ~0,5 mm (o mayor segun fresa). Es aceptable si nada depende de una esquina viva; si se quiere controlar, dibujar r=0,5-1 mm. |
| Pistas | Anchura minima F.Cu | 0.2 | 0.09 | OK |  |
| Pistas | Anchura minima In1.Cu | sin pistas | 0.09 | OK | Capa solo con plano |
| Pistas | Anchura minima In2.Cu | sin pistas | 0.09 | OK | Capa solo con plano |
| Pistas | Anchura minima B.Cu | 0.2 | 0.09 | OK |  |
| Vias | Taladro minimo (181 vias) | 0.3 | 0.15 | OK | Sin sobrecoste por via pequena |
| Vias | Diametro minimo | 0.6 | 0.25 | OK |  |
| Vias | Anillo minimo | 0.15 | 0.075 | OK |  |
| Vias | Tipos de via | 4 | pasante | OK | Todas pasantes (sin ciegas/enterradas/microvias). |
| Vias | Tenting | F=True B=True | - | INFO | Vias cubiertas de mascara en ambas caras. |
| Taladros | PTH redondo minimo | 0.33 | 0.2 | OK | U1 pad 65 |
| Taladros | Taladro maximo | 3.2 | 6.3 | OK |  |
| Taladros | NPTH minimo | 0.65 | 0.5 | OK | J10 pad  |
| Taladros | Ranura metalizada minima (4) | 0.6 | 0.5 | OK | J10 (carcasa USB-C) |
| Taladros | Anillo PTH minimo | 0.15 | 0.13 | AVISO | U1 pad 65 (0.63/0.33 mm) - vias termicas del EP, se fabrican como vias |
| Taladros | Anillo PTH minimo (componentes) | 0.2 | 0.13 | AVISO | J10 pad SH |
| Taladros | Distancia taladro-taladro (mismo net) | 0.862 | 0.2 | OK | U1 pad 65 / U1 pad 65 |
| Taladros | Distancia taladro-taladro (nets distintos) | 0.5 | 0.25 | OK | via DISP @[114.135725, 96.645486] / via HSYNC @[114.642706, 97.264335] |
| Holguras | Cobre-cobre minima F.Cu | 0.2 | 0.09 | OK | pista /Power_Supply_USB/USB_C_D- 0.2mm / via /Power_Supply_USB/USB_C_D+ |
| Cobre al borde | Minimo F.Cu | 0.99 | 0.3 | OK | J2 pad 1 |
| Holguras | Cobre-cobre minima In1.Cu | 0.2 | 0.09 | OK | via DISP / via HSYNC |
| Cobre al borde | Minimo In1.Cu | 0.499 | 0.3 | OK | plano GND |
| Holguras | Cobre-cobre minima In2.Cu | 0.2 | 0.09 | OK | via DISP / via HSYNC |
| Cobre al borde | Minimo In2.Cu | 0.499 | 0.3 | OK | plano +3.3V |
| Holguras | Cobre-cobre minima B.Cu | 0.2 | 0.09 | OK | pista Net-(U5-GPB5) 0.2mm / pista Net-(U5-GPB4) 0.2mm |
| Cobre al borde | Minimo B.Cu | 0.99 | 0.3 | OK | J2 pad 1 |
| Holguras | Taladro a cobre de otro net | 0.25 | 0.2 | OK | In1.Cu: J10 pad  / plano GND |
| Muesca antena | Cobre a <3 mm del borde de la muesca | 10 | - | INFO | distancia minima 0.5 mm; planos implicados: In1.Cu, In2.Cu |
| Mascara | Presa minima F.Mask (489 aperturas) | 0.2 | 0.1 | OK | J6 pad 1 / J6 pad 2 |
| Mascara | Presa minima B.Mask (123 aperturas) | 0.605 | 0.1 | OK | J10 pad  / J10 pad SH |
| Mascara | Expansion global de mascara | 0.0 | 0-0.05 | INFO | 0 mm: la apertura coincide con el pad; JLC aplica su propia compensacion. |
| Serigrafia | Altura minima de texto | 1.0 | 1.0 | OK |  |
| Serigrafia | Grosor minimo de trazo (fuente KiCad) | 0.15 | 0.15 | OK | Textos TrueType: Jose Ramirez Giron |
