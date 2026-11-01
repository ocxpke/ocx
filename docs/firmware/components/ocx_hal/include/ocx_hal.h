/*
 * ocx_hal.h — Capa de abstracción de hardware (HAL) de la consola OCX.
 *
 * Los drivers (BT817, MCP23017, entrada, pruebas de puesta en marcha) solo
 * conocen esta interfaz. Hay dos implementaciones:
 *   - main/hal_esp32s3.c  → ESP-IDF sobre la ESP32-S3-DevKitC-1-N16R8.
 *   - host/sim/sim_hal.c  → PC, con BT817, MCP23017, ADC y GPIO simulados.
 *
 * Todas las funciones son síncronas. `ctx` es el estado privado de cada
 * implementación.
 */
#ifndef OCX_HAL_H
#define OCX_HAL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    OCX_OK = 0,
    OCX_ERR_IO = -1,      /* fallo de bus (NACK, error SPI...) */
    OCX_ERR_TIMEOUT = -2, /* el periférico no respondió a tiempo */
    OCX_ERR_ARG = -3,     /* argumento inválido */
    OCX_ERR_STATE = -4,   /* estado inesperado (p. ej. REG_ID incorrecto) */
} ocx_err_t;

/* Ancho del bus del BT817: 1 = SPI simple, 4 = QSPI. */
typedef enum {
    OCX_BUS_SINGLE = 1,
    OCX_BUS_QUAD = 4,
} ocx_bus_width_t;

typedef struct ocx_hal {
    void *ctx;

    /* ---- BT817 (SPI/QSPI) ----------------------------------------------
     * eve_write: una transacción con CS bajo durante todo el envío.
     * eve_read : envía `hdr` y a continuación lee `rx_len` bytes, todo en
     *            la misma transacción (half-duplex).
     * eve_set_bus: ancho de bus y frecuencia de reloj para las siguientes
     *            transacciones. */
    ocx_err_t (*eve_write)(void *ctx, const uint8_t *data, size_t len);
    ocx_err_t (*eve_read)(void *ctx, const uint8_t *hdr, size_t hdr_len,
                          uint8_t *rx, size_t rx_len);
    ocx_err_t (*eve_set_bus)(void *ctx, ocx_bus_width_t width, uint32_t hz);

    /* ---- GPIO (número de GPIO de la ESP32-S3, ver ocx_board.h) --------- */
    void (*gpio_write)(void *ctx, int pin, int level);
    int (*gpio_read)(void *ctx, int pin);

    /* ---- I²C (dirección de 7 bits) ------------------------------------- */
    ocx_err_t (*i2c_write)(void *ctx, uint8_t addr, const uint8_t *data, size_t len);
    ocx_err_t (*i2c_write_read)(void *ctx, uint8_t addr, const uint8_t *w, size_t wlen,
                                uint8_t *r, size_t rlen);

    /* ---- ADC: lectura cruda de 12 bits (0..4095) del GPIO indicado ------ */
    ocx_err_t (*adc_read)(void *ctx, int pin, int *raw);

    /* ---- Tiempo --------------------------------------------------------- */
    void (*delay_ms)(void *ctx, uint32_t ms);
    uint64_t (*now_us)(void *ctx);
} ocx_hal_t;

/* Envoltorios cortos para que los drivers lean mejor. */
static inline void ocx_delay_ms(const ocx_hal_t *h, uint32_t ms) { h->delay_ms(h->ctx, ms); }
static inline uint64_t ocx_now_us(const ocx_hal_t *h) { return h->now_us(h->ctx); }
static inline void ocx_gpio_write(const ocx_hal_t *h, int pin, int lvl) { h->gpio_write(h->ctx, pin, lvl); }
static inline int ocx_gpio_read(const ocx_hal_t *h, int pin) { return h->gpio_read(h->ctx, pin); }

const char *ocx_err_str(ocx_err_t e);

#ifdef __cplusplus
}
#endif
#endif /* OCX_HAL_H */
