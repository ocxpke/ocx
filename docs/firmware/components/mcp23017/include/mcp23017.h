/*
 * mcp23017.h — Driver del expansor I²C MCP23017 (IOCON.BANK = 0).
 */
#ifndef MCP23017_H
#define MCP23017_H

#include <stdint.h>
#include "ocx_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Registros con IOCON.BANK = 0 (A y B intercalados). */
enum {
    MCP_IODIRA = 0x00, MCP_IODIRB = 0x01,
    MCP_IPOLA = 0x02, MCP_IPOLB = 0x03,
    MCP_GPINTENA = 0x04, MCP_GPINTENB = 0x05,
    MCP_DEFVALA = 0x06, MCP_DEFVALB = 0x07,
    MCP_INTCONA = 0x08, MCP_INTCONB = 0x09,
    MCP_IOCON = 0x0A,
    MCP_GPPUA = 0x0C, MCP_GPPUB = 0x0D,
    MCP_INTFA = 0x0E, MCP_INTFB = 0x0F,
    MCP_INTCAPA = 0x10, MCP_INTCAPB = 0x11,
    MCP_GPIOA = 0x12, MCP_GPIOB = 0x13,
    MCP_OLATA = 0x14, MCP_OLATB = 0x15,
};

#define MCP_IOCON_MIRROR (1u << 6) /* INTA = INTA | INTB */
#define MCP_IOCON_SEQOP  (1u << 5)
#define MCP_IOCON_ODR    (1u << 2)
#define MCP_IOCON_INTPOL (1u << 1)

/* Configuración que usa OCX: MIRROR = 1, INT activo a nivel bajo push-pull,
 * direccionamiento secuencial (SEQOP = 0). */
#define OCX_MCP_IOCON    MCP_IOCON_MIRROR

typedef struct {
    const ocx_hal_t *hal;
    uint8_t addr;
    int reset_pin; /* -1 si no hay */
} mcp23017_t;

void mcp23017_init(mcp23017_t *m, const ocx_hal_t *hal, uint8_t addr, int reset_pin);
void mcp23017_hw_reset(mcp23017_t *m);
ocx_err_t mcp23017_write_reg(mcp23017_t *m, uint8_t reg, uint8_t v);
ocx_err_t mcp23017_read_reg(mcp23017_t *m, uint8_t reg, uint8_t *v);
/* Lee el par A/B (reg A en el byte bajo). */
ocx_err_t mcp23017_read_pair(mcp23017_t *m, uint8_t reg_a, uint16_t *v);

/* Reset + todo entradas con pull-up, interrupción por cambio en los pines
 * de `int_mask` (bit 0..7 = GPA, 8..15 = GPB) e IOCON = OCX_MCP_IOCON.
 * Verifica por relectura IOCON e IODIR. */
ocx_err_t mcp23017_setup_inputs(mcp23017_t *m, uint16_t int_mask);

/* Estado de los 16 pines (1 = nivel alto). */
ocx_err_t mcp23017_read_gpio(mcp23017_t *m, uint16_t *v);
/* Lee INTF y INTCAP (lo que libera la línea INT). */
ocx_err_t mcp23017_read_int(mcp23017_t *m, uint16_t *flags, uint16_t *captured);

#ifdef __cplusplus
}
#endif
#endif
