# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline de runtime certificada integrada em `main`

```text
7803447a4c2179d088948b3c4288b6e3655bc1d5
fix(acpi): preserve bool type in PRT lowering
```

- CI #1056 / `34493002949` ✅;
- SMP #159 / `34493003041` ✅ — 3/3;
- NVMe #256 / `34493002936` ✅.

A PR #16 foi integrada por fast-forward no próprio SHA validado. Commits posteriores somente de documentação não alteram esta baseline de runtime.

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.** ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guard stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.** Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP->AP e teardown seguro.

Checkpoint histórico: `72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8`.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

| Etapa | Estado | Checkpoint |
|---|---|---|
| AML-0 Catálogo DSDT/SSDT | ✅ | TABLES_READY |
| AML-1 Decoder estrutural | ✅ | DECODER_READY |
| AML-2 Namespace core | ✅ | NAMESPACE_READY |
| AML-3 Data objects | ✅ | DATA_READY |
| AML-4 Namespace real | ✅ | `2a9974ad` |
| AML-5 Discovery estático | ✅ | `3f02decb` |
| AML-6a Evaluator bounded | ✅ | `8e553f79` |
| AML-6b Discovery dinâmico | ✅ | `4e90ec22` |
| AML-7 OperationRegion/Field core | ✅ | `7803447a` |
| AML-8 `_PIC`/`_PRT`/`_S5` | ✅ | `7803447a` |

**Trilha A — ACPI/AML CORE: ✅ CONCLUÍDA E CERTIFICADA.**

### Certificação final AML-7/8

```text
7803447a4c2179d088948b3c4288b6e3655bc1d5
fix(acpi): preserve bool type in PRT lowering
```

- CI #1056 / `34493002949` ✅;
- SMP #159 / `34493003041` ✅ — 3/3;
- NVMe #256 / `34493002936` ✅.

AML-7 entrega SystemMemory/SystemIO/PCIConfig mediados, bounds/overflow antes de hardware, Field <=32 bits dentro de um dword e init sem side effect. IndexField/BankField não são emulados sem backing dedicado.

AML-8 entrega `_PIC`, `_PRT` e `_S5` em subconjunto bounded/fail-closed. Unsupported permanece unresolved. EC/GPE/GlobalLock e transições físicas de energia ficam para power/hot-plug.

Markers finais:
```text
BAKEN:ACPI_AML_REGIONS_READY
BAKEN:ACPI_AML_PLATFORM_READY
```

Histórico: CI #1055 / `34491870501` ❌ detectou lowering `int* -> _Bool*` no candidato `1e333594`. A anotação explícita `let mut source_is_link: bool = false;` e teste de regressão produziram o candidato final verde `7803447a`.

## Trilha B — HID adicional / input de produção

**▶️ PRÓXIMA ETAPA.**

Objetivos:
- parser bounded de HID report descriptors;
- input genérico além do boot protocol;
- keyboard/mouse report protocol real sem quebrar o caminho atual;
- touchpad/touchscreen sobre HID quando transporte apropriado estiver disponível;
- I2C-HID somente após transporte I2C/ACPI seguro;
- hot-plug, attach/detach e lifecycle previsível;
- markers e provas QEMU sem mocks substituindo hardware real.

Critério de promoção: novo candidato em branch/PR, CI + SMP 3/3 + NVMe-only no mesmo SHA e nenhuma regressão no xHCI/HID atual.

## Trilha C — Storage de produção

**⬜ PLANEJADO.** Block cache, VFS, FAT32 robusto, handles, async e lifecycle de volumes.

## Trilha D — Rede

**⬜ PLANEJADO.** NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS.

## Trilha E — Áudio

**⬜ PLANEJADO.** HDA, DMA/ring buffer, codec/mixer e API userspace.

## Trilha F — GPU/composição

**⬜ PLANEJADO.** Framebuffer fallback, aceleração/compositor depois do modelo de memória seguro; zero lógica visual no compilador.

## Trilha G — Power / hot-plug ACPI avançado

**⬜ PLANEJADO.** EC, GPE, GlobalLock, transições físicas de energia e extensões firmware-specific estritamente necessárias.

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API, executáveis Sotlas, IPC, init/service manager e COW/demand paging.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, fontes/acessibilidade, shell, installer/OOBE, apps base, recovery e E2E.

## Regras permanentes

1. `main` não recebe candidato vermelho;
2. runtime real vale mais que teste textual;
3. Kernel Core permanece congelado;
4. toda camada de firmware/hardware tem bounds/marker/fail-closed;
5. nunca fazer scan cego de AML/HID;
6. firmware e descriptors são input não confiável;
7. hardware opcional degrada com diagnóstico;
8. unsupported = unresolved, nunca retorno inventado;
9. toda falha/correção/certificação deve constar aqui e em `KERNEL_HANDOFF.md`.
