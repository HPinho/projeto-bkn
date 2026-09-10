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
12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c
docs: note HID-4a revalidation runs
```

HID-4a está certificado e foi promovido para `main` por fast-forward, sem merge commit adicional.

- CI #1072 / `34516628427` ✅;
- SMP #175 / `34516628437` ✅ — 3/3 boots;
- NVMe-only #272 / `34516628445` ✅.

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

## HID-3 — modelo/fila unificada de input

**✅ COMPROVADO em `2775c12a`.** Runtime base `51631f23`; CI #1066 + SMP #169 3/3 + NVMe #266 verdes. O smoke exige `BAKEN:USB_HID_EVENT_MODEL_READY` e `BAKEN:USB_HID_EVENT_READY`; CI/NVMe continuam provando evento real via `sendkey a`.

## HID-4a — identidade, generation e lifecycle seguro

**✅ CERTIFICADO em `12c308b3`.**

Implementação:
- `input_device.sotlas`: registro transport-agnostic fixed-capacity de 16 devices, sem heap;
- identidade `device_id + generation`, impedindo stale handles após detach/re-attach;
- lifecycle ATTACHED/ACTIVE/FAILED/DETACHED;
- registry e fila protegidos com IRQ-save + spinlock;
- `InputEvent` carrega identidade da fonte;
- publicação revalida a identidade dentro do lock da fila;
- purge remove somente a geração desconectada;
- estado HID anterior particionado por device x Report ID;
- bind/unbind HID generation-safe;
- xHCI associa a interface real atual ao registry antes de aceitar Interrupt IN;
- marker `BAKEN:USB_HID_DEVICE_READY`; falha `BAKEN:USB_HID_DEVICE_FAILED`.

### Histórico de validação HID-4a

Primeiro candidato de validação `ebf21182b33252c7bb6270c82eb25441b1746487` falhou antes do QEMU:

- CI #1069 / `34513631621` ❌;
- SMP #172 / `34513631581` ❌;
- NVMe-only #269 / `34513631641` ❌.

Causa única: `compiler.py build` rejeitou `return false` dentro de um `if` usado como expressão em `xhci_hid_descriptor.sotlas`. Correção mínima:

```text
a4762cf614a0748336040be8d15e7f352b17f25f
fix(hid): avoid return in conditional expression
```

O runtime corrigido passou inclusive SMP #173 3/3. O head documental final `12c308b3` foi então revalidado integralmente com CI #1072 + SMP #175 3/3 + NVMe #272 verdes no mesmo SHA e promovido por fast-forward para `main`.

## HID-4b — mapa/decoder HID por device

**⏳ EM VALIDAÇÃO na branch `hid4b-validation`, baseada em `12c308b3`.**

Objetivo: remover o mapa HID-2 persistente singleton do caminho runtime sem reabrir HID-1/HID-3/HID-4a.

Implementação candidata:
- novo `hid_input_device_map.sotlas`, fixed-capacity e sem heap;
- até `INPUT_DEVICE_CAPACITY` snapshots HID-2 independentes, indexados por `device_id + generation`;
- campos, Report IDs e `expected_bytes` separados por device;
- parser HID-1 permanece stateless;
- builder HID-2 legado fica somente como scratch serializado durante construção do snapshot e é invalidado imediatamente depois;
- Interrupt IN, validação, decode e tradução deixam de consultar o singleton;
- self-test mantém simultaneamente um mapa de teclado e outro de mouse e prova isolamento cruzado;
- attach xHCI ocorre antes do build do mapa para fornecer identidade real;
- bind do event model ocorre somente depois do snapshot específico estar pronto;
- teardown segue `invalidate identity -> purge events -> clear HID event state -> remove device map`;
- novo marker `BAKEN:USB_HID_DEVICE_MAP_READY` e falha `BAKEN:USB_HID_DEVICE_MAP_FAILED`;
- CI, SMP e NVMe passam a exigir/validar essa camada.

### Limite explícito do HID-4b

HID-4b **não declara xHCI multi-device completo**. Slot, address/context, endpoint/ring e buffer de report do transporte ainda são singletons. A separação do mapa é pré-requisito para migrar esses recursos no HID-4c.

## Próximas fatias HID-4

- HID-4c: slot/context/address/HID rings/buffers xHCI por device/interface e enumeração de múltiplos HID simultâneos;
- HID-4d: detach físico, cancel/recovery de Interrupt IN e hot-plug/re-enumeração bounded/fail-closed.

Critério de promoção HID-4b: CI principal + SMP 3/3 + NVMe-only verdes no mesmo head final. Até isso ocorrer, `main` permanece em `12c308b3`.

I2C-HID continua somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
