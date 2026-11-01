/*
 * ocx_bringup.h — Pruebas de puesta en marcha de OCX, por bloques.
 *
 *   1. EVE_ID     BT817: arranque con cristal, REG_ID = 0x7C en SPI y QSPI.
 *   2. EVE_CLOCK  Cristal: frecuencia real medida con REG_CLOCK (72 MHz).
 *   3. DISPLAY    Tiempos NHD 800×480, REG_SWIZZLE = 3, REG_FRAMES avanza,
 *                 barras de color para revisión visual.
 *   4. BUTTONS    MCP23017: comunicación, reposo, los 16 botones e INTA
 *                 (IOCON.MIRROR) con ambos puertos.
 *   5. JOYSTICKS  Centro, ruido y recorrido de los cuatro ejes (ADC1).
 *   6. BEEP       Pitido del BT817 con el PAM8302A habilitado (GPIO21).
 *
 * Las pruebas solo usan ocx_hal, así que se ejecutan igual en la placa y en
 * el PC con los periféricos simulados.
 */
#ifndef OCX_BRINGUP_H
#define OCX_BRINGUP_H

#include <stdbool.h>
#include <stdint.h>
#include "bt817.h"
#include "ocx_hal.h"
#include "ocx_input.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    BU_EVE_ID,
    BU_EVE_CLOCK,
    BU_DISPLAY,
    BU_BUTTONS,
    BU_JOYSTICKS,
    BU_BEEP,
    BU_COUNT
} bu_block_t;

typedef enum { BU_NOT_RUN, BU_PASS, BU_WARN, BU_FAIL, BU_SKIP } bu_status_t;

typedef struct {
    bool interactive;              /* pide acciones al operador */
    uint32_t clock_window_ms;      /* ventana de medida de REG_CLOCK */
    uint32_t clock_tol_ppm;        /* tolerancia admitida */
    uint32_t button_timeout_ms;
    uint32_t joystick_timeout_ms;
    uint32_t confirm_timeout_ms;   /* confirmación del pitido con X/O */
    uint32_t beep_ms;
    bt817_cfg_t eve;
    const bt817_timing_t *timing;
    /* Mensajes al operador (puede ser NULL). */
    void (*prompt)(void *user, const char *msg);
    void *user;
} bu_cfg_t;

typedef struct {
    bu_status_t status;
    char detail[200];
} bu_result_t;

typedef struct {
    const ocx_hal_t *hal;
    bu_cfg_t cfg;
    bt817_t eve;
    ocx_input_t input;
    bool eve_ok;
    bool input_ok;
    uint32_t measured_hz;
    uint32_t fps;
    bu_result_t res[BU_COUNT];
} bu_ctx_t;

void bu_default_cfg(bu_cfg_t *cfg);
void bu_init(bu_ctx_t *ctx, const ocx_hal_t *hal, const bu_cfg_t *cfg);
bu_status_t bu_run_block(bu_ctx_t *ctx, bu_block_t b);
/* Ejecuta todos los bloques en orden; devuelve el número de FAIL. */
int bu_run_all(bu_ctx_t *ctx);

const char *bu_block_name(bu_block_t b);
const char *bu_status_name(bu_status_t s);
/* Una línea del informe ("[PASS] EVE_ID  ...") */
void bu_format_line(const bu_ctx_t *ctx, bu_block_t b, char *buf, size_t len);

#ifdef __cplusplus
}
#endif
#endif
