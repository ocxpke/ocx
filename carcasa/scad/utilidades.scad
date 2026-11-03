// =====================================================================
//  OCX - carcasa · utilidades geométricas
//  Convención: las coordenadas "K" son las del .kicad_pcb (Y hacia abajo).
//  En OpenSCAD se dibuja con Y = -y_kicad para que la vista desde +Z
//  coincida con la vista superior de KiCad.
// =====================================================================

function K(p) = [p[0], -p[1]];
function en_lista(x, l) = len([for (e = l) if (e == x) 1]) > 0;
function Kpts(pts) = [for (p = pts) K(p)];

module enK(x, y, z = 0) translate([x, -y, z]) children();

// Caja KiCad b = [x0, y0, x1, y1] entre z0 y z1
module cajaK(b, z0, z1) translate([b[0], -b[3], z0]) cube([b[2] - b[0], b[3] - b[1], z1 - z0]);

// Rectángulo redondeado 2D a partir de una caja KiCad
module rrectK(b, r) {
  rr = max(0.01, r);
  hull() for (x = [b[0] + rr, b[2] - rr], y = [b[1] + rr, b[3] - rr]) translate([x, -y]) circle(r = rr, $fn = fn);
}

// Caja KiCad con esquinas verticales redondeadas
module rcajaK(b, r, z0, z1) translate([0, 0, z0]) linear_extrude(z1 - z0) rrectK(b, r);

function encoge(b, d) = [b[0] + d, b[1] + d, b[2] - d, b[3] - d];
function crece(b, d) = encoge(b, -d);
function caja_centro(c, tam) = [c[0] - tam[0] / 2, c[1] - tam[1] / 2, c[0] + tam[0] / 2, c[1] + tam[1] / 2];

// Estadio 2D centrado (largo a lo largo de X)
module estadio(a, b) {
  r = min(a, b) / 2;
  hull() for (s = [-1, 1]) translate([s * (max(a, b) / 2 - r), 0]) circle(r = r, $fn = fn_peq * 2);
}

// Forma "D": círculo con un plano (antigiro) en el lado +Y
module forma_D(d, plano = 0.8) intersection() {
  circle(d = d, $fn = fn);
  translate([-d, -d / 2]) square([2 * d, d - plano]);
}

// Forma de capuchón según tipo ("D" o "estadio"), crecida en `extra` por lado
module forma_cap(forma, tam, extra = 0) {
  if (forma == "estadio") estadio(tam[0] + 2 * extra, tam[1] + 2 * extra);
  else offset(delta = extra) forma_D(tam[0]);
}

// Agujero horizontal en "lágrima" para imprimir sin soportes.
// eje: a lo largo de X. `punta` = +1 si la punta debe mirar a +Z del modelo,
// -1 si debe mirar a -Z (piezas frontales, que se imprimen boca abajo).
module lagrima_x(d, largo, punta = -1) {
  rotate([0, 90, 0]) linear_extrude(largo, center = true)
    rotate([0, 0, punta > 0 ? 180 : 0]) union() {
      circle(d = d, $fn = fn_peq);
      // en el plano rotado, +X local corresponde a -Z del modelo
      polygon([[0, 0], [d / 2 * 0.7071, -d / 2 * 0.7071], [d / 2 * 1.4142, 0], [d / 2 * 0.7071, d / 2 * 0.7071]]);
    }
}

// Cola de milano 2D: cuello en x = 0, crece hacia +X hasta `largo`
module cola_2d(largo, cuello, punta, extra = 0) {
  polygon([[-0.01 - extra, -cuello / 2 - extra], [largo + extra, -punta / 2 - extra],
           [largo + extra, punta / 2 + extra], [-0.01 - extra, cuello / 2 + extra]]);
}

// Hexágono (tuerca) 2D por distancia entre caras
module hexagono(ec) circle(d = ec / cos(30), $fn = 6);

// Pirámide de símbolos sencillos para grabar en los capuchones (2D, centrados)
module simbolo(nombre, t) {
  if (nombre == "arriba")    polygon([[0, t * 0.45], [-t * 0.4, -t * 0.25], [t * 0.4, -t * 0.25]]);
  else if (nombre == "abajo")     rotate(180) simbolo("arriba", t);
  else if (nombre == "izquierda") rotate(90) simbolo("arriba", t);
  else if (nombre == "derecha")   rotate(-90) simbolo("arriba", t);
  else if (nombre == "triangulo") difference() {
    polygon([[0, t * 0.42], [-t * 0.42, -t * 0.3], [t * 0.42, -t * 0.3]]);
    offset(delta = -0.6) polygon([[0, t * 0.42], [-t * 0.42, -t * 0.3], [t * 0.42, -t * 0.3]]);
  }
  else if (nombre == "circulo") difference() { circle(d = t * 0.8, $fn = 32); circle(d = t * 0.8 - 1.2, $fn = 32); }
  else if (nombre == "cuadrado") difference() { square(t * 0.62, center = true); square(t * 0.62 - 1.2, center = true); }
  else if (nombre == "cruz") for (a = [45, -45]) rotate(a) square([t * 0.85, 0.6], center = true);
  else if (nombre == "menos") square([t * 0.6, 0.7], center = true);
  else if (nombre == "mas") { square([t * 0.6, 0.7], center = true); square([0.7, t * 0.6], center = true); }
  else if (nombre == "select") for (y = [-1, 0, 1]) translate([0, y * t * 0.2]) square([t * 0.55, 0.5], center = true);
  else if (nombre == "home") union() {
    translate([0, -t * 0.12]) square([t * 0.4, t * 0.3], center = true);
    polygon([[0, t * 0.3], [-t * 0.3, t * 0.03], [t * 0.3, t * 0.03]]);
  }
  else if (nombre == "L" || nombre == "R")
    text(nombre, size = t * 0.55, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}
