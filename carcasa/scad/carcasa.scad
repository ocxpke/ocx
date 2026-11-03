// =====================================================================
//  OCX - carcasa de apoyo para la consola portátil OCX
//  Punto de entrada. Elige la pieza con  -D 'pieza="frontal_central"'
//  (o desde el Customizer de OpenSCAD).
//
//  pieza = "ensamblaje" | "explosionado" | "datos" | una de PIEZAS
//  modo  = "impresion" (girada y apoyada en la cama) | "montaje"
// =====================================================================

include <parametros.scad>
include <utilidades.scad>
include <componentes.scad>
include <piezas.scad>

pieza = "ensamblaje";
modo = "impresion";
con_electronica = true;   // en ensamblaje/explosionado, dibuja placa y componentes
explosion = 35;           // separación del explosionado (mm)

CAP_PIEZAS = [for (b = BOTONES) str("capuchon_", b[0])];
PIEZAS = concat(["frontal_izquierda", "frontal_central", "frontal_derecha",
                 "trasera_izquierda", "trasera_derecha",
                 "pisapantalla_izq", "pisapantalla_der", "empujador_boot"], CAP_PIEZAS);

function boton_de(n) = BOTONES[search([n], [for (b = BOTONES) str("capuchon_", b[0])], 1, 0)[0]];
function es_cap(n) = en_lista(n, CAP_PIEZAS);

module pieza_montaje(n) {
  if (n == "frontal_izquierda" || n == "frontal_central" || n == "frontal_derecha") frontal(n);
  else if (n == "trasera_izquierda" || n == "trasera_derecha") trasera(n);
  else if (n == "pisapantalla_izq") pisapantalla(0);
  else if (n == "pisapantalla_der") pisapantalla(1);
  else if (n == "empujador_boot") empujador_boot();
  else if (es_cap(n)) capuchon(boton_de(n));
  else assert(false, str("Pieza desconocida: ", n));
}

// Giro a la orientación de impresión (cara apoyada en z = 0)
module pieza_impresion(n) {
  if (n == "frontal_izquierda" || n == "frontal_central" || n == "frontal_derecha")
    translate([0, 0, ZF]) rotate([180, 0, 0]) pieza_montaje(n);       // boca abajo
  else if (n == "trasera_izquierda" || n == "trasera_derecha")
    translate([0, 0, -Z_TRASERA]) pieza_montaje(n);                    // apoyada en la tapa
  else if (n == "pisapantalla_izq" || n == "pisapantalla_der")
    translate([0, 0, -Z_PISA_INF]) pieza_montaje(n);
  else if (n == "empujador_boot")
    translate([0, 0, boot_varilla / 2]) rotate([0, 90, 0]) translate([-BOOT[0], 0, 0]) pieza_montaje(n);  // tumbado
  else if (es_cap(n)) let (b = boton_de(n), t = tipo_cap(b[1]), c = centro(b[0]))
    translate([0, 0, ZF + t[3]]) rotate([180, 0, 0]) translate([-c[0], c[1], 0]) pieza_montaje(n); // boca abajo
}

// Probeta de ajuste (~20 min): guía de capuchón ABXY, torreta para inserto y cola de milano
// hembra (A) más el macho (B). Ya está en orientación de impresión (boca abajo, como las frontales).
module probeta() {
  t = tipo_cap("abxy");
  difference() {
    union() {
      translate([2, 2, 0]) linear_extrude(piel) offset(r = 2, $fn = 24) square([40, 24]);
      translate([11, 14, 0]) linear_extrude(piel + cap_tubo_largo) forma_cap(t[1], t[2], holgura + pared_interna);
      translate([25, 14, 0]) cylinder(d = torreta_d, h = piel + 8, $fn = fn_peq * 2);
      translate([34, 4, 0]) cube([10, 20, piel + nervio_prof]);
    }
    translate([11, 14, -1]) linear_extrude(piel + cap_tubo_largo + 2) forma_cap(t[1], t[2], holgura);
    translate([25, 14, piel + 8 - inserto_l]) cylinder(d = inserto_d, h = inserto_l + 1, $fn = fn_peq);
    translate([44.01, 14, piel]) scale([-1, 1]) linear_extrude(nervio_prof + 1) cola_2d(cola_largo, cola_cuello, cola_punta, holgura);
  }
  // macho: cara de unión en x = 52, la cola crece hacia -X con la cuña de 45° por debajo
  translate([52, 0, 0]) {
    cube([12, 28, piel]);
    cube([3, 28, piel + nervio_prof]);
    difference() {
      translate([0, 14, piel]) scale([-1, 1]) linear_extrude(nervio_prof) cola_2d(cola_largo, cola_cuello, cola_punta);
      translate([0, 14, 0]) rotate([90, 0, 0]) linear_extrude(cola_punta + 2, center = true)
        polygon([[0.01, piel], [-cola_largo - 1, piel + cola_largo + 1], [-cola_largo - 1, piel - 1], [0.01, piel - 1]]);
    }
  }
}

// Todos los capuchones en una sola impresión (boca abajo, separados 18 mm)
module bandeja_capuchones() {
  for (i = [0:len(CAP_PIEZAS) - 1]) translate([(i % 4) * 18, -floor(i / 4) * 18, 0]) pieza_impresion(CAP_PIEZAS[i]);
}

COLOR_PIEZA = [
  ["frontal_izquierda", [0.93, 0.93, 0.95]], ["frontal_central", [0.85, 0.87, 0.92]],
  ["frontal_derecha", [0.93, 0.93, 0.95]], ["trasera_izquierda", [0.35, 0.45, 0.6]],
  ["trasera_derecha", [0.42, 0.52, 0.68]],
];
function color_pieza(n) = let (i = search([n], COLOR_PIEZA, 1, 0)[0]) i == undef ? [0.9, 0.3, 0.2] : COLOR_PIEZA[i][1];

// Desplazamiento del explosionado
function despl(n) =
  (n == "frontal_izquierda" || n == "frontal_central" || n == "frontal_derecha") ? [0, 0, 2 * explosion] :
  (n == "trasera_izquierda" || n == "trasera_derecha") ? [0, 0, -explosion] :
  (n == "pisapantalla_izq" || n == "pisapantalla_der") ? [0, 0, 1.3 * explosion] :
  n == "empujador_boot" ? [0, 0, 1.0 * explosion] :
  es_cap(n) ? [0, 0, 3.2 * explosion] : [0, 0, 0];

module montaje(e = 0) {
  for (n = PIEZAS) translate(e * despl(n) / max(explosion, 0.001)) color(color_pieza(n)) pieza_montaje(n);
  if (con_electronica) translate([0, 0, e > 0 ? 0 : 0]) {
    electronica(con_pantalla = false);
    translate(e > 0 ? [0, 0, 1.6 * e] : [0, 0, 0]) pantalla();
  }
}

// ---------------------------------------------------------------------
if (pieza == "ensamblaje") montaje(0);
else if (pieza == "explosionado") montaje(explosion);
else if (pieza == "datos") {
  // Datos para scripts/comprobar.py
  echo(DATOS = [
    ["ZF", ZF], ["Z_PIEL", Z_PIEL], ["Z_TRASERA", Z_TRASERA], ["Z_SUELO_INT", Z_SUELO_INT],
    ["Z_PANTALLA_TRAS", Z_PANTALLA_TRAS], ["PIEZAS", PIEZAS],
    ["zonas", zonas_prohibidas()],
    ["botones", [for (b = BOTONES) let (c = centro(b[0]), t = tipo_cap(b[1])) [str("capuchon_", b[0]), b[0], c, ZF + t[3]]]],
    ["cap_juego", cap_juego], ["sw_recorrido", sw_recorrido], ["sw_alto", sw_alto], ["CAP_Z_TUBO", CAP_Z_TUBO],
    ["joysticks", [[joy_izq, joy_giro_izq, "frontal_izquierda"], [joy_der, joy_giro_der, "frontal_derecha"]]],
    ["joy", [JOY_Z_BASE, joy_pivote, joy_total_alto, joy_cap_d, joy_cap_alto, joy_eje_d, joy_inclinacion]],
    ["boot", [BOOT, boot_varilla_y]],
    ["limite_pieza", 135],
    ["pared", pared], ["piel", piel], ["suelo", suelo], ["holgura", holgura],
    ["pantalla", [PANT, ZF]], ["CAJA_EXT", CAJA_EXT],
    // tornillos: [nombre, punto de asiento de la cabeza (coord. OpenSCAD), punta, diámetro, tipo]
    ["tornillos", concat(
      [for (h = PCB_AGUJEROS) [str("placa_", h[0], "_", h[1]), [h[0], -h[1], Z_TRASERA + m3_cabeza_h],
                                [h[0], -h[1], Z_TRASERA + m3_cabeza_h + tornillo_largo], 3.0, "placa"]],
      [for (pr = PERNOS) let (g = perno_geo(pr)) [str("union_", pr[0]), [g[4], -pr[2], Z_PERNO], [g[5], -pr[2], Z_PERNO], 3.0, "union"]],
      [for (t = PISA_TORRETAS) [str("pisapantalla_", t[0], "_", t[1]), [t[0], -t[1], Z_PISA_INF],
                                 [t[0], -t[1], Z_PISA_INF + tornillo_pisa_largo], 3.0, "pisapantalla"]])],
    ["pernos", [for (pr = PERNOS) let (g = perno_geo(pr)) [pr[0], g]]],
    ["inserto_l", inserto_l], ["fijacion_pcb", fijacion_pcb], ["tornillo_largo", tornillo_largo],
    ["empujador", [BOOT, boot_varilla_y, boot_brazo_z, Z_PIEL - cap_juego]],
  ]);
  cube(1);
}
else if (pieza == "bandeja_capuchones") bandeja_capuchones();
else if (pieza == "probeta") probeta();
else if (modo == "montaje") pieza_montaje(pieza);
else pieza_impresion(pieza);
