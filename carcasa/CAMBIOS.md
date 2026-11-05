# Cambios de esta versión

## Qué reimprimir

| Pieza | Reimprimir | Por qué |
|---|---|---|
| `01_frontal_izquierda.stl` | **Sí** | Joystick en su nueva posición (hueco y postes) y altavoz movido |
| `03_frontal_derecha.stl` | **Sí** | Joystick en su nueva posición y tubo del LED movido con D2 |
| Todas las demás (00, 02, 04–09 y capuchones) | No | Son idénticas a la versión anterior (comparadas malla a malla) |

Hace falta comprar también:
- un adaptador FPC/FFC de 40 vías a 0,5 mm (unos 30 × 12 × 3 mm);
- un FFC de 40 vías a 0,5 mm de 100 mm (vale desde 84 mm);
- 6 tacos de espuma de unos 4 × 3 × 14 mm con doble cara.

Los 4 tornillos de los joysticks ya no hacen falta.

## Qué ha cambiado

1. **Placa actualizada.** `scad/pcb_data.scad` se ha regenerado desde `hardware/` de `main`. Cambian de sitio C40, D2, R9 y los puntos de prueba, y aparece R28. El tubo del LED sigue a D2. C40, R28 y los puntos de prueba no chocan con nada.
2. **Joysticks.**
   - Cada módulo va al sur de J6/J7, girado 180°, con el eje en (37,5; 105,7) y (221,8; 105,7). El cable sale hacia el norte y baja con una S hasta el conector: nunca se dobla 180°.
   - El largo del cable es un parámetro nuevo, `joy_fpc_largo`. Vale 24 mm por defecto porque no tenía el dato.
   - La comprobación calcula la forma del cable. Con 24 mm, el radio mínimo es de 4,2 mm; con el módulo donde está caben cables de 21,0 a 32,4 mm. El stick inclinado 20° sigue libre.
   - El altavoz pasa a (40; 80,5) y el tubo del LED, a 1,5 mm de pared. El joystick derecho queda entre la torreta (230;92) y el tubo del LED, con 0,7–0,8 mm de aire a cada lado.
   - El módulo ya no se atornilla. Con un cable tan corto, J6/J7 no se pueden conectar con la placa abierta y quedan tapados con la placa puesta. Por eso el módulo va pegado a la placa sobre 3 tacos de espuma, y la frontal lo aprieta contra sus postes.
3. **Pantalla.** La cola del FPC no llega a J1, así que lleva un alargador: el adaptador va pegado a la trasera, al final de la cola, y un FFC vuelve por debajo de la pantalla hasta J1. Son zonas prohibidas nuevas. El adaptador queda a 19,6 mm de la DevKit y no toca ningún componente. El supuesto 24 está reescrito.
4. **Manual.**
   - Corregido «J10 es solo alimentación»: J10 lleva D+/D− a GPIO19/20, así que se programa y se ve la consola por J10 sin abrir.
   - Reescritos los pasos 4 a 8, los materiales y la tabla de medidas.
5. **Comprobaciones y renders.**
   - Nuevas comprobaciones: el cable de los joysticks (apartado 5) y el alargador (apartado 8).
   - Dos secciones nuevas: `img/seccion_joystick.png` e `img/seccion_tft.png`.
   - Todos los STL, renders y documentos están regenerados.

## Pendiente de medir

- **Cable del joystick**: largo desde el borde del módulo (`joy_fpc_largo`). Si se sale de 21,0–32,4 mm, `COMPROBACIONES.md` falla y hay que mover el módulo.
- **FPC de la pantalla**: ancho y grosor de su parte ancha (`tft_ancha_ancho`, `tft_ancha_e`).
- **Adaptador**: tamaño real (`adaptador`).
