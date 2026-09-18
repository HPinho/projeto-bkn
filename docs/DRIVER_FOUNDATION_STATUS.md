# Baken OS — Driver Foundation Status

Atualizado em 2026-09-17 (America/Fortaleza).

Este arquivo e o checkpoint operacional curto da Driver Foundation. O historico detalhado permanece preservado em `BAKEN_OS_ROADMAP.md`, `KERNEL_HANDOFF.md`, `KERNEL_HANDOFF_APPENDIX.md` e nos appendices especificos da Driver Foundation.

## Regra de seguranca da plataforma

O Baken OS ja atingiu boot em notebook real. A Driver Foundation deve preservar como invariantes:

- zero dependencia de firmware UEFI depois do cutover;
- CR3, PMM/VMM/DMA, ACPI/APIC/IRQ, xHCI/HID e storage bare-metal permanecem ownership do kernel;
- nenhum microcorte redesenha boot, allocator, interrupt core ou page tables sem necessidade provada;
- Generic IRQ Registry permanece a unica autoridade de vetores dinamicos;
- EOI permanece centralizado no dispatcher x86 existente;
- PCI/MSI/MSI-X/DMA evoluem em microcortes pequenos, fail-closed e reversiveis;
- nao empilhar funcionalidade sobre SHA candidato vermelho ou superseded por auditoria;
- feature so vira `CERTIFIED` depois dos gates obrigatorios no mesmo SHA.

## Estados formais

```text
PLANNED -> IMPLEMENTED -> VALIDATING -> CERTIFIED
                           |
                           +-> FAILED -> correction-only -> VALIDATING
                           +-> SUPERSEDED_BY_AUDIT -> correction-only -> VALIDATING
```

`IMPLEMENTED` significa somente que o codigo existe. Nao equivale a baseline certificada.

## Baseline certificada de fechamento do DF-7

```text
1e4d82034941c291737c748adf1db9ca23563cc1
test(pci): guard ivshmem MSI-X BAR sizing command restore
```

## Baseline certificada DF-8a

```text
e33e6780106edb61bdbca72fa818272d23e154e2
docs(driver): open DF-8a validation baseline
```

## Baseline certificada DF-8b

```text
bf0d75503dec9a83246b2a66fd94539cfd2c62cf
fix(test): ignore DMA comments in DF-8 guardrails
```

Os sete gates obrigatorios do SHA `bf0d75503dec9a83246b2a66fd94539cfd2c62cf` fecharam com sucesso. O DF-8b passa a ser a baseline certificada para typed constrained allocation.

## Driver Foundation

```text
DF-0   Architecture / contracts                    CERTIFIED
DF-1   Driver API / descriptors                    CERTIFIED
DF-2   Resource Manager                            CERTIFIED
DF-3   Device Core                                 CERTIFIED
DF-3.1 Transactional lifecycle                     CERTIFIED
DF-4   Generic IRQ Registry                        CERTIFIED
DF-5   PCI Core v2                                 CERTIFIED
DF-6   MSI                                         CERTIFIED
DF-7   MSI-X                                       CERTIFIED
  DF-7a  read-only capability model                CERTIFIED
  DF-7b  BAR-backed Table/PBA layout proof         CERTIFIED
  DF-7b1 controlled quiescent BAR sizing           CERTIFIED
  DF-7c  source/vector ownership                   CERTIFIED
  DF-7d  masked table-entry programming            CERTIFIED
  DF-7e1 activation + fail-closed teardown          CERTIFIED
  DF-7e2 QEMU ivshmem runtime proof                CERTIFIED
DF-8   DMA Device API                              CERTIFIED
  DF-8a read-only device constraints model         CERTIFIED
  DF-8b typed constrained allocation               CERTIFIED
  DF-8c per-device integration / NVMe first        CERTIFIED
  DF-8c2 AHCI runtime typed integration              CERTIFIED
  DF-8c3 AHCI read-buffer typed integration          CERTIFIED
  DF-8c4 AHCI write-buffer typed integration         CERTIFIED
  DF-8c5 xHCI runtime-arena typed integration        CERTIFIED
  DF-8c6 xHCI slot-context arena integration         CERTIFIED
  DF-8c7 xHCI device-descriptor buffer integration   CERTIFIED
  DF-8c8 xHCI configuration-buffer integration       CERTIFIED
  DF-8c9 xHCI HID transfer-ring integration           CERTIFIED
  DF-8c10 xHCI HID report-buffer integration          CERTIFIED
  DF-8c11 xHCI HID descriptor-buffer integration      CERTIFIED
  DF-8c12 AHCI generic block-I/O buffer integration   CERTIFIED
DF-9   MMIO Mapping API                            IN PROGRESS
  DF-9a Typed MMIO range/policy contract              CERTIFIED
  DF-9b MMIO ownership/claim integration              CERTIFIED
  DF-9c1 Cache-policy backend capability model         CERTIFIED
  DF-9c2 WC preflight/UC restore primitives            CERTIFIED
  DF-9c3 Generic WC promotion with rollback            CERTIFIED
  DF-9c4 Runtime PAT capability probe                  CERTIFIED
  DF-9c5 Generic WT/WB PAT-index backends              CERTIFIED
  DF-9d1 PCI ECAM typed UC mapping migration            CERTIFIED
  DF-9d2 MSI-X table typed UC mapping migration         CERTIFIED
  DF-9d3 MSI-X activation typed UC mapping migration    CERTIFIED
  DF-9d4 xHCI controller typed UC mapping migration     CERTIFIED
  DF-9d5 xHCI PORTSC typed UC mapping migration        IMPLEMENTED / VALIDATING
DF-10  Bus Model                                   PLANNED
DF-11  Class Registries                            PLANNED
```

## DF-8 — DMA Device API

Objetivo da macroetapa: representar e aplicar constraints DMA por dispositivo sem substituir o allocator fisico existente e sem criar caminhos paralelos ao PMM/VMM/DMA ja certificados.

### DF-8a — read-only device constraints model

**CERTIFIED.** Baseline `e33e6780106edb61bdbca72fa818272d23e154e2`.

### DF-8b — typed constrained allocation

**CERTIFIED.** Baseline `bf0d75503dec9a83246b2a66fd94539cfd2c62cf`.

`dma_alloc_for_constraints(size, constraints)` valida o contrato tipado e delega exatamente uma vez para `dma_alloc_for_device(...)`, que continua usando `pmm_alloc_pages_constrained(...)` como unico backend fisico constrained.

### DF-8c — per-device integration / NVMe first

**IMPLEMENTED / VALIDATING.**

Primeiro caller real escolhido: `kernel/src/drivers/nvme.sotlas`.

Motivos:

- ja possuia gate runtime dedicado NVMe-only;
- ja usava constraints explicitas e simples;
- a migracao preserva exatamente os valores anteriores: `alignment=4096`, `max_address=0xFFFFFFFFFFFFFFFF`, `boundary=0`;
- nenhuma mudanca em MMIO, filas, sharing, IRQ, comandos NVMe, teardown ou PMM/VMM.

Novo caminho:

```text
dma_device_constraints(4096, U64_MAX, 0)
-> dma_device_constraints_valid(...)
-> dma_alloc_for_constraints(20480, ...)
-> dma_buffer_satisfies_device_constraints(...)
-> dma_share_with_device(...)
```

Guardrails:

- `tests/test_foundation_nvme_gate.py` exige o caminho tipado e proibe a chamada legacy direta para a arena NVMe;
- `tests/test_dma_contract.py` exige que, neste primeiro corte DF-8c, o unico caller de `dma_alloc_for_constraints(...)` fora de `dma.sotlas` seja `kernel/src/drivers/nvme.sotlas`.

## Gates obrigatorios

Para candidatos funcionais da Driver Foundation, o conjunto atual e:

```text
1. CI/CD + Automated QEMU
2. SMP Bring-up
3. NVMe-only Bare-Metal
4. HID Dual-device
5. SMP Fault Diagnostic
6. MSI EDU Runtime
7. MSI-X ivshmem Runtime
```

Se qualquer gate falhar, o candidato entra em `correction-only` ate todos voltarem a verde no mesmo SHA corretivo.

## Regra de retomada

```text
main HEAD
-> ultima baseline certificada
-> candidate SHA
-> auditorias conhecidas do candidate
-> gates do candidate
-> correction-only se qualquer gate falhar OU auditoria invalidar a garantia
-> somente entao escolher o proximo microcorte
```

Documentacao complementar:

- `BAKEN_OS_DRIVER_FOUNDATION_ROADMAP_APPENDIX.md`
- `KERNEL_DRIVER_FOUNDATION_HANDOFF_APPENDIX.md`


### DF-8c2 — segunda integração por dispositivo: AHCI runtime

**CERTIFIED.** Baseline `253ed951efd2bc47e86fe2172c63e7b072b162fa`.

O segundo corte migra somente a arena principal de `kernel/src/drivers/ahci_runtime.sotlas` para o contrato tipado, preservando o comportamento anterior:

```text
alignment   = AHCI_RUNTIME_PAGE_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- a arena continua com `AHCI_RUNTIME_ARENA_PAGES * AHCI_RUNTIME_PAGE_SIZE`;
- nenhuma constraint nova de hardware foi introduzida;
- `dma_alloc_for_constraints(...)` continua delegando ao backend constrained existente;
- o buffer e validado por `dma_buffer_satisfies_device_constraints(...)` antes de ser publicado ao hardware;
- `dma_share_with_device(...)`, programacao CLB/FB, Bus Master e IDENTIFY permanecem inalterados;
- buffers AHCI de leitura/escrita continuam fora deste microcorte;
- o guard global permite somente NVMe e `ahci_runtime.sotlas` como callers tipados.


### DF-8c3 — terceira integração por dispositivo: AHCI read buffer

**CERTIFIED.** Baseline `a80599f6b0951bb43688cf2a0737a29a66fe2980`.

Este corte migra somente o buffer dedicado de leitura em `kernel/src/drivers/ahci_block_read.sotlas` para constraints tipadas:

```text
alignment   = AHCI_RUNTIME_PAGE_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- o buffer continua tendo uma pagina de 4096 bytes;
- nenhuma constraint nova de hardware foi introduzida;
- o buffer e validado por `dma_buffer_satisfies_device_constraints(...)` antes de `dma_share_with_device(...)`;
- o caminho de READ, PRDT, LBA e validacao da fixture permanece inalterado;
- o `AHCI_WRITE_BUFFER` continua usando o allocator legado neste microcorte;
- o guard global permite somente NVMe, `ahci_runtime.sotlas` e `ahci_block_read.sotlas` como callers tipados.


### DF-8c4 — quarta integração por dispositivo: AHCI write buffer

**CERTIFIED.** Baseline `2b537336858b93105bc1fece62d0f17c604f7949`.

Este corte migra somente o buffer dedicado de escrita em `kernel/src/drivers/ahci_block_read.sotlas` para constraints tipadas, com o mesmo perfil físico do read buffer:

```text
alignment   = AHCI_RUNTIME_PAGE_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- o buffer continua tendo uma pagina de 4096 bytes;
- nenhuma constraint nova de hardware foi introduzida;
- o buffer e validado por `dma_buffer_satisfies_device_constraints(...)` antes de `dma_share_with_device(...)`;
- a emissao WRITE DMA, o clear, o READ-back real e a verificacao persistida permanecem inalterados;
- como read e write residem no mesmo modulo, a lista global de arquivos callers tipados permanece em tres arquivos.


### DF-8c5 — quinta integração por dispositivo: xHCI runtime arena

**CERTIFIED.** Baseline `6107fdea189e9c592e087457ceb7222a2082bfb1`.

Este corte migra somente a arena principal de `kernel/src/drivers/xhci_runtime.sotlas` para constraints tipadas, preservando o contrato físico existente:

```text
alignment   = XHCI_RUNTIME_PAGE_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- `total_pages`, DCBAA, Command Ring, Event Ring, ERST e scratchpads permanecem no mesmo layout contiguo;
- nenhuma constraint nova de hardware foi introduzida;
- a arena e validada por `dma_buffer_satisfies_device_constraints(...)` antes de qualquer subbuffer ser derivado;
- nenhum doorbell, Bus Master, start do controller, ERST programming ou ownership de rings foi alterado;
- o guard global passa a permitir exatamente quatro arquivos callers tipados.


### DF-8c6 — sexta integração por dispositivo: xHCI slot-context arena

**CERTIFIED.** Baseline `75ef2c00d64d1770052d1790324a7bb7b8df57ee`.

Este corte migra somente a arena de Device Context / Input Context / EP0 Transfer Ring em `kernel/src/drivers/xhci_context.sotlas` para constraints tipadas:

```text
alignment   = XHCI_CONTEXT_PAGE_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- a arena continua tendo exatamente 3 paginas por slot;
- Device Context, Input Context e EP0 Ring continuam derivados da mesma arena;
- a arena e validada antes de zeroing/publicacao;
- rollback pre-DCBAA, rollback pos-DCBAA, unshare e release permanecem inalterados;
- Address Device, doorbells e command/event rings nao foram movidos para este corte;
- o guard global passa a permitir exatamente cinco arquivos callers tipados.


### DF-8c7 — setima integração por dispositivo: xHCI device-descriptor buffers

**CERTIFIED.** Baseline `6ddc9ec20b6c4a517499f238046558cad12fa4c1`.

Este corte migra os dois pontos de alocação do Device Descriptor em `kernel/src/drivers/xhci_descriptor.sotlas` (probe curto de 8 bytes e leitura completa de 18 bytes) para constraints tipadas, preservando o mesmo buffer físico de uma página:

```text
alignment   = XHCI_DESCRIPTOR_DMA_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- ambos os caminhos continuam usando um buffer de 4096 bytes;
- publish per-slot, quarantine, completion, teardown exact-epoch e tombstones permanecem inalterados;
- submit/wait ambiguo continua fail-closed e nunca libera o buffer publicado;
- nenhum endpoint, doorbell, Address Device ou command/event ring foi alterado;
- o guard global passa a permitir exatamente seis arquivos callers tipados.


### DF-8c8 — oitava integração por dispositivo: xHCI configuration buffers

**CERTIFIED.** Baseline `74477451185abea2ec316064ce0e263fbb569712`.

Este corte migra os dois pontos de alocação do Configuration Descriptor em `kernel/src/drivers/xhci_configuration.sotlas` (header e leitura completa) para constraints tipadas:

```text
alignment   = XHCI_CONFIGURATION_DMA_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- ambos os caminhos continuam usando um buffer de 4096 bytes;
- owner per-slot, quarantine, completion terminal, teardown exact-epoch e tombstones permanecem inalterados;
- submit/wait ambiguo continua fail-closed;
- parsing de HID/interface/endpoint e o fluxo SET_CONFIGURATION permanecem inalterados;
- o guard global passa a permitir exatamente sete arquivos callers tipados.


### DF-8c9 — nona integração por dispositivo: xHCI HID transfer ring

**CERTIFIED.** Baseline `13ecd2a02caeed26fc71029c5419b3ae81f4fd06`.

Este corte migra somente o HID Interrupt IN Transfer Ring em `kernel/src/drivers/xhci_hid_context.sotlas` para constraints tipadas:

```text
alignment   = XHCI_HID_RING_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- o ring continua com uma pagina de 4096 bytes e 256 TRBs;
- snapshot do Input Context ocorre antes da alocacao;
- zero/bind/write/share failures continuam passando pelo rollback existente;
- restore do Input Context continua precedendo release do candidato;
- o ring so e publicado depois de `dma_share_with_device(...)`;
- Configure Endpoint, Event Ring, report buffer e input-event pipeline permanecem fora deste corte;
- o guard global passa a permitir exatamente oito arquivos callers tipados.


### DF-8c10 — decima integração por dispositivo: xHCI HID report buffer

**CERTIFIED.** Baseline `5125585be18b831a2402898d917371f951d2c33c`.

Este corte migra somente o buffer DMA de reports HID Interrupt IN em `kernel/src/drivers/xhci_hid_report.sotlas` para constraints tipadas:

```text
alignment   = XHCI_HID_REPORT_DMA_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- o buffer continua com uma pagina de 4096 bytes;
- owner antigo ou em quarentena continua bloqueando novo prepare antes da alocacao;
- zero/share failures continuam liberando apenas o candidato nao publicado;
- TRB publish, doorbell, producer cycle, completion e pending bookkeeping permanecem inalterados;
- parser HID, input-device map, event queue e fallback boot keyboard/mouse permanecem fora deste corte;
- o guard global passa a permitir exatamente nove arquivos callers tipados.


### DF-8c11 — decima primeira integração por dispositivo: xHCI HID descriptor buffer

**CERTIFIED.** Baseline `6deb7110fd878cd9394f11ba2314b08189b002c0`.

Este corte migra somente o buffer DMA persistente do HID Report Descriptor em `kernel/src/drivers/xhci_hid_descriptor.sotlas` para constraints tipadas:

```text
alignment   = XHCI_HID_DESCRIPTOR_DMA_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- o buffer continua com uma pagina de 4096 bytes;
- owner per-slot e quarantine antes do EP0 submit permanecem inalterados;
- submit/wait ambiguo continua preservando o owner para recovery;
- identity teardown generation-safe e teardown DMA exact-epoch permanecem inalterados;
- parser HID, InputDevice, field map e event binding permanecem fora deste corte;
- o guard global passa a permitir exatamente dez arquivos callers tipados.


### DF-8c12 — decima segunda integração por dispositivo: AHCI generic block-I/O buffer

**CERTIFIED.** Baseline `db5aa0ce3866184f5e39d6bdb1338d244cf5a25d`.

Este corte migra somente o buffer DMA persistente de I/O genérico em `kernel/src/drivers/ahci_block_io.sotlas` para constraints tipadas:

```text
alignment   = AHCI_RUNTIME_PAGE_SIZE (4096)
max_address = 0xFFFFFFFFFFFFFFFF
boundary    = 0
```

Invariantes:

- o buffer continua com uma pagina de 4096 bytes;
- READ/WRITE genericos continuam compartilhando o mesmo buffer;
- PRDT, FIS, LBA28/LBA48, command issue e polling permanecem inalterados;
- nenhuma constraint nova de hardware foi introduzida;
- o guard global passa a permitir exatamente onze arquivos callers tipados.


## Fechamento DF-8 — DMA Device API

**CERTIFIED.** Baseline `2818f21ac0c4673a0eab201744ba123294b19734`.

A auditoria final apos DF-8c12 confirma:

- NVMe, AHCI e xHCI de runtime normal nao possuem mais callers legados de `dma_alloc(...)` para buffers diretamente entregues ao dispositivo;
- `kernel/src/drivers/storage_discovery.sotlas` preserva `dma_alloc(...)` somente para um buffer CPU-side do gate destrutivo de certificacao de BlockDevice; o DMA real ocorre dentro do driver AHCI ja migrado;
- `kernel/src/storage/foundation_probe.sotlas` preserva `dma_alloc_for_device(...)` deliberadamente como prova direta do backend constrained e nao como caminho normal de driver;
- buffers GPT/FAT32 e outros callers de `dma_alloc(...)` em `kernel/src/storage/` sao memoria interna de storage, nao contratos DMA por dispositivo;
- `dma_alloc_for_constraints(...)` continua delegando exatamente uma vez ao backend existente `dma_alloc_for_device(...)`.

Quando os sete gates deste fechamento estiverem verdes no mesmo SHA, DF-8 pode ser promovido a **CERTIFIED** e o proximo macrobloco passa a ser **DF-9 — MMIO Mapping API**.


### Correction-only HID — recovery de reenumeracao FAILED

**CERTIFIED.** Baseline `2818f21ac0c4673a0eab201744ba123294b19734`.

A validacao de fechamento do DF-8 expôs uma lacuna preexistente no segundo ciclo real de hotplug: uma falha transitória depois de Enable Slot podia deixar o slot em `FAILED` indefinidamente. O recovery já neutralizava mailbox e estados lógicos, mas preservava owners físicos e Device Table entry.

Este correction-only fecha, depois de Command Completion de Disable Slot:

```text
FAILED exact slot+epoch
-> block reuse guard
-> release HID Report Descriptor DMA
-> release HID Report DMA
-> release HID Transfer Ring
-> clear failed slot alias
-> clear DCBAA + release Device/Input/EP0 context arena
-> device_table_release
-> release reuse guard
```

Nenhum timeout, marker ou criterio do workflow HID foi relaxado. O DF-8 permanece VALIDATING ate os sete gates fecharem verdes no mesmo SHA corretivo.


## DF-9a — Typed MMIO range/policy contract

**CERTIFIED.** Baseline `5228d4b05da295e0e9f96958a2caa45d85b7768f`.

Primeiro microcorte do MMIO Mapping API:

- adiciona `MmioMapping` com base física original, tamanho, page base, page count e cache policy;
- políticas tipadas: `UC`, `WC`, `WT`, `WB`;
- somente `UC` é suportado neste corte e delega página a página ao backend certificado `active_page_tables_map_mmio_identity_4k()`;
- `WC`, `WT` e `WB` existem no contrato, mas falham fechado até backends explícitos;
- nenhum driver, APIC, ECAM, AML ou framebuffer é migrado neste corte;
- intervalos com overflow, tamanho zero, endereço zero ou política inválida falham fechado.


## DF-9b — MMIO ownership/claim integration

**CERTIFIED.** Baseline `5b39f1e0cc3b0b90f404b736ce1bff2f34b95600`.

Este microcorte nao cria um registry paralelo. Ele liga o contrato `MmioMapping`
ao Resource Manager certificado:

- claim usa `RESOURCE_KIND_MMIO`;
- o range reivindicado cobre paginas inteiras (`page_base + page_count * 4096`),
  evitando dois owners com aliases na mesma pagina;
- `resource_claim()` ocorre antes de qualquer mapeamento;
- falha em `mmio_map_identity()` executa rollback por
  `resource_release(resource, device, driver)`;
- release de claim e generation/owner-safe pelo Resource Manager;
- release nao remove PTE identity neste corte, pois o backend atual nao tem
  ownership de VA/unmap seguro para MMIO compartilhado;
- nenhum driver e migrado no DF-9b.


## DF-9c1 — Cache-policy backend capability model

**CERTIFIED.** Baseline `2a9a3b51f03667c6cd4a8eaf017af33462ca0b8d`.

Este microcorte separa a politica solicitada do backend realmente utilizavel:

- `UC` -> `MMIO_BACKEND_IDENTITY_UC`, backend generico suportado;
- `WC` -> `MMIO_BACKEND_FRAMEBUFFER_WC`, reconhecido como backend dedicado existente,
  mas deliberadamente nao aceito pelo mapper MMIO generico;
- `WT` e `WB` -> `MMIO_BACKEND_NONE`, fail-closed;
- `mmio_generic_mapping_supported()` aceita somente o backend UC generico;
- nenhum driver muda e nenhum BAR passa a usar WC por inferencia;
- a proxima etapa de WC generico exige rollback atomico de PTE antes de poder ser
  exposta ao contrato MMIO geral.


## DF-9c2 — WC preflight / UC restore primitives

**CERTIFIED.** Baseline `ef393bc2bf0f86eec0341c46510ae14632d60dd2`.

Este corte ainda nao expõe WC ao mapper generico. Ele adiciona somente as
primitivas necessárias para uma promoção futura com rollback:

- preflight exige cada página como identity mapping, RW, NX, supervisor-only e
  seleção UC atual `PWT|PCD` (PAT index 3);
- validação de range é overflow-safe e serializada pelo lock das active page tables;
- restauração UC recompõe explicitamente a seleção PAT UC e publica TLB shootdown
  página a página;
- `__dma_fence()` fecha a restauração;
- nenhum driver ou caller MMIO passa a usar WC neste microcorte.


## DF-9c3 — Generic WC promotion with rollback

**CERTIFIED.** Baseline `6ee39eeef5e097a376e6da7a82615caf06b0ec5a`.

Primeiro backend WC generico, ainda sem migracao de drivers:

- todo range e inicialmente materializado pelo backend UC identity certificado;
- promocao WC faz preflight de todas as paginas sob o mesmo lock;
- `__pat_install_wc()` precisa confirmar PAT antes da primeira mutacao;
- cada PTE e promovida para PAT index 7 (`0x98`) e publicada por TLB shootdown;
- qualquer falha tenta normalizar o range inteiro novamente para UC antes de retornar;
- o mapper aceita agora UC e WC; WT/WB continuam fail-closed;
- nenhum driver usa WC via esta API neste microcorte.


## DF-9c4 — Runtime PAT capability probe

**CERTIFIED.** Baseline `a934e77ff9406f3321fbcdda6e898194c21aa162`.

Este microcorte prova capacidades PAT sem alterar mappings:

- preserva `arch/x86_64/pat.sotlas` como helper puro de bits PTE;
- novo modulo separado le `IA32_PAT` via `x86_read_msr(0x277)`;
- tipos UC/WC/WT/WB sao identificados pelo valor real das oito entradas PAT;
- nenhum indice PAT e presumido/hardcoded para WT ou WB;
- a busca falha fechado com `MMIO_PAT_INDEX_INVALID` quando o tipo nao existe;
- nenhuma PTE, driver ou BAR e modificado neste corte.


## DF-9c5 — Generic WT/WB PAT-index backends

**CERTIFIED.** Baseline `4153471441d9a27ce69c142e9fe8c8b3d10bff7f`.

Este corte fecha o modelo de cache policy sem presumir indices PAT:

- UC continua usando o backend identity conservador existente;
- WC continua usando o backend certificado que instala/confirma WC antes da promocao;
- WT e WB consultam `IA32_PAT` em runtime e somente prosseguem se o tipo existir;
- a primitiva generica recebe o indice PAT real, codifica PTE via
  `x86_pat_pte_bits()` e verifica a selecao escrita;
- qualquer falha de promocao normaliza o range novamente para UC;
- nenhum driver foi migrado e nenhum caller passa a solicitar WT/WB neste corte.


## DF-9d1 — PCI ECAM typed UC mapping migration

**CERTIFIED.** Baseline `014f9e79b9f5845edaf57bc45ab4abdf1c500099`.

Primeira migracao real de caller MMIO:

- somente `kernel/src/drivers/pci_config.sotlas` muda;
- cada pagina ECAM continua sendo mapeada individualmente e mantida no mesmo cache;
- politica permanece exatamente UC;
- o mapper tipado recebe `mmio_describe_identity(page, 4096, MMIO_CACHE_POLICY_UC)`;
- fallback CF8/CFC, lock PCI_CONFIG, extended-space policy e cache capacity permanecem inalterados;
- nenhum MSI-X, xHCI, storage, APIC, GPIO ou AML e migrado neste corte.


## DF-9d2 — MSI-X table typed UC mapping migration

**CERTIFIED.** Baseline `3f40fe1d01b3f26126c0bc22afafa2a74693fb9f`.

Segundo caller real migrado:

- somente `kernel/src/drivers/pci_msix_table.sotlas` muda no runtime;
- o footprint antigo e preservado exatamente: primeira pagina da entry e,
  somente se a entry de 16 bytes cruzar a fronteira de 4 KiB, a ultima pagina;
- cada pagina continua UC e e descrita como range tipado de 4096 bytes;
- PBA nao e mapeada neste corte;
- programacao masked, readback, rollback de entry, ownership e quarantine
  permanecem inalterados;
- `pci_msix_activation.sotlas` permanece no backend legado para o DF-9d3.


## DF-9d3 — MSI-X activation typed UC mapping migration

**CERTIFIED.** Baseline `9447be5884e2cfb2b14e631d2bbeb8124c34018a`.

Terceiro caller real migrado:

- somente `kernel/src/drivers/pci_msix_activation.sotlas` muda no runtime;
- o footprint antigo e preservado exatamente: primeira pagina da entry e,
  somente em straddle dos 16 bytes, a ultima pagina;
- cada pagina permanece UC e usa range tipado de 4096 bytes;
- ordem global-mask -> entry-unmask -> function-unmask, teardown, rollback,
  ownership e quarantine permanecem inalterados;
- nenhum PBA, xHCI, storage, APIC, GPIO, I2C ou AML e migrado neste corte.


## DF-9d4 — xHCI controller typed UC mapping migration

**CERTIFIED.** Baseline `aa2f6d2cf7cf6f2453fb00894c766628e990992d`.

Quarto caller real migrado:

- somente `kernel/src/drivers/xhci_controller.sotlas` muda no runtime;
- o helper continua arredondando cada endereco para exatamente uma pagina de 4096 bytes;
- politica permanece UC;
- capability, operational registers e USB Legacy handoff continuam usando o mesmo
  helper e a mesma ordem de mapping antes de acesso MMIO;
- Memory Space enable, reset HCRST, CNR/HCHalted polling e Bus Master off
  permanecem inalterados;
- demais helpers xHCI continuam no backend legado para microcortes posteriores.


## DF-9d5 — xHCI PORTSC typed UC mapping migration

**IMPLEMENTED / VALIDATING.**

Quinto caller real migrado:

- somente `kernel/src/drivers/xhci_port.sotlas` muda no runtime;
- `xhci_port_map()` continua arredondando o registrador para exatamente uma
  pagina de 4096 bytes;
- politica permanece UC;
- `xhci_port_scan()` continua read-only: mapeia antes de ler PORTSC e nao
  escreve registradores de porta;
- inventario, contagem de portas conectadas, speed id e iteracao bounded
  permanecem inalterados;
- demais helpers xHCI continuam no backend legado para microcortes posteriores.
