# Sotlas Compile — lowering modular

O Baken OS usa `tools/sotlas_compile/compiler.py` como compilador modular da linguagem Sotlas. O compilador pertence ao host; o sistema operacional pertence aos módulos Sotlas.

```text
Python/Sotlas Compile = ferramenta de compilação
Sotlas                = código do sistema
UEFI                   = bootstrap
Baken kernel           = dono do hardware após o cutover bare-metal
```

A entrada canônica é `kernel/src/main.sotlas`.

## Fronteira do compilador

O frontend modular cuida de descoberta de módulos, imports, análise, lowering, geração de interfaces, compilação de objetos e linkedição PE/COFF. UI específica não pode ser sintetizada em Python: wallpaper, dock, janelas, animações, compositor, installer e OOBE ficam em `.sotlas`.

## Marco bare-metal atual

`BakenBootInfo v2` preserva temporariamente o ABI usado pelo runtime e acrescenta os dados de plataforma que o kernel precisará após o corte UEFI.

O bootloader já coleta:

- framebuffer GOP e pixel format;
- snapshot real do UEFI Memory Map por `GetMemoryMap()`;
- tamanho e versão dos memory descriptors;
- ACPI RSDP 2.0 com fallback 1.0;
- versão, tamanho e flags do handoff.

O kernel valida o v2 antes de iniciar a sessão gráfica.

O snapshot ainda não é o map final de `ExitBootServices()`, porque input/storage/timing continuam usando Boot Services. O corte final só ocorrerá depois da substituição dessas pontes por serviços nativos.

```text
ATUAL
UEFI -> GOP/ACPI/Memory Map -> BootInfo v2 -> kernel -> ponte UEFI transitória

ALVO
UEFI -> GOP/ACPI/Memory Map final -> ExitBootServices -> kernel -> drivers Baken
```

## Build

```powershell
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
& tools\build_uefi_desktop.ps1
```
