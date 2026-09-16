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
27a7ea6253c909617b7687532b5afea55f9f81e1
fix(pci): quarantine uncertain MSI reservations
```

Gates desse mesmo SHA:

- CI/CD + QEMU #1292: PASS
- SMP Bring-up #395: PASS
- NVMe-only Bare-Metal #492: PASS
- HID Dual-device #151: PASS
- SMP Fault Diagnostic #57: PASS

Essa baseline certifica o DF-6b completo: ownership exclusivo da fonte MSI por BDF, vetor generation-safe no Generic IRQ Registry e rollback/cleanup fail-closed com estado `QUARANTINED` quando a quiescencia nao pode ser provada.

Baseline anterior do DF-6a:

```text
4de09d94ab3681dd6d02da5cdec63fcade942586
feat(pci): add read-only MSI capability model
```

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
  DF-6b vector + ownership bridge            CERTIFIED
  DF-6c transactional MSI programming        IMPLEMENTED / VALIDATING
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

## DF-6b — single-vector reservation bridge — certificado

O DF-6b usa duas fundacoes ja existentes, com responsabilidades separadas:

```text
Resource Manager
  -> RESOURCE_KIND_PCI_MSI
  -> ownership logico exclusivo da fonte MSI por BDF

Generic IRQ Registry
  -> RESOURCE_KIND_IRQ
  -> unica autoridade sobre vetores dinamicos 0x50..0xEF
```

O claim `RESOURCE_KIND_PCI_MSI` nao escolhe nem representa vetor. Ele apenas impede que duas CPUs/rotinas reservem simultaneamente duas IRQs para a mesma fonte MSI convencional.

A reserva possui estado explicito:

```text
INVALID
  -> nenhum ownership MSI pendente

READY
  -> source claim + IrqHandle pertencem ao caller
  -> uma leitura recente provou MSI Enable = 0
  -> unico estado aceito pelo DF-6c para armamento

QUARANTINED
  -> existe ownership ainda nao reconciliado
  -> quiescencia ou rollback nao puderam ser provados
  -> nenhum handle pode voltar ao pool ate nova prova positiva
```

Ele pode:

- exigir `DeviceHandle + DriverHandle` validos e ownership PCI exato;
- exigir capability MSI valida e ainda desabilitada;
- adquirir um claim logico exclusivo da fonte MSI keyed por BDF;
- reservar exatamente um `IrqHandle` via `irq_registry_register()`;
- publicar `source + irq + vector + BDF + capability_offset + state` em uma `PciMsiReservation`;
- revalidar ownership PCI, ownership da fonte e layout MSI depois dos claims para fechar TOCTOU;
- publicar `READY` somente depois da revalidacao final;
- exigir uma NOVA prova de `MSI Enable = 0` antes de qualquer cleanup/rollback;
- fazer cleanup em ordem inversa: IRQ primeiro, fonte MSI por ultimo;
- retornar `QUARANTINED` se config space/capability nao puderem provar quiescencia;
- retornar `QUARANTINED` se unregister da IRQ ou release da fonte falharem;
- preservar somente os handles ainda vivos quando o rollback for parcial;
- permitir retry explicito de cleanup de uma reserva `QUARANTINED`;
- liberar reserva nao armada durante `BINDING`, `ACTIVE` ou `UNBINDING`;
- falhar fechado se o config space ou a capability deixarem de ser verificaveis.

Ele nao pode:

- usar `resource_claim()` para escolher vetor;
- criar tabela/allocator paralelo de MSI;
- escrever PCI config space;
- programar Message Address ou Message Data;
- alterar Multiple Message Enable;
- alterar MSI Enable;
- desabilitar INTx;
- tocar LAPIC, IOAPIC, IDT ou EOI;
- introduzir chamada nova no caminho de boot.

## DF-6c — transactional single-vector MSI programming

O DF-6c e o primeiro corte que escreve a capability MSI. Ele permanece separado de reserva e teardown.

Pre-condicoes obrigatorias:

```text
PciMsiReservation == READY
Device Core == ACTIVE
DeviceHandle + DriverHandle + BDF ainda coincidem
RESOURCE_KIND_PCI_MSI ainda pertence ao mesmo owner
IrqHandle ainda resolve para o mesmo vetor dinamico
LAPIC do BSP esta READY
```

Programacao:

```text
snapshot control/address/data
-> confirmar MSI Enable = 0
-> MME = 000 mantendo MSI desligado
-> Message Address low = 0xFEE00000 | (BSP APIC ID << 12)
-> Message Address high = 0 para layout 64-bit
-> Message Data = reserved[13:11] preservado | vector[7:0]
-> readback + revalidacao de ownership/layout
-> MSI Enable = 1 SOMENTE POR ULTIMO
-> readback final + revalidacao completa
```

Politica inicial:

- exatamente um vetor;
- destination fisico no BSP publicado por `lapic_id()`;
- Fixed Delivery;
- edge-triggered;
- `MME=0` mesmo quando MMC anuncia multiplas mensagens;
- bits reservados do Message Data sao preservados do snapshot;
- nenhum `lapic_eoi()` novo: EOI continua centralizado no dispatcher x86 existente;
- nenhuma alteracao implicita de INTx, Bus Master ou Memory Space;
- nenhuma chamada de `pci_msi_arm_single()` entra no boot neste microcorte.

Rollback:

- qualquer falha depois da primeira escrita tenta desabilitar MSI primeiro;
- restaura Message Data, Address High quando aplicavel, Address Low e Message Control original;
- somente um readback completo permite retornar estado de operacao `READY` para retry;
- qualquer incerteza retorna a reserva em `QUARANTINED`;
- DF-6c nunca faz `irq_registry_unregister()` nem `resource_release()`.

## Invariante de lifecycle para MSI

Reserva, armamento e teardown permanecem deliberadamente separados:

```text
BINDING
  -> detectar MSI
  -> claim exclusivo da fonte por BDF
  -> reservar IrqHandle
  -> provar MSI Enable = 0
  -> READY
  -> NAO habilitar MSI

qualquer incerteza antes do armamento
  -> QUARANTINED
  -> manter source/IRQ ainda vivos
  -> retry somente apos nova prova de quiescencia

ACTIVE
  -> DF-6c aceita somente READY
  -> programa Address/Data com MSI Enable = 0
  -> revalida ownership/layout/readback
  -> MSI Enable somente por ultimo

UNBINDING
  -> DF-6d deve desabilitar a fonte primeiro
  -> confirmar MSI Enable = 0
  -> liberar IrqHandle
  -> liberar ownership logico da fonte MSI
```

Isso impede MSI contra vetor devolvido ao pool, dupla reserva concorrente da mesma fonte e perda silenciosa de ownership durante rollback parcial.

## Sequencia de continuacao

Somente se o SHA candidato do DF-6c fechar os gates obrigatorios:

1. marcar DF-6c `CERTIFIED`;
2. manter single-vector como unico modo suportado;
3. iniciar DF-6d sem criar segundo interrupt core;
4. implementar disable transacional antes de qualquer release;
5. confirmar `MSI Enable = 0` antes de unregister/release;
6. usar o snapshot do armamento para restauracao segura quando aplicavel;
7. manter INTx, Bus Master e Memory Space fora da politica implicita de MSI;
8. criar prova runtime real antes de fechar DF-6;
9. MSI-X continua bloqueado ate DF-6 inteiro estar certificado.

## Regra de retomada

Ao abrir um novo chat ou retomar a implementacao, conferir nesta ordem:

```text
main HEAD
-> functional baseline certificada
-> candidate SHA
-> gates do candidate
-> somente entao escolher o proximo microcorte
```
