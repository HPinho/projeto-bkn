# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**
- trilha: **Trilha B — HID/input de produção**
- HID-4c multi-slot xHCI: **✅ concluído e certificado**
- HID-4d hot-plug/recovery: **⏳ em desenvolvimento**
- última baseline integralmente certificada: **identity teardown generation-safe — `81c486e35985e442adef39ab63d2c96f7e581a2b`**
- próximo microcorte funcional: **descriptor DMA exact-epoch, retry-safe, após identity teardown**
- macroetapa atual: **HID-4d.3b — teardown HID lógico generation-safe**
- branch: **`main`**
- Kernel Core: **congelado/invariant-preserving**

## Política de certificação

Todo incremento precisa passar no mesmo SHA:

1. Baken OS CI/CD & Automated QEMU Verification
2. Baken OS SMP Bring-up Verification
3. Baken OS NVMe-only Bare-Metal Verification
4. Baken OS HID Dual-device Verification para a trilha HID multi-device

Não empilhar funcionalidade sobre candidato vermelho. Não enfraquecer markers, proofs ou timeouts.

---

# Baseline certificada atual — identity teardown generation-safe

```text
81c486e35985e442adef39ab63d2c96f7e581a2b
feat(hid): add generation-safe identity teardown
```

Provas no mesmo SHA:

- CI #1166 ✅
- SMP #269 ✅
- NVMe #366 ✅
- HID Dual-device #25 ✅

Escopo certificado:

- `input_device_generation_for_id(device_id)` lê a generation corrente sob o mesmo lock do registry e continua observável após o record ficar `DETACHED`;
- `xhci_hid_descriptor_teardown_input_device_for_epoch(slot_id, epoch)` exige `slot_id + epoch + DETACH_PENDING` exatos;
- o helper preserva a identidade antiga até concluir event-unbind, purge e map-unbind;
- `input_device_detach(old_id, old_generation)` só é chamado se a generation corrente ainda for exatamente a antiga;
- se `device_id` já avançou para nova generation, o teardown velho nunca detach a geração nova;
- a identidade armazenada no descriptor só é zerada no fim, após revalidação do mesmo epoch/id/generation;
- chamadas repetidas após cleanup já concluído são idempotentes;
- o helper histórico de rollback da enumeração permanece separado;
- nenhum DMA, Transfer Ring, endpoint context, Device/Input Context ou Slot ID é liberado neste corte.

Esse checkpoint autoriza avançar para o lifetime dos buffers persistentes de 4d.3b, começando pelo **descriptor DMA exact-epoch**.

---

# Baseline anterior — lifecycle exact-epoch

```text
1c8b81b3cd021d12e46a964f54024f661bc1c2b3
fix(xhci): bind HID lifecycle pending checks to epoch
```

Provas no mesmo SHA:

- CI #1164 ✅
- SMP #267 ✅
- NVMe #364 ✅
- HID Dual-device #23 ✅

Escopo deliberadamente pequeno e já certificado:

- `xhci_hid_lifecycle_quiescent_for(slot_id, epoch)` usa `xhci_hid_report_transfer_pending_for_epoch(slot_id, epoch)`;
- a mesma função usa `xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)`;
- `xhci_hid_lifecycle_stop_endpoint_for(slot_id, epoch)` captura `had_pending` pela API exact-epoch;
- revalidações `DETACH_PENDING + epoch` antes/entre/depois permanecem como barreira TOCTOU;
- `xhci_hid_report_drain_cancelled_for_slot(slot_id)` permanece temporariamente como compatibilidade slot-only, cercada por revalidação exata;
- nenhum DMA, InputDevice, descriptor, ring, context ou Slot ID é liberado neste corte.

---

# Baseline anterior — demux/waiter exact-epoch

```text
5fa048986ab4cfb8313530e9945e513633ea944f
fix(xhci): make transfer demux epoch-safe
```

Provas no mesmo SHA:

- CI #1163 ✅
- SMP #266 ✅
- NVMe #363 ✅
- HID Dual-device #22 ✅

Esse checkpoint preserva o Event Ring com **consumidor global único** e endurece o caminho generation-sensitive da mailbox/waiter:

```text
slot_id + epoch + endpoint_id + TRB physical pointer
```

- `xhci_transfer_pending_matches_for_epoch(...)` faz matching exato e side-effect-free;
- `xhci_transfer_take_pending(...)` revalida a identidade antes da leitura e antes de publicar o resultado;
- `xhci_transfer_wait_completion(...)` mantém o epoch capturado e falha fechado se o slot trocar de geração durante o polling;
- wrappers slot-only permanecem somente como compatibilidade;
- como o Transfer Event TRB do xHCI não contém software epoch, **reuso físico de Slot ID continua proibido até o drain/barrier de HID-4d.5**.

---

# Progressão certificada do HID-4d.3b

| Microcorte / hardening | Estado | Checkpoint / prova |
|---|---|---|
| 4d.3b0 arbitrary DMA release | ✅ | `913663e673eb73ba127644bef98427e658bf95cb` — CI #1156 / SMP #259 / NVMe #356 / HID Dual #15 |
| 4d.3b1 gate lógico `slot_id + epoch` | ✅ | `f2139d41580384d7ef392f789afabbb35b19e313` — CI #1159 / SMP #262 / NVMe #359 / HID Dual #18 |
| report decode SMP-serializado contra detach | ✅ | `6eb10542e4ab024dda2c28ba25dfcb97fb83dbcb` — CI #1161 / SMP #264 / NVMe #361 / HID Dual #20 |
| pending queries exact-epoch | ✅ | `b6b7efacfa41eac6a89400b83f409b18b6b72a38` — CI #1162 / SMP #265 / NVMe #362 / HID Dual #21 |
| demux/waiter exact-epoch | ✅ | `5fa048986ab4cfb8313530e9945e513633ea944f` — CI #1163 / SMP #266 / NVMe #363 / HID Dual #22 |
| lifecycle pending checks exact-epoch | ✅ | `1c8b81b3cd021d12e46a964f54024f661bc1c2b3` — CI #1164 / SMP #267 / NVMe #364 / HID Dual #23 |
| identity teardown InputDevice/events/map | ✅ | `81c486e35985e442adef39ab63d2c96f7e581a2b` — CI #1166 / SMP #269 / NVMe #366 / HID Dual #25 |
| descriptor DMA exact-epoch | ⬜ | próximo microcorte |
| report DMA + mailbox/result lógico | ⬜ | depois do descriptor DMA |
| `logical_teardown_complete` | ⬜ | fecha 4d.3b |

A macroetapa **4d.3b ainda não está concluída**: a identidade lógica está desmontada de forma generation-safe, mas ainda faltam os buffers persistentes descriptor/report, o estado lógico de transfer e o gate final de conclusão.

---

# Histórico — baseline HID-4d.3a

```text
322a472edd3cc30e6fb1d28384802ec1a1844809
fix(xhci): release temporary enumeration DMA
```

Provas:

- CI #1154 / `34621455000` ✅
- SMP #257 / `34621454947` ✅
- NVMe #354 / `34621454968` ✅
- HID Dual-device #13 / `34621454938` ✅

Esse checkpoint certifica HID-4d.3a:

- buffers temporários do Device Descriptor probe e Configuration header são liberados após a última referência do xHC
- o caminho faz `dma_unshare_from_device()` antes de `dma_release()`
- buffers persistentes de descriptors continuam vivos no estado do slot
- nenhuma referência ativa do controller é liberada prematuramente
- `Stop Endpoint` + drain terminal de HID-4d.2b permanece intacto
- nenhum Slot ID, context persistente ou Transfer Ring é liberado ainda

---

# Histórico — HID-4d.3b0

## Motivo do microcorte

O hot-unplug real precisa permitir teardown de dispositivos em qualquer ordem. Até a baseline HID-4d.3a, `dma_release()` devolvia páginas com `pmm_free_pages_lifo()`, o que exigia que o buffer fosse a última alocação global registrada pelo PMM.

Isso é inadequado quando, por exemplo, dispositivo A foi enumerado antes de B e A é removido enquanto B continua ativo.

O PMM já possui a API correta para esse caso:

```text
pmm_free_pages(base, count)
```

Ela é bitmap-backed, protegida pelo lock/IRQ do allocator, valida range/ownership físico, rejeita double-free e já possui self-test de liberação fora de ordem. Portanto **o PMM não foi redesenhado nesse corte**.

## Contrato do 4d.3b0

O backend normal de:

```text
dma_release()
```

foi alterado de:

```text
pmm_free_pages_lifo((*buffer).physical_address, page_count)
```

para:

```text
pmm_free_pages((*buffer).physical_address, page_count)
```

Preservando:

- `buffer != null`
- `dma_buffer_cpu_owned()`
- allocator disponível
- cálculo de `page_count`
- falha fechada se o PMM rejeitar o free
- invalidação do `DmaBuffer` somente depois de o free retornar sucesso
- somente `DMA_OWNER_CPU` e `DMA_OWNER_COMPLETED` podem ser liberados
- `DMA_OWNER_DEVICE` e `DMA_OWNER_SHARED` continuam rejeitados

Os usos de `pmm_free_pages_lifo()` dentro de `dma_alloc()` e `dma_alloc_for_device()` continuam permitidos quando são rollback imediato da própria alocação recém-feita, antes de qualquer nova alocação intercalar o lifetime.

---

# Sequência segura do HID-4d

1. **HID-4d.1 ✅** — detectar detach e colocar slot em quarentena.
2. **HID-4d.2a ✅** — Command Completion e Transfer Event coexistem sem perda.
3. **HID-4d.2b ✅** — Stop Endpoint + drain terminal do TD outstanding.
4. **HID-4d.3a ✅** — liberar DMA temporário de enumeração após a última referência do controller.
5. **HID-4d.3b0 ✅** — permitir `dma_release()` fora de ordem via PMM bitmap-backed.
6. **HID-4d.3b1 ✅** — abrir gate de teardown lógico somente para o `slot_id + epoch` exato.
7. **HID-4d.3b identity teardown ✅** — remover event binding, purgar fila, desmontar field map e detach da generation antiga sem tocar em generation nova.
8. **HID-4d.3b descriptor DMA ⬜** — liberar descriptor persistente com ownership/epoch exatos.
9. **HID-4d.3b report/transfer lógico ⬜** — liberar report DMA e limpar mailbox/result sem tocar no ring.
10. **HID-4d.3b completion gate ⬜** — publicar `logical_teardown_complete` só após todos os sub-cleanups.
11. **HID-4d.3c ⬜** — Drop Endpoint/reconfiguração + release seguro de rings.
12. **HID-4d.4 ⬜** — Disable Slot + release de Device/Input Context + EP0.
13. **HID-4d.5 ⬜** — drain/barrier, reuse de Slot ID apenas com epoch novo e rejeição de estado stale.
14. **HID-4d.6 ⬜** — prova runtime detach/reconnect e hotplug stress.

---

# Ordem planejada para concluir 4d.3b

O cleanup deve ser **retry-safe**. A primeira metade já está certificada:

```text
preservar old device_id + generation
→ hid_input_events_unbind_device(old_id, old_generation) ✅
→ input_event_purge_device(old_id, old_generation) ✅
→ hid_input_device_map_unbind(old_id, old_generation) ✅
→ input_device_detach(old_id, old_generation) com generation guard ✅
→ limpar identidade guardada somente no final ✅
→ descriptor DMA: unshare se necessário → CPU-owned → dma_release ⬜
→ report DMA: somente após Stop Endpoint + terminal drain → unshare → dma_release ⬜
→ limpar mailbox/result lógico exact-epoch sem tocar no Transfer Ring ⬜
→ marcar logical_teardown_complete ⬜
```

A ordem event-unbind → purge → map-unbind continua obrigatória porque o report decode é serializado pelo mesmo lifecycle lock de events; quando o unbind retorna, nenhum decoder antigo continua lendo o field map daquela geração.

O helper de hotplug agora é dedicado e não reutiliza o rollback histórico de enumeração. Ele também lê a generation corrente do registry antes do detach; se o `device_id` já pertence a uma generation posterior, a geração nova fica intocada.

## Próximo microcorte — descriptor DMA exact-epoch

Contrato planejado:

```text
slot_id + epoch + DETACH_PENDING exatos
→ identity teardown já concluído
→ descriptor state ainda pertence ao mesmo epoch
→ se buffer SHARED: dma_unshare_from_device
→ exigir dma_buffer_cpu_owned
→ dma_release
→ invalidar descriptor ready/info do mesmo epoch
```

O helper deve ser idempotente se o buffer já estiver liberado e deve revalidar o epoch entre ownership transition, release e publicação do estado lógico. Nenhum HID Transfer Ring ou context entra nesse corte.

## HID-4d.3c — endpoint/rings

Depois do teardown lógico:

```text
Drop Endpoint / reconfiguração equivalente
→ garantir ausência de referência xHC ao Transfer Ring
→ dma_unshare_from_device(ring)
→ dma_release(ring)
→ limpar endpoint/configure-endpoint state
```

Nunca liberar ring enquanto o xHC puder manter referência física a ele.

## HID-4d.4 — Disable Slot

Somente depois de endpoints/rings seguros:

```text
Disable Slot Command
→ Command Completion validado
→ remover DCBAA reference
→ liberar Device Context
→ liberar Input Context
→ liberar EP0 Ring
→ limpar estados per-slot
→ release da entrada na device table
```

A proteção por epoch continua obrigatória.

## HID-4d.5 — Slot reuse / barrier

O xHCI Transfer Event não transporta o software `epoch`. Portanto, antes de permitir Slot X epoch N+1, o runtime deve provar que não resta completion física de N capaz de aliasar o mesmo Slot ID. A prova de 4d.5 deve incluir drain/barrier explícito e rejeição de estado stale.

---

# Invariantes congelados

1. Event Ring xHCI tem um único consumidor.
2. Completion nunca é atribuída a Slot ID/endpoint/TRB diferente; no caminho generation-sensitive o matching inclui `slot_id + epoch + endpoint_id + TRB pointer`.
3. Slot ID reutilizado exige cleanup completo, drain/barrier e epoch novo.
4. `DETACH_PENDING` bloqueia novos submits, mas não apaga TD já outstanding.
5. Stop Endpoint só abre o gate de teardown após Command Completion + drain terminal.
6. TD cancelado não pode gerar evento de teclado/mouse.
7. DMA temporário sem owner persistente deve ser liberado após a última referência do controller.
8. Drivers usam a API DMA; não chamam PMM free diretamente.
9. `dma_release()` normal deve aceitar release arbitrário; rollback imediato de allocator pode permanecer LIFO.
10. Nenhum DMA pode ser liberado enquanto hardware ainda o referencia.
11. Pending queries, demux e lifecycle generation-sensitive devem receber epoch esperado explicitamente; wrappers slot-only ficam restritos à compatibilidade cercada por revalidação.
12. Teardown de uma identidade antiga nunca pode detach ou apagar uma generation nova do mesmo `device_id`.
13. A identidade do descriptor só é apagada depois dos sub-cleanups dependentes da generation antiga.
14. Kernel Core, SMP, scheduler, TLB, Ring3 e FPU/SIMD não podem ser relaxados para acomodar driver.
15. `BAKEN:HEX=E:` permanece terminal.
16. `sendkey a`, `DUAL_READY` e `INTERLEAVE_READY` continuam preservados.

---

# Caminho legado obrigatório do primeiro teclado

```text
post_cutover_prepare_first_usb_port
→ post_cutover_enable_first_usb_slot
→ post_cutover_prepare_first_usb_context
→ post_cutover_address_first_usb_device
→ post_cutover_probe_first_usb_descriptor
→ post_cutover_reconcile_first_usb_ep0
→ post_cutover_read_full_usb_device_descriptor
→ post_cutover_probe_first_usb_configuration_header
→ post_cutover_read_full_usb_configuration_descriptor
→ post_cutover_parse_first_usb_hid_interface
→ post_cutover_configure_first_usb_hid_endpoint
→ post_cutover_set_first_usb_configuration
→ post_cutover_prove_first_usb_hid_keyboard_report
→ storage
```

---

# Regra de continuidade

1. confirmar `main` e SHA
2. checar os quatro gates do mesmo SHA
3. ler roadmap + handoff
4. inspecionar ownership/lifetime real antes de liberar DMA
5. fazer um microcorte funcional por vez
6. se qualquer gate falhar, corrigir o próprio checkpoint antes de avançar
7. próxima implementação: **HID-4d.3b descriptor DMA exact-epoch**, retry-safe, após identity teardown e ainda sem Drop Endpoint, Transfer Ring release ou `Disable Slot`

---

# Atualização de continuidade — baseline 4d.3b encerrada, 4d.3c1 candidato

> Esta seção é o estado operacional autoritativo mais recente e preserva as seções históricas acima sem apagá-las.

## Baselines certificadas posteriores

### HID-4d.3b final — teardown HID lógico generation-safe

```text
e9fbdee39fd791351d0b04fc81cbe787b1c37413
```

Provas no mesmo SHA:

- CI #1173 ✅
- SMP #276 ✅
- NVMe #373 ✅
- HID Dual-device #32 ✅

Escopo certificado:

- `InputDevice/events/map → descriptor DMA → report DMA → mailbox/result lógico`;
- preflight side-effect-free antes de qualquer cleanup de InputDevice/DMA;
- mailbox ainda válida bloqueia teardown;
- `XHCI_TRANSFER_RESULT` válido de foreign epoch bloqueia teardown;
- preflight ocorre sob o mesmo teardown lock SMP;
- nenhum HID Transfer Ring, Device/Input Context, EP0 ring ou Slot ID é liberado em 3b.

### Command Ring global — SMP/preemption-safe

```text
8300215380d2b15f95705531f884be2a37047353
fix(xhci): make command transactions preemption-safe
```

Provas no mesmo SHA:

- CI #1175 ✅
- SMP #278 ✅
- NVMe #375 ✅
- HID Dual-device #34 ✅

A transação global agora é indivisível por software:

```text
IRQ save/disable
→ spinlock
→ submit
→ Command Completion
→ captura do Slot ID
→ unlock
→ IRQ restore
```

`75a9a0cf74aad60bb71d8385804022b3dfc8b384` foi candidato vermelho e não é baseline.

## Candidato atual — HID-4d.3c1 Drop Endpoint

```text
146e3e8d5db55d0b18e7198ce164f3db1ab4e056
feat(xhci): add HID Drop Endpoint teardown proof
```

Estado: **⏳ EM CERTIFICAÇÃO**. Não iniciar 3c2 antes do 4/4 verde no SHA final que contém também esta atualização documental.

Contrato implementado:

```text
slot_id + epoch exatos
→ logical_teardown_complete
→ Output Endpoint Context == Stopped
→ Input Control Context: Drop[Dci] = 1
→ Add Context: somente Slot Context
→ Context Entries = 1 (EP0 permanece)
→ Configure Endpoint com deconfigure=false
→ Command Completion validado para o mesmo Slot ID
→ Output Endpoint Context == Disabled
→ publicar drop_complete
```

Pontos de segurança:

- `Disabled` tem encoding `0`; erro de acesso ao Output Context é representado separadamente como `0xFF`, evitando falso sucesso;
- chamadas stale/foreign-epoch falham antes de alterar o Input Context;
- falhas antes da Command Completion restauram Drop Flags, Add Flags e Slot Context DW0;
- depois de Command Completion bem-sucedida, uma prova física inconsistente falha fechado sem restaurar memória que o xHC já pode ter consumido;
- 3c1 não chama `dma_unshare_from_device`, `dma_release`, `Disable Slot`, DCBAA teardown ou release da device table.

## Próxima sequência, somente após 3c1 certificado

1. **HID-4d.3c2:** Transfer Ring `SHARED → unshare → CPU-owned → dma_release`, somente se `drop_complete` do mesmo epoch estiver comprovado.
2. **HID-4d.3c3:** orquestrar/publicar conclusão do teardown físico de endpoint.
3. **HID-4d.4:** `Disable Slot → confirmação → DCBAA/context arena/EP0 → device-table teardown`.
4. **HID-4d.5:** drain/barrier explícito do Event Ring antes de qualquer reuso físico de Slot ID.
5. **HID-4d.6:** ligar o state machine completo no runtime e provar detach/reconnect/hotplug stress em QEMU.

## Robustez obrigatória antes de encerrar a Trilha B

- rollback de DMA em falhas intermediárias de `xhci_hid_context_prepare_for_slot()`;
- rollback da arena em falhas intermediárias de `xhci_context_prepare_for_slot()`.

Esses itens não devem ser misturados com 3c1/3c2: são dívidas de rollback independentes e precisam de microcortes próprios antes do fechamento da trilha.

---

# Atualização de continuidade — 3c1/3c2 certificados, 3c3 em validação

> Estado operacional autoritativo em **2026-09-12 (America/Fortaleza)**. As seções históricas acima permanecem preservadas; esta seção corrige apenas os apontamentos que ficaram desatualizados.

## Baseline certificada mais recente

### HID-4d.3c1 — Drop Endpoint físico

```text
31e196a88cddf79b86e276a1b370f57f5e6e7cdb
fix(xhci): keep Drop Endpoint below HID lifecycle
```

- CI #1179 ✅
- SMP #282 ✅
- NVMe #379 ✅
- HID Dual-device #38 ✅

`146e3e8d5db55d0b18e7198ce164f3db1ab4e056` foi candidato vermelho por dependência circular e **não** é baseline. O desenho final mantém `xhci_configure_endpoint` abaixo do lifecycle; 3c1 é apenas a primitiva física `Stopped → Drop Context → Configure Endpoint → Output Endpoint Context Disabled`.

### HID-4d.3c2 — Transfer Ring release

```text
89a132d8885b0e11b422d0b64c4daf07b852e7a2
feat(xhci): release dropped HID transfer rings safely
```

- CI #1180 ✅
- SMP #283 ✅
- NVMe #380 ✅
- HID Dual-device #39 ✅

O owner real do ring é `xhci_hid_context`. O teardown é exact-epoch, retry-safe e executa `SHARED → unshare → CPU-owned → dma_release`, preservando um tombstone (`ready=false`, ring inválido, `ring_physical=0`) que impede recriação no mesmo epoch.

## Candidato atual — HID-4d.3c3

```text
2486600dab290d86cb48645d0fc50535565f5376
feat(xhci): orchestrate HID endpoint teardown
```

Estado: **⏳ EM CERTIFICAÇÃO**.

Gates do candidato:

- CI #1181 ⏳
- SMP #284 ⏳
- NVMe #381 ⏳
- HID Dual-device #40 ⏳

Novo módulo: `kernel/src/drivers/xhci_hid_teardown.sotlas`.

Sequência implementada:

```text
slot_id + epoch + DETACH_PENDING
→ logical_teardown_complete
→ 3c1 drop_complete / Output Endpoint Context Disabled
→ 3c2 ring_release_complete
→ revalidar as provas do mesmo epoch
→ endpoint_teardown_complete
```

A publicação possui lock próprio, mas esse lock não atravessa Configure Endpoint nem `dma_release`; assim o orquestrador não cria lock recursivo com Command Ring/lifecycle. O módulo não executa `Disable Slot`, não toca DCBAA, não libera a context arena e não chama `xhci_device_table_release`.

## Próxima fronteira — HID-4d.4 refinado

A auditoria de ownership mostrou que Device Context, Input Context e EP0 Ring pertencem à **mesma arena DMA de três páginas** em `xhci_context`; portanto o teardown físico deve fazer um único free dessa arena, e não três frees independentes.

Também continuam vivos após 3c os `DmaBuffer` persistentes do Device Descriptor completo e do Configuration Descriptor completo. O 4d.4 será dividido em microcortes:

1. **4d.4a1 — enumeration DMA teardown:** liberar Device Descriptor + Configuration Descriptor persistentes, exact-epoch e retry-safe.
2. **4d.4a2 — per-slot logical quiesce:** limpar readiness operacional de `SET_CONFIGURATION`, `Evaluate Context`, `EP0` e `Address Device` antes de invalidar a arena.
3. **4d.4b — Disable Slot + arena:** `Disable Slot` com Command Completion validado → `DCBAA[slot]=0` → `SHARED → unshare → CPU-owned → dma_release` da arena única → publicar context teardown complete.
4. **4d.4c — registry finalization:** `xhci_device_table_release(slot_id, epoch)` somente depois das provas anteriores, preservando tombstone suficiente para 4d.5.

`xhci_trb_disable_slot()` e `xhci_device_table_release(slot_id, epoch)` já existem; este último já é exact-epoch e lock-protected.

## Depois de 4d.4

- **4d.5:** drain/barrier usando exclusivamente o consumidor global único do Event Ring antes de qualquer reuso físico de Slot ID. Como Transfer Event TRB não contém software epoch, um novo `Enable Slot` não pode atravessar essa fronteira sem prova de ausência de eventos stale.
- **4d.6:** integrar no runtime `detach → stop/drain → 3b → 3c → 4d.4 → 4d.5 → reconnect` e provar múltiplos ciclos keyboard/mouse em QEMU.

## Débitos de robustez antes do fechamento da Trilha B

- rollback de DMA em falhas intermediárias de `xhci_hid_context_prepare_for_slot()`;
- rollback da context arena em falhas intermediárias de `xhci_context_prepare_for_slot()`.

Esses débitos continuam em microcortes separados do teardown de hot-unplug.

---

# Atualização autoritativa — HID-4d.3c3 → HID-4d.6 certificados

> Seção append-only autoritativa em **2026-09-12 (America/Fortaleza)**. Todo o conteúdo histórico acima permanece preservado. Esta seção substitui apenas o estado corrente e corrige descrições históricas que ficaram desatualizadas.

## Estado operacional atual

- **HID-4d hot-plug/recovery:** ✅ **CONCLUÍDO E CERTIFICADO no escopo atual da Trilha B**.
- **Baseline funcional certificada:** `0887373c8e22b35260dcbf11ce7cd05b2dac4311`.
- **Kernel Core:** permanece congelado/invariant-preserving.
- **Event Ring:** permanece com um único consumidor global.

## Checkpoints finais certificados

- **HID-4d.3c3 — orquestração/publicação:** `2486600dab290d86cb48645d0fc50535565f5376` — CI #1181 / SMP #284 / NVMe #381 / HID Dual #40 ✅.
- **HID-4d.4a1 — persistent enumeration DMA teardown:** `fa66a3cb9e269370eea99b39c12162534f811efd` — CI #1184 / SMP #287 / NVMe #384 / HID Dual #43 ✅.
- **HID-4d.4a2 — per-slot logical quiesce:** `8176d557f2ed1107ce790c62c00e7fc0592f88db` — CI #1185 / SMP #288 / NVMe #385 / HID Dual #44 ✅.
- **HID-4d.4b — Disable Slot + DCBAA/context arena teardown:** `2bcdcd3728a43955da81738ec7ca0c53bdfc6301` — CI #1187 / SMP #290 / NVMe #387 / HID Dual #46 ✅.
- **HID-4d.5 — registry/reuse finalization generation-safe:** `2c055ac73217340078ca30f301133b8267208170` — CI #1189 / SMP #292 / NVMe #389 / HID Dual #48 ✅.
- **HID-4d.6 — runtime hotplug/recovery proof:** `0887373c8e22b35260dcbf11ce7cd05b2dac4311` — CI #1197 (`34701604137`) / SMP #300 (`34701604118`) / NVMe #397 (`34701604185`) / HID Dual #56 (`34701604141`) ✅.

## Sequência runtime certificada

```text
disconnect
→ mark DETACH_PENDING
→ Stop Endpoint + terminal drain
→ logical teardown 3b
→ endpoint teardown 3c
→ persistent enumeration DMA release 4a1
→ logical quiesce 4a2
→ Disable Slot + DCBAA/context arena teardown 4b
→ registry/reuse finalization 4d.5
→ re-enumeration com epoch novo
```

O serviço roda no runtime nativo, oportunisticamente no frame loop. Ausência/transiente de xHCI é não fatal para a UI; retry usa tombstones e nunca retrocede para um owner já destruído.

## Correção arquitetural obrigatória sobre 4d.5

As referências históricas acima a “Event Ring drain/barrier em 4d.5” estão desatualizadas. O **terminal drain físico pertence ao HID-4d.2b, antes de `Disable Slot`**. O HID-4d.5 certificado não cria outro scanner e não consome o Event Ring: ele finaliza registry/reuse somente após as provas físicas anteriores, libera `xhci_device_table` exact-epoch, mantém o reuse guard bloqueado até confirmar a invalidação e só então libera o guard e publica o tombstone de conclusão.

Portanto:

- não existe segundo consumidor do Event Ring;
- 4d.5 não possui ownership de Command Ring nem DMA;
- reuse do mesmo Slot ID só ocorre depois do teardown antigo completo;
- a nova reserva avança o software epoch, impedindo teardown stale de atingir a nova geração.

## Prova real de HID-4d.6

O HID Dual #56 compilou o kernel Sotlas nativo, construiu ISO e executou QEMU com xHCI real emulado, teclado e mouse simultâneos. O proof preservou `BAKEN:USB_HID_DUAL_READY` e `BAKEN:USB_HID_INTERLEAVE_READY`, entrou no serviço com `BAKEN:USB_HID_HOTPLUG_RUNTIME_READY` e completou dois ciclos reais:

```text
device_del mouse0
→ BAKEN:USB_HID_HOTPLUG_DETACH_READY
→ device_add mouse1
→ BAKEN:USB_HID_HOTPLUG_RECONNECT_READY

device_del mouse1
→ BAKEN:USB_HID_HOTPLUG_DETACH_READY
→ device_add mouse2
→ BAKEN:USB_HID_HOTPLUG_RECONNECT_READY
```

Timeouts e markers não foram enfraquecidos.

## Fronteira exata do que está encerrado

Está encerrado o **escopo atual planejado de xHCI/USB HID da Trilha B**: multi-slot, identidade generation-safe, input/event demux, detach/quarentena, Stop Endpoint/drain, teardown lógico e físico, Disable Slot, liberação de contexts/DMA, reuse generation-safe e reenumeração runtime/hotplug.

Isso **não** significa que toda a especificação xHCI ou todas as classes USB estejam implementadas. I2C-HID e transportes/classes adicionais continuam fora deste fechamento.

## Hardening restante, separado do hotplug certificado

Dois débitos de prepare/rollback permanecem independentes e devem ser executados como microcortes próprios:

1. rollback de DMA em falhas intermediárias de `xhci_hid_context_prepare_for_slot()`;
2. rollback da arena de três páginas em falhas intermediárias de `xhci_context_prepare_for_slot()`.

Também pode ser adicionado posteriormente um proof explícito de **Interrupt-IN/input contínuo após reconnect**. O 4d.6 atual já prova teardown + reuse + reenumeração real até `HID_READY` em dois ciclos; uma Transfer Event pós-reconnect dedicada é hardening adicional, não condição retroativa da certificação 4d.6.

## Próxima continuidade recomendada

1. hardening do rollback de `xhci_hid_context_prepare_for_slot()`;
2. certificar nos quatro gates no mesmo SHA;
3. hardening do rollback da arena em `xhci_context_prepare_for_slot()`;
4. certificar novamente nos quatro gates;
5. somente depois escolher a próxima trilha de Platform/Drivers.
