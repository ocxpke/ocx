// =====================================================================
//  OCX - carcasa de apoyo · PARÁMETROS
//  Todas las posiciones X/Y están en coordenadas del .kicad_pcb
//  (mm, Y hacia abajo). Z = 0 es la cara superior de la placa.
//  Cambia aquí lo que midas de tus piezas reales y vuelve a exportar.
// =====================================================================

include <pcb_data.scad>

// ---------------------------------------------------------------------
// [Impresión]
// ---------------------------------------------------------------------
holgura        = 0.3;   // juego por lado en encajes, guías de botones y colas de milano
holgura_union  = 0.15;  // separación por lado en las caras de unión entre piezas
holgura_costura = 0.2;  // separación en la costura frontal/trasera (absorbe el grosor real de la placa)
pared          = 3.0;   // paredes laterales (>= 2)
piel           = 2.0;   // cara frontal (>= 2)
suelo          = 2.0;   // tapa trasera (>= 2)
pared_interna  = 2.0;   // tubos guía, marco de la pantalla y torretas
chaflan_frontal = 1.5;  // chaflán a 45° del canto frontal (redondeo imprimible boca abajo)
chaflan_trasero = 1.0;  // chaflán del canto trasero
fn = 48;                // facetas de los cilindros grandes
fn_peq = 24;            // facetas de agujeros y tetones pequeños

// ---------------------------------------------------------------------
// [Placa y holguras]
// ---------------------------------------------------------------------
holgura_pcb    = 0.5;   // del canto de la placa a la cara interior de la pared
hueco_inferior = 2.5;   // aire bajo la placa para las soldaduras THT (~2 mm + margen)
margen_componentes = 0.5; // margen que se suma a cada zona prohibida en la comprobación

// ---------------------------------------------------------------------
// [ESP32-S3-DevKitC-1] sobre J2/J3
// ---------------------------------------------------------------------
devkit_ancho   = 25.4;
devkit_largo   = 62.74;
devkit_pin1_desde_punta = 7.9;  // del extremo de la antena al pin 1 (supuesto: deja la antena sobre la muesca)
zocalo_alto    = 8.5;           // zócalos hembra 1x22
pin_plastico   = 2.5;           // plástico de los pines macho del DevKit
devkit_pcb_e   = 1.6;
devkit_modulo_alto = 3.3;       // el módulo sobresale de su placa
devkit_alto_total = zocalo_alto + pin_plastico + devkit_pcb_e + devkit_modulo_alto; // ~15.9 (unos 16)
devkit_modulo  = [18.0, 25.5];  // ESP32-S3-WROOM-1 (ancho, largo)
devkit_antena_largo = 6.4;      // zona de la antena en el extremo del módulo
antena_margen  = 3.0;           // margen alrededor de la antena sin plástico grueso ni tornillos

// ---------------------------------------------------------------------
// [Pantalla] NHD-5.0-800480AF-ASXP-CTP
// ---------------------------------------------------------------------
pantalla_ancho  = 120.7;   // contorno (dato del enunciado y de Newhaven)
pantalla_alto   = 75.8;
pantalla_grosor = 4.55;    // Newhaven: 120.7 x 75.8 x 4.55 mm. MÍDELA (si no, prueba 5)
pantalla_cx     = 132.69;  // centrada en X (enunciado)
// Posición vertical calculada (ver SUPUESTOS.md): borde inferior en y = 112.0
//  - el pliegue del FPC queda al sur de las bocas de J1 (y 106.4) y J4 (y 107.7)
//  - el marco superior deja sitio al agujero de RESET (y 31.5)
//  - el marco inferior no toca las guías de SW6-SW9 (y > 117)
pantalla_borde_inf = 112.0;
pantalla_cy     = pantalla_borde_inf - pantalla_alto / 2;   // 74.1
ventana         = [109.0, 65.8];   // zona visible (Newhaven); la activa es 108 x 64.8
ventana_desplaz = [0, 0];          // si la zona visible no está centrada en el contorno
ventana_radio   = 1.0;
ventana_chaflan = 1.0;             // chaflán exterior de la ventana
holgura_pantalla_devkit = 1.5;     // aire entre el DevKit y la trasera de la pantalla
espuma_pantalla = 0.5;             // hueco para cinta de espuma entre pantalla y pisapantallas
pisapantalla_e  = 2.0;             // grosor de las barras que sujetan la pantalla por detrás
pisapantalla_ancho = 5.0;
pisa_dx         = 9.7;    // distancia de cada barra al borde lateral de la pantalla
// FPC: salen por el borde inferior y se doblan hacia atrás hasta J1 y J4
fpc_tft_ancho   = 24.0;   // FPC de 40 pines (0.5 mm) + margen
fpc_ctp_ancho   = 10.0;   // FPC de 6 pines del táctil + margen
fpc_pliegue     = 3.5;    // espacio para el pliegue bajo el borde inferior

// ---------------------------------------------------------------------
// [Pulsadores] MLD-TS-6X6X5-J
// ---------------------------------------------------------------------
sw_cuerpo      = 6.0;
sw_alto_cuerpo = 3.5;
sw_vastago_d   = 3.5;
sw_alto        = 5.0;    // cara superior del vástago sobre la placa
sw_recorrido   = 0.25;   // recorrido hasta que hace clic
// Capuchones
cap_juego      = 0.4;    // juego vertical entre la brida y el tubo: absorbe tolerancias de altura
cap_tubo_largo = 6.0;    // largo del tubo guía bajo la piel
cap_pie_d      = 4.5;    // pie que apoya en el vástago
cap_brida      = 1.5;    // vuelo de la brida (tope) sobre el cuerpo
cap_brida_e    = 0.6;    // parte recta de la brida bajo el cono de 45°
grabado_prof   = 0.5;    // profundidad de los símbolos grabados
// tipos: [nombre, forma ("D" o "estadio"), tamaño [a, b], sobresale]
CAP_TIPOS = [
  ["cruceta", "D",       [8.0, 8.0],  1.5],
  ["abxy",    "D",       [8.0, 8.0],  1.5],
  ["gatillo", "estadio", [12.0, 7.0], 1.5],
  ["fila",    "D",       [6.0, 6.0],  1.2],
];
// botones: [ref, tipo, símbolo]
BOTONES = [
  ["SW1",  "gatillo", "L"],
  ["SW2",  "cruceta", "arriba"],
  ["SW3",  "cruceta", "derecha"],
  ["SW4",  "cruceta", "izquierda"],
  ["SW5",  "cruceta", "abajo"],
  ["SW6",  "fila",    "select"],
  ["SW7",  "fila",    "menos"],
  ["SW8",  "fila",    "mas"],
  ["SW9",  "fila",    "home"],
  ["SW10", "abxy",    "cruz"],
  ["SW11", "abxy",    "circulo"],
  ["SW12", "abxy",    "cuadrado"],
  ["SW13", "abxy",    "triangulo"],
  ["SW15", "gatillo", "R"],
];
// RESET (SW14): agujero para clip con tubo guía hasta el vástago
clip_d         = 2.2;
tubo_clip_pared = 2.0;   // pared de los tubos de RESET y BOOT
reset_tubo_hasta = sw_alto + 1.0;
// BOOT (SW16) queda bajo la pantalla: empujador en L que se pulsa con clip
boot_varilla   = 3.4;     // sección cuadrada de la varilla y del brazo
boot_brazo_alto = 4.5;
boot_brazo_z   = 7.5;     // cara inferior del brazo
boot_varilla_y = 30.5;    // la varilla sale por el bisel superior, fuera de la pantalla

// ---------------------------------------------------------------------
// [Joysticks] tipo Joy-Con (MIDE el tuyo y ajusta)
// ---------------------------------------------------------------------
joy_base       = [19.0, 18.0];   // placa base (con orejas)
joy_base_e     = 1.6;            // grosor de las orejas
joy_cuerpo_d   = 14.0;           // cúpula
joy_cuerpo_alto = 8.0;           // de la base a lo alto de la cúpula
joy_total_alto = 15.5;           // de la base a lo alto del capuchón en reposo
joy_cap_d      = 15.0;           // capuchón del stick
joy_cap_alto   = 3.0;            // canto del capuchón
joy_eje_d      = 4.0;
joy_pivote     = 5.0;            // altura del centro de giro sobre la base
joy_inclinacion = 20;            // inclinación máxima (grados)
joy_agujeros   = [[-7.75, -7.25], [7.75, 7.25]];  // tornillos (coord. del módulo, mm)
joy_tornillo_d = 1.6;            // agujero de las orejas
joy_piloto_d   = 1.2;            // agujero piloto en los postes (M1.4 o M1.6 autorroscante)
joy_poste_d    = 5.3;
joy_sobresale  = 5.0;            // altura del capuchón sobre la cara frontal
joy_agujero_d  = 21.0;           // hueco circular en la cara frontal
// posición del eje del stick (coordenadas KiCad) y giro del módulo
joy_izq        = [40.5, 84.0];
joy_der        = [216.5, 83.0];
joy_giro_izq   = 0;
joy_giro_der   = 0;

// ---------------------------------------------------------------------
// [Altavoz] en J5
// ---------------------------------------------------------------------
altavoz_d      = 20.0;
altavoz_alto   = 4.5;
altavoz_pos    = [45.0, 116.0];
altavoz_aro_e  = 1.6;
rejilla_d      = 15.0;   // diámetro de la zona con agujeros
rejilla_agujero = 1.6;
rejilla_paso   = 2.6;

// ---------------------------------------------------------------------
// [LED D2] tubo de luz
// ---------------------------------------------------------------------
led_tipo       = "tubo";   // "tubo": agujero de 2 mm para un trozo de filamento transparente
                           // "ventana": piel de 0.4 mm (filamento blanco o natural)
led_agujero_d  = 2.0;
led_ventana_e  = 0.4;
led_tubo_pared = 2.0;

// ---------------------------------------------------------------------
// [USB-C J10]
// ---------------------------------------------------------------------
usb_funda      = [12.5, 7.0];   // funda del conector del cable (ancho, alto)
usb_funda_radio = 1.5;          // radio de las esquinas de la funda
usb_z          = 1.63;          // centro del receptáculo sobre la placa (TYPE-C-31-M-12, 3.26 mm)

// ---------------------------------------------------------------------
// [Uniones]
// ---------------------------------------------------------------------
// Frontal: tres piezas para que las uniones queden fuera de la pantalla.
// Unión A (izquierda|central): x = 69.8 en el bisel superior y x = 66.5 en el resto
// (el escalón deja la torreta (65;24) entera en la pieza izquierda).
union_A_sup_x  = 69.8;
union_A_x      = 66.5;
union_A_escalon_y = 31.0;
union_B_x      = 200.25;        // unión B (central|derecha)
union_T_x      = 115.0;         // trasera: izquierda|derecha (franja sin patillas THT)
nervio_prof    = 9.0;           // nervio de unión bajo la piel frontal
nervio_e       = 3.0;
nervio_e_central = 6.0;         // en la pieza central rellena hasta el marco de la pantalla
tira_trasera_e = 3.0;           // franja engrosada del suelo junto a la unión trasera
cola_largo     = 3.5;           // colas de milano
cola_cuello    = 6.0;
cola_punta     = 8.0;
colas_A_y      = [42, 92, 106];
colas_B_y      = [40, 70, 100];
colas_T_y      = [30, 72, 108];
pernos_A_y     = [17.5, 70.0];  // tornillos M3 horizontales con tuerca
pernos_B_y     = [17.5, 126.5];
bloque_perno   = [7.0, 7.0];    // largo (x) por lado y ancho (y) de los bloques

// ---------------------------------------------------------------------
// [Tornillería]
// ---------------------------------------------------------------------
m3_paso        = 3.4;   // agujero pasante
m3_cabeza_d    = 6.2;   // alojamiento de cabeza DIN 912 (5.5) + holgura
m3_cabeza_h    = 3.0;
m3_tuerca      = 5.5;   // entre caras (DIN 934)
m3_tuerca_e    = 2.4;
m3_piloto      = 2.6;   // autorroscado de un M3 en PLA
fijacion_pcb   = "inserto";   // "inserto" (térmico M3) o "autorroscante" (el M3 rosca en un piloto de 2.6 mm)
inserto_d      = 4.0;   // agujero para inserto M3 x 5.7 (diámetro exterior 4.6)
inserto_l      = 6.0;
torreta_d      = 8.0;
pata_d         = 7.0;   // patas traseras bajo la placa
tornillo_largo = 10;    // M3 x 10: placa y uniones
tornillo_pisa_largo = 6; // M3 x 6: pisapantallas (más largo asomaría por la cara frontal)

// =====================================================================
//  VALORES DERIVADOS (no hace falta tocarlos)
// =====================================================================
PCB_BOT        = -PCB_GROSOR;
Z_PANTALLA_TRAS = devkit_alto_total + holgura_pantalla_devkit;
ZF             = Z_PANTALLA_TRAS + pantalla_grosor + piel;   // cara frontal
Z_PIEL         = ZF - piel;                                   // cara interior de la piel
Z_SUELO_INT    = PCB_BOT - hueco_inferior;
Z_TRASERA      = Z_SUELO_INT - suelo;
Z_COSTURA      = PCB_BOT;                       // costura visible frontal/trasera
LABIO          = 2.0;                           // solape del rebaje frontal/trasero
LABIO_E        = (pared - holgura) / 2;         // grosor de cada labio
Z_LABIO        = Z_COSTURA - LABIO;

// Caja de la placa con holgura y caja exterior
CAJA_CAV  = [PCB_BBOX[0] - holgura_pcb, PCB_BBOX[1] - holgura_pcb,
             PCB_BBOX[2] + holgura_pcb, PCB_BBOX[3] + holgura_pcb];
R_CAV     = PCB_RADIO_ESQUINA + holgura_pcb;
CAJA_EXT  = [CAJA_CAV[0] - pared, CAJA_CAV[1] - pared, CAJA_CAV[2] + pared, CAJA_CAV[3] + pared];
R_EXT     = R_CAV + pared;

// Pantalla
PANT = [pantalla_cx - pantalla_ancho / 2, pantalla_cy - pantalla_alto / 2,
        pantalla_cx + pantalla_ancho / 2, pantalla_cy + pantalla_alto / 2];
BOLSA = [PANT[0] - holgura, PANT[1] - holgura, PANT[2] + holgura, PANT[3] + holgura];
MARCO = [BOLSA[0] - pared_interna, BOLSA[1] - pared_interna, BOLSA[2] + pared_interna, BOLSA[3] + pared_interna];
Z_PISA_SUP = Z_PANTALLA_TRAS - espuma_pantalla;      // cara superior de los pisapantallas
Z_PISA_INF = Z_PISA_SUP - pisapantalla_e;
Z_MARCO_SI  = Z_PISA_SUP + 0.3;                      // fondo de las paredes del marco (sobre el DevKit y los pisapantallas)

// Componentes por referencia
function comp(ref) = PCB_COMPONENTES[search([ref], PCB_COMPONENTES, 1, 0)[0]];
function centro(ref) = comp(ref)[8];
function courtyard(ref) = comp(ref)[6];
function fab(ref) = comp(ref)[7];

J1 = comp("J1"); J4 = comp("J4"); J5 = comp("J5"); J6 = comp("J6"); J7 = comp("J7");
J10 = comp("J10");
DEVKIT_CX = (comp("J2")[3] + comp("J3")[3]) / 2;
DEVKIT_PUNTA = comp("J2")[4] - devkit_pin1_desde_punta;
DEVKIT = [DEVKIT_CX - devkit_ancho / 2, DEVKIT_PUNTA, DEVKIT_CX + devkit_ancho / 2, DEVKIT_PUNTA + devkit_largo];
DEVKIT_Z0 = zocalo_alto + pin_plastico;
ANTENA = [DEVKIT_CX - devkit_modulo[0] / 2, DEVKIT_PUNTA, DEVKIT_CX + devkit_modulo[0] / 2, DEVKIT_PUNTA + devkit_antena_largo];
// zona sin plástico grueso ni tornillos: toda la muesca y la antena con margen, hasta la piel
ZONA_ANTENA = [min(PCB_MUESCA_ANTENA[0], ANTENA[0] - antena_margen), CAJA_CAV[1],
               max(PCB_MUESCA_ANTENA[2], ANTENA[2] + antena_margen), ANTENA[3] + antena_margen];

// Joysticks: z de la base del módulo
JOY_Z_BASE = ZF + joy_sobresale - joy_total_alto;

// Posición vertical de los capuchones
CAP_Z_TUBO = Z_PIEL - cap_tubo_largo;          // extremo inferior del tubo guía
// arranque del cono de 45° de la brida: así el juego medido en el borde del tubo es cap_juego
CAP_Z_BRIDA = CAP_Z_TUBO - cap_juego + holgura;

// USB-C: cara del receptáculo y hueco
USB_X = J10[3];
USB_CARA_Y = fab("J10")[3];
USB_HUECO = [usb_funda[0] + 2 * holgura, usb_funda[1] + 2 * holgura];

// Regiones de las piezas (polígonos en coordenadas KiCad, sin holguras)
X_MIN = CAJA_EXT[0] - 10; X_MAX = CAJA_EXT[2] + 10;
Y_MIN = CAJA_EXT[1] - 10; Y_MAX = CAJA_EXT[3] + 10;
REGIONES = [
  ["frontal_izquierda", [[X_MIN, Y_MIN], [union_A_sup_x, Y_MIN], [union_A_sup_x, union_A_escalon_y],
                         [union_A_x, union_A_escalon_y], [union_A_x, Y_MAX], [X_MIN, Y_MAX]]],
  ["frontal_central",   [[union_A_sup_x, Y_MIN], [union_B_x, Y_MIN], [union_B_x, Y_MAX],
                         [union_A_x, Y_MAX], [union_A_x, union_A_escalon_y], [union_A_sup_x, union_A_escalon_y]]],
  ["frontal_derecha",   [[union_B_x, Y_MIN], [X_MAX, Y_MIN], [X_MAX, Y_MAX], [union_B_x, Y_MAX]]],
  ["trasera_izquierda", [[X_MIN, Y_MIN], [union_T_x, Y_MIN], [union_T_x, Y_MAX], [X_MIN, Y_MAX]]],
  ["trasera_derecha",   [[union_T_x, Y_MIN], [X_MAX, Y_MIN], [X_MAX, Y_MAX], [union_T_x, Y_MAX]]],
];
function region(nombre) = REGIONES[search([nombre], REGIONES, 1, 0)[0]][1];
// Rango X aproximado de cada pieza (para no construir rasgos que no le tocan)
function rango_x(nombre) =
  nombre == "frontal_izquierda" ? [X_MIN, union_A_sup_x + 8] :
  nombre == "frontal_central"   ? [union_A_x - 8, union_B_x + 8] :
  nombre == "frontal_derecha"   ? [union_B_x - 8, X_MAX] :
  nombre == "trasera_izquierda" ? [X_MIN, union_T_x + 8] :
  nombre == "trasera_derecha"   ? [union_T_x - 8, X_MAX] : [X_MIN, X_MAX];
function en_pieza(nombre, x, r = 0) = let (rx = rango_x(nombre)) x + r >= rx[0] && x - r <= rx[1];

// =====================================================================
//  COMPROBACIONES DE PARÁMETROS
// =====================================================================
assert(pared >= 2 && piel >= 2 && suelo >= 2, "Las paredes deben ser de al menos 2 mm");
assert(Z_PANTALLA_TRAS >= devkit_alto_total + 0.5, "La pantalla toca el DevKit");
assert(union_A_x + holgura_union + cola_largo + holgura + 1.5 <= BOLSA[0], "Unión A sin sitio para las colas");
assert(union_B_x - holgura_union - cola_largo - holgura - 1.5 >= BOLSA[2], "Unión B sin sitio para las colas");
