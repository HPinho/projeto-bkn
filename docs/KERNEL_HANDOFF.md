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
1b3f94ccca5e399550d0951fc2c9f133a768440c
feat(hid): parse real report descriptors
```

- CI #1059 / `34497000191` ✅;
- SMP #162 / `34497000136` ✅ — 3/3 boots;
- NVMe-only #259 / `34497000185` ✅.

A PR #17 foi integrada por fast-forward no próprio SHA validado. O commit documental posterior não substitui a baseline de runtime.

## Baseline anterior

```text
7803447a4c2179d088948b3c4288b6e3655bc1d5
fix(acpi): preserve bool type in PRT lowering
```

AML-0..AML-8 permanecem certificados nesse checkpoint e foram novamente exercitados pelos gates do HID-1.

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

**✅ CORE CONCLUÍDO E CERTIFICADO.**

AML-0..AML-8 estão fechados. AML-7 entrega OperationRegion/Field bounded para SystemMemory/SystemIO/PCIConfig; AML-8 entrega `_PIC`, `_PRT` e `_S5` no subconjunto fail-closed. EC/GPE/GlobalLock e transições físicas de energia ficam para power/hot-plug.

Histórico final AML: CI #1055 / `34491870501` detectou lowering `int* -> _Bool*`; a tipagem explícita de `source_is_link` produziu `7803447a`, aprovado por CI #1056 + SMP #159 3/3 + NVMe #256.

---

# HID / input de produção

## HID-0 — Boot HID xHCI

**✅ COMPROVADO.**

O xHCI enumera HID Boot keyboard/mouse, configura Interrupt IN e prova report real em QEMU.

## HID-1 — Report Descriptor genérico

**✅ COMPROVADO em `1b3f94cc`.**

Implementado:
- `kernel/src/drivers/hid_report_descriptor.sotlas` independente de transporte;
- parser bounded de HID short items: máximo 4096 bytes, 512 itens e collection depth 16;
- valida item size/type/tag e falha fechado em truncamento, reserved/long item e Push/Pop não suportado;
- extrai Usage Page/Application para keyboard/mouse, ReportSize/ReportCount, Report ID e geometria input/output/feature;
- `kernel/src/drivers/xhci_hid_descriptor.sotlas` busca o Report Descriptor real via EP0 com `GET_DESCRIPTOR`, `bmRequestType=0x81`, `wValue=0x2200`, `wIndex=interface` e comprimento do HID descriptor;
- descriptor real é validado antes de publicar `XHCI_SET_CONFIGURATION_READY`;
- Boot protocol serve apenas como checagem de consistência, nunca como descriptor sintético;
- marker `BAKEN:USB_HID_DESCRIPTOR_READY` é obrigatório no smoke e SMP;
- `BAKEN:USB_HID_DESCRIPTOR_FAILED` é terminal para essa prova.

Prova no mesmo SHA:
- CI #1059 / `34497000191` ✅ — suíte, grafo, build PE, ISO e QEMU;
- SMP #162 / `34497000136` ✅ — 3/3 e invariantes Kernel Core;
- NVMe #259 / `34497000185` ✅.

## Próximo incremento — HID-2

**⬜ PLANEJADO / próxima branch.**

Objetivo: construir field map bounded por Report ID/Usage e decoder genérico de Input reports. O decoder deverá operar sobre a geometria real do HID-1, preservar o caminho Boot atual como fallback e nunca ler além do tamanho real recebido pelo Interrupt IN.

Depois:
- HID-3: fila/event model unificada para keyboard, mouse, touchpad e touchscreen;
- HID-4: lifecycle/hot-plug xHCI;
- I2C-HID somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
