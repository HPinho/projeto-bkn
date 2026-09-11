# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`.

Uma feature só vira baseline integrada quando **CI principal + SMP + NVMe-only** passam no mesmo SHA. Teste textual não substitui build Sotlas nativo, ISO nem prova QEMU.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**  
**Fase 3 — Serviços e Userspace: ⬜ PLANEJADA**  
**Fase 4 — Experiência Baken: ⬜ PLANEJADA**

## Posição atual

O desenvolvimento está na **Fase 2 — Platform/Drivers**, na **Trilha B — HID/input de produção**, no fechamento do **HID-4c.3 — remoção dos singletons restantes do transporte xHCI**.

Em termos da Fase 2 inteira, o HID está em estágio avançado, mas **Platform/Drivers ainda não está perto de terminar como um todo**: ACPI/AML core está fechado; a fundação de storage existe; porém storage de produção/VFS, rede, áudio, GPU/composição, power/hot-plug avançado e HID-4d ainda permanecem futuros.

O Kernel Core permanece congelado. Desenvolvimento novo em drivers deve preservar seus invariantes de SMP, memória, Ring3, TLB, FPU/SIMD, scheduler e teardown.

A política atual é trabalhar diretamente em `main`, por microcortes verificáveis, sempre a partir do último checkpoint verde.

---

# Baseline de retomada HID-4c

Após regressões na antiga cadeia experimental HID-4c.3/4c.4, `main` foi restaurada ao último baseline totalmente verde:

```text
9558e5b3cb83064cc6a0b1548f03b3ed12c35a22
test(xhci): guard transfer results per slot
```

- CI #1127 ✅;
- SMP #230 ✅;
- NVMe #327 ✅.

A partir desse SHA, HID-4c passou a ser reconstruído em incrementos pequenos, sem reaplicar automaticamente os commits experimentais removidos.

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.**

Inclui ExitBootServices, CR3 próprio, PMM, VMM, DMA, W^X, guarded stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID base, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32 base, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.**

Inclui scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP→AP e teardown seguro.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 fechados; checkpoint final `7803447a`.

## Trilha B — HID adicional / input de produção

| Etapa | Estado | Objetivo |
|---|---|---|
| HID-0 Boot HID xHCI | ✅ | keyboard/mouse Boot + Interrupt IN real |
| HID-1 Report Descriptor | ✅ | fetch real + parser bounded transport-agnostic |
| HID-2 Field map / decoder | ✅ | Report ID, Usage, bit offsets, flags e valores |
| HID-3 Input event model | ✅ | fila e eventos normalizados keyboard/mouse |
| HID-4a Identity/lifecycle | ✅ | `device_id + generation`, lifecycle e fila segura |
| HID-4b Per-device HID map | ✅ | field map/decoder por `device_id + generation` |
| HID-4c Multi-slot xHCI | ⏳ | transporte completo por slot/interface e multi-device real |
| HID-4d Hot-plug/recovery | ⬜ | detach físico, cancel/recovery e reenumeração |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

`1b3f94cc`: CI #1059 ✅; SMP #162 ✅; NVMe #259 ✅.

### HID-2 — certificado

`a2e04a78`: CI #1063 ✅; SMP #166 ✅; NVMe #263 ✅.

### HID-3 — certificado

Runtime `51631f23`; head promovido `2775c12a`: CI #1066 ✅; SMP #169 ✅; NVMe #266 ✅.

Markers `BAKEN:USB_HID_EVENT_MODEL_READY` e `BAKEN:USB_HID_EVENT_READY` permanecem obrigatórios.

### HID-4a — certificado

```text
12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c
```

CI #1072 ✅; SMP #175 ✅; NVMe #272 ✅.

### HID-4b — certificado

```text
dbc5669aebd635b4e94c6e18e209f306cba5837f
feat(hid): isolate input maps per device
```

CI #1074 ✅; SMP #177 ✅; NVMe #274 ✅.

HID-4b entrega mapa HID persistente por `device_id + generation`, parser HID-1 stateless, tradução ligada ao mapa correto e teardown generation-safe.

---

## HID-4c — Multi-slot / multi-device xHCI

**⏳ EM DESENVOLVIMENTO DIRETO NA `main`.**

Objetivo: permitir que porta, Slot ID, Device/Input Context, EP0, descriptor state, HID endpoint/ring, configuration state, report buffer, identidade e eventos sejam associados ao device/interface correto, sem depender de singletons internos.

### HID-4c.1 — multi-slot transport core

**✅ VALIDADO.**

- `xhci_device_table.sotlas` fixed-capacity de 256 Slot IDs;
- associação `slot_id ↔ port_id`, `slot_type`, estado e `epoch`;
- Device Context, Input Context e EP0 ring por Slot ID;
- DCBAA publicado no índice correto;
- Address Device e USB address por slot+epoch;
- wrappers legados preservados.

Checkpoint histórico `22ede5d7`: CI #1078 ✅; SMP #181 ✅; NVMe #278 ✅.

A baseline `9558e5b` inclui também EP0/transfer result por slot e foi revalidada em CI #1127 + SMP #230 + NVMe #327.

### HID-4c.2 — HID Interrupt IN por slot/interface

**✅ BASE ESTRUTURAL PRESENTE E REVALIDADA.**

- `XHCI_HID_CONTEXTS[slot_id]` por epoch;
- DCI, endpoint address, max packet, interval e ring Interrupt IN por slot;
- Configure Endpoint per-slot;
- `XHCI_HID_REPORT_STATES[slot_id]` por epoch;
- producer cycle, enqueue index, DMA report buffer e fallback Boot por slot;
- transfer completion identificado por slot/DCI/TRB;
- wrappers do primeiro device continuam válidos.

### HID-4c.3 — remoção dos singletons restantes

**⏳ IMPLEMENTAÇÃO COMPLETA; CERTIFICAÇÃO FINAL EM ANDAMENTO.**

| Subetapa | Estado | Checkpoint / prova |
|---|---|---|
| Device Descriptor per-slot | ✅ | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 |
| Evaluate Context per-slot | ✅ | `3688423e85a9c214755cc4c966c27910680663dc` — CI #1131 / SMP #234 / NVMe #331 |
| Configuration Descriptor per-slot | ✅ | `72fa58228c24578ee50c39ca166d82ccc17a46a0` — CI #1132 / SMP #235 / NVMe #332 |
| HID Report Descriptor + InputDevice binding per-slot | ✅ | `4ae0a5c6341dd6ea62d2ea05b62001382bfa467d` — CI #1135 / SMP #238 / NVMe #335 |
| HID report runtime ligado ao mesmo slot | ✅ | `93fe9d9639b366b9395b0b49f0f293bdf64de588` — CI #1136 / SMP #239 / NVMe #336 |
| SET_CONFIGURATION per-slot | ✅ | `0ef4c670727a2d0b68324c4281972b2992fefb5c` — CI #1137 / SMP #240 / NVMe #337 |
| Report gate final usando SET_CONFIGURATION per-slot | ⏳ | candidato deste commit: `prepare_for_slot` usa readiness + configuration value do mesmo slot; aguarda triplo verde |

### Última baseline certificada

```text
0ef4c670727a2d0b68324c4281972b2992fefb5c
feat(xhci): isolate set configuration per slot
```

- CI #1137 / `34553335969` ✅ — suíte completa, grafo Sotlas, build nativo, ISO e QEMU;
- SMP #240 / `34553335968` ✅ — contracts, build e prova SMP;
- NVMe #337 / `34553335991` ✅ — contracts, build, fixture e QEMU NVMe-only.

### Candidato final HID-4c.3

O último microcorte remove a consulta global de `SET_CONFIGURATION` de `xhci_hid_report_prepare_for_slot(slot_id)`.

O caminho agora exige simultaneamente:

```text
xhci_hid_context_is_ready_for(slot_id)
xhci_configure_endpoint_is_ready_for(slot_id)
xhci_set_configuration_is_ready_for(slot_id)
xhci_set_configuration_value_for(slot_id) == xhci_configuration_value_for(slot_id)
xhci_hid_descriptor_input_map_is_ready_for(slot_id)
identidade InputDevice correspondente ao mesmo slot
```

O wrapper `xhci_hid_report_prepare()` somente seleciona o slot ativo e delega. A lógica interna multi-slot não consulta mais readiness global de SET_CONFIGURATION.

Se este candidato passar CI + SMP + NVMe no mesmo SHA, **HID-4c.3 estará fechado** e o próximo bloco passa a ser HID-4c.4.

### Regras de segurança HID-4c.3

- não empilhar mudança funcional sobre candidato vermelho;
- API `_for(slot_id)` nunca pode decidir identidade/configuração/resultados usando outro slot;
- toda transferência consome completion/result do mesmo slot;
- `epoch` invalida estado stale quando Slot ID é reutilizado;
- o proof legado `sendkey a` continua obrigatório;
- não relaxar timeout, marker ou teste para obter verde.

### HID-4c.4 — enumeração simultânea real

**⬜ PRÓXIMO BLOCO APÓ O TRIPLO VERDE DO FECHAMENTO HID-4c.3.**

Objetivos:

1. enumerar múltiplas portas conectadas elegíveis;
2. Enable Slot + Context + Address independentes por porta;
3. configurar pelo menos keyboard + mouse simultâneos no mesmo xHC;
4. cada device com Slot ID, epoch, endpoint/DCI, ring, descriptor state, `device_id + generation` e mapa próprios;
5. event/transfer demux nunca aceitar evento de outro slot;
6. preservar o teclado como primeiro device no QEMU para manter o proof histórico;
7. adicionar prova real e independente do mouse no segundo slot.

Não reintroduzir automaticamente os antigos commits experimentais HID-4c.4; eles servem somente como referência de design.

### HID-4d — hot-plug/recovery

**⬜ PLANEJADO.** Detach físico, cancel de transfers, cleanup generation-safe, slot reuse com epoch novo, reenumeração bounded e recuperação de endpoint/controller.

---

## Trilha C — Storage de produção

**⬜ PLANEJADO.** A fundação atual (`AHCI/NVMe → BlockDevice → GPT/MBR → FAT32`) será evoluída por uma camada VFS comum.

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
            ↓
        syscalls / userspace
```

| Etapa | Estado | Objetivo |
|---|---|---|
| STORAGE-0 Block cache | ⬜ | cache bounded, dirty/flush/barriers |
| STORAGE-1 Volume manager | ⬜ | GPT/MBR robusto, lifecycle e media generation |
| STORAGE-2 VFS core | ⬜ | mounts, vnode/inode, paths, handles e hooks de permissão |
| STORAGE-3 FAT32 produção | ⬜ | read/write robusto, LFN, diretórios, fsync |
| STORAGE-4 exFAT | ⬜ | read-only primeiro; escrita depois |
| STORAGE-5 NTFS | ⬜ | import/read-only seguro primeiro |
| STORAGE-6 ext2/ext3/ext4 | ⬜ | leitura com feature flags fail-closed |
| STORAGE-7 ISO9660/UDF | ⬜ | read-only |
| STORAGE-8 BakenFS v1 | ⬜ | filesystem nativo do Baken |
| STORAGE-9 Page/file cache + mmap | ⬜ | integração com VMM/processos |
| STORAGE-10 Async I/O + recovery | ⬜ | requests, cancel, flush ordering, recovery |
| STORAGE-11 Filesystems avançados | ⬜ | ZFS/importers somente depois do VFS/BakenFS maduros |

BakenFS será o filesystem nativo/preferencial, sem eliminar interoperabilidade: FAT32 read/write completo; exFAT prioritário para mídia removível; NTFS/ext inicialmente leitura segura; ISO/UDF read-only; ZFS tardio.

---

## Trilha D — Rede

**⬜ PLANEJADO.** NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS.

## Trilha E — Áudio

**⬜ PLANEJADO.** HDA, DMA/ring buffer, codec/mixer e API userspace.

## Trilha F — GPU/composição

**⬜ PLANEJADO.** Framebuffer fallback, aceleração/compositor depois do modelo de memória seguro; zero lógica visual no compilador.

## Trilha G — Power / hot-plug ACPI avançado

**⬜ PLANEJADO.** EC, GPE, GlobalLock, energia e extensões firmware-specific estritamente necessárias.

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API em Ring3, executáveis Sotlas, IPC, init/service manager e COW/demand paging.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, fontes/acessibilidade, shell, installer/OOBE, apps base, recovery e E2E.

---

# Regras permanentes

1. `main` recebe desenvolvimento incremental direto, mas cada novo subestágio parte do último checkpoint verde conhecido;
2. runtime real vale mais que teste textual;
3. Kernel Core permanece congelado;
4. firmware, descriptors e metadata on-disk são input não confiável;
5. toda camada hardware/firmware deve ser bounded e fail-closed;
6. unsupported = unresolved/fail-closed, nunca retorno inventado;
7. nunca obter verde removendo proof, marker, integridade ou aumentando timeout sem causa comprovada;
8. toda falha, correção e certificação relevante deve ser refletida neste roadmap;
9. `KERNEL_HANDOFF.md` acompanha mudanças de baseline/fase e mantém o estado operacional;
10. drivers de filesystem nunca bypassam VFS/BlockDevice para acessar AHCI/NVMe diretamente;
11. escrita em filesystem externo só é habilitada após testes explícitos de integridade, flush e recovery;
12. `HPinho/LangSotlas` é toolchain separada; migração deve ser seletiva e não misturada a checkpoint crítico de driver.
