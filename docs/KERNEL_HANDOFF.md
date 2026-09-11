# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**
- trilha: **Trilha B — HID/input de produção**
- HID-4c multi-slot xHCI: **✅ concluído e certificado**
- HID-4d hot-plug/recovery: **⏳ em desenvolvimento**
- último checkpoint certificado: **HID-4d.3a — lifetime de DMA temporário**
- candidato atual: **HID-4d.3b0 — arbitrary DMA release**
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

# Baseline certificada atual

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

# Candidato atual — HID-4d.3b0

## Motivo do microcorte

O hot-unplug real precisa permitir teardown de dispositivos em qualquer ordem. Até a baseline HID-4d.3a, `dma_release()` devolve páginas com `pmm_free_pages_lifo()`, o que exige que o buffer seja a última alocação global registrada pelo PMM.

Isso é inadequado quando, por exemplo, dispositivo A foi enumerado antes de B e A é removido enquanto B continua ativo.

O PMM já possui a API correta para esse caso:

```text
pmm_free_pages(base, count)
```

Ela é bitmap-backed, protegida pelo lock/IRQ do allocator, valida range/ownership físico, rejeita double-free e já possui self-test de liberação fora de ordem. Portanto **o PMM não deve ser redesenhado neste corte**.

## Contrato do 4d.3b0

Alterar somente o backend normal de:

```text
dma_release()
```

de:

```text
pmm_free_pages_lifo((*buffer).physical_address, page_count)
```

para:

```text
pmm_free_pages((*buffer).physical_address, page_count)
```

Preservar obrigatoriamente:

- `buffer != null`
- `dma_buffer_cpu_owned()`
- allocator disponível
- cálculo de `page_count`
- falha fechada se o PMM rejeitar o free
- invalidação do `DmaBuffer` somente depois de o free retornar sucesso
- somente `DMA_OWNER_CPU` e `DMA_OWNER_COMPLETED` podem ser liberados
- `DMA_OWNER_DEVICE` e `DMA_OWNER_SHARED` continuam rejeitados

## Rollback LIFO continua válido

Os usos de `pmm_free_pages_lifo()` dentro de `dma_alloc()` e `dma_alloc_for_device()` continuam permitidos quando são rollback imediato da própria alocação recém-feita, antes de qualquer nova alocação intercalar o lifetime.

Não trocar esses call sites neste microcorte.

## Guardrails do candidato

`tests/test_dma_release.py` deve provar:

- `dma_release()` usa `pmm_free_pages()`
- `dma_release()` não contém `pmm_free_pages_lifo()`
- ownership passa por `dma_buffer_cpu_owned()`
- `DEVICE`/`SHARED` não são CPU-owned
- invalidação ocorre somente após o PMM aceitar o free
- rollbacks dos allocators continuam LIFO
- a API/self-test de free arbitrário do PMM permanece presente

`tests/test_dma_contract.py` também precisa deixar de exigir o call site LIFO obsoleto dentro de `dma_release()`.

---

# Sequência segura do HID-4d

1. **HID-4d.1 ✅** — detectar detach e colocar slot em quarentena.
2. **HID-4d.2a ✅** — Command Completion e Transfer Event coexistem sem perda.
3. **HID-4d.2b ✅** — Stop Endpoint + drain terminal do TD outstanding.
4. **HID-4d.3a ✅** — liberar DMA temporário de enumeração após a última referência do controller.
5. **HID-4d.3b0 ⏳** — permitir `dma_release()` fora de ordem via PMM bitmap-backed.
6. **HID-4d.3b ⬜** — teardown HID lógico generation-safe por `slot_id + epoch`.
7. **HID-4d.3c ⬜** — Drop Endpoint/reconfiguração + release seguro de rings.
8. **HID-4d.4 ⬜** — Disable Slot + release de Device/Input Context + EP0.
9. **HID-4d.5 ⬜** — reuse de Slot ID apenas com epoch novo e rejeição de estado stale.
10. **HID-4d.6 ⬜** — prova runtime detach/reconnect e hotplug stress.

---

# Ordem planejada após 4d.3b0

## HID-4d.3b — teardown HID lógico

Somente depois de o 4d.3b0 estar certificado:

```text
report DMA
→ HID report state
→ InputDevice
→ HID field map
→ HID descriptor state
→ event/bindings
```

Antes de liberar qualquer objeto associado ao slot, validar que a geração armazenada ainda corresponde ao `current_device_table_epoch`. Uma geração antiga nunca pode destruir estado de uma nova enumeração que reutilizou o mesmo Slot ID.

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

---

# Invariantes congelados

1. Event Ring xHCI tem um único consumidor.
2. Completion nunca é atribuída a Slot ID/endpoint/TRB diferente.
3. Slot ID reutilizado exige cleanup completo e epoch novo.
4. `DETACH_PENDING` bloqueia novos submits, mas não apaga TD já outstanding.
5. Stop Endpoint só abre o gate de teardown após Command Completion + drain terminal.
6. TD cancelado não pode gerar evento de teclado/mouse.
7. DMA temporário sem owner persistente deve ser liberado após a última referência do controller.
8. Drivers usam a API DMA; não chamam PMM free diretamente.
9. `dma_release()` normal deve aceitar release arbitrário; rollback imediato de allocator pode permanecer LIFO.
10. Nenhum DMA pode ser liberado enquanto hardware ainda o referencia.
11. Kernel Core, SMP, scheduler, TLB, Ring3 e FPU/SIMD não podem ser relaxados para acomodar driver.
12. `BAKEN:HEX=E:` permanece terminal.
13. `sendkey a`, `DUAL_READY` e `INTERLEAVE_READY` continuam preservados.

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
7. se 4d.3b0 ficar verde, avançar para **HID-4d.3b teardown HID lógico per-epoch**, ainda sem `Disable Slot`
