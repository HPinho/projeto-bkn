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
4de09d94ab3681dd6d02da5cdec63fcade942586
feat(pci): add read-only MSI capability model
```

Gates desse mesmo SHA:

- CI/CD + QEMU #1288: PASS
- SMP Bring-up #391: PASS
- NVMe-only Bare-Metal #488: PASS
- HID Dual-device #147: PASS
- SMP Fault Diagnostic #53: PASS

Essa baseline preserva o PCI Core v2 e certifica o DF-6a sem programar MSI/MSI-X.

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
  DF-6a read-only MSI capability model       CERTIFIED
  DF-6b vector + ownership bridge            IMPLEMENTED / VALIDATING
  DF-6c transactional MSI programming        PLANNED
  DF-6d disable/teardown + runtime proof     PLANNED
DF-7  MSI-X                                  PLANNED
```

## DF-6a — certificado

O DF-6a interpreta a capability convencional MSI `0x05` sobre o walker bounded do DF-5c.

Ele:

- valida Message Control;
- distingue layout MSI 32-bit e 64-bit;
- identifica Per-Vector Masking;
- valida MMC/MME e expoe 1/2/4/8/16/32 mensagens;
- calcula offsets de Message Address/Data/Mask/Pending sem ultrapassar `0xFF`;
- falha fechado se BDF/capability mudar entre leituras;
- permanece estritamente read-only.

## DF-6b — single-vector reservation bridge

O DF-6b reutiliza o Generic IRQ Registry como unica autoridade sobre os vetores dinamicos `0x50..0xEF`.

Ele pode:

- exigir `DeviceHandle + DriverHandle` validos e ownership PCI exato;
- exigir capability MSI valida e ainda desabilitada;
- reservar exatamente um `IrqHandle` via `irq_registry_register()`;
- publicar `vector + BDF + capability_offset` em uma `PciMsiReservation`;
- revalidar ownership e layout MSI depois do claim para fechar TOCTOU;
- fazer rollback do `IrqHandle` se qualquer revalidacao falhar;
- liberar reserva nao armada durante `BINDING`, `ACTIVE` ou `UNBINDING`;
- recusar liberar o vetor se a capability MSI estiver habilitada.

Ele nao pode:

- chamar `resource_claim()` diretamente para escolher vetor;
- criar tabela/allocator paralelo de MSI;
- escrever PCI config space;
- programar Message Address ou Message Data;
- alterar Multiple Message Enable;
- alterar MSI Enable;
- desabilitar INTx;
- tocar LAPIC, IOAPIC, IDT ou EOI;
- introduzir chamada nova no caminho de boot.

## Invariante de lifecycle para MSI

Reserva e armamento ficam deliberadamente separados:

```text
BINDING
  -> detectar MSI
  -> reservar IrqHandle
  -> NAO habilitar MSI

ACTIVE
  -> DF-6c podera programar endereco/dado
  -> MSI Enable somente por ultimo

UNBINDING
  -> DF-6d deve desabilitar a fonte primeiro
  -> confirmar MSI Enable = 0
  -> somente entao liberar IrqHandle
```

Isso impede que um dispositivo emita MSI para um vetor que ja voltou ao pool dinamico.

## Sequencia de continuacao

Somente se o SHA candidato do DF-6b fechar os gates obrigatorios:

1. marcar DF-6b `CERTIFIED`;
2. manter single-vector como unico modo inicialmente suportado;
3. iniciar DF-6c sem criar segundo interrupt core;
4. derivar Message Address/Data a partir do LAPIC existente e do vetor reservado;
5. fazer programacao transacional com snapshots, verificacao e rollback;
6. escrever MSI Enable somente depois de address/data/MME estarem consistentes;
7. manter INTx e politica de fallback separados e explicitamente auditados;
8. MSI-X continua bloqueado ate DF-6 inteiro estar certificado.

## Regra de retomada

Ao abrir um novo chat ou retomar a implementacao, conferir nesta ordem:

```text
main HEAD
-> functional baseline certificada
-> candidate SHA
-> gates do candidate
-> somente entao escolher o proximo microcorte
```
