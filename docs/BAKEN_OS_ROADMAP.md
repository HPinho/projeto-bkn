# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-10 (America/Fortaleza).

Este roadmap separa **implementado**, **em validação**, **comprovado** e **planejado**. Uma feature só é promovida a comprovada quando seus gates obrigatórios passam no mesmo SHA de runtime.

## Estado geral

**Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Kernel Core: ✅ CONCLUÍDO E CERTIFICADO**  
**Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

## Baseline certificada da Fundação + Kernel Core

```text
ee19f2624c29ae97075d761eab8807fac4794ccd
fix(scheduler): isolate wait handoff from LAPIC preemption
```

Gates no mesmo SHA:

| Gate | Resultado |
|---|---|
| CI principal #1041 / `34425865124` | ✅ PASS |
| SMP #144 / `34425865126` | ✅ PASS — 3/3 boots |
| NVMe-only #241 / `34425865156` | ✅ PASS |

A antiga baseline `72422a7` permanece histórica. `ee19f26` é a baseline operacional atual porque revalidou o Kernel Core após a correção do handoff wait/wake e contém AML-2.

### Regressão WAIT_BLOCKED — ✅ ENCERRADA

No SHA `26e5670`, AML-2 chegou a `ACPI_AML_NAMESPACE_READY`, NVMe #240 e SMP #143 passaram, mas o CI #1040 parou em `WAIT_BLOCKED`. A causa foi isolada na competição temporal entre o handoff software do wait/wake e o LAPIC periódico.

`ee19f26` separou as provas:

- wait/wake: `INT 0x43` com timer periódico temporariamente mascarado;
- sleep: timer reativado somente depois de `SLEEP_BLOCKED`, preservando a prova de IRQ real.

Os checkpoints `HEX=W` tornam a fronteira observável. CI #1041 + SMP #144 + NVMe #241 fecharam a regressão.

---

## Política de acompanhamento

Toda alteração relevante deve aparecer aqui e em `docs/KERNEL_HANDOFF.md` como:

- `⏳ EM VALIDAÇÃO` enquanto o código existe mas os gates não fecharam;
- `✅ COMPROVADO` com SHA e runs verdes;
- `❌ FALHOU` com causa, diagnóstico e correção/next step.

Nunca remover teste/marker para mascarar regressão, nunca substituir prova bare-metal por mock e nunca avançar para uma camada dependente enquanto a anterior estiver vermelha.

---

## Fase 0 — Fundação Bare-Metal

**Estado: ✅ CONCLUÍDA.**

Comprovado:

- boot UEFI apenas como bootstrap;
- ExitBootServices real;
- zero UEFI pós-cutover;
- stack própria/trampoline;
- CR3 Baken;
- PMM/VMM/direct-map;
- W^X e guard stack;
- GDT/TSS/LTR/IDT;
- ACPI/MADT;
- LAPIC/IOAPIC/IRQ/timer;
- PCI/DMA;
- xHCI/USB HID;
- AHCI/NVMe/BlockDevice;
- GPT/MBR/FAT32;
- PAT/framebuffer WC.

---

## Fase 1 — Kernel Core

**Estado: ✅ CONCLUÍDA E CERTIFICADA em `ee19f26`.**

Comprovado:

- scheduler preemptivo;
- kernel threads;
- wait/wakeup/sleep;
- exit/reaper/stack release;
- heap PMM-backed;
- processos/PID/TID;
- address spaces privados;
- CR3 por processo;
- Ring 3;
- syscalls e user-copy;
- isolamento de exceções CPL3 no BSP e AP;
- FPU/SIMD por thread;
- scheduler SMP;
- active address-space tracking por CPU;
- TLB shootdown root-aware;
- processo Ring 3 real no AP;
- migração BSP -> AP do mesmo TID;
- preservação FPU/SIMD na migração;
- ownership/retirement sincronizado sem dupla execução;
- protocolo wait/wake isolado da preempção periódica sem enfraquecer sleep real.

Critério permanente: mudanças nessa área exigem novamente CI + SMP 3/3 + NVMe no mesmo SHA.

---

## Fase 2 — Platform e Drivers de produção

**Estado: ▶️ EM DESENVOLVIMENTO.**

### Trilha A — ACPI/AML

#### AML-0 — Catálogo DSDT/SSDT

**Estado: ✅ COMPROVADO.**

- DSDT via FADT validado;
- SSDTs enumerados com limite fixo;
- definition blocks somente após validação;
- marker `BAKEN:ACPI_AML_TABLES_READY`.

#### AML-1 — Decoder estrutural mínimo

**Estado: ✅ COMPROVADO.**

- cursor fail-closed;
- `PkgLength`;
- `NameString` (`\`, `^`, DualName, MultiName);
- `NameSeg`;
- constantes integer AML;
- marker `BAKEN:ACPI_AML_DECODER_READY`.

#### AML-2 — Namespace core read-only

**Estado: ✅ COMPROVADO na baseline `ee19f26`.**

Implementado originalmente em `26e5670`:

- storage estático de 256 nós;
- raiz explícita;
- Scope/Device/Name/Method preparados;
- parent + NameSeg;
- lookup absoluto/relativo;
- parent prefix `^`;
- duplicata/capacidade fail-closed;
- construção privada e leitura pública após READY;
- self-test estrutural;
- namespace sintético limpo antes da publicação;
- zero execução AML/hardware;
- marker `BAKEN:ACPI_AML_NAMESPACE_READY`.

O namespace real ainda contém somente a raiz; o loader DSDT/SSDT real pertence a AML-4.

#### AML-3 — Data objects / parser grammar-aware

**Estado: ⏳ IMPLEMENTADO; EM VALIDAÇÃO FINAL.**

Implementação:

```text
8966f2507a27fd7263fef31ffe0a965bff930772
feat(acpi): add bounded AML data object parser
```

Correção de wiring do gate:

```text
a872661c8c093ff5874e734b77fd05dbb8a713a3
fix(ci): require AML data proof in SMP gate
```

Implementado:

- `StringPrefix`;
- `BufferOp`;
- `PackageOp`;
- `VarPackageOp`;
- DataObject integer/string/buffer/package;
- PackageElement com subset conhecido + NameString;
- TermArg mínimo limitado a Integer constante;
- packages aninhados com profundidade limitada;
- orçamento global de objetos;
- limite de elementos e string;
- corpo delimitado por `PkgLength` e consumo exato;
- unknown opcode/truncamento fail-closed;
- zero scan cego, zero evaluator, zero OperationRegion;
- self-tests bare-metal;
- marker `BAKEN:ACPI_AML_DATA_READY`.

Limites atuais:

```text
AML_DATA_MAX_DEPTH = 8
AML_DATA_MAX_OBJECTS = 1024
AML_DATA_MAX_PACKAGE_ELEMENTS = 255
AML_DATA_MAX_STRING_BYTES = 4096
```

Validação:

- SMP #145 — ❌ falhou em `Verify SMP Contracts` antes de build/QEMU porque o novo marker ainda não aparecia literalmente no YAML; parser não foi executado nesse run;
- correção `a872661c` adicionou `tests/test_acpi_aml_data.py` e `BAKEN:ACPI_AML_DATA_READY` ao workflow SMP;
- CI #1043 / `34457568426` — ⏳ em execução;
- SMP #146 / `34457568498` — ⏳ em execução; contratos + `compiler.py check kernel/src/main.sotlas` já ✅;
- NVMe-only #243 / `34457568488` — ⏳ em execução; contratos já ✅.

**Promoção:** AML-3 só vira `✅ COMPROVADO` quando CI #1043, SMP #146 3/3 e NVMe #243 fecharem verdes no SHA `a872661c`.

#### AML-4 — Loader DSDT/SSDT -> namespace real

**Estado: ⬜ PRÓXIMO, BLOQUEADO ATÉ AML-3 FICAR VERDE.**

Escopo planejado:

- `NameOp`;
- `ScopeOp`;
- `ExtOpPrefix + DeviceOp`;
- `MethodOp` armazenado sem execução;
- DSDT primeiro e SSDTs depois;
- merge/resolução corretos para `\` e `^`;
- parsing somente por produções conhecidas e limitadas;
- duplicata/overflow/truncamento/opcode não suportado fail-closed;
- marker futuro `BAKEN:ACPI_AML_NAMESPACE_LOADED`.

#### AML-5 — Descoberta de dispositivos

**Estado: ⬜ PLANEJADO.**

- `_HID`;
- `_CID`;
- `_UID`;
- `_ADR`;
- `_STA` quando constante;
- `_CRS` estático;
- EISA ID;
- ResourceTemplate parser.

#### AML-6 — Evaluator controlado

**Estado: ⬜ PLANEJADO.**

- execution context limitado;
- Arg0..Arg6 / Local0..Local7;
- Return/Store;
- operações necessárias;
- If/Else quando demandado;
- chamadas de Method com aridade validada;
- fuel, profundidade e timeout.

#### AML-7 — OperationRegion / Field

**Estado: ⬜ PLANEJADO.**

- SystemMemory;
- SystemIO;
- PCIConfig;
- Field/IndexField quando necessário;
- bounds rigorosos;
- acesso apenas por camadas nativas MMIO/PIO/PCI.

#### AML-8 — ACPI power/routing de produção

**Estado: ⬜ PLANEJADO.**

- `_PRT` / `_PIC`;
- `_S5`;
- sleep/wake posterior;
- EC quando houver infraestrutura segura.

### Trilha B — HID adicional

**Estado: ⬜ DEPOIS DO AML/RESOURCE CORE.**

- descoberta de controlador I2C;
- I2C-HID;
- HID report descriptor genérico;
- touchpad/touchscreen;
- hot-plug/erro recuperável.

### Trilha C — Storage de produção

**Estado: ⬜ PLANEJADO.**

- block cache;
- VFS inicial;
- FAT32 robusto;
- handles/arquivos;
- async/completion posterior.

### Trilha D — Rede

**Estado: ⬜ PLANEJADO.**

- NIC;
- Ethernet/ARP;
- IPv4/IPv6;
- ICMP;
- UDP/TCP;
- DHCP/DNS.

### Trilha E — Áudio

**Estado: ⬜ PLANEJADO.**

- HDA/alternativa;
- DMA/ring buffer;
- codecs/mixer;
- API userspace posterior.

### Trilha F — GPU / composição

**Estado: ⬜ PLANEJADO.**

- framebuffer permanece fallback;
- aceleração somente após modelo de memória seguro;
- compositor separado do Kernel Core;
- zero lógica gráfica específica dentro do compilador Sotlas.

---

## Fase 3 — Serviços e userspace

**Estado: ⬜ PLANEJADO.**

- ABI de syscall versionada;
- handles/permissões;
- VFS/file API;
- executáveis Sotlas;
- IPC;
- init/service manager;
- logging/process manager;
- COW/demand paging após política de faults/TLB comprovada.

---

## Fase 4 — Experiência Baken

**Estado: ⬜ PLANEJADO.**

- compositor de produção;
- window manager;
- input unificado;
- fontes/acessibilidade;
- desktop/shell;
- installer/OOBE;
- apps base/configurações/recuperação;
- testes end-to-end da imagem instalada.

---

## Gates obrigatórios

Antes de promover um checkpoint da Fase 2:

```text
CI principal
SMP verification — 3/3 boots independentes
NVMe-only verification
```

Markers AML cumulativos obrigatórios agora:

```text
BAKEN:ACPI_AML_TABLES_READY
BAKEN:ACPI_AML_DECODER_READY
BAKEN:ACPI_AML_DATA_READY
BAKEN:ACPI_AML_NAMESPACE_READY
```

## Regras de prioridade

1. não avançar feature de alto nível sobre gate vermelho;
2. runtime real vale mais que teste de fonte isolado;
3. Kernel Core permanece congelado salvo extensão necessária e revalidada;
4. scheduler/process/page-table/CR3/TLB/FPU exigem CI + SMP + NVMe;
5. cada sucessão AML recebe marker + teste antes de ser comprovada;
6. nunca fazer scan cego de AML desconhecido;
7. firmware AML é input não confiável: bounds, budget/fuel e fail-closed são obrigatórios;
8. ausência de hardware opcional deve degradar com diagnóstico, nunca derrubar o kernel.
