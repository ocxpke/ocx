# Estudio de viabilidad: Fdf y cub3D (MLX42) en la consola OCX

Fecha: 3 de noviembre de 2026. Placa: OCX Fab v1.1 (`main` @ `b7c4baa`) con ESP32-S3-DevKitC-1-N16R8 y BT817Q.
Proyectos analizados, solo en lectura: `ocxpke/Fdf` @ `ba5f42d` (MLX42 2.4.1) y `ocxpke/cub3D` @ `394f89f` (MLX42 2.4.2).
No se ha hecho ningún cambio, rama ni commit en los repositorios de 42.

> **Respuesta corta.** Los dos proyectos se pueden portar, pero no con la misma estrategia y no "tal cual" a 800×480.
>
> - **cub3D** es viable a **50–59 fps** (el panel refresca a 59,3 Hz) si renderiza a **400×240 o 320×240** y el BT817 escala la imagen ×2 (estrategia c). Para eso el cálculo tiene que ser solo en `float` y hay que reescribir el bucle que pinta cada columna (unas 400 líneas, el 11 % del código). Si se usa una capa de compatibilidad con MLX42 sin tocar el render, a 400×240 se quedaría en **9–12 fps**. A 800×480 no pasaría de **3–4 fps**.
> - **Fdf** funciona bien con la capa de compatibilidad (estrategia a), porque solo redibuja cuando cambia algo. Con la rotación automática da **14–19 fps** en mapas pequeños y **1–4 fps** en los de 100×100 a 200×200 puntos (hasta unos 8 pasando a `float`). Los mapas de 500×500 (`julia`, `elem-fract`) no caben: la matriz ocupa 16 MB y hay 8 MB de PSRAM. Con líneas nativas del BT817 (estrategia b), los mapas de hasta unos 25×25 puntos van a 59 fps.
> - **Hardware.** Un juego sencillo a 60 fps (59,3 Hz del panel) sí cabe si usa el BT817 de forma nativa (tiles, sprites, texto): gasta menos de 1 ms de QSPI y menos del 5 % de CPU por fotograma. Un juego con render por software a pantalla completa (800×480) no llega: el QSPI lo limita a **17 fps en RGB565 y 34 fps en 8 bpp**.

## Índice

1. [Método, herramientas y límites](#1-método-herramientas-y-límites)
2. [Análisis de los proyectos](#2-análisis-de-los-proyectos)
3. [Cifras de referencia en el ESP32-S3](#3-cifras-de-referencia-en-el-esp32-s3)
4. [Estrategias de port](#4-estrategias-de-port)
5. [Entradas, ficheros y audio](#5-entradas-ficheros-y-audio)
6. [Conclusiones](#6-conclusiones)
7. [Anexos](#7-anexos)

---

## 1. Método, herramientas y límites

| Paso | Herramienta | Qué se obtiene |
|---|---|---|
| Compilar y ejecutar en Linux | clang 18.1.3 con `-Ofast` (el `-Werror` de los Makefile falla con el GCC de Ubuntu por `_FORTIFY_SOURCE`), MLX42 de cada repo, GLFW 3.3.10, Xvfb a 800×480 y 1920×1080, Mesa 25.2.8 (llvmpipe) | Comportamiento real de los dos programas |
| Instrumentar sin tocar el código | Envolturas del enlazador (`--wrap`) sobre `mlx_put_pixel`, `memset`/`ft_memset`, `malloc`/`calloc`/`realloc`/`free`, `mlx_new_image`, `mlx_load_png`, hooks y `glfwSwapBuffers`; teclas simuladas | Píxeles, `memset` y heap por fotograma |
| Detectar comportamiento indefinido | valgrind 3.22 | Lecturas no inicializadas (§2.9) |
| Compilar para el ESP32-S3 | ESP-IDF **v5.5.6**, GCC 14.2.0 (`esp-14.2.0_20260121`) | Tamaños, rutinas *soft-float* enlazadas, ensamblador |
| Emular el ESP32-S3 | QEMU de Espressif `esp_develop_9.2.2` (máquina `esp32s3`, PSRAM octal) con `-icount shift=0` | **Instrucciones exactas** ejecutadas por cada rutina medida. La calibración da 10 M instrucciones = 10 017 µs, así que 1 µs = 1 000 instrucciones |
| Pasar de instrucciones a ciclos | CoreMark (EEMBC, *port* de Espressif: `-O3`, código en IRAM) en el mismo QEMU: 279 917 instrucciones por iteración. La hoja de datos da 613,86 CoreMark a 240 MHz, es decir, 390 969 ciclos por iteración | **CPI = 1,40** para código entero. Se usa 1,4 con un rango de 1,2 a 1,8 |
| Cotas reales de la FPU | Pruebas de ESP-IDF (`idf_performance_target.h`, esp32s3) | División `float` ≤ 70 ciclos y `sqrtf` ≤ 140 ciclos: umbrales de sus pruebas en hardware |
| QSPI | Código y documentación del driver `spi_master` de ESP-IDF 5.5.6 | Frecuencias alcanzables, tamaño máximo de DMA y sobrecoste por transacción |

**Límites del estudio.**

- Nada se ha ejecutado en la placa.
- QEMU cuenta instrucciones, pero no modela la caché, la PSRAM ni la latencia de la FPU. Los tiempos de CPU son estimaciones con un margen de **±30 %**.
- El efecto de la PSRAM se ha estimado con datos publicados por la comunidad y hay que medirlo en la placa (§6.4).
- El BT817 no está emulado, así que las cifras del QSPI son cálculos sobre el comportamiento documentado del driver.
- Todo el código de medida (instrumentación, banco de pruebas para QEMU, firmware de referencia corregido) era desechable y no se entrega. En `datos/` solo están las salidas en bruto (§7).

---

## 2. Análisis de los proyectos

### 2.1 Tamaño y estructura

| | Fdf | cub3D |
|---|---|---|
| Líneas de código sin libft (sin blancos ni comentarios) | 1 316 en 23 ficheros | 3 715 en 59 ficheros |
| Reparto | Proyección y rotación ≈ 400, Bresenham 157, ventana y hooks ≈ 180, lectura del mapa ≈ 125 | Parseo **1 880 (50 %)**, raycasting 399, dibujo 198, minimapa 54, jugador 176, gestión de MLX42 252, init/fin 195 |
| Llamadas a MLX42 o GLFW | 22 en 4 ficheros | 53 en 11 ficheros |

### 2.2 Inventario de llamadas a MLX42 y a GLFW

| Función | Fdf | cub3D | Qué haría falta en OCX |
|---|---:|---:|---|
| `mlx_init`, `mlx_set_setting(MLX_MAXIMIZED)` | 1, 1 | 1, 1 | Arrancar el BT817 y devolver un tamaño fijo (800×480, o 400×240 "virtual"). MAXIMIZED se ignora |
| `mlx_terminate`, `mlx_close_window` | 1, 1 | 1, 1 | Volver al lanzador |
| `mlx_set_window_title` | 1 | – | No hace nada (o rótulo en pantalla) |
| `mlx_new_image`, `mlx_delete_image` | 1, 2 | 2, 2 | Búfer RGBA en PSRAM más un *bitmap* en RAM_G |
| `mlx_resize_image` (desde `resize_hook`) | – | 2 | Solo al arrancar: la pantalla es fija |
| `mlx_image_to_window` (instancias) | 2 | 2 | Una entrada de la lista de visualización. cub3D escribe `instances[0].x` |
| **`mlx_put_pixel`** | 2 | 9 | Igual que en MLX42. Es el camino crítico (§2.3) |
| `mlx_load_png`, `mlx_delete_texture` | 1, 1 | 7, 8 | lodepng en el ESP32 (§3.4) o recursos ya convertidos |
| `mlx_texture_to_image` | 1 | – | Leyenda de 500×500: mejor sustituirla por texto nativo |
| `mlx_put_string` | 3 | – | Fuente de MLX42 renderizada a imagen, o `CMD_TEXT` con una fuente de la ROM del BT817 |
| `mlx_loop`, `mlx_loop_hook` | 1, 1 | 1, 1 | Bucle propio: hooks, conversión y subida de las imágenes modificadas, cambio de lista en el vsync |
| `mlx_key_hook` (usa `MLX_PRESS` y `MLX_REPEAT`) | 1 | – | Eventos de botón con autorrepetición sintética |
| `mlx_is_key_down` | – | 9 | Tabla de estado de botones y ejes |
| `mlx_scroll_hook` | 1 | – | Joystick o táctil convertidos en desplazamiento |
| `mlx_cursor_hook`, `mlx_set_mouse_pos`, `mlx_set_cursor_mode` | – | 1, 1, 3 | Joystick derecho como desplazamiento de cursor virtual. El resto no hace nada |
| `mlx_resize_hook` | – | 1 | No se dispara nunca |
| Campos públicos usados | `img->pixels/width/height`, `img->enabled` | `->width/height/pixels`, `window->delta_time`, `window->window`, `instances[0].x` | La capa debe conservar estos campos |
| **GLFW directo (salta MLX42)** | `glfwGetPrimaryMonitor`, `glfwGetMonitorWorkarea` | `glfwWindowHint`, `glfwGetFramebufferSize` | Sustituir por constantes: 2 líneas en cada proyecto |

Dos detalles de MLX42 que condicionan el port:

- `mlx_loop` **sube todas las imágenes a la GPU en cada fotograma** con `glTexImage2D` (`mlx_loop.c`, `mlx_render_images`), hayan cambiado o no. Una capa de compatibilidad que haga lo mismo por QSPI desperdicia el ancho de banda. Tiene que subir solo las imágenes "sucias".
- Las imágenes son siempre RGBA8888 (4 B/píxel), y los dos programas escriben en `->pixels` directamente con `memset` de `ancho × alto × 4`. El BT817 no tiene formatos de 32 bits, así que hay que convertir a RGB565, ARGB4 o 8 bpp antes de subir.

### 2.3 Resolución y píxeles escritos por fotograma (medido en Linux)

**Resolución que usan.**

- Fdf crea una imagen del 95 % del área de trabajo del monitor: 760×456 en un panel de 800×480 y 1824×1026 en 1920×1080. Añade una leyenda PNG de 500×500 y dos textos (400×20 y 370×20).
- cub3D crea una imagen del tamaño del *framebuffer* de la ventana maximizada más un minimapa del 25 %.
- cub3D lanza un rayo por columna hasta 1 199 px de ancho (`col_gross = ancho/600`, como mínimo 1): 320, 400 u 800 rayos. A 1920 px lanza 640 rayos y repite cada columna tres veces.

**cub3D** (400 fotogramas por mapa, con giros y desplazamientos simulados):

| Resolución | Mapa | Píxeles en la vista 3D (media) | Minimapa (media) | `memset` por fotograma | Heap máximo |
|---|---|---:|---:|---:|---:|
| 320×240 | subject / diamonds | 76 992 / 78 482 | 2 194 / 3 804 | 17 328 B | 0,73 / 1,12 MB |
| 400×240 | subject / diamonds | 96 240 / 99 179 | 3 254 / 6 319 | 21 660 B | 0,81 / 1,20 MB |
| 800×480 | subject / diamonds | 384 960 / 388 116 | 12 823 / 17 929 | 86 640 B | 2,04 / 2,43 MB |
| 1920×1080 | subject / diamonds | 2 078 784 / 2 107 144 | 44 139 / 63 860 | 467 856 B | 9,22 / 9,61 MB |

cub3D **reescribe cada píxel de la vista 3D en cada fotograma** (algo más del 100 % por los sprites) y redibuja el minimapa cada vez que el jugador se mueve. Los otros dos mapas medidos (`k_p` y el de los gatos) dan cifras equivalentes: ver `datos/linux_cub3d.txt`.

**Fdf** con rotación automática, el peor caso. Sin entrada del usuario no redibuja nada:

| Mapa (puntos) | Píxeles por fotograma a 760×456 (media / máx.) | `memset` por fotograma | Heap máximo | Asignaciones |
|---|---:|---:|---:|---:|
| 42 (11×19) | 9 756 / 11 951 | 1,39 MB | 4,32 MB | 913 |
| 100-6 (100×101) | 184 199 / 238 070 | 1,39 MB | 4,96 MB | 13 442 |
| mars (116×200) | 150 159 / 190 169 | 1,39 MB | 5,80 MB | 28 146 |
| t1 (200×200) | 751 347 / 1 084 820 | 1,39 MB | 6,88 MB | 62 083 |
| julia (500×500) | 995 368 / 1 526 384 | 1,39 MB | **20,3 MB** | 392 375 |

El heap de Fdf incluye 2 MB por la leyenda (textura más imagen RGBA de 500×500) y un búfer temporal de lodepng de 1,5 MB.

### 2.4 Uso de `double` y `float`

| | Fdf | cub3D |
|---|---|---|
| Declaraciones | 48 `double`, 0 `float` | 122 `float`, 4 `double` |
| Funciones de libm | `sin`/`cos` en `double` y `round` | 28 llamadas a `tan`/`cos`/`sin`/`sqrt`/`floor`/`fabs` en `double` y `atan2f`; constantes `PI` y `ONE_DEGREE` sin sufijo `f` |
| Rutinas *soft-float* que enlaza en el ESP32-S3 | `__adddf3 __subdf3 __muldf3 __gedf2 __ledf2 __fixdfsi __floatsidf` más `sin`/`cos` en `double` | `__adddf3 __subdf3 __muldf3 __divdf3 __eqdf2 __gtdf2 __ltdf2 __extendsfdf2 __truncdfsf2 __floatsidf` más `tan sin cos sqrt floor` en `double` |

Conclusión: cub3D "parece" `float`, pero **todos los cálculos por rayo y por columna se hacen en `double`**. El ESP32-S3 solo tiene FPU de precisión simple, así que esos cálculos se emulan por software (§3.2). Ojo también con la división en `float`: no es una instrucción, sino una llamada a `__divsf3` que usa la FPU internamente.

### 2.5 Ficheros

| | Fdf | cub3D |
|---|---|---|
| Mapas | 25 `.fdf` de texto, 6,26 MB en total. Dos de 2,8 MB (500×500) y el resto ≤ 382 KB | 15 `.cub` válidos (< 4 KB cada uno) y 70 inválidos de prueba |
| Texturas | `img/leyenda.png`: 118 KB, 500×500 RGBA | 29 PNG por mapa con texturas: 4 paredes, puerta, 4 de lava, 8 de agua y 12 llaves. 64×64, ≈ 230 KB en PNG y 464 KB en RGBA |
| Rutas | `./img/leyenda.png`, `../test_maps` (TAB recorre el directorio con `opendir`) | Rutas relativas `./src/imgs/...` dentro de los `.cub` y en macros |

### 2.6 Dependencias de libc, POSIX y otras

| Dependencia | Fdf | cub3D | En ESP-IDF 5.5 |
|---|---|---|---|
| `open`/`read`/`close` (con `get_next_line`, `BUFFER_SIZE` 42) | sí | sí | Funcionan con el VFS y un sistema de ficheros: FAT o SPIFFS (incluidos en ESP-IDF) o LittleFS (componente `joltwallet/littlefs` del registro). **Las rutas tienen que ser absolutas con el prefijo de montaje**: el VFS no trata `.` ni `..` |
| `opendir`/`readdir`/`closedir` (usa `d_type == 8`) | sí | no | Lo admiten LittleFS y FAT. Hay que comprobar que rellenan `d_type` |
| `write`, `perror`, `printf`/`ft_printf` | sí | sí (111 *prints*, incluido el volcado del mapa con colores ANSI) | Consola USB-Serial/JTAG |
| `malloc`/`calloc`/`free` | sí | sí | Con `CONFIG_SPIRAM_USE_MALLOC`, las asignaciones grandes van a PSRAM |
| **`exit()`** | 6 | **42** | **`_exit()` llama a `abort()`**: el ESP32 entra en pánico y se reinicia. Hay que sustituirlo por volver al lanzador |
| `gettimeofday` | no | sí | Funciona (o `esp_timer`) |
| GLFW y OpenGL (a través de MLX42) | sí | sí | No existen: se sustituyen |

### 2.7 Memoria máxima

- **cub3D a 400×240: 1,2 MB** (vista RGBA 375 KB, minimapa 23 KB, texturas 464 KB, temporales de PNG). A 800×480 sube a 2,4 MB. Cabe holgado en PSRAM; en SRAM interna no.
- **Fdf: 4,3–6,9 MB** con los mapas de hasta 200×200 puntos, de los que 3,4 MB son imagen y leyenda. Cada punto ocupa **64 B** (`t_coordinates` con seis `double`, igual en x86-64 y en Xtensa): 2,6 MB para `t1` y **16 MB para los mapas de 500×500**, que no caben en los 8 MB de PSRAM.

### 2.8 Firmware de referencia (`claude/pensive-newton-k9wbx6`) frente a los datos verificados

Se corrigió en una copia desechable y **compila con ESP-IDF v5.5.6: imagen de 285 712 B, 81 % de la partición libre, sin avisos del compilador**.

| Parámetro | Rama `pensive-newton` | Valor verificado | Comentario |
|---|---|---|---|
| HCYCLE / HOFFSET / HSYNC1 | 928 / 88 / 48 | **816 / 8 / 4** | ST7262 |
| VCYCLE / VOFFSET / VSYNC1 | 525 / 32 / 3 | **496 / 8 / 4** | |
| REG_PCLK | 2 (36 MHz, ~74 Hz) | **3 (24 MHz, 59,3 Hz)** | DCLK admitido: 23–27 MHz |
| REG_PCLK_POL | 1 | **0** | |
| REG_PWM_HZ | 4000 | **10000** | Retroiluminación (DIO5661) |
| Volumen del pitido | 255 (100 %) | **≤ 76 (~30 %)** | Lo mismo para `REG_VOL_SOUND` y `REG_VOL_PB` |
| Consola | USB-Serial/JTAG "del DevKitC" | USB-Serial/JTAG por el **USB-C J10** | La opción de Kconfig es la misma; se añade `CONFIG_ESP_CONSOLE_SECONDARY_NONE` |
| Pulsadores L3/R3 | Pull-up interna | Pull-up externa de 10 k (Fab v1.1) | La interna sobra |
| CPU y optimización | 160 MHz, `-Og` | Para juegos: **240 MHz, `-O2`** | A 160 MHz todos los tiempos de §3 se multiplican por 1,5 |
| Escritura en el BT817 | Bloques de 512 B, `polling`, `max_transfer_sz` 1032 | Para fotogramas: DMA de 32 KiB en cola | Con el driver actual, subir 192 KB tarda unos 19 ms en vez de 14,6 ms **y bloquea la CPU** (§3.5) |

### 2.9 Hallazgos que afectan al port

1. **Lectura con puntero sin inicializar en cub3D.** En los mapas con suelo y techo de color (por ejemplo `subject.cub`), `color_of_ceil` y `color_of_floor` leen `all_textures[frame]` antes de comprobar el tipo, y `all_textures` nunca se inicializa porque `t_game` está en la pila de `main`.
   - Con `-Ofast` el compilador elimina la carga y "funciona": valgrind no da errores.
   - Compilando `ceiling_floor.c` con `-O0`, se cuelga con **SIGSEGV en el primer fotograma** (`datos/valgrind_cub3d.txt`).
   - En una reproducción mínima de la función, el GCC de Xtensa con **`-Og`, el nivel por defecto de ESP-IDF, hace la carga antes del `if`**, así que en la placa daría un `LoadProhibited`. Con `-O2` la mete dentro de la rama.
   - La corrección es una línea: inicializar `t_game` a cero.
2. **Salida con `exit()`**: 42 llamadas en cub3D y 6 en Fdf. En ESP-IDF provocan un reinicio. Se pueden cambiar una a una, o redirigir `exit` con `--wrap` del enlazador hacia una vuelta al lanzador, sin tocar los fuentes.
3. **Rutas relativas** en los `.cub` y en el código: hay que añadirles el prefijo de montaje.
4. **Memoria de Fdf**: 64 B por punto, así que los mapas de 500×500 no caben (§2.7).
5. **Tiempos de carga de Fdf**: leer `t1.fdf` cuesta 3,3 s; los de 500×500 costarían unos 24 s (§3.4).
6. **Semántica de subida de MLX42**: hay que subir solo lo que cambia (§2.2).

---

## 3. Cifras de referencia en el ESP32-S3

Salvo que se diga otra cosa: 240 MHz, un núcleo, CPI = 1,4 (rango 1,2–1,8), código compilado con las opciones originales (`-Ofast`) y `mlx_put_pixel` fuera de línea, como en `libmlx42.a`. Las instrucciones son las contadas por QEMU.

### 3.1 Coste por operación: `float` frente a `double`

Instrucciones ejecutadas por operación, ya descontado el bucle:

| Operación | `float` | `double` | Factor |
|---|---:|---:|---:|
| Suma | 3 (hardware) | 54 (`__adddf3`) | ×18 |
| Multiplicación | 3 (hardware) | 70 (`__muldf3`) | ×23 |
| División | 38 (`__divsf3`; ≤ 70 ciclos reales) | 570 (`__divdf3`) | ×15 |
| Raíz cuadrada | 50 (`sqrtf`; ≤ 140 ciclos reales) | 770 | ×15 |
| `sin` / `cos` | 110 / 100 | 1 406 / 1 307 | ×13 |
| `tan` | 182 | 2 861 | ×16 |
| `floor` | 35 | 76 | ×2 |
| Conversión `float`↔`double` | – | 20–24 | – |

### 3.2 Raycasting de cub3D: `float` frente a `double`

Se usó el raycaster de cub3D (rayos DDA de 64 unidades, corrección de ojo de pez, columnas con textura de pared y suelo/techo con o sin textura), transcrito casi literalmente en cuatro variantes:

- **double**: todo en `double`.
- **orig**: el código tal cual, con su mezcla de `float` y `double`.
- **float**: `tanf`/`cosf`/…, constantes con sufijo `f`.
- **opt**: igual que *float*, pero el bucle de columna está reescrito: sin divisiones por píxel, salida RGB565 directa y sombreado con un multiplicador de 8 bits.

Los *checksums* de las tres primeras coinciden hasta la sexta cifra. La imagen de *opt* difiere en el 0,22 % de los píxeles (bordes y redondeo). Cada cifra es la media de 36 fotogramas en el mapa `subject`, mirando en todas las direcciones.

**Solo rayos (320 columnas), la pregunta directa:**

| Variante | Instrucciones por fotograma | Por rayo | Tiempo (CPI 1,4) |
|---|---:|---:|---:|
| float | 0,26 M | 800 | **1,5 ms** |
| orig | 2,30 M | 7 186 | **13,4 ms** |
| double | 2,97 M | 9 278 | **17,3 ms** |

**Fotograma completo (rayos y píxeles):**

| Resolución | Suelo/techo | double | orig | float | opt (RGB565) |
|---|---|---:|---:|---:|---:|
| 320×240 | color | 28,7 M · 168 ms | 9,44 M · 55 ms | 5,94 M · 35 ms | **1,41 M · 8,2 ms** |
| 320×240 | textura | 62,3 M · 363 ms | 12,4 M · 73 ms | 8,95 M · 52 ms | **2,29 M · 13,3 ms** |
| 400×240 | color | 35,9 M · 210 ms | 11,8 M · 69 ms | 7,42 M · 43 ms | **1,76 M · 10,3 ms** |
| 400×240 | textura | 77,9 M · 454 ms | 15,5 M · 91 ms | 11,2 M · 65 ms | **2,86 M · 16,7 ms** |
| 800×480 | color | 131 M · 765 ms | 37,6 M · 219 ms | 28,6 M · 167 ms | 5,70 M · 33 ms |
| 800×480 | textura | 299 M · 1,75 s | 52,6 M · 307 ms | 43,7 M · 255 ms | 10,1 M · 59 ms |

Lectura de la tabla:

- Pasar a `float` (cambiar unas 30 llamadas y constantes) ahorra un **28–37 %** del fotograma. Los rayos se vuelven 9 veces más baratos.
- Lo que más pesa después es el bucle por píxel: una llamada a `mlx_put_pixel` y dos divisiones `float` por cada píxel de suelo o techo. Reescribirlo da otro **×4–5**.
- Todo en `double` es inviable: 3–6 veces peor que el original.
- Con dos núcleos repartiendo las columnas se gana algo menos de ×2.

### 3.3 Fdf

Fotograma de rotación automática sobre la imagen de 760×456: `memset` de la imagen, rotación, proyección isométrica y Bresenham con `mlx_put_pixel`.

| Mapa | Puntos | Píxeles por fotograma | Original (`double`) | Todo `float` |
|---|---:|---:|---:|---:|
| 42 | 209 | 13 880 | 1,6 M · **9 ms** | 1,2 M · 7 ms |
| 100-6 | 10 100 | 194 677 | 38,5 M · **224 ms** | 12,4 M · 73 ms |
| mars | 23 200 | 157 855 | 71,6 M · **417 ms** | 13,6 M · 80 ms |
| t1 | 40 000 | 801 775 | 128 M · **749 ms** | 47,8 M · 279 ms |

A estos tiempos de CPU hay que sumar el **`memset` de 1,39 MB en PSRAM**. En CPU son 2,5 ms, pero en PSRAM serían unos 17–35 ms (§3.4).

### 3.4 Otras cifras

| Medida | Instrucciones | Tiempo estimado |
|---|---:|---:|
| Convertir RGBA8888 → RGB565, 320×240 / 400×240 / 800×480 (13 instrucciones por píxel) | 1,0 / 1,25 / 5,0 M | 5,8 / 7,3 / 29 ms |
| Decodificar PNG de 64×64 con lodepng (`mlx_load_png`) | 0,5–1,2 M | 3–7 ms (las 29 texturas: ≈ 170 ms al arrancar) |
| Decodificar la leyenda PNG de 500×500 de Fdf | 37 M | 215 ms |
| Leer y montar la matriz de `42` / `mars` / `t1` (con el GNL y `ft_split` de Fdf, en memoria) | 0,5 / 59 / 562 M | 3 ms / 0,34 s / **3,3 s**; `julia` ≈ 24 s |
| Matriz resultante de `mars` / `t1` | – | 1,49 MB / 2,57 MB |

**PSRAM, no medida.** QEMU no modela la PSRAM. Los datos publicados para el ESP32-S3 con PSRAM octal (foros de Espressif) son estos:

- Unos **40 MB/s** escribiendo a través de la caché. La caché lee cada línea antes de escribirla, así que el tráfico se duplica.
- Unos 82 MB/s copiando de DRAM a PSRAM.
- 27 MB/s de PSRAM a PSRAM por GDMA.

Con 40–80 MB/s, un búfer RGBA en PSRAM añade por fotograma 4–8 ms a 320×240, 5–10 ms a 400×240 y 19–38 ms a 800×480. Si el *framebuffer* RGB565 está en SRAM interna, no añade nada. Hay unos **325 KB libres** de SRAM interna con la PSRAM activada y sin WiFi ni BT (medido en QEMU).

### 3.5 Subida por QSPI

Datos sacados del driver de ESP-IDF 5.5.6 para el ESP32-S3:

- El reloj de SPI2 sale de APB (80 MHz) dividido por un entero. Pedir 30 MHz da en realidad **26,67 MHz** (80/3); 30 MHz exactos no son alcanzables, y lo siguiente (40 MHz) supera el límite del BT817. Pedir 11 MHz para el arranque da 11,43 MHz, por encima del límite de 11 MHz: el arranque a 8 MHz del firmware de referencia es correcto.
- Una transacción DMA admite como mucho **32 KiB** (`SPI_LL_DMA_MAX_BIT_LEN` = 2¹⁸ bits). `max_transfer_sz` vale 4092 si no se configura.
- Sobrecoste por transacción: **26 µs** por interrupción con DMA y 11 µs en `polling` (documentación de ESP-IDF).
- **`SPI_TRANS_DMA_USE_PSRAM`** permite hacer DMA directo desde PSRAM, con unos 7 µs de espera extra por transacción. Comparte el bus con la caché, así que puede fallar por *underflow* si la CPU está usando la PSRAM a la vez.

El cálculo usa 4 bits por ciclo de reloj, una cabecera de 3 bytes y una transacción de 26 µs por cada 32 KiB. El BT817 admite escrituras continuas en RAM_G sin esperas.

| Datos | Bytes | 20 MHz | **26,67 MHz** (máx. real) | 30 MHz (teórico) | fps máx. a 26,67 MHz |
|---|---:|---:|---:|---:|---:|
| 1 KiB | 1 024 | 0,13 ms | 0,10 ms | 0,09 ms | – |
| 8 KiB (una lista de visualización llena) | 8 192 | 0,85 ms | 0,64 ms | 0,57 ms | – |
| 32 KiB (una transacción DMA) | 32 768 | 3,30 ms | 2,48 ms | 2,21 ms | – |
| 64 KiB | 65 536 | 6,61 ms | 4,97 ms | 4,42 ms | – |
| 320×240 a 8 bpp (L8/PALETTED8) | 76 800 | 7,76 ms | 5,84 ms | 5,20 ms | 171 |
| 400×240 a 8 bpp | 96 000 | 9,68 ms | 7,28 ms | 6,48 ms | 137 |
| 320×240 RGB565 | 153 600 | 15,5 ms | 11,7 ms | 10,4 ms | 86 |
| **400×240 RGB565** | 192 000 | 19,4 ms | **14,6 ms** | 13,0 ms | **69** |
| 760×456 a 8 bpp (imagen de Fdf) | 346 560 | 35,0 ms | 26,3 ms | 23,4 ms | 38 |
| 800×480 a 8 bpp | 384 000 | 38,7 ms | 29,1 ms | 25,9 ms | 34 |
| 760×456 RGB565 | 693 120 | 69,9 ms | 52,6 ms | 46,8 ms | 19 |
| **800×480 RGB565** | 768 000 | 77,4 ms | **58,2 ms** | 51,8 ms | **17** |

Regla rápida: **t(ms) ≈ 2·N / f(kHz)**, más unos 26 µs por cada 32 KiB. A 26,67 MHz salen **13,3 MB/s** de pico.

Con el driver de la rama de referencia (bloques de 512 B en `polling`), cada bloque cuesta unos 51 µs en lugar de 38 µs. El ancho de banda efectivo baja a 10 MB/s y **la CPU queda bloqueada mientras se sube**.

---

## 4. Estrategias de port

Qué es cada una:

- **(a) Capa de compatibilidad.** Implementa la API de MLX42 sobre el BT817. Las imágenes viven en PSRAM (RGBA). En cada fotograma se convierten las imágenes modificadas a RGB565 o 8 bpp y se suben a RAM_G, y una lista de visualización corta las compone, con sus instancias, transparencia y texto.
- **(a+c) Lo mismo, con ventana "virtual" de 400×240 o 320×240.** Los dos proyectos preguntan el tamaño de la ventana o del monitor, así que se adaptan solos. El BT817 escala el *bitmap* ×2 (`BITMAP_TRANSFORM` o `CMD_SCALE`, filtro NEAREST o BILINEAR).
- **(c) Render propio a baja resolución.** El juego escribe RGB565 u 8 bpp directamente en un búfer de SRAM, sin `mlx_put_pixel`, y lo envía por DMA mientras calcula el siguiente. Truco específico de raycaster: guardar el fotograma traspuesto (columna a columna) para que cada columna sea contigua en memoria, enviarlo por tiras y dejar que el BT817 lo gire 90° con la matriz del *bitmap*. Así basta con dos búferes de unos 30 KB. Hay que validar en la placa el coste de render del giro.
- **(b) BT817 nativo.** *Bitmaps* y texturas en RAM_G (o ASTC en la flash del BT817) y listas de visualización de como mucho 2 048 comandos (8 KB) por fotograma. La CPU solo calcula la lógica.

### 4.1 cub3D

| | (a) Compatibilidad a 800×480 | (a+c) Compatibilidad a 400×240 | (c) Render propio a 400×240 | (b) Nativo |
|---|---|---|---|---|
| QSPI por fotograma | 768 KB + minimapa 48 KB | 192 KB + minimapa 12 KB | 192 KB (RGB565) o 96 KB (8 bpp) | ≤ 8 KB de lista + FIFO |
| Tiempo QSPI (20 / 26,67 MHz) | 82 / 62 ms | 21 / 15,5 ms | 19,4 / 14,6 ms (8 bpp: 9,7 / 7,3 ms) | < 1 ms |
| fps máx. teórico (solo QSPI) | 16 | 64 | 69 (137 en 8 bpp), limitado a 59,3 por el panel | 59,3 |
| CPU por fotograma (1 núcleo) | Render 219–307 ms + PSRAM 19–38 ms + conversión 29 ms | Original: 69–91 + 5–10 + 7 ms. En `float`: 43–65 + 12–17 ms | **10–17 ms** (*opt*). Con 2 núcleos, 6–9 ms | Rayos 1,9 ms + lista ≈ 0,5 ms |
| **fps realistas** | **3–4** | **9–12** (original), **12–18** (`float`), ≈ 20–28 en `float` con 2 núcleos | **50–59** (vsync) con color; 45–59 con suelo texturizado | 59 si el BT817 aguanta el render (sin medir) |
| Carga de CPU | 100 % | 100 % | 60–100 % de un núcleo, o 2×35–55 % | ≈ 15 % de un núcleo |
| SRAM interna | 64 KB (DMA) | 64 KB | 188 KB de búfer, o 2×30 KB por tiras | < 50 KB |
| PSRAM | ≈ 2,4 MB | ≈ 1,2 MB | ≈ 0,5 MB (texturas) | ≈ 0,1 MB |
| RAM_G (1 MB) | 768 + 48 KB: **sin doble búfer** (hay *tearing*) | 2×(192+12) KB = 408 KB | 2–3 × 188 KB | Texturas 29×8 KB = 232 KB + fuentes |
| Cambios en cub3D | ≈ 150–200 líneas (5 %): ventana, GLFW, `exit`, rutas, inicialización, entradas | Lo mismo + paso a `float` (≈ 30 sitios) | + reescribir el dibujo de columnas, suelo/techo, sprites y minimapa (≈ 400 líneas, 11 %) | Reescribir todo el dibujo (≈ 650 líneas, 18 %) |
| Código nuevo | Capa de compatibilidad (orden de 1 500–2 500 líneas) | Lo mismo | Driver de subida por DMA y bucle de juego | Generador de listas de visualización y conversor de texturas |
| Limitaciones | Inviable | Jugable pero lento | – | Suelo/techo **sin textura**; cada columna de pared es una tira de *bitmap*: ≈ 5 comandos × 320–400 columnas, al borde de los 2 048 comandos |

### 4.2 Fdf

| | (a) Compatibilidad a 760×456 | (a) con 8 bpp (PALETTED8) | (c) 380×228 a 8 bpp | (b) Nativo (`LINE_STRIP`) |
|---|---|---|---|---|
| QSPI por redibujo | 693 KB (52,6 ms) | 347 KB (26,3 ms) | 87 KB (6,6 ms) | ≤ 8 KB |
| Vista estática | **0 B**: solo se sube al cambiar | 0 B | 0 B | Lista fija |
| Rotación automática, mapa 42 | ≈ 14–19 fps (limitan la CPU y el QSPI) | ≈ 14–19 fps con un núcleo; 23–38 con dos | ≈ 50–59 fps (estimado) | **59 fps** |
| Rotación, 100-6 / mars | ≈ 3,5 / 2 fps (`double`), ≈ 8 / 7 fps (`float`) | Igual: limita la CPU | Del orden de ×2, por la mitad de píxeles (estimado) | Solo con nivel de detalle: mostrar 1 de cada 4 filas y columnas |
| Rotación, t1 | ≈ 1 fps (`double`), ≈ 3 fps (`float`) | Igual | ≈ 5–7 fps (estimado) | Solo con nivel de detalle |
| Límite de mapa | **≤ 200×200** por memoria: 64 B por punto. 500×500 no cabe | Igual | Igual | ≈ 1 000 puntos por fotograma sin cambios de color; ≈ 500 con un color por segmento |
| PSRAM | 4,3–6,9 MB. Quitando la leyenda: −2 MB | Igual | Menos | Matriz únicamente |
| RAM_G | 693 KB + leyenda (L4 de 500×500 = 125 KB) | 2×347 KB + 125 KB | 2×87 KB | Casi nada |
| Cambios en Fdf | ≈ 60–100 líneas (5–8 %): ventana, leyenda, ruta del directorio, entradas, `exit` | Lo mismo + paleta de 6 colores | + resolución | Sustituir Bresenham y `display_*` por la generación de la lista (≈ 200 líneas, 15 %) |

### 4.3 Comparativa general

| Criterio | (a) Compatibilidad | (b) Nativo | (c) Baja resolución |
|---|---|---|---|
| Esfuerzo en el juego | Mínimo | Alto (reescribir el render) | Medio (solo los bucles calientes) |
| Reutilizable para otros proyectos de 42 (so_long, fract-ol…) | **Sí**, la misma capa sirve | Por juego | Por juego |
| Rendimiento | Limitado por QSPI y PSRAM | El mejor: 59 fps casi sin CPU | Bueno: 50–59 fps |
| Encaja con | Fdf, fract-ol a baja resolución | **so_long** y juegos de tiles: 375 tiles de 32×32 caben en ≈ 400 comandos | cub3D y cualquier render por software |

---

## 5. Entradas, ficheros y audio

### 5.1 Del teclado y el ratón a los botones y joysticks

Controles de OCX: cruceta, X, O, □, △, T_L, T_R, SELECT, HOME, VOL± (reservados para el sistema), L3/R3 (GPIO8/47), dos joysticks analógicos (ADC1) y pantalla táctil capacitiva gestionada por el BT817.

| Acción original | Tecla | Propuesta en OCX |
|---|---|---|
| **cub3D**: avanzar / retroceder | W / S | Joystick izquierdo en Y (umbral de ±30 %), o cruceta ↑/↓ |
| cub3D: desplazamiento lateral | A / D | Joystick izquierdo en X, o cruceta ←/→ |
| cub3D: girar | ← / → | Joystick derecho en X (proporcional), o T_L / T_R |
| cub3D: girar con el ratón (`cursor_hook`, Δx × `delta_time`) | ratón | Joystick derecho en X convertido en Δx virtual; o arrastrar en la pantalla táctil |
| cub3D: abrir o cerrar puerta | P | X |
| cub3D: capturar el ratón | M | Sobra (SELECT, si se quiere conservar) |
| cub3D: salir | ESC o cerrar ventana | HOME |
| **Fdf**: trasladar | flechas (con `MLX_REPEAT`) | Cruceta con autorrepetición sintética (≈ 500 ms y después 30 Hz, como GLFW) |
| Fdf: rotar en X / Y / Z | Q-W / A-S / Z-X | Joystick derecho en Y / joystick derecho en X / T_L-T_R |
| Fdf: zoom | rueda del ratón | Joystick izquierdo en Y, o pellizco en la pantalla táctil |
| Fdf: rotación automática, siguiente mapa, leyenda, vista de primer ángulo, reiniciar | SPACE, TAB, O, P, R | X, SELECT, △, □, O |
| Fdf: salir | ESC | HOME |

Coste: leer GPIOA y GPIOB del MCP23017 a 400 kHz lleva unos 110 µs, solo cuando salta INTA (GPIO17, con IOCON.MIRROR=1). Los 4 ejes del ADC1 llevan 40–120 µs por fotograma. En total, menos del 1 % de un fotograma de 16,9 ms.

### 5.2 Dónde guardar mapas y texturas

| Opción | Capacidad | A favor | En contra | Para qué |
|---|---|---|---|---|
| **LittleFS en la flash del ESP32** (16 MB; la app ocupa < 3 MB) | 8–12 MB | Funciona con `open`/`read`/`opendir` sin tocar el parseo de 42 (solo las rutas). Se puede escribir (partidas guardadas) | Mientras se escribe en flash la PSRAM no es accesible. Más lento que la memoria | **Mapas `.cub`/`.fdf`** y texturas PNG (o ya convertidas) para cub3D en (a) y (c) |
| Incrustado en el binario (`EMBED_FILES`) | Partición de la app | Sin sistema de ficheros; acceso mapeado en memoria | No respeta la API de ficheros de 42; hay que recompilar para cambiar un mapa | Recursos fijos |
| **Flash W25Q128 del BT817** (16 MB) | 16 MB | Llevar recursos a RAM_G con `CMD_FLASHREAD` no gasta QSPI del ESP32. El **ASTC se dibuja directamente desde la flash** | Formatos del BT817 (conversión fuera de línea). Se programa a través del ESP32 (`CMD_FLASHUPDATE`) o con una herramienta | Texturas y *sprites* de la estrategia (b), fuentes, fondos |

Las texturas que cub3D muestrea por CPU, en (a) y (c), tienen que estar en la memoria del ESP32. Leerlas de vuelta desde el BT817 no tiene sentido. Conviene convertirlas antes a RGB565 u 8 bpp con paleta: se ahorran los 170 ms de decodificación PNG al arrancar y la mitad o tres cuartos de la memoria.

### 5.3 Audio

Ninguno de los dos proyectos tiene sonido: MLX42 no ofrece audio. El BT817 permite dos cosas, mezcladas por la salida PWM (AUDIO_L, que va al PAM8302A con ~SD en GPIO21):

- **Sintetizador** (`REG_SOUND`, `REG_PLAY`): efectos integrados (seno, cuadrada, sierra, triángulo, piano, órgano, campanas, clics, caja, *hi-hat*…) con altura por nota MIDI. Es monofónico y no gasta RAM ni QSPI. Encaja con pasos, puertas o recoger llaves en cub3D.
- **Reproducción de muestras desde RAM_G** (`REG_PLAYBACK_*`): PCM de 8 bits con signo, µ-law o **IMA ADPCM de 4 bits**, un canal, frecuencia programable y bucle. Un segundo a 22 kHz en ADPCM ocupa 11 KB. Para música, un búfer circular en RAM_G rellenado a 11 KB/s gasta menos del 0,1 % del QSPI.
- **Volumen**: `REG_VOL_SOUND` y `REG_VOL_PB` **≤ 76 de 255 (~30 %)**, según los datos verificados.

---

## 6. Conclusiones

### 6.1 cub3D

- **Portable: sí, con la estrategia (c)**, o con (a+c) como paso intermedio.
- **fps esperados**: 50–59 a 400×240 o 320×240 con el bucle de columna reescrito y en `float`. Con suelo texturizado y un solo núcleo puede quedar en 45–59. Sin reescribir el render y con todo en `float`: 12–18 fps (≈ 20–28 con dos núcleos). Tal cual: 9–12.
- **Cuellos de botella, por orden**:
  1. CPU por píxel: la llamada a `mlx_put_pixel` y dos divisiones por píxel de suelo o techo.
  2. `double` en los rayos.
  3. QSPI: 14,6 ms por fotograma RGB565 a 400×240.
  4. PSRAM, si el búfer es RGBA.
- **Se mantiene**: todo el parseo y la validación (50 % del código), la lógica del jugador y las colisiones, el DDA de los rayos y la lógica de sprites y puertas.
- **Se reescribe**: la creación de la ventana y las llamadas a GLFW; el dibujo de columnas, suelo/techo, sprites y minimapa (≈ 400 líneas); la entrada (joysticks en lugar de teclado y ratón); la salida (`exit`); las rutas.
- **Riesgos**:
  - El puntero sin inicializar de §2.9: se cuelga con `-Og`.
  - *Tearing* si no hay doble búfer en RAM_G.
  - DMA desde PSRAM que compite con la CPU.
  - El coste en el BT817 del escalado ×2, o del giro de 90° si se usa el truco de transponer.

### 6.2 Fdf

- **Portable: sí, con (a)** usando 8 bpp para la imagen principal y sustituyendo la leyenda PNG por texto nativo, más **(b)** para mapas pequeños si se quiere 59 fps.
- **fps esperados**:
  - Vistas estáticas, traslaciones y zoom: cada redibujo cuesta lo que tarda la CPU más 26–53 ms de subida.
  - Rotación automática: 14–19 fps en mapas pequeños con un núcleo (hasta 38 con dos núcleos y 8 bpp); 1–8 fps en los de 10 000 a 40 000 puntos, según sea `double` o `float`.
  - **`julia` y `elem-fract` no caben** en memoria (16 MB de matriz).
- **Cuellos de botella**: la `memset` de 1,39 MB y la conversión por fotograma, la trigonometría en `double` por punto y el QSPI.
- **Se mantiene**: la lectura del mapa (lenta: `t1` tarda 3,3 s), las matemáticas de rotación y proyección y Bresenham.
- **Se reescribe**: `manage_window.c` (GLFW y leyenda), la ruta de `swap_map`, los hooks de entrada y, opcionalmente, el cambio de `double` a `float` (×3–5 en los mapas grandes).

### 6.3 Evaluación general del hardware

| Tipo de juego | ¿60 fps? | Por qué |
|---|---|---|
| Tiles y *sprites* con el BT817 nativo (so_long, plataformas, puzles) | **Sí, con margen** | Lista de ≤ 2 048 comandos: subida < 0,7 ms, CPU < 5 %. Recursos en RAM_G o en la flash del BT817 |
| Render por software a 320×240 o 400×240 y escalado ×2 (raycaster, *shooters* retro) | **Sí, justo**, con bucles optimizados y dos núcleos | QSPI de 6–15 ms y CPU de 8–17 ms, solapados |
| Render por software a 800×480 | **No** | QSPI: 17 fps como máximo en RGB565 y 34 en 8 bpp. Además, 768 KB de RAM_G no dejan sitio para un doble búfer |
| Alambre (Fdf) con líneas nativas | Sí, hasta unos 1 000 vértices | Tamaño de la lista de visualización |

El techo real lo fijan, por este orden: el **QSPI** (13,3 MB/s a 26,67 MHz; los 30 MHz no son alcanzables con un divisor de 80 MHz), la **CPU con `double`** (factor 13–23 por operación) y la **PSRAM** (unos 40 MB/s por la caché). La RAM_G de 1 MB y la lista de visualización de 8 KB limitan al estilo nativo. Una consola con BT817 está pensada para que sea el BT817 quien dibuja.

### 6.4 Qué medir en la placa para confirmarlo

| # | Medida | Resultado esperado | Si sale mal |
|---|---|---|---|
| 1 | Escribir 192 000 B y 768 000 B en RAM_G a 20 y 26,67 MHz, con DMA de 32 KiB y por interrupción (`esp_timer`); verificar con `CMD_MEMCRC` | 19,4 / 14,6 ms y 77 / 58 ms; 0 errores en 1 000 subidas | Bajar a 20 MHz; revisar el zócalo del DevKitC y las pistas con un analizador |
| 2 | Lo mismo desde PSRAM con `SPI_TRANS_DMA_USE_PSRAM`, con y sin la CPU usando la PSRAM | Sin `SPI_TRANS_DMA_TX_FAIL` | Pasar por búferes de SRAM |
| 3 | Las cuatro variantes del raycaster de cub3D (orig, float, double, opt) y el fotograma de Fdf, con `esp_cpu_get_cycle_count` a 240 MHz | Dentro de ±30 % de §3.2 y §3.3, con CPI entre 1,2 y 1,8 | Recalibrar las tablas de §4 |
| 4 | Ancho de banda de la PSRAM: `memset` y `memcpy` de 1 MiB entre SRAM y PSRAM; escritura por columnas en un búfer RGBA | 40–80 MB/s | Penalización mayor para (a) |
| 5 | `REG_UNDERRUN` del BT817 con: un *bitmap* de 400×240 escalado ×2 (NEAREST y BILINEAR), un *bitmap* girado 90°, 320–400 tiras (opción b de cub3D) y N `LINE_STRIP` (Fdf) | `REG_UNDERRUN` = 0 a 59,3 Hz | Reducir primitivas por línea; `REG_AH_HCYCLE_MAX` (hsync adaptativo) si el panel lo tolera |
| 6 | `REG_FRAMES` y latencia de `DLSWAP_FRAME`; *tearing* con 2 y 3 búferes | 59,3 Hz; cambio en ≤ 1 fotograma | – |
| 7 | Latencia de entrada: de INTA del MCP23017 al estado del botón; ruido de los ejes del ADC | < 1 ms; ruido ≤ 150 cuentas (prueba de puesta en marcha) | – |
| 8 | Audio PCM/ADPCM y sintetizador con volumen ≤ 76 | Sin saturación en el PAM8302A | Bajar el volumen |
| 9 | LittleFS: lectura de `t1.fdf` y decodificación de las 29 texturas al arrancar | ≈ 3–4 s y ≈ 0,2 s | Convertir los recursos antes |
| 10 | Temperatura y consumo a 240 MHz con dos núcleos y retroiluminación | – | – |

---

## 7. Anexos

### 7.1 Datos en bruto (`datos/`)

Son salidas de medida, sin código:

| Fichero | Contenido |
|---|---|
| `linux_cub3d.txt` | Contadores por mapa y resolución (píxeles, `memset`, heap, texturas) de cub3D en Linux |
| `linux_fdf.txt` | Lo mismo para Fdf con rotación automática, a 800×480 y 1920×1080 |
| `qemu_esp32s3_bench.txt` | Banco en QEMU con `-icount`: calibración, coste por operación, cub3D, Fdf, conversión, PNG y lectura de mapas |
| `qemu_coremark.txt` | CoreMark en QEMU (instrucciones por iteración), base del CPI = 1,40 |
| `valgrind_cub3d.txt` | La lectura sin inicializar de §2.9 (con `-O0`) y la ejecución limpia con `-Ofast` |

### 7.2 Cómo se obtuvieron (para repetirlo)

- **Linux.** Se compiló cada proyecto con su Makefile usando `CC=clang`. El enlace se repitió con un objeto de instrumentación y `--wrap` sobre las funciones de §1. Se ejecutó en Xvfb con una pantalla de 800×480 o 1920×1080; para cub3D se forzó el tamaño de ventana interceptando `mlx_init`. Las teclas se simularon por número de fotograma.
- **ESP32-S3.** Se usó un proyecto de ESP-IDF v5.5.6 con el raycaster de cub3D y el fotograma de Fdf transcritos de los fuentes originales, compilados con `-Ofast` como en sus Makefile. Configuración: 240 MHz, `-O2`, PSRAM octal a 80 MHz, caché de datos de 64 KB. Se ejecutó en QEMU (`-M esp32s3 -m 32M`, PSRAM octal, `-icount shift=0,sleep=off`). Las instrucciones son el tiempo de `esp_timer` × 1 000. Los milisegundos son instrucciones × 1,4 / 240 MHz.
- **QSPI.** Cálculo con el algoritmo de divisores de `spi_ll_master_cal_clock` (esp32s3) y los tiempos por transacción de la documentación de `spi_master`.

### 7.3 Fuentes externas

- Hoja de datos del ESP32-S3: 613,86 CoreMark a 240 MHz en un núcleo.
- ESP-IDF v5.5.6: `idf_performance_target.h` (ciclos de división y raíz), `spi_ll.h`, `spi_master.c`, `spi_master.rst`, `external-ram.rst`, `vfs.rst` y `syscalls.c` (`_exit` → `abort`).
- Constantes del BT817 (mapa de memoria, formatos, registros de audio, `REG_UNDERRUN`, `REG_AH_HCYCLE_MAX`, límite de 11 MHz en el arranque) contrastadas con la biblioteca EVE de R. Riedel (`FT800-FT813`). La hoja de datos de Bridgetek no se pudo descargar: el proxy bloquea el dominio.
- PSRAM: datos anecdóticos de los foros de Espressif (ESP32-BOX: 35 MB/s de PSRAM a PSRAM y 82 MB/s de DRAM a PSRAM; N16R8 a 80 MHz: unos 40 MB/s escribiendo). Hay que medirlo en la placa.
