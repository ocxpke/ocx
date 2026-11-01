#include "sim.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "bt817_regs.h"
#include "ocx_board.h"
#include "ocx_input.h"

#define REG_SPACE   0x1000u
#define RAMG_SIZE   0x10000u
#define NPINS       64
#define XTAL_HZ     12000000.0

typedef enum { OP_IDLE, OP_BUTTONS, OP_JOYSTICKS, OP_BEEP } op_mode_t;

struct sim {
    sim_faults_t f;
    uint64_t t_us;
    uint32_t lcg;

    /* GPIO de la ESP32-S3 */
    int gpio_out[NPINS];
    uint32_t pressed; /* máscara OCX_BTN_* */
    int axis[4];

    /* Bus del host */
    int host_width;
    uint32_t host_hz;

    /* BT817 */
    bool eve_powered, eve_active, clk_ext;
    uint8_t clk_mult;
    uint64_t t_active, t_pclk;
    uint32_t frames_base;
    int eve_width;
    uint8_t reg[REG_SPACE];
    uint8_t dl[BT_RAM_DL_SIZE];
    uint8_t *ramg;
    int audible_beeps;

    /* MCP23017 */
    uint8_t mcp[0x16];
    uint8_t mcp_ptr;
    uint16_t mcp_prev; /* niveles en la última actualización */
    int last_reset_level;

    /* Operador virtual */
    bool op_enabled;
    op_mode_t op_mode;
    uint64_t op_t0;
};

/* ======================================================================== */
/* Utilidades                                                               */
/* ======================================================================== */
static uint32_t rnd(sim_t *s)
{
    s->lcg = s->lcg * 1103515245u + 12345u;
    return (s->lcg >> 16) & 0x7FFF;
}

static void op_tick(sim_t *s);
static void mcp_update(sim_t *s);

static void advance_us(sim_t *s, uint64_t us)
{
    s->t_us += us;
    mcp_update(s);
}

static void bus_time(sim_t *s, size_t bytes, int width, uint32_t hz)
{
    if (!hz) hz = 1000000;
    uint64_t bits = (uint64_t)bytes * 8 / (uint64_t)width;
    advance_us(s, 2 + (bits * 1000000 + hz - 1) / hz);
}

static uint32_t rd_le(const uint8_t *p, int n)
{
    uint32_t v = 0;
    for (int i = n - 1; i >= 0; i--) v = (v << 8) | p[i];
    return v;
}

static void wr_le(uint8_t *p, uint32_t v, int n)
{
    for (int i = 0; i < n; i++) p[i] = (uint8_t)(v >> (8 * i));
}

/* ======================================================================== */
/* BT817                                                                    */
/* ======================================================================== */
static double eve_sys_hz(const sim_t *s)
{
    double base = s->clk_ext ? XTAL_HZ * (1.0 + s->f.xtal_ppm / 1e6) : XTAL_HZ * (1.0 + s->f.intosc_ppm / 1e6);
    return base * (s->clk_mult ? s->clk_mult : 5);
}

static bool eve_running(const sim_t *s)
{
    if (s->f.eve_absent || !s->eve_powered || !s->eve_active) return false;
    if (s->clk_ext && s->f.no_crystal) return false;
    return true;
}

static void eve_reset(sim_t *s)
{
    s->eve_active = false;
    s->clk_ext = false;
    s->clk_mult = 0;
    s->eve_width = 1;
    s->frames_base = 0;
    memset(s->reg, 0, sizeof s->reg);
    wr_le(&s->reg[REG_GPIOX_DIR - BT_RAM_REG], 0x8000, 2);
    wr_le(&s->reg[REG_PWM_HZ - BT_RAM_REG], 250, 4);
    wr_le(&s->reg[REG_PWM_DUTY - BT_RAM_REG], 128, 1);
}

static uint32_t eve_frames(const sim_t *s)
{
    uint32_t pclk = s->reg[REG_PCLK - BT_RAM_REG];
    uint32_t h = rd_le(&s->reg[REG_HCYCLE - BT_RAM_REG], 2) & 0xFFF;
    uint32_t v = rd_le(&s->reg[REG_VCYCLE - BT_RAM_REG], 2) & 0xFFF;
    if (!pclk || !h || !v || s->f.pclk_dead) return s->frames_base;
    double dt = (double)(s->t_us - s->t_pclk) / 1e6;
    return s->frames_base + (uint32_t)(dt * eve_sys_hz(s) / ((double)pclk * h * v));
}

/* Valor de un byte de memoria del BT817 tal como se leería ahora. */
static uint8_t eve_peek(sim_t *s, uint32_t addr)
{
    if (addr >= BT_RAM_REG && addr < BT_RAM_REG + REG_SPACE) {
        uint32_t off = addr - BT_RAM_REG, base = off & ~3u, v;
        uint64_t since = s->t_us - s->t_active;
        switch (base + BT_RAM_REG) {
        case REG_ID: v = since >= 40000 ? BT817_CHIP_ID : 0; break;
        case REG_CPURESET: v = since >= 50000 ? 0 : 7; break;
        case REG_CLOCK: v = (uint32_t)(uint64_t)((double)since * eve_sys_hz(s) / 1e6); break;
        case REG_FRAMES: v = eve_frames(s); break;
        default: return s->reg[off];
        }
        return (uint8_t)(v >> (8 * (off - base)));
    }
    if (addr >= BT_RAM_DL && addr < BT_RAM_DL + BT_RAM_DL_SIZE) return s->dl[addr - BT_RAM_DL];
    if (addr < RAMG_SIZE) return s->ramg[addr];
    return 0;
}

static void eve_poke(sim_t *s, uint32_t addr, uint8_t b)
{
    if (addr >= BT_RAM_REG && addr < BT_RAM_REG + REG_SPACE) {
        uint32_t off = addr - BT_RAM_REG;
        uint32_t r = BT_RAM_REG + (off & ~3u);
        if (r == REG_ID || r == REG_CLOCK || r == REG_FRAMES) return; /* solo lectura */
        if (r == REG_PCLK && off == (REG_PCLK - BT_RAM_REG)) {
            s->frames_base = eve_frames(s);
            s->t_pclk = s->t_us;
        }
        s->reg[off] = b;
        return;
    }
    if (addr >= BT_RAM_DL && addr < BT_RAM_DL + BT_RAM_DL_SIZE) { s->dl[addr - BT_RAM_DL] = b; return; }
    if (addr < RAMG_SIZE) s->ramg[addr] = b;
}

/* Efectos posteriores a una escritura (registros con acción). */
static void eve_after_write(sim_t *s, uint32_t a0, size_t n)
{
    for (uint32_t a = a0; a < a0 + n; a++) {
        if (a == REG_DLSWAP && s->reg[REG_DLSWAP - BT_RAM_REG] && s->reg[REG_PCLK - BT_RAM_REG] && !s->f.pclk_dead)
            s->reg[REG_DLSWAP - BT_RAM_REG] = 0; /* se completa en el siguiente cuadro */
        if (a == REG_SPI_WIDTH) s->eve_width = (s->reg[REG_SPI_WIDTH - BT_RAM_REG] & 3) == 2 ? 4 : 1;
        if (a == REG_PLAY && (s->reg[REG_PLAY - BT_RAM_REG] & 1)) {
            uint8_t effect = s->reg[REG_SOUND - BT_RAM_REG];
            uint8_t vol = s->reg[REG_VOL_SOUND - BT_RAM_REG];
            if (effect == SOUND_SILENCE) {
                s->reg[REG_PLAY - BT_RAM_REG] = 0;
            } else if (vol && s->gpio_out[OCX_PIN_AMP_SD] && !s->f.amp_unwired) {
                s->audible_beeps++;
            }
        }
    }
}

static uint8_t lane_mangle(const sim_t *s, uint8_t b)
{
    /* En QSPI cada byte va en dos nibbles; sin IO2/IO3 se pierden los bits 2,3,6,7. */
    return (s->eve_width == 4 && s->f.qspi_io23_broken) ? (uint8_t)(b & 0x33) : b;
}

static ocx_err_t eve_write(void *ctx, const uint8_t *d, size_t len)
{
    sim_t *s = ctx;
    bus_time(s, len, s->host_width, s->host_hz);
    if (s->f.eve_absent || !s->eve_powered || len < 3) return OCX_OK;
    if (s->host_width != s->eve_width) return OCX_OK; /* el BT817 no entiende la trama */

    uint8_t b0 = lane_mangle(s, d[0]);
    if ((b0 & 0xC0) == 0x80) { /* escritura en memoria */
        if (!eve_running(s)) return OCX_OK;
        uint32_t addr = ((uint32_t)(b0 & 0x3F) << 16) | ((uint32_t)lane_mangle(s, d[1]) << 8) | lane_mangle(s, d[2]);
        for (size_t i = 3; i < len; i++) eve_poke(s, addr + (uint32_t)(i - 3), lane_mangle(s, d[i]));
        eve_after_write(s, addr, len - 3);
        return OCX_OK;
    }
    if (len != 3) return OCX_OK;
    switch (b0) { /* comando de host */
    case HCMD_ACTIVE:
        if (!s->eve_active) {
            s->eve_active = true;
            s->t_active = s->t_us;
        }
        break;
    case HCMD_CLKEXT: if (!s->eve_active) s->clk_ext = true; break;
    case HCMD_CLKINT: if (!s->eve_active) s->clk_ext = false; break;
    case HCMD_CLKSEL: if (!s->eve_active) s->clk_mult = d[1] & 0x3F; break;
    case HCMD_RST_PULSE: wr_le(&s->reg[REG_CPURESET - BT_RAM_REG], 0, 1); break;
    default: break;
    }
    return OCX_OK;
}

static ocx_err_t eve_read(void *ctx, const uint8_t *hdr, size_t hlen, uint8_t *rx, size_t rlen)
{
    sim_t *s = ctx;
    bus_time(s, hlen + rlen, s->host_width, s->host_hz);
    if (!eve_running(s) || hlen != 4) { /* MISO sin manejar: se lee 0 */
        memset(rx, 0x00, rlen);
        return OCX_OK;
    }
    if (s->host_width != s->eve_width) {
        memset(rx, 0xFF, rlen);
        return OCX_OK;
    }
    uint32_t addr = ((uint32_t)(lane_mangle(s, hdr[0]) & 0x3F) << 16) | ((uint32_t)lane_mangle(s, hdr[1]) << 8) |
                    lane_mangle(s, hdr[2]);
    for (size_t i = 0; i < rlen; i++) rx[i] = lane_mangle(s, eve_peek(s, addr + (uint32_t)i));
    return OCX_OK;
}

static ocx_err_t eve_set_bus(void *ctx, ocx_bus_width_t w, uint32_t hz)
{
    sim_t *s = ctx;
    if (w != OCX_BUS_SINGLE && w != OCX_BUS_QUAD) return OCX_ERR_ARG;
    s->host_width = (int)w;
    s->host_hz = hz;
    return OCX_OK;
}

/* ======================================================================== */
/* MCP23017                                                                 */
/* ======================================================================== */
static void mcp_reset(sim_t *s)
{
    memset(s->mcp, 0, sizeof s->mcp);
    s->mcp[MCP_IODIRA] = s->mcp[MCP_IODIRB] = 0xFF;
    s->mcp_ptr = 0;
}

/* Nivel eléctrico de los 16 pines del MCP. */
static uint16_t mcp_levels(const sim_t *s)
{
    uint32_t closed = (s->pressed | s->f.stuck_buttons) & ~s->f.dead_buttons;
    uint16_t lv = 0;
    for (int i = 0; i < 16; i++) {
        bool has_btn = (OCX_MCP_BUTTON_MASK >> i) & 1;
        bool low = has_btn && ((closed >> i) & 1);
        /* Pin abierto: alto por el pull-up (sin él flotaría; se modela alto). */
        if (!low) lv |= (uint16_t)(1u << i);
    }
    return lv;
}

static uint16_t mcp_gpio_value(const sim_t *s)
{
    return (uint16_t)(mcp_levels(s) ^ (s->mcp[MCP_IPOLA] | (s->mcp[MCP_IPOLB] << 8)));
}

static void mcp_update(sim_t *s)
{
    int rl = s->gpio_out[OCX_PIN_MCP_RESET];
    if (!rl) mcp_reset(s);
    s->last_reset_level = rl;

    uint16_t lv = mcp_levels(s);
    uint16_t changed = lv ^ s->mcp_prev;
    s->mcp_prev = lv;
    if (!changed) return;
    uint16_t en = (uint16_t)(s->mcp[MCP_GPINTENA] | (s->mcp[MCP_GPINTENB] << 8));
    uint16_t trig = changed & en; /* INTCON = 0: interrupción por cambio */
    uint16_t gpio = mcp_gpio_value(s);
    for (int port = 0; port < 2; port++) {
        uint8_t t = (uint8_t)(trig >> (8 * port));
        if (!t) continue;
        if (s->mcp[MCP_INTFA + port] == 0) s->mcp[MCP_INTCAPA + port] = (uint8_t)(gpio >> (8 * port));
        s->mcp[MCP_INTFA + port] |= t;
    }
}

static int mcp_inta_level(const sim_t *s)
{
    bool mirror = (s->mcp[MCP_IOCON] & 0x40) && !s->f.mcp_no_mirror;
    bool act = s->mcp[MCP_INTFA] || (mirror && s->mcp[MCP_INTFB]);
    bool intpol = s->mcp[MCP_IOCON] & 0x02;
    return act ? intpol : !intpol;
}

static uint8_t mcp_read_byte(sim_t *s, uint8_t r)
{
    uint16_t g = mcp_gpio_value(s);
    switch (r) {
    case MCP_GPIOA: s->mcp[MCP_INTFA] = 0; return (uint8_t)g;
    case MCP_GPIOB: s->mcp[MCP_INTFB] = 0; return (uint8_t)(g >> 8);
    case MCP_INTCAPA: { uint8_t v = s->mcp[r]; s->mcp[MCP_INTFA] = 0; return v; }
    case MCP_INTCAPB: { uint8_t v = s->mcp[r]; s->mcp[MCP_INTFB] = 0; return v; }
    case 0x0B: return s->mcp[MCP_IOCON]; /* IOCON aparece en dos direcciones */
    default: return r < sizeof s->mcp ? s->mcp[r] : 0;
    }
}

static void mcp_write_byte(sim_t *s, uint8_t r, uint8_t v)
{
    switch (r) {
    case MCP_INTFA: case MCP_INTFB: case MCP_INTCAPA: case MCP_INTCAPB: return;
    case MCP_GPIOA: s->mcp[MCP_OLATA] = v; return;
    case MCP_GPIOB: s->mcp[MCP_OLATB] = v; return;
    case 0x0B: r = MCP_IOCON; /* fallthrough */
    default:
        if (r == MCP_IOCON) v &= 0x7E; /* el bit 0 no se implementa; BANK=1 no se modela */
        if (r < sizeof s->mcp) s->mcp[r] = v;
    }
}

static uint8_t mcp_next(sim_t *s, uint8_t r)
{
    if (s->mcp[MCP_IOCON] & MCP_IOCON_SEQOP) return r;
    return (uint8_t)((r + 1) % 0x16);
}

static ocx_err_t i2c_write(void *ctx, uint8_t addr, const uint8_t *d, size_t n)
{
    sim_t *s = ctx;
    bus_time(s, n + 1, 1, OCX_I2C_HZ * 8 / 9);
    if (s->f.mcp_absent || addr != OCX_MCP_I2C_ADDR || !s->gpio_out[OCX_PIN_MCP_RESET]) return OCX_ERR_IO;
    if (n == 0) return OCX_OK;
    s->mcp_ptr = d[0];
    for (size_t i = 1; i < n; i++) {
        mcp_write_byte(s, s->mcp_ptr, d[i]);
        s->mcp_ptr = mcp_next(s, s->mcp_ptr);
    }
    return OCX_OK;
}

static ocx_err_t i2c_write_read(void *ctx, uint8_t addr, const uint8_t *w, size_t wn, uint8_t *r, size_t rn)
{
    sim_t *s = ctx;
    ocx_err_t e = i2c_write(ctx, addr, w, wn);
    if (e != OCX_OK) return e;
    bus_time(s, rn + 1, 1, OCX_I2C_HZ * 8 / 9);
    for (size_t i = 0; i < rn; i++) {
        r[i] = mcp_read_byte(s, s->mcp_ptr);
        s->mcp_ptr = mcp_next(s, s->mcp_ptr);
    }
    return OCX_OK;
}

/* ======================================================================== */
/* GPIO, ADC, tiempo                                                        */
/* ======================================================================== */
static void gpio_write(void *ctx, int pin, int lvl)
{
    sim_t *s = ctx;
    if (pin < 0 || pin >= NPINS) return;
    lvl = lvl ? 1 : 0;
    if (pin == OCX_PIN_EVE_PD_N && lvl != s->gpio_out[pin]) {
        if (!lvl) {
            s->eve_powered = false;
        } else {
            s->eve_powered = true;
            eve_reset(s);
        }
    }
    s->gpio_out[pin] = lvl;
    mcp_update(s);
}

static int gpio_read(void *ctx, int pin)
{
    sim_t *s = ctx;
    mcp_update(s);
    switch (pin) {
    case OCX_PIN_MCP_INT: return mcp_inta_level(s);
    case OCX_PIN_EVE_INT_N: return 1;
    case OCX_PIN_JOY_L_BTN: return ((s->pressed | s->f.stuck_buttons) & ~s->f.dead_buttons & OCX_BTN_L3) ? 0 : 1;
    case OCX_PIN_JOY_R_BTN: return ((s->pressed | s->f.stuck_buttons) & ~s->f.dead_buttons & OCX_BTN_R3) ? 0 : 1;
    default: return (pin >= 0 && pin < NPINS) ? s->gpio_out[pin] : 0;
    }
}

static ocx_err_t adc_read(void *ctx, int pin, int *raw)
{
    sim_t *s = ctx;
    int a = -1;
    for (int i = 0; i < 4; i++)
        if (OCX_AXIS_PIN[i] == pin) a = i;
    if (a < 0) return OCX_ERR_ARG;
    advance_us(s, 20);
    int v;
    if (s->f.axis_fault[a] == 1) v = (int)(rnd(s) % 6);
    else if (s->f.axis_fault[a] == 2) v = 4095;
    else v = s->axis[a] + (int)(rnd(s) % 21) - 10;
    *raw = v < 0 ? 0 : v > 4095 ? 4095 : v;
    return OCX_OK;
}

static void delay_ms(void *ctx, uint32_t ms)
{
    sim_t *s = ctx;
    for (uint32_t i = 0; i < ms; i++) {
        advance_us(s, 1000);
        op_tick(s);
    }
}

static uint64_t now_us(void *ctx) { return ((sim_t *)ctx)->t_us; }

/* ======================================================================== */
/* Operador virtual                                                         */
/* ======================================================================== */
void sim_operator_enable(sim_t *s, bool on) { s->op_enabled = on; }

void sim_operator_prompt(void *ctx, const char *msg)
{
    sim_t *s = ctx;
    if (!s->op_enabled) return;
    op_mode_t m = OP_IDLE;
    if (!strncmp(msg, "Botones:", 8)) m = OP_BUTTONS;
    else if (!strncmp(msg, "Joysticks:", 10)) m = OP_JOYSTICKS;
    else if (!strncmp(msg, "Pitido:", 7)) m = OP_BEEP;
    else return;
    s->op_mode = m;
    s->op_t0 = s->t_us;
}

static void op_tick(sim_t *s)
{
    if (!s->op_enabled || s->op_mode == OP_IDLE) return;
    uint64_t t = (s->t_us - s->op_t0) / 1000; /* ms desde el mensaje */
    switch (s->op_mode) {
    case OP_BUTTONS: {
        /* Pulsa cada botón 60 ms, uno cada 150 ms. */
        uint32_t k = (uint32_t)(t / 150), phase = (uint32_t)(t % 150);
        uint32_t bit = 0;
        for (uint32_t i = 0, n = 0; i < 18; i++) {
            if (!((OCX_ALL_BUTTONS >> i) & 1)) continue;
            if (n++ == k) { bit = 1u << i; break; }
        }
        s->pressed = (bit && phase >= 20 && phase < 80) ? bit : 0;
        if (!bit) s->op_mode = OP_IDLE;
        break;
    }
    case OP_JOYSTICKS: {
        /* Dos vueltas completas en 2 s con radio máximo; luego al centro. */
        if (t > 2000) {
            for (int a = 0; a < 4; a++) s->axis[a] = 2048;
            s->op_mode = OP_IDLE;
            break;
        }
        double ang = 2.0 * 3.14159265358979 * (double)t / 1000.0;
        int dx = (int)(2047.0 * cos(ang)), dy = (int)(2047.0 * sin(ang));
        s->axis[0] = 2048 + dx; s->axis[1] = 2048 + dy;
        s->axis[2] = 2048 - dx; s->axis[3] = 2048 - dy;
        break;
    }
    case OP_BEEP: {
        uint32_t ans = s->audible_beeps ? OCX_BTN_X : OCX_BTN_O;
        s->pressed = (t >= 300 && t < 400) ? ans : 0;
        if (t >= 400) s->op_mode = OP_IDLE;
        break;
    }
    default: break;
    }
}

/* ======================================================================== */
/* Creación y observación                                                   */
/* ======================================================================== */
sim_t *sim_create(const sim_faults_t *faults)
{
    sim_t *s = calloc(1, sizeof *s);
    if (!s) return NULL;
    s->ramg = calloc(1, RAMG_SIZE);
    if (faults) s->f = *faults;
    s->lcg = 12345;
    s->host_width = 1;
    s->host_hz = 1000000;
    s->gpio_out[OCX_PIN_MCP_RESET] = 1; /* pull-up R5 */
    for (int a = 0; a < 4; a++) s->axis[a] = 2048 + 40 * a - 60; /* centros reales no perfectos */
    mcp_reset(s);
    s->mcp_prev = mcp_levels(s);
    eve_reset(s);
    return s;
}

void sim_destroy(sim_t *s)
{
    if (!s) return;
    free(s->ramg);
    free(s);
}

ocx_hal_t sim_hal(sim_t *s)
{
    ocx_hal_t h = {
        .ctx = s,
        .eve_write = eve_write,
        .eve_read = eve_read,
        .eve_set_bus = eve_set_bus,
        .gpio_write = gpio_write,
        .gpio_read = gpio_read,
        .i2c_write = i2c_write,
        .i2c_write_read = i2c_write_read,
        .adc_read = adc_read,
        .delay_ms = delay_ms,
        .now_us = now_us,
    };
    return h;
}

void sim_press(sim_t *s, uint32_t m) { s->pressed |= m; mcp_update(s); }
void sim_release(sim_t *s, uint32_t m) { s->pressed &= ~m; mcp_update(s); }
void sim_set_axis(sim_t *s, int a, int raw) { if (a >= 0 && a < 4) s->axis[a] = raw; }

uint64_t sim_time_us(const sim_t *s) { return s->t_us; }
uint32_t sim_eve_reg(const sim_t *s, uint32_t addr) { return rd_le(&s->reg[addr - BT_RAM_REG], 4); }
int sim_eve_width(const sim_t *s) { return s->eve_width; }
uint32_t sim_eve_sys_hz(const sim_t *s) { return eve_running(s) ? (uint32_t)eve_sys_hz(s) : 0; }
uint32_t sim_eve_dl_word(const sim_t *s, unsigned i) { return i < BT_RAM_DL_SIZE / 4 ? rd_le(&s->dl[4 * i], 4) : 0; }
int sim_audible_beeps(const sim_t *s) { return s->audible_beeps; }
uint8_t sim_mcp_reg(const sim_t *s, uint8_t r) { return r < sizeof s->mcp ? s->mcp[r] : 0; }
int sim_gpio_out(const sim_t *s, int pin) { return (pin >= 0 && pin < NPINS) ? s->gpio_out[pin] : 0; }
uint32_t sim_host_hz(const sim_t *s) { return s->host_hz; }
int sim_host_width(const sim_t *s) { return s->host_width; }
