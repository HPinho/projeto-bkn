# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**
- trilha: **Trilha B — HID/input de produção**
- HID-4c multi-slot xHCI: **✅ concluído e certificado**
- HID-4d hot-plug/recovery: **⏳ em desenvolvimento**
- último checkpoint certificado: **HID-4d.1**
- candidato atual: **HID-4d.2a — Command Completion + Transfer Event coexistence**
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
8473860f975d6e9faab50b85a65314c2f49dc931
feat(xhci): quarantine detached HID slots
```

Provas:

- CI #1150 / `34606338435` ✅
- SMP #253 / `34606338434` ✅
- NVMe #350 / `34606338405` ✅
- HID Dual-device #9 / `34606338389` ✅

Esse checkpoint certifica HID-4d.1:

- `XHCI_DEVICE_STATE_DETACH_PENDING`
- transição dedicada `HID_READY → DETACH_PENDING` por Slot ID + epoch
- detecção via snapshot PORTSC read-only
- scan bounded dos slots
- novos `prepare/submit` bloqueados após detach
- completion de TD já outstanding ainda permitida
- nenhum `Disable Slot`, release de InputDevice ou reuse de Slot ID ainda

---

# Checkpoint anterior — HID-4c.4e

```text
2a06393a144ded56dc9f3959314633f48792885a
fix(hid): preserve runtime maps across self-test
```

Provas:

- CI #1148 / `34602885463` ✅
- SMP #251 / `34602885439` ✅
- NVMe #348 / `34602885480` ✅
- HID Dual-device #7 / `34602885483` ✅

Esse SHA fecha HID-4c.4e com:

```text
BAKEN:USB_HID_DUAL_READY
BAKEN:USB_HID_INTERLEAVE_READY
```

Event Ring único, dois TDs HID simultaneamente outstanding e demux de Transfer Events por Slot ID + epoch estão certificados.

---

# Candidato atual — HID-4d.2a

## Problema que este corte resolve

Para cancelar com `Stop Endpoint`, pode existir um TD HID outstanding. Nesse caso um Transfer Event pode chegar antes do Command Completion.

O waiter antigo de comandos aceitava Port Status Change e depois exigia imediatamente Command Completion. Um Transfer Event legítimo fazia o waiter falhar, podendo tornar cancel/hotplug inconsistente.

## Novo contrato do Event Ring durante command wait

```text
xhci_command_wait_completion(command_physical)
→ peek no Event Ring único
→ Port Status Change:
     valida port_id
     consome
     continua
→ Transfer Event:
     xhci_transfer_route_next_event()
     mailbox per-slot+epoch recebe o completion
     Event Ring avança uma vez
     continua
→ Command Completion:
     exige SUCCESS
     exige command TRB pointer exato
     publica last_slot_id
     consome
→ qualquer outro tipo:
     fail-closed
```

Não é criado segundo cursor, segundo ERDP nem segundo consumidor.

## Stop Endpoint

O candidato também adiciona somente o construtor puro:

```text
xhci_trb_stop_endpoint(slot_id, endpoint_id, cycle)
```

TRB Type = 15, Endpoint ID em bits 16..20 e Slot ID em bits 24..31.

**Importante:** o comando ainda não é submetido em HID-4d.2a. A emissão real fica para HID-4d.2b depois que este checkpoint for certificado.

---

# Sequência segura do HID-4d

1. **HID-4d.1 ✅** — detectar detach e colocar slot em quarentena sem teardown destrutivo.
2. **HID-4d.2a ⏳** — Command Completion e Transfer Event coexistem sem perda.
3. **HID-4d.2b ⬜** — emitir Stop Endpoint para endpoint HID em `DETACH_PENDING` e drenar/classificar completion de parada.
4. **HID-4d.3 ⬜** — teardown generation-safe de report/transfer/descriptor/map/InputDevice/config/EP0/context.
5. **HID-4d.4 ⬜** — Disable Slot, `xhci_device_table_release()`, reuse somente com epoch novo.
6. **HID-4d.5 ⬜** — prova runtime detach → reattach → reenumeração sem estado stale.

---

# Invariantes congelados

1. Event Ring xHCI tem um único consumidor.
2. Completion nunca é atribuída a Slot ID/endpoint/TRB diferente.
3. Slot ID reutilizado exige cleanup completo e epoch novo.
4. `DETACH_PENDING` bloqueia novos submits, mas não apaga TD já outstanding.
5. teardown só ocorre após endpoint/transfer não poderem mais produzir referência válida ao estado antigo.
6. Kernel Core, SMP, scheduler, TLB, Ring3 e FPU/SIMD não podem ser relaxados para acomodar driver.
7. `BAKEN:HEX=E:` permanece terminal.
8. `sendkey a`, `DUAL_READY` e `INTERLEAVE_READY` continuam preservados.

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
