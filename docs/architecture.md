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

## Marcos já implementados nesta migração

- `BakenBootInfo v2` versionado, preservando temporariamente o prefixo legado;
- coleta real de `GetMemoryMap`, `descriptor_size` e `descriptor_version`;
- localização real da ACPI RSDP por GUID completa;
- inventário PMM do Memory Map sem alocar páginas enquanto Boot Services ainda vivem;
- enumeração PCI por `0xCF8/0xCFC` em modo somente leitura;
- leitura de BARs sem sizing destrutivo por `0xFFFFFFFF` durante varredura global;
- nenhuma habilitação automática de Bus Master/I/O Space durante discovery;
- backend GOP identificado corretamente como rasterização por CPU;
- remoção da escrita cega de `IA32_PAT` no driver de display;
- guardrails de testes para impedir regressão dessas fronteiras.

Ainda não estão implementados e não devem ser simulados:

- `ExitBootServices()` antes do kernel normal;
- PMM allocator ativo;
- VMM/page tables próprias;
- mapping PAT/WC real do framebuffer;
- GDT/IDT/TSS próprios carregados pelo kernel;
- APIC/IOAPIC e interrupções nativas completas;
- USB xHCI/HID e I2C-HID completos;
- NVMe/AHCI nativos na rota normal;
- command submission real para GPU.

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

A ordem de inicialização deve evoluir para:

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

### Pré-requisito do backend Sotlas para GDT/IDT/TSS

O compilador canônico ainda precisa de lowering explícito para instruções privilegiadas que não podem ser representadas como funções comuns: `lgdt`, `lidt`, `ltr`, leitura de `CR2`, `invlpg` e operações de controle de paginação relacionadas.

Essas operações devem ser intrínsecos do backend x86-64, com assinatura Sotlas estável e emissão de instrução real. Elas **não** serão implementadas como lógica visual, strings de assembly escondidas em módulos de UI ou stubs que apenas retornam sucesso.

Somente depois desses intrínsecos existirem e tiverem testes de codegen os módulos GDT/IDT/TSS serão conectados à entrada do kernel.

## PMM

O estágio atual é um **inventário**, não um allocator. Ele interpreta descritores UEFI reais, contabiliza regiões convencionais, ACPI e MMIO e identifica limites físicos.

Enquanto `BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE` existir, `EfiConventionalMemory` não pode ser entregue como página livre pelo PMM: Boot Services ainda podem consumir essa memória.

`pmm_alloc_page`/`pmm_free_page` só serão ativados depois do cutover, usando o último Memory Map válido obtido imediatamente antes de `ExitBootServices()`.

## Memória e PAT

O framebuffer deve ser mapeado como Write-Combining quando suportado. Não basta escrever `IA32_PAT`: a entrada PAT correta deve ser selecionada pelos bits PAT/PCD/PWT das page tables.

```text
normal RAM / backbuffer = WB
framebuffer GOP         = WC
MMIO                     = UC, salvo exigência explícita do dispositivo
```

O `display_driver` não escreve `IA32_PAT`. Ele só poderá registrar `framebuffer_wc_active=true` depois que o VMM tiver instalado e confirmado o mapping correto.

## ACPI e interrupções

ACPI deve fornecer pelo menos RSDP/XSDT, MADT, MCFG e FADT, expandindo depois para DSDT/SSDT e AML.

O IOAPIC não deve assumir mapeamento fixo de IRQ legado:

```text
MADT -> Interrupt Source Override -> GSI -> IOAPIC -> vetor IDT
```

## PCI / PCIe

A enumeração global PCI é somente leitura:

```text
pci_scan_all()
 -> Vendor/Device/Class
 -> Header Type
 -> Command atual
 -> BAR base/flags atuais
```

Durante discovery ela não habilita Bus Master, I/O Space ou Memory Space e não dimensiona BARs escrevendo `0xFFFFFFFF`. Cada driver deve solicitar explicitamente somente os command bits que utiliza, depois de validar recursos, DMA e MMIO.

PCIe ECAM será adicionado a partir da tabela ACPI MCFG.

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

O backend GOP atual é software e deve reportar `is_hardware_accelerated=false`. Encontrar uma GPU por PCI não promove o backend.

O backend universal inicial usa backbuffer WB, `DamageRegion` com múltiplos retângulos e cópia apenas das regiões alteradas para framebuffer WC depois que o VMM/PAT estiver ativo.

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

A leitura GPT fixa de 512 bytes ainda presente no bootloader é compatibilidade temporária da mídia atual e não deve migrar para a camada storage nativa.

## Scheduler e DMA

xHCI, NVMe, VirtIO e GPUs dependem de DMA. Deve existir API central de DMA com endereço virtual, endereço físico, tamanho e alinhamento.

Input, storage, compositor e USB não devem permanecer em um único polling loop; a evolução inclui kernel threads, ready queue, sleep queue, timer e context switch.

## Ordem de implementação

```text
0. Sotlas compiler/backend e intrínsecos confiáveis
1. BootInfo v2 + GetMemoryMap + ACPI handoff            [IMPLEMENTADO]
2. PMM inventory                                       [IMPLEMENTADO]
3. PCI discovery read-only                             [IMPLEMENTADO]
4. intrínsecos x86-64 para GDT/IDT/TSS                 [PRÓXIMO]
5. GDT/IDT/TSS/exceptions
6. PMM allocator pós-cutover + VMM/heap/PAT
7. ACPI/APIC/IOAPIC/timers
8. scheduler + PCIe ECAM + DMA
9. framebuffer/backbuffer/DamageRegion/compositor
10. i8042 + Input HAL
11. xHCI + USB HID
12. AHCI/NVMe + Block API
13. GPT/FAT32 + installer real
14. AML + I2C-HID
15. VirtIO-GPU
16. Intel GPU nativa
17. ExitBootServices cutover + remoção final das pontes UEFI
```

## Testes arquiteturais

A suíte deve garantir:

- `compiler.py`/`bootstrap.py` sem UI específica;
- ausência da antiga ponte monolítica;
- layout/versionamento de `BakenBootInfo`;
- metadados de Memory Map e ACPI no v2;
- PMM sem allocator enquanto a ponte UEFI existir;
- PCI scan sem habilitação automática de dispositivos;
- BAR discovery sem sizing destrutivo;
- backend GOP sem aceleração GPU fictícia;
- ausência de escrita cega de PAT no display;
- ausência de novos consumidores das pontes UEFI;
- PAT/PTE encoding, VMM, ACPI, DamageRegion, ring buffers, GPT/CRC32 e FAT32 conforme entrarem na rota;
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
