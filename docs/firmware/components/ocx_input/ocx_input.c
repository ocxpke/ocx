#include "ocx_input.h"
#include "ocx_board.h"

const int OCX_AXIS_PIN[OCX_AXIS_COUNT] = {
    [OCX_AXIS_LX] = OCX_PIN_JOY_L_X,
    [OCX_AXIS_LY] = OCX_PIN_JOY_L_Y,
    [OCX_AXIS_RX] = OCX_PIN_JOY_R_X,
    [OCX_AXIS_RY] = OCX_PIN_JOY_R_Y,
};

const char *ocx_axis_name(ocx_axis_t a)
{
    static const char *n[] = {"L.X", "L.Y", "R.X", "R.Y"};
    return (unsigned)a < OCX_AXIS_COUNT ? n[a] : "?";
}

const char *ocx_button_name(uint32_t bit)
{
    switch (bit) {
    case OCX_BTN_T_L: return "T_L";
    case OCX_BTN_A_UP: return "UP";
    case OCX_BTN_A_R: return "RIGHT";
    case OCX_BTN_A_L: return "LEFT";
    case OCX_BTN_A_DW: return "DOWN";
    case OCX_BTN_SLCT: return "SELECT";
    case OCX_BTN_VOL_M: return "VOL-";
    case OCX_BTN_VOL_P: return "VOL+";
    case OCX_BTN_HOME: return "HOME";
    case OCX_BTN_X: return "X";
    case OCX_BTN_O: return "O";
    case OCX_BTN_C: return "SQUARE";
    case OCX_BTN_T: return "TRIANGLE";
    case OCX_BTN_T_R: return "T_R";
    case OCX_BTN_L3: return "L3";
    case OCX_BTN_R3: return "R3";
    default: return "?";
    }
}

int ocx_popcount32(uint32_t v)
{
    int n = 0;
    for (; v; v &= v - 1) n++;
    return n;
}

uint32_t ocx_buttons_decode(uint16_t mcp_gpio, int l3_level, int r3_level)
{
    uint32_t b = (uint32_t)(~mcp_gpio) & OCX_MCP_BUTTON_MASK; /* pulsado = 0 V */
    if (!l3_level) b |= OCX_BTN_L3;
    if (!r3_level) b |= OCX_BTN_R3;
    return b;
}

int ocx_axis_normalize(const ocx_axis_cal_t *c, int raw)
{
    int d = raw - c->center;
    if (d > -c->deadzone && d < c->deadzone) return 0;
    int span, v;
    if (d > 0) {
        span = c->max - c->center - c->deadzone;
        v = span > 0 ? (d - c->deadzone) * 1000 / span : 0;
    } else {
        span = c->center - c->min - c->deadzone;
        v = span > 0 ? (d + c->deadzone) * 1000 / span : 0;
    }
    if (v > 1000) v = 1000;
    if (v < -1000) v = -1000;
    return v;
}

ocx_err_t ocx_input_init(ocx_input_t *in, const ocx_hal_t *hal)
{
    static const ocx_axis_cal_t def = OCX_AXIS_CAL_DEFAULT;
    in->hal = hal;
    for (int i = 0; i < OCX_AXIS_COUNT; i++) in->cal[i] = def;
    mcp23017_init(&in->mcp, hal, OCX_MCP_I2C_ADDR, OCX_PIN_MCP_RESET);
    return mcp23017_setup_inputs(&in->mcp, OCX_MCP_BUTTON_MASK);
}

ocx_err_t ocx_input_read_buttons(ocx_input_t *in, uint32_t *buttons)
{
    uint16_t g = 0xFFFF;
    ocx_err_t e = mcp23017_read_gpio(&in->mcp, &g);
    *buttons = ocx_buttons_decode(g, ocx_gpio_read(in->hal, OCX_PIN_JOY_L_BTN),
                                  ocx_gpio_read(in->hal, OCX_PIN_JOY_R_BTN));
    return e;
}

ocx_err_t ocx_input_read_axis_raw(ocx_input_t *in, ocx_axis_t a, int samples, int *raw)
{
    if (samples < 1) samples = 1;
    long acc = 0;
    for (int i = 0; i < samples; i++) {
        int v = 0;
        ocx_err_t e = in->hal->adc_read(in->hal->ctx, OCX_AXIS_PIN[a], &v);
        if (e != OCX_OK) return e;
        acc += v;
    }
    *raw = (int)((acc + samples / 2) / samples);
    return OCX_OK;
}

ocx_err_t ocx_input_read(ocx_input_t *in, ocx_input_state_t *st)
{
    ocx_err_t e = ocx_input_read_buttons(in, &st->buttons);
    for (int a = 0; a < OCX_AXIS_COUNT; a++) {
        ocx_err_t ea = ocx_input_read_axis_raw(in, (ocx_axis_t)a, 4, &st->raw[a]);
        if (ea != OCX_OK) e = ea;
        st->axis[a] = ocx_axis_normalize(&in->cal[a], st->raw[a]);
    }
    return e;
}
