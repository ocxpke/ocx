#include "ocx_bringup.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "ocx_board.h"

#define ADC_FULL 4095

static const char *const BLOCK_NAMES[BU_COUNT] = {
    "EVE_ID", "EVE_CLOCK", "DISPLAY", "BUTTONS", "JOYSTICKS", "BEEP",
};

const char *bu_block_name(bu_block_t b) { return (unsigned)b < BU_COUNT ? BLOCK_NAMES[b] : "?"; }

const char *bu_status_name(bu_status_t s)
{
    switch (s) {
    case BU_NOT_RUN: return "----";
    case BU_PASS: return "PASS";
    case BU_WARN: return "WARN";
    case BU_FAIL: return "FAIL";
    case BU_SKIP: return "SKIP";
    }
    return "?";
}

void bu_default_cfg(bu_cfg_t *cfg)
{
    static const bt817_cfg_t eve = BT817_CFG_DEFAULT;
    memset(cfg, 0, sizeof *cfg);
    cfg->interactive = true;
    cfg->clock_window_ms = 200;
    cfg->clock_tol_ppm = 2000; /* 0,2 %: el oscilador interno se sale de largo */
    cfg->button_timeout_ms = 30000;
    cfg->joystick_timeout_ms = 20000;
    cfg->confirm_timeout_ms = 10000;
    cfg->beep_ms = 500;
    cfg->eve = eve;
    cfg->timing = &BT817_TIMING_NHD_50_800480;
}

void bu_init(bu_ctx_t *ctx, const ocx_hal_t *hal, const bu_cfg_t *cfg)
{
    memset(ctx, 0, sizeof *ctx);
    ctx->hal = hal;
    ctx->cfg = *cfg;
    bt817_init(&ctx->eve, hal);
}

static bu_status_t set(bu_ctx_t *c, bu_block_t b, bu_status_t s, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(c->res[b].detail, sizeof c->res[b].detail, fmt, ap);
    va_end(ap);
    c->res[b].status = s;
    return s;
}

static void prompt(bu_ctx_t *c, const char *fmt, ...)
{
    if (!c->cfg.prompt) return;
    char msg[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(msg, sizeof msg, fmt, ap);
    va_end(ap);
    c->cfg.prompt(c->cfg.user, msg);
}

static void list_buttons(uint32_t mask, char *buf, size_t len)
{
    size_t n = 0;
    buf[0] = 0;
    for (int i = 0; i < 18 && n < len; i++) {
        if (mask & (1u << i))
            n += (size_t)snprintf(buf + n, len - n, "%s%s", n ? "," : "", ocx_button_name(1u << i));
    }
}

/* ---- 1. REG_ID ---------------------------------------------------------- */
static bu_status_t run_eve_id(bu_ctx_t *c)
{
    c->eve_ok = false;
    ocx_err_t e = bt817_boot(&c->eve, &c->cfg.eve);
    if (e == OCX_OK) {
        c->eve_ok = true;
        return set(c, BU_EVE_ID, BU_PASS, "REG_ID=0x%02X en SPI%s, CPURESET=0, SCLK %lu MHz",
                   c->eve.chip_id, c->cfg.eve.quad ? " y QSPI" : "",
                   (unsigned long)(c->cfg.eve.run_hz / 1000000));
    }
    if (e == OCX_ERR_STATE && c->cfg.eve.quad) {
        return set(c, BU_EVE_ID, BU_FAIL,
                   "REG_ID correcto en SPI simple pero 0x%02X en QSPI: revisar IO2 (GPIO%d) e IO3 (GPIO%d)",
                   c->eve.chip_id, OCX_PIN_EVE_IO2, OCX_PIN_EVE_IO3);
    }
    uint8_t id_ext = c->eve.chip_id;
    if (c->cfg.eve.use_crystal) {
        /* Diagnóstico: ¿responde con el oscilador interno? */
        bt817_cfg_t alt = c->cfg.eve;
        alt.use_crystal = false;
        alt.clk_mult = 0;
        alt.quad = false;
        if (bt817_boot(&c->eve, &alt) == OCX_OK) {
            return set(c, BU_EVE_ID, BU_FAIL,
                       "sin respuesta con CLKEXT (REG_ID=0x%02X) pero si con el oscilador interno: "
                       "revisar el cristal de 12 MHz y sus condensadores", id_ext);
        }
    }
    return set(c, BU_EVE_ID, BU_FAIL,
               "REG_ID=0x%02X (%s): revisar 3V3/1V2, PD_N (GPIO%d), CS (GPIO%d), SCK (GPIO%d), "
               "MOSI (GPIO%d), MISO (GPIO%d)",
               id_ext, ocx_err_str(e), OCX_PIN_EVE_PD_N, OCX_PIN_EVE_CS, OCX_PIN_EVE_SCLK,
               OCX_PIN_EVE_IO0, OCX_PIN_EVE_IO1);
}

/* ---- 2. Cristal con REG_CLOCK ------------------------------------------ */
static bu_status_t run_eve_clock(bu_ctx_t *c)
{
    if (!c->eve_ok) return set(c, BU_EVE_CLOCK, BU_SKIP, "BT817 no disponible");
    uint32_t hz = 0;
    ocx_err_t e = bt817_measure_clock(&c->eve, c->cfg.clock_window_ms, &hz);
    if (e != OCX_OK) return set(c, BU_EVE_CLOCK, BU_FAIL, "lectura de REG_CLOCK: %s", ocx_err_str(e));
    c->measured_hz = hz;
    const int64_t exp = c->eve.sys_hz;
    const int64_t ppm = ((int64_t)hz - exp) * 1000000 / exp;
    const int64_t aps = ppm < 0 ? -ppm : ppm;
    if (aps <= (int64_t)c->cfg.clock_tol_ppm)
        return set(c, BU_EVE_CLOCK, BU_PASS, "REG_CLOCK: %lu Hz (esperado %lu, %+lld ppm)",
                   (unsigned long)hz, (unsigned long)exp, (long long)ppm);
    return set(c, BU_EVE_CLOCK, BU_FAIL, "REG_CLOCK: %lu Hz (esperado %lu, %+lld ppm > %lu ppm)%s",
               (unsigned long)hz, (unsigned long)exp, (long long)ppm,
               (unsigned long)c->cfg.clock_tol_ppm,
               (hz > 54000000 && hz < 66000000) ? ": parece el oscilador interno (60 MHz)" : "");
}

/* ---- 3. Pantalla -------------------------------------------------------- */
static bu_status_t run_display(bu_ctx_t *c)
{
    if (!c->eve_ok) return set(c, BU_DISPLAY, BU_SKIP, "BT817 no disponible");
    const bt817_timing_t *t = c->cfg.timing;
    char why[96] = "";
    ocx_err_t e = bt817_display_init(&c->eve, t);
    if (e == OCX_OK) e = bt817_display_check(&c->eve, t, why, sizeof why);
    if (e != OCX_OK) return set(c, BU_DISPLAY, BU_FAIL, "configuracion: %s %s", ocx_err_str(e), why);
    bt817_backlight(&c->eve, 50);
    if ((e = bt817_test_pattern(&c->eve, t)) != OCX_OK)
        return set(c, BU_DISPLAY, BU_FAIL, "lista de visualizacion: %s", ocx_err_str(e));

    uint32_t f0 = 0, f1 = 0;
    const uint32_t win = 250;
    bt817_rd32(&c->eve, REG_FRAMES, &f0);
    ocx_delay_ms(c->hal, win);
    bt817_rd32(&c->eve, REG_FRAMES, &f1);
    c->fps = (f1 - f0) * 1000u / win;
    const uint32_t exp = c->eve.sys_hz / ((uint32_t)t->pclk * t->hcycle * t->vcycle);
    if (c->fps * 10 < exp * 8 || c->fps * 10 > exp * 12)
        return set(c, BU_DISPLAY, BU_FAIL, "REG_FRAMES: %lu fps (esperado ~%lu): PCLK no avanza",
                   (unsigned long)c->fps, (unsigned long)exp);
    prompt(c, "Pantalla: deben verse 4 barras verticales ROJO, VERDE, AZUL, BLANCO (izq. a dcha.)");
    return set(c, BU_DISPLAY, BU_PASS, "%ux%u, SWIZZLE=%u, %lu fps; barras R/G/B/blanco (revision visual)",
               t->hsize, t->vsize, t->swizzle, (unsigned long)c->fps);
}

/* ---- 4. Botones --------------------------------------------------------- */
static bu_status_t run_buttons(bu_ctx_t *c)
{
    c->input_ok = false;
    ocx_err_t e = ocx_input_init(&c->input, c->hal);
    if (e == OCX_ERR_STATE)
        return set(c, BU_BUTTONS, BU_FAIL, "MCP23017 responde pero la relectura de IOCON/IODIR/GPPU no coincide");
    if (e != OCX_OK)
        return set(c, BU_BUTTONS, BU_FAIL, "MCP23017 sin respuesta en 0x%02X (SCL GPIO%d, SDA GPIO%d, RESET GPIO%d): %s",
                   OCX_MCP_I2C_ADDR, OCX_PIN_I2C_SCL, OCX_PIN_I2C_SDA, OCX_PIN_MCP_RESET, ocx_err_str(e));
    c->input_ok = true;

    char names[128];
    uint32_t idle = 0;
    if ((e = ocx_input_read_buttons(&c->input, &idle)) != OCX_OK)
        return set(c, BU_BUTTONS, BU_FAIL, "lectura GPIO del MCP23017: %s", ocx_err_str(e));
    if (idle) {
        list_buttons(idle, names, sizeof names);
        return set(c, BU_BUTTONS, BU_FAIL, "pulsados en reposo (cortocircuito o pulsador atascado): %s", names);
    }
    if (!ocx_gpio_read(c->hal, OCX_PIN_MCP_INT))
        return set(c, BU_BUTTONS, BU_FAIL, "INTA (GPIO%d) a nivel bajo en reposo", OCX_PIN_MCP_INT);
    if (!c->cfg.interactive)
        return set(c, BU_BUTTONS, BU_PASS, "MCP23017 en 0x%02X, IOCON=0x%02X, todos en reposo (prueba interactiva omitida)",
                   OCX_MCP_I2C_ADDR, OCX_MCP_IOCON);

    prompt(c, "Botones: pulsa una vez cada uno de los %d botones (incluidos L3 y R3) en %lu s",
           OCX_BUTTON_COUNT, (unsigned long)(c->cfg.button_timeout_ms / 1000));
    uint32_t seen = 0, last = 0;
    unsigned int_ports = 0; /* bit0 = INTA por GPA, bit1 = INTA por GPB */
    const uint64_t t_end = ocx_now_us(c->hal) + (uint64_t)c->cfg.button_timeout_ms * 1000;
    while (ocx_now_us(c->hal) < t_end) {
        if (!ocx_gpio_read(c->hal, OCX_PIN_MCP_INT)) {
            uint16_t flags = 0, cap = 0;
            mcp23017_read_int(&c->input.mcp, &flags, &cap);
            if (flags & 0x00FF) int_ports |= 1;
            if (flags & 0xFF00) int_ports |= 2;
        }
        uint32_t now = 0;
        ocx_input_read_buttons(&c->input, &now);
        uint32_t newly = now & ~last & ~seen;
        if (newly) {
            list_buttons(newly, names, sizeof names);
            prompt(c, "  %s OK (%d/%d)", names, ocx_popcount32(seen | newly), OCX_BUTTON_COUNT);
        }
        seen |= now;
        last = now;
        if (seen == OCX_ALL_BUTTONS && !now) break;
        ocx_delay_ms(c->hal, 10);
    }
    uint32_t missing = OCX_ALL_BUTTONS & ~seen;
    if (missing) {
        list_buttons(missing, names, sizeof names);
        return set(c, BU_BUTTONS, BU_FAIL, "%d/%d botones; faltan: %s", ocx_popcount32(seen),
                   OCX_BUTTON_COUNT, names);
    }
    if (int_ports != 3)
        return set(c, BU_BUTTONS, BU_FAIL, "16/16 botones pero INTA no se activo con el puerto %s: "
                   "revisar IOCON.MIRROR y la linea GPIO%d", (int_ports & 2) ? "A" : "B", OCX_PIN_MCP_INT);
    return set(c, BU_BUTTONS, BU_PASS, "16/16 botones; INTA activa con GPA y GPB (MIRROR=1)");
}

/* ---- 5. Joysticks ------------------------------------------------------- */
static bu_status_t run_joysticks(bu_ctx_t *c)
{
    ocx_input_t *in = &c->input;
    if (!c->input_ok) { /* el ADC no depende del MCP: preparamos las calibraciones */
        static const ocx_axis_cal_t def = OCX_AXIS_CAL_DEFAULT;
        in->hal = c->hal;
        for (int a = 0; a < OCX_AXIS_COUNT; a++) in->cal[a] = def;
    }
    char buf[200];
    size_t n = 0;
    bool fail = false, warn = false;
    for (int a = 0; a < OCX_AXIS_COUNT; a++) {
        int lo = ADC_FULL, hi = 0;
        long acc = 0;
        for (int i = 0; i < 32; i++) {
            int v = 0;
            ocx_err_t e = c->hal->adc_read(c->hal->ctx, OCX_AXIS_PIN[a], &v);
            if (e != OCX_OK) return set(c, BU_JOYSTICKS, BU_FAIL, "ADC GPIO%d: %s", OCX_AXIS_PIN[a], ocx_err_str(e));
            acc += v;
            if (v < lo) lo = v;
            if (v > hi) hi = v;
            ocx_delay_ms(c->hal, 1);
        }
        int center = (int)(acc / 32), noise = hi - lo;
        in->cal[a].center = center;
        in->cal[a].deadzone = noise * 2 > 80 ? noise * 2 : 80;
        const char *tag = "";
        if (center < ADC_FULL * 30 / 100 || center > ADC_FULL * 70 / 100) {
            fail = true;
            tag = center < 100 ? "(a GND?)" : center > ADC_FULL - 100 ? "(a 3V3?)" : "(descentrado)";
        } else if (noise > 150) {
            warn = true;
            tag = "(ruidoso)";
        }
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%s%s=%d±%d%s", a ? " " : "", ocx_axis_name((ocx_axis_t)a),
                              center, noise / 2, tag);
    }
    if (fail) return set(c, BU_JOYSTICKS, BU_FAIL, "reposo: %s (revisar FPC del joystick)", buf);
    if (!c->cfg.interactive)
        return set(c, BU_JOYSTICKS, warn ? BU_WARN : BU_PASS, "reposo: %s (recorrido no probado)", buf);

    prompt(c, "Joysticks: lleva los dos joysticks hasta los topes en todas las direcciones (%lu s)",
           (unsigned long)(c->cfg.joystick_timeout_ms / 1000));
    int mn[OCX_AXIS_COUNT], mx[OCX_AXIS_COUNT];
    for (int a = 0; a < OCX_AXIS_COUNT; a++) mn[a] = mx[a] = in->cal[a].center;
    const int lo_t = ADC_FULL * 15 / 100, hi_t = ADC_FULL * 85 / 100;
    const uint64_t t_end = ocx_now_us(c->hal) + (uint64_t)c->cfg.joystick_timeout_ms * 1000;
    bool done = false;
    while (!done && ocx_now_us(c->hal) < t_end) {
        done = true;
        for (int a = 0; a < OCX_AXIS_COUNT; a++) {
            int v = 0;
            c->hal->adc_read(c->hal->ctx, OCX_AXIS_PIN[a], &v);
            if (v < mn[a]) mn[a] = v;
            if (v > mx[a]) mx[a] = v;
            if (mn[a] > lo_t || mx[a] < hi_t) done = false;
        }
        ocx_delay_ms(c->hal, 10);
    }
    n = 0;
    for (int a = 0; a < OCX_AXIS_COUNT; a++) {
        in->cal[a].min = mn[a];
        in->cal[a].max = mx[a];
        bool ok = mn[a] <= lo_t && mx[a] >= hi_t;
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%s%s=%d..%d..%d%s", a ? " " : "",
                              ocx_axis_name((ocx_axis_t)a), mn[a], in->cal[a].center, mx[a], ok ? "" : "(corto)");
    }
    if (!done) return set(c, BU_JOYSTICKS, BU_FAIL, "recorrido insuficiente: %s", buf);
    return set(c, BU_JOYSTICKS, warn ? BU_WARN : BU_PASS, "calibrado %s", buf);
}

/* ---- 6. Pitido ---------------------------------------------------------- */
static bu_status_t run_beep(bu_ctx_t *c)
{
    if (!c->eve_ok) return set(c, BU_BEEP, BU_SKIP, "BT817 no disponible");
    bt817_t *d = &c->eve;
    ocx_gpio_write(c->hal, OCX_PIN_AMP_SD, 1); /* PAM8302A activo */
    ocx_delay_ms(c->hal, 10);
    ocx_err_t e = bt817_sound_play(d, SOUND_SINE, MIDI_A4, 255);
    uint16_t snd = 0;
    bool busy = false;
    if (e == OCX_OK) e = bt817_rd16(d, REG_SOUND, &snd);
    if (e == OCX_OK) e = bt817_sound_busy(d, &busy);
    ocx_delay_ms(c->hal, c->cfg.beep_ms);
    ocx_err_t e2 = bt817_sound_stop(d);
    bool stopped = false;
    for (int i = 0; i < 20 && e2 == OCX_OK; i++) {
        bool b = true;
        e2 = bt817_sound_busy(d, &b);
        if (!b) { stopped = true; break; }
        ocx_delay_ms(c->hal, 5);
    }
    ocx_delay_ms(c->hal, 10);
    ocx_gpio_write(c->hal, OCX_PIN_AMP_SD, 0);

    if (e != OCX_OK || e2 != OCX_OK) return set(c, BU_BEEP, BU_FAIL, "acceso a registros de sonido: %s",
                                                ocx_err_str(e != OCX_OK ? e : e2));
    const uint16_t want = (uint16_t)((MIDI_A4 << 8) | SOUND_SINE);
    if (snd != want || !busy || !stopped)
        return set(c, BU_BEEP, BU_FAIL, "REG_SOUND=0x%04X (esperado 0x%04X), REG_PLAY %s, parada %s", snd, want,
                   busy ? "1" : "0", stopped ? "OK" : "sin terminar");

    if (!c->cfg.interactive || !c->input_ok)
        return set(c, BU_BEEP, BU_PASS, "seno 440 Hz %lu ms con GPIO%d=1; audicion sin confirmar",
                   (unsigned long)c->cfg.beep_ms, OCX_PIN_AMP_SD);

    prompt(c, "Pitido: ¿se ha oido el tono de 440 Hz? Pulsa X = si, O = no (%lu s)",
           (unsigned long)(c->cfg.confirm_timeout_ms / 1000));
    const uint64_t t_end = ocx_now_us(c->hal) + (uint64_t)c->cfg.confirm_timeout_ms * 1000;
    while (ocx_now_us(c->hal) < t_end) {
        uint32_t b = 0;
        ocx_input_read_buttons(&c->input, &b);
        if (b & OCX_BTN_X) return set(c, BU_BEEP, BU_PASS, "seno 440 Hz audible (confirmado por el operador)");
        if (b & OCX_BTN_O)
            return set(c, BU_BEEP, BU_FAIL, "registros OK pero no se oye: revisar AUDIO_L, PAM8302A (~SD GPIO%d) y altavoz",
                       OCX_PIN_AMP_SD);
        ocx_delay_ms(c->hal, 10);
    }
    return set(c, BU_BEEP, BU_WARN, "registros OK; audicion sin confirmar (timeout)");
}

bu_status_t bu_run_block(bu_ctx_t *c, bu_block_t b)
{
    switch (b) {
    case BU_EVE_ID: return run_eve_id(c);
    case BU_EVE_CLOCK: return run_eve_clock(c);
    case BU_DISPLAY: return run_display(c);
    case BU_BUTTONS: return run_buttons(c);
    case BU_JOYSTICKS: return run_joysticks(c);
    case BU_BEEP: return run_beep(c);
    default: return BU_NOT_RUN;
    }
}

int bu_run_all(bu_ctx_t *c)
{
    int fails = 0;
    for (int b = 0; b < BU_COUNT; b++) {
        prompt(c, "== %s ==", bu_block_name((bu_block_t)b));
        if (bu_run_block(c, (bu_block_t)b) == BU_FAIL) fails++;
    }
    return fails;
}

void bu_format_line(const bu_ctx_t *c, bu_block_t b, char *buf, size_t len)
{
    snprintf(buf, len, "[%s] %-10s %s", bu_status_name(c->res[b].status), bu_block_name(b), c->res[b].detail);
}
