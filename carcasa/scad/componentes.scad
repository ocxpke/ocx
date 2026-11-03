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
  // Pliegues de los FPC bajo el borde inferior de la pantalla
  ["caja", "FPC_TFT_pliegue", "fpc", [J1[3] - fpc_tft_ancho / 2 + 1, PANT[3], J1[3] + fpc_tft_ancho / 2 - 1, PANT[3] + fpc_pliegue], 1.0, Z_PIEL - 0.6],
  ["caja", "FPC_CTP_pliegue", "fpc", [J4[3] - fpc_ctp_ancho / 2 + 1, PANT[3], J4[3] + fpc_ctp_ancho / 2 - 1, PANT[3] + fpc_pliegue], 1.0, Z_PIEL - 0.6],
  ["caja", "FPC_TFT_tramo", "fpc", [J1[3] - fpc_tft_ancho / 2 + 1, fab("J1")[3], J1[3] + fpc_tft_ancho / 2 - 1, PANT[3] + fpc_pliegue], 0.0, 2.5],
  ["caja", "FPC_CTP_tramo", "fpc", [J4[3] - fpc_ctp_ancho / 2 + 1, fab("J4")[3], J4[3] + fpc_ctp_ancho / 2 - 1, PANT[3] + fpc_pliegue], 0.0, 3.0],
  // Paso del FPC de cada joystick: baja del módulo y entra en J6/J7 por el sur
  ["caja", "FPC_joy_izq", "fpc", [J6[3] - 3, fab("J6")[3], J6[3] + 3, joy_izq[1] + joy_base[1] / 2 + 5], 0.5, JOY_Z_BASE],
  ["caja", "FPC_joy_der", "fpc", [J7[3] - 3, fab("J7")[3], J7[3] + 3, joy_der[1] + joy_base[1] / 2 + 5], 0.5, JOY_Z_BASE],
  // Joysticks (placa base y cúpula; el barrido del stick se comprueba aparte)
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
   ["cil", str(nombre, "_cupula"), "joystick", pos, joy_cuerpo_d / 2, JOY_Z_BASE + joy_base_e, JOY_Z_BASE + joy_cuerpo_alto]];

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
  ["pcb", [0.05, 0.4, 0.2]], ["antena", [1, 0.2, 0.2]],
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
  if (con_pantalla) pantalla();
  for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
  color([0.55, 0.55, 0.6]) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
  // FPC
  color([0.9, 0.55, 0.1]) for (f = [[J1[3], fpc_tft_ancho - 2, fab("J1")[3] - 2], [J4[3], fpc_ctp_ancho - 2, fab("J4")[3] - 2]]) {
    cajaK([f[0] - f[1] / 2, f[2], f[0] + f[1] / 2, PANT[3] + 1.5], 1.0, 1.15);
    cajaK([f[0] - f[1] / 2, PANT[3] + 1.4, f[0] + f[1] / 2, PANT[3] + 1.55], 1.0, Z_PANTALLA_TRAS + 0.5);
    cajaK([f[0] - f[1] / 2, PANT[3] - 3, f[0] + f[1] / 2, PANT[3] + 1.55], Z_PANTALLA_TRAS + 0.35, Z_PANTALLA_TRAS + 0.5);
  }
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
