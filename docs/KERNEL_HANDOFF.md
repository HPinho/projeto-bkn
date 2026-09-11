# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

Este arquivo registra o estado operacional para continuidade. O roadmap estratégico está em `docs/BAKEN_OS_ROADMAP.md`.

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**;
- trilha: **Trilha B — HID/input de produção**;
- etapa: **HID-4c Multi-slot xHCI**;
- subetapa: **HID-4c.4 — enumeração simultânea real**;
- checkpoint certificado mais recente: **HID-4c.4c — pipeline completo por porta**;
- candidato atual: **HID-4c.4d — dual-device runtime proof**;
- branch: **`main`**;
- Kernel Core: **congelado/invariant-preserving**.

## Política de certificação

Um incremento só vira baseline quando os três gates passam no **mesmo SHA**:

1. Baken OS CI/CD & Automated QEMU Verification;
2. Baken OS SMP Bring-up Verification;
3. Baken OS NVMe-only Bare-Metal Verification.

Para HID-4c.4d existe ainda uma prova específica adicional: **Baken OS HID Dual-device Verification**, que não substitui os três gates acima.

Não empilhar mudança funcional sobre candidato vermelho. Não remover marker/proof/teste nem ampliar timeout para mascarar regressão. APIs `_for(slot_id)` consomem estado/resultados do mesmo slot.

---

# Última baseline certificada

```text
20b016973d12d4d669cf54ea79623a9116eb341f
feat(xhci): add per-port HID enumeration pipeline
```

Provas:

- CI #1141 / `34591682640` ✅;
- SMP #244 / `34591682675` ✅;
- NVMe #341 / `34591682642` ✅.

Essa baseline certifica:

- `xhci_hid_enumerate_port(port_id) -> slot_id`;
- toda a cadeia per-slot de Port Stage até HID Report Ring;
- rollback fail-closed com Disable Slot confirmado;
- quarentena `FAILED` sem reuse prematuro de epoch/context;
- caminho legado do primeiro teclado intacto.

---

# Candidato corrente — HID-4c.4d

Novo módulo:

```text
kernel::platform::hid_late_attach
```

API principal:

```text
platform_hid_late_attach_second_mouse()
```

## Contrato de runtime

1. o primeiro slot deve continuar sendo o teclado já certificado pelo `post_cutover`;
2. `xhci_hid_enumerate_next_connected(0)` seleciona a próxima porta sem Slot ID;
3. o segundo Slot ID precisa ser diferente do primeiro;
4. `xhci_slot_active_count()` precisa confirmar pelo menos dois slots;
5. `xhci_hid_enumeration_is_ready_for(second_slot)` precisa estar verdadeiro;
6. `xhci_hid_protocol_for(second_slot)` precisa ser `USB_HID_PROTOCOL_MOUSE`;
7. `xhci_hid_report_poll_slot_once(second_slot)` precisa completar Interrupt IN real;
8. o comprimento recebido precisa ser ao menos `XHCI_HID_BOOT_MOUSE_MIN_LENGTH`;
9. só então é emitido `BAKEN:USB_HID_DUAL_READY`.

O estado publica também `platform_hid_late_attach_is_ready()` e o Slot ID certificado do segundo HID.

## Integração

`baken_native_kernel_run()` chama o late attach imediatamente após validar o framebuffer e antes da inicialização AML/serviços. A chamada é deliberadamente **não fatal**:

```text
platform_hid_late_attach_second_mouse();
```

Hardware sem segundo HID continua inicializando. A ausência do marker não impede boot normal; somente o workflow de prova dual exige esse resultado.

O `post_cutover.sotlas` permanece inalterado. Isso preserva literalmente o proof histórico do primeiro teclado.

## Workflow dedicado

```text
.github/workflows/baken_hid_dual.yml
```

QEMU deve ser iniciado nessa ordem:

```text
-device qemu-xhci,id=xhci
-device usb-kbd,bus=xhci.0
-device usb-mouse,bus=xhci.0
```

A prova injeta repetidamente:

```text
sendkey a
mouse_move 5 3
```

O workflow só fica verde quando o serial contém:

```text
BAKEN:USB_HID_DUAL_READY
```

Esse marker não pode ser produzido por teste textual; ele só é emitido depois do report real do segundo slot.

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
- HID-4c.4d ⏳ candidato atual;
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

# Próximo corte se HID-4c.4d ficar verde

**HID-4c.4e — interleaving/event demux.**

Objetivo:

- manter keyboard e mouse ativos ao mesmo tempo;
- alternar eventos reais dos dois devices;
- provar completions atribuídas corretamente por Slot ID/DCI/TRB;
- provar que eventos `InputDevice + generation` não vazam entre slots;
- expandir o Event Ring demux somente se a prova runtime demonstrar necessidade;
- preservar integralmente o primeiro-keyboard proof.

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
3. em HID-4c.4d+, verificar também o workflow runtime específico quando aplicável;
4. ler roadmap + handoff;
5. inspecionar assinaturas reais;
6. fazer um microcorte funcional;
7. preservar wrappers, markers e proofs;
8. se qualquer gate ficar vermelho, corrigir o próprio checkpoint antes de avançar.
