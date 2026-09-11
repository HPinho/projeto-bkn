# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este é o registro operacional para continuidade do desenvolvimento. O roadmap estratégico está em `docs/BAKEN_OS_ROADMAP.md`; este arquivo deve responder rapidamente: **onde estamos, qual SHA é confiável, quais invariantes não podem quebrar, qual código está em validação e qual é o próximo corte seguro**.

## Estado operacional

- fase atual: **Fase 2 — Platform/Drivers**;
- trilha atual: **Trilha B — HID/input de produção**;
- etapa atual: **HID-4c Multi-slot xHCI**;
- subetapa: **HID-4c.3 — remoção dos singletons transport-specific restantes**;
- branch de trabalho: **`main`**;
- Kernel Core: **congelado/invariant-preserving**;
- `docs/BAKEN_OS_ROADMAP.md`: documento estratégico contínuo;
- `docs/KERNEL_HANDOFF.md`: reativado por solicitação do mantenedor e deve acompanhar checkpoints relevantes.

## Política de certificação

Um incremento só é considerado baseline quando os três gates abaixo passam no **mesmo SHA**:

1. Baken OS CI/CD & Automated QEMU Verification;
2. Baken OS SMP Bring-up Verification;
3. Baken OS NVMe-only Bare-Metal Verification.

Regras:

- trabalhar em incrementos pequenos diretamente em `main`;
- partir sempre do último checkpoint verde conhecido;
- não empilhar uma nova mudança funcional sobre candidato vermelho;
- não remover marker/proof/teste nem ampliar timeout para mascarar regressão;
- build Sotlas e runtime QEMU valem mais que guardrail puramente textual;
- qualquer API `_for(slot_id)` deve usar estado/resultados do mesmo slot;
- firmware, descriptors e eventos de hardware são input não confiável e devem falhar fechado.

---

# Última baseline certificada

```text
93fe9d9639b366b9395b0b49f0f293bdf64de588
feat(xhci): bind HID report runtime per slot
```

Provas do mesmo SHA:

- CI #1136 / `34551428603` ✅ — suíte completa, grafo Sotlas, build nativo, ISO e QEMU;
- SMP #239 / `34551428617` ✅ — contratos, build e prova SMP completos;
- NVMe #336 / `34551428650` ✅ — contratos, build, fixture e QEMU NVMe-only completos.

Essa baseline é descendente da retomada segura:

```text
9558e5b3cb83064cc6a0b1548f03b3ed12c35a22
test(xhci): guard transfer results per slot
```

`9558e5b` também foi triplo verde em CI #1127 / SMP #230 / NVMe #327 e é o ponto a partir do qual HID-4c.3 foi refeito em cortes pequenos após o rollback da cadeia experimental.

---

# Candidato corrente

**HID-4c.3 — SET_CONFIGURATION por Slot ID + epoch.**

O candidato corrente substitui os antigos singletons:

```text
XHCI_SET_CONFIGURATION_READY
XHCI_SET_CONFIGURATION_VALUE
```

por uma tabela fixa:

```text
XHCI_SET_CONFIGURATION_STATES[slot_id]
```

Cada entrada mantém:

- `ready`;
- `epoch`;
- `configuration value`.

A operação real deve usar exclusivamente o mesmo `slot_id` em:

```text
xhci_address_is_ready_for(slot_id)
xhci_configuration_is_ready_for(slot_id)
xhci_configuration_value_for(slot_id)
xhci_configure_endpoint_is_ready_for(slot_id)
xhci_ep0_is_ready_for(slot_id)
xhci_ep0_producer_cycle_for(slot_id)
xhci_ep0_submit_control_td_for_slot(slot_id, ...)
xhci_transfer_wait_ep0_completion(slot_id, ...)
xhci_transfer_last_residual_length_for(slot_id)
xhci_hid_descriptor_initialize_for_slot(slot_id)
xhci_hid_descriptor_is_ready_for(slot_id)
```

O wrapper `xhci_set_first_configuration()` continua existindo e deve apenas escolher o slot ativo de Configure Endpoint e delegar para `xhci_set_configuration_for_slot(slot_id)`.

**Não declarar este candidato certificado até CI + SMP + NVMe-only ficarem verdes no mesmo head.**

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
9. xHCI/HID não pode depender de UEFI após cutover;
10. nenhum novo estado de driver pode reutilizar Slot ID stale sem conferir `epoch`.

---

# ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 permanecem fechados. Checkpoint final: `7803447a`.

Não reabrir ACPI/AML por causa do HID xHCI. I2C-HID só começa depois de transporte I2C/ACPI seguro.

---

# HID / input de produção

## HID-0

**✅ COMPROVADO.** Boot HID xHCI com Interrupt IN real.

## HID-1

**✅ COMPROVADO em `1b3f94cc`.** Report Descriptor real via EP0 e parser bounded.

## HID-2

**✅ COMPROVADO em `a2e04a78`.** Field map/decoder por Report ID, Usage, offsets e flags.

## HID-3

**✅ COMPROVADO em `2775c12a`.** Event model/fila normalizada. O runtime continua exigindo markers de event model/event ready.

## HID-4a

**✅ CERTIFICADO em `12c308b3`.** `device_id + generation`, lifecycle ATTACHED/ACTIVE/FAILED/DETACHED, fila SMP-safe e purge generation-safe.

## HID-4b

**✅ CERTIFICADO em `dbc5669a`.** HID field map persistente por `device_id + generation`; parser HID-1 continua stateless.

## HID-4c.1 — transport core

**✅ VALIDADO.**

- `xhci_device_table`: 256 Slot IDs, port mapping, state e epoch;
- context/address/EP0 por slot;
- DCBAA no índice correto;
- wrappers legados do primeiro device preservados.

## HID-4c.2 — endpoint/report transport per-slot

**✅ PRESENTE E REVALIDADO.**

- `xhci_hid_context` por slot+epoch;
- DCI/ring/max packet/interval por slot;
- Configure Endpoint per-slot;
- report DMA/ring/produtor/fallback Boot por slot;
- transfer completion identificado por slot/DCI/TRB.

## HID-4c.3 — checkpoint por checkpoint

| Componente | Estado | Checkpoint |
|---|---|---|
| Device Descriptor per-slot | ✅ | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 |
| Evaluate Context per-slot | ✅ | `3688423e85a9c214755cc4c966c27910680663dc` — CI #1131 / SMP #234 / NVMe #331 |
| Configuration Descriptor per-slot | ✅ | `72fa58228c24578ee50c39ca166d82ccc17a46a0` — CI #1132 / SMP #235 / NVMe #332 |
| HID Report Descriptor + InputDevice binding | ✅ | `4ae0a5c6341dd6ea62d2ea05b62001382bfa467d` — CI #1135 / SMP #238 / NVMe #335 |
| HID report runtime identity/result per-slot | ✅ | `93fe9d9639b366b9395b0b49f0f293bdf64de588` — CI #1136 / SMP #239 / NVMe #336 |
| SET_CONFIGURATION per-slot | ⏳ | candidato corrente |
| report prepare ligado ao SET_CONFIGURATION do mesmo slot | ⬜ | próximo microcorte após candidato verde |

### Erros já encontrados nesta retomada

- `e82246b...` chamou um nome de API de Device Descriptor inexistente; corrigido em `3688423e...` usando as APIs certificadas reais;
- o primeiro candidato de HID descriptor per-slot revelou guardrails antigos que procuravam helper singleton; corrigidos em `0e50c8a...` e `4ae0a5c...` sem relaxar semântica;
- não repetir a cadeia experimental removida de HID-4c.3/4c.4 por cherry-pick em bloco.

### Caminho legado obrigatório do primeiro teclado

Preservar esta sequência enquanto o multi-device é construído:

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

O proof continua exigindo report Boot keyboard real, comprimento mínimo de 8 bytes e Usage ID `4` (`A`) dentro do limite `POST_CUTOVER_HID_REPORT_ATTEMPTS = 8`.

### QEMU

O workflow verde atual usa `qemu-xhci` + `usb-kbd` e injeta `sendkey a` via monitor.

Para HID-4c.4:

- manter keyboard como primeiro USB HID;
- adicionar mouse como segundo device somente quando a cadeia per-slot estiver integralmente certificada;
- não depender de comando de mouse do HMP sem confirmar suporte real;
- provar identidade/eventos independentes dos dois dispositivos.

---

# Próximo passo após o candidato corrente

Se SET_CONFIGURATION per-slot ficar verde nos três gates:

1. trocar `xhci_hid_report_prepare_for_slot(slot_id)` para exigir `xhci_set_configuration_is_ready_for(slot_id)` em vez do wrapper global;
2. adicionar guardrail impedindo `xhci_set_configuration_is_ready()` dentro do caminho `_for(slot_id)`;
3. validar CI + SMP + NVMe no mesmo SHA;
4. declarar HID-4c.3 fechado;
5. iniciar HID-4c.4 com enumeração de múltiplas portas/devices, sem reutilizar automaticamente os commits experimentais antigos.

Após HID-4c.4: **HID-4d hot-plug/recovery**.

---

# Storage e demais trilhas

Storage de produção/VFS, rede, áudio e GPU/composição pertencem à Fase 2, porém estão fora do foco atual. Não misturar essas alterações aos checkpoints HID.

A arquitetura de storage planejada permanece `BlockDevice → Block Cache → Volume Manager → VFS → drivers FAT32/exFAT/NTFS/ext/ISO-UDF/BakenFS`.

---

# Sotlas / toolchain

`HPinho/LangSotlas` permanece um repositório/toolchain separado. Recursos úteis já auditados incluem atomics, IRQ save/restore, fences, slices, Result e SIR, mas **não fazer migração ampla de toolchain durante HID-4c**.

Ao introduzir alguma API nova no compilador, provar primeiro que ela é necessária e compatível com o grafo Baken. Preferir formas de sintaxe já compiladas na baseline verde.

---

# Regra de continuidade para o próximo chat/agente

Antes de programar:

1. confirmar `main` e SHA atual;
2. verificar CI/SMP/NVMe do mesmo SHA;
3. ler este handoff e a seção HID-4c do roadmap;
4. inspecionar as assinaturas reais no head atual — nunca inferir nomes de API;
5. fazer um único microcorte funcional;
6. preservar wrappers/markers/proofs existentes;
7. parar e corrigir o próprio checkpoint se qualquer gate ficar vermelho.
