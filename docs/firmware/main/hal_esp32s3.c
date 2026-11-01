/*
 * hal_esp32s3.c — Implementación de ocx_hal con ESP-IDF 5.x.
 *
 * BT817  : SPI2 (FSPI) por IO_MUX, half-duplex, SPI simple o QIO por transacción.
 * MCP23017: I2C_NUM_0 con el driver i2c_master (las pull-up de 4,7 k están en placa).
 * Ejes   : ADC1 en modo oneshot, atenuación 12 dB (0..~3,1 V).
 */
#include "hal_esp32s3.h"

#include <string.h>

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/spi_master.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "ocx_board.h"

static const char *TAG = "ocx_hal";

#define EVE_BUF_SIZE 1024 /* ≥ 3 + 512 (bloque de escritura de bt817.c) */
#define I2C_TIMEOUT_MS 20

typedef struct {
    spi_device_handle_t eve;
    ocx_bus_width_t width;
    uint32_t hz;
    uint8_t *dma;
    i2c_master_bus_handle_t i2c_bus;
    i2c_master_dev_handle_t mcp;
    adc_oneshot_unit_handle_t adc;
} esp_hal_t;

static esp_hal_t s_hal;

/* ---- BT817 -------------------------------------------------------------- */
static esp_err_t eve_add_device(esp_hal_t *h, uint32_t hz)
{
    if (h->eve) {
        spi_bus_remove_device(h->eve);
        h->eve = NULL;
    }
    spi_device_interface_config_t dev = {
        .mode = 0,
        .clock_speed_hz = (int)hz,
        .spics_io_num = OCX_PIN_EVE_CS,
        .queue_size = 1,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };
    h->hz = hz;
    return spi_bus_add_device(SPI2_HOST, &dev, &h->eve);
}

static uint32_t trans_flags(const esp_hal_t *h)
{
    return h->width == OCX_BUS_QUAD ? SPI_TRANS_MODE_QIO : 0;
}

static ocx_err_t eve_write(void *ctx, const uint8_t *data, size_t len)
{
    esp_hal_t *h = ctx;
    if (len == 0 || len > EVE_BUF_SIZE) return OCX_ERR_ARG;
    memcpy(h->dma, data, len);
    spi_transaction_t t = {
        .flags = trans_flags(h),
        .length = len * 8,
        .tx_buffer = h->dma,
    };
    return spi_device_polling_transmit(h->eve, &t) == ESP_OK ? OCX_OK : OCX_ERR_IO;
}

static ocx_err_t eve_read(void *ctx, const uint8_t *hdr, size_t hdr_len, uint8_t *rx, size_t rx_len)
{
    esp_hal_t *h = ctx;
    if (hdr_len > 8 || rx_len == 0 || rx_len > EVE_BUF_SIZE) return OCX_ERR_ARG;
    /* Fase de escritura (dirección + dummy) seguida de fase de lectura con CS
     * bajo durante toda la transacción. */
    uint8_t hdr_buf[8];
    memcpy(hdr_buf, hdr, hdr_len);
    spi_transaction_t t = {
        .flags = trans_flags(h),
        .length = hdr_len * 8,
        .tx_buffer = hdr_buf,
        .rxlength = rx_len * 8,
        .rx_buffer = h->dma,
    };
    if (spi_device_polling_transmit(h->eve, &t) != ESP_OK) return OCX_ERR_IO;
    memcpy(rx, h->dma, rx_len);
    return OCX_OK;
}

static ocx_err_t eve_set_bus(void *ctx, ocx_bus_width_t width, uint32_t hz)
{
    esp_hal_t *h = ctx;
    if (width != OCX_BUS_SINGLE && width != OCX_BUS_QUAD) return OCX_ERR_ARG;
    h->width = width;
    if (hz != h->hz && eve_add_device(h, hz) != ESP_OK) return OCX_ERR_IO;
    return OCX_OK;
}

/* ---- GPIO --------------------------------------------------------------- */
static void hal_gpio_write(void *ctx, int pin, int level) { gpio_set_level((gpio_num_t)pin, level ? 1 : 0); }
static int hal_gpio_read(void *ctx, int pin) { return gpio_get_level((gpio_num_t)pin); }

/* ---- I²C ---------------------------------------------------------------- */
static i2c_master_dev_handle_t i2c_dev(esp_hal_t *h, uint8_t addr)
{
    /* Solo hay un dispositivo en el bus. */
    return addr == OCX_MCP_I2C_ADDR ? h->mcp : NULL;
}

static ocx_err_t hal_i2c_write(void *ctx, uint8_t addr, const uint8_t *d, size_t n)
{
    i2c_master_dev_handle_t dev = i2c_dev(ctx, addr);
    if (!dev) return OCX_ERR_ARG;
    return i2c_master_transmit(dev, d, n, I2C_TIMEOUT_MS) == ESP_OK ? OCX_OK : OCX_ERR_IO;
}

static ocx_err_t hal_i2c_write_read(void *ctx, uint8_t addr, const uint8_t *w, size_t wn, uint8_t *r, size_t rn)
{
    i2c_master_dev_handle_t dev = i2c_dev(ctx, addr);
    if (!dev) return OCX_ERR_ARG;
    return i2c_master_transmit_receive(dev, w, wn, r, rn, I2C_TIMEOUT_MS) == ESP_OK ? OCX_OK : OCX_ERR_IO;
}

/* ---- ADC ---------------------------------------------------------------- */
static ocx_err_t hal_adc_read(void *ctx, int pin, int *raw)
{
    esp_hal_t *h = ctx;
    adc_unit_t unit;
    adc_channel_t ch;
    if (adc_oneshot_io_to_channel(pin, &unit, &ch) != ESP_OK || unit != ADC_UNIT_1) return OCX_ERR_ARG;
    return adc_oneshot_read(h->adc, ch, raw) == ESP_OK ? OCX_OK : OCX_ERR_IO;
}

/* ---- Tiempo ------------------------------------------------------------- */
static void hal_delay_ms(void *ctx, uint32_t ms)
{
    if (ms) vTaskDelay(pdMS_TO_TICKS(ms) ? pdMS_TO_TICKS(ms) : 1);
}

static uint64_t hal_now_us(void *ctx) { return (uint64_t)esp_timer_get_time(); }

/* ---- Inicialización ----------------------------------------------------- */
static esp_err_t init_gpio(void)
{
    /* Niveles seguros antes de habilitar las salidas. */
    gpio_set_level(OCX_PIN_EVE_PD_N, 0);
    gpio_set_level(OCX_PIN_AMP_SD, 0);
    gpio_set_level(OCX_PIN_MCP_RESET, 1);
    gpio_config_t out = {
        .pin_bit_mask = (1ULL << OCX_PIN_EVE_PD_N) | (1ULL << OCX_PIN_AMP_SD) | (1ULL << OCX_PIN_MCP_RESET),
        .mode = GPIO_MODE_OUTPUT,
    };
    ESP_RETURN_ON_ERROR(gpio_config(&out), TAG, "gpio out");
    gpio_config_t in = {
        .pin_bit_mask = (1ULL << OCX_PIN_EVE_INT_N) | (1ULL << OCX_PIN_MCP_INT) | (1ULL << OCX_PIN_JOY_L_BTN) |
                        (1ULL << OCX_PIN_JOY_R_BTN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    return gpio_config(&in);
}

static esp_err_t init_spi(esp_hal_t *h)
{
    spi_bus_config_t bus = {
        .data0_io_num = OCX_PIN_EVE_IO0,
        .data1_io_num = OCX_PIN_EVE_IO1,
        .data2_io_num = OCX_PIN_EVE_IO2,
        .data3_io_num = OCX_PIN_EVE_IO3,
        .sclk_io_num = OCX_PIN_EVE_SCLK,
        .data4_io_num = -1,
        .data5_io_num = -1,
        .data6_io_num = -1,
        .data7_io_num = -1,
        .max_transfer_sz = EVE_BUF_SIZE + 8,
        .flags = SPICOMMON_BUSFLAG_MASTER | SPICOMMON_BUSFLAG_QUAD,
    };
    ESP_RETURN_ON_ERROR(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO), TAG, "spi bus");
    h->dma = heap_caps_malloc(EVE_BUF_SIZE, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    if (!h->dma) return ESP_ERR_NO_MEM;
    h->width = OCX_BUS_SINGLE;
    return eve_add_device(h, 1000000);
}

static esp_err_t init_i2c(esp_hal_t *h)
{
    i2c_master_bus_config_t bus = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = OCX_PIN_I2C_SDA,
        .scl_io_num = OCX_PIN_I2C_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false, /* R6/R7 de 4,7 k en placa */
    };
    ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bus, &h->i2c_bus), TAG, "i2c bus");
    i2c_device_config_t dev = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = OCX_MCP_I2C_ADDR,
        .scl_speed_hz = OCX_I2C_HZ,
    };
    return i2c_master_bus_add_device(h->i2c_bus, &dev, &h->mcp);
}

static esp_err_t init_adc(esp_hal_t *h)
{
    adc_oneshot_unit_init_cfg_t unit = {.unit_id = ADC_UNIT_1};
    ESP_RETURN_ON_ERROR(adc_oneshot_new_unit(&unit, &h->adc), TAG, "adc unit");
    const int pins[] = {OCX_PIN_JOY_L_X, OCX_PIN_JOY_L_Y, OCX_PIN_JOY_R_X, OCX_PIN_JOY_R_Y};
    adc_oneshot_chan_cfg_t cc = {.atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_12};
    for (size_t i = 0; i < sizeof pins / sizeof pins[0]; i++) {
        adc_unit_t u;
        adc_channel_t ch;
        ESP_RETURN_ON_ERROR(adc_oneshot_io_to_channel(pins[i], &u, &ch), TAG, "adc io %d", pins[i]);
        ESP_RETURN_ON_ERROR(adc_oneshot_config_channel(h->adc, ch, &cc), TAG, "adc ch %d", ch);
    }
    return ESP_OK;
}

esp_err_t ocx_hal_esp32s3_init(ocx_hal_t *out)
{
    esp_hal_t *h = &s_hal;
    ESP_RETURN_ON_ERROR(init_gpio(), TAG, "gpio");
    ESP_RETURN_ON_ERROR(init_spi(h), TAG, "spi");
    ESP_RETURN_ON_ERROR(init_i2c(h), TAG, "i2c");
    ESP_RETURN_ON_ERROR(init_adc(h), TAG, "adc");
    *out = (ocx_hal_t){
        .ctx = h,
        .eve_write = eve_write,
        .eve_read = eve_read,
        .eve_set_bus = eve_set_bus,
        .gpio_write = hal_gpio_write,
        .gpio_read = hal_gpio_read,
        .i2c_write = hal_i2c_write,
        .i2c_write_read = hal_i2c_write_read,
        .adc_read = hal_adc_read,
        .delay_ms = hal_delay_ms,
        .now_us = hal_now_us,
    };
    return ESP_OK;
}
