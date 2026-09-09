# Baken OS — Bare-Metal Foundation Progress

Atualizado em 2026-09-09.

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

**Estado: implementação atual certificada pelos gates; auditoria rigorosa ainda
aberta.** No commit `b703cb2e77442873910268532d6fc5272a51873f`, o CI
principal #1017, o SMP #120 e o NVMe-only #217 passaram no mesmo SHA.

A auditoria também mantém três bloqueadores de qualidade: snapshot de exceção
por-CPU/sincronizado, política que preserve NMI/double fault/machine check como
terminais e prova de uma falha CPL3 executada no AP.

Além da infraestrutura já comprovada, o último limite do Kernel Core agora tem
implementação e contrato de teste: um `#PF` vindo de CPL3 é identificado pelo
frame de exceção completo, encerra a thread/processo culpado, passa pelo reaper,
libera as páginas e o address space privados, e retorna pelo scheduler a um
frame de kernel válido. Falhas em CPL0 continuam `fail-closed` (`CLI` + `HLT`).

O gate de runtime exige `BAKEN:USER_FAULT_ISOLATED_READY` e rejeita
`BAKEN:HEX=E:`. Essa implementação está certificada pelos três gates atuais.
O selo formal de **Kernel Core concluído** permanece reservado até fechar os
três bloqueadores arquiteturais acima e repetir a certificação no mesmo SHA.

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
