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
DF-8   DMA Device API                              IN PROGRESS
  DF-8a read-only device constraints model         CERTIFIED
  DF-8b typed constrained allocation               CERTIFIED
  DF-8c per-device integration / NVMe first        IMPLEMENTED / VALIDATING
DF-9   MMIO Mapping API                            PLANNED
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

**IMPLEMENTED / VALIDATING.**

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

**IMPLEMENTED / VALIDATING.**

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
