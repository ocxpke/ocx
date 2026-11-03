# Manual de la consola OCX

- [`MANUAL-USUARIO.md`](MANUAL-USUARIO.md): manual de usuario y de mantenimiento (fuente).
- [`MANUAL-USUARIO.pdf`](MANUAL-USUARIO.pdf): versión en PDF generada con pandoc.
- `img/`: figuras. Cada una está en SVG (fuente) y en PNG (la que enlaza el manual).
  - `placa-controles.*` y `placa-servicio.*` se generan desde `hardware/ocxPrototype.kicad_pcb`.
  - `montaje-devkit.*`, `montaje-joystick.*`, `alimentacion.*` y `recuperacion.*` son dibujos esquemáticos hechos a mano.
- `herramientas/`: scripts para regenerar las figuras y el PDF.

## Regenerar

Requisitos: `python3`, `pandoc` y WeasyPrint (`pip install weasyprint`). Para volver a rasterizar los SVG a PNG hace falta también `node` con `playwright`.

```bash
manual/herramientas/generar-pdf.sh
```

El script vuelve a dibujar las figuras de la placa, las convierte a PNG y genera `MANUAL-USUARIO.pdf`.

Las partes que dependen del firmware están marcadas como **[PENDIENTE DE FIRMWARE]**, y las que dependen del diseño final de la carcasa como **[PENDIENTE: …]**. Para encontrarlas:

```bash
grep -n "PENDIENTE" manual/MANUAL-USUARIO.md
```
