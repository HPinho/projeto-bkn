# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

Este arquivo registra o estado operacional para continuidade. O roadmap estratégico está em `docs/BAKEN_OS_ROADMAP.md`.

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**;
- trilha: **Trilha B — HID/input de produção**;
- etapa: **HID-4c Multi-slot xHCI**;
- subetapa: **HID-4c.4 — enumeração simultânea real**;
- checkpoint certificado mais recente: **HID-4c.4d — dual-device runtime proof**;
- candidato atual: **HID-4c.4e — interleaving/event demux**;
- branch: **`main`**;
- Kernel Core: **congelado/invariant-preserving**.

## Política de certificação

Um incremento só vira baseline quando os três gates passam no **mesmo SHA**:

1. Baken OS CI/CD & Automated QEMU Verification;
2. Baken OS SMP Bring-up Verification;
3. Baken OS NVMe-only Bare-Metal Verification.

Para HID-4c.4d+ existe ainda a prova específica **Baken OS HID Dual-device Verification**, que não substitui os três gates acima.

Não empilhar mudança funcional sobre candidato vermelho. Não remover marker/proof/teste nem ampliar timeout para mascarar regressão. APIs `_for(slot_id)` consomem estado/resultados do mesmo slot.

---

# Última baseline certificada

```text
6e2ad50d613fcaf11bfa2c48d74f477ee6b76bfe
feat(xhci): prove dual HID runtime
```

Provas:

- CI #1142 / `34594304063` ✅;
- SMP #245 / `34594304079` ✅;
- NVMe #342 / `34594304338` ✅;
- HID Dual-device #1 / `34594304283` ✅.

Essa baseline certifica:

- teclado continua sendo o primeiro HID e conserva o proof `sendkey a`;
- mouse é enumerado pelo pipeline per-port em um segundo Slot ID;
- existem pelo menos dois slots xHCI ativos e independentes;
- segundo slot chega a `HID_READY` com protocolo Boot mouse;
- segundo slot possui report ring e DMA próprios;
- Interrupt IN real do mouse completa antes de `BAKEN:USB_HID_DUAL_READY`;
- ausência de segundo HID permanece não fatal em hardware normal.

---

# Candidato corrente — HID-4c.4e

Objetivo: permitir keyboard e mouse com Transfer TDs simultaneamente outstanding no mesmo xHC, sem duplicar o consumidor do Event Ring e sem atribuir completion ao slot errado.

## Event Ring / transfer demux

O módulo `xhci_event_consumer` permanece o **único** dono de dequeue index, Consumer Cycle State e ERDP.

`xhci_transfer` adiciona uma mailbox bounded por Slot ID:

```text
XhciTransferPendingEvent {
    valid,
    epoch,
    endpoint_id,
    trb_pointer,
    residual_length,
    completion_code
}
```

Fluxo:

```text
xhci_event_consumer_peek()
→ valida Transfer Event
→ lê Slot ID / Endpoint ID / TRB pointer do próprio Event TRB
→ publica na mailbox slot+epoch correspondente
→ xhci_event_consumer_consume()
→ waiter do slot coleta somente endpoint+TRB exatos
```

APIs centrais:

```text
xhci_transfer_pending_is_ready_for(slot_id)
xhci_transfer_pending_matches(slot_id, endpoint_id, trb_physical)
xhci_transfer_route_next_event()
xhci_transfer_wait_completion(slot_id, endpoint_id, trb_physical)
```

Regras fail-closed:

- event de outro slot é preservado, não descartado;
- event do mesmo slot com endpoint ou TRB inesperados continua falhando;
- Event Data não é aceito nesse caminho;
- mailbox de epoch stale é invalidada;
- segundo completion para uma mailbox ocupada do mesmo epoch é overflow e falha;
- Host Controller Error continua terminal para o waiter/dispatcher;
- nenhum código novo acessa diretamente índice/cycle/ERDP do Event Ring.

## HID report submit/complete

`xhci_hid_report` separa a antiga operação monolítica em:

```text
xhci_hid_report_submit_for_slot(slot_id)
xhci_hid_report_complete_for_slot(slot_id)
```

O contrato atual permite somente um TD HID outstanding por slot. O state guarda:

```text
transfer_pending
pending_trb_physical
pending_transfer_length
```

O wrapper legado permanece:

```text
xhci_hid_report_poll_slot_once(slot_id)
→ submit_for_slot(slot_id)
→ complete_for_slot(slot_id)
```

Assim `post_cutover_prove_first_usb_hid_keyboard_report()` continua chamando a mesma API histórica.

## Prova runtime de interleaving

Depois de `BAKEN:USB_HID_DUAL_READY`, `platform_hid_late_attach` tenta a prova adicional 4c.4e:

```text
submit mouse
→ submit keyboard
→ ambos os TDs ficam outstanding
→ route_next_event()
→ route_next_event()
→ exige mailbox do keyboard
→ exige mailbox do mouse
→ complete keyboard pelo seu Slot ID/DCI/TRB
→ complete mouse pelo seu Slot ID/DCI/TRB
→ exige ambos os pending states vazios
→ valida tamanhos de report Boot
→ BAKEN:USB_HID_INTERLEAVE_READY
```

A ordem de chegada das duas completions não é presumida: o próprio Event TRB determina a mailbox. A ordem de coleta é independente da ordem de submit.

A falha dessa prova adicional não transforma keyboard+mouse em requisito universal de boot. O workflow dedicado é quem exige o marker de interleaving.

## Workflow dedicado

`.github/workflows/baken_hid_dual.yml` continua usando:

```text
-device qemu-xhci,id=xhci
-device usb-kbd,bus=xhci.0
-device usb-mouse,bus=xhci.0
```

Injeção:

```text
sendkey a
mouse_move 5 3
```

O timeout não foi ampliado. O workflow exige agora os dois markers:

```text
BAKEN:USB_HID_DUAL_READY
BAKEN:USB_HID_INTERLEAVE_READY
```

---

# HID-4c.4c — pipeline certificado

```text
xhci_port_stage_prepare_for(port_id)
→ xhci_slot_enable_port(port_id, slot_type)
→ xhci_context_prepare_for_slot(slot_id)
→ xhci_address_slot(slot_id)
→ xhci_ep0_prepare_for_slot(slot_id)
→ xhci_probe_device_descriptor_8_for_slot(slot_id)
→ xhci_reconcile_ep0_from_descriptor_probe_for_slot(slot_id)
→ xhci_get_device_descriptor_for_slot(slot_id)
→ xhci_probe_configuration_header_for_slot(slot_id)
→ xhci_read_configuration_full_for_slot(slot_id)
→ xhci_get_hid_configuration_for_slot(slot_id)
→ xhci_hid_context_prepare_for_slot(slot_id, endpoint, max_packet, interval)
→ xhci_configure_hid_endpoint_for_slot(slot_id)
→ xhci_set_configuration_for_slot(slot_id)
→ xhci_hid_report_prepare_for_slot(slot_id)
→ xhci_hid_enumeration_is_ready_for(slot_id)
```

Em falha após Enable Slot, o record vai para `FAILED`, identidade HID é desmontada, Disable Slot é enviado e confirmado, e o record permanece em quarentena. Não liberar/reusar Slot ID até HID-4d possuir teardown completo de todos os estados per-slot.

---

# Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. frame/stack só é liberado após entrada posterior do scheduler na CPU anterior;
4. FPU save → schedule → CR3/TSS → FPU restore permanece sob switch lock;
5. migração Ring3 BSP→AP preserva TID, address-space root e SIMD;
6. teardown ocorre apenas após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` continua terminal;
8. wait/sleep, TLB, Ring3, PMM/VMM e SMP não podem ser relaxados para acomodar drivers;
9. xHCI/HID não depende de UEFI pós-cutover;
10. Slot ID reutilizado nunca reaproveita estado sem cleanup e epoch novo.

---

# HID / input de produção — checkpoints

- HID-0 Boot HID xHCI ✅;
- HID-1 `1b3f94cc` ✅;
- HID-2 `a2e04a78` ✅;
- HID-3 `2775c12a` ✅;
- HID-4a `12c308b3` ✅;
- HID-4b `dbc5669a` ✅;
- HID-4c.3 final `6eec0dcc36a32c26108629e5ede9f0b929fef2e2` ✅;
- HID-4c.4a `8ef11b5e9298552d52eee3954ccd305e4421708d` ✅;
- HID-4c.4b `ff98c978ea9f11f78217369a9ec856ffcdf7a45b` ✅;
- HID-4c.4c `20b016973d12d4d669cf54ea79623a9116eb341f` ✅;
- HID-4c.4d `6e2ad50d613fcaf11bfa2c48d74f477ee6b76bfe` ✅;
- HID-4c.4e ⏳ candidato atual;
- HID-4d ⬜ hot-plug/recovery.

### Caminho legado obrigatório do primeiro teclado

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

O proof continua exigindo Boot keyboard report real, mínimo de 8 bytes, Usage ID `4` (`A`) e `POST_CUTOVER_HID_REPORT_ATTEMPTS = 8`.

---

# Próximo corte se HID-4c.4e ficar verde

**HID-4d — hot-plug/recovery.**

Objetivo inicial:

- detectar detach físico sem polling infinito;
- cancelar/invalidar TDs pendentes antes de teardown;
- desmontar InputDevice/map/event binding generation-safe;
- limpar report/descriptor/configuration/EP0/context state do epoch antigo;
- confirmar Disable Slot;
- só então liberar Slot ID para reuse com epoch novo;
- provar detach → reattach → reenumeração sem estado stale.

---

# Outras trilhas

ACPI/AML core: ✅ checkpoint `7803447a`.

Storage alvo: `BlockDevice → Block Cache → Volume Manager → VFS → FAT32/exFAT/NTFS/ext/ISO-UDF/BakenFS`.

Rede, áudio, GPU/composição e power/hot-plug avançado permanecem posteriores ao foco HID atual.

`HPinho/LangSotlas` permanece toolchain separada; não fazer migração ampla durante checkpoint crítico de driver.

---

# Regra de continuidade

1. confirmar `main` e SHA;
2. verificar CI/SMP/NVMe do mesmo SHA;
3. em HID-4c.4d+, verificar também o workflow runtime específico;
4. ler roadmap + handoff;
5. inspecionar assinaturas reais;
6. fazer um microcorte funcional;
7. preservar wrappers, markers e proofs;
8. se qualquer gate ficar vermelho, corrigir o próprio checkpoint antes de avançar.
