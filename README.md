# Baken OS

Baken OS é um sistema operacional x86-64 em Sotlas com arquitetura bare-metal própria.

A arquitetura separa:

- **Python/Sotlas Compile**: toolchain de host;
- **UEFI/BOOTX64.EFI**: bootstrap somente;
- **Sotlas compilado**: kernel, drivers, gráficos, UI e serviços;
- **Baken kernel**: responsável pelo hardware depois de `ExitBootServices()`.

Veja [`docs/architecture.md`](docs/architecture.md) para o contrato arquitetural canônico.

## Estado atual da fundação

A fundação bare-metal x86-64 já possui:

- `ExitBootServices()` real com retry por `MapKey`;
- troca para CR3/page tables próprias;
- stack de transição com guard page;
- GDT, TSS, IDT e exceções próprias;
- PMM allocator e VMM ativos pós-cutover;
- W^X da imagem e direct map controlado;
- ACPI/MADT, LAPIC, IOAPIC, IRQs e timer nativo;
- PCI e DMA nativos;
- xHCI + USB HID nativos;
- AHCI, NVMe e Block Device API;
- GPT/MBR/FAT32;
- PAT com framebuffer Write-Combining;
- `BakenBootInfo v2` sem ponteiros para serviços UEFI;
- auditoria estática que proíbe reentrada em firmware no grafo pós-cutover;
- gate QEMU `BAKEN:BARE_METAL_READY` para certificar a sequência completa.

O kernel não usa Boot Services, Runtime Services, Pointer Protocol, Block I/O UEFI ou timers UEFI depois do cutover.

## Boot normal x certificação

O núcleo mínimo do sistema é fail-closed: CPU tables, PMM, VMM, ACPI/APIC, IRQ/timer e PAT/WC precisam estar válidos para o runtime continuar.

Controladores e dispositivos opcionais são tentados sem transformar a ausência de um backend específico em loop infinito. Já o CI continua exigindo todos os probes de fundação — incluindo USB HID, AHCI/NVMe, GPT/FAT32 e os marcadores de diagnóstico — antes de emitir `BAKEN:BARE_METAL_READY`.

Assim, o mesmo kernel pode:

- inicializar normalmente em hardware que não possua exatamente a fixture do QEMU;
- continuar oferecendo uma certificação rigorosa e reproduzível das fundações no CI.

## Sotlas e dependências

O kernel/runtime não depende de runtime de terceiros. Python, MinGW, QEMU, OVMF e GitHub Actions pertencem somente ao ambiente de desenvolvimento, build e teste.

O compilador Sotlas ainda é uma ferramenta de host. Self-hosting do compilador é uma etapa futura e não é requisito para o kernel ser bare-metal.

## Verificação

```powershell
python -m unittest discover -s tests -p "test_*.py"
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
& tools\build_uefi_desktop.ps1
```

A CI também constrói a ISO e executa o boot headless em QEMU/OVMF, exigindo o marcador terminal `BAKEN:BARE_METAL_READY`.
