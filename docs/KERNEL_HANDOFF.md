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

O runtime HID-2 foi introduzido em `7e3008ae43af73b89ea8cd3fbb03c8f3a45c920b`; `a2e04a78` altera apenas o guardrail de teste/documentação e é o SHA final certificado/promovido.

- CI #1063 / `34501892035` ✅;
- SMP #166 / `34501892066` ✅ — 3/3 boots independentes completos;
- NVMe-only #263 / `34501892022` ✅.

Em todos os boots SMP, `BAKEN:USB_HID_INPUT_MAP_READY` foi observado antes de `BAKEN:USB_HID_DESCRIPTOR_READY`, e a prova prosseguiu até `BAKEN:SMP_FPU_MIGRATION_READY` sem relaxar os invariantes do Kernel Core.

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

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 permanecem fechados. O checkpoint AML final `7803447a` passou CI #1056 + SMP #159 3/3 + NVMe #256 e continua sendo reexercitado pelos gates atuais.

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

Prova HID-1: CI #1059 / `34497000191` ✅; SMP #162 / `34497000136` ✅ 3/3; NVMe #259 / `34497000185` ✅.

## HID-2 — Field map / decoder genérico

**✅ COMPROVADO em `a2e04a78`.**

Implementação de runtime em `7e3008ae`:
- `hid_input_report.sotlas` independente de xHCI/DMA/ACPI;
- até 512 campos, 256 Report IDs e 256 usages locais por Main item, sem heap;
- mapa por Report ID, bit offset/width, Usage Page/Usage e flags Main;
- Usage list e Usage Minimum/Maximum bounded;
- Logical Minimum/Maximum + sign extension;
- Report ID é prefixo do wire report, separado dos offsets do payload;
- comprimento real do Interrupt IN deve coincidir exatamente com a geometria do Report ID;
- arrays não contíguos sem range demonstrável permanecem usage-unresolved;
- Buffered Bytes/Delimiter/Push/Pop continuam fail-closed;
- self-test cobre teclado Boot, mouse signed-relative, Report ID e truncamento;
- mapa é construído sobre os bytes reais do Report Descriptor HID-1;
- Interrupt IN real é validado pelo mapa antes do fallback Boot;
- `BAKEN:USB_HID_INPUT_MAP_READY` obrigatório no smoke;
- `BAKEN:USB_HID_INPUT_MAP_FAILED` terminal.

### Histórico de validação HID-2

- candidato inicial `7e3008ae43af73b89ea8cd3fbb03c8f3a45c920b`;
- SMP #165 / `34501501476` ❌ em `Verify SMP Contracts`, antes de build/QEMU;
- causa: o guardrail `test_hid2_map_uses_real_descriptor_bytes_before_descriptor_ready` comparava offsets de escopos diferentes porque `text.index("xhci_hid_input_map_emit_ready_marker()")` encontrava a definição da função antes da chamada em `probe_internal`;
- correção `a2e04a7858443a837488ff39fc2c26df4261fa58`: busca limitada ao corpo de `xhci_hid_descriptor_probe_internal`; nenhuma linha do runtime HID-2, Kernel Core, storage ou AML foi alterada;
- certificação final no mesmo SHA `a2e04a78`: CI #1063 ✅, SMP #166 ✅ 3/3, NVMe #263 ✅;
- `main` promovida por fast-forward diretamente para `a2e04a78`.

## Próximo estágio — HID-3

**⬜ PLANEJADO.** Criar um modelo/fila unificada de input consumindo os campos já decodificados, sem acoplar a fila ao xHCI e sem remover a prova Boot existente. O objetivo é publicar eventos normalizados de keyboard/mouse e preparar extensão futura para touch, deixando lifecycle/hot-plug e múltiplos devices para HID-4.

Depois:
- HID-4: lifecycle/hot-plug e múltiplos devices;
- I2C-HID somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
