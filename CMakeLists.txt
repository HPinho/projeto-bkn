cmake_minimum_required(VERSION 3.20)

# O CMake delega a compilação da linguagem Cq ao VortexC; fontes .cq nunca são
# entregues diretamente ao compilador C. O alvo cq_build produz o EFI modular
# usado pela rota oficial de empacotamento.
project(BakenEcosystem LANGUAGES NONE)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
enable_testing()

add_custom_target(cq_check
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/vortexc/vortexc.py
            check ${CMAKE_SOURCE_DIR}/kernel/src/main.cq
            --manifest ${CMAKE_BINARY_DIR}/cq-main.manifest.json
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Validando o grafo modular Cq"
)

add_custom_target(cq_build
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/vortexc/vortexc.py
            build ${CMAKE_SOURCE_DIR}/kernel/src/main.cq
            -o ${CMAKE_SOURCE_DIR}/build/cmake-cq/BOOTX64.EFI
            --manifest ${CMAKE_BINARY_DIR}/cq-main.manifest.json
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Gerando e vinculando o EFI modular Cq"
)

add_test(
    NAME vortexc_resolver
    COMMAND ${Python3_EXECUTABLE} -m unittest tests/test_vortexc_resolver.py
)
set_tests_properties(vortexc_resolver PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

add_test(
    NAME legacy_safety
    COMMAND ${Python3_EXECUTABLE} -m unittest tests/test_legacy_safety.py
)
set_tests_properties(legacy_safety PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

add_test(
    NAME packaging_contract
    COMMAND ${Python3_EXECUTABLE} -m unittest tests/test_packaging_contract.py
)
set_tests_properties(packaging_contract PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

add_test(
    NAME storage_installer
    COMMAND ${Python3_EXECUTABLE} -m unittest tests/test_storage_installer.py
)
set_tests_properties(storage_installer PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

add_test(
    NAME installed_disk
    COMMAND ${Python3_EXECUTABLE} -m unittest tests/test_installed_disk.py
)
set_tests_properties(installed_disk PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
