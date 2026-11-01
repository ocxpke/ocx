/*
 * sim.h — Periféricos simulados de OCX para ejecutar el firmware en un PC.
 *
 * Modelos (a nivel de registro y de protocolo, no eléctrico):
 *   - BT817: comandos de host, CLKEXT/CLKSEL, REG_ID tras ACTIVE, REG_CPURESET,
 *     REG_CLOCK y REG_FRAMES según el tiempo simulado, REG_SPI_WIDTH (SPI/QSPI),
 *     REG_SOUND/REG_PLAY.
 *   - MCP23017 (BANK = 0): registros, pull-ups, IPOL, interrupción por cambio
 *     con IOCON.MIRROR, borrado al leer GPIO/INTCAP, ~RESET.
 *   - ADC de los cuatro ejes con ruido, GPIO de L3/R3 y ~SD del amplificador.
 *   - Tiempo virtual: delay_ms avanza el reloj sin esperar.
 * Se pueden inyectar averías (sim_faults_t) para probar los diagnósticos.
 */
#ifndef OCX_SIM_H
#define OCX_SIM_H

#include <stdbool.h>
#include <stdint.h>
#include "ocx_hal.h"

typedef struct {
    bool eve_absent;        /* BT817 sin alimentar / no responde */
    bool no_crystal;        /* cristal de 12 MHz que no oscila */
    int32_t xtal_ppm;       /* error del cristal */
    int32_t intosc_ppm;     /* error del oscilador interno */
    bool qspi_io23_broken;  /* IO2/IO3 abiertos: QSPI corrompe datos */
    bool pclk_dead;         /* REG_FRAMES no avanza */
    bool mcp_absent;        /* NACK en 0x20 */
    bool mcp_no_mirror;     /* INTA solo refleja el puerto A */
    uint32_t stuck_buttons; /* máscara OCX_BTN_*: siempre pulsados */
    uint32_t dead_buttons;  /* máscara OCX_BTN_*: nunca se cierran */
    int axis_fault[4];      /* 0 = ok, 1 = a GND, 2 = a 3V3 */
    bool amp_unwired;       /* GPIO21 no llega al ~SD del PAM8302A */
} sim_faults_t;

typedef struct sim sim_t;

sim_t *sim_create(const sim_faults_t *faults);
void sim_destroy(sim_t *s);
ocx_hal_t sim_hal(sim_t *s);

/* Entradas del "mundo físico" */
void sim_press(sim_t *s, uint32_t buttons_mask);
void sim_release(sim_t *s, uint32_t buttons_mask);
void sim_set_axis(sim_t *s, int axis, int raw);

/* Operador virtual: reacciona a los mensajes de las pruebas
 * (bu_cfg_t.prompt = sim_operator_prompt, user = sim). */
void sim_operator_prompt(void *sim, const char *msg);
void sim_operator_enable(sim_t *s, bool on);

/* Observación del estado interno (para las pruebas unitarias) */
uint64_t sim_time_us(const sim_t *s);
uint32_t sim_eve_reg(const sim_t *s, uint32_t addr);
int sim_eve_width(const sim_t *s);
uint32_t sim_eve_sys_hz(const sim_t *s);
uint32_t sim_eve_dl_word(const sim_t *s, unsigned index);
int sim_audible_beeps(const sim_t *s);
uint8_t sim_mcp_reg(const sim_t *s, uint8_t reg);
int sim_gpio_out(const sim_t *s, int pin);
uint32_t sim_host_hz(const sim_t *s);
int sim_host_width(const sim_t *s);

#endif
