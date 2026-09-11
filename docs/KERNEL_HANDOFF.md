# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

Este arquivo registra o estado operacional para continuidade. O roadmap estratégico está em `docs/BAKEN_OS_ROADMAP.md`.

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**;
- trilha: **Trilha B — HID/input de produção**;
- etapa: **HID-4c Multi-slot xHCI**;
- subetapa: **HID-4c.4 — enumeração simultânea real**;
- checkpoint certificado mais recente: **HID-4c.4b — inventário/seleção multi-port**;
- candidato atual: **HID-4c.4c — pipeline completo por porta**;
- branch: **`main`**;
- Kernel Core: **congelado/invariant-preserving**.

## Política de certificação

Um incremento só vira baseline quando os três gates passam no **mesmo SHA**:

1. Baken OS CI/CD & Automated QEMU Verification;
2. Baken OS SMP Bring-up Verification;
3. Baken OS NVMe-only Bare-Metal Verification.

Não empilhar mudança funcional sobre candidato vermelho. Não remover marker/proof/teste nem ampliar timeout para mascarar regressão. APIs `_for(slot_id)` consomem estado/resultados do mesmo slot.

---

# Última baseline certificada

```text
ff98c978ea9f11f78217369a9ec856ffcdf7a45b
feat(xhci): add bounded multi-port staging
```

Provas:

- CI #1140 / `34558394871` ✅;
- SMP #243 / `34558394930` ✅;
- NVMe #340 / `34558394895` ✅.

Esse checkpoint certifica:

- `xhci_port_next_connected(after_port_id)`;
- `xhci_port_stage_prepare_for(port_id)`;
- staging multi-port sem reinicializar Command Ring/Event Consumer;
- caminho legado do primeiro teclado preservado.

---

# Candidato corrente — HID-4c.4c

Novo módulo:

```text
kernel::drivers::xhci_hid_enumeration
```

API principal:

```text
xhci_hid_enumerate_port(port_id) -> slot_id
```

A função rejeita porta `0`, rejeita porta já associada a slot e usa o `slot_type` produzido pelo staging da mesma porta.

## Cadeia por Slot ID

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

`xhci_set_configuration_for_slot(slot_id)` continua responsável por inicializar Report Descriptor + `InputDevice`/map para o mesmo slot antes de publicar configuração pronta.

## Rollback fail-closed

Se uma falha ocorrer depois de Enable Slot:

1. marca o registro como `XHCI_DEVICE_STATE_FAILED`;
2. chama `xhci_hid_descriptor_release_input_device_for_slot(slot_id)`;
3. envia `xhci_trb_disable_slot(slot_id, ...)`;
4. exige Command Completion correspondente ao mesmo `slot_id`;
5. mantém o registro local em quarentena.

**Não chamar `xhci_device_table_release()` neste estágio.** `xhci_context` ainda recusa um slot cujo record anterior permanece `ready` com outro epoch. Release/reuse só entra no HID-4d depois de teardown explícito de todos os estados per-slot.

Se Disable Slot não puder ser confirmado, o slot continua `FAILED` e não é reutilizado.

## Iteração da próxima porta

```text
xhci_hid_enumerate_next_connected(after_port_id) -> slot_id
```

- força novo `xhci_port_scan()`;
- usa `xhci_port_next_connected(cursor)`;
- é bounded por `XHCI_HID_ENUMERATION_SCAN_LIMIT`;
- pula somente portas que já têm Slot ID;
- não pula silenciosamente uma porta nova que falhou.

## Compatibilidade

`post_cutover.sotlas` permanece inalterado neste corte. O primeiro teclado continua seguindo o pipeline histórico e o proof `sendkey a`.

O orquestrador 4c.4c é apenas compilado e testado agora. **HID-4c.4d** será o estágio que o conectará a uma segunda porta real no QEMU, mantendo o keyboard como primeiro HID e adicionando mouse como segundo device.

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
- HID-4c.4c ⏳ candidato atual;
- HID-4c.4d ⬜ dual-device QEMU;
- HID-4c.4e ⬜ interleaving/event demux;
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

# Próximo corte se HID-4c.4c ficar verde

**HID-4c.4d — dual-device runtime proof.**

Objetivo:

- QEMU com `qemu-xhci`;
- `usb-kbd` continua sendo o primeiro HID;
- adicionar `usb-mouse` como segunda porta/device;
- chamar o pipeline 4c.4c somente para a segunda porta após o proof legado do teclado;
- provar Slot IDs/epochs/DCIs/rings/identidades independentes;
- não declarar `MULTI_DEVICE_READY`/`DUAL_DEVICE_READY` até existir prova runtime real.

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
3. ler roadmap + handoff;
4. inspecionar assinaturas reais;
5. fazer um microcorte funcional;
6. preservar wrappers, markers e proofs;
7. se qualquer gate ficar vermelho, corrigir o próprio checkpoint antes de avançar.
