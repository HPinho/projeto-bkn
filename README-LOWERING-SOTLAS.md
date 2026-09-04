# Sotlas Compile — lowering modular

O Baken OS usa `tools/sotlas_compile/compiler.py` como compilador modular da linguagem Sotlas. O compilador pertence ao host: ele resolve o grafo de módulos, valida interfaces e reduz cada unidade Sotlas para um objeto independente antes da linkedição do `BOOTX64.EFI`.

A regra arquitetural é simples:

```text
Python/Sotlas Compile = ferramenta de compilação
Sotlas                = código do sistema
UEFI                   = bootstrap
Baken kernel           = dono do hardware após o cutover bare-metal
```

A entrada canônica continua sendo:

```text
kernel/src/main.sotlas
```

O build oficial valida o grafo, gera uma unidade por módulo e compila `boot/uefi_bootloader.sotlas` separadamente como bootstrap UEFI.

## Estado do lowering

O frontend modular é responsável por:

- descoberta de módulos;
- imports transitivos;
- detecção de ciclos e módulos duplicados;
- parser/typechecker Sotlas;
- geração de interfaces públicas;
- lowering para unidades C freestanding;
- compilação de um objeto por módulo;
- linkedição PE/COFF UEFI.

Nenhum elemento visual específico deve ser sintetizado pelo compilador. Wallpaper, dock, janelas, animações, compositor, installer e OOBE pertencem aos módulos `.sotlas`.

A suíte `tests/test_compiler_ui_boundary.py` protege essa fronteira.

## Marco bare-metal: BakenBootInfo v2

A branch de fundação bare-metal introduz um envelope `BakenBootInfo v2` sem quebrar os offsets legados ainda consumidos pelo runtime atual.

O bootloader agora coleta de forma real:

- endereço/tamanho/formato do framebuffer GOP;
- snapshot do UEFI Memory Map;
- `descriptor_size` e `descriptor_version` do Memory Map;
- ACPI RSDP 2.0 com fallback 1.0;
- versão, tamanho e flags do contrato de handoff.

O snapshot é obtido usando `GetMemoryMap()` com alocação dimensionada pelo firmware. Esse mapa ainda não é o map key definitivo do `ExitBootServices()`, porque o runtime atual continua temporariamente usando Boot Services para input, temporização e Block I/O.

Assim, o estado atual é:

```text
UEFI
 -> GOP + ACPI + Memory Map real
 -> BakenBootInfo v2
 -> kernel Sotlas
 -> ponte UEFI transitória para input/storage/timing
```

O estado alvo é:

```text
UEFI
 -> GOP + ACPI + Memory Map final
 -> ExitBootServices()
 -> kernel Sotlas
 -> PMM/VMM/PAT
 -> drivers Baken
 -> compositor/desktop
```

O cutover final só deve acontecer quando as dependências de Pointer Protocol, Block I/O e timers UEFI forem substituídas por drivers/serviços nativos.

## Build

Validação:

```powershell
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
```

Build:

```powershell
& tools\build_uefi_desktop.ps1
```

A geração do EFI continua falhando de forma fechada quando o compilador, um módulo ou a linkedição retornam erro.
