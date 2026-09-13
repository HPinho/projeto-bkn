# Baken OS / Sotlas — Kernel Handoff Appendix (autoritativo, append-only)

Este arquivo complementa `docs/KERNEL_HANDOFF.md` e registra o estado operacional corrente sem apagar o histórico anterior. Sempre que um gate falhar, a entrada seguinte deve preservar a falha e registrar qual correção foi aplicada.

## Estado de retomada — 2026-09-13

Branch operacional: **`main`**.

Última baseline certificada antes do candidato atual:

```text
e39db2528de7bf2d7381befc696680f6d62205bd
fix(xhci): harden HID report DMA prepare publication
```

Gates:

- CI #1206 ✅
- SMP #309 ✅
- NVMe #406 ✅
- HID Dual-device #65 ✅

Não houve necessidade de alterar `HPinho/LangSotlas` nesse checkpoint.

## Candidato atual — FAILED Address Device logical cleanup

Estado: **⏳ aguardando certificação 4/4**.

Alterações funcionais deste corte:

- `kernel/src/drivers/xhci_address.sotlas`
  - adiciona validação `FAILED + slot_id + epoch` exata;
  - adiciona `xhci_address_release_failed_for_epoch()`;
  - adiciona `xhci_address_failed_release_complete_for()`;
  - preserva o epoch armazenado e nunca adota/reescreve estado stale;
  - reconhece estado já vazio como cleanup idempotente quando a etapa Address Device não chegou a ser publicada;
  - limpa apenas `ready`, `device_address` e seleção global legada do mesmo slot.
- `kernel/src/drivers/xhci_hid_enumeration.sotlas`
  - chama o cleanup Address Device somente depois da Command Completion de `Disable Slot`;
  - preserva a ordem Configuration Descriptor → Device Descriptor → Address lógico;
  - continua mantendo EP0/rings/contexts/Slot ID em quarentena.
- `tests/test_xhci_failed_address_cleanup.py`
  - prova exact-epoch/FAILED;
  - prova que stale epoch não é sobrescrito;
  - prova ausência de free físico neste corte;
  - prova a ordem do recovery após `Disable Slot`.

### O que este corte NÃO faz

- não libera HID Report Descriptor DMA;
- não libera HID Transfer Ring;
- não libera Device/Input Context;
- não libera EP0 Ring;
- não libera a entrada da Device Table, Slot ID ou porta;
- não altera o helper normal de detach `DETACH_PENDING`;
- não altera parser, lexer, semântica ou lowering de Sotlas.

## Regra de continuação

Enquanto os quatro gates deste candidato estiverem abertos, a `main` fica congelada neste microcorte.

Se houver falha, o próximo registro deve conter:

```text
SHA reprovado
→ workflow/run e step vermelho
→ causa técnica
→ correção aplicada
→ novo SHA candidato
```

Somente depois de 4/4 verde o próximo corte funcional será iniciado. A sequência planejada após Address Device é EP0 lógico FAILED → Evaluate Context lógico FAILED → SET_CONFIGURATION lógico FAILED → Configure Endpoint lógico FAILED → owners DMA/rings/contexts físicos → barrier/release de Slot ID e porta.
