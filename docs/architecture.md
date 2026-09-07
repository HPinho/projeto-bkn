# Arquitetura canônica do Baken OS

## Objetivo

O Baken OS é um sistema operacional x86-64 bare-metal próprio. Python é ferramenta de compilação/build/teste; **UEFI é apenas bootstrap**; Sotlas é compilado para código nativo; depois do handoff o kernel Baken assume memória, interrupções, barramentos, entrada, armazenamento e gráficos.

```text
Sotlas source
    -> Sotlas compiler
    -> x86-64 machine code
    -> Baken kernel / drivers / services
    -> hardware
```

A regra central permanece:

> O compilador não desenha o sistema operacional. Ele apenas permite que o sistema operacional exista.

## Fronteira UEFI

`BOOTX64.EFI` possui somente responsabilidades de bootstrap:

1. localizar/configurar GOP e registrar o framebuffer;
2. localizar ACPI RSDP;
3. reservar arena de page tables e stack de transição;
4. registrar a imagem carregada;
5. obter o Memory Map final;
6. construir as page tables de transição a partir do mapa que produz o `MapKey`;
7. executar `ExitBootServices()` com retry correto;
8. trocar para stack Baken e transferir controle para `sotlas_x86_post_cutover_entry`.

Depois de `ExitBootServices()`, nenhum Boot Service ou Runtime Service pode ser chamado novamente. O kernel não depende de Pointer Protocol, Block I/O UEFI, timers/eventos UEFI ou `EFI_SYSTEM_TABLE`.

O framebuffer descoberto por GOP continua utilizável como recurso físico, mas seu mapping e política de cache são responsabilidade do VMM/PAT Baken.

## BootInfo alvo

`BakenBootInfo v2` mantém 192 bytes por estabilidade ABI. Os offsets 48..79, que historicamente transportavam ponteiros de firmware, agora são reservas zeradas (`reserved_abi_0..3`).

Não fazem parte do contrato executável pós-cutover:

```text
EFI_SYSTEM_TABLE*
EFI_SIMPLE_POINTER_PROTOCOL*
EFI_ABSOLUTE_POINTER_PROTOCOL*
EFI_BLOCK_IO_PROTOCOL*
EFI_BOOT_SERVICES*
```

O contexto nativo `PostCutoverContext` contém apenas dados estáveis necessários depois do corte: CR3 raiz, stack, framebuffer, snapshot final de memória, ACPI RSDP e metadados da arena de page tables.

O snapshot recebido do bootstrap preserva o layout POD de 40 bytes do descritor para estabilidade binária, mas a API interna do kernel usa nomenclatura Baken (`BootMemoryDescriptor`, `BAKEN_BOOT_MEMORY_*`, `boot_memory_*`).

## Fundação x86-64

A sequência canônica implementada é:

```text
UEFI bootstrap
    -> final Memory Map / MapKey
    -> page tables de transição + W^X + guard stack
    -> ExitBootServices()
    -> stack switch
    -> CR3 Baken
    -> GDT/TSS/IDT
    -> PMM allocator
    -> VMM / active page tables
    -> ACPI / MADT
    -> LAPIC / IOAPIC
    -> IRQs
    -> LAPIC timer live
    -> PCI / DMA / drivers nativos
    -> PAT/WC framebuffer
    -> Baken native runtime
```

### Núcleo obrigatório

As seguintes invariantes são fail-closed: se falharem, o kernel não possui um ambiente seguro para continuar:

- contexto pós-cutover válido;
- CR3/page tables próprias;
- GDT/TSS/IDT;
- PMM allocator e VMM;
- ACPI/MADT;
- LAPIC/IOAPIC e infraestrutura de IRQ;
- timer nativo funcional;
- mapping PAT/WC válido do framebuffer antes do runtime gráfico.

### Hardware opcional e certificação

PS/2, xHCI/USB HID e um controlador/storage específico são backends de hardware, não pré-condições universais para existir um kernel válido. O boot normal tenta esses backends sem bloquear indefinidamente só porque um dispositivo não está presente.

A certificação de CI é deliberadamente mais rigorosa. O marcador:

```text
BAKEN:BARE_METAL_READY
```

só é emitido quando a fixture QEMU prova toda a cadeia configurada: timer, teclado, xHCI/USB HID, AHCI, Block Device, GPT redundante, MBR/FAT32, NVMe e PAT/WC.

Portanto `BAKEN:BARE_METAL_READY` significa **fundação completa comprovada na fixture**, não simplesmente “o desktop começou”.

## Memória

O kernel possui PMM allocator pós-`ExitBootServices()` e VMM ativo sobre as page tables próprias. O mapa final é consumido como dados do handoff, sem reentrada em firmware.

Política de cache:

```text
RAM/backbuffer = WB
framebuffer    = WC
MMIO           = UC salvo exigência explícita do dispositivo
```

O framebuffer WC é instalado pelo caminho de page tables/PAT do kernel e não pelo driver de display de forma isolada.

## ACPI, interrupções e timer

ACPI fornece o inventário de plataforma; MADT alimenta LAPIC/IOAPIC e roteamento de interrupções. O kernel carrega IDT própria e habilita interrupções somente depois das estruturas necessárias estarem válidas.

O timer pós-cutover é nativo e comprovado por IRQ real. Não há espera baseada em `Stall()` ou evento UEFI.

## PCI, DMA e USB

A enumeração PCI global é conservadora. Drivers habilitam explicitamente somente command bits que realmente precisam, após validar MMIO e recursos.

DMA é alocado pelo PMM e compartilhado explicitamente com dispositivos. xHCI possui caminho nativo de reset, rings, event ring, commands, enumeration, EP0 e HID Interrupt IN.

PS/2 e USB HID são backends independentes do Input HAL; xHCI não depende da existência de teclado PS/2.

## Storage

A pilha nativa possui AHCI, NVMe e Block Device API, com GPT/MBR/FAT32 acima da camada de bloco.

Os probes destrutivos de certificação só escrevem depois de reconhecer a assinatura específica da fixture de teste. Mídia comum não deve ser tratada como dispositivo de certificação.

A evolução de produto deve manter separados:

```text
boot normal: descoberta/inicialização tolerante à ausência de backends
certificação: probes rigorosos e reproduzíveis sobre mídia conhecida
```

## Gráficos e UI

Installer, OOBE, desktop, dock, janelas, animações e widgets pertencem a Sotlas e consomem APIs do Baken. Não acessam GOP, UEFI, PCI ou MMIO como atalhos de UI.

O backend framebuffer é software até existir um driver GPU real. Descoberta PCI de uma GPU não equivale a aceleração.

## Compilador Sotlas

`tools/sotlas_compile/` pertence ao host e pode implementar lexer, parser, AST, análise semântica, IR, lowering, ABI, backend x86-64, link orchestration e intrínsecos arquiteturais.

Ele não pode implementar wallpaper, dock, cursor, janelas, installer, OOBE, compositor ou lógica específica de dispositivos.

Python, MinGW, QEMU, OVMF e GitHub Actions são dependências de desenvolvimento/build/teste, não dependências de runtime do kernel. Self-hosting do compilador é um marco futuro separado.

## Auditoria e critérios de regressão

A suíte deve impedir:

- retorno de `baken_efi_*`, `uefi_*`, `Efi*`, `EFI_*`, Boot/Runtime Services no grafo pós-cutover;
- reintrodução da antiga ponte `baken_runtime.sotlas` ou `cutover_plan.sotlas`;
- UI específica dentro do compilador;
- transporte de Pointer Protocol/Block I/O pelo loader;
- ativação fictícia de GPU;
- PAT/WC sem page-table encoding real;
- storage/USB simulados que apenas retornam sucesso;
- regressão da ordem de ativação CPU -> memória -> ACPI -> interrupções -> timer -> runtime.

O auditor `tools/scripts/audit_post_cutover.py` percorre o grafo direto alcançável a partir das entradas pós-cutover e falha para símbolos de firmware. Chamadas opacas no limite dos intrínsecos x86 continuam sujeitas a revisão explícita.

## Critério de conclusão da fundação

A fundação x86-64 é considerada fechada quando o head atual da `main` comprova simultaneamente:

```text
Test Suite                    PASS
Sotlas modular graph          PASS
Native kernel build           PASS
UEFI ISO build                PASS
QEMU post-cutover boot        PASS
BAKEN:BARE_METAL_READY        PRESENT
zero firmware reentry audit   PASS
```

Depois desse ponto, scheduler/multitarefa, heap de propósito geral mais sofisticado, AML/I2C-HID, rede, áudio, drivers GPU e expansão da UI são **camadas seguintes do sistema**, não pré-requisitos para declarar a fundação bare-metal concluída.
