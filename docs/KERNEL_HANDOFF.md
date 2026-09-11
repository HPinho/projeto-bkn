# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**
- trilha: **Trilha B — HID/input de produção**
- HID-4c multi-slot xHCI: **✅ concluído e certificado**
- HID-4d hot-plug/recovery: **⏳ em desenvolvimento**
- último checkpoint certificado: **HID-4d.2a**
- candidato atual: **HID-4d.2b — Stop Endpoint + drain terminal**
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
d5d975dc396fb85fc3b3551a2969c9c9114c55b4
feat(xhci): prepare safe HID endpoint cancellation
```

Provas:

- CI #1152 / `34609196376` ✅
- SMP #255 / `34609196371` ✅
- NVMe #352 / `34609196531` ✅
- HID Dual-device #11 / `34609196451` ✅

Esse checkpoint certifica HID-4d.2a:

- Command waiter preserva Transfer Events via `xhci_transfer_route_next_event()`
- Event Ring continua com consumidor único
- completion de outro slot é preservada por mailbox slot+epoch
- Command Completion continua exigindo pointer exato + SUCCESS
- `xhci_trb_stop_endpoint(slot_id, endpoint_id, cycle)` está disponível como construtor puro
- nenhum Stop Endpoint era emitido ainda nesse SHA

Checkpoint anterior HID-4d.1: `8473860f975d6e9faab50b85a65314c2f49dc931`, CI #1150 / SMP #253 / NVMe #350 / HID Dual #9 ✅.

---

# Candidato atual — HID-4d.2b

Objetivo: parar o endpoint HID de um slot em `DETACH_PENDING` e garantir que qualquer TD outstanding do mesmo epoch deixe de referenciar estado vivo antes do teardown.

## Sequência

```text
xhci_hid_lifecycle_stop_endpoint_for(slot_id, epoch)
→ exige DETACH_PENDING no mesmo slot+epoch
→ exige HID context e Command Ring prontos
→ captura had_pending
→ lê DCI real via xhci_hid_context_dci_for(slot_id)
→ xhci_trb_stop_endpoint(slot_id, dci, PCS)
→ xhci_command_submit
→ xhci_command_wait_completion
→ exige xhci_command_last_slot_id() == slot_id
→ se had_pending:
     xhci_hid_report_drain_cancelled_for_slot(slot_id)
     → xhci_transfer_wait_stopped_or_completed(slot,dci,trb)
→ exige report TD vazio + transfer mailbox vazia
→ endpoint_stopped = true para o mesmo epoch
```

## Completion Codes aceitos no drain de lifecycle

O waiter normal continua aceitando apenas `SUCCESS`. O caminho específico de Stop Endpoint aceita, além da corrida em que o TD já completou com SUCCESS:

- 26 — Stopped
- 27 — Stopped - Length Invalid
- 28 — Stopped - Short Packet

Qualquer outro completion code continua fail-closed.

## Report state

`xhci_hid_report_drain_cancelled_for_slot(slot_id)` exige `DETACH_PENDING`, TD outstanding e DCI válido. Depois do completion terminal exato ele limpa apenas:

```text
transfer_pending = false
pending_trb_physical = 0
pending_transfer_length = 0
last_length = 0
```

Não chama `xhci_hid_report_parse_for_slot`, não valida o DMA como report novo e não publica eventos de input.

## Estado de lifecycle

`XhciHidLifecycleState` é keyed por Slot ID + epoch e contém:

```text
valid
epoch
detach_detected
endpoint_stopped
```

`xhci_hid_lifecycle_can_finalize_for(slot_id, epoch)` somente retorna true quando:

- mesmo slot+epoch continua em `DETACH_PENDING`
- `endpoint_stopped == true`
- nenhum TD HID permanece pending
- nenhuma Transfer Event mailbox permanece pending para o slot

## Fora do escopo deste corte

Continuam proibidos no 4d.2b:

- `xhci_trb_disable_slot`
- `xhci_device_table_release()`
- `input_device_detach`
- release de HID descriptor/InputDevice binding
- teardown de report DMA/ring, HID context, EP0, configuration ou device context
- reuse de Slot ID

Tudo isso começa apenas no HID-4d.3/4d.4.

---

# Sequência segura do HID-4d

1. **HID-4d.1 ✅** — detectar detach e colocar slot em quarentena.
2. **HID-4d.2a ✅** — Command Completion e Transfer Event coexistem sem perda.
3. **HID-4d.2b ⏳** — Stop Endpoint + drain terminal do TD outstanding.
4. **HID-4d.3 ⬜** — teardown generation-safe de report/transfer/descriptor/map/InputDevice/config/EP0/context.
5. **HID-4d.4 ⬜** — Disable Slot, release, reuse somente com epoch novo.
6. **HID-4d.5 ⬜** — prova runtime detach → reattach → reenumeração sem estado stale.

---

# Invariantes congelados

1. Event Ring xHCI tem um único consumidor.
2. Completion nunca é atribuída a Slot ID/endpoint/TRB diferente.
3. Slot ID reutilizado exige cleanup completo e epoch novo.
4. `DETACH_PENDING` bloqueia novos submits, mas não apaga TD já outstanding.
5. Stop Endpoint só pode abrir o gate de teardown após Command Completion + drain terminal.
6. TD cancelado não pode gerar evento de teclado/mouse.
7. Kernel Core, SMP, scheduler, TLB, Ring3 e FPU/SIMD não podem ser relaxados para acomodar driver.
8. `BAKEN:HEX=E:` permanece terminal.
9. `sendkey a`, `DUAL_READY` e `INTERLEAVE_READY` continuam preservados.

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
4. inspecionar APIs reais antes de alterar lifecycle
5. fazer um microcorte funcional por vez
6. se qualquer gate falhar, corrigir o próprio checkpoint antes de avançar
7. se 4d.2b ficar verde, o próximo corte é **HID-4d.3 teardown per-epoch**, ainda sem reuse antes do Disable Slot certificado
