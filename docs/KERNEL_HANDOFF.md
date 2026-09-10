# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este arquivo é o registro operacional de continuidade. Código presente não equivale a prova: um incremento só vira baseline quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Política de baseline verde

- `main` recebe somente runtime comprovado;
- trabalho novo ocorre em branch/PR;
- falhas e correções ficam fora de `main` até os gates fecharem;
- nunca remover marker/teste ou aumentar timeout sem causa para obter verde;
- runtime QEMU vale mais que teste textual;
- toda implementação, falha, correção e certificação deve ser registrada aqui e em `docs/BAKEN_OS_ROADMAP.md`.

## Baseline de runtime certificada e integrada em `main`

```text
7803447a4c2179d088948b3c4288b6e3655bc1d5
fix(acpi): preserve bool type in PRT lowering
```

Gates no mesmo SHA:
- CI #1056 / `34493002949` ✅;
- SMP #159 / `34493003041` ✅ — 3/3 boots;
- NVMe-only #256 / `34493002936` ✅.

A PR #16 foi integrada por fast-forward; o `merge_commit_sha` é o próprio `7803447a`, portanto nenhum commit de runtime diferente do candidato testado foi criado. Commits posteriores que alterem apenas documentação não substituem esta baseline de runtime.

## Baselines ACPI/AML relevantes

- AML-6a `8e553f791a8e67fa3dd673700077b6c28b485a71`: CI #1051 + SMP #154 3/3 + NVMe #251 ✅.
- AML-6b `4e90ec22097c71950dcfa9f84b734568d87ae022`: CI #1052 + SMP #155 3/3 + NVMe #252 ✅.
- AML-7/8 final `7803447a4c2179d088948b3c4288b6e3655bc1d5`: CI #1056 + SMP #159 3/3 + NVMe #256 ✅.

## Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. frame/stack só é liberado após entrada posterior do scheduler na CPU anterior;
4. FPU save -> schedule -> CR3/TSS -> FPU restore permanece sob switch lock;
5. migração Ring3 BSP->AP preserva TID, address-space root e SIMD;
6. teardown ocorre apenas após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` continua terminal;
8. wait/sleep, TLB, Ring3 e SMP não podem ser relaxados para acomodar novas camadas.

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
| AML-6a evaluator bounded | ✅ | `8e553f79` |
| AML-6b dynamic discovery | ✅ | `4e90ec22` |
| AML-7 OperationRegion/Field core | ✅ | `7803447a` |
| AML-8 `_PIC`/`_PRT`/`_S5` | ✅ | `7803447a` |

**Trilha ACPI/AML core: ✅ CONCLUÍDA E CERTIFICADA.**

## AML-7 — OperationRegion / Field core

Implementado e comprovado:
- descritores bounded para SystemMemory, SystemIO e PCIConfig;
- overflow e bounds validados antes do acesso;
- SystemMemory por MMIO 32-bit `volatile` + page mapping nativo;
- SystemIO por `__inl/__outl`;
- PCIConfig por `pci_read_config32/pci_write_config32` com BDF explícito;
- Field limitado a até 32 bits e um único dword;
- init/self-test sem acesso de hardware;
- IndexField/BankField não são emulados silenciosamente.

Markers:
```text
BAKEN:ACPI_AML_REGIONS_READY
BAKEN:ACPI_AML_REGIONS_FAILED
```

READY certifica o core de mediação; não significa execução irrestrita de AML/OperationRegion arbitrário do firmware.

## AML-8 — objetos de plataforma

Implementado e comprovado:
- `_PIC`: APIC mode com `Arg0=1` somente se a engine bounded conseguir executar com segurança;
- `_PRT`: Package bounded; entradas `Address, Pin, Source, SourceIndex`, Pin 0..3, máximo 256;
- `_S5`: dois primeiros SleepTypes inteiros 0..7;
- unsupported permanece unresolved; nenhum retorno é fabricado;
- EC/GPE/GlobalLock e transição física de sleep ficam para power/hot-plug posterior.

Markers:
```text
BAKEN:ACPI_AML_PLATFORM_READY
BAKEN:ACPI_AML_PLATFORM_FAILED
```

Barreira certificada:
```text
AML-5 static
-> AML-6a evaluator
-> AML-6b dynamic discovery
-> AML-7 region core
-> AML-8 platform objects
-> PLATFORM_READY
```

## Histórico da correção final AML-7/8

Candidato inicial:
```text
1e3335948e8cf412e8866e06a0224627b325fff8
feat(acpi): complete bounded AML platform core
```

CI #1055 / `34491870501` ❌ falhou antes do QEMU em `test_build_modular_compiles_kernel_objects`: `let mut source_is_link = false` foi lowered para `int`, enquanto `aml_platform_source(..., *mut bool, ...)` exigia `_Bool*`.

Correção final:
```text
let mut source_is_link: bool = false;
```

Foi adicionado teste de regressão para essa fronteira de lowering. O candidato `7803447a` passou os três gates e encerrou a falha.

## Próxima frente

Com ACPI/AML core fechado, a próxima trilha é **HID adicional / input de produção**:
- parser de HID report descriptor;
- abstração de dispositivos de input além do boot protocol;
- touchpad/touchscreen e I2C-HID quando houver transporte seguro;
- hot-plug e lifecycle sem quebrar xHCI/HID já certificado.

EC/GPE/GlobalLock e extensões firmware-specific permanecem na futura trilha de power/hot-plug.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
