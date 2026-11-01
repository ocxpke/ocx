/* Pruebas de los bloques de puesta en marcha: caso correcto y cada avería. */
#include "ocx_board.h"
#include "ocx_bringup.h"
#include "sim.h"
#include "test.h"

typedef struct {
    sim_t *sim;
    ocx_hal_t hal;
    bu_ctx_t ctx;
} rig_t;

static void rig_run(rig_t *r, const sim_faults_t *f, bool interactive)
{
    r->sim = sim_create(f);
    r->hal = sim_hal(r->sim);
    sim_operator_enable(r->sim, true);
    bu_cfg_t cfg;
    bu_default_cfg(&cfg);
    cfg.interactive = interactive;
    cfg.prompt = sim_operator_prompt;
    cfg.user = r->sim;
    bu_init(&r->ctx, &r->hal, &cfg);
    bu_run_all(&r->ctx);
}

static bu_status_t st(rig_t *r, bu_block_t b) { return r->ctx.res[b].status; }
static const char *det(rig_t *r, bu_block_t b) { return r->ctx.res[b].detail; }

static void test_all_pass(void)
{
    rig_t r;
    rig_run(&r, NULL, true);
    for (int b = 0; b < BU_COUNT; b++) {
        CHECK_EQ(st(&r, (bu_block_t)b), BU_PASS);
        if (st(&r, (bu_block_t)b) != BU_PASS) printf("    %s: %s\n", bu_block_name((bu_block_t)b), det(&r, (bu_block_t)b));
    }
    CHECK(r.ctx.measured_hz > 71990000 && r.ctx.measured_hz < 72010000);
    CHECK(r.ctx.fps >= 70 && r.ctx.fps <= 78);
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "16/16");
    CHECK_STR_HAS(det(&r, BU_BEEP), "confirmado");
    CHECK_EQ(sim_audible_beeps(r.sim), 1);
    CHECK_EQ(sim_gpio_out(r.sim, OCX_PIN_AMP_SD), 0); /* amplificador apagado al final */
    /* Calibración de los joysticks tras el recorrido */
    for (int a = 0; a < OCX_AXIS_COUNT; a++) {
        CHECK(r.ctx.input.cal[a].min <= 4095 * 15 / 100);
        CHECK(r.ctx.input.cal[a].max >= 4095 * 85 / 100);
    }
    sim_destroy(r.sim);
}

static void test_non_interactive(void)
{
    rig_t r;
    rig_run(&r, NULL, false);
    for (int b = 0; b < BU_COUNT; b++) CHECK_EQ(st(&r, (bu_block_t)b), BU_PASS);
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "omitida");
    CHECK_STR_HAS(det(&r, BU_BEEP), "sin confirmar");
    sim_destroy(r.sim);
}

static void test_eve_absent(void)
{
    sim_faults_t f = {.eve_absent = true};
    rig_t r;
    rig_run(&r, &f, true);
    CHECK_EQ(st(&r, BU_EVE_ID), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_EVE_ID), "PD_N (GPIO4)");
    CHECK_EQ(st(&r, BU_EVE_CLOCK), BU_SKIP);
    CHECK_EQ(st(&r, BU_DISPLAY), BU_SKIP);
    CHECK_EQ(st(&r, BU_BEEP), BU_SKIP);
    CHECK_EQ(st(&r, BU_BUTTONS), BU_PASS); /* bloques independientes siguen */
    CHECK_EQ(st(&r, BU_JOYSTICKS), BU_PASS);
    sim_destroy(r.sim);
}

static void test_no_crystal(void)
{
    sim_faults_t f = {.no_crystal = true};
    rig_t r;
    rig_run(&r, &f, false);
    CHECK_EQ(st(&r, BU_EVE_ID), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_EVE_ID), "cristal");
    sim_destroy(r.sim);
}

static void test_crystal_off_frequency(void)
{
    sim_faults_t f = {.xtal_ppm = 5000};
    rig_t r;
    rig_run(&r, &f, false);
    CHECK_EQ(st(&r, BU_EVE_ID), BU_PASS);
    CHECK_EQ(st(&r, BU_EVE_CLOCK), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_EVE_CLOCK), "+50");
    sim_destroy(r.sim);
}

static void test_crystal_in_tolerance(void)
{
    sim_faults_t f = {.xtal_ppm = -50};
    rig_t r;
    rig_run(&r, &f, false);
    CHECK_EQ(st(&r, BU_EVE_CLOCK), BU_PASS);
    sim_destroy(r.sim);
}

static void test_qspi_broken(void)
{
    sim_faults_t f = {.qspi_io23_broken = true};
    rig_t r;
    rig_run(&r, &f, false);
    CHECK_EQ(st(&r, BU_EVE_ID), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_EVE_ID), "IO2 (GPIO14)");
    CHECK_STR_HAS(det(&r, BU_EVE_ID), "IO3 (GPIO9)");
    sim_destroy(r.sim);
}

static void test_pclk_dead(void)
{
    sim_faults_t f = {.pclk_dead = true};
    rig_t r;
    rig_run(&r, &f, false);
    CHECK_EQ(st(&r, BU_DISPLAY), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_DISPLAY), "REG_FRAMES");
    sim_destroy(r.sim);
}

static void test_mcp_absent(void)
{
    sim_faults_t f = {.mcp_absent = true};
    rig_t r;
    rig_run(&r, &f, true);
    CHECK_EQ(st(&r, BU_BUTTONS), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "0x20");
    CHECK_EQ(st(&r, BU_JOYSTICKS), BU_PASS); /* el ADC no depende del MCP */
    CHECK_EQ(st(&r, BU_BEEP), BU_PASS);      /* sin confirmación posible */
    CHECK_STR_HAS(det(&r, BU_BEEP), "sin confirmar");
    sim_destroy(r.sim);
}

static void test_stuck_button(void)
{
    sim_faults_t f = {.stuck_buttons = OCX_BTN_HOME};
    rig_t r;
    rig_run(&r, &f, true);
    CHECK_EQ(st(&r, BU_BUTTONS), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "HOME");
    sim_destroy(r.sim);
}

static void test_dead_button(void)
{
    sim_faults_t f = {.dead_buttons = OCX_BTN_T_R | OCX_BTN_L3};
    rig_t r;
    rig_run(&r, &f, true);
    CHECK_EQ(st(&r, BU_BUTTONS), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "14/16");
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "T_R");
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "L3");
    sim_destroy(r.sim);
}

static void test_no_mirror(void)
{
    sim_faults_t f = {.mcp_no_mirror = true};
    rig_t r;
    rig_run(&r, &f, true);
    CHECK_EQ(st(&r, BU_BUTTONS), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_BUTTONS), "MIRROR");
    sim_destroy(r.sim);
}

static void test_joystick_grounded(void)
{
    sim_faults_t f = {0};
    f.axis_fault[OCX_AXIS_RY] = 1;
    rig_t r;
    rig_run(&r, &f, true);
    CHECK_EQ(st(&r, BU_JOYSTICKS), BU_FAIL);
    CHECK_STR_HAS(det(&r, BU_JOYSTICKS), "R.Y");
    CHECK_STR_HAS(det(&r, BU_JOYSTICKS), "GND");
    sim_destroy(r.sim);
}

static void test_mute(void)
{
    sim_faults_t f = {.amp_unwired = true};
    rig_t r;
    rig_run(&r, &f, true);
    CHECK_EQ(st(&r, BU_BEEP), BU_FAIL); /* el operador pulsa O */
    CHECK_STR_HAS(det(&r, BU_BEEP), "GPIO21");
    sim_destroy(r.sim);
}

int main(void)
{
    RUN(test_all_pass);
    RUN(test_non_interactive);
    RUN(test_eve_absent);
    RUN(test_no_crystal);
    RUN(test_crystal_off_frequency);
    RUN(test_crystal_in_tolerance);
    RUN(test_qspi_broken);
    RUN(test_pclk_dead);
    RUN(test_mcp_absent);
    RUN(test_stuck_button);
    RUN(test_dead_button);
    RUN(test_no_mirror);
    RUN(test_joystick_grounded);
    RUN(test_mute);
    return DONE();
}
