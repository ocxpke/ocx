# Informe: firmware de puesta en marcha de OCX

Fecha: 1 de noviembre de 2026. Placa: OCX Fab v1.0 (commit `6948262`). Módulo: ESP32-S3-DevKitC-1-N16R8.

## Resumen

- El proyecto ESP-IDF **compila** con ESP-IDF v5.5.1 para `esp32s3`. El binario ocupa 299 kB y la compilación no da avisos.
- La versión para PC pasa **6/6 pruebas de CTest**: 613 comprobaciones unitarias, la ejecución completa con resultado PASS y la detección de una avería. Se ha compilado con GCC + ASan/UBSan y con Clang.
- Las pruebas se organizan en **seis bloques**: REG_ID, cristal (REG_CLOCK), pantalla, botones, joysticks y pitido. Con 11 averías inyectadas en el simulador, cada una se detecta y el mensaje señala el pin o el componente que hay que revisar.
- El pinout pedido **coincide con el esquemático**. Esto incluye los pines de la ESP32-S3, IOCON.MIRROR (INTB está sin conectar) y REG_SWIZZLE = 3 (R/B intercambiados y con los bits invertidos). No se ha modificado nada de `hardware/`.

## Fuentes

- `hardware/*.kicad_sch`. Las netlists se extrajeron con un script propio que analiza los ficheros de KiCad, porque `kicad-cli` no está instalado en el entorno. Con ellas se verificaron J2/J3 (zócalos del DevKitC), U1 (BT817Q), U5 (MCP23017) y U4 (PAM8302A).
- `README.md` del repositorio.
- **No se han podido leer** `revision-final-esquematico.md`, `bom-lcsc.md` ni `revision-01-11-teel.md`, del proyecto de claude.ai «TFG: OCX». Esta sesión no tiene acceso a los documentos de proyectos de claude.ai. Por la misma razón, este informe no se ha podido guardar allí: hay que subirlo a mano. Si esos documentos contradicen algún supuesto de abajo, lo que cuenta son ellos.

## Pinout verificado contra el esquemático

| Señal | GPIO | Red en el esquemático | Nota |
|---|---|---|---|
| BT817 SCK | 12 | SCK | IO_MUX de SPI2 (FSPICLK) |
| BT817 IO0 / MOSI | 11 | MOSI | FSPID |
| BT817 IO1 / MISO | 13 | MISO | FSPIQ |
| BT817 IO2 | 14 | GPIO0/IO2 | FSPIWP |
| BT817 IO3 | 9 | GPIO1/IO3 | FSPIHD |
| BT817 CS_N | 10 | CS_N | FSPICS0 |
| BT817 PD_N | 4 | PD_N | |
| BT817 INT_N | 5 | INT_N | entrada con pull-up |
| I²C SCL / SDA | 15 / 16 | ESP_SCL / ESP_SDA | pull-up de 4,7 k (R6/R7) |
| MCP23017 INTA | 17 | BTN_INT | INTB sin conectar |
| MCP23017 ~RESET | 18 | MCP_RESET | pull-up de 10 k (R5) |
| Joystick L X / Y | 6 / 7 | JOY_L_X / JOY_L_Y | ADC1_CH5 / CH6 |
| Joystick R X / Y | **2 / 1** | JOY_R_X / JOY_R_Y | ADC1_CH1 / CH0: X va en el GPIO 2, no en el 1 |
| Pulsador L3 / R3 | 8 / 47 | JOY_L_BTN / JOY_R_BTN | sin pull-up externa |
| PAM8302A ~SD | 21 | VOL_MODE | 1 = amplificador activo |

Los seis pines del BT817 son justo los de IO_MUX de SPI2, así que el bus no pasa por la matriz GPIO.

**Botones del MCP23017** (todos van a GND y no tienen pull-up externa):

| Puerto A | Botón | Puerto B | Botón |
|---|---|---|---|
| GPA0 | T_L (SW1) | GPB0 | VOL+ (SW8) |
| GPA1 | Arriba (SW2) | GPB1 | HOME (SW9) |
| GPA2 | Derecha (SW3) | GPB2 | X (SW10) |
| GPA3 | Izquierda (SW4) | GPB3 | O (SW11) |
| GPA4 | Abajo (SW5) | GPB4 | C, cuadrado (SW12) |
| GPA5 | SELECT (SW6) | GPB5 | T, triángulo (SW13) |
| GPA6 | VOL− (SW7) | GPB6 | T_R (SW15) |
| GPA7 | libre | GPB7 | libre |

A0–A2 están a GND, así que la dirección es 0x20. El audio sale del BT817 (AUDIO_L, PWM) hacia el PAM8302A, de modo que el pitido lo genera el propio BT817.

## Arquitectura

```
app_main.c ─┐                         host/main_sim.c, host/tests ─┐
            ▼                                                       ▼
        ocx_bringup  ──►  bt817 · mcp23017 · ocx_input  ──►  ocx_hal.h (interfaz)
                                                                 ▲          ▲
                                           main/hal_esp32s3.c ───┘          └─── host/sim/sim.c
                                           (SPI2, I²C, ADC1, GPIO)              (modelos simulados)
```

- **`ocx_hal.h`** es una tabla de funciones: transacciones con el BT817 (escritura, lectura y cambio de ancho o frecuencia), GPIO, I²C, ADC y tiempo. Los drivers no incluyen nada de ESP-IDF.
- **Componentes portables**: el mismo `CMakeLists.txt` usa `idf_component_register` dentro de ESP-IDF y `add_library` en el PC.
- **Simulador**: modela el BT817 a nivel de registro. Incluye los comandos de host, el reloj externo o interno, REG_ID tras ACTIVE, REG_CLOCK y REG_FRAMES según el tiempo simulado, SPI/QSPI y el sonido. También modela el MCP23017 (MIRROR, INTCAP y borrado al leer). El tiempo es virtual: los 4,5 s de prueba duran milisegundos. Un «operador virtual» responde a los mensajes: pulsa los botones, mueve los joysticks y confirma el pitido.

## Pruebas de puesta en marcha

| Bloque | Criterio de PASS | Diagnóstico si falla |
|---|---|---|
| EVE_ID | REG_ID = 0x7C tras CLKEXT + CLKSEL(0x46) + ACTIVE, REG_CPURESET = 0, y de nuevo REG_ID = 0x7C en QSPI | Si responde con el oscilador interno, el fallo está en el cristal. Si va en SPI y no en QSPI, revisar IO2/IO3. Si no responde, se indican los pines de alimentación y del bus |
| EVE_CLOCK | REG_CLOCK medido = 72 MHz ± 2000 ppm (ventana de 200 ms, compensando la latencia de las lecturas) | Error en ppm; avisa si la frecuencia se parece a la del oscilador interno (60 MHz) |
| DISPLAY | Relectura de los 10 registros de tiempos, REG_SWIZZLE = 3 y REG_PCLK = 2; REG_FRAMES a 74 Hz ± 20 % | Indica el registro que no coincide, o que PCLK no avanza |
| BUTTONS | Relectura de IOCON = 0x40, IODIR y GPPU; ningún botón pulsado en reposo; INTA en reposo; los 16 botones; INTA salta con GPA y con GPB | Botones atascados o que faltan, MIRROR, línea GPIO17 |
| JOYSTICKS | Centro entre el 30 y el 70 %, ruido ≤ 150 cuentas, recorrido por debajo del 15 % y por encima del 85 % en los 4 ejes | Eje a GND o a 3V3 (FPC), eje descentrado, recorrido corto. Deja guardada la calibración |
| BEEP | REG_SOUND = 0x4502 y REG_PLAY = 1 mientras suena; parada correcta; el operador pulsa X | Si el operador pulsa O: AUDIO_L, PAM8302A, GPIO21 o altavoz |

Si REG_ID falla, los bloques del BT817 se marcan como SKIP, pero botones y joysticks se prueban igualmente.

## Supuestos (decididos sin consultar)

1. **Ubicación**: no se indicó carpeta, así que todo va en `docs/firmware/`. La rama es `claude/pensive-newton-k9wbx6`, la que tiene asignada esta sesión, creada desde `main`.
2. **ESP-IDF v5.5.1** con los drivers nuevos (`i2c_master`, `adc_oneshot`).
3. **Tiempos de la NHD-5.0-800480AF-ASXP**: HSYNC 48, HBP 40, HFP 40 → HCYCLE 928 y HOFFSET 88; VSYNC 3, VBP 29, VFP 13 → VCYCLE 525 y VOFFSET 32; PCLK_POL = 1. Son los valores habituales de Newhaven para sus paneles de 5" a 800×480. **Hay que comprobarlos con la hoja de datos del panel.**
4. **Reloj del sistema a 72 MHz** (12 MHz × 6) y **REG_PCLK = 2**, es decir 36 MHz de reloj de píxel y unos 74 Hz de refresco. Si el panel no admite 36 MHz, con REG_PCLK = 3 quedan 24 MHz y unos 49 Hz.
5. **SCLK**: 8 MHz durante el arranque (el BT817 exige ≤ 11 MHz antes de configurar el reloj) y 20 MHz después, por debajo del máximo de 30 MHz para dejar margen con el zócalo del DevKitC. Se cambia en `menuconfig`.
6. **QSPI** con transacciones half-duplex `SPI_TRANS_MODE_QIO`: la dirección y el byte de espera se envían como datos por 4 líneas y después se lee. Se puede desactivar (`CONFIG_OCX_EVE_QUAD=n`).
7. **Botones**: activos a nivel bajo. Se usan las pull-ups internas del MCP23017 (GPPU, unos 100 k) y de la ESP32-S3 para L3/R3, porque en placa no hay externas. INTCON = 0 (interrupción por cambio) e INTA push-pull activa a nivel bajo.
8. **Nombres de los botones**: C = cuadrado, T = triángulo, T_L/T_R = gatillos. Se han deducido de los valores del esquemático.
9. **Retroiluminación**: REG_PWM_HZ = 4 kHz y 50 % durante la prueba. Hay que revisar la frecuencia de PWM que admite el DIO5661.
10. **Pitido**: onda senoidal a 440 Hz (MIDI 69), volumen 255, durante 500 ms. El amplificador se enciende 10 ms antes y se apaga al terminar.
11. **ADC**: atenuación de 12 dB y 12 bits, sin calibración de curva. Basta para porcentajes; si hace falta medir en mV, se añade `adc_cali`.
12. **Tolerancia del cristal**: 2000 ppm. Es holgada frente a los ±30 ppm del cristal y el error de `esp_timer`, y muy estrecha frente al ±10 % del oscilador interno.

## Cómo se ha verificado en este entorno

| Comprobación | Resultado |
|---|---|
| `idf.py set-target esp32s3 && idf.py build` (ESP-IDF v5.5.1) | OK; 0 avisos; imagen de 298 721 B; PSRAM octal, 16 MB y FreeRTOS a 1 kHz aplicados |
| Host con GCC, `-Wall -Wextra -Werror`, ASan + UBSan | 6/6 pruebas de CTest |
| Host con Clang (sin sanitizers: el entorno no tiene el runtime de ASan para Clang) | 6/6 pruebas de CTest |
| `test_bt817` | 79 comprobaciones: cabeceras SPI, CLKSEL, tiempos NHD, arranque, sin cristal, QSPI averiado, medida de reloj (±40 y 3000 ppm), lista de visualización, sonido |
| `test_mcp23017` | 29 comprobaciones: registros tras la configuración, NACK, MIRROR con los puertos A y B, avería sin MIRROR, ~RESET |
| `test_input` | 441 comprobaciones: mapa de botones, nombres, pines de ADC1, normalización (zona muerta, saturación, monotonía) |
| `test_bringup` | 64 comprobaciones: todo PASS, modo no interactivo y 12 escenarios de avería o tolerancia |

Ejecución del simulador sin averías (`ocx_sim_bringup`):

```
[PASS] EVE_ID     REG_ID=0x7C en SPI y QSPI, CPURESET=0, SCLK 20 MHz
[PASS] EVE_CLOCK  REG_CLOCK: 72000000 Hz (esperado 72000000, +0 ppm)
[PASS] DISPLAY    800x480, SWIZZLE=3, 72 fps; barras R/G/B/blanco (revision visual)
[PASS] BUTTONS    16/16 botones; INTA activa con GPA y GPB (MIRROR=1)
[PASS] JOYSTICKS  calibrado L.X=5..1984..4091 L.Y=511..2028..4093 R.X=9..2068..4093 R.Y=0..2109..3577
[PASS] BEEP       seno 440 Hz audible (confirmado por el operador)
```

**Qué no se ha podido verificar**: nada se ha ejecutado en la placa real. En particular quedan sin probar la temporización del QSPI half-duplex del ESP32-S3 con el BT817, los tiempos reales del panel y la frecuencia de PWM de la retroiluminación.

## Primera prueba en placa: recomendaciones

1. Primero con `CONFIG_OCX_EVE_QUAD=n` y `CONFIG_OCX_EVE_RUN_HZ=8000000`. Cuando EVE_ID y EVE_CLOCK den PASS, activar QSPI y subir a 20 MHz.
2. Con un analizador lógico en CS, SCK e IO0–IO3, comprobar que en la lectura en QSPI el BT817 empieza a devolver datos justo después de los 8 ciclos de la cabecera (3 bytes de dirección + 1 de espera). Si los datos llegan desplazados, ajustar el byte de espera en `bt817_hdr_read` o en `REG_SPI_WIDTH`.
3. Si el bloque DISPLAY da PASS pero la imagen tiembla o los colores no cuadran, revisar PCLK_POL y los porches con la hoja de datos de la NHD. El orden de las barras (rojo, verde, azul, blanco) confirma el valor de REG_SWIZZLE.
4. Para una futura revisión de la placa: L3 y R3 dependen de la pull-up interna de unos 45 k de la ESP32-S3. Una pull-up externa de 10 k haría las entradas más robustas frente al ruido del FPC.
