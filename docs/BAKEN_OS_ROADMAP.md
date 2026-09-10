# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline de runtime certificada

```text
12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c
docs: note HID-4a revalidation runs
```

- CI #1072 / `34516628427` ✅;
- SMP #175 / `34516628437` ✅ — 3/3;
- NVMe #272 / `34516628445` ✅.

HID-4a foi promovido para `main` por fast-forward no próprio SHA certificado.

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
| HID-3 Input event model | ✅ | fila e eventos normalizados keyboard/mouse |
| HID-4a Identity/lifecycle core | ✅ | device_id+generation, SMP-safe queue, bind/unbind |
| HID-4b Per-device HID map | ⏳ | snapshots de field map/decoder por device+generation |
| HID-4c Multi-slot xHCI | ⬜ | slot/context/rings/buffers por device/interface |
| HID-4d Hot-plug/recovery | ⬜ | detach físico, cancel/recovery e reenumeração |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

`1b3f94cc`: CI #1059 / `34497000191` ✅; SMP #162 / `34497000136` ✅ 3/3; NVMe #259 / `34497000185` ✅.

### HID-2 — certificado

`a2e04a78`: CI #1063 / `34501892035` ✅; SMP #166 / `34501892066` ✅ 3/3; NVMe #263 / `34501892022` ✅.

### HID-3 — certificado

Runtime `51631f23`; head promovido `2775c12a`. CI #1066 / `34509266662` ✅; SMP #169 / `34509266645` ✅ 3/3; NVMe #266 / `34509266646` ✅. Markers `BAKEN:USB_HID_EVENT_MODEL_READY` e `BAKEN:USB_HID_EVENT_READY` permanecem obrigatórios no smoke.

### HID-4a — certificado

Runtime original `8f34ae13`; correção de parser Sotlas `a4762cf6`; head final certificado/promovido:

```text
12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c
```

- CI #1072 / `34516628427` ✅;
- SMP #175 / `34516628437` ✅ 3/3;
- NVMe #272 / `34516628445` ✅.

HID-4a entrega registro de 16 devices, `device_id + generation`, lifecycle explícito, fila/eventos SMP-safe, purge por geração, estado HID por device x Report ID, bind/unbind generation-safe e marker `BAKEN:USB_HID_DEVICE_READY`.

Histórico: CI #1069 / SMP #172 / NVMe #269 falharam antes do QEMU pela sintaxe `return` dentro de `if`-expressão em `xhci_hid_descriptor.sotlas`; `a4762cf6` corrigiu somente essa forma de controle de fluxo. A correção passou SMP #173 3/3 e depois o head final passou os três gates oficiais.

### HID-4b — candidato atual

Branch: `hid4b-validation`, criada diretamente da baseline certificada `12c308b3`.

Escopo candidato:
- `hid_input_device_map.sotlas` fixed-capacity, sem heap e transport-agnostic;
- snapshot HID-2 independente por `device_id + generation`;
- fields, Report IDs e expected bytes separados por device;
- parser HID-1 continua stateless;
- mapa HID-2 legado é apenas scratch serializado de construção, invalidado após copiar o snapshot;
- runtime de Interrupt IN usa exclusivamente APIs per-device;
- tradutor HID usa mapa e estado correspondentes à mesma generation;
- self-test mantém teclado e mouse simultaneamente e prova que um report não valida contra o mapa do outro;
- teardown remove mapa somente depois de invalidar identidade, purgar fila e limpar estado de eventos;
- marker novo `BAKEN:USB_HID_DEVICE_MAP_READY`; falha `BAKEN:USB_HID_DEVICE_MAP_FAILED`;
- smoke/SMP/NVMe passam a bloquear ausência ou falha do mapa específico.

**Limite:** xHCI ainda é single-slot/single-endpoint nesta fatia. HID-4b não declara múltiplos dispositivos USB simultâneos no transporte; ele remove o bloqueio semântico do mapa para que HID-4c possa fazê-lo corretamente.

**Critério:** CI principal + SMP 3/3 + NVMe-only verdes no mesmo SHA final da branch. Só então promover HID-4b e iniciar HID-4c.

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
