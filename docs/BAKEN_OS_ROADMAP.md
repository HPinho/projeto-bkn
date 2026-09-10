# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline de runtime certificada

```text
2775c12a1c36dbcf9f88cee25de0c8ad98242d3c
docs: track HID-3 input event validation
```

- CI #1066 / `34509266662` ✅;
- SMP #169 / `34509266645` ✅ — 3/3;
- NVMe #266 / `34509266646` ✅.

`75886e96` é somente o commit documental posterior de certificação HID-3.

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
| HID-4a Identity/lifecycle core | ⏳ | device_id+generation, SMP-safe queue, bind/unbind |
| HID-4b Per-device HID map | ⬜ | retirar singleton do Report Descriptor/field map |
| HID-4c Multi-slot xHCI | ⬜ | slot/context/rings por device/interface |
| HID-4d Hot-plug/recovery | ⬜ | detach físico, cancel/recovery e reenumeração |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

`1b3f94cc`: CI #1059 / `34497000191` ✅; SMP #162 / `34497000136` ✅ 3/3; NVMe #259 / `34497000185` ✅.

### HID-2 — certificado

`a2e04a78`: CI #1063 / `34501892035` ✅; SMP #166 / `34501892066` ✅ 3/3; NVMe #263 / `34501892022` ✅.

### HID-3 — certificado

Runtime `51631f23`; head promovido `2775c12a`. CI #1066 / `34509266662` ✅; SMP #169 / `34509266645` ✅ 3/3; NVMe #266 / `34509266646` ✅. Markers `BAKEN:USB_HID_EVENT_MODEL_READY` e `BAKEN:USB_HID_EVENT_READY` permanecem obrigatórios no smoke.

### HID-4a — candidato atual

Branch: `hid4-validation`.

Runtime original:
```text
8f34ae132454ef87afae67288b632886131acfe4
feat(hid): add generation-safe input lifecycle
```

Implementação:
- registro `input_device.sotlas` com 16 slots fixed-capacity, sem heap e sem dependência de transporte;
- identidade `device_id + generation`, impedindo stale handles após detach/re-attach;
- lifecycle ATTACHED/ACTIVE/FAILED/DETACHED;
- registry e fila protegidos com IRQ-save + spinlock;
- `InputEvent` inclui identidade da fonte;
- publicação revalida a identidade dentro do lock da fila;
- `input_event_purge_device` remove somente a geração desconectada sem apagar eventos de outros devices;
- estado HID anterior particionado por device x Report ID;
- bind/unbind HID generation-safe;
- xHCI associa a interface real atual a um registro USB e transmite essa identidade ao tradutor;
- detach lógico segue `invalidate -> purge -> clear HID state`;
- marker novo `BAKEN:USB_HID_DEVICE_READY`; falha `BAKEN:USB_HID_DEVICE_FAILED`;
- smoke CI/NVMe e SMP 3/3 passam a exigir identidade real pronta;
- HID-0..HID-3 e prova QEMU `sendkey a` permanecem.

#### Primeira validação HID-4a — falhou antes do QEMU

Head: `ebf21182b33252c7bb6270c82eb25441b1746487`.

- CI #1069 / `34513631621` ❌;
- SMP #172 / `34513631581` ❌;
- NVMe #269 / `34513631641` ❌.

Causa única nos três gates: `compiler.py build` reparsa `xhci_hid_descriptor.sotlas` para emissão dos headers C e falhou em `:235:9` com `expressão inválida: 'return'`. O `return false` estava dentro de um `if` usado como expressão ao inicializar `device_class`. Os contratos e `compiler.py check` passaram onde executados; não houve boot QEMU nem regressão runtime observada porque o PE não chegou a ser gerado.

Correção:
```text
a4762cf614a0748336040be8d15e7f352b17f25f
fix(hid): avoid return in conditional expression
```

A correção troca somente o `if`-expressão por controle de fluxo convencional e mantém o comportamento fail-closed. HID-4a continua **⏳ EM VALIDAÇÃO**; nenhum status foi promovido por causa dessa correção.

**Limite atual:** o xHCI ainda é singleton em slot/context/address/HID context/report, e o mapa HID-2 ainda é global. Portanto HID-4a não será descrito como suporte multi-device completo mesmo se seus gates passarem.

**Critério:** CI principal + SMP 3/3 + NVMe-only verdes no mesmo SHA final da branch. Só depois promover HID-4a e iniciar HID-4b.

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
