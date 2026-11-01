# Firmware de puesta en marcha de OCX

Proyecto ESP-IDF para la **ESP32-S3-DevKitC-1-N16R8** de la placa OCX (Fab v1.0). Comprueba la placa por bloques y comparte el código con una versión para PC que usa periféricos simulados.

El informe de diseño, los supuestos y los resultados están en [`INFORME.md`](INFORME.md).

## Estructura

```
docs/firmware/
├── CMakeLists.txt, sdkconfig.defaults     proyecto ESP-IDF
├── main/
│   ├── app_main.c                         pruebas + monitor de entradas
│   ├── hal_esp32s3.c/.h                   HAL real: SPI2/QSPI, I²C, ADC1, GPIO
│   └── Kconfig.projbuild                  menú "OCX" (SCLK, QSPI, modo interactivo)
├── components/                            código portable (sin ESP-IDF)
│   ├── ocx_hal/      ocx_hal.h (interfaz) y ocx_board.h (pines)
│   ├── bt817/        driver BT817: arranque, REG_CLOCK, tiempos NHD, sonido
│   ├── mcp23017/     driver MCP23017 (IOCON.MIRROR = 1)
│   ├── ocx_input/    mapa de botones y normalización de joysticks
│   └── ocx_bringup/  pruebas por bloques
└── host/                                  versión para PC
    ├── sim/          BT817, MCP23017, ADC y GPIO simulados
    ├── main_sim.c    pruebas sobre la placa simulada (con inyección de averías)
    └── tests/        pruebas unitarias (CTest)
```

## Placa (ESP-IDF 5.5)

```bash
cd docs/firmware
```

```bash
idf.py set-target esp32s3
```

```bash
idf.py build flash monitor
```

La consola sale por el conector **USB** (USB-Serial/JTAG) del DevKitC. Al arrancar se ejecutan los seis bloques y se imprime el informe. Después el programa muestra los botones y los ejes. Si se mantienen **HOME + SELECT** durante 2 s, las pruebas se repiten.

Opciones en `idf.py menuconfig` → *OCX*: SCLK de arranque y de trabajo, QSPI sí/no y pruebas interactivas sí/no.

## PC

```bash
cmake -S docs/firmware/host -B build-host
```

```bash
cmake --build build-host -j
```

```bash
ctest --test-dir build-host --output-on-failure
```

```bash
./build-host/ocx_sim_bringup --fault=no_crystal
```

Averías disponibles: `eve_absent`, `no_crystal`, `xtal_off`, `qspi_io23`, `pclk_dead`, `mcp_absent`, `no_mirror`, `stuck_btn`, `dead_btn`, `joy_gnd` y `mute`. Para ver solo las comprobaciones automáticas, usa `--no-interactive`.

## Bloques de prueba

| Bloque | Qué comprueba | Interacción |
|---|---|---|
| EVE_ID | Ciclo PD_N, CLKEXT + CLKSEL ×6, ACTIVE, REG_ID = 0x7C, REG_CPURESET = 0; paso a QSPI y relectura de REG_ID | — |
| EVE_CLOCK | Frecuencia real con REG_CLOCK frente a `esp_timer` (72 MHz ± 2000 ppm) | — |
| DISPLAY | Tiempos NHD 800×480 y REG_SWIZZLE = 3 releídos, DISP = 1, REG_FRAMES ≈ 74 Hz, barras R/G/B/blanco | mirar la pantalla |
| BUTTONS | MCP23017 en 0x20, IOCON = 0x40 releído, ningún botón en reposo, los 16 botones, INTA con GPA y GPB | pulsar cada botón |
| JOYSTICKS | Centro (30–70 %), ruido y recorrido (< 15 % y > 85 %) de los 4 ejes; calibración | mover a los topes |
| BEEP | ~SD = 1, seno de 440 Hz con REG_SOUND/REG_PLAY, parada y ~SD = 0 | X = se oye, O = no |
