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
1b3f94ccca5e399550d0951fc2c9f133a768440c
feat(hid): parse real report descriptors
```

- CI #1059 / `34497000191` ✅;
- SMP #162 / `34497000136` ✅ — 3/3 boots;
- NVMe-only #259 / `34497000185` ✅.

`a16e515b` é somente o commit documental de certificação posterior. A branch `hid2-validation` parte exatamente desse estado.

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

AML-0..AML-8 permanecem fechados. O checkpoint AML final `7803447a` passou CI #1056 + SMP #159 3/3 + NVMe #256 e voltou a ser exercitado pelos gates do HID-1.

---

# HID / input de produção

## HID-0 — Boot HID xHCI

**✅ COMPROVADO.** xHCI enumera HID Boot keyboard/mouse, configura Interrupt IN e prova report real no QEMU.

## HID-1 — Report Descriptor genérico

**✅ COMPROVADO em `1b3f94cc`.**

- parser bounded e transport-agnostic de HID Report Descriptor;
- EP0 busca o Report Descriptor real com `GET_DESCRIPTOR(Report)`;
- Boot protocol não inventa layout;
- `BAKEN:USB_HID_DESCRIPTOR_READY` obrigatório;
- `BAKEN:USB_HID_DESCRIPTOR_FAILED` terminal.

## HID-2 — Field map / decoder genérico

**⏳ EM VALIDAÇÃO na branch `hid2-validation`.**

Escopo do candidato:
- novo `kernel/src/drivers/hid_input_report.sotlas`, independente de xHCI/DMA/ACPI;
- até 512 campos, 256 Report IDs e 256 usages locais por Main item, sem heap;
- mapa por Report ID, bit offset, bit width, Usage Page/Usage, flags Constant/Data, Array/Variable, Absolute/Relative e Null State;
- Usage list segue ordem do descriptor; quando há menos usages que controles Variable, o último Usage é repetido;
- Usage Minimum/Maximum cria range bounded; arrays não contíguos sem range explícito continuam com valor bruto e usage unresolved, nunca fabricado;
- Logical Minimum/Maximum preservados; valores são sign-extended quando o mínimo lógico é negativo;
- Report ID é byte de prefixo do wire report e não altera o bit offset do payload;
- comprimento real do Interrupt IN deve coincidir exatamente com a geometria do Report ID;
- `Buffered Bytes`, Delimiter, Global Push/Pop e construções fora do subconjunto permanecem fail-closed;
- self-test cobre teclado Boot, mouse com X/Y relativos signed, Report ID e truncamento;
- `xhci_hid_descriptor` constrói o mapa a partir dos mesmos bytes reais já lidos no HID-1;
- `xhci_hid_report` valida cada report real pelo mapa HID-2 antes do fallback Boot legado;
- caminho existente da tecla `A` continua obrigatório no QEMU.

Markers:
```text
BAKEN:USB_HID_INPUT_MAP_READY
BAKEN:USB_HID_INPUT_MAP_FAILED
```

O smoke CI/NVMe exige `USB_HID_INPUT_MAP_READY`; `USB_HID_INPUT_MAP_FAILED` é terminal. O SMP continua provando o caminho porque `USB_HID_DESCRIPTOR_READY` só é publicado depois do mapa HID-2 estar pronto; não há relaxamento do gate SMP.

## Critério de promoção HID-2

1. CI principal verde;
2. SMP 3/3 verde;
3. NVMe-only verde;
4. todos no mesmo SHA da `hid2-validation`;
5. manter `USB_HID_DESCRIPTOR_READY`, prova real da tecla `A` e todos os invariantes do Kernel Core;
6. registrar SHA/run IDs aqui e no roadmap antes do fast-forward de `main`.

Depois do HID-2:
- HID-3: event model/fila unificada baseada nos campos decodificados;
- HID-4: lifecycle/hot-plug e múltiplos devices;
- I2C-HID somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
