#include "bt817.h"
#include "ocx_board.h"

#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define WR_CHUNK 512u /* bytes de datos por transacción de escritura */

const bt817_timing_t BT817_TIMING_NHD_50_800480 = {
    .hsize = 800, .hcycle = 928, .hoffset = 88, .hsync0 = 0, .hsync1 = 48,
    .vsize = 480, .vcycle = 525, .voffset = 32, .vsync0 = 0, .vsync1 = 3,
    .pclk = 2,      /* 72 MHz / 2 = 36 MHz → ~74 Hz de refresco */
    .pclk_pol = 1,
    .swizzle = 3,
    .cspread = 0,
    .dither = 1,
};

void bt817_init(bt817_t *dev, const ocx_hal_t *hal)
{
    memset(dev, 0, sizeof(*dev));
    dev->hal = hal;
    dev->width = OCX_BUS_SINGLE;
}

void bt817_hdr_write(uint32_t addr, uint8_t out[3])
{
    out[0] = (uint8_t)(0x80u | ((addr >> 16) & 0x3Fu));
    out[1] = (uint8_t)(addr >> 8);
    out[2] = (uint8_t)addr;
}

void bt817_hdr_read(uint32_t addr, uint8_t out[4])
{
    out[0] = (uint8_t)((addr >> 16) & 0x3Fu);
    out[1] = (uint8_t)(addr >> 8);
    out[2] = (uint8_t)addr;
    out[3] = 0x00; /* byte de espera (dummy) */
}

uint8_t bt817_clksel_param(uint8_t mult)
{
    /* bits 5..0 = multiplicador; bit 6 = rango alto del PLL (×4..×6). */
    return (uint8_t)((mult & 0x3Fu) | (mult >= 4 ? 0x40u : 0x00u));
}

ocx_err_t bt817_host_cmd(bt817_t *dev, uint8_t cmd, uint8_t param)
{
    const uint8_t b[3] = {cmd, param, 0x00};
    return dev->hal->eve_write(dev->hal->ctx, b, sizeof b);
}

ocx_err_t bt817_wr_mem(bt817_t *dev, uint32_t addr, const uint8_t *data, size_t len)
{
    uint8_t buf[3 + WR_CHUNK];
    while (len > 0) {
        size_t n = len > WR_CHUNK ? WR_CHUNK : len;
        bt817_hdr_write(addr, buf);
        memcpy(buf + 3, data, n);
        ocx_err_t e = dev->hal->eve_write(dev->hal->ctx, buf, 3 + n);
        if (e != OCX_OK) return e;
        addr += (uint32_t)n;
        data += n;
        len -= n;
    }
    return OCX_OK;
}

ocx_err_t bt817_rd_mem(bt817_t *dev, uint32_t addr, uint8_t *data, size_t len)
{
    uint8_t hdr[4];
    bt817_hdr_read(addr, hdr);
    return dev->hal->eve_read(dev->hal->ctx, hdr, sizeof hdr, data, len);
}

ocx_err_t bt817_wr8(bt817_t *dev, uint32_t addr, uint8_t v) { return bt817_wr_mem(dev, addr, &v, 1); }

ocx_err_t bt817_wr16(bt817_t *dev, uint32_t addr, uint16_t v)
{
    const uint8_t b[2] = {(uint8_t)v, (uint8_t)(v >> 8)};
    return bt817_wr_mem(dev, addr, b, 2);
}

ocx_err_t bt817_wr32(bt817_t *dev, uint32_t addr, uint32_t v)
{
    const uint8_t b[4] = {(uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16), (uint8_t)(v >> 24)};
    return bt817_wr_mem(dev, addr, b, 4);
}

/* Escribe palabras de 32 bits en little-endian, independiente del host. */
static ocx_err_t wr_words(bt817_t *dev, uint32_t addr, const uint32_t *w, size_t n)
{
    uint8_t b[4 * 24];
    if (n > 24) return OCX_ERR_ARG;
    for (size_t i = 0; i < n; i++) {
        b[4 * i] = (uint8_t)w[i];
        b[4 * i + 1] = (uint8_t)(w[i] >> 8);
        b[4 * i + 2] = (uint8_t)(w[i] >> 16);
        b[4 * i + 3] = (uint8_t)(w[i] >> 24);
    }
    return bt817_wr_mem(dev, addr, b, 4 * n);
}

ocx_err_t bt817_rd8(bt817_t *dev, uint32_t addr, uint8_t *v) { return bt817_rd_mem(dev, addr, v, 1); }

ocx_err_t bt817_rd16(bt817_t *dev, uint32_t addr, uint16_t *v)
{
    uint8_t b[2];
    ocx_err_t e = bt817_rd_mem(dev, addr, b, 2);
    *v = (uint16_t)(b[0] | (b[1] << 8));
    return e;
}

ocx_err_t bt817_rd32(bt817_t *dev, uint32_t addr, uint32_t *v)
{
    uint8_t b[4];
    ocx_err_t e = bt817_rd_mem(dev, addr, b, 4);
    *v = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    return e;
}

void bt817_power_cycle(bt817_t *dev, uint32_t boot_hz)
{
    const ocx_hal_t *h = dev->hal;
    /* Tras un reset el BT817 vuelve a SPI simple. */
    h->eve_set_bus(h->ctx, OCX_BUS_SINGLE, boot_hz);
    dev->width = OCX_BUS_SINGLE;
    ocx_gpio_write(h, OCX_PIN_EVE_PD_N, 0);
    ocx_delay_ms(h, 20);
    ocx_gpio_write(h, OCX_PIN_EVE_PD_N, 1);
    ocx_delay_ms(h, 20);
}

ocx_err_t bt817_set_quad(bt817_t *dev, bool quad, uint32_t hz)
{
    const ocx_hal_t *h = dev->hal;
    ocx_err_t e = bt817_wr8(dev, REG_SPI_WIDTH, quad ? SPI_WIDTH_4 : SPI_WIDTH_1);
    if (e != OCX_OK) return e;
    dev->width = quad ? OCX_BUS_QUAD : OCX_BUS_SINGLE;
    return h->eve_set_bus(h->ctx, dev->width, hz);
}

ocx_err_t bt817_boot(bt817_t *dev, const bt817_cfg_t *cfg)
{
    const ocx_hal_t *h = dev->hal;
    ocx_err_t e;

    bt817_power_cycle(dev, cfg->boot_hz);

    if (cfg->use_crystal) {
        if ((e = bt817_host_cmd(dev, HCMD_CLKEXT, 0)) != OCX_OK) return e;
    }
    if (cfg->clk_mult) {
        if ((e = bt817_host_cmd(dev, HCMD_CLKSEL, bt817_clksel_param(cfg->clk_mult))) != OCX_OK) return e;
    }
    if ((e = bt817_host_cmd(dev, HCMD_ACTIVE, 0)) != OCX_OK) return e;

    /* REG_ID puede tardar hasta 300 ms en valer 0x7C. */
    dev->chip_id = 0;
    for (int t = 0; t < 300; t += 5) {
        ocx_delay_ms(h, 5);
        if (bt817_rd8(dev, REG_ID, &dev->chip_id) == OCX_OK && dev->chip_id == BT817_CHIP_ID) break;
    }
    if (dev->chip_id != BT817_CHIP_ID) return OCX_ERR_TIMEOUT;

    /* Espera a que salgan de reset el coprocesador, el táctil y el audio. */
    uint8_t rst = 0xFF;
    for (int t = 0; t < 100 && rst != 0; t += 2) {
        if ((e = bt817_rd8(dev, REG_CPURESET, &rst)) != OCX_OK) return e;
        if (rst) ocx_delay_ms(h, 2);
    }
    if (rst != 0) return OCX_ERR_TIMEOUT;

    uint8_t mult = cfg->clk_mult ? cfg->clk_mult : 5; /* 5 × 12 MHz = 60 MHz por defecto */
    dev->sys_hz = 12000000UL * mult;
    if ((e = bt817_wr32(dev, REG_FREQUENCY, dev->sys_hz)) != OCX_OK) return e;

    /* Con el reloj ya configurado se puede subir SCLK. */
    if ((e = h->eve_set_bus(h->ctx, OCX_BUS_SINGLE, cfg->run_hz)) != OCX_OK) return e;
    if (cfg->quad) {
        if ((e = bt817_set_quad(dev, true, cfg->run_hz)) != OCX_OK) return e;
        /* Relectura en QSPI: comprueba IO2/IO3 (GPIO14/GPIO9). */
        uint8_t id = 0;
        if ((e = bt817_rd8(dev, REG_ID, &id)) != OCX_OK) return e;
        if (id != BT817_CHIP_ID) {
            dev->chip_id = id;
            return OCX_ERR_STATE;
        }
    }
    return OCX_OK;
}

ocx_err_t bt817_measure_clock(bt817_t *dev, uint32_t window_ms, uint32_t *hz)
{
    const ocx_hal_t *h = dev->hal;
    uint32_t c0, c1;
    ocx_err_t e;
    uint64_t t0 = ocx_now_us(h);
    if ((e = bt817_rd32(dev, REG_CLOCK, &c0)) != OCX_OK) return e;
    uint64_t t0b = ocx_now_us(h);
    ocx_delay_ms(h, window_ms);
    uint64_t t1 = ocx_now_us(h);
    if ((e = bt817_rd32(dev, REG_CLOCK, &c1)) != OCX_OK) return e;
    uint64_t t1b = ocx_now_us(h);
    /* Se toma el punto medio de cada lectura para compensar la latencia. */
    uint64_t dt = ((t1 + t1b) - (t0 + t0b)) / 2;
    if (dt == 0) return OCX_ERR_STATE;
    uint32_t dc = c1 - c0; /* aritmética módulo 2^32: soporta el desbordamiento */
    *hz = (uint32_t)(((uint64_t)dc * 1000000ULL + dt / 2) / dt);
    return OCX_OK;
}

ocx_err_t bt817_display_init(bt817_t *dev, const bt817_timing_t *t)
{
    ocx_err_t e = OCX_OK;
#define W16(r, v) do { if ((e = bt817_wr16(dev, (r), (v))) != OCX_OK) return e; } while (0)
#define W8(r, v)  do { if ((e = bt817_wr8(dev, (r), (v))) != OCX_OK) return e; } while (0)
    W8(REG_PCLK, 0); /* detener el barrido mientras se configura */
    W16(REG_HCYCLE, t->hcycle);
    W16(REG_HOFFSET, t->hoffset);
    W16(REG_HSYNC0, t->hsync0);
    W16(REG_HSYNC1, t->hsync1);
    W16(REG_VCYCLE, t->vcycle);
    W16(REG_VOFFSET, t->voffset);
    W16(REG_VSYNC0, t->vsync0);
    W16(REG_VSYNC1, t->vsync1);
    W16(REG_HSIZE, t->hsize);
    W16(REG_VSIZE, t->vsize);
    W8(REG_SWIZZLE, t->swizzle);
    W8(REG_PCLK_POL, t->pclk_pol);
    W8(REG_CSPREAD, t->cspread);
    W8(REG_DITHER, t->dither);

    /* Pantalla en negro antes de arrancar el reloj de píxel. */
    const uint32_t dl[] = {DL_CLEAR_COLOR_RGB(0, 0, 0), DL_CLEAR(1, 1, 1), DL_DISPLAY()};
    if ((e = wr_words(dev, BT_RAM_DL, dl, sizeof dl / sizeof dl[0])) != OCX_OK) return e;
    W8(REG_DLSWAP, DLSWAP_FRAME);

    /* DISP (GPIOX bit 15) a 1: el panel sale de reposo. */
    uint16_t dir = 0, val = 0;
    if ((e = bt817_rd16(dev, REG_GPIOX_DIR, &dir)) != OCX_OK) return e;
    if ((e = bt817_rd16(dev, REG_GPIOX, &val)) != OCX_OK) return e;
    W16(REG_GPIOX_DIR, (uint16_t)(dir | GPIOX_DISP));
    W16(REG_GPIOX, (uint16_t)(val | GPIOX_DISP));

    W8(REG_PCLK, t->pclk);
#undef W16
#undef W8
    return OCX_OK;
}

ocx_err_t bt817_display_check(bt817_t *dev, const bt817_timing_t *t, char *why, size_t why_len)
{
    static const struct { uint32_t reg; const char *name; size_t off; } regs[] = {
#define R(r, f) {r, #r, offsetof(bt817_timing_t, f)}
        R(REG_HCYCLE, hcycle), R(REG_HOFFSET, hoffset), R(REG_HSYNC0, hsync0), R(REG_HSYNC1, hsync1),
        R(REG_VCYCLE, vcycle), R(REG_VOFFSET, voffset), R(REG_VSYNC0, vsync0), R(REG_VSYNC1, vsync1),
        R(REG_HSIZE, hsize),   R(REG_VSIZE, vsize),
#undef R
    };
    for (size_t i = 0; i < sizeof regs / sizeof regs[0]; i++) {
        uint16_t got = 0, want;
        memcpy(&want, (const uint8_t *)t + regs[i].off, sizeof want);
        ocx_err_t e = bt817_rd16(dev, regs[i].reg, &got);
        if (e != OCX_OK) return e;
        if ((got & 0x0FFFu) != want) {
            snprintf(why, why_len, "%s=%u (esperado %u)", regs[i].name, got & 0x0FFFu, want);
            return OCX_ERR_STATE;
        }
    }
    uint8_t sw = 0, pclk = 0;
    ocx_err_t e;
    if ((e = bt817_rd8(dev, REG_SWIZZLE, &sw)) != OCX_OK) return e;
    if ((sw & 0x0Fu) != t->swizzle) {
        snprintf(why, why_len, "REG_SWIZZLE=%u (esperado %u)", sw & 0x0Fu, t->swizzle);
        return OCX_ERR_STATE;
    }
    if ((e = bt817_rd8(dev, REG_PCLK, &pclk)) != OCX_OK) return e;
    if (pclk != t->pclk) {
        snprintf(why, why_len, "REG_PCLK=%u (esperado %u)", pclk, t->pclk);
        return OCX_ERR_STATE;
    }
    return OCX_OK;
}

ocx_err_t bt817_backlight(bt817_t *dev, uint8_t percent)
{
    if (percent > 100) percent = 100;
    ocx_err_t e = bt817_wr16(dev, REG_PWM_HZ, 4000);
    if (e != OCX_OK) return e;
    return bt817_wr8(dev, REG_PWM_DUTY, (uint8_t)((percent * 128u + 50u) / 100u));
}

ocx_err_t bt817_test_pattern(bt817_t *dev, const bt817_timing_t *t)
{
    const uint16_t w = t->hsize / 4, hgt = t->vsize;
    const uint32_t col[4] = {0xFF0000, 0x00FF00, 0x0000FF, 0xFFFFFF};
    uint32_t dl[4 + 4 * 3 + 2];
    size_t n = 0;
    dl[n++] = DL_CLEAR_COLOR_RGB(0, 0, 0);
    dl[n++] = DL_CLEAR(1, 1, 1);
    dl[n++] = DL_VERTEX_FORMAT(0); /* coordenadas en píxeles */
    dl[n++] = DL_BEGIN(PRIM_RECTS);
    for (int i = 0; i < 4; i++) {
        dl[n++] = DL_COLOR_RGB(col[i] >> 16, col[i] >> 8, col[i]);
        dl[n++] = DL_VERTEX2F(i * w, 0);
        dl[n++] = DL_VERTEX2F((i + 1) * w - 1, hgt - 1);
    }
    dl[n++] = DL_END();
    dl[n++] = DL_DISPLAY();
    ocx_err_t e = wr_words(dev, BT_RAM_DL, dl, n);
    if (e != OCX_OK) return e;
    return bt817_wr8(dev, REG_DLSWAP, DLSWAP_FRAME);
}

ocx_err_t bt817_sound_play(bt817_t *dev, uint8_t effect, uint8_t midi_note, uint8_t volume)
{
    ocx_err_t e;
    if ((e = bt817_wr8(dev, REG_VOL_SOUND, volume)) != OCX_OK) return e;
    if ((e = bt817_wr16(dev, REG_SOUND, (uint16_t)((midi_note << 8) | effect))) != OCX_OK) return e;
    return bt817_wr8(dev, REG_PLAY, 1);
}

ocx_err_t bt817_sound_stop(bt817_t *dev) { return bt817_sound_play(dev, SOUND_SILENCE, 0, 0); }

ocx_err_t bt817_sound_busy(bt817_t *dev, bool *busy)
{
    uint8_t p = 0;
    ocx_err_t e = bt817_rd8(dev, REG_PLAY, &p);
    *busy = (p & 1u) != 0;
    return e;
}
