# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Este roadmap separa `✅ COMPROVADO`, `⏳ EM VALIDAÇÃO`, `❌ FALHOU` e `⬜ PLANEJADO`. Uma feature só vira baseline integrada quando CI principal + SMP 3/3 + NVMe-only fecham verdes para o mesmo candidato.

## Estado geral

**Fase 0 — Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Fase 1 — Kernel Core: ✅ CONCLUÍDA E CERTIFICADA**  
**Fase 2 — Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline integrada em `main`

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

Para evitar workflows vermelhos na baseline, `main` fica congelada no último checkpoint verde integrado. Trabalho novo ocorre em branch/PR; falhas são corrigidas ali. A baseline só avança após os três gates obrigatórios passarem.

A PR #16 já possui uma baseline verde própria para AML-6a:

```text
8e553f791a8e67fa3dd673700077b6c28b485a71
fix(ci): align SMP AML evaluator proof contract
```

Prova:
- CI #1051 / `34480220577` ✅;
- SMP #154 / `34480220696` ✅ — 3/3 boots;
- NVMe-only #251 / `34480220755` ✅.

Esse checkpoint é a base de AML-6b, sem mover `main`.

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
**✅ COMPROVADO na baseline integrada `3f02decb`.**

Inclui `_HID`, `_CID`, `_UID`, `_ADR`, `_STA` constante, `_CRS` estático, EISA ID e ResourceTemplate bounded. Métodos permanecem diferidos e marcados `requires_evaluator`. Marker `BAKEN:ACPI_AML_DEVICES_READY`.

Histórico de regressão:
- `a312c3e8` / CI #1047 (`34470298359`) ❌: criação de ponteiro cru fora de `unsafe`;
- `3f02decb` ✅: fronteira `unsafe` corrigida sem mudar a lógica; CI #1048 + SMP #151 + NVMe #248 passaram.

### AML-6a — Evaluator isolado e sem efeitos de hardware
**✅ COMPROVADO na PR #16 / branch `aml6a-validation`.**

Checkpoint:

```text
8e553f791a8e67fa3dd673700077b6c28b485a71
fix(ci): align SMP AML evaluator proof contract
```

| Gate | Resultado |
|---|---|
| CI principal #1051 / `34480220577` | ✅ PASS |
| SMP #154 / `34480220696` | ✅ PASS — 3/3 boots |
| NVMe-only #251 / `34480220755` | ✅ PASS |

Escopo comprovado:
- 7 Args e 8 Locals por frame;
- `Store` restrito a Local/Arg/Null target;
- `Return`;
- aritmética/lógica inteira básica;
- If/Else com PkgLength;
- leitura read-only de Name estático;
- aridade por MethodFlags;
- Serialized/SyncLevel rejeitado até existir lock;
- fuel 4096 + depth 8;
- sem nested Method, While, Sleep/Stall, Notify, OperationRegion/Field ou write global;
- marker `BAKEN:ACPI_AML_EVALUATOR_READY`.

#### Histórico de falhas AML-6a

Primeira rodada da PR:
- CI #1049 / `34474459862` ❌ falso positivo;
- SMP #152 / `34474459987` ✅ 3/3;
- NVMe #249 / `34474459985` ❌ falso positivo.

Causa: `HEX=T` já pertencia ao timer e `HEX=U` ao userspace. O validador os confundiu com erro AML.

`12b97433` criou `BAKEN:ACPI_AML_EVALUATOR_FAILED` como marker terminal exclusivo; `HEX=T/U` ficaram somente como detalhes.

SMP #153 / `34479698271` depois falhou em `Verify SMP Contracts`: runner Python exigia `ACPI_AML_EVALUATOR_READY`, mas YAML não. O gate recusou corretamente a divergência.

`8e553f79` alinhou YAML, runner e teste. A rodada #1051/#154/#251 fechou 3/3 verde e certificou AML-6a.

### AML-6b — Métodos predefinidos para discovery
**⏳ EM VALIDAÇÃO** na mesma PR #16, partindo de `8e553f79`.

Implementação candidata:
- novo overlay `aml_dynamic_discovery.sotlas`, separado do AML-5;
- processa somente devices já descobertos pelo AML-5;
- tenta apenas `_HID`, `_CID`, `_UID`, `_STA` e `_CRS` com `requires_evaluator`;
- somente métodos zero-arg, não-Serialized e SyncLevel zero;
- usa exclusivamente a engine AML-6a certificada;
- mantém arrays/capacidades fixas; zero heap;
- nenhum OperationRegion/Field ou write MMIO/PIO/PCI;
- método não suportado permanece **unresolved**, sem valor sintético;
- falha estrutural da camada impede `PLATFORM_READY`.

Validação de retorno:
- `_HID`: EISA Integer ou HID string estrita;
- `_CID`: Integer/string ou Package/VarPackage bounded;
- `_UID`: Integer ou string imprimível;
- `_STA`: Integer <= `0x1F`, com bits de presença/habilitação válidos;
- `_CRS`: Buffer completo com ResourceTemplate bounded, EndTag e checksum; sem zero-fill implícito fabricado.

Nova ordem de publicação:

```text
AML-5 static discovery
-> AML-6a evaluator
-> AML-6b dynamic discovery
-> PLATFORM_READY
```

Markers candidatos:

```text
BAKEN:ACPI_AML_DYNAMIC_READY
BAKEN:ACPI_AML_DYNAMIC_FAILED
```

`DYNAMIC_READY` certifica que o passe bounded completou; não afirma que todo método de firmware foi resolvido. Firmware que dependa de opcodes ainda fora do subconjunto continua pendente até etapas posteriores.

Gates exigidos para promoção de AML-6b:
- CI principal;
- SMP 3/3;
- NVMe-only;
todos no mesmo SHA.

### AML-7 — OperationRegion / Field
**⬜ PLANEJADO.** SystemMemory, SystemIO e PCIConfig mediados por camadas nativas, com bounds rígidos; Field/IndexField apenas quando necessário. Nenhuma região pode escapar de endereço/tamanho validado.

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

Markers AML comprovados até AML-6a na PR #16:

```text
BAKEN:ACPI_AML_TABLES_READY
BAKEN:ACPI_AML_DECODER_READY
BAKEN:ACPI_AML_DATA_READY
BAKEN:ACPI_AML_NAMESPACE_READY
BAKEN:ACPI_AML_NAMESPACE_LOADED
BAKEN:ACPI_AML_DEVICES_READY
BAKEN:ACPI_AML_EVALUATOR_READY
```

Falha exclusiva AML-6a:

```text
BAKEN:ACPI_AML_EVALUATOR_FAILED
```

`HEX=T/U` não são exclusivos de AML e não podem, isoladamente, reprovar um gate.

Markers candidatos AML-6b:

```text
BAKEN:ACPI_AML_DYNAMIC_READY
BAKEN:ACPI_AML_DYNAMIC_FAILED
```

## Regras de prioridade

1. `main` não recebe candidato com gate vermelho;
2. runtime real vale mais que teste textual;
3. Kernel Core fica congelado salvo necessidade comprovada;
4. cada sucessão AML recebe bounds/budget/marker/diagnóstico;
5. nunca fazer scan cego de AML desconhecido;
6. firmware AML é input não confiável;
7. hardware opcional deve degradar com diagnóstico, não corromper o kernel;
8. método dinâmico não suportado fica unresolved; nunca inventar retorno;
9. qualquer falha e sua correção são registradas aqui e em `KERNEL_HANDOFF.md`.
