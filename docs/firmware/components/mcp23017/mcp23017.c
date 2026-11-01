#include "mcp23017.h"

void mcp23017_init(mcp23017_t *m, const ocx_hal_t *hal, uint8_t addr, int reset_pin)
{
    m->hal = hal;
    m->addr = addr;
    m->reset_pin = reset_pin;
}

void mcp23017_hw_reset(mcp23017_t *m)
{
    if (m->reset_pin < 0) return;
    ocx_gpio_write(m->hal, m->reset_pin, 0);
    ocx_delay_ms(m->hal, 1); /* tRSTL ≥ 1 µs */
    ocx_gpio_write(m->hal, m->reset_pin, 1);
    ocx_delay_ms(m->hal, 1);
}

ocx_err_t mcp23017_write_reg(mcp23017_t *m, uint8_t reg, uint8_t v)
{
    const uint8_t b[2] = {reg, v};
    return m->hal->i2c_write(m->hal->ctx, m->addr, b, 2);
}

ocx_err_t mcp23017_read_reg(mcp23017_t *m, uint8_t reg, uint8_t *v)
{
    return m->hal->i2c_write_read(m->hal->ctx, m->addr, &reg, 1, v, 1);
}

ocx_err_t mcp23017_read_pair(mcp23017_t *m, uint8_t reg_a, uint16_t *v)
{
    uint8_t b[2] = {0, 0};
    ocx_err_t e = m->hal->i2c_write_read(m->hal->ctx, m->addr, &reg_a, 1, b, 2);
    *v = (uint16_t)(b[0] | (b[1] << 8));
    return e;
}

static ocx_err_t write_pair(mcp23017_t *m, uint8_t reg_a, uint16_t v)
{
    const uint8_t b[3] = {reg_a, (uint8_t)v, (uint8_t)(v >> 8)};
    return m->hal->i2c_write(m->hal->ctx, m->addr, b, 3);
}

ocx_err_t mcp23017_setup_inputs(mcp23017_t *m, uint16_t int_mask)
{
    ocx_err_t e;
    mcp23017_hw_reset(m);
    if ((e = mcp23017_write_reg(m, MCP_IOCON, OCX_MCP_IOCON)) != OCX_OK) return e;
    if ((e = write_pair(m, MCP_IODIRA, 0xFFFF)) != OCX_OK) return e;
    if ((e = write_pair(m, MCP_IPOLA, 0x0000)) != OCX_OK) return e;
    if ((e = write_pair(m, MCP_GPPUA, 0xFFFF)) != OCX_OK) return e; /* pull-up 100 k */
    if ((e = write_pair(m, MCP_INTCONA, 0x0000)) != OCX_OK) return e; /* por cambio */
    if ((e = write_pair(m, MCP_GPINTENA, int_mask)) != OCX_OK) return e;

    uint8_t iocon = 0;
    uint16_t iodir = 0, gppu = 0;
    if ((e = mcp23017_read_reg(m, MCP_IOCON, &iocon)) != OCX_OK) return e;
    if ((e = mcp23017_read_pair(m, MCP_IODIRA, &iodir)) != OCX_OK) return e;
    if ((e = mcp23017_read_pair(m, MCP_GPPUA, &gppu)) != OCX_OK) return e;
    if (iocon != OCX_MCP_IOCON || iodir != 0xFFFF || gppu != 0xFFFF) return OCX_ERR_STATE;

    uint16_t f, c;
    return mcp23017_read_int(m, &f, &c); /* limpia interrupciones pendientes */
}

ocx_err_t mcp23017_read_gpio(mcp23017_t *m, uint16_t *v) { return mcp23017_read_pair(m, MCP_GPIOA, v); }

ocx_err_t mcp23017_read_int(mcp23017_t *m, uint16_t *flags, uint16_t *captured)
{
    ocx_err_t e = mcp23017_read_pair(m, MCP_INTFA, flags);
    if (e != OCX_OK) return e;
    return mcp23017_read_pair(m, MCP_INTCAPA, captured);
}
