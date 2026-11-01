#ifndef HAL_ESP32S3_H
#define HAL_ESP32S3_H

#include "esp_err.h"
#include "ocx_hal.h"

/* Configura GPIO, SPI2 (BT817), I²C (MCP23017) y ADC1, y rellena `out`. */
esp_err_t ocx_hal_esp32s3_init(ocx_hal_t *out);

#endif
