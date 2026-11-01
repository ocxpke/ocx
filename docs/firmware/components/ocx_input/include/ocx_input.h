/*
 * ocx_input.h — Botones (MCP23017 + pulsadores de los joysticks) y ejes.
 */
#ifndef OCX_INPUT_H
#define OCX_INPUT_H

#include <stdbool.h>
#include <stdint.h>
#include "ocx_hal.h"
#include "mcp23017.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Bits 0..15 = pin del MCP23017 (GPA0..GPA7, GPB0..GPB7), según
 * hardware/buttons_joysticks.kicad_sch. Bits 16..17 = pulsadores de los
 * joysticks (GPIO de la ESP32-S3). */
typedef enum {
    OCX_BTN_T_L   = 1u << 0,  /* GPA0  SW1  gatillo izquierdo */
    OCX_BTN_A_UP  = 1u << 1,  /* GPA1  SW2  cruceta arriba    */
    OCX_BTN_A_R   = 1u << 2,  /* GPA2  SW3  cruceta derecha   */
    OCX_BTN_A_L   = 1u << 3,  /* GPA3  SW4  cruceta izquierda */
    OCX_BTN_A_DW  = 1u << 4,  /* GPA4  SW5  cruceta abajo     */
    OCX_BTN_SLCT  = 1u << 5,  /* GPA5  SW6  select            */
    OCX_BTN_VOL_M = 1u << 6,  /* GPA6  SW7  volumen −         */
    /* GPA7 sin conectar */
    OCX_BTN_VOL_P = 1u << 8,  /* GPB0  SW8  volumen +         */
    OCX_BTN_HOME  = 1u << 9,  /* GPB1  SW9  home              */
    OCX_BTN_X     = 1u << 10, /* GPB2  SW10 X                 */
    OCX_BTN_O     = 1u << 11, /* GPB3  SW11 círculo           */
    OCX_BTN_C     = 1u << 12, /* GPB4  SW12 cuadrado          */
    OCX_BTN_T     = 1u << 13, /* GPB5  SW13 triángulo         */
    OCX_BTN_T_R   = 1u << 14, /* GPB6  SW15 gatillo derecho   */
    /* GPB7 sin conectar */
    OCX_BTN_L3    = 1u << 16, /* GPIO8  pulsador joystick izquierdo */
    OCX_BTN_R3    = 1u << 17, /* GPIO47 pulsador joystick derecho   */
} ocx_button_t;

#define OCX_MCP_BUTTON_MASK 0x7F7Fu                 /* pines del MCP con botón */
#define OCX_ALL_BUTTONS     (OCX_MCP_BUTTON_MASK | OCX_BTN_L3 | OCX_BTN_R3)
#define OCX_BUTTON_COUNT    16

const char *ocx_button_name(uint32_t bit);
int ocx_popcount32(uint32_t v);

/* Convierte la lectura cruda del MCP (activo a nivel bajo) y de los dos
 * GPIO en la máscara de botones pulsados. */
uint32_t ocx_buttons_decode(uint16_t mcp_gpio, int l3_level, int r3_level);

/* ---- Ejes -------------------------------------------------------------- */
typedef enum { OCX_AXIS_LX, OCX_AXIS_LY, OCX_AXIS_RX, OCX_AXIS_RY, OCX_AXIS_COUNT } ocx_axis_t;

extern const int OCX_AXIS_PIN[OCX_AXIS_COUNT];
const char *ocx_axis_name(ocx_axis_t a);

typedef struct {
    int min, center, max; /* lecturas crudas 0..4095 */
    int deadzone;         /* en cuentas crudas alrededor del centro */
} ocx_axis_cal_t;

#define OCX_AXIS_CAL_DEFAULT { .min = 0, .center = 2048, .max = 4095, .deadzone = 80 }

/* −1000..1000, lineal a cada lado del centro, con zona muerta. */
int ocx_axis_normalize(const ocx_axis_cal_t *cal, int raw);

typedef struct {
    uint32_t buttons;
    int raw[OCX_AXIS_COUNT];
    int axis[OCX_AXIS_COUNT];
} ocx_input_state_t;

typedef struct {
    const ocx_hal_t *hal;
    mcp23017_t mcp;
    ocx_axis_cal_t cal[OCX_AXIS_COUNT];
} ocx_input_t;

ocx_err_t ocx_input_init(ocx_input_t *in, const ocx_hal_t *hal);
ocx_err_t ocx_input_read_buttons(ocx_input_t *in, uint32_t *buttons);
/* Media de `samples` lecturas. */
ocx_err_t ocx_input_read_axis_raw(ocx_input_t *in, ocx_axis_t a, int samples, int *raw);
ocx_err_t ocx_input_read(ocx_input_t *in, ocx_input_state_t *st);

#ifdef __cplusplus
}
#endif
#endif
