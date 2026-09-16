# Baken OS — Driver Foundation Status

Atualizado em 2026-09-16 (America/Fortaleza).

Este arquivo e o checkpoint operacional curto da Driver Foundation. O historico detalhado permanece preservado em `BAKEN_OS_ROADMAP.md`, `KERNEL_HANDOFF.md`, `KERNEL_HANDOFF_APPENDIX.md` e nos appendices especificos da Driver Foundation.

## Regra de seguranca da plataforma

O Baken OS ja atingiu boot em notebook real. A Driver Foundation deve preservar como invariantes:

- zero dependencia de firmware UEFI depois do cutover;
- CR3, PMM/VMM/DMA, ACPI/APIC/IRQ, xHCI/HID e storage bare-metal permanecem ownership do kernel;
- nenhum microcorte de driver redesenha boot, allocator, interrupt core ou page tables sem necessidade provada;
- Generic IRQ Registry permanece a unica autoridade de vetores dinamicos;
- EOI permanece centralizado no dispatcher x86 existente;
- PCI/MSI/MSI-X evoluem em microcortes pequenos, fail-closed e reversiveis;
- nao empilhar funcionalidade sobre SHA candidato vermelho;
- feature so vira `CERTIFIED` depois de todos os gates obrigatorios no mesmo SHA.

## Estados formais

```text
PLANNED -> IMPLEMENTED -> VALIDATING -> CERTIFIED
                           |
                           +-> FAILED -> correction-only -> VALIDATING
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

Gates no mesmo SHA: CI #1296, SMP #399, NVMe #496, HID #155, Fault #61 e MSI EDU #1, todos PASS. O gate MSI EDU compilou o kernel Sotlas instrumentado, executou QEMU EDU, observou `BAKEN:PCI_MSI_EDU_READY`, nao observou excecao de CPU e terminou com `stop_reason=complete`.

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
  DF-7c source/vector ownership                    PLANNED
  DF-7d masked table-entry programming             PLANNED
  DF-7e activation/teardown/runtime proof          PLANNED
```

## DF-6 — MSI convencional — fechado

O caminho certificado separa deliberadamente reserva, armamento e teardown:

```text
BINDING
  -> capability MSI read-only
  -> ownership logico exclusivo da fonte por BDF
  -> IrqHandle no Generic IRQ Registry
  -> MSI Enable comprovadamente 0

ACTIVE
  -> programacao single-vector transacional
  -> Message Address/Data com readback
  -> MSI Enable somente por ultimo

UNBINDING
  -> desabilitar fonte primeiro
  -> provar MSI Enable = 0
  -> restaurar snapshot quando aplicavel
  -> liberar IRQ
  -> liberar ownership logico da fonte
```

Qualquer incerteza de quiescencia/rollback preserva ownership em estado fail-closed; nenhum vetor pode voltar ao pool enquanto a fonte puder continuar ativa.

## DF-7a — MSI-X capability model — certificado

`kernel/src/drivers/pci_msix_capability.sotlas` interpreta somente a capability convencional MSI-X `0x11` no config space.

O modelo certificado:

- interpreta Message Control, Table Size, MSI-X Enable e Function Mask;
- aceita no maximo 2048 entradas;
- interpreta BIR + offset de Table e PBA;
- aceita somente BAR0..BAR5;
- calcula Table span como `entries * 16` bytes;
- calcula PBA span como `ceil(entries / 64) * 8` bytes;
- faz bounds/overflow checks;
- relê header/control/Table/PBA antes de publicar o snapshot;
- nao mapeia nem acessa MMIO;
- nao reserva IRQ;
- nao altera MSI-X, INTx, Memory Space ou Bus Master;
- nao introduz chamada no boot.

## DF-7b — BAR-backed Table/PBA layout proof — candidato

O DF-7b nao executa sizing destrutivo de BAR. A enumeracao global continua read-only e `PciBar.size == 0` permanece valido quando o tamanho nao foi medido.

A autoridade para provar os limites de Table/PBA passa a ser o `PciBarClaim` ja pertencente ao driver:

```text
PciBarClaim.logical
  -> RESOURCE_KIND_PCI_BAR
  -> owner Device/Driver
  -> BDF + BAR index

PciBarClaim.physical
  -> RESOURCE_KIND_MMIO
  -> BAR base + length efetivamente reivindicado
```

`pci_msix_layout_probe()` somente publica um layout quando:

- Device/Driver ainda coincidem e o Device Core esta BINDING ou ACTIVE;
- o BDF pertence ao segmento 0, coerente com o bridge PCI atual;
- DF-7a ainda publica exatamente a mesma capability MSI-X;
- BIR da Table/PBA coincide com os claims fornecidos;
- o claim logico prova `(BDF,BAR)` e o claim fisico prova MMIO do mesmo owner;
- o BAR atual ainda possui a mesma base do claim;
- BIR nunca aponta para I/O BAR, tipo reservado ou dword alto de BAR 64-bit;
- `offset + span` cabe integralmente no comprimento do claim MMIO sem overflow;
- quando Table e PBA usam o mesmo BIR, ambos recebem o mesmo claim generation-safe;
- lifecycle, capability, claims e BARs sao revalidados antes da publicacao final.

O DF-7b nao pode:

- chamar `pci_claim_bar()` ou `resource_claim()`;
- mapear, ler ou escrever Table/PBA MMIO;
- reservar/liberar IRQ;
- escrever PCI config space;
- alterar MSI-X Enable ou Function Mask;
- habilitar Memory Space ou Bus Master;
- tocar LAPIC, IOAPIC, IDT ou EOI;
- adicionar chamada runtime/boot.

Enquanto os gates do commit que contem DF-7b nao fecharem verdes, a baseline funcional continua `a34434aad5c1a795cdac70458efe26adb8b3a50a`.

## Continuacao bloqueada ate certificacao do DF-7b

Somente depois dos seis gates no mesmo SHA:

1. promover DF-7b a `CERTIFIED`;
2. manter o layout read-only separado de ownership/programacao;
3. desenhar DF-7c sem criar allocator de vetor paralelo;
4. reutilizar Generic IRQ Registry para cada vetor MSI-X suportado;
5. manter Table/PBA sem escrita ate ownership de fonte/vetores estar provado;
6. manter INTx, Memory Space e Bus Master como politicas explicitas e separadas;
7. exigir teardown source-off antes de qualquer devolucao de vetor;
8. criar prova runtime dedicada antes de fechar DF-7.

## Regra de retomada

```text
main HEAD
-> functional baseline certificada
-> candidate SHA
-> seis gates do candidate
-> correction-only se qualquer gate falhar
-> somente entao escolher o proximo microcorte
```

Documentacao complementar atual:

- `BAKEN_OS_DRIVER_FOUNDATION_ROADMAP_APPENDIX.md`
- `KERNEL_DRIVER_FOUNDATION_HANDOFF_APPENDIX.md`
