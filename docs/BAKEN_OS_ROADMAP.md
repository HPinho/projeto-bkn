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
- **HID-4d.2b — `Stop Endpoint` + drain terminal:** ✅ CERTIFICADO
- **HID-4d.3a — lifetime de DMA temporário:** ✅ CERTIFICADO
- **HID-4d.3b0 — `dma_release()` com liberação arbitrária:** ✅ CERTIFICADO
- **HID-4d.3b1 — gate de teardown lógico generation-safe:** ✅ CERTIFICADO
- **HID-4d.3b — teardown HID lógico generation-safe:** ⏳ EM DESENVOLVIMENTO
  - serialização SMP do report decode vs detach: ✅ CERTIFICADA
  - pending queries exact-epoch: ✅ CERTIFICADAS
  - demux/waiter exact-epoch: ✅ CERTIFICADO
  - lifecycle pending checks exact-epoch: ✅ CERTIFICADO
  - liberação lógica real de InputDevice/map/descriptor/report DMA: ⬜ PRÓXIMO MICROCORTE
- HID-4d.3c — Drop Endpoint / rings: ⬜
- HID-4d.4 — `Disable Slot` + context release: ⬜
- HID-4d.5 — reuse de Slot ID + epoch novo + drain/barrier: ⬜
- HID-4d.6 — runtime proof / hotplug stress: ⬜

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

A prova final 4c.4e mantém um consumidor único do Event Ring, arma keyboard e mouse simultaneamente, roteia Transfer Events por Slot ID + epoch e exige `BAKEN:USB_HID_DUAL_READY` e `BAKEN:USB_HID_INTERLEAVE_READY`.

## HID-4d — hot-plug/recovery

### HID-4d.1 — detach detection + quarantine

**✅ CERTIFICADO.** Checkpoint `8473860f975d6e9faab50b85a65314c2f49dc931`.

- CI #1150 / `34606338435` ✅
- SMP #253 / `34606338434` ✅
- NVMe #350 / `34606338405` ✅
- HID Dual-device #9 / `34606338389` ✅

### HID-4d.2a — Command/Transfer coexistence

**✅ CERTIFICADO.** Checkpoint `d5d975dc396fb85fc3b3551a2969c9c9114c55b4`.

- CI #1152 / `34609196376` ✅
- SMP #255 / `34609196371` ✅
- NVMe #352 / `34609196531` ✅
- HID Dual-device #11 / `34609196451` ✅

### HID-4d.2b — Stop Endpoint + drain terminal

**✅ CERTIFICADO.**

Checkpoint:

```text
efde07d76bb2a27d50fe91e0e2eae208ea624459
feat(xhci): stop detached HID endpoints safely
```

Provas no mesmo SHA:

- CI #1153 / `34618305685` ✅
- SMP #256 / `34618305742` ✅
- NVMe #353 / `34618305799` ✅
- HID Dual-device #12 / `34618305732` ✅

O corte certifica `DETACH_PENDING → Stop Endpoint → Command Completion → drain terminal`, aceitando apenas SUCCESS ou os Completion Codes xHCI 26/27/28 para o TD parado. O TD cancelado nunca passa pelo parser HID e `endpoint_stopped` só é publicado após mailbox e report pending estarem vazios.

### HID-4d.3a — lifetime de DMA temporário

**✅ CERTIFICADO.**

Checkpoint:

```text
322a472edd3cc30e6fb1d28384802ec1a1844809
fix(xhci): release temporary enumeration DMA
```

Provas no mesmo SHA:

- CI #1154 / `34621455000` ✅
- SMP #257 / `34621454947` ✅
- NVMe #354 / `34621454968` ✅
- HID Dual-device #13 / `34621454938` ✅

A auditoria do teardown encontrou dois buffers de enumeração que eram temporários, mas permaneciam alocados sem referência persistente:

1. `GET_DESCRIPTOR(Device)` de 8 bytes, usado apenas para `bMaxPacketSize0`;
2. header de 9 bytes do `Configuration Descriptor`, usado apenas para `wTotalLength` e `bConfigurationValue`.

O 4d.3a passa a executar, somente após Transfer Completion + parse válido:

```text
DMA temporário shared
→ dma_unshare_from_device
→ dma_buffer_cpu_owned
→ dma_release
→ só então publica probe/header ready
```

O Device Descriptor completo e o Configuration Descriptor completo continuam persistentes no estado do slot e **não** são liberados neste corte.

### HID-4d.3b0 — arbitrary DMA release

**✅ CERTIFICADO.** Checkpoint `913663e673eb73ba127644bef98427e658bf95cb`.

Provas no mesmo SHA:

- CI #1156 ✅
- SMP #259 ✅
- NVMe #356 ✅
- HID Dual-device #15 ✅

O teardown real não pode depender da ordem global de alocação entre dispositivos. O PMM já fornece `pmm_free_pages(base, count)` bitmap-backed, lock/IRQ-safe e capaz de liberar ranges fora de ordem; portanto o allocator não é redesenhado.

Este microcorte altera somente o backend normal de `dma_release()`:

```text
pmm_free_pages_lifo(buffer.physical_address, page_count)
→ pmm_free_pages(buffer.physical_address, page_count)
```

O contrato permanece fail-closed:

- `buffer != null`;
- somente `DMA_OWNER_CPU` ou `DMA_OWNER_COMPLETED` passam por `dma_buffer_cpu_owned()`;
- `DMA_OWNER_DEVICE` e `DMA_OWNER_SHARED` continuam proibidos;
- allocator precisa estar disponível;
- o `DmaBuffer` só é invalidado depois de o PMM confirmar o free.

Os `pmm_free_pages_lifo()` de `dma_alloc()` e `dma_alloc_for_device()` permanecem intactos quando representam rollback imediato da própria alocação recém-feita.

Guardrails do corte: `tests/test_dma_release.py` + atualização da expectativa legada em `tests/test_dma_contract.py`.

### HID-4d.3b — teardown HID lógico generation-safe

A macroetapa **4d.3b continua em desenvolvimento**. Os microcortes abaixo são pré-requisitos certificados para executar a liberação lógica real sem permitir que uma geração antiga destrua estado novo.

| Microcorte / hardening | Estado | Checkpoint / provas |
|---|---|---|
| 4d.3b1 — gate lógico `slot_id + epoch` | ✅ | `f2139d41580384d7ef392f789afabbb35b19e313` — CI #1159 / SMP #262 / NVMe #359 / HID Dual #18 |
| Serialização SMP report decode × detach | ✅ | `6eb10542e4ab024dda2c28ba25dfcb97fb83dbcb` — CI #1161 / SMP #264 / NVMe #361 / HID Dual #20 |
| Pending queries exact-epoch | ✅ | `b6b7efacfa41eac6a89400b83f409b18b6b72a38` — CI #1162 / SMP #265 / NVMe #362 / HID Dual #21 |
| Demux/waiter exact-epoch | ✅ | `5fa048986ab4cfb8313530e9945e513633ea944f` — CI #1163 / SMP #266 / NVMe #363 / HID Dual #22 |
| Lifecycle pending checks exact-epoch | ✅ | `1c8b81b3cd021d12e46a964f54024f661bc1c2b3` — CI #1164 / SMP #267 / NVMe #364 / HID Dual #23 |
| Cleanup lógico de InputDevice/map/descriptors/report DMA | ⬜ | próximo microcorte |

O Event Ring permanece com **consumidor global único**. A mailbox de Transfer Events e o waiter generation-sensitive usam a identidade `slot_id + epoch + endpoint_id + TRB pointer`. Como o Transfer Event TRB do xHCI não carrega o `epoch` de software, a reutilização física de Slot ID continua proibida até a prova de drain/barrier de **HID-4d.5**.

A liberação lógica real de 4d.3b deve permanecer retry-safe e preservar a identidade antiga até o fim do cleanup. Ordem planejada:

```text
preservar device_id + generation antigos
→ hid_input_events_unbind_device(old_id, old_generation)
→ input_event_purge_device(old_id, old_generation)
→ hid_input_device_map_unbind(old_id, old_generation)
→ input_device_detach(old_id, old_generation)
→ liberar descriptor/report DMA somente após ownership CPU e epoch exato
→ limpar mailbox/result lógico exact-epoch
→ marcar logical_teardown_complete
```

Não pertencem ao 4d.3b: Drop Endpoint, liberação do HID Transfer Ring, Disable Slot, Device/Input Context ou EP0 Ring.

### Próximos microcortes HID-4d

1. **4d.3b — teardown HID lógico generation-safe:** concluir cleanup de report DMA, HID report state, InputDevice, field map, descriptor state e bindings, sempre validando `slot_id + epoch`.
2. **4d.3c — endpoint/rings:** Drop Endpoint/reconfiguração equivalente, remover referência do xHC, unshare/free do Transfer Ring e limpar endpoint state.
3. **4d.4 — Disable Slot + contexts:** Command Completion validado, remover DCBAA reference e liberar Device/Input Context + EP0 Ring.
4. **4d.5 — Slot ID reuse:** provar Slot X / epoch N → drain/barrier → teardown → Slot X / epoch N+1 sem estado stale.
5. **4d.6 — runtime proof:** detach/reconnect em múltiplos ciclos, keyboard/mouse independentes e ausência de leaks/stale completions observáveis.

### Invariantes HID permanentes

- Event Ring possui um único consumidor global.
- APIs generation-sensitive de pending/demux/lifecycle usam `slot_id + epoch` explícitos; wrappers slot-only ficam apenas em caminhos de compatibilidade devidamente cercados.
- Transfer completion roteada para mailbox é identificada por `slot_id + epoch + endpoint_id + TRB pointer`.
- Transfer Event TRB não contém software epoch; Slot ID não pode ser fisicamente reutilizado antes do drain/barrier de 4d.5.
- Slot ID reutilizado exige cleanup completo e epoch novo.
- `DETACH_PENDING` bloqueia novos TDs, mas não apaga um TD já outstanding.
- Stop Endpoint só marca `endpoint_stopped` depois de Command Completion e drain terminal.
- TD cancelado não pode virar evento de teclado/mouse.
- DMA temporário de enumeração deve ser liberado assim que não puder mais ser referenciado pelo controller.
- drivers não chamam PMM free diretamente; lifetime passa pela API DMA.
- `dma_release()` normal usa free arbitrário; rollback imediato de uma alocação recém-feita pode continuar LIFO.
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
