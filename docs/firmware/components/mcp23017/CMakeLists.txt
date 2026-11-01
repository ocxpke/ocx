# Componente portable: se compila con ESP-IDF (ESP_PLATFORM) o con CMake normal (host/).
if(ESP_PLATFORM)
    idf_component_register(SRCS "mcp23017.c"
                           INCLUDE_DIRS "include"
                           REQUIRES ocx_hal)
else()
    add_library(mcp23017 STATIC mcp23017.c)
    target_include_directories(mcp23017 PUBLIC include)
    target_link_libraries(mcp23017 PUBLIC ocx_hal)
endif()
