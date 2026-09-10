# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Este roadmap separa `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU` e `⬜ PLANEJADO`. Uma feature só vira baseline quando CI principal + SMP 3/3 + NVMe-only fecham verdes para o mesmo candidato.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline operacional verde

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

Prova no mesmo SHA:

| Gate | Resultado |
|---|---|
| CI principal #1048 / `34471015124` | ✅ PASS |
| SMP #151 / `34471015170` | ✅ PASS — 3/3 boots |
| NVMe-only #248 / `34471015070` | ✅ PASS |

### Regra de integração

Para evitar workflows vermelhos na baseline, `main` fica congelada no último checkpoint verde. Trabalho novo ocorre em branch/PR; falhas são corrigidas ali. A baseline só avança após os três gates obrigatórios passarem.

---

## Fase 0 — Fundação Bare-Metal

**✅ CONCLUÍDA.** Boot/ExitBootServices, CR3 Baken, PMM/VMM/DMA, W^X/guard stack, GDT/TSS/IDT, ACPI/APIC/IRQ/timer, PCI, xHCI/HID, AHCI/NVMe/BlockDevice, GPT/MBR/FAT32, PAT/framebuffer WC e zero UEFI pós-cutover comprovados.

## Fase 1 — Kernel Core

**✅ CONCLUÍDA E CERTIFICADA.** Scheduler preemptivo/SMP, wait/wake/sleep, heap, processos/address spaces, Ring3/syscalls/user-copy, isolamento de faults, FPU/SIMD, TLB shootdown, migração BSP->AP do mesmo TID e teardown seguro permanecem invariantes congelados.

Checkpoint histórico de conclusão: `72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8`.

---

# Fase 2 — Platform e Drivers

## Trilha A — ACPI/AML

### AML-0 — Catálogo DSDT/SSDT
**✅ COMPROVADO.** Marker `BAKEN:ACPI_AML_TABLES_READY`.

### AML-1 — Decoder estrutural
**✅ COMPROVADO.** Cursor/PkgLength/NameString/NameSeg/inteiros. Marker `BAKEN:ACPI_AML_DECODER_READY`.

### AML-2 — Namespace core
**✅ COMPROVADO.** Namespace bounded e read-only fora da janela do loader. Marker `BAKEN:ACPI_AML_NAMESPACE_READY`.

### AML-3 — Data objects grammar-aware
**✅ COMPROVADO e revalidado em `3f02decb`.** String/Buffer/Package/VarPackage, budgets e fail-closed. Marker `BAKEN:ACPI_AML_DATA_READY`.

### AML-4 — DSDT/SSDT -> namespace real
**✅ COMPROVADO em `2a9974ad500ac65da360faf0d1f99461ef78b9bc`.**

Gates:
- CI #1046 / `34465896493` ✅;
- SMP #149 / `34465896534` ✅;
- NVMe #246 / `34465896564` ✅.

Materializa Name/Scope/Device e armazena Method opaco. Marker `BAKEN:ACPI_AML_NAMESPACE_LOADED`.

### AML-5 — Descoberta estática de dispositivos
**✅ COMPROVADO na baseline `3f02decb`.**

Inclui `_HID`, `_CID`, `_UID`, `_ADR`, `_STA` constante, `_CRS` estático, EISA ID e ResourceTemplate bounded. Métodos permanecem diferidos. Marker `BAKEN:ACPI_AML_DEVICES_READY`.

Histórico de regressão:
- `a312c3e8` / CI #1047 (`34470298359`) ❌: criação de ponteiro cru fora de `unsafe` durante `build_modular`;
- `3f02decb` ✅: fronteira `unsafe` corrigida sem mudar a lógica; CI #1048 + SMP #151 + NVMe #248 passaram.

### AML-6a — Evaluator isolado e sem efeitos de hardware
**⏳ EM VALIDAÇÃO** na branch `aml6a-validation`.

SHA técnico original:

```text
17267c3d51456935aefbd5347a4041f4eb69a91b
```

Head que produziu a primeira rodada da PR #16:

```text
7dcd1f6706db6b17c0174fe28839099dda18fb78
```

Implementado:
- 7 Args e 8 Locals por frame;
- `Store` restrito a Local/Arg/Null target;
- `Return`;
- aritmética e lógica inteira básica;
- If/Else com PkgLength;
- leitura read-only de Name estático;
- aridade por MethodFlags;
- serialized/SyncLevel rejeitado até existir lock;
- fuel 4096 + depth 8;
- sem nested Method, While, Sleep/Stall, Notify, OperationRegion/Field ou write global;
- self-test bare-metal antes de `PLATFORM_READY`;
- marker de sucesso `BAKEN:ACPI_AML_EVALUATOR_READY`.

O evaluator ainda não participa da descoberta real. Isso evita misturar engine + semântica de firmware em um único gate.

#### PR #16 — primeira rodada

Merge-test SHA: `7ad3cb6dd9099e2477ee91c6b26f96ebc702fd09`.

| Gate | Resultado |
|---|---|
| CI principal #1049 / `34474459862` | ❌ falso positivo no validador QEMU |
| SMP #152 / `34474459987` | ✅ PASS — 3/3 boots |
| NVMe-only #249 / `34474459985` | ❌ falso positivo no validador QEMU |

Os dois logs vermelhos chegaram a `BAKEN:ACPI_AML_EVALUATOR_READY`, `PLATFORM_READY`, scheduler, wait/wake e Ring3. A causa não foi a engine AML-6a: o smoke tratava `HEX=T` como falha do evaluator e `HEX=U` como detalhe, mas `HEX=T` já é usado pelo LAPIC timer e `HEX=U` pelo userspace loader.

#### Correção do protocolo — `12b97433`

```text
12b97433af677b2ea93764c95c0bcf38cfb8ce4d
fix(acpi): disambiguate AML evaluator diagnostics
```

Mudanças:
- novo marker terminal e exclusivo: `BAKEN:ACPI_AML_EVALUATOR_FAILED`;
- `HEX=T/U` permanecem apenas como detalhe diagnóstico e nunca classificam falha isoladamente;
- `verify_kernel_smoke.py` usa apenas o marker textual exclusivo para falha AML-6a;
- `run_smp_qemu.py` exige `BAKEN:ACPI_AML_EVALUATOR_READY` e reconhece o marker exclusivo de falha;
- teste de contrato garante que `HEX=T/U` isolados não gerem falso positivo;
- Kernel Core, timer, IRQ, CR3/TLB, FPU, Ring3 e lógica do evaluator permanecem intactos.

#### Segunda rodada — SMP #153

| Gate | Resultado observado |
|---|---|
| CI principal #1050 / `34479698316` | ⏳ estava em execução quando o gate SMP revelou a inconsistência |
| SMP #153 / `34479698271` | ❌ falhou em `Verify SMP Contracts`, antes de build/QEMU |
| NVMe-only #250 / `34479698333` | ⏳ estava em execução quando o gate SMP revelou a inconsistência |

Causa do SMP #153: `test_local_smp_runner.py::test_every_local_marker_is_required_by_workflow` detectou que o runner Python já exigia `BAKEN:ACPI_AML_EVALUATOR_READY`, mas o YAML `.github/workflows/baken_smp.yml` ainda não continha esse marker explicitamente. Portanto o gate recusou corretamente um desalinhamento entre a prova local e a prova do Actions.

Correção do candidato seguinte:
- adicionar `python3 tests/test_acpi_aml_evaluator.py` ao `Verify SMP Contracts`;
- adicionar parada fail-closed no YAML para `BAKEN:ACPI_AML_EVALUATOR_FAILED`;
- adicionar `require_marker 'BAKEN:ACPI_AML_EVALUATOR_READY'` em cada boot SMP;
- reforçar o contrato para manter runner Python, workflow e runtime sincronizados.

**Promoção:** somente após uma nova revisão da PR #16 fechar CI + SMP 3/3 + NVMe-only verdes.

### AML-6b — Métodos predefinidos para discovery
**⬜ BLOQUEADO ATÉ AML-6a VERDE.**

Planejado:
- chamar métodos zero-arg estritamente necessários (`_STA`, `_CRS`, `_HID`, `_CID`, `_UID`) quando o AML-5 registrar `requires_evaluator`;
- validar tipo do retorno por predefined object;
- preservar fuel/depth;
- nenhuma OperationRegion até AML-7;
- adicionar nested Method calls somente quando firmware real exigir e com profundidade/aridade controladas.

### AML-7 — OperationRegion / Field
**⬜ PLANEJADO.** SystemMemory, SystemIO e PCIConfig mediados por camadas nativas, com bounds rígidos; Field/IndexField apenas quando necessário.

### AML-8 — ACPI power/routing
**⬜ PLANEJADO.** `_PRT`/`_PIC`, `_S5`, sleep/wake posterior e EC somente após infraestrutura segura.

## Trilha B — HID adicional
**⬜ DEPOIS DO AML/RESOURCE CORE.** I2C-HID, report descriptors, touchpad/touchscreen, hot-plug.

## Trilha C — Storage de produção
**⬜ PLANEJADO.** Block cache, VFS, FAT32 robusto, handles e async posterior.

## Trilha D — Rede
**⬜ PLANEJADO.** NIC, Ethernet/ARP, IPv4/IPv6, ICMP, UDP/TCP, DHCP/DNS.

## Trilha E — Áudio
**⬜ PLANEJADO.** HDA, DMA/ring buffer, codec/mixer e API userspace.

## Trilha F — GPU/composição
**⬜ PLANEJADO.** Framebuffer como fallback; aceleração/compositor somente após modelo de memória seguro; zero lógica visual no compilador Sotlas.

---

# Fase 3 — Serviços e userspace

**⬜ PLANEJADO.** ABI versionada, handles/permissões, VFS/file API, executáveis Sotlas, IPC, init/service manager e COW/demand paging posterior.

# Fase 4 — Experiência Baken

**⬜ PLANEJADO.** Compositor, WM, input unificado, fontes/acessibilidade, shell, installer/OOBE, apps base, recuperação e E2E da imagem instalada.

---

## Gates permanentes

Antes de promover qualquer checkpoint da Fase 2:

```text
CI principal
SMP verification — 3/3 boots independentes
NVMe-only verification
```

Markers AML acumulados na baseline `3f02decb`:

```text
BAKEN:ACPI_AML_TABLES_READY
BAKEN:ACPI_AML_DECODER_READY
BAKEN:ACPI_AML_DATA_READY
BAKEN:ACPI_AML_NAMESPACE_READY
BAKEN:ACPI_AML_NAMESPACE_LOADED
BAKEN:ACPI_AML_DEVICES_READY
```

Markers candidatos AML-6a:

```text
BAKEN:ACPI_AML_EVALUATOR_READY
BAKEN:ACPI_AML_EVALUATOR_FAILED
```

O segundo é terminal somente quando explicitamente emitido. `HEX=T/U` não são exclusivos de AML e não podem, isoladamente, reprovar um gate.

## Regras de prioridade

1. `main` não recebe candidato com gate vermelho;
2. runtime real vale mais que teste textual;
3. Kernel Core fica congelado salvo necessidade comprovada;
4. cada sucessão AML recebe bounds/budget/marker/diagnóstico;
5. nunca fazer scan cego de AML desconhecido;
6. firmware AML é input não confiável;
7. hardware opcional deve degradar com diagnóstico, não corromper o kernel;
8. qualquer falha e sua correção são registradas aqui e em `KERNEL_HANDOFF.md`.
