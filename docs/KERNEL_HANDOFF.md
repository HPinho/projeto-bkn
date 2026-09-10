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

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 permanecem fechados. O checkpoint AML final `7803447a` passou CI #1056 + SMP #159 3/3 + NVMe #256 e voltou a ser exercitado pelos gates do HID-1.

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

**⏳ EM VALIDAÇÃO na PR #18 / branch `hid2-validation`.**

Candidato inicial:
```text
7e3008ae43af73b89ea8cd3fbb03c8f3a45c920b
feat(hid): decode mapped input reports
```

Escopo:
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
- `BAKEN:USB_HID_INPUT_MAP_READY` obrigatório no smoke CI/NVMe;
- `BAKEN:USB_HID_INPUT_MAP_FAILED` terminal.

### Validação HID-2 — histórico

- SMP #165 / run `34501501476` ❌ em `Verify SMP Contracts`, antes de build e QEMU.
- causa: erro no próprio guardrail `test_hid2_map_uses_real_descriptor_bytes_before_descriptor_ready`; `text.index("xhci_hid_input_map_emit_ready_marker()")` encontrou a definição da função, que aparece antes de `xhci_hid_descriptor_probe_internal`, e comparou offsets de escopos diferentes.
- o runtime não falhou e não chegou a ser compilado nesse gate.
- correção: o teste agora recorta apenas o corpo de `xhci_hid_descriptor_probe_internal` antes de verificar a ordem `map_build -> map_ready -> descriptor_store`.
- nenhuma linha do runtime HID-2, Kernel Core, storage ou AML foi alterada por essa correção.

## Critério de promoção HID-2

CI principal + SMP 3/3 + NVMe-only devem ficar verdes no mesmo SHA corrigido da PR #18. Depois, registrar SHA/run IDs aqui e no roadmap e fast-forward `main` somente para o runtime comprovado.

Depois do HID-2:
- HID-3: event model/fila unificada baseada nos campos decodificados;
- HID-4: lifecycle/hot-plug e múltiplos devices;
- I2C-HID somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
