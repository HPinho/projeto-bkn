# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este arquivo é o registro operacional de continuidade. O roadmap estratégico está em `docs/BAKEN_OS_ROADMAP.md`; aqui ficam o SHA confiável, o candidato atual, os invariantes e o próximo corte seguro.

## Estado operacional

- fase atual: **Fase 2 — Platform/Drivers**;
- trilha atual: **Trilha B — HID/input de produção**;
- etapa atual: **HID-4c Multi-slot xHCI**;
- subetapa: **HID-4c.3 — fechamento dos singletons transport-specific**;
- estado da subetapa: **implementação completa; certificação final do report gate em andamento**;
- branch de trabalho: **`main`**;
- Kernel Core: **congelado/invariant-preserving**;
- próximo bloco após triplo verde: **HID-4c.4 — keyboard + mouse simultâneos reais no mesmo xHC**.

## Política de certificação

Um incremento só vira baseline quando os três gates passam no **mesmo SHA**:

1. Baken OS CI/CD & Automated QEMU Verification;
2. Baken OS SMP Bring-up Verification;
3. Baken OS NVMe-only Bare-Metal Verification.

Regras:

- trabalhar em microcortes diretamente em `main`;
- partir do último checkpoint verde;
- não empilhar mudança funcional sobre candidato vermelho;
- não remover marker/proof/teste nem ampliar timeout para mascarar regressão;
- build Sotlas e runtime QEMU valem mais que guardrail textual;
- qualquer API `_for(slot_id)` deve consumir estado/resultados do mesmo slot;
- descriptors/eventos/hardware são input não confiável e devem falhar fechado.

---

# Última baseline certificada

```text
0ef4c670727a2d0b68324c4281972b2992fefb5c
feat(xhci): isolate set configuration per slot
```

Provas no mesmo SHA:

- CI #1137 / `34553335969` ✅ — suíte completa, grafo Sotlas, build nativo, ISO e QEMU;
- SMP #240 / `34553335968` ✅ — contracts, build e prova SMP;
- NVMe #337 / `34553335991` ✅ — contracts, build, fixture e QEMU NVMe-only.

Essa baseline é descendente do rollback seguro:

```text
9558e5b3cb83064cc6a0b1548f03b3ed12c35a22
test(xhci): guard transfer results per slot
```

`9558e5b` foi triplo verde em CI #1127 / SMP #230 / NVMe #327 e é a origem da reconstrução incremental de HID-4c.3.

---

# Candidato corrente — fechamento HID-4c.3

O último microcorte move a decisão final de readiness do report para o mesmo Slot ID.

Dentro de:

```text
xhci_hid_report_prepare_for_slot(slot_id)
```

o runtime passa a exigir:

```text
xhci_hid_context_is_ready_for(slot_id)
xhci_configure_endpoint_is_ready_for(slot_id)
xhci_set_configuration_is_ready_for(slot_id)
xhci_set_configuration_value_for(slot_id) == xhci_configuration_value_for(slot_id)
xhci_hid_descriptor_input_map_is_ready_for(slot_id)
InputDevice ativo cuja transport_address == slot_id
```

O wrapper:

```text
xhci_hid_report_prepare()
```

somente resolve o slot ativo de Configure Endpoint e delega para `_for_slot`; ele não decide mais readiness de SET_CONFIGURATION globalmente.

Guardrail obrigatório: o corpo de `xhci_hid_report_prepare_for_slot(slot_id)` não pode voltar a chamar `xhci_set_configuration_is_ready()`.

Se CI + SMP + NVMe ficarem verdes no SHA deste candidato, declarar **HID-4c.3 fechado** e iniciar HID-4c.4.

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
10. Slot ID reutilizado nunca pode reaproveitar estado sem validar `epoch`.

---

# ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 fechados; checkpoint `7803447a`.

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

**✅ COMPROVADO em `2775c12a`.** Event model/fila normalizada.

## HID-4a

**✅ CERTIFICADO em `12c308b3`.** `device_id + generation`, lifecycle e fila SMP-safe.

## HID-4b

**✅ CERTIFICADO em `dbc5669a`.** HID field map persistente por `device_id + generation`.

## HID-4c.1 — transport core

**✅ VALIDADO.**

- tabela de 256 Slot IDs com port mapping/state/epoch;
- context/address/EP0 por slot;
- DCBAA no índice correto;
- wrappers do primeiro device preservados.

## HID-4c.2 — endpoint/report transport per-slot

**✅ PRESENTE E REVALIDADO.**

- HID context por slot+epoch;
- DCI/ring/max packet/interval por slot;
- Configure Endpoint per-slot;
- report DMA/ring/produtor/fallback Boot por slot;
- completion identificada por slot/DCI/TRB.

## HID-4c.3 — checkpoints

| Componente | Estado | Checkpoint |
|---|---|---|
| Device Descriptor per-slot | ✅ | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 |
| Evaluate Context per-slot | ✅ | `3688423e85a9c214755cc4c966c27910680663dc` — CI #1131 / SMP #234 / NVMe #331 |
| Configuration Descriptor per-slot | ✅ | `72fa58228c24578ee50c39ca166d82ccc17a46a0` — CI #1132 / SMP #235 / NVMe #332 |
| HID Report Descriptor + InputDevice binding | ✅ | `4ae0a5c6341dd6ea62d2ea05b62001382bfa467d` — CI #1135 / SMP #238 / NVMe #335 |
| HID report runtime identity/result per-slot | ✅ | `93fe9d9639b366b9395b0b49f0f293bdf64de588` — CI #1136 / SMP #239 / NVMe #336 |
| SET_CONFIGURATION per-slot | ✅ | `0ef4c670727a2d0b68324c4281972b2992fefb5c` — CI #1137 / SMP #240 / NVMe #337 |
| report prepare + configuration value do mesmo slot | ⏳ | candidato atual; aguarda triplo verde |

### Erros já encontrados na retomada

- `e82246b...` chamou nome de API de Device Descriptor inexistente; corrigido em `3688423e...` usando as assinaturas certificadas reais;
- a migração do HID descriptor revelou guardrails singleton antigos; corrigidos em `0e50c8a...` e `4ae0a5c...` sem relaxar semântica;
- não reaplicar a antiga cadeia experimental HID-4c.3/4c.4 por cherry-pick em bloco.

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

O proof continua exigindo Boot keyboard report real, comprimento mínimo de 8 bytes e Usage ID `4` (`A`), com `POST_CUTOVER_HID_REPORT_ATTEMPTS = 8`.

### QEMU

O runtime certificado usa `qemu-xhci` + `usb-kbd` e injeta `sendkey a` pelo monitor.

No HID-4c.4:

- keyboard continua primeiro HID para preservar o proof histórico;
- mouse entra como segundo device/slot;
- cada device deve manter slot, epoch, endpoint/DCI, ring, mapa, generation e evento independentes;
- não aceitar Transfer Event de outro slot/DCI/TRB;
- não reutilizar automaticamente os commits experimentais antigos.

---

# Próximo bloco após triplo verde

**HID-4c.4 — enumeração simultânea real.**

Sequência recomendada:

1. auditar APIs de port/slot/event disponíveis no head certificado;
2. iterar portas conectadas elegíveis de modo bounded;
3. Enable Slot → Context → Address → descriptors → endpoint → SET_CONFIGURATION por porta/slot;
4. manter teclado no primeiro slot e adicionar mouse no segundo;
5. provar reports independentes e identidade correta;
6. só depois introduzir event demux/interleaving adicional se a prova real exigir;
7. certificar CI + SMP + NVMe no mesmo SHA antes de HID-4d.

Após HID-4c.4: **HID-4d hot-plug/recovery**.

---

# Storage e demais trilhas

Storage de produção/VFS, rede, áudio e GPU/composição pertencem à Fase 2, mas ficam fora do checkpoint HID atual.

Arquitetura planejada de storage:

```text
BlockDevice → Block Cache → Volume Manager → VFS
           → FAT32 / exFAT / NTFS / ext / ISO-UDF / BakenFS
```

Não misturar essas implementações ao fechamento HID.

---

# Sotlas / toolchain

`HPinho/LangSotlas` permanece toolchain/repositório separado. Atomics, IRQ save/restore, fences, slices, Result e SIR podem ser aproveitados depois, seletivamente. Não fazer migração ampla da toolchain durante HID-4c.

Preferir sempre formas de sintaxe já compiladas na baseline verde.

---

# Regra de continuidade para o próximo chat/agente

Antes de programar:

1. confirmar `main` e SHA atual;
2. verificar CI/SMP/NVMe do mesmo SHA;
3. ler este handoff e a seção HID-4c do roadmap;
4. inspecionar assinaturas reais no head atual — nunca inferir nomes de API;
5. fazer um único microcorte funcional;
6. preservar wrappers, markers e proofs existentes;
7. parar e corrigir o próprio checkpoint se qualquer gate ficar vermelho.
