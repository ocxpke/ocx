# Comprobaciones automáticas de la carcasa

Generado por `scripts/comprobar.py` con booleanas exactas (manifold3d) sobre los STL de `build/montaje/`. No lo edites: se regenera con `python3 carcasa/scripts/construir.py`.

**Resultado: TODO CORRECTO**

Cara frontal en z = 23.95 mm, trasera en z = -6.10 mm (grosor total 30.0 mm). Paredes 3 mm, cara frontal 2 mm, tapa trasera 2 mm, holgura 0.3 mm.

## 1. Tamaño de impresión (≤ 135 mm)

| Elemento | Estado | Detalle |
|---|---|---|
| 00_probeta_ajustes.stl | ✅ | 64.0 × 28.0 × 11.0 mm |
| 01_frontal_izquierda.stl | ✅ | 57.3 × 122.4 × 27.2 mm |
| 02_frontal_central.stl | ✅ | 133.4 × 122.4 × 27.2 mm |
| 03_frontal_derecha.stl | ✅ | 50.6 × 122.4 × 27.2 mm |
| 04_trasera_izquierda.stl | ✅ | 105.8 × 122.4 × 4.5 mm |
| 05_trasera_derecha.stl | ✅ | 132.4 × 122.4 × 4.5 mm |
| 06_pisapantalla_izq.stl | ✅ | 7.0 × 91.4 × 2.0 mm |
| 07_pisapantalla_der.stl | ✅ | 7.0 × 91.4 × 2.0 mm |
| 08_empujador_boot.stl | ✅ | 16.5 × 30.1 × 3.4 mm |
| 09_bandeja_capuchones.stl | ✅ | 67.0 × 64.5 × 20.4 mm |
| capuchon_SW10_X_cruz.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW11_O_circulo.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW12_C_cuadrado.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW13_T_triangulo.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW15_gatillo_R.stl | ✅ | 15.0 × 10.0 × 20.4 mm |
| capuchon_SW1_gatillo_L.stl | ✅ | 15.0 × 10.0 × 20.4 mm |
| capuchon_SW2_arriba.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW3_derecha.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW4_izquierda.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW5_abajo.stl | ✅ | 11.0 × 10.2 × 20.4 mm |
| capuchon_SW6_select.stl | ✅ | 9.0 × 8.2 × 20.1 mm |
| capuchon_SW7_vol_menos.stl | ✅ | 9.0 × 8.2 × 20.1 mm |
| capuchon_SW8_vol_mas.stl | ✅ | 9.0 × 8.2 × 20.1 mm |
| capuchon_SW9_home.stl | ✅ | 9.0 × 8.2 × 20.1 mm |

## 2. Choques pieza–componente

| Elemento | Estado | Detalle |
|---|---|---|
| frontal_izquierda | ✅ | sin choques (53 zonas cercanas revisadas) |
| frontal_central | ✅ | sin choques (170 zonas cercanas revisadas) |
| frontal_derecha | ✅ | sin choques (51 zonas cercanas revisadas) |
| trasera_izquierda | ✅ | sin choques (22 zonas cercanas revisadas) |
| trasera_derecha | ✅ | sin choques (95 zonas cercanas revisadas) |
| pisapantalla_izq | ✅ | sin choques (0 zonas cercanas revisadas) |
| pisapantalla_der | ✅ | sin choques (0 zonas cercanas revisadas) |
| empujador_boot | ✅ | sin choques (2 zonas cercanas revisadas) |
| capuchon_SW1 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW2 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW3 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW4 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW5 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW6 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW7 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW8 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW9 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW10 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW11 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW12 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW13 | ✅ | sin choques (1 zonas cercanas revisadas) |
| capuchon_SW15 | ✅ | sin choques (1 zonas cercanas revisadas) |

## 3. Choques entre piezas montadas

| Elemento | Estado | Detalle |
|---|---|---|
| 22 piezas | ✅ | ningún par se solapa (231 pares) |

## 4. Capuchones

| Elemento | Estado | Detalle |
|---|---|---|
| capuchon_SW1 (SW1) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW2 (SW2) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW3 (SW3) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW4 (SW4) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW5 (SW5) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW6 (SW6) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.2 mm (pulsado 0.95) |
| capuchon_SW7 (SW7) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.2 mm (pulsado 0.95) |
| capuchon_SW8 (SW8) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.2 mm (pulsado 0.95) |
| capuchon_SW9 (SW9) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.2 mm (pulsado 0.95) |
| capuchon_SW10 (SW10) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW11 (SW11) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW12 (SW12) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW13 (SW13) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| capuchon_SW15 (SW15) | ✅ | baja libre 1.25 mm (clic a 0.25 mm) · sube 0.40 mm hasta el tope · sobresale 1.5 mm (pulsado 1.25) |
| empujador_boot (SW16) | ✅ | baja libre 1.25 mm · sube 0.40 mm hasta el tope (la varilla toca la piel) |

## 5. Joysticks (stick inclinado 20°)

| Elemento | Estado | Detalle |
|---|---|---|
| frontal_izquierda en (40.5;84) | ✅ | libre en 24 direcciones |
| frontal_derecha en (216.5;83) | ✅ | libre en 24 direcciones |

## 6. Tornillería

| Elemento | Estado | Detalle |
|---|---|---|
| placa_195_24 | ✅ | no toca componentes ni la antena · rosca dentro de la torreta 6.9 mm |
| placa_230_92 | ✅ | no toca componentes ni la antena · rosca dentro de la torreta 6.9 mm |
| placa_26_92 | ✅ | no toca componentes ni la antena · rosca dentro de la torreta 6.9 mm |
| placa_65_24 | ✅ | no toca componentes ni la antena · rosca dentro de la torreta 6.9 mm |
| placa_173_122 | ✅ | no toca componentes ni la antena · rosca dentro de la torreta 6.9 mm |
| placa_76_122 | ✅ | no toca componentes ni la antena · rosca dentro de la torreta 6.9 mm |
| union_A1 | ✅ | no toca componentes ni la antena |
| union_A2 | ✅ | no toca componentes ni la antena |
| union_B1 | ✅ | no toca componentes ni la antena |
| union_B2 | ✅ | no toca componentes ni la antena |
| pisapantalla_82.04_31.9 | ✅ | no toca componentes ni la antena |
| pisapantalla_82.04_116.3 | ✅ | no toca componentes ni la antena |
| pisapantalla_183.34_31.9 | ✅ | no toca componentes ni la antena |
| pisapantalla_183.34_116.3 | ✅ | no toca componentes ni la antena |
| tuerca A1 | ✅ | el tornillo atraviesa la tuerca y sobresale 0.90 mm |
| tuerca A2 | ✅ | el tornillo atraviesa la tuerca y sobresale 0.75 mm |
| tuerca B1 | ✅ | el tornillo atraviesa la tuerca y sobresale 0.90 mm |
| tuerca B2 | ✅ | el tornillo atraviesa la tuerca y sobresale 0.90 mm |

## 7. Voladizos de impresión (informativo)

| Elemento | Estado | Detalle |
|---|---|---|
| 00_probeta_ajustes.stl | ℹ️ | 35 mm² hacia abajo con más de 45° (de ellos 0 mm² son techos planos: puentes de agujeros y ranuras) |
| 01_frontal_izquierda.stl | ℹ️ | 80 mm² hacia abajo con más de 45° (de ellos 28 mm² son techos planos: puentes de agujeros y ranuras) |
| 02_frontal_central.stl | ℹ️ | 31 mm² hacia abajo con más de 45° (de ellos 0 mm² son techos planos: puentes de agujeros y ranuras) |
| 03_frontal_derecha.stl | ℹ️ | 94 mm² hacia abajo con más de 45° (de ellos 32 mm² son techos planos: puentes de agujeros y ranuras) |
| 04_trasera_izquierda.stl | ℹ️ | 63 mm² hacia abajo con más de 45° (de ellos 63 mm² son techos planos: puentes de agujeros y ranuras) |
| 05_trasera_derecha.stl | ℹ️ | 63 mm² hacia abajo con más de 45° (de ellos 63 mm² son techos planos: puentes de agujeros y ranuras) |
| 06_pisapantalla_izq.stl | ℹ️ | 0 mm² hacia abajo con más de 45° (de ellos 0 mm² son techos planos: puentes de agujeros y ranuras) |
| 07_pisapantalla_der.stl | ℹ️ | 0 mm² hacia abajo con más de 45° (de ellos 0 mm² son techos planos: puentes de agujeros y ranuras) |
| 08_empujador_boot.stl | ℹ️ | 0 mm² hacia abajo con más de 45° (de ellos 0 mm² son techos planos: puentes de agujeros y ranuras) |
| 09_bandeja_capuchones.stl | ℹ️ | 205 mm² hacia abajo con más de 45° (de ellos 106 mm² son techos planos: puentes de agujeros y ranuras) |
