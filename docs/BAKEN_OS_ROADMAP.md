# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline de runtime certificada

```text
a2e04a7858443a837488ff39fc2c26df4261fa58
test(hid): scope HID-2 runtime order assertion
```

O runtime HID-2 está em `7e3008ae`; `a2e04a78` corrige apenas o guardrail de teste e é o SHA final promovido.

- CI #1063 / `34501892035` ✅;
- SMP #166 / `34501892066` ✅ — 3/3 boots;
- NVMe #263 / `34501892022` ✅.

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.** ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guard stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.** Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP->AP e teardown seguro.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 fechados; checkpoint AML final `7803447a`.

## Trilha B — HID adicional / input de produção

| Etapa | Estado | Objetivo |
|---|---|---|
| HID-0 Boot HID xHCI | ✅ | keyboard/mouse Boot + Interrupt IN real |
| HID-1 Report Descriptor | ✅ | fetch real + parser bounded transport-agnostic |
| HID-2 Field map / decoder | ✅ | Report ID, Usage, bit offsets, flags e valores |
| HID-3 Input event model | ⬜ | eventos unificados keyboard/mouse/touch |
| HID-4 Hot-plug/lifecycle | ⬜ | attach/detach/recovery e múltiplos devices |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

`1b3f94cc`: CI #1059 / `34497000191` ✅; SMP #162 / `34497000136` ✅ 3/3; NVMe #259 / `34497000185` ✅.

### HID-2 — certificado

Runtime implementado em `7e3008ae43af73b89ea8cd3fbb03c8f3a45c920b`:
- field map transport-agnostic e fixed-capacity;
- Report IDs;
- Usage lists e Usage Minimum/Maximum;
- bit offsets/widths e flags Main;
- Logical Minimum/Maximum e sign extension;
- validação exata do comprimento de cada Interrupt IN;
- arrays sem range demonstrável permanecem usage-unresolved;
- descriptor real HID-1 alimenta o mapa;
- report real passa pelo decoder antes do fallback Boot;
- marker `BAKEN:USB_HID_INPUT_MAP_READY` e falha `BAKEN:USB_HID_INPUT_MAP_FAILED`.

Histórico:
- SMP #165 / `34501501476` ❌ antes do build/QEMU por bug no próprio teste de ordem (`text.index` no arquivo inteiro);
- correção `a2e04a7858443a837488ff39fc2c26df4261fa58` restringiu a asserção a `xhci_hid_descriptor_probe_internal`, sem alterar runtime;
- CI #1063 / `34501892035` ✅;
- SMP #166 / `34501892066` ✅ — 3/3, com `USB_HID_INPUT_MAP_READY` e prova completa até `SMP_FPU_MIGRATION_READY`;
- NVMe #263 / `34501892022` ✅;
- `main` promovida por fast-forward para `a2e04a78`.

### HID-3 — próximo

**⬜ PLANEJADO.** Modelo e fila unificada de eventos consumindo os campos HID-2 já decodificados, inicialmente keyboard/mouse, com arquitetura extensível a touch. O event core deve ser transport-agnostic; xHCI atua como produtor. Lifecycle/hot-plug e múltiplos devices permanecem HID-4.

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
