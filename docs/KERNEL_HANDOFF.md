# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este arquivo é o registro operacional de continuidade. Código presente não equivale a prova: um incremento só vira baseline quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Política de baseline verde

- `main` recebe somente runtime comprovado;
- trabalho novo ocorre em branch/PR;
- falhas e correções ficam fora de `main` até os gates fecharem;
- nunca remover marker/teste ou aumentar timeout sem causa para obter verde;
- runtime QEMU vale mais que teste textual;
- toda implementação, falha, correção e certificação deve ser registrada aqui e em `docs/BAKEN_OS_ROADMAP.md`.

## Baseline de runtime certificada e integrada em `main`

```text
7803447a4c2179d088948b3c4288b6e3655bc1d5
fix(acpi): preserve bool type in PRT lowering
```

- CI #1056 / `34493002949` ✅;
- SMP #159 / `34493003041` ✅ — 3/3 boots;
- NVMe-only #256 / `34493002936` ✅.

PR #16 foi integrada por fast-forward no próprio SHA validado. `ead13903` é apenas a consolidação documental posterior e não substitui a baseline de runtime.

## Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. frame/stack só é liberado após entrada posterior do scheduler na CPU anterior;
4. FPU save -> schedule -> CR3/TSS -> FPU restore permanece sob switch lock;
5. migração Ring3 BSP->AP preserva TID, address-space root e SIMD;
6. teardown ocorre apenas após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` continua terminal;
8. wait/sleep, TLB, Ring3 e SMP não podem ser relaxados para acomodar drivers.

---

# ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO em `7803447a`.**

AML-0..AML-8 estão fechados. AML-7 entrega OperationRegion/Field bounded para SystemMemory/SystemIO/PCIConfig; AML-8 entrega `_PIC`, `_PRT` e `_S5` no subconjunto fail-closed. EC/GPE/GlobalLock e transições físicas de energia ficam para power/hot-plug.

Histórico final: CI #1055 / `34491870501` detectou lowering `int* -> _Bool*`; a tipagem explícita de `source_is_link` produziu o candidato `7803447a`, aprovado por CI #1056 + SMP #159 3/3 + NVMe #256.

---

# HID / input de produção

## HID-0 — Boot HID xHCI

**✅ BASELINE EXISTENTE.**

O xHCI atual já enumera o primeiro HID Boot keyboard/mouse, configura Interrupt IN e prova report real no QEMU. O parser de report atual ainda usa o formato fixo Boot: keyboard 8 bytes e mouse >=3 bytes.

## HID-1 — Report Descriptor genérico

**⏳ EM VALIDAÇÃO na branch `hid-input-validation`.**

Escopo do candidato:
- novo `kernel/src/drivers/hid_report_descriptor.sotlas`, independente de transporte;
- parser bounded de HID short items com limite de 4096 bytes, 512 itens e collection depth 16;
- valida item size/type/tag e falha fechado em truncamento, reserved/long item e Push/Pop ainda não implementado;
- extrai Usage Page/Application para keyboard/mouse, ReportSize/ReportCount, Report ID e geometria input/output/feature;
- self-test com descriptor Boot Keyboard realista de 63 bytes, 64 input bits e 8 output bits;
- novo `kernel/src/drivers/xhci_hid_descriptor.sotlas` busca o Report Descriptor real via EP0 usando `GET_DESCRIPTOR`, `bmRequestType=0x81`, `wValue=0x2200`, `wIndex=interface` e o `wDescriptorLength` descoberto no HID descriptor;
- o descriptor real é validado antes de `XHCI_SET_CONFIGURATION_READY`;
- Boot protocol serve apenas como checagem de consistência da Application Usage, não como fonte do layout;
- sem Report ID, o input report calculado deve caber no max packet do Interrupt IN endpoint;
- nenhum mock substitui a leitura real no QEMU.

Markers:
```text
BAKEN:USB_HID_DESCRIPTOR_READY
BAKEN:USB_HID_DESCRIPTOR_FAILED
```

O marker READY foi adicionado ao smoke geral e ao gate SMP; FAILED é terminal para essa prova. A `main` permanece em `ead13903`/runtime `7803447a` até CI + SMP 3/3 + NVMe-only fecharem no mesmo SHA desta branch.

## Próximos passos após HID-1

- HID-2: field map por Report ID/Usage e decoder genérico de Input reports;
- HID-3: fila/event model unificada para keyboard, mouse, touchpad e touchscreen;
- HID-4: lifecycle/hot-plug xHCI;
- I2C-HID somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
