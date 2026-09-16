# Baken OS — Driver Foundation Roadmap Appendix

Atualizado em 2026-09-16 (America/Fortaleza).

Este documento e **aditivo**. Ele nao substitui nem remove conteudo de `BAKEN_OS_ROADMAP.md`; serve para reconciliar a trilha Driver Foundation com os checkpoints mais recentes enquanto o roadmap historico preserva integralmente as etapas anteriores.

Estados usados aqui:

- `✅ CERTIFIED`: codigo + gates obrigatorios no mesmo SHA;
- `🟡 IMPLEMENTED / VALIDATING`: codigo publicado, mas ainda nao promovido a baseline;
- `⬜ PLANNED`: desenho seguinte, sem certificacao implicita.

## Posicao atual da Fase 2 — Platform/Drivers

A fundacao bare-metal e o Kernel Core permanecem congelados e certificados. A trilha ativa adicional da Fase 2 e a **Driver Foundation PCI/IRQ**, atualmente em MSI-X.

Baseline funcional certificada antes do candidato DF-7b:

```text
a34434aad5c1a795cdac70458efe26adb8b3a50a
feat(pci): add read-only MSI-X capability model
```

Gates desse SHA: CI #1297, SMP #400, NVMe #497, HID #156, Fault #62 e MSI EDU #2 — todos PASS.

## Macro-roadmap da Driver Foundation

| Etapa | Estado | Objetivo |
|---|---|---|
| DF-0 Architecture/contracts | ✅ | separar Device/Driver/Resource/IRQ ownership |
| DF-1 Driver API/descriptors | ✅ | contratos generation-safe de driver |
| DF-2 Resource Manager | ✅ | ownership transacional de recursos |
| DF-3 Device Core | ✅ | identidade/lifecycle universal |
| DF-3.1 Transactional lifecycle | ✅ | bind/unbind fail-closed |
| DF-4 Generic IRQ Registry | ✅ | unico allocator/registry de vetores dinamicos |
| DF-5 PCI Core v2 | ✅ | config core, ECAM/fallback, capabilities e bridge |
| DF-6 MSI | ✅ | MSI single-vector completo + runtime proof |
| DF-7 MSI-X | ▶️ | Table/PBA, ownership, programacao e teardown seguros |

## DF-5 — PCI Core v2 — certificado

```text
DF-5a CF8/CFC SMP-safe                  ✅
DF-5b ECAM/MCFG + CF8 fallback          ✅
DF-5c bounded capability walkers        ✅
DF-5d Device/Resource bridge            ✅
```

Invariantes que continuam valendo durante DF-7:

- nenhuma enumeracao global faz sizing destrutivo de BAR;
- `pci_claim_bar()` e o caminho de ownership `(BDF,BAR) + faixa fisica`;
- config space e acessado pelo PCI Config Core existente;
- o bridge atual publica dispositivos PCI do segmento 0;
- Memory Space e Bus Master so podem ser habilitados explicitamente por APIs estreitas.

## DF-6 — MSI convencional — certificado

```text
DF-6a read-only capability model                   ✅
DF-6b source ownership + IRQ reservation           ✅
DF-6c transactional single-vector programming      ✅
DF-6d1 fail-closed disable/teardown                 ✅
DF-6d2 QEMU EDU runtime proof                      ✅
```

Checkpoint de fechamento do runtime:

```text
b6cf5725439d946d017f6cd23e2ff14970d85a6b
test(pci): add QEMU EDU MSI runtime proof
```

Provas no mesmo SHA:

- CI #1296 ✅
- SMP #399 ✅
- NVMe #496 ✅
- HID #155 ✅
- Fault #61 ✅
- MSI EDU #1 ✅

A prova EDU exercitou entrega real de MSI e teardown source-off sem criar caminho paralelo de IRQ/EOI.

## DF-7 — MSI-X

### DF-7a — read-only capability model

**✅ CERTIFIED.**

Checkpoint:

```text
a34434aad5c1a795cdac70458efe26adb8b3a50a
feat(pci): add read-only MSI-X capability model
```

O corte interpreta somente os 12 bytes da capability MSI-X:

- capability ID `0x11`;
- Table Size de 1..2048 entradas;
- MSI-X Enable + Function Mask;
- BIR/offset de Table e PBA;
- Table span de 16 bytes por entrada;
- PBA span arredondado em grupos de 64 vetores;
- revalidacao integral antes da publicacao.

Nao ha mapping MMIO, IRQ claim, escrita PCI nem chamada no boot.

### DF-7b — BAR-backed Table/PBA layout proof

**🟡 IMPLEMENTED / VALIDATING.**

Objetivo: provar que Table/PBA apontadas pela capability realmente cabem em faixas MMIO pertencentes ao mesmo driver, **sem** fazer BAR sizing destrutivo e sem acessar Table/PBA.

Contrato pretendido:

```text
DF-7a PciMsixCapability
+ PciBarClaim ja existente para Table BIR
+ PciBarClaim ja existente para PBA BIR
+ Device/Driver ownership
-> PciMsixLayout somente se toda a prova for consistente
```

Provas obrigatorias:

- logical claim = `RESOURCE_KIND_PCI_BAR`, mesmo BDF/BIR/owner;
- physical claim = `RESOURCE_KIND_MMIO`, mesmo owner;
- base atual do BAR = `physical.start`;
- Table/PBA inteiras dentro de `physical.length`;
- rejeitar I/O BAR, tipo reservado, upper dword de 64-bit BAR e BAR5 64-bit incompleto;
- mesmo BIR para Table/PBA exige o mesmo claim generation-safe;
- revalidar lifecycle, capability, claims e BAR antes de publicar.

Explicitamente fora do corte:

- `pci_claim_bar()`/`resource_claim()` novos;
- MMIO map/read/write;
- IRQ reservation;
- MSI-X Enable/Function Mask;
- INTx policy;
- Memory Space/Bus Master;
- runtime activation.

DF-7b somente vira `CERTIFIED` depois dos seis gates no mesmo SHA.

### DF-7c — source/vector ownership

**⬜ PLANNED.**

Somente depois do DF-7b certificado. Objetivo: definir ownership generation-safe da fonte MSI-X e de vetor(es) sem criar allocator paralelo. O Generic IRQ Registry continua sendo a unica autoridade de vetores dinamicos.

Regras preliminares:

- Table/PBA layout certificado e ownership de BAR continuam pre-condicoes;
- nenhum vetor pode ser publicado sem owner Device/Driver exato;
- reservar primeiro, programar depois;
- nenhuma entrada de Table fica ativa durante BINDING;
- qualquer rollback incerto deve preservar ownership fail-closed.

### DF-7d — masked table-entry programming

**⬜ PLANNED.**

Programacao transacional de entrada(s) MSI-X somente com vetor(es) ja pertencentes ao caller. Inicio conservador: menor conjunto funcional possivel, entries mascaradas durante Address/Data/Vector Control writes, readback e rollback antes de exposicao da fonte.

Nao misturar neste corte:

- politica de INTx;
- enable global da Function;
- Bus Master;
- policy de afinidade/migracao de CPU;
- teardown final.

### DF-7e — activation, teardown e runtime proof

**⬜ PLANNED.**

Fechamento da macroetapa deve provar:

```text
ownership + layout validos
-> entry mascarada/programada
-> ativacao somente apos readback
-> entrega real
-> source/entry/function off no teardown
-> somente depois release de IRQ/BAR/source ownership
```

Uma prova runtime dedicada deve coexistir com CI, SMP, NVMe, HID, Fault e MSI EDU sem regressao das fundacoes existentes.

## Gates obrigatorios daqui em diante

Para cada candidato funcional da Driver Foundation:

```text
1. Baken OS CI/CD & Automated QEMU Verification
2. Baken OS SMP Bring-up Verification
3. Baken OS NVMe-only Bare-Metal Verification
4. Baken OS HID Dual-device Verification
5. Baken OS SMP Fault Diagnostic
6. Baken OS MSI EDU Runtime Verification
```

Se qualquer gate falhar, o candidato permanece nao certificado e o trabalho entra em `correction-only` ate voltar a verde no mesmo SHA corretivo.

## Invariantes permanentes

- UEFI termina no cutover; nenhuma dependencia nova de firmware apos ExitBootServices.
- Generic IRQ Registry = unica autoridade de vetores dinamicos.
- x86 dispatcher = unica rota dinamica de dispatch/EOI.
- BAR ownership continua no Resource Manager/PCI bridge.
- nenhum sizing destrutivo entra na enumeracao global.
- nenhum microcorte MSI-X altera boot, PMM/VMM, ACPI/APIC, xHCI/HID ou storage sem necessidade provada.
- notebook real ja bootavel e uma invariante de preservacao, nao um ambiente de experimento para atalhos arquiteturais.
