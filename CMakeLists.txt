cmake_minimum_required(VERSION 3.20)

# O CMake delega a compilação da linguagem Sotlas ao toolchain 'sotlas compile'.
# Fontes .st nunca são entregues diretamente ao compilador C.
# O alvo sotlas_build produz o EFI modular usado pela rota oficial de empacotamento.
project(BakenEcosystem LANGUAGES NONE)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
enable_testing()

add_custom_target(sotlas_check
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/sotlas_compile/compiler.py
            check ${CMAKE_SOURCE_DIR}/kernel/src/main.st
            --manifest ${CMAKE_BINARY_DIR}/sotlas-main.manifest.json
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Validando o grafo modular Sotlas"
)

add_custom_target(sotlas_build
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tools/sotlas_compile/compiler.py
            build ${CMAKE_SOURCE_DIR}/kernel/src/main.st
            -o ${CMAKE_SOURCE_DIR}/build/cmake-sotlas/BOOTX64.EFI
            --manifest ${CMAKE_BINARY_DIR}/sotlas-main.manifest.json
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Gerando e vinculando o EFI modular Sotlas"
)

add_test(
    NAME sotlas_resolver
    COMMAND ${Python3_EXECUTABLE} -m unittest tests/test_sotlas_resolver.py
)
set_tests_properties(sotlas_resolver PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

add_test(
    NAME sotlas_frontend_compat
    COMMAND ${Python3_EXECUTABLE} -m unittest tests/test_sotlas_frontend_compat.py
)
set_tests_properties(sotlas_frontend_compat PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

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

add_test(
    NAME sotlas_compiler
    COMMAND ${Python3_EXECUTABLE} -m unittest discover -s tests -p "test_sotlas_*.py"
)
set_tests_properties(sotlas_compiler PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
