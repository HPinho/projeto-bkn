# Baken OS — Trilha B2 / I2C Foundation Roadmap Appendix

Este apêndice inicia a continuação append-only da Trilha B para I2C e I2C-HID sem reescrever o histórico USB HID/xHCI já preservado em `BAKEN_OS_ROADMAP.md` e `BAKEN_OS_ROADMAP_APPENDIX.md`.

## 2026-09-13 — transição B1 → B2

A baseline imediatamente anterior fechou **4/4**:

```text
45c1bd406d7d200c50c20af4220a83b14f929db0
fix(xhci): quiesce failed transfer state by epoch
```

- CI #1213 ✅
- SMP #316 ✅
- NVMe #413 ✅
- HID Dual-device #72 ✅

O escopo funcional USB HID/xHCI da Trilha B1 permanece concluído/certificado. O hardening físico adicional de enumeração `FAILED` que ainda existe — HID Report Descriptor DMA, HID Report DMA, HID Transfer Ring, arena Device/Input Context + EP0 Ring e finalização Device Table/Slot ID/porta — fica preservado como backlog pós-certificação; ele não é apagado nem declarado concluído por esta transição.

## Trilha B2 — I2C Foundation / I2C-HID

| Etapa | Estado | Contrato |
| --- | --- | --- |
| I2C-0a — ACPI resource semantic decode | ⏳ | `I2CSerialBus` + `GpioInt` bounded/fail-closed, sem hardware |
| I2C-0b — ACPI namespace/resource binding | ⬜ | resolver `ResourceSource`, `_HID/_CID`, `_CRS` e preparar `_DSM` |
| I2C-1 — Generic I2C Core | ⬜ | read/write/combined/repeated-start + timeout/NACK/arbitration/busy |
| I2C-2 — ACPI ↔ controller binding | ⬜ | registry generation-safe entre device, connection e controller |
| I2C-3 — GPIO/IRQ Foundation | ⬜ | pin/trigger/polaridade/routing/dispatch |
| I2C-4 — Generic I2C Device Model | ⬜ | identidade, address, speed, controller, IRQ e lifecycle |
| I2C-HID-0 — transport | ⬜ | `PNP0C50`, `_DSM`, HID Descriptor Register e validação |
| I2C-HID-1 — enumeration/lifecycle | ⬜ | reset/power/report descriptor/IRQ/recovery |
| I2C-HID-2 — HID Core integration | ⬜ | reutilizar parser/field map/decoder/InputDevice existentes |
| I2C-HID-3 — input runtime | ⬜ | reports por IRQ para dispositivos descritos pelo firmware |
| I2C-HID-4 — power/recovery | ⬜ | suspend/resume, stale IRQ/report e teardown generation-safe |
| I2C-HID-5 — runtime certification | ⬜ | fault injection + provas disponíveis em QEMU/hardware |

## I2C-0a — contrato do primeiro microcorte

O AML-5 já fornece `_HID`, `_CID`, `_CRS` e `ResourceTemplate` cru com EndTag e bounds. Portanto I2C-0a não duplica discovery: adiciona uma camada semântica sobre `AmlResourceDescriptor`.

Escopo deste candidato:

- reconhecer Large Resource `0x0E` como GenericSerialBus e aceitar somente Serial Bus Type `1` para I2C;
- validar Revision ID 2, Type Revision 1, Type Data Length, flags reservados e endereços 7/10-bit;
- expor connection speed, slave address, sharing/consumer/slave-mode, vendor data e `ResourceSource`;
- preservar o byte LVR da ACPI 6.6 para decisão futura no binding do controlador;
- reconhecer Large Resource `0x0C` somente como `GpioInt` revision 1;
- validar flags, polaridade, edge/level, PinConfig, offsets relativos ao início do descriptor, pin table, `ResourceSource` e vendor data;
- manter o módulo read-only e sem estado global mutável.

Fora de escopo deste corte: resolução do namespace de `ResourceSource`, `_DSM`, `PNP0C50`, MMIO, controlador I2C, GPIO programming, IRQ registration, DMA, HID parsing ou input runtime.

A mesma regra de certificação continua valendo: **nenhum I2C-0b começa antes de CI + SMP + NVMe-only + HID Dual-device fecharem verdes no mesmo SHA I2C-0a**. Em caso de gate vermelho, o próximo commit é correction-only e a falha deve ser preservada.
