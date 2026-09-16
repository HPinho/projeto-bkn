# Baken OS — Kernel Driver Foundation Handoff Appendix

Atualizado em 2026-09-16 (America/Fortaleza).

Appendix **aditivo** para retomada tecnica da Driver Foundation. Nao remove nem reescreve o historico de `KERNEL_HANDOFF.md` ou `KERNEL_HANDOFF_APPENDIX.md`.

## 1. Invariantes de retomada

O Baken OS ja atingiu boot em notebook real. Preservar:

- ExitBootServices + zero UEFI pos-cutover;
- CR3 proprio, PMM/VMM/DMA e W^X;
- ACPI/APIC/IRQ/timer bare-metal;
- xHCI/HID e AHCI/NVMe/storage existentes;
- PAT/framebuffer WC;
- Generic IRQ Registry como unico allocator/registry de vetores dinamicos;
- dispatcher x86 como unico caminho de dispatch dinamico e LAPIC EOI;
- Device/Driver/Resource ownership generation-safe;
- correction-only sobre qualquer SHA vermelho.

## 2. Modelo de certificacao

```text
PLANNED -> IMPLEMENTED -> VALIDATING -> CERTIFIED
                           |
                           +-> FAILED -> correction-only -> VALIDATING
```

Seis gates sao obrigatorios para novos candidatos da Driver Foundation:

1. CI/CD + QEMU
2. SMP Bring-up
3. NVMe-only Bare-Metal
4. HID Dual-device
5. SMP Fault Diagnostic
6. MSI EDU Runtime

Nunca promover um resultado de outro SHA.

## 3. Baseline funcional certificada

```text
a34434aad5c1a795cdac70458efe26adb8b3a50a
feat(pci): add read-only MSI-X capability model
```

Gates no mesmo SHA:

```text
CI/CD + QEMU          #1297  PASS
SMP Bring-up           #400  PASS
NVMe-only              #497  PASS
HID Dual-device        #156  PASS
SMP Fault Diagnostic    #62  PASS
MSI EDU Runtime          #2  PASS
```

Esta e a baseline funcional a usar se o candidato DF-7b falhar.

## 4. DF-6 — MSI — fechado e certificado

Sequencia relevante:

```text
4de09d94ab3681dd6d02da5cdec63fcade942586  DF-6a read-only MSI model
27a7ea6253c909617b7687532b5afea55f9f81e1  DF-6b fail-closed reservation/quarantine
241e791aaec1bbd2fa3da71b89c91b5bd450340d  DF-6c transactional programming
6276f1f64f4554d74ff40510e1455ed82eae19a6  DF-6c linker-symbol correction
e75ec472f359acaf2ce3b626566ca79dc5a26f48  DF-6d1 fail-closed teardown
b6cf5725439d946d017f6cd23e2ff14970d85a6b  DF-6d2 QEMU EDU runtime proof
```

DF-6d2 gates:

```text
CI #1296 / SMP #399 / NVMe #496 / HID #155 / Fault #61 / MSI EDU #1
```

Todos PASS no mesmo SHA.

### Lifecycle MSI que nao pode ser quebrado

```text
BINDING
  capability read-only
  -> source claim exclusivo por BDF
  -> IrqHandle
  -> provar MSI Enable = 0
  -> NAO armar hardware

ACTIVE
  -> snapshot
  -> Address/Data
  -> readback/revalidacao
  -> Enable somente por ultimo

UNBINDING
  -> source OFF primeiro
  -> prova de MSI Enable = 0
  -> restauracao segura
  -> IRQ release
  -> source release
```

Qualquer incerteza preserva ownership em quarentena.

## 5. DF-7a — MSI-X capability model — certificado

Arquivo:

```text
kernel/src/drivers/pci_msix_capability.sotlas
```

Contrato:

- capability ID 0x11 via walker bounded DF-5c;
- control/Table/PBA somente no config space;
- Table Size 1..2048;
- Table/PBA BIR somente 0..5;
- Table bytes = entries * 16;
- PBA bytes = ceil(entries / 64) * 8;
- overflow/bounds checks;
- releitura integral antes de publicar;
- nenhuma escrita/config/MMIO/IRQ/runtime call.

Checkpoint:

```text
a34434aad5c1a795cdac70458efe26adb8b3a50a
```

## 6. Inventario BAR/bridge relevante para DF-7b

`pci_bus.sotlas` mantem enumeracao global read-only. `PciBar.size` pode permanecer 0; nao inferir tamanho de BAR a partir disso e nao adicionar sizing destrutivo ao scan global.

`pci_device_bridge.sotlas` ja possui:

```text
PciBarClaim.logical
  RESOURCE_KIND_PCI_BAR
  start = packed BDF
  length = 1
  auxiliary = BAR index

PciBarClaim.physical
  RESOURCE_KIND_MMIO ou IO_PORT
  start = BAR base
  length = extensao explicitamente reivindicada pelo driver
```

`pci_claim_bar()` e a autoridade de ownership. DF-7b nao deve criar segundo ownership model.

## 7. DF-7b — candidato atual

Novo modulo:

```text
kernel/src/drivers/pci_msix_layout.sotlas
```

Nova API:

```text
pci_msix_layout_probe(
    DeviceHandle,
    DriverHandle,
    table_claim: PciBarClaim,
    pba_claim: PciBarClaim
) -> PciMsixLayout
```

### Objetivo

Converter o snapshot DF-7a em janelas fisicas provadas, mas somente quando Table/PBA cabem em BAR claim(s) MMIO ja pertencentes ao mesmo Device/Driver.

### Ordem da prova

```text
Device Core snapshot BINDING/ACTIVE
-> segmento 0
-> DF-7a capability snapshot
-> validar logical BAR claim da Table
-> validar physical MMIO claim da Table
-> validar BAR atual + containment
-> repetir para PBA
-> se mesmo BIR: mesmos ResourceHandles
-> reler Device Core
-> reler DF-7a capability
-> reler ResourceClaims/BARs
-> publicar PciMsixLayout
```

### BAR sanity

O helper local caminha BAR0..BAR5 sem escrever config space:

- rejeita I/O BAR como backing de MSI-X;
- aceita Memory BAR tipo 32-bit ou 64-bit;
- rejeita tipos reservados;
- pula o dword alto de BAR 64-bit, portanto BIR nao pode apontar para upper half;
- rejeita BAR5 que anuncie 64-bit sem BAR6;
- exige base atual nao zero;
- exige base atual = `physical.request.start`.

### Bounds

Containment usa subtracao para evitar overflow:

```text
offset <= physical.length
bytes <= physical.length - offset
```

Depois calcula `physical.start + offset` e ainda verifica wraparound.

### Fora do escopo DF-7b

Proibido neste corte:

- `pci_claim_bar()` / `resource_claim()`;
- `resource_release()`;
- MMIO mapping;
- read/write da MSI-X Table/PBA;
- IRQ reserve/release;
- config writes;
- MSI-X Enable/Function Mask;
- Memory Space/Bus Master;
- INTx policy;
- LAPIC/IOAPIC/IDT/EOI;
- chamada no boot/runtime.

## 8. Se DF-7b falhar

Nao iniciar DF-7c. Fazer somente:

```text
falha de teste estrutural -> corrigir contrato/teste real
falha Sotlas frontend/link -> corrigir modulo sem expandir escopo
falha native build -> corrigir lowering/simbolo estritamente necessario
falha QEMU/SMP/NVMe/HID/Fault/MSI EDU -> tratar como regressao ate prova contraria
```

Criar novo SHA corretivo e exigir novamente os seis gates no mesmo SHA.

## 9. Depois de DF-7b certificado

Proximo microcorte: **DF-7c source/vector ownership**.

Diretrizes:

- nao criar allocator de vetor paralelo;
- Generic IRQ Registry continua autoridade de vetores;
- ownership da fonte MSI-X precisa ser generation-safe e fail-closed;
- reservar antes de programar;
- nao habilitar entradas MSI-X durante BINDING;
- Table/PBA continuam sem escrita ate ownership estar certificado;
- se for necessario novo `RESOURCE_KIND`, justificar conflito/lifecycle antes de adicionar;
- separar ownership, programacao, ativacao e teardown em cortes distintos.

## 10. Regra de retomada em novo chat

Sempre conferir:

```text
1. main HEAD
2. baseline funcional certificada
3. candidato atual
4. diff exato candidato vs baseline
5. seis workflow runs do SHA candidato
6. somente entao decidir correction-only ou proximo microcorte
```

Nao usar o HEAD documental como prova funcional se ele nao tiver os gates correspondentes; registrar baseline funcional separadamente.
