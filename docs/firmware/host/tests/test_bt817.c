/* Pruebas del driver BT817 contra el modelo simulado. */
#include "bt817.h"
#include "ocx_board.h"
#include "sim.h"
#include "test.h"

static bt817_cfg_t cfg_default(void)
{
    bt817_cfg_t c = BT817_CFG_DEFAULT;
    return c;
}

static void test_headers(void)
{
    uint8_t w[3], r[4];
    bt817_hdr_write(REG_PCLK, w); /* 0x302070 */
    CHECK_EQ(w[0], 0xB0);
    CHECK_EQ(w[1], 0x20);
    CHECK_EQ(w[2], 0x70);
    bt817_hdr_read(REG_ID, r);
    CHECK_EQ(r[0], 0x30);
    CHECK_EQ(r[1], 0x20);
    CHECK_EQ(r[2], 0x00);
    CHECK_EQ(r[3], 0x00); /* dummy */
    bt817_hdr_read(0x0FFFFF, r);
    CHECK_EQ(r[0], 0x0F);
    CHECK_EQ(bt817_clksel_param(6), 0x46);
    CHECK_EQ(bt817_clksel_param(3), 0x03);
}

static void test_timing_constants(void)
{
    const bt817_timing_t *t = &BT817_TIMING_NHD_50_800480;
    CHECK_EQ(t->hsize, 800);
    CHECK_EQ(t->vsize, 480);
    CHECK_EQ(t->swizzle, 3);
    CHECK_EQ(t->hcycle, t->hsize + 40 + 48 + 40); /* HFP + HSYNC + HBP */
    CHECK_EQ(t->vcycle, t->vsize + 13 + 3 + 29);
    CHECK_EQ(t->hoffset, 48 + 40);
    CHECK_EQ(t->voffset, 3 + 29);
    /* ~74 Hz con 72 MHz / 2 */
    unsigned fps = 72000000u / (t->pclk * t->hcycle * t->vcycle);
    CHECK(fps >= 60 && fps <= 80);
}

static void test_boot_ok(void)
{
    sim_t *s = sim_create(NULL);
    ocx_hal_t h = sim_hal(s);
    bt817_t d;
    bt817_init(&d, &h);
    bt817_cfg_t c = cfg_default();
    CHECK_EQ(bt817_boot(&d, &c), OCX_OK);
    CHECK_EQ(d.chip_id, 0x7C);
    CHECK_EQ(d.sys_hz, 72000000);
    CHECK_EQ(sim_eve_sys_hz(s), 72000000);
    CHECK_EQ(sim_eve_width(s), 4);
    CHECK_EQ(sim_host_width(s), 4);
    CHECK_EQ(sim_host_hz(s), c.run_hz);
    CHECK_EQ(sim_eve_reg(s, REG_FREQUENCY), 72000000);
    CHECK_EQ(sim_gpio_out(s, OCX_PIN_EVE_PD_N), 1);
    /* Lectura y escritura en RAM_G en QSPI */
    uint8_t buf[700], back[700];
    for (int i = 0; i < 700; i++) buf[i] = (uint8_t)(i * 7);
    CHECK_EQ(bt817_wr_mem(&d, 0x1000, buf, sizeof buf), OCX_OK); /* > un bloque */
    CHECK_EQ(bt817_rd_mem(&d, 0x1000, back, sizeof back), OCX_OK);
    CHECK(memcmp(buf, back, sizeof buf) == 0);
    sim_destroy(s);
}

static void test_boot_no_crystal(void)
{
    sim_faults_t f = {.no_crystal = true};
    sim_t *s = sim_create(&f);
    ocx_hal_t h = sim_hal(s);
    bt817_t d;
    bt817_init(&d, &h);
    bt817_cfg_t c = cfg_default();
    CHECK_EQ(bt817_boot(&d, &c), OCX_ERR_TIMEOUT);
    c.use_crystal = false;
    c.clk_mult = 0;
    CHECK_EQ(bt817_boot(&d, &c), OCX_OK); /* con oscilador interno sí arranca */
    CHECK_EQ(d.sys_hz, 60000000);
    sim_destroy(s);
}

static void test_boot_qspi_broken(void)
{
    sim_faults_t f = {.qspi_io23_broken = true};
    sim_t *s = sim_create(&f);
    ocx_hal_t h = sim_hal(s);
    bt817_t d;
    bt817_init(&d, &h);
    bt817_cfg_t c = cfg_default();
    CHECK_EQ(bt817_boot(&d, &c), OCX_ERR_STATE);
    CHECK(d.chip_id != 0x7C);
    c.quad = false;
    CHECK_EQ(bt817_boot(&d, &c), OCX_OK); /* en SPI simple funciona */
    sim_destroy(s);
}

static void test_clock_measure(void)
{
    const int32_t ppm[] = {0, 40, -40, 3000};
    for (unsigned i = 0; i < sizeof ppm / sizeof ppm[0]; i++) {
        sim_faults_t f = {.xtal_ppm = ppm[i]};
        sim_t *s = sim_create(&f);
        ocx_hal_t h = sim_hal(s);
        bt817_t d;
        bt817_init(&d, &h);
        bt817_cfg_t c = cfg_default();
        CHECK_EQ(bt817_boot(&d, &c), OCX_OK);
        uint32_t hz = 0;
        CHECK_EQ(bt817_measure_clock(&d, 100, &hz), OCX_OK);
        double exp = 72e6 * (1 + ppm[i] / 1e6);
        double err = (hz - exp) / exp * 1e6;
        CHECK(err > -20 && err < 20); /* error de medida < 20 ppm */
        sim_destroy(s);
    }
}

static void test_display_init(void)
{
    sim_t *s = sim_create(NULL);
    ocx_hal_t h = sim_hal(s);
    bt817_t d;
    bt817_init(&d, &h);
    bt817_cfg_t c = cfg_default();
    CHECK_EQ(bt817_boot(&d, &c), OCX_OK);
    const bt817_timing_t *t = &BT817_TIMING_NHD_50_800480;
    CHECK_EQ(bt817_display_init(&d, t), OCX_OK);
    char why[64] = "";
    CHECK_EQ(bt817_display_check(&d, t, why, sizeof why), OCX_OK);
    CHECK_EQ(sim_eve_reg(s, REG_SWIZZLE), 3);
    CHECK_EQ(sim_eve_reg(s, REG_HCYCLE), 928);
    CHECK_EQ(sim_eve_reg(s, REG_VCYCLE), 525);
    CHECK_EQ(sim_eve_reg(s, REG_HSYNC1), 48);
    CHECK_EQ(sim_eve_reg(s, REG_VSYNC1), 3);
    CHECK_EQ(sim_eve_reg(s, REG_PCLK_POL), 1);
    CHECK_EQ(sim_eve_reg(s, REG_PCLK), 2);
    CHECK(sim_eve_reg(s, REG_GPIOX) & GPIOX_DISP);
    CHECK(sim_eve_reg(s, REG_GPIOX_DIR) & GPIOX_DISP);
    CHECK_EQ(bt817_test_pattern(&d, t), OCX_OK);
    CHECK_EQ(sim_eve_dl_word(s, 0), DL_CLEAR_COLOR_RGB(0, 0, 0));
    CHECK_EQ(sim_eve_dl_word(s, 4), DL_COLOR_RGB(255, 0, 0));
    CHECK_EQ(sim_eve_dl_word(s, 6), DL_VERTEX2F(199, 479));
    CHECK_EQ(sim_eve_dl_word(s, 17), DL_DISPLAY());
    /* Si se cambia SWIZZLE la comprobación lo detecta */
    bt817_wr8(&d, REG_SWIZZLE, 0);
    CHECK_EQ(bt817_display_check(&d, t, why, sizeof why), OCX_ERR_STATE);
    CHECK_STR_HAS(why, "REG_SWIZZLE");
    sim_destroy(s);
}

static void test_sound(void)
{
    sim_t *s = sim_create(NULL);
    ocx_hal_t h = sim_hal(s);
    bt817_t d;
    bt817_init(&d, &h);
    bt817_cfg_t c = cfg_default();
    CHECK_EQ(bt817_boot(&d, &c), OCX_OK);
    bool busy = false;
    /* Amplificador apagado: el BT817 suena pero no se oye. */
    CHECK_EQ(bt817_sound_play(&d, SOUND_SINE, MIDI_A4, 200), OCX_OK);
    CHECK_EQ(sim_eve_reg(s, REG_SOUND) & 0xFFFF, (MIDI_A4 << 8) | SOUND_SINE);
    CHECK_EQ(sim_eve_reg(s, REG_VOL_SOUND), 200);
    CHECK_EQ(bt817_sound_busy(&d, &busy), OCX_OK);
    CHECK(busy);
    CHECK_EQ(sim_audible_beeps(s), 0);
    CHECK_EQ(bt817_sound_stop(&d), OCX_OK);
    CHECK_EQ(bt817_sound_busy(&d, &busy), OCX_OK);
    CHECK(!busy);
    h.gpio_write(h.ctx, OCX_PIN_AMP_SD, 1);
    CHECK_EQ(bt817_sound_play(&d, SOUND_SINE, MIDI_A4, 200), OCX_OK);
    CHECK_EQ(sim_audible_beeps(s), 1);
    sim_destroy(s);
}

int main(void)
{
    RUN(test_headers);
    RUN(test_timing_constants);
    RUN(test_boot_ok);
    RUN(test_boot_no_crystal);
    RUN(test_boot_qspi_broken);
    RUN(test_clock_measure);
    RUN(test_display_init);
    RUN(test_sound);
    return DONE();
}
