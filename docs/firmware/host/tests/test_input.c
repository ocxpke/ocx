/* Pruebas de la capa de entrada: mapa de botones y normalización de ejes. */
#include "ocx_board.h"
#include "ocx_input.h"
#include "sim.h"
#include "test.h"

static void test_decode(void)
{
    CHECK_EQ(ocx_buttons_decode(0xFFFF, 1, 1), 0);
    /* GPA7 y GPB7 no tienen botón: se ignoran aunque estén a 0 */
    CHECK_EQ(ocx_buttons_decode(0x7F7F, 1, 1), 0);
    CHECK_EQ(ocx_buttons_decode((uint16_t)~(1u << 2), 1, 1), OCX_BTN_A_R);
    CHECK_EQ(ocx_buttons_decode((uint16_t)~(1u << 10), 1, 1), OCX_BTN_X);
    CHECK_EQ(ocx_buttons_decode(0xFFFF, 0, 1), OCX_BTN_L3);
    CHECK_EQ(ocx_buttons_decode(0xFFFF, 1, 0), OCX_BTN_R3);
    CHECK_EQ(ocx_buttons_decode(0x0000, 0, 0), OCX_ALL_BUTTONS);
    CHECK_EQ(ocx_popcount32(OCX_ALL_BUTTONS), OCX_BUTTON_COUNT);
}

static void test_names_unique(void)
{
    for (int i = 0; i < 18; i++) {
        uint32_t bi = 1u << i;
        if (!(OCX_ALL_BUTTONS & bi)) continue;
        CHECK(strcmp(ocx_button_name(bi), "?") != 0);
        for (int j = i + 1; j < 18; j++) {
            uint32_t bj = 1u << j;
            if (OCX_ALL_BUTTONS & bj) CHECK(strcmp(ocx_button_name(bi), ocx_button_name(bj)) != 0);
        }
    }
}

static void test_pins(void)
{
    CHECK_EQ(OCX_AXIS_PIN[OCX_AXIS_LX], 6);
    CHECK_EQ(OCX_AXIS_PIN[OCX_AXIS_LY], 7);
    CHECK_EQ(OCX_AXIS_PIN[OCX_AXIS_RX], 2);
    CHECK_EQ(OCX_AXIS_PIN[OCX_AXIS_RY], 1);
    /* Todos en ADC1 (GPIO1..10 en la ESP32-S3), compatible con Wi-Fi. */
    for (int a = 0; a < OCX_AXIS_COUNT; a++) CHECK(OCX_AXIS_PIN[a] >= 1 && OCX_AXIS_PIN[a] <= 10);
}

static void test_normalize(void)
{
    ocx_axis_cal_t c = {.min = 100, .center = 2000, .max = 4000, .deadzone = 50};
    CHECK_EQ(ocx_axis_normalize(&c, 2000), 0);
    CHECK_EQ(ocx_axis_normalize(&c, 2049), 0);
    CHECK_EQ(ocx_axis_normalize(&c, 1951), 0);
    CHECK_EQ(ocx_axis_normalize(&c, 4000), 1000);
    CHECK_EQ(ocx_axis_normalize(&c, 4095), 1000); /* saturación */
    CHECK_EQ(ocx_axis_normalize(&c, 100), -1000);
    CHECK_EQ(ocx_axis_normalize(&c, 0), -1000);
    int mid = ocx_axis_normalize(&c, 2000 + 50 + (4000 - 2000 - 50) / 2);
    CHECK(mid >= 495 && mid <= 505);
    /* monotonía */
    int prev = -1001;
    for (int r = 0; r <= 4095; r += 15) {
        int v = ocx_axis_normalize(&c, r);
        CHECK(v >= prev);
        prev = v;
    }
    /* calibración degenerada: no divide por cero */
    ocx_axis_cal_t z = {.min = 2000, .center = 2000, .max = 2000, .deadzone = 0};
    CHECK_EQ(ocx_axis_normalize(&z, 3000), 0);
}

static void test_input_read(void)
{
    sim_t *s = sim_create(NULL);
    ocx_hal_t h = sim_hal(s);
    ocx_input_t in;
    CHECK_EQ(ocx_input_init(&in, &h), OCX_OK);
    sim_set_axis(s, OCX_AXIS_LX, 4095);
    sim_set_axis(s, OCX_AXIS_LY, 0);
    sim_set_axis(s, OCX_AXIS_RX, 2048);
    sim_press(s, OCX_BTN_T | OCX_BTN_R3);
    ocx_input_state_t st;
    CHECK_EQ(ocx_input_read(&in, &st), OCX_OK);
    CHECK_EQ(st.buttons, OCX_BTN_T | OCX_BTN_R3);
    CHECK(st.axis[OCX_AXIS_LX] > 950);
    CHECK(st.axis[OCX_AXIS_LY] < -950);
    CHECK_EQ(st.axis[OCX_AXIS_RX], 0);
    sim_destroy(s);
}

int main(void)
{
    RUN(test_decode);
    RUN(test_names_unique);
    RUN(test_pins);
    RUN(test_normalize);
    RUN(test_input_read);
    return DONE();
}
