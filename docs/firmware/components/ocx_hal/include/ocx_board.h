/*
 * ocx_board.h — Asignación de pines de la placa OCX (Fab v1.0).
 *
 * Verificado contra hardware/ocxPrototype.kicad_sch y
 * hardware/buttons_joysticks.kicad_sch (conectores J2/J3 del DevKitC-1).
 */
#ifndef OCX_BOARD_H
#define OCX_BOARD_H

/* ---- BT817Q (EVE4) por QSPI ------------------------------------------- *
 * Son exactamente los pines IO_MUX de SPI2 (FSPI) en la ESP32-S3, así que
 * el bus no pasa por la matriz GPIO.                                      */
#define OCX_PIN_EVE_SCLK   12 /* FSPICLK  → BT817 SCK            */
#define OCX_PIN_EVE_IO0    11 /* FSPID    → BT817 MOSI/IO0       */
#define OCX_PIN_EVE_IO1    13 /* FSPIQ    → BT817 MISO/IO1       */
#define OCX_PIN_EVE_IO2    14 /* FSPIWP   → BT817 GPIO0/IO2      */
#define OCX_PIN_EVE_IO3     9 /* FSPIHD   → BT817 GPIO1/IO3      */
#define OCX_PIN_EVE_CS     10 /* FSPICS0  → BT817 CS_N           */
#define OCX_PIN_EVE_PD_N    4 /* salida   → BT817 PD_N           */
#define OCX_PIN_EVE_INT_N   5 /* entrada  ← BT817 INT_N          */

/* ---- MCP23017 (14 botones) -------------------------------------------- */
#define OCX_PIN_I2C_SCL    15
#define OCX_PIN_I2C_SDA    16
#define OCX_PIN_MCP_INT    17 /* INTA; INTB sin conectar → IOCON.MIRROR = 1 */
#define OCX_PIN_MCP_RESET  18 /* activo a nivel bajo, pull-up 10 k (R5)      */
#define OCX_MCP_I2C_ADDR   0x20 /* A2..A0 a GND */
#define OCX_I2C_HZ         400000

/* ---- Joysticks (ADC1) y sus pulsadores -------------------------------- */
#define OCX_PIN_JOY_L_X     6 /* ADC1_CH5 */
#define OCX_PIN_JOY_L_Y     7 /* ADC1_CH6 */
#define OCX_PIN_JOY_R_X     2 /* ADC1_CH1 */
#define OCX_PIN_JOY_R_Y     1 /* ADC1_CH0 */
#define OCX_PIN_JOY_L_BTN   8 /* a GND al pulsar, pull-up interno */
#define OCX_PIN_JOY_R_BTN  47 /* a GND al pulsar, pull-up interno */

/* ---- Audio ------------------------------------------------------------- *
 * La señal sale del BT817 (AUDIO_L, PWM) al PAM8302A. GPIO21 = ~SD:
 * 1 = amplificador activo, 0 = apagado.                                    */
#define OCX_PIN_AMP_SD     21

#endif /* OCX_BOARD_H */
