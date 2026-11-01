/*
 * bt817.h — Driver mínimo del BT817 (EVE4) sobre ocx_hal.
 */
#ifndef BT817_H
#define BT817_H

#include <stdbool.h>
#include <stdint.h>
#include "ocx_hal.h"
#include "bt817_regs.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Tiempos del panel. Los nombres coinciden con los registros REG_*. */
typedef struct {
    uint16_t hsize, hcycle, hoffset, hsync0, hsync1;
    uint16_t vsize, vcycle, voffset, vsync0, vsync1;
    uint8_t pclk;     /* divisor: PCLK = reloj del sistema / pclk */
    uint8_t pclk_pol; /* 1 = datos válidos en el flanco de bajada */
    uint8_t swizzle;
    uint8_t cspread;
    uint8_t dither;
} bt817_timing_t;

/* Newhaven NHD-5.0-800480AF-ASXP(-CTP): 800×480, HSYNC 48, HBP 40, HFP 40,
 * VSYNC 3, VBP 29, VFP 13. REG_SWIZZLE = 3 porque la placa cablea R0..R7
 * del BT817 a B7..B0 del panel (y B↔R, G invertido); ver esquemático. */
extern const bt817_timing_t BT817_TIMING_NHD_50_800480;

typedef struct {
    bool use_crystal;    /* true: CLKEXT (cristal de 12 MHz) */
    uint8_t clk_mult;    /* 6 → 72 MHz; 0 → no enviar CLKSEL */
    uint32_t boot_hz;    /* SCLK antes de configurar el reloj (≤ 11 MHz) */
    uint32_t run_hz;     /* SCLK de trabajo */
    bool quad;           /* pasar a QSPI tras el arranque */
} bt817_cfg_t;

#define BT817_CFG_DEFAULT { .use_crystal = true, .clk_mult = 6, \
                            .boot_hz = 8000000, .run_hz = 20000000, .quad = true }

typedef struct {
    const ocx_hal_t *hal;
    ocx_bus_width_t width;
    uint32_t sys_hz;  /* frecuencia nominal configurada */
    uint8_t chip_id;  /* último REG_ID leído */
} bt817_t;

void bt817_init(bt817_t *dev, const ocx_hal_t *hal);

/* Acceso a memoria */
ocx_err_t bt817_host_cmd(bt817_t *dev, uint8_t cmd, uint8_t param);
ocx_err_t bt817_wr_mem(bt817_t *dev, uint32_t addr, const uint8_t *data, size_t len);
ocx_err_t bt817_rd_mem(bt817_t *dev, uint32_t addr, uint8_t *data, size_t len);
ocx_err_t bt817_wr8(bt817_t *dev, uint32_t addr, uint8_t v);
ocx_err_t bt817_wr16(bt817_t *dev, uint32_t addr, uint16_t v);
ocx_err_t bt817_wr32(bt817_t *dev, uint32_t addr, uint32_t v);
ocx_err_t bt817_rd8(bt817_t *dev, uint32_t addr, uint8_t *v);
ocx_err_t bt817_rd16(bt817_t *dev, uint32_t addr, uint16_t *v);
ocx_err_t bt817_rd32(bt817_t *dev, uint32_t addr, uint32_t *v);

/* Cabeceras de transacción (expuestas para las pruebas unitarias). */
void bt817_hdr_write(uint32_t addr, uint8_t out[3]);
void bt817_hdr_read(uint32_t addr, uint8_t out[4]);
uint8_t bt817_clksel_param(uint8_t mult);

/* Ciclo PD_N y arranque: reloj, ACTIVE, espera de REG_ID = 0x7C y de
 * REG_CPURESET = 0, REG_FREQUENCY, subida de SCLK y paso a QSPI. */
void bt817_power_cycle(bt817_t *dev, uint32_t boot_hz);
ocx_err_t bt817_boot(bt817_t *dev, const bt817_cfg_t *cfg);
ocx_err_t bt817_set_quad(bt817_t *dev, bool quad, uint32_t hz);

/* Mide la frecuencia real del reloj del sistema con REG_CLOCK frente al
 * reloj del host durante `window_ms`. */
ocx_err_t bt817_measure_clock(bt817_t *dev, uint32_t window_ms, uint32_t *hz);

/* Configura los tiempos, enciende DISP, carga una lista vacía y arranca PCLK. */
ocx_err_t bt817_display_init(bt817_t *dev, const bt817_timing_t *t);
ocx_err_t bt817_display_check(bt817_t *dev, const bt817_timing_t *t, char *why, size_t why_len);
ocx_err_t bt817_backlight(bt817_t *dev, uint8_t percent);
/* Barras rojo/verde/azul/blanco: verificación visual de REG_SWIZZLE. */
ocx_err_t bt817_test_pattern(bt817_t *dev, const bt817_timing_t *t);

/* Sonido (AUDIO_L → PAM8302A). */
ocx_err_t bt817_sound_play(bt817_t *dev, uint8_t effect, uint8_t midi_note, uint8_t volume);
ocx_err_t bt817_sound_stop(bt817_t *dev);
ocx_err_t bt817_sound_busy(bt817_t *dev, bool *busy);

#ifdef __cplusplus
}
#endif
#endif /* BT817_H */
