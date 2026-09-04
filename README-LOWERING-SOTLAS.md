# Sotlas Compile — lowering modular

O Baken OS usa `tools/sotlas_compile/compiler.py` como compilador modular da linguagem Sotlas. O compilador pertence ao host: ele resolve o grafo de módulos, valida interfaces e reduz cada unidade Sotlas para um objeto independente antes da linkedição do `BOOTX64.EFI`.

A regra arquitetural é:

```text
Python/Sotlas Compile = ferramenta de compilação
Sotlas                = código do sistema
UEFI                   = bootstrap
Baken kernel           = dono do hardware após o cutover bare-metal
```

A entrada canônica continua sendo `kernel/src/main.sotlas`.

## Responsabilidades do compilador

O frontend modular é responsável por descoberta de módulos, imports transitivos, detecção de ciclos e duplicatas, parser/typechecker, geração de interfaces, lowering para unidades C freestanding, compilação de um objeto por módulo e linkedição PE/COFF UEFI.

Nenhum elemento visual específico deve ser sintetizado pelo compilador. Wallpaper, dock, janelas, animações, compositor, installer e OOBE pertencem aos módulos `.sotlas`. `tests/test_compiler_ui_boundary.py` protege essa fronteira.

## Marco bare-metal atual

A branch de fundação bare-metal introduz `BakenBootInfo v2` como envelope de transição, preservando os offsets legados ainda usados pelo runtime enquanto adiciona metadados reais para o futuro handoff.

O bootloader já coleta:

- framebuffer GOP e formato;
- snapshot real do UEFI Memory Map via `GetMemoryMap()`;
- `memory_descriptor_size` e `memory_descriptor_version`;
- ACPI RSDP 2.0 com fallback 1.0;
- versão, tamanho e flags do contrato.

O snapshot de Memory Map ainda não é o map final do `ExitBootServices()`, pois input/storage/timing continuam usando pontes UEFI. O cutover final exige recapturar o mapa imediatamente antes de `ExitBootServices()` e só então entrar no kernel sem Boot Services.

Estado atual:

```text
UEFI
 -> GOP + ACPI + Memory Map real
 -> BakenBootInfo v2
 -> kernel Sotlas
 -> ponte UEFI transitória para input/storage/timing
```

Estado alvo:

```text
UEFI
 -> GOP + ACPI + Memory Map final
 -> ExitBootServices()
 -> kernel Sotlas
 -> PMM/VMM/PAT
 -> drivers Baken
 -> compositor/desktop
```

## Build

Validação:

```powershell
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
```

Build:

```powershell
& tools\build_uefi_desktop.ps1
```

A geração do EFI deve continuar falhando de forma fechada quando o compilador, um módulo ou a linkedição retornarem erro.
