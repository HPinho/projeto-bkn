# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

Este arquivo é o registro operacional de continuidade. O roadmap estratégico está em `docs/BAKEN_OS_ROADMAP.md`; aqui ficam o SHA confiável, o candidato atual, os invariantes e o próximo corte seguro.

## Estado operacional

- fase atual: **Fase 2 — Platform/Drivers**;
- trilha atual: **Trilha B — HID/input de produção**;
- etapa atual: **HID-4c Multi-slot xHCI**;
- subetapa atual: **HID-4c.4 — enumeração simultânea real**;
- primeiro corte HID-4c.4: **reset explícito por porta**;
- branch de trabalho: **`main`**;
- Kernel Core: **congelado/invariant-preserving**;
- `docs/BAKEN_OS_ROADMAP.md`: documento estratégico contínuo;
- `docs/KERNEL_HANDOFF.md`: estado operacional de continuidade.

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
- APIs `_for(slot_id)` usam exclusivamente o mesmo slot;
- hardware, descriptors e eventos são input não confiável e falham fechado.

---

# Última baseline certificada

```text
6eec0dcc36a32c26108629e5ede9f0b929fef2e2
feat(xhci): close HID-4c.3 slot coherence
```

Provas no mesmo SHA:

- CI #1138 / `34555120197` ✅ — suíte completa, grafo Sotlas, build nativo, ISO e QEMU;
- SMP #241 / `34555120203` ✅ — contracts, build e prova SMP;
- NVMe #338 / `34555120228` ✅ — contracts, build, fixture e QEMU NVMe-only.

Com esse SHA, **HID-4c.3 está fechado**.

A reconstrução segura de HID-4c.3 partiu de:

```text
9558e5b3cb83064cc6a0b1548f03b3ed12c35a22
test(xhci): guard transfer results per slot
```

Esse baseline foi triplo verde em CI #1127 / SMP #230 / NVMe #327.

---

# Candidato corrente — HID-4c.4a

Objetivo: remover a dependência de `first_connected` do reset de porta sem alterar o bring-up legado.

Novo contrato:

```text
xhci_port_reset_for(port_id)
```

Pré-condições e garantias:

- `port_id != 0`;
- `port_id` dentro do inventário retornado por `xhci_port_scan()`;
- controller iniciado e No-op já concluído;
- Supported Protocol revalidado para a porta;
- CCS presente antes do reset;
- USB2: PR → PRC → PED;
- USB3: PED já presente ou WPR → WRC → PED;
- PORTSC write image remove PED, RW1C, PR/WPR/LWS antes de adicionar o bit intencional;
- CCS + PED exigidos após sucesso;
- estado `XHCI_PORT_RESET_*` representa somente a última operação concluída, não identidade multi-device.

Compatibilidade obrigatória:

```text
xhci_port_reset_first_connected()
```

continua selecionando `xhci_first_connected_port()` e delega para `xhci_port_reset_for(port_id)`.

Se o candidato ficar triplo verde, o próximo microcorte é HID-4c.4b: inventário/seleção bounded de múltiplas portas conectadas elegíveis.

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
10. Slot ID reutilizado nunca reaproveita estado sem validar `epoch`.

---

# HID / input de produção

## HID-0..HID-4b

- HID-0 Boot HID xHCI: ✅;
- HID-1 Report Descriptor: ✅ `1b3f94cc`;
- HID-2 Field map/decoder: ✅ `a2e04a78`;
- HID-3 Event model: ✅ `2775c12a`;
- HID-4a Identity/lifecycle: ✅ `12c308b3`;
- HID-4b Per-device HID map: ✅ `dbc5669a`.

## HID-4c.1 — transport core

**✅ VALIDADO.**

- tabela bounded de Slot IDs;
- port mapping/state/epoch;
- Device/Input Context e EP0 por slot;
- DCBAA correto;
- Address Device por slot;
- wrappers do primeiro device preservados.

## HID-4c.2 — endpoint/report transport per-slot

**✅ PRESENTE E REVALIDADO.**

- HID context por slot+epoch;
- DCI/ring/max packet/interval por slot;
- Configure Endpoint per-slot;
- report DMA/ring/produtor/fallback Boot por slot;
- completion por slot/DCI/TRB.

## HID-4c.3 — concluído

| Componente | Checkpoint |
|---|---|
| Device Descriptor per-slot | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 |
| Evaluate Context per-slot | `3688423e85a9c214755cc4c966c27910680663dc` — CI #1131 / SMP #234 / NVMe #331 |
| Configuration Descriptor per-slot | `72fa58228c24578ee50c39ca166d82ccc17a46a0` — CI #1132 / SMP #235 / NVMe #332 |
| HID Report Descriptor + InputDevice binding | `4ae0a5c6341dd6ea62d2ea05b62001382bfa467d` — CI #1135 / SMP #238 / NVMe #335 |
| HID report runtime per-slot | `93fe9d9639b366b9395b0b49f0f293bdf64de588` — CI #1136 / SMP #239 / NVMe #336 |
| SET_CONFIGURATION per-slot | `0ef4c670727a2d0b68324c4281972b2992fefb5c` — CI #1137 / SMP #240 / NVMe #337 |
| slot coherence final | `6eec0dcc36a32c26108629e5ede9f0b929fef2e2` — CI #1138 / SMP #241 / NVMe #338 |

## HID-4c.4 — atual

Sequência segura:

1. **4c.4a** reset explícito por porta — candidato atual;
2. **4c.4b** iterar portas conectadas elegíveis de modo bounded;
3. **4c.4c** Reset → Enable Slot → Context → Address → descriptors → HID endpoint → SET_CONFIGURATION por porta/slot;
4. **4c.4d** manter keyboard como primeiro HID e adicionar mouse como segundo device;
5. **4c.4e** provar reports/identidade independentes e expandir demux apenas se necessário.

Não reaplicar automaticamente a antiga cadeia experimental HID-4c.4.

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

O proof continua exigindo Boot keyboard report real, comprimento mínimo de 8 bytes, Usage ID `4` (`A`) e `POST_CUTOVER_HID_REPORT_ATTEMPTS = 8`.

### QEMU

Baseline verde: `qemu-xhci` + `usb-kbd`, `sendkey a` pelo monitor.

Para HID-4c.4:

- keyboard permanece o primeiro HID;
- mouse entra depois como segundo device/slot;
- slot, epoch, endpoint/DCI, ring, generation e mapa permanecem independentes;
- Transfer Event de outro slot/DCI/TRB nunca satisfaz waiter incorreto.

---

# ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 fechados; checkpoint `7803447a`.

I2C-HID só começa depois de transporte I2C/ACPI seguro.

---

# Storage e demais trilhas

Continuam na Fase 2, fora do checkpoint HID atual.

Storage alvo:

```text
BlockDevice → Block Cache → Volume Manager → VFS
           → FAT32 / exFAT / NTFS / ext / ISO-UDF / BakenFS
```

Rede, áudio, GPU/composição e power/hot-plug avançado também permanecem posteriores ao foco HID atual.

---

# Sotlas / toolchain

`HPinho/LangSotlas` permanece toolchain separada. Não fazer migração ampla da toolchain durante HID-4c. Preferir sintaxe e intrinsics já comprovados no baseline verde.

---

# Regra de continuidade

Antes de programar:

1. confirmar `main` e SHA atual;
2. verificar CI/SMP/NVMe do mesmo SHA;
3. ler este handoff e a seção HID-4c do roadmap;
4. inspecionar assinaturas reais no head atual;
5. fazer um único microcorte funcional;
6. preservar wrappers, markers e proofs;
7. se qualquer gate ficar vermelho, corrigir o próprio checkpoint antes de avançar.
