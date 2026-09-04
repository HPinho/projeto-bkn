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

O kernel é responsável por GDT/IDT/TSS/exceções, PMM/VMM/heap/DMA, PAT, ACPI/APIC/IOAPIC/timers, PCI/PCIe, scheduler, input HAL, storage e Graphics API/compositor/backends.

### UI

Installer, OOBE, desktop, dock, janelas, animações e widgets devem existir em Sotlas e consumir APIs do Baken. Eles não acessam GOP, MSR, PCI ou MMIO diretamente.

## Estado transitório atual

A árvore ainda possui dívida de migração no bootloader. Pointer Protocol, Block I/O e SystemTable atravessam o handoff, e o kernel ainda roda antes do corte final de `ExitBootServices()`.

Essas pontes são legado transitório, não arquitetura final. Nenhuma nova funcionalidade pode depender delas.

A remoção deve ocorrer em ordem segura:

1. implementar entrada nativa suficiente para substituir pointer UEFI;
2. implementar block device nativo suficiente para substituir Block I/O UEFI;
3. completar PMM/VMM e preservar o mapa de memória;
4. estabilizar o BootInfo bare-metal;
5. executar `ExitBootServices()` antes de `baken_kernel_main`;
6. remover os campos e caminhos de runtime UEFI restantes.

## Marco implementado: BakenBootInfo v2 + Memory Map + ACPI

O `BakenBootInfo v2` já está implementado como envelope de transição, com validação no ponto de entrada Sotlas.

O bootloader coleta um snapshot real do UEFI Memory Map usando a negociação de tamanho com `EFI_BUFFER_TOO_SMALL`, aloca um buffer com folga e registra `memory_descriptor_size` e `memory_descriptor_version`.

Ele também localiza a ACPI RSDP por GUID completa, preferindo ACPI 2.0 e usando 1.0 como fallback. Framebuffer, pixel format, versão, tamanho e flags do handoff também são preenchidos.

O kernel valida versão, tamanho mínimo, framebuffer, dimensões e pitch antes de inicializar a sessão gráfica.

Como o runtime ainda usa Boot Services depois da entrada do kernel, esse snapshot **não é ainda o memory map final associado ao map key do ExitBootServices**. O map final será recapturado imediatamente antes do cutover.

## BakenBootInfo v2 — envelope de transição

Para evitar quebrar o ABI do runtime atual, o v2 preserva os primeiros 80 bytes do layout legado e adiciona depois metadados necessários ao futuro handoff bare-metal:

```text
legacy-compatible prefix (temporário)
├── framebuffer
├── memory map pointer/size
├── SystemTable            [LEGADO]
├── Pointer Protocol       [LEGADO]
├── Block I/O              [LEGADO]
└── Install target BlockIO [LEGADO]

v2 extension
├── version
├── struct_size
├── flags
├── memory_descriptor_size
├── memory_descriptor_version
├── pixel_format
└── acpi_rsdp
```

Ele **não é o contrato final**. Depois que input, timer e storage nativos substituírem as pontes de firmware, um ABI limpo removerá os ponteiros UEFI e será usado somente depois de `ExitBootServices()`.

## BootInfo alvo pós-cutover

```text
BakenBootInfo
├── version
├── struct_size
├── flags
├── framebuffer
│   ├── physical_base
│   ├── byte_size
│   ├── width
│   ├── height
│   ├── pixels_per_scanline
│   └── pixel_format
├── memory_map
│   ├── address
│   ├── size
│   ├── descriptor_size
│   └── descriptor_version
├── acpi_rsdp
├── kernel image metadata
└── initrd/system image metadata
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

A ordem de inicialização deve ser:

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

O framebuffer deve ser mapeado como Write-Combining quando suportado. Não basta escrever `IA32_PAT`: a entrada PAT correta deve ser selecionada pelos bits PAT/PCD/PWT das page tables.

```text
normal RAM / backbuffer = WB
framebuffer GOP         = WC
MMIO                     = UC, salvo exigência explícita do dispositivo
```

## ACPI e interrupções

ACPI deve fornecer pelo menos RSDP/XSDT, MADT, MCFG e FADT, expandindo depois para DSDT/SSDT e AML.

O IOAPIC não deve assumir mapeamento fixo de IRQ legado:

```text
MADT -> Interrupt Source Override -> GSI -> IOAPIC -> vetor IDT
```

## Input

```text
i8042/PS2 ----\
USB HID -------+-> Input HAL -> Event Normalizer -> Ring Buffer -> Window Manager
I2C-HID -------/
```

PS/2 é um backend, não garantia universal de touchpad. Notebooks modernos podem exigir ACPI + I2C + HID-over-I2C.

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

O backend universal inicial usa backbuffer WB, `DamageRegion` com múltiplos retângulos e cópia apenas das regiões alteradas para framebuffer WC.

PCI discovery e BAR mapping apenas descobrem a GPU. Aceleração real exige driver específico com MMIO, memória/contexts, queues/rings, command buffers, fences e present/scanout.

## Storage

```text
NVMe/AHCI
 -> Block Device API
 -> GPT
 -> filesystem
 -> installer
```

GPT e FAT32 devem ser calculados dinamicamente a partir do tamanho lógico de bloco e do volume real.

## Scheduler e DMA

xHCI, NVMe, VirtIO e GPUs dependem de DMA. Deve existir API central de DMA com endereço virtual, endereço físico, tamanho e alinhamento.

Input, storage, compositor e USB não devem permanecer em um único polling loop; a evolução inclui kernel threads, ready queue, sleep queue, timer e context switch.

## Ordem de implementação

```text
0. Sotlas compiler/backend e intrínsecos confiáveis
1. BootInfo v2 + GetMemoryMap + ACPI handoff            [IMPLEMENTADO]
2. GDT/IDT/TSS/exceptions                              [PRÓXIMO]
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
14. ExitBootServices cutover + remoção final das pontes UEFI
```

## Testes arquiteturais

A suíte deve garantir:

- `compiler.py`/`bootstrap.py` sem UI específica;
- ausência da antiga ponte monolítica;
- layout/versionamento de `BakenBootInfo`;
- metadados de Memory Map e ACPI no v2;
- validação do BootInfo no kernel;
- ausência de novos consumidores das pontes UEFI;
- PAT/PTE encoding, PMM/VMM, ACPI, DamageRegion, ring buffers, PCI, GPT/CRC32 e FAT32;
- boot pós-`ExitBootServices()` no momento do cutover.

## Critério de conclusão

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
