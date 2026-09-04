# Baken OS

Baken OS é um projeto de sistema operacional x86-64 em Sotlas.

A arquitetura em desenvolvimento separa explicitamente:

- **Python/Sotlas Compile**: toolchain de host;
- **UEFI/BOOTX64.EFI**: bootstrap;
- **Sotlas compilado**: kernel, drivers, gráficos, UI e serviços;
- **Baken kernel**: responsável pelo hardware após o cutover bare-metal.

O documento canônico é [`docs/architecture.md`](docs/architecture.md).

## Estado atual da migração bare-metal

`BakenBootInfo v2` já transporta framebuffer, snapshot real do UEFI Memory Map, metadados dos descriptors e ACPI RSDP. O runtime ainda mantém pontes UEFI temporárias para input/storage/timing; `ExitBootServices()` será movido para antes da entrada normal do kernel quando esses serviços forem substituídos por drivers nativos.

## Verificação

```powershell
python -m unittest discover -s tests -p "test_*.py"
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
& tools\build_uefi_desktop.ps1
```
