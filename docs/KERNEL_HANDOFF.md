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
2775c12a1c36dbcf9f88cee25de0c8ad98242d3c
docs: track HID-3 input event validation
```

O runtime HID-3 foi introduzido em `51631f23f8ffa3bd2593c405bfee90f0e5f2fe32`; `2775c12a` acrescenta somente documentação de validação e é o head efetivamente promovido para `main` após os três gates verdes.

- CI #1066 / `34509266662` ✅;
- SMP #169 / `34509266645` ✅ — 3/3 boots, todos `stop_reason=complete`;
- NVMe-only #266 / `34509266646` ✅.

O smoke CI/NVMe no mesmo head exige `BAKEN:USB_HID_EVENT_MODEL_READY` e `BAKEN:USB_HID_EVENT_READY`, além dos markers HID-1/HID-2 e `BAKEN:BARE_METAL_READY`. O SMP 3/3 preservou `BAKEN:SMP_PROCESS_MIGRATED` e `BAKEN:SMP_FPU_MIGRATION_READY`.

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

**✅ COMPROVADO em `2775c12a`.**

Runtime:
```text
51631f23f8ffa3bd2593c405bfee90f0e5f2fe32
feat(hid): add unified input event model
```

Head certificado/promovido:
```text
2775c12a1c36dbcf9f88cee25de0c8ad98242d3c
docs: track HID-3 input event validation
```

Escopo comprovado:
- `input_event.sotlas`: ABI comum de eventos e fila FIFO fixed-capacity de 512 entradas, sem heap;
- core de eventos sem import de HID, xHCI, DMA ou ACPI;
- classes generic/keyboard/pointer/touch e tipos key down/up, button down/up, relative/absolute;
- sequência monotônica, `peek`, `pop`, contador e diagnóstico de overflow;
- `hid_input_events.sotlas`: tradutor transport-agnostic HID-2 -> `InputEvent`;
- estado de teclas e botões separado por Report ID;
- teclado: Usage Page 0x07, transições reais e Usage 0 tratado como No Event;
- campos Variable só são considerados pressionados com valor diferente de zero;
- mouse: Button Page 0x09 + X/Y/Wheel relativos da Generic Desktop Page;
- HID-2 continua obrigatoriamente validando/decodificando o Interrupt IN antes da tradução;
- xHCI inicializa HID-3 somente depois do mapa HID-2 real;
- Interrupt IN real passa pelo tradutor HID-3 antes do fallback Boot legado;
- fallback Boot e a prova física QEMU da tecla A permanecem intactos.

Provas:
```text
BAKEN:USB_HID_EVENT_MODEL_READY
BAKEN:USB_HID_EVENT_READY
```

`USB_HID_EVENT_MODEL_READY` prova que o core/fila foi inicializado sobre o mapa real. `USB_HID_EVENT_READY` só é emitido quando um Interrupt IN real aumenta o número de eventos publicados. Como CI #1066 e NVMe #266 passaram o smoke que exige ambos os markers, a injeção `sendkey a` produziu a prova real de evento normalizado. SMP #169 confirmou ainda 3/3 boots do Kernel Core no mesmo candidato integrado.

Certificação:
- CI #1066 / `34509266662` ✅;
- SMP #169 / `34509266645` ✅ — 3/3;
- NVMe-only #266 / `34509266646` ✅.

## Próximo: HID-4 — lifecycle / múltiplos devices

**⬜ PLANEJADO.** A próxima etapa deve tratar concorrência e ciclo de vida do input sem reabrir HID-0..HID-3:
- identidade estável por dispositivo/interface, não somente um primeiro HID global;
- attach/detach e invalidação segura de estado/fila;
- múltiplos HID simultâneos sem colisão de Report ID entre dispositivos;
- cancelamento/recovery de Interrupt IN e endpoint lifecycle;
- hot-plug com bounds e diagnóstico fail-closed;
- preservar o event model genérico como fronteira entre transportes e consumers.

I2C-HID continua somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
