# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este é o registro operacional de continuidade. Código presente não equivale a prova: um incremento só vira baseline quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato.

## Política de baseline verde

A partir de AML-6, `main` permanece no último SHA comprovado integrado. Incrementos são desenvolvidos e corrigidos em branch/PR de validação. Um candidato só substitui a baseline integrada depois de fechar os três gates sem regressão.

Registrar sempre em **este arquivo e `docs/BAKEN_OS_ROADMAP.md`**:

- `⏳ EM VALIDAÇÃO`, `✅ COMPROVADO` ou `❌ FALHOU`;
- SHA exato do código quando já conhecido;
- runs/gates usados como prova;
- causa objetiva da falha;
- correção aplicada;
- próximo passo.

Nunca remover marker/teste, aumentar timeout sem causa ou trocar prova bare-metal por mock para esconder regressão.

---

## Baseline integrada em `main`

**Estado: ✅ CERTIFICADO**

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

Gates no mesmo SHA:

- CI principal #1048 — run `34471015124` — ✅ PASS;
- SMP #151 — run `34471015170` — ✅ PASS, incluindo 3/3 boots e migração Ring3/FPU;
- NVMe-only #248 — run `34471015070` — ✅ PASS.

A `main` continua propositalmente congelada nesse checkpoint durante a validação AML-6. O checkpoint histórico de conclusão inicial do Kernel Core continua sendo `72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8`.

### Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. ownership de frame/stack é liberado somente após entrada posterior do scheduler na CPU anterior;
4. BSP/AP usam FPU save -> schedule -> CR3/TSS -> restore;
5. o mesmo TID Ring3 migra BSP -> AP preservando address-space root e SIMD;
6. reaper/teardown só ocorre após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` é terminal;
8. `HEX=Q` e `HEX=W` permanecem fail-closed.

Nenhuma mudança AML-6a/6b deve alterar esses invariantes.

---

## Estado da Fase 2 — ACPI/AML

### AML-0 — tabelas DSDT/SSDT
**✅ COMPROVADO.** Catálogo validado e marker `BAKEN:ACPI_AML_TABLES_READY`.

### AML-1 — decoder estrutural
**✅ COMPROVADO.** Cursor limitado, PkgLength, NameString/NameSeg e inteiros; marker `BAKEN:ACPI_AML_DECODER_READY`.

### AML-2 — namespace core read-only
**✅ COMPROVADO.** Namespace estático/bounded, resolução absoluta/relativa/parent e janela controlada do loader; marker `BAKEN:ACPI_AML_NAMESPACE_READY`.

### AML-3 — data objects grammar-aware
**✅ COMPROVADO e revalidado em `3f02decb`.** String/Buffer/Package/VarPackage, budgets e nenhuma varredura cega; marker `BAKEN:ACPI_AML_DATA_READY`.

### AML-4 — DSDT/SSDT -> namespace real
**✅ COMPROVADO.**

Checkpoint:

```text
2a9974ad500ac65da360faf0d1f99461ef78b9bc
fix(acpi): accept root NullName in AML ScopeOp
```

Gates:
- CI #1046 — run `34465896493` — ✅;
- SMP #149 — run `34465896534` — ✅;
- NVMe #246 — run `34465896564` — ✅.

O loader materializa Name/Scope/Device e armazena Method como corpo opaco; não executa AML. Marker `BAKEN:ACPI_AML_NAMESPACE_LOADED`.

### AML-5 — descoberta estática de dispositivos
**✅ COMPROVADO na baseline integrada `3f02decb`.**

Implementação inicial:

```text
a312c3e87c388b70ee7248c2f710232a154cdd70
feat(acpi): discover static AML devices and resources
```

Implementado:
- `_HID`, `_CID`, `_UID`, `_ADR`;
- `_STA` apenas quando constante;
- `_CRS` estático;
- EISA ID;
- ResourceTemplate bounded com EndTag/checksum;
- métodos dinâmicos somente marcados como `requires_evaluator`;
- zero execução de Method/OperationRegion e zero escrita de hardware;
- marker `BAKEN:ACPI_AML_DEVICES_READY`;
- falhas estruturais `HEX=R/S`.

Falha histórica CI #1047 (`34470298359`): ponteiro cru fora de `unsafe` em `aml_discovery_pointer_add`. Corrigido em `3f02decb` sem mudar a lógica; CI #1048 + SMP #151 + NVMe #248 fecharam 3/3.

---

## AML-6a — evaluator controlado, sem hardware

**Estado: ✅ COMPROVADO na branch/PR de validação**

Branch: `aml6a-validation`  
PR: `#16`

Checkpoint certificado:

```text
8e553f791a8e67fa3dd673700077b6c28b485a71
fix(ci): align SMP AML evaluator proof contract
```

Gates do mesmo candidato:

- CI principal #1051 — run `34480220577` — ✅ PASS;
- SMP #154 — run `34480220696` — ✅ PASS, 3/3 boots independentes;
- NVMe-only #251 — run `34480220755` — ✅ PASS.

Isso certifica a engine AML-6a **e** o protocolo de diagnóstico/validação. A `main` não foi movida; `8e553f79` é a baseline verde da PR #16 para iniciar AML-6b.

Escopo comprovado:
- execution frame fixo: Arg0..Arg6 e Local0..Local7;
- `Store` somente para Local/Arg/Null target;
- `Return`;
- Add/Subtract/Multiply/Shift/And/Or/Xor/Not;
- LAnd/LOr/LNot/LEqual/LGreater/LLess;
- If/Else delimitados por PkgLength;
- leitura read-only de Name estático do namespace;
- aridade validada pelos MethodFlags;
- Method Serialized/SyncLevel bloqueado até existir lock AML;
- fuel `4096` e profundidade máxima `8`;
- métodos encadeados, While, Sleep/Stall, Notify, OperationRegion/Field e escrita global continuam proibidos;
- marker de sucesso `BAKEN:ACPI_AML_EVALUATOR_READY`.

### Histórico de validação AML-6a

Primeira rodada da PR #16, head `7dcd1f67`:
- CI #1049 / `34474459862` — ❌ falso positivo;
- SMP #152 / `34474459987` — ✅ 3/3;
- NVMe #249 / `34474459985` — ❌ falso positivo.

Os vermelhos chegaram a `ACPI_AML_EVALUATOR_READY`; a causa era colisão de canais: `HEX=T` já era checkpoint do LAPIC timer e `HEX=U` diagnóstico de userspace.

Correção:

```text
12b97433af677b2ea93764c95c0bcf38cfb8ce4d
fix(acpi): disambiguate AML evaluator diagnostics
```

Foi criado o marker terminal exclusivo:

```text
BAKEN:ACPI_AML_EVALUATOR_FAILED
```

`HEX=T/U` passaram a ser somente detalhes e nunca classificam falha isoladamente.

SMP #153 / `34479698271` então falhou antes do QEMU porque `run_smp_qemu.py` já exigia `ACPI_AML_EVALUATOR_READY`, mas o YAML SMP ainda não o exigia explicitamente. O gate detectou corretamente a divergência.

Correção final:

```text
8e553f791a8e67fa3dd673700077b6c28b485a71
fix(ci): align SMP AML evaluator proof contract
```

O YAML passou a executar o contrato AML-6a, abortar no marker exclusivo de falha e exigir `ACPI_AML_EVALUATOR_READY` em cada boot. A rodada #1051/#154/#251 confirmou 3/3 verde.

---

## AML-6b — predefined methods para discovery

**Estado: ⏳ EM VALIDAÇÃO**

Base de desenvolvimento:

```text
8e553f791a8e67fa3dd673700077b6c28b485a71
```

A implementação candidata é o próximo commit da PR #16 e introduz uma camada separada `aml_dynamic_discovery.sotlas`, sem reescrever AML-5.

### Contrato arquitetural

1. AML-5 continua sendo a fonte estática e marca `*_requires_evaluator`.
2. AML-6a continua sendo a única engine de execução.
3. AML-6b mantém um **overlay read-only**, com buffers/arrays de capacidade fixa e sem heap.
4. Somente `_HID`, `_CID`, `_UID`, `_STA` e `_CRS` marcados pelo AML-5 são candidatos.
5. Somente Method zero-arg, não-Serialized e SyncLevel zero é executado.
6. Falha de opcode/tipo/flag não suportado em um método de firmware deixa o valor **unresolved**; nenhum valor é fabricado.
7. Falha estrutural da própria camada dinâmica é terminal para publicação da plataforma.
8. Nenhum OperationRegion/Field, MMIO/PIO/PCI write, Sleep/Stall, Notify ou efeito de hardware é permitido.

### Validação por predefined object

- `_HID`: Integer EISA válido ou string HID estrita;
- `_CID`: Integer/string ou Package/VarPackage bounded de IDs válidos;
- `_UID`: Integer ou string ASCII imprimível;
- `_STA`: Integer dentro de `0x1F`, rejeitando combinação inválida `0b10` nos bits 0..1;
- `_CRS`: Buffer materializado integralmente, ResourceTemplate bounded, EndTag obrigatório e checksum validado. Nesta fase `BufferSize` deve coincidir com o ByteList real; AML-6b não fabrica o zero-fill implícito ainda.

### Publicação e prova

Nova ordem da barreira de plataforma:

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

`ACPI_AML_DYNAMIC_READY` significa que o passe bounded terminou sobre todos os devices AML-5; não significa que todo método de firmware foi resolvido. Métodos fora do subconjunto seguro permanecem explicitamente pendentes.

CI principal, runner SMP e workflow SMP passam a exigir o marker READY e reconhecer o FAILED de forma fail-closed.

---

## Próximos passos

1. validar o candidato AML-6b na PR #16;
2. exigir CI principal + SMP 3/3 + NVMe-only verdes no mesmo SHA;
3. se houver vermelho, diagnosticar o ponto exato sem relaxar marker/timeout nem alterar Kernel Core;
4. somente após AML-6b 3/3 verde considerar promoção/merge da PR;
5. AML-7: OperationRegion/Field mediados por MMIO/PIO/PCI nativo e com bounds;
6. AML-8: `_PRT`/`_PIC`, `_S5` e power/routing de produção.

Depois: HID adicional/I2C-HID, storage/VFS, rede, áudio, GPU/composição e power/hot-plug.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
