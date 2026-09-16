# Baken OS — Driver Foundation Status

Atualizado em 2026-09-16 (America/Fortaleza).

Este arquivo e o checkpoint operacional curto da Driver Foundation. Ele nao apaga o historico de `BAKEN_OS_ROADMAP.md`, `KERNEL_HANDOFF.md` ou `KERNEL_HANDOFF_APPENDIX.md`; quando esses documentos estiverem temporalmente atrasados, este status deve ser usado para retomar a trilha de drivers ate a reconciliacao documental seguinte.

## Regra de seguranca da plataforma

O Baken OS ja atingiu boot em notebook real. A partir deste ponto, qualquer incremento da Driver Foundation deve preservar como invariantes:

- zero dependencia de firmware UEFI depois do cutover;
- CR3, PMM/VMM/DMA, ACPI/APIC/IRQ e storage bare-metal existentes permanecem ownership do kernel;
- nenhum microcorte de driver pode redesenhar boot, allocator, interrupt core ou page tables sem necessidade explicitamente provada;
- mudancas em PCI/MSI devem ser pequenas, fail-closed e reversiveis;
- nao empilhar funcionalidade sobre SHA candidato vermelho;
- feature so vira `CERTIFIED` depois dos gates obrigatorios no mesmo SHA.

## Estados formais

```text
PLANNED -> IMPLEMENTED -> VALIDATING -> CERTIFIED
                           |
                           +-> FAILED -> correction-only -> VALIDATING
```

`IMPLEMENTED` significa somente que o codigo existe. Nao equivale a baseline certificada.

## Baseline funcional certificada

```text
5e03f98eb17abf2c2328b1b1dd8de37132c57665
feat(pci): bridge devices into driver foundation
```

Gates desse mesmo SHA:

- CI/CD + QEMU #1287: PASS
- SMP Bring-up #390: PASS
- NVMe-only Bare-Metal #487: PASS
- HID Dual-device #146: PASS
- SMP Fault Diagnostic #52: PASS

Essa baseline fecha o PCI Core v2 sem MSI/MSI-X programados.

## Driver Foundation

```text
DF-0  Architecture / contracts              CERTIFIED
DF-1  Driver API / descriptors               CERTIFIED
DF-2  Resource Manager                       CERTIFIED
DF-3  Device Core                            CERTIFIED
DF-3.1 Transactional lifecycle               CERTIFIED
DF-4  Generic IRQ Registry                   CERTIFIED
  DF-4a generation-safe registry             CERTIFIED
  DF-4b1 x86 dynamic dispatcher              CERTIFIED
DF-5  PCI Core v2                            CERTIFIED
  DF-5a CF8/CFC SMP-safe                     CERTIFIED
  DF-5b ECAM/MCFG + CF8 fallback             CERTIFIED
  DF-5c bounded capability walkers           CERTIFIED
  DF-5d Device/Resource bridge               CERTIFIED
DF-6  MSI                                    IN PROGRESS
  DF-6a read-only MSI capability model       IMPLEMENTED / VALIDATING
  DF-6b vector + ownership bridge            PLANNED
  DF-6c transactional MSI programming        PLANNED
  DF-6d disable/teardown + runtime proof     PLANNED
DF-7  MSI-X                                  PLANNED
```

## DF-6a — escopo deliberadamente nao invasivo

O DF-6a apenas interpreta a capability convencional MSI `0x05` sobre o walker bounded do DF-5c.

Ele pode:

- validar Message Control;
- distinguir layout MSI 32-bit e 64-bit;
- identificar Per-Vector Masking;
- validar MMC/MME e expor 1/2/4/8/16/32 mensagens;
- calcular offsets de Message Address/Data/Mask/Pending sem ultrapassar `0xFF`;
- falhar fechado se BDF/capability mudar entre leituras.

Ele nao pode:

- escrever PCI config space;
- reservar vetor;
- registrar handler;
- programar Message Address ou Message Data;
- alterar MSI Enable ou Multiple Message Enable;
- desabilitar INTx;
- tocar LAPIC, IOAPIC, IDT ou EOI;
- habilitar Memory Space ou Bus Master;
- introduzir chamada nova no caminho de boot.

## Sequencia de continuacao

Somente se o SHA do DF-6a fechar os gates obrigatorios:

1. marcar DF-6a `CERTIFIED`;
2. iniciar DF-6b com **single-vector MSI primeiro**;
3. integrar o ownership ao Generic IRQ Registry + Device/Driver/Resource sem duplicar o interrupt core;
4. manter Message Address/Data e MSI Enable ainda fora do DF-6b se isso puder ser separado;
5. programacao de hardware somente no DF-6c, transacionalmente, com enable por ultimo e rollback completo;
6. MSI-X continua bloqueado ate DF-6 inteiro estar certificado.

## Regra de retomada

Ao abrir um novo chat ou retomar a implementacao, conferir nesta ordem:

```text
main HEAD
-> functional baseline certificada
-> candidate SHA
-> gates do candidate
-> somente entao escolher o proximo microcorte
```
