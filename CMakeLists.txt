cmake_minimum_required(VERSION 3.20)
project(BakenEcosystem C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Includes globais
include_directories(
    kernel/include
    kernel/qhal
    bknc/include
)

# Biblioteca Q-HAL (Simulador Vetorial Quântico)
add_library(baken_qhal STATIC
    kernel/qhal/quantum_simulator.c
)

# Executável de Testes Matemáticos Quânticos
add_executable(test_qhal
    tests/test_quantum_simulator.c
)
target_link_libraries(test_qhal PRIVATE baken_qhal)

# Flags de Otimização e Segurança
if(MSVC)
    target_compile_options(baken_qhal PRIVATE /W4 /O2)
    target_compile_options(test_qhal PRIVATE /W4 /O2)
else()
    target_compile_options(baken_qhal PRIVATE -Wall -Wextra -O3 -mavx2)
    target_compile_options(test_qhal PRIVATE -Wall -Wextra -O3 -mavx2 -lm)
    target_link_libraries(test_qhal PRIVATE m)
endif()
