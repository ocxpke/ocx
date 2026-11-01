idf_component_register(SRCS "app_main.c" "hal_esp32s3.c"
                       INCLUDE_DIRS "."
                       REQUIRES ocx_hal bt817 mcp23017 ocx_input ocx_bringup
                                esp_driver_spi esp_driver_i2c esp_driver_gpio esp_adc esp_timer
                                esp_driver_usb_serial_jtag vfs)
