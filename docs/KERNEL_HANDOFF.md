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

O runtime HID-3 foi introduzido em `51631f23f8ffa3bd2593c405bfee90f0e5f2fe32`; `2775c12a` acrescenta somente documentação de validação e é o head efetivamente promovido após os três gates verdes.

- CI #1066 / `34509266662` ✅;
- SMP #169 / `34509266645` ✅ — 3/3 boots, todos `stop_reason=complete`;
- NVMe-only #266 / `34509266646` ✅.

`75886e96` é somente o commit documental posterior de certificação HID-3 e é a base da branch HID-4.

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

**⏳ EM VALIDAÇÃO na branch `hid4-validation`.**

Candidato de runtime original:
```text
8f34ae132454ef87afae67288b632886131acfe4
feat(hid): add generation-safe input lifecycle
```

Escopo desta fatia:
- novo `input_device.sotlas`, registro transport-agnostic fixed-capacity de 16 devices e sem heap;
- identidade composta por `device_id + generation`; device_id pode ser reutilizado somente com geração nova;
- estados `EMPTY -> ATTACHED -> ACTIVE`, além de `FAILED` e `DETACHED`;
- attach/activate/fail/detach/snapshot/is_active protegidos por IRQ-save + spinlock;
- metadata de transporte preserva kind, instance, address e interface sem importar xHCI;
- `InputEvent` passa a carregar `device_id` e `device_generation`;
- fila HID-3 deixa de ser caller-serialized: publish/peek/pop/count/purge são SMP/IRQ-safe;
- publicação revalida a geração ativa já dentro do lock da fila para fechar corrida detach-vs-publish;
- detach invalida primeiro a geração, depois purga eventos antigos e por último limpa o estado HID;
- `hid_input_events.sotlas` separa estado por device x Report ID e possui bind/unbind generation-safe;
- processamento HID continua transport-agnostic e HID-2 permanece autoridade de validação/decodificação;
- xHCI registra a primeira interface HID real no generic registry após HID-2/HID-3 estarem prontos;
- o report Interrupt IN usa a identidade registrada antes de publicar qualquer evento;
- fallback Boot e prova física QEMU da tecla A permanecem intactos.

Novo gate runtime:
```text
BAKEN:USB_HID_DEVICE_READY
```

Falha dedicada:
```text
BAKEN:USB_HID_DEVICE_FAILED
```

O smoke CI/NVMe exige `USB_HID_DEVICE_READY`; o SMP local/workflow também passa a exigir o marker em todos os três boots, além de HID-1/HID-2/HID-3 e das provas do Kernel Core.

### Histórico de validação HID-4a

Primeiro head de validação: `ebf21182b33252c7bb6270c82eb25441b1746487`.

- CI #1069 / `34513631621` ❌;
- SMP #172 / `34513631581` ❌;
- NVMe-only #269 / `34513631641` ❌.

Os três gates falharam pela mesma causa antes de qualquer execução QEMU. Os contratos, incluindo os novos testes HID-4a, e `compiler.py check kernel/src/main.sotlas` passaram nos gates que chegaram a essa etapa. O `compiler.py build`, porém, reparseia os módulos para emissão dos headers C e rejeitou `kernel/src/drivers/xhci_hid_descriptor.sotlas:235:9` com `expressão inválida: 'return'`. A causa era um `return false` dentro de um `if` usado como expressão para inicializar `device_class`.

Correção mínima:
```text
a4762cf614a0748336040be8d15e7f352b17f25f
fix(hid): avoid return in conditional expression
```

A correção preserva a semântica: keyboard -> `INPUT_DEVICE_CLASS_KEYBOARD`, mouse -> `INPUT_DEVICE_CLASS_POINTER` e protocolo não suportado continua fail-closed. Não altera lifecycle, locking, ABI, Kernel Core, AML ou storage.

Head final atualmente em revalidação:
```text
f9a2bf61a2b15ae3518e5a53f42827ec0ced5027
docs: record HID-4a parser gate failure
```

Gates disparados no mesmo head final:
- CI #1071 / `34516135043` ⏳;
- SMP #174 / `34516135064` ⏳;
- NVMe-only #271 / `34516135048` ⏳.

HID-4a permanece **não certificado** até os três fecharem verdes no mesmo `f9a2bf61` (ou em um head corretivo posterior, caso surja outra falha).

### Limite honesto desta fatia

HID-4a **não declara xHCI multi-device completo**. `xhci_slot`, `xhci_context`, `xhci_address`, `xhci_hid_context`, `xhci_hid_report` e o mapa HID-2 ainda possuem singletons. O objetivo desta fatia é estabelecer identidade/lifecycle/concurrency corretos antes de migrar esses estados para estruturas per-device.

### Próximas fatias HID-4

- HID-4b: transformar o mapa/decoder HID-2 em contexto per-device, eliminando o singleton do Report Descriptor/field map;
- HID-4c: converter slot/context/address/HID rings xHCI para tabelas por slot/interface e enumeração de múltiplos devices;
- HID-4d: attach/detach físico, cancel/recovery de Interrupt IN e hot-plug/re-enumeração bounded/fail-closed.

Critério de promoção HID-4a: CI principal + SMP 3/3 + NVMe-only verdes no mesmo head final da branch. Até isso ocorrer, `main` permanece na baseline HID-3 certificada.

I2C-HID continua somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
