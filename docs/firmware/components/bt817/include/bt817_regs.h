/*
 * bt817_regs.h — Mapa de memoria, registros y comandos del BT817 (EVE4)
 * usados por el firmware de OCX. Fuente: BT817/8 Datasheet y
 * BT81X Series Programming Guide (Bridgetek).
 */
#ifndef BT817_REGS_H
#define BT817_REGS_H

/* ---- Mapa de memoria ---------------------------------------------------- */
#define BT_RAM_G        0x000000UL
#define BT_RAM_DL       0x300000UL
#define BT_RAM_REG      0x302000UL
#define BT_RAM_CMD      0x308000UL
#define BT_RAM_DL_SIZE  8192u

/* ---- Registros ---------------------------------------------------------- */
#define REG_ID          0x302000UL /* siempre 0x7C */
#define REG_FRAMES      0x302004UL
#define REG_CLOCK       0x302008UL /* ciclos de reloj del sistema */
#define REG_FREQUENCY   0x30200CUL
#define REG_CPURESET    0x302020UL
#define REG_HCYCLE      0x30202CUL
#define REG_HOFFSET     0x302030UL
#define REG_HSIZE       0x302034UL
#define REG_HSYNC0      0x302038UL
#define REG_HSYNC1      0x30203CUL
#define REG_VCYCLE      0x302040UL
#define REG_VOFFSET     0x302044UL
#define REG_VSIZE       0x302048UL
#define REG_VSYNC0      0x30204CUL
#define REG_VSYNC1      0x302050UL
#define REG_DLSWAP      0x302054UL
#define REG_ROTATE      0x302058UL
#define REG_OUTBITS     0x30205CUL
#define REG_DITHER      0x302060UL
#define REG_SWIZZLE     0x302064UL
#define REG_CSPREAD     0x302068UL
#define REG_PCLK_POL    0x30206CUL
#define REG_PCLK        0x302070UL
#define REG_VOL_PB      0x302080UL
#define REG_VOL_SOUND   0x302084UL
#define REG_SOUND       0x302088UL
#define REG_PLAY        0x30208CUL
#define REG_GPIO_DIR    0x302090UL
#define REG_GPIO        0x302094UL
#define REG_GPIOX_DIR   0x302098UL
#define REG_GPIOX       0x30209CUL
#define REG_INT_FLAGS   0x3020A8UL
#define REG_INT_EN      0x3020ACUL
#define REG_INT_MASK    0x3020B0UL
#define REG_PWM_HZ      0x3020D0UL
#define REG_PWM_DUTY    0x3020D4UL
#define REG_CMD_READ    0x3020F8UL
#define REG_CMD_WRITE   0x3020FCUL
#define REG_SPI_WIDTH   0x302188UL

#define BT817_CHIP_ID   0x7Cu

/* ---- Comandos de host (3 bytes: cmd, parámetro, 0x00) ------------------ */
#define HCMD_ACTIVE     0x00u
#define HCMD_STANDBY    0x41u
#define HCMD_SLEEP      0x42u
#define HCMD_CLKEXT     0x44u /* reloj desde el cristal externo de 12 MHz */
#define HCMD_CLKINT     0x48u /* oscilador interno */
#define HCMD_CLKSEL     0x61u /* parámetro: multiplicador | rango PLL */
#define HCMD_RST_PULSE  0x68u

/* ---- Valores ------------------------------------------------------------ */
#define DLSWAP_FRAME    2u
#define SPI_WIDTH_1     0u
#define SPI_WIDTH_4     2u
#define GPIOX_DISP      (1u << 15) /* bit DISP del panel */

/* ---- Lista de visualización -------------------------------------------- */
#define DL_CLEAR_COLOR_RGB(r, g, b) ((2UL << 24) | (((r) & 0xFFUL) << 16) | (((g) & 0xFFUL) << 8) | ((b) & 0xFFUL))
#define DL_COLOR_RGB(r, g, b)       ((4UL << 24) | (((r) & 0xFFUL) << 16) | (((g) & 0xFFUL) << 8) | ((b) & 0xFFUL))
#define DL_CLEAR(c, s, t)           ((0x26UL << 24) | ((c) ? 4UL : 0) | ((s) ? 2UL : 0) | ((t) ? 1UL : 0))
#define DL_BEGIN(prim)              ((0x1FUL << 24) | ((prim) & 0xFUL))
#define DL_END()                    (0x21UL << 24)
#define DL_VERTEX_FORMAT(f)         ((0x27UL << 24) | ((f) & 7UL))
#define DL_VERTEX2F(x, y)           ((1UL << 30) | (((uint32_t)(x) & 0x7FFFUL) << 15) | ((uint32_t)(y) & 0x7FFFUL))
#define DL_DISPLAY()                0UL
#define PRIM_RECTS                  9u

/* ---- Sonido ------------------------------------------------------------- */
#define SOUND_SILENCE   0x00u
#define SOUND_SINE      0x02u
#define MIDI_A4         69u /* 440 Hz */

#endif /* BT817_REGS_H */
