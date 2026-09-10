# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`.

Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline integrada em `main`

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

| Gate | Resultado |
|---|---|
| CI #1048 / `34471015124` | ✅ |
| SMP #151 / `34471015170` | ✅ 3/3 |
| NVMe #248 / `34471015070` | ✅ |

`main` permanece congelada enquanto a PR #16 termina AML.

## Baselines verdes dentro da PR #16

AML-6a:
```text
8e553f791a8e67fa3dd673700077b6c28b485a71
```
#1051 / #154 / #251 ✅.

AML-6b:
```text
4e90ec22097c71950dcfa9f84b734568d87ae022
feat(acpi): evaluate bounded discovery methods
```

| Gate | Resultado |
|---|---|
| CI #1052 / `34484777900` | ✅ PASS |
| SMP #155 / `34484777931` | ✅ PASS — 3/3 |
| NVMe #252 / `34484777902` | ✅ PASS |

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.** ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guard stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.** Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP->AP e teardown seguro.

Checkpoint histórico: `72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8`.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

### AML-0 — Catálogo DSDT/SSDT
**✅ COMPROVADO**

### AML-1 — Decoder estrutural
**✅ COMPROVADO**

### AML-2 — Namespace core
**✅ COMPROVADO**

### AML-3 — Data objects grammar-aware
**✅ COMPROVADO**

### AML-4 — DSDT/SSDT -> namespace real
**✅ COMPROVADO** em `2a9974ad`.

### AML-5 — Discovery estático
**✅ COMPROVADO** em `3f02decb`.

### AML-6a — Evaluator bounded sem hardware
**✅ COMPROVADO** em `8e553f79`.

### AML-6b — Predefined methods de discovery
**✅ COMPROVADO** em `4e90ec22`.

Suporta resolução segura de `_HID`, `_CID`, `_UID`, `_STA` e `_CRS` quando o Method cabe no subconjunto AML-6a. Unsupported = unresolved; nenhum retorno sintético.

### AML-7 — OperationRegion / Field core
**⏳ EM VALIDAÇÃO NA PR #16**

Escopo final:
- SystemMemory/SystemIO/PCIConfig mediados;
- bounds + overflow;
- MMIO 32-bit alinhado via backend `volatile`;
- I/O 32-bit via `__inl/__outl`;
- PCI config via backend existente e BDF explícito;
- Field <=32 bits dentro de um único dword;
- init sem hardware side effect;
- IndexField/BankField não emulados sem backing seguro.

Markers:
```text
BAKEN:ACPI_AML_REGIONS_READY
BAKEN:ACPI_AML_REGIONS_FAILED
```

### AML-8 — ACPI platform objects
**⏳ EM VALIDAÇÃO NA PR #16**

- `_PIC`: APIC mode (`Arg0=1`) somente se o evaluator puder executar com segurança;
- `_PRT`: Packages de 4 elementos, Pin 0..3, máximo 256 rotas;
- `_S5`: dois SleepTypes 0..7;
- firmware mais complexo permanece unresolved.

Markers:
```text
BAKEN:ACPI_AML_PLATFORM_READY
BAKEN:ACPI_AML_PLATFORM_FAILED
```

Barreira de boot:
```text
AML tables/decoder/data/namespace
-> AML static discovery
-> AML evaluator
-> AML dynamic discovery
-> AML region core
-> AML platform objects
-> PLATFORM_READY
```

**Critério de encerramento AML:** head final da PR #16 com CI + SMP 3/3 + NVMe verdes no mesmo SHA. Após isso, integrar em `main` e promover Trilha A para ✅ CORE CONCLUÍDO.

EC/GPE/GlobalLock, transição efetiva S3/S5 e variações de firmware que exijam AML adicional migram para a futura trilha de power/hot-plug; não bloqueiam o core AML.

Os commits `770176be` e `123cd564` são intermediários de branch, não baseline.

## Trilha B — HID adicional
**⬜ APÓS MERGE AML.** I2C-HID, report descriptors, touchpad/touchscreen, hot-plug.

## Trilha C — Storage de produção
**⬜ PLANEJADO.** Block cache, VFS, FAT32 robusto, handles e async.

## Trilha D — Rede
**⬜ PLANEJADO.** NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS.

## Trilha E — Áudio
**⬜ PLANEJADO.** HDA, DMA/ring buffer, codec/mixer e API userspace.

## Trilha F — GPU/composição
**⬜ PLANEJADO.** Framebuffer fallback, aceleração/compositor após modelo de memória seguro; zero lógica visual no compilador.

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API, executáveis Sotlas, IPC, init/service manager e COW/demand paging.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, fontes/acessibilidade, shell, installer/OOBE, apps base, recovery e E2E da imagem instalada.

## Gates permanentes

```text
CI principal
SMP — 3/3 boots independentes
NVMe-only
```

Regras:
1. `main` não recebe candidato vermelho;
2. runtime real vale mais que teste textual;
3. Kernel Core fica congelado;
4. toda camada AML tem bounds/budget/marker;
5. nunca fazer scan cego;
6. firmware AML é input não confiável;
7. hardware opcional degrada com diagnóstico, não corrompe kernel;
8. unsupported permanece unresolved;
9. falha/correção deve constar aqui e em `KERNEL_HANDOFF.md`.
