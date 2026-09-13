# Baken OS — Roadmap Appendix (autoritativo, append-only)

Este arquivo complementa `docs/BAKEN_OS_ROADMAP.md` sem reescrever o histórico já existente. A partir de 2026-09-13, cada microcorte da trilha HID deve acrescentar uma entrada aqui com o resultado real dos gates, inclusive falhas, antes de avançar para o corte seguinte.

## Política de gates e correções

Um candidato da trilha HID só vira baseline certificada quando **CI principal + SMP + NVMe-only + HID Dual-device** terminam verdes no mesmo SHA.

- candidato com qualquer gate aberto: `⏳ EM VALIDAÇÃO`;
- candidato com qualquer gate vermelho: `❌ REPROVADO`, preservando SHA, workflow/step e causa conhecida;
- correção posterior deve citar explicitamente o SHA reprovado e o defeito corrigido;
- não apagar entradas reprovadas: elas fazem parte do histórico de engenharia;
- não empilhar outro microcorte funcional enquanto o candidato atual não fechar 4/4;
- documentação acompanha cada microcorte; mudanças de LangSotlas só entram quando sintaxe/semântica/lowering realmente exigirem.

---

## 2026-09-13 — baseline HID Report DMA prepare hardening

**✅ CERTIFICADO 4/4**

```text
e39db2528de7bf2d7381befc696680f6d62205bd
fix(xhci): harden HID report DMA prepare publication
```

Provas no mesmo SHA:

- CI #1206 ✅
- SMP #309 ✅
- NVMe #406 ✅
- HID Dual-device #65 ✅

Escopo certificado:

- rollback de candidato HID Report DMA somente enquanto ainda CPU-owned e não publicado;
- falhas de zero/share não descartam owner potencialmente entregue ao device;
- owner antigo/quarentenado impede overwrite por epoch novo;
- `ready=true` é a publicação final do registro per-slot;
- nenhuma mudança de sintaxe, semântica ou lowering em LangSotlas foi necessária.

---

## 2026-09-13 — recovery de enumeração FAILED / Address Device lógico

**⏳ CANDIDATO DESTE MICROCORTE — gates ainda não certificados nesta entrada.**

Objetivo deliberadamente pequeno:

```text
FAILED + slot_id + epoch exatos
→ Disable Slot já confirmado
→ Configuration Descriptor recovery tentado
→ Device Descriptor recovery tentado
→ limpar somente o estado lógico Address Device do mesmo epoch
→ manter EP0, Evaluate Context, SET_CONFIGURATION, Configure Endpoint,
  HID Report DMA, Transfer Ring, Device/Input Context e Slot ID em quarentena
```

Invariantes do corte:

- o helper de `DETACH_PENDING` existente permanece separado e inalterado;
- estado de outro epoch nunca é sobrescrito;
- se Address Device nunca chegou a publicar estado e o slot local já está vazio, cleanup é idempotente;
- estado vivo/stale de outro epoch falha fechado;
- nenhum `dma_release`, `dma_unshare_from_device`, context release ou Slot ID release é introduzido;
- guardrail novo deve provar a ordem `Disable Slot completion → descriptor recovery → Address cleanup`.

### Próximos microcortes, condicionados ao resultado dos gates

1. Se este candidato falhar: registrar SHA + gate/step vermelho + causa e corrigir **somente a regressão** no próximo candidato.
2. Se fechar 4/4: adicionar cleanup lógico `EP0` exact-epoch em `FAILED`.
3. Depois: `Evaluate Context` lógico exact-epoch.
4. Depois: `SET_CONFIGURATION` lógico exact-epoch.
5. Depois: `Configure Endpoint` lógico exact-epoch, sem fingir que Drop Endpoint físico ocorreu.
6. Depois dos estados lógicos: HID Report Descriptor DMA físico, HID Transfer Ring, arena Device/Input Context e, por último, release de Device Table / Slot ID / porta após barrier apropriado.

A porta continua deliberadamente bloqueada enquanto qualquer owner físico ou estado obrigatório de cleanup permanecer em `FAILED`.

---

## 2026-09-13 — fechamento do gate Address Device lógico FAILED

**✅ CERTIFICADO 4/4 — nenhuma correção intermediária necessária.**

```text
d0b8d98bbe8d1249f837519ef28e5022b1eb96d9
fix(xhci): quiesce failed address state by epoch
```

Provas no mesmo SHA:

- CI #1207 ✅
- SMP #310 ✅
- NVMe #407 ✅
- HID Dual-device #66 ✅

Resultado certificado:

- `FAILED + slot_id + epoch` exatos são obrigatórios para o cleanup Address Device;
- estado neutro quando Address Device nunca foi publicado é retry-safe/idempotente;
- estado vivo de outro epoch continua em quarentena e não é sobrescrito;
- cleanup ocorre somente depois de `Disable Slot` confirmado e depois do recovery dos descriptors;
- nenhum owner físico, ring, context, Device Table ou Slot ID foi liberado;
- nenhum ajuste em `HPinho/LangSotlas` foi necessário.

Não houve gate vermelho neste candidato, portanto não existe correção de regressão associada a este SHA.

---

## 2026-09-13 — recovery de enumeração FAILED / EP0 lógico

**⏳ CANDIDATO DO PRÓXIMO MICROCORTE — certificação depende dos quatro gates no novo SHA.**

Contrato do corte:

```text
FAILED + slot_id + epoch exatos
→ Disable Slot já confirmado
→ Configuration Descriptor recovery
→ Device Descriptor recovery
→ EP0 lógico: ready=false, enqueue=0, PCS=true, last_status=0,
  active_slot limpo somente se pertencer ao slot
→ Address Device lógico
→ EP0 Ring físico permanece na arena
```

Invariantes:

- `DETACH_PENDING` continua usando exclusivamente `xhci_ep0_quiesce_for_epoch()`;
- `FAILED` usa API dedicada e não muda o epoch armazenado;
- estado EP0 neutro de uma etapa nunca publicada é aceito como já limpo;
- estado vivo/stale de outro epoch falha fechado;
- nenhum acesso a `xhci_context_ep0_ring_physical_for()` ocorre dentro do release FAILED;
- nenhum DMA/free/context/Slot ID release ocorre neste corte;
- guardrail prova a ordem `Disable Slot → descriptors → EP0 lógico → Address lógico`.

Se este candidato fechar 4/4, o próximo microcorte será **Evaluate Context lógico exact-epoch em FAILED**. Se algum gate falhar, a próxima entrada preservará o SHA reprovado, workflow/step, causa e correção antes de qualquer feature nova.

---

## 2026-09-13 — fechamento do gate EP0 lógico FAILED

**✅ CERTIFICADO 4/4 — nenhuma correção intermediária necessária.**

```text
3248fcd86581a5e8822564dcbd0d71eb60d2c6ed
fix(xhci): quiesce failed EP0 state by epoch
```

Provas no mesmo SHA:

- CI #1208 ✅
- SMP #311 ✅
- NVMe #408 ✅
- HID Dual-device #67 ✅

Resultado certificado:

- cleanup EP0 exige Device Table válida, estado `FAILED` e epoch exato;
- estado neutro de EP0 nunca publicado é reconhecido como já limpo sem adotar epoch;
- estado vivo de outro epoch permanece em quarentena;
- somente `ready`, enqueue, Producer Cycle State, correlação do Status TRB e seleção global do slot são desmontados;
- EP0 Ring, Input/Device Context, HID Transfer Ring, Slot ID e porta permanecem fisicamente intactos;
- nenhum ajuste em `HPinho/LangSotlas` foi necessário.

Não houve gate vermelho neste candidato.

---

## 2026-09-13 — recovery de enumeração FAILED / Evaluate Context lógico

**⏳ CANDIDATO DESTE MICROCORTE — certificação depende dos quatro gates no novo SHA.**

Contrato do corte:

```text
FAILED + slot_id + epoch exatos
→ Disable Slot confirmado
→ Configuration Descriptor recovery
→ Device Descriptor recovery
→ Evaluate Context lógico:
    LAST_EP0_MAX_PACKET = 0
    COMMAND_SUBMITTED = false
→ EP0 lógico
→ Address Device lógico
→ Input/Device Context e EP0 Ring físicos permanecem na arena
```

Invariantes:

- `DETACH_PENDING` continua isolado em `xhci_evaluate_context_quiesce_for_epoch()`;
- recovery `FAILED` nunca chama `xhci_evaluate_context_reset_slot()` e nunca reescreve `XHCI_EVALUATE_CONTEXT_EPOCHS`;
- se Evaluate Context nunca publicou o epoch e o estado local está neutro, o cleanup é idempotente;
- estado não neutro de outro epoch falha fechado;
- nenhum `direct_map`, acesso a context físico, DMA release, command submission ou free físico ocorre no helper FAILED;
- a ordem de recovery passa a ser `Disable Slot → descriptors → Evaluate Context lógico → EP0 lógico → Address lógico`;
- a certificação EP0 anterior continua válida: naquele corte Evaluate Context permaneceu em quarentena e nenhum owner físico foi liberado. Este corte apenas refina a ordem de teardown lógico a partir daqui.

Se este candidato fechar 4/4, o próximo microcorte planejado é **SET_CONFIGURATION lógico exact-epoch em FAILED**. Qualquer gate vermelho deve ser registrado e corrigido antes desse avanço.

---

## 2026-09-13 — fechamento do gate Evaluate Context lógico FAILED

**✅ CERTIFICADO 4/4 — nenhuma correção intermediária necessária.**

```text
dc7a1fa8a003f9050e8a40817e2a1453f8e69714
fix(xhci): quiesce failed evaluate context state by epoch
```

Provas no mesmo SHA:

- CI #1209 ✅
- SMP #312 ✅
- NVMe #409 ✅
- HID Dual-device #68 ✅

Resultado certificado:

- cleanup exige `FAILED + slot_id + epoch` exatos;
- stale epoch só é aceito quando `LAST_EP0_MAX_PACKET == 0` e `COMMAND_SUBMITTED == false`;
- `XHCI_EVALUATE_CONTEXT_EPOCHS` nunca é reescrito no recovery;
- `xhci_evaluate_context_reset_slot()` não é usado no caminho FAILED;
- nenhum context físico, DMA, command submission ou ring foi liberado;
- teardown lógico certificado passa por `Evaluate Context → EP0 → Address` após os descriptors;
- nenhum ajuste em `HPinho/LangSotlas` foi necessário.

Não houve gate vermelho neste candidato.

---

## 2026-09-13 — recovery de enumeração FAILED / SET_CONFIGURATION lógico

**⏳ CANDIDATO DESTE MICROCORTE — certificação depende dos quatro gates no novo SHA.**

Contrato do corte:

```text
FAILED + slot_id + epoch exatos
→ Disable Slot confirmado
→ Configuration Descriptor recovery
→ Device Descriptor recovery
→ SET_CONFIGURATION lógico: ready=false, value=0, active_slot limpo
→ Evaluate Context lógico
→ EP0 lógico
→ Address Device lógico
```

Invariantes:

- o epoch armazenado por SET_CONFIGURATION é preservado e nunca adotado/reescrito;
- estado stale só pode ser reconhecido como já limpo se `ready=false`, `value=0` e `active_slot != slot_id`;
- recovery FAILED nunca chama `xhci_set_configuration_prepare_state()`;
- nenhum novo control transfer, Status TRB, wait de EP0 ou inicialização de HID descriptor é executado;
- nenhum DMA, context, ring, Slot ID ou porta é liberado neste corte;
- o Report Descriptor DMA físico continua em quarentena onde aplicável;
- guardrail prova a ordem `Disable Slot → descriptors → SET_CONFIGURATION → Evaluate → EP0 → Address`.

Se este candidato fechar 4/4, o próximo microcorte será **Configure Endpoint lógico exact-epoch em FAILED**, explicitamente sem reutilizar a primitiva física `Drop Endpoint` após `Disable Slot`.

---

## 2026-09-13 — gate vermelho SET_CONFIGURATION / correção-only de guardrails históricos

**❌ `3a45e9a777f9a823b621e2d74db68f4b4758cbf5` REPROVADO no gate 4/4 por CI principal.**

Resultado observado no mesmo SHA:

- CI #1210 ❌ — step `Run Complete Test Suite`;
- SMP #313 ✅;
- NVMe #410 ✅;
- HID Dual-device #69 ✅.

Falha preservada:

```text
test_xhci_failed_ep0_cleanup
→ esperava substring contígua `ep0_released && address_released`

test_xhci_failed_evaluate_context_cleanup
→ esperava substring contígua `evaluate_released && ep0_released && address_released`
```

Causa técnica:

- o microcorte SET_CONFIGURATION inseriu legitimamente `set_configuration_released` antes de Evaluate/EP0/Address e quebrou apenas asserções textuais antigas que exigiam nomes adjacentes na expressão final;
- as próprias provas de ordenação dos guardrails continuavam corretas;
- SMP, NVMe e HID completaram verdes, portanto não houve evidência de regressão funcional, compilação Sotlas ou runtime.

Correção aplicada neste candidato correction-only:

- os guardrails EP0 e Evaluate passam a localizar a expressão final `return` e verificar que seus owners obrigatórios continuam presentes nela, sem exigir adjacência textual;
- as provas de ordem `Evaluate → EP0 → Address` e `EP0 → Address` permanecem intactas;
- nenhum arquivo funcional de kernel, LangSotlas ou workflow é alterado.

A `main` permanece congelada nesta correção até **CI + SMP + NVMe + HID** fecharem 4/4 no novo SHA. Somente então Configure Endpoint lógico FAILED poderá começar.
