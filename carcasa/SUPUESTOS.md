# Tabla de supuestos

Todo lo que no sale del `.kicad_pcb` es un supuesto: un valor de hoja de datos, una medida típica o una decisión de diseño.
Cada fila dice de dónde sale el valor, cómo comprobarlo con tus piezas y qué parámetro de [`scad/parametros.scad`](scad/parametros.scad) lo controla.

Leyenda de la columna «Origen»:
- **PCB**: leído del `.kicad_pcb` con `scripts/extraer_pcb.py`. Es un dato, no un supuesto.
- **Enunciado**: dato que diste en la petición.
- **Fabricante**: hoja de datos o ficha del fabricante.
- **Típico**: valor habitual de ese tipo de pieza, sin hoja de datos concreta.
- **Diseño**: decisión mía para que todo encaje. Ajústala si quieres otra cosa.

## Placa y componentes

| # | Supuesto | Valor usado | Origen | Cómo comprobarlo | Parámetro |
|---|---|---|---|---|---|
| 1 | Contorno de la placa | 228 × 115,4 mm, esquinas r = 3, muesca x 136–176 / y 14,5–22,3 | PCB (coincide con el enunciado) | — | `pcb_data.scad` (no editar) |
| 2 | Grosor de la placa | 1,6 mm | PCB | Calibre | `pcb_data.scad` |
| 3 | Agujeros M3 | (65;24), (195;24), (26;92), (230;92), (76;122), (173;122), Ø 3,2 | PCB (coincide con el enunciado) | — | `pcb_data.scad` |
| 4 | Componentes solo en la cara de arriba; debajo solo soldaduras THT | Patillas que asoman ≤ 2 mm; hueco bajo la placa de 2,5 mm | Enunciado + 0,5 mm de margen. El script comprueba que no haya huellas en B.Cu | Corta las patillas largas a ras de 2 mm | `hueco_inferior` |
| 5 | Altura de cada componente | Tabla `ALTURAS` de `extraer_pcb.py` (p. ej. 0805: 1,3; SOIC-28: 2,65; SWPA4030: 3,0; USB-C: 3,3; C40: 6,0) + 0,5 mm de margen | Típico / hoja de datos | Calibre de profundidades | `ALTURAS` en `scripts/extraer_pcb.py`, `margen_componentes` |
| 6 | Huella de cada componente | Caja del courtyard de KiCad (ya incluye 0,25–0,5 mm de margen) | PCB | — | — |
| 7 | Conector del altavoz J5 con clavija y cables | Zona libre hasta 12 mm de alto sobre el cabezal JST PH | Típico (6 mm de cabezal + clavija + curva de los cables) | Mide la clavija montada | `zona_componente()` en `componentes.scad` |
| 8 | Pulsadores MLD-TS-6X6X5-J | Cuerpo 6 × 6 × 3,5 mm, vástago Ø 3,5 hasta 5,0 mm, recorrido 0,25 mm | Fabricante (serie TS-6×6) | Calibre sobre la placa soldada | `sw_alto`, `sw_alto_cuerpo`, `sw_vastago_d`, `sw_recorrido` |
| 9 | Centro de cada pulsador | Centro de sus 4 pads (no la posición de la huella, que es el pin 1) | PCB | — | — |
| 10 | Receptáculo USB-C J10 (HRO TYPE-C-31-M-12) | Montaje superficial, 3,26 mm de alto, centro a 1,63 mm, boca en y = 129,9 | Fabricante + PCB (caja F.Fab) | Calibre | `usb_z` |
| 11 | Funda de la clavija USB-C | 12,5 × 7 mm con esquinas r = 1,5; hueco 13,1 × 7,6 mm | Enunciado + `holgura` | Mide tu cable | `usb_funda`, `usb_funda_radio` |
| 12 | LED D2 (0805) | 1,3 mm de alto; tubo de luz Ø 2 mm para un trozo de filamento transparente de 1,75 mm | Típico | — | `led_tipo`, `led_agujero_d` |

## ESP32-S3-DevKitC-1 y antena

| # | Supuesto | Valor usado | Origen | Cómo comprobarlo | Parámetro |
|---|---|---|---|---|---|
| 13 | Tamaño del DevKit | 62,74 × 25,4 mm | Fabricante (dimensiones publicadas por distribuidores) | Calibre | `devkit_largo`, `devkit_ancho` |
| 14 | Altura total del DevKit sobre la placa | 8,5 (zócalo) + 2,5 (plástico de los pines) + 1,6 (su placa) + 3,3 (módulo) = 15,9 mm | Enunciado | Calibre desde la placa a lo alto del módulo | `zocalo_alto`, `pin_plastico`, `devkit_pcb_e`, `devkit_modulo_alto` |
| 15 | Distancia del extremo de la antena al pin 1 | 7,9 mm (la antena queda en y 16,2–22,6, sobre la muesca) | Diseño (cuadra con «la antena queda encima de la muesca») | Mide en tu DevKit | `devkit_pin1_desde_punta` |
| 16 | Antena del ESP32-S3-WROOM-1 | Primeros 6,4 mm de un módulo de 18 × 25,5 mm | Fabricante (dibujo del módulo) | — | `devkit_modulo`, `devkit_antena_largo` |
| 17 | Zona sin plástico grueso ni tornillos | Toda la muesca (x 136–176) y la antena + 3 mm, del suelo interior a la cara interior de la piel. Por encima solo pasa la piel frontal de 2 mm de PLA; no hay tornillos a menos de 19 mm | Diseño (enunciado) | `COMPROBACIONES.md`, zona «ANTENA» | `antena_margen` |

## Pantalla NHD-5.0-800480AF-ASXP-CTP

| # | Supuesto | Valor usado | Origen | Cómo comprobarlo | Parámetro |
|---|---|---|---|---|---|
| 18 | Contorno | 120,7 × 75,8 mm | Enunciado (coincide con Newhaven) | Calibre | `pantalla_ancho`, `pantalla_alto` |
| 19 | Grosor (LCD + táctil) | **4,55 mm.** Newhaven lo da en la ficha del producto (120,7 × 75,8 × 4,55). No pude abrir el PDF de la hoja de datos desde aquí. Con espuma de 0,5 mm, la bolsa admite también una pantalla de hasta ~5,0 mm | Fabricante (ficha web) | Calibre en el canto, sin el FPC | `pantalla_grosor` |
| 20 | Zona visible y zona activa | Visible 109 × 65,8 mm (la ventana); activa 108 × 64,8 mm (800 × 480 píxeles a 0,135 mm). Las dos se suponen centradas en el contorno | Fabricante (ficha) / supuesto de centrado | Mide el marco negro de la pantalla por los cuatro lados | `ventana`, `ventana_desplaz` |
| 21 | Posición horizontal | Centrada en x = 132,69 | Enunciado | — | `pantalla_cx` |
| 22 | Posición vertical (calculada) | Borde inferior en y = 112,0, centro en y = 74,1. Así el pliegue del FPC queda al sur de las bocas de J1 (y 106,4) y J4 (y 107,7), el marco superior deja sitio al agujero de RESET (y 31,5) y el inferior no toca las guías de SW6–SW9 (y > 117) | Diseño | — | `pantalla_borde_inf` |
| 23 | Altura de la pantalla | Trasera a 17,4 mm sobre la placa (1,5 mm por encima del DevKit); la cara de vidrio toca la piel por detrás | Diseño | — | `holgura_pantalla_devkit` |
| 24 | FPC de 40 pines | Sale por el borde inferior alineado con J1 (x = 108,74), ~24 mm de ancho, y es lo bastante largo para doblarse 180° y bajar ~17 mm hasta J1 (unos 35–40 mm desde el vidrio) | Supuesto (la placa se diseñó para esta pantalla) | Mide el largo del FPC. Si se queda corto, sube `pantalla_borde_inf` | `fpc_tft_ancho`, `fpc_pliegue` |
| 25 | FPC del táctil (6 pines) | Sale por el borde inferior alineado con J4 (x = 134), ~10 mm de ancho | Supuesto | Igual que el anterior | `fpc_ctp_ancho` |

## Joysticks, altavoz y botones

| # | Supuesto | Valor usado | Origen | Cómo comprobarlo | Parámetro |
|---|---|---|---|---|---|
| 26 | Base del módulo tipo Joy-Con | 19 × 18 mm, 1,6 mm de orejas | Enunciado | Calibre | `joy_base`, `joy_base_e` |
| 27 | Cúpula y altura | Cúpula Ø 14 × 8 mm sobre la base; capuchón a 15,5 mm de la base | Típico (sin dibujo oficial) | Calibre | `joy_cuerpo_d`, `joy_cuerpo_alto`, `joy_total_alto` |
| 28 | Capuchón del stick | Ø 15 mm, 3 mm de canto | Medidas de la comunidad (14,9–15,0 mm, dekuNukem/Nintendo_Switch_Reverse_Engineering#84) | Calibre | `joy_cap_d`, `joy_cap_alto` |
| 29 | Tornillos del módulo | 2 agujeros Ø 1,6 en esquinas opuestas, en (−7,75; −7,25) y (7,75; 7,25) desde el eje | Típico (agujero de 1,6 mm medido por la comunidad; posición supuesta) | Mide la distancia entre agujeros y al eje | `joy_agujeros`, `joy_tornillo_d`, `joy_piloto_d` |
| 30 | Inclinación máxima del stick | 20°; hueco frontal de Ø 21 mm | Típico | Inclina el stick con un transportador | `joy_inclinacion`, `joy_agujero_d` |
| 31 | Posición de los joysticks | Eje en (40,5; 84) y (216,5; 83), con el módulo encima de J6 y J7 y desplazado para no chocar con las torretas (26;92) y (230;92). El stick sobresale 5 mm | Diseño | — | `joy_izq`, `joy_der`, `joy_sobresale` |
| 32 | FPC del joystick | Sale del módulo, baja ~13 mm y entra en J6/J7 por el sur con los contactos hacia arriba. Hace falta un FPC de unos 30 mm | Supuesto | Mide el tuyo; si no llega, mueve o gira el módulo | `joy_izq`, `joy_der`, `joy_giro_izq`, `joy_giro_der` |
| 33 | Altavoz | Ø 20 × 4,5 mm, de frente a la rejilla, en (45; 116), a 21 mm de J5 | Enunciado (diámetro) / Diseño (posición, grosor) | Calibre | `altavoz_d`, `altavoz_alto`, `altavoz_pos` |
| 34 | Gatillos SW1/SW15 | Son pulsadores verticales en la cara de arriba, a 15,5 mm del borde. Llevan capuchón frontal (no hay palanca de hombro) | PCB | — | `BOTONES`, `CAP_TIPOS` |
| 35 | RESET (SW14) | Queda fuera de la pantalla: agujero de Ø 2,2 mm con tubo guía hasta 1 mm del vástago, para un clip | PCB + Diseño | — | `clip_d`, `reset_tubo_hasta` |
| 36 | BOOT (SW16) | Queda **debajo de la pantalla**, así que un agujero recto no llega. Lleva un empujador en L: se pulsa con un clip por un agujero del bisel superior (x 174,6; y 30,5) y un brazo de 27 mm por debajo de la pantalla pisa el vástago | Diseño | Pulsa con un clip | `boot_varilla_y`, `boot_brazo_z` |

## Impresión, uniones y tornillería

| # | Supuesto | Valor usado | Origen | Cómo comprobarlo | Parámetro |
|---|---|---|---|---|---|
| 37 | Volumen útil de la Finder | 140 × 140 × 140 mm; piezas ≤ 135 mm (la mayor mide 133,4 mm) | Enunciado | — | `limite_pieza` (en `carcasa.scad`) |
| 38 | Holguras | 0,3 mm por lado en guías de botones, colas de milano, labio frontal/trasero, USB y joystick; 0,15 mm por cara en las uniones planas (0,3 mm entre piezas) | Enunciado | Probeta `00_probeta_ajustes.stl` | `holgura`, `holgura_union` |
| 39 | Juego vertical de los capuchones | 0,4 mm entre la brida y el tubo. Absorbe la tolerancia de altura de pulsadores, torretas y primera capa sin dejar ningún botón pulsado | Diseño | Si un botón queda pulsado, lija 0,2 mm el pie del capuchón | `cap_juego` |
| 40 | Paredes | Laterales 3 mm, cara frontal 2 mm, tapa trasera 2 mm, tubos y marco 2 mm. Excepciones: cada labio del solape frontal/trasero (1,35 mm, la mitad de la pared) y los dedos elásticos del aro del altavoz (1,6 mm, tienen que doblarse) | Enunciado / Diseño | — | `pared`, `piel`, `suelo`, `pared_interna` |
| 41 | División en piezas | Frontal en 3 piezas para que las uniones queden fuera de la pantalla: con 120,7 mm de pantalla más su marco no caben dos mitades de ≤ 135 mm sin cortar el marco. Uniones en x = 66,5 (x = 69,8 en el bisel superior, para no partir la torreta 65;24) y x = 200,25. Trasera en 2 piezas unidas en x = 115, una franja sin patillas THT | Diseño | — | `union_A_x`, `union_A_sup_x`, `union_A_escalon_y`, `union_B_x`, `union_T_x` |
| 42 | Uniones de la trasera | Bajo la placa solo hay 2,5 mm, así que no caben tornillos horizontales. Llevan 3 colas de milano en una franja engrosada del suelo. Cada mitad se atornilla a la placa con 3 tornillos M3 que roscan en la frontal. La trasera izquierda une así la frontal izquierda con la central, y la derecha une la central con la derecha (juntas a tresbolillo) | Diseño | — | `colas_T_y` |
| 43 | Tornillos | DIN 912 (Allen), cabeza Ø 5,5 × 3 mm; M3 × 10 para la placa y las uniones, M3 × 6 para los pisapantallas | Típico | — | `tornillo_largo`, `tornillo_pisa_largo`, `m3_*` |
| 44 | Insertos térmicos | M3 × 5,7 mm, Ø exterior 4,6 mm, agujero de 4,0 mm. Alternativa sin soldador: `fijacion_pcb = "autorroscante"` (piloto de 2,6 mm) | Típico (ruthex y similares) | Prueba en la probeta | `fijacion_pcb`, `inserto_d`, `inserto_l` |
| 45 | Material y estimaciones | PLA, 1,24 g/cm³. Tiempo y gramos de PrusaSlicer 2.7 con un perfil aproximado de la Finder (`perfil/finder_pla_0.2.ini`): 0,2 mm, 3 perímetros, 20 % de relleno, 30–60 mm/s. FlashPrint puede dar ±20 % | Diseño | Lamina en FlashPrint | — |
| 46 | Grosor total | 30,05 mm (cara frontal a 23,95 mm sobre la placa, tapa trasera a −6,1 mm). Sale de apilar el DevKit (15,9), 1,5 mm de aire, la pantalla (4,55) y la piel (2) | Consecuencia de 14, 19 y 23 | — | — |
