# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-09 (America/Fortaleza).

Este documento separa **implementado**, **em validação**, **comprovado** e
**planejado**. Um recurso só é promovido a comprovado quando os gates exigidos
passam no mesmo SHA da `main`.

## Baseline atual

**Fundação Bare-Metal: ✅ CONCLUÍDA**  
**Kernel Core: ✅ CONCLUÍDO E CERTIFICADO**  
**Platform/Drivers: ▶️ EM DESENVOLVIMENTO**

Baseline certificada da Fundação + Kernel Core:

```text
72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8
```

Gates no mesmo SHA:

| Gate | Resultado |
|---|---|
| CI principal #1039 / `34421209110` | ✅ PASS |
| SMP #142 / `34421209023` | ✅ PASS |
| NVMe-only #239 / `34421209039` | ✅ PASS |

A regressão ANY/retirement do SMP #140 está encerrada nessa baseline. Mudanças
futuras em scheduler, processos, CR3/TLB, FPU/SIMD, SMP ou storage devem
preservar os três gates; uma regressão comprovada reabre somente o componente
afetado, não apaga a certificação histórica desta baseline.

## Política de acompanhamento

Toda alteração relevante deve ser registrada neste roadmap e em
`docs/KERNEL_HANDOFF.md` como:

- `⏳ EM VALIDAÇÃO` enquanto o código já existe mas os gates ainda não fecharam;
- `✅ COMPROVADO` com SHA e runs verdes;
- `❌ FALHOU` com causa, diagnóstico e correção/next step.

Nunca remover um teste ou marker para mascarar regressão.

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

**Estado: ✅ CONCLUÍDA E CERTIFICADA em `72422a7`.**

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
- syscalls;
- user-copy;
- isolamento de exceções CPL3 no BSP e AP;
- FPU/SIMD por thread;
- scheduler SMP;
- active address-space tracking por CPU;
- TLB shootdown root-aware;
- processo Ring 3 real no AP;
- migração BSP -> AP do mesmo TID;
- preservação de contexto FPU/SIMD na migração;
- ownership/retirement sincronizado sem dupla execução.

Critério permanente: qualquer alteração nessas áreas deve voltar a passar CI,
SMP 3/3 e NVMe no mesmo SHA.

---

## Fase 2 — Platform e Drivers de produção

**Estado: ▶️ EM DESENVOLVIMENTO.**

Objetivo: transformar as fundações de hardware em serviços robustos de
plataforma, com descoberta, recursos, power management, drivers opcionais e
interfaces estáveis.

### Trilha A — ACPI/AML

#### AML-0 — Catálogo DSDT/SSDT

**Estado: ✅ COMPROVADO na baseline `72422a7`.**

Implementado em `kernel/src/acpi/aml_tables.sotlas`:

- DSDT validado pelo FADT;
- SSDTs enumerados com limite fixo;
- payload somente de definition blocks catalogados;
- sem execução de AML;
- marker `BAKEN:ACPI_AML_TABLES_READY`.

#### AML-1 — Decoder estrutural mínimo

**Estado: ✅ COMPROVADO na baseline `72422a7`.**

Implementado em `kernel/src/acpi/aml_decoder.sotlas`:

- cursor limitado/fail-closed;
- PkgLength;
- NameString com `\`, `^`, DualName e MultiName;
- validação NameSeg;
- Zero/One/Ones/Byte/Word/DWord/QWord;
- self-test bare-metal;
- marker `BAKEN:ACPI_AML_DECODER_READY`.

#### AML-2 — Namespace core read-only

**Estado: ⏳ EM VALIDAÇÃO neste incremento.**

Implementado:

- novo `kernel/src/acpi/aml_namespace.sotlas`;
- capacidade fixa de 256 nós;
- raiz explícita;
- tipos Scope/Device/Name/Method preparados;
- parent + NameSeg por nó;
- lookup absoluto/relativo;
- suporte a parent prefix `^`;
- detecção de duplicata;
- fail-closed por capacidade;
- API mutável privada durante construção;
- API pública somente de consulta após READY;
- self-test sintético para `\_SB_.PCI0._HID` e resolução via `^`;
- limpeza do self-test antes da publicação;
- zero execução AML e zero acesso a hardware;
- marker `BAKEN:ACPI_AML_NAMESPACE_READY`.

O novo marker passa a ser obrigatório em:

- smoke QEMU principal;
- SMP runner e workflow 3/3;
- NVMe-only QEMU.

`tests/test_acpi_aml_namespace.py` protege as invariantes e é executado
explicitamente pelo workflow SMP, além da suíte geral.

**Importante:** neste estágio o namespace real ainda contém apenas a raiz. O
loader DSDT/SSDT real é o próximo incremento; isso evita scan cego de bytes AML.

#### AML-3 — Data objects / parser grammar-aware

**Estado: ⬜ PRÓXIMO.**

Implementar antes do loader real:

- StringPrefix;
- BufferOp;
- PackageOp;
- VarPackageOp;
- PackageElement;
- DataRefObject mínimo;
- TermArg mínimo para descoberta;
- skip grammar-aware apenas de produções conhecidas e limitadas.

Critério: truncamento/opcode inesperado deve falhar explicitamente, nunca pular
bytes arbitrariamente.

#### AML-4 — Loader DSDT/SSDT -> namespace real

**Estado: ⬜ PLANEJADO.**

- NameOp;
- ScopeOp;
- DeviceOp;
- MethodOp armazenado, ainda sem execução;
- demais objetos de escopo conforme necessidade;
- DSDT primeiro, SSDTs depois;
- namespace merge e resolução corretos;
- duplicatas/overflow/encodings inválidos fail-closed;
- marker futuro `BAKEN:ACPI_AML_NAMESPACE_LOADED`.

#### AML-5 — Descoberta de dispositivos

**Estado: ⬜ PLANEJADO.**

- `_HID`;
- `_CID`;
- `_UID`;
- `_ADR`;
- `_STA` quando data object constante;
- `_CRS` estático;
- EISA ID decoder;
- resource template parser.

#### AML-6 — Evaluator controlado

**Estado: ⬜ PLANEJADO.**

Somente após namespace real:

- execution context limitado;
- Arg0..Arg6;
- Local0..Local7;
- Return/Store;
- operações lógicas/aritméticas necessárias;
- If/Else conforme demanda;
- chamadas de Method com aridade validada;
- fuel/limite de instruções e profundidade.

#### AML-7 — OperationRegion / Field

**Estado: ⬜ PLANEJADO.**

- SystemMemory;
- SystemIO;
- PCIConfig;
- Field/IndexField quando necessário;
- validação de região e bounds;
- integração com camadas nativas MMIO/PIO/PCI;
- AML nunca escreve fora da região declarada.

#### AML-8 — Power/routing ACPI de produção

**Estado: ⬜ PLANEJADO.**

- `_PRT`/routing conforme necessidade;
- `_PIC` quando aplicável;
- `_S5`/shutdown;
- sleep/wake posterior;
- EC somente após infraestrutura segura;
- recursos necessários para I2C-HID e outros dispositivos ACPI.

### Trilha B — HID adicional

**Estado: ⬜ DEPOIS DO AML/RESOURCE CORE.**

- I2C controller discovery;
- I2C-HID;
- HID report descriptor genérico;
- touchpad/touchscreen;
- hot-plug e erros recuperáveis.

### Trilha C — Storage de produção

**Estado: ⬜ PLANEJADO.**

- cache de blocos;
- VFS inicial;
- montagem FAT32 robusta;
- handles/arquivos;
- async/completion posterior;
- política de erro sem derrubar kernel por dispositivo opcional.

### Trilha D — Rede

**Estado: ⬜ PLANEJADO.**

- driver NIC inicial;
- Ethernet;
- ARP;
- IPv4/IPv6;
- ICMP;
- UDP;
- TCP;
- DHCP;
- DNS posterior.

### Trilha E — Áudio

**Estado: ⬜ PLANEJADO.**

- descoberta HDA/alternativa;
- DMA/ring buffer;
- codecs;
- mixer;
- userspace API posterior.

### Trilha F — GPU / composição

**Estado: ⬜ PLANEJADO.**

- manter framebuffer funcional como fallback;
- aceleração somente após driver/modelo de memória seguro;
- compositor separado do kernel core;
- nenhuma lógica gráfica específica dentro do compilador Sotlas.

Saída da Fase 2: drivers possuem timeouts, diagnóstico explícito, QEMU tests e
interfaces de kernel estáveis; ausência de dispositivo opcional não derruba o
sistema.

---

## Fase 3 — Serviços e userspace

**Estado: ⬜ PLANEJADO.**

- ABI de syscall versionada;
- handles/permissões;
- VFS/file API;
- executáveis Sotlas;
- IPC;
- init/service manager;
- logging;
- gerenciamento de processos;
- COW/demand paging somente após política de faults/TLB comprovada.

---

## Fase 4 — Experiência Baken

**Estado: ⬜ PLANEJADO.**

- compositor de produção;
- window manager;
- input unificado;
- fontes/acessibilidade;
- desktop/shell;
- installer;
- OOBE;
- aplicativos-base;
- configurações/recuperação;
- testes end-to-end da imagem instalada.

---

## Regras de prioridade

1. Não contornar gate vermelho com feature de alto nível.
2. Cada marco precisa de prova de runtime, não apenas teste de fonte.
3. Kernel Core permanece congelado salvo extensão necessária e comprovada.
4. Mudanças em scheduler/process/page-table/CR3/TLB/FPU exigem CI + SMP + NVMe.
5. Cada sucessão AML recebe marker e teste antes de ser chamada de comprovada.
6. Nunca fazer scan cego de AML desconhecido; parsing deve respeitar grammar e
   limites do pacote.
7. Firmware AML é input não confiável: bounds, fuel e fail-closed são regra.
8. Drivers opcionais degradam com diagnóstico; memória, isolamento e scheduler
   permanecem fail-closed.
