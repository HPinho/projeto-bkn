# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-09 (America/Fortaleza).

Este é o documento operacional de continuidade do Baken OS. Ele deve registrar
sempre o que está implementado, o que foi realmente comprovado, regressões
observadas e o próximo passo. Não considerar um recurso certificado apenas por
existir no código ou passar teste de fonte.

## Regra de registro obrigatória

A partir da Fase 2, toda alteração relevante deve deixar neste handoff e em
`docs/BAKEN_OS_ROADMAP.md` um registro com:

- estado: `⏳ EM VALIDAÇÃO`, `✅ COMPROVADO` ou `❌ FALHOU`;
- SHA exato;
- gates executados e números dos runs quando disponíveis;
- causa objetiva quando houver falha;
- correção aplicada e o próximo passo ainda pendente.

Nunca esconder uma regressão relaxando marker, removendo teste ou substituindo
hardware/protocolo real por mock que apenas retorna sucesso.

---

## Baseline certificada — Fundação + Kernel Core

**Estado: ✅ CERTIFICADO.**

Baseline atual:

```text
72422a79dfcec4c9c43bd3a83ef8a9ad90c7c2c8
fix(ci): make SMP runner tests importable when executed directly
```

Os três gates obrigatórios passaram no MESMO SHA:

- CI principal #1039 — run `34421209110` — ✅ PASS;
- SMP #142 — run `34421209023` — ✅ PASS;
- NVMe-only #239 — run `34421209039` — ✅ PASS.

Esse checkpoint encerra a revalidação causada pela regressão ANY/retirement do
SMP #140 e passa a ser a baseline da Fase 2.

### Regressão ANY/retirement encerrada

A regressão mostrava `SMP_RING3_RESUMED_ON_AP` sem alcançar
`SMP_PROCESS_TLB_READY`. A correção preserva o ownership da thread até a CPU
anterior confirmar que saiu fisicamente do frame/stack, enquanto permite que a
afinidade de uma thread READY seja alterada durante o retirement sem transferir
ownership prematuramente.

Invariantes que NÃO podem regredir:

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. owner é liberado apenas numa entrada posterior do scheduler da CPU anterior;
4. BSP e AP usam o mesmo caminho FPU save -> schedule -> CR3/TSS -> restore;
5. processo Ring 3 pode migrar BSP -> AP mantendo TID, root e SIMD;
6. reaper/teardown ocorre somente depois da saída real da CPU anterior;
7. `BAKEN:HEX=E:` continua terminal para o gate;
8. falha `HEX=Q` continua fail-closed.

### Proteção de regressão do Kernel Core

Qualquer alteração em scheduler, IRQ, process registry, address spaces, CR3,
TLB, FPU/SIMD, SMP ou storage só é considerada válida quando os três gates
passarem no mesmo SHA novamente.

O repositório ainda não possui ruleset/proteção administrativa da `main`.
Portanto os gates detectam regressão, mas GitHub ainda permite que um push direto
vermelho entre na branch. Isso não bloqueia a Fase 2, porém continua sendo uma
melhoria administrativa recomendada.

---

## Registro de validação mais recente

### AML-2 / SHA `26e56700e4542085eefedd21368ad07b5b445705`

**Estado do SHA: ❌ NÃO CERTIFICADO COMO CHECKPOINT, apesar de AML-2 ter alcançado o runtime.**

Resultados observados:

- NVMe-only #240 — run `34423442122` — ✅ PASS;
- SMP #143 — run `34423442160` — ✅ PASS, incluindo os 3 boots independentes;
- CI principal #1040 attempt 1 — run `34423442134` — ❌ FAIL no smoke QEMU.

O CI principal completou suíte, grafo Sotlas, build e ISO. No QEMU, o novo
`BAKEN:ACPI_AML_NAMESPACE_READY` apareceu normalmente, sem `BAKEN:HEX=E:`. O
último checkpoint foi `BAKEN:WAIT_BLOCKED`; `WAIT_WAKE`, `WAIT_RESUME` e os
marcadores posteriores não apareceram antes do timeout.

Isso isola a falha fora do parser/namespace AML: o mesmo SHA passou NVMe e SMP
3/3 e o namespace chegou a READY no smoke que falhou. A regressão é tratada
como recorrência da fronteira sensível do probe wait/wake BSP.

### Correção em validação — isolamento do handoff wait/wake

**Estado: ⏳ EM VALIDAÇÃO no commit seguinte a `26e5670`.**

O probe mistura duas provas distintas: handoff software por `INT 0x43` e sleep
por IRQ periódico do LAPIC. Para remover a competição temporal sem enfraquecer
a prova:

1. o BSP mascara somente o LAPIC timer antes de publicar a waiter;
2. executa `bootstrap -> waiter -> WAIT_BLOCKED -> bootstrap` por `INT 0x43`;
3. o bootstrap faz o wake real e cede novamente;
4. a waiter retoma, emite `WAIT_RESUME`, registra o deadline de sleep e bloqueia
   em `SLEEP_BLOCKED` ainda com o timer mascarado;
5. o segundo yield retorna ao bootstrap;
6. somente então o LAPIC periódico é reativado;
7. três ticks reais devem produzir `SLEEP_WAKE`, `SLEEP_RESUME` e o reaper.

Assim wait/wake é uma prova determinística de troca software e sleep continua
uma prova real de hardware/timer. Não houve aumento de timeout, remoção de marker
ou rollback do ownership SMP.

Foram adicionados checkpoints `BAKEN:HEX=W:`. Estágios 1..6 indicam progresso;
bit 31 (`8xxxxxxx`) indica falha explícita no estágio correspondente. Isso evita
que um futuro stall nessa fronteira termine apenas com um marker ambíguo.

O Kernel Core certificado continua sendo `72422a7` até a correção passar os três
gates no mesmo SHA.

---

## Arquitetura que deve permanecer congelada

- UEFI somente bootstrap.
- Após `ExitBootServices()`, zero Boot Services/Runtime Services no kernel.
- Zero Pointer Protocol/Block I/O UEFI como ponte de runtime.
- `BakenBootInfo` apenas transporta dados, nunca funções executáveis de firmware.
- PMM/VMM/page tables são Baken-owned.
- W^X fail-closed e guard stacks permanecem obrigatórios.
- PAT/WC e MMIO pertencem à camada de memória/hardware nativa.
- TSS/RSP0 é per-CPU.
- Python é ferramenta de host; kernel/drivers/UI são Sotlas nativo.
- Compilador Sotlas deve permanecer genérico, sem lógica específica de UI ou
  drivers Baken embutida no compilador.

---

## O que já está implementado e comprovado

### Boot / CPU / memória — ✅

- ExitBootServices real;
- stack trampoline e stack própria;
- CR3 Baken;
- W^X;
- guard stack;
- GDT/segment reload;
- TSS/LTR per-CPU;
- IDT e política de exceções;
- PMM;
- VMM/direct map/active page tables;
- PAT/framebuffer WC;
- DMA;
- auditoria zero-UEFI pós-cutover.

### Plataforma/hardware de fundação — ✅

- ACPI tables básicas;
- MADT;
- LAPIC/IOAPIC;
- IRQ;
- LAPIC timer;
- PCI;
- xHCI/USB HID;
- AHCI;
- NVMe;
- BlockDevice;
- GPT/MBR/FAT32.

### Kernel Core — ✅

- scheduler preemptivo;
- threads de kernel;
- wait/wakeup/sleep;
- exit/reaper/stack release;
- heap PMM-backed;
- registry de processos;
- PID/TID;
- address spaces privados;
- CR3 por processo;
- Ring 3;
- syscalls;
- user-copy;
- isolamento de fault CPL3;
- fault CPL3 também comprovado em AP;
- FPU/SIMD por thread;
- SMP scheduler;
- active address-space tracking por CPU;
- TLB shootdown root-aware;
- processo Ring 3 no AP;
- migração real BSP -> AP;
- preservação FPU/SIMD na migração;
- ownership/retirement sincronizado.

---

## Fase 2 — AML / Platform / Drivers

**Estado geral: ▶️ EM DESENVOLVIMENTO.**

### AML-0 — Catálogo de definition blocks

**Estado: ✅ IMPLEMENTADO E COBERTO PELA BASELINE.**

`kernel/src/acpi/aml_tables.sotlas`:

- prefere DSDT validado pelo FADT;
- enumera SSDTs com limite fixo;
- aceita somente tabelas ACPI previamente validadas;
- expõe payload/length somente de definition blocks catalogados;
- não interpreta opcodes;
- marker obrigatório `BAKEN:ACPI_AML_TABLES_READY`.

### AML-1 — Decoder estrutural mínimo

**Estado: ✅ IMPLEMENTADO E COBERTO PELA BASELINE.**

`kernel/src/acpi/aml_decoder.sotlas`:

- cursor limitado;
- leitura fail-closed;
- `PkgLength` 1..4 bytes;
- valida bits reservados e limites;
- `NameString` com root `\`, parent `^`, DualName e MultiName;
- valida `NameSeg`;
- constantes Zero/One/Ones/Byte/Word/DWord/QWord little-endian;
- self-test bare-metal;
- marker `BAKEN:ACPI_AML_DECODER_READY`.

### AML-2 — Namespace core read-only

**Estado do recurso: ⏳ EM VALIDAÇÃO FINAL.**

Implementado em `26e5670`:

- storage estático com capacidade limitada, sem heap;
- raiz explícita;
- nós tipados preparados para Scope/Device/Name/Method;
- parent index e NameSeg por nó;
- resolução absoluta e relativa de `NameString`;
- suporte a prefixos `^` sem permitir subir acima da raiz;
- detecção de duplicata;
- falha explícita ao exceder capacidade;
- API de construção privada;
- API pública somente de consulta depois de READY;
- self-test cria `\_SB_.PCI0._HID`, testa lookup absoluto e `^`, testa
  duplicata e depois limpa os objetos sintéticos;
- namespace publicado após o self-test contém somente a raiz;
- não executa métodos, não acessa OperationRegion e não toca hardware;
- marker obrigatório `BAKEN:ACPI_AML_NAMESPACE_READY`.

O marker é exigido no smoke QEMU principal, runner SMP local, workflow SMP 3/3
e NVMe-only QEMU. O SMP executa `tests/test_acpi_aml_namespace.py` explicitamente.

`AML_NAMESPACE_READY` certifica o núcleo do namespace, não a ingestão completa
da DSDT/SSDT. O namespace real ainda fica vazio além da raiz; scan cego de bytes
AML desconhecidos continua proibido.

---

## Próximas sucessões AML

### AML-3 — Data objects e skip grammar-aware

Pendências:

- StringPrefix;
- BufferOp;
- PackageOp / VarPackageOp;
- PackageElement;
- DataRefObject mínimo;
- TermArg mínimo necessário para objetos de descoberta;
- rotina de skip somente para produções AML conhecidas e limitadas, nunca scan
  cego de bytes.

### AML-4 — Loader real DSDT/SSDT -> namespace

Implementar parser de declarations em ordem de definition block:

- `NameOp`;
- `ScopeOp`;
- `MethodOp` como objeto armazenado, ainda não executado;
- `ExtOpPrefix + DeviceOp`;
- ThermalZone/Processor/PowerResource quando necessário;
- regras de namespace e resolução corretas para `\` e `^`;
- DSDT primeiro, SSDTs depois;
- capacidade/duplicata/encodings inválidos fail-closed.

Critério: namespace deve conter objetos reais do firmware QEMU e emitir um marker
separado, por exemplo `BAKEN:ACPI_AML_NAMESPACE_LOADED`.

### AML-5 — Objetos de descoberta de dispositivo

Resolver sem executar métodos arbitrários, quando representados como dados:

- `_HID`;
- `_CID`;
- `_UID`;
- `_STA` quando constante;
- `_ADR`;
- `_CRS` estático.

Adicionar decodificação EISA ID e resource templates antes de conectar drivers.

### AML-6 — Evaluator controlado

Somente depois do namespace real estar comprovado:

- execution context com limites de profundidade/instruções;
- Arg0..Arg6 e Local0..Local7;
- Return;
- Store;
- operações aritméticas/lógicas necessárias;
- CondRefOf/If/Else conforme demanda;
- chamada de Method com aridade validada;
- timeout/fuel para impedir firmware AML de prender o kernel.

### AML-7 — OperationRegion / Field

Depois do evaluator:

- SystemMemory;
- SystemIO;
- PCIConfig;
- Field/IndexField quando necessário;
- validação rigorosa de endereço/tamanho;
- acesso por camada apropriada de MMIO/PIO/PCI;
- nunca permitir AML escrever fora da região declarada.

### AML-8 — ACPI de produção e power management

- `_PIC`/routing quando necessário;
- `_PRT`;
- `_S5`/shutdown;
- sleep/wake posterior;
- EC apenas quando houver infraestrutura segura;
- recursos para I2C-HID e outros dispositivos ACPI.

---

## Depois de AML

Ordem recomendada da Fase 2:

1. AML namespace real + evaluator limitado;
2. resource parser / `_CRS`;
3. I2C-HID e HID adicional;
4. VFS/cache/montagem de produção;
5. rede (NIC -> ARP -> IPv4/IPv6 -> UDP/TCP -> DHCP);
6. áudio;
7. GPU/aceleração/composição;
8. hot-plug, power e telemetria de drivers.

A ausência de hardware opcional deve degradar com diagnóstico, nunca derrubar o
kernel.

---

## Gates obrigatórios daqui em diante

Antes de chamar qualquer checkpoint de Fase 2 de comprovado:

```text
CI principal
SMP verification — 3/3 boots independentes
NVMe-only verification
```

Para AML, adicionalmente:

```text
BAKEN:ACPI_AML_TABLES_READY
BAKEN:ACPI_AML_DECODER_READY
BAKEN:ACPI_AML_NAMESPACE_READY
```

Markers futuros devem ser adicionados quando cada sucessão ganhar prova de
runtime. Nenhum marker antigo deve ser removido para fazer um gate passar.

`HPinho/LangSotlas` continua somente leitura/referência salvo instrução explícita
em contrário.
