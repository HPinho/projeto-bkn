# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Estados: `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU`, `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline integrada em `main`

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

- CI #1048 / `34471015124` ✅;
- SMP #151 / `34471015170` ✅ — 3/3;
- NVMe #248 / `34471015070` ✅.

`main` permanece congelada enquanto a PR #16 termina AML.

## Baselines verdes da PR #16

AML-6a `8e553f79`: #1051 / #154 / #251 ✅.  
AML-6b `4e90ec22`: #1052 / #155 / #252 ✅.

---

# Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.** ExitBootServices, CR3 próprio, PMM/VMM/DMA, W^X, guard stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32, PAT/framebuffer WC e zero UEFI pós-cutover.

# Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.** Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, fault isolation, FPU/SIMD, TLB shootdown, migração BSP->AP e teardown seguro.

Checkpoint histórico: `72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8`.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

| Etapa | Estado | Checkpoint |
|---|---|---|
| AML-0 Catálogo DSDT/SSDT | ✅ | TABLES_READY |
| AML-1 Decoder estrutural | ✅ | DECODER_READY |
| AML-2 Namespace core | ✅ | NAMESPACE_READY |
| AML-3 Data objects | ✅ | DATA_READY |
| AML-4 Namespace real | ✅ | `2a9974ad` |
| AML-5 Discovery estático | ✅ | `3f02decb` |
| AML-6a Evaluator bounded | ✅ | `8e553f79` |
| AML-6b Discovery dinâmico | ✅ | `4e90ec22` |
| AML-7 OperationRegion/Field core | ⏳ | PR #16 |
| AML-8 `_PIC`/`_PRT`/`_S5` | ⏳ | PR #16 |

### AML-6b — checkpoint certificado

```text
4e90ec22097c71950dcfa9f84b734568d87ae022
feat(acpi): evaluate bounded discovery methods
```

- CI #1052 / `34484777900` ✅;
- SMP #155 / `34484777931` ✅ — 3/3;
- NVMe #252 / `34484777902` ✅.

### AML-7 — OperationRegion / Field core

**⏳ EM VALIDAÇÃO.**

- SystemMemory/SystemIO/PCIConfig mediados;
- bounds/overflow antes de hardware;
- MMIO 32-bit alinhado via backend `volatile`;
- I/O via `__inl/__outl`;
- PCI config via backend existente e BDF explícito;
- Field <=32 bits dentro de um único dword;
- init sem side effect de hardware;
- IndexField/BankField não emulados sem backing dedicado.

Markers:
```text
BAKEN:ACPI_AML_REGIONS_READY
BAKEN:ACPI_AML_REGIONS_FAILED
```

### AML-8 — ACPI platform objects

**⏳ EM VALIDAÇÃO.**

- `_PIC`: APIC mode (`Arg0=1`) somente se AML-6a executar com segurança;
- `_PRT`: Package de entradas de quatro elementos, Pin 0..3, máximo 256;
- `_S5`: dois SleepTypes 0..7;
- unsupported permanece unresolved;
- EC/GPE/GlobalLock e sleep transition física ficam para power/hot-plug.

Markers:
```text
BAKEN:ACPI_AML_PLATFORM_READY
BAKEN:ACPI_AML_PLATFORM_FAILED
```

Barreira:
```text
AML tables/decoder/data/namespace
-> AML static discovery
-> AML evaluator
-> AML dynamic discovery
-> AML region core
-> AML platform objects
-> PLATFORM_READY
```

### Validação do candidato AML-7/8

Candidato inicial integrado:
```text
1e3335948e8cf412e8866e06a0224627b325fff8
feat(acpi): complete bounded AML platform core
```

CI #1055 / `34491870501` ❌ em `Run Complete Test Suite` antes de QEMU. `test_build_modular_compiles_kernel_objects` mostrou que o C gerado para `aml_platform_append_prt_entry` passava `int*` para parâmetro `_Bool*`: a variável `source_is_link` estava declarada como `let mut ... = false` e o lowering mutável inferiu `int`.

Correção aplicada no próximo candidato:
```text
let mut source_is_link: bool = false;
```

Foi adicionado teste de regressão exigindo tipagem explícita desse boolean mutável passado por ponteiro. Não houve alteração em scheduler, IRQ, CR3/TLB, FPU, storage ou lógica de acesso de hardware AML.

SMP #158 já havia passado `Verify SMP Contracts` + `compiler.py check` no candidato inicial antes de entrar no build completo; isso confirma que a falha específica era do lowering/C modular e não do grafo de imports.

Os commits `770176be` e `123cd564` são intermediários da branch e não são baselines.

**Critério de encerramento AML:** head final da PR #16 com CI + SMP 3/3 + NVMe verdes no mesmo SHA; então atualizar os dois documentos com os run IDs finais e fast-forward `main` para esse SHA validado.

Após isso: **Trilha A — ACPI/AML CORE = ✅ CONCLUÍDO.** EC/GPE/GlobalLock e firmware-specific AML passam para power/hot-plug.

## Trilha B — HID adicional
**⬜ APÓS MERGE AML.** I2C-HID, report descriptors, touchpad/touchscreen, hot-plug.

## Trilha C — Storage de produção
**⬜ PLANEJADO.** Block cache, VFS, FAT32 robusto, handles e async.

## Trilha D — Rede
**⬜ PLANEJADO.** NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS.

## Trilha E — Áudio
**⬜ PLANEJADO.** HDA, DMA/ring buffer, codec/mixer e API userspace.

## Trilha F — GPU/composição
**⬜ PLANEJADO.** Framebuffer fallback, aceleração/compositor depois do modelo de memória seguro; zero lógica visual no compilador.

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API, executáveis Sotlas, IPC, init/service manager e COW/demand paging.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, fontes/acessibilidade, shell, installer/OOBE, apps base, recovery e E2E.

## Regras permanentes

1. `main` não recebe candidato vermelho;
2. runtime real vale mais que teste textual;
3. Kernel Core permanece congelado;
4. toda camada AML tem bounds/marker/fail-closed;
5. nunca scan cego de AML;
6. firmware AML é input não confiável;
7. hardware opcional degrada com diagnóstico;
8. unsupported = unresolved, nunca retorno inventado;
9. falha/correção deve constar aqui e em `KERNEL_HANDOFF.md`.
