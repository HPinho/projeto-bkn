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

---

# Atualização operacional — 2026-09-13 / Address Device FAILED certificado

A entrada anterior de candidato foi encerrada sem falhas.

```text
d0b8d98bbe8d1249f837519ef28e5022b1eb96d9
fix(xhci): quiesce failed address state by epoch
```

Status final do SHA:

- CI #1207 ✅
- SMP #310 ✅
- NVMe #407 ✅
- HID Dual-device #66 ✅

Portanto `d0b8d98b...` passa a ser a **baseline certificada 4/4** para recovery lógico Address Device em enumeração `FAILED`. Não houve gate vermelho e nenhuma correção intermediária foi necessária.

Escopo efetivamente certificado:

- exact-epoch + `FAILED` para Address Device;
- estado neutro pode ser reconhecido como já limpo sem adotar epoch;
- stale/live state de outro epoch falha fechado;
- cleanup após `Disable Slot` e após recovery dos descriptors;
- EP0, Evaluate Context, SET_CONFIGURATION, Configure Endpoint, HID Report DMA, Transfer Ring, arena Device/Input Context e Slot ID continuam reservados.

## Novo candidato — FAILED EP0 logical cleanup

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Mudanças deste microcorte:

- `kernel/src/drivers/xhci_ep0.sotlas`
  - `xhci_ep0_failed_slot_matches()` exige Device Table válida, mesmo epoch e estado `FAILED`;
  - `xhci_ep0_release_failed_for_epoch()` limpa somente o estado lógico EP0 do epoch correspondente;
  - `xhci_ep0_failed_release_complete_for()` torna retries idempotentes;
  - se EP0 nunca foi publicado, estado neutro é aceito como cleanup já concluído;
  - estado vivo de outro epoch não é sobrescrito;
  - o epoch armazenado nunca é alterado pelo cleanup FAILED.
- `kernel/src/drivers/xhci_hid_enumeration.sotlas`
  - recovery passa a executar `Configuration Descriptor → Device Descriptor → EP0 lógico → Address lógico` após `Disable Slot` confirmado;
  - o retorno do orquestrador exige também `ep0_released`.
- `tests/test_xhci_failed_ep0_cleanup.py`
  - prova exact-epoch + FAILED;
  - prova separação do helper `DETACH_PENDING`;
  - prova ausência de DMA/context/ring free;
  - prova a ordem do recovery.

### Recursos que permanecem deliberadamente vivos

- EP0 Ring físico dentro da arena;
- Device Context;
- Input Context;
- HID Transfer Ring;
- HID Report Descriptor DMA/estado ainda não fechado pelo recovery FAILED;
- Configure Endpoint e SET_CONFIGURATION state;
- Evaluate Context state;
- Device Table entry, Slot ID e associação da porta.

Nenhuma mudança de parser, lexer, semântica ou lowering de `HPinho/LangSotlas` é necessária neste corte.

## Continuação depois deste gate

Se o novo SHA fechar 4/4: implementar **Evaluate Context logical cleanup exact-epoch em FAILED**. Se falhar, congelar a `main`, registrar o SHA + workflow/step + causa neste apêndice e fazer somente a correção no candidato seguinte antes de qualquer avanço funcional.

---

# Atualização operacional — 2026-09-13 / EP0 FAILED certificado

O candidato EP0 foi encerrado sem falhas:

```text
3248fcd86581a5e8822564dcbd0d71eb60d2c6ed
fix(xhci): quiesce failed EP0 state by epoch
```

Status final do SHA:

- CI #1208 ✅
- SMP #311 ✅
- NVMe #408 ✅
- HID Dual-device #67 ✅

`3248fcd...` é, portanto, a baseline certificada 4/4 para o cleanup lógico EP0 em enumeração `FAILED`. Não houve gate vermelho nem commit corretivo intermediário.

Escopo certificado:

- exact `slot_id + epoch + FAILED`;
- retry idempotente para EP0 já neutro;
- nenhuma adoção/reescrita de epoch stale;
- desmontagem apenas de `ready`, enqueue, PCS, correlação do Status TRB e seleção global;
- nenhum EP0 Ring, Device/Input Context, DMA, Slot ID ou porta liberados;
- LangSotlas permaneceu inalterado.

## Novo candidato — FAILED Evaluate Context logical cleanup

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Mudanças deste microcorte:

- `kernel/src/drivers/xhci_evaluate_context.sotlas`
  - adiciona `xhci_evaluate_context_failed_slot_matches()` para validar Device Table, epoch e estado `FAILED`;
  - adiciona `xhci_evaluate_context_release_failed_for_epoch()`;
  - adiciona `xhci_evaluate_context_failed_release_complete_for()`;
  - zera somente `LAST_EP0_MAX_PACKET` e `COMMAND_SUBMITTED`;
  - nunca chama `xhci_evaluate_context_reset_slot()` durante recovery FAILED;
  - nunca altera `XHCI_EVALUATE_CONTEXT_EPOCHS` durante cleanup;
  - estado neutro de uma etapa não publicada é aceito como já limpo;
  - estado vivo de outro epoch falha fechado.
- `kernel/src/drivers/xhci_hid_enumeration.sotlas`
  - recovery após `Disable Slot` passa a ordenar `Configuration Descriptor → Device Descriptor → Evaluate Context lógico → EP0 lógico → Address lógico`;
  - retorno exige `evaluate_released` além dos owners já certificados.
- `tests/test_xhci_failed_evaluate_context_cleanup.py`
  - prova exact-epoch + FAILED;
  - prova que `reset_slot` e assignment de epoch não aparecem no release;
  - prova ausência de access/free de contexts físicos e DMA;
  - prova separação de `DETACH_PENDING`;
  - prova a nova ordem de recovery.

### Refinamento de ordem

O corte EP0 anterior continua correto e certificado porque Evaluate Context permaneceu em quarentena e nenhum owner físico foi liberado. A partir deste microcorte, o teardown lógico explicita a dependência inversa `Evaluate Context → EP0 → Address`, deixando as camadas físicas preservadas até que todos os estados downstream estejam fechados.

### Recursos ainda deliberadamente vivos

- SET_CONFIGURATION state;
- Configure Endpoint state;
- HID Report Descriptor/Report DMA recovery ainda pendente onde aplicável;
- HID Transfer Ring;
- Device/Input Context e EP0 Ring;
- Device Table entry, Slot ID e associação da porta.

Nenhuma mudança em parser, lexer, semântica ou lowering de `HPinho/LangSotlas` foi necessária.

## Continuação depois deste gate

Se este SHA fechar 4/4, o próximo microcorte é **SET_CONFIGURATION logical cleanup exact-epoch em FAILED**. Se qualquer gate falhar, congelar a `main`, preservar o SHA reprovado + workflow/step + causa e fazer somente a correção antes de avançar.

---

# Atualização operacional — 2026-09-13 / Evaluate Context FAILED certificado

O candidato Evaluate Context foi encerrado sem falhas:

```text
dc7a1fa8a003f9050e8a40817e2a1453f8e69714
fix(xhci): quiesce failed evaluate context state by epoch
```

Status final do SHA:

- CI #1209 ✅
- SMP #312 ✅
- NVMe #409 ✅
- HID Dual-device #68 ✅

`dc7a1fa8...` passa a ser a baseline certificada 4/4 para o cleanup lógico Evaluate Context em enumeração `FAILED`. Não houve gate vermelho nem correção intermediária.

Escopo certificado:

- exact `slot_id + epoch + FAILED`;
- stale epoch aceito somente quando o estado Evaluate já está neutro;
- `EPOCHS` preservado e `reset_slot()` proibido no recovery;
- somente `LAST_EP0_MAX_PACKET` e `COMMAND_SUBMITTED` são neutralizados;
- nenhum Input/Device Context, EP0 Ring, DMA, Slot ID ou porta é liberado;
- ordem lógica após descriptors: Evaluate Context → EP0 → Address;
- LangSotlas permaneceu inalterado.

## Novo candidato — FAILED SET_CONFIGURATION logical cleanup

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Mudanças deste microcorte:

- `kernel/src/drivers/xhci_set_configuration.sotlas`
  - adiciona validação exact-epoch + `FAILED` dedicada;
  - adiciona `xhci_set_configuration_release_failed_for_epoch()` e completion verifier;
  - limpa somente `ready`, `value` e `ACTIVE_SLOT_ID` do mesmo slot;
  - preserva `epoch` e nunca chama `xhci_set_configuration_prepare_state()` durante recovery;
  - stale epoch só é aceito se o estado já estiver totalmente neutro.
- `kernel/src/drivers/xhci_hid_enumeration.sotlas`
  - recovery passa a ordenar `Configuration Descriptor → Device Descriptor → SET_CONFIGURATION lógico → Evaluate Context lógico → EP0 lógico → Address lógico`;
  - retorno exige também `set_configuration_released`.
- `tests/test_xhci_failed_set_configuration_cleanup.py`
  - prova exact-epoch + FAILED;
  - prova ausência de epoch adoption/prepare_state;
  - prova que nenhum control transfer, wait de EP0, descriptor init, command ou free físico ocorre;
  - prova a ordem do recovery e separação de `DETACH_PENDING`.

### Recursos ainda em quarentena

- Configure Endpoint state;
- HID Report Descriptor/Report DMA onde aplicável;
- HID Transfer Ring;
- Device/Input Context e EP0 Ring;
- Device Table entry, Slot ID e associação da porta.

Nenhuma mudança em `HPinho/LangSotlas` foi necessária.

## Continuação depois deste gate

Se este SHA fechar 4/4, avançar para **Configure Endpoint logical cleanup exact-epoch em FAILED**, sem chamar a primitiva física `xhci_configure_endpoint_drop_hid_for_slot()` depois de `Disable Slot`. Qualquer falha congela `main` e exige correção-only registrada antes de novo avanço.
