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

O runtime HID-3 está em `51631f23`; `2775c12a` adiciona somente documentação e é o head promovido após validação integrada.

- CI #1066 / `34509266662` ✅;
- SMP #169 / `34509266645` ✅ — 3/3, todos `stop_reason=complete`;
- NVMe #266 / `34509266646` ✅.

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
| HID-4 Hot-plug/lifecycle | ⬜ | concorrência, identidade, attach/detach/recovery e múltiplos devices |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

`1b3f94cc`: CI #1059 / `34497000191` ✅; SMP #162 / `34497000136` ✅ 3/3; NVMe #259 / `34497000185` ✅.

### HID-2 — certificado

`a2e04a78`: CI #1063 / `34501892035` ✅; SMP #166 / `34501892066` ✅ 3/3; NVMe #263 / `34501892022` ✅. Runtime base em `7e3008ae`; correção final foi somente do guardrail textual.

### HID-3 — certificado

Runtime:
```text
51631f23f8ffa3bd2593c405bfee90f0e5f2fe32
feat(hid): add unified input event model
```

Head promovido/certificado:
```text
2775c12a1c36dbcf9f88cee25de0c8ad98242d3c
docs: track HID-3 input event validation
```

Implementação comprovada:
- `input_event.sotlas`: fila FIFO 512, fixed-capacity, sem heap e independente de protocolo/transporte;
- ABI de eventos com classes keyboard/pointer/touch e key/button/relative/absolute;
- `hid_input_events.sotlas`: HID-2 -> eventos normalizados, sem dependência xHCI;
- estado anterior por Report ID;
- teclado por Usage Page 0x07 com press/release edge detection;
- Variable exige valor != 0; Usage 0 não gera tecla;
- mouse: botões + X/Y/Wheel relativos assinados;
- xHCI permanece produtor de reports, não dono da semântica de input;
- HID-2 continua autoridade de validação/decodificação antes do tradutor;
- fallback Boot e a prova QEMU da tecla A permanecem.

Markers obrigatórios no smoke:
```text
BAKEN:USB_HID_EVENT_MODEL_READY
BAKEN:USB_HID_EVENT_READY
```

O segundo marker exige que um Interrupt IN real publique evento. CI #1066 e NVMe #266 passaram o smoke que exige os dois markers, usando a injeção real `sendkey a`. SMP #169 passou 3/3 e preservou migração de processo/FPU.

Certificação:
- CI #1066 / `34509266662` ✅;
- SMP #169 / `34509266645` ✅ 3/3;
- NVMe #266 / `34509266646` ✅.

### HID-4 — próximo

**⬜ PLANEJADO.** Evoluir do primeiro HID global para lifecycle/múltiplos devices sem alterar o modelo de eventos já certificado:
- identidade estável por dispositivo/interface;
- estado HID separado por dispositivo e Report ID;
- attach/detach e invalidação segura;
- múltiplos keyboards/mice/HID simultâneos;
- lifecycle/cancelamento/recovery dos Interrupt IN;
- hot-plug e reenumeração bounded/fail-closed;
- fila de eventos continua sendo a fronteira transport-agnostic.

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
