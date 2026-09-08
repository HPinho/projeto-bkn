# Baken OS — Bare-Metal Foundation Progress

Atualizado em 2026-09-08.

## Estado geral

**FASE 0 — FUNDAÇÃO BARE-METAL: 100% / FECHADA**

Checkpoint de implementação:

```text
d5ad8e9163ee10b5e6d84162bc43e5a7722a00f5
```

Validação do mesmo SHA:

| Gate | Resultado |
|---|---|
| CI principal #987 / `34271845602` | ✅ PASS |
| SMP #90 / `34271845718` | ✅ PASS |
| NVMe-only #187 / `34271845584` | ✅ PASS |

## Fundação congelada

| Área | Estado | Evidência principal |
|---|---|---|
| UEFI bootstrap / ExitBootServices | ✅ | handoff real e entrada pós-cutover |
| zero reentrada UEFI pós-cutover | ✅ | auditoria do call graph + suíte CI |
| stack / CR3 / W^X / guard stack | ✅ | gates de memória e boot |
| GDT / TSS per-CPU / IDT | ✅ | bring-up + Ring 3 em AP |
| PMM / VMM / direct-map | ✅ | runtime pós-EBS |
| active page tables / PAT / WC | ✅ | framebuffer WC e guardrails |
| ACPI / MADT / LAPIC / IOAPIC | ✅ | bring-up nativo |
| IRQ / LAPIC timer | ✅ | timer real em BSP/AP |
| SMP / scheduler por CPU | ✅ | dispatch, timer e AP runtime |
| TLB shootdown kernel-global | ✅ | prova QEMU SMP |
| PCI / DMA | ✅ | caminhos nativos da fixture |
| xHCI / USB HID | ✅ | certificação QEMU configurada |
| AHCI / BlockDevice | ✅ | smoke comum |
| NVMe / BlockDevice | ✅ | workflow NVMe-only |
| GPT / MBR / FAT32 | ✅ | camada de bloco nativa |
| scheduler / threads / reaper | ✅ | round-trip, wait, sleep, exit, reap |
| processos / CR3 privado | ✅ | registry + scheduler process-aware |
| Ring 3 / syscalls / user-copy | ✅ | probes runtime |
| CPL3 em AP | ✅ | CPU 1, syscall e teardown |
| preempção + resume CPL3 em AP | ✅ | SMP #90 |
| build nativo / ISO / QEMU | ✅ | CI #987 |
| **Fundação bare-metal geral** | **✅ 100%** | três workflows verdes no mesmo SHA |

## Significado de 100%

O percentual de 100% se refere à **Fase 0 definida pela arquitetura do projeto**: uma base x86-64 bare-metal sem dependência de serviços UEFI depois do cutover, com CPU/memória/interrupções/timer, barramentos, entrada, armazenamento e gates de certificação funcionando nativamente.

Não significa que todos os recursos futuros do sistema operacional estão concluídos.

## Fase 1 — Kernel Core

A Fase 1 já começa com bastante infraestrutura pronta, mas ainda possui trabalho arquitetural relevante:

- afinidade e migração genérica de process threads entre CPUs;
- rastreamento da raiz de address space ativa por CPU;
- TLB shootdown seletivo por address space para mappings de usuário;
- locks de processo/address-space compatíveis com espera de IPI/ACK;
- sincronização SMP completa do heap;
- ownership e migração de estado FPU/SIMD;
- política de scheduling e load balancing além dos probes controlados;
- amadurecimento do modelo de processos e serviços de userspace.

A regra é: não mudar processos para afinidade `ANY` de forma irrestrita antes de fechar coerência de page tables/TLB e ownership de estado por CPU.

## Fases seguintes

**FASE 2 — PLATFORM / DRIVERS**

- AML;
- I2C-HID;
- rede;
- áudio;
- GPU e aceleração real.

**FASE 3 — USER EXPERIENCE**

- compositor;
- desktop/window manager;
- installer e OOBE;
- animações;
- aplicativos e serviços de experiência do usuário.

## Regra de regressão

Um recurso da Fundação só continua marcado como ✅ enquanto os guardrails correspondentes permanecerem ativos. Mudanças futuras devem preservar, no mínimo:

```text
Test Suite                    PASS
Sotlas modular graph          PASS
Native kernel build           PASS
UEFI ISO build                PASS
QEMU post-cutover boot        PASS
BAKEN:BARE_METAL_READY        PRESENT
zero firmware reentry audit   PASS
SMP proof                     PASS
NVMe-only proof               PASS
```

Código compilando sozinho não substitui prova runtime para gates de hardware.
