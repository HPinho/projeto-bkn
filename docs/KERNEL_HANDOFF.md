# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este documento é o registro operacional de continuidade do Baken OS. Um recurso só é chamado de comprovado quando existe prova correspondente no runtime/CI; código presente ou teste de fonte isolado não é suficiente.

## Regra de validação

Para alterações relevantes de Fundação, Kernel Core, scheduler, processos, memória, SMP, storage ou ACPI/AML, registrar sempre:

- estado: `⏳ EM VALIDAÇÃO`, `✅ COMPROVADO` ou `❌ FALHOU`;
- SHA exato;
- gates/runs utilizados;
- causa objetiva de qualquer falha;
- correção aplicada e próximo passo.

Nunca esconder regressão aumentando timeout sem causa, removendo marker/teste ou substituindo hardware/protocolo real por mock.

---

## Baseline certificada — Fundação + Kernel Core

**Estado: ✅ CERTIFICADO.**

Baseline atual:

```text
ee19f2624c29ae97075d761eab8807fac4794ccd
fix(scheduler): isolate wait handoff from LAPIC preemption
```

Os três gates obrigatórios passaram no mesmo SHA:

- CI principal #1041 — run `34425865124` — ✅ PASS;
- SMP #144 — run `34425865126` — ✅ PASS, 3/3 boots independentes;
- NVMe-only #241 — run `34425865156` — ✅ PASS.

A baseline anterior `72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8` permanece como checkpoint histórico da conclusão inicial do Kernel Core. `ee19f26` a substitui como baseline operacional porque revalida o mesmo núcleo após a correção do handoff wait/wake e também carrega AML-2.

### Invariantes do Kernel Core que permanecem congelados

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. ownership de frame/stack dinâmico só é liberado após uma entrada posterior do scheduler na CPU anterior;
4. BSP e AP usam o caminho FPU save -> schedule -> CR3/TSS -> restore;
5. o mesmo TID Ring 3 pode migrar BSP -> AP mantendo address-space root e SIMD;
6. reaper/teardown só ocorre depois do abandono físico do frame anterior;
7. `BAKEN:HEX=E:` é terminal para os gates;
8. falhas `HEX=Q` e `HEX=W` permanecem fail-closed.

---

## Regressão WAIT_BLOCKED — encerrada

### SHA `26e56700e4542085eefedd21368ad07b5b445705`

AML-2 foi implementado nesse SHA. Resultados:

- NVMe-only #240 — `34423442122` — ✅ PASS;
- SMP #143 — `34423442160` — ✅ PASS, 3/3;
- CI principal #1040 attempt 1 — `34423442134` — ❌ FAIL.

O CI principal chegou a `BAKEN:ACPI_AML_NAMESPACE_READY`, sem `BAKEN:HEX=E:`, e parou em `BAKEN:WAIT_BLOCKED`. Portanto a falha não estava no namespace AML; o novo layout/tempo voltou a expor uma janela sensível no probe BSP wait/wake.

### Correção `ee19f2624c29ae97075d761eab8807fac4794ccd`

A prova foi separada em duas fases:

- wait/wake por `INT 0x43` com LAPIC periódico temporariamente mascarado;
- sleep por IRQ real do LAPIC, reativado somente depois de a waiter registrar deadline e bloquear em `SLEEP_BLOCKED`.

A sequência observável é protegida por `BAKEN:HEX=W:`:

```text
W:1 -> WAIT_BLOCKED -> W:2 -> WAIT_WAKE -> W:3
-> WAIT_RESUME -> SLEEP_BLOCKED -> W:4 -> W:5
-> SLEEP_WAKE -> SLEEP_RESUME -> W:6
```

Bit 31 em `HEX=W` indica falha explícita. Não houve rollback de ownership SMP, remoção de marker nem relaxamento do timer real. CI #1041, SMP #144 e NVMe #241 fecharam a regressão.

---

## Estado da Fase 2 — AML / Platform / Drivers

**Estado geral: ▶️ EM DESENVOLVIMENTO.**

### AML-0 — Catálogo DSDT/SSDT

**Estado: ✅ COMPROVADO.**

- DSDT validado via FADT;
- SSDTs enumerados com limite fixo;
- definition blocks expostos somente após validação ACPI;
- sem execução AML;
- marker `BAKEN:ACPI_AML_TABLES_READY`.

### AML-1 — Decoder estrutural mínimo

**Estado: ✅ COMPROVADO.**

- cursor limitado/fail-closed;
- `PkgLength` 1..4 bytes;
- `NameString` com `\`, `^`, DualName e MultiName;
- validação `NameSeg`;
- Zero/One/Ones/Byte/Word/DWord/QWord;
- marker `BAKEN:ACPI_AML_DECODER_READY`.

### AML-2 — Namespace core read-only

**Estado: ✅ COMPROVADO na baseline `ee19f26`.**

Implementação original: `26e5670`.

- storage estático de 256 nós;
- raiz explícita;
- nós preparados para Scope/Device/Name/Method;
- parent + NameSeg;
- lookup absoluto e relativo;
- suporte a `^` sem subir acima da raiz;
- duplicatas/capacidade fail-closed;
- API mutável privada durante construção;
- API pública somente de consulta depois de READY;
- self-test para `\_SB_.PCI0._HID` e resolução relativa;
- objetos sintéticos removidos antes da publicação;
- zero execução AML, OperationRegion ou acesso a hardware;
- marker `BAKEN:ACPI_AML_NAMESPACE_READY`.

O namespace real ainda contém somente a raiz. AML-2 certifica a fundação do namespace, não a ingestão real da DSDT/SSDT.

### AML-3 — Data objects + skip grammar-aware

**Estado: ⏳ IMPLEMENTADO; EM VALIDAÇÃO FINAL.**

Implementação:

```text
8966f2507a27fd7263fef31ffe0a965bff930772
feat(acpi): add bounded AML data object parser
```

Novo `kernel/src/acpi/aml_data.sotlas`:

- `StringPrefix` (`0x0D`);
- `BufferOp` (`0x11`);
- `PackageOp` (`0x12`);
- `VarPackageOp` (`0x13`);
- Integer/DataObject mínimo;
- `PackageElement` com subset conhecido de DataObject ou NameString;
- `TermArg` deliberadamente limitado a Integer constante para `BufferSize` e `VarNumElements`;
- packages aninhados com limite explícito;
- `PkgLength` delimita todo corpo consumido;
- bytes restantes/unknown opcode/truncamento falham fechados;
- nenhum scan heurístico de bytes AML.

Limites de segurança:

```text
AML_DATA_MAX_DEPTH = 8
AML_DATA_MAX_OBJECTS = 1024
AML_DATA_MAX_PACKAGE_ELEMENTS = 255
AML_DATA_MAX_STRING_BYTES = 4096
```

Self-tests bare-metal cobrem String, Buffer, Package, VarPackage, package aninhado, NameString como PackageElement, String truncada e opcode não suportado. O novo marker é:

```text
BAKEN:ACPI_AML_DATA_READY
```

Ele é exigido pelos validadores centrais de smoke e SMP e precede `ACPI_AML_NAMESPACE_READY`.

#### Falha de wiring do gate — SMP #145

O primeiro push AML-3 disparou SMP #145 e falhou em `Verify SMP Contracts` antes de build/QEMU. A causa foi documental/CI: `tests/test_local_smp_runner.py` exige que cada marker do runner também apareça literalmente no YAML SMP, e `ACPI_AML_DATA_READY` ainda não estava listado ali. Isso não foi uma falha do parser em runtime.

Correção:

```text
a872661c8c093ff5874e734b77fd05dbb8a713a3
fix(ci): require AML data proof in SMP gate
```

O workflow SMP agora:

- executa `tests/test_acpi_aml_data.py` explicitamente;
- exige `BAKEN:ACPI_AML_DATA_READY` no próprio gate;
- mantém todos os markers SMP/Kernel anteriores.

Validação atual de `a872661c`:

- CI principal #1043 — run `34457568426` — ⏳ em execução;
- SMP #146 — run `34457568498` — ⏳ em execução; `Verify SMP Contracts` já passou, incluindo `test_acpi_aml_data.py` e `compiler.py check kernel/src/main.sotlas`;
- NVMe-only #243 — run `34457568488` — ⏳ em execução; contratos já passaram.

**Não promover AML-3 a `✅ COMPROVADO` até os três gates acima terminarem verdes no mesmo SHA `a872661c`.**

---

## Próximo incremento — AML-4

**Estado: ⬜ BLOQUEADO ATÉ AML-3 FECHAR 3/3 GATES.**

Objetivo: loader real DSDT/SSDT -> namespace, ainda sem evaluator arbitrário.

Implementar, em ordem de definition block e com bounds explícitos:

- `NameOp`;
- `ScopeOp`;
- `ExtOpPrefix + DeviceOp`;
- `MethodOp` apenas como objeto armazenado, não executado;
- objetos de escopo adicionais somente quando necessários;
- DSDT primeiro, SSDTs depois;
- merge/resolução de namespace corretos para `\` e `^`;
- duplicata, overflow, truncamento e opcode não suportado fail-closed;
- novo marker futuro `BAKEN:ACPI_AML_NAMESPACE_LOADED`.

Não implementar ainda evaluator, OperationRegion/Field, `_PRT`, `_S5` ou acesso AML a MMIO/PIO/PCI.

---

## Sequência posterior da trilha AML

- **AML-5:** `_HID`, `_CID`, `_UID`, `_ADR`, `_STA` constante, `_CRS` estático, EISA ID e ResourceTemplate.
- **AML-6:** evaluator limitado com fuel/profundidade, Arg/Local, Return/Store e operações estritamente necessárias.
- **AML-7:** OperationRegion/Field com bounds e acesso mediado por MMIO/PIO/PCI nativo.
- **AML-8:** routing/power (`_PRT`, `_PIC`, `_S5`) e infraestrutura ACPI de produção.

Depois: I2C-HID/HID adicional, VFS/storage de produção, rede, áudio, GPU/aceleração e power/hot-plug.

---

## Gates obrigatórios daqui em diante

Para checkpoint de Fase 2:

```text
CI principal
SMP verification — 3/3 boots independentes
NVMe-only verification
```

Para AML, os markers cumulativos atuais são:

```text
BAKEN:ACPI_AML_TABLES_READY
BAKEN:ACPI_AML_DECODER_READY
BAKEN:ACPI_AML_DATA_READY
BAKEN:ACPI_AML_NAMESPACE_READY
```

Markers futuros são adicionados cumulativamente; nenhum marker antigo deve ser removido para fazer um gate passar.

`HPinho/LangSotlas` permanece somente leitura/referência salvo instrução explícita em contrário.
