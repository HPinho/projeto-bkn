# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-11 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`.

Uma feature só vira baseline integrada quando **CI principal + SMP + NVMe-only** passam no mesmo SHA. Teste textual não substitui build Sotlas nativo, ISO nem prova QEMU.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**  
**Fase 3 — Serviços e Userspace: ⬜ PLANEJADA**  
**Fase 4 — Experiência Baken: ⬜ PLANEJADA**

## Posição atual

O desenvolvimento está na **Fase 2 — Platform/Drivers**, **Trilha B — HID/input de produção**, dentro do **HID-4c.4 — enumeração simultânea real de múltiplos dispositivos xHCI**.

O **HID-4c.3 está encerrado e certificado**. O **HID-4c.4a — reset explícito por porta** também está certificado. O candidato atual é **HID-4c.4b — inventário/seleção multi-port**, preparando a transição de `first_connected` para iteração bounded de portas reais.

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

### HID-1 — certificado

`1b3f94cc`: CI #1059 ✅; SMP #162 ✅; NVMe #259 ✅.

### HID-2 — certificado

`a2e04a78`: CI #1063 ✅; SMP #166 ✅; NVMe #263 ✅.

### HID-3 — certificado

Runtime `51631f23`; head `2775c12a`: CI #1066 ✅; SMP #169 ✅; NVMe #266 ✅.

### HID-4a — certificado

`12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c`: CI #1072 ✅; SMP #175 ✅; NVMe #272 ✅.

### HID-4b — certificado

`dbc5669aebd635b4e94c6e18e209f306cba5837f`: CI #1074 ✅; SMP #177 ✅; NVMe #274 ✅.

---

## HID-4c — Multi-slot / multi-device xHCI

**⏳ EM DESENVOLVIMENTO DIRETO NA `main`.**

Objetivo: múltiplos dispositivos HID simultâneos, cada um com porta, Slot ID, epoch, contexts, EP0, descriptors, HID endpoint/DCI/ring, configuração, identidade e eventos próprios.

### HID-4c.1 — transport core

**✅ VALIDADO.**

- `xhci_device_table` bounded para 256 Slot IDs;
- `slot_id ↔ port_id`, `slot_type`, estado e `epoch`;
- Device/Input Context e EP0 ring por slot;
- DCBAA no índice correto;
- Address Device e USB address por slot;
- wrappers legados preservados.

Checkpoint histórico `22ede5d7`: CI #1078 ✅; SMP #181 ✅; NVMe #278 ✅.

A retomada segura posterior partiu de `9558e5b3cb83064cc6a0b1548f03b3ed12c35a22`, triplo verde em CI #1127 / SMP #230 / NVMe #327.

### HID-4c.2 — HID Interrupt IN por slot/interface

**✅ ESTRUTURA PRESENTE E REVALIDADA.**

- HID context por slot+epoch;
- DCI/ring/max packet/interval por slot;
- Configure Endpoint per-slot;
- report DMA/ring/produtor/fallback Boot por slot;
- completion identificada por slot/DCI/TRB.

### HID-4c.3 — remoção dos singletons restantes

**✅ CONCLUÍDO E CERTIFICADO.**

| Subetapa | Checkpoint / prova |
|---|---|
| Device Descriptor per-slot | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 |
| Evaluate Context per-slot | `3688423e85a9c214755cc4c966c27910680663dc` — CI #1131 / SMP #234 / NVMe #331 |
| Configuration Descriptor per-slot | `72fa58228c24578ee50c39ca166d82ccc17a46a0` — CI #1132 / SMP #235 / NVMe #332 |
| HID Report Descriptor + InputDevice binding | `4ae0a5c6341dd6ea62d2ea05b62001382bfa467d` — CI #1135 / SMP #238 / NVMe #335 |
| HID report runtime per-slot | `93fe9d9639b366b9395b0b49f0f293bdf64de588` — CI #1136 / SMP #239 / NVMe #336 |
| SET_CONFIGURATION per-slot | `0ef4c670727a2d0b68324c4281972b2992fefb5c` — CI #1137 / SMP #240 / NVMe #337 |
| Slot coherence final | `6eec0dcc36a32c26108629e5ede9f0b929fef2e2` — CI #1138 / SMP #241 / NVMe #338 |

### HID-4c.4 — enumeração simultânea real

**⏳ ETAPA ATUAL.**

| Subetapa | Estado | Checkpoint / objetivo |
|---|---|---|
| HID-4c.4a Reset explícito por porta | ✅ | `8ef11b5e9298552d52eee3954ccd305e4421708d` — CI #1139 / SMP #242 / NVMe #339 |
| HID-4c.4b Inventário/seleção multi-port | ⏳ | candidato atual: iteração bounded + staging explícito por `port_id` |
| HID-4c.4c Pipeline completo por porta | ⬜ | Reset → Enable Slot → Context → Address → descriptors → endpoint → SET_CONFIGURATION |
| HID-4c.4d Dual-device runtime proof | ⬜ | keyboard primeiro + mouse segundo no QEMU |
| HID-4c.4e Interleaving/event demux | ⬜ | provar eventos independentes; expandir demux somente se necessário |

### Baseline certificada atual

```text
8ef11b5e9298552d52eee3954ccd305e4421708d
feat(xhci): start HID-4c.4 per-port reset
```

- CI #1139 / `34557045054` ✅;
- SMP #242 / `34557045108` ✅;
- NVMe #339 / `34557045133` ✅.

### Candidato atual — HID-4c.4b

O inventário de portas já era bounded e read-only, mas expunha apenas `xhci_first_connected_port()`. O candidato adiciona:

```text
xhci_port_next_connected(after_port_id)
```

para percorrer snapshots conectados sem tocar hardware. A iteração usa somente o inventário atual, retorna `0` ao final e nunca executa reset, Enable Slot ou doorbell.

O staging também passa a aceitar:

```text
xhci_port_stage_prepare_for(port_id)
```

com estas regras:

- exige controller/No-op já prontos;
- exige `xhci_command_is_ready()`;
- **não chama `xhci_command_prepare_after_noop()`**, evitando rebobinar Command Ring/Event Consumer depois do primeiro device;
- revalida Supported Protocol + PORTSC;
- exige snapshot válido e conectado;
- aceita somente USB2/USB3 suportado;
- chama `xhci_port_reset_for(port_id)` e confirma que o reset concluído pertence à mesma porta/protocolo;
- `XHCI_PORT_STAGE_*` permanece estado transitório da seleção atual, não identidade multi-device;
- `xhci_port_stage_prepare_first()` continua sendo o wrapper legado e preserva a ordem histórica do primeiro teclado.

Se este corte ficar triplo verde, o próximo checkpoint é **HID-4c.4c**, que usará a porta explicitamente preparada para executar a cadeia real por dispositivo: Enable Slot → Context → Address → descriptors → HID endpoint → SET_CONFIGURATION.

### Regras de segurança HID-4c

- não empilhar mudança funcional sobre candidato vermelho;
- API `_for(slot_id)` nunca decide identidade/configuração/resultados usando outro slot;
- hardware/descriptors/eventos são input não confiável e falham fechado;
- Slot ID reutilizado exige epoch novo;
- o proof legado `sendkey a` permanece obrigatório;
- não relaxar timeout, marker ou proof para obter verde;
- não reaplicar em bloco a antiga cadeia experimental HID-4c.4;
- staging multi-port nunca reinicializa o Command Ring após o bring-up inicial.

### HID-4d — hot-plug/recovery

**⬜ PLANEJADO.** Detach físico, cancel de transfers, cleanup generation-safe, slot reuse com epoch novo, reenumeração bounded e recovery de endpoint/controller.

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

1. `main` recebe microcortes incrementais, cada um partindo do último checkpoint verde;
2. runtime real vale mais que teste textual;
3. Kernel Core permanece congelado;
4. firmware, descriptors e metadata on-disk são input não confiável;
5. hardware/firmware deve ser bounded e fail-closed;
6. unsupported = unresolved/fail-closed, nunca retorno inventado;
7. nunca obter verde removendo proof, marker, integridade ou ampliando timeout sem causa comprovada;
8. falhas, correções e certificações relevantes devem entrar neste roadmap;
9. `KERNEL_HANDOFF.md` acompanha mudanças de baseline/fase;
10. filesystem nunca bypassa VFS/BlockDevice para acessar AHCI/NVMe diretamente;
11. escrita em FS externo só após testes de integridade, flush e recovery;
12. `HPinho/LangSotlas` permanece toolchain separada; migração é seletiva e não deve ser misturada a checkpoint crítico de driver.
