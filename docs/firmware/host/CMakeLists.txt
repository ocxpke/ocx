# Versión para PC: componentes portables + periféricos simulados + pruebas.
#   cmake -S docs/firmware/host -B build-host && cmake --build build-host && ctest --test-dir build-host
cmake_minimum_required(VERSION 3.16)
project(ocx_host C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug)
endif()
add_compile_options(-Wall -Wextra -Werror -Wno-unused-parameter)

option(OCX_SANITIZE "AddressSanitizer + UBSan" ON)
if(OCX_SANITIZE)
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
endif()

set(COMP ${CMAKE_CURRENT_SOURCE_DIR}/../components)
add_subdirectory(${COMP}/ocx_hal ocx_hal)
add_subdirectory(${COMP}/bt817 bt817)
add_subdirectory(${COMP}/mcp23017 mcp23017)
add_subdirectory(${COMP}/ocx_input ocx_input)
add_subdirectory(${COMP}/ocx_bringup ocx_bringup)

add_library(ocx_sim STATIC sim/sim.c)
target_include_directories(ocx_sim PUBLIC sim)
target_link_libraries(ocx_sim PUBLIC ocx_hal bt817 mcp23017 ocx_input m)

# Ejecutable de demostración: pruebas de puesta en marcha sobre la placa simulada.
add_executable(ocx_sim_bringup main_sim.c)
target_link_libraries(ocx_sim_bringup PRIVATE ocx_sim ocx_bringup)

enable_testing()
foreach(t test_bt817 test_mcp23017 test_input test_bringup)
    add_executable(${t} tests/${t}.c)
    target_include_directories(${t} PRIVATE tests)
    target_link_libraries(${t} PRIVATE ocx_sim ocx_bringup)
    add_test(NAME ${t} COMMAND ${t})
endforeach()
add_test(NAME sim_bringup_all_pass COMMAND ocx_sim_bringup)
add_test(NAME sim_bringup_detects_no_crystal COMMAND ocx_sim_bringup --fault=no_crystal)
set_tests_properties(sim_bringup_detects_no_crystal PROPERTIES WILL_FAIL TRUE)
