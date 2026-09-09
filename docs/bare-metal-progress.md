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

**Estado: ✅ 100% / CONCLUÍDA E CERTIFICADA.** No commit
`18343b99920c24deb3f27af0926202247206f69d`, o CI principal #1019, o SMP
#122 e o NVMe-only #219 passaram no mesmo SHA.

A auditoria encontrou três bloqueadores de qualidade. Eles foram implementados
e certificados: snapshot de exceção por CPU, política que preserva
NMI/double fault/machine check como terminais e uma falha CPL3 real executada
no AP. A nova prova SMP publica `BAKEN:SMP_USER_FAULT_ISOLATED_READY`.

Além da infraestrutura já comprovada, o último limite do Kernel Core agora tem
implementação e contrato de teste: um `#PF` vindo de CPL3 é identificado pelo
frame de exceção completo, encerra a thread/processo culpado, passa pelo reaper,
libera as páginas e o address space privados, e retorna pelo scheduler a um
frame de kernel válido. Falhas em CPL0 continuam `fail-closed` (`CLI` + `HLT`).

Os gates de runtime exigem `BAKEN:USER_FAULT_ISOLATED_READY` e
`BAKEN:SMP_USER_FAULT_ISOLATED_READY`, rejeitam `BAKEN:HEX=E:` e concluíram
com sucesso. O selo formal de **Kernel Core concluído** está concedido.

## Fases seguintes

**FASE 2 — PLATFORM / DRIVERS**

- AML: catálogo DSDT/SSDT implementado localmente e aguardando gates QEMU;
- decoder/namespace/métodos AML ainda pendentes;
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
