// =====================================================================
//  OCX - carcasa · componentes de la placa (fantasmas)
//  zonas_prohibidas() devuelve la lista de volúmenes que ninguna pieza
//  impresa puede invadir. La usan los renders y scripts/comprobar.py
//  (que la lee con  -D 'pieza="datos"').
//  Formato:  ["caja", nombre, grupo, [x0,y0,x1,y1] (KiCad), z0, z1]
//            ["cil",  nombre, grupo, [cx,cy] (KiCad), r, z0, z1]
// =====================================================================

function zona_componente(c) =
  let (ref = c[0], b = c[6], h = c[9] + margen_componentes, g = c[10])
  g == "pulsador" ?
    [["caja", str(ref, "_cuerpo"), "pulsador", caja_centro(c[8], [sw_cuerpo, sw_cuerpo]), 0, sw_alto_cuerpo + margen_componentes / 2],
     ["cil", str(ref, "_vastago"), "vastago", c[8], sw_vastago_d / 2, 0, sw_alto]] :
  ref == "J5" ?  // cabezal JST con su clavija y los cables saliendo hacia arriba
    [["caja", ref, "conector", b, 0, 12.0]] :
  g == "agujero" ? [] :
  [["caja", ref, g, b, 0, h]];

function zonas_pcb() = [for (c = PCB_COMPONENTES) each zona_componente(c)];

function zonas_tht() = [for (t = PCB_THT) ["cil", str(t[0], "_tht"), "tht", [t[1], t[2]], t[3] + 0.3, PCB_BOT - PCB_ASOMA_THT, PCB_BOT]];

function zonas_extra() = [
  // ESP32-S3-DevKitC-1 (placa + módulo + conectores USB, envolvente)
  ["caja", "DevKit", "devkit", [DEVKIT[0], DEVKIT[1], DEVKIT[2], DEVKIT[3] + 1.0], DEVKIT_Z0, devkit_alto_total + margen_componentes],
  // Pantalla (toca la piel por delante: contacto sin volumen)
  ["caja", "Pantalla", "pantalla", PANT, Z_PANTALLA_TRAS, Z_PIEL],
  // FPC de la pantalla (40 pines): el cuello rodea el canto inferior, la parte ancha va pegada
  // a la trasera y la cola llega plana hasta el adaptador; de ahí sale el FFC hasta J1
  ["caja", "FPC_TFT_cuello", "fpc", [TFT_X - fpc_tft_ancho / 2 + 1, PANT[3], TFT_X + fpc_tft_ancho / 2 - 1, PANT[3] + fpc_pliegue], TFT_Z_FILM - 0.3, Z_PIEL - 0.6],
  ["caja", "FPC_TFT_ancha", "fpc", [TFT_X - tft_ancha_ancho / 2, TFT_ANCHA_Y0, TFT_X + tft_ancha_ancho / 2, PANT[3]], Z_PANTALLA_TRAS - tft_ancha_e, Z_PANTALLA_TRAS],
  ["caja", "FPC_TFT_cola", "fpc", [TFT_X - tft_cola_ancho / 2 - 0.5, TFT_PUNTA_Y, TFT_X + tft_cola_ancho / 2 + 0.5, TFT_ANCHA_Y0], AD_RANURA_Z - 0.5, Z_PANTALLA_TRAS],
  ["caja", "Adaptador_TFT", "adaptador", AD, AD_Z0, Z_PANTALLA_TRAS],
  ["caja", "FFC_TFT", "fpc", [TFT_X - ffc_ancho / 2 - 0.5, FFC_Y_V1 - FFC_R1 - 0.5, TFT_X + ffc_ancho / 2 + 0.5, FFC_Y_V2 + FFC_R2 + 0.5],
                             ffc_z_conector - 0.5, AD_RANURA_Z + 0.5],
  // FPC del táctil: se dobla hacia atrás en el canto inferior y baja hasta J4
  ["caja", "FPC_CTP_pliegue", "fpc", [J4[3] - fpc_ctp_ancho / 2 + 1, PANT[3], J4[3] + fpc_ctp_ancho / 2 - 1, PANT[3] + fpc_pliegue], 1.0, Z_PIEL - 0.6],
  ["caja", "FPC_CTP_tramo", "fpc", [J4[3] - fpc_ctp_ancho / 2 + 1, fab("J4")[3], J4[3] + fpc_ctp_ancho / 2 - 1, PANT[3] + fpc_pliegue], 0.0, 3.0],
  // Paso del cable de cada joystick: sale del borde norte del módulo y baja con una S hasta J6/J7
  zona_cable_joy("FPC_joy_izq", joy_izq, joy_giro_izq, "J6"),
  zona_cable_joy("FPC_joy_der", joy_der, joy_giro_der, "J7"),
  // Joysticks (placa base, cúpula y tacos de espuma; el barrido del stick se comprueba aparte)
  each zonas_joystick("Joy_izq", joy_izq, joy_giro_izq),
  each zonas_joystick("Joy_der", joy_der, joy_giro_der),
  // Altavoz
  ["cil", "Altavoz", "altavoz", altavoz_pos, altavoz_d / 2, Z_PIEL - altavoz_alto, Z_PIEL],
  // Clavija USB-C con su funda entrando por el hueco
  //   ["redondeada_y", nombre, grupo, [cx, y0, y1], [ancho, alto], radio, cz]
  ["redondeada_y", "Clavija_USB", "usb", [USB_X, USB_CARA_Y + 0.05, USB_CARA_Y + 30], usb_funda, usb_funda_radio, usb_z],
  // La propia placa con su contorno real
  ["poli", "PCB", "pcb", PCB_CONTORNO, PCB_BOT, 0],
];

function zonas_joystick(nombre, pos, giro) = let (
    a = -giro,   // giro KiCad (antihorario en pantalla) -> en KiCad Y abajo
    hx = abs(joy_base[0] / 2 * cos(giro)) + abs(joy_base[1] / 2 * sin(giro)),
    hy = abs(joy_base[0] / 2 * sin(giro)) + abs(joy_base[1] / 2 * cos(giro)))
  [["caja", str(nombre, "_base"), "joystick", [pos[0] - hx, pos[1] - hy, pos[0] + hx, pos[1] + hy], JOY_Z_BASE, JOY_Z_BASE + joy_base_e],
   ["cil", str(nombre, "_cupula"), "joystick", pos, joy_cuerpo_d / 2, JOY_Z_BASE + joy_base_e, JOY_Z_BASE + joy_cuerpo_alto],
   for (i = [0:len(joy_tacos) - 1]) ["caja", str(nombre, "_taco", i + 1), "espuma", taco_joy(pos, giro, i), 0, JOY_Z_BASE]];

// Punto de un módulo dado respecto a su eje con el cable hacia el norte (giro 180)
function joy_punto(pos, giro, rel) = let (t = giro - 180)
  [pos[0] + rel[0] * cos(t) + rel[1] * sin(t), pos[1] - rel[0] * sin(t) + rel[1] * cos(t)];
// Huella de un taco de espuma (caja KiCad; los giros son múltiplos de 90°)
function taco_joy(pos, giro, i) = let (c = joy_punto(pos, giro, joy_tacos[i]),
    t = (round(giro / 90) % 2 == 0) ? joy_taco : [joy_taco[1], joy_taco[0]]) caja_centro(c, t);
// Salida del cable: punto del borde del módulo (KiCad) por donde sale (con giro 180, el borde norte)
function joy_salida(pos, giro) = joy_punto(pos, giro, [joy_fpc_desplaz, -joy_base[1] / 2]);
// Geometría de la S: [salida [x, y], y de la boca, z de salida, z de la ranura, recorrido D, bajada H]
function joy_cable(pos, giro, ref) = let (a = joy_salida(pos, giro), yb = fab(ref)[3])
  [a, yb, JOY_Z_CABLE, joy_fpc_z_conector, a[1] - yb, JOY_Z_CABLE - joy_fpc_z_conector];
// Zona que no puede invadir ninguna pieza: de la boca del conector al borde del módulo
function zona_cable_joy(nombre, pos, giro, ref) = let (g = joy_cable(pos, giro, ref), a = g[0])
  ["caja", nombre, "fpc", [a[0] - joy_fpc_ancho / 2 - 1, min(g[1], a[1]) - 0.5, a[0] + joy_fpc_ancho / 2 + 1, max(g[1], a[1]) + 1.0],
   0.2, JOY_Z_BASE + 1.0];
// Eje de la S como lista de [y KiCad, z] (dos arcos tangentes: la forma relajada del cable; la
// comprobación usa la elástica real en scripts/comprobar.py)
function joy_cable_puntos(pos, giro, ref, n = 16) = let (g = joy_cable(pos, giro, ref), d = g[4], h = g[5],
    th = 2 * atan2(h, d), r = d / (2 * sin(th)), y0 = g[0][1], za = g[2], zb = g[3])
  concat([for (i = [0:n]) let (t = th * i / n) [y0 - r * sin(t), za - r + r * cos(t)]],
         [for (i = [n:-1:0]) let (t = th * i / n) [y0 - d + r * sin(t), zb + r - r * cos(t)]],
         [[g[1] - joy_fpc_inserta, zb]]);

// Zona de la antena: nada de piezas entre el suelo interior y la piel
function zona_antena() = ["caja", "ANTENA", "antena", ZONA_ANTENA, Z_SUELO_INT, Z_PIEL];

function zonas_prohibidas() = concat(zonas_pcb(), zonas_tht(), zonas_extra(), [zona_antena()]);

// Puntos de los tornillos de los joysticks en coordenadas KiCad
function joy_tornillos(pos, giro) = [for (h = joy_agujeros)
  [pos[0] + h[0] * cos(giro) + h[1] * sin(giro), pos[1] - h[0] * sin(giro) + h[1] * cos(giro)]];

// ---------------------------------------------------------------------
//  Dibujo de las zonas (renders)
// ---------------------------------------------------------------------
COLORES = [
  ["pulsador", [0.15, 0.15, 0.15]], ["vastago", [0.85, 0.85, 0.85]], ["smd", [0.25, 0.25, 0.3]],
  ["zocalo", [0.1, 0.1, 0.1]], ["conector", [0.95, 0.95, 0.9]], ["tht", [0.7, 0.7, 0.7]],
  ["devkit", [0.1, 0.25, 0.55]], ["pantalla", [0.05, 0.05, 0.08]], ["fpc", [0.9, 0.55, 0.1]],
  ["joystick", [0.2, 0.2, 0.22]], ["altavoz", [0.55, 0.55, 0.6]], ["usb", [0.3, 0.3, 0.3]],
  ["pcb", [0.05, 0.4, 0.2]], ["antena", [1, 0.2, 0.2]], ["adaptador", [0.1, 0.45, 0.25]], ["espuma", [0.95, 0.85, 0.3]],
];
function color_de(g) = let (i = search([g], COLORES, 1, 0)[0]) i == undef ? [0.5, 0.5, 0.5] : COLORES[i][1];

module dibuja_zona_c(z) {
  if (z[0] == "caja") cajaK(z[3], z[4], z[5]);
  else if (z[0] == "cil") translate([z[3][0], -z[3][1], z[5]]) cylinder(r = z[4], h = z[6] - z[5], $fn = fn_peq);
  else if (z[0] == "poli") translate([0, 0, z[4]]) linear_extrude(z[5] - z[4]) polygon(Kpts(z[3]));
  else if (z[0] == "redondeada_y") translate([z[3][0], -z[3][1], z[6]]) rotate([90, 0, 0])
    linear_extrude(z[3][2] - z[3][1]) offset(r = z[5], $fn = fn_peq * 2) square(z[4] - [2, 2] * z[5], center = true);
}

// Placa con su contorno real y agujeros
module placa() {
  color([0.05, 0.4, 0.2]) translate([0, 0, PCB_BOT]) linear_extrude(PCB_GROSOR) difference() {
    polygon(Kpts(PCB_CONTORNO));
    for (h = PCB_AGUJEROS) translate(K(h)) circle(d = h[2], $fn = fn_peq);
  }
}

// Placa con sus componentes y el DevKit (sin lo que va sujeto a la carcasa)
module placa_montada() {
  placa();
  for (z = concat(zonas_pcb(), zonas_tht())) if (z[2] != "pcb") color(color_de(z[2])) dibuja_zona_c(z);
  color([0.1, 0.25, 0.55]) cajaK(DEVKIT, DEVKIT_Z0, DEVKIT_Z0 + devkit_pcb_e);
  color([0.75, 0.75, 0.78]) cajaK([DEVKIT_CX - devkit_modulo[0] / 2, DEVKIT_PUNTA + devkit_antena_largo,
                                   DEVKIT_CX + devkit_modulo[0] / 2, DEVKIT_PUNTA + devkit_modulo[1]],
                                  DEVKIT_Z0 + devkit_pcb_e, devkit_alto_total);
  color([0.1, 0.1, 0.12]) cajaK(ANTENA, DEVKIT_Z0 + devkit_pcb_e, DEVKIT_Z0 + devkit_pcb_e + 0.8);
}

// Componentes y montaje electrónico para los renders
module electronica(con_pantalla = true) {
  placa();
  for (z = concat(zonas_pcb(), zonas_tht())) if (z[2] != "pcb") color(color_de(z[2])) dibuja_zona_c(z);
  // DevKit: placa azul, módulo metálico y antena
  color([0.1, 0.25, 0.55]) cajaK(DEVKIT, DEVKIT_Z0, DEVKIT_Z0 + devkit_pcb_e);
  color([0.75, 0.75, 0.78]) cajaK([DEVKIT_CX - devkit_modulo[0] / 2, DEVKIT_PUNTA + devkit_antena_largo,
                                   DEVKIT_CX + devkit_modulo[0] / 2, DEVKIT_PUNTA + devkit_modulo[1]],
                                  DEVKIT_Z0 + devkit_pcb_e, devkit_alto_total);
  color([0.1, 0.1, 0.12]) cajaK(ANTENA, DEVKIT_Z0 + devkit_pcb_e, DEVKIT_Z0 + devkit_pcb_e + 0.8);
  if (con_pantalla) { pantalla(); fpc_pantalla(); }
  for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
  cables_joystick();
  color([0.55, 0.55, 0.6]) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
  fpc_tactil();
}

// FPC del táctil: baja doblado desde el canto inferior de la pantalla hasta J4
module fpc_tactil() color([0.9, 0.55, 0.1]) let (x = J4[3], w = fpc_ctp_ancho - 2, y0 = fab("J4")[3] - 2) {
  cajaK([x - w / 2, y0, x + w / 2, PANT[3] + 1.5], 1.0, 1.15);
  cajaK([x - w / 2, PANT[3] + 1.4, x + w / 2, PANT[3] + 1.55], 1.0, Z_PANTALLA_TRAS + 0.5);
  cajaK([x - w / 2, PANT[3] - 3, x + w / 2, PANT[3] + 1.55], Z_PANTALLA_TRAS + 0.35, Z_PANTALLA_TRAS + 0.5);
}

// Tira plana a lo largo de una polilínea [[y KiCad, z], ...], centrada en x (para los renders)
module tira(pts, x, ancho, e) for (i = [0:len(pts) - 2]) hull() for (p = [pts[i], pts[i + 1]])
  translate([x - ancho / 2, -p[0] - 0.005, p[1] - e / 2]) cube([ancho, 0.01, e]);

// Cable de cada joystick: S desde el borde norte del módulo hasta J6/J7
module cables_joystick() color([0.85, 0.6, 0.2])
  for (j = [[joy_izq, joy_giro_izq, "J6"], [joy_der, joy_giro_der, "J7"]])
    tira(joy_cable_puntos(j[0], j[1], j[2]), joy_cable(j[0], j[1], j[2])[0][0], joy_fpc_ancho, joy_fpc_e);

// Tacos de espuma bajo los módulos de los joysticks
module tacos_joystick(c = [0.95, 0.85, 0.3]) color(c)
  for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]], i = [0:len(joy_tacos) - 1]) cajaK(taco_joy(j[0], j[1], i), 0, JOY_Z_BASE);

// Eje del FFC del alargador como [[y KiCad, z], ...]: sale del adaptador hacia el norte, vuelve
// bajo la pantalla hacia el sur y entra en J1 hacia el norte
function ffc_puntos(n = 12) = concat(
  [[AD[1] + ffc_inserta, AD_RANURA_Z], [FFC_Y_V1, AD_RANURA_Z]],
  [for (i = [1:n]) let (t = 180 * i / n) [FFC_Y_V1 - FFC_R1 * sin(t), AD_RANURA_Z - FFC_R1 + FFC_R1 * cos(t)]],
  [for (i = [0:n]) let (t = 180 * i / n) [FFC_Y_V2 + FFC_R2 * sin(t), FFC_Z_TRAMO - FFC_R2 + FFC_R2 * cos(t)]],
  [[FFC_Y_J1 - ffc_inserta, ffc_z_conector]]);

// Cola de la pantalla: plana por la trasera y con una S corta hasta la boca del adaptador
function cola_tft_puntos(n = 10) = let (y1 = TFT_COLA_Y0 + 8, dz = TFT_Z_FILM - AD_RANURA_Z) concat(
  [[TFT_ANCHA_Y0, TFT_Z_FILM]],
  [for (i = [0:n]) let (t = i / n) [y1 - 8 * t, AD_RANURA_Z + dz * (1 + cos(180 * t)) / 2]],
  [[TFT_PUNTA_Y, AD_RANURA_Z]]);

// FPC de la pantalla con el alargador, por partes (los cortes de los renders las colorean por separado)
AMBAR = [0.9, 0.55, 0.1];
PLATA = [0.75, 0.76, 0.8];
AZUL_REFUERZO = [0.2, 0.35, 0.75];
VERDE_ADAPTADOR = [0.1, 0.45, 0.25];
NEGRO_CONECTOR = [0.12, 0.12, 0.12];
COLOR_FFC = [0.95, 0.75, 0.35];
TFT_ANCHA = [TFT_X - tft_ancha_ancho / 2, TFT_ANCHA_Y0, TFT_X + tft_ancha_ancho / 2, TFT_ANCHA_Y1];
// cuello (rodea el canto inferior y vuelve por la trasera), película de la parte ancha y cola
module fpc_tft_flexible() {
  tira(concat([for (i = [0:12]) let (t = 180 * i / 12)
      [PANT[3] + tft_pliegue_r * sin(t), TFT_Z_FILM + tft_pliegue_r + tft_pliegue_r * cos(t)]], [[TFT_ANCHA_Y1, TFT_Z_FILM]]),
    TFT_X, fpc_tft_ancho - 2, 0.15);
  cajaK(TFT_ANCHA, TFT_Z_FILM - 0.1, TFT_Z_FILM + 0.05);
  tira(cola_tft_puntos(), TFT_X, tft_cola_ancho, 0.15);
}
module fpc_tft_blindaje() cajaK(encoge(TFT_ANCHA, 1.5), Z_PANTALLA_TRAS - tft_ancha_e, TFT_Z_FILM - 0.1);
module fpc_tft_refuerzo() tira([[TFT_COLA_Y0, AD_RANURA_Z], [TFT_PUNTA_Y, AD_RANURA_Z]], TFT_X, tft_cola_ancho, 0.3);
// adaptador: placa con un conector en cada canto largo
module adaptador_tft_placa() cajaK(AD, AD_Z0 + 2.0, Z_PANTALLA_TRAS);
module adaptador_tft_conectores() for (y = [[AD[1], AD[1] + 4.5], [AD[3] - 4.5, AD[3]]])
  cajaK([AD[0] + 1.5, y[0], AD[2] - 1.5, y[1]], AD_Z0, AD_Z0 + 2.0);
// FFC hasta J1 (sin él, solo el arranque que sale del adaptador)
module ffc_tft(con_ffc = true) tira(con_ffc ? ffc_puntos() : [[AD[1] + ffc_inserta, AD_RANURA_Z], [AD[1] - 8, AD_RANURA_Z]],
                                    TFT_X, ffc_ancho, ffc_e);
module fpc_pantalla(con_ffc = true) {
  color(AMBAR) fpc_tft_flexible();
  color(PLATA) fpc_tft_blindaje();
  color(AZUL_REFUERZO) fpc_tft_refuerzo();
  color(VERDE_ADAPTADOR) adaptador_tft_placa();
  color(NEGRO_CONECTOR) adaptador_tft_conectores();
  color(COLOR_FFC) ffc_tft(con_ffc);
}

module pantalla() {
  color([0.08, 0.08, 0.1]) cajaK(PANT, Z_PANTALLA_TRAS, Z_PIEL - 0.6);
  color([0.02, 0.02, 0.05, 0.9]) cajaK(PANT, Z_PIEL - 0.6, Z_PIEL);
  color([0.1, 0.2, 0.35]) cajaK(caja_centro([pantalla_cx + ventana_desplaz[0], pantalla_cy + ventana_desplaz[1]], [108, 64.8]), Z_PIEL - 0.01, Z_PIEL + 0.01);
}

module joystick(pos, giro) {
  enK(pos[0], pos[1], JOY_Z_BASE) rotate([0, 0, giro]) {
    color([0.2, 0.2, 0.22]) difference() {
      translate([-joy_base[0] / 2, -joy_base[1] / 2, 0]) cube([joy_base[0], joy_base[1], joy_base_e]);
      for (h = joy_agujeros) translate([h[0], -h[1], -1]) cylinder(d = joy_tornillo_d, h = 5, $fn = 12);
    }
    color([0.25, 0.25, 0.27]) cylinder(d = joy_cuerpo_d, h = joy_cuerpo_alto, $fn = fn);
    color([0.3, 0.3, 0.32]) cylinder(d = joy_eje_d, h = joy_total_alto, $fn = fn_peq);
    color([0.12, 0.12, 0.12]) translate([0, 0, joy_total_alto - joy_cap_alto]) cylinder(d = joy_cap_d, h = joy_cap_alto, $fn = fn);
  }
}
