# Componente portable: se compila con ESP-IDF (ESP_PLATFORM) o con CMake normal (host/).
if(ESP_PLATFORM)
    idf_component_register(SRCS "ocx_hal.c"
                           INCLUDE_DIRS "include")
else()
    add_library(ocx_hal STATIC ocx_hal.c)
    target_include_directories(ocx_hal PUBLIC include)
endif()
