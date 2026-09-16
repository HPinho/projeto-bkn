# Baken OS — Driver Foundation Status

Atualizado em 2026-09-16 (America/Fortaleza).

Este arquivo e o checkpoint operacional curto da Driver Foundation. O historico detalhado permanece preservado em `BAKEN_OS_ROADMAP.md`, `KERNEL_HANDOFF.md`, `KERNEL_HANDOFF_APPENDIX.md` e nos appendices especificos da Driver Foundation.

## Regra de seguranca da plataforma

O Baken OS ja atingiu boot em notebook real. A Driver Foundation deve preservar como invariantes:

- zero dependencia de firmware UEFI depois do cutover;
- CR3, PMM/VMM/DMA, ACPI/APIC/IRQ, xHCI/HID e storage bare-metal permanecem ownership do kernel;
- nenhum microcorte redesenha boot, allocator, interrupt core ou page tables sem necessidade provada;
- Generic IRQ Registry permanece a unica autoridade de vetores dinamicos;
- EOI permanece centralizado no dispatcher x86 existente;
- PCI/MSI/MSI-X evoluem em microcortes pequenos, fail-closed e reversiveis;
- nao empilhar funcionalidade sobre SHA candidato vermelho ou superseded por auditoria;
- feature so vira `CERTIFIED` depois dos seis gates obrigatorios no mesmo SHA.

## Estados formais

```text
PLANNED -> IMPLEMENTED -> VALIDATING -> CERTIFIED
                           |
                           +-> FAILED -> correction-only -> VALIDATING
                           +-> SUPERSEDED_BY_AUDIT -> correction-only -> VALIDATING
```

`IMPLEMENTED` significa somente que o codigo existe. Nao equivale a baseline certificada.

## Baseline funcional certificada

```text
a34434aad5c1a795cdac70458efe26adb8b3a50a
feat(pci): add read-only MSI-X capability model
```

Gates no mesmo SHA:

- CI/CD + QEMU #1297: PASS
- SMP Bring-up #400: PASS
- NVMe-only Bare-Metal #497: PASS
- HID Dual-device #156: PASS
- SMP Fault Diagnostic #62: PASS
- MSI EDU Runtime #2: PASS

Essa baseline certifica o DF-7a e preserva integralmente a prova runtime de MSI convencional do DF-6.

Baseline anterior que fechou o DF-6:

```text
b6cf5725439d946d017f6cd23e2ff14970d85a6b
test(pci): add QEMU EDU MSI runtime proof
```

Gates: CI #1296, SMP #399, NVMe #496, HID #155, Fault #61 e MSI EDU #1, todos PASS. O MSI EDU observou `BAKEN:PCI_MSI_EDU_READY`, nenhuma excecao de CPU e `stop_reason=complete`.

## Driver Foundation

```text
DF-0  Architecture / contracts                    CERTIFIED
DF-1  Driver API / descriptors                     CERTIFIED
DF-2  Resource Manager                             CERTIFIED
DF-3  Device Core                                  CERTIFIED
DF-3.1 Transactional lifecycle                     CERTIFIED
DF-4  Generic IRQ Registry                         CERTIFIED
  DF-4a generation-safe registry                   CERTIFIED
  DF-4b1 x86 dynamic dispatcher                    CERTIFIED
DF-5  PCI Core v2                                  CERTIFIED
  DF-5a CF8/CFC SMP-safe                           CERTIFIED
  DF-5b ECAM/MCFG + CF8 fallback                   CERTIFIED
  DF-5c bounded capability walkers                 CERTIFIED
  DF-5d Device/Resource bridge                     CERTIFIED
DF-6  MSI                                          CERTIFIED
  DF-6a read-only capability model                 CERTIFIED
  DF-6b source ownership + IRQ reservation         CERTIFIED
  DF-6c transactional single-vector programming    CERTIFIED
  DF-6d1 fail-closed disable/teardown               CERTIFIED
  DF-6d2 QEMU EDU runtime proof                    CERTIFIED
DF-7  MSI-X                                        IN PROGRESS
  DF-7a read-only capability model                 CERTIFIED
  DF-7b BAR-backed Table/PBA layout proof          IMPLEMENTED / VALIDATING
  DF-7b1 controlled quiescent BAR sizing           PLANNED
  DF-7c source/vector ownership                    BLOCKED BY DF-7b/DF-7b1
  DF-7d masked table-entry programming             PLANNED
  DF-7e activation/teardown/runtime proof          PLANNED
```

## DF-7a — MSI-X capability model — certificado

`kernel/src/drivers/pci_msix_capability.sotlas` interpreta somente a capability MSI-X `0x11` no config space:

- Message Control, Table Size, Enable e Function Mask;
- BIR/offset de Table e PBA;
- Table Size de 1..2048;
- Table span `entries * 16`;
- PBA span `ceil(entries / 64) * 8`;
- overflow/bounds checks;
- releitura integral antes de publicar;
- zero MMIO/IRQ/config write/runtime call.

## DF-7b — layout Table/PBA contra BAR — correction-only

O primeiro candidato DF-7b:

```text
e6bbc3bf1b3b85545a4cedca63b191dc08ce8e7c
feat(pci): bind MSI-X windows to BAR ownership
```

foi **superseded antes de certificacao por auditoria**, independentemente do resultado eventual dos gates.

### Motivo da auditoria

`pci_probe_bar()` mantem a enumeracao global estritamente read-only e inicializa `PciBar.size = 0`. `pci_claim_bar()` aceita o `length` fornecido pelo driver quando `known_size == 0`.

Portanto:

```text
PciBarClaim.physical.length
!= prova automatica da aperture real do BAR
```

Um caller poderia reivindicar um extent maior que a aperture fisica quando o tamanho ainda fosse desconhecido. O DF-7b nao pode usar esse valor sozinho para declarar Table/PBA seguras.

### Contrato corrigido do DF-7b

O correction-only atual mantem o corte passivo, mas agora `pci_msix_layout_probe()` somente publica quando:

- o inventario PCI contem `PciBar.size > 0` para o mesmo BDF/BIR;
- o BAR atual continua Memory BAR valido, 32 ou 64-bit, com a mesma base;
- `PciBarClaim.logical` prova owner + BDF + BAR index;
- `PciBarClaim.physical` e MMIO do mesmo owner;
- `physical.start == BAR.base`;
- `physical.length == PciBar.size` **exatamente**;
- Table/PBA cabem em `PciBar.size`, nao em um extent escolhido pelo caller;
- mesmo BIR para Table/PBA exige os mesmos ResourceHandles generation-safe;
- lifecycle, capability, claims, BAR base e BAR size sao revalidados antes da publicacao.

Enquanto `PciBar.size == 0`, o DF-7b deve falhar fechado. Isso e intencional.

O DF-7b continua proibido de:

- executar BAR sizing;
- escrever PCI config space;
- chamar `pci_claim_bar()`/`resource_claim()`/`resource_release()`;
- mapear/ler/escrever MSI-X Table/PBA;
- reservar/liberar IRQ;
- alterar MSI-X Enable/Function Mask;
- habilitar Memory Space/Bus Master;
- tocar LAPIC/IOAPIC/IDT/EOI;
- entrar no boot/runtime.

## DF-7b1 — controlled quiescent BAR sizing — proximo pre-requisito

A aperture real devera ser medida em microcorte separado. Requisitos de desenho antes de qualquer implementacao:

- nunca inserir sizing destrutivo no scan global;
- somente device ownership generation-safe;
- exigir dispositivo quiescente e lifecycle apropriado;
- snapshot completo de Command + BAR low/high;
- nenhuma medicao enquanto DMA/Bus Master puder estar ativo;
- decode Memory/I/O tratado de forma explicita e restaurado exatamente;
- BAR 64-bit tratado atomica/transacionalmente como par low/high;
- write-all-ones/read-mask/restore com readback de restauracao;
- qualquer incerteza = falha fechada, sem publicar size;
- `PciBar.size` so recebe valor depois de restauracao comprovada;
- nenhum MSI-X MMIO e programado neste microcorte.

DF-7c permanece bloqueado ate DF-7b estar certificado e existir caminho seguro para obter `PciBar.size` quando necessario.

## Gates obrigatorios

Para todo candidato funcional da Driver Foundation:

```text
1. CI/CD + QEMU
2. SMP Bring-up
3. NVMe-only Bare-Metal
4. HID Dual-device
5. SMP Fault Diagnostic
6. MSI EDU Runtime
```

O candidato correction-only que contem este status deve fechar os seis gates no mesmo SHA antes de qualquer promocao.

## Regra de retomada

```text
main HEAD
-> functional baseline certificada
-> candidate SHA
-> auditorias conhecidas do candidate
-> seis gates do candidate
-> correction-only se qualquer gate falhar OU auditoria invalidar a garantia
-> somente entao escolher o proximo microcorte
```

Documentacao complementar:

- `BAKEN_OS_DRIVER_FOUNDATION_ROADMAP_APPENDIX.md`
- `KERNEL_DRIVER_FOUNDATION_HANDOFF_APPENDIX.md`
