# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este é o registro operacional de continuidade. Código presente não equivale a prova: um incremento só vira baseline quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato.

## Política de baseline verde

A partir de AML-6, `main` permanece no último SHA comprovado. Incrementos são desenvolvidos e corrigidos em branch/PR de validação. Um candidato só substitui a baseline depois de fechar os três gates sem regressão.

Registrar sempre em **este arquivo e `docs/BAKEN_OS_ROADMAP.md`**:

- `⏳ EM VALIDAÇÃO`, `✅ COMPROVADO` ou `❌ FALHOU`;
- SHA exato do código;
- runs/gates usados como prova;
- causa objetiva da falha;
- correção aplicada;
- próximo passo.

Nunca remover marker/teste, aumentar timeout sem causa ou trocar prova bare-metal por mock para esconder regressão.

---

## Baseline operacional atual

**Estado: ✅ CERTIFICADO**

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

Gates no mesmo SHA:

- CI principal #1048 — run `34471015124` — ✅ PASS;
- SMP #151 — run `34471015170` — ✅ PASS, incluindo 3/3 boots e migração Ring3/FPU;
- NVMe-only #248 — run `34471015070` — ✅ PASS.

Essa baseline substitui `ee19f26` como referência operacional. O checkpoint histórico de conclusão inicial do Kernel Core continua sendo `72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8`.

### Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. ownership de frame/stack é liberado somente após entrada posterior do scheduler na CPU anterior;
4. BSP/AP usam FPU save -> schedule -> CR3/TSS -> restore;
5. o mesmo TID Ring3 migra BSP -> AP preservando address-space root e SIMD;
6. reaper/teardown só ocorre após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` é terminal;
8. `HEX=Q` e `HEX=W` permanecem fail-closed.

---

## Estado da Fase 2 — ACPI/AML

### AML-0 — tabelas DSDT/SSDT
**✅ COMPROVADO.** Catálogo validado e marker `BAKEN:ACPI_AML_TABLES_READY`.

### AML-1 — decoder estrutural
**✅ COMPROVADO.** Cursor limitado, PkgLength, NameString/NameSeg e inteiros; marker `BAKEN:ACPI_AML_DECODER_READY`.

### AML-2 — namespace core read-only
**✅ COMPROVADO.** Namespace estático/bounded, resolução absoluta/relativa/parent e janela controlada do loader; marker `BAKEN:ACPI_AML_NAMESPACE_READY`.

### AML-3 — data objects grammar-aware
**✅ COMPROVADO e revalidado na baseline `3f02decb`.** String/Buffer/Package/VarPackage, budgets e nenhuma varredura cega; marker `BAKEN:ACPI_AML_DATA_READY`.

### AML-4 — DSDT/SSDT -> namespace real
**✅ COMPROVADO.**

Checkpoint de certificação:

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
**✅ COMPROVADO na baseline `3f02decb`.**

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
- ResourceTemplate bounded com EndTag;
- métodos dinâmicos somente marcados como `requires_evaluator`;
- zero execução de Method/OperationRegion e zero escrita de hardware;
- marker `BAKEN:ACPI_AML_DEVICES_READY`;
- falhas `HEX=R/S`.

#### Falha observada — CI #1047

**❌ FALHOU** no SHA `a312c3e8`, run `34470298359`, durante a suíte que executa `build_modular`. A segurança Sotlas rejeitou a criação de ponteiro cru em `aml_discovery_pointer_add`: `@system` não substitui `unsafe` explícito.

Correção:

```text
3f02decb2cacc94975113e1886ae3ed74cf8a698
fix(acpi): mark AML pointer conversion unsafe
```

A conversão foi colocada dentro de `unsafe`, sem alterar a lógica de discovery. CI #1048 + SMP #151 + NVMe #248 fecharam a regressão 3/3.

---

## AML-6a — evaluator controlado, sem hardware

**Estado: ⏳ EM VALIDAÇÃO**

Branch: `aml6a-validation`

SHA técnico do candidato:

```text
17267c3d51456935aefbd5347a4041f4eb69a91b
```

Escopo implementado:
- execution frame fixo: Arg0..Arg6 e Local0..Local7;
- `Store` somente para Local/Arg/Null target;
- `Return`;
- Add/Subtract/Multiply/Shift/And/Or/Xor/Not;
- LAnd/LOr/LNot/LEqual/LGreater/LLess;
- If/Else delimitados por PkgLength;
- leitura read-only de Name estático do namespace;
- aridade validada pelos MethodFlags;
- Method serialized/SyncLevel bloqueado até existir lock AML;
- fuel `4096` e profundidade máxima `8`;
- métodos encadeados, While, Sleep/Stall, Notify, OperationRegion/Field e escrita global continuam proibidos;
- self-tests bare-metal sintéticos para aritmética, branch verdadeira/falsa e exaustão de fuel;
- marker `BAKEN:ACPI_AML_EVALUATOR_READY`;
- diagnóstico `HEX=T/U`;
- `PLATFORM_READY` só pode ser emitido depois do marker do evaluator.

O AML-6a **não é usado ainda para resolver `_STA/_CRS/_HID/...` reais**. Essa ligação será AML-6b depois da certificação do engine isolado.

Critério de promoção: PR candidato precisa fechar CI + SMP 3/3 + NVMe-only verde. Até isso ocorrer, `main` permanece em `3f02decb`.

---

## Próximos passos

1. validar AML-6a na branch/PR sem mover `main`;
2. se qualquer gate falhar, registrar causa e corrigir somente na branch;
3. quando 3/3 estiver verde, promover candidato à nova baseline;
4. AML-6b: avaliação controlada de métodos predefinidos zero-arg necessários à descoberta (`_STA`, `_CRS`, `_HID`, `_CID`, `_UID`), mantendo tipos/bounds/fuel;
5. AML-7: OperationRegion/Field mediados por MMIO/PIO/PCI nativo e com bounds;
6. AML-8: `_PRT`/`_PIC`, `_S5` e power/routing de produção.

Depois: HID adicional/I2C-HID, storage/VFS, rede, áudio, GPU/composição e power/hot-plug.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.
