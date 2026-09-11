# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

Este arquivo é o registro operacional de continuidade. O roadmap estratégico está em `docs/BAKEN_OS_ROADMAP.md`; aqui ficam o SHA confiável, o candidato atual, os invariantes e o próximo corte seguro.

## Estado operacional

- fase atual: **Fase 2 — Platform/Drivers**;
- trilha atual: **Trilha B — HID/input de produção**;
- etapa atual: **HID-4c Multi-slot xHCI**;
- subetapa atual: **HID-4c.4 — enumeração simultânea real**;
- checkpoint certificado mais recente: **HID-4c.4a — reset explícito por porta**;
- candidato atual: **HID-4c.4b — inventário/seleção multi-port**;
- branch: **`main`**;
- Kernel Core: **congelado/invariant-preserving**.

## Política de certificação

Um incremento só vira baseline quando os três gates passam no **mesmo SHA**:

1. Baken OS CI/CD & Automated QEMU Verification;
2. Baken OS SMP Bring-up Verification;
3. Baken OS NVMe-only Bare-Metal Verification.

Não empilhar mudança funcional sobre candidato vermelho. Não remover marker/proof/teste nem ampliar timeout para mascarar regressão. APIs `_for(slot_id)` consomem estado/resultados do mesmo slot. Hardware, descriptors e eventos são input não confiável e falham fechado.

---

# Última baseline certificada

```text
8ef11b5e9298552d52eee3954ccd305e4421708d
feat(xhci): start HID-4c.4 per-port reset
```

Provas no mesmo SHA:

- CI #1139 / `34557045054` ✅;
- SMP #242 / `34557045108` ✅;
- NVMe #339 / `34557045133` ✅.

Essa baseline mantém o caminho QEMU legado do primeiro teclado verde e adiciona `xhci_port_reset_for(port_id)` sem remover `xhci_port_reset_first_connected()`.

---

# Candidato corrente — HID-4c.4b

Objetivo: permitir seleção sequencial e bounded de portas conectadas sem reinicializar infraestrutura global já usada pelo primeiro device.

## Inventário read-only

Novo contrato:

```text
xhci_port_next_connected(after_port_id)
```

Garantias:

- usa somente o inventário atual de `xhci_port_scan()`;
- começa em `after_port_id + 1`;
- percorre até `xhci_port_count()`;
- retorna somente snapshot `valid && connected`;
- retorna `0` ao final;
- não escreve MMIO;
- não executa reset, Enable Slot ou doorbell.

Exemplo de iteração futura:

```text
port = xhci_port_next_connected(0)
while port != 0:
    preparar/enumeração da porta
    port = xhci_port_next_connected(port)
```

## Staging por porta explícita

Novo contrato:

```text
xhci_port_stage_prepare_for(port_id)
```

Pré-condições e garantias:

- controller iniciado e No-op real concluído;
- `xhci_command_is_ready()` já verdadeiro;
- Supported Protocol + PORTSC são revalidados;
- `port_id` precisa estar no inventário e conectado;
- protocolo precisa ser USB2 ou USB3;
- usa `xhci_port_reset_for(port_id)`;
- confirma que `xhci_port_reset_port_id()` e protocolo correspondem à porta solicitada;
- publica somente o staging transitório da porta atual.

**Invariante crítico:** `xhci_port_stage_prepare_for(port_id)` não chama `xhci_command_prepare_after_noop()`. Esse helper reinicializa enqueue index, producer cycle, last slot e Event Consumer e só pertence ao bring-up inicial. Reexecutá-lo depois do primeiro dispositivo poderia invalidar o Command Ring em uso.

O wrapper legado:

```text
xhci_port_stage_prepare_first()
```

continua preservando a ordem histórica, inclusive `xhci_command_prepare_after_noop()` e `xhci_port_reset_first_connected()`.

`XHCI_PORT_STAGE_*` representa apenas a seleção transitória corrente; identidade multi-device durável continua em `xhci_device_table` por Slot ID + epoch.

Se este candidato ficar triplo verde, o próximo checkpoint será **HID-4c.4c — pipeline completo por porta**.

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

**✅ VALIDADO.** Tabela bounded de Slot IDs, port mapping/state/epoch, Device/Input Context e EP0 por slot, DCBAA correto e Address Device por slot.

## HID-4c.2 — endpoint/report transport per-slot

**✅ PRESENTE E REVALIDADO.** HID context, DCI/ring/max packet/interval, Configure Endpoint, report DMA/ring/produtor e completion por slot/DCI/TRB.

## HID-4c.3 — concluído

| Componente | Checkpoint |
|---|---|
| Device Descriptor per-slot | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 |
| Evaluate Context per-slot | `3688423e85a9c214755cc4c966c27910680663dc` — CI #1131 / SMP #234 / NVMe #331 |
| Configuration Descriptor per-slot | `72fa58228c24578ee50c39ca166d82ccc17a46a0` — CI #1132 / SMP #235 / NVMe #332 |
| HID Report Descriptor + InputDevice binding | `4ae0a5c6341dd6ea62d2ea05b62001382bfa467d` — CI #1135 / SMP #238 / NVMe #335 |
| HID report runtime per-slot | `93fe9d9639b366b9395b0b49f0f293bdf64de588` — CI #1136 / SMP #239 / NVMe #336 |
| SET_CONFIGURATION per-slot | `0ef4c670727a2d0b68324c4281972b2992fefb5c` — CI #1137 / SMP #240 / NVMe #337 |
| Slot coherence final | `6eec0dcc36a32c26108629e5ede9f0b929fef2e2` — CI #1138 / SMP #241 / NVMe #338 |

## HID-4c.4 — atual

1. **4c.4a reset explícito por porta** — ✅ `8ef11b5e...`, triplo verde;
2. **4c.4b inventário/seleção multi-port** — ⏳ candidato atual;
3. **4c.4c pipeline completo por porta** — próximo após triplo verde;
4. **4c.4d dual-device runtime** — keyboard primeiro + mouse segundo;
5. **4c.4e interleaving/event demux** — prova final de independência.

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

---

# Próximo corte se HID-4c.4b ficar verde

**HID-4c.4c — pipeline completo por porta.** Antes de programar, auditar as assinaturas reais de context/address/descriptor/configure endpoint/set configuration. O pipeline deve receber um `port_id` explícito, usar o `slot_type` do staging, criar um Slot ID novo e carregar o mesmo `slot_id` por toda a cadeia. Não modificar o post-cutover do primeiro teclado até existir prova independente do segundo device.

---

# ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8; checkpoint `7803447a`.

# Storage e demais trilhas

Continuam na Fase 2, fora do checkpoint HID atual. Storage alvo: `BlockDevice → Block Cache → Volume Manager → VFS → FAT32/exFAT/NTFS/ext/ISO-UDF/BakenFS`. Rede, áudio, GPU/composição e power/hot-plug avançado permanecem posteriores.

# Sotlas / toolchain

`HPinho/LangSotlas` permanece toolchain separada. Não fazer migração ampla durante HID-4c. Preferir sintaxe e intrinsics já comprovados.

---

# Regra de continuidade

1. confirmar `main` e SHA;
2. verificar CI/SMP/NVMe do mesmo SHA;
3. ler roadmap + handoff;
4. inspecionar assinaturas reais;
5. fazer um microcorte funcional;
6. preservar wrappers, markers e proofs;
7. se qualquer gate ficar vermelho, corrigir o próprio checkpoint antes de avançar.
