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

---

# Atualização operacional — 2026-09-13 / SET_CONFIGURATION reprovado no CI #1210

O candidato funcional abaixo **não pode ser certificado 4/4**:

```text
3a45e9a777f9a823b621e2d74db68f4b4758cbf5
fix(xhci): quiesce failed set configuration state by epoch
```

Status observado:

- CI #1210 ❌ — `Run Complete Test Suite`;
- SMP #313 ✅;
- NVMe #410 ✅;
- HID Dual-device #69 ✅.

A suíte executou 1630 testes e terminou com 2 falhas, ambas em guardrails históricos:

- `test_xhci_failed_ep0_cleanup.py` exigia a substring contígua `ep0_released && address_released`;
- `test_xhci_failed_evaluate_context_cleanup.py` exigia a substring contígua `evaluate_released && ep0_released && address_released`.

O novo owner `set_configuration_released` foi corretamente inserido antes de Evaluate/EP0/Address, então a expressão de retorno deixou de possuir essas sequências textuais adjacentes. As verificações de ordem por posição continuaram válidas; os três gates runtime/build independentes fecharam verdes. Assim, a causa foi classificada como **guardrail antigo excessivamente dependente da formatação/composição da expressão de retorno**, não regressão funcional do recovery.

## Candidato correction-only

A correção subsequente:

- não altera nenhum `.sotlas` funcional;
- não altera LangSotlas;
- não altera workflows;
- muda apenas os dois guardrails antigos para localizar a expressão final `return` e verificar que os owners que cada guardrail certifica continuam incluídos nela;
- mantém integralmente as provas de ordem `Evaluate → EP0 → Address` e `EP0 → Address`;
- preserva o novo guardrail SET_CONFIGURATION sem relaxamento.

A `main` deve permanecer congelada no SHA correction-only até os quatro gates fecharem verdes. **Configure Endpoint continua bloqueado** até essa certificação.

---

# Atualização operacional — 2026-09-13 / correction-only SET_CONFIGURATION certificado

O commit de correção dos guardrails fechou **4/4**:

```text
483e06ac02ada1a5511de6a1a6b6bf4f00a22d0e
test(xhci): relax failed recovery return guardrails
```

Status final:

- CI #1211 ✅ — suíte completa, grafo modular, build nativo, ISO e QEMU principal;
- SMP #314 ✅;
- NVMe #411 ✅;
- HID Dual-device #70 ✅.

A falha do SHA `3a45e9a7...` continua preservada na entrada anterior. O correction-only não alterou kernel Sotlas, LangSotlas ou workflows; apenas corrigiu a fragilidade textual dos guardrails EP0/Evaluate. Com isso, a cadeia de SET_CONFIGURATION fica encerrada e o próximo microcorte funcional pode avançar.

## Novo candidato — FAILED Configure Endpoint logical cleanup

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Mudanças deste microcorte:

- `kernel/src/drivers/xhci_configure_endpoint.sotlas`
  - adiciona `xhci_configure_endpoint_failed_slot_matches()` com Device Table válida, `FAILED` e epoch exato;
  - adiciona `xhci_configure_endpoint_release_failed_for_epoch()` e completion verifier;
  - neutraliza somente `READY`, `DROPPED`, `DCI` e seleção global do slot;
  - preserva `XHCI_CONFIGURE_ENDPOINT_EPOCHS` sem adoção/reescrita;
  - estado de outro epoch só é aceito como já limpo quando o bookkeeping está completamente neutro;
  - `dropped=false` é estado lógico neutro e não representa prova de Drop Endpoint físico.
- `kernel/src/drivers/xhci_hid_enumeration.sotlas`
  - recovery passa a executar `SET_CONFIGURATION → Configure Endpoint lógico → Evaluate → EP0 → Address` depois dos descriptors;
  - retorno passa a exigir `configure_endpoint_released`.
- `tests/test_xhci_failed_configure_endpoint_cleanup.py`
  - prova exact-epoch + FAILED;
  - prova stale-neutral e ausência de epoch adoption;
  - proíbe no release FAILED a primitiva física Drop Endpoint, leitura de Output Context, escrita de Input Context, direct-map/CR3, command execute e frees;
  - prova que a primitiva física normal continua separada e intacta;
  - prova a ordem completa do recovery e a inclusão de todos os owners obrigatórios no retorno.
- `tests/test_xhci_failed_set_configuration_cleanup.py`
  - deixa de exigir adjacency entre owners no `return`, mantendo as provas de ordem e verificando presença individual na expressão final.

### Recursos que permanecem deliberadamente em quarentena

- HID Report Descriptor / Report DMA físico onde publicado;
- HID Transfer Ring;
- Device Context;
- Input Context;
- EP0 Ring físico;
- Device Table entry, Slot ID e associação da porta.

Nenhum ajuste de parser, lexer, semântica ou lowering em `HPinho/LangSotlas` foi necessário para este corte.

## Continuação depois deste gate

Se o novo SHA fechar 4/4, o próximo passo é **auditar e fechar o owner HID Report Descriptor / Report DMA em FAILED** antes de liberar HID Transfer Ring ou a arena Device/Input Context. Se qualquer gate falhar, congelar `main`, registrar SHA + workflow/step + causa e fazer somente a correção no próximo commit.

---

# Atualização operacional — 2026-09-13 / Configure Endpoint FAILED certificado

O microcorte Configure Endpoint fechou **4/4** no mesmo SHA:

```text
da3c8ac27e6d9545609d801ca95839e62102116e
fix(xhci): quiesce failed configure endpoint state by epoch
```

Status final:

- CI #1212 ✅;
- SMP #315 ✅;
- NVMe #412 ✅;
- HID Dual-device #71 ✅.

O escopo certificado é estritamente lógico: exact `FAILED + slot_id + epoch`, neutralização de `READY/DROPPED/DCI/active slot`, preservação do epoch e ausência completa de Drop Endpoint físico, Input/Output Context access, command xHCI, DMA ou free. O lifecycle normal de `DETACH_PENDING` permanece separado. LangSotlas continuou inalterado.

## Novo candidato — FAILED Transfer mailbox/result cleanup

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Mudanças planejadas/aplicadas neste microcorte:

- `kernel/src/drivers/xhci_transfer.sotlas`
  - adiciona gate próprio `FAILED + slot_id + epoch`;
  - reconhece estado completamente neutro como idempotente;
  - aceita para mutação somente mailbox/result cujos epochs sejam `0` ou o epoch FAILED atual;
  - qualquer epoch estrangeiro falha fechado;
  - limpa apenas `XHCI_TRANSFER_PENDING_EVENTS`, `XHCI_TRANSFER_RESULTS` e seleção `ACTIVE_SLOT_ID`;
  - não consome Event Ring, não faz MMIO e não toca DMA/rings/contexts.
- `kernel/src/drivers/xhci_hid_enumeration.sotlas`
  - chama o cleanup Transfer imediatamente depois da Command Completion de `Disable Slot` e antes dos releases de descriptors;
  - retorno passa a exigir `transfer_released`.
- `tests/test_xhci_failed_transfer_cleanup.py`
  - prova exact-epoch + `FAILED`;
  - prova fail-closed para epoch estrangeiro;
  - prova neutralização completa dos campos de correlação;
  - prova que o Command waiter roteia Transfer Events enquanto aguarda Command Completion;
  - prova a ordem `Disable Slot → Transfer logical cleanup → descriptors → demais estados`;
  - usa inspeção robusta da expressão final de retorno.

### Fronteira física usada

`xhci_command_wait_completion()` já roteia qualquer Transfer Event observado antes da própria Command Completion para a mailbox de `xhci_transfer`. Portanto, depois da completion de `Disable Slot`, o recovery pode neutralizar essa mailbox/result do epoch sem reabrir polling ou consumir Event Ring. Slot ID/porta continuam reservados, impedindo reuse enquanto os owners físicos restantes não forem fechados.

### Próxima sequência se 4/4 verde

1. HID Report Descriptor DMA FAILED;
2. HID Report DMA FAILED;
3. HID Transfer Ring;
4. arena Device/Input Context + EP0 Ring;
5. barrier final e release Device Table / Slot ID / associação da porta.

Nenhum desses owners físicos é liberado neste microcorte Transfer.
