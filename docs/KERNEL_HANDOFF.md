# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este é o registro operacional de continuidade. Código presente não equivale a prova: um incremento só vira baseline quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato.

## Política de baseline verde

- `main` permanece no último SHA integrado e comprovado.
- trabalho novo ocorre em branch/PR;
- falhas são corrigidas fora de `main`;
- nenhuma etapa é promovida removendo marker/teste ou aumentando timeout sem causa;
- runtime QEMU vale mais do que teste textual;
- toda implementação/falha/correção deve ser refletida aqui e em `docs/BAKEN_OS_ROADMAP.md`.

## Baseline integrada em `main`

**✅ CERTIFICADO**

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

Gates:
- CI #1048 / `34471015124` ✅;
- SMP #151 / `34471015170` ✅ — 3/3 boots;
- NVMe-only #248 / `34471015070` ✅.

A `main` continua congelada durante a finalização da PR #16.

## Baseline verde da PR #16

### AML-6a

**✅ COMPROVADO**

```text
8e553f791a8e67fa3dd673700077b6c28b485a71
fix(ci): align SMP AML evaluator proof contract
```

- CI #1051 / `34480220577` ✅;
- SMP #154 / `34480220696` ✅ — 3/3;
- NVMe #251 / `34480220755` ✅.

### AML-6b

**✅ COMPROVADO**

```text
4e90ec22097c71950dcfa9f84b734568d87ae022
feat(acpi): evaluate bounded discovery methods
```

Gates no mesmo SHA:
- CI principal #1052 / `34484777900` ✅ PASS — suíte completa, grafo modular, build Sotlas, ISO e QEMU;
- SMP #155 / `34484777931` ✅ PASS — 3/3 boots com AP dispatch, TLB, Ring3 migration e FPU;
- NVMe-only #252 / `34484777902` ✅ PASS.

AML-6b mantém AML-5 como fonte estática e usa AML-6a apenas em `_HID`, `_CID`, `_UID`, `_STA` e `_CRS` marcados `requires_evaluator`. Métodos fora do subconjunto ficam unresolved; nenhum valor é fabricado.

## Histórico de falhas relevante

- AML-4: `Scope(\)` foi inicialmente rejeitado. Corrigido em `2a9974ad`; #1046/#149/#246 verdes.
- AML-5: CI #1047 detectou conversão de ponteiro fora de `unsafe`. Corrigido em `3f02decb`.
- AML-6a: CI #1049 e NVMe #249 foram falsos positivos por colisão `HEX=T/U`; criado `BAKEN:ACPI_AML_EVALUATOR_FAILED`.
- SMP #153 detectou divergência runner/YAML; corrigida em `8e553f79`.
- Nenhuma dessas correções relaxou scheduler, CR3/TLB, FPU, Ring3 ou storage.

## Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. frame/stack só é liberado após entrada posterior do scheduler na CPU anterior;
4. FPU save -> schedule -> CR3/TSS -> FPU restore permanece sob switch lock;
5. migração Ring3 BSP->AP preserva TID, address-space root e SIMD;
6. teardown só ocorre após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` continua terminal;
8. provas wait/sleep, TLB, Ring3 e SMP não podem ser removidas para acomodar AML.

---

# Estado ACPI/AML

## AML-0 — tabelas
**✅ COMPROVADO.** DSDT/SSDT bounded, checksum e `BAKEN:ACPI_AML_TABLES_READY`.

## AML-1 — decoder
**✅ COMPROVADO.** Cursor, PkgLength, NameString e Integer fail-closed.

## AML-2 — namespace
**✅ COMPROVADO.** Namespace bounded/read-only fora da janela do loader.

## AML-3 — Data Objects
**✅ COMPROVADO.** String/Buffer/Package/VarPackage, sem scan cego.

## AML-4 — DSDT/SSDT -> namespace
**✅ COMPROVADO em `2a9974ad500ac65da360faf0d1f99461ef78b9bc`.**

## AML-5 — discovery estático
**✅ COMPROVADO na baseline `3f02decb`.**

## AML-6a — evaluator sem hardware
**✅ COMPROVADO em `8e553f79`.**

Suporta Arg0..6, Local0..7, Store local/arg/null, Return, aritmética/lógica, If/Else, leitura read-only do namespace, fuel/depth e MethodFlags. Continua bloqueando nested method, While, Sleep/Stall, Notify, OperationRegion/Field, global writes e Serialized/SyncLevel.

## AML-6b — discovery dinâmico
**✅ COMPROVADO em `4e90ec22`.**

Markers:
```text
BAKEN:ACPI_AML_DYNAMIC_READY
BAKEN:ACPI_AML_DYNAMIC_FAILED
```

# AML-7 — OperationRegion / Field core

**⏳ EM VALIDAÇÃO NA PR #16**

Objetivo desta etapa final antes do merge:
- descritores bounded para SystemMemory, SystemIO e PCIConfig;
- overflow e limite validados antes de qualquer acesso;
- SystemMemory somente por MMIO 32-bit `volatile` já existente e page mapping nativo;
- SystemIO somente por `__inl/__outl`;
- PCIConfig somente via `pci_read_config32/pci_write_config32` com BDF explícito;
- Field limitado a até 32 bits e a um único dword;
- read-modify-write somente após validação de geometry e region bounds;
- init/self-test **não toca hardware**;
- IndexField/BankField não são emulados silenciosamente: permanecem unsupported até backing dedicado.

Markers candidatos:
```text
BAKEN:ACPI_AML_REGIONS_READY
BAKEN:ACPI_AML_REGIONS_FAILED
```

O marker READY prova o **core de mediação**, não execução automática de todos os OperationRegions do firmware.

# AML-8 — `_PIC`, `_PRT`, `_S5`

**⏳ EM VALIDAÇÃO NA PR #16**

- `_PIC`: se existir como Method de 1 argumento, tenta APIC mode com `Arg0=1` usando AML-6a. Se exigir global write/OperationRegion/opcode não suportado, fica presente porém não aplicado; o boot não inventa sucesso.
- `_PRT`: Name/Method zero-arg que produza Package bounded; cada rota exige exatamente 4 elementos `Address, Pin, Source, SourceIndex`; `Pin` 0..3; máximo 256 rotas.
- `_S5`: Name/Method zero-arg que produza Package; os dois primeiros elementos devem ser inteiros 0..7.
- EC, GPE, GlobalLock e transição física de sleep ficam fora deste core; são expansão posterior de power/hotplug.

Markers candidatos:
```text
BAKEN:ACPI_AML_PLATFORM_READY
BAKEN:ACPI_AML_PLATFORM_FAILED
```

Nova barreira:
```text
AML-5 static
-> AML-6a evaluator
-> AML-6b dynamic discovery
-> AML-7 region core
-> AML-8 platform objects
-> PLATFORM_READY
```

Os commits intermediários `770176be` e `123cd564` apenas adicionaram os dois módulos na branch e **não são baseline/candidatos de merge**. Somente o head final integrado, com testes/smoke/docs e os três gates verdes, pode substituir `4e90ec22`.

## Critério para encerrar AML e integrar PR #16

1. CI principal verde;
2. SMP verification verde em 3/3 boots independentes;
3. NVMe-only verde;
4. todos no mesmo head final;
5. `ACPI_AML_REGIONS_READY` e `ACPI_AML_PLATFORM_READY` presentes no smoke;
6. nenhum marker AML `*_FAILED`, `HEX=A/R` ou CPU `HEX=E`;
7. atualizar estes dois documentos com o SHA final e os run IDs;
8. só então integrar a PR #16 em `main`.

Depois do merge, a trilha ACPI/AML core é considerada encerrada. EC/GPE/GlobalLock, sleep transition completa e firmware-specific AML passam a pertencer à trilha de power/hot-plug, não bloqueiam Platform/Drivers.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
