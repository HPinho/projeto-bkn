# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este arquivo é o registro operacional de continuidade. Código presente não equivale a prova: um incremento só vira baseline quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato.

## Política de baseline verde

- `main` permanece no último SHA integrado e comprovado;
- trabalho novo ocorre em branch/PR;
- falhas e correções ficam fora de `main`;
- nunca remover marker/teste ou aumentar timeout sem causa para obter verde;
- runtime QEMU vale mais que teste textual;
- toda implementação, falha e correção deve ser registrada aqui e em `docs/BAKEN_OS_ROADMAP.md`.

## Baseline integrada em `main`

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

Gates:
- CI #1048 / `34471015124` ✅;
- SMP #151 / `34471015170` ✅ — 3/3 boots;
- NVMe-only #248 / `34471015070` ✅.

A `main` permanece congelada até a conclusão da PR #16.

## Baselines verdes da PR #16

### AML-6a — evaluator bounded

```text
8e553f791a8e67fa3dd673700077b6c28b485a71
```

- CI #1051 / `34480220577` ✅;
- SMP #154 / `34480220696` ✅ — 3/3;
- NVMe #251 / `34480220755` ✅.

### AML-6b — predefined discovery methods

```text
4e90ec22097c71950dcfa9f84b734568d87ae022
feat(acpi): evaluate bounded discovery methods
```

- CI #1052 / `34484777900` ✅ — suíte completa, grafo modular, build, ISO e QEMU;
- SMP #155 / `34484777931` ✅ — 3/3, AP/TLB/Ring3/FPU;
- NVMe #252 / `34484777902` ✅.

## Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. frame/stack só é liberado após entrada posterior do scheduler na CPU anterior;
4. FPU save -> schedule -> CR3/TSS -> FPU restore permanece sob switch lock;
5. migração Ring3 BSP->AP preserva TID, address-space root e SIMD;
6. teardown ocorre apenas após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` continua terminal;
8. wait/sleep, TLB, Ring3 e SMP não podem ser relaxados para acomodar AML.

---

# Estado ACPI/AML

| Etapa | Estado | Checkpoint principal |
|---|---|---|
| AML-0 DSDT/SSDT | ✅ | `ACPI_AML_TABLES_READY` |
| AML-1 decoder | ✅ | `ACPI_AML_DECODER_READY` |
| AML-2 namespace | ✅ | `ACPI_AML_NAMESPACE_READY` |
| AML-3 data objects | ✅ | `ACPI_AML_DATA_READY` |
| AML-4 DSDT/SSDT -> namespace | ✅ | `2a9974ad` |
| AML-5 discovery estático | ✅ | `3f02decb` |
| AML-6a evaluator | ✅ | `8e553f79` |
| AML-6b dynamic discovery | ✅ | `4e90ec22` |
| AML-7 OperationRegion/Field core | ⏳ | PR #16 |
| AML-8 `_PIC`/`_PRT`/`_S5` | ⏳ | PR #16 |

## AML-7 — OperationRegion / Field core

Candidato implementado na PR #16:
- descritores bounded para SystemMemory, SystemIO e PCIConfig;
- overflow e bounds validados antes do acesso;
- SystemMemory por MMIO 32-bit `volatile` + page mapping nativo;
- SystemIO por `__inl/__outl`;
- PCIConfig por `pci_read_config32/pci_write_config32` com BDF explícito;
- Field limitado a até 32 bits e um único dword;
- init/self-test não toca hardware;
- IndexField/BankField não são emulados silenciosamente.

Markers:
```text
BAKEN:ACPI_AML_REGIONS_READY
BAKEN:ACPI_AML_REGIONS_FAILED
```

READY certifica o core de mediação, não execução automática de todo OperationRegion do firmware.

## AML-8 — objetos de plataforma

Candidato implementado na PR #16:
- `_PIC`: tenta APIC mode com `Arg0=1` somente pela engine AML-6a; se exigir opcode/target proibido, fica presente e não aplicado;
- `_PRT`: Package bounded; cada entrada exige 4 elementos `Address, Pin, Source, SourceIndex`; Pin 0..3; máximo 256 rotas;
- `_S5`: Package com dois primeiros SleepTypes inteiros 0..7;
- unsupported permanece unresolved; nenhum retorno é fabricado;
- EC/GPE/GlobalLock e transição física de sleep ficam para power/hot-plug posterior.

Markers:
```text
BAKEN:ACPI_AML_PLATFORM_READY
BAKEN:ACPI_AML_PLATFORM_FAILED
```

Barreira de publicação:
```text
AML-5 static
-> AML-6a evaluator
-> AML-6b dynamic discovery
-> AML-7 region core
-> AML-8 platform objects
-> PLATFORM_READY
```

## Validação AML-7/8 — histórico atual

Candidato integrado inicial:
```text
1e3335948e8cf412e8866e06a0224627b325fff8
feat(acpi): complete bounded AML platform core
```

- SMP #158: `Verify SMP Contracts` + `compiler.py check` passaram; build nativo iniciou.
- CI #1055 / run `34491870501`: ❌ falhou em `Run Complete Test Suite`, especificamente `test_build_modular_compiles_kernel_objects`, antes de QEMU.
- causa: Sotlas lowered `let mut source_is_link = false` para temporário C `int`, mas `aml_platform_source(..., *mut bool, ...)` exige `_Bool*`; GCC com `-Werror` rejeitou `int* -> _Bool*`.
- correção: tipagem explícita `let mut source_is_link: bool = false;` em `aml_platform_append_prt_entry` e teste de regressão que exige essa anotação.
- a falha não envolveu scheduler, IRQ, FPU, CR3/TLB, storage nem acesso de hardware AML; o QEMU do CI #1055 não chegou a iniciar.

Os commits intermediários `770176be` e `123cd564` adicionaram módulos na branch e não são baselines/candidatos de merge.

## Histórico de falhas anterior

- AML-4: `Scope(\)` foi inicialmente rejeitado; corrigido em `2a9974ad`.
- AML-5: CI #1047 detectou raw pointer cast fora de `unsafe`; corrigido em `3f02decb`.
- AML-6a: CI #1049 e NVMe #249 foram falsos positivos por colisão `HEX=T/U`; criado `BAKEN:ACPI_AML_EVALUATOR_FAILED`.
- SMP #153 detectou divergência runner/YAML; corrigida em `8e553f79`.

## Critério para encerrar AML e integrar PR #16

1. CI principal verde;
2. SMP 3/3 verde;
3. NVMe-only verde;
4. todos no mesmo head final;
5. `ACPI_AML_REGIONS_READY` e `ACPI_AML_PLATFORM_READY` presentes nos smokes que usam `verify_kernel_smoke.py`;
6. nenhum `*_FAILED`, `HEX=A/R` ou `HEX=E`;
7. registrar SHA final e run IDs neste arquivo e no roadmap;
8. fast-forward de `main` para o SHA efetivamente validado, evitando criar um commit de merge não testado.

Depois do merge, a trilha ACPI/AML core é considerada concluída. EC/GPE/GlobalLock, transições completas de energia e extensões firmware-specific passam para power/hot-plug.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
