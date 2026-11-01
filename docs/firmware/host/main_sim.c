/*
 * main_sim.c — Pruebas de puesta en marcha de OCX sobre la placa simulada.
 *
 *   ocx_sim_bringup                    todo correcto, con operador virtual
 *   ocx_sim_bringup --no-interactive   solo comprobaciones automáticas
 *   ocx_sim_bringup --fault=<avería>   inyecta una avería (ver lista con --help)
 *
 * Devuelve 0 si no hay ningún FAIL.
 */
#include <stdio.h>
#include <string.h>

#include "ocx_bringup.h"
#include "sim.h"

static void print_prompt(void *user, const char *msg)
{
    printf("  > %s\n", msg);
    sim_operator_prompt(user, msg);
}

static const char *FAULTS[] = {
    "eve_absent", "no_crystal", "xtal_off", "qspi_io23", "pclk_dead", "mcp_absent", "no_mirror",
    "stuck_btn", "dead_btn", "joy_gnd", "mute",
};

static int apply_fault(sim_faults_t *f, const char *name)
{
    if (!strcmp(name, "eve_absent")) f->eve_absent = true;
    else if (!strcmp(name, "no_crystal")) f->no_crystal = true;
    else if (!strcmp(name, "xtal_off")) f->xtal_ppm = 5000;
    else if (!strcmp(name, "qspi_io23")) f->qspi_io23_broken = true;
    else if (!strcmp(name, "pclk_dead")) f->pclk_dead = true;
    else if (!strcmp(name, "mcp_absent")) f->mcp_absent = true;
    else if (!strcmp(name, "no_mirror")) f->mcp_no_mirror = true;
    else if (!strcmp(name, "stuck_btn")) f->stuck_buttons = OCX_BTN_HOME;
    else if (!strcmp(name, "dead_btn")) f->dead_buttons = OCX_BTN_T_R;
    else if (!strcmp(name, "joy_gnd")) f->axis_fault[OCX_AXIS_RY] = 1;
    else if (!strcmp(name, "mute")) f->amp_unwired = true;
    else return -1;
    return 0;
}

int main(int argc, char **argv)
{
    sim_faults_t f = {0};
    bu_cfg_t cfg;
    bu_default_cfg(&cfg);

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--no-interactive")) {
            cfg.interactive = false;
        } else if (!strncmp(argv[i], "--fault=", 8) && apply_fault(&f, argv[i] + 8) == 0) {
            continue;
        } else {
            printf("uso: %s [--no-interactive] [--fault=AVERIA]\naverias:", argv[0]);
            for (size_t k = 0; k < sizeof FAULTS / sizeof FAULTS[0]; k++) printf(" %s", FAULTS[k]);
            printf("\n");
            return 2;
        }
    }

    sim_t *sim = sim_create(&f);
    ocx_hal_t hal = sim_hal(sim);
    sim_operator_enable(sim, true);
    cfg.prompt = print_prompt;
    cfg.user = sim;

    bu_ctx_t ctx;
    bu_init(&ctx, &hal, &cfg);
    printf("OCX bring-up (placa simulada)\n");
    int fails = bu_run_all(&ctx);

    printf("\n---- Informe ----\n");
    char line[300];
    for (int b = 0; b < BU_COUNT; b++) {
        bu_format_line(&ctx, (bu_block_t)b, line, sizeof line);
        printf("%s\n", line);
    }
    printf("Resultado: %d FAIL, tiempo simulado %.2f s\n", fails, sim_time_us(sim) / 1e6);
    sim_destroy(sim);
    return fails ? 1 : 0;
}
