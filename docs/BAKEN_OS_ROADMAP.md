# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

### Posição atual

O desenvolvimento está na **Fase 2 — Platform/Drivers**, Trilha B de input, dentro do **HID-4c Multi-slot xHCI**. O Kernel Core permanece congelado; o trabalho corrente remove os últimos estados singleton do transporte USB/HID antes de hot-plug, storage de produção, rede, áudio e GPU/composição.

A política atual de desenvolvimento é trabalhar diretamente em `main`, em incrementos pequenos e verificáveis. Cada incremento deve preservar o caminho single-device já certificado e usar somente APIs confirmadas no baseline. CI principal, SMP e NVMe continuam sendo os três gates oficiais de runtime.

## Baseline verde de retomada e checkpoint atual

Após uma cadeia experimental posterior falhar nos workflows, `main` foi restaurada ao último baseline conhecido totalmente verde:

```text
9558e5b3cb83064cc6a0b1548f03b3ed12c35a22
test(xhci): guard transfer results per slot
```

- CI #1127 / `34541581807` ✅;
- SMP #230 / `34541581869` ✅ — 3/3;
- NVMe #327 / `34541581813` ✅.

O desenvolvimento foi retomado desse SHA sem reaproveitar automaticamente a cadeia experimental. O primeiro incremento novo também foi certificado nos três gates:

```text
d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3
feat(xhci): isolate device descriptors per slot
```

- CI #1128 / `34544233277` ✅;
- SMP #231 / `34544233290` ✅ — 3/3;
- NVMe #328 / `34544233455` ✅.

Esse checkpoint torna o **Device Descriptor per-slot + epoch** e preserva todos os wrappers do bring-up single-device. Configuration Descriptor, HID descriptor/binding e demais estados transport-specific ainda não são declarados concluídos até seus próprios incrementos passarem pelos mesmos gates.

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.** ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guard stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.** Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP->AP e teardown seguro.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 fechados; checkpoint AML final `7803447a`.

## Trilha B — HID adicional / input de produção

| Etapa | Estado | Objetivo |
|---|---|---|
| HID-0 Boot HID xHCI | ✅ | keyboard/mouse Boot + Interrupt IN real |
| HID-1 Report Descriptor | ✅ | fetch real + parser bounded transport-agnostic |
| HID-2 Field map / decoder | ✅ | Report ID, Usage, bit offsets, flags e valores |
| HID-3 Input event model | ✅ | fila e eventos normalizados keyboard/mouse |
| HID-4a Identity/lifecycle core | ✅ | device_id+generation, SMP-safe queue, bind/unbind |
| HID-4b Per-device HID map | ✅ | snapshots de field map/decoder por device+generation |
| HID-4c Multi-slot xHCI | ⏳ | slot/context/rings/buffers por device/interface |
| HID-4d Hot-plug/recovery | ⬜ | detach físico, cancel/recovery e reenumeração |
| I2C-HID | ⬜ | depois de transporte I2C/ACPI seguro |

### HID-1 — certificado

`1b3f94cc`: CI #1059 / `34497000191` ✅; SMP #162 / `34497000136` ✅ 3/3; NVMe #259 / `34497000185` ✅.

### HID-2 — certificado

`a2e04a78`: CI #1063 / `34501892035` ✅; SMP #166 / `34501892066` ✅ 3/3; NVMe #263 / `34501892022` ✅.

### HID-3 — certificado

Runtime `51631f23`; head promovido `2775c12a`. CI #1066 / `34509266662` ✅; SMP #169 / `34509266645` ✅ 3/3; NVMe #266 / `34509266646` ✅. Markers `BAKEN:USB_HID_EVENT_MODEL_READY` e `BAKEN:USB_HID_EVENT_READY` permanecem obrigatórios no smoke.

### HID-4a — certificado

Runtime original `8f34ae13`; correção de parser Sotlas `a4762cf6`; head final certificado/promovido:

```text
12c308b3d0d4a6bb3b17397ca74bfe4bcc95327c
```

- CI #1072 / `34516628427` ✅;
- SMP #175 / `34516628437` ✅ 3/3;
- NVMe #272 / `34516628445` ✅.

HID-4a entrega registro de 16 devices, `device_id + generation`, lifecycle explícito, fila/eventos SMP-safe, purge por geração, estado HID por device x Report ID, bind/unbind generation-safe e marker `BAKEN:USB_HID_DEVICE_READY`.

Histórico: CI #1069 / SMP #172 / NVMe #269 falharam antes do QEMU pela sintaxe `return` dentro de `if`-expressão em `xhci_hid_descriptor.sotlas`; `a4762cf6` corrigiu somente essa forma de controle de fluxo. A correção passou SMP #173 3/3 e depois o head final passou os três gates oficiais.

### HID-4b — certificado

Branch de validação: `hid4b-validation`, criada diretamente da baseline certificada `12c308b3`.

Escopo candidato preservado e agora certificado:
- `hid_input_device_map.sotlas` fixed-capacity, sem heap e transport-agnostic;
- snapshot HID-2 independente por `device_id + generation`;
- fields, Report IDs e expected bytes separados por device;
- parser HID-1 continua stateless;
- mapa HID-2 legado é apenas scratch serializado de construção, invalidado após copiar o snapshot;
- runtime de Interrupt IN usa exclusivamente APIs per-device;
- tradutor HID usa mapa e estado correspondentes à mesma generation;
- self-test mantém teclado e mouse simultaneamente e prova que um report não valida contra o mapa do outro;
- teardown remove mapa somente depois de invalidar identidade, purgar fila e limpar estado de eventos;
- marker novo `BAKEN:USB_HID_DEVICE_MAP_READY`; falha `BAKEN:USB_HID_DEVICE_MAP_FAILED`;
- smoke/SMP/NVMe passam a bloquear ausência ou falha do mapa específico.

**Limite certificado:** xHCI ainda era single-slot/single-endpoint nesta fatia. HID-4b não declarou múltiplos dispositivos USB simultâneos no transporte; ele removeu o bloqueio semântico do mapa para que HID-4c pudesse fazê-lo corretamente.

Head certificado/promovido:

```text
dbc5669aebd635b4e94c6e18e209f306cba5837f
feat(hid): isolate input maps per device
```

- CI #1074 / `34520772415` ✅;
- SMP #177 / `34520772429` ✅ 3/3;
- NVMe #274 / `34520772422` ✅.

HID-4b foi promovido para `main` por fast-forward sem criar merge commit diferente do SHA testado.

### HID-4c — candidato atual

Histórico: a implementação começou em branches de validação e depois passou a ser desenvolvida diretamente em `main`. A cadeia experimental posterior a `9558e5b` foi retirada da `main` após regressões nos workflows; o desenvolvimento atual parte do baseline verde `9558e5b` e avança por subestágios pequenos, cada um certificado antes do próximo.

Objetivo completo do HID-4c: retirar os singletons restantes do transporte xHCI e permitir slot/context/address/HID rings/buffers por device/interface, culminando em enumeração de múltiplos HID simultâneos.

#### HID-4c.1 — multi-slot transport core — validado

Implementado inicialmente até `bd6f1708`; head documental/revalidado da subfatia: `22ede5d7`.

- novo `xhci_device_table.sotlas` fixed-capacity de 256 Slot IDs, sem heap;
- associação explícita `slot_id <-> port_id` e `slot_type`;
- `epoch` por Slot ID para impedir reutilização stale;
- lifecycle de transporte `ENABLED`, `CONTEXT_READY`, `ADDRESSED`, `HID_READY` e `FAILED`;
- `xhci_slot_enable_port(port_id, slot_type)` registra Enable Slot sem sobrescrever outros devices;
- `xhci_slot_enable_first_port()` permanece como wrapper de compatibilidade para o bring-up certificado;
- Device Context, Input Context e EP0 Transfer Ring armazenados por Slot ID;
- arena DMA/context size/EP0 max packet separados por slot;
- DCBAA publicado no índice do Slot ID correspondente;
- `xhci_address_slot(slot_id)` executa Address Device usando o Input Context daquele slot;
- endereço USB armazenado por Slot ID + epoch;
- wrappers legados de context/address continuam apontando para o slot ativo para evitar regressão do boot atual;
- grafo canônico importa `xhci_device_table`;
- guardrails de slot/context/address atualizados para exigir as novas APIs e impedir retorno aos singletons antigos.

Validação final histórica da subfatia no head `22ede5d7`:
- CI #1078 / `34530989194` ✅;
- SMP #181 / `34530989212` ✅ — 3/3;
- NVMe #278 / `34530989192` ✅.

O baseline de retomada `9558e5b` também inclui a evolução per-slot de EP0/transfer results e passou novamente nos três gates oficiais (CI #1127, SMP #230 e NVMe #327).

#### HID-4c.2 — HID Interrupt IN por slot/interface — implementado no baseline de retomada

Implementação preservada em `9558e5b`:
- `xhci_hid_context` possui tabela `XHCI_HID_CONTEXTS` por Slot ID + epoch;
- DCI, endpoint address, max packet, interval e Transfer Ring Interrupt IN ficam separados por slot;
- `xhci_hid_context_prepare_for_slot(slot_id, endpoint_address, max_packet, usb_interval)` usa o Input Context correspondente;
- `xhci_configure_endpoint` armazena READY/epoch/DCI por slot e oferece `xhci_configure_hid_endpoint_for_slot(slot_id)`;
- confirmação de Endpoint State=Running é lida do Device Context do mesmo Slot ID;
- `xhci_hid_report` possui estado por slot+epoch;
- producer cycle, enqueue index, DMA report buffer e last length ficam ligados ao slot correspondente;
- ring base e Link TRB são resolvidos pelo contexto HID do mesmo slot;
- polling usa explicitamente slot/DCI e resultados de transferência do mesmo slot;
- wrappers legados continuam preservando o boot single-device certificado.

Histórico de desenvolvimento desta subfatia permanece abaixo para rastreabilidade:
- `e2486b2b` — `feat(xhci): isolate HID endpoint contexts per slot`;
- `d3fcaf8e` — `feat(xhci): configure HID endpoints per slot`;
- `0dd3ea5a` — `feat(xhci): isolate HID report rings per slot`;
- `f51f5cb0` — guardrail agregado do contrato HID-4c;
- `f51f5cb0`: CI #1085 / `34533310356` ❌ na suíte; SMP #188 / `34533310323` ✅; NVMe #285 / `34533310320` ✅;
- `bffcd2d6`: CI #1087 / `34533512920` ❌ na suíte; SMP #190 / `34533512907` ✅ — 3/3; NVMe #287 / `34533512927` ✅;
- `b32cad41` e `18b6e308` corrigiram guardrails textuais obsoletos sem relaxar os contratos.

#### HID-4c.3 — remoção dos singletons restantes — EM DESENVOLVIMENTO

Objetivo: migrar Device Descriptor, Evaluate Context, Configuration Descriptor, HID descriptor e binding transport-specific da interface para estado por Slot ID/epoch, preservando HID-1/HID-2/HID-3/HID-4a/HID-4b como camadas transport-agnostic.

Subetapas atuais:

| Subetapa | Estado | Checkpoint |
|---|---|---|
| Device Descriptor per-slot | ✅ | `d85d9f2424818f4cf9e2fc61967ac7cd9cace2a3` — CI #1128 / SMP #231 / NVMe #328 verdes |
| Evaluate Context per-slot | ⬜ | próximo incremento; usar somente APIs `*_for(slot_id)` já existentes |
| Configuration Descriptor per-slot | ⬜ | depois do Evaluate Context verde |
| HID descriptor/interface binding per-slot | ⬜ | depois de Configuration verde |
| SET_CONFIGURATION/report binding final | ⬜ | fechar coerência slot/interface antes de multi-device runtime |

**Regra do HID-4c.3:** nenhum subestágio é empilhado sobre outro candidato ainda vermelho. O wrapper single-device deve continuar produzindo o mesmo runtime já certificado.

#### HID-4c.4 — fechamento

**⬜ PLANEJADO.** Enumerar múltiplas portas/devices conectados no runtime normal e provar pelo menos keyboard + mouse simultâneos no mesmo xHC, cada um com Slot ID, contexto, endpoint/ring, mapa HID e geração próprios.

O QEMU de fechamento deve preservar o teclado como primeiro device para manter o proof legado e adicionar um mouse físico em segundo slot, com eventos e identidade independentes.

**Critério de promoção HID-4c:** CI principal + SMP 3/3 + NVMe-only verdes no mesmo SHA final, com os contratos multi-slot/multi-device e prova runtime preservando toda a baseline anterior. Só então iniciar HID-4d.

## Trilha C — Storage de produção

**⬜ PLANEJADO.** Esta trilha transforma a fundação já existente (`AHCI/NVMe -> BlockDevice -> GPT/MBR -> FAT32`) em uma pilha de storage/filesystem de produção.

### Arquitetura alvo

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

O **VFS** será a fronteira comum. Drivers de filesystem não acessam AHCI/NVMe diretamente; recebem um volume/BlockDevice e implementam o mesmo contrato de inode/node, lookup, open, read, write, directory iteration, metadata, flush e mount/unmount. Assim o restante do kernel não precisa saber se um arquivo veio de FAT32, NTFS ou BakenFS.

### Sequência proposta

| Etapa | Estado | Objetivo |
|---|---|---|
| STORAGE-0 Block cache | ⬜ | cache bounded, dirty state, flush/barriers e coerência por BlockDevice |
| STORAGE-1 Volume manager | ⬜ | GPT/MBR robusto, lifecycle de volumes, mount identity e media generation |
| STORAGE-2 VFS core | ⬜ | mount table, vnode/inode abstraction, path resolution, handles e permissions hooks |
| STORAGE-3 FAT32 produção | ⬜ | transformar parser atual em filesystem robusto read/write, LFN, diretórios, alocação e fsync |
| STORAGE-4 exFAT | ⬜ | interoperabilidade moderna com pendrives/cartões, inicialmente read-only e depois write |
| STORAGE-5 NTFS | ⬜ | import/read-only seguro: boot sector, MFT, attributes, directories e data runs |
| STORAGE-6 ext2/ext3/ext4 | ⬜ | leitura compatível; ext4 inicialmente sem escrita e com feature flags fail-closed |
| STORAGE-7 ISO9660/UDF | ⬜ | mídia óptica/imagens de instalação em modo read-only |
| STORAGE-8 BakenFS v1 | ⬜ | filesystem nativo do Baken, integrado ao VFS e usado como formato preferencial do sistema |
| STORAGE-9 Page/file cache + mmap | ⬜ | page cache coerente, read-ahead, mmap e integração com VMM/processos |
| STORAGE-10 Async I/O + recovery | ⬜ | requests assíncronos, cancel, flush ordering, mount recovery e hot-unplug seguro |
| STORAGE-11 Filesystems avançados | ⬜ | ZFS/importers adicionais somente depois do VFS/BakenFS maduros |

### Política de compatibilidade de filesystems

- **FAT32:** read/write completo e altamente testado; obrigatório para ESP/boot/intercâmbio.
- **exFAT:** prioridade alta para mídia removível moderna; read-only primeiro, write depois de testes de corrupção/recovery.
- **NTFS:** prioridade alta para leitura de discos Windows. Escrita fica para uma etapa posterior porque a superfície de corrupção é muito maior.
- **ext2/ext3/ext4:** prioridade alta para leitura de volumes Linux. O driver deve recusar features incompatíveis em vez de interpretar estruturas que não entende.
- **ISO9660/UDF:** read-only é suficiente para imagens/mídia e instalação.
- **ZFS:** opcional e tardio; começar, se necessário, como import/read-only com subset explícito de feature flags. Não copiar implementação de terceiros para preservar o objetivo de código próprio.
- **APFS e outros formatos proprietários/complexos:** somente depois de storage/VFS maduros e apenas com contrato fail-closed.

### BakenFS — filesystem nativo

O Baken pode e deve ter um filesystem próprio sem perder compatibilidade com os formatos principais. Nome de trabalho: **BakenFS**.

Princípios para BakenFS v1:
- formato on-disk próprio e versionado;
- UUID de volume e superblocks redundantes;
- checksums de metadata desde a primeira versão;
- extents 64-bit em vez de FAT chains;
- diretórios indexados;
- timestamps de alta resolução;
- permissões/ownership compatíveis com o modelo futuro de userspace;
- journaling de metadata **ou** desenho copy-on-write; escolher um modelo e provar recovery antes de habilitar uso de produção;
- feature flags `compatible`, `read-only-compatible` e `incompatible` para evolução futura;
- mount fail-closed se versão/feature não for suportada;
- ferramentas próprias de `mkfs`, inspect, fsck/recovery e imagens de teste;
- nenhum dado estático fictício e nenhuma dependência de firmware/UEFI pós-cutover.

**Decisão arquitetural:** BakenFS não substitui os leitores de FAT32/exFAT/NTFS/ext. Ele será o filesystem nativo/preferencial, enquanto os outros drivers oferecem interoperabilidade.

## Trilha D — Rede

**⬜ PLANEJADO.** NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS.

## Trilha E — Áudio

**⬜ PLANEJADO.** HDA, DMA/ring buffer, codec/mixer e API userspace.

## Trilha F — GPU/composição

**⬜ PLANEJADO.** Framebuffer fallback, aceleração/compositor depois do modelo de memória seguro; zero lógica visual no compilador.

## Trilha G — Power / hot-plug ACPI avançado

**⬜ PLANEJADO.** EC, GPE, GlobalLock, transições físicas de energia e extensões firmware-specific estritamente necessárias.

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API exposta ao userspace, executáveis Sotlas, IPC, init/service manager e COW/demand paging.

A implementação estrutural do VFS e dos drivers de filesystem pertence à **Fase 2 / Trilha C**; a Fase 3 expõe essa infraestrutura por syscalls/handles/permissions aos processos de Ring3.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, fontes/acessibilidade, shell, installer/OOBE, apps base, recovery e E2E.

## Regras permanentes

1. `main` pode receber desenvolvimento incremental direto, mas cada novo subestágio deve partir do último checkpoint verde conhecido;
2. runtime real vale mais que teste textual;
3. Kernel Core permanece congelado;
4. toda camada de firmware/hardware tem bounds/marker/fail-closed;
5. nunca fazer scan cego de AML/HID/filesystem;
6. firmware, descriptors e metadata on-disk são input não confiável;
7. hardware/filesystem opcional degrada com diagnóstico;
8. unsupported = unresolved/fail-closed, nunca retorno inventado;
9. toda falha/correção/certificação deve constar aqui e em `KERNEL_HANDOFF.md`;
10. drivers de filesystem nunca bypassam VFS/BlockDevice para acessar AHCI/NVMe diretamente;
11. escrita em filesystem externo só é habilitada depois de testes explícitos de integridade, flush e recovery.
