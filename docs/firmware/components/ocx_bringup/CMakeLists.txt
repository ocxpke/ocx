# Componente portable: se compila con ESP-IDF (ESP_PLATFORM) o con CMake normal (host/).
if(ESP_PLATFORM)
    idf_component_register(SRCS "ocx_bringup.c"
                           INCLUDE_DIRS "include"
                           REQUIRES ocx_hal bt817 mcp23017 ocx_input)
else()
    add_library(ocx_bringup STATIC ocx_bringup.c)
    target_include_directories(ocx_bringup PUBLIC include)
    target_link_libraries(ocx_bringup PUBLIC ocx_hal bt817 mcp23017 ocx_input)
endif()
