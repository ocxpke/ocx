// =====================================================================
//  OCX - carcasa · escenas para los renders (las usa scripts/renders.py)
//  Importa las piezas ya calculadas de build/montaje/ y dibuja la
//  electrónica como fantasmas de colores.
// =====================================================================

include <parametros.scad>
include <utilidades.scad>
include <componentes.scad>
include <piezas.scad>

escena = "montado";   // montado | trasera | explosionado | seccion | pieza | paso
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
  translate([0, 0, 1.75 * e]) { pantalla(); }
  translate([0, 0, 1.45 * e]) { todas(PEQ); }
  translate([0, 0, 1.1 * e]) for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
  translate([0, 0, 1.1 * e]) color([0.55, 0.55, 0.6]) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
  electronica_sin_pantalla();
  translate([0, 0, -1.2 * e]) todas(TRASERAS);
  translate([0, 0, -2.2 * e]) color([0.55, 0.55, 0.6]) for (h = PCB_AGUJEROS) enK(h[0], h[1], Z_TRASERA + m3_cabeza_h) tornillo_m3(tornillo_largo);
}

// Cortes: las piezas impresas vienen ya cortadas de build/corte/ (scripts/renders.py)
// para que la cara de corte conserve su color; la electrónica se corta aquí.
module corta(clave, cubo) {
  for (n = concat(FRONTALES, TRASERAS, CAPS, PEQ)) color(color_base(n)) import(str("../build/corte/", clave, "/", n, ".stl"), convexity = 6);
  intersection() { union() { pantalla(); placa_montada(); }; cubo_corte(cubo); }
  intersection() { for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]); cubo_corte(cubo); }
  color([0.55, 0.55, 0.6]) intersection() { tornilleria(); cubo_corte(cubo); }
}
module cubo_corte(c) translate(c[0]) cube(c[1]);

module escena_seccion() corta("y4975", [[-10, -49.75 + 0.05, -50], [300, 80, 100]]);       // cruceta, DevKit y ABXY
module escena_seccion_boot() corta("x1746", [[174.6 + 0.05, -200, -50], [100, 220, 100]]);  // empujador de BOOT

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
    translate([0, 0, -10]) pantalla();
    translate([0, 0, -22]) { pieza_c("pisapantalla_izq", NUEVO); pieza_c("pisapantalla_der", NUEVO); }
    translate([0, 0, -38]) pieza_c("empujador_boot", NUEVO);
    translate([0, 0, -30]) color([0.55, 0.55, 0.6]) for (t = PISA_TORRETAS) enK(t[0], t[1], Z_PISA_INF) tornillo_m3(tornillo_pisa_largo);
  }
  if (k == 5) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla();
    translate([0, 0, -12]) for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) color(NUEVO) joystick(j[0], j[1]);
  }
  if (k == 6) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla();
    for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
    translate([0, 0, -10]) color(NUEVO) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
  }
  if (k == 7) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla();
    for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
    color([0.55, 0.55, 0.6]) enK(altavoz_pos[0], altavoz_pos[1], Z_PIEL - altavoz_alto) cylinder(d = altavoz_d, h = altavoz_alto, $fn = fn);
    // la placa de canto, girada sobre su borde inferior, para conectar los FPC
    translate([0, -PCB_BBOX[3] - 6, -2]) rotate([-70, 0, 0]) translate([0, PCB_BBOX[3], 0]) placa_montada();
  }
  if (k == 8) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla();
    for (j = [[joy_izq, joy_giro_izq], [joy_der, joy_giro_der]]) joystick(j[0], j[1]);
    translate([0, 0, -16]) placa_montada();
  }
  if (k == 9) boca_abajo() {
    todas(FRONTALES); todas(CAPS); todas(PEQ); pantalla(); electronica_sin_pantalla();
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
  rotulo("altavoz", [altavoz_pos[0], altavoz_pos[1] + 13.5]);
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
else if (escena == "pieza") color(color_pieza_stl(nombre)) import(str("../stl/", nombre, ".stl"), convexity = 6);
else if (escena == "capuchones") escena_capuchones();
else if (escena == "paso") escena_paso(paso);
