/* Pruebas del driver MCP23017 contra el modelo simulado. */
#include "mcp23017.h"
#include "ocx_board.h"
#include "ocx_input.h"
#include "sim.h"
#include "test.h"

static void test_setup_registers(void)
{
    sim_t *s = sim_create(NULL);
    ocx_hal_t h = sim_hal(s);
    mcp23017_t m;
    mcp23017_init(&m, &h, OCX_MCP_I2C_ADDR, OCX_PIN_MCP_RESET);
    CHECK_EQ(mcp23017_setup_inputs(&m, OCX_MCP_BUTTON_MASK), OCX_OK);
    CHECK_EQ(sim_mcp_reg(s, MCP_IOCON), 0x40); /* MIRROR = 1, BANK = 0, INTPOL = 0 */
    CHECK_EQ(sim_mcp_reg(s, MCP_IODIRA), 0xFF);
    CHECK_EQ(sim_mcp_reg(s, MCP_IODIRB), 0xFF);
    CHECK_EQ(sim_mcp_reg(s, MCP_GPPUA), 0xFF);
    CHECK_EQ(sim_mcp_reg(s, MCP_GPPUB), 0xFF);
    CHECK_EQ(sim_mcp_reg(s, MCP_GPINTENA), 0x7F);
    CHECK_EQ(sim_mcp_reg(s, MCP_GPINTENB), 0x7F);
    CHECK_EQ(sim_gpio_out(s, OCX_PIN_MCP_RESET), 1);
    uint16_t g = 0;
    CHECK_EQ(mcp23017_read_gpio(&m, &g), OCX_OK);
    CHECK_EQ(g, 0xFFFF); /* nada pulsado */
    sim_destroy(s);
}

static void test_absent(void)
{
    sim_faults_t f = {.mcp_absent = true};
    sim_t *s = sim_create(&f);
    ocx_hal_t h = sim_hal(s);
    mcp23017_t m;
    mcp23017_init(&m, &h, OCX_MCP_I2C_ADDR, OCX_PIN_MCP_RESET);
    CHECK_EQ(mcp23017_setup_inputs(&m, 0xFFFF), OCX_ERR_IO);
    sim_destroy(s);
}

static void test_mirror_interrupt(void)
{
    sim_t *s = sim_create(NULL);
    ocx_hal_t h = sim_hal(s);
    mcp23017_t m;
    mcp23017_init(&m, &h, OCX_MCP_I2C_ADDR, OCX_PIN_MCP_RESET);
    CHECK_EQ(mcp23017_setup_inputs(&m, OCX_MCP_BUTTON_MASK), OCX_OK);
    CHECK_EQ(h.gpio_read(h.ctx, OCX_PIN_MCP_INT), 1);

    /* Un botón del puerto B debe activar INTA gracias a MIRROR. */
    sim_press(s, OCX_BTN_X); /* GPB2 */
    CHECK_EQ(h.gpio_read(h.ctx, OCX_PIN_MCP_INT), 0);
    uint16_t fl = 0, cap = 0;
    CHECK_EQ(mcp23017_read_int(&m, &fl, &cap), OCX_OK);
    CHECK_EQ(fl, OCX_BTN_X);
    CHECK_EQ(cap >> 8, 0xFF & ~(OCX_BTN_X >> 8)); /* INTCAPB = GPIOB al saltar */
    CHECK_EQ(h.gpio_read(h.ctx, OCX_PIN_MCP_INT), 1); /* leer INTCAP libera INT */

    /* Puerto A, y borrado al leer GPIO */
    sim_release(s, OCX_BTN_X);
    uint16_t g;
    mcp23017_read_gpio(&m, &g);
    sim_press(s, OCX_BTN_A_UP);
    CHECK_EQ(h.gpio_read(h.ctx, OCX_PIN_MCP_INT), 0);
    mcp23017_read_gpio(&m, &g);
    CHECK_EQ(g, 0xFFFF & ~OCX_BTN_A_UP);
    CHECK_EQ(h.gpio_read(h.ctx, OCX_PIN_MCP_INT), 1);
    sim_destroy(s);
}

static void test_no_mirror_fault(void)
{
    sim_faults_t f = {.mcp_no_mirror = true};
    sim_t *s = sim_create(&f);
    ocx_hal_t h = sim_hal(s);
    mcp23017_t m;
    mcp23017_init(&m, &h, OCX_MCP_I2C_ADDR, OCX_PIN_MCP_RESET);
    CHECK_EQ(mcp23017_setup_inputs(&m, OCX_MCP_BUTTON_MASK), OCX_OK);
    sim_press(s, OCX_BTN_O);
    CHECK_EQ(h.gpio_read(h.ctx, OCX_PIN_MCP_INT), 1); /* sin MIRROR, INTA no se entera */
    sim_destroy(s);
}

static void test_reset_pin(void)
{
    sim_t *s = sim_create(NULL);
    ocx_hal_t h = sim_hal(s);
    mcp23017_t m;
    mcp23017_init(&m, &h, OCX_MCP_I2C_ADDR, OCX_PIN_MCP_RESET);
    CHECK_EQ(mcp23017_write_reg(&m, MCP_GPPUA, 0x12), OCX_OK);
    mcp23017_hw_reset(&m);
    uint8_t v = 0xAA;
    CHECK_EQ(mcp23017_read_reg(&m, MCP_GPPUA, &v), OCX_OK);
    CHECK_EQ(v, 0x00); /* valores por defecto tras ~RESET */
    CHECK_EQ(mcp23017_read_reg(&m, MCP_IODIRB, &v), OCX_OK);
    CHECK_EQ(v, 0xFF);
    sim_destroy(s);
}

int main(void)
{
    RUN(test_setup_registers);
    RUN(test_absent);
    RUN(test_mirror_interrupt);
    RUN(test_no_mirror_fault);
    RUN(test_reset_pin);
    return DONE();
}
