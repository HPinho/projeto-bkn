# Arquitetura canônica do Baken OS

## Objetivo

O Baken OS deve ser um sistema operacional x86-64 bare-metal próprio. Python é ferramenta de compilação/build/teste; UEFI é apenas bootstrap; Sotlas é compilado para código nativo; depois do handoff o kernel Baken assume memória, interrupções, barramentos, entrada, armazenamento e gráficos.

```text
Sotlas source
    -> Sotlas compiler
    -> x86-64 machine code
    -> Baken kernel / drivers / services
    -> hardware
```

A regra central é:

> O compilador não desenha o sistema operacional. Ele apenas permite que o sistema operacional exista.

## Fronteiras obrigatórias

### Python

`tools/sotlas_compile/` pertence ao host. Pode implementar lexer, parser, AST, análise semântica, IR, lowering, ABI, backend x86-64, linker orchestration e intrínsecos de baixo nível.

Não pode implementar wallpaper, dock, cursor, janelas, installer, OOBE, shimmer, compositor, drivers ou lógica específica de dispositivos.

### UEFI

`BOOTX64.EFI` deve ter somente responsabilidades de bootstrap:

1. localizar/carregar o kernel;
2. obter GOP e registrar endereço físico, tamanho, pitch e formato do framebuffer;
3. obter `GetMemoryMap`;
4. localizar ACPI RSDP;
5. opcionalmente coletar SMBIOS e outros descritores passivos;
6. construir `BakenBootInfo` somente com dados estáveis após o handoff;
7. executar `ExitBootServices()` com retry correto se o map key mudar;
8. transferir controle para `baken_kernel_main`.

Depois de `ExitBootServices()`, o kernel não deve depender de `EFI_SIMPLE_POINTER_PROTOCOL`, `EFI_ABSOLUTE_POINTER_PROTOCOL`, `EFI_BLOCK_IO_PROTOCOL`, timers UEFI, eventos UEFI ou outras interfaces de Boot Services.

O framebuffer descoberto pelo GOP pode continuar sendo usado porque seu endereço físico é conhecido, mas seu mapeamento e política de cache passam a ser responsabilidade do VMM/PAT do Baken.

### Kernel

O kernel é responsável por:

- GDT, IDT, TSS e exceções;
- PMM, VMM, heap e DMA;
- PAT e atributos de cache;
- ACPI, APIC, IOAPIC e timers;
- PCI/PCIe;
- scheduler;
- input HAL e drivers;
- block device API e storage;
- Graphics API, compositor e backends.

### UI

Installer, OOBE, desktop, dock, janelas, animações e widgets devem existir em Sotlas e consumir APIs do Baken. Eles não acessam GOP, MSR, PCI ou MMIO diretamente.

## Estado transitório atual

A árvore atual ainda possui dívida de migração no bootloader. Em particular, o bootloader atual localiza Pointer Protocol e Block I/O e os entrega pelo `BakenBootInfo`; também chama o kernel sem uma fronteira final baseada em `GetMemoryMap` + `ExitBootServices`.

Essas pontes são consideradas **legado transitório**, não arquitetura final. Nenhuma nova funcionalidade pode depender delas.

A remoção deve ocorrer em ordem segura:

1. implementar entrada nativa suficiente para substituir pointer UEFI;
2. implementar block device nativo suficiente para substituir Block I/O UEFI;
3. completar PMM/VMM e preservar o mapa de memória;
4. mudar `BakenBootInfo` para conter apenas dados estáveis pós-ExitBootServices;
5. executar `ExitBootServices()` antes de `baken_kernel_main`;
6. remover os campos e caminhos de runtime UEFI restantes.

Até esse corte, a branch principal deve continuar bootável; a migração deve ser feita por commits pequenos e testáveis.

## BootInfo alvo

O contrato alvo é conceitualmente:

```text
BakenBootInfo
├── version
├── framebuffer
│   ├── physical_base
│   ├── byte_size
│   ├── width
│   ├── height
│   ├── pixels_per_scanline
│   └── pixel_format
├── memory_map
│   ├── physical/virtual address
│   ├── size
│   ├── descriptor_size
│   └── descriptor_version
├── acpi_rsdp
├── kernel image metadata
└── initrd/system image metadata (quando aplicável)
```

Não fazem parte do BootInfo final:

```text
EFI_SYSTEM_TABLE*
EFI_SIMPLE_POINTER_PROTOCOL*
EFI_ABSOLUTE_POINTER_PROTOCOL*
EFI_BLOCK_IO_PROTOCOL*
EFI_BOOT_SERVICES*
```

## Fundação x86-64

A ordem de inicialização do kernel deve ser:

```text
kernel_entry
    -> early serial/debug
    -> GDT/TSS
    -> IDT/exceptions
    -> PMM
    -> VMM/page tables próprias
    -> PAT/cache policy
    -> ACPI
    -> LAPIC/IOAPIC
    -> timers
    -> scheduler
    -> PCI/PCIe
    -> DMA
    -> drivers
    -> compositor
    -> desktop shell
```

UEFI já entrega a CPU x86-64 em long mode em uma inicialização UEFI normal; o trabalho do Baken é assumir o controle desse ambiente e estabelecer suas próprias tabelas, descritores e políticas.

## Memória e PAT

O framebuffer deve ser mapeado como Write-Combining quando suportado. Não basta escrever `IA32_PAT`: a entrada PAT correta deve ser selecionada pelos bits PAT/PCD/PWT das page tables que cobrem a região.

Política inicial:

```text
normal RAM / backbuffer = WB
framebuffer GOP         = WC
MMIO                     = UC, salvo exigência explícita do dispositivo
```

O código deve ler o PAT existente, verificar suporte via CPUID e alterar o mínimo necessário, com invalidação/coerência apropriada dos mappings.

## ACPI e interrupções

ACPI deve fornecer pelo menos RSDP/XSDT, MADT, MCFG e FADT, expandindo depois para DSDT/SSDT e AML.

O IOAPIC não deve assumir mapeamento fixo de IRQ legado. O fluxo é:

```text
MADT
 -> Interrupt Source Override
 -> GSI
 -> IOAPIC redirection entry
 -> vetor IDT
```

## Input

Arquitetura canônica:

```text
i8042/PS2 ----\
USB HID -------+-> Input HAL -> Event Normalizer -> Ring Buffer -> Window Manager
I2C-HID -------/
```

Eventos normalizados incluem `PointerMove`, `PointerDown`, `PointerUp`, `Scroll`, `KeyDown`, `KeyUp`, `TouchBegin`, `TouchMove` e `TouchEnd`.

PS/2 é um backend, não garantia universal de touchpad. Notebooks modernos podem exigir ACPI + controlador I2C + HID-over-I2C.

## Graphics Architecture

```text
Desktop / Apps
    -> Baken Graphics API
    -> Compositor / Rasterizer
    -> Graphics Device HAL
       -> software framebuffer backend
       -> VirtIO-GPU
       -> driver Intel nativo posterior
```

O backend universal inicial usa:

```text
UI
 -> rasterização em backbuffer WB
 -> DamageRegion (múltiplos retângulos)
 -> cópia otimizada das regiões alteradas
 -> framebuffer WC
```

Não usar um único bounding rectangle global quando regiões distantes mudarem. O compositor deve manter uma coleção de damage rectangles e fazer merge somente quando isso reduzir custo.

`movntdq`/streaming stores não são regra universal; `memops` deve escolher estratégia conforme tamanho, alinhamento e capacidades CPUID (REP MOVSB/ERMS/FSRM/SIMD quando apropriado).

## GPU

PCI discovery e BAR mapping apenas descobrem a GPU. Não constituem aceleração gráfica por si sós.

Aceleração real exige driver específico capaz de lidar, conforme a família, com MMIO, memória da GPU, page tables/contextos, filas/rings, command buffers, sincronização/fences, interrupções e scanout/present.

A ordem preferencial é:

1. software framebuffer backend;
2. VirtIO-GPU em VM;
3. uma família Intel específica;
4. outros fabricantes somente depois da HAL estabilizar.

## Storage

A pilha é:

```text
NVMe/AHCI
 -> Block Device API
 -> GPT
 -> filesystem
 -> installer
```

O installer não escreve registradores NVMe/AHCI nem LBAs diretamente a partir da UI.

GPT deve calcular dinamicamente o tamanho da partition-entry array a partir do logical block size; não assumir permanentemente LBAs 2-33. Protective MBR, primary/backup headers, arrays e CRC32 devem ser gerados e validados.

FAT32 deve calcular BPB/FAT/root/FSInfo/backup boot sector a partir do volume real.

## Scheduler e DMA

xHCI, NVMe, VirtIO e GPUs dependem de DMA. Deve existir uma API central de alocação DMA que exponha endereço virtual, endereço físico, tamanho e alinhamento.

O kernel não deve manter input, storage, compositor e USB em um único polling loop. A evolução mínima inclui kernel threads, ready queue, sleep queue, timer e context switch.

## Ordem de implementação

```text
0. Sotlas compiler/backend e intrínsecos confiáveis
1. BootInfo v2 + GetMemoryMap + handoff preparado
2. GDT/IDT/TSS/exceptions
3. PMM/VMM/heap/PAT
4. ACPI/APIC/IOAPIC/timers
5. scheduler + PCI/PCIe + DMA
6. framebuffer/backbuffer/DamageRegion/compositor
7. i8042 + Input HAL
8. xHCI + USB HID
9. AHCI/NVMe + Block API
10. GPT/FAT32 + installer real
11. AML + I2C-HID
12. VirtIO-GPU
13. Intel GPU nativa
14. remoção final das pontes UEFI e `ExitBootServices()` obrigatório antes do kernel normal
```

As fases 1-13 podem possuir marcos intermediários, mas nenhum novo módulo pode aumentar a dependência do kernel em Boot Services.

## Testes arquiteturais

A suíte deve continuar garantindo que `compiler.py`/`bootstrap.py` não contenham UI específica e que a antiga ponte monolítica não retorne.

Devem ser adicionados gradualmente testes para:

- layout/versionamento de `BakenBootInfo`;
- ausência de ponteiros UEFI no BootInfo v2;
- serialização e interpretação do Memory Map;
- PAT/PTE encoding;
- PMM/VMM;
- ACPI checksums e MADT/MCFG;
- DamageRegion;
- ring buffers;
- PCI enumeration;
- GPT/CRC32;
- FAT32;
- block drivers em QEMU;
- boot após `ExitBootServices()`.

## Critério de conclusão da migração bare-metal

A migração só pode ser considerada concluída quando o caminho normal de boot for:

```text
Firmware UEFI
 -> BOOTX64.EFI
 -> GOP + Memory Map + ACPI + kernel load
 -> ExitBootServices()
 -> Baken kernel
 -> Baken drivers
 -> Baken compositor
 -> Desktop Shell
```

sem dependência de serviços UEFI para input, storage, temporização ou lógica de desktop.
