# Componente portable: se compila con ESP-IDF (ESP_PLATFORM) o con CMake normal (host/).
if(ESP_PLATFORM)
    idf_component_register(SRCS "ocx_input.c"
                           INCLUDE_DIRS "include"
                           REQUIRES ocx_hal mcp23017)
else()
    add_library(ocx_input STATIC ocx_input.c)
    target_include_directories(ocx_input PUBLIC include)
    target_link_libraries(ocx_input PUBLIC ocx_hal mcp23017)
endif()
