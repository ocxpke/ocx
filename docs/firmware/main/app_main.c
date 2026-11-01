/*
 * app_main.c — Firmware de puesta en marcha de OCX.
 *
 * 1. Inicializa la HAL de la ESP32-S3.
 * 2. Ejecuta las pruebas por bloques (ocx_bringup) y escribe el informe por
 *    la consola USB.
 * 3. Queda mostrando el estado de botones y joysticks. Mantener HOME + SELECT
 *    2 s repite las pruebas.
 */
#include <inttypes.h>
#include <stdio.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "hal_esp32s3.h"
#include "ocx_bringup.h"

static const char *TAG = "ocx";

#ifdef CONFIG_OCX_BRINGUP_INTERACTIVE
#define INTERACTIVE true
#else
#define INTERACTIVE false
#endif
#ifdef CONFIG_OCX_EVE_QUAD
#define EVE_QUAD true
#else
#define EVE_QUAD false
#endif

static void console_prompt(void *user, const char *msg)
{
    printf("  > %s\n", msg);
    fflush(stdout);
}

static void run_bringup(bu_ctx_t *ctx, const ocx_hal_t *hal)
{
    bu_cfg_t cfg;
    bu_default_cfg(&cfg);
    cfg.interactive = INTERACTIVE;
    cfg.eve.boot_hz = CONFIG_OCX_EVE_BOOT_HZ;
    cfg.eve.run_hz = CONFIG_OCX_EVE_RUN_HZ;
    cfg.eve.quad = EVE_QUAD;
    cfg.prompt = console_prompt;

    bu_init(ctx, hal, &cfg);
    printf("\n==== OCX bring-up ====\n");
    int fails = bu_run_all(ctx);
    printf("\n---- Informe ----\n");
    char line[300];
    for (int b = 0; b < BU_COUNT; b++) {
        bu_format_line(ctx, (bu_block_t)b, line, sizeof line);
        printf("%s\n", line);
    }
    printf("Resultado: %d FAIL\n\n", fails);
}

void app_main(void)
{
    static ocx_hal_t hal;
    static bu_ctx_t ctx;

    ESP_ERROR_CHECK(ocx_hal_esp32s3_init(&hal));
    run_bringup(&ctx, &hal);

    if (!ctx.input_ok) {
        ESP_LOGW(TAG, "MCP23017 no disponible: solo se muestran los ejes");
    }
    ocx_input_state_t prev = {0}, st;
    uint32_t combo_ms = 0;
    for (;;) {
        ocx_input_read(&ctx.input, &st);
        bool changed = st.buttons != prev.buttons;
        for (int a = 0; a < OCX_AXIS_COUNT; a++)
            if (st.axis[a] / 50 != prev.axis[a] / 50) changed = true;
        if (changed) {
            printf("btn=%05" PRIx32 "  L=(%5d,%5d)  R=(%5d,%5d)\n", st.buttons, st.axis[OCX_AXIS_LX],
                   st.axis[OCX_AXIS_LY], st.axis[OCX_AXIS_RX], st.axis[OCX_AXIS_RY]);
            prev = st;
        }
        const uint32_t combo = OCX_BTN_HOME | OCX_BTN_SLCT;
        combo_ms = ((st.buttons & combo) == combo) ? combo_ms + 20 : 0;
        if (combo_ms >= 2000) {
            combo_ms = 0;
            run_bringup(&ctx, &hal);
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
