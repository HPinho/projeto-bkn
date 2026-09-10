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

## Baseline de runtime certificada

```text
a2e04a7858443a837488ff39fc2c26df4261fa58
test(hid): scope HID-2 runtime order assertion
```

O runtime HID-2 foi introduzido em `7e3008ae`; `a2e04a78` alterou apenas o guardrail final e é o SHA certificado/promovido.

- CI #1063 / `34501892035` ✅;
- SMP #166 / `34501892066` ✅ — 3/3 boots;
- NVMe-only #263 / `34501892022` ✅.

`89640db8` é o commit documental posterior de certificação HID-2.

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

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 permanecem fechados. Checkpoint final `7803447a`; os gates HID continuam reexercitando essa base.

---

# HID / input de produção

## HID-0 — Boot HID xHCI

**✅ COMPROVADO.** xHCI enumera HID Boot keyboard/mouse, configura Interrupt IN e prova report real no QEMU.

## HID-1 — Report Descriptor genérico

**✅ COMPROVADO em `1b3f94cc`.** Report Descriptor real via EP0, parser bounded/transport-agnostic e marker `BAKEN:USB_HID_DESCRIPTOR_READY`.

## HID-2 — Field map / decoder genérico

**✅ COMPROVADO em `a2e04a78`.** Field map por Report ID, Usage, offsets/flags, sign extension e validação exata de Interrupt IN. Marker `BAKEN:USB_HID_INPUT_MAP_READY`.

Histórico HID-2: SMP #165 `34501501476` falhou somente no guardrail textual antes de build/QEMU; `a2e04a78` corrigiu o escopo da asserção sem mudar runtime. CI #1063 + SMP #166 3/3 + NVMe #263 ficaram verdes e `main` foi promovida por fast-forward.

## HID-3 — modelo/fila unificada de input

**⏳ EM VALIDAÇÃO na branch `hid3-validation`.**

Candidato de runtime:
```text
51631f23f8ffa3bd2593c405bfee90f0e5f2fe32
feat(hid): add unified input event model
```

Escopo:
- novo `input_event.sotlas`: ABI comum de eventos e fila FIFO fixed-capacity de 512 entradas, sem heap;
- core de eventos não importa HID, xHCI, DMA ou ACPI;
- classes generic/keyboard/pointer/touch e tipos key down/up, button down/up, relative/absolute;
- sequência monotônica, `peek`, `pop`, contador e diagnóstico de overflow;
- novo `hid_input_events.sotlas`: tradutor transport-agnostic HID-2 -> `InputEvent`;
- estado de teclas e botões separado por Report ID, evitando releases fabricados entre reports compostos;
- teclado: Usage Page 0x07, transições reais e Usage 0 tratado como No Event;
- campos Variable só são considerados pressionados com valor diferente de zero;
- mouse: Button Page 0x09 + X/Y/Wheel relativos da Generic Desktop Page;
- reports continuam obrigatoriamente validados/decodificados pelo HID-2 antes da tradução;
- xHCI inicializa HID-3 somente depois do mapa HID-2 real;
- Interrupt IN real passa por HID-3 antes do fallback Boot legado;
- o fallback Boot e a prova física QEMU da tecla A permanecem intactos.

Provas novas:
```text
BAKEN:USB_HID_EVENT_MODEL_READY
BAKEN:USB_HID_EVENT_READY
```

`USB_HID_EVENT_MODEL_READY` prova que o core/fila foi inicializado sobre o mapa real. `USB_HID_EVENT_READY` só é emitido quando um Interrupt IN real aumenta o número de eventos publicados; report neutro não satisfaz esse gate. CI/NVMe continuam injetando `sendkey a`, então o smoke exige ambos os markers além do `STEP=W` existente.

Falhas dedicadas:
```text
BAKEN:USB_HID_EVENT_MODEL_FAILED
BAKEN:USB_HID_EVENT_FAILED
```

Critério de promoção HID-3: CI principal + SMP 3/3 + NVMe-only verdes no mesmo SHA final da branch, sem relaxar os gates HID-0/1/2 nem qualquer invariante do Kernel Core.

## Depois do HID-3

- HID-4: concorrência/lifecycle, attach/detach/recovery e múltiplos devices;
- I2C-HID somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
