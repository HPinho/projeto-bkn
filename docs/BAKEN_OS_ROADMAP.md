# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline de runtime certificada

```text
1b3f94ccca5e399550d0951fc2c9f133a768440c
feat(hid): parse real report descriptors
```

- CI #1059 / `34497000191` ✅;
- SMP #162 / `34497000136` ✅ — 3/3;
- NVMe #259 / `34497000185` ✅.

`a16e515b` é o commit documental posterior.

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
| HID-2 Field map / decoder | ⏳ | Report ID, Usage, bit offsets, flags e valores |
| HID-3 Input event model | ⬜ | eventos unificados keyboard/mouse/touch |
| HID-4 Hot-plug/lifecycle | ⬜ | attach/detach/recovery e múltiplos devices |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

```text
1b3f94ccca5e399550d0951fc2c9f133a768440c
feat(hid): parse real report descriptors
```

Gates: CI #1059 / `34497000191` ✅; SMP #162 / `34497000136` ✅ 3/3; NVMe #259 / `34497000185` ✅.

### HID-2 — candidato atual

Branch: `hid2-validation`. **⏳ EM VALIDAÇÃO.**

- `hid_input_report.sotlas` transport-agnostic, fixed-capacity e sem heap;
- field map por Report ID, Usage Page/Usage, bit offset/width e Main flags;
- Usage list e Usage Minimum/Maximum bounded;
- Logical Minimum/Maximum + sign extension;
- byte de Report ID separado do payload;
- comprimento real precisa coincidir com a geometria do Report ID;
- Arrays mantêm range de usages quando demonstrável; combinação não contígua não gera Usage sintético;
- Buffered Bytes/Delimiter/Push/Pop continuam fail-closed;
- self-test de keyboard, mouse signed-relative e Report ID;
- mapa é construído sobre o descriptor real do HID-1;
- report Interrupt IN real é validado pelo mapa antes do fallback Boot;
- marker `BAKEN:USB_HID_INPUT_MAP_READY` obrigatório no smoke CI/NVMe;
- `BAKEN:USB_HID_INPUT_MAP_FAILED` terminal.

Critério: CI + SMP 3/3 + NVMe verdes no mesmo SHA; só então fast-forward de `main`.

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
