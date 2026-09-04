# Baken OS

Baken OS é um projeto de sistema operacional x86-64 em Sotlas.

A arquitetura separa:

- **Python/Sotlas Compile**: toolchain de host;
- **UEFI/BOOTX64.EFI**: bootstrap;
- **Sotlas compilado**: kernel, drivers, gráficos, UI e serviços;
- **Baken kernel**: responsável pelo hardware após o cutover bare-metal.

Veja [`docs/architecture.md`](docs/architecture.md) para o plano canônico.

## Estado atual

`BakenBootInfo v2` já transporta framebuffer, snapshot real do UEFI Memory Map, metadados dos descriptors e ACPI RSDP. O ponto de entrada Sotlas valida o contrato antes de iniciar a sessão gráfica.

O runtime ainda mantém pontes UEFI temporárias para input/storage/timing. A próxima fundação é GDT/IDT/TSS/exceções, seguida de PMM/VMM/PAT; `ExitBootServices()` será antecipado quando as pontes de firmware puderem ser removidas.

## Verificação

```powershell
python -m unittest discover -s tests -p "test_*.py"
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
& tools\build_uefi_desktop.ps1
```
