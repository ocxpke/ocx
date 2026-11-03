// =====================================================================
//  OCX - carcasa · piezas imprimibles
//  Todas las piezas se definen en posición de MONTAJE (coordenadas de la
//  placa). carcasa.scad las gira a su orientación de impresión.
// =====================================================================

// ---------------------------------------------------------------------
//  Tornillos de unión horizontales (M3 x 10 + tuerca)
//  [nombre, x_unión, y, lado_cabeza(-1 izq/+1 der), pieza_izq, pieza_der,
//   bloque_cabeza, bloque_tuerca, dist_tuerca, rebaje_cabeza]
// ---------------------------------------------------------------------
// A2 está a la altura de la pantalla: en la central solo hay 5.4 mm hasta la bolsa,
// así que su bloque es corto, la tuerca va a 1 mm de la cara y la cabeza no se embute
// (la punta del M3 x 10 se queda a 1 mm de la bolsa).
PERNOS = [
  ["A1", union_A_sup_x, pernos_A_y[0], -1, "frontal_izquierda", "frontal_central", bloque_perno[0], bloque_perno[0], 2.5, m3_cabeza_h + 0.3],
  ["A2", union_A_x,     pernos_A_y[1], -1, "frontal_izquierda", "frontal_central", 5.35, 5.4, 1.0, 0],
  ["B1", union_B_x,     pernos_B_y[0], +1, "frontal_central", "frontal_derecha", bloque_perno[0], bloque_perno[0], 2.5, m3_cabeza_h + 0.3],
  ["B2", union_B_x,     pernos_B_y[1], +1, "frontal_central", "frontal_derecha", bloque_perno[0], bloque_perno[0], 2.5, m3_cabeza_h + 0.3],
];
Z_PERNO = Z_PIEL - nervio_prof / 2;
Z_NERVIO = Z_PIEL - nervio_prof;

// Geometría derivada de un perno: [x_cara_cabeza, x_fin_bloque_cabeza, x_cara_tuerca, x_fin_bloque_tuerca,
//                                  x_asiento, x_punta, x_tuerca0, x_tuerca1]
function perno_geo(p) = let (
    xj = p[1], s = p[3], hu = holgura_union,
    xfc = xj + s * hu, xbc = xfc + s * p[6],
    xft = xj - s * hu, xbt = xft - s * p[7],
    xa = xbc - s * p[9], xp = xa - s * tornillo_largo,
    xt0 = xj - s * (hu + p[8]), xt1 = xt0 - s * (m3_tuerca_e + 0.2))
  [xfc, xbc, xft, xbt, xa, xp, xt0, xt1];

// Colas de milano: [x_unión, y, pieza_macho, pieza_hembra, sentido(+1 macho crece hacia +X), z0, z1, cuña]
COLAS = concat(
  [for (y = colas_A_y) [union_A_x, y, "frontal_izquierda", "frontal_central", +1, Z_NERVIO, Z_PIEL, true]],
  [for (y = colas_B_y) [union_B_x, y, "frontal_derecha", "frontal_central", -1, Z_NERVIO, Z_PIEL, true]],
  [for (y = colas_T_y) [union_T_x, y, "trasera_izquierda", "trasera_derecha", +1, Z_TRASERA, PCB_BOT - 0.3, false]]);

// Torretas de los pisapantallas: en las 4 esquinas de las barras, fuera de la pantalla.
// Las barras van por detrás de la pantalla, apartadas de las torretas de la placa.
PISA_X = [PANT[0] + pisa_dx, PANT[2] - pisa_dx];
PISA_Y = [MARCO[1] - 2.0, MARCO[3] + 2.0];
PISA_TORRETAS = [for (x = PISA_X, y = PISA_Y) [x, y]];

// Altura del tubo del LED y del tubo de BOOT
Z_LED0 = comp("D2")[9] + margen_componentes;
Z_TUBO_BOOT = boot_brazo_z + boot_brazo_alto + 2 * holgura;
BOOT = centro("SW16");
RESET = centro("SW14");

// =====================================================================
//  Cascarones
// =====================================================================
module cascaron_frontal() {
  difference() {
    union() {
      hull() {
        rcajaK(CAJA_EXT, R_EXT, Z_COSTURA + holgura_costura, ZF - chaflan_frontal);
        rcajaK(encoge(CAJA_EXT, chaflan_frontal), R_EXT - chaflan_frontal, ZF - 0.01, ZF);
      }
      // labio interior que entra en el rebaje de la trasera
      translate([0, 0, Z_LABIO + holgura]) linear_extrude(Z_COSTURA + holgura_costura - Z_LABIO - holgura + 0.01)
        difference() { rrectK(crece(CAJA_CAV, LABIO_E), R_CAV + LABIO_E); rrectK(CAJA_CAV, R_CAV); }
    }
    rcajaK(CAJA_CAV, R_CAV, Z_LABIO - 1, Z_PIEL);
  }
}

module cascaron_trasero() {
  difference() {
    hull() {
      rcajaK(encoge(CAJA_EXT, chaflan_trasero), R_EXT - chaflan_trasero, Z_TRASERA, Z_TRASERA + 0.01);
      rcajaK(CAJA_EXT, R_EXT, Z_TRASERA + chaflan_trasero, Z_COSTURA);
    }
    rcajaK(CAJA_CAV, R_CAV, Z_SUELO_INT, Z_COSTURA + 1);
    rcajaK(crece(CAJA_CAV, LABIO_E + holgura), R_CAV + LABIO_E + holgura, Z_LABIO, Z_COSTURA + 1);
  }
}

// =====================================================================
//  Rasgos de la parte frontal (sólidos), filtrados por pieza
// =====================================================================
module rasgos_frontal(p) {
  // Marco de la pantalla y torretas de los pisapantallas
  if (p == "frontal_central") {
    // la bolsa se vacía después en huecos_frontal(): aquí basta con el bloque exterior del marco
    cajaK(MARCO, Z_MARCO_SI, Z_PIEL + 0.01);
    for (t = PISA_TORRETAS) enK(t[0], t[1], Z_PISA_SUP) cylinder(d = 7, h = Z_PIEL - Z_PISA_SUP + 0.01, $fn = fn_peq * 2);
    // tubo de RESET
    enK(RESET[0], RESET[1], reset_tubo_hasta) cylinder(d = clip_d + 2 * tubo_clip_pared, h = Z_PIEL - reset_tubo_hasta + 0.01, $fn = fn_peq);
    // tubo cuadrado del empujador de BOOT
    lb = boot_varilla + 2 * holgura + 2 * tubo_clip_pared;
    enK(BOOT[0], boot_varilla_y, Z_TUBO_BOOT) translate([-lb / 2, -lb / 2, 0]) cube([lb, lb, Z_PIEL - Z_TUBO_BOOT + 0.01]);
  }
  // Tubos guía de los capuchones
  for (b = BOTONES) let (c = centro(b[0]), t = tipo_cap(b[1])) if (en_pieza(p, c[0], 8))
    enK(c[0], c[1], CAP_Z_TUBO) linear_extrude(Z_PIEL - CAP_Z_TUBO + 0.01) forma_cap(t[1], t[2], holgura + pared_interna);
  // Torretas de los agujeros de la placa
  for (h = PCB_AGUJEROS) if (en_pieza(p, h[0], torreta_d / 2))
    enK(h[0], h[1], 0) cylinder(d = torreta_d, h = Z_PIEL + 0.01, $fn = fn_peq * 2);
  // Postes de los joysticks
  for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) if (en_pieza(p, j[0][0], 15))
    for (t = joy_tornillos(j[0], j[1])) enK(t[0], t[1], JOY_Z_BASE + joy_base_e)
      cylinder(d = joy_poste_d, h = Z_PIEL - JOY_Z_BASE - joy_base_e + 0.01, $fn = fn_peq);
  // Aro del altavoz
  if (en_pieza(p, altavoz_pos[0], altavoz_d / 2 + 3)) aro_altavoz();
  // Tubo de luz del LED
  let (d2 = centro("D2")) if (en_pieza(p, d2[0], 4))
    enK(d2[0], d2[1], Z_LED0) cylinder(d = led_agujero_d + 2 * led_tubo_pared, h = Z_PIEL - Z_LED0 + 0.01, $fn = fn_peq);
}

function tipo_cap(nombre) = CAP_TIPOS[search([nombre], CAP_TIPOS, 1, 0)[0]];

ALTAVOZ_ZH = Z_PIEL - altavoz_alto - 0.05;   // cara de retención de los ganchos
module aro_altavoz() {
  ri = altavoz_d / 2 + holgura;
  re = ri + altavoz_aro_e;
  z0 = ALTAVOZ_ZH - 1.0;
  enK(altavoz_pos[0], altavoz_pos[1], 0) {
    difference() {
      translate([0, 0, z0]) cylinder(r = re, h = Z_PIEL - z0 + 0.01, $fn = fn);
      translate([0, 0, z0 - 1]) cylinder(r = ri, h = Z_PIEL - z0 + 1, $fn = fn);
      // ranuras que dejan tres dedos elásticos
      for (a = [0, 120, 240], s = [-1, 1]) rotate([0, 0, a + s * 18])
        translate([ri - 1, -0.5, z0 - 1]) cube([altavoz_aro_e + 2, 1.0, (altavoz_alto + 1.0) * 0.8 + 1]);
    }
    // ganchos con rampa de entrada
    for (a = [0, 120, 240]) rotate([0, 0, a - 14]) rotate_extrude(angle = 28, $fn = fn)
      polygon([[ri + 0.01, z0], [ri + 0.01, ALTAVOZ_ZH], [ri - 0.6, ALTAVOZ_ZH], [ri - 0.6, z0 + 0.6], [ri - 0.2, z0]]);
  }
}

// =====================================================================
//  Huecos de la parte frontal
// =====================================================================
module huecos_frontal(p) {
  if (p == "frontal_central") {
    // bolsa de la pantalla y ventana con chaflán
    cajaK(BOLSA, Z_TRASERA - 1, Z_PIEL);   // nada de la pieza central bajo la pantalla
    vc = [pantalla_cx + ventana_desplaz[0], pantalla_cy + ventana_desplaz[1]];
    hull() {
      rcajaK(caja_centro(vc, ventana), ventana_radio, Z_PIEL - 0.5, ZF - ventana_chaflan);
      rcajaK(caja_centro(vc, ventana + [2, 2] * ventana_chaflan), ventana_radio + ventana_chaflan, ZF + 0.01, ZF + 0.02);
    }
    // ranuras de los FPC en la pared inferior del marco
    for (f = [[J1[3], fpc_tft_ancho], [J4[3], fpc_ctp_ancho]])
      cajaK([f[0] - f[1] / 2, BOLSA[3] - 0.01, f[0] + f[1] / 2, MARCO[3] + 0.01], Z_MARCO_SI - 1, Z_PIEL);
    // pilotos de los pisapantallas (M3 autorroscante)
    for (t = PISA_TORRETAS) enK(t[0], t[1], Z_PISA_SUP - 0.01) cylinder(d = m3_piloto, h = min(tornillo_pisa_largo - pisapantalla_e + 1, Z_PIEL - Z_PISA_SUP), $fn = fn_peq);
    // RESET: agujero para clip
    enK(RESET[0], RESET[1], reset_tubo_hasta - 1) cylinder(d = clip_d, h = ZF, $fn = fn_peq);
    // BOOT: guía cuadrada y agujero para clip
    lb = boot_varilla + 2 * holgura;
    enK(BOOT[0], boot_varilla_y, Z_TUBO_BOOT - 1) translate([-lb / 2, -lb / 2, 0]) cube([lb, lb, Z_PIEL - Z_TUBO_BOOT + 1]);
    enK(BOOT[0], boot_varilla_y, Z_PIEL - 1) cylinder(d = clip_d, h = piel + 2, $fn = fn_peq);
  }
  // Agujeros de los capuchones
  for (b = BOTONES) let (c = centro(b[0]), t = tipo_cap(b[1])) if (en_pieza(p, c[0], 8))
    enK(c[0], c[1], CAP_Z_TUBO - 1) linear_extrude(ZF - CAP_Z_TUBO + 2) forma_cap(t[1], t[2], holgura);
  // Torretas: inserto térmico o piloto autorroscante, y paso del tornillo
  for (h = PCB_AGUJEROS) if (en_pieza(p, h[0], torreta_d / 2)) enK(h[0], h[1], 0) {
    if (fijacion_pcb == "inserto") {
      translate([0, 0, -0.1]) cylinder(d = inserto_d, h = inserto_l + 0.1, $fn = fn_peq);
      translate([0, 0, -0.1]) cylinder(d1 = inserto_d + 0.8, d2 = inserto_d, h = 0.5, $fn = fn_peq);
    } else
      translate([0, 0, -0.1]) cylinder(d = m3_piloto, h = inserto_l + 0.1, $fn = fn_peq);
    cylinder(d = 3.0, h = Z_TRASERA + m3_cabeza_h + tornillo_largo + 0.8 - 0, $fn = fn_peq);
  }
  // Joysticks: hueco del stick (con chaflán) y pilotos de los tornillos
  for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) if (en_pieza(p, j[0][0], 15)) {
    enK(j[0][0], j[0][1], Z_PIEL - 1) cylinder(d = joy_agujero_d, h = piel + 2, $fn = fn * 2);
    enK(j[0][0], j[0][1], ZF - 1.0) cylinder(d1 = joy_agujero_d, d2 = joy_agujero_d + 2.02, h = 1.01, $fn = fn * 2);
    for (t = joy_tornillos(j[0], j[1])) enK(t[0], t[1], JOY_Z_BASE)
      cylinder(d = joy_piloto_d, h = joy_base_e + 5.5, $fn = 12);
  }
  // Rejilla del altavoz
  if (en_pieza(p, altavoz_pos[0], altavoz_d / 2 + 3))
    for (q = rejilla_puntos()) enK(altavoz_pos[0] + q[0], altavoz_pos[1] + q[1], Z_PIEL - 1)
      cylinder(d = rejilla_agujero, h = piel + 2, $fn = 12);
  // LED
  let (d2 = centro("D2")) if (en_pieza(p, d2[0], 4))
    enK(d2[0], d2[1], Z_LED0 - 1) cylinder(d = led_agujero_d, h = (led_tipo == "ventana" ? ZF - led_ventana_e : ZF + 1) - Z_LED0 + 1, $fn = fn_peq);
  // USB-C
  if (en_pieza(p, USB_X, USB_HUECO[0])) hueco_usb();
}

module hueco_usb() {
  translate([USB_X, -(CAJA_CAV[3] - 2), usb_z]) rotate([90, 0, 0]) linear_extrude(pared + 5)
    offset(r = usb_funda_radio + holgura, $fn = fn_peq * 2) square(usb_funda - [2, 2] * usb_funda_radio, center = true);
}

function rejilla_puntos() = let (n = ceil(rejilla_d / rejilla_paso) + 1)
  [for (i = [-n:n], j = [-n:n]) let (x = (i + (j % 2 == 0 ? 0 : 0.5)) * rejilla_paso, y = j * rejilla_paso * 0.866)
    if (sqrt(x * x + y * y) <= rejilla_d / 2 - rejilla_agujero / 2) [x, y]];

// =====================================================================
//  Uniones
// =====================================================================
module region_2d(p) offset(delta = -holgura_union) polygon(Kpts(region(p)));
module region_3d(p) translate([0, 0, Z_TRASERA - 5]) linear_extrude(ZF - Z_TRASERA + 10) region_2d(p);

// Nervio a lo largo de las caras de unión (solo dentro de la cavidad)
module nervios_union(p, t, z0, z1) {
  translate([0, 0, z0]) linear_extrude(z1 - z0) intersection() {
    difference() { region_2d(p); offset(delta = -t) region_2d(p); }
    rrectK(CAJA_CAV, R_CAV);
  }
}

module refuerzos_union_frontal(p) {
  // en la central el nervio termina sobre los pisapantallas; los bloques de pernos y colas llegan más abajo
  nervios_union(p, p == "frontal_central" ? nervio_e_central : nervio_e, p == "frontal_central" ? Z_MARCO_SI : Z_NERVIO, Z_PIEL + 0.01);
  // bloques de los pernos
  for (pr = PERNOS) let (g = perno_geo(pr), yy = pr[2], w = bloque_perno[1]) {
    if (p == (pr[3] < 0 ? pr[4] : pr[5])) cajaK([min(g[0], g[1]), yy - w / 2, max(g[0], g[1]), yy + w / 2], Z_NERVIO, Z_PIEL + 0.01);
    if (p == (pr[3] < 0 ? pr[5] : pr[4])) cajaK([min(g[2], g[3]), yy - w / 2, max(g[2], g[3]), yy + w / 2], Z_NERVIO, Z_PIEL + 0.01);
  }
  // refuerzo alrededor de las hembras de las colas
  for (c = COLAS) if (c[3] == p && c[7]) let (x0 = c[0] + c[4] * holgura_union)
    cajaK([min(x0, x0 + c[4] * (cola_largo + holgura + 2.5)), c[1] - cola_punta / 2 - 2.5,
           max(x0, x0 + c[4] * (cola_largo + holgura + 2.5)), c[1] + cola_punta / 2 + 2.5], Z_NERVIO, Z_PIEL + 0.01);
}

module refuerzos_union_trasera(p) {
  nervios_union(p, tira_trasera_e, Z_SUELO_INT - 0.01, PCB_BOT - 0.3);
  for (c = COLAS) if (c[3] == p && !c[7]) let (x0 = c[0] + c[4] * holgura_union)
    cajaK([min(x0, x0 + c[4] * (cola_largo + holgura + 3)), c[1] - cola_punta / 2 - 3,
           max(x0, x0 + c[4] * (cola_largo + holgura + 3)), c[1] + cola_punta / 2 + 3], Z_SUELO_INT - 0.01, PCB_BOT - 0.3);
}

// Machos de las colas de milano (sobresalen de la pieza hacia la vecina)
module machos_union(p) {
  for (c = COLAS) if (c[2] == p) let (xf = c[0] - c[4] * holgura_union) {
    difference() {
      translate([xf, -c[1], c[5]]) linear_extrude(c[6] - c[5]) scale([c[4], 1]) cola_2d(cola_largo, cola_cuello, cola_punta);
      // cuña a 45° en el lado de la piel: se imprime boca abajo sin soportes
      if (c[7]) translate([0, -c[1], 0]) rotate([90, 0, 0]) linear_extrude(cola_punta + 2, center = true)
        polygon([[xf, c[6]], [xf + c[4] * (cola_largo + 1), c[6] - cola_largo - 1], [xf + c[4] * (cola_largo + 1), c[6] + 1], [xf, c[6] + 1]]);
    }
  }
}

module hembras_union(p) {
  for (c = COLAS) if (c[3] == p) let (xf = c[0] - c[4] * holgura_union)
    translate([xf, -c[1], c[5] - 1]) linear_extrude(c[6] - c[5] + (c[7] ? 1 : 1.01))
      scale([c[4], 1]) cola_2d(cola_largo, cola_cuello, cola_punta, holgura);
}

module tornillos_union(p) {
  for (pr = PERNOS) if (p == pr[4] || p == pr[5]) let (g = perno_geo(pr), s = pr[3], yy = pr[2]) {
    // paso del tornillo
    translate([(g[4] + g[5]) / 2 + s * 0.2, -yy, Z_PERNO]) lagrima_x(m3_paso, abs(g[4] - g[5]) + 1.0, -1);
    // alojamiento de la cabeza
    if (pr[9] > 0) translate([(g[1] + g[4]) / 2, -yy, Z_PERNO]) lagrima_x(m3_cabeza_d, abs(g[1] - g[4]) + 0.4, -1);
    // ranura de la tuerca, abierta hacia la placa para meterla desde dentro
    hx = abs(g[7] - g[6]);
    translate([min(g[6], g[7]) - 0.1, -yy - (m3_tuerca + 0.3) / 2, Z_NERVIO - 1])
      cube([hx + 0.2, m3_tuerca + 0.3, Z_PERNO - Z_NERVIO + 1 + m3_tuerca / cos(30) / 2 + 0.2]);
  }
}

// =====================================================================
//  Piezas frontales y traseras
// =====================================================================
module frontal(p) {
  difference() {
    union() {
      intersection() {
        difference() {
          union() { cascaron_frontal(); rasgos_frontal(p); refuerzos_union_frontal(p); }
          huecos_frontal(p);
        }
        region_3d(p);
      }
      machos_union(p);
    }
    hembras_union(p);
    tornillos_union(p);
  }
}

module rasgos_trasera(p) {
  for (h = PCB_AGUJEROS) if (en_pieza(p, h[0], pata_d / 2))
    enK(h[0], h[1], Z_SUELO_INT - 0.01) cylinder(d = pata_d, h = PCB_BOT - Z_SUELO_INT + 0.01, $fn = fn_peq * 2);
}

module huecos_trasera(p) {
  for (h = PCB_AGUJEROS) if (en_pieza(p, h[0], pata_d / 2)) enK(h[0], h[1], 0) {
    translate([0, 0, Z_TRASERA - 1]) cylinder(d = m3_paso, h = 20, $fn = fn_peq);
    translate([0, 0, Z_TRASERA - 1]) cylinder(d = m3_cabeza_d, h = m3_cabeza_h + 1, $fn = fn_peq * 2);
  }
  if (en_pieza(p, USB_X, USB_HUECO[0])) hueco_usb();
}

module trasera(p) {
  difference() {
    union() {
      intersection() {
        difference() {
          union() { cascaron_trasero(); rasgos_trasera(p); refuerzos_union_trasera(p); }
          huecos_trasera(p);
        }
        region_3d(p);
      }
      machos_union(p);
    }
    hembras_union(p);
  }
}

// =====================================================================
//  Piezas pequeñas
// =====================================================================
// Capuchón en posición de montaje (reposo: el pie toca el vástago)
module capuchon(b) {
  c = centro(b[0]);
  t = tipo_cap(b[1]);
  z_top = ZF + t[3];
  enK(c[0], c[1], 0) difference() {
    union() {
      // cuerpo guiado con chaflán arriba
      hull() {
        translate([0, 0, CAP_Z_BRIDA]) linear_extrude(z_top - 0.6 - CAP_Z_BRIDA) forma_cap(t[1], t[2]);
        translate([0, 0, z_top - 0.01]) linear_extrude(0.01) forma_cap(t[1], t[2], -0.6);
      }
      // brida-tope: cono de 45° (imprimible boca abajo) y parte recta
      hull() {
        translate([0, 0, CAP_Z_BRIDA]) linear_extrude(0.01) forma_cap(t[1], t[2]);
        translate([0, 0, CAP_Z_BRIDA - cap_brida - cap_brida_e]) linear_extrude(cap_brida_e) forma_cap(t[1], t[2], cap_brida);
      }
      // pie hasta el vástago
      translate([0, 0, sw_alto]) cylinder(d = cap_pie_d, h = CAP_Z_BRIDA - cap_brida - cap_brida_e - sw_alto + 0.01, $fn = fn_peq);
    }
    translate([0, 0, z_top - grabado_prof]) linear_extrude(grabado_prof + 0.1)
      simbolo(b[2], min(t[2][0], t[2][1]) - 1.2);
  }
}

// Barras que sujetan la pantalla por detrás (izquierda: 0, derecha: 1)
module pisapantalla(i) {
  x = PISA_X[i];
  difference() {
    union() {
      cajaK([x - pisapantalla_ancho / 2, PISA_Y[0], x + pisapantalla_ancho / 2, PISA_Y[1]], Z_PISA_INF, Z_PISA_SUP);
      for (y = PISA_Y) enK(x, y, Z_PISA_INF) cylinder(d = 7, h = pisapantalla_e, $fn = fn_peq * 2);
    }
    for (y = PISA_Y) enK(x, y, Z_PISA_INF - 1) cylinder(d = m3_paso, h = pisapantalla_e + 2, $fn = fn_peq);
  }
}

// Empujador en L para pulsar BOOT (SW16, bajo la pantalla) con un clip
module empujador_boot() {
  v = boot_varilla;
  enK(BOOT[0], 0, 0) {
    // varilla vertical dentro del tubo
    translate([-v / 2, -boot_varilla_y - v / 2, boot_brazo_z + boot_brazo_alto - 0.01])
      cube([v, v, Z_PIEL - cap_juego - (boot_brazo_z + boot_brazo_alto) + 0.01]);
    // brazo bajo la pantalla
    translate([-v / 2, -BOOT[1] - v / 2, boot_brazo_z]) cube([v, BOOT[1] - boot_varilla_y + v, boot_brazo_alto]);
    // dedo sobre el vástago de BOOT
    translate([-v / 2, -BOOT[1] - v / 2, sw_alto]) cube([v, v, boot_brazo_z - sw_alto + 0.01]);
  }
}

// Tornillos (para renders y comprobación de choques con componentes)
module tornillo_m3(l, cabeza = true) {
  cylinder(d = 3, h = l, $fn = 16);
  if (cabeza) translate([0, 0, -m3_cabeza_h]) cylinder(d = 5.5, h = m3_cabeza_h, $fn = 24);
}

module tornilleria() {
  // placa: de la trasera a la torreta frontal
  for (h = PCB_AGUJEROS) enK(h[0], h[1], Z_TRASERA + m3_cabeza_h) tornillo_m3(tornillo_largo);
  // uniones frontales
  for (pr = PERNOS) let (g = perno_geo(pr), s = pr[3])
    translate([g[4], -pr[2], Z_PERNO]) rotate([0, -s * 90, 0]) tornillo_m3(tornillo_largo);
  // pisapantallas
  for (t = PISA_TORRETAS) enK(t[0], t[1], Z_PISA_INF) tornillo_m3(tornillo_pisa_largo);
}

module tuercas() {
  for (pr = PERNOS) let (g = perno_geo(pr))
    translate([(g[6] + g[7]) / 2, -pr[2], Z_PERNO]) rotate([0, 90, 0]) rotate([0, 0, 30])
      linear_extrude(m3_tuerca_e, center = true) difference() { hexagono(m3_tuerca); circle(d = 3, $fn = 12); }
}
