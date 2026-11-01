# Componente portable: se compila con ESP-IDF (ESP_PLATFORM) o con CMake normal (host/).
if(ESP_PLATFORM)
    idf_component_register(SRCS "bt817.c"
                           INCLUDE_DIRS "include"
                           REQUIRES ocx_hal)
else()
    add_library(bt817 STATIC bt817.c)
    target_include_directories(bt817 PUBLIC include)
    target_link_libraries(bt817 PUBLIC ocx_hal)
endif()
