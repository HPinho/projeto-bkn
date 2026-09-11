# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-11 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`.

Uma feature só vira baseline integrada quando **CI principal + SMP + NVMe-only** passam no mesmo SHA. Teste textual não substitui build Sotlas nativo, ISO nem prova QEMU. Etapas que introduzem um proof de hardware específico podem exigir um workflow runtime adicional sem substituir esses três gates.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**  
**Fase 3 — Serviços e Userspace: ⬜ PLANEJADA**  
**Fase 4 — Experiência Baken: ⬜ PLANEJADA**

## Posição atual

O desenvolvimento está na **Fase 2 — Platform/Drivers**, **Trilha B — HID/input de produção**, dentro do **HID-4c.4 — enumeração simultânea real de múltiplos dispositivos xHCI**.

O **HID-4c.3 está encerrado e certificado**. **HID-4c.4a, HID-4c.4b e HID-4c.4c também estão certificados**. O candidato atual é **HID-4c.4d — dual-device runtime proof**, mantendo o teclado legado como primeiro HID e anexando um mouse como segundo Slot ID independente.

O Kernel Core permanece congelado. Drivers novos não podem relaxar invariantes de SMP, scheduler, memória, TLB, Ring3, FPU/SIMD ou teardown.

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.**

ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guarded stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID base, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32 base, PAT/framebuffer WC e zero UEFI pós-cutover.

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
| HID-4c Multi-slot xHCI | ⏳ | multi-device real no mesmo xHC |
| HID-4d Hot-plug/recovery | ⬜ | detach, cancel, recovery e reenumeração |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### Checkpoints HID já certificados

- HID-1 `1b3f94cc` — CI #1059 / SMP #162 / NVMe #259;
- HID-2 `a2e04a78` — CI #1063 / SMP #166 / NVMe #263;
- HID-3 `2775c12a` — CI #1066 / SMP #169 / NVMe #266;
- HID-4a `12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c` — CI #1072 / SMP #175 / NVMe #272;
- HID-4b `dbc5669aebd635b4e94c6e18e209f306cba5837f` — CI #1074 / SMP #177 / NVMe #274.

### HID-4c.1 — transport core

**✅ VALIDADO.**

Tabela bounded para 256 Slot IDs, `slot_id ↔ port_id`, `slot_type`, state+epoch, Device/Input Context e EP0 por slot, DCBAA por índice, Address Device por slot e wrappers legados preservados.

Checkpoint histórico `22ede5d7`: CI #1078 / SMP #181 / NVMe #278.

### HID-4c.2 — endpoint/report transport per-slot

**✅ PRESENTE E REVALIDADO.**

HID context por slot+epoch, DCI/ring/max packet/interval, Configure Endpoint, report DMA/ring/produtor/fallback Boot e completion por slot/DCI/TRB.

### HID-4c.3 — remoção dos singletons restantes

**✅ CONCLUÍDO E CERTIFICADO.**

| Componente | Checkpoint / prova |
|---|---|
| Device Descriptor per-slot | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 |
| Evaluate Context per-slot | `3688423e85a9c214755cc4c966c27910680663dc` — CI #1131 / SMP #234 / NVMe #331 |
| Configuration Descriptor per-slot | `72fa58228c24578ee50c39ca166d82ccc17a46a0` — CI #1132 / SMP #235 / NVMe #332 |
| HID Report Descriptor + InputDevice binding | `4ae0a5c6341dd6ea62d2ea05b62001382bfa467d` — CI #1135 / SMP #238 / NVMe #335 |
| HID report runtime per-slot | `93fe9d9639b366b9395b0b49f0f293bdf64de588` — CI #1136 / SMP #239 / NVMe #336 |
| SET_CONFIGURATION per-slot | `0ef4c670727a2d0b68324c4281972b2992fefb5c` — CI #1137 / SMP #240 / NVMe #337 |
| Slot coherence final | `6eec0dcc36a32c26108629e5ede9f0b929fef2e2` — CI #1138 / SMP #241 / NVMe #338 |

## HID-4c.4 — enumeração simultânea real

**⏳ ETAPA ATUAL.**

| Subetapa | Estado | Checkpoint / objetivo |
|---|---|---|
| HID-4c.4a Reset explícito por porta | ✅ | `8ef11b5e9298552d52eee3954ccd305e4421708d` — CI #1139 / SMP #242 / NVMe #339 |
| HID-4c.4b Inventário/seleção multi-port | ✅ | `ff98c978ea9f11f78217369a9ec856ffcdf7a45b` — CI #1140 / SMP #243 / NVMe #340 |
| HID-4c.4c Pipeline completo por porta | ✅ | `20b016973d12d4d669cf54ea79623a9116eb341f` — CI #1141 / SMP #244 / NVMe #341 |
| HID-4c.4d Dual-device runtime proof | ⏳ | candidato atual: keyboard primeiro + mouse segundo no QEMU |
| HID-4c.4e Interleaving/event demux | ⬜ | provar eventos independentes e alternados; expandir demux somente se necessário |

### Baseline certificada atual

```text
20b016973d12d4d669cf54ea79623a9116eb341f
feat(xhci): add per-port HID enumeration pipeline
```

- CI #1141 / `34591682640` ✅;
- SMP #244 / `34591682675` ✅;
- NVMe #341 / `34591682642` ✅.

Essa baseline certifica o pipeline por porta:

```text
Port Stage explícito
→ Enable Slot
→ Device/Input Context + EP0
→ Address Device
→ Device Descriptor 8 bytes
→ Evaluate Context
→ Device Descriptor completo
→ Configuration Descriptor
→ parser HID
→ HID endpoint context
→ Configure Endpoint
→ SET_CONFIGURATION
→ Report Descriptor/InputDevice map
→ HID report ring ready
```

O mesmo `slot_id` é propagado em toda a cadeia. Em falha pós-Enable Slot, o dispositivo é marcado `FAILED`, identidade HID é desmontada, Disable Slot precisa ser confirmado pelo xHC e o registro permanece em quarentena até existir teardown completo em HID-4d.

### Candidato atual — HID-4c.4d dual-device runtime

Novo estágio de plataforma:

```text
kernel::platform::hid_late_attach
```

Contrato:

```text
platform_hid_late_attach_second_mouse()
```

Regras do candidato:

- o caminho `post_cutover` do primeiro teclado permanece literalmente intacto;
- o late attach roda somente depois do proof/fundação e **não é fatal** se não houver segundo HID;
- o primeiro slot precisa continuar sendo Boot keyboard;
- `xhci_hid_enumerate_next_connected(0)` seleciona a próxima porta ainda sem Slot ID;
- o segundo Slot ID precisa ser diferente do primeiro e `xhci_slot_active_count() >= 2`;
- o segundo device precisa chegar a `xhci_hid_enumeration_is_ready_for(second_slot)`;
- o protocolo do segundo slot precisa ser `USB_HID_PROTOCOL_MOUSE`;
- a prova final chama `xhci_hid_report_poll_slot_once(second_slot)` e exige comprimento real de Boot mouse;
- somente depois dessa completion o kernel publica `BAKEN:USB_HID_DUAL_READY`.

A ausência/falha do segundo dispositivo não bloqueia o boot normal. A prova forte pertence ao workflow dedicado:

```text
Baken OS HID Dual-device Verification
```

Esse workflow executa QEMU com a ordem obrigatória:

```text
qemu-xhci
→ usb-kbd
→ usb-mouse
```

mantém `sendkey a` para o primeiro teclado, injeta `mouse_move 5 3` para o segundo device e só fica verde se o marker `BAKEN:USB_HID_DUAL_READY` aparecer no serial. Os três gates CI/SMP/NVMe continuam obrigatórios no mesmo SHA; o workflow dual é a prova adicional específica do HID-4c.4d.

### Compatibilidade

O caminho histórico permanece:

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

### Regras permanentes HID-4c

- não empilhar mudança funcional sobre candidato vermelho;
- API `_for(slot_id)` nunca usa identidade/configuração/resultados de outro slot;
- hardware/descriptors/eventos são input não confiável e falham fechado;
- Slot ID reutilizado exige cleanup + epoch novo;
- `sendkey a` do primeiro teclado permanece obrigatório;
- não relaxar timeout, marker ou proof para obter verde;
- staging multi-port nunca reinicializa o Command Ring após o bring-up inicial;
- `DUAL_READY` só pode ser publicado após completion Interrupt IN real do segundo slot;
- o late attach de HIDs adicionais não pode transformar presença de segundo device em requisito universal de boot.

### HID-4c.4e — próximo após 4c.4d verde

**⬜ PLANEJADO.** Provar interleaving keyboard/mouse, completions alternadas no mesmo Event Ring, atribuição correta por Slot ID/DCI/TRB e independência de `InputDevice + generation`. Só alterar demux se a prova real demonstrar necessidade.

### HID-4d — hot-plug/recovery

**⬜ PLANEJADO.** Detach físico, cancel de transfers, teardown de contexts/rings/descriptors, release generation-safe, slot reuse com epoch novo, reenumeração bounded e recovery de endpoint/controller.

---

## Trilha C — Storage de produção

**⬜ PLANEJADO.** Fundação presente: `AHCI/NVMe → BlockDevice → GPT/MBR → FAT32 base`.

Arquitetura alvo:

```text
AHCI / NVMe / futuros USB Mass Storage
            ↓
       BlockDevice
            ↓
        Block Cache
            ↓
   GPT / MBR / Volume Manager
            ↓
      Filesystem Probe
            ↓
            VFS
      ↙      ↓      ↘
   FAT32   exFAT   NTFS   ext*   ISO/UDF   BakenFS
            ↓
   handles / page cache / mmap / async I/O
```

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
| STORAGE-11 FS avançados/ZFS | ⬜ |

## Trilhas D–G

- Rede: ⬜ NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS.
- Áudio: ⬜ HDA, DMA/ring, codec/mixer e API userspace.
- GPU/composição: ⬜ framebuffer fallback, aceleração/compositor, zero lógica visual no compilador.
- Power/hot-plug ACPI avançado: ⬜ EC, GPE, GlobalLock, energia e extensões estritamente necessárias.

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API em Ring3, executáveis Sotlas, IPC, init/service manager e COW/demand paging.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, fontes/acessibilidade, shell, installer/OOBE, apps base, recovery e E2E.

---

# Regras permanentes

1. `main` recebe microcortes incrementais, sempre a partir do último checkpoint verde;
2. runtime real vale mais que teste textual;
3. Kernel Core permanece congelado;
4. firmware, descriptors e metadata on-disk são input não confiável;
5. hardware/firmware deve ser bounded e fail-closed;
6. unsupported = unresolved/fail-closed, nunca retorno inventado;
7. nunca obter verde removendo proof, marker, integridade ou ampliando timeout sem causa comprovada;
8. falhas, correções e certificações relevantes entram no roadmap/handoff;
9. filesystem nunca bypassa VFS/BlockDevice para acessar AHCI/NVMe diretamente;
10. escrita em FS externo só após testes de integridade, flush e recovery;
11. `HPinho/LangSotlas` permanece toolchain separada; migração é seletiva e não deve ser misturada a checkpoint crítico de driver.
