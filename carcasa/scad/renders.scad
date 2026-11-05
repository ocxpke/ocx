// =====================================================================
//  OCX - carcasa · escenas para los renders (las usa scripts/renders.py)
//  Importa las piezas ya calculadas de build/montaje/ y dibuja la
//  electrónica como fantasmas de colores.
// =====================================================================

include <parametros.scad>
include <utilidades.scad>
include <componentes.scad>
include <piezas.scad>

escena = "montado";   // montado | trasera | explosionado | seccion | seccion_boot | seccion_joy | seccion_tft | pieza | paso
nombre = "frontal_central";
paso = 1;

M = "../build/montaje/";
GRIS = [0.92, 0.92, 0.94];
GRIS_C = [0.84, 0.86, 0.91];
AZUL = [0.55, 0.65, 0.8];
NUEVO = [1.0, 0.55, 0.12];
OSCURO = [0.22, 0.22, 0.24];

FRONTALES = ["frontal_izquierda", "frontal_central", "frontal_derecha"];
TRASERAS = ["trasera_izquierda", "trasera_derecha"];
CAPS = [for (b = BOTONES) str("capuchon_", b[0])];
PEQ = ["pisapantalla_izq", "pisapantalla_der", "empujador_boot"];

module stl(n) import(str(M, n, ".stl"), convexity = 6);
module pieza_c(n, c) color(c) stl(n);

function color_base(n) =
  n == "frontal_central" ? GRIS_C :
  en_lista(n, FRONTALES) ? GRIS :
  n == "trasera_izquierda" ? AZUL : n == "trasera_derecha" ? AZUL * 1.12 :
  n == "empujador_boot" || n == "pisapantalla_izq" || n == "pisapantalla_der" ? [0.95, 0.6, 0.2] : OSCURO;

// color de un STL de stl/ por su nombre (01_frontal_izquierda...)
function color_pieza_stl(f) =
  let (s = search("_", f)[0], n = f == "" ? "" : chr([for (i = [s + 1:len(f) - 1]) ord(f[i])]))
  en_lista(n, concat(FRONTALES, TRASERAS)) ? color_base(n) : en_lista(n, PEQ) ? color_base(n) :
  n == "probeta_ajustes" ? GRIS : [0.3, 0.3, 0.33];

// Un capuchón de cada tipo, cortado por su eje, con su tubo guía, el pulsador y la placa
module escena_capuchones() {
  refs = ["SW2", "SW13", "SW1", "SW8"];
  for (i = [0:len(refs) - 1]) let (c = centro(refs[i])) translate([i * 24 - c[0], c[1], 0]) {
    color(GRIS) import(str("../build/corte/caps/", refs[i], "_frontal.stl"), convexity = 6);
    color(NUEVO) import(str("../build/corte/caps/", refs[i], "_cap.stl"), convexity = 6);
    intersection() {
      union() {
        color([0.15, 0.15, 0.15]) enK(c[0], c[1], 0) translate([-3, -3, 0]) cube([6, 6, sw_alto_cuerpo]);
        color([0.85, 0.85, 0.85]) enK(c[0], c[1], 0) cylinder(d = sw_vastago_d, h = sw_alto, $fn = 24);
        color([0.05, 0.4, 0.2]) enK(c[0], c[1], -PCB_GROSOR) translate([-11, -11, 0]) cube([22, 22, PCB_GROSOR]);
      }
      enK(c[0], c[1], -10) translate([-20, 0.05, 0]) cube([40, 20, 60]);   // apenas detrás del corte: evita parpadeo
    }
  }
}

module todas(lista, c = undef) for (n = lista) pieza_c(n, c == undef ? color_base(n) : c);

module tornillos_c() color([0.55, 0.55, 0.6]) tornilleria();
module tuercas_c() color([0.6, 0.6, 0.65]) tuercas();
module insertos_c() color([0.85, 0.65, 0.25]) for (h = PCB_AGUJEROS) enK(h[0], h[1], 0)
  difference() { cylinder(d = 4.6, h = 5.7, $fn = 24); translate([0, 0, -1]) cylinder(d = 3, h = 8, $fn = 16); }

module electronica_sin_pantalla() electronica(con_pantalla = false);

// ---------------------------------------------------------------------
module escena_montado() {
  todas(FRONTALES); todas(TRASERAS); todas(CAPS);
  for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
  pantalla();
  color([0.05, 0.4, 0.2]) placa();
}

module escena_explosionado(e = 28) {
  translate([0, 0, 3.4 * e]) todas(CAPS);
  translate([0, 0, 2.4 * e]) todas(FRONTALES);
  translate([0, 0, 1.75 * e]) { pantalla(); fpc_pantalla(con_ffc = false); }
  translate([0, 0, 1.45 * e]) { todas(PEQ); }
  translate([0, 0, 1.1 * e]) for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
  translate([0, 0, 1.1 * e]) color([0.55, 0.55, 0.6]) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
  electronica_sin_pantalla();
  translate([0, 0, -1.2 * e]) todas(TRASERAS);
  translate([0, 0, -2.2 * e]) color([0.55, 0.55, 0.6]) for (h = PCB_AGUJEROS) enK(h[0], h[1], Z_TRASERA + m3_cabeza_h) tornillo_m3(tornillo_largo);
}

// Cortes: las piezas impresas vienen ya cortadas de build/corte/ (scripts/renders.py)
// para que la cara de corte conserve su color. La electrónica se corta aquí; como la vista previa
// pinta todas las caras de corte de un mismo color, cada parte lleva además una "tapa": su sección
// (projection con cut = true) como una lámina fina de su color justo delante del plano de corte.
// plano = ["x", x0] (se mira hacia +X) o ["y", y0] (se mira hacia +Y), en coordenadas OpenSCAD.
module tapa(c, plano) color(c)
  if (plano[0] == "x")
    translate([plano[1], 0, 0]) rotate([0, -90, 0]) linear_extrude(0.02)
      projection(cut = true) rotate([0, 90, 0]) translate([-plano[1], 0, 0]) children();
  else
    translate([0, plano[1], 0]) rotate([-90, 0, 0]) translate([0, 0, -0.02]) linear_extrude(0.02)
      projection(cut = true) rotate([90, 0, 0]) translate([0, -plano[1], 0]) children();
module cortado(c, cubo, plano) {
  intersection() { color(c) children(); cubo_corte(cubo); }
  tapa(c, plano) children();
}
module corta(clave, cubo, plano) {
  for (n = concat(FRONTALES, TRASERAS, CAPS, PEQ)) color(color_base(n)) import(str("../build/corte/", clave, "/", n, ".stl"), convexity = 6);
  cortado([0.05, 0.4, 0.2], cubo, plano) placa();
  for (g = ["pulsador", "vastago", "smd", "zocalo", "conector", "tht"])
    cortado(color_de(g), cubo, plano) for (z = concat(zonas_pcb(), zonas_tht())) if (z[2] == g) dibuja_zona_c(z);
  cortado([0.1, 0.25, 0.55], cubo, plano) cajaK(DEVKIT, DEVKIT_Z0, DEVKIT_Z0 + devkit_pcb_e);
  cortado([0.75, 0.75, 0.78], cubo, plano) cajaK([DEVKIT_CX - devkit_modulo[0] / 2, DEVKIT_PUNTA + devkit_antena_largo,
                                                  DEVKIT_CX + devkit_modulo[0] / 2, DEVKIT_PUNTA + devkit_modulo[1]],
                                                 DEVKIT_Z0 + devkit_pcb_e, devkit_alto_total);
  cortado([0.1, 0.1, 0.12], cubo, plano) cajaK(ANTENA, DEVKIT_Z0 + devkit_pcb_e, DEVKIT_Z0 + devkit_pcb_e + 0.8);
  cortado([0.08, 0.08, 0.1], cubo, plano) pantalla();
  cortado(AMBAR, cubo, plano) { fpc_tft_flexible(); fpc_tactil(); }
  cortado(PLATA, cubo, plano) fpc_tft_blindaje();
  cortado(AZUL_REFUERZO, cubo, plano) fpc_tft_refuerzo();
  cortado(VERDE_ADAPTADOR, cubo, plano) adaptador_tft_placa();
  cortado(NEGRO_CONECTOR, cubo, plano) adaptador_tft_conectores();
  cortado(COLOR_FFC, cubo, plano) ffc_tft();
  cortado([0.85, 0.6, 0.2], cubo, plano) cables_joystick();
  cortado([0.95, 0.85, 0.3], cubo, plano) tacos_joystick();
  cortado([0.55, 0.55, 0.6], cubo, plano) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
  cortado([0.25, 0.25, 0.27], cubo, plano) for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
  cortado([0.55, 0.55, 0.6], cubo, plano) tornilleria();
}
module cubo_corte(c) translate(c[0]) cube(c[1]);

module escena_seccion() corta("y4975", [[-10, -49.75 + 0.05, -50], [300, 80, 100]], ["y", -49.75 + 0.05]);  // cruceta, DevKit y ABXY
module escena_seccion_boot() corta("x1746", [[174.6 + 0.05, -200, -50], [100, 220, 100]], ["x", 174.6 + 0.05]);  // empujador de BOOT
// Rótulo en el plano del corte (plano YZ), mirando hacia -X, delante de la cara cortada
module rotulo_corte(t, y, z, x, tam = 2.6, c = [0.15, 0.15, 0.18]) color(c)
  multmatrix([[0, 0, -1, x], [-1, 0, 0, -y], [0, 1, 0, z], [0, 0, 0, 1]]) linear_extrude(0.3)
    text(t, size = tam, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
module escena_seccion_joy() {     // joystick izquierdo y su cable
  corta("x375", [[37.5 + 0.05, -200, -50], [30, 220, 100]], ["x", 37.5 + 0.05]);
  x = 36.3;
  rotulo_corte("J6", fab("J6")[1] + 1.5, 4.6, x);
  rotulo_corte("cable", 85.5, 10.5, x);
  rotulo_corte("taco de espuma", 103.5, 6.5, x, 1.8);
  rotulo_corte("joystick", joy_izq[1] + 15.5, ZF + 2.4, x);
  rotulo_corte("altavoz", altavoz_pos[1], ZF + 2.4, x);
}
module escena_seccion_tft() {     // cola de la pantalla y alargador
  corta("x10874", [[108.74 + 0.05, -200, -50], [16, 220, 100]], ["x", 108.74 + 0.05]);
  x = 107.5;
  rotulo_corte("pantalla", 50, (Z_PANTALLA_TRAS + Z_PIEL) / 2, x, 2.6, [0.92, 0.92, 0.94]);
  rotulo_corte("parte ancha (no se dobla)", (TFT_ANCHA_Y0 + TFT_ANCHA_Y1) / 2, 13.4, x, 2.0);
  rotulo_corte("cola", (TFT_COLA_Y0 + TFT_ANCHA_Y0) / 2, 13.4, x, 2.0);
  rotulo_corte("adaptador", (AD[1] + AD[3]) / 2, 11.6, x, 2.0);
  rotulo_corte("FFC de 40 vías", 82, FFC_Z_TRAMO - 2.2, x, 2.0);
  rotulo_corte("J1", fab("J1")[1] - 1.5, 4.4, x, 2.4);
}

// Joysticks pegados a la placa con sus tacos y con el cable puesto
module joysticks_en_placa(c = undef) {
  for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) if (c == undef) joystick(j[0], j[1]); else color(c) joystick(j[0], j[1]);
  cables_joystick();
  tacos_joystick();
}

// Montaje boca abajo, como se hace sobre la mesa: giro de 180° alrededor de X
module boca_abajo() translate([0, 0, ZF]) rotate([180, 0, 0]) children();

module escena_paso(k) {
  if (k == 1) boca_abajo() {
    pieza_c("frontal_central", GRIS_C);
    translate([-14, 0, 0]) pieza_c("frontal_izquierda", GRIS);
    translate([14, 0, 0]) pieza_c("frontal_derecha", GRIS);
    color(NUEVO) for (h = PCB_AGUJEROS) translate([h[0] < union_A_x + 1 ? -14 : h[0] > union_B_x ? 14 : 0, 0, -7]) enK(h[0], h[1], 0)
      difference() { cylinder(d = 4.6, h = 5.7, $fn = 24); translate([0, 0, -1]) cylinder(d = 3, h = 8, $fn = 16); }
  }
  if (k == 2) boca_abajo() {
    pieza_c("frontal_central", GRIS_C);
    translate([-14, 0, 0]) pieza_c("frontal_izquierda", NUEVO);
    translate([14, 0, 0]) pieza_c("frontal_derecha", NUEVO);
    tuercas_c();
    for (pr = PERNOS) let (g = perno_geo(pr), s = pr[3])
      translate([g[4] + s * 24, -pr[2], Z_PERNO]) color([0.55, 0.55, 0.6]) rotate([0, -s * 90, 0]) tornillo_m3(tornillo_largo);
  }
  if (k == 3) boca_abajo() { todas(FRONTALES); translate([0, 0, -8]) todas(CAPS, NUEVO); }
  if (k == 4) boca_abajo() {
    todas(FRONTALES); todas(CAPS);
    translate([0, 0, -10]) { pantalla(); fpc_pantalla(con_ffc = false); }
    translate([0, 0, -22]) { pieza_c("pisapantalla_izq", NUEVO); pieza_c("pisapantalla_der", NUEVO); }
    translate([0, 0, -38]) pieza_c("empujador_boot", NUEVO);
    translate([0, 0, -30]) color([0.55, 0.55, 0.6]) for (t = PISA_TORRETAS) enK(t[0], t[1], Z_PISA_INF) tornillo_m3(tornillo_pisa_largo);
  }
  if (k == 5) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla(); fpc_pantalla(con_ffc = false);
    translate([0, 0, -8]) for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) color(NUEVO) joystick(j[0], j[1]);
    translate([0, 0, -20]) tacos_joystick(NUEVO * 0.85);
  }
  if (k == 6) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla(); fpc_pantalla(con_ffc = false);
    for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
    tacos_joystick();
    translate([0, 0, -10]) color(NUEVO) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
  }
  if (k == 7) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla(); fpc_pantalla(con_ffc = false);
    color([0.55, 0.55, 0.6]) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
    // la placa de canto, girada sobre su borde inferior, con los joysticks pegados para conectar los cables
    translate([0, -PCB_BBOX[3] - 6, -2]) rotate([-70, 0, 0]) translate([0, PCB_BBOX[3], 0]) { placa_montada(); joysticks_en_placa(NUEVO); }
  }
  if (k == 8) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla(); fpc_pantalla();
    color([0.55, 0.55, 0.6]) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
    translate([0, 0, -16]) { placa_montada(); joysticks_en_placa(); }
  }
  if (k == 9) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla(); fpc_pantalla(); electronica_sin_pantalla(); tacos_joystick();
    translate([0, 0, -14]) { pieza_c("trasera_izquierda", NUEVO); translate([-6, 0, 0]) pieza_c("trasera_derecha", NUEVO * 0.9); }
    translate([0, 0, -30]) color([0.55, 0.55, 0.6]) for (h = PCB_AGUJEROS) enK(h[0], h[1], Z_TRASERA + m3_cabeza_h) tornillo_m3(tornillo_largo);
  }
  if (k == 10) escena_montado();
}

// Vista en planta con rótulos de los agujeros y botones
module rotulo(t, p, tam = 3.2) color([0.15, 0.15, 0.18]) enK(p[0], p[1], ZF + 4)
  linear_extrude(0.4) text(t, size = tam, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
module escena_planta() {
  escena_montado();
  rotulo("RESET", [RESET[0], RESET[1] - 5.5]);
  rotulo("BOOT", [BOOT[0], boot_varilla_y - 5.5]);
  rotulo("LED", [centro("D2")[0], centro("D2")[1] + 5.5]);
  rotulo("USB-C", [USB_X, CAJA_EXT[3] + 4]);
  rotulo("altavoz", [altavoz_pos[0] - 17.5, altavoz_pos[1]], 2.6);
  rotulo("L", [centro("SW1")[0] - 10, centro("SW1")[1]]);
  rotulo("R", [centro("SW15")[0] + 10, centro("SW15")[1]]);
  for (r = [["SW6", "SELECT"], ["SW7", "VOL-"], ["SW8", "VOL+"], ["SW9", "HOME"]])
    rotulo(r[1], [centro(r[0])[0], centro(r[0])[1] + 6.2], 2.2);
}

if (escena == "montado" || escena == "trasera") escena_montado();
else if (escena == "planta") escena_planta();
else if (escena == "explosionado") escena_explosionado();
else if (escena == "seccion") escena_seccion();
else if (escena == "seccion_boot") escena_seccion_boot();
else if (escena == "seccion_joy") escena_seccion_joy();
else if (escena == "seccion_tft") escena_seccion_tft();
else if (escena == "pieza") color(color_pieza_stl(nombre)) import(str("../stl/", nombre, ".stl"), convexity = 6);
else if (escena == "capuchones") escena_capuchones();
else if (escena == "paso") escena_paso(paso);
