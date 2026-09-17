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

No mesmo SHA passaram:

- CI/CD + Automated QEMU #1321;
- SMP Bring-up #424;
- NVMe-only Bare-Metal #521;
- HID Dual-device #180;
- SMP Fault Diagnostic #86;
- MSI EDU Runtime #26;
- MSI-X ivshmem Runtime #13.

Esse checkpoint fecha a macroetapa DF-7 com entrega MSI-X real em QEMU `ivshmem-doorbell`, teardown fail-closed e guard estrutural do caminho de BAR sizing.

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
  DF-8a read-only device constraints model         IMPLEMENTED / VALIDATING
DF-9   MMIO Mapping API                            PLANNED
DF-10  Bus Model                                   PLANNED
DF-11  Class Registries                            PLANNED
```

## DF-8 — DMA Device API

Objetivo da macroetapa: representar e aplicar constraints DMA por dispositivo sem substituir o allocator fisico existente e sem criar caminhos paralelos ao PMM/VMM/DMA ja certificados.

### DF-8a — read-only device constraints model

Candidato atual:

```text
84cd12125940d8b2517d742b3ea63bdb17c6ccd4
feat(dma): add DF-8a device constraint model
```

O microcorte adiciona `DmaDeviceConstraints` em `kernel/src/memory/dma.sotlas` com apenas os limites que o allocator existente ja entende:

```text
alignment
max_address
boundary
```

Contratos:

- `dma_device_constraints(...)` valida alignment, address ceiling e boundary;
- `dma_device_constraints_valid(...)` revalida o objeto antes de consumo;
- `dma_buffer_satisfies_device_constraints(...)` e estritamente read-only e verifica alignment fisico, overflow do ultimo byte, teto de endereco e cruzamento de boundary;
- nenhuma API DF-8a aloca/libera pagina, muda owner/fence, mapeia MMIO ou chama firmware;
- `dma_alloc_for_device(size, alignment, max_address, boundary)` permanece intocado e continua chamando diretamente `pmm_alloc_pages_constrained(...)`;
- xHCI/HID, NVMe, AHCI e storage nao sao migrados neste corte.

Guardrails foram adicionados a `tests/test_dma_contract.py` para impedir que o modelo read-only vire allocator ou altere ownership por acidente.

DF-8a permanece `IMPLEMENTED / VALIDATING` ate os gates do head final passarem no mesmo SHA.

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

## Proximos microcortes, somente apos DF-8a certificado

```text
DF-8b typed constrained allocation
-> consumir DmaDeviceConstraints sem duplicar allocator
-> manter pmm_alloc_pages_constrained como backend unico
-> nenhuma migracao de driver ainda

DF-8c per-device integration
-> migracao incremental de callers reais
-> um subsistema por vez
-> runtime proof + regressao dos gates existentes
```

A escolha exata do primeiro caller de DF-8c deve ser feita somente depois de DF-8b certificado e de auditoria dos requisitos reais de cada dispositivo.

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
