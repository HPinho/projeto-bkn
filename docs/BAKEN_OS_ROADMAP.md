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

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.** ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guard stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.** Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP->AP e teardown seguro.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.**

AML-0..AML-8 fechados. O checkpoint `7803447a` passou CI #1056 + SMP #159 3/3 + NVMe #256 e permanece coberto pelos gates posteriores.

## Trilha B — HID adicional / input de produção

| Etapa | Estado | Objetivo |
|---|---|---|
| HID-0 Boot HID xHCI | ✅ | keyboard/mouse Boot + Interrupt IN real |
| HID-1 Report Descriptor | ✅ | fetch real + parser bounded transport-agnostic |
| HID-2 Field map / decoder | ⬜ | Report ID, Usage, bit offsets e valores |
| HID-3 Input event model | ⬜ | eventos unificados keyboard/mouse/touch |
| HID-4 Hot-plug/lifecycle | ⬜ | attach/detach/recovery sem estado global frágil |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

```text
1b3f94ccca5e399550d0951fc2c9f133a768440c
feat(hid): parse real report descriptors
```

Implementação:
- parser `hid_report_descriptor.sotlas` sem dependência de xHCI/DMA;
- máximo 4096 bytes, 512 itens, collection depth 16, ReportSize <=64, ReportCount <=256 e geometria total <=32768 bits;
- parsing real de short item size/type/tag;
- Application Usage keyboard/mouse, Report ID e geometria input/output/feature;
- unsupported/truncated/reserved/long/Push/Pop = fail-closed;
- `xhci_hid_descriptor.sotlas` usa EP0 `GET_DESCRIPTOR(Report)` com request `0x81`, value `0x2200`, índice de interface e comprimento vindo do HID descriptor;
- descriptor real validado antes de SET_CONFIGURATION pronto;
- report Boot fixo continua apenas como fallback de consumo, não como descriptor sintético;
- marker `BAKEN:USB_HID_DESCRIPTOR_READY` obrigatório; `BAKEN:USB_HID_DESCRIPTOR_FAILED` terminal.

Gates no mesmo SHA:
- CI #1059 / `34497000191` ✅;
- SMP #162 / `34497000136` ✅ — 3/3;
- NVMe #259 / `34497000185` ✅.

### HID-2 — próximo incremento

**⬜ PLANEJADO.**

Construir field map bounded por Report ID, Usage Page/Usage, bit offset, bit width, flags e signedness; em seguida decodificar Input reports reais sem ultrapassar o comprimento efetivo recebido no endpoint. O caminho Boot atual deve continuar válido como fallback/prova de regressão.

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
