# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-11 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `⬜ PLANEJADO`.

Uma feature só vira baseline integrada quando **CI principal + SMP + NVMe-only** passam no mesmo SHA. Para a trilha HID multi-device, a prova **HID Dual-device** também permanece obrigatória. Teste textual não substitui build Sotlas nativo, ISO nem prova QEMU.

## Estado geral

- **Fase 0 — Fundação Bare-Metal:** ✅ CONCLUÍDA
- **Fase 1 — Kernel Core:** ✅ CONCLUÍDA E CERTIFICADA
- **Fase 2 — Platform/Drivers:** ▶️ EM DESENVOLVIMENTO
- **Fase 3 — Serviços e Userspace:** ⬜ PLANEJADA
- **Fase 4 — Experiência Baken:** ⬜ PLANEJADA

## Posição atual

O desenvolvimento está na **Fase 2 — Platform/Drivers**, **Trilha B — HID/input de produção**.

O **HID-4c — multi-slot xHCI está concluído e certificado**, incluindo enumeração real keyboard+mouse, dois TDs simultaneamente outstanding, demultiplexação por Slot ID + epoch e prova QEMU de interleaving.

O trabalho atual está em **HID-4d — hot-plug/recovery**:

- **HID-4d.1 — detecção e quarentena de detach:** ✅ CERTIFICADO
- **HID-4d.2a — coexistência Command Completion + Transfer Event:** ✅ CERTIFICADO
- **HID-4d.2b — `Stop Endpoint` + drain terminal:** ⏳ CANDIDATO ATUAL
- HID-4d.3 — teardown generation-safe de HID/transfer/config/context: ⬜
- HID-4d.4 — `Disable Slot` + release + reuse com epoch novo: ⬜
- HID-4d.5 — prova detach → reattach → reenumeração: ⬜

O Kernel Core permanece congelado e invariant-preserving.

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.**

ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guarded stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI base, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32 base, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.**

Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP→AP e teardown seguro.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 fechados; checkpoint final `7803447a`.

## Trilha B — HID / input de produção

| Etapa | Estado | Objetivo |
|---|---|---|
| HID-0 Boot HID xHCI | ✅ | keyboard/mouse Boot + Interrupt IN real |
| HID-1 Report Descriptor | ✅ | fetch real + parser bounded |
| HID-2 Field map / decoder | ✅ | Report ID, Usage, offsets, flags e valores |
| HID-3 Input event model | ✅ | fila e eventos normalizados |
| HID-4a Identity/lifecycle | ✅ | `device_id + generation` |
| HID-4b Per-device HID map | ✅ | mapa por `device_id + generation` |
| HID-4c Multi-slot xHCI | ✅ | multi-device real + interleaving |
| HID-4d Hot-plug/recovery | ⏳ | detach, cancel, teardown, reuse e reenumeração |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### Checkpoints HID certificados

- HID-1 `1b3f94cc` — CI #1059 / SMP #162 / NVMe #259
- HID-2 `a2e04a78` — CI #1063 / SMP #166 / NVMe #263
- HID-3 `2775c12a` — CI #1066 / SMP #169 / NVMe #266
- HID-4a `12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c` — CI #1072 / SMP #175 / NVMe #272
- HID-4b `dbc5669aebd635b4e94c6e18e209f306cba5837f` — CI #1074 / SMP #177 / NVMe #274
- HID-4c.3 final `6eec0dcc36a32c26108629e5ede9f0b929fef2e2` — CI #1138 / SMP #241 / NVMe #338

### HID-4c.4 — multi-device real

| Subetapa | Estado | Checkpoint / prova |
|---|---|---|
| 4c.4a Reset explícito por porta | ✅ | `8ef11b5e9298552d52eee3954ccd305e4421708d` — CI #1139 / SMP #242 / NVMe #339 |
| 4c.4b Inventário/seleção multi-port | ✅ | `ff98c978ea9f11f78217369a9ec856ffcdf7a45b` — CI #1140 / SMP #243 / NVMe #340 |
| 4c.4c Pipeline completo por porta | ✅ | `20b016973d12d4d669cf54ea79623a9116eb341f` — CI #1141 / SMP #244 / NVMe #341 |
| 4c.4d Dual-device runtime proof | ✅ | `6e2ad50d613fcaf11bfa2c48d74f477ee6b76bfe` — CI #1142 / SMP #245 / NVMe #342 / HID Dual #1 |
| 4c.4e Interleaving/event demux | ✅ | `2a06393a144ded56dc9f3959314633f48792885a` — CI #1148 / SMP #251 / NVMe #348 / HID Dual #7 |

A prova final 4c.4e mantém um consumidor único do Event Ring, arma keyboard e mouse simultaneamente, roteia Transfer Events por Slot ID + epoch e exige:

```text
BAKEN:USB_HID_DUAL_READY
BAKEN:USB_HID_INTERLEAVE_READY
```

## HID-4d — hot-plug/recovery

### HID-4d.1 — detach detection + quarantine

**✅ CERTIFICADO.**

Checkpoint `8473860f975d6e9faab50b85a65314c2f49dc931` (`feat(xhci): quarantine detached HID slots`).

- CI #1150 / `34606338435` ✅
- SMP #253 / `34606338434` ✅
- NVMe #350 / `34606338405` ✅
- HID Dual-device #9 / `34606338389` ✅

O corte introduziu `XHCI_DEVICE_STATE_DETACH_PENDING`, transição dedicada por `slot_id + epoch`, scan read-only de PORTSC e bloqueio de novos `prepare/submit`.

### HID-4d.2a — Command/Transfer coexistence

**✅ CERTIFICADO.**

Checkpoint:

```text
d5d975dc396fb85fc3b3551a2969c9c9114c55b4
feat(xhci): prepare safe HID endpoint cancellation
```

Provas no mesmo SHA:

- CI #1152 / `34609196376` ✅
- SMP #255 / `34609196371` ✅
- NVMe #352 / `34609196531` ✅
- HID Dual-device #11 / `34609196451` ✅

Esse checkpoint permite que `xhci_command_wait_completion()` encontre um Transfer Event enquanto aguarda Command Completion e o encaminhe ao demux `xhci_transfer_route_next_event()`. O construtor puro `xhci_trb_stop_endpoint(slot_id, endpoint_id, cycle)` também está certificado, ainda sem emissão nesse checkpoint.

### HID-4d.2b — Stop Endpoint + drain terminal

**⏳ CANDIDATO ATUAL.**

Contrato do microcorte:

```text
DETACH_PENDING + mesmo slot/epoch
→ captura se havia TD HID outstanding
→ Stop Endpoint(slot_id, HID DCI)
→ Command Completion SUCCESS + Slot ID exato
→ se havia TD: coleta Transfer Event exato do mesmo slot/DCI/TRB
→ aceita somente SUCCESS em corrida normal ou completion 26/27/28 de Stop Endpoint
→ limpa apenas transfer_pending/TRB/length do report state
→ não parseia/publica input do TD cancelado
→ exige mailbox vazia
→ endpoint_stopped = true no mesmo epoch
```

Completion Codes terminais usados pela especificação xHCI:

- `26` — Stopped
- `27` — Stopped - Length Invalid
- `28` — Stopped - Short Packet

Qualquer outro erro permanece fail-closed.

Este corte **não** executa `Disable Slot`, `input_device_detach`, release de identidade, limpeza de contexts/rings/descriptors nem reuse de Slot ID. `xhci_hid_lifecycle_can_finalize_for()` só abre o gate seguinte após `endpoint_stopped` e ausência de TD/mailbox pendentes.

### Próximos microcortes HID-4d

1. **4d.3 — teardown per-epoch:** limpar report/transfer/descriptor/map/InputDevice binding, configuration, endpoint, EP0/context no mesmo epoch.
2. **4d.4 — Disable Slot + release:** só depois do teardown completo; liberar record e permitir reuse com epoch novo.
3. **4d.5 — runtime proof:** detach → cancel → teardown → reattach → reenumeração, sem estado stale.

### Invariantes HID permanentes

- Event Ring possui um único consumidor global.
- API `_for(slot_id)` só usa identidade/resultados do mesmo slot e epoch.
- Slot ID reutilizado exige cleanup completo e epoch novo.
- `DETACH_PENDING` bloqueia novos TDs, mas não apaga um TD já outstanding.
- Stop Endpoint só marca `endpoint_stopped` depois de Command Completion e drain terminal.
- TD cancelado não pode virar evento de teclado/mouse.
- `sendkey a`, `DUAL_READY` e `INTERLEAVE_READY` continuam obrigatórios nos respectivos proofs.
- não ampliar timeout, remover marker ou enfraquecer teste para obter verde.
- hardware, descriptors e events são input não confiável e devem falhar fechado.

### Caminho legado do primeiro teclado

Permanece preservado:

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

## Trilha C — Storage de produção

Fundação presente: `AHCI/NVMe → BlockDevice → GPT/MBR → FAT32 base`.

| Etapa | Estado |
|---|---|
| STORAGE-0 Block cache | ⬜ |
| STORAGE-1 Volume manager | ⬜ |
| STORAGE-2 VFS core | ⬜ |
| STORAGE-3 FAT32 produção RW | ⬜ |
| STORAGE-4 exFAT | ⬜ |
| STORAGE-5 NTFS RO seguro primeiro | ⬜ |
| STORAGE-6 ext2/ext3/ext4 RO primeiro | ⬜ |
| STORAGE-7 ISO9660/UDF RO | ⬜ |
| STORAGE-8 BakenFS v1 | ⬜ |
| STORAGE-9 Page/file cache + mmap | ⬜ |
| STORAGE-10 Async I/O + recovery | ⬜ |

## Outras trilhas de Fase 2

- Rede: ⬜ NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS
- Áudio: ⬜ HDA, DMA/ring, codec/mixer, API userspace
- GPU/composição: ⬜ compositor e aceleração, com framebuffer fallback
- Power/hot-plug ACPI avançado: ⬜ somente depois das bases de driver atuais

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API Ring3, executáveis Sotlas, IPC, init/service manager e COW/demand paging.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, shell, installer/OOBE, apps base, recovery e E2E.

---

# Regras permanentes

1. `main` recebe microcortes a partir do último checkpoint verde.
2. Não empilhar funcionalidade sobre candidato vermelho.
3. Runtime QEMU vale mais que teste textual isolado.
4. Kernel Core permanece congelado.
5. Firmware/hardware/descriptors/metadata são input não confiável.
6. Unsupported = fail-closed, nunca valor inventado.
7. Não remover proof/marker nem ampliar timeout para mascarar regressão.
8. Certificações entram neste roadmap com SHA e runs exatos.
9. Storage não bypassa BlockDevice/VFS.
10. `HPinho/LangSotlas` permanece toolchain separada; migração ampla não entra em checkpoint crítico de driver.
